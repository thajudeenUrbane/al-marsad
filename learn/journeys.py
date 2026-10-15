"""Journeys: ordered walks through the graph, chosen by rules, never by hand.

A journey is a JSON file in learn/journeys/. It names no entity ID and holds no prose:
its title and lead are i18n keys, and its steps come from selection rules that this
module applies to build/graph.ttl (read through site/model.py, so every step links to
the same page the reader tier builds). The rule language is small on purpose; every
rule is printed in plain words on the journey's page, so a reviewer approves the rule,
not a hand-made list.

Three step types:
  events   events and stories whose recorded name contains a word, plus events the
           record links to them (part-of claims, before/after links on recorded
           dates, other event-to-event claims), up to `max_links` links away.
           Order "recorded": recorded dates and before/after links decide; where the
           record says nothing, dated steps first, then story order, then name.
  people   people with a recorded participation in the events chosen as above.
           Other claims (for example "absent from") are shown beside, never used to
           choose. People whose every record carries a set-apart qualifier are listed
           apart. Order: the Prophet first (if present), then name; no ranking.
  stories  the stories in a part of a story document whose title contains a word,
           with the people each story names. Order: the document's reading order.

A journey is a draft until its file records the approval of both the maintainer and
the scholars' review board. Software never writes that approval.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from rdflib import Namespace, URIRef
from rdflib.namespace import RDFS

import display
from model import CRM, MRS, Claim, Entity, Site

TIME = Namespace("http://www.w3.org/2006/time#")
MRSV = Namespace("https://w3id.org/marsad/vocab/")
PREFIXES = {"mrs": str(MRS), "mrsv": str(MRSV)}

# Allen relations recorded on a relative date anchor that give an order.
BEFORE = {TIME.before, TIME.intervalBefore, TIME.intervalMeets}
AFTER = {TIME.after, TIME.intervalAfter, TIME.intervalMetBy}
# Event-to-event claims that give an order: subject before object, or after it.
CLAIM_BEFORE = {MRS.rel_preceded}
CLAIM_AFTER = {MRS.rel_followed}

STEP_TYPES = ("events", "people", "stories")
EVENT_KINDS = ("event", "story")
FOLLOW = ("part_of", "date_anchor", "event_claim")
ORDERS = {"events": ("recorded",), "people": ("prophet_first_then_name", "name"), "stories": ("story",)}
DOORS = ("study", "discover")          # study: evidence first; discover: story first (R9)
APPROVERS = ("maintainer", "review_board")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
KEY = re.compile(r"^[a-z_]+(?:\.[a-z0-9_]+)+$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class RuleError(ValueError):
    """A journey file that does not follow the rule language."""


# --------------------------------------------------------------------------- the rule file
def _keys(d: dict, allowed: set, required: set, where: str):
    if not isinstance(d, dict):
        raise RuleError(f"{where}: expected an object")
    extra, missing = set(d) - allowed, required - set(d)
    if extra:
        raise RuleError(f"{where}: unknown key(s) {sorted(extra)}")
    if missing:
        raise RuleError(f"{where}: missing key(s) {sorted(missing)}")


def _words(v, where: str) -> list[str]:
    if not isinstance(v, list) or not v or not all(isinstance(w, str) and re.fullmatch(r"[A-Za-z][A-Za-z'-]*", w) for w in v):
        raise RuleError(f"{where}: 'words' must be a non-empty list of plain words")
    return v


def _named(d: dict, where: str):
    _keys(d, {"kinds", "words"}, {"kinds", "words"}, where)
    if not d["kinds"] or any(k not in EVENT_KINDS for k in d["kinds"]):
        raise RuleError(f"{where}: kinds must be some of {EVENT_KINDS}")
    _words(d["words"], where)


def _event_rule(d: dict, where: str):
    _keys(d, {"named", "follow", "max_links"}, {"named", "follow", "max_links"}, where)
    _named(d["named"], f"{where}.named")
    if any(f not in FOLLOW for f in d["follow"]):
        raise RuleError(f"{where}: follow must be some of {FOLLOW}")
    if not isinstance(d["max_links"], int) or not 0 <= d["max_links"] <= 3:
        raise RuleError(f"{where}: max_links must be an integer from 0 to 3")


def term(curie: str, where: str) -> URIRef:
    """'mrs:rel_led' -> the IRI. Only ontology and vocabulary terms; never an entity."""
    m = re.fullmatch(r"(mrs|mrsv):([A-Za-z_][A-Za-z0-9_]*)", curie or "")
    if not m:
        raise RuleError(f"{where}: {curie!r} is not an ontology term like 'mrs:rel_led'")
    return URIRef(PREFIXES[m.group(1)] + m.group(2))


def validate(spec: dict, stem: str | None = None) -> dict:
    """Check a journey file against the rule language. Returns the spec."""
    _keys(spec, {"slug", "status", "approved_by", "title", "lead", "door", "select", "order"},
          {"slug", "status", "approved_by", "title", "lead", "door", "select", "order"}, "journey")
    slug = spec["slug"]
    if not isinstance(slug, str) or not SLUG.match(slug):
        raise RuleError(f"slug {slug!r} must be lower-case words joined by hyphens")
    if stem is not None and stem != slug:
        raise RuleError(f"{slug}: the file must be named {slug}.json")
    for k in ("title", "lead"):
        if not isinstance(spec[k], str) or not KEY.match(spec[k]):
            raise RuleError(f"{slug}: {k} must be an i18n key")
    if spec["door"] not in DOORS:
        raise RuleError(f"{slug}: door must be one of {DOORS}")
    approvals = spec["approved_by"]
    if not isinstance(approvals, list):
        raise RuleError(f"{slug}: approved_by must be a list")
    for i, a in enumerate(approvals):
        _keys(a, {"who", "date", "note"}, {"who", "date"}, f"{slug}.approved_by[{i}]")
        if a["who"] not in APPROVERS or not DATE.match(str(a["date"])):
            raise RuleError(f"{slug}.approved_by[{i}]: who must be one of {APPROVERS}, date YYYY-MM-DD")
    if spec["status"] not in ("draft", "approved"):
        raise RuleError(f"{slug}: status must be draft or approved")
    if spec["status"] == "approved" and {a["who"] for a in approvals} != set(APPROVERS):
        raise RuleError(f"{slug}: approved needs a recorded approval from both {APPROVERS}")
    sel = spec["select"]
    if not isinstance(sel, dict) or sel.get("type") not in STEP_TYPES:
        raise RuleError(f"{slug}: select.type must be one of {STEP_TYPES}")
    t = sel["type"]
    if t == "events":
        rest = {k: v for k, v in sel.items() if k != "type"}
        _event_rule(rest, f"{slug}.select")
    elif t == "people":
        _keys(sel, {"type", "events", "participation", "also_show", "set_apart"},
              {"type", "events", "participation", "also_show", "set_apart"}, f"{slug}.select")
        _event_rule(sel["events"], f"{slug}.select.events")
        p = sel["participation"]
        _keys(p, {"records", "claims"}, {"records", "claims"}, f"{slug}.select.participation")
        if not isinstance(p["records"], bool) or not isinstance(p["claims"], list):
            raise RuleError(f"{slug}.select.participation: records is true/false, claims a list")
        for c in p["claims"] + sel["also_show"] + sel["set_apart"]:
            term(c, f"{slug}.select")
        if not p["records"] and not p["claims"]:
            raise RuleError(f"{slug}.select.participation: nothing would choose a person")
    else:
        _keys(sel, {"type", "part"}, {"type", "part"}, f"{slug}.select")
        _keys(sel["part"], {"words"}, {"words"}, f"{slug}.select.part")
        _words(sel["part"]["words"], f"{slug}.select.part")
    if spec["order"] not in ORDERS[t]:
        raise RuleError(f"{slug}: order for {t} must be one of {ORDERS[t]}")
    return spec


def load_specs(folder: Path) -> list[dict]:
    specs = []
    for path in sorted(Path(folder).glob("*.json")):
        spec = json.loads(path.read_text(encoding="utf-8"))
        specs.append(validate(spec, path.stem))
    slugs = [s["slug"] for s in specs]
    if len(slugs) != len(set(slugs)):
        raise RuleError("two journeys share a slug")
    return specs


# --------------------------------------------------------------------------- results
@dataclass
class Reason:
    """Why a step is in the journey: a matched word, or a link to another step."""
    kind: str   # named | part_of | has_part | date_after | date_before | date_related | dated_after_this |
                # dated_before_this | dated_related_this | event_claim | part
    other: str | None = None       # IRI of the linked entity
    word: str | None = None        # the matched word (named) or part title (part)
    label: str | None = None       # relation label for event_claim (data string)
    claims: list[Claim] = field(default_factory=list)   # the claims behind the link, with status


@dataclass
class Step:
    entity: Entity
    reasons: list[Reason] = field(default_factory=list)  # why it was chosen
    links: list[Reason] = field(default_factory=list)    # its other recorded links to steps of the journey
    records: list[Claim] = field(default_factory=list)   # people: records that choose them; stories: people named
    contrary: list[Claim] = field(default_factory=list)  # shown beside, never used to choose
    order_note: str | None = None  # None (first) | part | recorded | unrecorded
    order_ref: str | None = None   # IRI of the step the note refers to
    hop: int = 0

    @property
    def iri(self) -> str:
        return self.entity.iri


@dataclass
class Journey:
    spec: dict
    steps: list[Step]
    set_apart: list[Step] = field(default_factory=list)
    anchors: list[str] = field(default_factory=list)     # IRIs of the events a people journey hangs on
    part_labels: list[str] = field(default_factory=list)  # stories journey: the matching part titles
    universe: int = 0              # how many entities of the step kind(s) the record holds
    mixes_stories_and_events: bool = False
    order_conflict: bool = False   # the record's order links contradicted each other

    @property
    def slug(self) -> str:
        return self.spec["slug"]

    @property
    def is_draft(self) -> bool:
        return self.spec["status"] != "approved"


# --------------------------------------------------------------------------- helpers
def tokens(label: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", display.fold(label).lower()))


def name_matches(site: Site, iri: str, words: list[str]) -> str | None:
    """The first rule word found as a whole word in any recorded label of the entity."""
    toks = set()
    for lab in site.g.objects(URIRef(iri), RDFS.label):
        toks |= tokens(str(lab))
    for w in words:
        if w.lower() in toks:
            return w
    return None


def claim_node(site: Site, c: Claim, prop):
    return site.g.value(URIRef(c.node), prop) if c.node else None


def claim_qualifiers(site: Site, c: Claim) -> set[URIRef]:
    return set(site.g.objects(URIRef(c.node), MRS.qualifier)) if c.node else set()


def _bounds(ent: Entity) -> tuple[str | None, str | None]:
    """Earliest recorded start and latest recorded end over all the entity's dates."""
    lo = hi = None
    for x in ent.data.get("dates") or []:
        e, l = x.get("earliest"), x.get("latest")
        if not e or not l:
            continue
        lo = e if lo is None or e < lo else lo
        hi = l if hi is None or l > hi else hi
    return lo, hi


