"""Tests for the Sky Atlas build that need no graph: the layout, the event order, the
citation split, the strings and the standing rules on the page's sources.

    .venv/bin/python -m unittest discover -s atlas/tests
"""
import csv
import json
import math
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ATLAS = HERE.parent
ROOT = ATLAS.parent
for p in (ATLAS, ROOT / "site" / "observatory", ROOT / "site", ROOT / "learn"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import layout  # noqa: E402


def node(i, kind, **kw):
    return {"id": f"id{i:04d}", "k": kind, **kw}


def tiny():
    """A light, three events (one dated but never named in the text), two people."""
    nodes = [node(0, "person"), node(1, "event", d=[[624.0, 624.5, "624", []]]), node(2, "event"),
             node(3, "event", d=[[624.1, 624.2, "624", []]]), node(4, "person"), node(5, "person")]
    links = [{"a": 1, "b": 4, "c": "participation"}, {"a": 2, "b": 5, "c": "participation"},
             {"a": 4, "b": 5, "c": "kinship"}, {"a": 0, "b": 4, "c": "kinship"}]
    tell = {1: 500, 2: 100}
    return nodes, links, tell


class Layout(unittest.TestCase):
    def test_event_order_follows_the_text_and_places_dated_events_among_their_years(self):
        nodes, _links, tell = tiny()
        order = [i for i, _k in layout.event_order(nodes, tell)]
        self.assertEqual(order, [2, 1, 3])  # 3 is never named: it sits with 1, whose years overlap

    def test_light_is_at_the_origin_and_events_on_the_spiral(self):
        nodes, links, tell = tiny()
        out = layout.sky(nodes, links, tell, 0, set())
        p = out["pos"]
        self.assertEqual(p[0:3], [0.0, 0.0, 0.0])
        for i in (1, 2, 3):
            r = math.sqrt(p[3 * i] ** 2 + p[3 * i + 1] ** 2 + p[3 * i + 2] ** 2)
            self.assertAlmostEqual(r, layout.R_SPIRAL, delta=0.5)
        self.assertEqual([e[0] for e in out["ecliptic"]], [2, 1, 3])
        for i in (4, 5):  # nobody but the light inside the clear space
            r = math.sqrt(p[3 * i] ** 2 + p[3 * i + 1] ** 2 + p[3 * i + 2] ** 2)
            self.assertGreater(r, layout.R_CLEAR - 1)

    def test_layout_is_deterministic(self):
        nodes, links, tell = tiny()
        self.assertEqual(layout.sky(nodes, links, tell, 0, {5}), layout.sky(nodes, links, tell, 0, {5}))

    def test_spiral_runs_from_north_to_south(self):
        self.assertGreater(layout.spiral_point(0)[1], 0)
        self.assertLess(layout.spiral_point(1)[1], 0)


class BuildHelpers(unittest.TestCase):
    def setUp(self):
        import importlib.util  # by path: site/build.py shares the module name
        spec = importlib.util.spec_from_file_location("atlas_build", ATLAS / "build.py")
        self.b = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.b)

    def test_gloss_and_role(self):
        g, r = self.b.gloss_or_role(self.b.GLOSS_PREFIX + "X led Y.")
        self.assertEqual((g, r), ("X led Y.", None))
        self.assertEqual(self.b.gloss_or_role("commander"), (None, "commander"))

    def test_citation_split_keeps_every_character(self):
        pre = {}
        cit = "Ibn Hishām, al-Sīra al-Nabawiyya (al-Saqqā et al. ed., Cairo 1375/1955; provisional), vol. 1, p. 666; OpenITI ms442, lines 12244–12247"
        k, rest = self.b.split_citation(cit, pre)
        self.assertEqual(list(pre)[k] + ", " + rest, cit)
        self.assertEqual(self.b.split_citation(None, pre), (None, None))


class Strings(unittest.TestCase):
    def test_arabic_has_every_english_key_and_the_page_uses_only_known_keys(self):
        en = json.loads((ATLAS / "i18n" / "en.json").read_text(encoding="utf-8"))
        ar = json.loads((ATLAS / "i18n" / "ar.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(set(en) - set(ar)), [])
        src = "".join(f.read_text(encoding="utf-8") for f in sorted((ATLAS / "static" / "app").glob("*.js"))) + (ATLAS / "static" / "template.html").read_text(encoding="utf-8")
        used = set(re.findall(r'\bt\("([a-z0-9_.\-]+)"', src)) | set(re.findall(r"\{\{t:([a-z0-9_.]+)\}\}", src))
        used |= set(re.findall(r'data-i18n(?:-ph|-aria)?="([a-z0-9_.]+)"', src))
        missing = sorted(k for k in used if k not in en and not k.endswith("."))
        self.assertEqual(missing, [])

    def test_every_predicate_in_relations_has_an_arabic_label_or_is_unused(self):
        ar = json.loads((ATLAS / "i18n" / "ar.json").read_text(encoding="utf-8"))
        self.assertTrue(any(k.startswith("pred.") for k in ar))


class StandingRules(unittest.TestCase):
    def test_no_entity_id_in_the_page_sources(self):
        ids = set()
        with (ROOT / "ontology" / "corpus" / "identity.csv").open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                ids.add(row["canonical_id"].split(":", 1)[-1])
        for f in sorted(p for p in (ATLAS / "static").rglob("*") if p.is_file()):
            text = f.read_text(encoding="utf-8")
            found = [t for t in re.findall(r"[A-Za-z0-9]{20,24}", text) if t in ids]
            self.assertEqual(found, [], f.name)

    def test_lists_name_people_by_name_and_carry_a_source_and_status(self):
        spec = json.loads((ATLAS / "data" / "lists.json").read_text(encoding="utf-8"))
        self.assertEqual(spec["status"], "proposed")
        for ls in spec["lists"]:
            self.assertTrue(ls["source"])
            for m in ls["members"]:
                self.assertNotRegex(m, r"^[A-Za-z0-9]{20,24}$")

    def test_no_model_names_in_the_atlas(self):
        for f in [p for p in ATLAS.rglob("*") if p.is_file() and p.suffix in (".py", ".js", ".json", ".html", ".css", ".md", ".cjs") and p.name != "index.html"]:
            self.assertNotRegex(f.read_text(encoding="utf-8"), r"claude-(opus|sonnet|haiku|fable)", f.name)


if __name__ == "__main__":
    unittest.main()
