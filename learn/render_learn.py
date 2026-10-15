"""Turns journeys and the practice bank into HTML. No file is read here except the
templates, and no UI string is written here: every visible string is a key in
learn/i18n/en.json (or, for the shared page frame, dates and status words,
site/i18n/en.json), or comes from the graph through site/model.py. The markup reuses
the site's CSS classes, so site.css styles most of it; learn.css adds the rest."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from string import Template

from rdflib import URIRef
from rdflib.namespace import RDFS, SKOS

import display
from model import MRS, Claim, Entity, Site
from render import URL_AGPL, URL_CC_BY_SA, URL_LICENSING

from journeys import Journey, Reason, Step, term

NAV = (("people", "person"), ("events", "event"), ("places", "place"), ("groups", "group"),
       ("stories", "story"), ("glossary", "glossary"))
QUESTIONS_PER_PAGE = 40


class Strings:
    """Learn keys first, then the site's keys for the shared frame, dates and statuses."""

    def __init__(self, learn: Path, site: Path):
        self.learn: dict[str, str] = json.loads(Path(learn).read_text(encoding="utf-8"))
        self.site: dict[str, str] = json.loads(Path(site).read_text(encoding="utf-8"))
        self.used: set[str] = set()

    def raw(self, key: str) -> str:
        self.used.add(key)
        if key in self.learn:
            return self.learn[key]
        return self.site[key]  # a missing key is a build error on purpose

    def t(self, key: str, **kw) -> str:
        s = self.raw(key)
        return s.format(**kw) if kw else s

    def th(self, key: str, **kw) -> str:
        """Escaped template; keyword values must already be HTML."""
        s = html.escape(self.raw(key), quote=False)
        return s.format(**kw) if kw else s

    def tn(self, key: str, n: int, **kw) -> str:
        return self.t(f"{key}.{'one' if n == 1 else 'other'}", n=n, **kw)


def esc(s: str) -> str:
    return display.mark_arabic(html.escape(s, quote=False))


def attr(s: str) -> str:
    return html.escape(s, quote=True)