def _iso_key(s: str) -> tuple:
    """Sort key for xsd:dateTime text, with negative years before positive ones."""
    m = re.match(r"^(-?)(\d+)-(\d\d)-(\d\d)(.*)$", s)
    if not m:
        return (0, s)
    year = int(m.group(2)) * (-1 if m.group(1) else 1)
    return (year, m.group(3), m.group(4), m.group(5))


# --------------------------------------------------------------------------- event links
class Links:
    """Every recorded link between two event or story entities, both directions."""

    def __init__(self, site: Site):
        self.site = site
        g = site.g
        self.events = {e.iri for k in EVENT_KINDS for e in site.by_kind[k]}
        self.adj: dict[str, list[tuple[str, str, Reason]]] = {}     # iri -> [(other, follow, reason shown on other)]
        self.about: dict[str, list[tuple[str, str, Reason]]] = {}   # iri -> [(other, follow, reason shown on iri)]
        self.order: list[tuple[str, str, str]] = []                  # (before, after, kind)
        self.whole_of: dict[str, set[str]] = {}                      # part -> wholes
        # part-of claims and other event-to-event claims
        self.by_node: dict[str, Claim] = {}
        for cs in site.claims.values():
            for c in cs:
                if c.kind == "assertion" and c.node:
                    self.by_node[c.node] = c
        for node in sorted(self.by_node):
            c = self.by_node[node]
            if c.subject not in self.events or c.object not in self.events or c.subject == c.object:
                continue
            pred = g.value(URIRef(node), MRS.predicate)
            if pred == MRS.rel_part_of:
                self._part(c.subject, c.object, [c])
            else:
                self._add(c.subject, c.object, "event_claim",
                          Reason("event_claim", other=c.subject, label=c.predicate, claims=[c]),
                          Reason("event_claim", other=c.object, label=c.predicate, claims=[c]))
                if pred in CLAIM_BEFORE:
                    self.order.append((c.subject, c.object, "claim"))
                elif pred in CLAIM_AFTER:
                    self.order.append((c.object, c.subject, "claim"))
        # plain part-of triples (no status of their own)
        for s, o in sorted(g.subject_objects(CRM.P9i_forms_part_of), key=lambda t: (str(t[0]), str(t[1]))):
            s, o = str(s), str(o)
            if s in self.events and o in self.events and s != o:
                if not any(b == o and f == "part_of" for b, f, _ in self.adj.get(s, [])):
                    self._part(s, o, [])
        # relative date anchors recorded on an event's date
        for ev in sorted(self.events):
            for te in sorted(g.objects(URIRef(ev), MRS.eventTemporalExtent), key=str):
                for ra in sorted(g.objects(te, MRS.relativeAnchor), key=lambda n: (str(g.value(n, MRS.anchorTarget)), str(g.value(n, MRS.allenRelation)))):
                    target = g.value(ra, MRS.anchorTarget)
                    rel = g.value(ra, MRS.allenRelation)
                    if target is None or str(target) not in self.events or str(target) == ev:
                        continue
                    claims = self.claims_for(g.objects(ra, MRS.attestedBy))
                    t = str(target)
                    if rel in AFTER:
                        self.order.append((t, ev, "anchor"))
                        kind_ev, kind_t = "date_after", "dated_after_this"
                    elif rel in BEFORE:
                        self.order.append((ev, t, "anchor"))
                        kind_ev, kind_t = "date_before", "dated_before_this"
                    else:
                        kind_ev, kind_t = "date_related", "dated_related_this"
                    # the reason shown on t names ev, and the reason shown on ev names t
                    self._add(ev, t, "date_anchor",
                              Reason(kind_t, other=ev, claims=claims),
                              Reason(kind_ev, other=t, claims=claims))

    def claims_for(self, nodes) -> list[Claim]:
        """The site's Claim objects for the given assertion nodes, in a stable order."""
        return [self.by_node[n] for n in sorted({str(x) for x in nodes}) if n in self.by_node]

    def _add(self, a: str, b: str, follow: str, reason_for_b_about_a: Reason, reason_for_a_about_b: Reason):
        """adj[a] holds (b, follow, the reason shown on b, which names a); about[b] holds
        the same reason as (a, follow, reason)."""
        self.adj.setdefault(a, []).append((b, follow, reason_for_b_about_a))
        self.adj.setdefault(b, []).append((a, follow, reason_for_a_about_b))
        self.about.setdefault(b, []).append((a, follow, reason_for_b_about_a))
        self.about.setdefault(a, []).append((b, follow, reason_for_a_about_b))

    def _part(self, part: str, whole: str, claims: list[Claim]):
        self.whole_of.setdefault(part, set()).add(whole)
        self._add(part, whole, "part_of",
                  Reason("has_part", other=part, claims=claims),     # on the whole: it has this part
                  Reason("part_of", other=whole, claims=claims))     # on the part: it is part of the whole


