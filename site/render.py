"""Turns the model into HTML pages. No data is read here and no UI string is written
here: every visible string is an i18n key (site/i18n/en.json) or comes from the graph."""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from string import Template

import display
import experiments
import hub
from glossary import Glossary
from model import KINDS, Claim, Entity, Lit, Site
from thread import FOCUS_KINDS

NAV = (("people", "person"), ("events", "event"), ("places", "place"),
       ("groups", "group"), ("stories", "story"))
KIND_NAV = {"person": "people", "event": "events", "place": "places", "group": "groups", "story": "stories"}

URL_LICENSING = "https://github.com/thajudeenUrbane/al-marsad/blob/main/LICENSING.md"
URL_CC_BY_SA = "https://creativecommons.org/licenses/by-sa/4.0/"
URL_AGPL = "https://www.gnu.org/licenses/agpl-3.0.html"

SECTION_ORDER = {
    "person": ["stories", "events", "kinship", "people", "places", "groups", "other"],
    "group": ["stories", "events", "people", "groups", "places", "other"],
    "event": ["people_groups", "events", "places", "stories", "other"],
    "story": ["people_groups", "events", "places", "other"],
    "place": ["events", "people_groups", "stories", "other"],
}


class I18n:
    def __init__(self, path: str | Path):
        self.d: dict[str, str] = json.loads(Path(path).read_text(encoding="utf-8"))
        self.used: set[str] = set()

    def t(self, key: str, **kw) -> str:
        s = self.d[key]  # a missing key is a build error on purpose
        self.used.add(key)
        return s.format(**kw) if kw else s

    def th(self, key: str, **kw) -> str:
        """Escaped string; keyword values must already be HTML."""
        s = html.escape(self.d[key], quote=False)
        self.used.add(key)
        return s.format(**kw) if kw else s

    def tn(self, key: str, n: int, **kw) -> str:
        return self.t(f"{key}.{'one' if n == 1 else 'other'}", n=n, **kw)

    def has(self, key: str) -> bool:
        return key in self.d


@dataclass
class Ctx:
    path: str                      # directory of the page: '', 'person/', 'person/ID/'
    seen: set = field(default_factory=set)   # glossary terms already linked on this page

    @property
    def base(self) -> str:
        return "../" * self.path.count("/")


