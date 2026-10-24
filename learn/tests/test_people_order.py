"""People order E3 and side groups (learn-v2 design §6).

Fixture graphs (made up, see fixtures.py) carry the exact cases; the real-graph tests
state invariants only. Nothing here names a real entity ID.
Run:  .venv/bin/python -m unittest discover -s learn/tests -v
"""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

LEARN = Path(__file__).resolve().parents[1]
ROOT = LEARN.parent
sys.path.insert(0, str(ROOT / "site"))
sys.path.insert(0, str(LEARN))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import display  # noqa: E402
import journey_lists as JL  # noqa: E402
import journeys as J  # noqa: E402
from fixtures import (SOURCE, PROPHET, Fx, acceptance_fixture, list_file, people_spec, side_fixture,  # noqa: E402
                      site_of, tiers_fixture)
from model import Site  # noqa: E402

GRAPH = ROOT / "build" / "graph.ttl"
LISTS = LEARN / "lists" / "people.json"
EN = json.loads((LEARN / "i18n" / "en.json").read_text(encoding="utf-8"))
PROPHET_NAME = display.person_display_name(PROPHET, True)


def names(steps):
    return [s.entity.name for s in steps]


class E3Order(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fx, cls.ids = tiers_fixture()
        cls.site = site_of(fx)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, **kw):
        list_file(self.root, self.ids["rashidun"], self.ids["ten"], **kw)
        return J.build(self.site, J.validate(people_spec()), lists_root=self.root)

    def test_e3_tiers_prophet_four_ten_then_links(self):
        j = self.build()
        self.assertEqual(names(j.steps), [PROPHET_NAME, "Person Delta", "Person Alpha", "Person Charlie", "Person Bravo",
                                          "Person Zulu", "Person Echo",
                                          "Person Juliet", "Person Kilo", "Person Lima", "Person Mike"])
        self.assertEqual(j.order_applied, "e3")
        self.assertEqual((j.lists["state"], j.lists["applied"], j.lists["sources_complete"]), ("reviewed", True, True))
        tiers = [(st.e3["tier"], st.e3["pos"]) for st in j.steps]
        self.assertEqual(tiers, [(0, None), (1, 1), (1, 2), (1, 3), (1, 4), (2, 5), (2, 6),
                                 (3, None), (3, None), (3, None), (3, None)])
        self.assertEqual([st.e3["links"] for st in j.steps[7:]], [4, 4, 2, 1])   # Juliet and Kilo tie: by name
        self.assertGreater(j.steps[6].e3["links"], j.steps[7].e3["links"])     # a listed person is placed by the list

    def test_unreviewed_list_orders_a_to_z_after_the_prophet(self):
        az = [PROPHET_NAME] + [f"Person {n}" for n in ("Alpha", "Bravo", "Charlie", "Delta", "Echo", "Juliet", "Kilo",
                                                        "Lima", "Mike", "Zulu")]
        for why, kw in (("proposed", {"status": "proposed"}), ("no approvals", {"approve": False}),
                        ("stale approvals", {"sha": "0" * 12})):
            with self.subTest(why):
                j = self.build(**kw)
                self.assertEqual(names(j.steps), az)
                self.assertEqual(j.order_applied, "e3_pending")
                self.assertEqual((j.lists["state"], j.lists["applied"]), ("proposed", False))
                self.assertTrue(all(st.e3["tier"] == (0 if st.entity.prophet else None) for st in j.steps))
        shipped = JL.load_lists(LISTS)
        self.assertEqual(shipped["state"], "proposed")
        self.assertEqual(json.loads(LISTS.read_text(encoding="utf-8"))["approved_by"], [])

    def test_a_list_without_sources_is_never_reviewed(self):
        for why, sources in (("no rashidun source", (None, SOURCE)), ("empty source", ("", SOURCE)),
                             ("blank source", ("  ", SOURCE)),
                             ("a review word in a source", (SOURCE, SOURCE + "; numbers to be checked"))):
            with self.subTest(why):
                path = list_file(self.root, self.ids["rashidun"], self.ids["ten"], sources=sources)
                info = JL.load_lists(path)
                self.assertEqual(info["state"], "proposed")
                self.assertFalse(info["sources_complete"])
        info = JL.load_lists(list_file(self.root, self.ids["rashidun"], self.ids["ten"]))
        self.assertEqual(info["state"], "reviewed")
        shipped = JL.load_lists(LISTS)
        self.assertIsNone([ls for ls in shipped["lists"] if ls["key"] == "rashidun"][0]["source"])

    def test_missing_list_file_fails_at_build_not_at_load(self):
        folder = self.root / "journeys"
        folder.mkdir()
        spec = people_spec(lists="lists/nowhere.json")
        (folder / "fixture-people.json").write_text(json.dumps(spec), encoding="utf-8")
        loaded = J.load_specs(folder, lists_root=self.root)
        self.assertEqual(loaded[0]["status"], "draft")
        self.assertEqual(J.lists_sha(spec, lists_root=self.root), "missing")
        with self.assertRaises(J.RuleError) as cm:
            J.build(self.site, loaded[0], lists_root=self.root)
        self.assertIn("missing", str(cm.exception))

    def test_links_ties_by_name_then_pid(self):
        fx = Fx()
        battle = fx.event("fxBattle", "Battle of Fixtureplace")
        listed = fx.person("fxPListed", "Person Listed")
        same_b = fx.person("fxPSameB", "Person Same")
        same_a = fx.person("fxPSameA", "Person Same")
        able = fx.person("fxPAble", "Person Able")
        many = fx.person("fxPMany", "Person Zed")
        for who in (listed, same_b, same_a, able, many):
            fx.participation(battle, who)
        fx.claim(many, "rel_participated_in", fx.event("fxOther", "Another event"))
        site = site_of(fx)
        list_file(self.root, ["Person Listed"], ["Person Listed"])
        j = J.build(site, J.validate(people_spec()), lists_root=self.root)
        self.assertEqual([s.iri for s in j.steps], [listed, many, able, same_a, same_b])
        self.assertEqual([s.e3["links"] for s in j.steps[1:]], [2, 1, 1, 1])

    def test_nobody_is_placed_last_for_faith(self):
        fx, i = side_fixture()
        site = site_of(fx)
        list_file(self.root, ["Person Along"], ["Person Along", "Person Both"])
        j = J.build(site, J.validate(people_spec(group_by="side")), lists_root=self.root)
        self.assertEqual([g.key for g in j.groups], ["main", "against"])
        self.assertTrue(all(st.e3["tier"] in (0, 1, 2, 3) for st in j.steps))
        main = j.steps[j.groups[0].start:j.groups[0].end]
        # opposition claims outside the anchors move nobody: the person keeps their coverage place
        tier3 = [st for st in main if st.e3["tier"] == 3]
        key = [(-st.e3["links"], display.sort_key(st.entity.name), st.entity.pid) for st in tier3]
        self.assertEqual(key, sorted(key))
        self.assertIn(i["opposer"], [st.iri for st in tier3])
        for k in J.RESERVED_LAST:
            self.assertNotIn(k, json.loads(LISTS.read_text(encoding="utf-8")))


