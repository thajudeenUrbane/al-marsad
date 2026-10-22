# al-Marsad: rules for every Claude Code session

## Saving GitHub Actions minutes

- **Taste at home first.** Before every push, run what `.github/workflows/checks.yml` runs:
  `python3 -m pip install --require-hashes -r requirements.txt` once, then
  `bash scripts/check_all.sh` (it needs Node.js 22 and the `playwright` npm package with its
  headless Chromium; the workflow names the versions). Push once when the work is finished, not
  after every commit.
- Checks run on pull requests and on pushes to `main`; a push to any other branch runs nothing.
  A change that touches only notes (the `paths-ignore` list in `checks.yml`) runs nothing either.
  Before adding a file to that list, check that no build, test or site page reads it
  (`learn/tests` reads `docs/handover/slice-6-7*.md`, so those stay out).

## Before you start: the work board

Several Claude sessions work on this repository, in parallel and one after another. To avoid
building the same thing twice, every session uses the work board, `WORKBOARD.md` on the
`coordination` branch (that branch holds only the board, so pushing to it runs no checks).

- **Read it first**, before planning: `git fetch origin coordination && git show origin/coordination:WORKBOARD.md`.
  Check *Built, not merged* and *Done* as well as *In progress*: a feature may already exist on a
  branch that is not merged yet.
- **If your task overlaps a row in progress**, stop and tell your user which row and which
  session; do not redo it. You can message that session if it is still running.
- **Claim your work** with one row (work, branch, session link, what it touches, status, date)
  and push it to `coordination` before you start building. **Update the row** when you push, open
  a PR or stop; move finished work to *Done*.
- Edit only your own rows. Mark a row with no update for 7 days `stale (date)`; never delete
  another session's row. The board's own header says how to push to it.
