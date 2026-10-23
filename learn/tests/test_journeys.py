"""Journeys are chosen by rules over the graph (slice 6, learn-v2).

Fixture graphs (made up, see fixtures.py) test the rule engine; the real graph tests
check the three shipped drafts. Nothing here names a real entity ID: real entities are
found by the same rules the journeys use. Real-graph tests state invariants, never
corpus counts (design §17 item 11); exact numbers are on fixtures only.
Run:  .venv/bin/python -m unittest discover -s learn/tests -v
"""
import ast
import contextlib
import copy
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import unicodedata
from pathlib import Path

LEARN = Path(__file__).resolve().parents[1]
ROOT = LEARN.parent
sys.path.insert(0, str(ROOT / "site"))
sys.path.insert(0, str(LEARN))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rdflib import URIRef  # noqa: E402

import display  # noqa: E402
import golden  # noqa: E402
import journey_lists as JL  # noqa: E402
import journeys as J  # noqa: E402
from fixtures import Fx, events_spec, facade_graph, list_file, people_spec, site_of, stories_spec  # noqa: E402
from model import MRS, Site  # noqa: E402

GRAPH = ROOT / "build" / "graph.ttl"
SPECS = sorted((LEARN / "journeys").glob("*.json"))
V1_REASON_KINDS = {"named", "part_of", "has_part", "date_after", "date_before", "date_related", "dated_after_this",
                   "dated_before_this", "dated_related_this", "event_claim", "part"}
V2_KEYS = ("lead_study", "hold_study", "story_mode", "lists", "kind")
EN = json.loads((LEARN / "i18n" / "en.json").read_text(encoding="utf-8"))
AR_PATH = LEARN / "i18n" / "ar.json"
ARABIC_INDIC_DIGIT = re.compile("[٠-٩۰-۹]")
# Vendor and model-family names, model IDs among them (brief: no model names or IDs in a
# repository file). Each name has one letter in brackets, so this file, which is scanned
# too, does not match itself.
MODEL_NAME = re.compile(r"\b(?:cl[a]ude|anth[r]opic|open[a]i|chat[g]pt|gem[i]ni|ll[a]ma|mis[t]ral|op[u]s|son[n]et|"
                        r"hai[k]u)\b|\bg[p]t-?\d", re.I)
SOURCE_SUFFIXES = (".py", ".json", ".html", ".css", ".js", ".cjs", ".md", ".lock")


def learn_sources() -> list[Path]:
    """Every text file in learn/, and the slice-6-7 and learn-v2 handover notes."""
    files = [p for p in sorted(LEARN.rglob("*")) if p.is_file() and p.suffix in SOURCE_SUFFIXES]
    notes = sorted((ROOT / "docs" / "handover").glob("slice-6-7*.md")) + \
        sorted((ROOT / "docs" / "handover").glob("learn-v2*.md"))
    assert any(p.name.startswith("learn-v2") for p in notes), "the learn-v2 notes are missing"
    return files + notes


def names(steps):
    return [s.entity.name for s in steps]


def shipped(slug: str) -> dict:
    return json.loads((LEARN / "journeys" / f"{slug}.json").read_text(encoding="utf-8"))


def as_v1(spec: dict) -> dict:
    """The file with every v2 key removed: the v1 rule it extends."""
    s = copy.deepcopy(spec)
    for k in V2_KEYS:
        s.pop(k, None)
    if s["order"] == "e3":
        s["order"] = "prophet_first_then_name"
    sel = s["select"]
    sel.pop("group_by", None)
    for named in (sel.get("named"), (sel.get("events") or {}).get("named")):
        if named:
            named.pop("not_words", None)
            named.pop("phrase", None)
    return s


def refused(test, spec, why=""):
    with test.subTest(why):
        with test.assertRaises(J.RuleError):
            J.validate(spec)


def atlas_load_journeys(site, index: dict, log, journeys_dir: Path, strings_path: Path) -> list[dict]:
    """atlas/build.py load_journeys (origin/sky-atlas-new, lines 124-153), copied call for
    call, with its JOURNEYS folder and ROOT strings file passed in. The Atlas imports the
    facade this way; nothing here may need a change on the Atlas's side."""
    try:
        import journeys as jmod
    except ImportError as e:  # learn/ is part of the repository; say so if it is not there
        log(f"journeys skipped: {e}")
        return []
    strings = json.loads(strings_path.read_text(encoding="utf-8"))
    out = []
    for spec in jmod.load_specs(journeys_dir):
        try:
            j = jmod.build(site, spec)
        except jmod.RuleError as e:
            log(f"journey {spec['slug']}: {e}")
            continue
        steps = [index[s.iri] for s in j.steps if s.iri in index]
        apart = [index[s.iri] for s in j.set_apart if s.iri in index]
        anchors = [index[a] for a in j.anchors if a in index]
        why = []  # per step: the rule's own reasons, then the records that chose it
        for st in j.steps:
            if st.iri not in index:
                continue
            rs = [[r.kind, index.get(r.other, -1) if r.other else -1, r.word or r.label or ""] for r in st.reasons]
            for c in st.records[:3]:
                o = c.object if c.subject == st.iri else c.subject
                rs.append(["record", index.get(o, -1), c.predicate if not c.predicate_is_key else c.predicate.split(".")[-1].replace("_", " ")])
            why.append(rs)
        out.append({"key": spec["slug"], "title": strings.get(spec["title"], spec["slug"]),
                    "lead": strings.get(spec["lead"], ""), "type": spec["select"]["type"],
                    "status": spec["status"], "steps": steps, "apart": apart, "anchors": anchors, "why": why})
    return out


def node_index(site) -> dict:
    """IRI -> node number, as the Atlas's ObsData gives one per entity (a stable order here)."""
    out = {}
    for kind in ("person", "group", "place", "event", "story"):
        for e in site.by_kind[kind]:
            out[e.iri] = len(out)
    return out


@contextlib.contextmanager
def cwd(path):
    old = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


