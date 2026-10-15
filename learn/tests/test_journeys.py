"""Journeys are chosen by rules over the graph (slice 6).

Fixture graphs (made up, see fixtures.py) test the rule engine; the real graph tests
check the three shipped drafts. Nothing here names a real entity ID: real entities are
found by the same rules the journeys use.
Run:  .venv/bin/python -m unittest discover -s learn/tests -v
"""
import copy
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

from rdflib import URIRef  # noqa: E402

import journeys as J  # noqa: E402
from fixtures import Fx  # noqa: E402
from model import MRS, Site  # noqa: E402

GRAPH = ROOT / "build" / "graph.ttl"
SPECS = sorted((LEARN / "journeys").glob("*.json"))


def events_spec(words, follow=("parts", "date_anchors"), max_links=2, kinds=("event", "story")):
    return {"slug": "fixture-events", "status": "draft", "approved_by": [], "title": "journey.hijrah.title",
            "lead": "journey.hijrah.lead", "door": "study",
            "select": {"type": "events", "named": {"kinds": list(kinds), "words": list(words)},
                       "follow": list(follow), "max_links": max_links},
            "order": "recorded"}


def site_of(fx: Fx) -> Site:
    tmp = tempfile.NamedTemporaryFile("w", suffix=".ttl", delete=False, encoding="utf-8")
    tmp.write(fx.ttl())
    tmp.close()
    try:
        return Site(tmp.name)
    finally:
        Path(tmp.name).unlink()


def names(steps):
    return [s.entity.name for s in steps]


class RuleFiles(unittest.TestCase):
    def test_the_three_shipped_journeys_are_valid_drafts(self):
        self.assertEqual(len(SPECS), 3)
        for path in SPECS:
            spec = json.loads(path.read_text(encoding="utf-8"))
            with self.subTest(path.name):
                J.validate(spec, path.stem)
                self.assertEqual(spec["status"], "draft")
                self.assertEqual(spec["approved_by"], [])
        types = sorted(json.loads(p.read_text(encoding="utf-8"))["select"]["type"] for p in SPECS)
        self.assertEqual(types, ["events", "people", "stories"])

    def test_bad_rule_files_are_refused(self):
        good = events_spec(["Rihla"])
        J.validate(copy.deepcopy(good))
        bad = []
        s = copy.deepcopy(good); s["extra"] = 1; bad.append(("unknown key", s))
        s = copy.deepcopy(good); s["status"] = "approved"; bad.append(("approved without approvals", s))
        s = copy.deepcopy(good); s["status"] = "approved"
        s["approved_by"] = [{"who": "maintainer", "date": "2026-10-15"}]; bad.append(("only one approval", s))
        s = copy.deepcopy(good); s["select"]["named"]["words"] = ["5rTyU9mN"]; bad.append(("an ID-like word", s))
        s = copy.deepcopy(good); s["select"]["max_links"] = 9; bad.append(("too many links", s))
        s = copy.deepcopy(good); s["select"]["follow"] = ["part_of"]; bad.append(("unknown direction", s))
        s = copy.deepcopy(good); s["select"]["follow"] = []; bad.append(("links but no direction", s))
        s = copy.deepcopy(good); s["select"]["max_links"] = 0; bad.append(("directions but no links", s))
        s = copy.deepcopy(good); s["order"] = "story"; bad.append(("wrong order for the type", s))
        s = copy.deepcopy(good); s["title"] = "The Hijrah"; bad.append(("title is not an i18n key", s))
        s = copy.deepcopy(good); s["door"] = "elsewhere"; bad.append(("unknown door", s))
        s = copy.deepcopy(good); s["slug"] = "practice"; bad.append(("a slug that is a learn folder", s))
        for why, spec in bad:
            with self.subTest(why):
                with self.assertRaises(J.RuleError):
                    J.validate(spec)
        with self.assertRaises(J.RuleError):
            J.validate(copy.deepcopy(good), "another-name")

    def test_terms_are_ontology_terms_never_entities(self):
        self.assertEqual(J.term("mrs:rel_led", "t"), URIRef("https://w3id.org/marsad/core#rel_led"))
        for bad in ("https://w3id.org/marsad/id/person/abc", "per:abc", "rel_led", "mrs:"):
            with self.assertRaises(J.RuleError):
                J.term(bad, "t")

    def test_an_approved_file_needs_both_approvals(self):
        s = events_spec(["Rihla"])
        s["status"] = "approved"
        s["approved_by"] = [{"who": "maintainer", "date": "2026-11-01"}, {"who": "review_board", "date": "2026-11-02"}]
        J.validate(s)