class Matching(unittest.TestCase):
    def test_list_names_match_through_b_ibn_and_diacritics(self):
        fx = Fx()
        target = fx.person("fxTarget", "ʿAbd al-Ṣamad b. Fāris", "Abu Fixture")
        fx.person("fxOther", "Person Other")
        for expand in (False, True):
            old = display.EXPAND_B_TO_IBN
            display.EXPAND_B_TO_IBN = expand
            try:
                site = site_of(fx)
            finally:
                display.EXPAND_B_TO_IBN = old
            for name in ("Abd as-Samad ibn Faris", "‘Abd al-Samad bin Faris", "Abd al-Samad b. Faris",
                         "ʿAbd al-Ṣamad b. Fāris", "abd samad ibn faris", "Abu Fixture"):
                with self.subTest(expand=expand, name=name):
                    self.assertEqual(JL.match_members(site, [name]), [target])

    def test_list_zero_or_two_matches_is_a_rule_error_naming_the_member(self):
        fx = Fx()
        fx.person("fxTwin1", "Person Twin")
        fx.person("fxTwin2", "Person Twin")
        fx.person("fxSingle", "Person Single")
        site = site_of(fx)
        self.assertEqual(len(JL.match_members(site, ["Person Single"])), 1)
        for member, n in (("Person Twin", 2), ("Person Nobody", 0)):
            with self.subTest(member):
                with self.assertRaises(J.RuleError) as cm:
                    JL.match_members(site, ["Person Single", member])
                self.assertIn(repr(member), str(cm.exception))
                self.assertIn(f"matches {n} people", str(cm.exception))

    def test_members_are_names_never_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            for bad in ("https://w3id.org/marsad/id/person/fxP", "per:fxP"):
                path = list_file(tmp, [bad], [bad])
                with self.subTest(bad):
                    with self.assertRaises(J.RuleError):
                        JL.load_lists(path)

    def test_list_file_shape_is_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = list_file(tmp, ["Person A"], ["Person A"])
            good = json.loads(path.read_text(encoding="utf-8"))
            JL.validate_lists(copy.deepcopy(good))
            bad = []
            d = copy.deepcopy(good); d["format"] = "marsad-journeys"; bad.append(("format", d))
            d = copy.deepcopy(good); d["version"] = 2; bad.append(("version", d))
            d = copy.deepcopy(good); d["status"] = "approved"; bad.append(("status", d))
            d = copy.deepcopy(good); d["lists"] = d["lists"][:1]; bad.append(("a list missing", d))
            d = copy.deepcopy(good); d["lists"][1]["key"] = "rashidun"; bad.append(("a list twice", d))
            d = copy.deepcopy(good); d["lists"][0]["members"] = ["Person A", "Person A"]; bad.append(("member twice", d))
            d = copy.deepcopy(good); d["lists"][0]["extra"] = 1; bad.append(("unknown list key", d))
            d = copy.deepcopy(good); d["approved_by"][0]["sha"] = "short"; bad.append(("sha", d))
            d = copy.deepcopy(good); del d["approved_by"][0]["sha"]; bad.append(("no sha", d))
            for why, data in bad:
                with self.subTest(why):
                    with self.assertRaises(J.RuleError):
                        JL.validate_lists(data)


