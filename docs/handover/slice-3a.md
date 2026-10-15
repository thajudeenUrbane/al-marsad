# Slice 3a handover — review data model, queue and importer (no UI)

Spec: docs/handover/slice-3-brief.md, part 3a. No status moved in the real corpus: all 549 claims stay `proposed`, and `ontology/corpus/reviews.ttl` ships with no decision. Nothing invented: test reviewers, notes and citations say they are fixtures.

## Model (marsad.ttl, shapes.ttl)
- `mrs:ReviewDecision` ⊑ `crm:E13_Attribute_Assignment`, `prov:Activity`. It has `reviewedBy` (a `prov:Person` with an opaque `agt:` ID), `reviewTarget`, `reviewOutcome` (`ro_accept` / `ro_reject` / `ro_needs_discussion`), `checkPerformed` (`rc_report_in_source`, `rc_chain_sound`, `rc_summary_fair`, `rc_identity`), `reviewNote`, `reviewDate` (xsd:date), `sourceCitation` and `tradition`. It also has either `statusBefore` + `statusAfter` (a claim) or `identityQuestion` (an identity row). It is not an `mrs:Evaluation`, and no Passage is faked.
- `mrs:tradition_first_board` is the first board's lens: `mrs:declaredDefault true`, prefLabel "Sunni, across the four madhhabs, coordinated initially by Shāfiʿī scholars", and a comment saying it is a declared default, not neutral.
- Shapes RD1–RD6: one human reviewer, never a SoftwareAgent; one target, outcome, date and lens; the status follows the outcome; RD5: accepting a claim with no Report needs `sourceCitation`; RD6: needs discussion needs a note; RD4: in a graph that holds `mrs:ReviewLog` (reviews.ttl, so the unified graph), every accepted, rejected or under-review claim needs a human decision that set that status. `TraditionShape`: at most one declared default, no tradition labelled "neutral". A corpus file validated alone is unaffected.

## Queue: `review/build_queue.py` writes `review/dist/queue.json` (gitignored, deterministic)
- 549 proposed claims in 97 batches: 50 story batches (one per story, in order), 45 person batches (sorted by name) and 2 file batches. Any batch over 50 is split; the Prophet ﷺ's is 50 + 14.
- Each unit holds: id, the claim in plain words, subject/predicate/object (identity.csv names, Arabic where present), qualifiers, the doc's own wording, its basis verbatim, status, file, topic and period. It also has the flags `ai_generated_basis` and `citation_required_to_accept`, and lists earlier decisions. Passages are verbatim in `passages` (English, and Arabic where the graph has it).
- The identity queue holds needs-review rows as "same as?" questions. Today it is empty: all 32 rows are ID bookkeeping (see For a human). `--identity-confidence needs-review,probable` adds the 18 `probable` rows and the two label merges among the 32 (ʿĀʾisha, Makkah): 20 real identity questions.
- The queue builder refuses to run while corpus statuses disagree with reviews.ttl, so decided claims are not sent back to the scholars.

## Importer: `review/import_decisions.py [files]` (default `review/inbox/*.json`)
- The whole file is refused if it is malformed, its reviewer is not on the roster, or it names a target twice.
- One decision is refused, with a message, if: a field is bad or the target unknown; the reviewer has no grant active on that date whose role and scope fit; it accepts without a required citation; it is needs discussion without a note; it holds a roster name, email or phone number; the same reviewer already decided the target differently; or it disagrees with a decided claim (that goes to the board). A decision that agrees with a decided claim is recorded and changes nothing.
- How a decision is applied: it is appended to reviews.ttl with a minted `rvw:` ID. One status triple is swapped in the file that states it; the edit is located in the text and checked by re-parsing. The tool validates reviews.ttl and, when a status moved, the whole graph as build_graph.py builds it. It writes nothing unless everything conforms.
- Re-importing changes nothing. `--dry-run` writes nothing. `--check` exits 1 on drift. `--reapply` restores reviewed statuses after a regenerated file. Exit codes: 0 ok, 1 refused/drift, 2 cannot run.