def select_events(site: Site, links: Links, rule: dict) -> tuple[dict[str, int], dict[str, list[Reason]]]:
    """BFS from the named events. Returns (hop per IRI, reasons per IRI)."""
    named = rule["named"]
    hop: dict[str, int] = {}
    reasons: dict[str, list[Reason]] = {}
    for kind in named["kinds"]:
        for e in site.by_kind[kind]:
            w = name_matches(site, e.iri, named["words"])
            if w:
                hop[e.iri] = 0
                reasons[e.iri] = [Reason("named", word=w)]
    frontier = sorted(hop)
    for depth in range(1, rule["max_links"] + 1):
        nxt = []
        for iri in frontier:
            for other, follow, reason in links.adj.get(iri, []):
                if follow not in rule["follow"] or other == iri:
                    continue
                if other not in hop:
                    hop[other] = depth
                    reasons[other] = []
                    nxt.append(other)
                # the reason shown on `other` names `iri`, the step it was reached from
                if hop[other] == depth and reason not in reasons[other]:
                    reasons[other].append(reason)
        frontier = sorted(set(nxt))
    return hop, reasons


# --------------------------------------------------------------------------- ordering
def _order_events(site: Site, links: Links, chosen: list[str]) -> tuple[list[str], dict, bool]:
    """Topological order from recorded dates, before/after links and part-of (a part
    follows its whole). Ties: dated before undated, then date, then story number, then
    name. Returns (order, notes, conflict)."""
    ents = {i: site.entity(i) for i in chosen}
    sel = set(chosen)
    recorded: set[tuple[str, str]] = set()
    for a, b, _kind in links.order:
        if a in sel and b in sel:
            recorded.add((a, b))
    bounds = {i: _bounds(ents[i]) for i in chosen}
    dated: set[tuple[str, str]] = set()
    for a in chosen:
        for b in chosen:
            (alo, ahi), (blo, bhi) = bounds[a], bounds[b]
            if a != b and ahi and blo and _iso_key(ahi) < _iso_key(blo):
                dated.add((a, b))
    parts: set[tuple[str, str]] = set()
    whole_in_sel = {p: sorted(w for w in links.whole_of.get(p, ()) if w in sel) for p in chosen}
    for p, ws in whole_in_sel.items():
        for w in ws:
            parts.add((w, p))

    def key(i: str):
        e = ents[i]
        lo, _ = bounds[i]
        n = e.data.get("number") if e.kind == "story" else None
        return (lo is None, _iso_key(lo) if lo else (), n is None, n or 0, display.sort_key(e.name), e.pid)

    conflict = False
    order: list[str] = []
    used: set = set()
    for edges in (recorded | dated | parts, recorded | dated, recorded, set()):
        found = _kahn(chosen, edges, whole_in_sel, key)
        if found is not None:
            order, used = found, edges
            break
        conflict = True
    # notes: how each step's place relates to the step before it. A recorded order
    # (dates, before/after links) is named first; a part follows its whole; otherwise
    # the record gives no order and the tie-break rule placed it.
    closure = _closure(chosen, used & (recorded | dated))
    notes: dict[str, tuple[str | None, str | None]] = {}
    for idx, i in enumerate(order):
        if idx == 0:
            notes[i] = (None, None)
            continue
        prev = order[idx - 1]
        ws = [w for w in whole_in_sel[i] if order.index(w) < idx]
        if (prev, i) in closure:
            notes[i] = ("recorded", prev)
        elif ws and (ws[0], i) in used:
            notes[i] = ("part", ws[0])
        else:
            notes[i] = ("unrecorded", prev)
    return order, notes, conflict


