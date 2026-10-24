"""People order E3: membership lists by name, coverage counts and the acceptance sort.

Imported by learn/journeys.py only when a journey's order is "e3" (design §6).

The list file (learn/lists/people.json, format marsad-lists v1) names its members by
their name as the graph records it, never by ID, and says where each list comes from:

    {"format": "marsad-lists", "version": 1, "about": "...", "status": "proposed",
     "approved_by": [{"who": "maintainer"|"review_board", "date": "YYYY-MM-DD", "sha": "12 hex digits"}],
     "lists": [{"key": "rashidun", "members": [names], "order": "...", "source": text|null},
               {"key": "ten", ...}]}

The file is reviewed only when it says so, both roles approved the current sha12 of its
"lists" array, and every list has a source with no review word in it. Until then the
E3 order is the Prophet ﷺ, then everyone A to Z (the v1 order): applying only the last
part of E3, a computed count, would read as a ranking E3 does not describe.

Reviewed, the key is: tier 0 the Prophet ﷺ; tier 1 al-Khulafāʾ al-Rāshidūn in list
order; tier 2 the rest of the ten in list order; tier 3 everyone else by how many
records about them the graph holds (coverage, never rank), then name, then pid.

Nobody is placed last for faith: there is no recorded term for it (round 4 Q2), and a
"last" list or rule is refused.
"""
from __future__ import annotations

import json
from pathlib import Path

import display
import names
from model import MRS, Site

from journeys import (APPROVERS, EVENT_KINDS, RESERVED_LAST, ROUND4_Q2, RuleError, Step, _bounds, _day, _iso_key,
                      _keys, approvals, claim_node, name_matches, refuse_reserved, review_words, sha12)

FORMAT = "marsad-lists"
VERSION = 1
LIST_KEYS = ("rashidun", "ten")        # tier 1 and tier 2 (the ten less those already placed)
LIST_STATES = ("proposed", "reviewed")
# Acceptance of Islam, a named rule (never an ID): cited records at events whose label
# holds this phrase, the person as subject (design §6.5).
ACCEPTANCE_RULE = {"kinds": ["event"], "phrase": ["acceptance", "of", "islam"]}
ACCEPTANCE_NEEDS = "citation"
ACCEPTANCE_RECORDS = {"participation": "took_part", "assertion": MRS.rel_participated_in}


# --------------------------------------------------------------------------- the list file
def validate_lists(data, where: str = "lists") -> dict:
    """Check a list file against marsad-lists v1. Returns it."""
    refuse_reserved(data, where)
    _keys(data, {"format", "version", "about", "status", "approved_by", "lists"},
          {"format", "version", "status", "approved_by", "lists"}, where)
    if data["format"] != FORMAT or data["version"] != VERSION:
        raise RuleError(f"{where}: format must be {FORMAT!r}, version {VERSION}")
    if "about" in data and not isinstance(data["about"], str):
        raise RuleError(f"{where}: about must be a text")
    if data["status"] not in LIST_STATES:
        raise RuleError(f"{where}: status must be one of {LIST_STATES}")
    approvals(data["approved_by"], f"{where}.approved_by", sha_key="sha", sha_required=True)
    lists = data["lists"]
    if not isinstance(lists, list) or not lists:
        raise RuleError(f"{where}: lists must be a non-empty list")
    keys = []
    for i, ls in enumerate(lists):
        at = f"{where}.lists[{i}]"
        _keys(ls, {"key", "members", "order", "source"}, {"key", "members", "order", "source"}, at)
        if ls["key"] in RESERVED_LAST:
            raise RuleError(f"{at}: a list keyed {ls['key']!r} {ROUND4_Q2}")
        if ls["key"] not in LIST_KEYS:
            raise RuleError(f"{at}: key must be one of {LIST_KEYS}")
        keys.append(ls["key"])
        m = ls["members"]
        if (not isinstance(m, list) or not m or not all(isinstance(x, str) and x.strip() for x in m)
                or len(set(m)) != len(m)):
            raise RuleError(f"{at}: members must be a non-empty list of distinct names")
        for x in m:
            if "/" in x or ":" in x:
                raise RuleError(f"{at}: {x!r} looks like an ID or a link; members are names as the graph records them")
        if not isinstance(ls["order"], str) or not ls["order"].strip():
            raise RuleError(f"{at}: order must say how the list is ordered")
        if ls["source"] is not None and not isinstance(ls["source"], str):
            raise RuleError(f"{at}: source must be a text or null")
    if sorted(keys) != sorted(LIST_KEYS):
        raise RuleError(f"{where}: give each of the lists {LIST_KEYS} once")
    return data


