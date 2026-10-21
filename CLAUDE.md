# al-Marsad: rules for every Claude Code session

## Saving GitHub Actions minutes (the Actions budget is $10 until the month resets)

- **Taste at home first.** Before every push, run what `.github/workflows/checks.yml` runs:
  `python3 -m pip install --require-hashes -r requirements.txt` once, then
  `bash scripts/check_all.sh` (it needs Node.js 22 and the `playwright` npm package with its
  headless Chromium; the workflow names the versions). Push once when the work is finished, not
  after every commit.
- Checks run on pull requests and on pushes to `main`; a push to any other branch runs nothing.
  A change that touches only notes (the `paths-ignore` list in `checks.yml`) runs nothing either.
  Before adding a file to that list, check that no build, test or site page reads it
  (`learn/tests` reads `docs/handover/slice-6-7*.md`, so those stay out).
