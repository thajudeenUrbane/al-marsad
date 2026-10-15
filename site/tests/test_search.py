"""Tests for search (slice 2b): the normaliser and the ranking in site/names.py, their
browser port site/static/search.js (same cases, same results), the index, the search
page and the shared display rules.
Run:  .venv/bin/python -m unittest discover -s site/tests -v
The parity tests need `node`; without it they are skipped (site/check_search.cjs then
checks the port in a browser).
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
ROOT = SITE.parent
sys.path.insert(0, str(SITE))

import build as site_build  # noqa: E402
import check_budget  # noqa: E402
import display  # noqa: E402
import names  # noqa: E402

GRAPH = ROOT / "build" / "graph.ttl"
CASES = json.loads((SITE / "tests" / "search_cases.json").read_text(encoding="utf-8"))["cases"]
EN = json.loads((SITE / "i18n" / "en.json").read_text(encoding="utf-8"))
JS = SITE / "static" / "search.js"
NODE = shutil.which("node")
REQUIRED = ("Abu Bakr", "Abū Bakr", "abubakr", "ابو بكر", "أبو بكر")   # slice-2 brief, 2b item 3
EXTRA_QUERIES = ("Abu Bark", "zzqx", "Mohammed", "Muhammad", "Medina", "عمر", "Siddiq", "abu ba",
                 "siddiq abu", "akr", "Khaild", "b", "al-", "ﷺ", "",
                 "Arrival in Madinah and the Building of the Mosqeu", "arrivalinmadinahandthebuildingx")


def run_node(job: dict) -> dict:
    r = subprocess.run([NODE, str(SITE / "tests" / "search_parity.cjs")], input=json.dumps(job, ensure_ascii=False),
                       capture_output=True, text=True, encoding="utf-8", check=True, timeout=120)
    return json.loads(r.stdout)


def toy_items() -> list[dict]:
    """One index item per case text, so the ranking can be compared without the graph."""
    return [names.index_item(f"t/{i}", c["in"], []) for i, c in enumerate(CASES) if names.normalise(c["in"])]


class Normaliser(unittest.TestCase):
    def test_shared_cases(self):
        for c in CASES:
            with self.subTest(c["in"]):
                self.assertEqual(names.normalise(c["in"]), c["normal"])
                self.assertEqual(names.skeleton(c["normal"]), c["sound"])

    def test_the_required_queries_meet_abu_bakr(self):
        """Latin spellings meet his kunya in the normal form, Arabic script in the sound key."""
        kunya = names.normalise("Abū Bakr")
        for q in REQUIRED[:3]:
            self.assertEqual(names.normalise(q).replace(" ", ""), kunya.replace(" ", ""), q)
        for q in REQUIRED[3:]:
            self.assertEqual(names.normalise(q), "ابو بكر", q)
            self.assertEqual(names.skeleton(names.normalise(q)), names.skeleton(kunya), q)

    def test_the_brief_rules(self):
        n = names.normalise
        self.assertEqual(n("ʿUthmān"), n("Uthman"))                       # diacritics, ayn
        self.assertEqual(n("Saʿd"), n("Sa'd"))                             # ' marks
        self.assertEqual(n("Zayd b. Ḥāritha"), n("Zayd bin Haritha"))       # b. / bin / ibn
        self.assertEqual(n("Zayd b. Ḥāritha"), n("Zayd ibn Haritha"))
        self.assertEqual(n("al-Ṣiddīq"), n("Siddiq"))                       # optional al-
        self.assertEqual(n("el-Medina"), n("Medina"))                       # optional el-
        self.assertEqual(n("أحمد"), n("احمد"))                              # alif forms
        self.assertEqual(n("إبراهيم"), n("ابراهيم"))
        self.assertEqual(n("آمنة"), n("امنه"))                              # and ة -> ه
        self.assertEqual(n("موسى"), n("موسي"))                              # ى -> ي
        self.assertEqual(n("مُحَمَّدٌ"), n("محمد"))                          # tashkil
        self.assertEqual(n("محـــمد"), n("محمد"))                           # tatweel

    def test_the_last_word_of_a_query_is_left_as_typed(self):
        self.assertEqual(names.normalise("Zayd b"), "zayd b")             # could be the start of Bakr
        self.assertEqual(names.normalise("Zayd b Haritha"), "zayd ibn haritha")

    def test_rules_are_plain_data_and_every_pattern_compiles(self):
        self.assertEqual(json.loads(json.dumps(names.RULES)), names.RULES)
        for k in ("nonword", "abd", "sk_keep"):
            re.compile(names.RULES[k])
        self.assertEqual(names.RULES["tiers"], len(names.TIERS))


class DisplayAndSearchShareRules(unittest.TestCase):
    def test_one_place(self):
        """display.py keeps no copy of the name tables, and search.js none at all."""
        self.assertIs(display.fold, names.fold)
        self.assertIs(display.has_scholarly_marks, names.has_scholarly_marks)
        src = (SITE / "display.py").read_text(encoding="utf-8")
        for table in ("SUN_LETTERS", "AYN_HAMZA", "_SUN_ARTICLE", "_LEADING_MARKS"):
            self.assertNotIn(table, src)
        js = JS.read_text(encoding="utf-8")
        self.assertTrue(js.isascii(), "search.js must hold no letter tables (no Arabic letters)")
        for entry in ('"ibn"', '"abu"', '"kh"', '"al"', '"sh"'):
            self.assertNotIn(entry, js)

    def test_the_popular_form_and_the_recorded_form_search_alike(self):
        for c in CASES:
            with self.subTest(c["in"]):
                self.assertEqual(names.normalise(display.popularize(c["in"])), c["normal"])

    def test_b_to_ibn_switch_changes_display_not_search(self):
        self.assertEqual(display.popularize("Zayd b. Ḥāritha"), "Zayd b. Haritha")
        display.EXPAND_B_TO_IBN = True
        try:
            self.assertEqual(display.popularize("Zayd b. Ḥāritha"), "Zayd ibn Haritha")
        finally:
            display.EXPAND_B_TO_IBN = False
        self.assertEqual(names.normalise("Zayd b. Haritha"), names.normalise("Zayd ibn Haritha"))


class Ranking(unittest.TestCase):
    ITEMS = names.prepare([
        names.index_item("person/1", "Abu Bakr as-Siddiq", ["Abū Bakr al-Ṣiddīq", "Abū Bakr", "al-Ṣiddīq"]),
        names.index_item("person/2", "A'isha bint Abi Bakr", ["ʿĀʾisha bint Abī Bakr", "ʿĀʾisha"]),
        names.index_item("event/3", "Abu Bakr's acceptance of Islam", []),
        names.index_item("person/4", "al-Bukhari", ["al-Bukhārī", "Muḥammad"]),
        names.index_item("person/5", "The Prophet Muhammad ﷺ", ["Muḥammad"]),
        names.index_item("place/6", "Makkah", ["مكة"]),
    ])

    def first(self, q):
        r = names.search(self.ITEMS, q)
        return r[0] if r else None

    def test_tiers(self):
        self.assertEqual(self.first("abubakr"), ("person/1", 0))
        self.assertEqual(self.first("abu ba"), ("person/1", 1))
        self.assertEqual(self.first("siddiq abu"), ("person/1", 2))
        self.assertEqual(self.first("ابو بكر"), ("person/1", 4))
        self.assertEqual(self.first("Mecca"), ("place/6", 4))
        self.assertEqual(self.first("مكة"), ("place/6", 0))
        self.assertEqual(self.first("Abu Bark"), ("person/1", 6))
        self.assertEqual(names.search(self.ITEMS, "zzqx"), [])

    def test_one_edit(self):
        yes = [("abubakr", "abubakr"), ("abubark", "abubakr"), ("abubakx", "abubakr"),
               ("abubak", "abubakr"), ("abubakrr", "abubakr"), ("bubakr", "abubakr")]
        no = [("abukabr", "abubakr"), ("abubkar", "abubakrx"), ("ab", "abcd"), ("abcd", "abdc x")]
        for a, b in yes:
            self.assertTrue(names.within_one(a, b), (a, b))
            self.assertTrue(names.within_one(b, a), (b, a))
        for a, b in no:
            self.assertFalse(names.within_one(a, b), (a, b))
            self.assertFalse(names.within_one(b, a), (b, a))

    def test_the_name_as_shown_breaks_ties(self):
        """Both have the ism Muhammad; the one whose shown name has it comes first."""
        self.assertEqual([u for u, _ in names.search(self.ITEMS, "Muhammad")][:2], ["person/5", "person/4"])
        self.assertEqual([u for u, _ in names.search(self.ITEMS, "Mohammed")][:2], ["person/5", "person/4"])

    def test_similar_spellings_are_marked(self):
        tiers = dict(names.search(self.ITEMS, "ابو بكر"))
        self.assertTrue(all(t >= names.SIMILAR_FROM for t in tiers.values()))


@unittest.skipUnless(NODE, "node not found: the JavaScript port is checked in a browser by site/check_search.cjs")
class Parity(unittest.TestCase):
    """The browser port gives the same output as the Python on the same input."""

    def test_normaliser_and_sound_key(self):
        inputs = [c["in"] for c in CASES]
        js = run_node({"rules": names.RULES, "inputs": inputs, "items": [], "queries": []})
        for i, text in enumerate(inputs):
            with self.subTest(text):
                self.assertEqual(js["normal"][i], names.normalise(text))
                self.assertEqual(js["sound"][i], names.skeleton(names.normalise(text)))

    def test_search_on_the_cases(self):
        items = toy_items()
        queries = [c["in"] for c in CASES] + list(EXTRA_QUERIES)
        js = run_node({"rules": names.RULES, "inputs": [], "items": items, "queries": queries})
        prepared = names.prepare(items)
        for i, q in enumerate(queries):
            with self.subTest(q):
                self.assertEqual([tuple(x) for x in js["search"][i]], names.search(prepared, q))

    @unittest.skipUnless(GRAPH.exists(), "build/graph.ttl missing")
    def test_search_on_the_real_index(self):
        from model import Site
        index = site_build.search_index(Site(GRAPH))
        queries = list(REQUIRED) + [c["in"] for c in CASES] + list(EXTRA_QUERIES)
        js = run_node({"rules": index["rules"], "inputs": [], "items": index["items"], "queries": queries})
        prepared = names.prepare(index["items"])
        for i, q in enumerate(queries):
            with self.subTest(q):
                self.assertEqual([tuple(x) for x in js["search"][i]], names.search(prepared, q))


@unittest.skipUnless(GRAPH.exists(), "build/graph.ttl missing: run ontology/build_graph.py")
class BuiltSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from model import Site
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        site_build.build(GRAPH, cls.out, quiet=True)
        cls.site = Site(GRAPH)
        cls.index = json.loads((cls.out / "search.json").read_text(encoding="utf-8"))
        cls.items = names.prepare(cls.index["items"])
        cls.page = (cls.out / "search" / "index.html").read_text(encoding="utf-8")
        # found by his name as recorded in the graph, never by ID
        abu = [e for e in cls.site.by_kind["person"] if e.scholarly == "Abū Bakr al-Ṣiddīq"]
        cls.abu = abu[0] if len(abu) == 1 else None

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_required_queries_find_abu_bakr_first(self):
        self.assertIsNotNone(self.abu)
        for q in REQUIRED:
            with self.subTest(q):
                found = names.search(self.items, q)
                self.assertEqual(found[0][0], f"person/{self.abu.pid}")

    def test_index_is_small_and_has_one_item_per_entity(self):
        size = (self.out / "search.json").stat().st_size
        self.assertLess(size / len(self.site.entities), 200, "index items average over 200 bytes")
        self.assertEqual(sorted(it["u"] for it in self.index["items"]),
                         sorted(f"{e.kind}/{e.pid}" for e in self.site.entities.values()))
        self.assertEqual(self.index["rules"], names.RULES)
        for it in self.index["items"]:
            self.assertEqual(set(it), {"u", "n", "k"})
            self.assertTrue((self.out / it["u"] / "index.html").is_file(), it["u"])
            self.assertEqual(it["k"][0], names.normalise(it["n"]), "the first key is the name as shown")
            self.assertEqual(len(it["k"]), len(set(it["k"])))

    def test_scholarly_and_popular_forms_are_both_findable(self):
        for e in self.site.entities.values():
            for label in (e.scholarly, e.name):
                key = names.normalise(display.strip_blessing_tail(label))
                with self.subTest(label):
                    self.assertIn(key, [k for it in self.index["items"] if it["u"] == f"{e.kind}/{e.pid}" for k in it["k"]])

    def test_every_display_name_assimilates_al_before_a_sun_letter(self):
        sun = re.compile(r"\b[Aa]l-(?:" + "|".join(names.SUN_LETTERS) + ")", re.IGNORECASE)
        for e in self.site.entities.values():
            self.assertIsNone(sun.search(e.name), e.name)

    def test_search_page_works_without_javascript(self):
        p = self.page
        self.assertIn('data-fetch="../search.json"', p)
        self.assertIn('<script src="../assets/search.js" defer></script>', p)
        nojs = p[p.index('id="search-nojs"'):p.index('id="search-status"')]
        self.assertIn(EN["search.nojs"].replace("'", "&#x27;").split(",")[0], nojs.replace("'", "&#x27;"))
        self.assertTrue(EN["search.unverified"] in nojs or "search.partly_verified" in nojs)
        for e in self.site.entities.values():   # the A-Z list holds every name
            self.assertIn(f'href="../{e.kind}/{e.pid}/"', p)
        self.assertIn(">" + self.abu.name + "</a>", p)

    def test_empty_result_reports_coverage_never_a_blank(self):
        """docs/05 section 3: what was searched, what the corpus holds, that it is unverified."""
        empty = self.page[self.page.index('id="search-empty"'):self.page.index('id="search-results"')]
        self.assertIn(" hidden>", empty[:60])
        for k in ("person", "event", "place", "group", "story"):
            self.assertIn(f'href="../{k}/"', empty)
        self.assertIn(EN["search.empty_next"], empty)
        sc, cc = self.site.status_counts(), self.site.coverage_counts()
        if not sc.get("accepted") and not cc.get("reviewed") and not cc.get("verified"):
            self.assertIn(EN["search.unverified"], empty)
        strings = json.loads(re.search(r'<script type="application/json" id="search-strings">(.*?)</script>',
                                       self.page, re.S).group(1))
        self.assertEqual(strings["none"], EN["search.none"])
        self.assertIn("{q}", strings["none"])
        self.assertTrue(set(strings.values()) <= set(EN.values()))

    def test_every_other_page_has_a_search_box_that_submits_to_the_search_page(self):
        for path in self.out.rglob("index.html"):
            rel = path.relative_to(self.out).as_posix()
            src = path.read_text(encoding="utf-8")
            if rel == "search/index.html":
                self.assertNotIn('class="site-search"', src)
                continue
            if rel.startswith("experiments/") and rel != "experiments/index.html":
                continue   # the copied prototypes keep their own pages (site/experiments.py)
            depth = rel.count("/")
            self.assertIn(f'<form class="site-search" role="search" action="{"../" * depth}search/" method="get">', src, rel)

    def test_budget_counts_the_script_and_the_index_on_the_search_page(self):
        results, problems = check_budget.check(self.out)
        self.assertEqual(problems, [])
        total = {rel: t for t, rel, _, _ in results}["search/index.html"]
        parts = [self.out / "search" / "index.html", self.out / "assets" / "site.css",
                 self.out / "assets" / "search.js", self.out / "search.json", self.out / "assets" / "enhance.js"]
        self.assertEqual(total, sum(p.stat().st_size for p in parts))
        self.assertLess(total, check_budget.LIMIT)


class ScriptHasNoText(unittest.TestCase):
    def test_no_ui_words_and_no_urls_in_search_js(self):
        js = JS.read_text(encoding="utf-8")
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
        literals = re.findall(r'"((?:[^"\\]|\\.)*)"', code)
        words = [s for s in literals if s != "use strict" and re.search(r"[A-Za-z]{3,}\s+[A-Za-z]{3,}", s)]
        self.assertEqual(words, [], "visible text belongs in site/i18n/en.json")
        urls = [s for s in literals if re.search(r"https?:|//|\.json\b", s)]
        self.assertEqual(urls, [], "the script fetches only what the page names in data-fetch")
        self.assertIn('fetch(form.getAttribute("data-fetch"))', code)


if __name__ == "__main__":
    unittest.main()
