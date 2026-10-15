"""Gathers what the Lifelines view may draw, from sourced records only.

Sources, in the order they are read:
  1. build/graph.ttl, through site/model.py (names, events, participations, deaths, births,
     ṭabaqa, kinship and membership claims). Graph dates are fields, not claims: they
     carry no status of their own.
  2. Proposed Wikidata dates (ontology/corpus/external-dates.csv, written by slice 5).
  3. Proposed Ibn Hishām claims (slice 4): ages as given at events (mrs:rel_age_at), births and
     deaths during an event (mrs:rel_born_during / rel_died_during), dates as written
     (mrs:rel_dated), and birth/death events (crm:E67_Birth / crm:E69_Death).
     Ages as given are never converted: the text does not say lunar or solar years.

Nothing here invents a date. A person is drawn only when at least one birth or death
date with a source can be placed on the axis; everyone else goes on the "no dates
recorded yet" list. Entity IDs are never written in this file: people, events and
vocabulary are found by type and by predicate.
"""
from __future__ import annotations

import csv
import io
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS

import calendars as cal
import display

MRS = Namespace("https://w3id.org/marsad/core#")
PROV = Namespace("http://www.w3.org/ns/prov#")
CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
ID_BASE = "https://w3id.org/marsad/id/"

# Relation types that mean "took part in" an event. "absent from" is deliberately not here.
TOOK_PART = ("rel_participated_in", "rel_led", "rel_witnessed", "rel_present_at",
             "rel_pledged_allegiance_to", "rel_party_to_treaty_with")
MEMBER_OF = "rel_member_of"
# Ibn Hishām lifeline relations (slice 4)
REL_AGE_AT, REL_BORN_DURING, REL_DIED_DURING, REL_DATED = "rel_age_at", "rel_born_during", "rel_died_during", "rel_dated"
KINSHIP_CLASS = "relclass_kinship"
SPATIAL_CLASS = "relclass_spatial"
PARENT_OF = ("rel_father_of", "rel_mother_of")          # subject is the parent
CHILD_OF = ("rel_child_of",)                            # subject is the child
SPOUSE_OF = ("rel_spouse_of", "rel_divorced_from")
SIBLING_OF = ("rel_sibling_of",)

# Wikidata calendar models (vocabulary, not entity IDs of this project)
WD_JULIAN = ("Q1985786", "julian")
WD_GREGORIAN = ("Q1985727", "gregorian")
USABLE_MATCH = ("exact", "probable")


def _local(iri) -> str:
    return re.split(r"[#/]", str(iri))[-1]


@dataclass
class DateClaim:
    kind: str                       # birth | death
    lo: int | None                  # day numbers; None when the value cannot be placed
    hi: int | None
    precision: str | None
    text: str                       # Gregorian first, Hijri beside it
    notes: list[str]
    source: dict                    # {type, label, href?, detail, status, confidence?}
    review: bool = False            # True: identity match needs review (hidden by default)
    alt: bool = False               # an alternative value (Wikidata normal rank beside a preferred one): listed, not drawn

    @property
    def drawable(self) -> bool:
        return self.lo is not None and self.hi is not None and self.lo <= self.hi and not self.alt


@dataclass
class AgeClaim:
    person: str                     # IRIs
    event: str
    values: list[float]             # the numbers as given, one per alternative; never converted
    written: str | None             # the age exactly as written (Arabic)
    source: dict


@dataclass
class Person:
    iri: str
    pid: str
    name: str
    sort: str
    prophet: bool
    tabaqa: str | None
    agents: list[str]
    claims: list[DateClaim] = field(default_factory=list)
    kin: int | None = None
    tribes: list[str] = field(default_factory=list)
    other_candidates: list[str] = field(default_factory=list)   # Wikidata items not used (need review)
    ambiguous: bool = False         # several candidate items, none usable: nothing drawn from them


