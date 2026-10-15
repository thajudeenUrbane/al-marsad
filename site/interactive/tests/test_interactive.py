"""Tests for the interactive tier (slice 10): the timeline and the map.

Run:  .venv/bin/python -m unittest discover -s site/interactive/tests -v
The integration tests need build/graph.ttl (ontology/build_graph.py) and are skipped without it;
they build the reader pages and these pages into a temporary folder. No test names an entity
ID: entities are found by type and by name only.
"""
import ast
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]          # site/interactive
SITE = HERE.parent
ROOT = SITE.parent
for p in (str(SITE), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import build_interactive as bi  # noqa: E402
import extract  # noqa: E402

GRAPH = ROOT / "build" / "graph.ttl"
OWN = json.loads((HERE / "i18n" / "en.json").read_text(encoding="utf-8"))
READER = json.loads((SITE / "i18n" / "en.json").read_text(encoding="utf-8"))
PY = [HERE / "build_interactive.py", HERE / "extract.py", HERE / "tools" / "make_basemap.py"]
JS = {n: (HERE / "static" / f"{n}.js").read_text(encoding="utf-8") for n in ("common", "timeline", "map")}
CSS = (HERE / "static" / "interactive.css").read_text(encoding="utf-8")
KEY = re.compile(r"^ix\.[a-z0-9_]+(\.[a-z0-9_]+)+$")


def quiet(fn, *args, **kw):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*args, **kw)


def py_literals() -> set:
    out = set()
    for path in PY:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                out.add(node.value)
            if isinstance(node, ast.JoinedStr):
                for v in node.values:
                    if isinstance(v, ast.Constant):
                        out.add(v.value)
    return out


def own_families() -> set:
    """Keys built at run time from data values (f"ix.lc.{value}" and the like)."""
    keys = set()
    for k in OWN:
        for prefix in ("ix.allen.", "ix.lc.", "ix.gb.", "ix.legend.segment.", "ix.seg.not_drawn.",
                       "ix.legend.kind.", "ix.ctl.focus_group.", "ix.tl.unplaced.", "ix.map.off.", "ix.tl.alt."):
            if k.startswith(prefix):
                keys.add(k)
    return keys


class Calendars(unittest.TestCase):
    def test_hijri_epoch_and_a_stored_conversion(self):
        # 1 Muharram 1 AH (civil epoch) is 16 July 622 in the Julian calendar
        self.assertEqual(extract.muharram_first(1), extract.jdn_julian(622, 7, 16))
        # 17 Ramadan 2 AH by the tabular civil calendar is 13 March 624 (Julian)
        self.assertEqual(extract.muharram_first(2) + 236 + 16, extract.jdn_julian(624, 3, 13))
        # year 2 is a leap year of the 30-year cycle: 355 days
        self.assertEqual(extract.muharram_first(3) - extract.muharram_first(2), 355)

    def test_day_numbers_keep_the_recorded_bounds(self):
        start = extract.day_number("0624-03-13T00:00:00+00:00")
        end = extract.day_number("0624-03-13T23:59:59+00:00", end=True)
        self.assertEqual(end - start, 1.0)                  # one whole day, not a point
        self.assertEqual(extract.day_number("0609-01-01"), extract.jdn_julian(609, 1, 1))
        self.assertIsNone(extract.day_number("c. 610"))
        self.assertIsNone(extract.day_number(None))

    def test_year_of(self):
        self.assertEqual(bi.year_of("0624-03-13"), 624)
        self.assertEqual(bi.year_of("1200-01-01"), 1200)


class Geometry(unittest.TestCase):
    def test_points(self):
        self.assertEqual(extract.parse_point("POINT(39.8262 21.4225)"), (39.8262, 21.4225))
        self.assertEqual(extract.parse_point(" point ( -1.5 2 ) "), (-1.5, 2.0))
        for bad in ("POINT(39.8)", "POINT EMPTY", "POLYGON((0 0, 1 1, 0 1, 0 0))", "", "LINESTRING(0 0, 1 1)"):
            self.assertIsNone(extract.parse_point(bad), bad)

    def test_lines(self):
        self.assertEqual(extract.parse_line("LINESTRING(39.8262 21.4225, 39.8570 21.3580)"),
                         [(39.8262, 21.4225), (39.857, 21.358)])
        for bad in ("LINESTRING(1 2)", "LINESTRING(1 2, x y)", "POINT(1 2)", "MULTILINESTRING((0 0, 1 1))"):
            self.assertIsNone(extract.parse_line(bad), bad)