def sources_complete(data: dict) -> bool:
    """Every list has a non-empty source, and no source holds a review word."""
    return all(isinstance(ls["source"], str) and ls["source"].strip() and not review_words(ls["source"])
               for ls in data["lists"])


def list_state(data: dict) -> str:
    """"reviewed" only when the file says so, both roles approved sha12 of its lists, and
    its sources are complete; otherwise "proposed"."""
    sha = sha12(data["lists"])
    both = set(APPROVERS) <= {a["who"] for a in data["approved_by"] if a["sha"] == sha}
    return "reviewed" if data["status"] == "reviewed" and both and sources_complete(data) else "proposed"


def load_lists(path: Path | str, where: str | None = None) -> dict:
    """Read and check a list file. Every problem is a RuleError. Returns
    {file, state, sha, sources_complete, stale_approval, lists}."""
    where = where or str(path)
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise RuleError(f"{where}: the list file is missing") from None
    except (OSError, UnicodeDecodeError) as e:
        raise RuleError(f"{where}: the list file cannot be read ({type(e).__name__})") from None
    try:
        data = json.loads(raw)
    except ValueError as e:
        raise RuleError(f"{where}: the list file is not JSON ({e.msg}, line {e.lineno})") from None
    validate_lists(data, where)
    sha = sha12(data["lists"])
    order = {k: n for n, k in enumerate(LIST_KEYS)}
    return {"file": where, "state": list_state(data), "sha": sha, "sources_complete": sources_complete(data),
            "stale_approval": any(a["sha"] != sha for a in data["approved_by"]),
            "lists": sorted(data["lists"], key=lambda ls: order[ls["key"]])}


# --------------------------------------------------------------------------- matching names
def _person_index(site: Site) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for e in site.by_kind["person"]:
        for label in [e.name, e.scholarly, *e.other_labels]:
            index.setdefault(names.normalise(label), set()).add(e.iri)
    return index


def match_members(site: Site, members: list[str]) -> list[str]:
    """The person each name names, in list order. The name is compared, in search form
    (names.normalise: marks, b./ibn and the article folded), with every person's display
    name, scholarly label and other labels. Each must match exactly one person."""
    index = _person_index(site)
    out = []
    for m in members:
        hits = sorted(index.get(names.normalise(m), ()))
        if len(hits) != 1:
            raise RuleError(f"list member {m!r} matches {len(hits)} people in this graph; it must match exactly one")
        out.append(hits[0])
    return out


# --------------------------------------------------------------------------- the key
def links_count(site: Site, iri: str) -> int:
    """How many records about this entity the graph holds: assertions, participation
    records and links. Coverage, never rank."""
    return len(site.claims.get(iri, []))


def e3_tier(site: Site, st: Step, members: dict | None) -> tuple[int | None, int | None]:
    """(tier, 1-based place in its list) under a reviewed list; (0 or None, None) otherwise."""
    e = st.entity
    if e.prophet:
        return 0, None
    if members is None:
        return None, None
    rashidun, ten = members.get("rashidun", []), members.get("ten", [])
    if e.iri in rashidun:
        return 1, rashidun.index(e.iri) + 1
    if e.iri in ten:
        return 2, ten.index(e.iri) + 1
    return 3, None


