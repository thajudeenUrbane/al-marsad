# Slice 6–7 handover: learning paths and practice

Spec: docs/handover/slice-6-7-brief.md. Nothing shown is verified history: every claim is still `proposed`, every journey a draft. No status was upgraded; no name, date or summary was written. No entity ID appears in `learn/` (a test checks every file against the graph).

## What a learner can do (site/dist/learn/, no account, works with JS off)
- Open **Learn**: three journeys, each marked Draft, and a practice page.
- Walk a journey step by step. Each step links to its entity page and shows its coverage and the status and source of every claim behind it; event steps also say why the step is there and where its place in the order comes from.
- Read how each journey was chosen: the rules are printed in plain words from the journey file itself.
- With JS on, tick steps "Done": progress is kept in this browser only (localStorage, every access in try/catch); with storage refused the page simply has no boxes.
- Practice: today it says plainly that there are no questions yet, because questions are made only from claims scholars have accepted, and none are (0 of 549).

## Files
`learn/journeys/*.json` (rules), `journeys.py` (rule engine, reads the graph through site/model.py), `practice.py` (question bank), `render_learn.py`, `build_learn.py`, `templates/`, `i18n/en.json` (learn keys; frame, status and date words come from site/i18n/en.json), `static/learn.css` (logical properties) and `learn.js` (progress only, no text in it), `check_nojs.cjs`, `tests/` (58 tests). Reuses site/display.py, site/model.py and the site stylesheet; no site file was changed.

## The journeys and their rules (graph of 15 October 2026, after slice 1e)
1. **The Hijrah, step by step** (Study: evidence first). Events and stories whose recorded name contains "Hijra" or "Hijrah", plus the events recorded as part of them and the events their own recorded dates are placed before or after, up to 2 links away. Links are walked in named directions only: an event merely dated "after the Hijra" does not join (the engine also offers "wholes" and "event_claims"; neither draft uses them). Order: recorded dates and before/after links; a part follows its whole; else dated steps by date, then story order, then name. Each step says which applied. Today 6 steps: The beginning of the Hijra migrations; The Hijra: departure from Makkah, via Ghar Thawr; Departure from Makkah and Sheltering at Ghar Thawr (its parts); Arrival at Quba' (the cave's date is recorded as before it); story 14, The Hijrah and the Cave of Thawr. Steps 1–2 and 5–6 have no recorded order between them and say so.
2. **The people of Badr** (Study). People with a participation record, or a "participated in / led / present at / witnessed" claim, on an event or story whose name contains "Badr" (Battle of Badr; stories 20 and 37), or on their recorded parts. "Absent from" claims are shown beside, never used to choose (Uthman, Talha, Sa'id b. Zayd have both). People whose every record carries the 50 Stories marker "accepted Islam later" are listed apart (al-Abbas, Abu al-As). Order: the Prophet ﷺ first, then A–Z; the page says the order is not a ranking. Today 27 steps + 2 apart.
3. **The first believers** (Discover: story first). The stories of the 50 Stories part whose title contains "Makkan" (Part 1, 13 stories) in reading order, each with "Read the story" and, one tap below, the people and groups it names with their status.
All three pages carry the draft banner and the AI note (they draw on the AI-generated 50 Stories document). The Hijrah and Badr pages also say that a story and an event with a similar name are separate records (stories-50.ttl leaves that alignment to scholars).

## Practice (slice 7)
`practice.bank()` joins two claims whose status is exactly `accepted`: "Who is recorded as having participated in (led / present at / witnessed) both X and Y?" and "In which events are both A and B recorded …?". A claim that is proposed, under review, rejected, superseded, unstated or has two statuses never helps make a question; participation records (no status) never do. Any "absent from" claim that is not rejected or superseded removes that person from the answer. No multiple choice (a wrong option would assert an absence). Each answer lists its claims with status, source and links; the bank is also written to `learn/practice/bank.json`; over 40 questions it pages. Tests: fixed cases for every status, 400 random graphs checked against a brute-force oracle, 200 more with "accepted" swapped for each other status (always empty), and a fixture build that renders accepted questions with their sources.

## Numbers
Heaviest learn pages: first believers 63,288 bytes (HTML 48,744 + site.css + learn.css + learn.js), people of Badr 62,615, Hijrah 50,511, index 20,378, practice 13,528; budget 300,000.

## Verify
`.venv/bin/python ontology/build_graph.py` (CONFORMS) `&& .venv/bin/python site/build.py && .venv/bin/python learn/build_learn.py && .venv/bin/python site/check_html.py site/dist && .venv/bin/python site/check_budget.py site/dist` (all OK, 326 pages).
`.venv/bin/python -m unittest discover -s learn/tests` (58 OK, including a two-process determinism check); site tests still 64 OK; `scripts/check_all.sh` (main with slice 2c): all 17 steps pass (it does not run the learn steps yet, see 6).
`NODE_PATH="$(npm root -g)" PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers node learn/check_nojs.cjs site/dist`: JS off, all 5 pages complete (steps, links, a status on every claim, progress hidden, no request off localhost); JS on, a ticked step survives reload, shows on the index and clears; storage refused, no errors and no boxes. OK.

## Needs approval or a decision
1. **Each journey's rules** (maintainer and review board). Approval goes in the file's `approved_by` (who: maintainer / review_board, date) with `status: approved`; validation refuses `approved` without both. Software never writes it.
2. Hijrah: Arrival in Madinah and the Second Pledge of al-Aqaba are not linked to the Hijra by any claim, so they are not steps. A reviewable "part of" claim would bring them in.
3. Badr: whether story-based records (AI-generated document) should count; the set-apart rule; the "Prophet ﷺ first" convention.
4. First believers: the title covers all 13 Makkan-period stories (not only story 2, "The First Believers"); story lists name narrators too (shown with their role text). Narrow the rule, or wait for the stories' review.
5. Practice wording and the two question types; the rule that any live "absent from" claim removes a person.
6. Integration (outside this slice's scope): site/build.py deletes site/dist, so learn/build_learn.py runs after it. In scripts/check_all.sh, add `step "learn: build" "$PY" learn/build_learn.py` right after "site: build" (the site's budget and HTML checks then cover the learn pages), a JS-off step running `node learn/check_nojs.cjs site/dist` like `nojs_check`, and `step "learn: tests" "$PY" -m unittest discover -s learn/tests`. Link Learn from the home page; the index lists journeys by file name.

Not in this slice: saved progress across devices (needs accounts and a backend, R5), the young-learner mode (R7, later), a teacher's journey builder (doc 05 §6.2), story mode (ships last, doc 05 §5).