class StaticChecks(unittest.TestCase):
    def test_every_key_used_exists(self):
        used = {s for s in py_literals() if KEY.match(s)}
        for view in bi.JS_KEYS.values():
            used |= set(view)
        missing = sorted(k for k in used if k not in OWN and f"{k}.one" not in OWN)
        self.assertEqual(missing, [])

    def test_no_unused_keys(self):
        used = {s for s in py_literals() if KEY.match(s)} | own_families()
        for view in bi.JS_KEYS.values():
            used |= set(view)
        unused = [k for k in OWN if k not in used and k.rsplit(".", 1)[0] not in used]
        self.assertEqual(unused, [])

    def test_own_keys_are_prefixed_and_reader_keys_are_not_redefined(self):
        self.assertTrue(all(k.startswith("ix.") for k in OWN))
        self.assertFalse(set(OWN) & set(READER))

    def test_scripts_read_only_keys_the_builder_sends(self):
        for name, src in JS.items():
            sent = set(bi.JS_KEYS["common"]) | set(bi.JS_KEYS.get(name, ()))
            for key in re.findall(r'S\["(ix\.[a-z0-9_.]+)"\]', src):
                with self.subTest(script=name, key=key):
                    self.assertIn(key, sent)
            for prefix in re.findall(r'S\["(ix\.[a-z0-9_.]+\.)" \+', src):
                with self.subTest(script=name, prefix=prefix):
                    self.assertTrue(any(k.startswith(prefix) for k in sent))

    def test_scripts_hold_no_ui_text(self):
        """Every visible string in the scripts comes from data.strings: no literal prose."""
        bad = []
        for name, src in JS.items():
            code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
            code = re.sub(r"(?m)^\s*//.*$", "", code)
            for lit in re.findall(r'"((?:[^"\\]|\\.)*)"|\'((?:[^\'\\]|\\.)*)\'', code):
                s = lit[0] or lit[1]
                if re.search(r"[A-Z][a-z]+\s+[A-Za-z]", s) or re.search(r"\b[a-z]{3,}\s+[a-z]{3,}\s+[a-z]{3,}\b", s):
                    if not re.fullmatch(r"[a-z0-9 :.\-()/]+", s):
                        bad.append((name, s))
        self.assertEqual(bad, [])

    def test_html_built_in_python_has_no_hard_coded_words(self):
        bad = []
        for path in (HERE / "build_interactive.py",):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            inner = {id(v) for n in ast.walk(tree) if isinstance(n, ast.JoinedStr) for v in n.values}
            for node in ast.walk(tree):
                if id(node) in inner:
                    continue
                if isinstance(node, ast.JoinedStr):
                    s = "".join(v.value if isinstance(v, ast.Constant) else "{}" for v in node.values)
                elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                    s = node.value
                else:
                    continue
                if "<" not in s:
                    continue
                text = re.sub(r"<[^>]+>", " ", s)
                text = re.sub(r"\{[^}]*\}|&\w+;", " ", text)
                if re.findall(r"[A-Za-z]{2,}", text):
                    bad.append((node.lineno, s[:70]))
        self.assertEqual(bad, [])

    def test_css_uses_logical_properties_only(self):
        css = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
        css = re.sub(r"@media[^{]*\{", "{", css)          # media conditions may name width
        self.assertEqual(re.findall(r"[^\n]*\b(?:left|right|top|bottom)\b[^\n]*", css), [])
        self.assertEqual(re.findall(r"(?<![-\w])(?:width|height|margin-top|padding-left)\s*:", css), [])

    def test_motion_is_reduced_on_request(self):
        self.assertIn("prefers-reduced-motion: reduce", CSS)
        self.assertIn("prefers-reduced-motion: reduce", JS["common"])

    def test_no_external_requests_in_the_scripts(self):
        for name, src in JS.items():
            urls = re.findall(r"https?://[^\s\"']+", src)
            self.assertEqual([u for u in urls if u != "http://www.w3.org/2000/svg"], [], name)
            self.assertNotIn("import(", src)
            self.assertEqual(len(re.findall(r"\bfetch\(", src)), 1 if name == "common" else 0, name)

    def test_basemap_records_its_source_and_licence(self):
        data = json.loads((HERE / "data" / "basemap.json").read_text(encoding="utf-8"))
        src = data["source"]
        self.assertIn("naturalearth", src["url"].replace("-", "").replace("_", "").lower() + src["licence_url"])
        self.assertEqual(src["licence"], "public domain")
        self.assertRegex(src["sha256"], r"^[0-9a-f]{64}$")
        self.assertIn("make_basemap.py", src["processing"])
        self.assertLess((HERE / "data" / "basemap.json").stat().st_size, 15_000)
        w, s, e, n = data["layers"]["land"]["bbox"]
        for ring in data["layers"]["land"]["rings"]:
            for x, y in ring:
                self.assertTrue(w <= x <= e and s <= y <= n, (x, y))


