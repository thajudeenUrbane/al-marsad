# learn-v2 brief — one journey format for every way of learning al-Marṣad

Context: README "Standing rules"; docs/05-ux-architecture.md §5–6; docs/handover/slice-6-7.md (learn v1); docs/handover/maintainer-answers-3.md (G1, E1, E3, E4, E6, F11, F14, H1, L1, L2, W5, W6, X1); docs/handover/sky-guided-brief.md; docs/handover/reader-r3-brief.md. Do not read chat history; this file is the brief.

## Why
Guided learning is to be the main way into al-Marṣad: a learner should be able to reach every person, event, place, story, report and tool through journeys, from the first plain step to the evidence underneath. Today three surfaces each model journeys their own way: the Learn pages (`learn/journeys.py`, rules over the graph), the Sky's guided mode (`atlas/`, which imports `learn/journeys.py`) and Expeditions (`expeditions/` and `lab/hijrah-night-v2/`, moving to `learning-lab`). learn-v2 makes `learn/` the one source of journeys that all three play, so a journey is chosen once, reviewed once and shown everywhere.

## Decisions (maintainer, 22 October 2026; round 3 wins where they differ)
1. **Narration.** Sentences generated from claims by templates, plus short prose only after the maintainer and the review board approve it. AI may draft prose; the draft is labelled "AI draft" until approved.
2. **Method journeys** (how to read al-Marṣad, how each tool works) may be written by hand, for tools and method only. Any historical example in them comes from the graph by rule, with its source.
3. **Teacher lessons** (records chosen by hand) are kept apart from journeys, labelled "a teacher's lesson, not reviewed", and never listed among journeys unless the board approves one.
4. **Practice feedback** never says "wrong" or "not there": "The record does not place them at both, as far as reviewed claims go", with a link to what is recorded. Graded practice only from accepted claims; prompts of any status are never graded; no multiple choice.
5. **Story mode** opens per journey when the board decides; the share of accepted claims is shown to the board as a guide.
6. **50 Stories records** may place a person on a journey, always labelled as coming from that document (AI-generated, not reviewed).
7. **"Part of the Hijrah"**: proposed claims for Arrival in Madinah and the Second Pledge of al-ʿAqaba go to the board for review; until accepted they are not added by software.
8. **Round 3 wins.** Discover (the public depth) shows no review status or review language, only the source line (work and page), until round 4 question 1 is answered (G1, G8); status appears in Study and Research. People follow the E3 order: the Prophet ﷺ, al-Khulafāʾ al-Rāshidūn, the ten promised Paradise, then by number of recorded links, labelled as coverage in the sources and never rank; membership comes from a reviewed list file with its source, never from IDs in code; those recorded as having died as disbelievers come last. The graph has no recorded term for that yet, so nobody is placed last until round 4 question 2 gives one; until the list file is reviewed, the order is the Prophet ﷺ, then A–Z. The background layer stays out of journeys (F11). Quests and milestones may come later, gradually, without compromising accuracy (W5).
9. **Name and scope.** This work is learn-v2 (slice 11 is the joined graph). It builds the shared format in `learn/`; the Sky's guided mode stays with the Atlas session, and Expeditions read the same export.

Unchanged rules: journeys are chosen by rules, never by hand (except method text, decision 2); a journey is a draft until the maintainer and the review board approve it, and software never writes that approval; never hard-code entity IDs; no model names or IDs in repo files; pages work with JavaScript off; reading never needs an account.

## The plan: guided learning as the main way in
Every learner, from a newcomer at Discover to a researcher, should be able to start at the Learn home and reach every record and every tool through journeys. Three layers make that possible:

