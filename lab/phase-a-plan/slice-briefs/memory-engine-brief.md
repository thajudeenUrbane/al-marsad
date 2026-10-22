# Memory engine brief — guess first, recall, spaced review, your sky

Context: README "Standing rules"; lab/beyond-the-graph (N4; "Learner" layer; experiments 2 and 9); learn/ (existing journeys and practice); docs/handover/maintainer-answers-3.md (E5, H4, X1, T4); lab/phase-a-plan/PLAN.md (pilot 1 needs). Do not read chat history; this file is the brief. Build on the scene packs and question banks of `moments-layer`.

## Build
1. **Learner model, on the device.** An FSRS-style scheduler per item (person, place, moment). Storage is local, every read and write wrapped in try/catch; the world works with storage blocked. No accounts (E5).
2. **Guess first.** Each scene asks before it tells. A seeded pilot flag switches the prompt on or off per chapter (experiment 2).
3. **Recall.** At the end of each chapter: cued and free recall. After the attempt, the claim and its source are shown; a wrong choice is explained by the claim behind the distractor (e.g. ʿUmar emigrated earlier, §665).
4. **Spaced review.** A list of what is due. No streaks, no points, no leaderboards.
5. **Your sky.** Everyone met is a star that brightens with recall. The Prophet ﷺ is the light, never a star or node. Opponents are stones; merged people are one star.
6. **Pilot support.** A pilot code tags sessions; learner state exports to a file a researcher collects. No names stored. A reading-page control built from the same scene packs: same claims, order and citations, no world, no guess-first.

## Done when
Unit tests for the scheduler and recall scoring; a Playwright check at 390×844 with storage blocked and allowed; the control page builds in CI; steps added to `scripts/check_all.sh`. Handover `docs/handover/memory-engine.md` (≤60 lines).

## Rules
AI never asserts; every answer and explanation is a claim with its source; computed ≠ significant (no scores presented as rank); learner data stays on the device; no model names or IDs in the repo.
