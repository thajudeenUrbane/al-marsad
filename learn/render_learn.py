"""Turns journeys and the practice bank into HTML. No file is read here except the
templates, and no UI string is written here: every visible string is a key in
learn/i18n/en.json (or, for the shared page frame, dates and status words,
site/i18n/en.json), or comes from the graph through site/model.py and the
marsad-journey export. The markup reuses the site's CSS classes, so site.css styles
most of it; learn.css adds the rest.

Journey pages are rendered from the resolved marsad-journey document
(journey_export.resolve_all) at three depths, each its own static page (design §8):

  discover   the public depth, rendered from the export dict alone: names, dates and
             places, the computed reasons, narration sentences whose claims give a work and
             page (each with its short source line), one ungraded prompt and the next
             directions. It never shows a status, review language, a claim ID, a gloss, a
             note, a basis text or who recorded a claim; Strings.at("discover") refuses
             every key that carries them (ReviewLanguageAtDiscover).
  study      the v1 page (claims with their status and source) plus the layers: narration,
             prompts, next directions, notes, the accepted share and the list state, with
             claim lists capped at 40 per step. A journey with hold_study renders exactly
             as v1 did, with only the additions design §3.7 permits.
  research   Study plus claim IDs, AI glosses (labelled), who recorded each claim, 80
             claims per step, the data files, the hashes and what was left out.

Each depth is cut into pages at its own weight (reader_plans, STEP_HTML_BUDGET bytes of
step HTML per page). The door depth is learn/{slug}/, the others learn/{slug}/{depth}/,
page k of a split depth .../p{k}/. Study and Research claim rows show the same Site
claims the export resolved, found through the export's claim IDs."""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from string import Template

from rdflib import URIRef
from rdflib.namespace import RDFS, SKOS

import display
import journey_export as X
import journeys as J
from journeys import Journey, Reason, Step, term
from model import MRS, Claim, Entity, Site
from render import URL_AGPL, URL_CC_BY_SA, URL_LICENSING

HERE = Path(__file__).resolve().parent
SITE_DIR = HERE.parent / "site"
NAV = (("people", "person"), ("events", "event"), ("places", "place"), ("groups", "group"),
       ("stories", "story"), ("glossary", "glossary"))
QUESTIONS_PER_PAGE = 40


def practice_path(n: int) -> str:
    """The folder of practice page n (1-based), relative to the site root."""
    return "learn/practice/" if n == 1 else f"learn/practice/{n}/"