class RuleFiles(unittest.TestCase):
    def test_no_model_name_is_written_in_the_learn_sources(self):
        """No vendor or model name, nor a model ID, in learn/ (this file included) or the
        learn-v2 notes; needs no graph, so it runs everywhere."""
        files = learn_sources()
        self.assertIn(Path(__file__).resolve(), [p.resolve() for p in files])
        for path in files:
            found = MODEL_NAME.search(path.read_text(encoding="utf-8"))
            self.assertIsNone(found, f"{path}: {found and found.group(0)!r}")
        for probe in ("written with Cl" "aude", "an op" "enai key", "g" "pt-4o", "Son" "net 4", "a hai" "ku model"):
            self.assertIsNotNone(MODEL_NAME.search(probe), probe)
        self.assertIsNone(MODEL_NAME.search("the opusculum, a sonnetwise gloss"))

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
        s = copy.deepcopy(good); s["slug"] = "data"; bad.append(("the export's folder", s))
        s = copy.deepcopy(good); s["slug"] += "\n"; bad.append(("a slug ending in a newline", s))
        s = copy.deepcopy(good); s["title"] += "\n"; bad.append(("a key ending in a newline", s))
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

    def test_titles_and_leads_are_discover_safe(self):
        for path in SPECS:
            spec = json.loads(path.read_text(encoding="utf-8"))
            for role in ("title", "lead"):
                with self.subTest(path.name, role=role):
                    self.assertEqual(J.review_words(EN[spec[role]]), [])
            if "lead_study" in spec:
                self.assertIn(spec["lead_study"], EN)
                self.assertNotEqual(EN[spec["lead_study"]], EN[spec["lead"]])
        self.assertEqual(J.review_words("Numbers to be checked by the Board."), ["checked", "board"])
        self.assertEqual(J.ar_review_stems("مسودة"), ["مسود"])

    def test_arabic_titles_and_leads_are_discover_safe(self):
        """design §12: learn/i18n/ar.json holds every journey's title, lead and lead_study;
        the title and lead are free of the Arabic review stems. lead_study is a Study and
        Research text, held like the English one: not to the Discover word lists (test_build
        keeps it off Discover pages and the index). Both drafts say "checked", which
        AR_REVIEW_STEMS does not cover (design §20.1)."""
        ar = json.loads(AR_PATH.read_text(encoding="utf-8"))
        for spec_path in SPECS:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            for role in J.TEXT_ROLES:
                if role not in spec:
                    continue
                with self.subTest(spec_path.name, role=role):
                    self.assertTrue(ar.get(spec[role]), "no Arabic text")
                    if role in ("title", "lead"):
                        self.assertEqual(J.ar_review_stems(ar[spec[role]]), [])

    def test_arabic_strings_have_parity_with_english(self):
        """design §12: ar.json is a flat key -> text object, like en.json. In this slice it
        holds exactly the title, lead and lead_study keys the shipped journeys name; every
        key is also an en key, with the same {placeholders}; texts are NFC and write their
        digits 0-9 (L2)."""
        ar = json.loads(AR_PATH.read_text(encoding="utf-8"))
        self.assertIsInstance(ar, dict)
        named = {json.loads(p.read_text(encoding="utf-8"))[r] for p in SPECS for r in J.TEXT_ROLES
                 if r in json.loads(p.read_text(encoding="utf-8"))}
        self.assertEqual(set(ar), named)
        slot = re.compile(r"\{([a-z_]+)\}")
        for key, text in sorted(ar.items()):
            with self.subTest(key):
                self.assertIsInstance(text, str)
                self.assertIn(key, EN)
                self.assertEqual(sorted(slot.findall(text)), sorted(slot.findall(EN[key])))
                self.assertEqual(unicodedata.normalize("NFC", text), text)
                self.assertIsNone(ARABIC_INDIC_DIGIT.search(text))
                self.assertRegex(text, r"[ء-ي]")
        self.assertEqual(J.load_i18n()["ar"], ar)

    def test_arabic_review_stems_are_found_with_harakat_and_tatweel(self):
        self.assertEqual(J.ar_review_stems("مُرَاجَعَة"), ["مراجع"])
        self.assertEqual(J.ar_review_stems("مســودة"), ["مسود"])
        self.assertEqual(J.ar_review_stems("مَقبُول"), ["مقبول"])
        self.assertEqual(J.ar_review_stems("الهجرة خطوةً خطوة"), [])

    def test_v1_files_stay_valid_without_v2_keys(self):
        for spec in (events_spec(["Rihla"]), people_spec(order="name"), stories_spec()):
            J.validate(spec)
        for path in SPECS:
            with self.subTest(path.name):
                J.validate(as_v1(json.loads(path.read_text(encoding="utf-8"))), path.stem)
        if not GRAPH.exists():
            self.skipTest("build/graph.ttl missing")
        site = Site(GRAPH)
        links = J.Links(site)
        for spec in J.load_specs(LEARN / "journeys"):
            with self.subTest(spec["slug"]):
                v2 = J.build(site, spec, links)
                v1 = J.build(site, as_v1(spec), links)
                self.assertEqual([s.iri for s in v2.steps], [s.iri for s in v1.steps])
                self.assertEqual([s.iri for s in v2.set_apart], [s.iri for s in v1.set_apart])
                self.assertEqual(v2.anchors, v1.anchors)

    def test_v2_keys_are_validated(self):
        good = people_spec(group_by="side")
        J.validate(copy.deepcopy(good))
        ok = copy.deepcopy(good)
        ok.update(lead_study="journey.badr.lead_study", hold_study=True, kind="official",
                  story_mode={"open": False, "approved_by": []})
        J.validate(ok)
        cases = {
            "lead_study is not a key": {"lead_study": "The people"},
            "hold_study is not a bool": {"hold_study": "yes"},
            "story_mode has an unknown key": {"story_mode": {"open": False, "approved_by": [], "play": True}},
            "story_mode.open is not a bool": {"story_mode": {"open": 1, "approved_by": []}},
            "story_mode.open without a board record": {
                "story_mode": {"open": True, "approved_by": [{"who": "maintainer", "date": "2026-11-02"}]}},
            "lists outside the repository": {"lists": "../lists/people.json"},
            "lists through a parent folder": {"lists": "learn/../lists/people.json"},
            "lists is absolute": {"lists": "/learn/lists/people.json"},
            "lists is not json": {"lists": "learn/lists/people.txt"},
            "lists has capitals": {"lists": "Learn/lists/people.json"},
            "approval spec is not 12 hex": {"approved_by": [{"who": "maintainer", "date": "2026-11-02",
                                                            "spec": "ABCDEF123456"}]},
            "approval note too long": {"approved_by": [{"who": "maintainer", "date": "2026-11-02", "note": "x" * 301}]},
            "approval has an unknown key": {"approved_by": [{"who": "maintainer", "date": "2026-11-02", "sha": "a" * 12}]},
            "unknown top-level key": {"stages": []},
        }
        for why, over in cases.items():
            s = copy.deepcopy(good)
            s.update(over)
            refused(self, s, why)
        s = copy.deepcopy(good); s["select"]["group_by"] = "faith"; refused(self, s, "group_by is not side")
        s = events_spec(["Rihla"]); s["select"]["group_by"] = "side"; refused(self, s, "group_by on events")
        s = stories_spec(); s["select"]["group_by"] = "side"; refused(self, s, "group_by on stories")
        s = copy.deepcopy(good); s["select"]["events"]["named"]["words_ar"] = ["بدر"]; refused(self, s, "a later key")

    def test_kind_other_than_official_is_refused_at_top_level(self):
        J.validate(dict(events_spec(["Rihla"]), kind="official"))
        for kind, words in (("method", "method/"), ("teacher", "never a file"), ("other", "kind must be")):
            with self.subTest(kind):
                with self.assertRaises(J.RuleError) as cm:
                    J.validate(dict(events_spec(["Rihla"]), kind=kind))
                self.assertIn(words, str(cm.exception))

    def test_reserved_last_keys_are_refused(self):
        for where in ("top", "select", "events"):
            s = people_spec()
            target = {"top": s, "select": s["select"], "events": s["select"]["events"]}[where]
            target["last_if"] = {"claims": ["mrs:rel_fought_against"]}
            with self.subTest(where):
                with self.assertRaises(J.RuleError) as cm:
                    J.validate(s)
                self.assertIn("waits for round 4 Q2", str(cm.exception))
        s = people_spec(); s["last"] = []
        with self.assertRaises(J.RuleError) as cm:
            J.validate(s)
        self.assertIn("waits for round 4 Q2", str(cm.exception))
        with tempfile.TemporaryDirectory() as tmp:
            for how in ("key", "list"):
                path = list_file(tmp, ["Person A"], ["Person A"], approve=False)
                data = json.loads(path.read_text(encoding="utf-8"))
                if how == "key":
                    data["last"] = {"members": ["Person B"]}
                else:
                    data["lists"].append({"key": "last", "members": ["Person B"], "order": "x", "source": None})
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.subTest(how):
                    with self.assertRaises(J.RuleError) as cm:
                        JL.load_lists(path)
                    self.assertIn("waits for round 4 Q2", str(cm.exception))

    def test_words_that_can_never_match_are_refused(self):
        for word in ("Abu-Bakr", "Ka'b", "ﷺ", "", " Badr", "Badr ", "al Badr", "9th", "raid\n", "Hijra\n", "\nBadr"):
            for key in ("words", "phrase", "not_words"):
                s = events_spec(["Rihla"])
                s["select"]["named"][key] = [word]
                refused(self, s, f"{key}: {word!r}")
            s = stories_spec([word]) if word else stories_spec()
            if word:
                refused(self, s, f"part word {word!r}")
        for key in ("words", "phrase", "not_words"):
            s = events_spec(["Rihla"])
            s["select"]["named"][key] = []
            refused(self, s, f"empty {key}")
        s = events_spec([])
        refused(self, s, "neither words nor a phrase")
        J.validate(events_spec([], phrase=["Rihla", "of", "Two"]))
        J.validate(events_spec(["Rihla", "Rihla2"], not_words=["raid"]))

    def test_phrase_and_not_words(self):
        fx = Fx()
        exact = fx.event("fxExact", "The great Rihla of the year")
        apart = fx.event("fxApart", "Rihla, the great")                 # both words, not in that order
        split = fx.event("fxSplit", "A great day", more=("The Rihla",))  # the words in two different labels
        raid = fx.event("fxRaid", "The Rihla raid")
        site = site_of(fx)
        j = J.build(site, J.validate(events_spec([], follow=[], max_links=0, phrase=["great", "Rihla"])))
        self.assertEqual([s.iri for s in j.steps], [exact])
        self.assertEqual([(r.kind, r.word) for r in j.steps[0].reasons], [("named", "great Rihla")])
        j = J.build(site, J.validate(events_spec(["Rihla"], follow=[], max_links=0)))
        self.assertEqual({s.iri for s in j.steps}, {exact, apart, split, raid})
        j = J.build(site, J.validate(events_spec(["Rihla"], follow=[], max_links=0, not_words=["raid"])))
        self.assertEqual({s.iri for s in j.steps}, {exact, apart, split})
        j = J.build(site, J.validate(events_spec(["Rihla"], follow=[], max_links=0, not_words=["day"])))
        self.assertNotIn(split, {s.iri for s in j.steps})   # a not_word in any label leaves it out
        self.assertEqual(J.token_seq("Death of the Prophet ﷺ"), ["death", "of", "the", "prophet"])

    def test_bad_terms_raise_rule_errors_not_type_errors(self):
        cases = []
        for where in ("claims", "also_show", "set_apart"):
            for bad in (5, None, {"x": 1}, ["mrs:rel_led"]):
                s = people_spec(order="name")
                (s["select"]["participation"] if where == "claims" else s["select"])[where] = [bad]
                cases.append((f"{where}: {bad!r}", s))
        s = people_spec(order="name"); s["select"]["events"]["named"]["kinds"] = [["event"]]; cases.append(("kinds", s))
        s = events_spec(["Rihla"]); s["select"]["follow"] = [{"parts": 1}]; cases.append(("follow", s))
        s = events_spec(["Rihla"]); s["order"] = ["recorded"]; cases.append(("order", s))
        s = events_spec(["Rihla"]); s["select"]["named"]["words"] = [7]; cases.append(("word", s))
        s = events_spec(["Rihla"]); s["approved_by"] = [{"who": ["maintainer"], "date": "2026-11-02"}]
        cases.append(("who", s))
        s = events_spec(["Rihla"]); s["approved_by"] = [{"who": "maintainer", "date": 20261102}]; cases.append(("date", s))
        s = people_spec(); s["lists"] = ["learn/lists/people.json"]; cases.append(("lists", s))
        for why, spec in cases:
            with self.subTest(why):
                try:
                    J.validate(spec)
                except J.RuleError:
                    pass
                else:
                    self.fail(f"{why}: accepted")
        for bad in (5, None, ["mrs:rel_led"]):
            with self.assertRaises(J.RuleError):
                J.term(bad, "t")

    def test_duplicate_kinds_approvers_and_impossible_dates_are_refused(self):
        s = events_spec(["Rihla"], kinds=("event", "event")); refused(self, s, "kinds twice")
        two = [{"who": "maintainer", "date": "2026-11-01"}, {"who": "maintainer", "date": "2026-11-02"}]
        s = events_spec(["Rihla"]); s["approved_by"] = two; refused(self, s, "approver twice")
        s = events_spec(["Rihla"]); s["story_mode"] = {"open": False, "approved_by": two}
        refused(self, s, "story approver twice")
        for date in ("2026-02-30", "20261102", "2026-W45-1", "2026-13-01", "26-11-02", "2026-11-02\n",
                     "٢٠٢٦-١١-٠٢", "2026-11-02T10:00"):
            s = events_spec(["Rihla"])
            s["approved_by"] = [{"who": "maintainer", "date": date}]
            refused(self, s, f"date {date!r}")
        with tempfile.TemporaryDirectory() as tmp:
            path = list_file(tmp, ["Person A"], ["Person A"])
            data = json.loads(path.read_text(encoding="utf-8"))
            data["approved_by"][1]["who"] = "maintainer"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(J.RuleError):
                JL.load_lists(path)

    def test_lists_key_is_required_exactly_for_e3(self):
        J.validate(people_spec(order="e3"))
        s = people_spec(order="e3"); del s["lists"]; refused(self, s, "e3 without lists")
        s = people_spec(order="name"); s["lists"] = "lists/people.json"; refused(self, s, "lists without e3")
        s = events_spec(["Rihla"]); s["lists"] = "lists/people.json"; refused(self, s, "lists on events")
        s = events_spec(["Rihla"]); s["order"] = "e3"; refused(self, s, "e3 on events")


