"""Slice 2c-site: the three doors, the hub of views, the thread view, plain words, the
Experiments page and the external-ID hook.
Run:  .venv/bin/python -m unittest discover -s site/tests -v
"""
import contextlib
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
ROOT = SITE.parent
sys.path.insert(0, str(SITE))

import build as site_build  # noqa: E402
import check_budget  # noqa: E402
import check_hub  # noqa: E402
import display  # noqa: E402
import experiments  # noqa: E402
import external  # noqa: E402
import hub  # noqa: E402

GRAPH = ROOT / "build" / "graph.ttl"
EN = json.loads((SITE / "i18n" / "en.json").read_text(encoding="utf-8"))


def quiet(fn, *args, **kw):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*args, **kw)


def matchers(*pairs):
    """Glossary-style matchers on folded text, longest first."""
    out = [(re.compile(r"(?<![a-z0-9'])" + re.escape(display.fold(t).lower()) + r"(?![a-z0-9'])", re.I), k)
           for t, k in pairs]
    return sorted(out, key=lambda m: -len(m[0].pattern))


PLAIN = {"ridda": "apostasy", "khandaq": "the Trench", "tabaqa": "generation"}
M = matchers(("Ridda", "ridda"), ("Khandaq", "khandaq"), ("ṭabaqa", "tabaqa"))


def link(text, once=False, seen=None):
    return display.link_terms(text, M, lambda k: f"g#{k}", seen if seen is not None else set(), once,
                              plain_for=PLAIN.get)[0]


class PlainWords(unittest.TestCase):
    def test_a_term_in_brackets_after_its_english_is_marked_to_hide(self):
        out = link("Generation (ṭabaqa)")
        self.assertEqual(out, 'Generation<span class="t-gloss"> (<a class="term" href="g#tabaqa">ṭabaqa</a>)</span>')
        out = link("The Battle of the Trench (al-Khandaq)")
        self.assertIn('<span class="t-gloss"> (al-<a class="term" href="g#khandaq">Khandaq</a>)</span>', out)
        self.assertNotIn("data-plain", out)

    def test_a_free_standing_term_gets_its_plain_wording_capitalised_like_the_term(self):
        out = link("Seed item 091 (Ridda Wars): rebellions")
        self.assertIn('<a class="term" href="g#ridda" data-plain="Apostasy">Ridda</a>', out)
        self.assertIn(" Wars): rebellions", out)

    def test_joined_or_already_glossed_terms_are_left_as_written(self):
        self.assertNotIn("data-plain", link("The Ridda ('apostasy') wars"))
        self.assertNotIn("data-plain", link("Ghazwat wal-Khandaq"))

    def test_terms_without_a_plain_wording_are_only_linked(self):
        m = matchers(("Ansar", "ansar"))
        out = display.link_terms("the Ansar came", m, lambda k: "g", set(), plain_for=PLAIN.get)[0]
        self.assertEqual(out, 'the <a class="term" href="g">Ansar</a> came')

    def test_a_term_linked_once_still_switches_where_it_repeats(self):
        seen = set()
        link("Ridda Wars", once=True, seen=seen)
        out = link("after the Ridda", once=True, seen=seen)
        self.assertEqual(out, 'after the <span class="term-text" data-plain="Ridda">Ridda</span>'.replace(
            'data-plain="Ridda"', 'data-plain="Apostasy"'))

    def test_without_plain_words_the_output_is_as_before(self):
        out = display.link_terms("Generation (ṭabaqa) and Ridda", M, lambda k: "g", set())[0]
        self.assertNotIn("data-plain", out)
        self.assertIn('<a class="term" href="g">Ridda</a>', out)


