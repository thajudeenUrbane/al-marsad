#!/usr/bin/env python3
"""Builds the Lifelines view: one self-contained page, each person's life as a line.

    .venv/bin/python site/lifelines/build_lifelines.py [--graph build/graph.ttl]
        [--out site/dist/lifelines] [--external-dates FILE] [--reader-base ../]

Reads build/graph.ttl (through site/model.py), the proposed Wikidata dates
(ontology/corpus/external-dates.csv in the working tree, else from the fetched branch
origin/slice-5-links), and writes index.html with its CSS, script, strings and data
inline: no external request, system fonts only. The table, the legend and the list of
people with no dates are plain HTML, so the page still reads with JavaScript off.

Standalone: it does not need or change site/build.py. If site/dist does not exist yet it
is created with the marker file site/build.py looks for, so a later site build may
replace it.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
ROOT = SITE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(SITE))

import calendars as cal  # noqa: E402
import collect  # noqa: E402
import display  # noqa: E402
import lives  # noqa: E402

EXTERNAL_DATES = "ontology/corpus/external-dates.csv"
EXTERNAL_BRANCH = "slice-5-links"
IBN_HISHAM = "ontology/corpus/ibn-hisham.ttl"
IBN_HISHAM_BRANCH = "slice-4-ingest"
MERGED_GRAPH = "build/lifelines-graph.ttl"     # gitignored: the graph plus a branch's Ibn Hisham file
# canonical-ID prefix -> IRI path, for mapping renamed IDs (ontology/corpus/id-renames.csv)
ID_PATHS = {"per": "person", "ev": "event", "plc": "place", "grp": "group", "act": "activity",
            "agt": "agent", "ast": "assertion", "tmp": "temporal", "psg": "passage", "rpt": "report"}
SITE_MARKER = ".al-marsad-site"
URL_LICENSING = "https://github.com/thajudeenUrbane/al-marsad/blob/main/LICENSING.md"
URL_CC_BY_SA = "https://creativecommons.org/licenses/by-sa/4.0/"
URL_AGPL = "https://www.gnu.org/licenses/agpl-3.0.html"
MAX_BYTES = 2_000_000


class T:
    """Translator over i18n/en.json. A missing key is a build error on purpose."""

    def __init__(self, path: Path):
        self.d: dict[str, str] = json.loads(path.read_text(encoding="utf-8"))
        self.used: set[str] = set()

    def __call__(self, key: str, **kw) -> str:
        s = self.d[key]
        self.used.add(key)
        return s.format(**kw) if kw else s


def esc(s) -> str:
    return display.mark_arabic(html.escape(str(s), quote=False))


def attr(s) -> str:
    return html.escape(str(s), quote=True)


# ---------------------------------------------------------------- data
def ages_text(values: list[float], t: T) -> str:
    vals = [str(int(v)) if float(v).is_integer() else str(v) for v in values]
    if not vals:
        return ""
    return vals[0] if len(vals) == 1 else t("ih.ages_or", a=", ".join(vals[:-1]), b=vals[-1])


def ages_only_life(values: list[float]) -> dict:
    """A line placed only by ages as given (by age, never by date): from 0 to the last
    anchor, open after it. Nothing is extrapolated past the last anchor."""
    return {"b": None, "d": None, "s": None, "e": None, "segment": False, "open_start": False,
            "open_end": True, "conflict": [], "ages_only": True, "amax": max(values)}


def build_data(site, t: T, external: tuple[str | None, str | None], reader_base: str | None,
               renames: dict, ibn_hisham: str | None = None, reader_iris: set | None = None
               ) -> tuple[dict, collect.Collector]:
    text, label = external
    c = collect.Collector(site, t, ROOT, external_csv=text, external_label=label, renames=renames)
    people = sorted(c.people.values(), key=lambda p: (p.sort, p.pid))

    def link(kind: str, ent) -> str | None:
        if reader_base is None or (reader_iris is not None and ent.iri not in reader_iris):
            return None
        return f"{reader_base}{kind}/{ent.pid}/"

    # dated events each person is linked to (took part, or an age is given there)
    ev_ranges: dict[str, list[tuple[int, int]]] = {}
    for ev in c.events.values():
        if ev.lo is None:
            continue
        for part in ev.parts:
            ev_ranges.setdefault(part["person"], []).append((ev.lo, ev.hi))
    ages_by_person: dict[str, list] = {}
    for a in c.ages:
        ages_by_person.setdefault(a.person, []).append(a)
        ev = c.events[a.event]
        if ev.lo is not None:
            ev_ranges.setdefault(a.person, []).append((ev.lo, ev.hi))
    lifes = {}
    for p in people:
        rng = sorted(set(ev_ranges.get(p.iri, [])))
        base = lives.life(p.claims, rng, include_review=False)
        allv = lives.life(p.claims, rng, include_review=True)
        given = [v for a in ages_by_person.get(p.iri, []) for v in a.values]
        if given:
            base = base or ages_only_life(given)
            allv = allv or ages_only_life(given)
            for lf in (base, allv):
                if not lf.get("ages_only"):
                    lf["gmax"] = max(given)     # by age, a line with no birth date is placed by these anchors
        lifes[p.iri] = (base, allv if allv != base else None)
    drawn = [p for p in people if lifes[p.iri][0] or lifes[p.iri][1]]
    index = {p.iri: i for i, p in enumerate(drawn)}

    def claim_json(cl: collect.DateClaim) -> dict:
        return {"k": cl.kind, "lo": cl.lo, "hi": cl.hi, "t": cl.text, "nt": cl.notes,
                "src": cl.source, "rv": cl.review, "pr": cl.precision, "alt": cl.alt}

    kin_labels: dict[int, str] = {}
    for p in drawn:
        if p.kin is not None and p.kin not in kin_labels:
            members = [q for q in drawn if q.kin == p.kin]
            kin_labels[p.kin] = t("group.kin", names=", ".join(q.name for q in members[:3]),
                                  more=(t("group.more", n=len(members) - 3) if len(members) > 3 else ""))
    out_people = []
    for p in drawn:
        base, allv = lifes[p.iri]
        v = {}
        if base:
            v["b"] = base
        if allv:
            v["a"] = allv
        ties = sorted(index[q] for q in c.ties.get(p.iri, ()) if q in index)
        out_people.append({
            "id": p.pid, "n": p.name, "u": link("person", p),
            "pr": p.prophet, "tb": p.tabaqa or "", "kin": p.kin if p.kin is not None else -1,
            "tr": p.tribes, "c": [claim_json(cl) for cl in p.claims], "v": v, "ties": ties,
            "oc": p.other_candidates})

    def placements(iri: str, ev) -> dict:
        lb, la = lifes[iri]
        pl = {}
        for key, lf in (("b", lb), ("a", la)):
            if lf and ev.lo is not None and not lf.get("ages_only"):
                pl[key] = lives.placement(lf, ev.lo, ev.hi)
        return pl

    out_events, undrawn_events, ev_iri = [], 0, []
    ages_by_event: dict[str, list] = {}
    for a in c.ages:
        ages_by_event.setdefault(a.event, []).append(a)
    for ev in sorted(c.events.values(), key=lambda e: (e.lo if e.lo is not None else 10**9, display.sort_key(e.name))):
        given = ages_by_event.get(ev.iri, [])
        if ev.lo is None and not given:
            continue
        ps, others = [], []
        for part in ev.parts if ev.lo is not None else []:
            if part["person"] in index:
                ps.append({"p": index[part["person"]], "how": part["how"], "st": part["status"],
                           "cit": part.get("citation"), "wk": part.get("work"), "ai": part["ai"],
                           "kd": part["kind"], "pl": placements(part["person"], ev)})
            else:
                person = c.people[part["person"]]
                if person.name not in [o["n"] for o in others]:
                    others.append({"n": person.name, "u": link("person", person)})
        for a in given:
            if a.person not in index:
                continue
            ps.append({"p": index[a.person], "kd": "age", "ag": a.values, "aw": a.written,
                       "how": t("ih.age_as_given", ages=ages_text(a.values, t)) if a.values else t("ih.age_no_number"),
                       "st": a.source["status"], "cit": a.source["detail"], "src": a.source["label"],
                       "ai": True, "pl": placements(a.person, ev)})
        if not ps:
            if ev.parts:
                undrawn_events += 1
            continue
        ev_iri.append(ev.iri)
        out_events.append({"id": ev.pid, "n": ev.name, "kd": ev.kind, "u": link(ev.kind, ev),
                           "lo": ev.lo, "hi": ev.hi, "t": ev.text, "nt": ev.notes, "dis": ev.disputed,
                           "ag": ev.agents, "ps": ps, "oth": others})
    # places: presences come only from dated events with a recorded place that the person took part
    # in, and from place affiliations with a dated extent; nothing between them is assumed
    place_index: dict[str, int] = {}
    places_out: list[dict] = []

    def place_of(iri: str) -> int:
        if iri not in place_index:
            ent = site.entities.get(iri)
            place_index[iri] = len(places_out)
            places_out.append({"n": ent.name if ent else site.label_of(iri), "u": link("place", ent) if ent else None})
        return place_index[iri]

    presences: dict[int, list] = {}
    for ei, ev_out in enumerate(out_events):
        ev = c.events[ev_iri[ei]]
        if ev.lo is None or not ev.places:
            continue
        for ps in ev_out["ps"]:
            if ps["kd"] == "age":
                continue                                  # an age given at an event is not presence there
            for pl_iri in ev.places:
                row = [place_of(pl_iri), ev.lo, ev.hi, ei]
                if row not in presences.setdefault(ps["p"], []):
                    presences[ps["p"]].append(row)
    for r in c.residences:
        if r["person"] in index:
            presences.setdefault(index[r["person"]], []).append([place_of(r["place"]), r["lo"], r["hi"], -1, r["label"], r["text"]])
    undated_places: dict[int, list] = {}
    for link_ in c.place_links:
        if link_["person"] in index:
            undated_places.setdefault(index[link_["person"]], []).append(
                [place_of(link_["place"]), link_["label"], link_["status"]])
    for i, p_out in enumerate(out_people):
        p_out["pp"] = sorted(presences.get(i, []), key=lambda r: (r[1], r[0]))
        p_out["pu"] = undated_places.get(i, [])
    kin_ties: dict[tuple, dict] = {}
    for tie in c.kin_ties:
        if tie["a"] not in index or tie["b"] not in index:
            continue
        a, b = index[tie["a"]], index[tie["b"]]
        if tie["kd"] != "parent" and a > b:
            a, b = b, a                                   # symmetric ties: one bracket per pair
        key = (a, b, tie["kd"])
        kin_ties.setdefault(key, {"a": a, "b": b, "kd": tie["kd"], "cl": []})["cl"].append({
            "lab": tie["label"], "st": tie["status"], "cit": tie["citation"], "wk": tie["work"],
            "ai": tie["ai"], "bs": tie["basis"], "ag": tie["agents"]})
    undated = [{"n": p.name, "u": link("person", p),
                "why": "ambiguous" if p.ambiguous else "unplaced" if p.claims else "none"}
               for p in people if p.iri not in index]
    # axis helpers: year starts for both calendars across the drawn domain (computed here,
    # so the page does no calendar arithmetic of its own)
    dated = [v for p in out_people for v in p["v"].values() if not v.get("ages_only")]
    lo_all = [v["b"][0] if v["b"] else v["s"] for v in dated] + [e["lo"] for e in out_events if e["lo"] is not None]
    hi_all = [v["d"][1] if v["d"] else v["e"] for v in dated] + [e["hi"] for e in out_events if e["hi"] is not None]
    axis = {}
    if lo_all:
        y0 = cal.julian_from_jdn(min(lo_all))[0] - 12
        y1 = cal.julian_from_jdn(max(hi_all))[0] + 12
        axis["ce"] = [[y, cal.jdn_from_julian(y, 1, 1)] for y in range(y0, y1 + 1)]
        h0 = cal.hijri_from_jdn(cal.jdn_from_julian(y0, 1, 1))[0]
        h1 = cal.hijri_from_jdn(cal.jdn_from_julian(y1, 1, 1))[0] + 1
        axis["ah"] = [[h, cal.hijri_year_start(h)] for h in range(h0, h1 + 1)]
    ih_dates = sum(1 for p in c.people.values() for cl in p.claims if cl.source["type"] == "ibn-hisham")
    sources = {
        "graph": t("src.graph"),
        "external": label,
        "external_used": getattr(c, "external_used", 0),
        "ibn_hisham": ibn_hisham,
        "ibn_hisham_ages": len(c.ages),
        "ibn_hisham_dates": ih_dates,
    }
    data = {
        "people": out_people, "events": out_events, "undated": undated,
        "kt": [kin_ties[k] for k in sorted(kin_ties)],
        "places": places_out,
        "kin": {str(k): v for k, v in kin_labels.items()},
        "unitDays": {"lunar": cal.LUNAR_YEAR_DAYS, "solar": cal.SOLAR_YEAR_DAYS},
        "axis": axis, "sources": sources,
        "counts": {"people": len(c.people), "drawn": len(out_people),
                   "drawn_base": sum(1 for p in out_people if "b" in p["v"]),
                   "drawn_by_date": sum(1 for p in out_people if "b" in p["v"] and not p["v"]["b"].get("ages_only")),
                   "ages_only": sum(1 for p in out_people if "b" in p["v"] and p["v"]["b"].get("ages_only")),
                   "review_only": sum(1 for p in out_people if "b" not in p["v"]),
                   "events": len(out_events), "events_undrawn": undrawn_events,
                   "events_dated": sum(1 for e in c.events.values() if e.lo is not None),
                   "events_all": len(c.events)},
        "warnings": c.warnings,
    }
    return data, c


# ---------------------------------------------------------------- static HTML parts
def src_text(src: dict, t: T) -> str:
    parts = [esc(src["label"])]
    if src.get("href"):
        parts = [f'<a href="{attr(src["href"])}">{esc(src["label"])}</a>']
    if src.get("detail"):
        parts.append(esc(src["detail"]))
    parts.append(esc(t("status.label", value=t(f"status.{src['status']}") if src.get("status") else t("status.none"))))
    return " · ".join(parts)


def dates_cell(person: dict, kind: str, t: T, include_review: bool) -> str:
    items = [c for c in person["c"] if c["k"] == kind and (include_review or not c["rv"])]
    if not items:
        return f'<span class="none">{esc(t("table.not_recorded"))}</span>'
    out = []
    for c in items:
        rv = f' <span class="rvtag">{esc(t("table.needs_review"))}</span>' if c["rv"] else ""
        notes = "".join(f"<br><small>{esc(n)}</small>" for n in c["nt"])
        out.append(f'<div class="dc{" rv" if c["rv"] else ""}">{esc(c["t"])}{rv}<br><small>{src_text(c["src"], t)}</small>{notes}</div>')
    return "".join(out)


def ages_cell(pi: int, data: dict, t: T, variant: str) -> str:
    rows = []
    for ei, ev in enumerate(data["events"]):
        for ps in ev["ps"]:
            if ps["p"] != pi:
                continue
            pl = ps["pl"].get(variant) or ps["pl"].get("b")
            parts = [ps["how"]] if ps["kd"] == "age" else []
            if pl and not pl["ok"]:
                parts.append(t(f"age.flag.{pl['flag']}"))
            elif pl and "lunar" in pl:
                parts.append(t("table.computed", value=t("age.both", lunar=pl["lunar_text"], solar=pl["solar_text"])))
            elif pl:
                parts.append(t("age.no_birth"))
            if parts:
                rows.append(f'<li data-ev="{ei}">{esc(ev["n"])}: {esc(" · ".join(parts))}</li>')
    return f'<ul class="ages">{"".join(rows)}</ul>' if rows else f'<span class="none">{esc(t("table.no_events"))}</span>'


def table_html(data: dict, t: T) -> str:
    head = "".join(f'<th scope="col">{esc(t(k))}</th>' for k in
                   ("table.person", "table.born", "table.died", "table.age_death", "table.ages"))
    body = []
    for i, p in enumerate(data["people"]):
        for variant in ("b", "a"):
            if variant not in p["v"]:
                continue
            lf = p["v"][variant]
            inc = variant == "a"
            ad = lf.get("age_at_death") if not lf.get("ages_only") else None
            age = esc(t("age.both", lunar=ad["lunar"], solar=ad["solar"])) if ad else \
                f'<span class="none">{esc(t("table.age_unknown"))}</span>'
            name = f'<a href="{attr(p["u"])}">{esc(p["n"])}</a>' if p["u"] else esc(p["n"])
            hidden = " hidden" if variant == "a" else ""
            body.append(
                f'<tr data-p="{i}" data-v="{variant}"{hidden}><th scope="row">{name}</th>'
                f'<td>{dates_cell(p, "birth", t, inc)}</td><td>{dates_cell(p, "death", t, inc)}</td>'
                f'<td>{age}</td><td>{ages_cell(i, data, t, variant)}</td></tr>')
    if not body:
        return f'<p class="none">{esc(t("table.empty"))}</p>'
    return (f'<div class="tablewrap" tabindex="0" role="region" aria-labelledby="table-h">'
            f'<table class="ll-table"><caption>{esc(t("table.caption"))}</caption>'
            f'<thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>')


def undated_html(data: dict, t: T) -> str:
    items = []
    for u in data["undated"]:
        name = f'<a href="{attr(u["u"])}">{esc(u["n"])}</a>' if u["u"] else esc(u["n"])
        why = (f' <small>({esc(t("undated." + u["why"]))})</small>' if u["why"] in ("unplaced", "ambiguous") else "")
        items.append(f"<li>{name}{why}</li>")
    return f'<ul class="undated">{"".join(items)}</ul>'


def legend_html(t: T) -> str:
    sw = {
        "line": '<svg width="56" height="14" aria-hidden="true"><line x1="2" y1="7" x2="54" y2="7" class="lg-line"></line></svg>',
        "range": '<svg width="56" height="14" aria-hidden="true"><rect x="8" y="3" width="40" height="8" rx="2" class="lg-range"></rect></svg>',
        "open": '<svg width="56" height="14" aria-hidden="true"><rect x="2" y="6" width="40" height="2" fill="url(#lg-fade)"></rect><line x1="42" y1="7" x2="54" y2="7" class="lg-line"></line><defs><linearGradient id="lg-fade"><stop offset="0" class="fade-0"></stop><stop offset="1" class="fade-1"></stop></linearGradient></defs></svg>',
        "conn": '<svg width="56" height="28" aria-hidden="true"><line x1="20" y1="2" x2="20" y2="26" class="lg-conn"></line><rect x="31" y="2" width="8" height="24" class="lg-band"></rect></svg>',
        "node": '<svg width="56" height="14" aria-hidden="true"><line x1="2" y1="7" x2="54" y2="7" class="lg-line"></line><circle cx="28" cy="7" r="4.5" class="lg-node"></circle></svg>',
        "gap": '<svg width="56" height="28" aria-hidden="true"><line x1="28" y1="2" x2="28" y2="26" class="lg-conn"></line><line x1="2" y1="14" x2="54" y2="14" class="lg-halo"></line><line x1="2" y1="14" x2="54" y2="14" class="lg-line"></line></svg>',
        "given": '<svg width="56" height="14" aria-hidden="true"><line x1="2" y1="7" x2="54" y2="7" class="lg-line"></line><path d="M22.5 7 L28 1.5 L33.5 7 L28 12.5 Z" class="lg-given"></path></svg>',
        "tie": '<svg width="56" height="28" aria-hidden="true"><path d="M16 4 H10 V24 H16" class="lg-tie"></path><line x1="7" y1="12" x2="13" y2="12" class="lg-tie-mark"></line><line x1="7" y1="15" x2="13" y2="15" class="lg-tie-mark"></line><line x1="18" y1="4" x2="54" y2="4" class="lg-line"></line><line x1="18" y1="24" x2="54" y2="24" class="lg-line"></line></svg>',
        "place": '<svg width="56" height="28" aria-hidden="true"><line x1="2" y1="22" x2="54" y2="22" class="lg-line"></line><path d="M22 22 V6 H34 V22" class="lg-exc"></path></svg>',
        "review": '<svg width="56" height="14" aria-hidden="true"><line x1="2" y1="7" x2="54" y2="7" class="lg-line rv"></line></svg>',
    }
    rows = "".join(f'<li>{sw[k]}<span>{esc(t("legend." + k))}</span></li>' for k in
                   ("line", "range", "open", "conn", "node", "given", "gap", "tie", "place", "review"))
    return (f'<ul class="legend">{rows}</ul>'
            f'<p class="note">{esc(t("legend.hue"))}</p>'
            f'<p class="note">{esc(t("legend.calendar"))}</p>'
            f'<p class="note">{esc(t("legend.ages"))}</p>')


def footer_html(t: T) -> str:
    return (f'<p class="licence"><a href="{URL_LICENSING}">{esc(t("footer.text_data"))}</a> '
            f'<a href="{URL_CC_BY_SA}">{esc(t("footer.cc_by_sa"))}</a>{esc(t("footer.sep"))}'
            f'<a href="{URL_LICENSING}">{esc(t("footer.code"))}</a> <a href="{URL_AGPL}">{esc(t("footer.agpl"))}</a>'
            f'{esc(t("footer.sep"))}<a href="{URL_LICENSING}">{esc(t("footer.ids"))}</a>{esc(t("footer.dash"))}'
            f'<a href="{URL_LICENSING}">{esc(t("footer.contributors"))}</a></p>')


def sources_html(data: dict, t: T) -> str:
    s = data["sources"]
    items = [t("sources.graph")]
    if s["external"]:
        items.append(t("sources.external", file=s["external"], n=s["external_used"]))
    else:
        items.append(t("sources.external_missing"))
    items.append(t("sources.ibn_hisham", file=s["ibn_hisham"]) if s["ibn_hisham"] else t("sources.ibn_hisham_missing"))
    return "<ul>" + "".join(f"<li>{esc(i)}</li>" for i in items) + "</ul>"


def limits_html(data: dict, t: T) -> str:
    c = data["counts"]
    items = [t("limits.undated", n=len(data["undated"]), total=c["people"]),
             t("limits.events", dated=c["events_dated"], total=c["events_all"], drawn=c["events"],
               undrawn=c["events_undrawn"]),
             t("limits.no_review"), t("limits.relative")]
    return "<ul>" + "".join(f"<li>{esc(i)}</li>" for i in items) + "</ul>"


def render(data: dict, t: T, home: str | None) -> str:
    css = (HERE / "lifelines.css").read_text(encoding="utf-8")
    js = (HERE / "lifelines.js").read_text(encoding="utf-8")
    js_keys = sorted(k for k in t.d if k.split(".")[0] in JS_PREFIXES)
    for k in js_keys:
        t.used.add(k)
    i18n = {k: t.d[k] for k in js_keys}
    dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"), sort_keys=True).replace("</", "<\\/")
    c = data["counts"]
    home_link = f'<a class="home-link" href="{attr(home)}">{esc(t("nav.home"))}</a>' if home is not None else ""
    return f"""<!doctype html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<title>{esc(t("page.title"))}</title>
