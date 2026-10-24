# al-Marṣad work board

Every Claude Code session that works on this repository reads this board before it starts, claims its work here, and updates its row when it pushes or stops. This branch holds only this file, so pushing here runs no checks (CI runs on `main` and pull requests only). The rule is in `CLAUDE.md` on `main`.

**How to use it**

1. `git fetch origin coordination && git show origin/coordination:WORKBOARD.md`
2. If your task overlaps a row under *In progress*, stop and tell your user which row and session; do not redo it.
3. Otherwise add a row under *In progress* (work, branch, session link, what it touches, date) and push: `git fetch origin coordination`, edit on top of `origin/coordination`, `git push origin HEAD:coordination`. If the push is rejected, fetch, re-apply your one-line change and push again.
4. When you push your work, open a PR, or stop, update your row's status. Move finished work to *Done*.
5. Edit only your own rows. A row with no update for 7 days may be marked `stale (date)` by anyone; never delete another session's row.
6. Before building something new, check *Done* and *Built, not merged* so it is not rebuilt.

Keep each row to one line. Status words: `claimed`, `building`, `in review (PR #n)`, `paused`, `stale`, `done`.

## In progress

| Work | Branch | Session | Touches | Status | Updated |
|---|---|---|---|---|---|
| Sky Atlas round 3: Ask adversarial set + refusal patterns (`ask/`), Ask tab, Merges tab as a study aid (review pages record decisions), class notes | `sky-atlas-round3` | [session_01FqdCKi3xBmAaxFfcPL4rgu](https://claude.ai/code/session_01FqdCKi3xBmAaxFfcPL4rgu) | `ask/`, `atlas/` | in review (PR #35) | 2026-10-24 |
| Preview refresh (Observatory, Lifelines), scholar pilot pack, Khadīja fix check, identity questions for scholars | `fixes/pilot-and-corrections` | [session_01EbeK4zbgeZZ2BG7bPF3LPF](https://claude.ai/code/session_01EbeK4zbgeZZ2BG7bPF3LPF) | `review/`, `docs/handover/` | done (PR #33, merged 24 Oct; row updated by the hub, session archived) | 2026-10-22 |
| Slice 11b: the reader site on the joined graph (thread file per person, a page per letter for long lists, long records in parts, sharded search, redirects for retired IDs). Not in it: F13 "same clan" (belongs to the Atlas trace / Ask path), F11 background layer (needs period data) | `slice-11b-site` | [session_016qVqtfhyhh4S1yN49wjcyi](https://claude.ai/code/session_016qVqtfhyhh4S1yN49wjcyi) | `site/` (not `learn/`, not `ask/`), `ontology/shacl_check.py` | paused: WIP pushed (13dfc2f); budget passes; site tests and the other views on the joined graph still to fix | 2026-10-22 |
| **Hub session**: the only open al-Marsad session since 24 Oct. The other nine sessions are archived and their work is pushed; route every new task here | none | [session_01MMFsjHHmzvhvLhM5s4NpnH](https://claude.ai/code/session_01MMFsjHHmzvhvLhM5s4NpnH) | none | active | 2026-10-24 |
| Learning lab: `expeditions` + `lab-hijrah-night` in one branch; drafts kept out of the repo | `learning-lab` | [session_01MMFsjHHmzvhvLhM5s4NpnH](https://claude.ai/code/session_01MMFsjHHmzvhvLhM5s4NpnH) | `expeditions/`, `lab/` | done (PR #32, merged 22 Oct) | 2026-10-24 |
| Round-4 question sheet: published to the maintainer (13 questions, 6 starred); answers to be recorded as `docs/handover/maintainer-answers-4.md`. Slice 11b resumes after R1 | none | [session_01MMFsjHHmzvhvLhM5s4NpnH](https://claude.ai/code/session_01MMFsjHHmzvhvLhM5s4NpnH) | artifact; later `docs/handover/` | waiting on the maintainer | 2026-10-24 |
| Maintainer decision, 22 Oct: merge review lives in the **review pages** (PR #30). The Atlas merge-review screen is dropped and Atlas class notes are paused; the hub schedules them | none | [session_01MMFsjHHmzvhvLhM5s4NpnH](https://claude.ai/code/session_01MMFsjHHmzvhvLhM5s4NpnH) | none | decided | 2026-10-22 |
| learn-v2: one shared journey format in `learn/` (step layers, three depths, view-state links, new step kinds) that the reader pages, the Sky's guided mode and Expeditions can all play; brief `docs/handover/learn-v2-brief.md` | `learn-v2` | [session_01H6nc9zUEjqmVk9eCFtt5ss](https://claude.ai/code/session_01H6nc9zUEjqmVk9eCFtt5ss) | `learn/`, `docs/handover/learn-v2*.md`; keeps the `learn/journeys.py` interface that `atlas/build.py` imports | in review (PR #34); merges main and commits a rebuilt atlas/index.html (no Atlas source change) | 2026-10-23 |
| Housekeeping: cost table off the strategy page; checks time limit 35 min | `hub/housekeeping` | [session_01MMFsjHHmzvhvLhM5s4NpnH](https://claude.ai/code/session_01MMFsjHHmzvhvLhM5s4NpnH) | `lab/beyond-the-graph/`, `.github/workflows/checks.yml` | done (PR #36, merged 24 Oct) | 2026-10-24 |
| Hub merges, 22–24 Oct: #30, #31, #32, #33, #36, #34, #35, #37 (all with the maintainer's OK). No open PRs | none | [session_01MMFsjHHmzvhvLhM5s4NpnH](https://claude.ai/code/session_01MMFsjHHmzvhvLhM5s4NpnH) | none | done | 2026-10-24 |
| Exhibition requests for atlas/ and lab/ (from the exhibition session, 24 Oct): **1** Arabic Atlas empty sky: FIXED in main (PR #37, merged 24 Oct; the exhibition can drop its runtime CSS). **4** the Badr count label: goes with **2** (its English text comes from learn-v2's journey lead). **2** A13 wording: waits on the maintainer's round-4 D1/D2. **3** B14 "الحاكم": needs a native speaker or scholar. **5** rebuild the Atlas after the exhibition's P1 corpus fixes merge: tell the hub. **6** hijrah-night-v2 (Qurʾān grade chips, H1 honorifics, the Abū Ṭālib line) and **7** vendoring three.js: put to the maintainer | none yet | [session_01MMFsjHHmzvhvLhM5s4NpnH](https://claude.ai/code/session_01MMFsjHHmzvhvLhM5s4NpnH) | `atlas/`, `lab/hijrah-night-v2/` | 1 done (#37); 2,3,4,6,7 with the maintainer | 2026-10-24 |
| After the exhibition, P1 data fixes (exhibition-audit-scholar.md): generation-1 A5, A6, A7, B11 (fix, or a "prototype, order not yet checked" banner); corpus A8 Usāma's expedition reversed (seed-incidents.ttl:1482), A9 Kaʿb b. Mālik at Tabūk (:613), B1 "full sisters" (generation-1.ttl:797), B8 Abū Dujāna's headband (:1228); then rebuild generation-1 and the Atlas | none yet | [session_01MMFsjHHmzvhvLhM5s4NpnH](https://claude.ai/code/session_01MMFsjHHmzvhvLhM5s4NpnH) | `generation-1/`, `ontology/corpus/`, `atlas/` | after the meeting; the maintainer schedules | 2026-10-24 |
| After the exhibition: full rebuild of `expeditions/dist` with its five downloads (terrain tiles, OpenITI Ibn Hishām text, HYG star CSV, astronomy-engine, Pillow); steps in exhibition-build-expeditions.md and exhibition-build-dist.md | none yet | [session_01MMFsjHHmzvhvLhM5s4NpnH](https://claude.ai/code/session_01MMFsjHHmzvhvLhM5s4NpnH) | `expeditions/` | needs the maintainer's OK for the downloads | 2026-10-24 |
| Before raising CI's Playwright above 1.56.1: add a favicon to site/dist (or ignore its 404) for the interactive, observatory and lifelines checks; review/check_pages.py download wait times out on 1.62.1 | none yet | [session_01MMFsjHHmzvhvLhM5s4NpnH](https://claude.ai/code/session_01MMFsjHHmzvhvLhM5s4NpnH) | `site/`, `review/` | backlog (CI green today) | 2026-10-24 |
| Maintainer calls from the exhibition: C7 Badr 313 tagged "attested" (expeditions/defs/expeditions.json:136); C8 "Who was there" → "Who the text places here" (expeditions/app/app.js:123); Atlas glosses on Khadīja's record; J2–J11 (exhibition-build-review.md); thawr.ttl sourceDate 256 AH; a scholar on the demo report's ascription; site/experiments.py wrap() adds a second charset to stories-50 (exhibition-build-p1-demo.md) | none | [session_01MMFsjHHmzvhvLhM5s4NpnH](https://claude.ai/code/session_01MMFsjHHmzvhvLhM5s4NpnH) | none | for the round-5 sheet | 2026-10-24 |

## Built, not merged (check before building anything like these)

| Work | Branch | Session | Notes | Updated |
|---|---|---|---|---|
| Expeditions: five expeditions (Abyssinia, al-ʿAqaba, Hijrah, Badr, Uḥud) with terrain, computed sky, investigations, spaced review, review desk, halaqa room, WhatsApp packs | `expeditions` | [session_01CWyx8Z6Cd9Q5dJF4Ndramm](https://claude.ai/code/session_01CWyx8Z6Cd9Q5dJF4Ndramm) | `expeditions/` | 2026-10-17 |
| Badr Lab: prototype expedition (terrain, computed sky, the 314 investigation) | `lab-badr` | [session_01CWyx8Z6Cd9Q5dJF4Ndramm](https://claude.ai/code/session_01CWyx8Z6Cd9Q5dJF4Ndramm) | `lab/badr/`; also inside `expeditions` | 2026-10-17 |
| Lab: Hijrah Night (150 evidence-graded stages), Beyond the Graph strategy, partner and donor drafts, panel dock | `lab-hijrah-night` | [session_016x4WaWfmAmJ69fpCEdmNib](https://claude.ai/code/session_016x4WaWfmAmJ69fpCEdmNib) | `lab/` | 2026-10-20 |
| CI: raise the checks time limit from 30 to 60 minutes | `ci/raise-checks-timeout` | not recorded | `.github/workflows/checks.yml` | 2026-10-21 |
| Earlier Sky and Sky Atlas (superseded by `atlas/`) | `sky-observatory`, `sky-atlas` | not recorded | kept for reference | 2026-10-16 |

## Done (merged to main)

| Work | PR | Merged |
|---|---|---|
| Exhibition for a scholar-leader (meeting 24 Oct): the offline eight-hall walk in `exhibition/` and the P0 fixes (#38); the Hijrah demo and stories-50 from P1 (#39). After the meeting: the rest of P1 (`generation-1/`, `ontology/corpus`) and the full `expeditions/dist` rebuild, now the Hub's backlog rows under *In progress* | #38, #39 | 2026-10-24 |
| Sky Atlas: the whole joined graph as one guided sky (onto main) | #31 | 2026-10-22 |
| Merge proposals for every person (908) + merge-review cards in the review pages | #30 | 2026-10-22 |
| Work board (`coordination` branch) and the CLAUDE.md rule | #29 | 2026-10-22 |
| CI speed: full-book file out of review test copies, one-pass identity audit, skip review steps on unrelated PRs | #27 | 2026-10-21 |
| Public readiness: draft and AI banner in README | #25 | 2026-10-21 |
| CI: check main and PRs only, skip notes-only changes; CLAUDE.md | #24 | 2026-10-21 |
| Slice 11a: the full Ibn Hishām layer joins one graph; merge proposals, audit sample, side claims | #22 | 2026-10-17 |
| Decisions round 3: maintainer answers; briefs for slice 11, the guided Sky, reader decisions | #21 | 2026-10-17 |
