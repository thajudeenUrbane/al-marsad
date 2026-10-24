"""
Tests for the pilot pack (review/pilot_pack.py): which batches it picks, and that the
selection keeps only those batches.

    .venv/bin/python -m unittest discover -s review/tests

A small made-up queue is enough here; the pages themselves are tested in test_pages.py.
"""

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

REVIEW = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REVIEW))
import pilot_pack as pp  # noqa: E402


def batch(name, kind, n):
    return {"batch": name, "kind": kind, "title": name, "units": [{"id": f"{name}-{i}"} for i in range(n)]}


QUEUE = {
    "format": "marsad-review-queue", "version": 1,
    "claims": [batch("story-01", "story", 20), batch("person-x", "person", 9),
               batch("story-02", "story", 25), batch("story-03", "story", 10), batch("story-04", "story", 4)],
    "identity": [batch("identity-p1", "identity", 50), batch("identity-p2", "identity", 30)],
    "count_checks": [{"key": "badr"}],
}


class PilotPack(unittest.TestCase):
    def test_default_is_story_batches_to_fifty_then_first_identity_batch(self):
        self.assertEqual(pp.default_batches(QUEUE), ["story-01", "story-02", "story-03", "identity-p1"])

    def test_select_keeps_only_the_chosen_batches(self):
        picked = pp.select(QUEUE, ["story-02", "identity-p2"])
        self.assertEqual([b["batch"] for b in picked["claims"]], ["story-02"])
        self.assertEqual([b["batch"] for b in picked["identity"]], ["identity-p2"])
        self.assertEqual(picked["count_checks"], [])
        self.assertEqual(len(QUEUE["claims"]), 5, "the queue it was given is left alone")

    def test_unknown_batch_is_refused(self):
        with self.assertRaises(ValueError):
            pp.select(QUEUE, ["story-99"])

    def test_zip_is_the_same_every_time_and_holds_the_guide(self):
        with tempfile.TemporaryDirectory() as tmp:
            pages = Path(tmp) / "pages"
            pages.mkdir()
            (pages / "index.html").write_text("<p>x</p>", encoding="utf-8")
            (pages / "queue.json").write_text("{}", encoding="utf-8")
            a, b = Path(tmp) / "a.zip", Path(tmp) / "b.zip"
            pp.write_zip(pages, a)
            pp.write_zip(pages, b)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            self.assertEqual(sorted(zipfile.ZipFile(a).namelist()), ["GUIDE.txt", "index.html"])


if __name__ == "__main__":
    unittest.main()