class Approval(unittest.TestCase):
    I18N = {"en": {"journey.badr.title": "Title A", "journey.badr.lead": "Lead A", "journey.badr.lead_study": "Study A"},
            "ar": {"journey.badr.title": "عنوان"}}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        list_file(self.root, ["Person A"], ["Person A", "Person B"])

    def tearDown(self):
        self.tmp.cleanup()

    def sha(self, spec, i18n=None):
        return J.rule_sha(spec, lists_root=self.root, i18n=i18n or self.I18N)

    def test_canonical_known_vector(self):
        obj = {"b": ["Marsád", "المرصد"], "a": {"ź": 1, "y": [True, None, 2.5]}}
        self.assertEqual(J.canonical(obj), '{"a":{"y":[true,null,2.5],"ź":1},"b":["Marsád","المرصد"]}'.encode("utf-8"))
        self.assertEqual(J.sha12(obj), "dbcd4070c042")
        self.assertEqual(J.sha12(obj), hashlib.sha256(J.canonical(obj)).hexdigest()[:12])
        self.assertEqual(J.sha12(obj), J.sha12(json.loads(json.dumps(J.nfc(obj)))))
        self.assertEqual(golden.sha12(obj), J.sha12(obj))   # the golden files use the same form
        self.assertEqual(unicodedata.normalize("NFC", "á"), "á")

    def test_rule_sha_covers_rule_and_title_lead_wording_in_en_and_ar(self):
        base = people_spec()
        base["lead_study"] = "journey.badr.lead_study"
        h = self.sha(base)
        self.assertRegex(h, r"^[0-9a-f]{12}$")
        changed = []
        s = copy.deepcopy(base); s["select"]["events"]["named"]["words"] = ["Elsewhere"]; changed.append(("select", s, None))
        s = copy.deepcopy(base); s["order"] = "name"; del s["lists"]; changed.append(("order", s, None))
        s = copy.deepcopy(base); s["door"] = "discover"; changed.append(("door", s, None))
        i = copy.deepcopy(self.I18N); i["en"]["journey.badr.lead"] = "Lead B"; changed.append(("en lead", base, i))
        i = copy.deepcopy(self.I18N); i["en"]["journey.badr.lead_study"] = "Study B"; changed.append(("en lead_study", base, i))
        i = copy.deepcopy(self.I18N); i["ar"]["journey.badr.title"] = "عنوان آخر"; changed.append(("ar title", base, i))
        i = copy.deepcopy(self.I18N); i["ar"]["journey.badr.lead"] = "مقدمة"; changed.append(("ar lead added", base, i))
        for why, spec, i18n in changed:
            with self.subTest(why):
                self.assertNotEqual(self.sha(spec, i18n), h)
        list_file(self.root, ["Person A"], ["Person A", "Person C"])
        self.assertNotEqual(self.sha(base), h, "list content")
        list_file(self.root, ["Person A"], ["Person A", "Person B"])
        self.assertEqual(self.sha(base), h)
        same = []
        s = copy.deepcopy(base); s["status"] = "approved"
        s["approved_by"] = [{"who": "maintainer", "date": "2026-11-02", "spec": h},
                            {"who": "review_board", "date": "2026-11-09", "spec": h, "note": "rule only"}]
        same.append(("status and approvals", s))
        s = copy.deepcopy(base); s["story_mode"] = {"open": True, "approved_by": [
            {"who": "review_board", "date": "2026-11-09", "spec": h}]}; same.append(("story_mode", s))
        s = copy.deepcopy(base); s["hold_study"] = True; same.append(("hold_study", s))
        for why, spec in same:
            with self.subTest(why):
                self.assertEqual(self.sha(spec), h)
        list_file(self.root, ["Person A"], ["Person A", "Person B"], status="proposed", approve=False)
        self.assertEqual(self.sha(base), h, "the list file's own status and approvals are not its content")
        self.assertEqual(J.rule_sha(base, lists_root=self.root), J.rule_sha(base, lists_root=self.root))

    def test_missing_or_broken_list_file_gives_a_sentinel_and_draft_and_build_raises_rule_error(self):
        spec = people_spec()
        good = J.rule_sha(spec, lists_root=self.root)       # with the shipped strings, as load_specs reads them
        approved = dict(copy.deepcopy(spec), status="approved",
                        approved_by=[{"who": "maintainer", "date": "2026-11-02", "spec": good},
                                     {"who": "review_board", "date": "2026-11-09", "spec": good}])
        self.assertEqual(J.state(approved, lists_root=self.root), "approved")
        fx, ids = facade_like_people()
        site = site_of(fx)
        folder = self.root / "journeys"
        folder.mkdir()
        (folder / "fixture-people.json").write_text(json.dumps(approved), encoding="utf-8")
        self.assertEqual(J.load_specs(folder, lists_root=self.root)[0]["status"], "approved")
        self.assertEqual([s.entity.name for s in J.build(site, spec, lists_root=self.root).steps][:1],
                         ["The Prophet Muhammad (fixture) ﷺ"])
        path = self.root / "lists" / "people.json"
        cases = {"missing": None, "unreadable": "{not json", "invalid": json.dumps({"format": "marsad-lists"})}
        for why, content in cases.items():
            with self.subTest(why):
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_text(content, encoding="utf-8")
                sentinel = J.lists_sha(spec, lists_root=self.root)
                self.assertEqual(sentinel, "unreadable" if why == "invalid" else why)
                self.assertEqual(J.state(approved, lists_root=self.root), "draft")
                specs = J.load_specs(folder, lists_root=self.root)   # never raises on a valid file
                self.assertEqual(specs[0]["status"], "draft")
                with self.assertRaises(J.RuleError):
                    J.build(site, specs[0], lists_root=self.root)
        list_file(self.root, ["Nobody Here"], ["Nobody Here"])
        with self.assertRaises(J.RuleError) as cm:
            J.build(site, spec, lists_root=self.root)
        self.assertIn("Nobody Here", str(cm.exception))

    def test_approved_needs_both_roles_on_the_current_rule_sha(self):
        spec = people_spec()
        h = self.sha(spec)
        def with_approvals(*shas):
            return dict(copy.deepcopy(spec), status="approved",
                        approved_by=[{"who": w, "date": "2026-11-02", **({"spec": x} if x else {})}
                                     for w, x in zip(("maintainer", "review_board"), shas)])
        self.assertEqual(J.state(with_approvals(h, h), lists_root=self.root, i18n=self.I18N), "approved")
        for shas in ((h, "0" * 12), ("0" * 12, h), (h, None), (None, None)):
            with self.subTest(shas):
                self.assertEqual(J.state(with_approvals(*shas), lists_root=self.root, i18n=self.I18N), "draft")
        draft = dict(copy.deepcopy(spec), approved_by=with_approvals(h, h)["approved_by"])
        self.assertEqual(J.state(draft, lists_root=self.root, i18n=self.I18N), "draft")   # the file still says draft
        with tempfile.TemporaryDirectory() as tmp:
            j = with_approvals(h, h)
            j["title"], j["lead"] = "journey.badr.title", "journey.badr.lead"
            real = J.rule_sha(j, lists_root=self.root)        # the shipped strings
            j["approved_by"] = [{"who": "maintainer", "date": "2026-11-02", "spec": real},
                                {"who": "review_board", "date": "2026-11-09", "spec": real}]
            (Path(tmp) / "fixture-people.json").write_text(json.dumps(j), encoding="utf-8")
            self.assertEqual(J.load_specs(Path(tmp), lists_root=self.root)[0]["status"], "approved")
            self.assertEqual(json.loads((Path(tmp) / "fixture-people.json").read_text(encoding="utf-8"))["status"],
                             "approved")

    def test_stale_approval_reads_as_draft_and_never_raises(self):
        spec = dict(people_spec(), status="approved",
                    approved_by=[{"who": "maintainer", "date": "2026-11-02", "spec": "0123456789ab"},
                                 {"who": "review_board", "date": "2026-11-09", "spec": "0123456789ab"}])
        self.assertTrue(J.stale_approval(spec, lists_root=self.root, i18n=self.I18N))
        self.assertEqual(J.state(spec, lists_root=self.root, i18n=self.I18N), "draft")
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "fixture-people.json").write_text(json.dumps(spec), encoding="utf-8")
            loaded = J.load_specs(Path(tmp), lists_root=self.root)
        self.assertEqual(loaded[0]["status"], "draft")
        self.assertEqual(loaded[0]["approved_by"], spec["approved_by"])
        self.assertFalse(J.stale_approval(people_spec(), lists_root=self.root, i18n=self.I18N))

    def test_no_shipped_journey_has_a_stale_approval(self):
        for path in SPECS:
            spec = json.loads(path.read_text(encoding="utf-8"))
            with self.subTest(path.name):
                self.assertFalse(J.stale_approval(spec), "an approval is recorded for another rule_sha")
                self.assertFalse(J.story_mode(spec)["stale"], "story mode is recorded open for another rule_sha")
                self.assertNotEqual(J.lists_sha(spec), "missing")
                self.assertNotEqual(J.lists_sha(spec), "unreadable")
        self.assertFalse(JL.load_lists(LEARN / "lists" / "people.json")["stale_approval"])

    def test_story_mode_opens_only_with_a_board_record_on_the_current_rule_sha(self):
        spec = people_spec()
        h = self.sha(spec)
        def sm(open_, *entries):
            return dict(copy.deepcopy(spec), story_mode={"open": open_, "approved_by": list(entries)})
        board = {"who": "review_board", "date": "2026-11-09", "spec": h}
        old = {"who": "review_board", "date": "2026-11-09", "spec": "0" * 12}
        nosha = {"who": "review_board", "date": "2026-11-09"}
        maint = {"who": "maintainer", "date": "2026-11-02", "spec": h}
        self.assertEqual(J.story_mode(sm(True, board), lists_root=self.root, i18n=self.I18N),
                         {"open": True, "stale": False, "approved_by": [board]})
        for why, s in (("old hash", sm(True, old)), ("no hash", sm(True, nosha)), ("maintainer only", sm(True, maint, nosha))):
            with self.subTest(why):
                got = J.story_mode(s, lists_root=self.root, i18n=self.I18N)
                self.assertEqual((got["open"], got["stale"]), (False, True))
        self.assertEqual(J.story_mode(sm(False, board), lists_root=self.root, i18n=self.I18N)["open"], False)
        self.assertEqual(J.story_mode(people_spec(), lists_root=self.root, i18n=self.I18N),
                         {"open": False, "stale": False, "approved_by": []})
        with self.assertRaises(J.RuleError):
            J.validate(sm(True, maint))
        for spec in J.load_specs(LEARN / "journeys"):
            with self.subTest(spec["slug"]):
                self.assertEqual(spec["story_mode"], {"open": False, "stale": False, "approved_by": []})

    def test_software_never_writes_spec_list_or_approval_files(self):
        writes = {"write_text", "write_bytes", "mkdir", "touch", "unlink", "rename", "replace", "rmdir", "symlink_to",
                  "copyfile", "copy", "copy2", "copytree", "move", "rmtree", "dump"}
        protected = re.compile(r"(^|/)(journeys|lists)(/|$)")

        def mentions(node, tainted):
            for n in ast.walk(node):
                if isinstance(n, ast.Constant) and isinstance(n.value, str) and protected.search(n.value):
                    return True
                if isinstance(n, ast.Name) and n.id in tainted:
                    return True
            return False

        found, bad = 0, []
        for path in sorted(LEARN.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            tainted: set[str] = set()
            for _ in range(3):
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None \
                            and mentions(node.value, tainted):
                        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                        tainted |= {n.id for t in targets for n in ast.walk(t) if isinstance(n, ast.Name)}
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
                mode = [a.value for a in node.args[1:] if isinstance(a, ast.Constant)] + \
                       [k.value.value for k in node.keywords if k.arg == "mode" and isinstance(k.value, ast.Constant)]
                if name == "open" and not any(isinstance(m, str) and set(m) & set("wax+") for m in mode):
                    continue
                if name not in writes and name != "open":
                    continue
                found += 1
                if mentions(node, tainted):
                    bad.append((path.name, node.lineno))
        self.assertGreater(found, 0, "the scan found no write call at all")
        self.assertEqual(bad, [])
        if not GRAPH.exists():
            self.skipTest("build/graph.ttl missing")
        import build as site_build
        import build_learn

        def snapshot():
            return {p.relative_to(LEARN).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for d in ("journeys", "lists") for p in sorted((LEARN / d).rglob("*")) if p.is_file()}

        before = snapshot()
        self.assertTrue(any(k.startswith("lists/") for k in before))
        with tempfile.TemporaryDirectory() as out, contextlib.redirect_stdout(io.StringIO()):
            site_build.build(GRAPH, Path(out), True)
            build_learn.build(GRAPH, Path(out), True)
        self.assertEqual(snapshot(), before)


def facade_like_people():
    """A battle with people whose names a fixture list file can name."""
    fx = Fx()
    battle = fx.event("fxBattle", "Battle of Fixtureplace")
    ids = {"battle": battle, "prophet": fx.prophet()}
    fx.participation(battle, ids["prophet"], "role_leader")
    for k in "ABC":
        ids[k] = fx.person(f"fxPerson{k}", f"Person {k}")
        fx.participation(battle, ids[k])
    return fx, ids


@unittest.skipUnless(GRAPH.exists(), "build/graph.ttl missing: run ontology/build_graph.py")
class Facade(unittest.TestCase):
    """What atlas/build.py (origin/sky-atlas-new) reads from this module must keep working."""

    @classmethod
    def setUpClass(cls):
        cls.site = Site(GRAPH)

    def test_the_atlas_contract_is_intact(self):
        logged = []
        index = node_index(self.site)
        out = atlas_load_journeys(self.site, index, logged.append, ROOT / "learn" / "journeys",
                                  ROOT / "learn" / "i18n" / "en.json")
        self.assertEqual(logged, [])
        self.assertEqual([j["key"] for j in out], ["first-believers", "hijrah-step-by-step", "people-of-badr"])
        back = {n: iri for iri, n in index.items()}
        for j in out:
            spec = shipped(j["key"])
            with self.subTest(j["key"]):
                self.assertEqual(j["title"], EN[spec["title"]])
                self.assertEqual(j["lead"], EN[spec["lead"]])
                self.assertEqual(j["type"], spec["select"]["type"])
                self.assertEqual(j["status"], "draft")
                self.assertTrue(j["steps"])
                self.assertEqual(len(j["why"]), len(j["steps"]))
                for rs in j["why"]:
                    for kind, other, text in rs:
                        self.assertIn(kind, V1_REASON_KINDS | {"record"})
                        self.assertIsInstance(text, str)
                        self.assertTrue(other == -1 or other in back)
                self.assertTrue(set(j["anchors"]) <= set(back))
        # the facade attributes the Atlas reads, and the computed copies it gets
        specs = J.load_specs(LEARN / "journeys")
        for spec in specs:
            for k in ("slug", "title", "lead", "status", "select", "story_mode"):
                self.assertIn(k, spec)
            self.assertIs(spec["story_mode"]["open"], False)
            j = J.build(self.site, spec)
            for st in j.steps + j.set_apart:
                self.assertIsInstance(st.iri, str)
                for r in st.reasons:
                    self.assertIn(r.kind, V1_REASON_KINDS)
                    self.assertTrue(hasattr(r, "other") and hasattr(r, "word") and hasattr(r, "label"))
                for c in st.records + st.contrary:
                    self.assertTrue(all(hasattr(c, a) for a in ("subject", "object", "predicate", "predicate_is_key")))
            self.assertIsInstance(j.anchors, list)
        self.assertEqual(J.FACADE_VERSION, 2)
        self.assertTrue(callable(J.build_all) and issubclass(J.RuleError, ValueError))

    def test_v1_order_is_unchanged_on_the_page_graph(self):
        want = json.loads(golden.ORDER_FILE.read_text(encoding="utf-8"))
        if golden.fingerprint(self.site.g) != want["graph"]["fingerprint"]:
            self.skipTest("the page graph changed since the v1 order was recorded")
        built = {j.slug: j for j in J.build_all(self.site, J.load_specs(LEARN / "journeys"))}
        self.assertEqual({slug: golden.order_facts(self.site, j) for slug, j in sorted(built.items())},
                         want["journeys"])

    def test_load_specs_reads_only_top_level_official_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "fixture-events.json").write_text(json.dumps(events_spec(["Rihla"])), encoding="utf-8")
            (folder / "method").mkdir()
            (folder / "method" / "how-to-read.json").write_text(json.dumps({"slug": "how-to-read", "kind": "method"}),
                                                                encoding="utf-8")
            (folder / "notes.txt").write_text("not a journey", encoding="utf-8")
            self.assertEqual([s["slug"] for s in J.load_specs(folder)], ["fixture-events"])
            lesson = dict(events_spec(["Rihla"]), slug="a-lesson", kind="teacher")
            (folder / "a-lesson.json").write_text(json.dumps(lesson), encoding="utf-8")
            with self.assertRaises(J.RuleError):
                J.load_specs(folder)

    def test_layer_keys_never_change_the_facade(self):
        index = node_index(self.site)
        def facade(extra: dict, slug="hijrah-step-by-step") -> list:
            with tempfile.TemporaryDirectory() as tmp:
                spec = shipped(slug)
                for k in ("lead_study", "hold_study", "story_mode"):
                    spec.pop(k, None)
                spec.update(extra)
                (Path(tmp) / f"{slug}.json").write_text(json.dumps(spec), encoding="utf-8")
                return atlas_load_journeys(self.site, index, self.fail, Path(tmp), LEARN / "i18n" / "en.json")
        base = facade({})
        for extra in ({"lead_study": "journey.hijrah.lead_study"}, {"hold_study": True}, {"hold_study": False},
                      {"story_mode": {"open": False, "approved_by": []}},
                      {"story_mode": {"open": False, "approved_by": [{"who": "review_board", "date": "2026-11-09"}]}}):
            with self.subTest(extra):
                self.assertEqual(facade(extra), base)

    def test_facade_reason_kinds_are_v1_kinds(self):
        for j in J.build_all(self.site, J.load_specs(LEARN / "journeys")):
            for st in j.steps + j.set_apart:
                self.assertTrue({r.kind for r in st.reasons + st.links} <= V1_REASON_KINDS, j.slug)

    def test_stable_slugs(self):
        self.assertEqual([s["slug"] for s in J.load_specs(LEARN / "journeys")],
                         ["first-believers", "hijrah-step-by-step", "people-of-badr"])

    def test_new_fields_have_defaults(self):
        e = self.site.by_kind["event"][0]
        st = J.Step(entity=e)
        self.assertEqual((st.side, st.group, st.side_conflict, st.e3), ([], "main", False, None))
        j = J.Journey({"slug": "x", "status": "draft"}, [st])
        self.assertEqual((j.excluded, j.groups, j.order_applied, j.lists), ([], [], None, None))
        for name in ("load_specs", "build", "build_all", "RuleError", "Journey", "Step", "Reason", "Links",
                     "tokens", "term", "validate"):
            self.assertTrue(hasattr(J, name), name)

    def test_learn_modules_do_not_shadow_other_modules(self):
        mine = {p.stem for p in LEARN.glob("*.py")}
        new = mine - {"build_learn", "journeys", "practice", "render_learn"}
        self.assertTrue(all(n.startswith("journey_") for n in new), sorted(new))
        others = set()
        for d in (ROOT / "site", ROOT / "site" / "observatory", ROOT / "ask", ROOT / "atlas"):
            others |= {p.stem for p in d.glob("*.py")} | {p.name for p in d.iterdir() if p.is_dir()} if d.is_dir() else set()
        try:
            listed = subprocess.run(["git", "-C", str(ROOT), "ls-tree", "--name-only", "origin/sky-atlas-new", "atlas/"],
                                    capture_output=True, text=True, timeout=30)
            others |= {Path(n).stem for n in listed.stdout.split() if n.endswith(".py")}
        except (OSError, subprocess.SubprocessError):
            pass
        self.assertEqual(sorted(mine & others), [])

    def test_lists_path_resolves_against_the_repository_root_not_the_cwd(self):
        spec = shipped("people-of-badr")
        want = J.sha12(json.loads((LEARN / "lists" / "people.json").read_text(encoding="utf-8"))["lists"])
        with tempfile.TemporaryDirectory() as tmp, cwd(tmp):
            self.assertEqual(J.lists_file(spec), ROOT / "learn" / "lists" / "people.json")
            self.assertEqual(J.lists_sha(spec), want)
            j = J.build(self.site, J.load_specs(LEARN / "journeys")[2])
            self.assertEqual(j.lists["sha"], want)
        code = ("import sys; sys.path[:0] = [sys.argv[1] + '/site', sys.argv[1] + '/learn']\n"
                "import journeys as J, json\n"
                "spec = json.load(open(sys.argv[1] + '/learn/journeys/people-of-badr.json'))\n"
                "print(J.lists_sha(spec))\n")
        with tempfile.TemporaryDirectory() as tmp:
            got = subprocess.run([sys.executable, "-c", code, str(ROOT)], cwd=tmp, capture_output=True, text=True,
                                 check=True).stdout.strip()
        self.assertEqual(got, want)


