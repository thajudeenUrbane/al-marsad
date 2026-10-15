"""Tests for the Lifelines view (site/lifelines).

    .venv/bin/python -m unittest discover -s site/lifelines/tests

The fixture graph and CSV in tests/fixtures are wholly fictional ("Test person ...").
"""
from __future__ import annotations

import csv
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
LL = HERE.parent
SITE = LL.parent
ROOT = SITE.parent
sys.path.insert(0, str(LL))
sys.path.insert(1, str(SITE))

import build_lifelines as B  # noqa: E402
import calendars as cal  # noqa: E402
import lives  # noqa: E402
from collect import DateClaim  # noqa: E402

FX_GRAPH = HERE / "fixtures" / "graph.ttl"
FX_CSV = HERE / "fixtures" / "external-dates.csv"
GRAPH = ROOT / "build" / "graph.ttl"
J = cal.jdn_from_julian


def claim(kind, lo, hi, review=False, precision="year"):
    return DateClaim(kind=kind, lo=lo, hi=hi, precision=precision, text="", notes=[],
                     source={"type": "test", "label": "test", "status": "proposed"}, review=review)


def year(y):
    return cal.range_for(y, 1, 1, "year", "julian")


class Calendars(unittest.TestCase):
    def test_tabular_hijri_matches_the_graphs_own_conversion(self):
        # the graph stores 17 Ramadan 2 AH (tabular-islamic-civil) as 0624-03-13
        self.assertEqual(cal.jdn_from_hijri(2, 9, 17), J(624, 3, 13))
        self.assertEqual(cal.jdn_from_hijri(1, 1, 1), J(622, 7, 16))
        self.assertEqual(cal.jdn_from_iso_bound("0624-03-13T00:00:00+00:00"), J(624, 3, 13))

    def test_round_trips(self):
        for j in range(J(450, 1, 1), J(900, 1, 1), 97):
            self.assertEqual(J(*cal.julian_from_jdn(j)), j)
            self.assertEqual(cal.jdn_from_gregorian(*cal.gregorian_from_jdn(j)), j)
            self.assertEqual(cal.jdn_from_hijri(*cal.hijri_from_jdn(j)), j)

    def test_julian_and_gregorian_differ_by_three_days_in_the_seventh_century(self):
        self.assertEqual(cal.jdn_from_gregorian(632, 6, 11), J(632, 6, 8))

    def test_years_before_the_hijra_count_back_in_lunar_years(self):
        self.assertEqual(cal.hijri_from_jdn(J(622, 7, 15))[0], 0)       # the year 1 BH
        self.assertEqual(cal.hijri_year_label(0, "AH", "BH"), "1 BH")
        self.assertEqual(cal.hijri_year_label(1, "AH", "BH"), "1 AH")
        # 1 January 570 is 54.15 lunar years before 16 July 622, so in the 55th lunar year before it
        lo, hi = year(570)
        self.assertAlmostEqual((cal.HIJRA_EPOCH_JDN - lo) / cal.LUNAR_YEAR_DAYS, 54.15, places=2)
        self.assertEqual(cal.hijri_years_text(lo, hi, "AH", "BH"), "55–54 BH")


class Ages(unittest.TestCase):
    def test_63_lunar_years_are_about_61_solar_years(self):
        days = 63 * cal.LUNAR_YEAR_DAYS
        self.assertAlmostEqual(days / cal.SOLAR_YEAR_DAYS, 61.12, places=2)
        self.assertEqual(cal.completed_years(days / cal.SOLAR_YEAR_DAYS, days / cal.SOLAR_YEAR_DAYS), (61, 61))
        self.assertAlmostEqual(cal.LUNAR_YEAR_DAYS, 354.3667, places=4)

    def test_age_is_a_range_that_carries_the_birth_uncertainty(self):
        b = year(570)
        at = (J(632, 6, 8), J(632, 6, 8))
        lo, hi = cal.age_range(b, at, "lunar")
        self.assertAlmostEqual(hi - lo, 364 / cal.LUNAR_YEAR_DAYS, places=6)
        self.assertEqual(lives.age_text(lo, hi), "63–64")
        slo, shi = cal.age_range(b, at, "solar")
        self.assertEqual(lives.age_text(slo, shi), "61–62")
        self.assertGreater(lo, slo)                       # lunar years are shorter, so more of them

    def test_completed_years_text(self):
        self.assertEqual(lives.age_text(63.2, 63.9), "63")
        self.assertEqual(lives.age_text(63.2, 64.1), "63–64")
        self.assertEqual(lives.age_text(-0.4, 0.5), "0")


