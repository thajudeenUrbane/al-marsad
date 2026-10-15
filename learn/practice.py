"""Practice questions, made only from claims that scholars have accepted (slice 7).

    bank(graph) -> list of question dicts

A question is a join of two accepted claims and nothing else: "Who is recorded as
having participated in both X and Y?" needs, for every person in the answer, an
accepted claim that they participated in X and another that they participated in Y.
"At which events are both A and B recorded?" is the same join seen from the people.

The one rule that matters: a claim is usable only if its assertionStatus is exactly
`accepted` (mrs:as_accepted) and nothing else. A claim that is proposed, under review,
rejected, superseded, has no status, or carries two statuses at once never helps to
make a question. Participation records stored on an event (mrs:Participation) have no
status at all, so they never make a question either.

Claims that are not accepted can only take away, never add: an "absent from" claim for
the same person and event that has not been rejected or superseded (whatever else its
status) removes that person from the answer, so a contested matter is never presented
as settled. Answers are not multiple choice: a wrong option would assert that someone
was *not* somewhere, which no claim says.

Each answer carries the claims behind it (their IRIs, citation and basis), so a page
can link every answer to its sources. This module reads only an rdflib Graph; it does
not know about pages, names or URLs.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS

MRS = Namespace("https://w3id.org/marsad/core#")
PROV = Namespace("http://www.w3.org/ns/prov#")
ACCEPTED = MRS.as_accepted

# Claims that put a person or group at an event, in the order questions are made.
PARTICIPATION = (MRS.rel_participated_in, MRS.rel_led, MRS.rel_present_at, MRS.rel_witnessed)
# A claim of this kind for the same person and event, unless rejected or superseded,
# takes the person out of every answer about that event (see contested_pairs).
CONTRARY = (MRS.rel_absent_from,)
WHO_TYPES = {MRS.Person, MRS.Group, MRS.Tribe, MRS.Clan, MRS.Family}
EVENT_TYPES = {MRS.Event, MRS.Journey}
QUESTION_TYPES = ("both_events", "shared_events")


@dataclass(frozen=True)
class AcceptedClaim:
    node: str
    subject: str
    predicate: str
    object: str
    citation: str | None
    basis: str | None
    passage: str | None

    def as_dict(self) -> dict:
        return {"claim": self.node, "subject": self.subject, "predicate": local(self.predicate),
                "object": self.object, "status": "accepted", "citation": self.citation,
                "basis": self.basis, "passage": self.passage}


def local(iri: str) -> str:
    return str(iri).rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def _one(g: Graph, s, p):
    """The single value of s p, or None if there are none or several (ambiguous)."""
    vals = set(g.objects(s, p))
    return next(iter(vals)) if len(vals) == 1 else None


def is_accepted(g: Graph, node) -> bool:
    """True only when the claim's one and only status is accepted."""
    return set(g.objects(node, MRS.assertionStatus)) == {ACCEPTED}


def accepted_claims(g: Graph) -> list[AcceptedClaim]:
    out = []
    for a in sorted(set(g.subjects(RDF.type, MRS.Assertion)), key=str):
        if not isinstance(a, URIRef) or not is_accepted(g, a):
            continue
        s, p, o = _one(g, a, MRS.assertionSubject), _one(g, a, MRS.predicate), _one(g, a, MRS.assertionObject)
        if not isinstance(s, URIRef) or not isinstance(p, URIRef) or not isinstance(o, URIRef):
            continue
        passage = _one(g, a, PROV.wasDerivedFrom)
        cit = _one(g, passage, MRS.canonicalCitation) if passage is not None else None
        basis = _one(g, a, MRS.nonReportBasis)
        out.append(AcceptedClaim(str(a), str(s), str(p), str(o),
                                 str(cit) if cit is not None else None,
                                 str(basis) if basis is not None else None,
                                 str(passage) if isinstance(passage, URIRef) else None))
    return out