def e3_key(site: Site, st: Step, members: dict | None):
    """Sort key for order e3, inside each group. members is None while the list is not
    reviewed: then the Prophet ﷺ, then A to Z (the v1 prophet_first_then_name order)."""
    e = st.entity
    if members is None:
        return (0 if e.prophet else 1, 0, 0, display.sort_key(e.name), e.pid)
    tier, pos = e3_tier(site, st, members)
    links = -links_count(site, e.iri) if tier == 3 else 0
    return (tier, pos or 0, links, display.sort_key(e.name), e.pid)


def e3_data(site: Site, st: Step, members: dict | None, accept: list[str] | None = None) -> dict:
    tier, pos = e3_tier(site, st, members)
    return {"tier": tier, "pos": pos, "links": links_count(site, st.entity.iri),
            "accepted_islam": accepted_islam_records(site, st.entity.iri, accept)}


# --------------------------------------------------------------------------- acceptance of Islam
def acceptance_events(site: Site) -> list[str]:
    """The events ACCEPTANCE_RULE names, by name then pid."""
    out = []
    for kind in ACCEPTANCE_RULE["kinds"]:
        out += [e for e in site.by_kind[kind] if kind in EVENT_KINDS
                and name_matches(site, e.iri, None, ACCEPTANCE_RULE["phrase"])]
    return [e.iri for e in sorted(out, key=lambda e: (display.sort_key(e.name), e.pid))]


def _precision_at_start(e) -> str | None:
    best = None
    for x in e.data.get("dates") or []:
        if x.get("earliest") and (best is None or _iso_key(x["earliest"]) < _iso_key(best["earliest"])):
            best = x
    return best.get("precision") if best else None


def accepted_islam_records(site: Site, iri: str, accept: list[str] | None = None) -> list[dict]:
    """[{event, earliest, latest, precision, claims}] for a person: their cited records at
    an acceptance event (ACCEPTANCE_RULE), the person as subject. Dated events first, by
    earliest start; then undated ones by name."""
    accept = acceptance_events(site) if accept is None else accept
    at = set(accept)
    by_event: dict[str, list] = {}
    for c in site.claims.get(iri, []):
        if c.subject != iri or c.object not in at or not c.citation:
            continue
        if c.kind == "assertion":
            if claim_node(site, c, MRS.predicate) != ACCEPTANCE_RECORDS["assertion"]:
                continue
        elif c.kind != "participation":     # a participation record never carries a citation today
            continue
        by_event.setdefault(c.object, []).append(c)
    out = []
    for ev in sorted(by_event, key=accept.index):
        e = site.entity(ev)
        lo, hi = _bounds(e)
        out.append({"event": ev, "earliest": lo, "latest": hi, "precision": _precision_at_start(e) if lo else None,
                    "claims": sorted(by_event[ev], key=lambda c: c.node or "")})
    out.sort(key=lambda r: (r["earliest"] is None, _iso_key(r["earliest"]) if r["earliest"] else (),
                            accept.index(r["event"])))
    return out


def accepted_islam_rank(site: Site, records: dict[str, list[dict]]) -> dict[str, int | None]:
    """Dense rank of the acceptance sort: people at a dated event by its earliest start
    (equal extents share a rank), then people recorded only at undated events, one rank
    per event in name order, then None (not recorded)."""
    def key(recs):
        dated = [r for r in recs if r["earliest"]]
        if dated:
            r = dated[0]
            return (0, _day(r["earliest"]), _day(r["latest"] or r["earliest"]), "", "")
        if recs:
            e = site.entity(recs[0]["event"])
            return (1, (0, 0, 0), (0, 0, 0), display.sort_key(e.name), e.pid)
        return None

    keys = {iri: key(recs) for iri, recs in records.items()}
    distinct = sorted({k for k in keys.values() if k is not None})
    rank = {k: n for n, k in enumerate(distinct, 1)}
    return {iri: (rank[k] if k is not None else None) for iri, k in sorted(keys.items())}
