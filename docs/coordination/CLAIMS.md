# Claims ledger — who is doing what

Every cloud session reads this file before starting work, and writes to it when it starts and when it stops. The point is to avoid two sessions building the same thing.

## Protocol

1. **Pull first.** `git fetch origin && git checkout main && git pull` (or read `origin/main:docs/coordination/CLAIMS.md`), then read this file.
2. **Check for overlap.** Look at the open rows and at `git branch -r`. If a row covers your task, do not start it. Message the owner (see below) or ask the user.
3. **Claim before coding.** Add one row under *Active* with the task, your branch, the files you expect to touch, and today's date. Push the claim to main on its own commit, so the claim is visible before any code exists.
4. **Keep the row current.** Set the status to `in progress`, `blocked: <reason>` or `handed over: <where>`.
5. **Finish.** Move the row to *Done* with the merged PR or commit. Nothing stays in *Active* after its branch is merged or abandoned.
6. **Freezes** (below) override claims. A session may not claim work inside a frozen area.

Columns: `task | branch | files | owner | since | status`. *owner* is the session's title or the person who started it, not a model name.

## Freezes

| Area | Frozen since | Until | Reason |
|---|---|---|---|
| New visual or sky work (`sky-atlas*`, `sky-observatory`, `lab-*`, `expeditions`) | 22 Oct 2026 | the ledger has an owner for each open branch | Two `sky-atlas` branches and a `graph-type-identification` session overlap. Pick one base before anything new starts. |

## Active

| task | branch | files | owner | since | status |
|---|---|---|---|---|---|
| Public prototype and role invitations (artifact, not in repo) | — | — | project owner | 22 Oct 2026 | in progress: shared with board and partners by the owner |
| Ledger set-up | uncommitted in working tree | `docs/coordination/CLAIMS.md` | this session | 22 Oct 2026 | in progress: awaiting commit approval |

## Open branches with no owner yet

These exist on `origin` but no session has claimed them. An owner must claim one before anyone builds on it.

- `sky-atlas`, `sky-atlas-new`: duplicates; a base must be picked (see Freezes)
- `sky-observatory`, `lab-hijrah-night`, `lab-badr`, `expeditions`: no current session
- `public-readiness`, `ci/raise-checks-timeout`: CI and readiness work; check PR state before touching
- `slice-11a-graph`, `sira-full-pass`, `decisions-round-3`: data work; slice 11a is the next data task
- `slice-4-int`, `slice-4-ingest`, `slice-9-arabic`: earlier slices, probably merged; confirm before reuse

## Done

| task | merged as | date |
|---|---|---|
| CI speed fix (30-minute timeout down to 14–18 minutes) | PR #27 | 21–22 Oct 2026 |