class Background(unittest.TestCase):
    """F11 (design §5): background is never a seed, never walked through, listed apart."""

    def bound(self, fx):
        site = site_of(fx)
        info = J.background_info(site)
        return info["after_source"], info["after_bound"], site

    def test_after_bound_comes_from_the_recorded_death_then_the_named_event_then_the_fallback(self):
        fx = Fx()
        p = fx.prophet()
        passing = fx.event("fxPassing", "The passing (fixture)", dates=("0632-06-10", "0632-06-12"), precision="day")
        fx.event("fxDeath", "Death of the Prophet ﷺ", dates=("0632-06-01", "0632-06-03"), precision="day")
        fx.claim(p, "rel_died_during", passing, ("rejected",))       # any status counts
        self.assertEqual(self.bound(fx)[:2], ("recorded_death", "0632-06-12"))
        fx = Fx()
        p = fx.prophet()
        a = fx.event("fxPassingA", "The passing (fixture)", dates=("0632-06-10", "0632-06-12"), precision="day")
        b = fx.event("fxPassingB", "Another passing (fixture)", dates=("0632-07-10", "0632-07-12"), precision="day")
        fx.claim(p, "rel_died_during", a)
        fx.claim(p, "rel_died_during", b)                              # two events: not "exactly one"
        fx.event("fxDeath", "Death of the Prophet ﷺ", dates=("0632-06-01", "0632-06-03"), precision="day")
        self.assertEqual(self.bound(fx)[:2], ("named_event", "0632-06-03"))
        fx = Fx()
        fx.prophet()
        fx.event("fxDeath", "Death of the Prophet ﷺ", dates=("0632-06-01", "0632-06-03"), precision="day")
        fx.event("fxNear", "Death of the Prophet's companion", dates=("0632-01-01", "0632-01-02"), precision="day")
        fx.event("fxUndated", "Death of the prophet")                 # undated: not a bound
        self.assertEqual(self.bound(fx)[:2], ("named_event", "0632-06-03"))
        fx = Fx()
        fx.event("fxDeath1", "Death of the Prophet", dates=("0632-06-01", "0632-06-03"), precision="day")
        fx.event("fxDeath2", "Death of the prophet ﷺ", dates=("0632-06-04", "0632-06-05"), precision="day")
        fx.event("fxDeath3", "The death of the prophet", dates=("0632-06-09", "0632-06-10"), precision="day")
        self.assertEqual(self.bound(fx)[:2], ("fallback", J.AFTER_FALLBACK))
        self.assertEqual(self.bound(Fx())[:2], ("fallback", "0632-12-31"))

    def fixture(self):
        fx = Fx()
        fx.event("fxDeath", "Death of the Prophet ﷺ", dates=("0632-06-06", "0632-06-08"), precision="day")
        named = fx.event("fxNamed", "The Rihla", dates=("0622-01-01", "0622-12-31"))
        later = fx.event("fxLaterRihla", "The Rihla, a later one", dates=("0650-01-01", "0650-12-31"))
        late_part = fx.event("fxLatePart", "A part dated later", dates=("0640-01-01", "0640-12-31"))
        deep = fx.event("fxDeep", "A part of the later part")
        coarse = fx.event("fxCoarse", "A part dated only to the year", dates=("0632-01-01", "0632-12-31"))
        fine = fx.event("fxFine", "A part dated to the day", dates=("0632-06-01", "0632-06-02"), precision="day")
        old = fx.event("fxOld", "A part long before", dates=("0500-01-01", "0510-12-31"))
        for part, whole in ((late_part, named), (deep, late_part), (coarse, named), (fine, named), (old, named)):
            fx.claim(part, "rel_part_of", whole)
        return fx, {"named": named, "later": later, "late_part": late_part, "deep": deep, "coarse": coarse,
                    "fine": fine, "old": old}

    def test_background_events_are_never_seeds_or_walked_through(self):
        fx, i = self.fixture()
        site = site_of(fx)
        j = J.build(site, J.validate(events_spec(["Rihla"], follow=["parts"], max_links=2)))
        got = {s.iri for s in j.steps}
        self.assertEqual(got, {i["named"], i["fine"]})
        self.assertNotIn(i["later"], got)       # a background seed
        self.assertNotIn(i["deep"], got)        # reached only through a background part
        self.assertEqual(dict(j.excluded), {i["later"]: "after_prophet", i["late_part"]: "after_prophet",
                                            i["coarse"]: "not_placed", i["old"]: "before"})
        self.assertEqual(J.background(site), {i["later"]: "after_prophet", i["late_part"]: "after_prophet",
                                              i["coarse"]: "not_placed", i["old"]: "before"})

    def test_coarse_events_containing_the_bound_are_not_placed_and_listed_as_excluded(self):
        fx, i = self.fixture()
        site = site_of(fx)
        self.assertEqual(J.background(site)[i["coarse"]], "not_placed")
        self.assertNotIn(i["fine"], J.background(site))            # dated to the day, before the bound
        # people: a background anchor chooses no one; stories: a background story is skipped
        fx, i = self.fixture()
        who = fx.person("fxWho", "Person A")
        fx.participation(i["coarse"], who)
        other = fx.person("fxOther", "Person B")
        fx.participation(i["named"], other)
        work = fx.story_doc("fxWork", "Fixture stories")
        part = fx.story_part("fxPart1", work, "Part 1: The Early Days", 1)
        s1 = fx.story("fxStory1", "The first story", 1, part)
        s2 = fx.story("fxStory2", "The second story", 2, part)
        fx.extent(s2, "0700-01-01", "0700-12-31")
        site = site_of(fx)
        spec = people_spec(words=("Rihla",), order="name")
        spec["select"]["events"].update(follow=["parts"], max_links=1)
        j = J.build(site, J.validate(spec))
        self.assertEqual([s.iri for s in j.steps], [other])
        self.assertNotIn(i["coarse"], j.anchors)
        self.assertIn((i["coarse"], "not_placed"), j.excluded)
        j = J.build(site, J.validate(stories_spec()))
        self.assertEqual([s.iri for s in j.steps], [s1])
        self.assertEqual(j.excluded, [(s2, "after_prophet")])

    def test_the_marker_makes_anything_background(self):
        fx = Fx()
        named = fx.event("fxNamed", "The Rihla")
        fx.out.append(f"<{named}> <https://w3id.org/marsad/core#fixtureBackground> true .")
        site = site_of(fx)
        self.assertEqual(J.background(site), {})
        old = J.BACKGROUND_MARKER
        J.BACKGROUND_MARKER = "https://w3id.org/marsad/core#fixtureBackground"
        try:
            self.assertEqual(J.background(site), {named: "marker"})
            self.assertEqual(J.background_info(site)["marker"], J.BACKGROUND_MARKER)
        finally:
            J.BACKGROUND_MARKER = old
        self.assertEqual(J.background(site), {})


