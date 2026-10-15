"""Tests for the Arabic interface (slice 9): ar.json against en.json, the plural rules, and
the built Arabic copy under ar/. Needs build/graph.ttl for the built-site tests.
Run:  .venv/bin/python -m unittest discover -s site/tests -v
"""
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
import check_html  # noqa: E402
import display  # noqa: E402
from render import I18n, plural_category  # noqa: E402

GRAPH = ROOT / "build" / "graph.ttl"
EN = json.loads((SITE / "i18n" / "en.json").read_text(encoding="utf-8"))
AR = json.loads((SITE / "i18n" / "ar.json").read_text(encoding="utf-8"))
ARABIC_FORMS = ("zero", "two", "few", "many")   # the plural forms Arabic has beyond one and other


def plural_bases(d: dict) -> set:
    return {k.rsplit(".", 1)[0] for k in d if k.endswith(".one")}


class KeysAgree(unittest.TestCase):
    def test_ar_has_every_key_of_en(self):
        self.assertEqual([k for k in EN if k not in AR], [])

    def test_ar_has_no_other_keys_than_the_extra_plural_forms(self):
        """Exactly en.json's keys, plus the Arabic plural forms (two, few, many) of the
        counted strings en.json writes as one and other."""
        bases = plural_bases(EN)
        extra = [k for k in AR if k not in EN]
        stray = [k for k in extra if k.rsplit(".", 1)[0] not in bases or k.rsplit(".", 1)[1] not in ARABIC_FORMS]
        self.assertEqual(stray, [])

    def test_every_counted_string_has_all_arabic_forms(self):
        for base in sorted(plural_bases(EN)):
            for form in ("one", "two", "few", "many", "other"):
                self.assertIn(f"{base}.{form}", AR, base)

    def test_placeholders_agree(self):
        """A {name} in the English string is in the Arabic one, and the other way round
        (the "one" forms may leave the number out: "قصة واحدة")."""
        for k, en in EN.items():
            if k.endswith(".one") or k == "date.converted_one":
                continue
            self.assertEqual(set(re.findall(r"\{(\w+)\}", en)), set(re.findall(r"\{(\w+)\}", AR[k])), k)

    def test_the_draft_status_is_stated_in_the_file_and_in_the_footer_strings(self):
        self.assertEqual(AR["footer.ar_draft_en"], "Arabic interface text: draft, awaiting review by the scholars")
        self.assertTrue(AR["footer.ar_draft"].startswith("نص الواجهة العربية"))

    def test_no_value_is_left_in_english_except_names_and_identifiers(self):
        allowed = {"footer.ar_draft_en", "lang.switch", "footer.cc_by_sa", "footer.agpl", "details.turtle",
                   "external.system.wikidata", "external.system.althurayya", "external.system.openiti",
                   "external.id", "date.around_recorded"}
        for k, v in AR.items():
            if k in allowed:
                continue
            letters = re.sub(r"\{\w+\}|https?://\S+|CC0?[ A-Z0-9.-]*|Turtle|IRI|CSV|A–Z|AGPL-3\.0|\bw3id\.org\S*|\b(?:b|bin|ibn)\b", "", v)
            self.assertFalse(re.search(r"[A-Za-z]{3,}", letters), f"{k}: {v}")


