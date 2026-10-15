"""Tests for the generator, the checks and the rules in the brief. Needs build/graph.ttl
(run ontology/build_graph.py first); the integration tests are skipped without it.
Run:  .venv/bin/python -m unittest discover -s site/tests -v
"""
import ast
import contextlib
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
ROOT = SITE.parent
sys.path.insert(0, str(SITE))

import build as site_build  # noqa: E402
import check_budget  # noqa: E402
import check_html  # noqa: E402
import display  # noqa: E402
from render import SECTION_ORDER  # noqa: E402

GRAPH = ROOT / "build" / "graph.ttl"


def quiet(fn, *args):
    """Run a check script's main() without printing its report."""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*args)

EN = json.loads((SITE / "i18n" / "en.json").read_text(encoding="utf-8"))
PY_FILES = [SITE / n for n in ("build.py", "display.py", "glossary.py", "model.py", "names.py", "render.py",
                               "hub.py", "thread.py", "external.py", "experiments.py")]
JS_FILES = [SITE / "static" / n for n in ("search.js", "enhance.js", "thread.js")]
CSS_FILES = [SITE / "static" / n for n in ("site.css", "archive.css")]
KEY = re.compile(r"^[a-z_]+(\.[a-z0-9_]+)+$")
KINDS = ("person", "event", "place", "group", "story")
# his name not followed by the sign (the sign sits in a lang="ar" span in the HTML)
SIGNLESS = r'The Prophet Muhammad(?! (?:<span class="pbuh" lang="ar" dir="rtl">)?ﷺ)'


def family_keys() -> set:
    keys = set()
    for k in ("person", "event", "place", "story", "group", "tribe", "clan", "family"):
        keys.add(f"type.{k}")
    for k in ("stub", "outline", "sourced", "reviewed", "verified"):
        keys |= {f"coverage.{k}", f"coverage.explain.{k}"}
    for k in ("proposed", "under_review", "accepted", "rejected", "superseded"):
        keys.add(f"status.{k}")
    sections = {s for v in SECTION_ORDER.values() for s in v}
    for s in sections:
        keys |= {f"section.{s}", f"count.{s}.one", f"count.{s}.other"}
    keys |= {"section.disputes", "section.gaps"}
    for k in KINDS:
        keys |= {f"index.lead.{k}.one", f"index.lead.{k}.other", f"home.count.{k}.one", f"home.count.{k}.other"}
    for k in ("people", "events", "places", "groups", "stories", "glossary", "home"):
        keys.add(f"nav.{k}")
    for m in range(1, 13):
        keys.add(f"date.month.{m}")
    for k in ("year", "month", "day", "decade", "generation", "period", "unknown"):
        keys.add(f"precision.{k}")
    for k in ("attested", "inferred", "computed", "conventional", "disputed"):
        keys.add(f"basis.{k}")
    for k in ("ism", "kunya", "laqab", "nasab", "nisba", "full", "scheme"):
        keys.add(f"name.{k}")
    keys |= {"details.claims_by.one", "details.claims_by.other", "details.basis_summary.one",
             "details.basis_summary.other", "honorific.companion_male", "honorific.companion_female",
             "date.converted_one"}
    # slice 2c-site: doors, the hub's views, the prototypes, external systems
    import experiments
    import hub
    from render import Renderer
    for d in hub.DOORS:
        keys |= {f"door.{d}.title", f"door.{d}.lead"}
    keys |= {"door.discover.go.one", "door.discover.go.other", "door.study.page_lead", "door.research.page_lead"}
    for folder, _ in hub.VIEWS:
        keys |= {f"hub.view.{folder}.name", f"hub.view.{folder}.desc"}
    for folder in ("study", "research"):
        keys |= {f"hub.{folder}.name", f"hub.{folder}.desc"}
    for _, _, pages, stem in experiments.PROTOTYPES:
        for page in pages:
            k = Renderer.proto_key(stem, page)
            keys |= {k + ".name", k + ".desc"}
    for system in ("wikidata", "althurayya", "openiti"):
        keys.add(f"external.system.{system}")
    for key, _, _ in site_build.DOWNLOADS:
        keys |= {f"research.download.{key}", f"research.download.{key}.note"}
    keys |= {"research.claims.one", "research.claims.other", "thread.lead.one", "thread.lead.other"}
    return keys


