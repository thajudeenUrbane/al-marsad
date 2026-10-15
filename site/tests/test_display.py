"""Unit tests for the display rules (site/display.py). No graph needed.
Run:  .venv/bin/python -m unittest discover -s site/tests -v
"""
import json
import re
import sys
import unittest
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SITE))

import display  # noqa: E402

I18N = json.loads((SITE / "i18n" / "en.json").read_text(encoding="utf-8"))


def t(key, **kw):
    s = I18N[key]
    return s.format(**kw) if kw else s


class Popularize(unittest.TestCase):
    def test_maintainers_example(self):
        self.assertEqual(display.popularize("Abū Bakr al-Ṣiddīq"), "Abu Bakr as-Siddiq")

    def test_leading_ayn_and_hamza_dropped(self):
        self.assertEqual(display.popularize("ʿUmar b. al-Khaṭṭāb"), "Umar b. al-Khattab")
        self.assertEqual(display.popularize("ʿAbd al-Raḥmān b. ʿAwf"), "Abd ar-Rahman b. Awf")

    def test_inner_ayn_and_hamza_become_apostrophes(self):
        self.assertEqual(display.popularize("Saʿd b. Muʿādh"), "Sa'd b. Mu'adh")
        self.assertEqual(display.popularize("ʿĀʾisha bint Abī Bakr"), "A'isha bint Abi Bakr")

    def test_sun_letters_assimilate(self):
        cases = {"al-Ṣiddīq": "as-Siddiq", "al-Raḥmān": "ar-Rahman", "al-Zubayr": "az-Zubayr",
                 "al-Naḍr": "an-Nadr", "al-Dārimī": "ad-Darimi", "al-Ṭabarī": "at-Tabari",
                 "al-Thaqafī": "ath-Thaqafi", "al-Dhahabī": "adh-Dhahabi", "al-Shāfiʿī": "ash-Shafi'i",
                 "al-Suyūṭī": "as-Suyuti"}
        for scholarly, popular in cases.items():
            with self.subTest(scholarly):
                self.assertEqual(display.popularize("Abū " + scholarly), "Abu " + popular)

    def test_moon_letters_and_lam_keep_al(self):
        for word in ("al-Madīna", "al-Ḥārith", "al-Khaṭṭāb", "al-Layth", "al-ʿAwwām", "al-Bukhārī"):
            with self.subTest(word):
                self.assertTrue(display.popularize(word).startswith("al-"), display.popularize(word))

    def test_capital_article(self):
        self.assertEqual(display.popularize("Al-Ṣafā"), "As-Safa")

    def test_already_popular_form_is_kept_as_written(self):
        for name in ("Anas ibn al-Nadr", "Abdullah ibn Abbas", "Abdullah b. Mas'ud", "Ahl al-Suffah",
                     "Al-Tufayl ibn Amr al-Dawsi", "The Ridda ('apostasy') wars", "Uthman and the Well of Rumah"):
            with self.subTest(name):
                self.assertEqual(display.popularize(name), name)

    def test_b_to_ibn_is_off_until_the_maintainer_rules(self):
        self.assertFalse(display.EXPAND_B_TO_IBN)
        self.assertEqual(display.popularize("Zayd b. Ḥāritha"), "Zayd b. Haritha")
        display.EXPAND_B_TO_IBN = True
        try:
            self.assertEqual(display.popularize("Zayd b. Ḥāritha"), "Zayd ibn Haritha")
        finally:
            display.EXPAND_B_TO_IBN = False

    def test_fold_keeps_length_for_nfc_text(self):
        text = "Abū Bakr al-Ṣiddīq ʿUmar"
        folded, index_map = display.fold_with_map(text)
        self.assertEqual(len(folded), len(index_map))
        self.assertEqual(folded, "Abu Bakr al-Siddiq 'Umar")


class Prophet(unittest.TestCase):
    LABEL = "The Prophet Muḥammad (peace and blessings be upon him)"

    def test_identified_by_label_only(self):
        self.assertTrue(display.is_prophet_label(self.LABEL))
        self.assertFalse(display.is_prophet_label("Muhammad ibn Maslamah"))
        self.assertFalse(display.is_prophet_label("Fāṭima bint Muḥammad"))

    def test_name_has_the_sign_and_no_english_blessing(self):
        self.assertEqual(display.person_display_name(self.LABEL), "The Prophet Muhammad ﷺ")

    def test_sign_not_doubled(self):
        self.assertEqual(display.person_display_name("The Prophet Muḥammad ﷺ", True), "The Prophet Muhammad ﷺ")

    def test_honour_in_names_and_notes(self):
        cases = {
            "Abu Bakr's address after the Prophet's death": "Abu Bakr's address after the Prophet's ﷺ death",
            "Death of the Prophet": "Death of the Prophet ﷺ",
            "Death of the Prophet ﷺ": "Death of the Prophet ﷺ",
            "the Prophet's ﷺ face": "the Prophet's ﷺ face",
            "with the Prophet Muhammad": "with the Prophet Muhammad ﷺ",
            "the Prophet (peace and blessings be upon him) said": "the Prophet ﷺ said",
            "the Messenger of Allah": "the Messenger of Allah ﷺ",
            "Prophet Yusuf": "Prophet Yusuf",
            'he said, "I am the Prophet, no lie"': 'he said, "I am the Prophet, no lie"',
            "a boy in the Prophet's household": "a boy in the Prophet's \ufdfa household",
            "prophetic era": "prophetic era",
            "Prophets of old": "Prophets of old",
        }
        for src, want in cases.items():
            with self.subTest(src):
                self.assertEqual(display.honour(src), want)
                self.assertEqual(display.honour(want), want, "honour must be idempotent")