class Plurals(unittest.TestCase):
    def test_arabic_categories(self):
        want = {0: "zero", 1: "one", 2: "two", 3: "few", 10: "few", 11: "many", 99: "many", 100: "other",
                101: "other", 102: "other", 103: "few", 110: "few", 111: "many", 184: "many", 200: "other"}
        for n, cat in want.items():
            self.assertEqual(plural_category("ar", n), cat, n)

    def test_english_is_unchanged(self):
        self.assertEqual([plural_category("en", n) for n in (0, 1, 2, 5)], ["other", "one", "other", "other"])

    def test_counted_phrases_agree_in_number_and_case(self):
        i = I18n(SITE / "i18n" / "ar.json", "ar")
        self.assertEqual(i.tn("home.count.person", 1), "شخص واحد")
        self.assertEqual(i.tn("home.count.person", 2), "شخصان")
        self.assertEqual(i.tn("home.count.person", 5), "5 أشخاص")
        self.assertEqual(i.tn("home.count.person", 11), "11 شخصًا")
        self.assertEqual(i.tn("home.count.person", 184), "184 شخصًا")
        self.assertEqual(i.tn("home.count.person", 100), "100 شخص")
        self.assertEqual(i.tn("home.count.person", 0), "0 شخص")   # no zero form is written: the "other" form

    def test_latin_data_is_isolated_inside_an_arabic_sentence(self):
        i = I18n(SITE / "i18n" / "ar.json", "ar")
        self.assertEqual(i.t("claim.role", value="scribe"), "الدور: ⁦scribe⁩")
        self.assertEqual(i.t("claim.role", value="كاتب"), "الدور: كاتب")
        self.assertEqual(I18n(SITE / "i18n" / "en.json").t("claim.role", value="scribe"), "Role: scribe")


class Dates(unittest.TestCase):
    """Gregorian first, as the maintainer ruled, in either language; the words are translated,
    the digits are not, and a recorded English date is left as recorded."""

    def t(self, key, **kw):
        return AR[key].format(**kw)

    def test_a_date_worked_out_from_bounds_uses_arabic_words(self):
        v = display.format_extent({"earliest": "0622-09-24", "latest": "0622-09-24", "precision": "day"}, self.t)
        self.assertEqual(v["text"], "24 سبتمبر 622 م")

    def test_a_recorded_date_stays_as_recorded(self):
        v = display.format_extent({"native": "1 AH / 622 CE"}, self.t)
        self.assertEqual(v["text"], "622 CE (1 AH)")   # Gregorian first
        mark = lambda s: f"<{s}>"   # a page marks the recorded parts; a worked-out part stays unmarked
        v = display.format_extent({"native": "1 AH", "earliest": "0622-09-24", "latest": "0622-09-24",
                                   "precision": "day"}, self.t, mark)
        self.assertEqual(v["text"], "24 سبتمبر 622 م (<1 AH>)")
        v = display.format_extent({"native": "c. 615 CE"}, self.t)
        self.assertEqual(v["text"], "around 615 CE")   # not "نحو": the recorded words stay English


