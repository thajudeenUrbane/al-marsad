"""Tests for ask/: the rules of the brief, the normaliser, the DSL, the translator and the
build. The golden set is in test_golden.py, Python/JS parity in test_parity.py.

Run:  .venv/bin/python -m unittest discover -s ask/tests
Integration tests need build/graph.ttl (ontology/build_graph.py) and are skipped without it.
"""
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from common import ASK, GRAPH, ROOT, engine, golden, have_graph, i18n

from ask import dsl, normalise, translate
from ask.dsl import DslError, Engine, parse, year_bounds
from ask.normalise import RULES, name_tokens, score, text_key

EN = json.loads((ASK / "i18n" / "en.json").read_text(encoding="utf-8"))
PY = [ASK / n for n in ("normalise.py", "index.py", "dsl.py", "translate.py", "present.py", "build_ask.py")]
JS = ASK / "static" / "ask.js"
TEMPLATES = sorted((ASK / "templates").glob("*.html"))
KEY = re.compile(r"""["']([a-z_]+(?:\.[a-z0-9_]+)+)["']""")


def used_keys() -> set:
    """i18n keys named in the code and templates, plus the families built at run time."""
    found = set()
    namespaces = {k.split(".")[0] for k in EN}
    for path in PY + [JS]:
        for k in KEY.findall(path.read_text(encoding="utf-8")):
            if k.split(".")[0] in namespaces and not k.endswith("_") and not re.search(r"\.(html|json|css|js|py)$", k):
                found.add(k)
    for path in TEMPLATES:
        found |= set(re.findall(r"\[\[([a-z0-9_.]+)\]\]", path.read_text(encoding="utf-8")))
    for r in RULES["refusals"]:
        found |= {f"refusal.{r['class']}.reason", f"refusal.{r['class']}.offer", f"refusal.limit.{r['class']}"}
    for s in RULES["shapes"]:
        if s.get("note"):
            found.add(f"note.{s['note']}")
    for reason in ("generic", "time_needs_place", "time_era", "time_bh", "reviewed_needs_list"):
        found.add(f"unsupported.{reason}")
    for st in ("proposed", "under_review", "accepted", "rejected", "superseded", "none"):
        found.add(f"status.{st}")
    found |= {f"kind.{k}" for k in dsl.KINDS}
    found |= {f"want.{w}" for w in list(dsl.REF_KINDS) + ["target", "set", "year"]}
    found |= {f"plain.relatives_{t}" for t in dsl.TIES} | {f"plain.connected_{v}" for v in ("any", "ties", "events")}
    found |= {f"plain.{op}" for op in ("both", "either", "except")}
    found |= {f"answer.lead.{of}" for of in dsl.SET_TYPES}
    found |= {f"about.{c}" for c in ("stories", "events", "places", "groups", "kinship", "people")}
    found |= {f"claim.{p}" for p in ("took_part", "took_place_at", "part_of")}
    found |= {f"page.group.{g}" for g in ("presence", "family", "events", "links", "stories", "other", "refusal")}
    return found


def has_key(k: str, keys: set) -> bool:
    return k in keys or f"{k}.one" in keys


def stem(k: str) -> str:
    return k[: -len(".one")] if k.endswith(".one") else k[: -len(".other")] if k.endswith(".other") else k


def words_outside_markup(s: str) -> list:
    """Words left in an HTML-building string once tags, entities and placeholders are gone.
    A string may hold the start or the end of a tag that another string completes."""
    s = re.sub(r"<[^<>]*>", " ", s)
    s = re.sub(r"^[^<>]*>", " ", s)
    s = re.sub(r"<[^<>]*$", " ", s)
    s = re.sub(r"\{[^}]*\}|&\w+;|\$\{?\w+\}?", " ", s)
    return re.findall(r"[A-Za-z]{2,}", s)