def _kahn(nodes: list[str], edges: set, whole_in_sel: dict, key) -> list[str] | None:
    succ: dict[str, set[str]] = {n: set() for n in nodes}
    indeg: dict[str, int] = {n: 0 for n in nodes}
    for a, b in edges:
        if b not in succ[a]:
            succ[a].add(b)
            indeg[b] += 1
    ready = {n for n in nodes if indeg[n] == 0}
    out: list[str] = []
    open_wholes: list[str] = []
    while ready:
        pick = None
        for w in reversed(open_wholes):          # keep parts right after their whole
            cands = [n for n in ready if w in whole_in_sel.get(n, ())]
            if cands:
                pick = min(cands, key=key)
                break
        if pick is None:
            pick = min(ready, key=key)
        ready.discard(pick)
        out.append(pick)
        if any(pick in whole_in_sel.get(n, ()) for n in nodes):
            open_wholes.append(pick)
        for b in sorted(succ[pick]):
            indeg[b] -= 1
            if indeg[b] == 0:
                ready.add(b)
    return out if len(out) == len(nodes) else None


def _closure(nodes: list[str], edges: set) -> set[tuple[str, str]]:
    succ: dict[str, set[str]] = {n: set() for n in nodes}
    for a, b in edges:
        succ[a].add(b)
    out = set()
    for n in nodes:
        stack, seen = list(succ[n]), set()
        while stack:
            m = stack.pop()
            if m in seen:
                continue
            seen.add(m)
            out.add((n, m))
            stack.extend(succ[m])
    return out


