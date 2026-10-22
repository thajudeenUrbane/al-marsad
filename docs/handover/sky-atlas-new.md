# Sky Atlas (new): handover

**What.** Asked for by the maintainer, 17 October 2026: a new and separate Sky Atlas of al-Marṣad, with all the content developed so far and a guided-learning mode, not an extension of the earlier Sky or Sky Atlas. It lives in `atlas/` (see `atlas/README.md`) and follows `docs/handover/sky-guided-brief.md` where it applies. Branch `sky-atlas-new`, from `slice-11a-graph` (main plus the joined graph).

**Content.** The joined graph `build/graph-all.ttl`: 8,373 marks, 15,961 claims, all `proposed`, 0 reviewed. Through `site/observatory/obsdata.py`, unchanged, so statuses, sources and dates match the reader tier.

**Against the brief.**
1. Built from the graph, every string an i18n key, no external request, one file (2.2 MB with the data gzip-packed; the 2 MB site budget does not apply to a prototype island, and the page could load data in parts if it moves into `site/`).
2. H4: the Prophet ﷺ is the light at the centre in every view and never a mark; in Map it hangs above the land, in Book and Time above the scale, so it marks no place, page or date. H5: the Key says the stars are the project's metaphor, not a hadith. T4: generation by brightness only.
3. E3: default order as asked, from `atlas/data/lists.json` (proposed, with sources, matched by display name; the build stops on a name that matches none or several). Other sorts: A–Z, recorded links (labelled coverage), first named in the text. "Order of accepting Islam" is not offered: it is not recorded for most people.
4. X1: dark marks only from recorded claims (37 people); the turning toggle only where a claim says "accepted Islam later" (2). The edge cases of round 4 question 2 are not singled out: nobody is marked without a claim.
5. Guided mode: 192 events in the text's order, 44 dated events, the three journeys, the ten, the 50 Stories, opposition; tours from any record; three depths; next directions at every stop.
6. F14: connection stories appear only once approved; none is, so the page says so. Trace shows each step's claim and source.
7. W6/A2: no AI runs in the page. It chooses routes, cameras and next suggestions by fixed rules; every sentence is a claim with its source or an interface string.
8. W5: logbook and milestones (the learner's own exploring, never a person's rank); a place-centred tour ("Standing at…").

**Decisions to confirm.**
- *The text's order.* An event's place on the spiral is the median milestone of the claims that cite it. Its first mention is often an aside (Uḥud appears in an early genealogy), which put it before the Prophet's ﷺ birth. People and places in the Book view still sit at their first mention.
- *Lineage-only names* (5,554 people with only kinship claims) hang outside the events in the Sky and stay out of the tours (F11). A switch hides them.
- *Trace* never passes through the Prophet ﷺ (linked to almost everyone) or, by default, lineage-only names (F13's spirit; "same clan" wording is not yet added).
- *Recall* never marks an answer wrong: an absent claim is not a false one.
- *Lists*: the four by succession, the ten by the reports of ʿAbd al-Raḥmān b. ʿAwf (Tirmidhī, Manāqib 3747) and Saʿīd b. Zayd (Abū Dāwūd, Sunna 4649); the report numbers need checking against print.

**Known data issues the page makes visible.** Duplicates in the full layer (several al-Zubayr, Hāshim, al-Qāsim…) and kunya-only merges: in ʿAlī's lineage the light appears ten generations up through a merged name. Two Uḥud and two Badr events. These are slice 11a's merge proposals, not page bugs.

**Checks.** `atlas/tests` (11 tests), `atlas/check.cjs` (Playwright, desktop and 390 × 844: welcome, tour, search, record, study depth, lineage, trace, every view, every drawer tab, Arabic, no sideways scroll, no page error, no external request; all pass), the committed page matches a fresh build (byte-identical across hash seeds). All three are steps in `scripts/check_all.sh`.

## Round 2 (17 October 2026): every earlier feature, and more

Asked for by the maintainer: "Add all the features into new sky atlas. Don't miss anything", plus suggestions. Every one of the 31 features the earlier Sky Atlas had and this page lacked is now in it: the Stories, Transmission and Globe views (with arcs that grow with history), the blend slider, viewpoints, the five vantage points, Back and Home, flick inertia, the view in the address (a link-safe code, plus copy and open), links to the reader pages and Ask (when built with `--reader-base` / `--ask-url`), Play history, the period scrub, hollow undated marks, date ranges as bars and the generation band, shelves in every view, light by chain distance, the generation-light switch, distant stars, grouping, the test load with the GPU switch and speed readout (a Canvas 2D renderer now covers browsers without WebGL), absence on the sky, the full tour trail, tap feedback, the evidence summary, the ladder for an item and for a line, the panel's way back, why each journey stop was chosen, the full trace tool (several ranked threads, swap, copy link), the text view of the picture, the Arabic draft note and the `0` key. Generation shells stay out on purpose (T4).

New, suggested in the session: read aloud (the device's voice), compare two records, nine quests, entries that share a written name (shown, never merged; an Index filter), copy a citation or a list, classroom mode, a star chart that becomes *My tour*, and larger text.

Decisions to confirm: chain distance counts the 11 recorded chains and every `narrated_from` / `transmitted_to` claim (181 people), not only the chains; "same written name" sets aside text in brackets; quests and milestones count the learner's own exploring and never rank a person; a shared event in Compare is labelled as a fact about each person, not a recorded meeting.

Checks: `atlas/check.cjs` now walks every feature at desktop and 390 × 844 (all pass, no page error, no external request); the page script is split into `static/app/01-core.js` … `08-main.js`, joined by the build.

**Published.** As an Artifact (private until shared); the link is in `pages/README.md`.

## Round 3 (22 October 2026): Ask, the merge review, class notes

Chosen by the maintainer from the session's suggestions, with the Atlas onto `main` (PR #31) and the work board.

- **Adversarial questions first (rule A2).** `ask/golden/adversarial.jsonl`: 89 questions written to make the Ask engine do what it must not. They cover refusals in other words, a refusal hidden inside an answerable question, instructions aimed at the translator, hostile typed-in queries, names not in the graph, limits, and fair questions that must still be answered. `ask/tests/test_adversarial.py` runs them, and the parity test runs them through the browser port too. Nothing was answered that should not have been, but 22 were turned away as "not understood" instead of refused with their reason; new refusal patterns in `ask/rules.json` cover them. A question of punctuation only is now empty. The set is in-house: docs/07 §9 still asks for one written by people trying to break the engine, with published results.
- **Ask in the Atlas.** A tab in the drawer runs the same engine over the joined graph; no model. Answers light their names on the sky and open records. English questions only for now (the Arabic interface says so).
- **Merge review.** It overlaps the review pages' screen in PR #30 (the other session built it after this one was claimed; both read the same file). PR #30 records decisions through the roster and `review/import_decisions.py`, which is the governed path. So the Atlas keeps decisions in the browser as a working list (`MERGE_SHARED = false` in `static/app/09-shared.js`) and never writes a name into `decided_by`. **Decision to confirm:** keep both (the Atlas as the visual aid, or exporting decision files the importer reads), or only one.
- **Class notes** on every record: shared where the page is published with a shared store (editors write, all read), otherwise kept in the browser.

Checks: `atlas/check.cjs` walks Ask, the merge review and notes at both sizes; `atlas/tests` (12) checks that the page carries `ask/static/ask.js` unchanged and calls no model; `ask/tests` (all, with parity).