1. **One format** (this PR). A journey is a rule file. One engine chooses and orders its stops, and one resolver writes it as `marsad-journey` JSON: stops, why each is there, the claims behind it with their sources, narration as templates bound to claims, ungraded prompts, a checkpoint from accepted claims only, next directions and view hints, all chosen by rule. Every surface plays that document: the reader Learn pages at three depths, the Sky's guided mode, Expeditions.
2. **Coverage.** Generated short journeys for every record (an event's who, when, where, before, after, and how we know; a person's life; a place), and a CI check that every record can be reached from the Learn home. Curated tracks sit on top:
   - **Track 0, how to read al-Marṣad:** what a claim is, the source line, a report and its chain, dates in two calendars, the light and the generations, absence is not silence, the depths, and each view and tool.
   - **Track 1, the Seerah end to end:** the Makkan period, the Hijrah, early Madinah, the battles, Ḥudaybiyya, Khaybar, the Conquest, Ḥunayn and al-Ṭāʾif, Tabūk, the Farewell Pilgrimage, the Prophet's ﷺ death and the succession. The fitna period waits for the board (round 2 R6).
   - **Track 2, people:** the first believers, the Prophet's ﷺ household, the people of each battle and pledge, one life per Companion.
   - **Track 3, places:** Makkah, Madinah, the routes, the globe.
   - **Track 4, transmission:** how a report travelled, on the 11 recorded chains.
   - **Track 5, the stories:** the 50 Stories in their four parts, replaced gradually by stories built from accepted claims (G2).
3. **The learning loop.** Prompts lead to the evidence and are never marked. Graded practice comes from accepted claims only. What a learner explored stays on their device, so a returning learner sees what changed since their last walk. Quests and milestones may be built later on the same stops (W5).

### Order of work (owners as on the work board, 22 October 2026)
| Step | What | Owner |
|---|---|---|
| **learn-v2** (this PR) | The shared format, the export, three depths with layers on the reader pages, E3 order and side groups, F11 exclusion, the decision-6 proposals file | this session (`learn-v2`) |
| learn-v2b | New step kinds with data today (place, chain, dispute, compare), Track 0 method journeys, the Learn home as a course map, the coverage check | next learn session |
| learn-v2c | life, period and family kinds (after slice 11b's background marker), Arabic learn pages and Arabic narration templates, the free-recall checkpoint and spaced review (shared with Expeditions' memory), the approved prose layer | later learn session |
| Sky guided mode plays the export | `resolve_all(site)` or `site/dist/learn/data/`; story-mode gate; G1 at its public depth | Atlas session (`sky-atlas-new`, PR #31) |
| Expeditions read the export | a `#j-<slug>~<pid>` route next to `#x-<slug>` | learning-lab |
| Reader pages on the joined graph | no learn code change needed; `LEARN_JOINED=1` proves it | slice 11b |
| Teacher lessons, story mode, quests, Ask leading to a journey | after the board opens each; Ask only after published adversarial tests (A2) | later |

## This PR: learn-v2
The design is `docs/handover/learn-v2-design.md`; the format contract is `learn/FORMAT.md`.

**Builds:** the v1 rule language plus optional keys (`lead_study`, `story_mode`, `lists`, `hold_study`, `select.group_by`, `named.phrase`, `named.not_words`); approvals bound to a hash of the rule; `learn/journey_lists.py` and `learn/lists/people.json` (E3, names only, both lists unreviewed); `learn/journey_export.py` (the `marsad-journey` export, the CLI and the Atlas projection) and `learn/facade.lock`; the reader pages at Discover, Study and Research, split under the budget; the Hijrah Study page held as v1 (`hold_study`) for the class (E1); `learn/i18n/ar.json` (titles and leads); `learn/proposals/hijrah-parts.json` (decision 7, for the board).

**Does not touch** `site/`, `ontology/`, `atlas/`, `expeditions/`, `lab/`, `ask/`, `scripts/` or `.github/`.

## Done when
- The three journeys build on the page graph with their v1 stops and order (Badr's Study order unchanged while the list file is unreviewed), and on the joined graph (`LEARN_JOINED=1`) within the budget.
- Discover pages show no review status or review language, and every sentence on them has a work-and-page source; Study and Research show the status of every claim.
- The Hijrah Study page matches its v1 golden hash; `atlas/build.py`'s import works unchanged and `learn/facade.lock` is current.
- Two builds under different hash seeds are byte-identical; `learn/tests`, `learn/check_nojs.cjs` and `scripts/check_all.sh` pass.
- Handover `docs/handover/learn-v2.md` (60 lines or fewer).

## Rules
AI never asserts. Never upgrade a status. Never invent names, dates or IDs; never hard-code entity IDs. No model names or IDs in any repo file. Software never writes an approval. Commit messages end with the attribution lines given in the session.