def contested_pairs(g: Graph) -> set[tuple[str, str]]:
    """(person, event) pairs that a live "absent from" claim contests: any status except
    rejected or superseded, including none. Used only to remove answers, never to add."""
    dead = {MRS.as_rejected, MRS.as_superseded}
    out = set()
    for a in set(g.subjects(RDF.type, MRS.Assertion)):
        if set(g.objects(a, MRS.predicate)) & set(CONTRARY):
            statuses = set(g.objects(a, MRS.assertionStatus))
            if statuses and statuses <= dead:
                continue
            for s in g.objects(a, MRS.assertionSubject):
                for o in g.objects(a, MRS.assertionObject):
                    out.add((str(s), str(o)))
    return out


def _types(g: Graph, iri: str) -> set:
    return set(g.objects(URIRef(iri), RDF.type))


def _same_name(g: Graph, a: str, b: str) -> bool:
    la = {str(x) for x in g.objects(URIRef(a), RDFS.label)}
    lb = {str(x) for x in g.objects(URIRef(b), RDFS.label)}
    return bool(la & lb)


def question_id(qtype: str, predicate: str, about: list[str]) -> str:
    h = hashlib.sha1("|".join([qtype, predicate] + sorted(about)).encode("utf-8")).hexdigest()
    return h[:12]


def bank(g: Graph) -> list[dict]:
    """Every question the accepted claims support, in a stable order."""
    claims = accepted_claims(g)
    contrary = contested_pairs(g)
    who_ok = {}
    ev_ok = {}

    def is_who(i):
        if i not in who_ok:
            who_ok[i] = bool(_types(g, i) & WHO_TYPES)
        return who_ok[i]

    def is_event(i):
        if i not in ev_ok:
            ev_ok[i] = bool(_types(g, i) & EVENT_TYPES)
        return ev_ok[i]

    # predicate -> event -> who -> [claims]
    at: dict[str, dict[str, dict[str, list[AcceptedClaim]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for c in claims:
        if URIRef(c.predicate) not in PARTICIPATION or (c.subject, c.object) in contrary:
            continue
        if is_who(c.subject) and is_event(c.object):
            at[c.predicate][c.object][c.subject].append(c)

    questions: list[dict] = []
    for pred in (str(p) for p in PARTICIPATION):
        events = sorted(at.get(pred, {}))
        for i, e1 in enumerate(events):
            for e2 in events[i + 1:]:
                if _same_name(g, e1, e2):
                    continue
                both = sorted(set(at[pred][e1]) & set(at[pred][e2]))
                if not both:
                    continue
                answers = [{"entity": w, "claims": [c.as_dict() for c in at[pred][e1][w] + at[pred][e2][w]]}
                           for w in both]
                questions.append({"id": question_id("both_events", local(pred), [e1, e2]),
                                  "type": "both_events", "predicate": local(pred),
                                  "about": [e1, e2], "answers": answers})
        whos: dict[str, dict[str, list[AcceptedClaim]]] = defaultdict(dict)
        for ev, by_who in at.get(pred, {}).items():
            for w, cs in by_who.items():
                whos[w][ev] = cs
        people = sorted(whos)
        for i, w1 in enumerate(people):
            for w2 in people[i + 1:]:
                if _same_name(g, w1, w2):
                    continue
                common = sorted(set(whos[w1]) & set(whos[w2]))
                if not common:
                    continue
                answers = [{"entity": ev, "claims": [c.as_dict() for c in whos[w1][ev] + whos[w2][ev]]}
                           for ev in common]
                questions.append({"id": question_id("shared_events", local(pred), [w1, w2]),
                                  "type": "shared_events", "predicate": local(pred),
                                  "about": [w1, w2], "answers": answers})
    return questions


def claims_used(questions: list[dict]) -> set[str]:
    """Every claim IRI any question rests on."""
    return {c["claim"] for q in questions for a in q["answers"] for c in a["claims"]}


def status_counts(g: Graph) -> dict[str, int]:
    """How many claims carry each status (local name without as_), for the page."""
    counts: dict[str, int] = defaultdict(int)
    for a in set(g.subjects(RDF.type, MRS.Assertion)):
        st = set(g.objects(a, MRS.assertionStatus))
        key = local(next(iter(st))).removeprefix("as_") if len(st) == 1 else ("none" if not st else "several")
        counts[key] += 1
    return dict(counts)
