#!/usr/bin/env bash
# Every check in the repository, in one script that people and CI
# (.github/workflows/checks.yml) both run:
#
#     scripts/check_all.sh
#
# Each step runs from the repository root and shows its own output. A failing
# step does not stop the later ones, so one run shows every problem; a summary
# comes last. Exit status: 0 every step passed, 1 a step failed, 2 no usable Python.
#
# Needs git; Python 3.13 with requirements.txt installed; and, for the JS-off
# browser check, Node.js 22 with the `playwright` npm package and its Chromium
# (CI installs the versions named in .github/workflows/checks.yml).
#   PYTHON                    the Python to use. Default: .venv/bin/python; in a git
#                             worktree, the main checkout's .venv; else python3.
#   NODE_PATH                 where the playwright package is. Default: `npm root -g`.
#   PLAYWRIGHT_BROWSERS_PATH  where its browsers are. Default: Playwright's own,
#                             or /opt/pw-browsers when that folder exists.
#
# Adding a module: append one `step "name" command args...` line to the list at
# the end (see the commented placeholders). Nothing else needs to change.

set -uo pipefail
shopt -s nullglob
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2

# Fold each step's output in the GitHub Actions log; plain headers elsewhere.
if [ -n "${GITHUB_ACTIONS:-}" ]; then
  begin() { echo "::group::$1"; }
  end() { echo "::endgroup::"; }
  flag() { echo "::error title=check_all.sh::$1"; }
else
  begin() { printf '\n=== %s\n' "$1"; }
  end() { :; }
  flag() { :; }
fi

summary=()
failed=0
started=$SECONDS

# step NAME COMMAND [ARGS...]: run one check, record PASS or FAIL, return its exit status.
step() {
  local name=$1 t=$SECONDS rc
  shift
  begin "$name"
  echo "\$ $*"
  "$@"
  rc=$?
  end
  if [ "$rc" -eq 0 ]; then
    summary+=("PASS  $name ($((SECONDS - t))s)")
  else
    summary+=("FAIL  $name (exit $rc)")
    failed=$((failed + 1))
    flag "$name failed (exit $rc)"
  fi
  return "$rc"
}

# skip NAME REASON: record a step that could not run because an earlier one failed.
skip() {
  summary+=("SKIP  $1 ($2)")
}

# --- Python ------------------------------------------------------------------
find_python() {
  local c common
  if [ -n "${PYTHON:-}" ]; then echo "$PYTHON"; return 0; fi
  common=$(git rev-parse --git-common-dir 2>/dev/null) || common=""
  for c in .venv/bin/python ${common:+"$common/../.venv/bin/python"}; do
    if [ -x "$c" ]; then echo "$c"; return 0; fi
  done
  command -v python3 || command -v python
}
PY=$(find_python) || PY=""
if [ -z "$PY" ] || ! "$PY" -c "import rdflib, pyshacl" 2>/dev/null; then
  echo "error: no Python with rdflib and pyshacl found (tried: ${PY:-none})." >&2
  echo "Install them:  python3 -m pip install --require-hashes -r requirements.txt  (or set PYTHON=...)" >&2
  exit 2
fi
"$PY" - <<'EOF'
import re, sys
from importlib.metadata import PackageNotFoundError, version
def have(name):
    try:
        return version(name)
    except PackageNotFoundError:
        return "missing"
pins = dict(re.findall(r"^([A-Za-z0-9_.-]+)==(\S+)", open("requirements.txt", encoding="utf-8").read(), re.M))
print(f"python {sys.version.split()[0]} ({sys.executable}), rdflib {have('rdflib')}, pyshacl {have('pyshacl')}")
off = [f"{n} {have(n)} (pinned {v})" for n, v in sorted(pins.items()) if have(n) != v]
if off:
    print("warning: not the versions in requirements.txt, so results may differ from CI: " + "; ".join(off))
EOF

# --- helpers used by the steps -----------------------------------------------
ISLANDS=(demo generation-1 stories-50)

# The three earlier prototypes commit their built pages: a fresh build must leave them unchanged.
islands_current() {
  local new
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "not a git checkout"; return 1; }
  if ! git diff --exit-code --stat -- "${ISLANDS[@]}"; then
    echo "A fresh build changed the files above, or they have uncommitted edits: rebuild, review and commit them."
    return 1
  fi
  new=$(git ls-files --others --exclude-standard -- "${ISLANDS[@]}")
  if [ -n "$new" ]; then
    printf 'Files the builds wrote that are not committed:\n%s\n' "$new"
    return 1
  fi
  echo "OK: the committed ${ISLANDS[*]} outputs match a fresh build"
}