class EventJourneys(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fx = Fx()
        cls.place = fx.place("fxPlaceA", "Place A")
        cls.whole = fx.event("fxWhole", "The Rihla: setting out", dates=("0622-01-01", "0622-12-31"), place=cls.place)
        cls.leave = fx.event("fxLeave", "Leaving town")
        cls.arrive = fx.event("fxArrive", "Arriving", dates=("0622-01-01", "0622-12-31"))
        att = "https://w3id.org/marsad/id/assertion/fxAnchorClaim"
        cls.rest = fx.event("fxRest", "Resting in a cave",
                            anchors=[("after", cls.leave, att), ("before", cls.arrive, att)])
        fx.claim(cls.leave, "rel_part_of", cls.whole, ("proposed",), pid="fxPartLeave")
        fx.claim(cls.rest, "rel_part_of", cls.whole, ("proposed",), pid="fxPartRest")
        witness = fx.person("fxPersonZ", "Person Z")
        fx.claim(witness, "rel_present_at", cls.place, ("proposed",), pid="fxAnchorClaim")  # attests the anchors
        cls.far = fx.event("fxFar", "A far event")
        fx.claim(cls.far, "rel_part_of", cls.arrive, ("proposed",))          # three links from the named event
        cls.other = fx.event("fxOther", "An unrelated event", dates=("0600-01-01", "0600-12-31"))
        work = fx.story_doc("fxWork", "Fixture stories")
        part = fx.story_part("fxPart1", work, "Part 1: The Rihla", 1)
        cls.story = fx.story("fxStory", "The Rihla told as a story", 7, part)
        cls.site = site_of(fx)
        cls.journey = J.build(cls.site, J.validate(events_spec(["Rihla"])))

    def test_named_events_and_their_recorded_links_are_chosen(self):
        got = {s.iri for s in self.journey.steps}
        self.assertEqual(got, {self.whole, self.leave, self.rest, self.arrive, self.story})
        self.assertNotIn(self.far, got)      # three links away; the rule allows two
        self.assertNotIn(self.other, got)    # no recorded link

    def test_order_follows_recorded_links_then_dates_then_story_order(self):
        self.assertEqual([s.iri for s in self.journey.steps],
                         [self.whole, self.leave, self.rest, self.arrive, self.story])
        notes = [s.order_note for s in self.journey.steps]
        self.assertEqual(notes, [None, "part", "recorded", "recorded", "unrecorded"])

    def test_every_step_says_why_it_is_here_with_the_claims_status(self):
        by = {s.iri: s for s in self.journey.steps}
        self.assertEqual([r.kind for r in by[self.whole].reasons], ["named"])
        self.assertEqual([r.kind for r in by[self.leave].reasons], ["part_of"])
        self.assertEqual([c.status for c in by[self.leave].reasons[0].claims], ["proposed"])
        self.assertEqual([r.kind for r in by[self.arrive].reasons], ["dated_before_this"])
        self.assertEqual(by[self.arrive].reasons[0].other, self.rest)
        self.assertEqual({(r.kind, r.other) for r in by[self.rest].links},
                         {("date_after", self.leave), ("date_before", self.arrive)})
        self.assertTrue(self.journey.mixes_stories_and_events)

    def test_fewer_links_choose_fewer_steps(self):
        j0 = J.build(self.site, J.validate(events_spec(["Rihla"], follow=[], max_links=0)))
        self.assertEqual({s.iri for s in j0.steps}, {self.whole, self.story})
        j1 = J.build(self.site, J.validate(events_spec(["Rihla"], follow=["parts"], max_links=3)))
        self.assertEqual({s.iri for s in j1.steps}, {self.whole, self.leave, self.rest, self.story})

    def test_date_anchors_are_walked_only_from_the_dated_event(self):
        fx = Fx()
        named = fx.event("fxNamed", "The Rihla")
        later = fx.event("fxLater", "A later event", anchors=[("after", named, None)])   # dated after the Rihla
        before = fx.event("fxBefore", "An earlier event")
        fx.event("fxNamed2", "The Rihla, second record", anchors=[("after", before, None)])
        j = J.build(site_of(fx), J.validate(events_spec(["Rihla"])))
        got = {s.iri for s in j.steps}
        self.assertNotIn(later, got)     # being dated after a step does not make an event a step
        self.assertIn(before, got)       # a step's own date placed after it does
        self.assertEqual(j.steps[0].iri, before)

    def test_wholes_and_their_other_parts_only_when_the_rule_asks(self):
        fx = Fx()
        named = fx.event("fxNamed", "The Rihla")
        whole = fx.event("fxWholeBig", "A larger whole")
        sibling = fx.event("fxSibling", "Another part of the whole")
        fx.claim(named, "rel_part_of", whole, ("proposed",))
        fx.claim(sibling, "rel_part_of", whole, ("proposed",))
        site = site_of(fx)
        only_parts = J.build(site, J.validate(events_spec(["Rihla"], follow=["parts"])))
        self.assertEqual({s.iri for s in only_parts.steps}, {named})
        wholes = J.build(site, J.validate(events_spec(["Rihla"], follow=["wholes"])))
        self.assertEqual({s.iri for s in wholes.steps}, {named, whole})
        both = J.build(site, J.validate(events_spec(["Rihla"], follow=["wholes", "parts"])))
        self.assertEqual({s.iri for s in both.steps}, {named, whole, sibling})

    def test_other_event_claims_link_both_ways_and_can_order(self):
        fx = Fx()
        named = fx.event("fxNamed", "The Rihla")
        nxt = fx.event("fxNext", "What came next")
        fx.claim(named, "rel_preceded", nxt, ("proposed",))
        site = site_of(fx)
        self.assertEqual({s.iri for s in J.build(site, J.validate(events_spec(["Rihla"]))).steps}, {named})
        j = J.build(site, J.validate(events_spec(["Rihla"], follow=["event_claims"], max_links=1)))
        self.assertEqual([s.iri for s in j.steps], [named, nxt])
        self.assertEqual(j.steps[1].order_note, "recorded")
        self.assertEqual([c.status for c in j.steps[1].reasons[0].claims], ["proposed"])

    def test_dates_order_steps_the_record_does_not_link(self):
        fx = Fx()
        late = fx.event("fxLate", "Rihla A, the later one", dates=("0630-01-01", "0630-12-31"))
        early = fx.event("fxEarly", "Rihla B, the earlier one", dates=("0610-01-01", "0610-12-31"))
        j = J.build(site_of(fx), J.validate(events_spec(["Rihla"])))
        self.assertEqual([s.iri for s in j.steps], [early, late])
        self.assertEqual(j.steps[1].order_note, "recorded")

    def test_contradicting_links_are_reported_not_hidden(self):
        fx = Fx()
        a = fx.event("fxA", "Rihla one")
        b = fx.event("fxB", "Rihla two", anchors=[("after", a, None), ("before", a, None)])
        j = J.build(site_of(fx), J.validate(events_spec(["Rihla"])))
        self.assertTrue(j.order_conflict)
        self.assertEqual({s.iri for s in j.steps}, {a, b})

    def test_a_rule_that_chooses_nothing_fails_loudly(self):
        with self.assertRaises(J.RuleError):
            J.build(self.site, J.validate(events_spec(["Nowhere"])))


class PeopleAndStoryJourneys(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fx = Fx()
        cls.battle = fx.event("fxBattle", "Battle of Fixtureplace")
        cls.elsewhere = fx.event("fxElsewhere", "Another battle")
        work = fx.story_doc("fxWork", "Fixture stories")
        p1 = fx.story_part("fxPart1", work, "Part 1: The Early Days", 1)
        p2 = fx.story_part("fxPart2", work, "Part 2: Later Days", 2)
        cls.story = fx.story("fxStoryBattle", "The Battle of Fixtureplace", 3, p2)
        cls.s1 = fx.story("fxStory1", "The first story", 1, p1)
        cls.s2 = fx.story("fxStory2", "The second story", 2, p1)
        cls.a, cls.b, cls.c, cls.d, cls.e = (fx.person(f"fxPerson{x}", f"Person {x}") for x in "ABCDE")
        cls.g = fx.group("fxGroup", "Group G")
        fx.participation(cls.battle, cls.a, "role_leader")
        fx.claim(cls.b, "rel_participated_in", cls.story, ("proposed",), role="named in the story")
        fx.claim(cls.b, "rel_absent_from", cls.battle, ("proposed",))
        fx.claim(cls.c, "rel_participated_in", cls.story, ("proposed",), qualifiers=["q_later"])
        fx.claim(cls.d, "rel_participated_in", cls.elsewhere, ("proposed",))
        fx.claim(cls.e, "rel_absent_from", cls.battle, ("proposed",))
        fx.claim(cls.g, "rel_participated_in", cls.battle, ("proposed",))
        fx.claim(cls.d, "rel_participated_in", cls.s1, ("proposed",), role="first named")
        fx.claim(cls.g, "rel_participated_in", cls.s2, ("under_review",))
        cls.site = site_of(fx)

    def people_spec(self, **over):
        sel = {"type": "people",
               "events": {"named": {"kinds": ["event", "story"], "words": ["Fixtureplace"]}, "follow": ["parts"],
                          "max_links": 1},
               "participation": {"records": True, "claims": ["mrs:rel_participated_in", "mrs:rel_led"]},
               "also_show": ["mrs:rel_absent_from"], "set_apart": ["mrsv:q_later"]}
        sel.update(over)
        return J.validate({"slug": "fixture-people", "status": "draft", "approved_by": [], "title": "journey.badr.title",
                           "lead": "journey.badr.lead", "door": "study", "select": sel, "order": "name"})

    def test_people_with_a_recorded_participation_are_chosen(self):
        j = J.build(self.site, self.people_spec())
        self.assertEqual(names(j.steps), ["Person A", "Person B"])
        self.assertEqual(names(j.set_apart), ["Person C"])
        b = j.steps[1]
        self.assertEqual([c.object for c in b.records], [self.story])
        self.assertEqual([c.object for c in b.contrary], [self.battle])   # shown beside, never chooses
        self.assertEqual(sorted(j.anchors), sorted([self.battle, self.story]))

    def test_records_alone_or_claims_alone(self):
        only_records = self.people_spec(participation={"records": True, "claims": []})
        self.assertEqual(names(J.build(self.site, only_records).steps), ["Person A"])
        only_claims = self.people_spec(participation={"records": False, "claims": ["mrs:rel_participated_in"]})
        self.assertEqual(names(J.build(self.site, only_claims).steps), ["Person B"])

    def test_without_set_apart_everyone_is_a_step(self):
        j = J.build(self.site, self.people_spec(set_apart=[]))
        self.assertEqual(names(j.steps), ["Person A", "Person B", "Person C"])

    def test_stories_come_from_the_part_whose_title_has_the_word(self):
        spec = J.validate({"slug": "fixture-stories", "status": "draft", "approved_by": [],
                           "title": "journey.first_believers.title", "lead": "journey.first_believers.lead",
                           "door": "discover", "select": {"type": "stories", "part": {"words": ["Early"]}},
                           "order": "story"})
        j = J.build(self.site, spec)
        self.assertEqual([s.iri for s in j.steps], [self.s1, self.s2])
        self.assertEqual(j.part_labels, ["Part 1: The Early Days"])
        self.assertEqual([c.subject for c in j.steps[0].records], [self.d])
        self.assertEqual([c.status for c in j.steps[1].records], ["under_review"])


@unittest.skipUnless(GRAPH.exists(), "build/graph.ttl missing: run ontology/build_graph.py")
class ShippedJourneys(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = Site(GRAPH)
        cls.links = J.Links(cls.site)
        cls.j = {j.slug: j for j in J.build_all(cls.site, J.load_specs(LEARN / "journeys"))}

    def tokens_of(self, iri):
        return set().union(*[J.tokens(str(l)) for l in self.site.g.objects(URIRef(iri), J.RDFS.label)])

    def test_three_drafts_build_from_the_graph(self):
        self.assertEqual(sorted(self.j), ["first-believers", "hijrah-step-by-step", "people-of-badr"])
        for j in self.j.values():
            self.assertTrue(j.is_draft)
            self.assertGreater(len(j.steps), 0)
            for st in j.steps + j.set_apart:
                self.assertIs(self.site.entity(st.iri), st.entity)

    def test_hijrah_steps_are_named_or_linked_and_keep_the_recorded_order(self):
        j = self.j["hijrah-step-by-step"]
        pos = {s.iri: n for n, s in enumerate(j.steps)}
        self.assertGreaterEqual(len(j.steps), 3)
        for st in j.steps:
            self.assertIn(st.entity.kind, ("event", "story"))
            named = any(r.kind == "named" and r.word.lower() in self.tokens_of(st.iri) for r in st.reasons)
            linked = any(r.other in pos for r in st.reasons)
            self.assertTrue(named or linked, st.entity.name)
        for before, after, _kind in self.links.order:
            if before in pos and after in pos:
                self.assertLess(pos[before], pos[after])
        self.assertFalse(j.order_conflict)

    def test_badr_steps_each_have_a_participation_record_at_badr(self):
        j = self.j["people-of-badr"]
        allowed = {MRS.rel_participated_in, MRS.rel_led, MRS.rel_present_at, MRS.rel_witnessed}
        for st in j.steps + j.set_apart:
            self.assertEqual(st.entity.kind, "person")
            self.assertTrue(st.records)
            for c in st.records:
                self.assertIn("badr", self.tokens_of(c.object))
                if c.kind == "assertion":
                    self.assertIn(self.site.g.value(URIRef(c.node), MRS.predicate), allowed)
                else:
                    self.assertEqual(c.kind, "participation")
            for c in st.contrary:
                self.assertEqual(self.site.g.value(URIRef(c.node), MRS.predicate), MRS.rel_absent_from)
        for st in j.set_apart:
            for c in st.records:
                self.assertIn(URIRef("https://w3id.org/marsad/vocab/q_accepted_islam_later"),
                              J.claim_qualifiers(self.site, c))
        prophets = [n for n, st in enumerate(j.steps) if st.entity.prophet]
        self.assertIn(prophets, ([], [0]))

    def test_first_believers_are_the_makkan_part_in_reading_order(self):
        j = self.j["first-believers"]
        want = [e for e in self.site.stories_in_order() if "makkan" in J.tokens(e.data.get("part_label") or "")]
        self.assertEqual([s.iri for s in j.steps], [e.iri for e in want])
        numbers = [s.entity.data["number"] for s in j.steps]
        self.assertEqual(numbers, sorted(numbers))

    def test_no_entity_id_is_written_in_the_learn_sources(self):
        payloads = {e.pid for e in self.site.entities.values()}
        for path in sorted(LEARN.rglob("*")):
            if path.is_file() and path.suffix in (".py", ".json", ".html", ".css", ".js", ".cjs", ".md"):
                text = path.read_text(encoding="utf-8")
                leaked = sorted(p for p in payloads if p in text)
                self.assertEqual(leaked, [], path)
        for path in sorted((ROOT / "docs" / "handover").glob("slice-6-7*.md")):
            text = path.read_text(encoding="utf-8")
            self.assertEqual(sorted(p for p in payloads if p in text), [], path)


if __name__ == "__main__":
    unittest.main()
