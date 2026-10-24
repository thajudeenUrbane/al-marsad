"""The decision-7 proposals (learn/proposals/hijrah-parts.json, design §15).

The file is for the review board. Software never writes its claims into the graph: the
simulation here adds them to a temporary copy of the page graph only. Each subject and
object is a named rule, never an ID. Nothing here names a real entity ID either.
Run:  .venv/bin/python -m unittest discover -s learn/tests -v
"""
import ast
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

LEARN = Path(__file__).resolve().parents[1]
ROOT = LEARN.parent
sys.path.insert(0, str(ROOT / "site"))
sys.path.insert(0, str(LEARN))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rdflib import RDF, URIRef  # noqa: E402

import journey_export as X  # noqa: E402
import journeys as J  # noqa: E402
from model import MRS, Site  # noqa: E402

GRAPH = ROOT / "build" / "graph.ttl"
PATH = LEARN / "proposals" / "hijrah-parts.json"
KEYS = {"format", "version", "about", "status", "approved_by", "journey", "graph", "proposals", "effects",
        "joined_graph"}
PROPOSAL_KEYS = {"n", "subject", "predicate", "object", "basis"}
EFFECT_KEYS = {"with", "steps", "text"}
SHELTERING = {"kinds": ["event"], "phrase": ["sheltering", "at", "ghar", "thawr"]}   # a route event no proposal names
SCRATCH = "https://w3id.org/marsad/id/assertion/scratch-proposal-{n}"   # made up; only in a temporary graph


def load() -> dict:
    return json.loads(PATH.read_text(encoding="utf-8"))


def resolve(site: Site, rule: dict) -> list[str]:
    """Every entity of the rule's kinds whose labels match it, as the journeys' named selector does."""
    return sorted(e.iri for kind in rule["kinds"] for e in site.by_kind[kind]
                  if J.name_matches(site, e.iri, rule.get("words"), rule.get("phrase"), rule.get("not_words")))