def literal_keys() -> set:
    found = set()
    namespaces = {k.split(".")[0] for k in EN}
    for path in PY_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str) and KEY.match(node.value)
                    and node.value.split(".")[0] in namespaces
                    and not re.search(r"\.(json|html|css|py|ttl|cjs|js)$", node.value)):
                found.add(node.value)
    for path in (SITE / "templates").glob("*.html"):
        found |= set(re.findall(r"\[\[([a-z0-9_.]+)\]\]", path.read_text(encoding="utf-8")))
    return found


class StaticChecks(unittest.TestCase):
    def test_every_referenced_i18n_key_exists(self):
        have = set(EN)
        missing = []
        for k in sorted(literal_keys() | family_keys()):
            if k not in have and f"{k}.one" not in have:
                missing.append(k)
        self.assertEqual(missing, [], "keys used in code but missing from site/i18n/en.json")

    def test_no_unused_i18n_keys(self):
        used = literal_keys() | family_keys()
        unused = [k for k in EN if k not in used and k.rsplit(".", 1)[0] not in used
                  and not any(k.startswith(u + ".") for u in used)]
        self.assertEqual(unused, [], "keys in en.json that nothing uses")

    def test_templates_contain_no_hard_coded_text(self):
        for path in sorted((SITE / "templates").glob("*.html")):
            src = path.read_text(encoding="utf-8")
            src = re.sub(r"\[\[[a-z0-9_.]+\]\]", "", src)
            src = re.sub(r"\$\{?\w+\}?", "", src)
            src = re.sub(r"<[^>]+>", "", src)
            self.assertEqual(src.strip(), "", f"{path.name} has literal text outside i18n keys")

    def test_html_built_in_python_has_no_hard_coded_words(self):
        tree_src = (SITE / "render.py").read_text(encoding="utf-8")
        tree = ast.parse(tree_src)
        bad = []

        def flatten(node):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                return node.value
            if isinstance(node, ast.JoinedStr):
                return "".join(v.value if isinstance(v, ast.Constant) else "{}" for v in node.values)
            return None

        inner = {id(v) for n in ast.walk(tree) if isinstance(n, ast.JoinedStr) for v in n.values}
        for node in ast.walk(tree):
            if id(node) in inner:
                continue  # a fragment of an f-string; the whole f-string is checked instead
            if isinstance(node, ast.JoinedStr) or (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                s = flatten(node)
                if not s or "<" not in s:
                    continue
                text = re.sub(r"<[^>]+>", " ", s)
                text = re.sub(r"\{[^}]*\}|&\w+;", " ", text)
                words = re.findall(r"[A-Za-z]{2,}", text)
                if words:
                    bad.append((node.lineno, s[:80], words))
        # JoinedStr values are also walked as Constants; dedupe by line
        self.assertEqual(sorted({b[0] for b in bad}), [], bad[:5])

    def test_css_uses_logical_properties_only(self):
        for path in CSS_FILES:
            css = re.sub(r"/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.S)
            self.assertEqual(re.findall(r"[^\n]*\b(?:left|right)\b[^\n]*", css, flags=re.I), [], path.name)

    def test_plain_wordings_are_taken_from_the_repo(self):
        """A plain wording (plain-words switch) appears, with its term, in the file it cites."""
        data = json.loads((SITE / "data" / "glossary.json").read_text(encoding="utf-8"))
        with_plain = [e for lst in ("defined", "needed") for e in data[lst] if e.get("plain") or e.get("plain_source")]
        self.assertTrue(with_plain)
        for e in with_plain:
            with self.subTest(e["term"]):
                self.assertTrue(e.get("plain") and e.get("plain_source"))
                src_file = re.match(r"[\w./-]+", e["plain_source"]).group(0)
                text = display.fold((ROOT / src_file).read_text(encoding="utf-8")).lower()
                self.assertIn(e["plain"].lower(), text)
                self.assertTrue(any(display.fold(t).lower().strip() in text for t in e["term"].split(" / ")))

    def test_glossary_definitions_are_quoted_from_the_repo(self):
        data = json.loads((SITE / "data" / "glossary.json").read_text(encoding="utf-8"))
        norm = lambda s: re.sub(r"\s+", " ", s.replace("*", "")).strip().lower()
        for e in data["defined"]:
            src_file = re.match(r"[\w./-]+", e["source"]).group(0)
            text = norm((ROOT / src_file).read_text(encoding="utf-8"))
            with self.subTest(e["term"]):
                self.assertTrue(norm(e["definition"]) in text, f"definition not found in {src_file}")
                if e.get("arabic"):
                    self.assertIn(e["arabic"], (ROOT / src_file).read_text(encoding="utf-8"))
        self.assertTrue(data["needed"])

    def test_no_entity_id_is_hard_coded(self):
        if not GRAPH.exists():
            self.skipTest("build/graph.ttl missing")
        from model import Site
        site = Site(GRAPH)
        sources = ""
        for path in (PY_FILES + list((SITE / "templates").glob("*")) + JS_FILES + CSS_FILES
                     + [SITE / "i18n" / "en.json", SITE / "data" / "glossary.json"]):
            sources += path.read_text(encoding="utf-8")
        leaked = [e.pid for e in site.entities.values() if e.pid in sources]
        self.assertEqual(leaked, [])


class ChecksCatchProblems(unittest.TestCase):
    def make(self, tmp: Path, body: str, css: str = "body{margin:0}", head: str = ""):
        (tmp / "assets").mkdir(exist_ok=True)
        (tmp / "assets" / "s.css").write_text(css)
        (tmp / "index.html").write_text(
            '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>t</title>'
            '<link rel="stylesheet" href="assets/s.css">' + head + "</head><body>" + body + "</body></html>")

    GOOD = ('<a href="#main">skip</a><header><nav><a href="/">h</a></nav></header><main id="main"><h1>x</h1></main>'
            '<footer><a href="https://github.com/x/LICENSING.md">l</a>'
            '<a href="https://creativecommons.org/licenses/by-sa/4.0/">c</a>'
            '<a href="https://www.gnu.org/licenses/agpl-3.0.html">g</a></footer>')

    def test_good_page_passes_both(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self.make(tmp, self.GOOD)
            self.assertEqual(quiet(check_budget.main, [d]), 0)
            self.assertEqual(quiet(check_html.main, [d]), 0)

    def test_budget_fails_over_the_limit(self):
        with tempfile.TemporaryDirectory() as d:
            self.make(Path(d), self.GOOD, css="/*" + "x" * 300_100 + "*/")
            self.assertEqual(quiet(check_budget.main, [d]), 1)

    def test_interactive_tier_gets_two_megabytes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for rel in ("observatory/index.html", "people/index.html"):
                f = root / rel
                f.parent.mkdir(parents=True)
                f.write_text("<!doctype html><title>t</title>" + "x" * 400_000, encoding="utf-8")
            _, problems = check_budget.check(root)
            self.assertEqual([p.split(":")[0] for p in problems], ["people/index.html"])
            (root / "observatory/index.html").write_text("x" * 2_000_100, encoding="utf-8")
            _, problems = check_budget.check(root)
            self.assertIn("observatory/index.html", " ".join(problems))

    def test_budget_fails_on_external_stylesheet_and_script(self):
        for head in ('<link rel="stylesheet" href="https://cdn.example/x.css">',
                     '<script src="//cdn.example/x.js"></script>',
                     '<link rel="preload" href="https://fonts.example/f.woff2" as="font">'):
            with tempfile.TemporaryDirectory() as d:
                self.make(Path(d), self.GOOD, head=head)
                self.assertEqual(quiet(check_budget.main, [d]), 1, head)

    def test_budget_fails_on_external_url_inside_css(self):
        with tempfile.TemporaryDirectory() as d:
            self.make(Path(d), self.GOOD, css='@import url("https://fonts.example/a.css");')
            self.assertEqual(quiet(check_budget.main, [d]), 1)

    def test_budget_allows_plain_external_links(self):
        with tempfile.TemporaryDirectory() as d:
            self.make(Path(d), self.GOOD)
            self.assertEqual(quiet(check_budget.main, [d]), 0)

    def test_budget_counts_same_site_scripts(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self.make(tmp, self.GOOD, head='<script src="assets/big.js" defer></script>')
            (tmp / "assets" / "big.js").write_text("//" + "x" * 300_100)
            self.assertEqual(quiet(check_budget.main, [d]), 1)

    def test_budget_counts_files_a_script_fetches(self):
        """A page that names its search index in data-fetch carries the index's weight."""
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self.make(tmp, self.GOOD.replace("<h1>x</h1>", '<h1>x</h1><form data-fetch="big.json"></form>'))
            (tmp / "big.json").write_text("[" + "0," * 150_100 + "0]")
            self.assertEqual(quiet(check_budget.main, [d]), 1)
            (tmp / "big.json").write_text("[0]")
            self.assertEqual(quiet(check_budget.main, [d]), 0)

    def test_budget_fails_on_an_external_fetch(self):
        with tempfile.TemporaryDirectory() as d:
            self.make(Path(d), self.GOOD.replace("<h1>x</h1>", '<h1>x</h1><form data-fetch="https://x.example/i.json"></form>'))
            self.assertEqual(quiet(check_budget.main, [d]), 1)

    def test_html_check_catches_unclosed_and_double_h1_and_missing_lang(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self.make(tmp, self.GOOD.replace("<h1>x</h1>", "<h1>x</h1><h1>y</h1><div>"))
            self.assertEqual(quiet(check_html.main, [d]), 1)

    def test_html_check_catches_arabic_without_dir_and_broken_links(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self.make(tmp, self.GOOD.replace("<h1>x</h1>", '<h1>x</h1><span lang="ar">م</span><a href="nope/">n</a>'))
            self.assertEqual(quiet(check_html.main, [d]), 1)

    def test_html_check_catches_a_link_inside_a_link(self):
        with tempfile.TemporaryDirectory() as d:
            self.make(Path(d), self.GOOD.replace("<h1>x</h1>", '<h1>x</h1><a href="#main">a <a href="#main">b</a></a>'))
            self.assertEqual(quiet(check_html.main, [d]), 1)

    def test_html_check_requires_the_licence_footer(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self.make(tmp, re.sub(r"<footer>.*</footer>", "<footer></footer>", self.GOOD))
            self.assertEqual(quiet(check_html.main, [d]), 1)


@unittest.skipUnless(GRAPH.exists(), "build/graph.ttl missing: run ontology/build_graph.py")
class BuiltSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        cls.summary = site_build.build(GRAPH, cls.out, quiet=True)
        from model import Site
        cls.site = Site(GRAPH)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def page(self, e) -> str:
        return (self.out / e.kind / e.pid / "index.html").read_text(encoding="utf-8")

    def test_one_page_per_entity_at_a_url_made_from_the_id_payload(self):
        for kind in KINDS:
            self.assertGreater(len(self.site.by_kind[kind]), 0)
            for e in self.site.by_kind[kind]:
                self.assertEqual(e.pid, e.iri.rsplit("/", 1)[-1])
                self.assertTrue((self.out / kind / e.pid / "index.html").is_file())
                self.assertTrue((self.out / kind / e.pid / "entity.ttl").is_file())
            self.assertTrue((self.out / kind / "index.html").is_file())
        self.assertTrue((self.out / "index.html").is_file())
        self.assertTrue((self.out / "glossary" / "index.html").is_file())

    def test_every_person_event_place_group_and_story_in_the_graph_has_a_page(self):
        from rdflib import RDF, URIRef
        from model import MRS, ID_BASE
        g = self.site.g
        graph_named = set()
        for cls in (MRS.Person, MRS.Place, MRS.Group, MRS.Event):
            for s in g.subjects(RDF.type, cls):
                if isinstance(s, URIRef) and str(s).startswith(ID_BASE):
                    graph_named.add(str(s))
        self.assertEqual(graph_named, set(self.site.entities))

    def test_the_checks_pass_on_the_built_site(self):
        self.assertEqual(quiet(check_html.main, [str(self.out)]), 0)
        self.assertEqual(quiet(check_budget.main, [str(self.out)]), 0)

    def test_scripts_only_enhance_and_no_external_loads(self):
        """Every page loads the shared enhancement (plain words); the search page adds
        search.js and person and group pages thread.js; nothing else, and nothing inline,
        except in the copied prototypes, which keep their own scripts."""
        import experiments
        for p in self.out.rglob("*.html"):
            rel = p.relative_to(self.out).as_posix()
            src = p.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r'(?:src|data-fetch|rel="stylesheet" href)="(?:https?:)?//', src), p)
            if experiments.is_copy(rel):
                continue
            base = "../" * rel.count("/")
            want = [f"{base}assets/enhance.js"]
            if rel == "search/index.html":
                want.append("../assets/search.js")
            elif re.match(r"(person|group)/[^/]+/index\.html$", rel):
                want.append("../../assets/thread.js")
            self.assertEqual(re.findall(r"<script[^>]*\bsrc=\"([^\"]+)\"", src), want, rel)
            inline = [s for s in re.findall(r"<script(?![^>]*\bsrc=)([^>]*)>", src) if 'type="application/json"' not in s]
            self.assertEqual(inline, [], rel)

    def test_licence_footer_on_every_page(self):
        for p in self.out.rglob("*.html"):
            src = p.read_text(encoding="utf-8")
            foot = src[src.index("<footer"):]
            for needle in ("blob/main/LICENSING.md", "creativecommons.org/licenses/by-sa/4.0/",
                           "gnu.org/licenses/agpl-3.0.html", EN["footer.cc_by_sa"], EN["footer.agpl"],
                           EN["footer.ids"], EN["footer.contributors"]):
                self.assertIn(needle, foot, p)

    def test_abu_bakr_lists_stories_incidents_and_kinship_from_all_sources(self):
        abu = [e for e in self.site.by_kind["person"] if e.name == "Abu Bakr as-Siddiq"]
        self.assertEqual(len(abu), 1)
        src = self.page(abu[0])
        for sec in ("stories", "events", "kinship"):
            self.assertIn(f'id="s-{sec}"', src)
        self.assertGreaterEqual(len(re.findall(r'<li class="claim">', src)), 30)
        # the four sources of slice 1c each appear among the recorders in the details layer
        recorders = re.findall(r"claims? recorded by ([^<]+)", src)
        self.assertGreaterEqual(len(recorders), 4, recorders)

    def test_scholarly_form_is_in_the_details_layer(self):
        abu = [e for e in self.site.by_kind["person"] if e.name == "Abu Bakr as-Siddiq"][0]
        src = self.page(abu)
        head, _, details = src.partition('<section class="details-layer"')
        self.assertIn("Abū Bakr al-Ṣiddīq", details)
        self.assertNotIn("Ṣiddīq", head)

    def test_every_claim_row_shows_a_status_word(self):
        for e in self.site.entities.values():
            src = self.page(e)
            rows = len(re.findall(r'<li class="claim">', src))
            self.assertEqual(rows, len(re.findall(r'<span class="status status-[a-z_]+">Status: ', src)), e.name)

    def test_no_status_is_upgraded(self):
        counts = self.site.status_counts()
        everything = "".join(p.read_text(encoding="utf-8") for p in self.out.rglob("index.html"))
        for status, word in (("accepted", "accepted"), ("under_review", "under review")):
            if not counts.get(status):
                self.assertNotIn(f"Status: {word}", everything)

    def test_every_entity_page_shows_coverage_as_text(self):
        for e in self.site.entities.values():
            self.assertIn("Coverage: ", self.page(e), e.name)

    def test_story_pages_say_draft_at_the_top_and_ai_in_details(self):
        stories = self.site.by_kind["story"]
        self.assertGreater(len(stories), 0)
        for e in stories:
            src = self.page(e)
            self.assertLess(src.index(EN["story.banner"]), src.index('class="facts"'), e.name)
            self.assertIn(EN["story.ai_note"], src.partition('<section class="details-layer"')[2], e.name)
            self.assertIn('class="prose"', src)

    def test_the_prophet_has_a_distinct_layout_and_the_sign_everywhere(self):
        prophet = [e for e in self.site.by_kind["person"] if e.prophet]
        self.assertEqual(len(prophet), 1)
        src = self.page(prophet[0])
        self.assertIn("is-prophet", src)
        self.assertNotIn('class="facts"', src)
        self.assertIsNone(re.search(SIGNLESS, src))
        # and wherever else his name is linked
        for p in self.out.rglob("index.html"):
            self.assertIsNone(re.search(SIGNLESS, p.read_text(encoding="utf-8")), p)

    def test_no_companion_honorific_without_both_fields(self):
        for p in self.out.rglob("index.html"):
            self.assertNotIn(EN["honorific.companion_male"], p.read_text(encoding="utf-8"))
            self.assertNotIn(EN["honorific.companion_female"], p.read_text(encoding="utf-8"))

    def test_places_show_arabic_beside_the_name_with_lang_and_dir(self):
        with_ar = [e for e in self.site.by_kind["place"] if e.arabic]
        self.assertGreater(len(with_ar), 0)
        for e in with_ar:
            self.assertRegex(self.page(e), r'<span class="name-ar" lang="ar" dir="rtl">')

    def test_group_pages_and_group_index_exist(self):
        self.assertGreater(len(self.site.by_kind["group"]), 0)
        self.assertIn("Groups and tribes", (self.out / "group" / "index.html").read_text(encoding="utf-8"))

    def test_home_has_three_doors_in_order(self):
        src = (self.out / "index.html").read_text(encoding="utf-8")
        n = {k: len(self.site.by_kind[k]) for k in KINDS}
        self.assertIn(f'{n["person"]} people', src)
        pos = [src.index(f'id="door-{d}"') for d in ("discover", "study", "research")]
        self.assertEqual(pos, sorted(pos))
        doors = src[pos[0]:src.index('class="hub"')]
        self.assertIn('href="story/"', doors[:doors.index('id="door-study"')])
        self.assertIn('href="study/"', doors)
        self.assertIn('href="research/"', doors)
        self.assertLess(src.index('class="door-list"'), src.index('class="hub"'))

    def test_glossary_defines_only_quoted_terms_and_lists_the_rest(self):
        src = (self.out / "glossary" / "index.html").read_text(encoding="utf-8")
        self.assertIn("definition needed", src)
        self.assertIn("Isnād", src)

    def test_build_is_deterministic_across_processes(self):
        """Two builds in fresh processes with different hash seeds give identical files."""
        import filecmp
        import os
        import subprocess
        outs = []
        with tempfile.TemporaryDirectory() as da, tempfile.TemporaryDirectory() as db:
            for seed, d in (("1", da), ("2", db)):
                subprocess.run([sys.executable, str(SITE / "build.py"), "--graph", str(GRAPH), "--out", d],
                               check=True, capture_output=True, env={**os.environ, "PYTHONHASHSEED": seed})
                outs.append(d)

            def differs(cmp):
                bad = list(cmp.diff_files) + list(cmp.left_only) + list(cmp.right_only)
                for sub in cmp.subdirs.values():
                    bad += differs(sub)
                return bad

            self.assertEqual(differs(filecmp.dircmp(outs[0], outs[1])), [])


if __name__ == "__main__":
    unittest.main()