@unittest.skipUnless(GRAPH.exists(), "build/graph.ttl missing: run ontology/build_graph.py")
class BuiltArabicSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        site_build.build(GRAPH, cls.out, quiet=True)
        from model import Site
        cls.site = Site(GRAPH)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_every_reader_page_has_an_arabic_twin_at_the_same_path_below_ar(self):
        english = {p.relative_to(self.out).as_posix() for p in self.out.rglob("index.html")}
        arabic = {p.relative_to(self.out / "ar").as_posix() for p in (self.out / "ar").rglob("index.html")}
        self.assertEqual(arabic, {r for r in english if not r.startswith(("ar/", "experiments/"))})
        for kind in ("person", "event", "place", "group", "story"):
            for e in self.site.by_kind[kind]:
                self.assertTrue((self.out / "ar" / kind / e.pid / "index.html").is_file())

    def test_arabic_pages_are_right_to_left_with_a_switch_and_alternates(self):
        for p in (self.out / "ar").rglob("index.html"):
            src = p.read_text(encoding="utf-8")
            rel = p.relative_to(self.out / "ar").as_posix()
            self.assertIn('<html lang="ar" dir="rtl">', src, rel)
            self.assertIn('hreflang="en"', src, rel)
            self.assertEqual(len(re.findall(r'<a class="lang-switch" href="[^"]+" hreflang="en" lang="en"', src)), 1, rel)
            self.assertIn(AR["footer.ar_draft"], src, rel)
        for p in self.out.rglob("index.html"):
            rel = p.relative_to(self.out).as_posix()
            if rel.startswith(("ar/", "experiments/")) or "alternate" not in p.read_text(encoding="utf-8"):
                continue
            self.assertIn('hreflang="ar" lang="ar" dir="rtl"', p.read_text(encoding="utf-8"), rel)

    def test_english_pages_carry_no_arabic_draft_notice_and_no_rtl(self):
        for rel in ("index.html", "person/index.html", "search/index.html"):
            src = (self.out / rel).read_text(encoding="utf-8")
            self.assertNotIn(AR["footer.ar_draft"], src)
            self.assertIn('<html lang="en" dir="ltr">', src)

    def test_data_is_not_translated_and_english_data_is_marked(self):
        abu = [e for e in self.site.by_kind["person"] if e.name == "Abu Bakr as-Siddiq"][0]
        src = (self.out / "ar" / "person" / abu.pid / "index.html").read_text(encoding="utf-8")
        self.assertIn('<h1><span lang="en" dir="ltr">Abu Bakr as-Siddiq</span>', src)
        self.assertIn("Abū Bakr al-Ṣiddīq", src)   # the scholarly form as recorded, under Details
        # every claim keeps its status label, in Arabic: none is upgraded or invented
        self.assertEqual(len(re.findall(r'<li class="claim">', src)), len(re.findall(r'class="status status-[a-z_]+">الحالة: ', src)))
        self.assertNotIn("Status:", src)

    def test_story_text_is_recorded_english_marked_as_such(self):
        story = self.site.by_kind["story"][0]
        src = (self.out / "ar" / "story" / story.pid / "index.html").read_text(encoding="utf-8")
        self.assertIn('<div class="prose" lang="en" dir="ltr">', src)
        self.assertIn(AR["story.ai_note"], src)
        self.assertIn(AR["story.banner"], src)

    def test_the_arabic_hub_links_english_only_views_and_says_so(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            site_build.build(GRAPH, out, quiet=True)
            # a view built by another builder: the link goes to the site root and is labelled
            (out / "timeline").mkdir()
            (out / "timeline" / "index.html").write_text("<!doctype html><title>t</title>", encoding="utf-8")
            site_build.build_hub(GRAPH, out, quiet=True)
            src = (out / "ar" / "index.html").read_text(encoding="utf-8")
            self.assertIn('href="../timeline/" hreflang="en"', src)
            self.assertIn(AR["hub.english_only"], src)
            self.assertEqual(check_html.check_page(out, out / "ar" / "index.html", check_html.collect_ids(out)), [])

    def test_arabic_thread_json_has_arabic_strings_and_plural_forms(self):
        d = json.loads((self.out / "ar" / "thread.json").read_text(encoding="utf-8"))
        for cat in ("one", "two", "few", "many", "other"):
            self.assertIn(f"lead.{cat}", d["s"])
        self.assertEqual(d["s"]["close"], AR["thread.close"])
        en = json.loads((self.out / "thread.json").read_text(encoding="utf-8"))
        self.assertEqual([r[:3] for r in d["e"]], [r[:3] for r in en["e"]])   # the same records, names as recorded
        self.assertEqual(sorted(en["s"]), sorted(k for k in d["s"] if k.split(".")[-1] not in ARABIC_FORMS))

    def test_search_page_strings_have_arabic_plural_forms(self):
        src = (self.out / "ar" / "search" / "index.html").read_text(encoding="utf-8")
        m = re.search(r'<script type="application/json" id="search-strings">(.*?)</script>', src, re.S)
        strings = json.loads(m.group(1))
        for cat in ("one", "two", "few", "many", "other"):
            self.assertIn(f"count_{cat}", strings)
        self.assertIn('data-fetch="../../search.json"', src)   # the one index, shared

    def test_the_arabic_pages_do_not_copy_what_the_site_root_holds(self):
        self.assertFalse((self.out / "ar" / "assets").exists())
        self.assertFalse((self.out / "ar" / "search.json").exists())
        self.assertEqual(list((self.out / "ar").rglob("*.ttl")), [])


if __name__ == "__main__":
    unittest.main()
