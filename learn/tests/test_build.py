"""The learn pages: built output, budgets, i18n, logical CSS, JS-free reading.

The built-site tests need build/graph.ttl (run ontology/build_graph.py first) and are
skipped without it. The practice rendering test uses a made-up fixture graph.
Run:  .venv/bin/python -m unittest discover -s learn/tests -v
"""
import ast
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

LEARN = Path(__file__).resolve().parents[1]
ROOT = LEARN.parent
SITE = ROOT / "site"
sys.path.insert(0, str(SITE))
sys.path.insert(0, str(LEARN))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import build as site_build  # noqa: E402
import build_learn  # noqa: E402
import check_budget  # noqa: E402
import check_html  # noqa: E402
import golden  # noqa: E402
import journeys as J  # noqa: E402
import practice  # noqa: E402
import render_learn  # noqa: E402
from fixtures import Fx, people_spec, side_fixture  # noqa: E402
from model import Site  # noqa: E402

GRAPH = ROOT / "build" / "graph.ttl"
EN = json.loads((LEARN / "i18n" / "en.json").read_text(encoding="utf-8"))
SITE_EN = json.loads((SITE / "i18n" / "en.json").read_text(encoding="utf-8"))
PY_FILES = sorted(LEARN.glob("*.py"))
KEY = re.compile(r"^[a-z_]+(\.[a-z0-9_]+)+$")


def quiet(fn, *args, **kw):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*args, **kw)


def family_keys() -> set:
    """Keys the code builds from parts, listed here so that none can go missing or stale."""
    keys = set()
    for k in ("named", "part_of", "has_part", "date_after", "date_before", "date_related", "dated_after_this",
              "dated_before_this", "dated_related_this", "event_claim"):
        keys.add(f"learn.why.{k}")
    keys |= {f"learn.order_note.{k}" for k in ("part", "recorded", "unrecorded")}
    keys |= {f"learn.order.{o}" for orders in J.ORDERS.values() for o in orders}
    keys |= {f"learn.follow.{f}" for f in J.FOLLOW}
    keys |= {f"learn.list.{n}_{w}" for n in ("two", "many") for w in ("or", "and")}
    keys |= {"learn.kinds.event", "learn.kinds.story", "learn.kinds.event_story"}
    keys |= {f"learn.legend.{t}" for t in J.STEP_TYPES}
    keys |= {f"learn.door.{d}" for d in J.DOORS}
    keys |= {f"learn.state.{s}" for s in ("draft", "approved")}
    for t in practice.QUESTION_TYPES:
        for p in practice.PARTICIPATION:
            keys.add(f"learn.q.{t}.{practice.local(p)}")
    plural = ["learn.scale.events", "learn.scale.people", "learn.scale.stories", "learn.scale.apart",
              "learn.claims.assertions", "learn.claims.links", "learn.claims.show", "learn.records.heading",
              "learn.contrary.heading", "learn.named.summary", "learn.named.show", "learn.index.steps",
              "learn.index.practice_count", "learn.rule.events_follow", "learn.rule.people_follow"]
    for k in plural:
        keys |= {f"{k}.one", f"{k}.other"}
    for path in sorted((LEARN / "journeys").glob("*.json")):
        spec = json.loads(path.read_text(encoding="utf-8"))
        keys |= {spec[k] for k in ("title", "lead", "lead_study") if k in spec}
    return keys


def literal_keys() -> set:
    found = set()
    namespaces = {k.split(".")[0] for k in list(EN) + list(SITE_EN)}
    for path in PY_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        inner = {id(v) for n in ast.walk(tree) if isinstance(n, ast.JoinedStr) for v in n.values}
        for node in ast.walk(tree):
            if id(node) in inner:
                continue  # a fragment of an f-string builds a key family, listed in family_keys()
            if (isinstance(node, ast.Constant) and isinstance(node.value, str) and KEY.match(node.value)
                    and node.value.split(".")[0] in namespaces
                    and not re.search(r"\.(json|html|css|py|ttl|cjs|js)$", node.value)):
                found.add(node.value)
    for path in (LEARN / "templates").glob("*.html"):
        found |= set(re.findall(r"\[\[([a-z0-9_.]+)\]\]", path.read_text(encoding="utf-8")))
    return found


