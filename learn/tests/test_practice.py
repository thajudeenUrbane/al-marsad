"""Practice questions come only from accepted claims (slice 7).

The fixture graphs below are made up for the tests. They prove that no claim that is
proposed, under review, rejected, superseded, unstated or doubly stated can produce a
question, alone or together with accepted claims, and that the real graph (where no
claim is accepted today) gives an empty bank.
Run:  .venv/bin/python -m unittest discover -s learn/tests -v
"""
import itertools
import random
import sys
import unittest
from pathlib import Path

LEARN = Path(__file__).resolve().parents[1]
ROOT = LEARN.parent
sys.path.insert(0, str(LEARN))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rdflib import Graph, URIRef  # noqa: E402

import practice  # noqa: E402
from fixtures import Fx  # noqa: E402

GRAPH = ROOT / "build" / "graph.ttl"
NOT_ACCEPTED = [(), ("proposed",), ("under_review",), ("rejected",), ("superseded",),
                ("accepted", "proposed"), ("accepted", "under_review"), ("accepted", "rejected"),
                ("accepted", "superseded")]
PART = ("rel_participated_in", "rel_led", "rel_present_at", "rel_witnessed")


def two_events_one_person(st1, st2, predicate="rel_participated_in"):
    fx = Fx()
    p = fx.person("fxPersonA", "Person A")
    e1 = fx.event("fxEventA", "Event A")
    e2 = fx.event("fxEventB", "Event B")
    c1 = fx.claim(p, predicate, e1, st1)
    c2 = fx.claim(p, predicate, e2, st2)
    return fx, p, e1, e2, c1, c2