# A browser check (site/check_nojs.cjs, site/check_search.cjs) with Node and Playwright found as documented above.
# Usage: browser_check SCRIPT
browser_check() {
  local script=$1 np
  if ! command -v node >/dev/null 2>&1; then
    echo "node not found: install Node.js 22 and the playwright npm package with its Chromium"
    return 1
  fi
  np=${NODE_PATH:-$(npm root -g 2>/dev/null)}
  if ! NODE_PATH="$np" node -e 'require.resolve("playwright")' 2>/dev/null; then
    echo "the playwright npm package was not found (NODE_PATH=$np)"
    return 1
  fi
  if [ -z "${PLAYWRIGHT_BROWSERS_PATH:-}" ] && [ -d /opt/pw-browsers ]; then
    export PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers
  fi
  echo "node $(node --version), playwright $(NODE_PATH="$np" node -p 'require("playwright/package.json").version')"
  NODE_PATH="$np" node "$script" site/dist
}

# Every `uses:` in the workflows names a full commit SHA, with the tag in a comment.
actions_pinned() {
  local files=(.github/workflows/*.yml .github/workflows/*.yaml) bad
  if [ ${#files[@]} -eq 0 ]; then echo "no workflow files"; return 0; fi
  bad=$(grep -HnE '^[[:space:]-]*uses:' "${files[@]}" \
    | grep -vE "uses:[[:space:]]*[^@[:space:]]+@[0-9a-f]{40}[\"']?[[:space:]]+#[[:space:]]*v[0-9]" \
    | grep -vE 'uses:[[:space:]]*\./')
  if [ -n "$bad" ]; then
    printf 'Not pinned to a full commit SHA with "# vX.Y.Z" after it:\n%s\n' "$bad"
    return 1
  fi
  echo "OK: every action is pinned to a commit SHA"
}

# --- the checks, in order: add a module with one `step` line ------------------
step "ontology: build the graph (must conform)"    "$PY" ontology/build_graph.py
step "ontology: identity table"                    "$PY" ontology/tools/identity_audit.py --check
step "ontology: stories-50.ttl is current"         "$PY" ontology/tools/stories50_to_ttl.py --check
for f in ontology/corpus/*.ttl ontology/examples/*.ttl; do
  step "ontology: validate $f"                     "$PY" ontology/validate.py "$f"
done
step "prototypes: build demo"                      "$PY" demo/build.py
step "prototypes: build generation-1"              "$PY" generation-1/build.py
step "prototypes: build stories-50"                "$PY" stories-50/build.py
step "prototypes: outputs committed and current"   islands_current
if step "site: build"                              "$PY" site/build.py; then
  # Module builders write into site/dist after site/build.py (which empties it), so the
  # budget and HTML checks below cover their pages too.
  step "learn: build"                              "$PY" learn/build_learn.py
  step "site/interactive: build"                   "$PY" site/interactive/build_interactive.py
  step "site/observatory: build"                   "$PY" site/observatory/build_observatory.py
  step "ask: build"                                "$PY" ask/build_ask.py
  # Keep after every builder that writes a view into site/dist (site/hub.py lists them):
  step "site: hub pages link the views just built" "$PY" site/build.py --hub
  step "site: page budget"                         "$PY" site/check_budget.py
  step "site: HTML checks"                         "$PY" site/check_html.py
  step "site: pages work with JavaScript off"      browser_check site/check_nojs.cjs
  step "site: search works (JS on and off)"        browser_check site/check_search.cjs
  step "learn: pages work with JavaScript off"     browser_check learn/check_nojs.cjs
  step "site/interactive: timeline and map pages"  browser_check site/interactive/check_interactive.cjs
  step "site/interactive: tests"                   "$PY" -m unittest discover -s site/interactive/tests
  step "site/observatory: page"                    browser_check site/observatory/check_observatory.cjs
  step "site/observatory: tests"                   "$PY" -m unittest discover -s site/observatory/tests
  step "ask: page works (JS on and off)"           browser_check ask/tests/check_page.cjs
  step "site: home page links every built view"    "$PY" site/check_hub.py
  step "site: doors, thread, plain words (JS on/off)" browser_check site/check_doors.cjs
  # Checks that read site/dist go here.
else
  skip "site: budget, HTML and JS-off checks" "the site did not build"
fi
step "site: unit tests"                            "$PY" -m unittest discover -s site/tests
# Other modules, one line each when they land, e.g.
step "review: statuses agree with the review log"  "$PY" review/import_decisions.py --check
step "review: tests"                               "$PY" -m unittest discover -s review/tests
step "learn: tests"                                "$PY" -m unittest discover -s learn/tests
step "ask: tests"                                  "$PY" -m unittest discover -s ask/tests
step "ci: actions pinned to commit SHAs"           actions_pinned

# --- summary ------------------------------------------------------------------
printf '\n=== Summary (%ss)\n' "$((SECONDS - started))"
printf '%s\n' "${summary[@]}"
if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  { echo '### scripts/check_all.sh'; echo '```'; printf '%s\n' "${summary[@]}"; echo '```'; } >> "$GITHUB_STEP_SUMMARY"
fi
if [ "$failed" -gt 0 ]; then
  echo "FAILED: $failed step(s); the reason is in that step's output above."
  exit 1
fi
echo "OK: all ${#summary[@]} steps passed"
