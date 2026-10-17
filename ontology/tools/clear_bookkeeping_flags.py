#!/usr/bin/env python3
"""
Clear the identity flags that were only ID bookkeeping (maintainer answers round 3, P9).

    .venv/bin/python ontology/tools/clear_bookkeeping_flags.py     # apply (idempotent)

32 needs-review rows of ontology/corpus/identity.csv were flagged only because of the
slice-1a ID problems that slice 1d fixed by re-minting (review/common.py sorts their note
parts). The maintainer decided to clear those flags without scholar time:
- the 20 entity rows take the confidence their own evidence gives (review/common.py,
  queued_confidence: 'probable' for the two label merges, 'exact' otherwise);
- the 12 groups of the 50 Stories stay needs-review with a different question for the
  scholars: is this a real tribe, clan or group the sources name, or only a description?
Each changed row's note records the change. Nothing else in the table is touched.
"""

import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "review"))
import common as rc  # noqa: E402

IDENTITY = ROOT / "ontology" / "corpus" / "identity.csv"
CLEARED = "slice 11a (17 Oct 2026): ID-bookkeeping flag cleared by the maintainer's decision (round 3, P9)"


def main():
    text = IDENTITY.read_text(encoding="utf-8")
    rows = list(csv.DictReader(io.StringIO(text)))
    fields = list(rows[0].keys())
    cleared = groups = 0
    for r in rows:
        if r["confidence"] != "needs-review" or CLEARED in r.get("note", ""):
            continue
        q = rc.queued_confidence(r)
        if q == "needs-review" or q == r["confidence"]:
            continue
        if r["kind"] == "group":
            r["note"] = (r["note"] + " | " if r["note"] else "") + CLEARED + " | " + rc.REAL_GROUP_NOTE
            groups += 1
        else:
            r["confidence"] = q
            r["note"] = (r["note"] + " | " if r["note"] else "") + CLEARED
            cleared += 1
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    IDENTITY.write_text(buf.getvalue(), encoding="utf-8")
    print(f"{cleared} entity flags cleared; {groups} groups now ask whether they are real groups")
    return 0


if __name__ == "__main__":
    sys.exit(main())
