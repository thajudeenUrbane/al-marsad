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