class ExternalIds(unittest.TestCase):
    HEADER = "canonical_id,kind,system,external_id,external_label,evidence,confidence,status\n"

    def write(self, tmp, body, header=None):
        p = Path(tmp) / "external-ids.csv"
        p.write_text((header or self.HEADER) + body, encoding="utf-8")
        return p

    def test_no_file_means_nothing_shown(self):
        self.assertEqual(external.load(Path("/nonexistent/external-ids.csv")), {})

    def test_rows_are_read_keyed_by_iri_and_linked_only_when_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.write(tmp, "per:Abc123,person,wikidata,Q42,Some Name,name forms,probable,proposed\n"
                                "per:Abc123,person,althurayya,MAKKA_1,Makka,name,needs-review,proposed\n"
                                "per:Abc123,person,wikidata,javascript:x,bad,,needs-review,proposed\n"
                                "wrk:Zzz,work,openiti,0218IbnHisham,Sira,,exact,proposed\n")
            rows = external.load(p)
        iri = external.ID_BASE + "person/Abc123"
        self.assertEqual(list(rows), [iri])
        self.assertEqual([r["external_id"] for r in rows[iri]], ["Q42", "javascript:x", "MAKKA_1"])
        self.assertEqual(rows[iri][0]["url"], "https://www.wikidata.org/wiki/Q42")
        self.assertIsNone(rows[iri][1]["url"])
        self.assertIsNone(rows[iri][2]["url"])

    def test_rows_for_records_without_a_page_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.write(tmp, "per:Abc123,person,wikidata,Q42,X,,exact,proposed\n")
            self.assertEqual(external.load(p, known=set()), {})

    def test_a_changed_format_fails_the_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.write(tmp, "per:A,person,Q1\n", header="canonical_id,kind,qid\n")
            with self.assertRaises(ValueError):
                external.load(p)

    def test_prefixes_agree_with_the_identity_audit(self):
        sys.path.insert(0, str(ROOT / "ontology" / "tools"))
        import identity_audit
        self.assertEqual(external.PREFIX_SEGMENT, identity_audit.IRI_SEGMENT)


class HubAndPrototypes(unittest.TestCase):
    def test_a_view_counts_as_built_only_with_an_index_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "observatory").mkdir()
            self.assertEqual(hub.built(out), [])
            (out / "observatory" / "index.html").write_text("x")
            (out / "map").mkdir()
            (out / "map" / "index.html").write_text("x")
            self.assertEqual(hub.built(out), ["map", "observatory"] if False else ["observatory", "map"])

    def test_every_view_has_a_door_and_its_strings(self):
        for folder, door in hub.VIEWS:
            self.assertIn(door, hub.DOORS)
            self.assertIn(f"hub.view.{folder}.name", EN)
            self.assertIn(f"hub.view.{folder}.desc", EN)

    def test_a_prototype_fragment_becomes_a_document_without_web_fonts(self):
        frag = ('<title>T</title>\n<link rel="preconnect" href="https://fonts.googleapis.com">\n'
                '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=X">\n<style>a{}</style>\n\n<header><h1>T</h1></header>')
        page = experiments.wrap(experiments.strip_web_fonts(frag), lang="en", base="../../", note="<p>N</p>", footer="<footer>F</footer>")
        self.assertNotIn("fonts.g", page)
        self.assertEqual(experiments.outside_loads(page), [])
        head, body = page.split("<body>")
        self.assertIn("<title>T</title>", head)
        self.assertIn("<style>a{}</style>", head)
        self.assertLess(body.index("<p>N</p>"), body.index("<header>"))
        self.assertLess(body.index("<header>"), body.index("<footer>F</footer>"))
        self.assertTrue(experiments.is_copy("experiments/x/index.html"))
        self.assertFalse(experiments.is_copy("experiments/index.html"))


class ScriptsHoldNoText(unittest.TestCase):
    def test_no_ui_words_and_no_urls_in_the_scripts(self):
        for name in ("enhance.js", "thread.js"):
            js = (SITE / "static" / name).read_text(encoding="utf-8")
            code = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
            literals = re.findall(r'"((?:[^"\\]|\\.)*)"', code)
            classes = re.compile(r"^[a-z][a-z0-9-]*(?: [a-z][a-z0-9-]*)*$")   # CSS class lists
            words = [s for s in literals if s != "use strict" and not classes.match(s)
                     and re.search(r"[A-Za-z]{3,}\s+[A-Za-z]{3,}", s)]
            self.assertEqual(words, [], name)
            self.assertEqual([s for s in literals if re.search(r"https?:|//|\.json\b", s)], [], name)
        thread = (SITE / "static" / "thread.js").read_text(encoding="utf-8")
        self.assertIn('fetch(root.getAttribute("data-fetch"))', thread)
        enhance = (SITE / "static" / "enhance.js").read_text(encoding="utf-8")
        self.assertEqual(enhance.count("window.localStorage"), 2)
        self.assertEqual(enhance.count("try {"), 2)


