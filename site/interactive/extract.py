"""What the timeline and the map need, read from the graph as plain Python values.

The reader tier's model (site/model.py) loads the graph and names every entity; this module
adds the few reads that model does not make (coordinates, routes, date nodes with what attests
them, relative anchors) through `site.g`. It is the only module in site/interactive that
touches rdflib, and it hard-codes no entity ID: everything is found by its rdf:type.

Rules, from docs/handover/slice-10-brief.md and the standing rules:
- An item is placed on the timeline only by the earliest and latest bounds its record gives.
  A record with no bounds, or with one bound only, or dated only relative to another event,
  is listed, never placed. Nothing is computed into a date and no bound is narrowed.
- A place is drawn only where its record gives a coordinate (a WKT point). A route segment is
  drawn only where its record gives a geometry, and never when its confidence is unknown.
- Every value keeps its source: the date's own record, the status of what attests it (if
  anything does), the record's coverage. A field with no review status says so.

Day numbers. Positions on the time axis are Julian Day Numbers. The graph stores CE bounds
as ISO dates; the ones converted from Hijri dates (method "tabular-islamic-civil") are dates
of the Julian calendar (17 Ramadan 2 AH is stored as 624-03-13), so every stored Y-M-D is
read as a Julian-calendar date. This changes no recorded value; it only spaces them.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from rdflib import Namespace, URIRef
from rdflib.namespace import RDF, RDFS

import display
from model import MRS, Entity, Site

GEO = Namespace("http://www.opengis.net/ont/geosparql#")

_NUM = r"(-?\d+(?:\.\d+)?)"
_POINT = re.compile(rf"^\s*POINT\s*\(\s*{_NUM}\s+{_NUM}\s*\)\s*$", re.IGNORECASE)
_LINE = re.compile(r"^\s*LINESTRING\s*\(([^()]*)\)\s*$", re.IGNORECASE)
_PAIR = re.compile(rf"^\s*{_NUM}\s+{_NUM}\s*$")
_ISO = re.compile(r"^(-?\d{1,6})-(\d\d)-(\d\d)(?:T(\d\d):(\d\d):(\d\d))?")

# Kinds an item on the timeline can be focused on, and the kinds a claim can link it to.
FOCUS_KINDS = ("person", "group", "place")


# --------------------------------------------------------------------------- calendars
def jdn_julian(y: int, m: int, d: int) -> int:
    """Julian Day Number of a date in the Julian calendar."""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - 32083


def day_number(iso: str | None, end: bool = False) -> float | None:
    """Day number of a stored ISO date-time (read as a Julian-calendar date, see above).
    A start is the beginning of its day; an end is its recorded time of day (23:59:59 is
    the whole day)."""
    if not iso:
        return None
    m = _ISO.match(iso)
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    base = float(jdn_julian(y, mo, d))
    if m.group(4) is not None:
        secs = int(m.group(4)) * 3600 + int(m.group(5)) * 60 + int(m.group(6))
        if end and secs >= 86399:
            return base + 1.0
        return base + secs / 86400.0
    return base + (1.0 if end else 0.0)


def muharram_first(ah_year: int) -> int:
    """JDN of 1 Muharram of a Hijri year in the tabular Islamic calendar (civil epoch,
    16 July 622 Julian). Used only to label the AH row of the axis; never to date anything."""
    return 1948440 + 354 * (ah_year - 1) + (3 + 11 * ah_year) // 30


def iso_date(iso: str | None) -> str | None:
    m = _ISO.match(iso or "")
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


# --------------------------------------------------------------------------- geometry
def parse_point(wkt: str) -> tuple[float, float] | None:
    m = _POINT.match(wkt or "")
    return (float(m.group(1)), float(m.group(2))) if m else None


def parse_line(wkt: str) -> list[tuple[float, float]] | None:
    m = _LINE.match(wkt or "")
    if not m:
        return None
    pts = []
    for part in m.group(1).split(","):
        pm = _PAIR.match(part)
        if not pm:
            return None
        pts.append((float(pm.group(1)), float(pm.group(2))))
    return pts if len(pts) >= 2 else None


# --------------------------------------------------------------------------- reading helpers
def _local(iri) -> str:
    return re.split(r"[#/]", str(iri))[-1] if iri is not None else ""


@dataclass
class Ref:
    """A link to an entity page, or to something that has none."""
    id: str                 # "kind/pid" for an entity with a page, else the IRI
    name: str               # display name
    href: str | None        # relative to a page one level below the site root
    kind: str | None


def ref(site: Site, iri: str) -> Ref:
    e = site.entity(iri)
    if e is not None:
        return Ref(f"{e.kind}/{e.pid}", e.name, f"../{e.kind}/{e.pid}/", e.kind)
    return Ref(iri, site.label_of(iri), None, None)


def statuses_of(site: Site, node) -> list[str]:
    """Statuses of the assertions that attest a node (mrs:attestedBy), as recorded."""
    out = []
    for a in site.g.objects(node, MRS.attestedBy):
        st = site.vkey(site.g.value(a, MRS.assertionStatus), "as_")
        if st and st not in out:
            out.append(st)
    return sorted(out)


def extent_record(site: Site, node) -> dict | None:
    """One TemporalExtent with what the timeline needs beyond site.extent()."""
    ext = site.extent(node)
    if ext is None:
        return None
    g = site.g
    anchors = []
    for ra in g.objects(node, MRS.relativeAnchor):
        target = g.value(ra, MRS.anchorTarget)
        anchors.append({"relation": _local(g.value(ra, MRS.allenRelation)) or None,
                        "target": ref(site, str(target)) if target is not None else None,
                        "statuses": statuses_of(site, ra)})
    anchors.sort(key=lambda a: (a["relation"] or "", a["target"].id if a["target"] else ""))
    disputes = []
    for d in g.objects(node, MRS.dispute):
        q = site.first_lit(d, MRS.disputeQuestion) or site.first_lit(d, RDFS.label)
        disputes.append(q.text if q else _local(d))
    return {"ext": ext, "statuses": statuses_of(site, node), "anchors": anchors,
            "disputes": sorted(disputes), "node": str(node)}


def _linked(site: Site, iri: str) -> list[str]:
    """People, groups and places the record links to this event (claims of any kind)."""
    out = set()
    for c in site.claims.get(iri, []):
        other = c.object if c.subject == iri else c.subject
        e = site.entity(other)
        if e is not None and e.kind in FOCUS_KINDS:
            out.add(f"{e.kind}/{e.pid}")
    return sorted(out)


# --------------------------------------------------------------------------- timeline
def _placement(rec: dict) -> str:
    """'placed' (both bounds), 'inconsistent' (the latest bound is before the earliest),
    'one_bound', 'relative' (only a relative anchor) or 'none'."""
    ext = rec["ext"]
    e, l = day_number(ext.get("earliest")), day_number(ext.get("latest"), end=True)
    if e is not None and l is not None:
        return "placed" if l >= e else "inconsistent"
    if e is not None or l is not None:
        return "one_bound"
    if rec["anchors"]:
        return "relative"
    return "none"


def timeline(site: Site) -> dict:
    """Placed spans, and everything that is not placed with the reason why."""
    g = site.g
    spans, not_placed = [], defaultdict(list)
    event_like = site.by_kind["event"] + site.by_kind["story"]
    for e in event_like:
        recs = [r for r in (extent_record(site, n) for n in g.objects(URIRef(e.iri), MRS.eventTemporalExtent)) if r]
        recs.sort(key=lambda r: (r["ext"].get("earliest") or "", r["ext"].get("latest") or "", r["node"]))
        if not recs:
            not_placed["no_date"].append({"entity": e, "role": "event", "rec": None})
        for i, rec in enumerate(recs):
            how = _placement(rec)
            item = {"entity": e, "role": "event", "rec": rec, "n": i + 1, "of": len(recs)}
            (spans if how == "placed" else not_placed[how]).append(item)
    for p in site.by_kind["person"]:
        recs = []
        for death in g.objects(URIRef(p.iri), MRS.death):
            for n in g.objects(death, MRS.eventTemporalExtent):
                r = extent_record(site, n)
                if r:
                    recs.append(r)
        recs.sort(key=lambda r: (r["ext"].get("earliest") or "", r["ext"].get("latest") or "", r["node"]))
        if not recs:
            not_placed["no_date"].append({"entity": p, "role": "person", "rec": None})
        for i, rec in enumerate(recs):
            how = _placement(rec)
            item = {"entity": p, "role": "death", "rec": rec, "n": i + 1, "of": len(recs)}
            (spans if how == "placed" else not_placed[how]).append(item)
    for grp in site.by_kind["group"]:
        not_placed["no_date"].append({"entity": grp, "role": "group", "rec": None})
    for s in spans:
        ext = s["rec"]["ext"]
        s["start"] = day_number(ext["earliest"])
        s["end"] = day_number(ext["latest"], end=True)
        s["linked"] = [f"{s['entity'].kind}/{s['entity'].pid}"] if s["role"] == "death" else _linked(site, s["entity"].iri)
        s["places"] = list(s["entity"].data.get("places") or []) if s["role"] == "event" else []
    order = {"event": 0, "death": 1}
    spans.sort(key=lambda s: (order[s["role"]], s["start"], s["end"], display.sort_key(s["entity"].name), s["entity"].pid))
    return {"spans": spans, "not_placed": dict(not_placed)}


# --------------------------------------------------------------------------- map
def places(site: Site) -> dict:
    """Plotted points per place, and the places that are not plotted with the reason why."""
    g = site.g
    plotted, unlocated, no_location, other_geometry = [], [], [], []
    for e in site.by_kind["place"]:
        points: dict[tuple, dict] = {}
        states = list(g.objects(URIRef(e.iri), MRS.geometryState))
        said_unlocated = False
        other = []
        for gs in states:
            conf = site.vkey(g.value(gs, MRS.locationConfidence), "lc_")
            basis = site.vkey(g.value(gs, MRS.geometryBasis), "gb_")
            valid = site.extent(g.value(gs, MRS.validExtent))
            wkts = [str(w) for geom in g.objects(gs, MRS.geometry) for w in g.objects(geom, GEO.asWKT)]
            if conf == "unlocated" or not wkts:
                said_unlocated = said_unlocated or conf == "unlocated"
                continue
            for w in wkts:
                pt = parse_point(w)
                if pt is None:
                    other.append(w)
                    continue
                key = (pt, conf, basis)
                rec = points.setdefault(key, {"lon": pt[0], "lat": pt[1], "wkt": w.strip(), "confidence": conf,
                                              "confidence_label": site.vocab(g.value(gs, MRS.locationConfidence)),
                                              "basis": basis, "basis_label": site.vocab(g.value(gs, MRS.geometryBasis)),
                                              "valid": [], "statuses": []})
                if valid and valid not in rec["valid"]:
                    rec["valid"].append(valid)
                for st in statuses_of(site, gs):
                    if st not in rec["statuses"]:
                        rec["statuses"].append(st)
        if points:
            for i, (key, rec) in enumerate(sorted(points.items(), key=lambda kv: (kv[0][0], kv[0][1] or "", kv[0][2] or ""))):
                rec["valid"].sort(key=lambda v: (v.get("earliest") or "", v.get("native") or ""))
                plotted.append({"entity": e, "point": rec, "n": i + 1, "of": len(points)})
        elif other:
            other_geometry.append({"entity": e, "wkt": sorted(other)})
        elif said_unlocated:
            unlocated.append({"entity": e})
        else:
            no_location.append({"entity": e})
    key = lambda x: (display.sort_key(x["entity"].name), x["entity"].pid)
    plotted.sort(key=lambda p: (-p["point"]["lat"], p["point"]["lon"], key(p)))
    return {"plotted": plotted, "unlocated": sorted(unlocated, key=key),
            "no_location": sorted(no_location, key=key), "other_geometry": sorted(other_geometry, key=key)}


def routes(site: Site) -> list[dict]:
    """Every Route with its segments in recorded order; a segment is drawn only from its own
    recorded geometry, and never when its confidence is unknown."""
    g = site.g
    out = []
    for r in sorted(set(g.subjects(RDF.type, MRS.Route)), key=str):
        if not isinstance(r, URIRef):
            continue
        label = site.first_lit(r, RDFS.label)
        segs = []
        for seg in g.objects(r, MRS.hasSegment):
            order = g.value(seg, MRS.segmentOrder)
            conf = site.vkey(g.value(seg, MRS.segmentConfidence), "sc_")
            wkts = [str(w) for geom in g.objects(seg, MRS.segmentGeometry) for w in g.objects(geom, GEO.asWKT)]
            line, reason = None, None
            if conf == "unknown":
                reason = "unknown"
            elif not wkts:
                reason = "no_geometry"
            else:
                line = parse_line(wkts[0]) if len(wkts) == 1 else None
                if line is None:
                    reason = "other_geometry"
            frm, to = g.value(seg, MRS.segmentFrom), g.value(seg, MRS.segmentTo)
            disputes = []
            for d in g.objects(seg, MRS.dispute):
                q = site.first_lit(d, MRS.disputeQuestion) or site.first_lit(d, RDFS.label)
                disputes.append(q.text if q else _local(d))
            segs.append({
                "order": int(str(order)) if order is not None and str(order).lstrip("-").isdigit() else None,
                "from": ref(site, str(frm)) if frm is not None else None,
                "to": ref(site, str(to)) if to is not None else None,
                "confidence": conf, "confidence_label": site.vocab(g.value(seg, MRS.segmentConfidence)),
                "mode": site.vocab(g.value(seg, MRS.travelMode)),
                "line": line, "wkt": wkts[0].strip() if wkts else None, "reason": reason,
                "traversal": [x for x in (site.extent(t) for t in g.objects(seg, MRS.traversal)) if x],
                "disputes": sorted(disputes), "statuses": statuses_of(site, seg),
            })
        segs.sort(key=lambda s: (s["order"] is None, s["order"] or 0, s["from"].id if s["from"] else ""))
        cov = g.value(r, MRS.coverageState)
        journeys = [ref(site, str(j)) for j in g.subjects(MRS.hasRoute, r)]
        out.append({"iri": str(r), "pid": str(r).rsplit("/", 1)[-1], "label": label.text if label else _local(r),
                    "coverage": site.vkey(cov, "cs_"), "coverage_label": site.vocab(cov),
                    "journeys": sorted(journeys, key=lambda j: j.id), "segments": segs})
    return out


def events_at_places(site: Site, spans: list[dict]) -> dict[str, list[dict]]:
    """For each place IRI: the events and stories recorded there (eventPlace), with the
    timeline span of each where the event is placed."""
    by_entity = defaultdict(list)
    for s in spans:
        if s["role"] == "event":
            by_entity[s["entity"].iri].append(s)
    out = defaultdict(list)
    for e in site.by_kind["event"] + site.by_kind["story"]:
        for p in e.data.get("places") or []:
            out[p].append({"entity": e, "spans": by_entity.get(e.iri, [])})
    for p in out:
        out[p].sort(key=lambda x: (not x["spans"], x["spans"][0]["start"] if x["spans"] else 0,
                                   display.sort_key(x["entity"].name), x["entity"].pid))
    return out


def entity_id(e: Entity) -> str:
    return f"{e.kind}/{e.pid}"