class Companions(unittest.TestCase):
    def test_needs_both_fields_and_never_guesses(self):
        f = display.companion_honorific_key
        self.assertIsNone(f(None, None))
        self.assertIsNone(f("attested", None))
        self.assertIsNone(f(None, "male"))
        self.assertIsNone(f("disputed", "male"))
        self.assertIsNone(f("undetermined", "female"))
        self.assertEqual(f("attested", "male"), "honorific.companion_male")
        self.assertEqual(f("attested", "female"), "honorific.companion_female")

    def test_no_gender_predicate_is_configured_yet(self):
        self.assertEqual(display.GENDER_PREDICATES, ())


class Dates(unittest.TestCase):
    def fmt(self, **ext):
        base = {"native": None, "calendar": None, "earliest": None, "latest": None, "precision": None,
                "basis": None, "conv_method": None, "conv_days": None, "relative": False, "disputed": False}
        base.update(ext)
        return display.format_extent(base, t)

    def test_gregorian_first_then_hijri(self):
        self.assertEqual(self.fmt(native="1 AH / 622 CE", calendar="gregorian")["text"], "622 CE (1 AH)")
        self.assertEqual(self.fmt(native="13-15 AH / 634-636 CE", calendar="gregorian")["text"], "634-636 CE (13-15 AH)")

    def test_circa_is_said_in_words(self):
        self.assertEqual(self.fmt(native="c. 610 CE", calendar="gregorian")["text"], "around 610 CE")

    def test_hijri_only_uses_recorded_bounds_and_says_it_is_converted(self):
        v = self.fmt(native="7 Shawwāl 3 AH", calendar="hijri", earliest="0625-03-23T00:00:00+00:00",
                     latest="0625-03-23T23:59:59+00:00", precision="day",
                     conv_method="tabular-islamic-civil", conv_days="1")
        self.assertEqual(v["text"], "23 March 625 CE (7 Shawwal 3 AH)")
        self.assertTrue(any("converted" in n and "up to 1 day" in n for n in v["notes"]), v["notes"])

    def test_no_bounds_no_gregorian_date_is_made_up(self):
        v = self.fmt(native="shortly after Badr, 2 AH", calendar="hijri", precision="period", relative=True)
        self.assertEqual(v["text"], "shortly after Badr, 2 AH")
        self.assertNotIn("CE", v["text"])
        self.assertTrue(any("relative" in n for n in v["notes"]))

    def test_nothing_recorded_gives_nothing(self):
        self.assertIsNone(self.fmt()["text"])

    def test_bounds_wider_than_precision_are_not_narrowed(self):
        v = self.fmt(calendar="hijri", earliest="0627-01-01T00:00:00+00:00", latest="0629-12-31T00:00:00+00:00",
                     precision="month")
        self.assertEqual(v["text"], "627–629 CE")

    def test_arabic_digits_for_a_hijri_year(self):
        v = self.fmt(native="٩٤", calendar="hijri", earliest="0712-10-06T00:00:00+00:00",
                     latest="0713-09-24T00:00:00+00:00", precision="year")
        self.assertEqual(v["text"], "712–713 CE (94 AH)")

    def test_arabic_text_is_kept_as_recorded(self):
        v = self.fmt(native="ثلاث ليال", calendar="hijri", precision="day", relative=True)
        self.assertEqual(v["text"], "ثلاث ليال")

    def test_remark_moves_out_of_the_date(self):
        v = self.fmt(native="619 CE ('year of sorrow', conventionally cited)", calendar="gregorian")
        self.assertEqual(v["text"], "619 CE")
        self.assertTrue(any("year of sorrow" in n for n in v["notes"]))


class Sorting(unittest.TestCase):
    def test_articles_are_ignored(self):
        self.assertEqual(display.index_letter("al-Abbas b. Abd al-Muttalib"), "A")
        self.assertEqual(display.index_letter("The Prophet Muhammad ﷺ"), "P")
        self.assertEqual(display.index_letter("'Umar"), "U")

    def test_sort_key_folds(self):
        self.assertLess(display.sort_key("Ḥafṣa"), display.sort_key("Ibn Shihāb"))


class Terms(unittest.TestCase):
    def test_link_wraps_original_characters_and_escapes(self):
        matchers = [(re.compile(r"(?<![a-z0-9'])sahabi(?![a-z0-9'])", re.I), "sahabi")]
        out, keys = display.link_terms("A <b>ṣaḥābī</b> & more", matchers, lambda k: "g/#" + k)
        self.assertEqual(out, 'A &lt;b&gt;<a class="term" href="g/#sahabi">ṣaḥābī</a>&lt;/b&gt; &amp; more')
        self.assertEqual(keys, {"sahabi"})

    def test_once_links_the_first_occurrence_only(self):
        matchers = [(re.compile(r"adhan", re.I), "adhan")]
        seen = set()
        out, _ = display.link_terms("adhan and adhan", matchers, lambda k: "#" + k, seen, once=True)
        self.assertEqual(out.count("<a "), 1)
        out2, _ = display.link_terms("the adhan", matchers, lambda k: "#" + k, seen, once=True)
        self.assertEqual(out2.count("<a "), 0)

    def test_arabic_script_is_marked(self):
        self.assertEqual(display.mark_arabic("Makkah مكة"), 'Makkah <span lang="ar" dir="rtl">مكة</span>')
        self.assertEqual(display.mark_arabic("Prophet ﷺ"), 'Prophet <span class="pbuh" lang="ar" dir="rtl">ﷺ</span>')


if __name__ == "__main__":
    unittest.main()
