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

## Working alongside other sessions

- **Before starting work**, read the work board, issue #28 (what other sessions are doing), the open
  pull requests, and `git log origin/main` (what has landed). If the work is claimed or done, stop and
  tell the user.
- **Claim it** with a comment on #28: `STARTING: <what>`, the branch and the session link.
  **Close it** with `DONE: <what>` and the PR number, or `STOPPED: <what>` and why.