class SideGroups(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fx, cls.i = side_fixture()
        cls.site = site_of(fx)

    def spec(self, **kw):
        return J.validate(people_spec(order="prophet_first_then_name", **kw))

    def test_side_groups(self):
        j = J.build(self.site, self.spec(group_by="side"))
        i = self.i
        self.assertEqual([(g.key, g.start, g.end, g.t, g.lead) for g in j.groups],
                         [("main", 0, 9, None, None),
                          ("against", 9, 11, "learn.group.against", "learn.group.against_lead")])
        self.assertEqual([s.iri for s in j.steps],
                         [i["prophet"], i["along"], i["both"], i["elsewhere"], i["notprophet"], i["object"],
                          i["opposer"], i["rejected"], i["uncited"],          # main: the Prophet, then A to Z
                          i["against"], i["convert"]])                        # against: A to Z
        by = {s.iri: s for s in j.steps}
        self.assertEqual([st.group for st in j.steps], ["main"] * 9 + ["against"] * 2)
        self.assertTrue(by[i["both"]].side_conflict)
        self.assertEqual(sum(st.side_conflict for st in j.steps), 1)
        self.assertEqual(by[i["prophet"]].side, [])                          # subject side only
        self.assertEqual(by[i["object"]].side, [])
        for k in ("uncited", "rejected", "elsewhere", "notprophet", "opposer"):
            self.assertEqual(by[i[k]].side, [], k)
        self.assertEqual([J.side_of(self.site, c) for c in by[i["convert"]].side], ["against"])
        self.assertEqual(sorted(J.side_of(self.site, c) for c in by[i["both"]].side), ["against", "alongside"])
        self.assertTrue(all(c.subject == st.iri and c.citation for st in j.steps for c in st.side))

    def test_without_group_by_everyone_stays_in_one_list(self):
        j = J.build(self.site, self.spec())
        self.assertEqual(j.groups, [])
        self.assertEqual({st.group for st in j.steps}, {"main"})
        self.assertEqual(names(j.steps)[0], PROPHET_NAME)
        self.assertEqual(names(j.steps)[1:], sorted(names(j.steps)[1:], key=display.sort_key))
        by = {s.iri: s for s in j.steps}
        self.assertEqual([J.side_of(self.site, c) for c in by[self.i["against"]].side], ["against"])

    def test_group_texts_say_the_side_at_this_event_not_faith(self):
        self.assertEqual(EN["learn.group.against"], "Recorded as fighting against the Prophet ﷺ at this event")
        lead = EN["learn.group.against_lead"]
        self.assertIn("at this event only", lead)
        self.assertIn("says nothing about anyone's faith or later life", lead)
        for key in ("learn.group.against", "learn.group.against_lead"):
            self.assertEqual(J.review_words(EN[key]), [], key)
            self.assertNotIn("last", EN[key].lower().split())


class Wording(unittest.TestCase):
    def test_e3_sentences_say_coverage_not_rank(self):
        keys = sorted(k for k in EN if k.startswith("learn.order.e3"))
        self.assertIn("learn.order.e3", keys)
        for k in keys:
            text = EN[k]
            with self.subTest(k):
                if k not in ("learn.order.e3_lists", "learn.order.e3_pending"):   # Study and Research only
                    self.assertEqual(J.review_words(text), [])
                low = text.lower()
                if "rank" in low:
                    self.assertTrue("not a ranking" in low or "not rank" in low, text)
                self.assertNotIn("important", low.replace("not rank or importance", ""))
        self.assertIn("not a ranking", EN["learn.order.e3"].lower())
        self.assertIn("coverage, never rank", JL.__doc__.replace("\n", " "))


class Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fx, cls.i = acceptance_fixture()
        cls.site = site_of(fx)

    def test_accepted_islam_sort_uses_cited_records_only(self):
        i = self.i
        self.assertEqual(JL.ACCEPTANCE_RULE, {"kinds": ["event"], "phrase": ["acceptance", "of", "islam"]})
        self.assertEqual(JL.acceptance_events(self.site),
                         [i["ev_other"], i["ev_list"], i["ev_a"], i["ev_b"], i["ev_c"]])
        people = "ABCDEFGHJ"
        recs = {i[k]: JL.accepted_islam_records(self.site, i[k]) for k in people}
        self.assertEqual({k: [r["event"] for r in recs[i[k]]] for k in people},
                         {"A": [i["ev_a"]], "B": [i["ev_b"]], "C": [i["ev_c"], i["ev_list"]], "D": [i["ev_list"]],
                          "E": [i["ev_other"]], "F": [], "G": [], "H": [], "J": []})
        a = recs[i["A"]][0]
        self.assertTrue(a["earliest"].startswith("0610-01-01") and a["latest"].startswith("0610-12-31"))
        self.assertEqual(a["precision"], "year")
        self.assertTrue(all(c.citation for rs in recs.values() for r in rs for c in r["claims"]))
        self.assertIsNone(recs[i["D"]][0]["earliest"])
        rank = JL.accepted_islam_rank(self.site, recs)
        self.assertEqual({k: rank[i[k]] for k in people},
                         {"A": 1, "B": 1, "C": 2, "E": 3, "D": 4, "F": None, "G": None, "H": None, "J": None})


@unittest.skipUnless(GRAPH.exists(), "build/graph.ttl missing: run ontology/build_graph.py")
class OnTheGraph(unittest.TestCase):
    def test_e3_order_survives_the_ibn_display_switch(self):
        lists = JL.load_lists(LISTS)["lists"]
        got = {}
        for expand in (False, True):
            old = display.EXPAND_B_TO_IBN
            display.EXPAND_B_TO_IBN = expand
            try:
                site = Site(GRAPH)
            finally:
                display.EXPAND_B_TO_IBN = old
            got[expand] = {ls["key"]: JL.match_members(site, ls["members"]) for ls in lists}
            for ls in lists:
                self.assertEqual(len(set(got[expand][ls["key"]])), len(ls["members"]))
            if expand:
                j = J.build(site, J.load_specs(LEARN / "journeys")[2])
                self.assertEqual(j.lists["members"], got[expand])
        self.assertEqual(got[False], got[True])

    def test_acceptance_records_on_badr_are_cited_and_at_acceptance_events(self):
        site = Site(GRAPH)
        accept = set(JL.acceptance_events(site))
        j = J.build(site, J.load_specs(LEARN / "journeys")[2])
        for st in j.steps + j.set_apart:
            for r in st.e3["accepted_islam"]:
                self.assertIn(r["event"], accept)
                for c in r["claims"]:
                    self.assertTrue(c.citation)
                    self.assertEqual(c.subject, st.iri)
                    self.assertIn("acceptance of islam", " ".join(J.token_seq(site.entity(r["event"]).scholarly)))


class AtlasLists(unittest.TestCase):
    def atlas_lists(self):
        local = ROOT / "atlas" / "data" / "lists.json"
        if local.is_file():
            return json.loads(local.read_text(encoding="utf-8"))
        try:
            out = subprocess.run(["git", "-C", str(ROOT), "show", "origin/sky-atlas-new:atlas/data/lists.json"],
                                 capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return None
        return json.loads(out.stdout) if out.returncode == 0 else None

    def test_lists_match_atlas_members(self):
        atlas = self.atlas_lists()
        if atlas is None:
            self.skipTest("atlas/data/lists.json is not here and origin/sky-atlas-new is not fetched")
        mine = {ls["key"]: ls["members"] for ls in json.loads(LISTS.read_text(encoding="utf-8"))["lists"]}
        theirs = {ls["key"]: ls["members"] for ls in atlas["lists"]}
        self.assertEqual(mine, theirs)
        src = {ls["key"]: ls["source"] for ls in json.loads(LISTS.read_text(encoding="utf-8"))["lists"]}
        self.assertIsNone(src["rashidun"])
        self.assertEqual(src["ten"], {ls["key"]: ls["source"] for ls in atlas["lists"]}["ten"])


if __name__ == "__main__":
    unittest.main()
