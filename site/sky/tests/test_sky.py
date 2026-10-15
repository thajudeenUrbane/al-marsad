"""Tests for the Sky builder. Needs build/graph.ttl (run ontology/build_graph.py first);
every test that reads the graph is skipped without it.

Run:  .venv/bin/python -m unittest discover -s site/sky/tests -v
"""
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKY = Path(__file__).resolve().parents[1]
SITE = SKY.parent
ROOT = SITE.parent
OBS = SITE / "observatory"
for p in (SKY, OBS, SITE):
    sys.path.insert(0, str(p))

GRAPH = ROOT / "build" / "graph.ttl"
BUILDER = SKY / "build_sky.py"
SOURCES = [p for p in SKY.rglob("*") if p.is_file() and p.suffix in {".py", ".js", ".cjs", ".json", ".html", ".css"}
           and "tests" not in p.parts]


def _page_payload(html_text: str) -> dict:
    m = re.search(r'<script type="application/json" id="obs-data">(.*?)</script>', html_text, re.S)
    return json.loads(m.group(1))


@unittest.skipUnless(GRAPH.exists(), "build/graph.ttl missing: run ontology/build_graph.py")
class SkyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import build_sky
        cls.bs = build_sky
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "dist" / "sky"
        cls.summary = build_sky.build(GRAPH, cls.out, quiet=True)
        cls.html = (cls.out / "index.html").read_text(encoding="utf-8")
        cls.data = _page_payload(cls.html)
        cls.nodes = cls.data["nodes"]
        cls.sky = cls.data["frames"]["network"]
        cls.light = cls.data["meta"]["light"]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def p3(self, i):
        p = self.sky["pos3"]
        return p[3 * i], p[3 * i + 1], p[3 * i + 2]

    def test_deterministic_across_processes_and_hash_seeds(self):
        """Two separate builds with different hash seeds produce the same page byte for byte."""
        outs = []
        for seed in ("1", "4242"):
            with tempfile.TemporaryDirectory() as d:
                out = Path(d) / "dist" / "sky"
                env = dict(os.environ, PYTHONHASHSEED=seed)
                subprocess.run([sys.executable, str(BUILDER), "--graph", str(GRAPH), "--out", str(out)],
                               check=True, env=env, cwd=ROOT, capture_output=True)
                outs.append((out / "index.html").read_bytes())
        self.assertEqual(outs[0], outs[1], "the page differs between two builds")

    def test_every_item_has_a_3d_position_and_the_flat_frames_are_the_observatorys(self):
        n = len(self.nodes)
        self.assertEqual(len(self.sky["pos3"]), 3 * n)
        self.assertEqual(len(self.sky["region"]), n)
        self.assertTrue(all(math.isfinite(v) for v in self.sky["pos3"]))
        from frames import compute_frames
        from model import Site
        from obsdata import ObsData, Translator
        t = Translator(self.bs.strings())
        flat = compute_frames(ObsData(Site(GRAPH), t), t)
        for f in ("time", "geo", "stories", "isnad"):
            self.assertEqual(self.data["frames"][f]["pos"], flat[f]["pos"], f"frame {f} differs from the Observatory's")

    def test_the_light_is_the_prophet_at_the_origin(self):
        import display
        self.assertIsNotNone(self.light)
        nd = self.nodes[self.light]
        self.assertEqual(nd["k"], "person")
        self.assertTrue(display.is_prophet_label(nd["n"]))
        self.assertTrue(nd["n"].endswith(display.PBUH_SIGN))
        self.assertEqual(self.p3(self.light), (0.0, 0.0, 0.0))
        self.assertEqual(self.sky["region"][self.light], "light")

    def test_stories_sit_on_the_ring_in_reading_order(self):
        stories = sorted((i for i, nd in enumerate(self.nodes) if nd["k"] == "story"), key=lambda i: self.nodes[i]["no"])
        ring = self.sky["ring"]
        angles = []
        for i in stories:
            x, y, z = self.p3(i)
            self.assertEqual(z, 0.0)
            self.assertAlmostEqual(math.hypot(x, y), ring, delta=0.2)
            self.assertEqual(self.sky["region"][i], "ring")
            angles.append((math.atan2(y, x) + math.pi / 2) % math.tau)
        self.assertEqual(angles, sorted(angles), "stories are not in reading order round the ring")

    def test_distance_from_the_light_follows_recorded_generation_only(self):
        """Every Companion is nearer the light than every Successor, and so on outwards."""
        by_gen = {}
        for i, nd in enumerate(self.nodes):
            if nd["k"] == "person" and i != self.light and nd.get("tbk"):
                by_gen.setdefault(nd["tbk"], []).append(math.dist((0, 0, 0), self.p3(i)))
                self.assertEqual(self.sky["region"][i], "shell")
        from obsdata import TABAQA_ORDER
        present = [g for g in TABAQA_ORDER if g in by_gen]
        self.assertGreaterEqual(len(present), 2)
        for inner, outer in zip(present, present[1:]):
            self.assertLess(max(by_gen[inner]), min(by_gen[outer]), f"{inner} and {outer} shells overlap")

    def test_no_position_or_size_by_how_many_links(self):
        """The layout never reads a degree to place anything; the renderer sizes no mark by a measure."""
        layout = (SKY / "skylayout.py").read_text(encoding="utf-8")
        targets = [line for line in layout.splitlines() if "target[i] =" in line or "goal =" in line]
        self.assertTrue(targets)
        for line in targets:
            self.assertNotIn("deg", line.split("#")[0], f"a target radius reads a degree: {line.strip()}")
        js = (SKY / "static" / "render3d.js").read_text(encoding="utf-8")
        self.assertNotRegex(js, r"(?i)centrality|pagerank|betweenness|shadowBlur|adj\[|\.cl\.length")
        self.assertRegex(js, r"const radius = \(i\) => [^;]*mag\(i\)")  # one size rule for every mark: distance only
        self.assertNotRegex(js.split("const radius")[1].split(";")[0], r"deg|adj|N\[i\]")

    def test_brightness_is_generation_and_can_be_switched_off(self):
        js = (SKY / "static" / "render3d.js").read_text(encoding="utf-8")
        self.assertRegex(js, r"const GEN = \{ sahabi:")
        self.assertIn('toggle("sky-generation", "generation"', js)
        self.assertIn('id="sky-generation"', self.html)

    def test_presets_carry_over_and_point_at_real_items(self):
        n = len(self.nodes)
        self.assertGreaterEqual(len(self.data["presets"]), 3)
        for p in self.data["presets"]:
            self.assertIn(p["frame"], self.data["frames"])
            self.assertTrue(all(0 <= i < n for i in p["hl"]))

    def test_every_ui_string_is_a_key(self):
        strings = self.bs.strings()
        js = "\n".join(f.read_text(encoding="utf-8") for f in self.bs.JS_FILES)
        for key in set(re.findall(r'\bt\("([a-z0-9_.]+)"', js)):
            if key.endswith("."):
                continue
            self.assertIn(key, strings, f"a script uses a missing key {key}")
        for msg in set(re.findall(r'toggle\("[a-z-]+", "[a-z]+", "([a-z_.]+)"\)', js)):
            self.assertIn(msg + ".on", strings)
            self.assertIn(msg + ".off", strings)
        tpl = self.bs.TEMPLATE.read_text(encoding="utf-8")
        for key in set(re.findall(r"\{\{t:([a-z0-9_.]+)\}\}", tpl)):
            self.assertIn(key, strings, f"template.html uses a missing key {key}")
        visible_text = re.sub(r"\{\{[^}]+\}\}", "", re.sub(r"<[^>]+>", " ", tpl))
        self.assertFalse(re.search(r"[A-Za-z]{3,}", visible_text), "template.html has text that is not an i18n key")
        for r in set(self.sky["region"]):
            self.assertIn(f"textalt.region.network.{r}", strings)
            self.assertIn(f"textalt.region_title.network.{r}", strings)
        sky_only = json.loads((SKY / "i18n" / "en.json").read_text(encoding="utf-8"))
        self.assertTrue(sky_only, "the Sky has strings of its own")

    def test_page_is_self_contained_and_within_budget(self):
        self.assertLessEqual(len(self.html.encode("utf-8")), self.bs.BUDGET)
        self.assertNotRegex(self.html, r"<script[^>]+src=", "external script")
        self.assertNotRegex(self.html, r"<link[^>]+rel=.?stylesheet", "external stylesheet")
        self.assertNotRegex(self.html, r"<img|@import|url\(\s*['\"]?https?:", "external resource")
        js = (SKY / "static" / "render3d.js").read_text(encoding="utf-8")
        self.assertNotRegex(js, r"\bfetch\(|XMLHttpRequest|import\(|WebSocket|EventSource", "network call in the script")
        self.assertIn("<title>Sky", self.html)

    def test_css_uses_logical_properties_only(self):
        css = re.sub(r"/\*.*?\*/", "", (SKY / "static" / "sky.css").read_text(encoding="utf-8"), flags=re.S)
        self.assertNotRegex(css, r"(margin|padding|border)-(left|right|top|bottom)\b")
        self.assertNotRegex(css, r"(^|[;{\s])(left|right|top|bottom)\s*:")
        self.assertNotRegex(css, r"(text-align|float|clear)\s*:\s*(left|right)")

    def test_every_colour_the_renderer_reads_is_defined(self):
        css = (SKY / "static" / "sky.css").read_text(encoding="utf-8") + (OBS / "static" / "observatory.css").read_text(encoding="utf-8")
        js = (SKY / "static" / "render3d.js").read_text(encoding="utf-8")
        names = set(re.findall(r'cv\("(--[a-z0-9-]+)"\)', js)) | {"--l-" + c for c in ("participation", "kinship", "social_political", "spatial", "transmission")}
        for name in names:
            self.assertRegex(css, re.escape(name) + r"\s*:", f"{name} is not defined in the CSS")

    def test_no_hard_coded_ids_in_the_sky_sources(self):
        ids = {nd["id"] for nd in self.nodes}
        token = re.compile(r"[0-9A-Za-z]{20,24}")
        for path in SOURCES:
            hits = {m for m in token.findall(path.read_text(encoding="utf-8")) if m in ids}
            self.assertFalse(hits, f"{path.relative_to(ROOT)} hard-codes entity IDs: {sorted(hits)[:3]}")


if __name__ == "__main__":
    unittest.main()
