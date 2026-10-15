# Slice 8 brief — ask the graph

Saved verbatim from the session brief (15 October 2026). Branch: `slice-8-ask`.

## Read first
README.md "Standing rules"; docs/13-platform-direction.md (§2 D4: no live AI per visitor yet; §4 slice 8); docs/07-ai-architecture.md (all, especially §1–§5, §9, §10); docs/05-ux-architecture.md §3 (search modes, empty-state rule); docs/06-scholarly-methodology.md §10 red lines; docs/handover/maintainer-answers-1.md and maintainer-answers-2.md; docs/handover/slice-2a.md (how site/ works).

## Goal
A plain-language question becomes a typed query in a small DSL; the DSL runs against the graph; the answer is a list or small graph view with the claims behind it and their status. Questions about rulings, fatwa, interpretation of scripture, ranking people by religious significance, or anything doc 07 §5 / doc 06 §10 forbid are refused politely with the reason. No model is called at runtime.

## Do
1. `ask/dsl.py` + `ask/DSL.md`: the typed query DSL from doc 07 §4 (if doc 07 leaves gaps, design the smallest DSL that covers the examples in doc 05 §3 and doc 07). Parser, validator, executor over build/graph.ttl returning rows with the assertion behind each row and its status.
2. `ask/translate.py`: deterministic plain-language → DSL for common question shapes (who was at X; who was at both X and Y; relatives of X; events at place P; …) with spelling-tolerant name lookup (import the site's normaliser from site/display.py if present; do not copy), and the refusal classifier. Leave a clean interface for a model-backed translator later (not implemented).
3. `ask/build_ask.py` (standalone; do NOT edit site/build.py or other site files): writes site/dist/ask/ with a compact JSON index and a page where a visitor types a question; the deterministic translator + executor run in the browser (port the logic to JS and test parity with Python on the golden set), or answers come from a precomputed cache; with JS off the page shows the cached questions and answers. ≤2 MB. Own i18n file ask/i18n/en.json; logical CSS.
4. `ask/golden/questions.jsonl`: about 30 questions with expected DSL and expected answer rows, labelled "pending scholar check" (doc 13 requires a scholar-checked golden set); plus refusal cases. Tests run them all.
5. Wording: never present a `proposed` claim as fact ("recorded, not yet reviewed by scholars").

## Done when
Tests pass (Python and JS parity), the golden set passes, the page works with JS on and off. Handover docs/handover/slice-8.md (≤60 lines). Save this brief as docs/handover/slice-8-brief.md.

## Scope
`ask/**` (new), `docs/handover/slice-8*.md`. Linking from the home page happens at integration.

## Project rules
AI never asserts; never upgrade a status; never invent names, dates or answers; no model names or IDs in any repo file; never hard-code entity IDs (slice 1e re-minted 16 IDs; golden answers name entities by label and resolve at test time); every UI string an i18n key.

## Parallel work
Others are changing site/ (search, including the normaliser in site/display.py), adding site/interactive/, site/observatory/, review/, ingest/, learn/ and CI.

## Finish
1. Checks: `ontology/build_graph.py` CONFORMS; `site/build.py` then the ask builder; `python -m unittest discover -s ask/tests`; JS parity test; a Playwright check of the ask page with JS on and off.
2. Commits end with the session's attribution lines.
3. `git fetch origin main && git rebase origin/main`; rebuild; re-run checks; commit fixes.
4. Push the branch (`--force-with-lease` only on this branch after the rebase). Never push to main, never open a PR.
