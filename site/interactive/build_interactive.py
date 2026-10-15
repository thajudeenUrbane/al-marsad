#!/usr/bin/env python3
"""Interactive tier (slice 10): a timeline page and a map page over the one graph.

    .venv/bin/python site/interactive/build_interactive.py [--graph build/graph.ttl] [--out site/dist]

Run it after site/build.py: every mark links to a reader page that site/build.py writes. If
the output folder has no reader pages yet, this script runs site/build.py first. It writes,
and owns, only these two folders inside the output:

    timeline/  index.html  data.json  timeline.js  common.js  interactive.css
    map/       index.html  data.json  map.js       common.js  interactive.css

Each page is complete without JavaScript as a text version generated from the same data that
the drawing uses; with JavaScript it draws the timeline or the map from its data.json. No
external requests, no web fonts, no images, no figures of people. Names and dates go through
site/display.py, the page frame through site/render.py, so they read exactly as the reader
pages do. Every visible string is an i18n key: this slice's keys (prefix "ix.") live in
site/interactive/i18n/en.json; dates, status and coverage words come from site/i18n/en.json.
"""
from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
ROOT = SITE.parent
for p in (str(SITE), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import display  # noqa: E402
import extract  # noqa: E402
from glossary import Glossary  # noqa: E402
from model import Entity, Site  # noqa: E402
from render import Ctx, I18n, Renderer  # noqa: E402

MARKER = ".al-marsad-site"          # written by site/build.py into the folder it owns
VIEWS = ("timeline", "map")
STATIC = HERE / "static"
SHARED = ("common.js", "interactive.css")
PAGE_BUDGET = 2_000_000             # docs/05 section 7: interactive tier, bytes per page
# The AH row of the timeline axis is worked out with the tabular Islamic calendar, the method
# the graph records for its own conversions. It labels the axis only; no item is dated by it.
# Set to False to draw the CE row alone.
HIJRI_AXIS = True
LONG_LIST = 12                      # longer lists of unplaced items start folded


# ------------------------------------------------------------------------------ strings
class Strings:
    """This slice's strings ("ix." keys) first; every other key from the reader's file."""
    PREFIX = "ix."

    def __init__(self, own: Path, reader: I18n):
        self.own: dict[str, str] = json.loads(own.read_text(encoding="utf-8"))
        self.reader = reader
        self.used: set[str] = set()

    def raw(self, key: str) -> str:
        if key.startswith(self.PREFIX):
            self.used.add(key)
            return self.own[key]  # a missing key is a build error on purpose
        s = self.reader.d[key]
        self.reader.used.add(key)
        return s

    def t(self, key: str, **kw) -> str:
        s = self.raw(key)
        return s.format(**kw) if kw else s

    def th(self, key: str, **kw) -> str:
        """The string escaped for HTML; keyword values must already be HTML."""
        s = html.escape(self.raw(key), quote=False)
        return s.format(**kw) if kw else s

    def tn(self, key: str, n: int, **kw) -> str:
        return self.t(f"{key}.{'one' if n == 1 else 'other'}", n=n, **kw)

    def thn(self, key: str, n: int, **kw) -> str:
        return self.th(f"{key}.{'one' if n == 1 else 'other'}", n=n, **kw)


def esc(s: str) -> str:
    return display.mark_arabic(html.escape(s, quote=False))


def attr(s: str) -> str:
    return html.escape(s, quote=True)


# ------------------------------------------------------------------------------ shared fragments
class Pieces:
    def __init__(self, site: Site, S: Strings):
        self.site, self.S = site, S

    def link(self, e: Entity) -> str:
        return f'<a href="../{e.kind}/{e.pid}/">{esc(e.name)}</a>'

    def ref_link(self, r: extract.Ref) -> str:
        return f'<a href="{attr(r.href)}">{esc(r.name)}</a>' if r.href else esc(r.name)

    def status_words(self, statuses: list[str]) -> str:
        if not statuses:
            return self.S.t("status.none")
        return ", ".join(display.t_opt(self.S.t, f"status.{s}", s) for s in statuses)

    def status(self, statuses: list[str]) -> str:
        cls = f"status-{attr(statuses[0])}" if statuses else "status-none"
        return f'<span class="status {cls}">{html.escape(self.S.t("status.label", value=self.status_words(statuses)))}</span>'

    def coverage_word(self, key: str | None, label: str | None) -> str:
        return display.t_opt(self.S.t, f"coverage.{key}", label or self.S.t("common.not_recorded"))

    def coverage(self, key: str | None, label: str | None) -> str:
        word = self.coverage_word(key, label)
        return (f'<span class="status coverage-{attr(key or "none")}">'
                f'{html.escape(self.S.t("coverage.label", value=word))}</span>')

    def lst(self, items: list[str], cls: str = "ix-facts") -> str:
        return f'<ul class="{cls}">' + "".join(f"<li>{i}</li>" for i in items if i) + "</ul>"

    def date(self, ext: dict) -> dict:
        """display.format_extent, with the sign after every mention of the Prophet in the
        recorded text (maintainer: honorifics on every mention)."""
        fx = display.format_extent(ext, self.S.t)
        return {"text": display.honour(fx["text"]) if fx["text"] else fx["text"],
                "notes": [display.honour(n) for n in fx["notes"]]}

    def notes(self, fx: dict, rec: dict) -> list[str]:
        """The display notes of a date, less the two this page says more fully itself: that
        it is disputed (with the questions) and that it is relative (with the anchors)."""
        drop = {self.S.t("date.disputed")}
        if rec["anchors"]:
            drop.add(self.S.t("date.relative"))
        return [n for n in fx["notes"] if n and n not in drop]

    def drawn(self, ext: dict) -> str:
        """The recorded bounds a bar spans, written out to the day (never narrowed)."""
        return display.bounds_text(ext.get("earliest"), ext.get("latest"), "day", self.S.t) or ""

    def year(self, y: int) -> str:
        return f'{y} {self.S.t("date.ce")}'


def wider_than_precision(ext: dict, start: float, end: float) -> bool:
    limit = {"day": 1.0, "month": 31.0, "year": 366.0}.get(ext.get("precision") or "")
    return limit is not None and (end - start) > limit + 0.001


def year_of(iso: str) -> int:
    """The year of a stored ISO date ("0624-03-13" -> 624)."""
    return -int(iso[1:].split("-")[0]) if iso.startswith("-") else int(iso.split("-")[0])


def app_div(S: Strings) -> str:
    """The container the script draws into; without JavaScript it points to the text version."""
    return (f'<div id="ix-app" class="ix-app" data-src="data.json" data-loading="{attr(S.t("ix.app.loading"))}" '
            f'data-failed="{attr(S.t("ix.app.failed"))}"><p class="ix-nojs">{html.escape(S.t("ix.app.nojs"))}</p></div>')


# ------------------------------------------------------------------------------ timeline
def disputes_of(site: Site, e: Entity) -> list[dict]:
    """Disputes whose subject is the entity, with the significance key (sig_...)."""
    from rdflib import URIRef
    from model import MRS
    g = site.g
    out = []
    for d in g.subjects(MRS.disputeSubject, URIRef(e.iri)):
        q = site.first_lit(d, MRS.disputeQuestion)
        out.append({"question": q.text if q else None,
                     "significance": site.vkey(g.value(d, MRS.disputeSignificance), "sig_")})
    return sorted(out, key=lambda d: (d["significance"] or "", d["question"] or ""))


def span_view(site: Site, P: Pieces, span: dict) -> dict:
    """One placed span: its data for the drawing and its HTML for the text version."""
    S = P.S
    e, rec = span["entity"], span["rec"]
    ext = rec["ext"]
    fx = P.date(ext)
    ent_id = extract.entity_id(e)
    item_id = ent_id + (f"~{span['n']}" if span["of"] > 1 else "")
    href = f"../{e.kind}/{e.pid}/"
    ev_disputes = disputes_of(site, e) if span["role"] == "event" else []
    date_disputes = list(rec["disputes"]) + [d["question"] for d in ev_disputes
                                             if d["significance"] == "chronological" and d["question"]]
    disputed = bool(ext.get("disputed") or ext.get("basis") == "disputed" or date_disputes)
    other_questions = [d for d in ev_disputes if d["significance"] != "chronological"]
    has_dispute_section = bool(e.data.get("disputes"))

    date_html = esc(fx["text"]) if fx["text"] else html.escape(S.t("common.not_recorded"))
    if span["role"] == "death":
        date_html = S.th("ix.tl.died", date=date_html)
    facts = [S.th("ix.info.drawn", range=esc(P.drawn(ext)))]
    facts += [esc(n) for n in P.notes(fx, rec)]
    if wider_than_precision(ext, span["start"], span["end"]):
        facts.append(html.escape(S.t("ix.info.wider", precision=display.t_opt(
            S.t, f"precision.{ext['precision']}", ext["precision"]))))
    if span["of"] > 1:
        facts.append(html.escape(S.t("ix.info.several_dates", n=span["n"], of=span["of"])))
    for a in rec["anchors"]:
        facts.append(anchor_html(P, a))
    if disputed:
        qs = "".join(f"<li>{esc(q)}</li>" for q in date_disputes)
        more = (f' <a href="{href}#s-disputes">{html.escape(S.t("ix.info.see_questions"))}</a>'
                if has_dispute_section else "")
        facts.append(f'<strong class="ix-disputed">{html.escape(S.t("ix.info.disputed"))}</strong>{more}'
                     + (f'<ul class="ix-questions">{qs}</ul>' if qs else ""))
    if other_questions:
        facts.append(S.thn("ix.info.other_questions", len(other_questions),
                           link=f'<a href="{href}#s-disputes">{html.escape(S.t("ix.info.see_questions"))}</a>'
                           if has_dispute_section else ""))
    facts.append(P.status(rec["statuses"]) + " " + P.coverage(e.coverage, e.coverage_label))
    if span["places"]:
        links = ", ".join(P.link(site.entity(p)) if site.entity(p) else esc(site.label_of(p)) for p in span["places"])
        facts.append(S.th("ix.info.where", places=links))
    people = [x for x in span["linked"] if x != ent_id and x.split("/", 1)[0] in ("person", "group")]
    if span["role"] == "event" and people:
        facts.append(S.thn("ix.info.linked", len(people)))
    info = f'<p class="ix-date">{date_html}</p>' + P.lst(facts)

    basis = ext.get("basis") or "none"
    title = " — ".join(x for x in (e.name, fx["text"], S.t("status.label", value=P.status_words(rec["statuses"]))) if x)
    return {
        "id": item_id, "entity": ent_id, "kind": e.kind, "role": span["role"],
        "href": href, "name_html": esc(e.name), "name": e.name, "title": title, "date_html": date_html,
        "status_html": P.status(rec["statuses"]),
        "basis": basis, "basis_text": html.escape(S.t("date.basis", value=display.t_opt(S.t, f"basis.{basis}", basis)))
        if ext.get("basis") else "",
        "disputed": disputed, "conv": int(ext["conv_days"]) if (ext.get("conv_days") or "").isdigit() else 0,
        "start": span["start"], "end": span["end"],
        "earliest": extract.iso_date(ext.get("earliest")), "latest": extract.iso_date(ext.get("latest")),
        "precision": ext.get("precision"), "calendar": ext.get("calendar"), "native": ext.get("native"),
        "statuses": rec["statuses"], "coverage": e.coverage,
        "linked": span["linked"], "places": [extract.entity_id(site.entity(p)) for p in span["places"] if site.entity(p)],
        "info_html": info,
    }


def anchor_html(P: Pieces, a: dict) -> str:
    S = P.S
    rel = display.t_opt(S.t, f"ix.allen.{a['relation'].lower()}", a["relation"]) \
        if a["relation"] else S.t("common.not_recorded")
    target = P.ref_link(a["target"]) if a["target"] else html.escape(S.t("common.not_recorded"))
    return S.th("ix.info.anchor", relation=html.escape(rel), target=target, status=P.status(a["statuses"]))


def timeline_page(site: Site, S: Strings, P: Pieces, R: Renderer, tl: dict) -> tuple[str, dict]:
    spans = tl["spans"]
    items = [span_view(site, P, s) for s in spans]
    events = [i for i in items if i["role"] == "event"]
    deaths = [i for i in items if i["role"] == "death"]
    np_ = tl["not_placed"]

    # axis: whole Julian-calendar years around everything placed
    y0 = min(year_of(i["earliest"]) for i in items) if items else 600
    y1 = max(year_of(i["latest"]) for i in items) if items else 700
    start, end = float(extract.jdn_julian(y0, 1, 1)), float(extract.jdn_julian(y1 + 1, 1, 1))
    ce = [{"x": float(extract.jdn_julian(y, 1, 1)), "y": y} for y in range(y0, y1 + 2)]
    ah = []
    if HIJRI_AXIS:
        n = 1
        while extract.muharram_first(n) <= end:
            x = float(extract.muharram_first(n))
            if x >= start:
                ah.append({"x": x, "y": n})
            n += 1

    # focus: people, groups and places that placed items link to
    focus = focus_index(site, items, spans, tl, kinds=("person", "group", "place"))

    data = {
        "view": "timeline",
        "axis": {"start": start, "end": end, "first_year": y0, "last_year": y1, "ce": ce, "ah": ah,
                 "ce_label": S.t("date.ce"), "ah_label": S.t("date.ah")},
        "items": items, "focus": focus,
        "strings": js_strings(S, "timeline"),
    }

    # ---------------------------------------------------------------- HTML
    alt = text_version_timeline(S, P, events, deaths, tl, y0, y1)
    unplaced = unplaced_html(site, S, P, np_)
    legend = timeline_legend(S, items)
    body = f"""<article class="ix ix-timeline" data-view="timeline">
<h1>{html.escape(S.t("ix.timeline.title"))}</h1>
<p class="lead">{html.escape(S.t("ix.timeline.lead"))}</p>
{banner(site, S)}
<section class="ix-view" aria-labelledby="ix-view-h">
<h2 id="ix-view-h">{html.escape(S.t("ix.timeline.view_heading"))}</h2>
{app_div(S)}
{legend}
</section>
{alt}
{unplaced}
{about_timeline(S)}
</article>"""
    page = shell(R, S, "timeline", body, S.t("ix.timeline.lead"))
    return page, data


def focus_index(site: Site, items: list[dict], spans: list[dict], tl: dict, kinds) -> list[dict]:
    """Who and where the drawn items link to, with how many linked items are not placed."""
    placed_entities = {s["entity"].iri for s in spans if s["role"] == "event"}
    by = {}
    for it in items:
        for x in set(it["linked"]) | set(it["places"]):
            by.setdefault(x, []).append(it["id"])
    out = []
    for x, ids in by.items():
        kind, pid = x.split("/", 1)
        if kind not in kinds:
            continue
        e = next((y for y in site.by_kind[kind] if y.pid == pid), None)
        if e is None:
            continue
        linked_events = set()
        for c in site.claims.get(e.iri, []):
            other = c.object if c.subject == e.iri else c.subject
            oe = site.entity(other)
            if oe is not None and oe.kind in ("event", "story"):
                linked_events.add(oe.iri)
        if kind == "place":
            linked_events |= {y.iri for y in site.by_kind["event"] + site.by_kind["story"]
                              if e.iri in (y.data.get("places") or [])}
        unplaced = len([i for i in linked_events if i not in placed_entities])
        out.append({"id": x, "kind": kind, "name": e.name, "items": sorted(set(ids)), "unplaced": unplaced})
    order = {k: i for i, k in enumerate(kinds)}
    out.sort(key=lambda f: (order[f["kind"]], display.sort_key(f["name"]), f["id"]))
    return out


def banner(site: Site, S: Strings) -> str:
    sc = site.status_counts()
    cc = site.coverage_counts()
    if sc.get("accepted") or cc.get("reviewed") or cc.get("verified"):
        return f'<p class="banner" role="note">{html.escape(S.t("ix.banner.some"))}</p>'
    return f'<p class="banner" role="note"><strong>{html.escape(S.t("ix.banner.none"))}</strong></p>'


def timeline_legend(S: Strings, items: list[dict]) -> str:
    """Generated from the items: only what the drawing actually uses is explained."""
    rows = []
    for role, kind in (("event", "event"), ("death", "person")):
        if any(i["role"] == role for i in items):
            rows.append(f'<li><span class="sw tl-bar kind-{kind}" aria-hidden="true"></span>'
                        f'{html.escape(S.t("ix.legend.kind." + role))}</li>')
    present = []  # a disputed date is drawn with the dashed outline, explained below
    for b in ("attested", "conventional", "inferred", "computed", "none"):
        if any(i["basis"] == b and not i["disputed"] for i in items):
            present.append(b)
    for b in present:
        word = display.t_opt(S.t, f"basis.{b}", b) if b != "none" else S.t("common.not_recorded")
        rows.append(f'<li><span class="sw tl-bar basis-{b}" aria-hidden="true"></span>'
                    f'{html.escape(S.t("ix.legend.basis", value=word))}</li>')
    if any(i["disputed"] for i in items):
        rows.append(f'<li><span class="sw tl-bar is-disputed" aria-hidden="true"></span>'
                    f'{html.escape(S.t("ix.legend.disputed"))}</li>')
    if any(i["conv"] for i in items):
        rows.append(f'<li><span class="sw sw-whisker" aria-hidden="true"></span>'
                    f'{html.escape(S.t("ix.legend.converted"))}</li>')
    rows.append(f'<li><span class="sw sw-min" aria-hidden="true"></span>{html.escape(S.t("ix.legend.min_width"))}</li>')
    return (f'<div class="ix-legend"><p class="ix-legend-lead">{html.escape(S.t("ix.legend.bar"))}</p>'
            f'<ul class="ix-legend-list">{"".join(rows)}</ul></div>')


def alt_entry(i: dict) -> str:
    anchor = "alt-" + i["id"].replace("/", "-").replace("~", "-")
    return (f'<li id="{attr(anchor)}" data-id="{attr(i["id"])}"><a class="ix-alt-name" href="{attr(i["href"])}">'
            f'{i["name_html"]}</a>{i["info_html"]}</li>')


def text_version_timeline(S: Strings, P: Pieces, events, deaths, tl, y0, y1) -> str:
    np_ = tl["not_placed"]
    n_np = sum(len(v) for v in np_.values())
    scene = [S.t("ix.tl.scene.span", start=P.year(y0), end=P.year(y1)),
             S.tn("ix.tl.scene.events", len(events)),
             S.tn("ix.tl.scene.deaths", len(deaths)),
             S.t("ix.tl.scene.bars"),
             S.t("ix.tl.scene.status"),
             S.tn("ix.tl.scene.unplaced", n_np)]
    out = [f'<section class="ix-text" id="ix-text" aria-labelledby="ix-text-h">',
           f'<h2 id="ix-text-h">{html.escape(S.t("ix.text.heading"))}</h2>',
           f'<p class="ix-scene">{html.escape(" ".join(scene))}</p>']
    for key, group in (("events", events), ("deaths", deaths)):
        if not group:
            continue
        out.append(f'<h3 id="ix-alt-{key}-h">{html.escape(S.tn("ix.tl.alt." + key, len(group)))}</h3>')
        out.append(f'<ol class="ix-alt" data-group="{key}" aria-labelledby="ix-alt-{key}-h">'
                   + "".join(alt_entry(i) for i in group) + "</ol>")
    out.append("</section>")
    return "\n".join(out)


def unplaced_html(site: Site, S: Strings, P: Pieces, np_: dict) -> str:
    groups = []
    rel = np_.get("relative", [])
    if rel:
        lis = []
        for it in sorted(rel, key=lambda x: (x["entity"].kind, display.sort_key(x["entity"].name))):
            e, ext = it["entity"], it["rec"]["ext"]
            fx = P.date(ext)
            bits = [P.link(e)]
            if it["role"] == "death":
                bits.append(S.th("ix.tl.died", date=esc(fx["text"]) if fx["text"] else html.escape(S.t("common.not_recorded"))))
            elif fx["text"]:
                bits.append(f'<span class="date">{esc(fx["text"])}</span>')
            facts = [anchor_html(P, a) for a in it["rec"]["anchors"]]
            facts += [esc(n) for n in P.notes(fx, it["rec"])]
            if it["rec"]["disputes"] or ext.get("disputed") or ext.get("basis") == "disputed":
                facts.append(f'<strong class="ix-disputed">{html.escape(S.t("ix.info.disputed"))}</strong>'
                             + ('<ul class="ix-questions">' + "".join(f"<li>{esc(q)}</li>" for q in it["rec"]["disputes"]) + "</ul>"
                                if it["rec"]["disputes"] else ""))
            facts.append(P.status(it["rec"]["statuses"]) + " " + P.coverage(e.coverage, e.coverage_label))
            lis.append(f'<li data-id="{attr(extract.entity_id(e))}">' + " ".join(bits) + P.lst(facts) + "</li>")
        groups.append(("relative", len(rel), "".join(lis)))
    for reason in ("one_bound", "inconsistent"):
        lst = np_.get(reason, [])
        if lst:
            lis = []
            for it in lst:
                fx = P.date(it["rec"]["ext"])
                lis.append(f'<li data-id="{attr(extract.entity_id(it["entity"]))}">{P.link(it["entity"])} '
                           f'<span class="date">{esc(fx["text"] or "")}</span></li>')
            groups.append((reason, len(lst), "".join(lis)))
    nd = np_.get("no_date", [])
    for kind in ("event", "story", "person", "group"):
        ents = [it["entity"] for it in nd if it["entity"].kind == kind]
        if not ents:
            continue
        if kind == "story":
            ents.sort(key=lambda x: (x.data.get("number") is None, x.data.get("number") or 0, x.name))
        else:
            ents.sort(key=lambda x: (display.sort_key(x.name), x.pid))
        lis = "".join(f'<li data-id="{attr(extract.entity_id(x))}">{P.link(x)}</li>' for x in ents)
        groups.append((f"no_date_{kind}", len(ents), lis))
    out = [f'<section class="ix-unplaced" id="ix-unplaced" aria-labelledby="ix-unplaced-h">',
           f'<h2 id="ix-unplaced-h">{html.escape(S.t("ix.tl.unplaced.heading"))}</h2>',
           f'<p>{html.escape(S.t("ix.tl.unplaced.lead"))}</p>']
    for key, n, lis in groups:
        title = html.escape(S.tn(f"ix.tl.unplaced.{key}", n))
        tag = "ol" if key == "no_date_story" else "ul"
        lst = f'<{tag} class="ix-list ix-list-{key}">{lis}</{tag}>'
        if n > LONG_LIST:
            out.append(f'<details class="ix-fold"><summary><h3 class="ix-inline-h">{title}</h3></summary>{lst}</details>')
        else:
            out.append(f"<h3>{title}</h3>{lst}")
    out.append("</section>")
    return "\n".join(out)


def about_timeline(S: Strings) -> str:
    paras = [S.t("ix.tl.about.bars"), S.t("ix.tl.about.status"), S.t("ix.tl.about.people")]
    if HIJRI_AXIS:
        paras.append(S.t("ix.tl.about.ah_axis"))
    paras.append(S.t("ix.about.data"))
    return (f'<section class="ix-about" aria-labelledby="ix-about-h"><h2 id="ix-about-h">'
            f'{html.escape(S.t("ix.about.heading"))}</h2>'
            + "".join(f"<p>{html.escape(p)}</p>" for p in paras)
            + f'<p><a href="data.json">{html.escape(S.t("ix.about.download"))}</a></p></section>')


# ------------------------------------------------------------------------------ map
def coord_text(S: Strings, lon: float, lat: float, wkt: str) -> str:
    m = extract._POINT.match(wkt)
    lon_s, lat_s = (m.group(1), m.group(2)) if m else (repr(lon), repr(lat))
    ns = S.t("ix.coord.lat_n" if lat >= 0 else "ix.coord.lat_s", value=lat_s.lstrip("-"))
    ew = S.t("ix.coord.lon_e" if lon >= 0 else "ix.coord.lon_w", value=lon_s.lstrip("-"))
    return S.t("ix.info.coords", lat=ns, lon=ew)


def place_view(site: Site, S: Strings, P: Pieces, pl: dict, at_place: dict, span_ids: dict) -> dict:
    e, pt = pl["entity"], pl["point"]
    ent_id = extract.entity_id(e)
    item_id = ent_id + (f"~{pl['n']}" if pl["of"] > 1 else "")
    loc = [x for x in (pt["confidence_label"],) if x]
    loc_text = " · ".join(loc + ([S.t("location.basis", value=pt["basis_label"])] if pt["basis_label"] else []))
    facts = [html.escape(S.t("ix.info.location", value=loc_text or S.t("common.not_recorded"))),
             html.escape(coord_text(S, pt["lon"], pt["lat"], pt["wkt"]))]
    for v in pt["valid"]:
        fx = P.date(v)
        if fx["text"]:
            facts.append(S.th("ix.info.valid", value=esc(fx["text"])))
    if pl["of"] > 1:
        facts.append(html.escape(S.t("ix.info.several_points", n=pl["n"], of=pl["of"])))
    facts.append(P.status(pt["statuses"]) + " " + P.coverage(e.coverage, e.coverage_label))
    evs = at_place.get(e.iri, [])
    linked, ev_ids, spans = set(), [], []
    if evs:
        lis = []
        for x in evs:
            ee = x["entity"]
            when = ""
            if x["spans"]:
                fx = P.date(x["spans"][0]["rec"]["ext"])
                when = f' <span class="date">{esc(fx["text"])}</span>' if fx["text"] else ""
                for s in x["spans"]:
                    spans.append({"item": span_ids[id(s)], "start": s["start"], "end": s["end"]})
            else:
                when = f' <span class="not-recorded">{html.escape(S.t("ix.info.no_date"))}</span>'
            lis.append(f"<li>{P.link(ee)}{when}</li>")
            ev_ids.append(extract.entity_id(ee))
            for c in site.claims.get(ee.iri, []):
                other = c.object if c.subject == ee.iri else c.subject
                oe = site.entity(other)
                if oe is not None and oe.kind in ("person", "group"):
                    linked.add(extract.entity_id(oe))
        facts.append(S.thn("ix.info.events_here", len(evs)) + f'<ul class="ix-events">{"".join(lis)}</ul>')
    else:
        facts.append(html.escape(S.t("ix.info.no_events_here")))
    arabic = "".join(f' <span class="name-ar" lang="ar" dir="rtl">{html.escape(a, quote=False)}</span>' for a in e.arabic)
    title = " — ".join([e.name, loc_text, S.t("status.label", value=P.status_words(pt["statuses"]))])
    return {
        "id": item_id, "entity": ent_id, "href": f"../{e.kind}/{e.pid}/", "name": e.name,
        "name_html": esc(e.name), "arabic_html": arabic.strip(),
        "lon": pt["lon"], "lat": pt["lat"], "wkt": pt["wkt"],
        "confidence": pt["confidence"] or "none", "basis": pt["basis"] or "none",
        "statuses": pt["statuses"], "coverage": e.coverage, "title": title,
        "events": ev_ids, "spans": spans, "linked": sorted(linked),
        "info_html": P.lst(facts),
    }


def segment_view(S: Strings, P: Pieces, route: dict, seg: dict, n_segs: int) -> dict:
    sid = f"route/{route['pid']}/{seg['order'] if seg['order'] is not None else 'x'}"
    anchor = "seg-" + sid.replace("/", "-")
    frm = P.ref_link(seg["from"]) if seg["from"] else html.escape(S.t("common.not_recorded"))
    to = P.ref_link(seg["to"]) if seg["to"] else html.escape(S.t("common.not_recorded"))
    head = S.th("ix.seg.head", order=html.escape(str(seg["order"] or "?")), n=str(n_segs),
                route=esc(display.name_display(route["label"])), frm=frm, to=to)
    conf = seg["confidence_label"] or S.t("common.not_recorded")
    facts = [html.escape(S.t("ix.seg.confidence", value=conf))]
    if seg["mode"]:
        facts.append(html.escape(S.t("ix.seg.mode", value=seg["mode"])))
    if seg["line"]:
        facts.append(html.escape(S.tn("ix.seg.drawn", len(seg["line"]), wkt=seg["wkt"])))
    else:
        facts.append(f'<strong>{html.escape(S.t("ix.seg.not_drawn." + seg["reason"]))}</strong>')
    for x in seg["traversal"]:
        fx = P.date(x)
        if fx["text"]:
            facts.append(S.th("ix.seg.when", value=esc(fx["text"])))
    for q in seg["disputes"]:
        facts.append(S.th("ix.seg.dispute", question=esc(q)))
    facts.append(P.status(seg["statuses"]) + " " + P.coverage(route["coverage"], route["coverage_label"]))
    title =" — ".join([display.name_display(route["label"]), S.t("ix.seg.confidence", value=conf),
                        S.t("status.label", value=P.status_words(seg["statuses"]))])
    return {"id": sid, "anchor": anchor, "href": f"#{anchor}", "order": seg["order"],
            "confidence": seg["confidence"] or "none", "drawn": bool(seg["line"]),
            "line": [[x, y] for x, y in seg["line"]] if seg["line"] else None,
            "from": seg["from"].id if seg["from"] else None, "to": seg["to"].id if seg["to"] else None,
            "title": title, "head_html": head, "info_html": P.lst(facts)}


def map_page(site: Site, S: Strings, P: Pieces, R: Renderer, tl: dict, tl_items: list[dict]) -> tuple[str, dict]:
    pl = extract.places(site)
    rts = extract.routes(site)
    span_ids = {}
    for s, it in zip(tl["spans"], tl_items):
        span_ids[id(s)] = it["id"]
    at_place = extract.events_at_places(site, tl["spans"])
    marks = [place_view(site, S, P, p, at_place, span_ids) for p in pl["plotted"]]
    routes_v = []
    for r in rts:
        segs = [segment_view(S, P, r, s, len(r["segments"])) for s in r["segments"]]
        routes_v.append({"id": f"route/{r['pid']}", "name_html": esc(display.name_display(r["label"])),
                         "coverage": r["coverage"], "segments": segs})
    basemap = json.loads((HERE / "data" / "basemap.json").read_text(encoding="utf-8"))

    # where events are recorded, for the coverage line
    plotted_iris = {p["entity"].iri for p in pl["plotted"]}
    ev_at_plotted = ev_elsewhere = ev_none = 0
    for e in site.by_kind["event"] + site.by_kind["story"]:
        ps = e.data.get("places") or []
        if not ps:
            ev_none += 1
        elif any(p in plotted_iris for p in ps):
            ev_at_plotted += 1
        else:
            ev_elsewhere += 1

    focus = map_focus(site, marks)
    years = [it for it in tl_items if it["role"] == "event"]
    y0 = min((year_of(i["earliest"]) for i in years), default=None)
    y1 = max((year_of(i["latest"]) for i in years), default=None)
    data = {
        "view": "map",
        "places": marks, "routes": routes_v, "focus": focus,
        "years": {"first": y0, "last": y1,
                  "starts": {str(y): float(extract.jdn_julian(y, 1, 1)) for y in range(y0, y1 + 2)} if y0 else {}},
        "basemap": {"source": basemap["source"], "rings": basemap["layers"]["land"]["rings"],
                    "bbox": basemap["layers"]["land"]["bbox"]},
        "strings": js_strings(S, "map"),
    }
    alt = text_version_map(S, P, marks, routes_v, pl, (ev_at_plotted, ev_elsewhere, ev_none))
    legend = map_legend(S, marks, routes_v)
    body = f"""<article class="ix ix-map" data-view="map">
<h1>{html.escape(S.t("ix.map.title"))}</h1>
<p class="lead">{html.escape(S.t("ix.map.lead"))}</p>
{banner(site, S)}
<section class="ix-view" aria-labelledby="ix-view-h">
<h2 id="ix-view-h">{html.escape(S.t("ix.map.view_heading"))}</h2>
{app_div(S)}
{legend}
</section>
{alt}
{about_map(S, basemap["source"])}
</article>"""
    page = shell(R, S, "map", body, S.t("ix.map.lead"))
    return page, data


def map_focus(site: Site, marks: list[dict]) -> list[dict]:
    by: dict[str, set] = {}
    for m in marks:
        for x in m["linked"]:
            by.setdefault(x, set()).add(m["id"])
    out = []
    for x, ids in by.items():
        kind, pid = x.split("/", 1)
        e = next((y for y in site.by_kind[kind] if y.pid == pid), None)
        if e is not None:
            out.append({"id": x, "kind": kind, "name": e.name, "items": sorted(ids)})
    order = {"person": 0, "group": 1}
    out.sort(key=lambda f: (order.get(f["kind"], 9), display.sort_key(f["name"]), f["id"]))
    return out


def map_legend(S: Strings, marks: list[dict], routes_v: list[dict]) -> str:
    rows, seen = [], set()
    for m in marks:
        key = (m["confidence"], m["basis"])
        if key in seen:
            continue
        seen.add(key)
        conf = display.t_opt(S.t, f"ix.lc.{m['confidence']}", m["confidence"])
        basis = display.t_opt(S.t, f"ix.gb.{m['basis']}", m["basis"])
        rows.append(f'<li><svg class="sw-mk" viewBox="-8 -8 16 16" aria-hidden="true" focusable="false">'
                    f'<use href="#ix-sym-{attr(m["basis"])}" class="mk-shape conf-{attr(m["confidence"])}"></use></svg>'
                    f'{html.escape(S.t("ix.legend.place", confidence=conf, basis=basis))}</li>')
    segs = [s for r in routes_v for s in r["segments"]]
    for conf in ("attested", "probable", "conjectural"):
        if any(s["drawn"] and s["confidence"] == conf for s in segs):
            rows.append(f'<li><span class="sw sw-seg seg-{conf}" aria-hidden="true"></span>'
                        f'{html.escape(S.t("ix.legend.segment." + conf))}</li>')
    if any(not s["drawn"] for s in segs):
        rows.append(f'<li><span class="sw sw-gap" aria-hidden="true"></span>{html.escape(S.t("ix.legend.segment_gap"))}</li>')
    symbols = "".join(
        f'<symbol id="ix-sym-{b}" viewBox="-8 -8 16 16"><path d="{d}"></path></symbol>'
        for b, d in MARK_SHAPES.items())
    defs = f'<svg class="ix-defs" aria-hidden="true" focusable="false"><defs>{symbols}</defs></svg>'
    return (f'<div class="ix-legend">{defs}<p class="ix-legend-lead">{html.escape(S.t("ix.legend.map"))}</p>'
            f'<ul class="ix-legend-list">{"".join(rows)}</ul></div>')


# One shape per geometry basis (how the location was identified), so that "traditional" never
# looks like "modern identification" (ontology: mrs:GeometryBasis). Fill and outline show the
# location confidence. Abstract geometry only.
MARK_SHAPES = {
    "modern_identification": "M0,-5.5A5.5,5.5 0 1,1 0,5.5A5.5,5.5 0 1,1 0,-5.5Z",
    "traditional": "M0,-6.5L6.5,0L0,6.5L-6.5,0Z",
    "archaeological": "M-5,-5H5V5H-5Z",
    "textual": "M0,-6L5.5,4.5H-5.5Z",
    "inferred": "M-5.5,-2H-2V-5.5H2V-2H5.5V2H2V5.5H-2V2H-5.5Z",
    "none": "M0,-5.5A5.5,5.5 0 1,1 0,5.5A5.5,5.5 0 1,1 0,-5.5Z",
}


def text_version_map(S: Strings, P: Pieces, marks, routes_v, pl, ev_counts) -> str:
    lat = [m["lat"] for m in marks]
    lon = [m["lon"] for m in marks]
    segs = [s for r in routes_v for s in r["segments"]]
    scene = []
    if marks:
        scene.append(S.tn("ix.map.scene.places", len(marks), south=f"{min(lat):g}", north=f"{max(lat):g}",
                          west=f"{min(lon):g}", east=f"{max(lon):g}"))
    else:
        scene.append(S.t("ix.map.scene.no_places"))
    scene.append(S.t("ix.map.scene.north"))
    scene.append(S.tn("ix.map.scene.routes", len(routes_v), drawn=sum(1 for s in segs if s["drawn"]), segments=len(segs)))
    n_off = len(pl["unlocated"]) + len(pl["no_location"]) + len(pl["other_geometry"])
    scene.append(S.tn("ix.map.scene.unplotted", n_off))
    scene.append(S.t("ix.map.scene.status"))
    scene.append(S.t("ix.map.scene.events", at=ev_counts[0], elsewhere=ev_counts[1], none=ev_counts[2]))
    out = [f'<section class="ix-text" id="ix-text" aria-labelledby="ix-text-h">',
           f'<h2 id="ix-text-h">{html.escape(S.t("ix.text.heading"))}</h2>',
           f'<p class="ix-scene">{html.escape(" ".join(scene))}</p>',
           f'<h3 id="ix-alt-places-h">{html.escape(S.tn("ix.map.alt.places", len(marks)))}</h3>',
           '<ol class="ix-alt" data-group="places" aria-labelledby="ix-alt-places-h">'
           + "".join(f'<li id="alt-{attr(m["id"].replace("/", "-").replace("~", "-"))}" data-id="{attr(m["id"])}">'
                     f'<a class="ix-alt-name" href="{attr(m["href"])}">{m["name_html"]}</a>'
                     f'{(" " + m["arabic_html"]) if m["arabic_html"] else ""}{m["info_html"]}</li>' for m in marks)
           + "</ol>"]
    for r in routes_v:
        out.append(f'<h3>{S.th("ix.map.alt.route", route=r["name_html"])}</h3>')
        out.append(f'<p>{html.escape(S.t("ix.info.segment_field"))}</p>')
        out.append('<ol class="ix-alt ix-segments" data-group="segments">' + "".join(
            f'<li id="{attr(s["anchor"])}" data-id="{attr(s["id"])}" data-drawn="{"1" if s["drawn"] else "0"}">'
            f'<p class="ix-seg-head">{s["head_html"]}</p>{s["info_html"]}</li>' for s in r["segments"]) + "</ol>")
    out.append(f'<h3 id="ix-off-h">{html.escape(S.t("ix.map.off.heading"))}</h3>')
    for key in ("unlocated", "no_location", "other_geometry"):
        lst = pl[key]
        if not lst:
            continue
        lis = "".join(f'<li data-id="{attr(extract.entity_id(x["entity"]))}">{P.link(x["entity"])}</li>' for x in lst)
        out.append(f'<h4>{html.escape(S.tn("ix.map.off." + key, len(lst)))}</h4><ul class="ix-list">{lis}</ul>')
    out.append("</section>")
    return "\n".join(out)


def about_map(S: Strings, source: dict) -> str:
    link = f'<a href="{attr(source["licence_url"])}">{html.escape(S.t("ix.map.about.licence"))}</a>'
    paras = [html.escape(S.t("ix.map.about.marks")), html.escape(S.t("ix.map.about.routes")),
             html.escape(S.t("ix.map.about.status")), html.escape(S.t("ix.map.about.projection")),
             S.th("ix.map.about.basemap", source=html.escape(source["name"]), licence=link),
             html.escape(S.t("ix.about.data"))]
    return (f'<section class="ix-about" aria-labelledby="ix-about-h"><h2 id="ix-about-h">'
            f'{html.escape(S.t("ix.about.heading"))}</h2>' + "".join(f"<p>{p}</p>" for p in paras)
            + f'<p><a href="data.json">{html.escape(S.t("ix.about.download"))}</a></p></section>')


# ------------------------------------------------------------------------------ frame and output
def shell(R: Renderer, S: Strings, view: str, body: str, description: str) -> str:
    title = S.t(f"ix.{view}.title")
    page = R.shell(Ctx(f"{view}/"), R.page_title(title), body, body_class=f"page-interactive view-{view}",
                   current=None, crumbs=[(title, None)], description=description)
    head = ('<link rel="stylesheet" href="interactive.css">\n'
            '<script src="common.js" defer></script>\n'
            f'<script src="{view}.js" defer></script>\n</head>')
    return page.replace("</head>", head, 1)


# Keys the scripts use; written into each data.json so the scripts hold no UI text.
JS_KEYS = {
    "common": ("ix.ctl.focus", "ix.ctl.focus_none", "ix.ctl.focus_group.person", "ix.ctl.focus_group.group",
               "ix.ctl.focus_group.place", "ix.ctl.year", "ix.ctl.year_off", "ix.ctl.year_value",
               "ix.ctl.year_clear"),
    "timeline": ("ix.ctl.window_summary", "ix.ctl.from", "ix.ctl.to", "ix.ctl.reset", "ix.ctl.to_map", "ix.ctl.details",
                 "ix.ctl.details_for", "ix.tl.band.events", "ix.tl.band.deaths", "ix.tl.chart_label",
                 "ix.tl.axis_label", "ix.summary.window", "ix.summary.hidden.one", "ix.summary.hidden.other",
                 "ix.summary.year.one", "ix.summary.year.other", "ix.summary.focus_tl"),
    "map": ("ix.ctl.zoom", "ix.ctl.zoom_in", "ix.ctl.zoom_out", "ix.ctl.zoom_fit", "ix.ctl.zoom_fit_long",
            "ix.ctl.zoom_region", "ix.ctl.zoom_region_long",
            "ix.ctl.to_timeline", "ix.map.scale", "ix.map.chart_label", "ix.map.zoom_value", "ix.map.attrib",
            "ix.map.panel_label", "ix.map.panel_empty", "ix.map.open", "ix.map.open_segment", "ix.map.on_timeline",
            "ix.summary.focus_map", "ix.summary.year_map"),
}


def js_strings(S: Strings, view: str) -> dict:
    return {k: S.t(k) for k in JS_KEYS["common"] + JS_KEYS[view]}


def weigh(out: Path, view: str) -> dict[str, int]:
    """Bytes a view's page loads before any user action: the page, its stylesheets and
    scripts, and the data.json its script fetches."""
    d = out / view
    files = {f"{view}/index.html": d / "index.html", "assets/site.css": out / "assets" / "site.css"}
    for name in SHARED + (f"{view}.js", "data.json"):
        files[f"{view}/{name}"] = d / name
    return {k: v.stat().st_size for k, v in files.items() if v.is_file()}


def build(graph: Path, out: Path, quiet: bool = False) -> dict:
    if not graph.exists():
        subprocess.run([sys.executable, str(ROOT / "ontology" / "build_graph.py")], check=True, cwd=ROOT)
    if not (out / MARKER).exists():
        if not quiet:
            print(f"{out} has no reader pages; running site/build.py first", file=sys.stderr)
        subprocess.run([sys.executable, str(SITE / "build.py"), "--graph", str(graph), "--out", str(out)],
                       check=True, cwd=ROOT, stdout=subprocess.DEVNULL if quiet else None)
    site = Site(graph)
    reader = I18n(SITE / "i18n" / "en.json")
    S = Strings(HERE / "i18n" / "en.json", reader)
    glossary = Glossary(SITE / "data" / "glossary.json", site.all_graph_labels(), site.vocabulary_labels())
    R = Renderer(site, glossary, reader, SITE / "templates")
    P = Pieces(site, S)

    tl = extract.timeline(site)
    tl_page, tl_data = timeline_page(site, S, P, R, tl)
    map_html, map_data = map_page(site, S, P, R, tl, tl_data["items"])

    for view, page, data in (("timeline", tl_page, tl_data), ("map", map_html, map_data)):
        d = out / view
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        (d / "index.html").write_text(page, encoding="utf-8")
        (d / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n",
                                     encoding="utf-8")
        for name in SHARED + (f"{view}.js",):
            shutil.copyfile(STATIC / name, d / name)

    np_ = tl["not_placed"]
    summary = {
        "timeline": {"placed_events": sum(1 for i in tl_data["items"] if i["role"] == "event"),
                     "placed_people": sum(1 for i in tl_data["items"] if i["role"] == "death"),
                     "not_placed": {k: len(v) for k, v in sorted(np_.items())}},
        "map": {"places": len(map_data["places"]),
                "segments_drawn": sum(1 for r in map_data["routes"] for s in r["segments"] if s["drawn"]),
                "segments": sum(len(r["segments"]) for r in map_data["routes"])},
        "weights": {v: sum(weigh(out, v).values()) for v in VIEWS},
        "strings_used": sorted(S.used),
    }
    if not quiet:
        t = summary["timeline"]
        print(f"timeline: {t['placed_events']} events and {t['placed_people']} people placed; not placed: "
              + ", ".join(f"{k} {v}" for k, v in t["not_placed"].items()))
        m = summary["map"]
        print(f"map: {m['places']} places plotted; route segments drawn {m['segments_drawn']} of {m['segments']}")
        for v in VIEWS:
            w = summary["weights"][v]
            print(f"  {v}/: {w:,} bytes before user action (budget {PAGE_BUDGET:,})")
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--graph", default=str(ROOT / "build" / "graph.ttl"))
    ap.add_argument("--out", default=str(SITE / "dist"))
    a = ap.parse_args(argv)
    s = build(Path(a.graph), Path(a.out))
    over = {v: w for v, w in s["weights"].items() if w > PAGE_BUDGET}
    if over:
        print(f"FAILED: over the {PAGE_BUDGET:,} byte budget: {over}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
