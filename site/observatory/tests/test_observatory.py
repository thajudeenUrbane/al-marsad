"""Tests for the Observatory builder. Needs build/graph.ttl (run ontology/build_graph.py
first); every test that reads the graph is skipped without it.

Run:  .venv/bin/python -m unittest discover -s site/observatory/tests -v
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

OBS = Path(__file__).resolve().parents[1]
SITE = OBS.parent
ROOT = SITE.parent
sys.path.insert(0, str(OBS))
sys.path.insert(0, str(SITE))

GRAPH = ROOT / "build" / "graph.ttl"
BUILDER = OBS / "build_observatory.py"
SOURCES = [p for p in OBS.rglob("*") if p.is_file() and p.suffix in {".py", ".js", ".cjs", ".json", ".html", ".css"}
           and "tests" not in p.parts]


def _page_payload(html_text: str) -> dict:
    m = re.search(r'<script type="application/json" id="obs-data">(.*?)</script>', html_text, re.S)
    return json.loads(m.group(1))


@unittest.skipUnless(GRAPH.exists(), "build/graph.ttl missing: run ontology/build_graph.py")
class ObservatoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import build_observatory as bo
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "dist" / "observatory"
        cls.summary = bo.build(GRAPH, cls.out, quiet=True)
        cls.html = (cls.out / "index.html").read_text(encoding="utf-8")
        cls.data = _page_payload(cls.html)
        cls.nodes = cls.data["nodes"]
        cls.frames = cls.data["frames"]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def pos(self, frame, i):
        p = self.frames[frame]["pos"]
        return p[2 * i], p[2 * i + 1]

    # ------------------------------------------------------------------ determinism
    def test_frames_deterministic_across_processes_and_hash_seeds(self):
        """Two separate builds with different hash seeds produce the same page byte for byte."""
        outs = []
        for seed in ("1", "4242"):
            with tempfile.TemporaryDirectory() as d:
                out = Path(d) / "dist" / "observatory"
                env = dict(os.environ, PYTHONHASHSEED=seed)
                subprocess.run([sys.executable, str(BUILDER), "--graph", str(GRAPH), "--out", str(out)],
                               check=True, env=env, cwd=ROOT, capture_output=True)
                outs.append((out / "index.html").read_bytes())
        self.assertEqual(outs[0], outs[1], "the page differs between two builds")
        self.assertEqual(_page_payload(outs[0].decode("utf-8"))["frames"], self.frames)

    def test_every_node_has_a_position_in_every_frame(self):
        n = len(self.nodes)
        for name in ("network", "time", "geo", "stories", "isnad"):
            f = self.frames[name]
            self.assertEqual(len(f["pos"]), 2 * n, name)
            self.assertEqual(len(f["region"]), n, name)
            self.assertTrue(all(isinstance(v, (int, float)) and math.isfinite(v) for v in f["pos"]), name)

    # ------------------------------------------------------------------ time
    def test_no_undated_item_on_the_time_axis(self):
        f = self.frames["time"]
        ax = f["axis"]
        X = lambda yr: ax["x0"] + (yr - ax["y0"]) / (ax["y1"] - ax["y0"]) * (ax["x1"] - ax["x0"])  # noqa: E731
        on_axis = 0
        for i, nd in enumerate(self.nodes):
            region = f["region"][i]
            if region == "axis":
                on_axis += 1
                self.assertTrue(nd.get("mk"), f"{nd['n']} is on the time axis without a recorded date")
                x, _ = self.pos("time", i)
                lo, hi = min(m[0] for m in nd["mk"]), max(m[1] for m in nd["mk"])
                self.assertTrue(X(lo) - 0.2 <= x <= X(hi) + 0.2, f"{nd['n']} placed outside its recorded range")
                self.assertIn(str(i), f["marks"], nd["n"])
            else:
                self.assertFalse(nd.get("mk"), f"{nd['n']} has a recorded date but is off the axis")
                self.assertNotIn(str(i), f["marks"])
            if region == "band":
                self.assertTrue(nd.get("tb"), f"{nd['n']} is in the generation band without a recorded ṭabaqa")
        self.assertGreater(on_axis, 0)

    def test_people_on_the_axis_only_by_dated_events_they_attended_or_a_recorded_death(self):
        claims, links = self.data["claims"], self.data["links"]
        for i, nd in enumerate(self.nodes):
            if nd["k"] != "person" or not nd.get("mk"):
                continue
            allowed = []
            for l in links:
                if i not in (l["a"], l["b"]):
                    continue
                other = l["b"] if l["a"] == i else l["a"]
                if self.nodes[other]["k"] != "event":
                    continue
                if all(claims[ci].get("pk") == "absent_from" for ci in l["cl"]):
                    continue
                allowed += [[d[0], d[1]] for d in self.nodes[other].get("d", []) if d[0] is not None]
            allowed += [[d[0], d[1]] for d in nd.get("death", []) if d[0] is not None]
            for m in nd["mk"]:
                self.assertIn(m, allowed, f"{nd['n']}: a date mark that no recorded event or death gives")

    # ------------------------------------------------------------------ geography
    def test_no_unlocated_item_on_the_map(self):
        f = self.frames["geo"]
        on_map = 0
        for i, nd in enumerate(self.nodes):
            if f["region"][i] != "map":
                if nd["k"] == "place":
                    self.assertNotIn("geo", nd, f"{nd['n']} has coordinates but is off the map")
                else:
                    self.assertNotIn("pl", nd, f"{nd['n']} has a located place but is off the map")
                continue
            on_map += 1
            if nd["k"] == "place":
                self.assertIn("geo", nd, f"{nd['n']} is on the map without recorded coordinates")
            else:
                self.assertIn("pl", nd, f"{nd['n']} is on the map without a located place")
                place = nd["pl"]
                self.assertIn("geo", self.nodes[place])
                (x, y), (px, py) = self.pos("geo", i), self.pos("geo", place)
                self.assertLess(math.hypot(x - px, y - py), 80, f"{nd['n']} is drawn away from {self.nodes[place]['n']}")
        self.assertGreater(on_map, 0)

    def test_map_positions_follow_the_recorded_coordinates(self):
        located = [(i, nd) for i, nd in enumerate(self.nodes) if nd["k"] == "place" and "geo" in nd]
        self.assertGreater(len(located), 1)
        for (i, a), (j, b) in zip(located, located[1:]):
            (xa, ya), (xb, yb) = self.pos("geo", i), self.pos("geo", j)
            if a["geo"][0] != b["geo"][0]:
                self.assertEqual(xa < xb, a["geo"][0] < b["geo"][0], "east-west order changed")
            if a["geo"][1] != b["geo"][1]:
                self.assertEqual(ya > yb, a["geo"][1] < b["geo"][1], "north-south order changed")

    # ------------------------------------------------------------------ stories and transmission
    def test_stories_frame_places_every_story_on_the_dial(self):
        f = self.frames["stories"]
        for i, nd in enumerate(self.nodes):
            if nd["k"] == "story":
                self.assertEqual(f["region"][i], "dial", nd["n"])

    def test_transmission_frame_shows_only_recorded_chains(self):
        f = self.frames["isnad"]
        on_chain = {i for i, r in enumerate(f["region"]) if r == "chain"}
        recorded = set()
        for ch in self.data["chains"]:
            for ln in ch["links"]:
                recorded.update(ln[:2])
            if ch["collector"] is not None:
                recorded.add(ch["collector"])
        self.assertEqual(on_chain, recorded)
        transmission_links = [l for l in self.data["links"] if l["c"] == "transmission"]
        self.assertEqual(len(transmission_links), sum(len(ch["links"]) for ch in self.data["chains"]))

    # ------------------------------------------------------------------ claims, statuses, sources
    def test_every_link_carries_its_claim_status_and_source(self):
        claims, sources = self.data["claims"], self.data["sources"]
        self.assertTrue(self.data["links"])
        for l in self.data["links"]:
            self.assertTrue(l["cl"], l)
            for ci in l["cl"]:
                c = claims[ci]
                self.assertIn("st", c, c)  # the status, or null where the graph records none
                self.assertIsNotNone(c.get("src"), f"claim without a recorded source: {c}")
                self.assertLess(c["src"], len(sources))
                if c["k"] == "a":
                    self.assertIsNotNone(c["st"], f"an Assertion without its status: {c}")
                else:
                    self.assertIsNone(c["st"], f"a record link was given a status it does not have: {c}")
                if "w" in c:
                    self.assertEqual(sources[c["w"]]["kind"], "work")

    def test_statuses_match_the_graph_and_none_is_upgraded(self):
        from rdflib import Graph, Namespace
        from rdflib.namespace import RDF
        mrs = Namespace("https://w3id.org/marsad/core#")
        g = Graph()
        g.parse(str(GRAPH), format="turtle")
        recorded = {}
        for a in g.subjects(RDF.type, mrs.Assertion):
            st = g.value(a, mrs.assertionStatus)
            recorded[str(a).rsplit("/", 1)[-1]] = str(st).split("#")[-1][3:] if st is not None else None
        seen = 0
        for c in self.data["claims"]:
            if c["k"] == "a":
                self.assertEqual(c["st"], recorded[c["id"]], c["id"])
                seen += 1
        self.assertEqual(self.data["meta"]["counts"]["assertions"], seen)

    def test_fifty_stories_claims_are_marked_ai_generated(self):
        works = [s for s in self.data["sources"] if s["kind"] == "work" and s["label"].startswith("50 Stories")]
        self.assertTrue(works)
        self.assertTrue(all(w["ai"] for w in works))

    # ------------------------------------------------------------------ IDs, presets, strings
    def test_no_hard_coded_ids_in_the_observatory_sources(self):
        ids = {nd["id"] for nd in self.nodes}
        token = re.compile(r"[0-9A-Za-z]{20,24}")
        for path in SOURCES:
            text = path.read_text(encoding="utf-8")
            hits = {m for m in token.findall(text) if m in ids}
            self.assertFalse(hits, f"{path.relative_to(ROOT)} hard-codes entity IDs: {sorted(hits)[:3]}")

    def test_presets_are_found_by_name_and_point_at_real_items(self):
        presets = self.data["presets"]
        self.assertGreaterEqual(len(presets), 3)
        strings = json.loads((OBS / "i18n" / "en.json").read_text(encoding="utf-8"))
        n = len(self.nodes)
        for p in presets:
            self.assertIn(f"preset.{p['key']}", strings)
            self.assertIn(p["frame"], self.frames)
            self.assertTrue(p["hl"])
            self.assertTrue(all(0 <= i < n for i in p["hl"]))
            if p.get("focus") is not None:
                self.assertIn(p["focus"], p["hl"])

    def test_every_ui_string_is_a_key_in_en_json(self):
        strings = json.loads((OBS / "i18n" / "en.json").read_text(encoding="utf-8"))
        js = (OBS / "static" / "observatory.js").read_text(encoding="utf-8")
        for key in set(re.findall(r'\bt\("([a-z0-9_.]+)"', js)):
            if key.endswith("."):
                continue  # a prefix completed at run time; the families are checked below
            self.assertTrue(key in strings, f"observatory.js uses a missing key {key}")
        tpl = (OBS / "static" / "template.html").read_text(encoding="utf-8")
        for key in set(re.findall(r"\{\{t:([a-z0-9_.]+)\}\}", tpl)):
            self.assertTrue(key in strings, f"template.html uses a missing key {key}")
        visible_text = re.sub(r"\{\{[^}]+\}\}", "", re.sub(r"<[^>]+>", " ", tpl))
        self.assertFalse(re.search(r"[A-Za-z]{3,}", visible_text), "template.html has text that is not an i18n key")
        for kind in ("person", "group", "place", "event", "story"):
            for prefix in ("kind.", "kind.plural.", "legend.kind."):
                self.assertIn(prefix + kind, strings)
        for cls in ("participation", "kinship", "social_political", "spatial", "transmission"):
            self.assertIn("class." + cls, strings)
            self.assertIn("legend.class." + cls, strings)
        for frame, regions in {"network": ("main", "shelf"), "time": ("axis", "band", "shelf"), "geo": ("map", "shelf"),
                               "stories": ("dial", "shelf"), "isnad": ("chain", "shelf")}.items():
            self.assertIn("frame." + frame, strings)
            self.assertIn("textalt.frame." + frame, strings)
            for r in regions:
                self.assertIn(f"textalt.region.{frame}.{r}", strings)
                self.assertIn(f"textalt.region_title.{frame}.{r}", strings)
        for p in self.data["presets"]:
            self.assertIn(f"preset.{p['key']}.about", strings)

    # ------------------------------------------------------------------ page rules
    def test_page_is_self_contained_and_within_budget(self):
        self.assertLessEqual(len(self.html.encode("utf-8")), 2_000_000)
        self.assertNotRegex(self.html, r"<script[^>]+src=", "external script")
        self.assertNotRegex(self.html, r"<link[^>]+rel=.?stylesheet", "external stylesheet")
        self.assertNotRegex(self.html, r"<img|@import|url\(\s*['\"]?https?:", "external resource")
        js = (OBS / "static" / "observatory.js").read_text(encoding="utf-8")
        self.assertNotRegex(js, r"\bfetch\(|XMLHttpRequest|import\(|WebSocket|EventSource", "network call in the script")
        self.assertIn("<title>", self.html)

    def test_css_uses_logical_properties_only(self):
        css = re.sub(r"/\*.*?\*/", "", (OBS / "static" / "observatory.css").read_text(encoding="utf-8"), flags=re.S)
        self.assertNotRegex(css, r"(margin|padding|border)-(left|right|top|bottom)\b")
        self.assertNotRegex(css, r"(^|[;{\s])(left|right|top|bottom)\s*:")
        self.assertNotRegex(css, r"(text-align|float|clear)\s*:\s*(left|right)")
        self.assertNotRegex(css, r"border-(top|bottom)-(left|right)-radius")
        self.assertIn("color-scheme: dark", css)

    def test_no_size_or_glow_by_a_computed_measure(self):
        js = (OBS / "static" / "observatory.js").read_text(encoding="utf-8")
        self.assertNotRegex(js, r"(?i)centrality|pagerank|betweenness|shadowBlur")
        self.assertNotRegex(js, r"nodeRadius\([^)]")  # one radius for every node: no per-node argument
        for nd in self.nodes:
            self.assertNotIn("prophet", nd)  # nothing marks anyone out for special drawing

    def test_the_prophet_is_named_with_the_sign(self):
        import display
        named = [nd for nd in self.nodes if nd["k"] == "person" and display.is_prophet_label(nd["n"])]
        self.assertEqual(len(named), 1)
        self.assertTrue(named[0]["n"].endswith(display.PBUH_SIGN))

    def test_counts_on_the_page_come_from_the_graph(self):
        c = self.data["meta"]["counts"]
        kinds = {}
        for nd in self.nodes:
            kinds[nd["k"]] = kinds.get(nd["k"], 0) + 1
        self.assertEqual(c["kinds"], {k: kinds.get(k, 0) for k in ("person", "group", "place", "event", "story")})
        self.assertEqual(c["located"], sum(1 for nd in self.nodes if nd["k"] == "place" and "geo" in nd))
        self.assertEqual(c["tabaqa"], sum(1 for nd in self.nodes if nd.get("tb")))
        self.assertEqual(c["chains"], len(self.data["chains"]))


if __name__ == "__main__":
    unittest.main()