# --------------------------------------------------------------------------- the three step types
def build_events(site: Site, links: Links, spec: dict) -> Journey:
    rule = spec["select"]
    hop, reasons = select_events(site, links, rule)
    chosen = sorted(hop)
    order, notes, conflict = _order_events(site, links, chosen)
    sel = set(chosen)
    steps = []
    for i in order:
        st = Step(entity=site.entity(i), reasons=reasons[i], hop=hop[i])
        st.order_note, st.order_ref = notes[i]
        for other, follow, r in links.about.get(i, []):
            if other in sel and follow in rule["follow"] and r not in st.reasons and r not in st.links:
                st.links.append(r)
        pos = {x: n for n, x in enumerate(order)}
        st.links.sort(key=lambda r: (pos.get(r.other, 10**6), r.kind))
        steps.append(st)
    kinds = {s.entity.kind for s in steps}
    universe = sum(len(site.by_kind[k]) for k in EVENT_KINDS)
    return Journey(spec, steps, universe=universe, order_conflict=conflict,
                   mixes_stories_and_events=kinds == {"event", "story"})


def build_people(site: Site, links: Links, spec: dict) -> Journey:
    rule = spec["select"]
    hop, _reasons = select_events(site, links, rule["events"])
    anchors = sorted(hop, key=lambda i: (site.entity(i).kind == "story", site.entity(i).data.get("number") or 0,
                                         display.sort_key(site.entity(i).name), i))
    want = {term(c, "claims") for c in rule["participation"]["claims"]}
    also = {term(c, "also_show") for c in rule["also_show"]}
    apart = {term(q, "set_apart") for q in rule["set_apart"]}
    records: dict[str, list[Claim]] = {}
    contrary: dict[str, list[Claim]] = {}
    for ev in anchors:
        for c in site.claims.get(ev, []):
            if c.object != ev:
                continue
            who = site.entity(c.subject)
            if who is None or who.kind != "person":
                continue
            if c.kind == "participation":
                if rule["participation"]["records"]:
                    records.setdefault(who.iri, []).append(c)
            elif c.kind == "assertion":
                pred = claim_node(site, c, MRS.predicate)
                if pred in want:
                    records.setdefault(who.iri, []).append(c)
                elif pred in also:
                    contrary.setdefault(who.iri, []).append(c)
    anchor_pos = {a: n for n, a in enumerate(anchors)}

    def rec_key(c: Claim):
        return (anchor_pos.get(c.object, 10**6), c.kind != "participation", c.predicate, c.node or "")

    steps, set_apart = [], []
    for iri, recs in records.items():
        st = Step(entity=site.entity(iri), records=sorted(recs, key=rec_key),
                  contrary=sorted(contrary.get(iri, []), key=rec_key))
        if apart and all(claim_qualifiers(site, c) & apart for c in recs if c.kind == "assertion") \
                and not any(c.kind == "participation" for c in recs):
            set_apart.append(st)
        else:
            steps.append(st)

    def person_key(st: Step):
        first = spec["order"] == "prophet_first_then_name" and st.entity.prophet
        return (not first, display.sort_key(st.entity.name), st.entity.pid)

    steps.sort(key=person_key)
    set_apart.sort(key=person_key)
    kinds = {site.entity(a).kind for a in anchors}
    return Journey(spec, steps, set_apart=set_apart, anchors=anchors, universe=len(site.by_kind["person"]),
                   mixes_stories_and_events=kinds == {"event", "story"})


