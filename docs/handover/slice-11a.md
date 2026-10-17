# Slice 11a handover: one graph, the full Sīra joined and cleaned (data)

Brief: docs/handover/slice-11-brief.md, part 11a. Maintainer decisions: docs/handover/maintainer-answers-3.md (chapter F, G5, G6, P8, P9, S6). Every claim is still `proposed`. Nothing was merged; the text itself is not committed.

## What changed
- **Joined.** `ontology/corpus/ibn-hisham-full.ttl` (moved from `corpus-full/`) is in the graph.
  - `build_graph.py` writes `build/graph-all.ttl` (the joined graph) and `build/graph.ttl` (what the pages, Ask and views read). `ON_HOLD_FROM_PAGES` keeps the full layer off the pages until slice 11b.
  - Checking at this size: each file is checked on its own and the verdict is cached by checksum (`ontology/shacl_check.py`, one SHACL pass instead of two). The joined graph is checked where files meet. A build takes about 2½ minutes; a whole check of the large file takes about 30 minutes and runs only with `--full`, `validate.py FILE` or `CHECK_FULL_SIRA=1`.
- **Story events are not events.** The full pass had linked 1,141 claims to 16 events of the AI-written 50 Stories ("The Battle of Badr" = story 20). They now point at the historical events: 10 existing, 6 minted needs-review. The fix is `ingest/fix_story_events.py`, recorded in `docs/CHANGELOG-data.md`.
- **Added by rule** (`ingest/sira_derive.py`, which writes `ingest/claims/ibn-hisham-full-derived.jsonl` from the cached text and the committed offsets):
  - **Sides (F1):** 537 claims, each "fought alongside" or "fought against" the Prophet ﷺ, with `mrs:atEvent` Badr or Uḥud. Each rests on the person's listing and on Ibn Isḥāq's own words that open the list. Nobody is on both sides; the 7 men counted at Badr without being there get none.
  - **Formulas (F5):** 1,135 of 1,250 narrations carry the formula as written and its mode: `mrs:narrationFormula`, plus `mrs:narrationMode` (ḥaddatha or samiʿa = samāʿ, ʿan = ʿanʿana, the rest unspecified). The formula chosen is the one followed by the narrated-from person's name. Spot checks: about 1 in 40 wrong.
  - **Voice (F7):** 12,863 claims are marked Ibn Isḥāq or Ibn Hishām. Ibn Hishām's voice covers only the paragraph his "qāla Ibn Hishām" opens. Where it cannot be told, no voice is recorded.
  - **Poetry doubts:** 60 claims carry the qualifier `poem_doubted_in_passage`.
  - New vocabulary in `marsad.ttl` and `shapes.ttl`: `atEvent`, `Voice`, `voice`, `voiceCarried`, `narrationFormula`, `narrationMode`.
- **Count checks (F2).** `ingest/count_checks.py` compares 11 totals the text gives with the graph and writes `ingest/claims/ibn-hisham-full-counts.json`.
  - Matching: Uḥud martyrs 65, Uḥud's slain 22, first ʿAqaba 12.
  - One name short: second ʿAqaba (74 of 75) and the Badr captives (42 of 43).
  - Badr (321 against 314, with 22 in Ibn Hishām's voice) and Abyssinia (87 against 83 men; the list names women too) need an editor.
  - `review/build_queue.py` lists the mismatches under `count_checks`. They are questions, so they carry no decision.
- **Merge proposals (F3).** `ontology/tools/propose_merges.py` writes `ontology/corpus/merge-proposals.csv`: 59 rows (18 events, 29 people, 12 royal titles) with evidence and confidence (probable / possible / scholar).
  - An editor fills in `decision`; the maintainer approves; applying an accepted row (old ID → variant, old address redirects) is slice 11b.
  - Story events are never proposed as historical events, and a bare single name is never matched on.
- **The scholars' queue.** The 7,885 rows the full pass created are new entries, not "same as?" questions, so they are left out of the identity queue (they go through merge proposals). The queue holds 180 "same as?" questions plus 12 "is this a real group?" questions (P9).
- **Small fixes.**
  - P9: 20 bookkeeping flags cleared (`ontology/tools/clear_bookkeeping_flags.py`).
  - G6: Khadīja is now "mother of" Fāṭima. `generation-1/build.py` shows mother-of ties, and Ask golden g18 is updated.
  - S6: al-Thurayya's rows moved to `external-ids-althurayya.csv` (CC BY 4.0); the site reads both files and offers both downloads; `link_external.py` writes the split.
- **Audit (F4).** `ingest/audit_sample.py`:
  - `sample` draws 400 claims (seed 20261017, at least 5 per relation, the rest in proportion).
  - `sheet` writes a local page, `ingest/cache/audit.html`, which quotes the text.
  - `report` gives the rate per relation and a weighted overall rate with 95% intervals, from `ingest/claims/ibn-hisham-full-audit-results.csv`, which the editor saves from that page.

## Not done here
- **F12 offices.** The royal titles are proposed as `title` rows for scholars. Modelling an office with its holders needs their ruling on who held which title, so nothing was changed.
- **F10 Nasab Quraysh.** This is an editor's task; nothing in code.
- **The whole check of `ibn-hisham-full.ttl`.** It was last run in full before this slice. The 1,725 new and changed claims were checked against it (conform). Run `CHECK_FULL_SIRA=1` once before 11b.

## For a human
1. The editor works through `merge-proposals.csv`, the audit sheet and the 8 count-check mismatches. Publish the audit rate (F4).
2. The new derive, count and audit steps need the cached text. CI does not fetch it, so they are run locally, like `ingest/ibn_hisham.py check`. CI could run `ingest/ibn_hisham.py fetch` first.
3. Ask, learn and the views still read `build/graph.ttl`, without the full layer, until 11b.

## Verify
`ingest/ibn_hisham.py check all`, `ingest/sira_derive.py check`, `ingest/count_checks.py --check`, `ontology/tools/propose_merges.py --check`, `ontology/tools/identity_audit.py --check`, `ontology/build_graph.py` (CONFORMS), `scripts/check_all.sh`.