## Decision file (3b's pages produce this)
```json
{"format": "marsad-review-decisions", "version": 1, "reviewer_id": "agt:<22 base62>",
 "created": "<optional>", "queue": "<optional: queue.json fingerprint>",
 "decisions": [{"kind": "claim|identity", "target": "<unit id from queue.json>",
   "decision": "accept|reject|needs_discussion", "checks": ["report_in_source", "chain_sound", "summary_fair", "identity"],
   "note": "<optional; required for needs_discussion; max 4000>", "date": "YYYY-MM-DD",
   "citation": "<optional; required to accept a unit with citation_required_to_accept; max 500>"}]}
```
No other fields are allowed. `checks` may be empty or left out.

## Roster: `review/roster.csv` (gitignored; copy `review/roster.example.csv`, which has the header only)
- Columns: reviewer_id (`mint_id.py agt`), name, role (docs/06 §3.1), scope, granted_on, granted_by, revoked_on (optional). One row per grant.
- Who may decide: reviewers and scholars decide claims; editors may also decide identity rows.
- Scope is a list of grants separated by `;`. Each grant is space-separated conditions, all of which must hold: `source:<file stem>`, `topic:<relation class|identity>` or `period:A..B` (CE years; an undated claim never matches). Example: `source:stories-50; topic:kinship period:570..661`.

## Verify (all pass)
`scripts/check_all.sh` (all 18 steps) · `.venv/bin/python ontology/build_graph.py` (CONFORMS) · `ontology/validate.py` on each of corpus/{generation-1,seed-incidents,stories-50,reviews}.ttl and examples/thawr.ttl (CONFORMS) · `.venv/bin/python -m unittest discover -s review/tests` (16 tests, about 2 min, on a temporary copy; the real corpus is checked byte-identical) · site build and site tests still pass · `review/build_queue.py` · `review/import_decisions.py --check` · `identity_audit.py --check` · `stories50_to_ttl.py --check`.

## For a human
1. **Identity flags to clear.** 32 needs-review rows are flagged only for slice-1a ID bookkeeping. `build_queue.py --list-excluded` prints their IDs and reasons.
   - 20 are the collision rows slice 1d named: al-Bukhārī, al-Layth b. Saʿd, al-Zubayr, Anas b. Mālik, Ibn Shihāb al-Zuhrī, Muṣʿab b. ʿUmayr, Saʿd b. Muʿādh, Yaḥyā b. Bukayr, ʿAlī, ʿUmar, ʿUqayl b. Khālid, ʿUrwa b. al-Zubayr, ʿUthmān, ʿĀʾisha, Ḥamza, al-Ḥudaybiyya, Makkah, Uḥud and the two route waypoints. ʿĀʾisha and Makkah become `probable` label merges once cleared.
   - 12 are the 50 Stories groups, whose only flag is the slice-1a hash ID (re-minted in 1d). They have no "same as?" question, so I left them out too; say if they should be asked.
2. **Citation rule.** It applies to every claim with no real source in the graph (all 549 today, including generation-1 and seed claims, which say "pending scholarly citation"), not only the 50 Stories. Relaxing it is a change to `has_real_source` and RD5.
3. **Generated files.** `stories50_to_ttl.py` always writes `proposed`. After the first real import, its `--check` fails, and regenerating resets statuses. The generator should read reviews.ttl; until it does, run `import_decisions.py --reapply` after regenerating.
4. **CI.** scripts/check_all.sh (outside this slice's files) passes as it is. It should also uncomment its `review: tests` line and add `step "review: statuses agree with reviews.ttl" "$PY" review/import_decisions.py --check`.
5. **ID tooling.** `identity_audit.py` scans only the four original .ttl files; it should also cover reviews.ttl (`rvw:` and `agt:` IDs). mint_id.py already does. docs/02 §5.2.1 should list `rvw:` = `https://w3id.org/marsad/id/review/`. The ontology version was not bumped.
6. **Changing a decision.** For now, a reviewer's change of mind goes through you, and a disagreement goes to the board (3c). Identity decisions are only recorded: nothing is merged, and identity.csv is untouched.
7. **The roster.** Fill in names and scopes on your machine. The importer prints the roster name for each file so you can check who sent it; names are never written to the repo.