class StaticChecks(unittest.TestCase):
    def test_every_used_i18n_key_exists(self):
        keys = set(EN)
        self.assertEqual(sorted(k for k in used_keys() if not has_key(k, keys)), [])

    def test_no_unused_i18n_keys(self):
        used = used_keys()
        self.assertEqual([k for k in EN if k not in used and stem(k) not in used], [])

    def test_templates_have_no_literal_text(self):
        for path in TEMPLATES:
            src = re.sub(r"\[\[[a-z0-9_.]+\]\]", "", path.read_text(encoding="utf-8"))
            src = re.sub(r"\$\{?\w+\}?", "", src)
            src = re.sub(r"<[^>]+>", "", src)
            self.assertEqual(src.strip(), "", path.name)

    def test_html_built_in_python_has_no_hard_coded_words(self):
        bad = []
        for path in (ASK / "present.py", ASK / "build_ask.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            docs = {id(n.body[0].value) for n in ast.walk(tree)
                    if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body
                    and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
            for node in ast.walk(tree):
                if id(node) in docs:
                    continue
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and "<" in node.value:
                    w = words_outside_markup(node.value)
                    if w:
                        bad.append((path.name, node.lineno, node.value[:60], w))
        self.assertEqual(bad, [])

    def test_html_built_in_js_has_no_hard_coded_words(self):
        src = JS.read_text(encoding="utf-8")
        bad = []
        for m in re.finditer(r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'', src):
            lit = m.group(0)[1:-1]
            if "<" in lit:
                w = words_outside_markup(lit)
                if w:
                    bad.append((lit[:60], w))
        self.assertEqual(bad, [])

    def test_css_uses_logical_properties_only(self):
        css = re.sub(r"/\*.*?\*/", "", (ASK / "static" / "ask.css").read_text(encoding="utf-8"), flags=re.S)
        self.assertEqual(re.findall(r"[^\n]*\b(?:left|right)\b[^\n]*", css, flags=re.I), [])

    def test_rules_use_only_portable_regex(self):
        """Python and JavaScript read the same patterns; keep to what both treat alike."""
        pats = [p for r in RULES["refusals"] for p in r["patterns"] + ([r["unless"]] if r.get("unless") else [])]
        pats += [p for s in RULES["shapes"] for p in s["patterns"]] + RULES["status_suffix"]
        pats += [RULES["time"][k] for k in ("range", "single", "single_bare")]
        pats += [RULES["normalise"][k] for k in ("spaces", "honorific_paren", "possessive")]
        for p in pats:
            with self.subTest(p[:50]):
                re.compile(p)
                for bad in ("\\b", "\\w", "\\W", "\\B", "(?P<", "(?<=", "(?<!", "\\Z", "\\A"):
                    self.assertNotIn(bad, p)

    def test_site_normaliser_is_imported_not_copied(self):
        import display
        import names
        self.assertIs(normalise.fold, display.fold)
        self.assertIs(normalise.names, names)
        src = (ASK / "normalise.py").read_text(encoding="utf-8")
        for fn in ("def fold", "def normalise", "def skeleton"):
            self.assertNotIn(fn, src)

    @unittest.skipUnless(have_graph(), "build/graph.ttl missing")
    def test_no_entity_id_is_hard_coded(self):
        pids = [e["r"].split("/", 1)[1] for e in engine().E]
        files = [p for p in ASK.rglob("*") if p.is_file() and p.suffix in (".py", ".js", ".cjs", ".json", ".jsonl", ".md", ".html", ".css")]
        leaked = [(p.name, pid) for p in files for pid in pids if pid in p.read_text(encoding="utf-8")]
        self.assertEqual(leaked, [])


class Normaliser(unittest.TestCase):
    def same(self, *names):
        keys = {tuple(name_tokens(n)) for n in names}
        self.assertEqual(len(keys), 1, {n: name_tokens(n) for n in names})

    def test_spellings_that_give_the_same_key(self):
        self.same("Abū Bakr", "Abu Bakr", "abu  bakr", "ABU BAKR", "Abu Bakr (RA)")
        self.same("ʿAbd Allāh", "Abdullah", "Abdallah", "Abd Allah")
        self.same("ʿUthmān", "Uthman")
        self.same("أُحُد", "احد")
        self.same("Ibn Hisham", "b. Hisham", "bin Hisham")
        self.same("al-Madīna", "Madina")

    def test_spellings_that_meet_by_sound_or_one_letter(self):
        k = name_tokens
        for a, b in (("Hudaybiyah", "al-Ḥudaybiyya"), ("Medina", "al-Madīna"), ("Usman", "ʿUthmān"),
                     ("Othman", "ʿUthmān"), ("Bedr", "Badr"), ("Ohud", "Uḥud")):
            with self.subTest(a):
                self.assertEqual(score(k(a), k(b)), 5)
        self.assertEqual(score(k("Mecca"), k("Makkah")), 3)
        self.assertEqual(score(k("Ayesha"), k("ʿĀʾisha bint Abī Bakr")), 3)

    def test_the_key_is_the_sites_search_form(self):
        import names
        self.assertEqual(" ".join(name_tokens("Abū Bakr al-Ṣiddīq")), names.normalise("Abū Bakr al-Ṣiddīq"))

    def test_text_key_folds_and_drops_signs(self):
        self.assertEqual(text_key("Who was at Badr ﷺ (pbuh)?"), "who was at badr ?")
        self.assertEqual(text_key("  ʿAlī b. Abī Ṭālib "), "'ali b. abi talib")

    def test_score_levels(self):
        k = name_tokens
        self.assertEqual(score(k("Abu Bakr al-Siddiq"), k("Abū Bakr al-Ṣiddīq")), 6)
        self.assertEqual(score(k("Hudaybiyah"), k("al-Ḥudaybiyya")), 5)
        self.assertEqual(score(k("Umar"), k("ʿUmar b. al-Khaṭṭāb")), 4)
        self.assertEqual(score(k("Belal"), k("Bilāl b. Rabāḥ")), 3)
        self.assertEqual(score(k("Khattab"), k("ʿUmar b. al-Khaṭṭāb")), 2)
        self.assertEqual(score(k("abubakr"), k("Abū Bakr")), 2)
        self.assertEqual(score(k("uhud battle"), k("Battle of Uḥud")), 1)
        self.assertEqual(score(k("Siffin"), k("Badr")), 0)


class Calendar(unittest.TestCase):
    def test_year_bounds(self):
        self.assertEqual(year_bounds(1, "ah"), ("0622-07-16", "0623-07-04"))
        self.assertEqual(year_bounds(2, "ah"), ("0623-07-05", "0624-06-23"))
        self.assertEqual(year_bounds(6, "ah")[0], "0627-05-23")
        self.assertEqual(year_bounds(624, "ce"), ("0624-01-01", "0624-12-31"))

    @unittest.skipUnless(have_graph(), "build/graph.ttl missing")
    def test_agrees_with_the_graphs_own_conversions(self):
        """Every Hijri date the graph converted to day precision lies inside the AH year
        these bounds give for it (within the graph's stated one day)."""
        def jdn(iso):
            y, m, d = (int(x) for x in iso[:10].split("-"))
            a = (14 - m) // 12
            yy, mm = y + 4800 - a, m + 12 * a - 3
            return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - 32083
        checked = 0
        for e in engine().E:
            for d in e.get("dates", []) + e.get("death", []):
                m = re.search(r"(\d+) AH", d["t"] or "")
                if not m or not d["s"] or d["s"] != d["e"]:
                    continue
                s, end = year_bounds(int(m.group(1)), "ah")
                self.assertTrue(jdn(s) - 1 <= jdn(d["s"]) <= jdn(end) + 1, (e["l"], d))
                checked += 1
        self.assertGreater(checked, 2)


@unittest.skipUnless(have_graph(), "build/graph.ttl missing")
class Dsl(unittest.TestCase):
    def setUp(self):
        self.eng, self.T = engine(), i18n()

    def err(self, text):
        with self.assertRaises(DslError) as cm:
            self.eng.validate(parse(text))
        return cm.exception.key

    def test_golden_queries_are_canonical(self):
        for c in golden():
            if "dsl" in c["expect"]:
                with self.subTest(c["id"]):
                    self.assertEqual(self.eng.text(self.eng.validate(parse(c["expect"]["dsl"]))), c["expect"]["dsl"])

    def test_malformed_queries_fail_loudly(self):
        cases = {
            "foo(x)": "error.unknown_op",
            'participants(person "Abū Bakr al-Ṣiddīq")': "error.type",
            'participants(event "No Such Battle")': "error.not_found",
            'about(place "Route waypoint (unidentified)")': "error.ambiguous",
            'events(at: place "Makkah", from: 5 AH, to: 1 AH)': "error.range",
            "events(from: 0 AH, to: 1 AH)": "error.year",
            'path(person "Bilāl b. Rabāḥ", person "Bilāl b. Rabāḥ")': "error.same",
            'path(person "Bilāl b. Rabāḥ", person "Abū Bakr al-Ṣiddīq", max: 9)': "error.steps",
            'both(events(at: place "Makkah"), people(at: place "Badr"))': "error.mixed",
            'participants(as: leader, event "Battle of Badr")': "error.positional",
            'participants(event "Battle of Badr"': "error.expected",
            'participants(event "Battle of Badr)': "error.unterminated",
            "events()": "error.filter",
            'relatives(person "Abū Bakr al-Ṣiddīq", tie: cousin)': "error.word",
            "about(place #NOPE)": "error.no_id",
            "count(" * 8 + 'people(at: place "Badr")' + ")" * 8: "error.too_deep",
            'people(from: 1 AH)': "error.missing",
            'participants(event "Battle of Badr", colour: red)': "error.keyword",
        }
        for text, key in cases.items():
            with self.subTest(text[:40]):
                self.assertEqual(self.err(text), key)

    def test_rows_carry_the_claims_behind_them(self):
        from ask.translate import answer
        C = self.eng.C
        for c in golden():
            a = answer(c["question"], self.eng, self.T)
            res = a.get("result") or {}
            rows = (res.get("set") or res).get("rows", []) if res else []
            for r in rows:
                with self.subTest(c["id"], row=self.eng.E[r["e"]]["l"]):
                    if res.get("type") == "set" and res.get("of") == "events" and not r["c"]:
                        continue  # a time-only events query: the evidence is the recorded date
                    self.assertTrue(r["c"])
                    self.assertTrue(any(r["e"] in (C[j]["s"], C[j]["o"]) for j in r["c"]))

    def test_no_status_is_upgraded(self):
        """Every claim's status in the index is the one the graph records (all proposed
        today); links and participations carry none."""
        from rdflib import Graph, Namespace, URIRef
        MRS = Namespace("https://w3id.org/marsad/core#")
        g = Graph().parse(GRAPH, format="turtle")
        base = "https://w3id.org/marsad/id/"
        for c in self.eng.C:
            if c["k"] == "a":
                st = g.value(URIRef(base + c["id"]), MRS.assertionStatus)
                self.assertEqual(c.get("st"), str(st).split("#")[-1].removeprefix("as_"), c["id"])
            else:
                self.assertNotIn("st", c)

    def test_proposed_claims_are_never_shown_as_fact(self):
        from ask.present import Presenter
        from ask.translate import answer
        self.assertIn("not yet reviewed", self.T["status.proposed"])
        label = self.T["status.label"].format(value=self.T["status.proposed"])
        p = Presenter(self.eng, self.T, "../")
        for c in golden():
            html = p.render(answer(c["question"], self.eng, self.T))
            for span in re.findall(r'<span class="status status-proposed">(.*?)</span>', html):
                self.assertEqual(span, label)
            if 'class="claim' in html:
                self.assertIn('class="status', html)

    def test_unlinked_or_unknown_names_are_reported_not_guessed(self):
        from ask.translate import answer
        a = answer("Who was at Siffin?", self.eng, self.T)
        self.assertEqual(a["outcome"], "not_found")
        a = answer("Relatives of Zayd", self.eng, self.T)
        self.assertEqual(a["outcome"], "ambiguous")
        self.assertEqual(len(a["options"]), 2)


@unittest.skipUnless(have_graph(), "build/graph.ttl missing")
class Translator(unittest.TestCase):
    def setUp(self):
        self.eng, self.T = engine(), i18n()

    def test_refusals_and_what_must_not_be_refused(self):
        refuse = {
            "Is music halal?": "ruling", "Should women pray at home?": "ruling", "Give me a fatwa on fasting": "ruling",
            "Explain the verse of the cave": "interpretation", "Is this narration weak?": "grading",
            "Compose a sermon about Badr": "fabrication", "Paint Bilal": "depiction",
            "Who was more pious, Umar or Uthman?": "ranking", "Rank the caliphs by virtue": "ranking",
            "Guess who else was in the cave": "speculation", "Is Abu Talib in hell?": "judgement",
        }
        for q, cls in refuse.items():
            with self.subTest(q):
                self.assertEqual(translate.classify_refusal(translate.strip_trailing(text_key(q))), cls)
        keep = ["Who was at Badr?", "Can you tell me who was at Badr?", "Who led the army at Uhud?",
                "Who fought the Ridda wars?", "Which stories mention Abu Bakr?", "Draw a map of the Hijra route",
                "Who was the father of Aisha?", "How many people were at Uhud?", "What happened at Makkah?",
                "Who was in the story of Anas ibn al-Nadr: I Smell Paradise?"]
        for q in keep:
            with self.subTest(q):
                self.assertIsNone(translate.classify_refusal(translate.strip_trailing(text_key(q))))

    def test_refusal_runs_before_any_translator(self):
        calls = []

        class Spy:
            name = "spy"

            def translate(self, q):
                calls.append(q)
                return None
        a = translate.answer("What is the ruling on music?", self.eng, self.T, [Spy()])
        self.assertEqual(a["outcome"], "refusal")
        self.assertEqual(calls, [])

    def test_a_later_translator_plugs_in_and_is_validated(self):
        class Broken:
            name = "broken"

            def translate(self, q):
                return {"outcome": "query", "dsl": "nonsense(", "notes": [], "alts": []}

        class Fixed:
            name = "fixed"

            def translate(self, q):
                return {"outcome": "query", "dsl": 'people(at: place "Badr")', "notes": [], "alts": []}
        rules = translate.RuleTranslator(self.eng)
        a = translate.answer("Relatives of Abu Bakr", self.eng, self.T, [Broken(), rules])
        self.assertEqual(a["dsl"], 'relatives(person "Abū Bakr al-Ṣiddīq")')
        a = translate.answer("anything at all", self.eng, self.T, [Fixed()])
        self.assertEqual(a["outcome"], "answer")
        self.assertEqual(a["dsl"], 'people(at: place "Badr")')
        with self.assertRaises(NotImplementedError):
            translate.ModelTranslator().translate("Who was at Badr?")

    def test_time_windows(self):
        a = translate.answer("What happened in Makkah between 1 and 8 AH?", self.eng, self.T)
        self.assertEqual(a["dsl"], 'events(at: place "Makkah", from: 1 AH, to: 8 AH)')
        a = translate.answer("events between 1 and 5", self.eng, self.T)
        self.assertEqual(a["dsl"], "events(from: 1 AH, to: 5 AH)")
        self.assertIn({"key": "note.time_assumed_ah"}, a["notes"])
        a = translate.answer("Who was at the Battle of Badr in 2 AH?", self.eng, self.T)
        self.assertEqual((a["outcome"], a["reason"]), ("unsupported", "time_needs_place"))
        a = translate.answer("What happened between 13 BH and 1 AH?", self.eng, self.T)
        self.assertEqual((a["outcome"], a["reason"]), ("unsupported", "time_bh"))

    def test_same_question_same_answer(self):
        a = translate.answer("Who met both Abu Bakr and Umar?", self.eng, self.T)
        b = translate.answer("Who met both Abu Bakr and Umar?", Engine(self.eng.ix), self.T)
        self.assertEqual(a, b)


@unittest.skipUnless(have_graph(), "build/graph.ttl missing")
class Build(unittest.TestCase):
    """site/build.py into a temporary folder, then ask/build_ask.py on top of it."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "dist"
        for script, extra in (("site/build.py", ["--out", str(cls.out)]), ("ask/build_ask.py", ["--site", str(cls.out)])):
            subprocess.run([sys.executable, str(ROOT / script), "--graph", str(GRAPH)] + extra,
                           check=True, capture_output=True, cwd=ROOT)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_files_and_budget(self):
        ask = self.out / "ask"
        for name in ("index.html", "ask.js", "ask.css", "ask-index.json.gz"):
            self.assertTrue((ask / name).is_file(), name)
        total = sum(p.stat().st_size for p in ask.rglob("*") if p.is_file())
        self.assertLessEqual(total, 2_000_000)
        cached = [g for g in golden() if g.get("cache")]
        self.assertEqual(len(list((ask / "q").glob("*/index.html"))), len(cached))
        import gzip
        data = json.loads(gzip.decompress((ask / "ask-index.json.gz").read_bytes()).decode("utf-8"))
        self.assertTrue({"entities", "claims", "rules", "i18n", "version"} <= set(data))
        html = (ask / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-fetch="ask-index.json.gz"', html)  # so site/check_budget.py counts it

    def test_site_checks_pass_with_the_ask_pages(self):
        sys.path.insert(0, str(ROOT / "site"))
        import check_budget
        import check_html
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(check_html.main([str(self.out)]), 0)
            self.assertEqual(check_budget.main([str(self.out)]), 0)

    def test_page_without_javascript(self):
        html = (self.out / "ask" / "index.html").read_text(encoding="utf-8")
        self.assertRegex(html, r'<form id="ask-form"[^>]* hidden')
        self.assertIn('id="ask-nojs"', html)
        self.assertIn('<script src="ask.js" defer></script>', html)
        self.assertNotIn("ask-index.json", html.split("<form", 1)[0])  # never preloaded
        self.assertIsNone(re.search(r'(?:src|href)="(?:https?:)?//[^"]*\.(?:js|css|json)"', html))

    def test_build_is_deterministic(self):
        outs = []
        with tempfile.TemporaryDirectory() as d:
            for seed in ("1", "2"):
                site = Path(d) / seed
                env = {**os.environ, "PYTHONHASHSEED": seed}
                subprocess.run([sys.executable, str(ROOT / "site/build.py"), "--graph", str(GRAPH), "--out", str(site)],
                               check=True, capture_output=True, cwd=ROOT, env=env)
                subprocess.run([sys.executable, str(ROOT / "ask/build_ask.py"), "--graph", str(GRAPH), "--site", str(site)],
                               check=True, capture_output=True, cwd=ROOT, env=env)
                outs.append({p.relative_to(site / "ask").as_posix(): p.read_bytes() for p in (site / "ask").rglob("*") if p.is_file()})
        self.assertEqual(sorted(outs[0]), sorted(outs[1]))
        self.assertEqual([k for k in outs[0] if outs[0][k] != outs[1][k]], [])


if __name__ == "__main__":
    unittest.main()
