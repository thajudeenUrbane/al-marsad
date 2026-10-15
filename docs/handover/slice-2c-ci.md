# Slice 2c-ci handover: continuous checks and deploy

Spec: docs/handover/slice-2-brief.md, 2c items 2 and 3. No data, status, page or check was changed; this slice only runs them.

## What runs
- `scripts/check_all.sh` is the one list of checks; people and CI run the same script. In order: build the graph (must conform); identity audit; stories-50.ttl is current; validate each .ttl in ontology/corpus and ontology/examples on its own; rebuild demo, generation-1 and stories-50 and fail if their committed files change (`git diff`) or new ones appear; build the site; page budget; HTML checks; JS-off browser check; site unit tests; every workflow action pinned to a commit SHA. A failing step does not stop the others; a PASS/FAIL/SKIP summary comes last; exit 1 if any step failed.
- `.github/workflows/checks.yml`, job **All checks**, runs it on every push and pull request: Ubuntu 24.04, Python 3.13.16, Node 22.23.3, Playwright 1.56.1 with its headless Chromium. Python packages come from `requirements.txt`: the dev venv's exact versions (rdflib 7.6.0, pyshacl 0.40.1 and their six dependencies), hash-checked.
- Job **Deploy to Cloudflare Pages** runs only for a push to main of this repository (never a pull request, never a fork), after All checks passed. It publishes the very `site/dist` that was checked, with wrangler 4.145.0 (`wrangler pages deploy`). Without both secrets it prints "Deploy skipped" and stays green. Project name: repository variable `CLOUDFLARE_PAGES_PROJECT`, default `al-marsad`. Only wrangler sees the token: that job has no checkout and no Python.
- Every run on main also keeps the built site for 7 days as a download (artifact `site-dist` on the run's page).
- First run (branch slice-2c-ci): All checks passed, 51 s for the checks, about 2 minutes in total; deploy skipped (not main).

## Run it locally
`scripts/check_all.sh` (about 90 s). Python: `$PYTHON`, else `.venv/bin/python`, else (in a git worktree) the main checkout's `.venv`, else `python3`; it warns when versions differ from requirements.txt. The JS-off check needs Node 22 and the `playwright` package (found via `npm root -g`, or `NODE_PATH`) and its browsers (`PLAYWRIGHT_BROWSERS_PATH`, or /opt/pw-browsers when present). New machine: `python3 -m pip install --require-hashes -r requirements.txt`, then `npm install -g playwright@1.56.1` and `npx playwright@1.56.1 install chromium`.
A new module adds one `step "name" command` line to the list at the end of the script; commented placeholders are there for review/, learn/, ask/, site/interactive/ and site/observatory/.

## For the maintainer: turning on the deploy (about 30 minutes, once)
Nothing is published until you finish these steps. Do them in this order, so the site is private from its first real upload.
1. **Cloudflare account.** Sign up free at dash.cloudflare.com and confirm your email.
2. **Pages project.** Workers & Pages → Create → choose **Pages** (Cloudflare now suggests Workers first; this repository uses Pages) → Upload assets (Direct Upload) → project name `al-marsad` → Create. If it asks for files first, upload any small file; the first real deploy replaces it.
3. **Keep it private with Cloudflare Access** (free for small teams; the Free plan covers up to 50 people). In the project: Settings → General → Access policy → Enable. If Cloudflare asks you to set up Zero Trust, choose any team name and the Free plan. Then Manage (opens the Access application) → in its address, delete the `*` from the subdomain box so the main address (`al-marsad.pages.dev`) itself is covered → Save (rename it if asked). Go back to the project and Enable the access policy again; this covers the extra address every deployment gets (like `1a2b3c4d.al-marsad.pages.dev`). Zero Trust → Access → Applications should now list two al-marsad applications. In each one's policy, allow only: Include → Emails → each scholar's and team member's address. (If the menus have moved, Cloudflare's guide "Enable Access on your pages.dev domain" has the current clicks.)
4. **API token.** Profile icon → My Profile → API Tokens → Create Token → Create Custom Token. Name it `al-marsad deploy`. Permissions: Account · Cloudflare Pages · Edit, and nothing else. Account Resources: your account. Create, then copy the token (shown only once). Your **Account ID** is the 32-character code in the address bar after `dash.cloudflare.com/`.
5. **GitHub secrets.** In the repository: Settings → Secrets and variables → Actions → New repository secret. Name `CLOUDFLARE_API_TOKEN`, paste the token, Add secret. Again: `CLOUDFLARE_ACCOUNT_ID` with the Account ID. Only if the project has another name: Variables tab → New repository variable `CLOUDFLARE_PAGES_PROJECT` = that name.
6. **First deploy.** The next merge into main deploys. To deploy now: Actions → Checks and deploy → the latest run on main → Re-run all jobs. The deploy log ends with the site's address.
7. **Check it is private.** Open the project's address in a private browser window (shown on the project's page; normally `https://al-marsad.pages.dev`, with a few extra letters if that name was taken): you must see a Cloudflare sign-in page, not the site. Listed people type their email and get a one-time code.
8. Optional: Settings → Branches → protect main → Require status checks → **All checks**, so nothing merges unless the checks pass.

**Going public is your decision alone.** The site stays private until you delete both al-marsad Access applications (Zero Trust → Access → Applications). To stop all deploys, delete either secret.
If a deploy fails with "The Pages project ... does not exist", the name in step 2 and the variable in step 5 differ. If the address still shows the placeholder after a deploy, the project's production branch must be `main`.

## Left for a human
- Steps 1–8 above. Until then every push to main ends with "Deploy skipped" (green).
- wrangler 4.145.0 calls Workers "the recommended way to deploy all new projects"; Pages still works with `wrangler pages deploy`. If Cloudflare ever retires Pages direct upload, only the last step of the deploy job changes.
- Pins to refresh now and then: the four versions in the `env` block of checks.yml, requirements.txt (with its hashes) and the action SHAs. Dependabot could propose these; it is not switched on.
- Locally, uncommitted edits in demo/, generation-1/ or stories-50/ make the "outputs committed and current" step fail until they are committed. That is by design: CI checks the committed files.
