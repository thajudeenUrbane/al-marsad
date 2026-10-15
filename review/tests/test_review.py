"""
Tests for the review queue and the decision importer (slice 3a).

    .venv/bin/python -m unittest discover -s review/tests

Everything runs on a temporary copy of ontology/ with the throwaway roster in this
folder (roster.test.csv: clearly fake reviewers, never real people). The real corpus
files are never written; the last test checks that byte for byte. Claims are picked
from the queue built on the copy, never by a hard-coded ID. Citations and notes in the
decision files are labelled as unit-test fixtures, not real sources.
"""

import contextlib
import csv
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from pyshacl import validate
from rdflib import Graph

HERE = Path(__file__).resolve().parent
REVIEW = HERE.parent
ROOT = REVIEW.parent
sys.path.insert(0, str(REVIEW))
import build_queue  # noqa: E402
import common as c  # noqa: E402
import import_decisions  # noqa: E402

ROSTER = HERE / "roster.test.csv"
CITATION = "Test Source, vol. 0 p. 0 (unit-test fixture, not a real citation)"
NOTE = "Test note (unit-test fixture)"
TODAY = date.today().isoformat()


def real_corpus_digest() -> str:
    h = hashlib.sha256()
    for f in sorted((ROOT / "ontology").rglob("*")):
        if f.is_file() and f.suffix in (".ttl", ".csv"):
            h.update(str(f.relative_to(ROOT)).encode() + b"\0" + f.read_bytes())
    return h.hexdigest()


def reviewer_id(name: str) -> str:
    with ROSTER.open(encoding="utf-8") as fh:
        return next(r["reviewer_id"] for r in csv.DictReader(fh) if r["name"] == name)


def decision(unit: dict, outcome: str, **extra) -> dict:
    return {"kind": unit["kind"], "target": unit["id"], "decision": outcome, "date": TODAY, **extra}