class Precision(unittest.TestCase):
    def test_a_year_is_drawn_as_the_whole_year(self):
        lo, hi = year(570)
        self.assertEqual((lo, hi), (J(570, 1, 1), J(570, 12, 31)))
        lo, hi = year(572)                                 # Julian leap year
        self.assertEqual(hi - lo + 1, 366)

    def test_month_decade_century(self):
        self.assertEqual(cal.range_for(632, 6, 1, "month"), (J(632, 6, 1), J(632, 6, 30)))
        self.assertEqual(cal.range_for(595, 1, 1, "decade"), (J(590, 1, 1), J(599, 12, 31)))
        self.assertEqual(cal.range_for(650, 1, 1, "century"), (J(601, 1, 1), J(700, 12, 31)))
        self.assertIsNone(cal.range_for(650, 1, 1, "millennium"))

    def test_wikidata_month_and_day_zero_mean_a_coarser_value(self):
        self.assertEqual(cal.parse_iso("+0570-00-00T00:00:00Z"), (570, 1, 1))


class Lives(unittest.TestCase):
    def test_no_sourced_date_no_line(self):
        self.assertIsNone(lives.life([], [year(610)]))
        self.assertIsNone(lives.life([claim("death", None, None)], [year(610)]))

    def test_needs_review_dates_only_when_switched_on(self):
        cs = [claim("birth", *year(600), review=True)]
        self.assertIsNone(lives.life(cs, []))
        self.assertIsNotNone(lives.life(cs, [], include_review=True))

    def test_sources_that_disagree_give_the_range(self):
        lf = lives.life([claim("birth", *year(570)), claim("birth", *year(571))], [])
        self.assertEqual(lf["b"], [J(570, 1, 1), J(571, 12, 31)])

    def test_unknown_ends_stay_open_and_nothing_is_guessed(self):
        lf = lives.life([claim("death", J(625, 3, 23), J(625, 3, 23), precision="day")], [year(616)])
        self.assertTrue(lf["open_start"])
        self.assertIsNone(lf["b"])
        self.assertEqual(lf["s"], year(616)[1])            # certainly alive only from the event's latest date
        self.assertNotIn("age", lf)                         # no age without a birth
        lf = lives.life([claim("birth", *year(590))], [])
        self.assertTrue(lf["open_end"])
        self.assertIsNone(lf["d"])
        self.assertEqual(lf["e"], year(590)[1])

    def test_events_outside_the_life_are_flagged_not_drawn(self):
        lf = lives.life([claim("birth", *year(570)), claim("death", *year(632))], [])
        self.assertEqual(lives.placement(lf, *year(560))["flag"], "before_birth")
        self.assertEqual(lives.placement(lf, *year(640))["flag"], "after_death")
        pl = lives.placement(lf, *year(622))
        self.assertTrue(pl["ok"])
        self.assertEqual(pl["lunar_text"], "52–54")


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from model import Site
        cls.site = Site(FX_GRAPH)
        cls.t = B.T(LL / "i18n" / "en.json")
        cls.data, cls.coll = B.build_data(cls.site, cls.t, (FX_CSV.read_text(encoding="utf-8"), FX_CSV.name),
                                          "../", {})
        cls.by_name = {p["n"]: p for p in cls.data["people"]}

    def test_no_person_drawn_without_a_sourced_date(self):
        for p in self.data["people"]:
            sourced = [c for c in p["c"] if c["lo"] is not None and c["src"]["type"] in ("graph", "wikidata", "ibn-hisham")]
            self.assertTrue(sourced, p["n"])
            if "b" in p["v"]:
                self.assertTrue([c for c in sourced if not c["rv"]], p["n"])
            for c in p["c"]:
                self.assertTrue(c["src"]["label"], p["n"])
                self.assertIn(c["src"]["status"], (None, "proposed"))

    def test_people_without_dates_are_listed_not_drawn(self):
        self.assertEqual(sorted(u["n"] for u in self.data["undated"]),
                         ["Test person Eta", "Test person Iota", "Test person Zeta"])
        why = {u["n"]: u["why"] for u in self.data["undated"]}
        self.assertEqual(why["Test person Zeta"], "ambiguous")     # two candidate items: never mixed
        self.assertEqual(why["Test person Iota"], "unplaced")      # relative date, in words only
        self.assertEqual(why["Test person Eta"], "none")

    def test_year_precision_dates_are_drawn_as_ranges(self):
        n = 0
        for p in self.data["people"]:
            for c in p["c"]:
                if c["pr"] == "year" and c["lo"] is not None:
                    self.assertGreaterEqual(c["hi"] - c["lo"], 364, p["n"])
                    n += 1
            for v in p["v"].values():
                for k in ("b", "d"):
                    if v[k]:
                        self.assertLessEqual(v[k][0], v[k][1])
        self.assertGreater(n, 3)
        beta = self.by_name["Test person Beta"]
        self.assertEqual(beta["v"]["b"]["b"], list(year(573)))            # the preferred value is drawn
        alt = [c for c in beta["c"] if c["alt"]]
        self.assertEqual([(c["k"], c["lo"]) for c in alt], [("birth", J(574, 1, 1))])   # the other is listed
        self.assertEqual(beta["v"]["b"]["d"], [J(633, 1, 1), J(634, 12, 31)])  # earliest-date qualifier widens
        delta = self.by_name["Test person Delta"]["v"]["b"]
        self.assertEqual(delta["d"], [J(650, 1, 1), J(652, 12, 31)])     # no preferred value: the range

    def test_connectors_only_at_recorded_event_dates(self):
        from rdflib import Graph, Namespace, URIRef
        mrs = Namespace("https://w3id.org/marsad/core#")
        g = Graph()
        g.parse(str(FX_GRAPH), format="turtle")
        names = []
        for e in self.data["events"]:
            node = URIRef("https://w3id.org/marsad/id/event/" + e["id"])
            recorded = [(cal.jdn_from_iso_bound(str(g.value(x, mrs.earliestStart))),
                         cal.jdn_from_iso_bound(str(g.value(x, mrs.latestEnd))))
                        for x in g.objects(node, mrs.eventTemporalExtent) if g.value(x, mrs.earliestStart) is not None]
            self.assertIn((e["lo"], e["hi"]), recorded, e["n"])
            names.append(e["n"])
        self.assertNotIn("Test undated event", names)
        self.assertNotIn("Test relative event", names)
        battle = next(e for e in self.data["events"] if e["n"] == "Test battle")
        who = {self.data["people"][ps["p"]]["n"] for ps in battle["ps"]}
        self.assertEqual(who, {"Test person Alpha", "Test person Beta", "Test person Gamma"})
        self.assertNotIn("Test person Delta", who)                        # "absent from" is not taking part
        self.assertEqual([o["n"] for o in battle["oth"]], ["Test person Eta"])

    def test_one_wikidata_item_per_person(self):
        alpha = self.by_name["Test person Alpha"]
        self.assertEqual({c["src"]["label"] for c in alpha["c"]}, {"proposed: from Wikidata Q900000001"})
        self.assertEqual(alpha["oc"], ["Q900000099"])
        eps = self.by_name["Test person Epsilon"]
        self.assertNotIn("b", eps["v"])
        self.assertIn("a", eps["v"])
        self.assertTrue(all(c["rv"] for c in eps["c"]))

    def test_calendar_models_and_coarse_precision(self):
        theta = self.by_name["Test person Theta"]
        birth = next(c for c in theta["c"] if c["k"] == "birth")
        self.assertEqual(birth["lo"], cal.jdn_from_gregorian(600, 7, 4))
        death = next(c for c in theta["c"] if c["k"] == "death")
        self.assertIsNone(death["lo"])                                    # millennium: not placed
        self.assertTrue(theta["v"]["b"]["open_end"])

    def test_ages_at_events(self):
        mig = next(e for e in self.data["events"] if e["n"] == "Test migration")
        ps = next(ps for ps in mig["ps"] if self.data["people"][ps["p"]]["n"] == "Test person Alpha")
        self.assertEqual(ps["pl"]["b"]["lunar_text"], "52–54")
        self.assertEqual(ps["pl"]["b"]["solar_text"], "51–52")
        early = next(e for e in self.data["events"] if e["n"] == "Test early event")
        self.assertEqual(early["ps"][0]["pl"]["b"]["flag"], "before_birth")
        gamma = next(ps for e in self.data["events"] for ps in e["ps"] if self.data["people"][ps["p"]]["n"] == "Test person Gamma")
        self.assertNotIn("lunar", gamma["pl"]["b"])                       # no birth, no age

    def test_grouping_data_comes_from_recorded_claims(self):
        self.assertGreaterEqual(self.by_name["Test person Alpha"]["kin"], 0)
        self.assertEqual(self.by_name["Test person Alpha"]["kin"], self.by_name["Test person Beta"]["kin"])
        self.assertEqual(self.by_name["Test person Theta"]["tr"], ["Test tribe"])
        self.assertEqual(self.by_name["Test person Alpha"]["tb"], "ṣaḥābī")

    def test_page_is_self_contained_and_deterministic(self):
        page = B.render(self.data, self.t, home="../")
        again = B.render(B.build_data(self.site, self.t, (FX_CSV.read_text(encoding="utf-8"), FX_CSV.name), "../", {})[0],
                         self.t, home="../")
        self.assertEqual(page, again)
        self.assertLess(len(page.encode("utf-8")), B.MAX_BYTES)
        self.assertIsNone(re.search(r"<(script|link|img|iframe)[^>]+(src|href)=[\"']?https?:", page))
        self.assertIsNone(re.search(r"@import|url\(\s*[\"']?https?:", page))
        self.assertIn(self.t("banner.strong"), page)
        self.assertIn('class="ll-table"', page)
        data = json.loads(page.split('id="ll-data">')[1].split("</script>")[0])
        self.assertEqual(len(data["people"]), len(self.data["people"]))

    def test_page_passes_the_sites_html_check(self):
        import check_html
        data = B.build_data(self.site, self.t, (FX_CSV.read_text(encoding="utf-8"), FX_CSV.name), None, {})[0]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "lifelines").mkdir()
            page = root / "lifelines" / "index.html"
            page.write_text(B.render(data, self.t, home=None), encoding="utf-8")
            self.assertEqual(check_html.check_page(root, page, check_html.collect_ids(root)), [])

    def test_output_next_to_the_site_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "dist" / "lifelines"
            rc = B.main(["--graph", str(FX_GRAPH), "--external-dates", str(FX_CSV), "--out", str(out)])
            self.assertEqual(rc, 0)
            self.assertTrue((out / "index.html").exists())
            self.assertTrue((out.parent / B.SITE_MARKER).exists())       # site/build.py may replace it later