class TheFile(unittest.TestCase):
    def test_the_file_is_a_proposals_file_for_the_board(self):
        doc = load()
        self.assertEqual(set(doc), KEYS)
        self.assertEqual((doc["format"], doc["version"]), ("marsad-claim-proposals", 1))
        self.assertEqual(doc["status"], "proposed", "the board's answer is written by people, never by software")
        self.assertEqual(doc["approved_by"], [])
        self.assertTrue((LEARN / "journeys" / f"{doc['journey']}.json").is_file())
        self.assertEqual(doc["graph"]["file"], "build/graph.ttl")
        self.assertRegex(doc["graph"]["fingerprint"], r"^[0-9a-f]{12}$")
        self.assertEqual([p["n"] for p in doc["proposals"]], list(range(1, len(doc["proposals"]) + 1)))
        for p in doc["proposals"]:
            with self.subTest(p["n"]):
                self.assertEqual(set(p), PROPOSAL_KEYS)
                for role in ("subject", "object"):
                    J._named(p[role], f"proposal {p['n']}.{role}")
                    self.assertEqual(p[role]["kinds"], ["event"])
                J.term(p["predicate"], f"proposal {p['n']}.predicate")
                self.assertTrue(p["basis"].startswith("Open question for the board: "), p["basis"])
                self.assertIn("?", p["basis"])
        numbers = {p["n"] for p in doc["proposals"]}
        for e in doc["effects"]:
            self.assertEqual(set(e), EFFECT_KEYS)
            self.assertTrue(set(e["with"]) <= numbers)
        self.assertEqual(sorted(len(e["with"]) for e in doc["effects"]), [2, 4, 5])

    def test_proposals_name_no_entity_id(self):
        text = PATH.read_text(encoding="utf-8")
        self.assertNotIn("w3id.org/marsad/id/", text)
        self.assertIsNone(re.search(r"\b[A-Za-z0-9]{22}\b", text), "an ID-shaped token")
        if not GRAPH.exists():
            self.skipTest("build/graph.ttl missing")
        site = Site(GRAPH)
        payloads = {e.pid for e in site.entities.values()}
        self.assertEqual(sorted(p for p in payloads if p in text), [])

    def test_software_never_reads_or_writes_the_proposals(self):
        """No learn module names the proposals folder: the build, the export and the
        engine never see these claims, so they cannot reach a page or the graph."""
        for path in sorted(LEARN.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    self.assertNotIn("proposals", node.value, path.name)


@unittest.skipUnless(GRAPH.exists(), "build/graph.ttl missing")
class OnThePageGraph(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = load()
        cls.site = Site(GRAPH)
        cls.spec = next(s for s in J.load_specs(LEARN / "journeys") if s["slug"] == cls.doc["journey"])
        cls.base = J.build(cls.site, cls.spec)
        cls.same_graph = X.fingerprint(cls.site.g) == cls.doc["graph"]["fingerprint"]

    def one(self, rule: dict) -> str:
        got = resolve(self.site, rule)
        self.assertEqual(len(got), 1, f"{rule} names {len(got)} events")
        return got[0]

    def test_each_proposal_rule_names_exactly_one_event_on_the_page_graph(self):
        for p in self.doc["proposals"]:
            with self.subTest(p["n"]):
                s, o = self.one(p["subject"]), self.one(p["object"])
                self.assertNotEqual(s, o)
                self.assertEqual({self.site.entity(s).kind, self.site.entity(o).kind}, {"event"})
                self.assertIn((J.term(p["predicate"], "t"), RDF.type, MRS.RelationType), self.site.g)

    def test_the_record_does_not_hold_the_proposed_claims_yet(self):
        """Until the board accepts a proposal, no assertion on the graph links its two events
        by its relation or the inverse; when one does, record the board's answer in the file."""
        g = self.site.g
        for p in self.doc["proposals"]:
            s, o = URIRef(self.one(p["subject"])), URIRef(self.one(p["object"]))
            pred = J.term(p["predicate"], "t")
            pairs = [(s, pred, o)] + [(o, inv, s) for inv in g.objects(pred, MRS.inverseRelation)]
            for a, rel, b in pairs:
                held = set(g.subjects(MRS.assertionSubject, a)) & set(g.subjects(MRS.assertionObject, b)) \
                    & set(g.subjects(MRS.predicate, rel))
                self.assertEqual(held, set(), f"proposal {p['n']} is in the graph: record the board's answer")

    def simulate(self, numbers: list[int]):
        """The Hijrah journey on a temporary copy of the page graph with these proposals added
        as proposed assertions, built by the unchanged engine."""
        extra = []
        for p in self.doc["proposals"]:
            if p["n"] in numbers:
                extra.append(
                    f"<{SCRATCH.format(n=p['n'])}> a <{MRS.Assertion}> ;\n"
                    f"  <{MRS.assertionSubject}> <{self.one(p['subject'])}> ;\n"
                    f"  <{MRS.predicate}> <{J.term(p['predicate'], 't')}> ;\n"
                    f"  <{MRS.assertionObject}> <{self.one(p['object'])}> ;\n"
                    f"  <{MRS.assertionStatus}> <{MRS.as_proposed}> .\n")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "graph.ttl"
            path.write_text(GRAPH.read_text(encoding="utf-8") + "\n" + "\n".join(extra), encoding="utf-8")
            return J.build(Site(path), self.spec)

    def test_simulated_effect_matches_the_record(self):
        """design §15: 1-2 alone list Arrival in Madinah before Departure from Makkah; 1-4 put
        the route in order while the council stays unordered; 1-5 move the council before the
        Hijra event. The step numbers the effects give are checked while the graph
        fingerprint is the one the file names (otherwise re-simulate and update the texts);
        on any graph the proposals add their two subjects and the order relations hold."""
        by = {p["n"]: p for p in self.doc["proposals"]}
        arrival, hijra = self.one(by[1]["subject"]), self.one(by[1]["object"])
        pledge, departure = self.one(by[3]["subject"]), self.one(by[3]["object"])
        quba, council = self.one(by[4]["object"]), self.one(by[5]["subject"])
        thawr = self.one(SHELTERING)
        base = [s.entity.iri for s in self.base.steps]
        self.assertNotIn(arrival, base)
        self.assertNotIn(pledge, base)
        effects = {tuple(e["with"]): e for e in self.doc["effects"]}

        def added(order: list) -> None:
            """The proposals keep every step and add the two events they make parts (on the
            file's graph those two alone; elsewhere also what the walk reaches from them)."""
            self.assertEqual(len(order), len(set(order)))
            self.assertEqual(set(base) - set(order), set())
            self.assertLessEqual({arrival, pledge}, set(order) - set(base))
            if self.same_graph:
                self.assertEqual(set(order) - set(base), {arrival, pledge})

        j = self.simulate([1, 2])
        order = [s.entity.iri for s in j.steps]
        added(order)
        self.assertLess(order.index(arrival), order.index(departure))
        if self.same_graph:
            self.assertEqual(len(order), effects[(1, 2)]["steps"])
            self.assertEqual((order.index(arrival) + 1, order.index(departure) + 1), (3, 5))

        j = self.simulate([1, 2, 3, 4])
        order = [s.entity.iri for s in j.steps]
        notes = {s.entity.iri: s.order_note for s in j.steps}
        added(order)
        route = [hijra, pledge, departure, thawr, quba, arrival]
        self.assertEqual([order.index(i) for i in route], sorted(order.index(i) for i in route))
        self.assertEqual(notes[council], "unrecorded")
        self.assertFalse(j.order_conflict)
        if self.same_graph:
            self.assertEqual(len(order), effects[(1, 2, 3, 4)]["steps"])
            tail = [s.entity for s in j.steps[-2:]]
            self.assertEqual(sorted(e.kind for e in tail), ["event", "story"])
            self.assertEqual(order.index(council) + 1, 9)
            self.assertEqual({notes[e.iri] for e in tail}, {"unrecorded"})

        j = self.simulate([1, 2, 3, 4, 5])
        order = [s.entity.iri for s in j.steps]
        added(order)
        self.assertLess(order.index(council), order.index(hijra))
        self.assertLess(order.index(council), order.index(departure))
        self.assertFalse(j.order_conflict)
        if self.same_graph:
            self.assertEqual(len(order), effects[(1, 2, 3, 4, 5)]["steps"])
            self.assertEqual((order.index(council) + 1, order.index(hijra) + 1), (3, 4))
            self.assertEqual(j.steps[1].entity.kind, "story")


if __name__ == "__main__":
    unittest.main()
