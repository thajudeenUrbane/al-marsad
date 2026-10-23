"""The learn build on the joined graph (build/graph-all.ttl): a smoke test, design §13.

Off by default, because the joined graph takes about half a minute to load and the reader
site built from it is large. Run it with
    LEARN_JOINED=1 .venv/bin/python -m unittest test_joined -v      (from learn/tests)
It builds the reader site and then learn from the joined graph into a scratch folder
(site/dist is never touched), runs every page invariant the page-graph build keeps
(test_build.PageChecks: manifest, anchors, depth links, caps, Discover sources and review
language, check_html; check_budget for the learn pages, since the reader tier's own pages
on this graph are slice 11b's), checks the export parts against PART_BUDGET, the
side groups and the Atlas facade, and prints the step, page and part counts, the graph
fingerprint and each journey's content_sha. It asserts none of those numbers as constants.
Slice 11b moves the reader pages to this graph with no learn code change; this is the gate.
"""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

LEARN = Path(__file__).resolve().parents[1]
ROOT = LEARN.parent
sys.path.insert(0, str(ROOT / "site"))
sys.path.insert(0, str(LEARN))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_budget  # noqa: E402
import check_html  # noqa: E402
import journey_export as X  # noqa: E402
import journeys as J  # noqa: E402
from model import Site  # noqa: E402
from test_build import EN, PageChecks, build_into, export_of, journey_pages, quiet  # noqa: E402
from test_journeys import atlas_load_journeys, node_index  # noqa: E402

JOINED = ROOT / "build" / "graph-all.ttl"
ON = os.environ.get("LEARN_JOINED") == "1"
PAGE_BUDGET = 300_000     # site/check_budget.py's limit for a page with its assets


def say(line: str = ""):
    print(line, file=sys.stderr, flush=True)