@unittest.skipUnless(GRAPH.exists(), "build/graph.ttl missing: run ontology/build_graph.py")
class BackgroundOnTheGraph(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = Site(GRAPH)
        cls.bg = J.background(cls.site)
        cls.info = J.background_info(cls.site)

    def test_page_graph_after_source_is_named_event(self):
        self.assertIn(self.info["after_source"], ("recorded_death", "named_event"))
        named = [e for e in self.site.by_kind["event"] if J._bounds(e)[1]
                 and any(J.token_seq(lab) == list(J.DEATH_OF_THE_PROPHET) for lab in J.labels_of(self.site, e.iri))]
        if self.info["after_source"] == "named_event":
            self.assertEqual(len(named), 1)
            self.assertEqual(self.info["after_bound"], J._bounds(named[0])[1][:10])

    def test_every_flagged_event_meets_its_rule_and_no_unflagged_event_does(self):
        bound = J._day(self.info["after_bound"])
        before = J._day(J.BACKGROUND_BEFORE)
        for kind in ("event", "story"):
            for e in self.site.by_kind[kind]:
                exts = e.data.get("dates") or []
                starts = [J._day(x.get("earliest")) for x in exts]
                ends = [J._day(x.get("latest")) for x in exts]
                after = bool(exts) and all(s and s > bound for s in starts)
                coarse = kind == "event" and bool(exts) and all(
                    x.get("precision") != "day" and s and en and s <= bound <= en for x, s, en in zip(exts, starts, ends))
                old = bool(exts) and all(en and en < before for en in ends)
                want = "after_prophet" if after else "not_placed" if coarse else "before" if old else None
                with self.subTest(e.name):
                    self.assertEqual(self.bg.get(e.iri), want)

    def test_lineage_only_people_are_not_background(self):
        self.assertIsNone(J.BACKGROUND_MARKER)
        kinds = {self.site.entity(i).kind for i in self.bg}
        self.assertTrue(kinds <= {"event", "story"}, kinds)

    def test_shipped_journeys_have_no_background_step(self):
        for j in J.build_all(self.site, J.load_specs(LEARN / "journeys")):
            with self.subTest(j.slug):
                for iri in [s.iri for s in j.steps + j.set_apart] + j.anchors:
                    self.assertNotIn(iri, self.bg)
                self.assertTrue(all(iri in self.bg for iri, _ in j.excluded))


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
        self.assertIs(j.spec["hold_study"], True)

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

    def test_badr_not_words_remove_exactly_the_named_anchors_whose_labels_hold_them(self):
        rule = shipped("people-of-badr")["select"]["events"]
        not_words = rule["named"]["not_words"]
        wide = copy.deepcopy(rule)
        del wide["named"]["not_words"]
        seeds_wide = {i for i, h in J.select_events(self.site, self.links, wide)[0].items() if h == 0}
        hop = J.select_events(self.site, self.links, rule)[0]
        seeds = {i for i, h in hop.items() if h == 0}
        holds = {i for i in seeds_wide if self.tokens_of(i) & {w.lower() for w in not_words}}
        self.assertEqual(seeds, seeds_wide - holds)
        self.assertEqual(set(self.j["people-of-badr"].anchors), set(hop))

    def test_badr_order_is_the_v1_order_inside_each_group_while_the_list_is_unreviewed(self):
        j = self.j["people-of-badr"]
        self.assertEqual(j.lists["state"], "proposed")
        self.assertEqual(j.order_applied, "e3_pending")
        self.assertFalse(j.lists["applied"])
        self.assertEqual([g.key for g in j.groups][:1], ["main"])
        self.assertEqual(sum(g.end - g.start for g in j.groups), len(j.steps))
        for g in j.groups:
            inside = j.steps[g.start:g.end]
            self.assertTrue(all(st.group == g.key for st in inside))
            v1 = sorted(inside, key=lambda st: (not st.entity.prophet, display.sort_key(st.entity.name), st.entity.pid))
            self.assertEqual([s.iri for s in inside], [s.iri for s in v1], g.key)
        v1 = sorted(j.set_apart, key=lambda st: (not st.entity.prophet, display.sort_key(st.entity.name), st.entity.pid))
        self.assertEqual([s.iri for s in j.set_apart], [s.iri for s in v1])
        for st in j.steps + j.set_apart:
            self.assertEqual(st.e3["tier"], 0 if st.entity.prophet else None)
            self.assertEqual(st.e3["links"], len(self.site.claims.get(st.iri, [])))

    def test_every_against_group_person_has_a_cited_subject_side_claim_at_an_anchor(self):
        j = self.j["people-of-badr"]
        anchors = set(j.anchors)
        for st in j.steps + j.set_apart:
            sides = set()
            for c in self.site.claims.get(st.iri, []):
                if c.kind != "assertion" or c.subject != st.iri:
                    continue
                pred = self.site.g.value(URIRef(c.node), MRS.predicate)
                at = self.site.g.value(URIRef(c.node), MRS.atEvent)
                other = self.site.entity(c.object)
                if pred in J.SIDE and at is not None and str(at) in anchors and other is not None and other.prophet \
                        and c.citation and not J.claim_statuses(self.site, c) & set(J.NOT_SHOWN):
                    sides.add(J.SIDE[pred])
            with self.subTest(st.entity.name):
                self.assertEqual({J.side_of(self.site, c) for c in st.side}, sides)
                self.assertTrue(all(c.subject == st.iri for c in st.side))
                if st in j.steps:
                    want = "against" if sides == {"against"} and not st.entity.prophet else "main"
                    self.assertEqual(st.group, want)
                self.assertEqual(st.side_conflict, sides == {"alongside", "against"})
        for st in j.steps:
            if st.entity.prophet:
                self.assertEqual(st.side, [])
                self.assertEqual(st.group, "main")

    def test_the_shipped_list_names_match_one_person_each(self):
        lists = JL.load_lists(LEARN / "lists" / "people.json")
        self.assertEqual(lists["state"], "proposed")
        self.assertFalse(lists["sources_complete"])
        for ls in lists["lists"]:
            got = JL.match_members(self.site, ls["members"])
            self.assertEqual(len(set(got)), len(ls["members"]))
            self.assertTrue(all(self.site.entity(i).kind == "person" for i in got))

    def test_first_believers_are_the_makkan_part_in_reading_order(self):
        j = self.j["first-believers"]
        want = [e for e in self.site.stories_in_order() if "makkan" in J.tokens(e.data.get("part_label") or "")]
        self.assertEqual([s.iri for s in j.steps], [e.iri for e in want])
        numbers = [s.entity.data["number"] for s in j.steps]
        self.assertEqual(numbers, sorted(numbers))

    def test_no_entity_id_is_written_in_the_learn_sources(self):
        payloads = {e.pid for e in self.site.entities.values()}
        for path in learn_sources():
            text = path.read_text(encoding="utf-8")
            self.assertEqual(sorted(p for p in payloads if p in text), [], path)


if __name__ == "__main__":
    unittest.main()
