# Slice 6–7 brief — learning paths and practice

Context, to read first (nothing else in the repo is the brief): README.md "Standing rules"; docs/13-platform-direction.md §4 slices 6 and 7; docs/05-ux-architecture.md §5 (journeys and story mode), §9, §10; docs/06-scholarly-methodology.md §2 and §10 (red lines); docs/handover/maintainer-answers-1.md and maintainer-answers-2.md (serious students first; young learners 15+ later; Discover = story first, Study = evidence first; reading never needs an account, progress stays on the device for now); docs/handover/slice-2a.md (how site/ works). Do not read chat history; this file is the brief.

## Do
1. **Journeys:** `learn/journeys/*.json` (or similar), each defined by selection rules over `build/graph.ttl`, not by hard-coded IDs or hand-written prose. Three drafts:
   - "The Hijrah, step by step": events that are part of or tied to the Hijra, ordered by recorded date, else by story order.
   - "The people of Badr": people with a recorded participation in Badr.
   - "The first believers": from the 50 Stories part on early Islam.
   Each journey is a DRAFT awaiting the maintainer's and the scholars' approval, and its page says so.
2. **Builder:** `learn/build_learn.py`, standalone (do not edit `site/build.py` or other site files), writes `site/dist/learn/`: a journey index and one page per journey. Each step links to its entity page and shows the status of the claims behind it. Progress is saved on the device with localStorage (wrapped in try/catch; the page works fully without it). Reader-tier budget ≤300 KB; works with JS off (progress is the only JS feature). Own i18n file `learn/i18n/en.json`; logical CSS; reuse `site/display.py` and link the site CSS rather than copying it.
3. **Practice (slice 7):** `learn/practice.py` generates questions only from relationships between `accepted` claims (e.g. "Who was present at both X and Y?"), each answer linked to its sources. Today no claim is accepted, so the bank is empty, and the practice page says plainly that questions appear only after scholars accept claims. Unit tests with fixture graphs prove that no `proposed`, `under review` or `rejected` claim can ever produce a question.
4. Tests under `learn/tests`.

## Done when
Three draft journeys build from the graph; practice is tested and honest about being empty; budgets met; the JS-off check passes. Handover `docs/handover/slice-6-7.md` (≤60 lines): what a learner can do, the journeys and their selection rules, what needs approval.

## Scope
`learn/**` (new) and `docs/handover/slice-6-7*.md` only. Linking from the home page happens at integration. Others are changing `site/` (search) and adding `site/interactive/`, `site/observatory/`, `review/`, `ingest/`, `ask/` and CI in parallel.

## Rules
AI never asserts. Never upgrade a status. Never invent names, dates or summaries. No model names or model IDs in any repo file. Never hard-code entity IDs (slice 1e re-mints 16 IDs, including the Prophet ﷺ, Abū Bakr and Badr). Every UI string is an i18n key.

## Finish
1. Checks: `ontology/build_graph.py` conforms; `site/build.py`, then the learn builder; `python -m unittest discover -s learn/tests`; a Playwright JS-off check of the journey pages.
2. Commit messages end with the attribution lines you are given.
3. Rebase on `origin/main`, rebuild, re-run the checks, commit fixes. Push the slice branch only (never `main`); do not open a PR.