@unittest.skipUnless(GRAPH.exists(), "build/graph.ttl missing: run ontology/build_graph.py")
class BuiltDoorsAndThread(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        cls.summary = quiet(site_build.build, GRAPH, cls.out, quiet=True)
        from model import Site
        cls.site = Site(GRAPH)
        cls.thread = json.loads((cls.out / "thread.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def page(self, rel):
        return (self.out / rel).read_text(encoding="utf-8")

    def test_every_entity_page_has_one_evidence_anchor_after_the_summary(self):
        for e in self.site.entities.values():
            src = self.page(f"{e.kind}/{e.pid}/index.html")
            self.assertEqual(src.count('id="evidence"'), 1, e.name)
            self.assertLess(src.index("<h1>"), src.index('id="evidence"'))
            if e.kind == "story":
                self.assertLess(src.index('class="story-text"'), src.index('id="evidence"'), e.name)
            for sec in re.findall(r'id="s-([a-z_]+)"', src):
                self.assertLess(src.index('id="evidence"'), src.index(f'id="s-{sec}"'))

    def test_study_and_research_open_records_at_their_evidence(self):
        for rel in ("study/index.html", "research/index.html"):
            src = self.page(rel)
            links = re.findall(r'href="\.\./(person|group|place|event|story)/([^/"]+)/([^"]*)"', src)
            self.assertTrue(links, rel)
            for kind, pid, rest in links:
                self.assertIn(rest, ("#evidence", "#s-disputes", "#s-gaps", "entity.ttl"), (rel, kind, pid, rest))
        research = self.page("research/index.html")
        for e in self.site.entities.values():
            self.assertIn(f'href="../{e.kind}/{e.pid}/#evidence"', research, e.name)
        self.assertIn('href="../data/graph.ttl"', research)
        self.assertTrue((self.out / "data" / "graph.ttl").is_file())

    def test_study_lists_events_by_recorded_date_and_undated_apart(self):
        src = self.page("study/index.html")
        timeline = src[src.index('class="index-list timeline-list"'):]
        timeline = timeline[:timeline.index("</ol>")]
        names = re.findall(r'<li><span class="when">', timeline)
        dated = [e for e in self.site.by_kind["event"]
                 if any(x.get("earliest") for x in e.data["dates"])]
        self.assertEqual(len(names), len(dated))

    def test_discover_leads_to_the_stories_in_reading_order(self):
        home = self.page("index.html")
        first = self.site.stories_in_order()[0]
        door = home[home.index('id="door-discover"'):home.index('id="door-study"')]
        self.assertIn('href="story/"', door)
        self.assertIn(f'href="story/{first.pid}/"', door)
        self.assertNotIn("#evidence", door)

    def test_the_hub_links_only_views_that_were_built(self):
        self.assertEqual(self.summary["views"], [])
        home = self.page("index.html")
        for folder, _ in hub.VIEWS:
            self.assertNotIn(f'href="{folder}/"', home)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "dist"
            shutil.copytree(self.out, out)
            (out / "timeline").mkdir()
            (out / "timeline" / "index.html").write_text(self.page("glossary/index.html"), encoding="utf-8")
            self.assertEqual(quiet(check_hub.main, [str(out)]), 1)       # built after the hub pages
            quiet(site_build.build_hub, GRAPH, out)
            self.assertEqual(quiet(check_hub.main, [str(out)]), 0)
            home = (out / "index.html").read_text(encoding="utf-8")
            self.assertIn('href="timeline/"', home)
            self.assertIn('href="../timeline/"', (out / "study" / "index.html").read_text(encoding="utf-8"))
            quiet(site_build.build, GRAPH, out, quiet=True)             # a full rebuild keeps the view
            self.assertTrue((out / "timeline" / "index.html").is_file())
            self.assertIn('href="timeline/"', (out / "index.html").read_text(encoding="utf-8"))
            shutil.rmtree(out / "timeline")
            quiet(site_build.build_hub, GRAPH, out)
            self.assertNotIn('href="timeline/"', (out / "index.html").read_text(encoding="utf-8"))

    def test_thread_switch_only_on_person_and_group_pages_hidden_without_js(self):
        for e in self.site.entities.values():
            src = self.page(f"{e.kind}/{e.pid}/index.html")
            if e.kind in ("person", "group"):
                root = re.search(r'<div class="thread-root"[^>]*>', src).group(0)
                self.assertIn(" hidden", root)
                self.assertIn('data-fetch="../../thread.json"', root)
                self.assertIn(f'data-self="{e.kind}/{e.pid}"', root)
            else:
                self.assertNotIn("thread-root", src)

    def test_thread_data_is_the_graph_with_status_on_every_claim(self):
        T = self.thread
        rows = [e for k in T["k"] for e in self.site.by_kind[k]]
        self.assertEqual([(T["k"][r[0]], r[1], r[2]) for r in T["e"]], [(e.kind, e.pid, e.name) for e in rows])
        statuses = {k: v for k, v in T["t"]}
        self.assertTrue(set(statuses) <= {"none", "proposed", "under_review", "accepted", "rejected", "superseded"})
        for k, v in statuses.items():
            self.assertTrue(v.startswith(EN["status.label"].split("{")[0]))
        counts = self.site.status_counts()
        if not counts.get("accepted"):
            self.assertNotIn("accepted", statuses)
        for c in T["c"]:
            self.assertLess(c[3], len(T["t"]))
        for r in T["e"]:
            if T["k"][r[0]] == "story":
                self.assertFalse(len(r) > 3 and r[3], "a story was given a date")
        self.assertTrue(set(T["s"]) >= {"close", "also", "lead.one", "lead.other", "note"})
        self.assertFalse(any("{" in v and "}" in v and not re.search(r"\{(n|name)\}", v) for v in T["s"].values()))

    def test_abu_bakr_thread_reaches_his_stories_and_people(self):
        T = self.thread
        abu = [i for i, r in enumerate(T["e"]) if r[2] == "Abu Bakr as-Siddiq"]
        self.assertEqual(len(abu), 1)
        mine = [c for c in T["c"] if abu[0] in c[:2]]
        others = {c[1] if c[0] == abu[0] else c[0] for c in mine}
        kinds = {T["k"][T["e"][o][0]] for o in others}
        self.assertTrue({"story", "event", "person"} <= kinds)

    def test_person_pages_carry_the_thread_within_budget(self):
        results, problems = check_budget.check(self.out)
        self.assertEqual(problems, [])
        heaviest = max((t, rel) for t, rel, _, _ in results if rel.startswith("person/"))
        self.assertLess(heaviest[0], check_budget.LIMIT)
        src = self.page(heaviest[1])
        self.assertIn("thread.js", src)

    def test_prototype_copies_are_labelled_and_load_nothing_outside(self):
        exp = self.page("experiments/index.html")
        for folder, source, pages, _ in experiments.PROTOTYPES:
            self.assertIn(f'href="{folder}/"', exp)
            for name in pages:
                rel = f"experiments/{folder}/{name}"
                src = self.page(rel)
                self.assertIn('class="archive-note"', src)
                self.assertIn(EN["experiments.copy_note"].split(" (")[0], src)
                self.assertIn("LICENSING.md", src[src.index('archive-footer'):])
                self.assertEqual(experiments.outside_loads(src), [], rel)
                self.assertTrue((ROOT / source / name).is_file())
        self.assertIn('href="experiments/"', self.page("index.html"))

    def test_plain_words_marks_on_pages(self):
        abu = [e for e in self.site.by_kind["person"] if e.name == "Abu Bakr as-Siddiq"][0]
        src = self.page(f"person/{abu.pid}/index.html")
        self.assertIn('<span class="t-gloss"> (<a class="term"', src)
        self.assertIn('class="plain-toggle" aria-pressed="false"', src)
        self.assertRegex(src, r'<button type="button" class="plain-toggle"[^>]* hidden>')
        glossary = self.page("glossary/index.html")
        self.assertIn("plain-wording", glossary)

    def test_external_matches_render_as_proposals(self):
        from render import Ctx  # noqa: F401
        r = site_build.renderer(GRAPH)[2]
        e = self.site.by_kind["person"][0]
        iri = e.iri
        r.external = {iri: [{"canonical_id": "per:x", "kind": "person", "system": "wikidata", "external_id": "Q42",
                             "external_label": "Some", "evidence": "name", "confidence": "probable",
                             "status": "proposed", "url": "https://www.wikidata.org/wiki/Q42"}]}
        html = r.external_matches(r.site.entity(iri))
        self.assertIn(EN["external.heading"], html)
        self.assertIn('href="https://www.wikidata.org/wiki/Q42"', html)
        self.assertIn(EN["external.proposed"], html)
        self.assertEqual(r.external_matches(r.site.by_kind["person"][1]), "")


if __name__ == "__main__":
    unittest.main()