<meta name="description" content="{attr(t("page.description"))}">
<style>{css}</style>
</head>
<body class="nojs">
<a class="skip" href="#main">{esc(t("nav.skip_main"))}</a>
<header class="top">
<nav class="brand" aria-label="{attr(t("nav.label"))}">{home_link}<a class="home-link" href="#table">{esc(t("nav.skip_table"))}</a></nav>
<h1>{esc(t("page.h1"))}</h1>
<p class="sub">{esc(t("page.sub"))}</p>
</header>
<p class="banner" role="note"><strong>{esc(t("banner.strong"))}</strong> <span class="long">{esc(t("banner.text"))}</span><span class="short">{esc(t("banner.short"))}</span></p>
<main id="main">
<section class="controls" aria-label="{attr(t("controls.label"))}" hidden>
<fieldset class="seg"><legend>{esc(t("controls.align"))}</legend>
<label><input type="radio" name="align" value="date" checked> {esc(t("controls.by_date"))}</label>
<label><input type="radio" name="align" value="age"> {esc(t("controls.by_age"))}</label>
<label><input type="radio" name="align" value="place"> {esc(t("controls.by_place"))}</label></fieldset>
<fieldset class="seg"><legend>{esc(t("controls.units"))}</legend>
<label><input type="radio" name="units" value="lunar" checked> {esc(t("controls.lunar"))}</label>
<label><input type="radio" name="units" value="solar"> {esc(t("controls.solar"))}</label></fieldset>
<label class="ctl">{esc(t("controls.order"))} <select name="order">
<option value="birth">{esc(t("order.birth"))}</option>
<option value="tabaqa">{esc(t("order.tabaqa"))}</option>
<option value="kin">{esc(t("order.kin"))}</option>
<option value="tribe">{esc(t("order.tribe"))}</option>
</select></label>
<label class="ctl find">{esc(t("controls.filter"))} <input type="search" name="filter" list="ll-names" autocomplete="off" placeholder="{attr(t("controls.filter_ph"))}"></label>
<datalist id="ll-names"></datalist>
<button type="button" class="btn" data-act="clear-filter" hidden>{esc(t("controls.clear"))}</button>
<label class="ctl chk"><input type="checkbox" name="review"> {esc(t("controls.review"))}</label>
<div class="zoom" role="group" aria-label="{attr(t("controls.zoom"))}">
<button type="button" class="btn" data-act="zoom-out" aria-label="{attr(t("controls.zoom_out"))}">−</button>
<button type="button" class="btn" data-act="zoom-in" aria-label="{attr(t("controls.zoom_in"))}">+</button>
<button type="button" class="btn" data-act="home">{esc(t("controls.home"))}</button>
</div>
<div class="moment-ctl" role="group" aria-label="{attr(t("controls.moment_group"))}">
<label class="ctl">{esc(t("controls.moment"))} <input type="number" name="my" inputmode="numeric" step="1" placeholder="{attr(t("controls.moment_ph"))}"></label>
<select name="mcal" aria-label="{attr(t("controls.moment_cal"))}"><option value="ce">{esc(t("date.ce"))}</option><option value="ah">{esc(t("date.ah"))}</option><option value="bh">{esc(t("date.bh"))}</option></select>
<button type="button" class="btn" data-act="moment">{esc(t("controls.moment_go"))}</button>
<button type="button" class="btn" data-act="clear-moment" hidden>{esc(t("controls.moment_clear"))}</button>
</div>
<label class="ctl chk young"><input type="checkbox" name="young"> {esc(t("controls.young_before"))} <input type="number" name="yn" value="20" min="1" max="120" step="1" aria-label="{attr(t("controls.young_n"))}"> {esc(t("controls.young_after"))}</label>
<span class="young-none note" hidden>{esc(t("controls.young_none"))}</span>
<p class="orient" aria-live="polite"><output id="ll-count"></output></p>
</section>
<div class="stage" hidden>
<div class="scroller" id="ll-scroller" tabindex="0" aria-label="{attr(t("chart.label"))}" aria-describedby="ll-chart-desc"></div>
<p id="ll-chart-desc" class="sr">{esc(t("chart.desc"))}</p>
<aside class="details" id="ll-details" aria-labelledby="ll-details-h" hidden tabindex="-1"></aside>
</div>
<section class="legend-wrap" aria-labelledby="legend-h"><h2 id="legend-h">{esc(t("legend.h"))}</h2>{legend_html(t)}</section>
<section id="table" aria-labelledby="table-h"><h2 id="table-h">{esc(t("table.h"))}</h2>
<p class="note">{esc(t("table.intro"))}</p>
{table_html(data, t)}</section>
<section id="undated-sec" aria-labelledby="undated-h"><h2 id="undated-h">{esc(t("undated.h", n=len(data["undated"])))}</h2>
<p class="note">{esc(t("undated.intro"))}</p>{undated_html(data, t)}</section>
<section aria-labelledby="sources-h"><h2 id="sources-h">{esc(t("sources.h"))}</h2>{sources_html(data, t)}
<h2>{esc(t("limits.h"))}</h2>{limits_html(data, t)}</section>
</main>
<footer class="site-footer">{footer_html(t)}</footer>
<script type="application/json" id="ll-data">{dump(data)}</script>
<script type="application/json" id="ll-i18n">{dump(i18n)}</script>
<script>{js}</script>
</body>
</html>
"""


def merge_graph(graph: Path, ih_text: str, renames: dict, out: Path) -> tuple[Path, set]:
    """The graph plus an Ibn Hisham Turtle file from a branch, with renamed IDs mapped to the
    current ones. Returns (merged file, IRIs of entities that have reader pages)."""
    from rdflib import Graph, URIRef
    from rdflib.namespace import RDF
    base = "https://w3id.org/marsad/id/"
    iri_map = {}
    for old, new in renames.items():
        po, pn = old.split(":", 1), new.split(":", 1)
        if po[0] in ID_PATHS and pn[0] in ID_PATHS:
            iri_map[URIRef(f"{base}{ID_PATHS[po[0]]}/{po[1]}")] = URIRef(f"{base}{ID_PATHS[pn[0]]}/{pn[1]}")
    g = Graph()
    g.parse(str(graph), format="turtle")
    reader_iris = {str(s) for s in g.subjects(RDF.type, None) if str(s).startswith(base)}
    ih = Graph()
    ih.parse(data=ih_text, format="turtle")
    for s, p, o in ih:
        g.add((iri_map.get(s, s), p, iri_map.get(o, o)))
    out.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(str(out), format="turtle")
    return out, reader_iris


JS_PREFIXES = ("js", "status", "age", "group", "match", "order", "units", "axis", "flag", "date", "ih")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--graph", default=str(ROOT / "build" / "graph.ttl"))
    ap.add_argument("--out", default=str(SITE / "dist" / "lifelines"))
    ap.add_argument("--external-dates", default=None,
                    help=f"CSV of proposed external dates (default: {EXTERNAL_DATES}, else origin/{EXTERNAL_BRANCH})")
    ap.add_argument("--ibn-hisham", default=None,
                    help=f"Turtle of proposed Ibn Hisham claims (default: {IBN_HISHAM} when it is in the graph, "
                         f"else origin/{IBN_HISHAM_BRANCH}); 'none' to leave them out")
    ap.add_argument("--reader-base", default="../",
                    help="prefix for links to reader pages; pass '' for none (page published on its own)")
    a = ap.parse_args(argv)
    graph = Path(a.graph)
    if not graph.exists():
        sys.exit(f"{graph} not found: run ontology/build_graph.py first")
    from model import Site  # site/model.py, the site's only rdflib reader
    t = T(HERE / "i18n" / "en.json")
    renames = collect.read_renames(ROOT / "ontology" / "corpus" / "id-renames.csv")
    graph_used, ih_label, reader_iris = graph, None, None
    if a.ibn_hisham != "none" and not (ROOT / IBN_HISHAM).exists():
        if a.ibn_hisham:
            ih_text, ih_label = Path(a.ibn_hisham).read_text(encoding="utf-8"), Path(a.ibn_hisham).name
        else:
            ih_text, ih_label = collect.read_text_source(ROOT, IBN_HISHAM, IBN_HISHAM_BRANCH)
        if ih_text:
            graph_used, reader_iris = merge_graph(graph, ih_text, renames, ROOT / MERGED_GRAPH)
    elif (ROOT / IBN_HISHAM).exists():
        ih_label = IBN_HISHAM
    site = Site(graph_used)
    if a.external_dates:
        p = Path(a.external_dates)
        external = (p.read_text(encoding="utf-8"), p.name) if p.exists() else (None, None)
    else:
        external = collect.read_text_source(ROOT, EXTERNAL_DATES, EXTERNAL_BRANCH)
    reader_base = a.reader_base if a.reader_base != "" else None
    data, coll = build_data(site, t, external, reader_base, renames, ibn_hisham=ih_label, reader_iris=reader_iris)
    page = render(data, t, home=reader_base)
    out = Path(a.out)
    dist = out.parent
    if not dist.exists():
        dist.mkdir(parents=True)
        (dist / SITE_MARKER).write_text("made by site/lifelines/build_lifelines.py; safe to delete and rebuild\n",
                                        encoding="utf-8")
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    size = len(page.encode("utf-8"))
    c = data["counts"]
    print(f"wrote {out / 'index.html'} ({size:,} bytes)")
    print(f"  people with a line: {c['drawn_base']} ({c['drawn_by_date']} by date, {c['ages_only']} by ages as given only;"
          f" +{c['review_only']} only from matches that need review) of {c['people']}; no dates recorded: {len(data['undated'])}")
    print(f"  events on the chart: {c['events']} ({c['events_dated']} of {c['events_all']} events have a date that can be placed)")
    print(f"  external dates: {data['sources']['external'] or 'not found'}"
          f"{' (' + str(data['sources']['external_used']) + ' rows used)' if data['sources']['external'] else ''}")
    if data["sources"]["ibn_hisham"]:
        print(f"  Ibn Hisham: {data['sources']['ibn_hisham']} ({data['sources']['ibn_hisham_ages']} ages as given,"
              f" {data['sources']['ibn_hisham_dates']} born/died-during claims)")
    for w in data["warnings"]:
        print("  warning:", w)
    if size > MAX_BYTES:
        print(f"page is over {MAX_BYTES:,} bytes", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