class Links(HTMLParser):
    """Collects data-id values per list group, hrefs and tags from a generated page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.groups: dict[str, list[str]] = {}
        self.unplaced: list[str] = []
        self.off: list[str] = []
        self.tags: set[str] = set()
        self._group = None
        self._section = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.add(tag)
        if tag == "section":
            self._section.append(a.get("id") or "")
        if tag == "ol" and "data-group" in a:
            self._group = a["data-group"]
            self.groups.setdefault(self._group, [])
        if tag == "li" and "data-id" in a:
            if self._group:
                self.groups[self._group].append(a["data-id"])
            elif "ix-unplaced" in self._section:
                self.unplaced.append(a["data-id"])
            else:
                self.off.append(a["data-id"])

    def handle_endtag(self, tag):
        if tag == "ol":
            self._group = None
        if tag == "section" and self._section:
            self._section.pop()


@unittest.skipUnless(GRAPH.exists(), "build/graph.ttl missing: run ontology/build_graph.py")
class Built(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import build as site_build
        from model import Site
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "dist"
        quiet(site_build.build, GRAPH, cls.out, quiet=True)
        cls.summary = quiet(bi.build, GRAPH, cls.out, quiet=True)
        cls.site = Site(GRAPH)
        cls.tl = json.loads((cls.out / "timeline" / "data.json").read_text(encoding="utf-8"))
        cls.map = json.loads((cls.out / "map" / "data.json").read_text(encoding="utf-8"))
        cls.tl_html = (cls.out / "timeline" / "index.html").read_text(encoding="utf-8")
        cls.map_html = (cls.out / "map" / "index.html").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def parsed(self, html_text: str) -> Links:
        p = Links()
        p.feed(html_text)
        return p

    def test_no_entity_id_is_hard_coded(self):
        sources = "".join(p.read_text(encoding="utf-8") for p in HERE.rglob("*")
                          if p.is_file() and p.suffix in (".py", ".js", ".css", ".json", ".cjs"))
        from rdflib import URIRef
        ids = {str(s).rsplit("/", 1)[-1] for s in self.site.g.subjects() if isinstance(s, URIRef)
               and str(s).startswith("https://w3id.org/marsad/id/")}
        self.assertTrue(ids)
        self.assertEqual(sorted(i for i in ids if len(i) >= 8 and i in sources), [])

    # ------------------------------------------------------------------ what is written
    def test_pages_data_and_assets_are_written(self):
        for view in bi.VIEWS:
            names = sorted(p.name for p in (self.out / view).iterdir())
            self.assertEqual(names, sorted(["index.html", "data.json", f"{view}.js"] + list(bi.SHARED)))

    def test_only_text_files_and_no_images(self):
        for view in bi.VIEWS:
            for p in (self.out / view).iterdir():
                self.assertIn(p.suffix, (".html", ".js", ".css", ".json"), p)
        for html_text in (self.tl_html, self.map_html):
            self.assertNotIn("<img", html_text)
            self.assertNotIn("<image", html_text)

    def test_each_page_is_under_two_megabytes(self):
        for view in bi.VIEWS:
            total = sum(bi.weigh(self.out, view).values())
            self.assertLess(total, bi.PAGE_BUDGET, view)

    def test_the_reader_checks_pass_on_these_pages(self):
        import check_budget
        import check_html
        ids = check_html.collect_ids(self.out)
        for view in bi.VIEWS:
            self.assertEqual(check_html.check_page(self.out, self.out / view / "index.html", ids), [], view)
        results, problems = check_budget.check(self.out)
        self.assertEqual([p for p in problems if p.startswith(("timeline/", "map/"))], [])

    def test_no_external_loads(self):
        for html_text in (self.tl_html, self.map_html):
            self.assertIsNone(re.search(r'(?:src|rel="stylesheet" href)="(?:https?:)?//', html_text))

    def test_build_is_deterministic_across_processes(self):
        copy = Path(self.tmp.name) / "again"
        shutil.copytree(self.out, copy)
        outs = []
        for seed in ("1", "2"):
            for view in bi.VIEWS:
                shutil.rmtree(copy / view)
            env = dict(os.environ, PYTHONHASHSEED=seed)
            subprocess.run([sys.executable, str(HERE / "build_interactive.py"), "--graph", str(GRAPH), "--out", str(copy)],
                           check=True, env=env, stdout=subprocess.DEVNULL, cwd=ROOT)
            outs.append({p.relative_to(copy).as_posix(): p.read_bytes()
                         for view in bi.VIEWS for p in sorted((copy / view).iterdir())})
        mine = {p.relative_to(self.out).as_posix(): p.read_bytes()
                for view in bi.VIEWS for p in sorted((self.out / view).iterdir())}
        self.assertEqual(outs[0], outs[1])
        self.assertEqual(outs[0], mine)

    # ------------------------------------------------------------------ the timeline
    def recorded_bounds(self) -> dict:
        """entity id -> set of (earliest, latest) date pairs stored in the graph."""
        from rdflib import URIRef
        from model import MRS
        g = self.site.g
        out = {}
        for kind in ("event", "story", "person"):
            for e in self.site.by_kind[kind]:
                nodes = list(g.objects(URIRef(e.iri), MRS.eventTemporalExtent))
                for d in g.objects(URIRef(e.iri), MRS.death):
                    nodes += list(g.objects(d, MRS.eventTemporalExtent))
                pairs = set()
                for n in nodes:
                    a, b = g.value(n, MRS.earliestStart), g.value(n, MRS.latestEnd)
                    pairs.add((extract.iso_date(str(a)) if a is not None else None,
                               extract.iso_date(str(b)) if b is not None else None))
                out[f"{kind}/{e.pid}"] = pairs
        return out

    def test_every_placed_item_is_placed_by_its_recorded_bounds_only(self):
        rec = self.recorded_bounds()
        self.assertTrue(self.tl["items"])
        for it in self.tl["items"]:
            with self.subTest(it["id"]):
                self.assertIn((it["earliest"], it["latest"]), rec[it["entity"]])
                y, m, d = (int(x) for x in it["earliest"].split("-"))
                self.assertEqual(it["start"], extract.jdn_julian(y, m, d))      # never narrowed
                self.assertGreater(it["end"], it["start"])                      # a range, never a point
                self.assertIn(it["role"], ("event", "death"))

    def test_people_are_placed_only_by_a_recorded_death(self):
        from rdflib import URIRef
        from model import MRS
        people = {f"person/{p.pid}": p for p in self.site.by_kind["person"]}
        for it in self.tl["items"]:
            if it["kind"] == "person":
                e = people[it["entity"]]
                self.assertTrue(list(self.site.g.objects(URIRef(e.iri), MRS.death)))
                self.assertEqual(it["role"], "death")

    def test_undated_records_are_listed_and_never_placed(self):
        rec = self.recorded_bounds()
        placed = {it["entity"] for it in self.tl["items"]}
        listed = set(self.parsed(self.tl_html).unplaced)
        for ent, pairs in rec.items():
            if not any(a and b for a, b in pairs):
                self.assertNotIn(ent, placed)
                self.assertIn(ent, listed)
        for g in self.site.by_kind["group"]:
            self.assertIn(f"group/{g.pid}", listed)

    def test_relative_dates_are_listed_with_their_anchor_and_never_placed(self):
        section = self.tl_html[self.tl_html.index('id="ix-unplaced"'):]
        rel = [it for it in quiet(extract.timeline, self.site)["not_placed"].get("relative", [])]
        for it in rel:
            ent = extract.entity_id(it["entity"])
            self.assertNotIn(ent, {i["entity"] for i in self.tl["items"]})
            self.assertIn(f'data-id="{ent}"', section)
            for a in it["rec"]["anchors"]:
                if a["target"] and a["target"].href:
                    self.assertIn(a["target"].href, section)

    def test_the_text_version_lists_every_placed_item(self):
        p = self.parsed(self.tl_html)
        listed = p.groups.get("events", []) + p.groups.get("deaths", [])
        self.assertEqual(sorted(listed), sorted(it["id"] for it in self.tl["items"]))
        for it in self.tl["items"]:
            self.assertIn(f'href="{it["href"]}"', self.tl_html)

    def test_every_mark_links_to_an_existing_entity_page(self):
        for it in self.tl["items"]:
            target = (self.out / "timeline" / it["href"]).resolve() / "index.html"
            self.assertTrue(target.is_file(), it["href"])
        for m in self.map["places"]:
            target = (self.out / "map" / m["href"]).resolve() / "index.html"
            self.assertTrue(target.is_file(), m["href"])

    def test_every_item_shows_a_status_and_no_status_is_upgraded(self):
        from model import MRS
        recorded = {self.site.vkey(o, "as_") for o in self.site.g.objects(None, MRS.assertionStatus)}
        word = READER["status.label"].split("{")[0]
        for it in self.tl["items"]:
            self.assertIn(word, it["status_html"])
            self.assertIn(word, it["info_html"])
            self.assertTrue(set(it["statuses"]) <= recorded)
            if not it["statuses"]:
                self.assertIn(READER["status.none"], it["status_html"])
        for m in self.map["places"]:
            self.assertIn(word, m["info_html"])
            self.assertTrue(set(m["statuses"]) <= recorded)
        if "accepted" not in recorded:
            self.assertNotIn(READER["status.label"].format(value=READER["status.accepted"]), self.tl_html + self.map_html)

    def test_dates_read_gregorian_first_with_hijri_beside(self):
        ce, ah = READER["date.ce"], READER["date.ah"]
        both = [it for it in self.tl["items"] if ce in it["date_html"] and ah in it["date_html"]]
        self.assertTrue(both)
        for it in both:
            self.assertLess(it["date_html"].index(ce), it["date_html"].index(ah), it["id"])
        # a date recorded only in the Hijri calendar is shown with its stored Gregorian bounds first
        hijri_only = [it for it in self.tl["items"]
                      if it["native"] and re.search(r"\bAH\b", it["native"]) and "CE" not in it["native"]]
        self.assertTrue(hijri_only)
        for it in hijri_only:
            self.assertLess(it["date_html"].index(ce), it["date_html"].index(ah), it["id"])

    def test_disputed_dates_are_marked_in_drawing_and_text(self):
        for it in self.tl["items"]:
            if it["basis"] == "disputed":
                self.assertTrue(it["disputed"], it["id"])
            if it["disputed"]:
                self.assertIn(OWN["ix.info.disputed"], it["info_html"])
        self.assertIn("is-disputed", JS["timeline"])

    def test_focus_index_points_at_drawn_items(self):
        ids = {it["id"] for it in self.tl["items"]}
        for f in self.tl["focus"]:
            self.assertTrue(f["items"])
            self.assertTrue(set(f["items"]) <= ids, f["id"])
            self.assertIn(f["kind"], ("person", "group", "place"))

    def test_axis_covers_every_placed_item(self):
        ax = self.tl["axis"]
        for it in self.tl["items"]:
            self.assertGreaterEqual(it["start"], ax["start"])
            self.assertLessEqual(it["end"], ax["end"])
        years = [t["y"] for t in ax["ce"]]
        self.assertEqual(years, list(range(ax["first_year"], ax["last_year"] + 2)))

    # ------------------------------------------------------------------ the map
    def recorded_points(self) -> dict:
        from rdflib import URIRef
        from model import MRS
        g = self.site.g
        out = {}
        for e in self.site.by_kind["place"]:
            pts = set()
            for gs in g.objects(URIRef(e.iri), MRS.geometryState):
                for geom in g.objects(gs, MRS.geometry):
                    for w in g.objects(geom, extract.GEO.asWKT):
                        p = extract.parse_point(str(w))
                        if p:
                            pts.add(p)
            out[f"place/{e.pid}"] = pts
        return out

    def test_places_are_plotted_only_at_recorded_coordinates(self):
        rec = self.recorded_points()
        plotted = {m["entity"] for m in self.map["places"]}
        self.assertTrue(plotted)
        for m in self.map["places"]:
            self.assertIn((m["lon"], m["lat"]), rec[m["entity"]], m["id"])
        for ent, pts in rec.items():
            if not pts:
                self.assertNotIn(ent, plotted)

    def test_places_without_coordinates_are_listed(self):
        rec = self.recorded_points()
        off = set(self.parsed(self.map_html).off)
        for ent, pts in rec.items():
            if not pts:
                self.assertIn(ent, off)

    def test_routes_are_drawn_only_where_recorded(self):
        from rdflib import RDF
        from model import MRS
        g = self.site.g
        recorded_lines = set()
        unknown = 0
        for r in g.subjects(RDF.type, MRS.Route):
            for seg in g.objects(r, MRS.hasSegment):
                if self.site.vkey(g.value(seg, MRS.segmentConfidence), "sc_") == "unknown":
                    unknown += 1
                for geom in g.objects(seg, MRS.segmentGeometry):
                    for w in g.objects(geom, extract.GEO.asWKT):
                        line = extract.parse_line(str(w))
                        if line:
                            recorded_lines.add(tuple(line))
        segs = [s for r in self.map["routes"] for s in r["segments"]]
        for s in segs:
            if s["drawn"]:
                self.assertIn(tuple(tuple(p) for p in s["line"]), recorded_lines)
                self.assertNotEqual(s["confidence"], "unknown")
            else:
                self.assertIsNone(s["line"])
        self.assertEqual(sum(1 for s in segs if s["confidence"] == "unknown" and not s["drawn"]), unknown)

    def test_the_text_version_lists_every_plotted_place_and_every_segment(self):
        p = self.parsed(self.map_html)
        self.assertEqual(sorted(p.groups.get("places", [])), sorted(m["id"] for m in self.map["places"]))
        self.assertEqual(sorted(p.groups.get("segments", [])),
                         sorted(s["id"] for r in self.map["routes"] for s in r["segments"]))
        for r in self.map["routes"]:
            for s in r["segments"]:
                self.assertIn(f'id="{s["anchor"]}"', self.map_html)

    def test_basemap_is_land_only_and_credited(self):
        bm = self.map["basemap"]
        self.assertEqual(bm["source"]["licence"], "public domain")
        self.assertIn(bm["source"]["licence_url"], self.map_html)
        self.assertEqual(set(bm), {"source", "rings", "bbox"})

    def test_map_marks_use_abstract_shapes_only(self):
        shapes = set(bi.MARK_SHAPES)
        for m in self.map["places"]:
            self.assertIn(m["basis"], shapes)
        for b in shapes:
            self.assertIn(f'id="ix-sym-{b}"', self.map_html)


if __name__ == "__main__":
    unittest.main()