class StaticChecks(unittest.TestCase):
    def test_every_key_used_exists(self):
        missing = [k for k in sorted(literal_keys() | family_keys()) if k not in EN and k not in SITE_EN
                   and f"{k}.one" not in EN]
        self.assertEqual(missing, [])

    def test_no_unused_learn_keys(self):
        used = literal_keys() | family_keys()
        unused = [k for k in EN if k not in used and not any(k.startswith(u + ".") for u in used)]
        self.assertEqual(unused, [])

    def test_learn_keys_do_not_shadow_site_keys(self):
        self.assertEqual(sorted(set(EN) & set(SITE_EN)), [])

    def test_templates_contain_no_hard_coded_text(self):
        for path in sorted((LEARN / "templates").glob("*.html")):
            src = path.read_text(encoding="utf-8")
            src = re.sub(r"\[\[[a-z0-9_.]+\]\]", "", src)
            src = re.sub(r"\$\{?\w+\}?", "", src)
            src = re.sub(r"<[^>]+>", "", src)
            self.assertEqual(src.strip(), "", f"{path.name} has literal text outside i18n keys")

    def test_html_built_in_python_has_no_hard_coded_words(self):
        bad = []
        for path in PY_FILES:
            tree = ast.parse(path.read_text(encoding="utf-8"))

            def flatten(node):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    return node.value
                if isinstance(node, ast.JoinedStr):
                    return "".join(v.value if isinstance(v, ast.Constant) else "{}" for v in node.values)
                return None

            inner = {id(v) for n in ast.walk(tree) if isinstance(n, ast.JoinedStr) for v in n.values}
            for node in ast.walk(tree):
                if id(node) in inner:
                    continue
                if isinstance(node, ast.JoinedStr) or (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                    s = flatten(node)
                    if not s or "<" not in s:
                        continue
                    text = re.sub(r"<[^>]+>", " ", s)
                    text = re.sub(r"\{[^}]*\}|&\w+;", " ", text)
                    words = re.findall(r"[A-Za-z]{2,}", text)
                    if words:
                        bad.append((path.name, node.lineno, words))
        self.assertEqual(bad, [])

    def test_css_uses_logical_properties_only(self):
        css = re.sub(r"/\*.*?\*/", "", (LEARN / "static" / "learn.css").read_text(encoding="utf-8"), flags=re.S)
        self.assertEqual(re.findall(r"[^\n]*\b(?:left|right)\b[^\n]*", css, flags=re.I), [])

    def test_script_holds_no_interface_text_and_guards_storage(self):
        js = (LEARN / "static" / "learn.js").read_text(encoding="utf-8")
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
        literals = re.findall(r'"((?:[^"\\]|\\.)*)"', code)
        phrases = [s for s in literals if re.search(r"[A-Za-z]+\s+[A-Za-z]+", s) and s != "use strict"]
        self.assertEqual(phrases, [])
        self.assertIn("try", code)
        for call in re.findall(r"\b\w+\.(?:getItem|setItem|removeItem)\(", code):
            self.assertTrue(call)
        # every storage call sits inside a function whose body is wrapped in try/catch
        for fn in ("storage", "load", "save"):
            body = re.search(r"function " + fn + r"\([^)]*\) \{(.*?)\n  \}", code, flags=re.S).group(1)
            self.assertIn("try {", body)
            self.assertIn("catch (e)", body)
        self.assertNotIn("localStorage", code.replace("window.localStorage", ""))

    def test_progress_markup_is_hidden_until_the_script_runs(self):
        src = (LEARN / "templates" / "progress.html").read_text(encoding="utf-8")
        self.assertRegex(src, r"<div class=\"learn-progress\"[^>]* hidden>")
        self.assertIn("<template id=\"learn-step-done\">", src)


class GoldenRecipe(unittest.TestCase):
    """golden.held_page takes out exactly the additions a held Study page may carry
    (design §3.7 and §8), so the E1 hash recorded on the v1 page still applies to it."""

    V1 = ('<article class="journey door-study" data-journey="x">\n<header class="journey-head">\n<h1>T</h1>\n'
          '</header>\n<nav class="breadcrumb"><ol><li><a href="../../">H</a></li></ol></nav>\n'
          '<ol class="journey-steps">\n<li class="step" id="step-1" data-step="p1" aria-labelledby="step-1-title">\n'
          '<h3 class="step-title" id="step-1-title"><a href="../../event/p1/">N</a></h3>\n</li>\n</ol>\n</article>')

    def held(self) -> str:
        v2 = self.V1.replace('data-journey="x">', 'data-journey="x" data-depth="study" data-total="1" data-steps="p1">')
        v2 = v2.replace('<header class="journey-head">\n',
                        '<header class="journey-head">\n<nav class="journey-depths" aria-label="D"><ul><li>'
                        '<a href="discover/#s-p1">D</a></li><li><a href="./#s-p1" aria-current="page">S</a></li>'
                        '</ul></nav>\n')
        v2 = v2.replace('aria-labelledby="step-1-title">\n', 'aria-labelledby="step-1-title">\n<span id="s-p1"></span>\n')
        return v2.replace('href="../../event/p1/"', 'href="../../../event/p1/"')

    def test_the_permitted_additions_are_neutralised(self):
        v2 = self.held()
        self.assertNotEqual(golden.page_sha(v2), golden.page_sha(self.V1))
        self.assertEqual(golden.page_sha(golden.held_page(v2)), golden.page_sha(self.V1))

    def test_a_page_without_them_is_unchanged(self):
        self.assertEqual(golden.held_page(self.V1), self.V1)

    def test_nothing_else_is_taken_out(self):
        for extra in ('<span data-id="s-p1"></span>', '<span id="s-p1">text</span>', '<p data-depth="study">x</p>',
                      '<nav class="journey-contents"><a href="#s-p1">C</a></nav>'):
            page = self.held().replace("<h1>T</h1>", "<h1>T</h1>" + extra)
            with self.subTest(extra):
                self.assertIn(extra, golden.held_page(page))


def build_into(out: Path, graph: Path = GRAPH, journeys_dir: Path | None = None) -> dict:
    quiet(site_build.build, graph, out, True)
    return quiet(build_learn.build, graph, out, True, journeys_dir)


@unittest.skipUnless(GRAPH.exists(), "build/graph.ttl missing: run ontology/build_graph.py")
class BuiltPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        cls.summary = build_into(cls.out)
        cls.learn = cls.out / "learn"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def pages(self):
        return sorted(self.learn.rglob("*.html"))

    def test_the_pages_exist(self):
        rel = sorted(p.relative_to(self.learn).as_posix() for p in self.pages())
        self.assertEqual(rel, ["first-believers/index.html", "hijrah-step-by-step/index.html", "index.html",
                               "people-of-badr/index.html", "practice/index.html"])
        self.assertEqual(json.loads((self.learn / "practice" / "bank.json").read_text(encoding="utf-8")),
                         {"questions": []})

    def test_the_site_checks_pass_with_the_learn_pages_in_place(self):
        self.assertEqual(quiet(check_html.main, [str(self.out)]), 0)
        self.assertEqual(quiet(check_budget.main, [str(self.out)]), 0)
        results, problems = check_budget.check(self.out)
        learn = [r for r in results if r[1].startswith("learn/")]
        self.assertEqual(len(learn), 5)
        self.assertTrue(all(total <= 300_000 for total, *_ in learn))

    def test_every_journey_page_says_draft_and_shows_status_on_every_claim(self):
        for slug in self.summary["journeys"]:
            src = (self.learn / slug / "index.html").read_text(encoding="utf-8")
            with self.subTest(slug):
                self.assertIn(EN["learn.draft_banner"], src.replace("&#x27;", "'"))
                self.assertIn(EN["learn.rule.heading"], src)
                for li in re.findall(r'<li class="claim[^"]*">(.*?)</li>', src, flags=re.S):
                    self.assertIn("Status:", li)
                steps = re.findall(r'<li class="step" id="step-(\d+)" data-step="([^"]+)"', src)
                self.assertEqual([int(n) for n, _ in steps], list(range(1, len(steps) + 1)))
                self.assertEqual(len(steps), self.summary["journeys"][slug]["steps"])

    def test_every_step_links_to_its_entity_page(self):
        for slug in self.summary["journeys"]:
            src = (self.learn / slug / "index.html").read_text(encoding="utf-8")
            for block in re.split(r'(?=<li class="step")', src)[1:]:
                pid = re.search(r'data-step="([^"]+)"', block).group(1)
                href = re.search(r'<h3 class="step-title"[^>]*>.*?<a href="\.\./\.\./([a-z]+)/([^/"]+)/">', block, flags=re.S)
                self.assertIsNotNone(href, slug)
                self.assertEqual(href.group(2), pid)
                self.assertTrue((self.out / href.group(1) / pid / "index.html").is_file())

    def test_ai_generated_material_is_flagged(self):
        for slug in self.summary["journeys"]:
            src = (self.learn / slug / "index.html").read_text(encoding="utf-8")
            self.assertIn(EN["learn.ai_note"], src, slug)
        fb = (self.learn / "first-believers" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(fb.count(SITE_EN["story.banner"]), self.summary["journeys"]["first-believers"]["steps"])

    def test_the_practice_page_is_honest_about_being_empty(self):
        src = (self.learn / "practice" / "index.html").read_text(encoding="utf-8")
        self.assertIn(EN["learn.practice.empty"], src)
        self.assertNotIn('class="questions"', src)
        self.assertNotIn("<script", src)
        self.assertIn("0 accepted", src)

    def test_only_progress_needs_the_script(self):
        for p in self.pages():
            src = p.read_text(encoding="utf-8")
            scripts = re.findall(r"<script[^>]*>", src)
            if p.parent.name == "practice":
                self.assertEqual(scripts, [], p)
            else:
                self.assertEqual(scripts, ['<script src="' + "../" * (len(p.relative_to(self.out).parts) - 1)
                                           + 'learn/assets/learn.js" defer>'], p)
            self.assertNotIn("onclick", src)
            # nothing on the page depends on the script: progress controls are hidden or inert
            self.assertNotIn("<input", re.sub(r"<template.*?</template>", "", src, flags=re.S))

    def test_licence_footer_on_every_page(self):
        for p in self.pages():
            foot = p.read_text(encoding="utf-8").split("<footer", 1)[1]
            for needle in ("LICENSING.md", "creativecommons.org/licenses/by-sa/4.0/", "gnu.org/licenses/agpl-3.0.html"):
                self.assertIn(needle, foot, p)

    def test_hijrah_page_still_matches_the_e1_golden_hash(self):
        """The E1 class page (design §3.7): the golden hash recorded on the v1 renderer
        (learn/tests/golden_e1.json), compared while the Hijrah content is unchanged."""
        want = json.loads(golden.E1_FILE.read_text(encoding="utf-8"))
        site = Site(GRAPH)
        j = next(j for j in J.build_all(site, J.load_specs(LEARN / "journeys")) if j.slug == golden.HIJRAH)
        if golden.content_facts(site, j) != want["gate"]:
            self.skipTest("re-verify E1: the Hijrah content changed since the golden hash was recorded")
        page = (self.learn / golden.HIJRAH / "index.html").read_text(encoding="utf-8")
        self.assertEqual(golden.page_sha(golden.held_page(page)), want["page_sha256"])
        self.assertIn(EN["journey.hijrah.lead_study"], page)

    def test_rebuilding_replaces_only_learn(self):
        marker = self.out / "person" / "index.html"
        before = marker.read_bytes()
        quiet(build_learn.build, GRAPH, self.out, True)
        self.assertEqual(marker.read_bytes(), before)
        self.assertTrue((self.learn / ".al-marsad-learn").is_file())

    def test_build_is_deterministic_across_processes(self):
        import filecmp
        outs = []
        with tempfile.TemporaryDirectory() as da, tempfile.TemporaryDirectory() as db:
            for seed, d in (("1", da), ("2", db)):
                env = {**os.environ, "PYTHONHASHSEED": seed}
                subprocess.run([sys.executable, str(SITE / "build.py"), "--graph", str(GRAPH), "--out", d],
                               check=True, capture_output=True, env=env)
                subprocess.run([sys.executable, str(LEARN / "build_learn.py"), "--graph", str(GRAPH), "--site", d],
                               check=True, capture_output=True, env=env)
                outs.append(Path(d) / "learn")

            def differs(cmp):
                bad = list(cmp.diff_files) + list(cmp.left_only) + list(cmp.right_only)
                for sub in cmp.subdirs.values():
                    bad += differs(sub)
                return bad

            self.assertEqual(differs(filecmp.dircmp(outs[0], outs[1])), [])


class PracticeWithAcceptedClaims(unittest.TestCase):
    """A made-up graph where scholars have accepted four claims: the page shows the
    questions, each answer linked to the people, events and sources behind it."""

    @classmethod
    def setUpClass(cls):
        fx = Fx()
        cls.a, cls.b = fx.person("fxPersonA", "Person A"), fx.person("fxPersonB", "Person B")
        cls.e1, cls.e2 = fx.event("fxEventA", "Rihla one"), fx.event("fxEventB", "Rihla two")
        cls.claims = [fx.claim(w, "rel_participated_in", e, ("accepted",)) for w in (cls.a, cls.b) for e in (cls.e1, cls.e2)]
        fx.claim(cls.a, "rel_led", cls.e1, ("proposed",))
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        graph = fx.write(root / "graph.ttl")
        jdir = root / "journeys"
        jdir.mkdir()
        spec = json.loads((LEARN / "journeys" / "hijrah-step-by-step.json").read_text(encoding="utf-8"))
        spec["select"]["named"]["words"] = ["Rihla"]
        (jdir / "hijrah-step-by-step.json").write_text(json.dumps(spec), encoding="utf-8")
        cls.out = root / "dist"
        old = render_learn.QUESTIONS_PER_PAGE
        render_learn.QUESTIONS_PER_PAGE = 1        # two questions -> two pages
        try:
            cls.summary = build_into(cls.out, graph, jdir)
        finally:
            render_learn.QUESTIONS_PER_PAGE = old

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_questions_are_made_and_paged(self):
        self.assertEqual(self.summary["questions"], 2)
        self.assertEqual(self.summary["practice_pages"], 2)
        bank = json.loads((self.out / "learn" / "practice" / "bank.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(q["type"] for q in bank["questions"]), ["both_events", "shared_events"])
        self.assertEqual(practice.claims_used(bank["questions"]), set(self.claims))

    def test_each_answer_links_to_its_entities_and_sources(self):
        pages = [self.out / "learn" / "practice" / "index.html", self.out / "learn" / "practice" / "2" / "index.html"]
        text = "".join(p.read_text(encoding="utf-8") for p in pages)
        self.assertEqual(text.count('<li class="question"'), 2)
        self.assertEqual(text.count("Status: accepted"), 8)          # two answers x two claims, per question
        self.assertNotIn("Status: proposed", text)
        self.assertEqual(text.count("Source: Fixture basis."), 8)
        for href in set(re.findall(r'href="((?:\.\./)+)(person|event)/([^/"]+)/"', text)):
            self.assertTrue((self.out / href[1] / href[2] / "index.html").is_file())
        self.assertEqual(quiet(check_html.main, [str(self.out)]), 0)
        self.assertEqual(quiet(check_budget.main, [str(self.out)]), 0)


class SideGroupsOnTheStudyPage(unittest.TestCase):
    """A made-up battle with people recorded on both sides (fixtures.side_fixture): the
    Study page gives the against group its heading and lead where the group starts,
    numbers the steps across both lists, and says in the rule box that the order holds
    inside each group (design §6.4). Without group_by, neither appears."""

    @classmethod
    def setUpClass(cls):
        fx, cls.i = side_fixture()
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        graph = fx.write(root / "graph.ttl")
        cls.out = {}
        for name, group_by in (("grouped", "side"), ("plain", None)):
            jdir = root / f"journeys-{name}"
            jdir.mkdir()
            spec = people_spec(order="prophet_first_then_name", group_by=group_by)
            (jdir / f"{spec['slug']}.json").write_text(json.dumps(spec), encoding="utf-8")
            out = root / f"dist-{name}"
            build_into(out, graph, jdir)
            cls.out[name] = out
        cls.slug = spec["slug"]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def page(self, name: str) -> str:
        return (self.out[name] / "learn" / self.slug / "index.html").read_text(encoding="utf-8")

    def test_the_against_group_has_its_heading_and_lead_where_it_starts(self):
        src = self.page("grouped")
        heading, lead = (render_learn.esc(EN[k]) for k in ("learn.group.against", "learn.group.against_lead"))
        self.assertEqual(src.count(heading), 1)
        self.assertEqual(src.count(lead), 1)
        before, after = src.split(heading, 1)
        steps_before = re.findall(r'<li class="step" id="step-(\d+)" data-step="([^"]+)"', before)
        steps_after = re.findall(r'<li class="step" id="step-(\d+)" data-step="([^"]+)"', after)
        self.assertEqual(sorted(pid for _, pid in steps_after),
                         sorted(self.i[k].rsplit("/", 1)[-1] for k in ("against", "convert")))
        self.assertEqual([int(n) for n, _ in steps_before + steps_after], list(range(1, 12)))
        self.assertIn(f'<ol class="journey-steps" start="{len(steps_before) + 1}">', after)
        self.assertEqual(quiet(check_html.main, [str(self.out["grouped"])]), 0)

    def test_the_rule_box_says_the_order_holds_inside_each_group(self):
        rule = self.page("grouped").split('id="h-rule"', 1)[1].split("</section>", 1)[0]
        order = rule.index(render_learn.esc(EN["learn.order.prophet_first_then_name"]))
        self.assertGreater(rule.index(render_learn.esc(EN["learn.rule.group_side"])), order)
        self.assertEqual(J.review_words(EN["learn.rule.group_side"]), [])
        self.assertNotIn("last", EN["learn.rule.group_side"].lower().split())

    def test_without_group_by_there_is_one_list_and_no_group_text(self):
        src = self.page("plain")
        for k in ("learn.group.against", "learn.group.against_lead", "learn.rule.group_side"):
            self.assertNotIn(render_learn.esc(EN[k]), src, k)
        self.assertEqual(src.count('<ol class="journey-steps"'), 1)


if __name__ == "__main__":
    unittest.main()