@dataclass
class Event:
    iri: str
    pid: str
    kind: str                       # event | story
    name: str
    lo: int | None
    hi: int | None
    text: str
    notes: list[str]
    disputed: bool
    agents: list[str]
    parts: list[dict] = field(default_factory=list)   # {person, how, status, citation, ai}
    places: list[str] = field(default_factory=list)  # place IRIs the event is recorded at


class Collector:
    def __init__(self, site, t, root: Path, external_csv: str | None = None,
                 external_label: str | None = None, renames: dict | None = None):
        self.site, self.g, self.t, self.root = site, site.g, t, root
        self.renames = renames or {}
        self.warnings: list[str] = []
        self.people: dict[str, Person] = {}
        self.events: dict[str, Event] = {}
        self.ties: dict[str, set[str]] = {}
        self.kin_ties: list[dict] = []
        self.place_links: list[dict] = []      # person -> place claims with no date (shown in words)
        self.residences: list[dict] = []       # person -> place affiliations with a placed extent
        self.external_label = external_label
        self.ages: list[AgeClaim] = []
        self._load_people()
        self._load_graph_dates()
        if external_csv is not None:
            self._load_external(external_csv)
        self._load_events()
        self._load_ibn_hisham()
        self._date_life_events()
        self._load_kinship_and_membership()

    # ------------------------------------------------------------ people
    def _load_people(self):
        for e in self.site.by_kind["person"]:
            self.people[e.iri] = Person(
                iri=e.iri, pid=e.pid, name=e.name, sort=display.sort_key(e.name),
                prophet=e.prophet, tabaqa=e.data.get("tabaqa"),
                agents=[a.label for a in e.agents])

    def _graph_source(self, person: Person, ext: dict) -> dict:
        return {"type": "graph", "label": self.t("src.graph"),
                "detail": self.t("src.graph_detail", agents=", ".join(person.agents) or self.t("src.unknown_agent")),
                "status": None}

    def _dual_text(self, ext_text: str | None, lo: int | None, hi: int | None) -> tuple[str, list[str]]:
        """Recorded text as display.py formats it; a Hijri reading is added (marked
        computed) only when the recorded text has none."""
        notes = []
        text = ext_text or ""
        ah = self.t("date.ah")
        if lo is not None and hi is not None and not re.search(rf"\b{re.escape(ah)}\b", text):
            notes.append(self.t("date.hijri_computed",
                                value=cal.hijri_years_text(lo, hi, ah, self.t("date.bh"))))
        return text, notes

    def _extent_claim(self, kind: str, person: Person, ext: dict) -> DateClaim:
        lo = cal.jdn_from_iso_bound(ext["earliest"]) if ext.get("earliest") else None
        hi = cal.jdn_from_iso_bound(ext["latest"]) if ext.get("latest") else None
        if lo is None or hi is None:
            lo = hi = None                      # open or relative: shown in words, not drawn
        fmt = display.format_extent(ext, self.t)
        text, extra = self._dual_text(fmt["text"], lo, hi)
        notes = list(fmt["notes"]) + extra
        if lo is None:
            notes.append(self.t("date.not_placed"))
        return DateClaim(kind=kind, lo=lo, hi=hi, precision=ext.get("precision"), text=text,
                         notes=notes, source=self._graph_source(person, ext))

    def _load_graph_dates(self):
        g = self.g
        for p in self.people.values():
            node = URIRef(p.iri)
            for kind, prop in (("birth", MRS.birth), ("death", MRS.death)):
                for ev in g.objects(node, prop):
                    for ext in self.site.extents(ev, MRS.eventTemporalExtent):
                        p.claims.append(self._extent_claim(kind, p, ext))

    # ------------------------------------------------------------ external (Wikidata) dates
    @staticmethod
    def _norm(h: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", (h or "").strip().lower()).strip("_")

    _ALIASES = {
        "id": ("canonical_id", "id", "entity", "entity_id"),
        "qid": ("external_id", "qid", "wikidata", "wikidata_id", "wikidata_qid", "item"),
        "kind": ("property", "kind", "date_kind", "birth_death", "event", "field", "which", "type", "date_type"),
        "value": ("value", "date", "time", "time_value", "date_value"),
        "precision": ("precision", "wikidata_precision", "date_precision"),
        "calendar": ("calendar_model", "calendar", "calendarmodel", "calendar_model_qid"),
        "confidence": ("match_confidence", "confidence", "match"),
        "status": ("status",),
        "rank": ("rank",),
        "qualifiers": ("qualifiers",),
        "note": ("note", "notes"),
    }
    _QUAL_REFINE = re.compile(r"^P4241\b[^:]*:\s*(\d{1,4})\s*AH\b")
    _QUAL_TIME = re.compile(r"^(P1319|P1326)\b[^:]*:\s*([+-]?\d{1,6}-\d\d-\d\dT\S*)\s*\((\w+),\s*(\w+)\)")

    def _load_external(self, text: str):
        """Rows of external-dates.csv (slice 5). Per person, only one Wikidata item is used:
        the exact match, else a single probable one. Statements of that item that differ
        are all kept (drawn as their union). Needs-review candidates are used only for a
        person with no exact or probable match, and only when there is a single one;
        several candidates are never mixed, since they may be different people."""
        rows = list(csv.reader(io.StringIO(text)))
        if not rows:
            return
        header = [self._norm(h) for h in rows[0]]
        col = {}
        for key, names in self._ALIASES.items():
            for n in names:
                if n in header:
                    col[key] = header.index(n)
                    break
        missing = [k for k in ("id", "qid", "kind", "value", "precision", "calendar", "confidence") if k not in col]
        if missing:
            self.warnings.append(f"external dates: columns not found {missing}; file not used")
            return
        by_pid = {p.pid: p for p in self.people.values()}
        recs: dict[str, list[dict]] = {}
        for row in rows[1:]:
            if not row:
                continue
            get = lambda k, row=row: (row[col[k]].strip() if k in col and col[k] < len(row) else "")
            cid = self.renames.get(get("id"), get("id"))
            person = by_pid.get(cid.split(":", 1)[-1])
            kind = get("kind").lower()
            kind = "birth" if ("birth" in kind or kind == "p569") else "death" if ("death" in kind or kind == "p570") else None
            conf = get("confidence").lower().replace("_", "-")
            if person is None or kind is None or conf not in USABLE_MATCH + ("needs-review",):
                continue
            recs.setdefault(person.iri, []).append({k: get(k) for k in col} | {"kind": kind, "conf": conf})
        used = 0
        for iri, rs in recs.items():
            person = self.people[iri]
            qids = lambda c: sorted({r["qid"] for r in rs if r["conf"] == c})
            exact, probable, review = qids("exact"), qids("probable"), qids("needs-review")
            if len(exact) == 1:
                chosen, is_review = exact, False
            elif not exact and len(probable) == 1:
                chosen, is_review = probable, False
            else:
                review = sorted(set(review) | set(exact) | set(probable))
                chosen, is_review = (review, True) if len(review) == 1 else ([], True)
            for r in rs:
                if r["qid"] in chosen:
                    # Wikidata's preferred rank, where a person has one, is drawn; the item's
                    # other values are listed beside it as alternatives, not drawn
                    alt = (r.get("rank", "").lower() != "preferred" and
                           any(x.get("rank", "").lower() == "preferred" for x in rs
                               if x["qid"] == r["qid"] and x["kind"] == r["kind"]))
                    claim = self._wikidata_claim(r, is_review)
                    if claim:
                        claim.alt = alt
                        if alt:
                            claim.notes.insert(0, self.t("src.wikidata_alternative"))
                        person.claims.append(claim)
                        used += 1
            others = sorted({r["qid"] for r in rs} - set(chosen))
            if others:
                person.other_candidates = others
                if not chosen:
                    person.ambiguous = True
        self.external_used = used

    def _range_of(self, value: str, precision: str | None, calendar: str | None) -> tuple[int, int] | None:
        ymd = cal.parse_iso(value)
        if not ymd or precision not in cal.DRAWN_PRECISIONS or not calendar or ymd[0] <= 0:
            return None
        return cal.range_for(*ymd, precision, calendar)

    def _wikidata_claim(self, r: dict, review: bool) -> DateClaim | None:
        value, prec_raw = r["value"], r["precision"].lower()
        precision = (cal.WIKIDATA_PRECISION.get(int(prec_raw)) if prec_raw.isdigit()
                     else prec_raw if prec_raw in cal.PRECISIONS else None)
        calraw = r["calendar"]
        calendar = ("gregorian" if any(k.lower() in calraw.lower() for k in WD_GREGORIAN)
                    else "julian" if any(k.lower() in calraw.lower() for k in WD_JULIAN) else None)
        notes: list[str] = []
        rng = self._range_of(value, precision, calendar)
        if rng is None:
            notes.append(self.t("date.not_placed_precision", precision=self.t(f"precision.{precision}") if precision else prec_raw or "?")
                         if calendar else self.t("date.not_placed_calendar"))
        # earliest / latest date qualifiers widen the range; never narrow it. Day- or month-precise
        # qualifier values come from the query service, which may give a Julian date converted to
        # the Gregorian calendar, so both readings are covered.
        quals = [q.strip() for q in r.get("qualifiers", "").split(" | ") if q.strip()]
        for q in quals:
            m = self._QUAL_TIME.match(q)
            if not m or rng is None:
                continue
            qprec = m.group(3).lower()
            qcal = "gregorian" if "greg" in m.group(4).lower() else "julian"
            cands = [self._range_of(m.group(2), qprec, qcal)]
            if qprec in ("day", "month"):
                cands.append(self._range_of(m.group(2), qprec, "gregorian" if qcal == "julian" else "julian"))
            cands = [c for c in cands if c]
            if cands:
                rng = (min([rng[0]] + [c[0] for c in cands]), max([rng[1]] + [c[1] for c in cands]))
                notes.append(self.t("date.qualifier_range", value=q))
        for q in quals:
            m = self._QUAL_REFINE.match(q)
            if m and rng is not None:            # "refine date: 74 AH": the range also covers that Hijri year
                y = int(m.group(1))
                rng = (min(rng[0], cal.hijri_year_start(y)), max(rng[1], cal.hijri_year_start(y + 1) - 1))
                notes.append(self.t("date.qualifier_range", value=q))
        lo, hi = rng if rng else (None, None)
        qid = r["qid"].rsplit("/", 1)[-1]
        text = self._ce_text(lo, hi, precision) if lo is not None else value
        if lo is not None:
            notes.append(self.t("date.hijri_computed",
                                value=cal.hijri_years_text(lo, hi, self.t("date.ah"), self.t("date.bh"))))
            if calendar == "gregorian" and precision in ("day", "month"):
                notes.append(self.t("date.from_gregorian"))
        notes.append(self.t("src.wikidata_value", value=value,
                            precision=self.t(f"precision.{precision}") if precision else prec_raw or "?",
                            calendar=self.t(f"calendar.{calendar}") if calendar else (calraw or "?")))
        if r.get("rank"):
            notes.append(self.t("src.wikidata_rank", rank=r["rank"]))
        for q in quals:
            if not self._QUAL_TIME.match(q) and not self._QUAL_REFINE.match(q):
                notes.append(self.t("src.wikidata_qualifier", value=q))
        if r.get("note"):
            notes.append(self.t("src.wikidata_note", value=r["note"]))
        conf = "needs_review" if review else r["conf"]
        src = {"type": "wikidata", "label": self.t("src.wikidata", qid=qid),
               "href": f"https://www.wikidata.org/wiki/{qid}" if re.fullmatch(r"Q\d+", qid) else None,
               "detail": self.t("src.wikidata_detail", confidence=self.t(f"match.{conf}"),
                                file=self.external_label or ""),
               "status": r.get("status") or "proposed"}
        return DateClaim(kind=r["kind"], lo=lo, hi=hi, precision=precision, text=text, notes=notes,
                         source=src, review=review)

    def _ce_text(self, lo: int, hi: int, precision: str | None) -> str:
        e = "%04d-%02d-%02d" % cal.julian_from_jdn(lo)
        l = "%04d-%02d-%02d" % cal.julian_from_jdn(hi)
        return display.bounds_text(e, l, precision if precision in ("day", "month") else "year", self.t) or ""

    # ------------------------------------------------------------ events and participation
    def _load_events(self):
        g, site = self.g, self.site
        for kind in ("event", "story"):
            for e in site.by_kind[kind]:
                dates = e.data.get("dates") or []
                placed = []
                for ext in dates:
                    lo = cal.jdn_from_iso_bound(ext["earliest"]) if ext.get("earliest") else None
                    hi = cal.jdn_from_iso_bound(ext["latest"]) if ext.get("latest") else None
                    if lo is not None and hi is not None and lo <= hi:
                        placed.append((lo, hi, ext))
                texts, notes = [], []
                for ext in dates:
                    fmt = display.format_extent(ext, self.t)
                    if fmt["text"] and fmt["text"] not in texts:
                        texts.append(fmt["text"])
                    notes.extend(n for n in fmt["notes"] if n not in notes)
                lo = min(p[0] for p in placed) if placed else None
                hi = max(p[1] for p in placed) if placed else None
                if len(placed) > 1:
                    notes.append(self.t("date.several_ranges"))
                text, extra = self._dual_text(" / ".join(texts), lo, hi)
                notes.extend(extra)
                self.events[e.iri] = Event(
                    iri=e.iri, pid=e.pid, kind=kind, name=e.name, lo=lo, hi=hi, text=text, notes=notes,
                    disputed=any(x.get("disputed") or x.get("basis") == "disputed" for x in dates),
                    agents=[a.label for a in e.agents], places=list(e.data.get("places") or []))
        # participation nodes (no status of their own)
        seen = set()
        for ev_iri, ev in self.events.items():
            node = URIRef(ev_iri)
            for part in g.objects(node, MRS.hasParticipation):
                who = g.value(part, MRS.participant)
                if who is None or str(who) not in self.people:
                    continue
                role = g.value(part, MRS.participantRole)
                key = (ev_iri, str(who), "part", str(role))
                if key in seen:
                    continue
                seen.add(key)
                ev.parts.append({"person": str(who), "kind": "participation",
                                 "how": site_vocab(self.site, role) or self.t("part.took_part"),
                                 "status": None, "citation": None, "ai": False})
        # assertions whose predicate means "took part"
        for a in g.subjects(RDF.type, MRS.Assertion):
            pred = g.value(a, MRS.predicate)
            if pred is None or _local(pred) not in TOOK_PART:
                continue
            subj, obj = str(g.value(a, MRS.assertionSubject)), str(g.value(a, MRS.assertionObject))
            if subj not in self.people or obj not in self.events:
                continue
            key = (obj, subj, "assert", str(a))
            if key in seen:
                continue
            seen.add(key)
            passage = g.value(a, PROV.wasDerivedFrom)
            pinfo = self.site.passage_info(passage) if passage is not None else {}
            wi = pinfo.get("work") if pinfo else None
            self.events[obj].parts.append({
                "person": subj, "kind": "assertion", "how": self.site.vocab(pred) or _local(pred),
                "status": self.site.vkey(g.value(a, MRS.assertionStatus), "as_"),
                "citation": pinfo.get("citation") if pinfo else None,
                "work": (wi or {}).get("label") if wi else None,
                "ai": bool(wi and wi["ai"])})
        for ev in self.events.values():
            ev.parts.sort(key=lambda p: (self.people[p["person"]].sort, p["kind"], p["how"]))

    # ------------------------------------------------------------ Ibn Hishām (slice 4)
    def _load_ibn_hisham(self):
        g, t = self.g, self.t
        for a in g.subjects(RDF.type, MRS.Assertion):
            pred = g.value(a, MRS.predicate)
            name = _local(pred) if pred is not None else ""
            if name not in (REL_AGE_AT, REL_BORN_DURING, REL_DIED_DURING, REL_DATED):
                continue
            subj, obj = g.value(a, MRS.assertionSubject), g.value(a, MRS.assertionObject)
            passage = g.value(a, PROV.wasDerivedFrom)
            pinfo = self.site.passage_info(passage) if passage is not None else {}
            cit = (pinfo or {}).get("citation")
            src = {"type": "ibn-hisham", "label": t("src.ibn_hisham"), "detail": cit or "",
                   "status": self.site.vkey(g.value(a, MRS.assertionStatus), "as_")}
            if name == REL_DATED:
                ev = self.events.get(str(subj))
                if ev is not None and isinstance(obj, Literal):
                    ev.notes.append(t("ih.dated", value=str(obj), cite=cit or ""))
                continue
            person = self.people.get(str(subj))
            ev = self.events.get(str(obj)) if obj is not None else None
            if person is None:
                continue
            if name == REL_AGE_AT:
                if ev is None:
                    continue
                vals = sorted({float(str(v)) for v in g.objects(a, MRS.ageYearsAsGiven)})
                written = g.value(a, MRS.ageAsWritten)
                self.ages.append(AgeClaim(person=person.iri, event=ev.iri, values=vals,
                                          written=str(written) if written is not None else None, source=src))
                continue
            kind = "birth" if name == REL_BORN_DURING else "death"
            ev_name = ev.name if ev is not None else self.site.label_of(str(obj))
            written = g.value(a, MRS.dateAsWritten)
            notes = [t("ih.as_written", value=str(written))] if written is not None else []
            if ev is not None and ev.lo is not None:
                lo, hi = ev.lo, ev.hi
                notes.append(t("ih.dated_by_event", event=ev_name, date=ev.text))
            else:
                lo = hi = None
                notes.append(t("ih.event_undated", event=ev_name))
            person.claims.append(DateClaim(kind=kind, lo=lo, hi=hi, precision=None,
                                           text=t(f"ih.{kind}_during", event=ev_name), notes=notes, source=src))

    def _date_life_events(self):
        """A birth event (crm:E67_Birth) is that person's birth, so it takes the person's
        recorded birth date, and likewise a death event; it is said so wherever shown."""
        g, t = self.g, self.t
        for cls, prop, kind in ((CRM.E67_Birth, CRM.P98_brought_into_life, "birth"),
                                (CRM.E69_Death, CRM.P100_was_death_of, "death")):
            for node in g.subjects(RDF.type, cls):
                ev, who = self.events.get(str(node)), g.value(node, prop)
                person = self.people.get(str(who)) if who is not None else None
                if ev is None or person is None or ev.lo is not None:
                    continue
                cs = [c for c in person.claims if c.kind == kind and c.drawable and not c.review]
                if not cs:
                    ev.notes.append(t("ih.life_event_undated", name=person.name))
                    continue
                ev.lo, ev.hi = min(c.lo for c in cs), max(c.hi for c in cs)
                ev.text = " / ".join(dict.fromkeys(c.text for c in cs))
                ev.notes.append(t("ih.life_event_dated", name=person.name,
                                  sources="; ".join(dict.fromkeys(c.source["label"] for c in cs))))

    # ------------------------------------------------------------ kinship, membership, ties
    def _kin_tie(self, a, pred, subj: str, obj: str) -> dict:
        """One recorded kinship claim. For parent ties 'a' is the parent, 'b' the child."""
        g, local = self.g, _local(pred)
        a_iri, b_iri = (obj, subj) if local in CHILD_OF else (subj, obj)
        passage = g.value(a, PROV.wasDerivedFrom)
        pinfo = self.site.passage_info(passage) if passage is not None else {}
        wi = (pinfo or {}).get("work")
        basis = g.value(a, MRS.nonReportBasis)
        return {"a": a_iri, "b": b_iri, "kd": _tie_kind(local),
                "label": self.site.vocab(pred) or local,
                "status": self.site.vkey(g.value(a, MRS.assertionStatus), "as_"),
                "citation": (pinfo or {}).get("citation"), "work": (wi or {}).get("label"),
                "ai": bool(wi and wi["ai"]), "basis": str(basis) if basis is not None else None,
                "agents": [ag.label for ag in self.site.agents_of(a)]}


    def _load_kinship_and_membership(self):
        g = self.g
        parent: dict[str, str] = {}

        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        groups = {e.iri: e for e in self.site.by_kind["group"]}
        for a in g.subjects(RDF.type, MRS.Assertion):
            pred = g.value(a, MRS.predicate)
            if pred is None:
                continue
            subj, obj = str(g.value(a, MRS.assertionSubject)), str(g.value(a, MRS.assertionObject))
            rc = g.value(pred, MRS.relationClass)
            if subj in self.people and obj in self.people and subj != obj:
                self.ties.setdefault(subj, set()).add(obj)
                self.ties.setdefault(obj, set()).add(subj)
                if rc is not None and _local(rc) == KINSHIP_CLASS:
                    parent[find(subj)] = find(obj)
                    self.kin_ties.append(self._kin_tie(a, pred, subj, obj))
            if (rc is not None and _local(rc) == SPATIAL_CLASS and subj in self.people
                    and obj in self.site.entities and self.site.entities[obj].kind == "place"):
                self.place_links.append({"person": subj, "place": obj, "label": self.site.vocab(pred) or _local(pred),
                                         "status": self.site.vkey(g.value(a, MRS.assertionStatus), "as_")})
            if _local(pred) == MEMBER_OF and subj in self.people and obj in groups:
                name = groups[obj].name
                if name not in self.people[subj].tribes:
                    self.people[subj].tribes.append(name)
        for person in self.people.values():
            for aff in g.objects(URIRef(person.iri), MRS.placeAffiliation):
                place = g.value(aff, MRS.affiliatedPlace)
                ext = self.site.extent(g.value(aff, MRS.affiliationExtent))
                if place is None or not ext or not ext.get("earliest") or not ext.get("latest"):
                    continue
                self.residences.append({"person": person.iri, "place": str(place),
                                        "lo": cal.jdn_from_iso_bound(ext["earliest"]), "hi": cal.jdn_from_iso_bound(ext["latest"]),
                                        "label": self.site.vocab(g.value(aff, MRS.affiliationType)) or "",
                                        "text": display.format_extent(ext, self.t)["text"] or ""})
        comps: dict[str, list[str]] = {}
        for iri in list(parent):
            comps.setdefault(find(iri), []).append(iri)
        for i, root in enumerate(sorted(comps, key=lambda r: min(self.people[m].sort for m in comps[r]))):
            for m in comps[root]:
                self.people[m].kin = i


def _tie_kind(local: str) -> str:
    if local in PARENT_OF or local in CHILD_OF:
        return "parent"
    if local in SPOUSE_OF:
        return "spouse"
    if local in SIBLING_OF:
        return "sibling"
    return "kin"


def site_vocab(site, node):
    return site.vocab(node) if node is not None else None


def read_renames(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return {r["old_id"]: r["new_id"] for r in csv.DictReader(f)}


def read_text_source(root: Path, rel: str, branch: str) -> tuple[str | None, str | None]:
    """The file from the working tree, else from a fetched branch (git show). Returns
    (text, label) or (None, None). The caller fetches; nothing is fetched here."""
    p = root / rel
    if p.exists():
        return p.read_text(encoding="utf-8"), rel
    try:
        out = subprocess.run(["git", "show", f"origin/{branch}:{rel}"], cwd=root,
                             capture_output=True, text=True, check=True)
        sha = subprocess.run(["git", "rev-parse", "--short", f"origin/{branch}"], cwd=root,
                             capture_output=True, text=True, check=True).stdout.strip()
        return out.stdout, f"{rel} @ {branch} {sha}"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None, None
