"""Reads build/graph.ttl and exposes what the pages need as plain Python objects.

This is the only module that touches rdflib. It never reads the old islands' JSON or
Markdown, and it hard-codes no entity ID: every entity is found by its rdf:type.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import RDF, RDFS, SKOS

import display

MRS = Namespace("https://w3id.org/marsad/core#")
CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
PROV = Namespace("http://www.w3.org/ns/prov#")
DCT = Namespace("http://purl.org/dc/terms/")
ID_BASE = "https://w3id.org/marsad/id/"

KINDS = ("person", "group", "place", "event", "story")

# Ontology classes that make an entity page, most specific first.
_GROUP_TYPES = (("tribe", MRS.Tribe), ("clan", MRS.Clan), ("family", MRS.Family), ("group", MRS.Group))


@dataclass
class Lit:
    text: str
    lang: str | None = None


@dataclass
class Agent:
    label: str
    software: bool


@dataclass
class Claim:
    kind: str                     # assertion | participation | link
    subject: str
    object: str
    predicate: str                # label shown for the relation (data or i18n key, see key_label)
    predicate_is_key: bool = False
    relclass: str | None = None
    role: Lit | None = None       # the doc's own role text, or the participation role label
    qualifiers: list[str] = field(default_factory=list)
    status: str | None = None     # proposed | under_review | ... ; None = no status recorded
    basis: Lit | None = None
    passage: str | None = None
    citation: str | None = None
    story: str | None = None      # IRI of the story event the passage narrates, if any
    ai_draft: bool = False
    agents: list[Agent] = field(default_factory=list)
    node: str | None = None
    literal: Lit | None = None    # the object, when it is a text as written (rel_dated) and not an entity


@dataclass
class Entity:
    iri: str
    kind: str                     # person | group | place | event | story
    pid: str
    scholarly: str                # primary label exactly as recorded
    name: str                     # display name (popular form, honorifics)
    other_labels: list[str] = field(default_factory=list)
    arabic: list[str] = field(default_factory=list)
    other_names: list[Lit] = field(default_factory=list)   # other-language name phases
    coverage: str | None = None
    coverage_label: str | None = None
    subtype: str | None = None    # group / tribe / clan / family
    prophet: bool = False
    agents: list[Agent] = field(default_factory=list)
    recorded: list[str] = field(default_factory=list)
    # kind-specific, filled by Site
    data: dict = field(default_factory=dict)


_IRI_LIKE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")


def _local(iri) -> str:
    s = str(iri)
    return re.split(r"[#/]", s)[-1]


def _strip_prefix(local: str, prefix: str) -> str:
    return local[len(prefix):] if local.startswith(prefix) else local


class Site:
    def __init__(self, graph_path: str | Path):
        g = Graph()
        g.parse(str(graph_path), format="turtle")
        self.g = g
        self.entities: dict[str, Entity] = {}
        self.by_kind: dict[str, list[Entity]] = {k: [] for k in KINDS}
        self.claims: dict[str, list[Claim]] = defaultdict(list)   # entity IRI -> claims touching it
        self._story_passage: dict[str, URIRef] = {}
        self._load_entities()
        self._load_claims()
        self._finish()

    # ------------------------------------------------------------------ helpers
    def lits(self, s, p) -> list[Lit]:
        return [Lit(str(o), o.language) for o in self.g.objects(s, p) if isinstance(o, Literal)]

    def first_lit(self, s, p, lang_pref="en") -> Lit | None:
        ls = self.lits(s, p)
        if not ls:
            return None
        for l in ls:
            if l.lang == lang_pref:
                return l
        return ls[0]

    def vocab(self, iri) -> str | None:
        if iri is None:
            return None
        for p in (SKOS.prefLabel, RDFS.label):
            l = self.first_lit(iri, p)
            if l:
                return l.text
        return None

    def vkey(self, iri, prefix: str) -> str | None:
        return _strip_prefix(_local(iri), prefix) if iri is not None else None

    def agent(self, node) -> Agent | None:
        label = self.first_lit(node, RDFS.label)
        if not label:
            return None
        return Agent(label.text, (node, RDF.type, PROV.SoftwareAgent) in self.g)

    def agents_of(self, node) -> list[Agent]:
        out = []
        for a in self.g.objects(node, MRS.createdBy):
            ag = self.agent(a)
            if ag and ag not in out:
                out.append(ag)
        return out

    # ------------------------------------------------------------------ entities
    def _classify(self, node):
        types = set(self.g.objects(node, RDF.type))
        if MRS.Person in types:
            return "person", None
        if MRS.Place in types:
            return "place", None
        if types & {MRS.Group, MRS.Tribe, MRS.Clan, MRS.Family}:
            for name, cls in _GROUP_TYPES:
                if cls in types:
                    return "group", name
            return "group", "group"
        if types & {MRS.Event, MRS.Journey}:
            return "event", None
        return None, None

    def _load_entities(self):
        g = self.g
        # A story is an Event that a Passage of a Work narrates (slice 1c model).
        for passage in g.subjects(RDF.type, MRS.Passage):
            for ev in g.objects(passage, CRM.P67_refers_to):
                if isinstance(ev, URIRef) and self._work_of(passage) is not None:
                    self._story_passage[str(ev)] = passage
        seen_pid: dict[str, str] = {}
        for node in set(g.subjects(RDF.type, None)):
            if not isinstance(node, URIRef) or not str(node).startswith(ID_BASE):
                continue
            kind, sub = self._classify(node)
            if kind is None:
                continue
            if kind == "event" and str(node) in self._story_passage:
                kind = "story"
            pid = str(node).rsplit("/", 1)[-1]
            labels = [l.text for l in self.lits(node, RDFS.label)]
            if not labels:
                continue  # an entity without a name cannot be listed; none exist today
            # one name per entity: shortest recorded label, ties broken alphabetically
            ordered = sorted(labels, key=lambda s: (len(s), s))
            primary = ordered[0]
            prophet = kind == "person" and display.is_prophet_label(primary)
            if kind == "person":
                name = display.person_display_name(primary, prophet)
            else:
                name = display.name_display(primary)
            others, seen_names = [], {display.popularize(primary)}
            for l in ordered[1:]:
                k = display.popularize(l)
                if k not in seen_names:
                    seen_names.add(k)
                    others.append(l)
            ent = Entity(iri=str(node), kind=kind, pid=pid, scholarly=primary, name=name,
                         other_labels=others, subtype=sub, prophet=prophet)
            cov = g.value(node, MRS.coverageState)
            ent.coverage = self.vkey(cov, "cs_")
            ent.coverage_label = self.vocab(cov)
            ent.agents = self.agents_of(node)
            ent.recorded = sorted(str(o)[:10] for o in g.objects(node, MRS.recordedAt))
            if pid.lower() in {e.pid.lower() for e in self.entities.values() if e.kind == kind}:
                raise ValueError(f"payload collides case-insensitively within {kind}: {pid}")
            self.entities[ent.iri] = ent
            self.by_kind[kind].append(ent)
            seen_pid[pid] = ent.iri
        for kind in KINDS:
            self.by_kind[kind].sort(key=lambda e: (display.sort_key(e.name), e.pid))

    # ------------------------------------------------------------------ passages and works
    def _work_of(self, passage):
        node, hops = passage, 0
        while node is not None and hops < 6:
            if (node, RDF.type, MRS.Work) in self.g:
                return node
            node = self.g.value(node, DCT.isPartOf)
            hops += 1
        return None

    def work_info(self, work) -> dict:
        label = self.first_lit(work, RDFS.label)
        comment = self.first_lit(work, RDFS.comment)
        creators = [self.agent(a) for a in self.g.objects(work, DCT.creator)]
        creators = [c for c in creators if c]
        ai = any(c.software for c in creators) or bool(
            label and label.text.startswith(display.AI_GENERATED_WORK_LABEL_PREFIXES))
        return {"iri": str(work), "label": label.text if label else None,
                "comment": comment, "creators": creators, "ai": ai,
                "version": (str(self.g.value(work, DCT.hasVersion)) if self.g.value(work, DCT.hasVersion) else None)}

    def passage_info(self, passage) -> dict:
        work = self._work_of(passage)
        wi = self.work_info(work) if work is not None else None
        cit = self.g.value(passage, MRS.canonicalCitation)
        refers = [str(o) for o in self.g.objects(passage, CRM.P67_refers_to)]
        story = next((r for r in refers if r in self._story_passage), None)
        return {"citation": str(cit) if cit else None, "story": story, "work": wi}

    # ------------------------------------------------------------------ dates
    def extent(self, node) -> dict | None:
        g = self.g
        if node is None or (node, RDF.type, MRS.TemporalExtent) not in g:
            return None
        def s(p):
            v = g.value(node, p)
            return str(v) if v is not None else None
        d = {
            "native": s(MRS.nativeValue),
            "calendar": self.vkey(g.value(node, MRS.calendar), "cal_"),
            "earliest": s(MRS.earliestStart),
            "latest": s(MRS.latestEnd),
            "precision": self.vkey(g.value(node, MRS.precision), "pr_"),
            "basis": self.vkey(g.value(node, MRS.temporalBasis), "tbas_"),
            "conv_method": s(MRS.conversionMethod),
            "conv_days": s(MRS.conversionUncertaintyDays),
            "relative": g.value(node, MRS.relativeAnchor) is not None,
            "disputed": g.value(node, MRS.dispute) is not None,
        }
        return d

    def extents(self, node, prop) -> list[dict]:
        out = []
        for e in self.g.objects(node, prop):
            d = self.extent(e)
            if d and d not in out:
                out.append(d)
        return out

    # ------------------------------------------------------------------ claims
    def _load_claims(self):
        g = self.g
        for a in g.subjects(RDF.type, MRS.Assertion):
            subj, obj = g.value(a, MRS.assertionSubject), g.value(a, MRS.assertionObject)
            if subj is None or obj is None:
                continue
            pred = g.value(a, MRS.predicate)
            rel_class = g.value(pred, MRS.relationClass) if pred is not None else None
            passage = g.value(a, PROV.wasDerivedFrom)
            pinfo = self.passage_info(passage) if passage is not None else {}
            wi = pinfo.get("work") if pinfo else None
            claim = Claim(
                kind="assertion", subject=str(subj), object=str(obj),
                literal=Lit(str(obj), obj.language) if isinstance(obj, Literal) else None,
                predicate=self.vocab(pred) or _local(pred or ""),
                relclass=self.vkey(rel_class, "relclass_"),
                role=self.first_lit(a, RDFS.comment),
                qualifiers=[self.vocab(q) or _local(q) for q in g.objects(a, MRS.qualifier)],
                status=self.vkey(g.value(a, MRS.assertionStatus), "as_"),
                basis=self.first_lit(a, MRS.nonReportBasis),
                passage=str(passage) if passage is not None else None,
                citation=pinfo.get("citation"), story=pinfo.get("story"),
                ai_draft=bool(wi and wi["ai"]),
                agents=self.agents_of(a), node=str(a),
            )
            self.claims[claim.subject].append(claim)
            if claim.literal is None and claim.object != claim.subject:
                self.claims[claim.object].append(claim)   # a text is no entity: nothing is filed under it
        # participations: stored on the event, no status of their own
        seen_part: set = set()
        for ev in sorted(set(g.subjects(MRS.hasParticipation, None)), key=str):
            if not isinstance(ev, URIRef):
                continue
            for part in g.objects(ev, MRS.hasParticipation):
                who = g.value(part, MRS.participant)
                if who is None:
                    continue
                role = g.value(part, MRS.participantRole)
                if (str(ev), str(who), str(role)) in seen_part:
                    continue  # the same person in the same role, recorded twice
                seen_part.add((str(ev), str(who), str(role)))
                claim = Claim(kind="participation", subject=str(who), object=str(ev),
                              predicate="claim.took_part", predicate_is_key=True,
                              role=Lit(self.vocab(role)) if role is not None and self.vocab(role) else None,
                              agents=self.agents_of(ev))
                self.claims[claim.subject].append(claim)
                self.claims[claim.object].append(claim)
        # where an event took place: a field of the event, no status of its own
        for ev in sorted(set(g.subjects(MRS.eventPlace, None)), key=str):
            if not isinstance(ev, URIRef):
                continue
            for place in g.objects(ev, MRS.eventPlace):
                claim = Claim(kind="link", subject=str(ev), object=str(place),
                              predicate="claim.took_place_at", predicate_is_key=True,
                              agents=self.agents_of(ev))
                self.claims[claim.subject].append(claim)
                self.claims[claim.object].append(claim)
        # plain part-of triples (slice 1d turns them into assertions; skip pairs that already are)
        have = {(c.subject, c.object) for cs in self.claims.values() for c in cs
                if c.kind == "assertion" and "part of" in c.predicate.lower()}
        for s, o in g.subject_objects(CRM.P9i_forms_part_of):
            if (str(s), str(o)) in have:
                continue
            claim = Claim(kind="link", subject=str(s), object=str(o),
                          predicate="claim.part_of", predicate_is_key=True,
                          agents=self.agents_of(s))
            self.claims[claim.subject].append(claim)
            self.claims[claim.object].append(claim)

    # ------------------------------------------------------------------ per-kind data
    def _finish(self):
        for ent in self.entities.values():
            getattr(self, f"_data_{ent.kind}")(ent)

    def _gaps(self, node) -> list[dict]:
        out = []
        for gap in self.g.objects(node, MRS.coverageGap):
            desc = self.first_lit(gap, MRS.gapDescription)
            out.append({"description": desc, "cause": self.vocab(self.g.value(gap, MRS.gapCause)),
                        "scope": self.vocab(self.g.value(gap, MRS.gapScope)),
                        "known_source": self.first_lit(gap, MRS.knownSource)})
        return out

    def _disputes(self, node) -> list[dict]:
        g = self.g
        out = []
        for d in g.subjects(MRS.disputeSubject, node):
            positions = []
            for pos in g.objects(d, MRS.hasPosition):
                prop = g.value(pos, MRS.proponent)
                positions.append({"claim": self.first_lit(pos, MRS.positionClaim),
                                  "proponent": self.agent(prop) if prop is not None else None})
            out.append({"question": self.first_lit(d, MRS.disputeQuestion),
                        "status": self.vocab(g.value(d, MRS.disputeStatus)),
                        "significance": self.vocab(g.value(d, MRS.disputeSignificance)),
                        "positions": positions})
        return out

    def _data_person(self, ent: Entity):
        g, node = self.g, URIRef(ent.iri)
        forms, seen = [], set()
        for nf in g.objects(node, MRS.nameForm):
            nasab = g.value(nf, MRS.nasab)
            nasab_list = [str(x) for x in Collection(g, nasab)] if nasab is not None else []
            f = {
                "ism": self._s(nf, MRS.ism), "kunya": self._s(nf, MRS.kunya),
                "laqab": [str(o) for o in g.objects(nf, MRS.laqab)],
                "nasab": nasab_list,
                "nisba": [str(g.value(n, MRS.nisbaValue)) for n in g.objects(nf, MRS.nisba)
                          if g.value(n, MRS.nisbaValue) is not None],
                "full": self._s(nf, MRS.fullFormAsAttested),
                "scheme": self._s(nf, MRS.transliterationScheme),
            }
            key = repr(sorted(f.items()))
            if key not in seen:
                seen.add(key)
                forms.append(f)
        deaths = []
        for dn in g.objects(node, MRS.death):
            deaths.extend(self.extents(dn, MRS.eventTemporalExtent))
        affiliations = []
        for pa in g.objects(node, MRS.placeAffiliation):
            place = g.value(pa, MRS.affiliatedPlace)
            affiliations.append({"place": str(place) if place is not None else None,
                                 "type": self.vocab(g.value(pa, MRS.affiliationType)),
                                 "extent": self.extent(g.value(pa, MRS.affiliationExtent))})
        companion = g.value(node, MRS.companionStatus)
        gender = None  # no gender field in the ontology; see display.GENDER_PREDICATES
        for pred in display.GENDER_PREDICATES:
            v = g.value(node, URIRef(pred))
            if v is not None:
                gender = display.GENDER_VALUES.get(str(v).lower())
        ent.data = {
            "name_forms": forms,
            "tabaqa": self.vocab(g.value(node, MRS.tabaqa)),
            "transmitter_role": self.vocab(g.value(node, MRS.transmitterRole)),
            "death": deaths, "affiliations": affiliations,
            "companion_status": self.vkey(companion, "comp_"),
            "gender": gender,
            "gaps": self._gaps(node),
        }

    def _s(self, node, prop):
        v = self.g.value(node, prop)
        return str(v) if v is not None else None

    def _data_group(self, ent: Entity):
        ent.data = {"gaps": self._gaps(URIRef(ent.iri))}

    def _data_place(self, ent: Entity):
        g, node = self.g, URIRef(ent.iri)
        arabic_count: dict[str, int] = defaultdict(int)
        other = []
        for ph in g.objects(node, MRS.namePhase):
            for l in self.lits(ph, MRS.phaseName):
                if l.lang == "ar" or display.has_arabic(l.text):
                    arabic_count[l.text] += 1
                elif l.lang not in (None, "en") and l not in other:
                    other.append(l)
        # the Arabic name most often recorded comes first; the graph gives no other order
        ent.arabic = sorted(arabic_count, key=lambda t: (-arabic_count[t], t))
        ent.other_names = sorted(other, key=lambda l: (l.lang or "", l.text))
        states = []
        for gs in g.objects(node, MRS.geometryState):
            states.append({"confidence": self.vocab(g.value(gs, MRS.locationConfidence)),
                           "basis": self.vocab(g.value(gs, MRS.geometryBasis)),
                           "extent": self.extent(g.value(gs, MRS.validExtent))})
        within = [str(o) for o in g.objects(node, MRS.within)]
        ent.data = {
            "types": [self.vocab(o) for o in g.objects(node, MRS.placeType) if self.vocab(o)],
            "geometry": states, "within": within, "gaps": self._gaps(node),
        }

    def _data_event(self, ent: Entity):
        g, node = self.g, URIRef(ent.iri)
        places = [str(o) for o in g.objects(node, MRS.eventPlace)]
        part_of = [str(o) for o in g.objects(node, CRM.P9i_forms_part_of)]
        parts = [str(s) for s in g.subjects(CRM.P9i_forms_part_of, node)]
        ent.data = {
            "dates": self.extents(node, MRS.eventTemporalExtent),
            "places": places, "part_of": part_of, "parts": parts,
            "disputes": self._disputes(node), "gaps": self._gaps(node),
        }

    def _data_story(self, ent: Entity):
        g, node = self.g, URIRef(ent.iri)
        passage = self._story_passage[ent.iri]
        prose = self.first_lit(passage, CRM.P190_has_symbolic_content)
        number = g.value(node, SKOS.notation)
        part = g.value(passage, DCT.isPartOf)
        part_label = part_no = None
        if part is not None and (part, RDF.type, MRS.Passage) in g:
            pl = self.first_lit(part, RDFS.label)
            part_label = pl.text if pl else None
            pn = g.value(part, SKOS.notation)
            part_no = int(str(pn)) if pn is not None and str(pn).isdigit() else None
        work = self._work_of(passage)
        witness = g.value(passage, MRS.inWitness)
        cit = g.value(passage, MRS.canonicalCitation)
        ent.data = {
            "prose": prose, "number": int(str(number)) if number is not None and str(number).isdigit() else None,
            "part_label": part_label, "part_number": part_no,
            "citation": str(cit) if cit else None,
            "work": self.work_info(work) if work is not None else None,
            "witness": self.vocab(witness) if witness is not None else None,
            "passage": str(passage),
            "dates": self.extents(node, MRS.eventTemporalExtent),
            "places": [str(o) for o in g.objects(node, MRS.eventPlace)],
            "disputes": self._disputes(node), "gaps": self._gaps(node),
        }
        # reading order, then title
    # ------------------------------------------------------------------ queries used by pages
    def entity(self, iri: str) -> Entity | None:
        return self.entities.get(iri)

    def url(self, iri: str) -> str | None:
        e = self.entities.get(iri)
        return f"{e.kind}/{e.pid}/" if e else None

    def label_of(self, iri: str) -> str:
        """Display text for any node: an entity name, a plain label, or the last IRI segment."""
        e = self.entities.get(iri)
        if e:
            return e.name
        if not _IRI_LIKE.match(iri):
            return iri  # a text as written (a literal object), not a node of the graph
        l = self.first_lit(URIRef(iri), RDFS.label)
        return display.name_display(l.text) if l else iri.rsplit("/", 1)[-1]

    def stories_in_order(self) -> list[Entity]:
        return sorted(self.by_kind["story"], key=lambda e: (e.data.get("number") is None, e.data.get("number") or 0, e.name))

    def status_counts(self) -> dict[str, int]:
        c: dict[str, int] = defaultdict(int)
        for a in self.g.subjects(RDF.type, MRS.Assertion):
            c[self.vkey(self.g.value(a, MRS.assertionStatus), "as_") or "none"] += 1
        return dict(c)

    def coverage_counts(self) -> dict[str, int]:
        c: dict[str, int] = defaultdict(int)
        for e in self.entities.values():
            c[e.coverage or "none"] += 1
        return dict(c)

    # ------------------------------------------------------------------ vocabulary labels for the glossary
    def vocabulary_labels(self) -> list[str]:
        """Labels of controlled-vocabulary concepts and relation types (data strings)."""
        out = []
        for s, o in self.g.subject_objects(SKOS.prefLabel):
            if str(s).startswith(str(MRS)) and isinstance(o, Literal):
                out.append(str(o))
        return sorted(set(out))

    def all_graph_labels(self) -> list[str]:
        """Every label in the graph (entities, vocabularies, works, agents)."""
        out = []
        for pred in (RDFS.label, SKOS.prefLabel):
            for o in self.g.objects(None, pred):
                if isinstance(o, Literal):
                    out.append(str(o))
        return out

    # ------------------------------------------------------------------ turtle export
    def turtle_for(self, iri: str) -> str:
        g = self.g
        out = Graph()
        for prefix, ns in g.namespaces():
            out.bind(prefix, ns)

        def add_closure(node, depth=0):
            for p, o in g.predicate_objects(node):
                out.add((node, p, o))
                if isinstance(o, BNode) and depth < 6:
                    add_closure(o, depth + 1)

        node = URIRef(iri)
        add_closure(node)
        for c in self.claims.get(iri, []):
            if c.kind == "assertion" and c.node:
                add_closure(URIRef(c.node))
            elif c.kind == "participation" and c.subject == iri:
                ev = URIRef(c.object)
                for part in g.objects(ev, MRS.hasParticipation):
                    if g.value(part, MRS.participant) == node:
                        out.add((ev, MRS.hasParticipation, part))
                        add_closure(part)
        return out.serialize(format="turtle")