class OnlyAcceptedClaims(unittest.TestCase):
    def test_two_accepted_claims_make_one_question_each_way(self):
        fx, p, e1, e2, c1, c2 = two_events_one_person(("accepted",), ("accepted",))
        bank = practice.bank(fx.graph())
        self.assertEqual([q["type"] for q in bank], ["both_events"])
        q = bank[0]
        self.assertEqual(sorted(q["about"]), sorted([e1, e2]))
        self.assertEqual([a["entity"] for a in q["answers"]], [p])
        self.assertEqual(sorted(c["claim"] for c in q["answers"][0]["claims"]), sorted([c1, c2]))
        self.assertTrue(all(c["status"] == "accepted" for c in q["answers"][0]["claims"]))

    def test_no_other_status_on_either_claim_ever_makes_a_question(self):
        for st1, st2 in itertools.product(NOT_ACCEPTED + [("accepted",)], repeat=2):
            if st1 == st2 == ("accepted",):
                continue
            for pred in PART:
                with self.subTest(first=st1, second=st2, predicate=pred):
                    fx, *_ = two_events_one_person(st1, st2, pred)
                    self.assertEqual(practice.bank(fx.graph()), [])

    def test_participation_records_without_status_never_make_a_question(self):
        fx = Fx()
        p, q = fx.person("fxPersonA", "Person A"), fx.person("fxPersonB", "Person B")
        e1, e2 = fx.event("fxEventA", "Event A"), fx.event("fxEventB", "Event B")
        for e in (e1, e2):
            for w in (p, q):
                fx.participation(e, w, "role_leader")
        self.assertEqual(practice.bank(fx.graph()), [])

    def test_mixing_accepted_and_unaccepted_claims_uses_only_the_accepted_pairs(self):
        fx = Fx()
        a, b, c = (fx.person(f"fxPerson{x}", f"Person {x}") for x in "ABC")
        e1, e2 = fx.event("fxEventA", "Event A"), fx.event("fxEventB", "Event B")
        fx.claim(a, "rel_participated_in", e1, ("accepted",))
        fx.claim(a, "rel_participated_in", e2, ("accepted",))
        fx.claim(b, "rel_participated_in", e1, ("accepted",))
        fx.claim(b, "rel_participated_in", e2, ("proposed",))
        fx.claim(c, "rel_participated_in", e1, ("under_review",))
        fx.claim(c, "rel_participated_in", e2, ("rejected",))
        bank = practice.bank(fx.graph())
        both = [q for q in bank if q["type"] == "both_events"]
        self.assertEqual(len(both), 1)
        self.assertEqual([x["entity"] for x in both[0]["answers"]], [a])
        # A and B share one event through two accepted claims; C has no accepted claim at all
        shared = [q for q in bank if q["type"] == "shared_events"]
        self.assertEqual(len(shared), 1)
        self.assertEqual(sorted(shared[0]["about"]), sorted([a, b]))
        self.assertEqual([x["entity"] for x in shared[0]["answers"]], [e1])
        self.assertNotIn(c, {w for q in bank for w in q["about"]} | {x["entity"] for q in bank for x in q["answers"]})

    def test_two_people_at_two_events_make_both_kinds_of_question(self):
        fx = Fx()
        a, b = fx.person("fxPersonA", "Person A"), fx.person("fxPersonB", "Person B")
        e1, e2 = fx.event("fxEventA", "Event A"), fx.event("fxEventB", "Event B")
        for w in (a, b):
            for e in (e1, e2):
                fx.claim(w, "rel_led", e, ("accepted",))
        bank = practice.bank(fx.graph())
        self.assertEqual(sorted((q["type"], q["predicate"]) for q in bank),
                         [("both_events", "rel_led"), ("shared_events", "rel_led")])
        shared = [q for q in bank if q["type"] == "shared_events"][0]
        self.assertEqual(sorted(shared["about"]), sorted([a, b]))
        self.assertEqual(sorted(x["entity"] for x in shared["answers"]), sorted([e1, e2]))

    def test_different_kinds_of_claim_are_never_joined(self):
        fx = Fx()
        a = fx.person("fxPersonA", "Person A")
        e1, e2 = fx.event("fxEventA", "Event A"), fx.event("fxEventB", "Event B")
        fx.claim(a, "rel_led", e1, ("accepted",))
        fx.claim(a, "rel_participated_in", e2, ("accepted",))
        self.assertEqual(practice.bank(fx.graph()), [])

    def test_other_relations_and_wrong_types_make_no_question(self):
        fx = Fx()
        a, b = fx.person("fxPersonA", "Person A"), fx.person("fxPersonB", "Person B")
        pl = fx.place("fxPlaceA", "Place A")
        e1 = fx.event("fxEventA", "Event A")
        fx.claim(a, "rel_father_of", b, ("accepted",))
        fx.claim(b, "rel_father_of", a, ("accepted",))
        fx.claim(a, "rel_participated_in", pl, ("accepted",))   # object is a place, not an event
        fx.claim(a, "rel_participated_in", e1, ("accepted",))
        fx.claim(e1, "rel_participated_in", e1, ("accepted",))  # subject is not a person or group
        self.assertEqual(practice.bank(fx.graph()), [])

    def test_a_live_absent_from_claim_removes_the_person(self):
        for st in [("accepted",), ("proposed",), ("under_review",), ()]:
            with self.subTest(absent_status=st):
                fx, p, e1, e2, *_ = two_events_one_person(("accepted",), ("accepted",))
                fx.claim(p, "rel_absent_from", e2, st)
                self.assertEqual(practice.bank(fx.graph()), [])
        for st in [("rejected",), ("superseded",)]:
            with self.subTest(absent_status=st):
                fx, p, e1, e2, *_ = two_events_one_person(("accepted",), ("accepted",))
                fx.claim(p, "rel_absent_from", e2, st)
                self.assertEqual(len(practice.bank(fx.graph())), 1)

    def test_events_with_the_same_name_are_not_asked_about_together(self):
        fx = Fx()
        p = fx.person("fxPersonA", "Person A")
        e1, e2 = fx.event("fxEventA", "Same name"), fx.event("fxEventB", "Same name")
        fx.claim(p, "rel_participated_in", e1, ("accepted",))
        fx.claim(p, "rel_participated_in", e2, ("accepted",))
        self.assertEqual(practice.bank(fx.graph()), [])

    def test_a_claim_with_two_subjects_is_ambiguous_and_never_used(self):
        fx, p, e1, e2, c1, c2 = two_events_one_person(("accepted",), ("accepted",))
        q = fx.person("fxPersonB", "Person B")
        fx.out.append(f"<{c1}> <https://w3id.org/marsad/core#assertionSubject> <{q}> .")
        self.assertEqual(practice.bank(fx.graph()), [])

    def test_answers_carry_their_claims_and_sources(self):
        fx, p, e1, e2, c1, c2 = two_events_one_person(("accepted",), ("accepted",))
        bank = practice.bank(fx.graph())
        claims = [c for a in bank[0]["answers"] for c in a["claims"]]
        self.assertEqual(sorted(c["claim"] for c in claims), sorted([c1, c2]))
        for c in claims:
            self.assertEqual((c["subject"], c["predicate"], c["status"]), (p, "rel_participated_in", "accepted"))
            self.assertEqual(c["basis"], "Fixture basis.")

    def test_question_ids_do_not_depend_on_order(self):
        a = practice.question_id("both_events", "rel_led", ["x", "y"])
        self.assertEqual(a, practice.question_id("both_events", "rel_led", ["y", "x"]))
        self.assertNotEqual(a, practice.question_id("both_events", "rel_participated_in", ["x", "y"]))