def practice_page_count(n_questions: int) -> int:
    """How many practice pages a bank of n questions fills (one page when it is empty)."""
    return max(1, -(-n_questions // QUESTIONS_PER_PAGE))
DEPTHS = X.DEPTHS
DEPTH_RANK = {d: i for i, d in enumerate(DEPTHS)}
STEP_HTML_BUDGET = 220_000              # bytes of step HTML per reader page (design §13)
PLAN_ROUNDS = 6                         # page plans are measured until they no longer change
NARRATION = {d: X.DEPTH_POLICY[d]["narration"] for d in DEPTHS}
CLAIM_LIST = {d: X.DEPTH_POLICY[d]["claim_list"] for d in DEPTHS}
NEXT_CAP = {d: X.DEPTH_POLICY[d]["next"] for d in DEPTHS}
DEPTH_LABEL = {"discover": "learn.depth.discover", "study": "learn.depth.study", "research": "learn.depth.research"}
KICKER = {"discover": "learn.door.discover", "study": "learn.door.study", "research": "learn.kicker.research"}
EXCLUDED = {"marker": "learn.research.excluded.marker", "after_prophet": "learn.research.excluded.after_prophet",
            "not_placed": "learn.research.excluded.not_placed", "before": "learn.research.excluded.before"}

# Keys a Discover render may never use (design §8, enforcement 1): status, review language,
# coverage state, legends, claim summaries, the accepted share, list state, research
# data, glosses, checkpoint wording, prose drafts and teacher lessons; and the text that
# rests on claims with no work-and-page source shown: notes, order notes, the side and
# link rows, and every reason but the computed ones (DISCOVER_REASONS).
DISCOVER_FORBIDDEN_PREFIXES = ("status.", "coverage.", "learn.state.", "learn.legend.", "learn.claims.",
                               "learn.named.summary.", "learn.accepted_share.", "learn.order.e3_lists",
                               "learn.order.e3_pending", "learn.research.", "learn.gloss.", "learn.check.",
                               "learn.prose.", "learn.teacher.", "learn.note.", "learn.order_note.",
                               "learn.side.", "learn.links.", "learn.why.")
DISCOVER_FORBIDDEN_KEYS = ("learn.draft_banner", "learn.approved_banner", "learn.ai_note",
                           "learn.rule.separate_records", "story.banner", "claim.recorded_by")
DISCOVER_REASONS = ("learn.why.named", "learn.why.part")    # the computed reasons Discover shows (§8)
SEP = ' <span class="sep" aria-hidden="true">&middot;</span> '
_EMPTY_OL = re.compile(r'<ol class="journey-steps"(?: start="\d+")?>\s*</ol>\n?')


class ReviewLanguageAtDiscover(J.RuleError):
    """A Discover render asked for an i18n key that carries review status or review
    language, or text resting on claims Discover shows no source for (DISCOVER_FORBIDDEN_*).
    Raised at build time, so no such page is written."""


def forbidden_at_discover(key: str) -> bool:
    if key in DISCOVER_REASONS:
        return False
    return key in DISCOVER_FORBIDDEN_KEYS or key.startswith(DISCOVER_FORBIDDEN_PREFIXES)


class Strings:
    """Learn keys first, then the site's keys for the shared frame, dates and statuses.

    at(depth) is a view of the same tables for one depth: at "discover" it raises
    ReviewLanguageAtDiscover for every forbidden key. `used` holds every key any view
    read; `used_at[depth]` the keys read at that depth."""

    def __init__(self, learn: Path, site: Path):
        self.learn: dict[str, str] = json.loads(Path(learn).read_text(encoding="utf-8"))
        self.site: dict[str, str] = json.loads(Path(site).read_text(encoding="utf-8"))
        self.used: set[str] = set()
        self.used_at: dict[str | None, set[str]] = {}
        self.depth: str | None = None
        self._views: dict[str | None, Strings] = {None: self}

    def at(self, depth: str | None) -> "Strings":
        if depth not in self._views:
            view = object.__new__(Strings)
            view.__dict__.update(self.__dict__)     # the same tables, used sets and views
            view.depth = depth
            self._views[depth] = view
        return self._views[depth]

    def raw(self, key: str) -> str:
        if self.depth == "discover" and forbidden_at_discover(key):
            raise ReviewLanguageAtDiscover(f"{key!r} carries review status or review language, or text resting on "
                                           "claims shown without a source, and may not be used on a Discover page "
                                           "(design §8)")
        self.used.add(key)
        self.used_at.setdefault(self.depth, set()).add(key)
        if key in self.learn:
            return self.learn[key]
        return self.site[key]  # a missing key is a build error on purpose

    def t(self, key: str, **kw) -> str:
        s = self.raw(key)
        return s.format(**kw) if kw else s

    def th(self, key: str, **kw) -> str:
        """Escaped template, Arabic runs marked; keyword values must already be HTML."""
        s = display.mark_arabic(html.escape(self.raw(key), quote=False))
        return s.format(**kw) if kw else s

    def tn(self, key: str, n: int, **kw) -> str:
        return self.t(f"{key}.{'one' if n == 1 else 'other'}", n=n, **kw)

    def thn(self, key: str, n: int, **kw) -> str:
        return self.th(f"{key}.{'one' if n == 1 else 'other'}", n=n, **kw)


def esc(s: str) -> str:
    return display.mark_arabic(html.escape(s, quote=False))


def attr(s: str) -> str:
    return html.escape(s, quote=True)


def claim_anchor(cid: str) -> str:
    """The id of a claim's row on a Research page: c-{local name} for an assertion, else
    c- and the whole claim ID, with characters an id should not hold replaced."""
    body = cid[len("assertion/"):] if cid.startswith("assertion/") else cid
    return "c-" + re.sub(r"[^A-Za-z0-9_~-]", "-", body)


# --------------------------------------------------------------------------- page plans
def cut(keys: list[str], sizes: list[int], budget: int, contents: int = 0, apart: frozenset = frozenset(),
        apart_head: int = 0) -> list[list[str]]:
    """Greedy cut in stop order (design §13): one page when everything fits, else pages of
    at most `budget` bytes, page 1 less the contents list. A page holds at least one stop,
    so a single stop over the budget gets a page of its own. The set-apart section's head
    counts with the first set-apart stop of each page."""
    def size(i: int, first: bool) -> int:
        head = apart_head if keys[i] in apart and (first or keys[i - 1] not in apart) else 0
        return sizes[i] + head

    if sum(sizes) + (apart_head if apart else 0) <= budget:
        return [list(keys)]
    pages, cur, used, cap = [], [], 0, budget - contents
    for i, key in enumerate(keys):
        n = size(i, not cur)
        if cur and used + n > cap:
            pages.append(cur)
            cur, used, cap = [], 0, budget
            n = size(i, True)
        cur.append(key)
        used += n
    pages.append(cur)
    return pages


def default_renderer(site: Site) -> "LearnRenderer":
    strings = Strings(HERE / "i18n" / "en.json", SITE_DIR / "i18n" / "en.json")
    return LearnRenderer(site, strings, HERE / "templates")


def reader_plans(site: Site, journeys: list, *, strings: dict | None = None, lists_root=None, bank: list | None = None,
                 graph: dict | None = None, step_budget: int = STEP_HTML_BUDGET,
                 renderer: "LearnRenderer | None" = None) -> dict:
    """{slug: {depth: [[stop keys of a page], ...]}}: the reader's page cuts. Each depth is
    measured at its own weight on pages rendered from the export, then re-measured with the
    URLs of the new cut, until the cut no longer changes (at most PLAN_ROUNDS times)."""
    r = renderer or default_renderer(site)
    plans: dict = {}
    for _ in range(PLAN_ROUNDS):
        docs = X.resolve_docs(site, journeys, plans=plans or None, strings=strings, lists_root=lists_root, bank=bank,
                              graph=graph)
        current = {j.slug: plans.get(j.slug) or X.default_plan(stop_keys(docs[j.slug])) for j in journeys}
        new = {j.slug: r.plan_journey(j, docs, current[j.slug], step_budget) for j in journeys}
        if new == current:
            return new
        plans = new
    return plans


def stop_keys(doc: dict) -> list[str]:
    return [s["key"] for s in doc["stops"]] + [s["key"] for s in doc["set_apart"]]


# --------------------------------------------------------------------------- one journey, one page
@dataclass
class Book:
    """What every page of one journey shares: the engine's journey, its resolved document,
    the documents of every journey (for the other journeys' titles), the page plan and,
    once the export is split, its index.json entry."""
    j: Journey
    doc: dict
    docs: dict
    plan: dict
    entry: dict | None = None
    steps: dict = field(default_factory=dict)     # stop key -> exported step
    st: dict = field(default_factory=dict)        # stop key -> engine Step
    stops: dict = field(default_factory=dict)     # stop key -> head stop or set-apart entry
    apart: frozenset = frozenset()
    order: list = field(default_factory=list)     # every stop key: the steps, then the set-apart people

    @property
    def held(self) -> bool:
        return bool(self.doc.get("hold_study"))


@dataclass
class Ctx:
    """One page: a depth and page number of a journey."""
    book: Book
    depth: str
    k: int
    pages: int
    keys: list
    path: str                                     # learn/{slug}/... with a final /
    base: str                                     # ../ up to the site root
    anchors: set = field(default_factory=set)     # Research claim-row ids already on this page
    prompted: bool = False
    refs: dict | None = None


class LearnRenderer:
    def __init__(self, site: Site, strings: Strings, templates: Path, *, depth: str | None = None,
                 _cache: dict | None = None):
        self.site = site
        self.depth = depth
        self.s = strings.at(depth)
        self.t = self.s.t
        self.tpl_dir = Path(templates)
        self._tpl: dict[tuple[str, str | None], str] = {} if _cache is None else _cache
        self._ix = None

    def at(self, depth: str | None) -> "LearnRenderer":
        """The same renderer at one depth: its strings refuse what that depth may not show,
        and its templates are cached for that depth alone."""
        if depth == self.depth:
            return self
        return LearnRenderer(self.site, self.s, self.tpl_dir, depth=depth, _cache=self._tpl)

    @property
    def ix(self):
        if self._ix is None:
            self._ix = X.claim_index(self.site)
        return self._ix

    # ------------------------------------------------------------------ templates and frame
    def tpl(self, name: str, **vars) -> str:
        """A template with its [[key]] strings filled in. The cache is keyed by (name, depth),
        and the keys are read through this depth's strings when the template loads, so a
        Discover render after a Research render reads the same keys as a fresh one."""
        key = (name, self.depth)
        if key not in self._tpl:
            src = (self.tpl_dir / f"{name}.html").read_text(encoding="utf-8")
            src = re.sub(r"\[\[([a-z0-9_.]+)\]\]", lambda m: html.escape(self.s.t(m.group(1)), quote=False), src)
            self._tpl[key] = src
        return Template(self._tpl[key]).substitute(vars)

    def shell(self, base: str, title: str, body: str, *, body_class: str, crumbs: list, description: str,
              script: bool) -> str:
        nav = [f'<li><a href="{base}">{html.escape(self.t("nav.home"))}</a></li>']
        for key, kind in NAV:
            nav.append(f'<li><a href="{base}{kind}/">{html.escape(self.t("nav." + key))}</a></li>')
        # the section link is marked current on every learn page, as the site does for its sections
        nav.append(f'<li><a href="{base}learn/" aria-current="page">{html.escape(self.t("learn.nav"))}</a></li>')
        items = [f'<li><a href="{base}">{html.escape(self.t("nav.home"))}</a></li>']
        for text, href in crumbs:
            if href is None:
                items.append(f'<li aria-current="page">{esc(text)}</li>')
            else:
                items.append(f'<li><a href="{base}{href}">{esc(text)}</a></li>')
        breadcrumb = (f'<nav class="breadcrumb" aria-label="{attr(self.t("nav.breadcrumb"))}"><ol>'
                      + "".join(items) + "</ol></nav>")
        scripts = f'<script src="{base}learn/assets/learn.js" defer></script>' if script else ""
        full_title = f'{title} {self.t("title.sep")} {self.t("site.name")}'
        return self.tpl("base", lang="en", dir="ltr", title=html.escape(full_title, quote=False),
                        description=attr(description), base=base, body_class=body_class, scripts=scripts,
                        nav="\n".join(nav), breadcrumb=breadcrumb, body=body,
                        url_licensing=URL_LICENSING, url_cc_by_sa=URL_CC_BY_SA, url_agpl=URL_AGPL)

    # ------------------------------------------------------------------ small pieces (v1)
    def link(self, base: str, iri: str | None) -> str:
        if not iri:
            return f'<span class="not-recorded">{html.escape(self.t("common.not_recorded"))}</span>'
        e = self.site.entity(iri)
        if e is None:
            return esc(self.site.label_of(iri))
        return f'<a href="{base}{e.kind}/{e.pid}/">{esc(e.name)}</a>'

    def status_html(self, status: str | None) -> str:
        if status:
            word = display.t_opt(self.t, f"status.{status}", status)
            cls = f"status-{attr(status)}"
        else:
            word, cls = self.t("status.none"), "status-none"
        return f'<span class="status {cls}">{html.escape(self.t("status.label", value=word))}</span>'

    def coverage_html(self, e: Entity) -> str:
        label = display.t_opt(self.t, f"coverage.{e.coverage}", e.coverage_label or self.t("common.not_recorded"))
        return (f'<span class="status coverage-{attr(e.coverage or "none")}">'
                f'{html.escape(self.t("coverage.label", value=label))}</span>')

    def source_html(self, base: str, c: Claim) -> str:
        label = html.escape(self.t("claim.source"))
        if c.citation:
            cit = esc(c.citation)
            story = self.site.entity(c.story) if c.story else None
            if story is not None:
                cit = f'<a href="{base}story/{story.pid}/">{cit}</a>'
            return f'<span class="source">{label} {cit}</span>'
        if c.basis:
            return f'<span class="source">{label} {esc(display.honour(c.basis.text))}</span>'
        if c.agents:
            who = "; ".join(a.label for a in c.agents)
            return f'<span class="source">{html.escape(self.t("claim.recorded_by", value=who))}</span>'
        return (f'<span class="source not-recorded">{label} '
                f'{html.escape(self.t("common.not_recorded"))}</span>')

    def predicate_text(self, c: Claim) -> str:
        return self.t(c.predicate) if c.predicate_is_key else c.predicate

    def claim_li(self, base: str, c: Claim, extra_class: str = "", show_source: bool = True) -> str:
        sentence = (f'{self.link(base, c.subject)} <span class="rel">{esc(self.predicate_text(c))}</span> '
                    f'{self.link(base, c.object)}')
        parts = [f'<p class="claim-text">{sentence}</p>']
        if c.kind == "participation" and c.role:
            parts.append(f'<p class="claim-role">{html.escape(self.t("claim.role", value=c.role.text))}</p>')
        elif c.role:
            parts.append(f'<p class="claim-role">{esc(display.honour(c.role.text))}</p>')
        if c.qualifiers:
            parts.append('<p class="claim-marker">' + esc(self.t("claim.marker", value="; ".join(c.qualifiers))) + "</p>")
        meta = [self.status_html(c.status)]
        if show_source:
            meta.append(self.source_html(base, c))
        parts.append('<p class="claim-meta">' + SEP.join(meta) + "</p>")
        cls = f"claim {extra_class}".strip()
        return f'<li class="{cls}">' + "".join(parts) + "</li>"

    def words_list(self, words: list[str]) -> str:
        quoted = [self.t("learn.quote", value=w) for w in words]
        return self.join_or(quoted)

    def join_or(self, items: list[str]) -> str:
        return self.join(items, "or")

    def join(self, items: list[str], word: str) -> str:
        if len(items) == 1:
            return items[0]
        if len(items) == 2:
            return self.t(f"learn.list.two_{word}", a=items[0], b=items[1])
        return self.t(f"learn.list.many_{word}", head=self.t("learn.list.sep").join(items[:-1]), last=items[-1])

    def join_html(self, items: list[str], word: str) -> str:
        """join() for items that are already HTML."""
        if not items:
            return ""
        if len(items) == 1:
            return items[0]
        if len(items) == 2:
            return self.s.th(f"learn.list.two_{word}", a=items[0], b=items[1])
        return self.s.th(f"learn.list.many_{word}", head=html.escape(self.t("learn.list.sep")).join(items[:-1]),
                         last=items[-1])

    def status_counts(self, claims: list[Claim]) -> tuple[str, int]:
        """('7 proposed, 1 accepted', number of claims) for assertions; links without a status counted apart."""
        counts: dict[str, int] = {}
        for c in claims:
            if c.kind == "assertion":
                counts[c.status or "none"] = counts.get(c.status or "none", 0) + 1
        order = ["accepted", "under_review", "proposed", "rejected", "superseded", "none"]
        bits = []
        for k in order + sorted(set(counts) - set(order)):
            if counts.get(k):
                word = self.t("status.none") if k == "none" else display.t_opt(self.t, f"status.{k}", k)
                bits.append(self.t("learn.count_status", n=counts[k], status=word))
        return self.t("learn.list.sep").join(bits), sum(counts.values())

    def date_text(self, e: Entity) -> str | None:
        for x in e.data.get("dates") or []:
            v = display.format_extent(x, self.t)
            if v["text"]:
                notes = [n for n in v["notes"] if n]
                return esc(v["text"]) + (f' <span class="note">({esc("; ".join(notes))})</span>' if notes else "")
        return None

    # ------------------------------------------------------------------ rule in plain words (v1)
    def rule_html(self, j: Journey) -> str:
        spec, sel = j.spec, j.spec["select"]
        paras = []
        if sel["type"] == "events":
            paras.append(self.rule_events(sel))
        elif sel["type"] == "people":
            ev = sel["events"]
            paras.append(self.t("learn.rule.people", words=self.words_list(self.named_words(ev["named"])),
                                kinds=self.kinds_text(ev["named"]["kinds"]),
                                records=self.t("learn.rule.people_records") if sel["participation"]["records"] else "",
                                claims=self.join_or([self.t("learn.quote", value=self.term_label(c))
                                                     for c in sel["participation"]["claims"]])))
            if ev["named"].get("not_words"):      # the events chosen by name, before the links add more
                paras.append(self.rule_not_words(ev["named"]))
            if ev["max_links"]:
                paras.append(self.rule_follow(ev, "learn.rule.people_follow"))
            if sel["also_show"]:
                paras.append(self.t("learn.rule.also_show", kinds=self.join_or(
                    [self.t("learn.quote", value=self.term_label(c)) for c in sel["also_show"]])))
            if sel["set_apart"]:
                paras.append(self.t("learn.rule.set_apart", markers=self.join_or(
                    [self.t("learn.quote", value=self.term_label(q)) for q in sel["set_apart"]])))
        else:
            parts = self.join_or([self.t("learn.quote", value=display.name_display(p)) for p in j.part_labels])
            paras.append(self.t("learn.rule.stories", words=self.words_list(sel["part"]["words"]), parts=parts))
        paras.append(self.t(f"learn.order.{self.order_shown(j)}"))
        if sel.get("group_by") == "side":
            paras.append(self.t("learn.rule.group_side"))   # the order above holds inside each group (§6.4)
        if j.mixes_stories_and_events:
            paras.append(self.t("learn.rule.separate_records"))
        if j.order_conflict:
            paras.append(self.t("learn.rule.order_conflict"))
        return "".join(f"<p>{esc(p)}</p>" for p in paras)

    def order_shown(self, j: Journey) -> str:
        """The order a page states: the one applied. An e3 journey whose list file is not
        reviewed is ordered, and so described, as the Prophet first, then by name."""
        applied = j.order_applied or j.spec["order"]
        return "prophet_first_then_name" if applied == "e3_pending" else applied

    def rule_not_words(self, named: dict) -> str:
        return self.t("learn.rule.not_words", words=self.words_list(named["not_words"]))

    def kinds_text(self, kinds: list[str]) -> str:
        return self.t("learn.kinds." + "_".join(sorted(kinds)))

    def rule_events(self, sel: dict) -> str:
        text = self.t("learn.rule.events", kinds=self.kinds_text(sel["named"]["kinds"]),
                      words=self.words_list(self.named_words(sel["named"])))
        if sel["named"].get("not_words"):
            text += " " + self.rule_not_words(sel["named"])
        if sel["max_links"]:
            text += " " + self.rule_follow(sel, "learn.rule.events_follow")
        return text

    @staticmethod
    def named_words(named: dict) -> list[str]:
        """The rule's words, and its phrase as one quoted item."""
        return list(named.get("words") or []) + ([" ".join(named["phrase"])] if named.get("phrase") else [])

    def rule_follow(self, rule: dict, key: str) -> str:
        links = self.join([self.t(f"learn.follow.{f}") for f in rule["follow"]], "and")
        return self.s.tn(key, rule["max_links"], links=links)

    def term_label(self, curie: str) -> str:
        """The graph's own label for an ontology term named in a rule."""
        node = term(curie, "rule")
        for p in (SKOS.prefLabel, RDFS.label):
            v = self.site.first_lit(node, p)
            if v:
                return v.text
        return curie.split(":", 1)[1]

    # ------------------------------------------------------------------ steps (v1)
    def reason_html(self, base: str, r: Reason, positions: dict, source=None) -> str:
        """positions: IRI -> (step number, href) of every step; source(claim) gives a claim's
        source span (v1: source_html)."""
        source = source or (lambda c: self.source_html(base, c))
        other = ""
        if r.other:
            other = self.link(base, r.other)
            if r.other in positions:
                n, href = positions[r.other]
                other += " " + self.s.th("learn.step_ref", n=f'<a href="{href}">{n}</a>')
        if r.kind == "named":
            text = self.s.th("learn.why.named", word=html.escape(self.t("learn.quote", value=r.word), quote=False))
        elif r.kind == "event_claim":
            text = self.s.th("learn.why.event_claim", other=other,
                             label=esc(self.t("learn.quote", value=r.label or "")))
        else:
            text = self.s.th(f"learn.why.{r.kind}", other=other)
        meta = []
        if r.kind != "named":
            if r.claims:
                for c in r.claims:
                    meta.append(self.status_html(c.status) + SEP + source(c))
            else:
                meta.append(self.status_html(None) + SEP + f'<span class="note">{html.escape(self.t("learn.why.plain_link"))}</span>')
        out = f'<li><p>{text}</p>'
        if meta:
            out += "".join(f'<p class="claim-meta">{m}</p>' for m in meta)
        return out + "</li>"

    def order_html(self, st: Step, positions: dict) -> str:
        if not st.order_note:
            return ""
        n, href = positions.get(st.order_ref, (None, None))
        ref = f'<a href="{href}">{n}</a>' if n else ""
        return f'<p class="order-note">{self.s.th("learn.order_note." + st.order_note, n=ref)}</p>'

    def step_head(self, base: str, n: int, e: Entity) -> str:
        kind = self.t(f"type.{e.subtype or e.kind}")
        return (f'<h3 class="step-title" id="step-{n}-title"><span class="step-no">{self.s.th("learn.step_no", n=n)}</span> '
                f'<a href="{base}{e.kind}/{e.pid}/">{esc(e.name)}</a> <span class="kind">({html.escape(kind)})</span></h3>')

    def facts_line(self, base: str, e: Entity) -> str:
        """When and where, as recorded. An event says "not yet recorded" for a missing
        value; a story, which is a narrative rather than a dated record, just leaves it out."""
        bits = []
        when = self.date_text(e)
        places = e.data.get("places") or []
        where = ", ".join(self.link(base, p) for p in places) if places else None
        if e.kind == "event" or when:
            bits.append(self.s.th("learn.facts.when", value=when or self.not_recorded()))
        if e.kind == "event" or where:
            bits.append(self.s.th("learn.facts.where", value=where or self.not_recorded()))
        if e.kind == "story" and e.data.get("number") is not None:
            bits.append(html.escape(self.t("fact.story_number", n=e.data["number"], total=len(self.site.by_kind["story"]))))
        return f'<p class="step-facts">{SEP.join(bits)}</p>' if bits else ""

    def not_recorded(self) -> str:
        return f'<span class="not-recorded">{html.escape(self.t("common.not_recorded"))}</span>'

    def claims_block(self, base: str, e: Entity, open_: bool) -> str:
        claims = self.site.claims.get(e.iri, [])
        if not claims:
            return f'<p class="claims-summary">{html.escape(self.t("learn.claims.none"))}</p>'
        summary, n_assert = self.status_counts(claims)
        n_links = sum(1 for c in claims if c.kind != "assertion")
        lines = []
        if n_assert:
            lines.append(self.s.tn("learn.claims.assertions", n_assert, statuses=summary))
        if n_links:
            lines.append(self.s.tn("learn.claims.links", n_links))
        rows = sorted(claims, key=lambda c: (c.kind != "assertion", display.sort_key(self.site.label_of(c.subject)),
                                             c.predicate, c.object, c.node or ""))
        lis = "\n".join(self.claim_li(base, c) for c in rows)
        op = " open" if open_ else ""
        return (f'<p class="claims-summary">{esc(" ".join(lines))}</p>'
                f'<details class="step-claims"{op}><summary>{html.escape(self.s.tn("learn.claims.show", len(claims)))}</summary>'
                f'<ul class="claim-list">\n{lis}\n</ul></details>')

    def step_li(self, base: str, j: Journey, n: int, st: Step, positions: dict, anchor: str | None = None) -> str:
        """The v1 step. A held Study page (design §3.7) uses it as it is, plus the anchor span."""
        e = st.entity
        t = j.spec["select"]["type"]
        study = j.spec["door"] == "study"
        parts = [self.step_head(base, n, e), self.facts_line(base, e), f'<p class="coverage">{self.coverage_html(e)}</p>']
        if t == "events":
            if e.kind == "story":
                parts.append(f'<p class="banner" role="note">{html.escape(self.t("story.banner"))}</p>')
            why = "".join(self.reason_html(base, r, positions) for r in st.reasons)
            parts.append(f'<div class="step-why"><h4>{html.escape(self.t("learn.why.heading"))}</h4><ul class="plain">{why}</ul></div>')
            if st.links:
                more = "".join(self.reason_html(base, r, positions) for r in st.links)
                parts.append(f'<div class="step-why step-links"><h4>{html.escape(self.t("learn.links.heading"))}</h4>'
                             f'<ul class="plain">{more}</ul></div>')
            parts.append(self.order_html(st, positions))
            parts.append(self.claims_block(base, e, open_=study))
        elif t == "people":
            recs = "\n".join(self.claim_li(base, c) for c in st.records)
            parts.append(f'<div class="step-records"><h4>{html.escape(self.s.tn("learn.records.heading", len(st.records)))}</h4>'
                         f'<ul class="claim-list">\n{recs}\n</ul></div>')
            if st.contrary:
                con = "\n".join(self.claim_li(base, c, "contrary") for c in st.contrary)
                parts.append(f'<div class="step-contrary"><h4>{html.escape(self.s.tn("learn.contrary.heading", len(st.contrary)))}</h4>'
                             f'<ul class="claim-list">\n{con}\n</ul></div>')
        else:
            parts.append(f'<p class="banner" role="note">{html.escape(self.t("story.banner"))}</p>')
            parts.append(f'<p class="read-story"><a href="{base}{e.kind}/{e.pid}/">{html.escape(self.t("learn.read_story"))}</a></p>')
            summary, n_claims = self.status_counts(st.records)
            sources = []
            for c in st.records:
                s = self.source_html(base, c)
                if s not in sources:
                    sources.append(s)
            rows = "\n".join(self.claim_li(base, c, show_source=False) for c in st.records)
            op = " open" if study else ""
            named = (f'<p class="claims-summary">{esc(self.s.tn("learn.named.summary", n_claims, statuses=summary))}</p>'
                     f'<details class="step-claims"{op}><summary>{html.escape(self.s.tn("learn.named.show", len(st.records)))}</summary>'
                     f'<ul class="claim-list">\n{rows}\n</ul>'
                     + "".join(f'<p class="claim-meta">{s}</p>' for s in sources) + "</details>")
            parts.append(named if st.records else f'<p class="claims-summary">{html.escape(self.t("learn.named.none"))}</p>')
        body = "\n".join(p for p in parts if p)
        span = f'<span id="s-{attr(anchor)}"></span>\n' if anchor else ""
        return (f'<li class="step" id="step-{n}" data-step="{attr(e.pid)}" aria-labelledby="step-{n}-title">\n'
                f'{span}{body}\n</li>')

    def group_head(self, g: dict, n: int) -> str:
        """The heading and lead of an exported group ({key, t, lead, from, to}), before step n."""
        lead = f'<p class="group-lead">{esc(self.t(g["lead"]))}</p>' if g["lead"] else ""
        return (f'</ol>\n<h3 class="group-heading" id="group-{attr(g["key"])}">{esc(self.t(g["t"]))}</h3>{lead}\n'
                f'<ol class="journey-steps" start="{n}">')

    def v1_apart_li(self, base: str, st: Step) -> str:
        e = st.entity
        recs = "\n".join(self.claim_li(base, c) for c in st.records + st.contrary)
        return (f'<li class="apart"><span id="s-{attr(e.pid)}"></span><h3><a href="{base}{e.kind}/{e.pid}/">{esc(e.name)}</a></h3>'
                f'<p class="coverage">{self.coverage_html(e)}</p><ul class="claim-list">\n{recs}\n</ul></li>')

    def banner(self, j: Journey) -> str:
        if j.is_draft:
            return f'<p class="banner" role="note"><strong>{html.escape(self.t("learn.draft_banner"))}</strong></p>'
        dates = {a["who"]: a["date"] for a in j.spec["approved_by"]}
        return (f'<p class="banner" role="note">{html.escape(self.t("learn.approved_banner", maintainer=dates.get("maintainer", ""), board=dates.get("review_board", "")))}</p>')

    def scale(self, j: Journey) -> str:
        t = j.spec["select"]["type"]
        if t == "people":
            text = self.s.tn("learn.scale.people", len(j.steps), apart=len(j.set_apart), universe=j.universe)
            if j.set_apart:
                text += " " + self.s.tn("learn.scale.apart", len(j.set_apart))
        else:
            text = self.s.tn(f"learn.scale.{t}", len(j.steps), universe=j.universe)
        return f'<p class="scale">{html.escape(text)}</p>'

    def progress_ui(self, total: int) -> str:
        return self.tpl("progress", total=total)

    def ai_involved(self, j: Journey) -> bool:
        """True if a step, an anchor or a shown record comes from an AI-generated work."""
        def ai_story(iri: str | None) -> bool:
            e = self.site.entity(iri) if iri else None
            return bool(e and e.kind == "story" and (e.data.get("work") or {}).get("ai"))

        for st in j.steps + j.set_apart:
            if ai_story(st.iri):
                return True
            for c in st.records + st.contrary + [c for r in st.reasons for c in r.claims]:
                if c.ai_draft or ai_story(c.object) or ai_story(c.subject):
                    return True
        return any(ai_story(a) for a in j.anchors)

    # ------------------------------------------------------------------ journeys: plans and pages
    def book(self, j: Journey, docs: dict, plan: dict, entry: dict | None = None) -> Book:
        doc = docs[j.slug]
        engine = {st.entity.pid: st for st in j.steps + j.set_apart}
        return Book(j=j, doc=doc, docs=docs, plan=plan, entry=entry,
                    steps={s["key"]: s for s in doc["steps"]}, st=engine,
                    stops={s["key"]: s for s in doc["stops"] + doc["set_apart"]},
                    apart=frozenset(s["key"] for s in doc["set_apart"]), order=stop_keys(doc))

    def ctx(self, book: Book, depth: str, k: int) -> Ctx:
        pages = book.plan[depth]
        path = X.page_url(book.doc["slug"], book.doc["door"], depth, k)
        return Ctx(book=book, depth=depth, k=k, pages=len(pages), keys=list(pages[k - 1]), path=path,
                   base="../" * path.count("/"))

    def plan_journey(self, j: Journey, docs: dict, plan: dict, budget: int) -> dict:
        """The page cut of one journey at every depth, measured on pages rendered with `plan`."""
        book = self.book(j, docs, plan)
        out = {}
        for depth in DEPTHS:
            r = self.at(depth)
            sizes: dict[str, int] = {}
            for k in range(1, len(plan[depth]) + 1):
                ctx = r.ctx(book, depth, k)
                for key in ctx.keys:
                    sizes[key] = len(r.item(ctx, key).encode("utf-8"))
            first = r.ctx(book, depth, 1)
            contents = len(r.contents_html(first).encode("utf-8"))
            head = len("".join(r.apart_head(first)).encode("utf-8")) if book.apart else 0
            out[depth] = cut(book.order, [sizes[k] for k in book.order], budget, contents, book.apart, head)
        return out

    def journey_pages(self, j: Journey, docs: dict, plan: dict, entry: dict | None = None) -> dict[str, str]:
        """{page path (learn/{slug}/...): HTML} for every depth and page of one journey."""
        book = self.book(j, docs, plan, entry)
        out = {}
        for depth in DEPTHS:
            r = self.at(depth)
            for k in range(1, len(plan[depth]) + 1):
                ctx = r.ctx(book, depth, k)
                out[ctx.path] = r.held_page(ctx) if depth == "study" and book.held else r.page(ctx)
        return out

    def item(self, ctx: Ctx, key: str) -> str:
        """The HTML of one stop on its page: a step (with the heading of a group it opens) or
        a set-apart person."""
        held = ctx.depth == "study" and ctx.book.held
        if key in ctx.book.apart:
            if held:
                return self.v1_apart_li(ctx.base, ctx.book.st[key])
            return self.apart_discover(ctx, key) if ctx.depth == "discover" else self.apart_deep(ctx, key)
        head = self.group_head_for(ctx, key)
        if held:
            st = ctx.book.st[key]
            return head + self.step_li(ctx.base, ctx.book.j, ctx.book.steps[key]["n"], st, self.positions(ctx), key)
        if ctx.depth == "discover":
            return head + self.discover_step(ctx, key)
        return head + self.deep_step(ctx, key)

    def group_head_for(self, ctx: Ctx, key: str) -> str:
        """The heading and lead of a titled group where it starts, and again at the top of
        every later page that starts inside it, so that no page shows its steps without them."""
        n = ctx.book.steps[key]["n"]
        for g in ctx.book.doc["groups"]:
            if g["t"] and (g["from"] == n or (key == ctx.keys[0] and g["from"] < n <= g["to"])):
                return self.group_head(g, n)
        return ""

    def titled_group(self, ctx: Ctx, step: dict) -> dict | None:
        """The exported group of a step when it has a heading (the against group), else None."""
        return next((g for g in ctx.book.doc["groups"] if g["t"] and g["key"] == step.get("group")), None)

    def positions(self, ctx: Ctx) -> dict:
        """IRI -> (step number, href) for every step of the journey, from this page."""
        if ctx.refs is None:
            ctx.refs = {ctx.book.st[key].iri: (step["n"], self.stop_href(ctx, key))
                        for key, step in ctx.book.steps.items() if step["n"]}
        return ctx.refs

    def stop_href(self, ctx: Ctx, key: str) -> str:
        """A link to a stop: #step-N (or #s-{key} when set apart) on this page, else the URL
        of the page at this depth that holds it."""
        url = ctx.book.stops[key]["urls"][ctx.depth]
        page, frag = url.split("#", 1)
        if page == ctx.path:
            n = ctx.book.steps[key]["n"]
            return f"#step-{n}" if n else f"#{frag}"
        return ctx.base + url

    # ------------------------------------------------------------------ pieces from the export
    def entity_rec(self, ctx: Ctx, ref: str) -> dict:
        return ctx.book.doc["entities"][ref]

    def ref_link(self, ctx: Ctx, ref: str) -> str:
        """An exported entity: a link to its page, or its label as data when it has none."""
        e = self.entity_rec(ctx, ref)
        if e["kind"] == "node":
            return f'<span class="data">{esc(e["name"])}</span>'
        return f'<a href="{ctx.base}{ref}/">{esc(e["name"])}</a>'

    def ref_data(self, ctx: Ctx, ref: str) -> str:
        return f'<span class="data">{esc(self.entity_rec(ctx, ref)["name"])}</span>'

    def term_span(self, ctx: Ctx, ref: str) -> str:
        label = (ctx.book.doc["terms"].get(ref) or {}).get("en") or ref.split(":", 1)[-1]
        return f'<span class="term">{esc(label)}</span>'

    @staticmethod
    def data_span(value: str, lang: str | None = None) -> str:
        """A recorded value as written. An Arabic literal is marked as Arabic, right to left;
        Arabic runs inside any other value are marked by esc()."""
        if lang == "ar":
            return f'<span class="data" lang="ar" dir="rtl">{html.escape(value, quote=False)}</span>'
        lang_attr = f' lang="{attr(lang)}"' if lang and lang != "en" else ""
        return f'<span class="data"{lang_attr}>{esc(value)}</span>'

    def sentence_html(self, ctx: Ctx, item: dict) -> str:
        """A narration item as a sentence: its template filled with names, terms and literals
        from the export, then its marker sentences."""
        slots = {}
        for k in ("subject", "object", "event"):
            if item.get(k):
                slots[k] = self.ref_link(ctx, item[k])
        for k in ("role", "relation"):
            if item.get(k):
                slots[k] = self.term_span(ctx, item[k])
        if item.get("text"):
            slots["text"] = self.data_span(item["text"]["value"], item["text"].get("lang"))
        text = self.s.th(item["t"], **slots)
        for m in item.get("markers") or []:
            text += " " + self.s.th(m["t"], marker=self.term_span(ctx, m["marker"]))
        return text

    def sources_html(self, ctx: Ctx, cids: list[str]) -> str:
        """The source lines of claims at this depth, each in its own .source span. As on a
        claim row (source_x), the claim.source label goes before a citation, a basis or "not
        yet recorded", never before a line that only says who recorded the claim: an agent
        is not a source."""
        doc = ctx.book.doc
        labelled, agents, seen = [], [], set()
        for cid in cids:
            rec = doc["claims"][cid]
            text = X.source_line(rec, ctx.depth, doc["passages"], self.t)
            if not text or text in seen:
                continue
            seen.add(text)
            cite = (doc["passages"].get(rec.get("passage") or "") or {}).get("cite")
            if cite or rec.get("basis"):
                labelled.append(f'<span class="source">{esc(text)}</span>')
            elif rec.get("recorded_by"):
                agents.append(f'<span class="source">{esc(text)}</span>')
            else:
                labelled.append(f'<span class="source not-recorded">{esc(text)}</span>')
        bits = ([f'{html.escape(self.t("claim.source"))} {SEP.join(labelled)}'] if labelled else []) + agents
        return f' <span class="sources">{SEP.join(bits)}</span>' if bits else ""

    def refs_html(self, ctx: Ctx, cids: list[str], linkable: set) -> str:
        """Research: links to the claim rows behind a sentence instead of its source line."""
        links = [f'<a class="claim-ref" href="#{claim_anchor(c)}">{esc(c)}</a>' for c in cids
                 if claim_anchor(c) in linkable]
        return f' <span class="claim-refs">{SEP.join(links)}</span>' if links else ""

    def sentence_li(self, ctx: Ctx, item: dict, cids: list[str], linkable: set | None = None) -> str:
        body = self.sentence_html(ctx, item)
        if ctx.depth == "research":
            tail = self.refs_html(ctx, cids, linkable if linkable is not None else ctx.anchors)
        else:
            tail = self.sources_html(ctx, cids)
        return f'<li class="sentence">{body}{tail}</li>'

    def eligible(self, ctx: Ctx, cids: list[str]) -> list[str]:
        claims = ctx.book.doc["claims"]
        return [c for c in cids if claims[c]["discover"]]

    def prompts_html(self, ctx: Ctx, step: dict, linkable: set | None = None, shown: set | None = None) -> str:
        """Ungraded prompts, each a details element with no form control: one at Discover
        (whose answer shows only claims with a work and page), every one at Study and Research.
        An answer is capped like the narration: at most NARRATION[depth] sentences (3 at
        Discover, 6 at Study, 80 at Research). `shown` collects the claims the answers show."""
        prompts = step["prompts"]
        if ctx.depth == "discover":
            prompts = [p for p in prompts if p["d"] == "discover"][:1]
        cap = NARRATION[ctx.depth]
        items = []
        for p in prompts:
            question = self.s.th(p["t"], **{k: self.ref_data(ctx, v) for k, v in p["slots"].items()})
            ans = p["answer"]
            if ans.get("href"):
                name = esc(self.entity_rec(ctx, step["ref"])["name"])
                body = (f'<p><a href="{attr(ctx.base + ans["href"])}">'
                        f'{self.s.th("learn.next.page", name=name)}</a></p>')
            else:
                want = set(self.eligible(ctx, ans["claims"]) if ctx.depth == "discover" else ans["claims"])
                lis, cids_shown = [], []
                for item in step["narration"]:
                    if len(lis) == cap:
                        break
                    cids = [c for c in item["c"] if c in want]
                    if cids:
                        lis.append(self.sentence_li(ctx, item, cids, linkable))
                        cids_shown += cids
                if not lis:
                    continue
                if shown is not None:
                    shown.update(cids_shown)
                body = '<ul class="plain">' + "".join(lis) + "</ul>"
            items.append(f'<details class="prompt"><summary>{question}</summary>{body}</details>')
        if not items:
            return ""
        ctx.prompted = True
        return f'<div class="step-prompts">{"".join(items)}</div>'

    def next_html(self, ctx: Ctx, step: dict) -> str:
        """The next directions fixed by rule (design §7.5): at most 3 at Discover."""
        items = [x for x in step["next"] if x.get("only") in (None, ctx.depth)]
        if NEXT_CAP[ctx.depth]:
            items = items[:NEXT_CAP[ctx.depth]]
        lis = []
        for x in items:
            name = esc(self.entity_rec(ctx, x["ref"])["name"])
            if x.get("journey"):
                other = ctx.book.docs.get(x["journey"])
                title = self.t(other["title"]["key"]) if other else x["journey"]
                href = (x.get("urls") or {}).get(ctx.depth) or x.get("href")
                text = self.s.th(x["t"], name=name, journey=esc(title))
            else:
                href = x.get("href")
                text = self.s.th(x["t"], name=name)
            if href:
                lis.append(f'<li><a href="{attr(ctx.base + href)}">{text}</a></li>')
        return f'<ul class="plain step-next">{"".join(lis)}</ul>' if lis else ""

    # ------------------------------------------------------------------ Discover
    def head_x(self, ctx: Ctx, n: int, ref: str) -> str:
        e = self.entity_rec(ctx, ref)
        kind = self.t(f"type.{e.get('subtype') or e['kind']}")
        return (f'<h3 class="step-title" id="step-{n}-title"><span class="step-no">{self.s.th("learn.step_no", n=n)}</span> '
                f'{self.ref_link(ctx, ref)} <span class="kind">({html.escape(kind)})</span></h3>')

    def facts_x(self, ctx: Ctx, ref: str) -> str:
        """When and where as entity fields, Gregorian first (the export's date text)."""
        e = self.entity_rec(ctx, ref)
        when = next((d["text"]["en"] for d in e.get("dates") or [] if (d.get("text") or {}).get("en")), None)
        places = e.get("places") or []
        bits = []
        if e["kind"] == "event" or when:
            bits.append(self.s.th("learn.facts.when", value=self.data_span(when) if when else self.not_recorded()))
        if e["kind"] == "event" or places:
            where = ", ".join(self.ref_link(ctx, p) for p in places) if places else self.not_recorded()
            bits.append(self.s.th("learn.facts.where", value=where))
        if e["kind"] == "story" and e.get("number") is not None:
            bits.append(html.escape(self.t("fact.story_number", n=e["number"], total=ctx.book.doc["graph"]["stories"])))
        return f'<p class="step-facts">{SEP.join(bits)}</p>' if bits else ""

    def computed_reasons(self, ctx: Ctx, step: dict) -> str:
        """Discover's reasons: only those the rule computes (a matched word, or a story's part
        with the AI-document label), never one that rests on a claim."""
        lis = []
        for r in step["reasons"]:
            if r["kind"] == "named":
                lis.append(self.s.th("learn.why.named", word=html.escape(self.t("learn.quote", value=r["word"]), quote=False)))
            elif r["kind"] == "part":
                work = self.entity_rec(ctx, step["ref"]).get("work")
                work_html = self.data_span(work) if work else self.not_recorded()
                if r.get("ai_document"):
                    work_html = self.s.th("learn.source.ai_document", source=work_html)
                lis.append(self.s.th("learn.why.part", word=self.s.th("learn.quote", value=self.data_span(r.get("word") or "")),
                                     work=work_html))
        return ('<ul class="plain step-why">' + "".join(f"<li>{x}</li>" for x in lis) + "</ul>") if lis else ""

    def discover_lines(self, ctx: Ctx, key: str, step: dict, cap: int | None, also: frozenset = frozenset()) -> list[str]:
        """Narration sentences whose claims give a work and page, each with its short source
        line, then the absence line or the count of records left for Study: the records the
        step shows neither here nor in its prompt's answer (`also`). In a titled group the
        sentences of the step's side claims come first, so the record behind the group's
        heading is shown within the cap."""
        items = [i for i in step["narration"] if i["d"] == "discover"]
        if self.titled_group(ctx, step):
            side = {c for s in step["side"] for c in s["claims"]}
            items.sort(key=lambda i: not side & set(i["c"]))     # stable: otherwise the export's order
        if cap is not None:
            items = items[:cap]
        shown: set[str] = set(also)
        lis = []
        for item in items:
            cids = self.eligible(ctx, item["c"])
            shown.update(cids)
            lis.append(self.sentence_li(ctx, item, cids))
        out = [f'<ul class="plain narration">\n' + "\n".join(lis) + "\n</ul>"] if lis else []
        study = attr(ctx.base + ctx.book.stops[key]["urls"]["study"])
        records = step["counts"]["records"]
        if step["counts"]["discover"] == 0:
            out.append(f'<p class="no-work"><a href="{study}">{esc(self.s.tn("learn.discover.no_work", records))}</a></p>')
        elif records > len(shown):
            out.append(f'<p class="narr-more"><a href="{study}">{esc(self.s.tn("learn.narr.more", records - len(shown)))}</a></p>')
        return out

    def discover_step(self, ctx: Ctx, key: str) -> str:
        step = ctx.book.steps[key]
        n = step["n"]
        parts = [self.head_x(ctx, n, step["ref"]), self.facts_x(ctx, step["ref"]), self.computed_reasons(ctx, step)]
        answered: set[str] = set()
        prompt = self.prompts_html(ctx, step, shown=answered)
        parts += self.discover_lines(ctx, key, step, NARRATION["discover"], frozenset(answered))
        parts.append(prompt)
        parts.append(self.next_html(ctx, step))
        body = "\n".join(p for p in parts if p)
        return (f'<li class="step" id="step-{n}" data-step="{attr(key)}" aria-labelledby="step-{n}-title">\n'
                f'<span id="s-{attr(key)}"></span>\n{body}\n</li>')

    def apart_discover(self, ctx: Ctx, key: str) -> str:
        step = ctx.book.steps[key]
        lines = self.discover_lines(ctx, key, step, None)
        return (f'<li class="apart"><span id="s-{attr(key)}"></span><h3>{self.ref_link(ctx, step["ref"])}</h3>\n'
                + "\n".join(lines) + "</li>")

    def apart_head(self, ctx: Ctx) -> tuple[str, str]:
        lead = "learn.apart.lead_discover" if ctx.depth == "discover" else "learn.apart.lead"
        return (f'<section class="journey-apart" aria-labelledby="h-apart"><h2 id="h-apart">'
                f'{html.escape(self.t("learn.apart.heading"))}</h2><p>{html.escape(self.t(lead))}</p>'
                f'<ul class="plain apart-list">', "</ul></section>")

    # ------------------------------------------------------------------ Study and Research
    def source_x(self, ctx: Ctx, cid: str) -> str:
        """A claim's full source line (design §7.2), the citation linked to its story."""
        doc = ctx.book.doc
        rec = doc["claims"][cid]
        text = esc(X.source_line(rec, ctx.depth, doc["passages"], self.t))
        p = doc["passages"].get(rec.get("passage") or "") or {}
        label = html.escape(self.t("claim.source"))
        if p.get("cite"):
            if p.get("story"):
                text = f'<a href="{ctx.base}{p["story"]}/">{text}</a>'
            return f'<span class="source">{label} {text}</span>'
        if rec.get("basis"):
            return f'<span class="source">{label} {text}</span>'
        if rec.get("recorded_by"):
            return f'<span class="source">{text}</span>'
        return f'<span class="source not-recorded">{label} {text}</span>'

    def claim_id_html(self, ctx: Ctx, cid: str) -> str:
        anchor = claim_anchor(cid)
        if anchor in ctx.anchors:
            return f'<span class="claim-id">{esc(cid)}</span>'
        ctx.anchors.add(anchor)
        return f'<span class="claim-id" id="{attr(anchor)}">{esc(cid)}</span>'

    def claim_row(self, ctx: Ctx, cid: str, extra_class: str = "", show_source: bool = True) -> str:
        """A claim with its exact status and source (design §8 Study), its note, and at
        Research its ID, its AI gloss and who recorded it. Never its comment as a role."""
        c = self.ix.claim[cid]
        rec = ctx.book.doc["claims"][cid]
        base = ctx.base
        sentence = (f'{self.link(base, c.subject)} <span class="rel">{esc(self.predicate_text(c))}</span> '
                    f'{self.link(base, c.object)}')
        parts = [f'<p class="claim-text">{sentence}</p>']
        if c.kind == "participation" and c.role:
            parts.append(f'<p class="claim-role">{html.escape(self.t("claim.role", value=c.role.text))}</p>')
        note = rec.get("note")
        if note:
            key = "learn.note.ai_document" if note.get("ai_document") else "learn.note.text"
            parts.append(f'<p class="claim-note">{esc(self.t(key, note=display.honour(note["text"])))}</p>')
        gloss = ctx.book.doc["glosses"].get(cid) if ctx.depth == "research" else None
        if gloss:
            parts.append(f'<p class="claim-gloss"><span class="gloss-label">{html.escape(self.t("learn.gloss.label"))}</span> '
                         f'{esc(gloss)}</p>')
        if c.qualifiers:
            parts.append('<p class="claim-marker">' + esc(self.t("claim.marker", value="; ".join(c.qualifiers))) + "</p>")
        meta = [self.status_html(rec.get("status"))]
        if show_source:
            meta.append(self.source_x(ctx, cid))
        if ctx.depth == "research":
            meta.append(self.claim_id_html(ctx, cid))
        parts.append('<p class="claim-meta">' + SEP.join(meta) + "</p>")
        if ctx.depth == "research" and rec.get("recorded_by"):
            who = "; ".join(self.t("learn.research.software", name=a["label"]) if a["software"] else a["label"]
                            for a in rec["recorded_by"])
            parts.append(f'<p class="claim-agents">{esc(self.t("claim.recorded_by", value=who))}</p>')
        cls = f"claim {extra_class}".strip()
        return f'<li class="{cls}">' + "".join(parts) + "</li>"

    def row_plan(self, ctx: Ctx, key: str) -> tuple[dict[str, list[str]], int]:
        """The claim rows a step shows at this depth, by list, capped at the depth's
        claim_list (40 at Study, 80 at Research), and how many more its page holds."""
        step = ctx.book.steps[key]
        cap = CLAIM_LIST[ctx.depth]
        if "claims" in step:
            lists = {"claims": list(step["claims"]["ids"])}
            total = step["claims"]["total"]
        else:
            side = [c for s in step["side"] for c in s["claims"]]
            seen = set(step["records"]) | set(step["contrary"])
            lists = {"records": list(step["records"]), "contrary": list(step["contrary"]),
                     "side": [c for c in dict.fromkeys(side) if c not in seen]}
            total = step["counts"]["records"]
        out, left = {}, cap
        for name, ids in lists.items():
            out[name] = ids[:max(left, 0)]
            left -= len(out[name])
        shown = sum(len(v) for v in out.values())
        return out, max(total - shown, 0)

    def more_html(self, ctx: Ctx, key: str, more: int) -> str:
        if not more:
            return ""
        ref = ctx.book.steps[key]["ref"]
        return (f'<p class="claims-more"><a href="{ctx.base}{ref}/#evidence">'
                f'{esc(self.s.tn("learn.claims.more", more))}</a></p>')

    def narration_block(self, ctx: Ctx, step: dict, linkable: set) -> str:
        lis = [self.sentence_li(ctx, item, item["c"], linkable) for item in step["narration"][:NARRATION[ctx.depth]]]
        return ('<ul class="plain narration">\n' + "\n".join(lis) + "\n</ul>") if lis else ""

    def deep_step(self, ctx: Ctx, key: str) -> str:
        """A Study (without hold_study) or Research step: the v1 step with export-driven claim
        rows, plus narration, prompts and next directions."""
        book, base = ctx.book, ctx.base
        st, step = book.st[key], book.steps[key]
        e, n = st.entity, step["n"]
        t = book.doc["type"]
        positions = self.positions(ctx)
        rows, more = self.row_plan(ctx, key)
        linkable = set(ctx.anchors) | {claim_anchor(c) for ids in rows.values() for c in ids}
        source = lambda c: self.source_x(ctx, self.ix.id_of(c))   # noqa: E731
        parts = [self.step_head(base, n, e), self.facts_line(base, e), f'<p class="coverage">{self.coverage_html(e)}</p>',
                 self.narration_block(ctx, step, linkable)]
        if t == "events":
            if e.kind == "story":
                parts.append(f'<p class="banner" role="note">{html.escape(self.t("story.banner"))}</p>')
            why = "".join(self.reason_html(base, r, positions, source) for r in st.reasons)
            parts.append(f'<div class="step-why"><h4>{html.escape(self.t("learn.why.heading"))}</h4><ul class="plain">{why}</ul></div>')
            if st.links:
                links = "".join(self.reason_html(base, r, positions, source) for r in st.links)
                parts.append(f'<div class="step-why step-links"><h4>{html.escape(self.t("learn.links.heading"))}</h4>'
                             f'<ul class="plain">{links}</ul></div>')
            parts.append(self.order_html(st, positions))
            parts.append(self.claims_block_x(ctx, key, e, rows["claims"], more))
        elif t == "people":
            parts.append(f'<div class="step-records"><h4>{html.escape(self.s.tn("learn.records.heading", len(step["records"])))}</h4>'
                         f'<ul class="claim-list">\n' + "\n".join(self.claim_row(ctx, c) for c in rows["records"]) + "\n</ul></div>")
            if rows["contrary"]:
                parts.append(f'<div class="step-contrary"><h4>{html.escape(self.s.tn("learn.contrary.heading", len(step["contrary"])))}</h4>'
                             f'<ul class="claim-list">\n' + "\n".join(self.claim_row(ctx, c, "contrary") for c in rows["contrary"])
                             + "\n</ul></div>")
            if rows["side"]:
                parts.append(f'<div class="step-side"><h4>{html.escape(self.t("learn.side.heading"))}</h4>'
                             f'<ul class="claim-list">\n' + "\n".join(self.claim_row(ctx, c) for c in rows["side"]) + "\n</ul></div>")
            parts.append(self.more_html(ctx, key, more))
        else:
            parts.append(f'<p class="banner" role="note">{html.escape(self.t("story.banner"))}</p>')
            parts.append(f'<p class="read-story"><a href="{base}{e.kind}/{e.pid}/">{html.escape(self.t("learn.read_story"))}</a></p>')
            parts.append(self.named_block_x(ctx, key, st, rows["claims"], more))
        parts.append(self.prompts_html(ctx, step, linkable))
        parts.append(self.next_html(ctx, step))
        body = "\n".join(p for p in parts if p)
        return (f'<li class="step" id="step-{n}" data-step="{attr(key)}" aria-labelledby="step-{n}-title">\n'
                f'<span id="s-{attr(key)}"></span>\n{body}\n</li>')

    def claims_block_x(self, ctx: Ctx, key: str, e: Entity, rows: list[str], more: int) -> str:
        claims = self.site.claims.get(e.iri, [])
        if not claims:
            return f'<p class="claims-summary">{html.escape(self.t("learn.claims.none"))}</p>'
        summary, n_assert = self.status_counts(claims)
        n_links = sum(1 for c in claims if c.kind != "assertion")
        lines = []
        if n_assert:
            lines.append(self.s.tn("learn.claims.assertions", n_assert, statuses=summary))
        if n_links:
            lines.append(self.s.tn("learn.claims.links", n_links))
        lis = "\n".join(self.claim_row(ctx, c) for c in rows)
        return (f'<p class="claims-summary">{esc(" ".join(lines))}</p>'
                f'<details class="step-claims" open><summary>{html.escape(self.s.tn("learn.claims.show", len(claims)))}</summary>'
                f'<ul class="claim-list">\n{lis}\n</ul>{self.more_html(ctx, key, more)}</details>')

    def named_block_x(self, ctx: Ctx, key: str, st: Step, rows: list[str], more: int) -> str:
        if not st.records:
            return f'<p class="claims-summary">{html.escape(self.t("learn.named.none"))}</p>'
        summary, n_claims = self.status_counts(st.records)
        sources = []
        for cid in rows:
            s = self.source_x(ctx, cid)
            if s not in sources:
                sources.append(s)
        lis = "\n".join(self.claim_row(ctx, c, show_source=False) for c in rows)
        return (f'<p class="claims-summary">{esc(self.s.tn("learn.named.summary", n_claims, statuses=summary))}</p>'
                f'<details class="step-claims" open><summary>{html.escape(self.s.tn("learn.named.show", len(st.records)))}</summary>'
                f'<ul class="claim-list">\n{lis}\n</ul>' + "".join(f'<p class="claim-meta">{s}</p>' for s in sources)
                + f'{self.more_html(ctx, key, more)}</details>')

    def apart_deep(self, ctx: Ctx, key: str) -> str:
        st, step = ctx.book.st[key], ctx.book.steps[key]
        e = st.entity
        rows, more = self.row_plan(ctx, key)
        ids = rows["records"] + rows["contrary"] + rows["side"]
        linkable = set(ctx.anchors) | {claim_anchor(c) for c in ids}
        recs = "\n".join(self.claim_row(ctx, c) for c in ids)
        return (f'<li class="apart"><span id="s-{attr(key)}"></span><h3><a href="{ctx.base}{e.kind}/{e.pid}/">{esc(e.name)}</a></h3>'
                f'<p class="coverage">{self.coverage_html(e)}</p>{self.narration_block(ctx, step, linkable)}'
                f'<ul class="claim-list">\n{recs}\n</ul>{self.more_html(ctx, key, more)}</li>')

    # ------------------------------------------------------------------ the page around the steps
    def depth_nav(self, ctx: Ctx) -> str:
        """Links to the three depths, each to the page holding this page's first stop. From
        page 1 the link has no stop fragment: every depth's page 1 starts with the journey's
        first stop, so the reader lands at that page's header (its banners, rule and depth
        links). From a later page it ends in the stop's anchor."""
        first = ctx.keys[0]
        lis = []
        for d in DEPTHS:
            cur = ' aria-current="page"' if d == ctx.depth else ""
            url = ctx.book.stops[first]["urls"][d]
            href = attr(ctx.base + (url.split("#", 1)[0] if ctx.k == 1 else url))
            lis.append(f'<li><a href="{href}"{cur}>{html.escape(self.t(DEPTH_LABEL[d]))}</a></li>')
        return (f'<nav class="journey-depths" aria-label="{attr(self.t("learn.depths.label"))}"><ul>'
                + "".join(lis) + "</ul></nav>")

    def contents_html(self, ctx: Ctx) -> str:
        """Page 1 of a split depth: every stop, linked to the page that holds it. A stop on
        another page has its anchor here, so learn/{slug}/#s-{key} resolves without JavaScript."""
        lis = []
        for key in ctx.book.order:
            step = ctx.book.steps[key]
            name = esc(self.entity_rec(ctx, step["ref"])["name"])
            label = f'{self.s.th("learn.step_no", n=step["n"])} {name}' if step["n"] else name
            url = ctx.book.stops[key]["urls"][ctx.depth]
            page, frag = url.split("#", 1)
            if page == ctx.path:
                lis.append(f'<li><a href="#{attr(frag)}">{label}</a></li>')
            else:
                lis.append(f'<li id="{attr(frag)}"><a href="{attr(ctx.base + url)}">{label}</a></li>')
        return (f'<nav class="journey-contents" aria-labelledby="h-contents"><h2 id="h-contents">'
                f'{html.escape(self.t("learn.contents.heading"))}</h2>\n<ol class="plain">\n' + "\n".join(lis)
                + "\n</ol></nav>")

    def pager_html(self, ctx: Ctx) -> str:
        """The pages of a split depth under a visible label; learn.css marks the current
        page (aria-current) and gives every link a tap target of at least 2.75rem."""
        links = []
        for k in range(1, ctx.pages + 1):
            href = attr(ctx.base + X.page_url(ctx.book.doc["slug"], ctx.book.doc["door"], ctx.depth, k))
            cur = ' aria-current="page"' if k == ctx.k else ""
            links.append(f'<li><a href="{href}"{cur}>{k}</a></li>')
        return (f'<nav class="pager journey-pager" aria-labelledby="pager-label"><p class="pager-label" id="pager-label">'
                f'{html.escape(self.t("learn.pager.label"))}</p><ul>' + "".join(links) + "</ul></nav>")

    def rule_box(self, ctx: Ctx) -> str:
        """The rule in plain words, from the export alone: the rule as written (select), graph
        term labels from its terms in .term, recorded part titles in .data, then the order
        sentences of its rule_text that this depth shows."""
        doc, depth = ctx.book.doc, ctx.depth
        sel = doc["select"]

        def quote(h: str) -> str:
            return self.s.th("learn.quote", value=h)

        def word(w: str) -> str:
            return quote(html.escape(w, quote=False))

        def term_q(curie: str, qualifier: bool = False) -> str:
            label = doc["terms"][X.rule_term_ref(curie, qualifier)]["en"]
            return quote(f'<span class="term">{esc(label)}</span>')

        def words(named: dict, key: str = "words") -> str:
            ws = self.named_words(named) if key == "words" else named[key]
            return self.join_html([word(w) for w in ws], "or")

        def follow(rule: dict, key: str) -> str:
            links = self.join_html([html.escape(self.t(f"learn.follow.{f}")) for f in rule["follow"]], "and")
            return self.s.thn(key, rule["max_links"], links=links)

        paras = []
        if sel["type"] == "events":
            text = self.s.th("learn.rule.events", kinds=html.escape(self.kinds_text(sel["named"]["kinds"])),
                             words=words(sel["named"]))
            if sel["named"].get("not_words"):
                text += " " + self.s.th("learn.rule.not_words", words=words(sel["named"], "not_words"))
            if sel["max_links"]:
                text += " " + follow(sel, "learn.rule.events_follow")
            paras.append(text)
        elif sel["type"] == "people":
            ev = sel["events"]
            records = html.escape(self.t("learn.rule.people_records")) if sel["participation"]["records"] else ""
            paras.append(self.s.th("learn.rule.people", words=words(ev["named"]),
                                   kinds=html.escape(self.kinds_text(ev["named"]["kinds"])), records=records,
                                   claims=self.join_html([term_q(c) for c in sel["participation"]["claims"]], "or")))
            if ev["named"].get("not_words"):      # the events chosen by name, before the links add more
                paras.append(self.s.th("learn.rule.not_words", words=words(ev["named"], "not_words")))
            if ev["max_links"]:
                paras.append(follow(ev, "learn.rule.people_follow"))
            if sel["also_show"]:
                paras.append(self.s.th("learn.rule.also_show", kinds=self.join_html([term_q(c) for c in sel["also_show"]], "or")))
            if sel["set_apart"]:
                paras.append(self.s.th("learn.rule.set_apart", markers=self.join_html([term_q(q, True) for q in sel["set_apart"]], "or")))
        else:
            parts = self.join_html([quote(self.data_span(display.name_display(p))) for p in doc["part_labels"]], "or")
            paras.append(self.s.th("learn.rule.stories", words=self.join_html([word(w) for w in sel["part"]["words"]], "or"),
                                   parts=parts))
        for item in doc["rule_text"]:
            if DEPTH_RANK[item["d"]] <= DEPTH_RANK[depth] and item.get("only") in (None, depth):
                paras.append(self.rule_item(item))
        if depth != "discover" and doc["mixes_stories_and_events"]:
            paras.append(esc(self.t("learn.rule.separate_records")))
        if doc["order_conflict"]:
            paras.append(esc(self.t("learn.rule.order_conflict")))
        return "".join(f"<p>{p}</p>" for p in paras)

    def rule_item(self, item: dict) -> str:
        kw = {}
        for k, v in (item.get("slots") or {}).items():
            if isinstance(v, list):
                kw[k] = self.join_html([f'<span class="source">{esc(x)}</span>' for x in v if x], "and")
            else:
                kw[k] = self.data_span(str(v))
        return self.s.th(item["t"], **kw)

    def research_html(self, ctx: Ctx) -> str:
        """Research: the rule's hash, the content digest, the graph, the data files and what
        the rule left out as background."""
        if ctx.depth != "research":
            return ""
        doc, slug = ctx.book.doc, ctx.book.doc["slug"]
        g = doc["graph"]
        facts = [self.t("learn.research.rule_sha", sha=doc["rule_sha"]),
                 self.t("learn.research.content_sha", sha=doc["content_sha"]),
                 self.t("learn.research.graph", file=g.get("file") or "", fingerprint=g["fingerprint"], triples=g["triples"])]
        parts = (ctx.book.entry or {}).get("parts") or 0
        files = [f"journeys/{slug}/journey.json"] + [f"journeys/{slug}/part-{k}.json" for k in range(1, parts + 1)] \
            + [f"journeys/{slug}/research-{k}.json" for k in range(1, parts + 1)] + ["index.json", "strings.json", "pages.json"]
        data = SEP.join(f'<a href="{attr(ctx.base)}learn/data/{attr(f)}">{esc(f)}</a>' for f in files)
        if doc["excluded"]:
            lis = "".join(f'<li>{self.ref_link(ctx, x["ref"])}: {html.escape(self.t(EXCLUDED[x["reason"]]))}</li>'
                          for x in doc["excluded"])
            excluded = (f'<h3>{html.escape(self.t("learn.research.excluded_heading"))}</h3>'
                        f'<ul class="plain research-excluded">{lis}</ul>')
        else:
            excluded = f'<p>{html.escape(self.t("learn.research.excluded_none"))}</p>'
        return (f'<section class="journey-research" aria-labelledby="h-research"><h2 id="h-research">'
                f'{html.escape(self.t("learn.research.heading"))}</h2>'
                f'<ul class="plain research-facts">{"".join(f"<li>{esc(x)}</li>" for x in facts)}</ul>'
                f'<p class="research-data">{html.escape(self.t("learn.research.data"))} {data}</p>{excluded}</section>')

    def scale_x(self, doc: dict) -> str:
        t, n, apart = doc["type"], len(doc["stops"]), len(doc["set_apart"])
        if t == "people":
            text = self.s.tn("learn.scale.people", n, apart=apart, universe=doc["universe"])
            if apart:
                text += " " + self.s.tn("learn.scale.apart", apart)
        else:
            text = self.s.tn(f"learn.scale.{t}", n, universe=doc["universe"])
        return f'<p class="scale">{html.escape(text)}</p>'

    def page_title(self, ctx: Ctx, title: str) -> str:
        door = ctx.book.doc["door"]
        if ctx.depth == door and ctx.k == 1:
            return title
        depth = self.t(DEPTH_LABEL[ctx.depth])
        if ctx.k == 1:
            return self.t("learn.title.depth", title=title, depth=depth)
        return self.t("learn.title.page", title=title, depth=depth, n=ctx.k)

    def crumbs(self, ctx: Ctx, title: str) -> list:
        door = ctx.book.doc["door"]
        if ctx.depth == door and ctx.k == 1:
            return [(self.t("learn.nav"), "learn/"), (title, None)]
        depth = self.t(DEPTH_LABEL[ctx.depth])
        last = depth if ctx.k == 1 else self.t("learn.crumb.page", depth=depth, n=ctx.k)
        return [(self.t("learn.nav"), "learn/"), (title, f"learn/{ctx.book.doc['slug']}/"), (last, None)]

    def journey_tpl(self, ctx: Ctx, **parts) -> str:
        book = ctx.book
        keys = " ".join(s["key"] for s in book.doc["stops"])
        data = f' data-depth="{ctx.depth}" data-total="{len(book.doc["stops"])}" data-steps="{attr(keys)}"'
        numbers = [book.steps[k]["n"] for k in ctx.keys if book.steps[k]["n"]]
        start = f' start="{numbers[0]}"' if numbers and numbers[0] != 1 else ""
        split = ctx.pages > 1
        return self.tpl("journey", slug=attr(book.doc["slug"]), door=attr(book.doc["door"]), data=data, base=ctx.base,
                        depthnav=self.depth_nav(ctx), contents=self.contents_html(ctx) if split and ctx.k == 1 else "",
                        pager=self.pager_html(ctx) if split else "", start=start, research=self.research_html(ctx),
                        **parts)

    def page_body(self, ctx: Ctx) -> tuple[str, str]:
        """The page's step items and its set-apart section."""
        steps = "\n".join(self.item(ctx, k) for k in ctx.keys if k not in ctx.book.apart)
        apart_keys = [k for k in ctx.keys if k in ctx.book.apart]
        apart = ""
        if apart_keys:
            head, tail = self.apart_head(ctx)
            apart = head + "".join(self.item(ctx, k) for k in apart_keys) + tail
        return steps, apart

    def held_page(self, ctx: Ctx) -> str:
        """The v1 Study page of a journey with hold_study (design §3.7), with only the
        depth links, the s-{key} anchor spans, base-relative links and the article's
        data-depth, data-total and data-steps added."""
        j = ctx.book.j
        steps, apart = self.page_body(ctx)
        title = self.t(j.spec["title"])
        lead = self.t(j.spec.get("lead_study") or j.spec["lead"])   # this page shows the claims and their status
        banner = self.banner(j)
        if self.ai_involved(j):
            banner += f'<p class="banner" role="note">{html.escape(self.t("learn.ai_note"))}</p>'
        legend = f'<p class="legend">{html.escape(self.t("learn.legend." + j.spec["select"]["type"]))}</p>'
        content = self.journey_tpl(ctx, kicker=html.escape(self.t(f"learn.door.{j.spec['door']}")), h1=esc(title),
                                   banner=banner, lead=esc(lead), scale=self.scale(j), progress=self.progress_ui(len(j.steps)),
                                   rule=self.rule_html(j), legend=legend, steps=steps, apart=apart)
        page = self.shell(ctx.base, self.page_title(ctx, title), content,
                          body_class=f"page-learn page-journey door-{j.spec['door']}",
                          crumbs=self.crumbs(ctx, title), description=lead, script=True)
        return _EMPTY_OL.sub("", page)

    def page(self, ctx: Ctx) -> str:
        """A Discover, Study or Research page, rendered from the export."""
        doc, depth = ctx.book.doc, ctx.depth
        steps, apart = self.page_body(ctx)
        title = self.t(doc["title"]["key"])
        lead = self.t(doc["lead"]["key"] if depth == "discover" else (doc["lead_study"] or doc["lead"])["key"])
        scale = self.scale_x(doc)
        if depth == "discover":
            banner = ""
            if doc.get("ai_note"):
                works = self.join_html([self.data_span(w) for w in doc["ai_documents"]], "and")
                banner = f'<p class="note ai-source">{self.s.th(doc["ai_note"]["discover"], work=works)}</p>'
            legend = ""
        else:
            if doc["state"] == "approved":
                dates = {a["who"]: a["date"] for a in doc["approved_by"]}
                banner = (f'<p class="banner" role="note">{html.escape(self.t("learn.approved_banner", maintainer=dates.get("maintainer", ""), board=dates.get("review_board", "")))}</p>')
            else:
                banner = f'<p class="banner" role="note"><strong>{html.escape(self.t("learn.draft_banner"))}</strong></p>'
            if doc.get("ai_note"):
                banner += f'<p class="banner" role="note">{html.escape(self.t(doc["ai_note"]["study"]))}</p>'
            share = doc["accepted_share"]
            scale += (f'<p class="accepted-share">{html.escape(self.t("learn.accepted_share.line", accepted=share["accepted"], of=share["of"], no_status=share["no_status"]))}</p>')
            legend = f'<p class="legend">{html.escape(self.t("learn.legend." + doc["type"]))}</p>'
        if ctx.prompted:
            legend += f'<p class="note prompt-note">{html.escape(self.t("learn.prompt.note"))}</p>'
        content = self.journey_tpl(ctx, kicker=html.escape(self.t(KICKER[depth])), h1=esc(title), banner=banner,
                                   lead=esc(lead), scale=scale, progress=self.progress_ui(len(doc["stops"])),
                                   rule=self.rule_box(ctx), legend=legend, steps=steps, apart=apart)
        page = self.shell(ctx.base, self.page_title(ctx, title), content,
                          body_class=f"page-learn page-journey door-{doc['door']}",
                          crumbs=self.crumbs(ctx, title), description=lead, script=True)
        return _EMPTY_OL.sub("", page)

    # ------------------------------------------------------------------ index
    def index_page(self, journeys: list[Journey], n_questions: int, entries: list[dict] | None = None) -> str:
        """The learn index, depth-neutral (rendered at Discover): each journey's title, lead,
        step count and links to its three depths."""
        base = "../"
        urls = {e["slug"]: e["urls"] for e in entries or []}
        cards = []
        for j in journeys:
            title = self.t(j.spec["title"])
            keys = " ".join(st.entity.pid for st in j.steps)
            depths = []
            for d in DEPTHS:
                url = (urls.get(j.slug) or {}).get(d, [X.page_url(j.slug, j.spec["door"], d, 1)])[0]
                depths.append(f'<a href="{attr(url[len("learn/"):])}">{html.escape(self.t(DEPTH_LABEL[d]))}</a>')
            cards.append(
                f'<li class="journey-card" data-journey-card="{attr(j.slug)}" data-steps="{attr(keys)}">'
                f'<h3><a href="{j.slug}/">{esc(title)}</a></h3>'
                f'<p>{esc(self.t(j.spec["lead"]))}</p>'
                f'<p class="meta">{html.escape(self.s.tn("learn.index.steps", len(j.steps)))}{SEP}'
                f'<span class="depth-links">{html.escape(self.t("learn.index.depths"))} {SEP.join(depths)}</span></p>'
                f'<p class="card-progress" data-card-progress hidden></p></li>')
        practice = self.s.tn("learn.index.practice_count", n_questions)
        content = self.tpl("index", cards="\n".join(cards), practice_count=html.escape(practice))
        title = self.t("learn.nav")
        return self.shell(base, title, content, body_class="page-learn page-learn-index",
                          crumbs=[(title, None)], description=self.t("learn.index.lead"), script=True)

    # ------------------------------------------------------------------ practice
    def question_text(self, base: str, q: dict) -> str:
        a, b = (self.link(base, x) for x in q["about"])
        return self.s.th(f"learn.q.{q['type']}.{q['predicate']}", a=a, b=b)

    def answer_claim(self, base: str, c: dict) -> str:
        """One accepted claim behind an answer: the sentence, its status and its source."""
        claim = None
        for cl in self.site.claims.get(c["subject"], []):
            if cl.node == c["claim"]:
                claim = cl
        if claim is None:  # not in the site model: fall back to the bank's own fields
            src = c.get("citation") or c.get("basis")
            source = (f'<span class="source">{html.escape(self.t("claim.source"))} {esc(src)}</span>' if src
                      else f'<span class="source not-recorded">{html.escape(self.t("claim.source"))} {html.escape(self.t("common.not_recorded"))}</span>')
            pred = self.site.vocab(URIRef(str(MRS) + c["predicate"])) or c["predicate"]
            return (f'<li class="claim"><p class="claim-text">{self.link(base, c["subject"])} '
                    f'<span class="rel">{esc(pred)}</span> {self.link(base, c["object"])}</p>'
                    f'<p class="claim-meta">{self.status_html(c["status"])} {source}</p></li>')
        return self.claim_li(base, claim)

    def practice_pages(self, questions: list[dict], counts: dict[str, int]) -> dict[str, str]:
        """{relative path: html}. One page when the bank is empty; more when it is long."""
        def sort_key(q):
            names = [display.sort_key(self.site.label_of(x)) for x in q["about"]]
            return (q["type"], q["predicate"], names, q["id"])
        questions = sorted(questions, key=sort_key)
        chunks = [questions[i:i + QUESTIONS_PER_PAGE] for i in range(0, len(questions), QUESTIONS_PER_PAGE)] or [[]]
        pages = {}
        for n, chunk in enumerate(chunks, 1):
            path = practice_path(n).removeprefix("learn/") + "index.html"
            base = "../../" if n == 1 else "../../../"
            pages[path] = self.practice_page(base, chunk, n, len(chunks), len(questions), counts)
        return pages

    def practice_page(self, base: str, chunk: list[dict], page: int, pages: int, total: int, counts: dict) -> str:
        status = self.t("learn.practice.counts", total=sum(counts.values()), accepted=counts.get("accepted", 0),
                        proposed=counts.get("proposed", 0), under_review=counts.get("under_review", 0),
                        rejected=counts.get("rejected", 0))
        if total == 0:
            body = (f'<p class="banner" role="note"><strong>{html.escape(self.t("learn.practice.empty"))}</strong></p>'
                    f'<p>{html.escape(self.t("learn.practice.empty_why"))}</p><p>{html.escape(status)}</p>')
        else:
            items = []
            for q in chunk:
                answers = []
                for a in q["answers"]:
                    claims = "\n".join(self.answer_claim(base, c) for c in a["claims"])
                    answers.append(f'<li><p class="answer">{self.link(base, a["entity"])}</p>'
                                   f'<ul class="claim-list">\n{claims}\n</ul></li>')
                items.append(f'<li class="question" id="q-{attr(q["id"])}"><p class="q-text">{self.question_text(base, q)}</p>'
                             f'<details class="answer-box"><summary>{html.escape(self.t("learn.practice.show_answer"))}</summary>'
                             f'<p class="note">{html.escape(self.t("learn.practice.answer_note"))}</p>'
                             f'<ul class="plain answers">{"".join(answers)}</ul></details></li>')
            body = f'<p>{html.escape(status)}</p><ol class="questions" start="{(page - 1) * QUESTIONS_PER_PAGE + 1}">' + "".join(items) + "</ol>"
            if pages > 1:
                links = []
                for n in range(1, pages + 1):
                    href = f"{base}{practice_path(n)}"
                    cur = ' aria-current="page"' if n == page else ""
                    links.append(f'<li><a href="{href}"{cur}>{n}</a></li>')
                body += (f'<nav class="pager" aria-label="{attr(self.t("learn.practice.pages"))}"><ul>'
                         + "".join(links) + "</ul></nav>")
        content = self.tpl("practice", body=body, bank=f"{base}learn/practice/bank.json")
        title = self.t("learn.practice.title")
        return self.shell(base, title, content, body_class="page-learn page-practice",
                          crumbs=[(self.t("learn.nav"), "learn/"), (title, None)],
                          description=self.t("learn.practice.lead"), script=False)