def build_stories(site: Site, spec: dict) -> Journey:
    words = spec["select"]["part"]["words"]
    parts: dict[str, str] = {}
    chosen = []
    for e in site.stories_in_order():
        label = e.data.get("part_label")
        if not label:
            continue
        toks = tokens(label)
        if any(w.lower() in toks for w in words):
            parts.setdefault(label, label)
            chosen.append(e)
    steps = []
    for e in chosen:
        named = [c for c in site.claims.get(e.iri, []) if c.kind == "assertion" and c.object == e.iri
                 and site.entity(c.subject) is not None]
        named.sort(key=lambda c: (display.sort_key(site.entity(c.subject).name), c.node or ""))
        steps.append(Step(entity=e, records=named,
                          reasons=[Reason("part", word=e.data.get("part_label"))]))
    return Journey(spec, steps, part_labels=sorted(parts), universe=len(site.by_kind["story"]))


def build(site: Site, spec: dict, links: Links | None = None) -> Journey:
    links = links or Links(site)
    t = spec["select"]["type"]
    if t == "events":
        j = build_events(site, links, spec)
    elif t == "people":
        j = build_people(site, links, spec)
    else:
        j = build_stories(site, spec)
    if not j.steps:
        raise RuleError(f"{spec['slug']}: the rule chose no step in this graph")
    return j


def build_all(site: Site, specs: list[dict]) -> list[Journey]:
    links = Links(site)
    return [build(site, s, links) for s in specs]