class IbnHisham(unittest.TestCase):
    """Claims shaped like slice 4's, from a fictional fixture merged into the fixture graph."""

    @classmethod
    def setUpClass(cls):
        from model import Site
        cls.tmp = tempfile.TemporaryDirectory()
        renames = {"per:TestOldAlphaId00000000x": "per:TestAlpha00000000000a"}
        merged, cls.reader_iris = B.merge_graph(FX_GRAPH, (HERE / "fixtures" / "ibn-hisham.ttl").read_text(encoding="utf-8"),
                                                renames, Path(cls.tmp.name) / "merged.ttl")
        cls.site = Site(merged)
        cls.t = B.T(LL / "i18n" / "en.json")
        cls.data = B.build_data(cls.site, cls.t, (FX_CSV.read_text(encoding="utf-8"), FX_CSV.name), "../", renames,
                                ibn_hisham="ibn-hisham.ttl", reader_iris=cls.reader_iris)[0]
        cls.P = {p["n"]: p for p in cls.data["people"]}
        cls.E = {e["n"]: e for e in cls.data["events"]}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def links(self, event, person):
        return [ps for ps in self.E[event]["ps"] if self.data["people"][ps["p"]]["n"] == person]

    def test_ages_as_given_are_kept_as_given_and_never_merged(self):
        ps = [x for x in self.links("Test battle", "Test person Gamma") if x["kd"] == "age"][0]
        self.assertEqual(ps["ag"], [40.0])
        self.assertIn("as given", ps["how"])
        self.assertNotIn("lunar years", ps["how"])                       # no unit is claimed for it
        alpha = [x for x in self.links("Birth of Test person Beta", "Test person Alpha") if x["kd"] == "age"][0]
        self.assertEqual(alpha["ag"], [7.0, 8.0])                       # both alternatives, as given
        self.assertEqual(alpha["aw"], "سبع أو ثمان")
        self.assertEqual(alpha["pl"]["b"]["lunar_text"], "2–4")          # computed separately (years 570, 573), beside it

    def test_renamed_ids_are_mapped(self):
        self.assertTrue(self.links("Birth of Test person Beta", "Test person Alpha"))

    def test_a_birth_event_takes_that_persons_recorded_birth(self):
        ev = self.E["Birth of Test person Beta"]
        self.assertEqual((ev["lo"], ev["hi"]), year(573))
        self.assertTrue(any("Test person Beta" in n for n in ev["nt"]))

    def test_died_during_a_dated_event_places_the_death(self):
        kappa = self.P["Test person Kappa"]
        death = [c for c in kappa["c"] if c["k"] == "death"][0]
        self.assertEqual((death["lo"], death["hi"]), (J(624, 3, 13), J(624, 3, 13)))
        self.assertEqual(death["src"]["type"], "ibn-hisham")
        self.assertEqual(death["src"]["status"], "proposed")
        self.assertIsNone(kappa["u"])                                     # no reader page in the main graph yet

    def test_born_during_an_undated_event_is_listed_not_drawn(self):
        self.assertIn("Test person Lambda", {u["n"]: u for u in self.data["undated"]})

    def test_ages_only_lines_stop_at_the_last_age_given(self):
        mu = self.P["Test person Mu"]["v"]["b"]
        self.assertTrue(mu["ages_only"])
        self.assertEqual(mu["amax"], 30.0)
        self.assertIsNone(mu["b"])
        gamma = self.P["Test person Gamma"]["v"]["b"]                     # a death date but no birth
        self.assertEqual(gamma["gmax"], 40.0)
        self.assertIn("Test undated gathering", self.E)                   # undated: shown by age only
        self.assertIsNone(self.E["Test undated gathering"]["lo"])

    def test_dates_as_written_are_shown_in_words(self):
        self.assertTrue(any("يوم الاختبار" in n for n in self.E["Test battle"]["nt"]))