@unittest.skipUnless(ON, "set LEARN_JOINED=1 to build learn on build/graph-all.ttl (design §13)")
class JoinedGraph(PageChecks, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not JOINED.exists():
            raise AssertionError(f"LEARN_JOINED=1 but {JOINED} is missing: run the joined graph build first")
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        start = time.monotonic()
        cls.summary = build_into(cls.out, JOINED)
        cls.seconds = time.monotonic() - start
        cls.exp = export_of(cls.out)
        cls.data = cls.out / "learn" / "data"
        # check_budget walks the whole joined site (about 17,000 pages): run it once
        cls.budget = check_budget.check(cls.out)
        cls.report()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @classmethod
    def report(cls):
        g = cls.exp["index"]["graph"]
        results, _ = cls.budget
        learn = sorted((r for r in results if r[1].startswith("learn/")), key=lambda r: (-r[0], r[1]))
        say()
        say(f"joined graph {g['file']}: fingerprint {g['fingerprint']}, {g['triples']} triples; "
            f"site and learn built in {cls.seconds:.0f} s")
        for slug, s in sorted(cls.summary["journeys"].items()):
            folder = cls.data / "journeys" / slug
            parts = [len((folder / name).read_bytes()) for name in cls.exp["journeys"][slug]["head"]["parts"]]
            head = len((folder / "journey.json").read_bytes())
            apart = f" (+{s['apart']} apart)" if s["apart"] else ""
            groups = ", ".join(f"{gr['key']} {gr['to'] - gr['from'] + 1}" for gr in
                               cls.exp["journeys"][slug]["head"]["groups"])
            say(f"  {slug}: {s['steps']} steps{apart}; groups {groups or 'none'}; "
                f"pages discover {s['pages']['discover']}, study {s['pages']['study']}, research {s['pages']['research']}; "
                f"{len(parts)} parts, largest {max(parts)} B; head {head} B; content_sha {s['content_sha']}")
        say(f"  learn pages {len(learn)}; largest {learn[0][1]} {learn[0][0]} B with its assets")
        say(f"  export {cls.summary['export']['files']} files, digest {cls.summary['export']['digest']}; "
            f"atlas facade (joined graph) {cls.summary['export']['facade']}")

    def test_the_site_checks_pass_with_the_learn_pages_in_place(self):
        """check_html passes on the whole joined site, learn pages included, and
        check_budget finds no problem under learn/. The reader tier's own pages on this
        graph (entity, search, Study and Research pages, in both languages) are over its
        budget: that is the site's work for slice 11b, not learn's, so it is printed here,
        never asserted (PageChecks asserts the whole site on the page graph)."""
        self.assertEqual(quiet(check_html.main, [str(self.out)]), 0)
        results, problems = self.budget
        self.assertEqual([p for p in problems if p.startswith("learn/")], [])
        outside = sorted({p.split("/", 1)[0] for p in problems})
        say(f"  reader tier on the joined graph: {len(problems)} of {len(results)} pages over check_budget's "
            f"limits, none under learn/ (folders: {', '.join(outside) or 'none'})")

    def test_every_learn_page_is_within_the_page_budget(self):
        results, problems = self.budget
        learn = [r for r in results if r[1].startswith("learn/")]
        self.assertEqual(len(learn), len(self.exp["pages"]))
        for total, rel, *_ in learn:
            self.assertLessEqual(total, PAGE_BUDGET, rel)

    def test_every_export_part_is_within_the_part_budget(self):
        for path in sorted((self.data / "journeys").rglob("*.json")):
            if path.name.startswith(("part-", "research-")):
                self.assertLessEqual(len(path.read_bytes()), X.PART_BUDGET, path.relative_to(self.data))

    def test_the_prophet_step_has_no_side_entries(self):
        seen = 0
        for slug, doc in self.exp["journeys"].items():
            for st in doc["steps"]:
                if doc["entities"][st["ref"]].get("prophet"):
                    seen += 1
                    self.assertEqual(st.get("side") or [], [], slug)
        self.assertGreater(seen, 0)

    def test_every_against_group_person_has_a_cited_side_claim(self):
        """design §6.4: a person is in the against group only through a cited
        rel_fought_against claim of their own at the anchors, never a proxy."""
        for slug, doc in self.exp["journeys"].items():
            for st in doc["steps"]:
                if st["group"] != "against":
                    continue
                with self.subTest(slug, key=st["key"]):
                    cited = [c for s in st["side"] if s["pk"] == "rel_fought_against" for c in s["claims"]
                             if doc["claims"][c].get("passage")
                             and doc["passages"][doc["claims"][c]["passage"]]["cite"]]
                    self.assertTrue(cited)
                    self.assertFalse(any(s["pk"] == "rel_fought_alongside" for s in st["side"]))

    def test_the_atlas_facade_replica_runs_on_the_joined_graph(self):
        """atlas/build.py load_journeys (the replica in test_journeys) runs unchanged on the
        joined graph, and atlas_projection gives the same record."""
        site = Site(JOINED)
        index = node_index(site)
        back = {n: iri for iri, n in index.items()}
        replica = atlas_load_journeys(site, index, self.fail, LEARN / "journeys", LEARN / "i18n" / "en.json")
        built = J.build_all(site, J.load_specs(LEARN / "journeys"))
        self.assertEqual([r["key"] for r in replica], [j.slug for j in built])
        for rec, j in zip(replica, built):
            mine = X.atlas_projection(j, EN)
            self.assertEqual(mine.pop("story_mode"), {"open": False})
            as_iris = dict(rec, steps=[back[n] for n in rec["steps"]], apart=[back[n] for n in rec["apart"]],
                           anchors=[back[n] for n in rec["anchors"]],
                           why=[[[k, back.get(o) if o != -1 else None, t] for k, o, t in rs] for rs in rec["why"]])
            self.assertEqual(mine, as_iris, j.slug)
            self.assertEqual(len(rec["steps"]), self.summary["journeys"][j.slug]["steps"])

    def test_the_printed_page_counts_are_the_pages_built(self):
        """The counts the build prints are the pages in pages.json and on disk (the order
        of the stops on them is PageChecks.test_reader_pages_follow_the_export)."""
        for slug in self.exp["journeys"]:
            for depth in X.DEPTHS:
                pages = journey_pages(self.out, self.exp, slug, depth)
                self.assertEqual(len(pages), self.summary["journeys"][slug]["pages"][depth], (slug, depth))
                self.assertEqual([e["page"] for e, _ in pages], list(range(1, len(pages) + 1)))


if __name__ == "__main__":
    unittest.main()