class LearnRenderer:
    def __init__(self, site: Site, strings: Strings, templates: Path):
        self.site, self.s = site, strings
        self.t = strings.t
        self.tpl_dir = Path(templates)
        self._tpl: dict[str, str] = {}

    # ------------------------------------------------------------------ templates and frame
    def tpl(self, name: str, **vars) -> str:
        if name not in self._tpl:
            src = (self.tpl_dir / f"{name}.html").read_text(encoding="utf-8")
            src = re.sub(r"\[\[([a-z0-9_.]+)\]\]", lambda m: html.escape(self.s.t(m.group(1)), quote=False), src)
            self._tpl[name] = src
        return Template(self._tpl[name]).substitute(vars)

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

    # ------------------------------------------------------------------ small pieces
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
        parts.append('<p class="claim-meta">' + ' <span class="sep" aria-hidden="true">&middot;</span> '.join(meta) + "</p>")
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

    # ------------------------------------------------------------------ rule in plain words
    def rule_html(self, j: Journey) -> str:
        spec, sel = j.spec, j.spec["select"]
        paras = []
        if sel["type"] == "events":
            paras.append(self.rule_events(sel))
        elif sel["type"] == "people":
            ev = sel["events"]
            paras.append(self.t("learn.rule.people", words=self.words_list(ev["named"]["words"]),
                                kinds=self.kinds_text(ev["named"]["kinds"]),
                                records=self.t("learn.rule.people_records") if sel["participation"]["records"] else "",
                                claims=self.join_or([self.t("learn.quote", value=self.term_label(c))
                                                     for c in sel["participation"]["claims"]])))
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
        paras.append(self.t(f"learn.order.{spec['order']}"))
        if j.mixes_stories_and_events:
            paras.append(self.t("learn.rule.separate_records"))
        if j.order_conflict:
            paras.append(self.t("learn.rule.order_conflict"))
        return "".join(f"<p>{esc(p)}</p>" for p in paras)

    def kinds_text(self, kinds: list[str]) -> str:
        return self.t("learn.kinds." + "_".join(sorted(kinds)))

    def rule_events(self, sel: dict) -> str:
        text = self.t("learn.rule.events", kinds=self.kinds_text(sel["named"]["kinds"]),
                      words=self.words_list(sel["named"]["words"]))
        if sel["max_links"]:
            text += " " + self.rule_follow(sel, "learn.rule.events_follow")
        return text

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

    # ------------------------------------------------------------------ steps
    def reason_html(self, base: str, r: Reason, positions: dict[str, int]) -> str:
        other = ""
        if r.other:
            other = self.link(base, r.other)
            if r.other in positions:
                other += " " + self.s.th("learn.step_ref", n=f'<a href="#step-{positions[r.other]}">{positions[r.other]}</a>')
        if r.kind == "named":
            text = self.s.th("learn.why.named", word=html.escape(self.t("learn.quote", value=r.word), quote=False))
        elif r.kind == "event_claim":
            text = self.s.th("learn.why.event_claim", other=other,
                             label=esc(self.t("learn.quote", value=r.label or "")))
        else:
            text = self.s.th(f"learn.why.{r.kind}", other=other)
        meta = []
        sep = ' <span class="sep" aria-hidden="true">&middot;</span> '
        if r.kind != "named":
            if r.claims:
                for c in r.claims:
                    meta.append(self.status_html(c.status) + sep + self.source_html(base, c))
            else:
                meta.append(self.status_html(None) + sep + f'<span class="note">{html.escape(self.t("learn.why.plain_link"))}</span>')
        out = f'<li><p>{text}</p>'
        if meta:
            out += "".join(f'<p class="claim-meta">{m}</p>' for m in meta)
        return out + "</li>"

    def order_html(self, st: Step, positions: dict[str, int]) -> str:
        if not st.order_note:
            return ""
        n = positions.get(st.order_ref)
        ref = f'<a href="#step-{n}">{n}</a>' if n else ""
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
        sep = ' <span class="sep" aria-hidden="true">&middot;</span> '
        return f'<p class="step-facts">{sep.join(bits)}</p>' if bits else ""

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

    def step_li(self, base: str, j: Journey, n: int, st: Step, positions: dict[str, int]) -> str:
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
        return (f'<li class="step" id="step-{n}" data-step="{attr(e.pid)}" aria-labelledby="step-{n}-title">\n'
                f'{body}\n</li>')

    def apart_html(self, base: str, j: Journey) -> str:
        if not j.set_apart:
            return ""
        lis = []
        for st in j.set_apart:
            e = st.entity
            recs = "\n".join(self.claim_li(base, c) for c in st.records + st.contrary)
            lis.append(f'<li class="apart"><h3><a href="{base}{e.kind}/{e.pid}/">{esc(e.name)}</a></h3>'
                       f'<p class="coverage">{self.coverage_html(e)}</p><ul class="claim-list">\n{recs}\n</ul></li>')
        return (f'<section class="journey-apart" aria-labelledby="h-apart"><h2 id="h-apart">'
                f'{html.escape(self.t("learn.apart.heading"))}</h2><p>{html.escape(self.t("learn.apart.lead"))}</p>'
                f'<ul class="plain apart-list">{"".join(lis)}</ul></section>')

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

    def journey_page(self, j: Journey) -> str:
        base = "../../"
        positions = {st.iri: n for n, st in enumerate(j.steps, 1)}
        steps = "\n".join(self.step_li(base, j, n, st, positions) for n, st in enumerate(j.steps, 1))
        title = self.t(j.spec["title"])
        banner = self.banner(j)
        if self.ai_involved(j):
            banner += f'<p class="banner" role="note">{html.escape(self.t("learn.ai_note"))}</p>'
        content = self.tpl("journey", slug=attr(j.slug), door=attr(j.spec["door"]),
                           kicker=html.escape(self.t(f"learn.door.{j.spec['door']}")),
                           h1=esc(title), banner=banner, lead=esc(self.t(j.spec["lead"])),
                           scale=self.scale(j), progress=self.progress_ui(len(j.steps)), rule=self.rule_html(j),
                           legend=html.escape(self.t(f"learn.legend.{j.spec['select']['type']}")),
                           steps=steps, apart=self.apart_html(base, j))
        return self.shell(base, title, content, body_class=f"page-learn page-journey door-{j.spec['door']}",
                          crumbs=[(self.t("learn.nav"), "learn/"), (title, None)],
                          description=self.t(j.spec["lead"]), script=True)

    # ------------------------------------------------------------------ index
    def index_page(self, journeys: list[Journey], n_questions: int) -> str:
        base = "../"
        cards = []
        for j in journeys:
            title = self.t(j.spec["title"])
            state = self.t("learn.state.draft") if j.is_draft else self.t("learn.state.approved")
            keys = " ".join(st.entity.pid for st in j.steps)
            cards.append(
                f'<li class="journey-card" data-journey-card="{attr(j.slug)}" data-steps="{attr(keys)}">'
                f'<h3><a href="{j.slug}/">{esc(title)}</a></h3>'
                f'<p>{esc(self.t(j.spec["lead"]))}</p>'
                f'<p class="meta"><span class="status status-draft">{html.escape(state)}</span> '
                f'<span class="sep" aria-hidden="true">&middot;</span> {html.escape(self.s.tn("learn.index.steps", len(j.steps)))} '
                f'<span class="sep" aria-hidden="true">&middot;</span> {html.escape(self.t("learn.door." + j.spec["door"]))}</p>'
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
            path = "practice/index.html" if n == 1 else f"practice/{n}/index.html"
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
                    href = f"{base}learn/practice/" if n == 1 else f"{base}learn/practice/{n}/"
                    cur = ' aria-current="page"' if n == page else ""
                    links.append(f'<li><a href="{href}"{cur}>{n}</a></li>')
                body += (f'<nav class="pager" aria-label="{attr(self.t("learn.practice.pages"))}"><ul>'
                         + "".join(links) + "</ul></nav>")
        content = self.tpl("practice", body=body, bank=f"{base}learn/practice/bank.json")
        title = self.t("learn.practice.title")
        return self.shell(base, title, content, body_class="page-learn page-practice",
                          crumbs=[(self.t("learn.nav"), "learn/"), (title, None)],
                          description=self.t("learn.practice.lead"), script=False)
