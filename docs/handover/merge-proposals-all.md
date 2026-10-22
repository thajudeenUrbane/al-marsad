# Merge proposals for every person (follow-up to slice 11a, F3)

Slice 11a proposed merges for events, royal titles and the 100 most-connected people: 59 rows.
`ontology/tools/propose_merges.py` now compares **every person with a recorded claim**, by the same rules,
so `ontology/corpus/merge-proposals.csv` holds **908 proposals**:

- events: 7 probable, 11 scholar (as before);
- people: **193 probable** (same name and the same recorded father, and the same grandfather where
  both record one), **197 possible** (same name, one side records no father, or only one entry carries
  a note telling namesakes apart), **488 scholar** (kunya only, different fathers or grandfathers, or
  notes that tell namesakes apart);
- titles: 12 scholar (as before).

All 59 earlier rows are still there with the same confidence. Proposal numbers (M0001 ...) are
renumbered, because rows are sorted by kind, confidence and name; no decision had been written yet.
Decisions are kept by `keep_id` + `merge_id`, so later runs never lose them.

One rule was tightened: a single name is never matched on. Before, a compound ism counted as two words,
so every bare ʿAbd Allāh in the book was proposed against every other. Now ʿAbd X, X Allāh (ʿUbayd
Allāh) and Imruʾ al-Qays count as one name, like ʿAmr or Kaʿb.

Nothing is merged. As F3 and P8 say: an editor fills in `decision`, the maintainer approves, and
applying an accepted row (the old ID becomes a variant and its address redirects) is slice 11b's work.
Suggested order for the editor: the 193 `probable` people first (mostly the same person under two
spellings or with a "(2)" suffix from the full pass), then `possible`, and send `scholar` rows on.

Verify: `ontology/tools/propose_merges.py --check`.

## The merge-review screen

The review pages now carry the undecided proposals as "Same entry?" questions, so the editor decides on
a phone or laptop instead of editing the CSV.

- `review/build_queue.py` adds `merges` to the queue: one batch per kind and confidence (events first,
  then probable and possible people, then the scholars' rows), 25 cards per page. Each card shows both
  entries (name, Arabic form, ID, files), up to 8 relations the Ibn Hishām layers record for each, and
  the evidence for the proposal.
- The choices are the usual three: Accept (one entry), Reject (different), Needs discussion (to the
  scholars; a note is required).
- `review/import_decisions.py` takes `"kind": "merge"` decisions, with the target `keep_id|merge_id`.
  The reviewer needs an **editor** or **scholar** grant whose scope covers the two entries (for example
  `topic:identity`). The decision, the reviewer's opaque ID, the date and the note go into the four
  decision columns of `ontology/corpus/merge-proposals.csv` (needs discussion is written as
  `scholar`). **No Turtle file changes, and nothing is merged.** A proposal already decided is refused;
  a change goes through the maintainer. A decided row leaves the queue.
- `propose_merges.py` keeps all four decision columns when it re-runs.

To start: add the editor to `review/roster.csv` (role `editor`, scope `topic:identity`), run
`review/build_pages.py`, and send the pages. When the decision files come back, run
`review/import_decisions.py` on them.

Tests: `review/tests/test_review.py` (an editor's accept and needs discussion are written, a reviewer is
refused, a bare needs discussion is refused, a re-import changes nothing, no Turtle file changes) and
`review/tests/test_pages.py` (the cards show both entries and the evidence).