def decision_file(path: Path, reviewer: str, decisions: list) -> Path:
    path.write_text(json.dumps({"format": "marsad-review-decisions", "version": 1, "reviewer_id": reviewer_id(reviewer),
                                "decisions": decisions}, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


class ReviewSlice3a(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.digest = real_corpus_digest()
        cls.tmp = Path(tempfile.mkdtemp(prefix="marsad-review-test-"))
        cls.ont = cls.tmp / "ontology"
        shutil.copytree(ROOT / "ontology", cls.ont, ignore=shutil.ignore_patterns("__pycache__", "*.tmp"))
        cls.inbox = cls.tmp / "inbox"
        cls.inbox.mkdir()
        cls.queue = build_queue.build(c.Tree(cls.ont), {"needs-review"}, 50)
        story = next(b for b in cls.queue["claims"] if b["kind"] == "story" and len(b["units"]) >= 6)
        cls.units = story["units"]
        u = cls.units
        cls.accepted, cls.rejected, cls.discussed, cls.no_citation, cls.out_of_scope, cls.named = u[:6]
        cls.file_a = decision_file(cls.inbox / "a.json", "Test Reviewer A", [
            decision(cls.accepted, "accept", checks=["report_in_source", "identity"], citation=CITATION, note=NOTE),
            decision(cls.rejected, "reject", checks=["summary_fair"], note=NOTE),
            decision(cls.discussed, "needs_discussion", note=NOTE),
        ])
        cls.file_b = decision_file(cls.inbox / "b.json", "Test Reviewer A", [
            decision(cls.no_citation, "accept", checks=["report_in_source"]),
            decision(cls.named, "reject", note="Seen by Test Reviewer B"),
        ])
        cls.file_c = decision_file(cls.inbox / "c.json", "Test Reviewer B", [decision(cls.out_of_scope, "accept", citation=CITATION)])
        cls.code, cls.out = cls.run_import(cls.file_a, cls.file_b, cls.file_c)
        # one identity question (from the 'probable' rows, since every needs-review row is ID bookkeeping)
        cls.identity_queue = build_queue.build(c.Tree(cls.ont), {"probable"}, 50)
        cls.identity_unit = cls.identity_queue["identity"][0]["units"][0]
        cls.file_i = decision_file(cls.inbox / "i.json", "Test Reviewer A", [decision(cls.identity_unit, "needs_discussion", note=NOTE)])
        cls.code_i, cls.out_i = cls.run_import(cls.file_i)
        # a second reviewer: agreeing is recorded, disagreeing goes to the board
        cls.file_d = decision_file(cls.inbox / "d.json", "Test Reviewer D", [
            decision(cls.accepted, "accept", citation=CITATION),
            decision(cls.discussed, "reject", note=NOTE),
        ])
        cls.code_d, cls.out_d = cls.run_import(cls.file_d)
        cls.tree = c.Tree(cls.ont)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    @classmethod
    def run_import(cls, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = import_decisions.main([*map(str, args), "--ontology", str(cls.ont), "--roster", str(ROSTER)])
        return code, buf.getvalue()

    def snapshot(self):
        return {p: p.read_bytes() for p in sorted(self.ont.rglob("*")) if p.is_file() and p.suffix in (".ttl", ".csv")}

    def status(self, unit):
        return c.Tree(self.ont).status(c.expand(unit["id"]))

    # ---- the queue ----------------------------------------------------------------------------
    def test_queue_batches_every_proposed_claim_once(self):
        q = self.queue
        kinds = [b["kind"] for b in q["claims"]]
        self.assertEqual(kinds, sorted(kinds, key=["story", "person", "file"].index), "story, then person, then file")
        ids = [u["id"] for b in q["claims"] for u in b["units"]]
        self.assertEqual(len(ids), len(set(ids)))
        tree = c.Tree(ROOT / "ontology")
        self.assertEqual(set(ids), {c.curie(a) for a in tree.assertions() if tree.status(a) == "proposed"})
        for b in q["claims"]:
            self.assertLessEqual(len(b["units"]), 50)
            if b["kind"] == "story":
                self.assertIn(b["passage"], q["passages"])
                self.assertTrue(q["passages"][b["passage"]]["text"], "the story passage is carried verbatim")
                for u in b["units"]:  # every 50 Stories link rests on an AI-generated document
                    self.assertTrue(u["ai_generated_basis"] and u["citation_required_to_accept"])
            for u in b["units"]:
                self.assertEqual(u["status"], "proposed")
                self.assertTrue(u["claim"] and u["basis"]["kind"] in ("report", "non_report"))

    def test_identity_queue_leaves_out_id_bookkeeping_rows(self):
        q = self.queue
        rows = [r for r in c.Tree(ROOT / "ontology").identity if r["confidence"] == "needs-review"]
        listed = {u["id"] for b in q["identity"] for u in b["units"]} | {r["id"] for r in q["identity_excluded"]}
        self.assertEqual(listed, {r["canonical_id"] for r in rows})
        for r in q["identity_excluded"]:
            self.assertTrue(r["reasons"])
        # the classifier: an ID-only note is left out, any other flag is kept
        self.assertTrue(c.id_only({"note": "IRI nearly identical to per:X, which is a different entity by label; do not merge "
                                           "or trim IDs | slice 1d (15 Oct 2026): ID re-minted, retired ID(s) kept"}))
        self.assertFalse(c.id_only({"note": "IRI nearly identical to per:X | may name the same man as per:Y; a scholar's call"}))
        self.assertFalse(c.id_only({"note": ""}))

    # ---- the import ---------------------------------------------------------------------------
    def test_import_moves_three_claims(self):
        self.assertEqual(self.code, 1, self.out)  # 1 because files b and c hold refused decisions
        self.assertEqual(self.status(self.accepted), "accepted")
        self.assertEqual(self.status(self.rejected), "rejected")
        self.assertEqual(self.status(self.discussed), "under_review")
        decisions = {c.curie(d.target): d for d in self.tree.decisions() if c.curie(d.reviewer) == reviewer_id("Test Reviewer A")}
        acc = decisions[self.accepted["id"]]
        self.assertEqual((acc.outcome, acc.status_before, acc.status_after), ("accept", "proposed", "accepted"))
        self.assertEqual(acc.citation, CITATION)
        self.assertEqual(acc.checks, ("identity", "report_in_source"))
        self.assertEqual(c.curie(acc.reviewer), reviewer_id("Test Reviewer A"))
        self.assertEqual(acc.tradition, self.tree.default_tradition())
        self.assertEqual(decisions[self.discussed["id"]].status_after, "under_review")
        self.assertEqual(decisions[self.rejected["id"]].status_after, "rejected")

    def test_accept_of_50_stories_claim_without_citation_is_refused(self):
        self.assertIn("accept refused", self.out)
        self.assertEqual(self.status(self.no_citation), "proposed")

    def test_out_of_scope_reviewer_is_refused(self):
        self.assertIn("out of scope", self.out)
        self.assertEqual(self.status(self.out_of_scope), "proposed")

    def test_names_never_enter_the_record(self):
        self.assertIn("contains a reviewer's name", self.out)
        self.assertEqual(self.status(self.named), "proposed")
        with ROSTER.open(encoding="utf-8") as fh:
            names = [r["name"] for r in csv.DictReader(fh)]
        for path, data in self.snapshot().items():
            for name in names:
                self.assertNotIn(name, data.decode("utf-8"), f"{name} in {path.name}")

    def test_needs_discussion_identity_question_recorded(self):
        self.assertEqual(self.code_i, 0, self.out_i)
        d = next(d for d in self.tree.decisions() if c.curie(d.target) == self.identity_unit["id"])
        self.assertEqual((d.outcome, d.question, d.status_after), ("needs_discussion", "same_as", None))
        self.assertEqual((self.ont / "corpus" / "identity.csv").read_bytes(), (ROOT / "ontology" / "corpus" / "identity.csv").read_bytes())

    def test_second_reviewer_agrees_or_goes_to_the_board(self):
        self.assertEqual(self.code_d, 1, self.out_d)
        self.assertIn("1 new (agrees; no change)", self.out_d)
        self.assertIn("conflict", self.out_d)
        self.assertEqual(self.status(self.accepted), "accepted")
        self.assertEqual(self.status(self.discussed), "under_review")
        on_accepted = [d for d in self.tree.decisions() if c.curie(d.target) == self.accepted["id"]]
        self.assertEqual(sorted(d.status_before for d in on_accepted), ["accepted", "proposed"])

    def test_reimport_changes_nothing(self):
        before = self.snapshot()
        code, out = self.run_import(self.file_a, self.file_i)
        self.assertEqual(code, 0, out)
        self.assertIn("3 already imported", out)
        self.assertEqual(self.snapshot(), before)

    def test_renamed_target_followed_and_dry_run_writes_nothing(self):
        tree = c.Tree(self.ont)
        decided = {d.target for d in tree.decisions()}
        old = next(o for o, n in sorted(tree.renames.items()) if o.startswith("ast:")
                   and tree.status(c.expand(n)) == "proposed" and c.expand(n) not in decided)
        f = decision_file(self.inbox / "renamed.json", "Test Reviewer A",
                          [{"kind": "claim", "target": old, "decision": "reject", "note": NOTE, "date": TODAY}])
        before = self.snapshot()
        code, out = self.run_import(f, "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("1 new", out)
        self.assertIn("dry run: 1 decision(s) would be recorded", out)
        self.assertEqual(self.snapshot(), before)

    def test_malformed_file_refused_whole(self):
        bad = self.inbox / "bad.json"
        bad.write_text(json.dumps({"format": "marsad-review-decisions", "version": 1, "reviewer_id": reviewer_id("Test Reviewer A"),
                                   "decisions": [], "signed_by": "x"}), encoding="utf-8")
        unknown = decision_file(self.inbox / "unknown.json", "Test Reviewer A", [])
        data = json.loads(unknown.read_text(encoding="utf-8"))
        data["reviewer_id"] = "agt:" + "0" * 22
        unknown.write_text(json.dumps(data), encoding="utf-8")
        before = self.snapshot()
        code, out = self.run_import(bad, unknown)
        self.assertEqual(code, 1)
        self.assertIn("bad.json: REFUSED", out)
        self.assertIn("is not on the roster", out)
        self.assertEqual(self.snapshot(), before)

    def test_check_and_reapply_after_regeneration(self):
        f = self.ont / "corpus" / f"{self.accepted['file']}"
        original = f.read_text(encoding="utf-8")
        a = c.expand(self.accepted["id"])
        span, = c.locate_object(original, c.mask_turtle(original), str(a), str(c.MRS.assertionStatus), str(c.status_iri("accepted")))
        f.write_text(c.replace_term(original, span, str(c.status_iri("proposed"))), encoding="utf-8")  # as a regeneration would
        try:
            code, out = self.run_import("--check")
            self.assertEqual(code, 1)
            self.assertIn("out of step", out)
            code, out = self.run_import(self.file_a)  # nothing is imported while out of step
            self.assertEqual(code, 1)
            self.assertIn("Run --check, then --reapply", out)
            code, out = self.run_import("--reapply", "--no-validate")
            self.assertEqual(code, 0, out)
            self.assertEqual(f.read_text(encoding="utf-8"), original)
            self.assertEqual(self.run_import("--check")[0], 0)
        finally:
            f.write_text(original, encoding="utf-8")

    def test_status_without_decision_violates_rd4(self):
        thawr = self.ont / "examples" / "thawr.ttl"
        text = thawr.read_text(encoding="utf-8")
        tree = c.Tree(self.ont)
        claim = next(a for a in tree.assertions() if tree.source_of(a) == "thawr" and tree.status(a) == "proposed")
        span, = c.locate_object(text, c.mask_turtle(text), str(claim), str(c.MRS.assertionStatus), str(c.status_iri("proposed")))
        g = Graph()
        g += tree.vocab
        g.parse(data=c.replace_term(text, span, str(c.status_iri("accepted"))), format="turtle")
        g.parse(self.ont / "corpus" / "reviews.ttl", format="turtle")
        conforms, _, report = validate(g, shacl_graph=Graph().parse(self.ont / "shapes.ttl"), advanced=True, allow_warnings=True)
        self.assertFalse(conforms)
        self.assertIn("RD4", report)

    def test_roster_rejects_bad_rows(self):
        tree = c.Tree(self.ont)
        bad = self.tmp / "bad-roster.csv"
        for row in ["agt:TestReviewerZ000000000,Test Reviewer Z,scholar,topic:everything,2026-10-15,Test Maintainer,",
                    "agt:TestReviewerZ000000000,Test Reviewer Z,sheikh,source:stories-50,2026-10-15,Test Maintainer,",
                    "per:TestReviewerZ000000000,Test Reviewer Z,scholar,source:stories-50,2026-10-15,Test Maintainer,"]:
            bad.write_text(",".join(c.ROSTER_COLUMNS) + "\n" + row + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                c.load_roster(bad, tree)

    def test_unified_graph_conforms_after_import(self):
        res = subprocess.run([sys.executable, str(self.ont / "build_graph.py")], cwd=self.tmp, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stdout[-3000:] + res.stderr[-2000:])
        self.assertIn("CONFORMS", res.stdout)

    def test_zz_real_corpus_untouched(self):
        self.assertEqual(real_corpus_digest(), self.digest)


if __name__ == "__main__":
    unittest.main()