class Renderer:
    def __init__(self, site: Site, glossary: Glossary, i18n: I18n, templates: str | Path,
                 external: dict[str, list[dict]] | None = None):
        self.site, self.glossary, self.i = site, glossary, i18n
        self.tpl_dir = Path(templates)
        self._tpl: dict[str, str] = {}
        self.t = i18n.t
        self.external = external or {}   # possible matches elsewhere (site/external.py), by IRI

    # ------------------------------------------------------------------ templates
    def tpl(self, name: str, **vars) -> str:
        if name not in self._tpl:
            src = (self.tpl_dir / f"{name}.html").read_text(encoding="utf-8")
            src = re.sub(r"\[\[([a-z0-9_.]+)\]\]", lambda m: html.escape(self.i.t(m.group(1)), quote=False), src)
            self._tpl[name] = src
        return Template(self._tpl[name]).substitute(vars)

    # ------------------------------------------------------------------ text helpers
    @staticmethod
    def esc(s: str) -> str:
        return display.mark_arabic(html.escape(s, quote=False))

    @staticmethod
    def attr(s: str) -> str:
        return html.escape(s, quote=True)

    def text(self, ctx: Ctx, s: str, verbatim: bool = False, once: bool = False) -> str:
        if not verbatim:
            s = display.honour(s)
        out, keys = display.link_terms(s, self.glossary.matchers,
                                       lambda k: f"{ctx.base}glossary/#term-{k}", ctx.seen, once,
                                       plain_for=self.glossary.plain_for)
        self.glossary.used |= keys
        return out

    def label(self, ctx: Ctx, key: str, **kw) -> str:
        """A UI string that may contain glossary terms."""
        return self.text(ctx, self.t(key, **kw), verbatim=True)

    def ent_link(self, ctx: Ctx, iri: str, cur: str | None = None) -> str:
        e = self.site.entity(iri)
        if e is None:
            return self.esc(self.site.label_of(iri))
        if iri == cur:
            return f'<strong class="self">{self.esc(e.name)}</strong>'
        return f'<a href="{ctx.base}{e.kind}/{e.pid}/">{self.esc(e.name)}</a>'

    @staticmethod
    def arabic_names(names: list[str]) -> str:
        """Arabic names beside the English one; several are told apart by a slash."""
        spans = [f'<span class="name-ar" lang="ar" dir="rtl">{html.escape(n, quote=False)}</span>' for n in names]
        return " " + ' <span class="sep" aria-hidden="true">/</span> '.join(spans) if spans else ""

    def name_h1(self, e: Entity) -> str:
        return self.esc(e.name) + self.arabic_names(e.arabic)

    def honorific_html(self, e: Entity) -> str:
        key = display.companion_honorific_key(e.data.get("companion_status"), e.data.get("gender")) \
            if e.kind == "person" else None
        if not key:
            return ""
        return f' <span class="honorific" lang="ar" dir="rtl">{html.escape(self.t(key), quote=False)}</span>'

    def date_html(self, ext: dict) -> str:
        v = display.format_extent(ext, self.t)
        if not v["text"]:
            return f'<span class="not-recorded">{html.escape(self.t("common.not_recorded"))}</span>'
        out = f'<span class="date">{self.esc(v["text"])}</span>'
        if v["notes"]:
            out += f'<br><span class="note">{self.esc(" · ".join(v["notes"]))}</span>'
        return out

    def dates_html(self, exts: list[dict]) -> str:
        if not exts:
            return f'<span class="not-recorded">{html.escape(self.t("common.not_recorded"))}</span>'
        return "<br>".join(self.date_html(x) for x in exts)

    def short_date(self, exts: list[dict]) -> str | None:
        for x in exts:
            v = display.format_extent(x, self.t)
            if v["text"]:
                return v["text"]
        return None

    # ------------------------------------------------------------------ page shell
    def shell(self, ctx: Ctx, title: str, body: str, *, body_class: str, current: str | None,
              crumbs: list[tuple[str, str | None]], description: str, search_box: bool = True,
              scripts: str = "") -> str:
        nav = [f'<li><a href="{ctx.base}"{" aria-current=" + chr(34) + "page" + chr(34) if current == "home" else ""}>'
               f'{html.escape(self.t("nav.home"))}</a></li>']
        for key, kind in NAV + (("glossary", "glossary"),):
            cur = ' aria-current="page"' if current == key else ""
            nav.append(f'<li><a href="{ctx.base}{kind}/"{cur}>{html.escape(self.t("nav." + key))}</a></li>')
        crumb_items = [f'<li><a href="{ctx.base}">{html.escape(self.t("nav.home"))}</a></li>']
        for text, href in crumbs:
            if href is None:
                crumb_items.append(f'<li aria-current="page">{self.esc(text)}</li>')
            else:
                crumb_items.append(f'<li><a href="{ctx.base}{href}">{self.esc(text)}</a></li>')
        breadcrumb = (f'<nav class="breadcrumb" aria-label="{self.attr(self.t("nav.breadcrumb"))}"><ol>'
                      + "".join(crumb_items) + "</ol></nav>") if crumbs else ""
        return self.tpl("base", lang="en", dir="ltr", title=html.escape(title, quote=False),
                        description=self.attr(description), base=ctx.base, body_class=body_class,
                        nav="\n".join(nav), breadcrumb=breadcrumb, body=body,
                        search_box=self.tpl("search_box", base=ctx.base) if search_box else "",
                        scripts=scripts, footer=self.footer_html())

    def footer_html(self, footer_class: str = "site-footer") -> str:
        """The licence footer: every page ends with it, the prototype copies too."""
        return self.tpl("footer", footer_class=footer_class, url_licensing=URL_LICENSING,
                        url_cc_by_sa=URL_CC_BY_SA, url_agpl=URL_AGPL)

    def page_title(self, name: str) -> str:
        return f'{name} {self.t("title.sep")} {self.t("site.name")}'

    # ------------------------------------------------------------------ coverage and status
    def coverage_text(self, e: Entity) -> str:
        label = display.t_opt(self.t, f"coverage.{e.coverage}", e.coverage_label or self.t("common.not_recorded"))
        out = f'<span class="status coverage-{self.attr(e.coverage or "none")}">{html.escape(self.t("coverage.label", value=label))}</span>'
        key = f"coverage.explain.{e.coverage}"
        if self.i.has(key):
            out += " " + html.escape(self.t(key))
        return out

    def status_html(self, c: Claim) -> str:
        if c.status:
            word = display.t_opt(self.t, f"status.{c.status}", c.status)
            cls = f"status-{self.attr(c.status)}"
        else:
            word = self.t("status.none")
            cls = "status-none"
        return f'<span class="status {cls}">{html.escape(self.t("status.label", value=word))}</span>'

    # ------------------------------------------------------------------ claims
    def bucket(self, kind: str, c: Claim, cur: str) -> str:
        other = c.object if c.subject == cur else c.subject
        oe = self.site.entity(other)
        if oe is None:
            return "other"
        if oe.kind in ("story", "event", "place"):
            return {"story": "stories", "event": "events", "place": "places"}[oe.kind]
        if kind in ("event", "story", "place"):
            return "people_groups"
        if oe.kind == "group":
            return "groups"
        return "kinship" if c.relclass == "kinship" else "people"

    def claim_li(self, ctx: Ctx, c: Claim, cur: str) -> str:
        pred = self.t(c.predicate) if c.predicate_is_key else c.predicate
        sentence = (f'{self.ent_link(ctx, c.subject, cur)} '
                    f'<span class="rel">{self.text(ctx, pred, verbatim=True)}</span> '
                    f'{self.ent_link(ctx, c.object, cur)}')
        parts = [f'<p class="claim-text">{sentence}</p>']
        if c.kind == "participation" and c.role:
            parts.append(f'<p class="claim-role">{html.escape(self.t("claim.role", value=c.role.text))}</p>')
        elif c.role:
            parts.append(f'<p class="claim-role">{self.text(ctx, c.role.text, once=True)}</p>')
        if c.qualifiers:
            parts.append('<p class="claim-marker">' + html.escape(
                self.t("claim.marker", value="; ".join(c.qualifiers))) + "</p>")
        meta = [self.status_html(c), self.source_html(ctx, c, cur)]
        parts.append('<p class="claim-meta">' + ' <span class="sep" aria-hidden="true">&middot;</span> '.join(meta) + "</p>")
        return '<li class="claim">' + "".join(parts) + "</li>"

    def source_html(self, ctx: Ctx, c: Claim, cur: str | None = None) -> str:
        label = html.escape(self.t("claim.source"))
        if c.citation:
            cit = self.esc(c.citation)
            if c.story and c.story != cur and self.site.entity(c.story):
                story = self.site.entity(c.story)
                cit = f'<a href="{ctx.base}story/{story.pid}/">{cit}</a>'
            return f'<span class="source">{label} {cit}</span>'
        if c.basis:
            return f'<span class="source">{label} {self.text(ctx, c.basis.text, once=False, verbatim=False)}</span>'
        if c.agents:
            who = "; ".join(a.label for a in c.agents)
            return f'<span class="source">{html.escape(self.t("claim.recorded_by", value=who))}</span>'
        return f'<span class="source not-recorded">{label} {html.escape(self.t("common.not_recorded"))}</span>'

    def claim_sort_key(self, c: Claim, cur: str, bucket: str):
        other = c.object if c.subject == cur else c.subject
        oe = self.site.entity(other)
        if bucket == "stories" and oe is not None and oe.kind == "story":
            n = oe.data.get("number")
            return (0, n if n is not None else 10**6, c.predicate)
        return (1, display.sort_key(oe.name if oe else other), c.predicate)

    def sections(self, ctx: Ctx, e: Entity) -> tuple[str, dict[str, int]]:
        claims = self.site.claims.get(e.iri, [])
        buckets: dict[str, list[Claim]] = {}
        for c in claims:
            buckets.setdefault(self.bucket(e.kind, c, e.iri), []).append(c)
        out, counts = [], {}
        first = True
        for key in SECTION_ORDER[e.kind]:
            items = buckets.get(key, [])
            if not items:
                continue
            items.sort(key=lambda c: self.claim_sort_key(c, e.iri, key))
            counts[key] = len(items)
            h = html.escape(self.t(f"section.{key}")) + f' <span class="count">({len(items)})</span>'
            legend = f'<p class="legend">{html.escape(self.t("claims.legend"))}</p>' if first else ""
            first = False
            lis = "\n".join(self.claim_li(ctx, c, e.iri) for c in items)
            out.append(f'<section class="claims" id="s-{key}" aria-labelledby="h-{key}">'
                       f'<h3 id="h-{key}">{h}</h3>{legend}<ul class="claim-list">\n{lis}\n</ul></section>')
        return "\n".join(out), counts

    def counts_row(self, counts: dict[str, int], kind: str) -> str:
        bits = []
        for key in SECTION_ORDER[kind]:
            n = counts.get(key)
            if n:
                bits.append(f'<a href="#s-{key}">{html.escape(self.i.tn("count." + key, n))}</a>')
        return " &middot; ".join(bits)

    # ------------------------------------------------------------------ open questions and gaps
    def open_questions(self, ctx: Ctx, e: Entity) -> str:
        out = []
        disputes = e.data.get("disputes") or []
        if disputes:
            lis = []
            for d in disputes:
                q = self.text(ctx, d["question"].text, verbatim=False) if d["question"] else ""
                meta = []
                if d["status"]:
                    meta.append(html.escape(self.t("dispute.status", value=d["status"])))
                if d["significance"]:
                    meta.append(html.escape(self.t("dispute.significance", value=d["significance"])))
                pos = ""
                if d["positions"]:
                    pl = []
                    for p in d["positions"]:
                        who = f' ({self.esc(p["proponent"].label)})' if p["proponent"] else ""
                        claim = self.text(ctx, p["claim"].text) if p["claim"] else ""
                        pl.append(f"<li>{claim}{who}</li>")
                    pos = f'<ul class="positions">{"".join(pl)}</ul>'
                lis.append(f'<li><p class="question">{q}</p><p class="claim-meta">{" &middot; ".join(meta)}</p>{pos}</li>')
            out.append(f'<section class="disputes" id="s-disputes" aria-labelledby="h-disputes">'
                       f'<h3 id="h-disputes">{html.escape(self.t("section.disputes"))}</h3><ul>{"".join(lis)}</ul></section>')
        gaps = e.data.get("gaps") or []
        if gaps:
            lis = []
            for g in gaps:
                desc = self.text(ctx, g["description"].text) if g["description"] else ""
                cause = (f' <span class="note">({html.escape(self.t("gap.cause", value=g["cause"]))})</span>'
                         if g["cause"] else "")
                lis.append(f"<li>{desc}{cause}</li>")
            out.append(f'<section class="gaps" id="s-gaps" aria-labelledby="h-gaps">'
                       f'<h3 id="h-gaps">{html.escape(self.t("section.gaps"))}</h3><ul>{"".join(lis)}</ul></section>')
        return "\n".join(out)

    # ------------------------------------------------------------------ facts (top of page)
    def dl(self, rows: list[tuple[str, str]]) -> str:
        if not rows:
            return ""
        items = "".join(f"<dt>{dt}</dt><dd>{dd}</dd>" for dt, dd in rows)
        return f'<dl class="facts">{items}</dl>'

    def place_links(self, ctx: Ctx, iris: list[str]) -> str:
        return ", ".join(self.ent_link(ctx, i) for i in iris)

    def facts(self, ctx: Ctx, e: Entity, counts: dict[str, int]) -> str:
        rows: list[tuple[str, str]] = []
        d = e.data
        nr = f'<span class="not-recorded">{html.escape(self.t("common.not_recorded"))}</span>'
        note = ""
        if e.kind == "person":
            if d["tabaqa"]:
                rows.append((self.label(ctx, "fact.generation"), self.text(ctx, d["tabaqa"], verbatim=True)))
            if d["transmitter_role"]:
                rows.append((html.escape(self.t("fact.transmitter")), self.text(ctx, d["transmitter_role"], verbatim=True)))
            if d["death"]:
                rows.append((html.escape(self.t("fact.died")), self.dates_html(d["death"])))
            if d["affiliations"]:
                bits = []
                for a in d["affiliations"]:
                    place = self.ent_link(ctx, a["place"]) if a["place"] else nr
                    extra = [x for x in (a["type"], self.short_date([a["extent"]]) if a["extent"] else None) if x]
                    bits.append(place + (f' ({self.esc("; ".join(extra))})' if extra else ""))
                rows.append((html.escape(self.t("fact.places")), "<br>".join(bits)))
            if not rows:
                rows.append((html.escape(self.t("fact.dates_places")), nr))
            note = html.escape(self.t("facts.no_status"))
        elif e.kind == "event":
            rows.append((html.escape(self.t("fact.when")), self.dates_html(d["dates"])))
            rows.append((html.escape(self.t("fact.where")), self.place_links(ctx, d["places"]) if d["places"] else nr))
            if d["part_of"]:
                rows.append((html.escape(self.t("fact.part_of")), self.place_links(ctx, d["part_of"])))
            if d["parts"]:
                rows.append((html.escape(self.t("fact.parts")), self.place_links(ctx, d["parts"])))
            note = html.escape(self.t("facts.no_status"))
        elif e.kind == "story":
            if d["part_label"]:
                part = self.esc(display.name_display(d["part_label"]))
                if d["number"] is not None:
                    part += " &middot; " + html.escape(self.t("fact.story_number", n=d["number"], total=len(self.site.by_kind["story"])))
                rows.append((html.escape(self.t("fact.part")), part))
            elif d["number"] is not None:
                rows.append((html.escape(self.t("fact.part")), html.escape(self.t("fact.story_number", n=d["number"], total=len(self.site.by_kind["story"])))))
            rows.append((html.escape(self.t("fact.when")), self.dates_html(d["dates"])))
            rows.append((html.escape(self.t("fact.where")), self.place_links(ctx, d["places"]) if d["places"] else nr))
            note = html.escape(self.t("facts.no_status"))
        elif e.kind == "place":
            if d["types"]:
                rows.append((html.escape(self.t("fact.place_type")), ", ".join(self.text(ctx, x, verbatim=True) for x in d["types"])))
            if d["geometry"]:
                bits = []
                for g in d["geometry"]:
                    seg = [g["confidence"]] if g["confidence"] else []
                    if g["basis"]:
                        seg.append(self.t("location.basis", value=g["basis"]))
                    b = self.esc(" · ".join(seg)) if seg else nr
                    if b not in bits:
                        bits.append(b)
                rows.append((html.escape(self.t("fact.location")), "<br>".join(bits)))
            else:
                rows.append((html.escape(self.t("fact.location")), nr))
            note = html.escape(self.t("facts.no_status"))
        cr = self.counts_row(counts, e.kind)
        rows.append((html.escape(self.t("fact.in_record")),
                     cr or f'<span class="not-recorded">{html.escape(self.t("fact.no_links"))}</span>'))
        out = self.dl(rows)
        if note and any([d.get("tabaqa"), d.get("death"), d.get("affiliations"), d.get("dates"), d.get("places"),
                         d.get("geometry"), d.get("transmitter_role"), d.get("types"), d.get("part_of"),
                         d.get("parts"), d.get("part_label"), d.get("number") is not None]):
            out += f'<p class="facts-note">{note}</p>'
        return out

    # ------------------------------------------------------------------ details layer
    def details(self, ctx: Ctx, e: Entity) -> str:
        d, out = e.data, []
        # names as recorded
        names = [f'<dt>{html.escape(self.t("details.scholarly"))}</dt><dd>{self.esc(e.scholarly)}</dd>']
        if e.other_labels:
            names.append(f'<dt>{html.escape(self.t("details.other_labels"))}</dt><dd>'
                         + "<br>".join(self.esc(x) for x in e.other_labels) + "</dd>")
        if e.arabic:
            names.append(f'<dt>{html.escape(self.t("details.arabic"))}</dt><dd>'
                         + "<br>".join(f'<span lang="ar" dir="rtl">{html.escape(x, quote=False)}</span>' for x in e.arabic) + "</dd>")
        for l in e.other_names:
            names.append(f'<dt>{html.escape(self.t("details.other_names"))}</dt><dd>{self.esc(l.text)}'
                         f' <span class="note">({html.escape(l.lang or "")})</span></dd>')
        if e.kind == "person":
            for f in d["name_forms"]:
                bits = []
                for key, val in (("ism", f["ism"]), ("kunya", f["kunya"]), ("laqab", "; ".join(f["laqab"])),
                                 ("nasab", " > ".join(f["nasab"])), ("nisba", "; ".join(f["nisba"])),
                                 ("full", f["full"])):
                    if val:
                        bits.append((key, val))
                if f["scheme"]:
                    bits.append(("scheme", f["scheme"]))
                if bits:
                    inner = "".join(f'<li><span class="k">{self.label(ctx, "name." + k)}</span> {self.esc(v)}</li>' for k, v in bits)
                    names.append(f'<dt>{html.escape(self.t("details.name_form"))}</dt><dd><ul class="plain">{inner}</ul></dd>')
        out.append(f'<h3>{html.escape(self.t("details.names_heading"))}</h3><dl class="meta">{"".join(names)}</dl>')

        # story: source work
        if e.kind == "story":
            w = d.get("work")
            items = []
            items.append(f'<li>{html.escape(self.t("story.ai_note"))}</li>')
            if w:
                label = self.esc(display.name_display(w["label"])) if w["label"] else ""
                ver = f' ({self.esc(w["version"])})' if w["version"] else ""
                items.append(f'<li>{html.escape(self.t("story.work"))} {label}{ver}</li>')
                if w["comment"]:
                    items.append(f'<li>{html.escape(self.t("story.work_note"))} {self.text(ctx, w["comment"].text)}</li>')
            if d.get("citation"):
                items.append(f'<li>{html.escape(self.t("story.citation", value=d["citation"]))}</li>')
            if d.get("witness"):
                items.append(f'<li>{html.escape(self.t("story.witness"))} {self.esc(d["witness"])}</li>')
            out.append(f'<h3>{html.escape(self.t("details.story_heading"))}</h3><ul class="plain">{"".join(items)}</ul>')
        else:
            claims = self.site.claims.get(e.iri, [])
            if any(c.ai_draft for c in claims):
                out.append(f'<h3>{html.escape(self.t("details.story_heading"))}</h3>'
                           f'<p>{html.escape(self.t("claims.ai_note"))}</p>')

        # coverage
        out.append(f'<h3>{html.escape(self.t("details.coverage_heading"))}</h3><p>{self.coverage_text(e)}</p>')

        # who recorded what
        claims = self.site.claims.get(e.iri, [])
        by_agent: dict[tuple[str, bool], int] = {}
        for c in claims:
            for a in (c.agents or []):
                by_agent[(a.label, a.software)] = by_agent.get((a.label, a.software), 0) + 1
        who = []
        for a in e.agents:
            who.append(f'<li>{html.escape(self.t("details.record_by"))} {self.esc(a.label)}'
                       + (f' <span class="note">({html.escape(self.t("details.software"))})</span>' if a.software else "")
                       + "</li>")
        if e.recorded:
            who.append(f'<li>{html.escape(self.t("details.recorded_on", value=e.recorded[0]))}</li>')
        for (label, soft), n in sorted(by_agent.items(), key=lambda x: (-x[1], x[0][0])):
            who.append(f'<li>{html.escape(self.i.tn("details.claims_by", n))} {self.esc(label)}'
                       + (f' <span class="note">({html.escape(self.t("details.software"))})</span>' if soft else "") + "</li>")
        if who:
            out.append(f'<h3>{html.escape(self.t("details.recorded_heading"))}</h3><ul class="plain">{"".join(who)}</ul>')

        # basis statements for claims that cite a passage
        bases = []
        for c in claims:
            if c.basis and c.citation and c.basis.text not in bases:
                bases.append(c.basis.text)
        if bases:
            lis = "".join(f"<li>{self.text(ctx, b)}</li>" for b in bases)
            out.append(f'<h3>{html.escape(self.t("details.basis_heading"))}</h3>'
                       f'<details class="nested"><summary>{html.escape(self.i.tn("details.basis_summary", len(bases)))}</summary>'
                       f'<ul class="plain">{lis}</ul></details>')

        # raw identifiers and turtle
        raw = [f'<dt>{html.escape(self.t("details.iri"))}</dt><dd><code class="iri">{html.escape(e.iri, quote=False)}</code></dd>',
               f'<dt>{html.escape(self.t("details.turtle"))}</dt><dd><a href="entity.ttl">{html.escape(self.t("details.turtle_link"))}</a></dd>']
        out.append(f'<h3>{html.escape(self.t("details.raw_heading"))}</h3><dl class="meta">{"".join(raw)}</dl>')
        claim_iris = sorted({c.node for c in claims if c.node})
        if claim_iris:
            lis = "".join(f'<li><code class="iri">{html.escape(i, quote=False)}</code></li>' for i in claim_iris)
            out.append(f'<h4>{html.escape(self.t("details.claim_iris"))}</h4><ul class="plain iri-list">{lis}</ul>')
        out.append(self.external_matches(e))
        return "\n".join(p for p in out if p)

    def external_matches(self, e: Entity) -> str:
        """Possible matches in other databases (site/external.py): each one a proposal shown
        with the status its row records, never a statement that it is the same person."""
        rows = self.external.get(e.iri)
        if not rows:
            return ""
        lis = []
        for r in rows:
            system = display.t_opt(self.t, f"external.system.{r['system']}", r["system"])
            name = html.escape(self.t("external.id", system=system, id=r["external_id"]), quote=False)
            if r["url"]:
                name = f'<a href="{self.attr(r["url"])}" rel="external noreferrer">{name}</a>'
            bits = [name]
            if r["external_label"]:
                bits.append(self.esc(self.t("external.label", value=r["external_label"])))
            if r["status"] == "proposed":
                word = self.t("external.proposed")
            else:
                word = self.t("status.label", value=display.t_opt(self.t, f"status.{r['status']}", r["status"] or self.t("status.none")))
            bits.append(f'<span class="status status-{self.attr(r["status"] or "none")}">{html.escape(word)}</span>')
            notes = []
            if r["evidence"]:
                notes.append(self.t("external.evidence", value=r["evidence"]))
            if r["confidence"]:
                notes.append(self.t("external.confidence", value=r["confidence"]))
            if notes:
                bits.append(f'<span class="note">{self.esc(" ".join(notes))}</span>')
            lis.append(f'<li>{" ".join(bits)}</li>')
        return (f'<h3>{html.escape(self.t("external.heading"))}</h3><p class="note">{html.escape(self.t("external.lead"))}</p>'
                f'<ul class="plain external-list">{"".join(lis)}</ul>')

    # ------------------------------------------------------------------ entity page
    def thread_root(self, ctx: Ctx, e: Entity) -> str:
        """The "follow the thread" switch: hidden, and so absent, without JavaScript;
        static/thread.js shows it and draws the thread from thread.json."""
        if e.kind not in FOCUS_KINDS:
            return ""
        return self.tpl("thread_root", base=ctx.base, focus=f"{e.kind}/{e.pid}")

    def entity_page(self, e: Entity) -> str:
        ctx = Ctx(f"{e.kind}/{e.pid}/")
        sections, counts = self.sections(ctx, e)
        extra = ""
        banner = ""
        if e.kind == "story":
            cov = e.coverage
            if cov in (None, "stub", "outline", "sourced"):
                msg = self.t("story.banner")
            else:
                msg = self.t("story.banner_other", value=e.coverage_label or cov)
            banner = f'<p class="banner" role="note"><strong>{html.escape(msg)}</strong></p>'
        if e.kind == "person" and e.prophet:
            extra = " is-prophet"
            facts = f'<p class="prophet-note">{html.escape(self.t("prophet.note"))}</p>'
            cr = self.counts_row(counts, "person")
            if cr:
                facts += f'<p class="prophet-counts">{cr}</p>'
        else:
            facts = self.facts(ctx, e, counts)
        h1 = self.name_h1(e) + self.honorific_html(e)
        type_label = self.t(f"type.{e.subtype or e.kind}")
        story_html = ""
        if e.kind == "story":
            prose = e.data.get("prose")
            if prose:
                paras = [p for p in re.split(r"\n\s*\n", prose.text) if p.strip()]
                inner = "".join(f"<p>{self.text(ctx, p.strip(), once=True)}</p>" for p in paras)
            else:
                inner = f'<p class="not-recorded">{html.escape(self.t("story.no_text"))}</p>'
            story_html = (f'<section class="story-text" aria-labelledby="h-story">'
                          f'<h2 id="h-story">{html.escape(self.t("story.text_heading"))}</h2>'
                          f'<div class="prose">{inner}</div></section>')
        evidence = "\n".join(p for p in (sections, self.open_questions(ctx, e)) if p)
        # The evidence: one anchor (#evidence) that the Study and Research doors link to, so
        # those readers land on the claims first while Discover readers start at the top.
        lead_key = "evidence.lead" if evidence else "evidence.none"
        evidence_lead = self.i.th(lead_key, name=self.esc(e.name))
        desc = self.t("meta.entity", type=type_label, coverage=display.t_opt(self.t, f"coverage.{e.coverage}", e.coverage or ""))
        thread = self.thread_root(ctx, e)
        content = self.tpl("entity", kind=e.kind, extra_class=extra, type_label=html.escape(type_label), h1=h1,
                           banner=banner, coverage=self.coverage_text(e), facts=facts, thread=thread,
                           story=story_html, evidence_lead=evidence_lead, sections=evidence,
                           details=self.details(ctx, e))
        kind_dir = e.kind
        return self.shell(ctx, self.page_title(e.name), content,
                          body_class=f"page-entity kind-{e.kind}" + (" is-prophet" if e.prophet else ""),
                          current=KIND_NAV[e.kind],
                          crumbs=[(self.t(f"nav.{KIND_NAV[e.kind]}"), f"{kind_dir}/"), (e.name, None)],
                          description=desc,
                          scripts=f'<script src="{ctx.base}assets/thread.js" defer></script>' if thread else "")

    # ------------------------------------------------------------------ index pages
    def index_row(self, ctx: Ctx, e: Entity, numbered: bool = False, anchor: str = "") -> str:
        """One line of an A-Z list. anchor="evidence" opens the page at its evidence."""
        meta = []
        d = e.data
        if e.kind == "event":
            when = self.short_date(d["dates"])
            if when:
                meta.append(self.esc(when))
            if d["places"]:
                meta.append(self.place_links(ctx, d["places"]))
        elif e.kind == "place" and d["types"]:
            meta.append(", ".join(self.esc(x) for x in d["types"]))
        elif e.kind == "group":
            meta.append(html.escape(self.t(f"type.{e.subtype or 'group'}")))
        cov = display.t_opt(self.t, f"coverage.{e.coverage}", e.coverage or self.t("common.not_recorded"))
        ar = self.arabic_names(e.arabic)
        m = f' <span class="meta">{" &middot; ".join(meta)}</span>' if meta else ""
        value = f' value="{e.data["number"]}"' if numbered and e.data.get("number") is not None else ""
        frag = f"#{anchor}" if anchor else ""
        return (f'<li{value}><a href="{ctx.base}{e.kind}/{e.pid}/{frag}">{self.esc(e.name)}</a>{ar}{m} '
                f'<span class="cov"><span class="sr-only">{html.escape(self.t("coverage.sr"))} </span>{html.escape(cov)}</span></li>')

    def coverage_summary(self, ents: list[Entity]) -> str:
        counts: dict[str, int] = {}
        for e in ents:
            counts[e.coverage or "none"] = counts.get(e.coverage or "none", 0) + 1
        order = ["stub", "outline", "sourced", "reviewed", "verified", "none"]
        bits = []
        for k in order:
            if counts.get(k):
                lab = display.t_opt(self.t, f"coverage.{k}", k) if k != "none" else self.t("common.not_recorded")
                bits.append(f"{counts[k]} {html.escape(lab)}")
        return html.escape(self.t("index.coverage_prefix")) + " " + ", ".join(bits)

    def index_page(self, kind: str) -> str:
        ctx = Ctx(f"{kind}/")
        ents = self.site.by_kind[kind]
        nav_key = KIND_NAV[kind]
        banner = ""
        if kind == "story":
            groups: dict[tuple, list[Entity]] = {}
            for e in self.site.stories_in_order():
                key = (e.data.get("part_number") is None, e.data.get("part_number") or 0, e.data.get("part_label") or "")
                groups.setdefault(key, []).append(e)
            sections = []
            for key, items in groups.items():
                title = display.name_display(key[2]) if key[2] else self.t("common.not_recorded")
                lis = "\n".join(self.index_row(ctx, e, numbered=True) for e in items)
                sections.append(f'<section><h2>{self.esc(title)}</h2><ol class="index-list reading-order">\n{lis}\n</ol></section>')
            az = self.az_sections(ctx, ents, "story-az", level=3)
            body = ("".join(sections) + f'<h2 id="story-az-top">{html.escape(self.t("index.story_az"))}</h2>' + az)
            banner = f'<p class="banner" role="note"><strong>{html.escape(self.t("story.banner"))}</strong></p>'
        else:
            body = self.az_nav(ents) + self.az_sections(ctx, ents, "letter")
        lead = self.i.tn(f"index.lead.{kind}", len(ents))
        content = self.tpl("index", kind=kind, h1=html.escape(self.t(f"nav.{nav_key}")), lead=html.escape(lead),
                           coverage_summary=self.coverage_summary(ents), banner=banner, body=body)
        return self.shell(ctx, self.page_title(self.t(f"nav.{nav_key}")), content, body_class=f"page-index kind-{kind}",
                          current=nav_key, crumbs=[(self.t(f"nav.{nav_key}"), None)],
                          description=lead)

    def letters(self, ents: list[Entity]) -> list[str]:
        seen = []
        for e in ents:
            l = display.index_letter(e.name)
            if l not in seen:
                seen.append(l)
        return seen

    def az_nav(self, ents: list[Entity], prefix: str = "letter") -> str:
        items = "".join(f'<li><a href="#{prefix}-{self.attr(l if l != "#" else "other")}">{html.escape(l)}</a></li>'
                        for l in self.letters(ents))
        return f'<nav class="az" aria-label="{self.attr(self.t("index.az"))}"><ul>{items}</ul></nav>'

    def az_sections(self, ctx: Ctx, ents: list[Entity], prefix: str, level: int = 2, row=None) -> str:
        row = row or self.index_row
        out, cur, lis = [], None, []

        def flush():
            if cur is not None:
                anchor = cur if cur != "#" else "other"
                out.append(f'<section><h{level} id="{prefix}-{self.attr(anchor)}">{html.escape(cur)}</h{level}>'
                           f'<ul class="index-list">\n' + "\n".join(lis) + "\n</ul></section>")

        for e in ents:
            letter = display.index_letter(e.name)
            if letter != cur:
                flush()
                cur, lis = letter, []
            lis.append(row(ctx, e))
        flush()
        return "".join(out)

    # ------------------------------------------------------------------ home
    def checked_html(self) -> str:
        """How far the record has been checked, in numbers read from the graph."""
        s = self.site
        sc, cc = s.status_counts(), s.coverage_counts()
        total = sum(sc.values())
        parts = [self.i.th("home.status_claims", total=total,
                           proposed=sc.get("proposed", 0), under_review=sc.get("under_review", 0),
                           accepted=sc.get("accepted", 0)),
                 self.i.th("home.status_records", stub=cc.get("stub", 0), outline=cc.get("outline", 0),
                           sourced=cc.get("sourced", 0), reviewed=cc.get("reviewed", 0),
                           verified=cc.get("verified", 0))]
        parts.append(self.i.th("home.status_unstated"))
        status = "".join(f"<p>{p}</p>" for p in parts)
        if not sc.get("accepted") and not cc.get("reviewed") and not cc.get("verified"):
            status += f'<p><strong>{html.escape(self.t("home.status_none"))}</strong></p>'
        return status

    def view_link(self, ctx: Ctx, folder: str) -> str:
        return f'<a href="{ctx.base}{folder}/">{html.escape(self.t(f"hub.view.{folder}.name"))}</a>'

    def door_views(self, ctx: Ctx, door: str, views: list[str]) -> str:
        """The views built for one door (site/hub.py), as a short list; empty if none is built."""
        mine = [v for v in views if hub.door_of(v) == door]
        if not mine:
            return ""
        lis = "".join(f'<li>{self.view_link(ctx, v)} <span class="note">{html.escape(self.t(f"hub.view.{v}.desc"))}</span></li>'
                      for v in mine)
        return f'<ul class="door-more">{lis}</ul>'

    def doors_html(self, ctx: Ctx, views: list[str]) -> str:
        """The three doors (maintainer answer R4). Discover leads to the stories, read story
        first; Study and Research lead to pages whose links open each record at #evidence
        (R9: the evidence first). One page per record either way."""
        s = self.site
        stories = s.stories_in_order()
        go = {
            "discover": [(f"{ctx.base}story/", self.i.tn("door.discover.go", len(stories)))],
            "study": [(f"{ctx.base}study/", self.t("door.study.go"))],
            "research": [(f"{ctx.base}research/", self.t("door.research.go"))],
        }
        if stories:
            go["discover"].append((f"{ctx.base}story/{stories[0].pid}/", self.t("door.discover.first", name=stories[0].name)))
        out = []
        for door in hub.DOORS:
            links = "".join(f'<li><a href="{href}">{self.esc(text)}</a></li>' for href, text in go[door])
            out.append(f'<li class="door door-{door}" id="door-{door}"><h2>{html.escape(self.t(f"door.{door}.title"))}</h2>'
                       f'<p>{html.escape(self.t(f"door.{door}.lead"))}</p><ul class="door-go">{links}</ul>'
                       f'{self.door_views(ctx, door, views)}</li>')
        return "\n".join(out)

    def hub_html(self, ctx: Ctx, views: list[str]) -> str:
        """Every view of the graph: the reader pages, the door pages, each view another
        builder has written into site/dist (only those that exist), and the prototypes."""
        s = self.site
        reader = [f'<a href="{ctx.base}{kind}/">{html.escape(self.i.tn("home.count." + kind, len(s.by_kind[kind])))}</a>'
                  for _, kind in NAV]
        reader += [f'<a href="{ctx.base}search/">{html.escape(self.t("search.title"))}</a>',
                   f'<a href="{ctx.base}glossary/">{html.escape(self.t("nav.glossary"))}</a>']
        sep = ' <span class="sep" aria-hidden="true">&middot;</span> '
        items = [f'<li><span class="hub-name">{html.escape(self.t("hub.reader.name"))}</span> '
                 f'<span class="hub-desc">{html.escape(self.t("hub.reader.desc"))}</span>'
                 f'<span class="hub-links">{sep.join(reader)}</span></li>']
        for folder in ("study", "research"):
            items.append(f'<li><a class="hub-name" href="{ctx.base}{folder}/">{html.escape(self.t(f"hub.{folder}.name"))}</a> '
                         f'<span class="hub-desc">{html.escape(self.t(f"hub.{folder}.desc"))}</span></li>')
        for v in views:
            items.append(f'<li><a class="hub-name" href="{ctx.base}{v}/">{html.escape(self.t(f"hub.view.{v}.name"))}</a> '
                         f'<span class="hub-desc">{html.escape(self.t(f"hub.view.{v}.desc"))}</span></li>')
        items.append(f'<li><a class="hub-name" href="{ctx.base}{experiments.FOLDER}/">{html.escape(self.t("experiments.title"))}</a> '
                     f'<span class="hub-desc">{html.escape(self.t("hub.experiments.desc"))}</span></li>')
        return f'<ul class="hub-list" data-views="{self.attr(" ".join(views))}">' + "\n".join(items) + "</ul>"

    def home_page(self, views: list[str] | None = None) -> str:
        """The home page: three doors, then the hub. `views`: the view folders found in
        site/dist (site/hub.py); the hub links only those."""
        ctx = Ctx("")
        views = views or []
        names_note = html.escape(self.t("home.names_note"))
        glossary_note = self.i.th("home.glossary_note", glossary=f'<a href="{ctx.base}glossary/">{html.escape(self.t("nav.glossary"))}</a>')
        content = self.tpl("home", doors=self.doors_html(ctx, views), hub=self.hub_html(ctx, views),
                           status=self.checked_html(), names_note=names_note, glossary_note=glossary_note)
        return self.shell(ctx, self.t("site.name") + f' {self.t("title.sep")} ' + self.t("home.title_suffix"), content,
                          body_class="page-home", current="home", crumbs=[], description=self.t("home.lead"))

    # ------------------------------------------------------------------ door pages
    def door_page(self, door: str, views: list[str], toc: list[tuple[str, str]], body: str) -> str:
        ctx = Ctx(f"{door}/")
        title = self.t(f"door.{door}.title")
        toc_html = "".join(f'<li><a href="#{a}">{html.escape(text)}</a></li>' for a, text in toc)
        more = self.door_views(ctx, door, views)
        views_html = (f'<p class="door-views-lead">{html.escape(self.t("door.views_lead"))}</p>{more}') if more else ""
        content = self.tpl("door", door=door, h1=html.escape(title), lead=html.escape(self.t(f"door.{door}.page_lead")),
                           views=views_html, toc=toc_html, body=body)
        return self.shell(ctx, self.page_title(title), content, body_class=f"page-door door-{door}",
                          current=None, crumbs=[(title, None)], description=self.t(f"door.{door}.page_lead"))

    def evidence_href(self, ctx: Ctx, e: Entity, anchor: str = "evidence") -> str:
        return f"{ctx.base}{e.kind}/{e.pid}/#{anchor}"

    def timeline_rows(self, ctx: Ctx) -> tuple[list[str], list[str]]:
        """Events in time order by the earliest recorded day; the date shown is the recorded
        one. Events with no recorded day are returned apart, never placed."""
        dated, undated = [], []
        for e in self.site.by_kind["event"]:
            days = sorted(x["earliest"][:10] for x in e.data.get("dates", []) if x.get("earliest"))
            ends = sorted(x["latest"][:10] for x in e.data.get("dates", []) if x.get("latest"))
            when = self.short_date(e.data.get("dates", []))
            place = self.place_links(ctx, e.data["places"]) if e.data.get("places") else ""
            cov = display.t_opt(self.t, f"coverage.{e.coverage}", e.coverage or self.t("common.not_recorded"))
            row = (f'<a href="{self.evidence_href(ctx, e)}">{self.esc(e.name)}</a>'
                   + (f' <span class="meta">{place}</span>' if place else "")
                   + f' <span class="cov"><span class="sr-only">{html.escape(self.t("coverage.sr"))} </span>{html.escape(cov)}</span>')
            if days and when:
                dated.append(((days[0], ends[0] if ends else "", display.sort_key(e.name), e.pid),
                              f'<li><span class="when">{self.esc(when)}</span> {row}</li>'))
            else:
                undated.append(f"<li>{row}</li>")
        return [r for _, r in sorted(dated)], undated

    def study_page(self, views: list[str]) -> str:
        """Study: people, groups and events in time order; every link opens the record's page
        at its evidence (#evidence)."""
        ctx = Ctx("study/")
        s = self.site
        dated, undated = self.timeline_rows(ctx)
        events = (f'<section id="study-events" aria-labelledby="study-events-h"><h2 id="study-events-h">{html.escape(self.t("study.events"))}</h2>'
                  f'<p class="note">{html.escape(self.t("study.events_note"))}</p>'
                  f'<ol class="index-list timeline-list">\n' + "\n".join(dated) + "\n</ol>")
        if undated:
            events += (f'<h3>{html.escape(self.t("study.undated"))}</h3><ul class="index-list">\n' + "\n".join(undated) + "\n</ul>")
        events += "</section>"
        row = lambda c, e: self.index_row(c, e, anchor="evidence")
        people = (f'<section id="study-people" aria-labelledby="study-people-h"><h2 id="study-people-h">{html.escape(self.t("nav.people"))}</h2>'
                  + self.az_nav(s.by_kind["person"], "study-p") + self.az_sections(ctx, s.by_kind["person"], "study-p", level=3, row=row)
                  + "</section>")
        groups = (f'<section id="study-groups" aria-labelledby="study-groups-h"><h2 id="study-groups-h">{html.escape(self.t("nav.groups"))}</h2>'
                  f'<ul class="index-list">\n' + "\n".join(row(ctx, e) for e in s.by_kind["group"]) + "\n</ul></section>")
        toc = [("study-events", self.t("study.events")), ("study-people", self.t("nav.people")),
               ("study-groups", self.t("nav.groups"))]
        return self.door_page("study", views, toc, events + people + groups)

    def sources_html(self) -> str:
        """Who recorded the claims and which works they cite, counted from the graph."""
        claims = {id(c): c for cs in self.site.claims.values() for c in cs}.values()
        by_agent: dict[tuple[str, bool], int] = {}
        by_work: dict[str, list] = {}
        for c in claims:
            for a in c.agents:
                by_agent[(a.label, a.software)] = by_agent.get((a.label, a.software), 0) + 1
            story = self.site.entity(c.story) if c.story else None
            work = story.data.get("work") if story else None
            if work and work.get("label"):
                by_work.setdefault(work["label"], [0, work.get("ai")])[0] += 1
        soft = f' <span class="note">({html.escape(self.t("details.software"))})</span>'
        agents = "".join(f'<li>{self.esc(label)}{soft if software else ""}: {html.escape(self.i.tn("research.claims", n))}</li>'
                         for (label, software), n in sorted(by_agent.items(), key=lambda x: (-x[1], x[0][0])))
        works = "".join(f'<li>{self.esc(display.name_display(label))}: {html.escape(self.i.tn("research.claims", n))}'
                        + (f' <span class="note">{html.escape(self.t("claims.ai_note"))}</span>' if ai else "") + "</li>"
                        for label, (n, ai) in sorted(by_work.items()))
        out = (f'<h3>{html.escape(self.t("research.recorded_by"))}</h3><ul class="plain">{agents}</ul>')
        if works:
            out += f'<h3>{html.escape(self.t("research.works"))}</h3><ul class="plain">{works}</ul>'
        return out

    def questions_html(self, ctx: Ctx) -> str:
        """Records with open questions (disputes) or recorded gaps, linked at those sections."""
        out = []
        for key, anchor, heading in (("disputes", "s-disputes", "section.disputes"), ("gaps", "s-gaps", "section.gaps")):
            ents = [e for k in KINDS for e in self.site.by_kind[k] if e.data.get(key)]
            if not ents:
                continue
            lis = "".join(f'<li><a href="{self.evidence_href(ctx, e, anchor)}">{self.esc(e.name)}</a> '
                          f'<span class="meta">{html.escape(self.t(f"type.{e.subtype or e.kind}"))}</span></li>' for e in ents)
            out.append(f'<h3>{html.escape(self.t(heading))}</h3><ul class="plain">{lis}</ul>')
        return "".join(out) or f'<p class="not-recorded">{html.escape(self.t("research.no_questions"))}</p>'

    def downloads_html(self, ctx: Ctx, downloads: list[tuple[str, str, int]]) -> str:
        """`downloads`: (key, path in site/dist, bytes) for each data file build.py copied."""
        lis = []
        for key, rel, size in downloads:
            kb = html.escape(self.t("research.size_kb", n=max(1, round(size / 1000))))
            lis.append(f'<li><a href="{ctx.base}{rel}">{html.escape(self.t(f"research.download.{key}"))}</a> '
                       f'<span class="note">({kb})</span> {html.escape(self.t(f"research.download.{key}.note"))}</li>')
        lis.append(f'<li>{html.escape(self.t("research.entity_ttl"))}</li>')
        lis.append(f'<li>{html.escape(self.t("research.iris"))}</li>')
        return f'<ul class="plain downloads">{"".join(lis)}</ul><p class="note">{html.escape(self.t("research.licence"))}</p>'

    def record_row(self, ctx: Ctx, e: Entity) -> str:
        n = len(self.site.claims.get(e.iri, []))
        cov = display.t_opt(self.t, f"coverage.{e.coverage}", e.coverage or self.t("common.not_recorded"))
        return (f'<li><a href="{self.evidence_href(ctx, e)}">{self.esc(e.name)}</a> '
                f'<span class="meta">{html.escape(self.i.tn("research.claims", n))}</span> '
                f'<a class="ttl" href="{ctx.base}{e.kind}/{e.pid}/entity.ttl">{html.escape(self.t("details.turtle"))}</a>'
                f' <span class="cov"><span class="sr-only">{html.escape(self.t("coverage.sr"))} </span>{html.escape(cov)}</span></li>')

    def research_page(self, views: list[str], downloads: list[tuple[str, str, int]]) -> str:
        """Research: sources and data, and every record linked at its evidence (#evidence)."""
        ctx = Ctx("research/")
        s = self.site
        records = "".join(f'<h3 id="research-{kind}">{html.escape(self.t(f"nav.{nav}"))}</h3>'
                          f'<ul class="index-list">\n' + "\n".join(self.record_row(ctx, e) for e in s.by_kind[kind]) + "\n</ul>"
                          for nav, kind in NAV)
        parts = [
            ("research-status", "home.status_heading", self.checked_html()),
            ("research-sources", "research.sources", f'<p>{html.escape(self.t("research.sources_lead"))}</p>' + self.sources_html()),
            ("research-questions", "research.questions", self.questions_html(ctx)),
            ("research-data", "research.data", self.downloads_html(ctx, downloads)),
            ("research-records", "research.records", f'<p class="note">{html.escape(self.t("research.records_note"))}</p>' + records),
        ]
        body = "".join(f'<section id="{a}" aria-labelledby="{a}-h"><h2 id="{a}-h">{html.escape(self.t(k))}</h2>{inner}</section>'
                       for a, k, inner in parts)
        toc = [(a, self.t(k)) for a, k, _ in parts]
        return self.door_page("research", views, toc, body)

    # ------------------------------------------------------------------ earlier prototypes
    @staticmethod
    def proto_key(stem: str, page: str) -> str:
        return f"experiments.{stem}" if page == "index.html" else f"experiments.{stem}.{page[:-5].replace('-', '_')}"

    def experiments_page(self) -> str:
        ctx = Ctx(f"{experiments.FOLDER}/")
        items = []
        for folder, _, pages, stem in experiments.PROTOTYPES:
            subs = []
            for page in pages[1:]:
                key = self.proto_key(stem, page)
                subs.append(f'<li><a href="{folder}/{page}">{html.escape(self.t(key + ".name"))}</a> '
                            f'<span class="note">{html.escape(self.t(key + ".desc"))}</span></li>')
            key = self.proto_key(stem, pages[0])
            items.append(f'<li><h2><a href="{folder}/">{html.escape(self.t(key + ".name"))}</a></h2>'
                         f'<p>{self.esc(self.t(key + ".desc"))}</p>'
                         + (f'<ul class="plain">{"".join(subs)}</ul>' if subs else "") + "</li>")
        content = self.tpl("experiments", items="\n".join(items))
        return self.shell(ctx, self.page_title(self.t("experiments.title")), content, body_class="page-experiments",
                          current=None, crumbs=[(self.t("experiments.title"), None)], description=self.t("experiments.lead"))

    def archive_note(self, folder: str, base: str) -> str:
        """The note at the top of each copied prototype page."""
        return self.tpl("archive_note", back=f"{base}{experiments.FOLDER}/", home=base)

    # ------------------------------------------------------------------ search
    def search_row(self, ctx: Ctx, e: Entity) -> str:
        """One line of the all-names list. search.js shows copies of these lines as results."""
        kind = html.escape(self.t(f"type.{e.subtype or e.kind}"))
        cov = display.t_opt(self.t, f"coverage.{e.coverage}", e.coverage or self.t("common.not_recorded"))
        return (f'<li><a href="{ctx.base}{e.kind}/{e.pid}/">{self.esc(e.name)}</a>{self.arabic_names(e.arabic)} '
                f'<span class="meta">{kind}</span> <span class="cov"><span class="sr-only">'
                f'{html.escape(self.t("coverage.sr"))} </span>{html.escape(cov)}</span></li>')

    def search_scope(self, ctx: Ctx) -> str:
        """What a search looks through and how far it has been checked: the empty-result
        rule of docs/05 section 3 (report coverage, never a blank)."""
        s = self.site
        link = {k: f'<a href="{ctx.base}{k}/">{html.escape(self.i.tn("home.count." + k, len(s.by_kind[k])))}</a>'
                for k in KINDS}
        arabic = sum(len(e.arabic) for e in s.entities.values())
        scope = self.i.th("search.scope", people=link["person"], events=link["event"], places=link["place"],
                          groups=link["group"], stories=link["story"],
                          arabic=html.escape(self.i.tn("search.arabic_count", arabic)))
        sc, cc = s.status_counts(), s.coverage_counts()
        if not sc.get("accepted") and not cc.get("reviewed") and not cc.get("verified"):
            checked = html.escape(self.t("search.unverified"))
        else:
            checked = html.escape(self.t("search.partly_verified", accepted=sc.get("accepted", 0),
                                         total=sum(sc.values())))
        return f"<p>{scope}</p><p>{checked}</p>"

    def search_page(self) -> str:
        """The search page. Without JavaScript it is an A-Z list of every name, which the
        search box on every page submits to; with it, search.js filters by search.json."""
        ctx = Ctx("search/")
        ents = sorted(self.site.entities.values(),
                      key=lambda e: (display.sort_key(e.name), KINDS.index(e.kind), e.pid))
        scope = self.search_scope(ctx)
        strings = {
            "count_one": self.t("search.count.one"), "count_other": self.t("search.count.other"),
            "none": self.t("search.none"), "matching": self.t("search.matching"),
            "similar": self.t("search.similar"), "similar_note": self.t("search.similar_note"),
            "arabic_note": self.t("search.arabic_note"), "more": self.t("search.more"),
        }
        content = self.tpl(
            "search", base=ctx.base,
            nojs=f'<p>{html.escape(self.t("search.nojs"))}</p>{scope}',
            empty=f'{scope}<p>{html.escape(self.t("search.empty_next"))}</p>',
            az=self.az_nav(ents, "all") + self.az_sections(ctx, ents, "all", level=3, row=self.search_row),
            strings=json.dumps(strings, ensure_ascii=False, sort_keys=True).replace("</", "<\\/"))
        return self.shell(ctx, self.page_title(self.t("search.title")), content, body_class="page-search",
                          current="search", crumbs=[(self.t("search.title"), None)],
                          description=self.t("search.help"), search_box=False,
                          scripts=f'<script src="{ctx.base}assets/search.js" defer></script>')

    # ------------------------------------------------------------------ glossary
    def glossary_page(self) -> str:
        ctx = Ctx("glossary/")
        defined, needed = self.glossary.listed()
        dl = []
        def plain(e: dict) -> str:
            if not e.get("plain"):
                return ""
            return (f'<p class="note plain-wording">{self.esc(self.t("glossary.plain", value=e["plain"]))} '
                    f'{html.escape(self.t("glossary.source", value=e["plain_source"]))}</p>')
        for e in defined:
            ar = f' <span class="name-ar" lang="ar" dir="rtl">{html.escape(e["arabic"], quote=False)}</span>' if e.get("arabic") else ""
            dl.append(f'<dt id="term-{self.attr(e["key"])}">{self.esc(e["term"])}{ar}</dt>'
                      f'<dd><p>{self.esc(e["definition"])}</p>'
                      f'<p class="note">{html.escape(self.t("glossary.source", value=e["source"]))}</p>{plain(e)}</dd>')
        defined_html = f'<dl class="glossary-list">{"".join(dl)}</dl>' if dl else f'<p>{html.escape(self.t("glossary.none_defined"))}</p>'
        lis = "".join(f'<li id="term-{self.attr(e["key"])}">{self.esc(e["term"])} '
                      f'<span class="note">({html.escape(self.t("glossary.needed_tag"))})</span>{plain(e)}</li>' for e in needed)
        needed_html = f'<ul class="glossary-needed">{lis}</ul>'
        content = self.tpl("glossary", defined=defined_html, needed=needed_html)
        return self.shell(ctx, self.page_title(self.t("nav.glossary")), content, body_class="page-glossary",
                          current="glossary", crumbs=[(self.t("nav.glossary"), None)],
                          description=self.t("glossary.lead"))