class Repo(unittest.TestCase):
    SOURCES = sorted(p for p in LL.rglob("*") if p.suffix in (".py", ".js", ".cjs", ".css", ".json")
                     and "fixtures" not in p.parts)

    def test_no_entity_id_is_hard_coded(self):
        text = "".join(p.read_text(encoding="utf-8") for p in self.SOURCES)
        self.assertIsNone(re.search(r"\b(per|ev|grp|plc|act|agt):[0-9A-Za-z]{22}\b", text))
        ids = csv.DictReader((ROOT / "ontology" / "corpus" / "identity.csv").open(encoding="utf-8"))
        leaked = [r["canonical_id"] for r in ids if r["canonical_id"].split(":", 1)[-1] in text]
        self.assertEqual(leaked, [])
        if GRAPH.exists():
            from model import Site
            site = Site(GRAPH)
            self.assertEqual([e.pid for e in site.entities.values() if e.pid in text], [])

    def test_every_string_used_by_the_script_exists(self):
        js = (LL / "lifelines.js").read_text(encoding="utf-8")
        en = json.loads((LL / "i18n" / "en.json").read_text(encoding="utf-8"))
        keys = set(re.findall(r"\bt\(\"([a-z0-9_.]+)\"", js))
        self.assertTrue(keys)
        for k in keys:
            self.assertIn(k.split(".")[0], B.JS_PREFIXES, k)
            if k.endswith("."):          # a key completed at run time: some key must have the prefix
                self.assertTrue([x for x in en if x.startswith(k)], k)
            else:
                self.assertIn(k, en, k)

    def test_css_uses_logical_properties_only(self):
        css = (LL / "lifelines.css").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\b(left|right)\b", css))
        self.assertIn("color-scheme: dark", css)


if __name__ == "__main__":
    unittest.main()
