# learn-v2 handover: one shared journey format

Brief: docs/handover/learn-v2-brief.md. Design: docs/handover/learn-v2-design.md (its §20 says where the build differs). Contract: learn/FORMAT.md. Nothing shown is verified history: every claim is still `proposed`, every journey a draft, the list file and the proposals `proposed`. No status was upgraded and software writes no approval, status or story mode (a test keeps every rule and list file byte-identical). No entity ID or model name appears in learn/ or these notes (tests scan them). Only learn/ and docs/handover/learn-v2*.md changed.

## What a learner can do (site/dist/learn/, no account, works with JS off)
- Open **Learn** (depth-neutral) and walk each journey at three depths, each its own static page: **Discover** (public), **Study**, **Research**. Depth links land on the page holding the same stop; long depths split into pages with a pager and a contents list.
- **Discover** shows a sentence only when a claim behind it gives a work and page, with that short source line ("Ibn Hishām, al-Sīra al-Nabawiyya, vol. 1, p. 485"), and never a status, a banner or review words. A stop with no such claim says so and points to Study. The 50 Stories document is labelled "a document generated with AI" at every depth.
- **Study** (Hijrah's is the held v1 page) adds the status of every claim, the draft note, narration from claim templates (attributive: "The record says…"), ungraded prompts that open onto the evidence, next directions, the accepted share and the list state. **Research** adds claim IDs, labelled AI glosses, who recorded each claim, the data files, rule_sha, content_sha, the graph fingerprint and what the rule left out (F11).
- Ticking "done" (JS on) is kept in this browser and shared by every page and depth of a journey. Practice is unchanged: 0 questions, because none of the 953 claims is accepted.

## Files
`learn/journeys/*.json` (v1 rules plus optional v2 keys), `journeys.py` (engine, v1 facade kept, FACADE_VERSION 2), `journey_lists.py` + `lists/people.json` (E3 lists, names only), `journey_export.py` (marsad-journey v1 export, CLI, Atlas projection), `facade.lock`, `FORMAT.md`, `render_learn.py`, `build_learn.py`, `templates/`, `static/`, `i18n/en.json` and `ar.json` (journey titles and leads), `proposals/hijrah-parts.json` (decision 7), `check_nojs.cjs`, `tests/` (268 tests; the 23 in test_joined.py run only under LEARN_JOINED=1).

## The journeys and their rules (page graph, fingerprint 808a048b0c16)
1. **The Hijrah, step by step** (door Study, `hold_study`: the Study page is the v1 page for the E1 class, guarded by a golden hash). Events and stories named Hijra or Hijrah, plus their parts and date anchors up to 2 links; recorded order. 7 steps; 9 on the joined graph.
2. **The people of Badr** (door Study). People with a participation record or a participated/led/present/witnessed claim at events named Badr but not "expedition" or "raid", and their parts; "absent from" is shown, never chooses; "accepted Islam later" records set apart. Order E3: while the list file is unreviewed, the Prophet ﷺ then A–Z (not a ranking). `group_by: side`: people recorded, with a work and page, as fighting against the Prophet ﷺ at the event come after the others under their own heading, which says it is the event's side only, nothing about faith. 92 steps (+2 apart), against group empty; joined 438 (+1), against group 79. Nobody is placed last for faith.
3. **The first believers** (door Discover). The Makkan part of the 50 Stories in reading order. 13 steps.
Background (F11) is never a seed or a step: events after the Prophet's ﷺ death, coarse year-632 events ("not placed") and events before 570.

## For the other surfaces
Atlas: `atlas/build.py` imports work unchanged; its output changes on purpose (Discover-safe leads; on the joined graph Badr has 4 anchors, not 9, and the 79 come after the others). Whichever of learn-v2 and PR #31 merges second rebuilds atlas/index.html once; `facade.lock` and the build's facade line say when. Gate Play and read-aloud on `spec["story_mode"]["open"]` (all closed). Atlas and Expeditions read `site/dist/learn/data/` or run `learn/journey_export.py --graph build/graph-all.ttl --out DIR`, and at a public depth show only `discover` claims with their short source. Expeditions needs its own route (`#j-<slug>~<pid>`).

## Numbers
- Page graph, pages Discover / Study / Research: first-believers 1/1/1, Hijrah 1/1/1, Badr 1/2/2. Heaviest learn page: Badr Research page 1, 256,975 B with assets (229,624 B HTML); budget 300,000. Export: 14 files, digest 5974256887e2; facade 18b41847880a. rule_sha (what an approval names): first-believers a918944231ff, Hijrah bcbdff55f02d, Badr fa1f23da270e.
- Joined graph (LEARN_JOINED=1, fingerprint c99b3100aba6, reader site and learn built in a scratch folder in 168 s): Badr 4/8/10 pages, the other two 1/1/1; heaviest learn page Badr Research page 6, 268,377 B; Badr in 10 parts, the largest 149,913 B (budget 150,000), head 211,095 B; facade 22cf577d7c35. check_html passes on the whole joined site and check_nojs on its learn pages. The reader tier's own pages there are not learn's: 15,768 of 16,814 (entity pages, search and the site's study and research hubs, in both languages) are over check_budget's limits, for slice 11b.

## Verify
`.venv/bin/python site/build.py && .venv/bin/python learn/build_learn.py` (prints the lines above), `.venv/bin/python site/check_html.py site/dist` (1027 pages OK), `.venv/bin/python site/check_budget.py site/dist` (OK), `NODE_PATH="$(npm root -g)" PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers node learn/check_nojs.cjs site/dist` (OK at every depth; progress across pages and depths; storage refused stays inert), `.venv/bin/python -m unittest discover -s learn/tests` (268 tests OK, of which 23 skipped: the joined test), and from learn/tests `LEARN_JOINED=1 ../../.venv/bin/python -m unittest test_joined -v` (23 OK). scripts/check_all.sh already runs the learn build, browser check and tests.

## Needs approval or a decision (round-4 sheet)
1. **Each journey's rule** (maintainer and review board): `{who, date, spec: <rule_sha>}` with `status: approved`, written by people. A changed rule or title makes the approval stale. Story mode opens per journey by the board, the same way.
2. **The list file** `learn/lists/people.json`: the rāshidūn need a work-and-page source (null now: the Atlas's points to unsourced background events); the ten's hadith numbers need checking against print. Then both roles approve `sha12(lists)` and Badr gets the E3 tiers. Its single home: recommended this file, read by the Atlas, which retires its own copy.
3. Badr: the side group and its wording (or keep the side as a sentence per step); `not_words [expedition, raid]`.
4. Discover: stops with no work-and-page claim shown with the no-work line (2 Hijrah, 1 Badr); entity dates and places shown as fields (round 4 Q1); no provenance cue beyond work and page; draft journeys listed without a draft word.
5. Order of accepting Islam (exported, not rendered) and "died as disbelievers, last", which waits for a recorded term (round 4 Q2).
6. Hijrah E1: lift `hold_study` when the class run ends; then consider Discover as its door.
7. F11 provisional rule: year-632-only events (the Farewell Pilgrimage, Usāma's appointment) are "not placed" until slice 11b's marker.
8. Decision 7: `learn/proposals/hijrah-parts.json`, proposals 1–5 together (1–2 alone list Arrival in Madinah before the departure; 5 moves the council); on the joined graph also which Hijra event is the whole.
9. Decision 4 wording "as far as reviewed claims go", kept word for word.
10. Arabic (L3): the `lead_study` drafts; the Badr Arabic lead, copied from the Atlas, is shorter than the English one.
11. CI: `paths-ignore docs/handover/[a-r]*.md` skips the ID scan on docs-only edits to these notes (every PR touching learn/ still scans them).

Deferred: Track 0 method journeys, teacher lessons (refused by `validate`), the approved prose layer, new step kinds (place, chain, dispute, compare; life, period and family after slice 11b), Arabic learn pages and narration templates, the free-recall checkpoint (empty: 0 accepted), an accepted-only resolve (public mode `accepted` stops the build), the other sorts on reader pages, G5 `was` aliases, the Atlas's move to `resolve_all`.
