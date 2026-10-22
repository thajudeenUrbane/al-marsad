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
| Sky Atlas onto main: merge main in, checks, one PR | `sky-atlas-new` | [session_01FqdCKi3xBmAaxFfcPL4rgu](https://claude.ai/code/session_01FqdCKi3xBmAaxFfcPL4rgu) | `atlas/`, `scripts/check_all.sh`, `README.md`, `LICENSING.md`, `pages/README.md` | building | 2026-10-22 |
| Sky Atlas: merge-review screen (slice 11a merge proposals; editor approves or rejects; review-decisions export) | `sky-atlas-new` | same | `atlas/` (reads `ontology/corpus/merge-proposals.csv`) | claimed | 2026-10-22 |
| Sky Atlas: shared class notes on stars | `sky-atlas-new` | same | `atlas/` | claimed | 2026-10-22 |
| Plain-language questions: adversarial tests first (rule A2), then rule-based translation in the Atlas | `sky-atlas-new` | same | `ask/` tests, `atlas/` | claimed | 2026-10-22 |
| Work board and the CLAUDE.md rule | `coordination`, `claude/workboard-rule` | same | `WORKBOARD.md`, `CLAUDE.md` | building | 2026-10-22 |

## Built, not merged (check before building anything like these)

| Work | Branch | Session | Notes | Updated |
|---|---|---|---|---|
| Sky Atlas: the whole joined graph as one guided sky, eight views, tours, history, threads, compare, quests, Arabic | `sky-atlas-new` | [session_01FqdCKi3xBmAaxFfcPL4rgu](https://claude.ai/code/session_01FqdCKi3xBmAaxFfcPL4rgu) | `atlas/`; published as an Artifact, link in `pages/README.md` on that branch | 2026-10-17 |
| Expeditions: five expeditions (Abyssinia, al-ʿAqaba, Hijrah, Badr, Uḥud) with terrain, computed sky, investigations, spaced review, review desk, halaqa room, WhatsApp packs | `expeditions` | [session_01CWyx8Z6Cd9Q5dJF4Ndramm](https://claude.ai/code/session_01CWyx8Z6Cd9Q5dJF4Ndramm) | `expeditions/` | 2026-10-17 |
| Badr Lab: prototype expedition (terrain, computed sky, the 314 investigation) | `lab-badr` | [session_01CWyx8Z6Cd9Q5dJF4Ndramm](https://claude.ai/code/session_01CWyx8Z6Cd9Q5dJF4Ndramm) | `lab/badr/`; also inside `expeditions` | 2026-10-17 |
| Lab: Hijrah Night (150 evidence-graded stages), Beyond the Graph strategy, partner and donor drafts, panel dock | `lab-hijrah-night` | [session_016x4WaWfmAmJ69fpCEdmNib](https://claude.ai/code/session_016x4WaWfmAmJ69fpCEdmNib) | `lab/` | 2026-10-20 |
| CI: raise the checks time limit from 30 to 60 minutes | `ci/raise-checks-timeout` | not recorded | `.github/workflows/checks.yml` | 2026-10-21 |
| Earlier Sky and Sky Atlas (superseded by `atlas/`) | `sky-observatory`, `sky-atlas` | not recorded | kept for reference | 2026-10-16 |

## Done (merged to main)

| Work | PR | Merged |
|---|---|---|
| CI speed: full-book file out of review test copies, one-pass identity audit, skip review steps on unrelated PRs | #27 | 2026-10-21 |
| Public readiness: draft and AI banner in README | #25 | 2026-10-21 |
| CI: check main and PRs only, skip notes-only changes; CLAUDE.md | #24 | 2026-10-21 |
| Slice 11a: the full Ibn Hishām layer joins one graph; merge proposals, audit sample, side claims | #22 | 2026-10-17 |
| Decisions round 3: maintainer answers; briefs for slice 11, the guided Sky, reader decisions | #21 | 2026-10-17 |