def random_graph(rng: random.Random) -> tuple[Fx, list[tuple]]:
    """A random fixture graph and the list of its claims (iri, subject, predicate, object, statuses)."""
    fx = Fx()
    people = [fx.person(f"fxP{i}", f"Person {i}") for i in range(rng.randint(2, 5))]
    groups = [fx.group("fxG0", "Group 0")]
    events = [fx.event(f"fxE{i}", f"Event {i}") for i in range(rng.randint(2, 4))]
    places = [fx.place("fxL0", "Place 0")]
    statuses = NOT_ACCEPTED + [("accepted",)] * 6
    claims = []
    for _ in range(rng.randint(6, 30)):
        if rng.random() < 0.7:   # most claims put a person or group at an event, so joins happen
            pred = rng.choice(PART[:2] + ("rel_absent_from",))
            s, o = rng.choice(people + groups), rng.choice(events)
        else:                    # the rest is noise: other relations, wrong types
            pred = rng.choice(PART + ("rel_absent_from", "rel_father_of"))
            s = rng.choice(people + groups + events)
            o = rng.choice(events + places + people) if pred != "rel_father_of" else rng.choice(people)
        st = rng.choice(statuses)
        iri = fx.claim(s, pred, o, st)
        claims.append((iri, s, pred, o, st))
    for _ in range(rng.randint(0, 4)):
        fx.participation(rng.choice(events), rng.choice(people))
    return fx, claims


def oracle(claims, people_groups, events) -> set:
    """The questions the rules allow, computed the slow, obvious way."""
    contested = {(s, o) for (_, s, p, o, st) in claims
                 if p == "rel_absent_from" and not (st and set(st) <= {"rejected", "superseded"})}
    at = {}
    for (_, s, p, o, st) in claims:
        if st == ("accepted",) and p in PART and s in people_groups and o in events and (s, o) not in contested:
            at.setdefault(p, {}).setdefault(o, set()).add(s)
    out = set()
    for p, by_event in at.items():
        evs = sorted(by_event)
        for e1, e2 in itertools.combinations(evs, 2):
            both = by_event[e1] & by_event[e2]
            if both:
                out.add(("both_events", p, e1, e2, frozenset(both)))
        whos = sorted({w for ws in by_event.values() for w in ws})
        for w1, w2 in itertools.combinations(whos, 2):
            common = {e for e, ws in by_event.items() if w1 in ws and w2 in ws}
            if common:
                out.add(("shared_events", p, w1, w2, frozenset(common)))
    return out


class RandomGraphs(unittest.TestCase):
    def test_every_question_rests_only_on_accepted_claims(self):
        rng = random.Random(20261015)
        made = 0
        for i in range(400):
            fx, claims = random_graph(rng)
            g = fx.graph()
            bank = practice.bank(g)
            made += len(bank)
            status_of = {iri: st for (iri, *_rest, st) in claims}
            with self.subTest(graph=i):
                for c in practice.claims_used(bank):
                    self.assertEqual(status_of[c], ("accepted",))
                    self.assertTrue(practice.is_accepted(g, URIRef(c)))
                people_groups = {s for (_, s, *_r) in claims if "/person/" in s or "/group/" in s}
                people_groups |= {o for (_, _s, _p, o, _st) in claims if "/person/" in o}
                events = {x for (_, s, _p, o, _st) in claims for x in (s, o) if "/event/" in x}
                got = set()
                for q in bank:
                    a, b = q["about"]
                    got.add((q["type"], q["predicate"], a, b, frozenset(x["entity"] for x in q["answers"])))
                self.assertEqual(got, oracle(claims, people_groups, events))
        self.assertGreater(made, 50, "the random graphs should make some questions")

    def test_without_accepted_claims_the_bank_is_always_empty(self):
        rng = random.Random(7)
        for i in range(200):
            fx, claims = random_graph(rng)
            for other in ("proposed", "under_review", "rejected", "superseded"):
                ttl = fx.ttl().replace("mrs:assertionStatus mrs:as_accepted", f"mrs:assertionStatus mrs:as_{other}")
                g = Graph()
                g.parse(data=ttl, format="turtle")
                with self.subTest(graph=i, status=other):
                    self.assertEqual(practice.bank(g), [])


@unittest.skipUnless(GRAPH.exists(), "build/graph.ttl missing: run ontology/build_graph.py")
class RealGraph(unittest.TestCase):
    def test_the_bank_uses_accepted_claims_only_and_is_empty_without_them(self):
        g = Graph()
        g.parse(str(GRAPH), format="turtle")
        bank = practice.bank(g)
        for c in practice.claims_used(bank):
            self.assertTrue(practice.is_accepted(g, URIRef(c)), c)
        if practice.status_counts(g).get("accepted", 0) == 0:   # true on 15 October 2026
            self.assertEqual(practice.accepted_claims(g), [])
            self.assertEqual(bank, [])


if __name__ == "__main__":
    unittest.main()
