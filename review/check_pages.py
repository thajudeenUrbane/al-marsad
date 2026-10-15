#!/usr/bin/env python3
"""
Round trip for the review pages (slice 3b): browser to importer, on a temporary copy.

    .venv/bin/python review/check_pages.py            # the check scripts/check_all.sh runs
    .venv/bin/python review/check_pages.py --timing   # also time 50 claims on an emulated Android phone

1. Copies ontology/ to a temporary folder, builds the queue there (identity questions
   included, so their cards are exercised too) and the pages from it.
2. Writes a throwaway roster in that folder: one clearly fake reviewer, in scope for every
   source file. The real roster is never read.
3. Runs review/check_pages.cjs in Chromium (Playwright): it fills a batch on a phone
   (accept with a citation, reject, needs discussion), works offline, sends, and captures
   the decision files; see that file for every check.
4. Runs review/import_decisions.py --dry-run on each captured file against the temporary
   copy: each must import cleanly (exit 0, nothing refused). Then imports the phone's file
   for real into the copy, and checks the three claims are accepted, rejected and under
   review there, with the graph still conforming (the importer validates it).
5. Checks the real corpus is byte for byte unchanged.
Needs Node.js with the `playwright` npm package and its Chromium (NODE_PATH, default
`npm root -g`; PLAYWRIGHT_BROWSERS_PATH, default /opt/pw-browsers when it exists).
Exit 0 when everything passes, 1 otherwise.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

REVIEW = Path(__file__).resolve().parent
sys.path.insert(0, str(REVIEW))
import build_pages  # noqa: E402
import build_queue  # noqa: E402
import common as c  # noqa: E402

REVIEWER = "agt:TestRoundTrip000000000"  # a fixture ID, written only to the temporary roster


def corpus_digest() -> str:
    h = hashlib.sha256()
    for f in sorted(c.ONTOLOGY.rglob("*")):
        if f.is_file() and f.suffix in (".ttl", ".csv"):
            h.update(str(f.relative_to(c.ROOT)).encode() + b"\0" + f.read_bytes())
    return h.hexdigest()


def node_env() -> tuple[str | None, dict]:
    node = shutil.which("node")
    env = dict(os.environ)
    if node and not env.get("NODE_PATH"):
        npm = shutil.which("npm")
        if npm:
            env["NODE_PATH"] = subprocess.run([npm, "root", "-g"], capture_output=True, text=True).stdout.strip()
    if not env.get("PLAYWRIGHT_BROWSERS_PATH") and Path("/opt/pw-browsers").is_dir():
        env["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/pw-browsers"
    return node, env


def importer(ont: Path, roster: Path, *args) -> tuple[int, str]:
    res = subprocess.run([sys.executable, str(REVIEW / "import_decisions.py"), "--ontology", str(ont), "--roster", str(roster), *map(str, args)],
                         capture_output=True, text=True)
    return res.returncode, res.stdout + res.stderr


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--timing", action="store_true", help="also time 50 claims on an emulated mid-range Android phone")
    ap.add_argument("--keep", type=Path, help="copy the captured files (and timing.json) here")
    args = ap.parse_args(argv)
    node, env = node_env()
    if not node:
        print("node not found: install Node.js 22 and the playwright npm package with its Chromium")
        return 1
    digest = corpus_digest()
    problems = []
    tmp = Path(tempfile.mkdtemp(prefix="marsad-review-pages-"))
    try:
        ont = tmp / "ontology"
        shutil.copytree(c.ONTOLOGY, ont, ignore=shutil.ignore_patterns("__pycache__", "*.tmp"))
        tree = c.Tree(ont)
        queue = build_queue.build(tree, {"needs-review", "probable"}, 50)
        (tmp / "queue.json").write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
        pages = tmp / "pages"
        build_pages.build(queue, pages)
        scope = "; ".join([f"source:{s}" for s in sorted(tree.sources())] + ["topic:identity"])
        roster = tmp / "roster.csv"
        roster.write_text(",".join(c.ROSTER_COLUMNS) + "\n" +
                          f"{REVIEWER},Test Reviewer RT,scholar,{scope},{date.today() - timedelta(days=1)},Test Maintainer,\n",
                          encoding="utf-8")
        story = next(b for b in queue["claims"] if b["kind"] == "story" and len(b["units"]) >= 3)
        cmd = [node, str(REVIEW / "check_pages.cjs"), str(pages), str(tmp / "out"), "--reviewer", REVIEWER,
               "--batch", build_pages.page_file(story["batch"])]
        if queue["identity"]:
            cmd += ["--identity", build_pages.page_file(queue["identity"][0]["batch"])]
        if args.timing:
            cmd.append("--timing")
        print("$ node review/check_pages.cjs ...")
        res = subprocess.run(cmd, env=env)
        if res.returncode:
            problems.append(f"browser checks failed (exit {res.returncode})")
        captured = [p for p in (tmp / "out" / n for n in ("download.json", "shared.txt", "blocked.json", "timing-decisions.json")) if p.exists()]
        for f in captured:
            code, out = importer(ont, roster, "--dry-run", f)
            n = len(json.loads(f.read_text(encoding="utf-8"))["decisions"])
            clean = code == 0 and "refused" not in out and f"dry run: {n} decision(s) would be recorded" in out
            print(f"importer --dry-run {f.name}: {'imports cleanly' if clean else 'PROBLEM'} ({n} decisions)")
            if not clean:
                problems.append(f"{f.name} does not import cleanly:\n{out}")
        phone = tmp / "out" / "download.json"
        if phone.exists():
            code, out = importer(ont, roster, phone)
            doc = json.loads(phone.read_text(encoding="utf-8"))
            after = c.Tree(ont)
            got = sorted((d["decision"], after.status(c.expand(d["target"]))) for d in doc["decisions"])
            want = [("accept", "accepted"), ("needs_discussion", "under_review"), ("reject", "rejected")]
            print(f"importer {phone.name} into the copy: exit {code}; statuses {got}")
            if code or got != want:
                problems.append(f"the real import into the copy went wrong (exit {code}, {got}):\n{out}")
            again, out2 = importer(ont, roster, phone)
            if again or "3 already imported" not in out2:
                problems.append(f"re-importing the phone's file was not a no-op:\n{out2}")
        else:
            problems.append("the browser check captured no file")
        if args.keep:
            args.keep.mkdir(parents=True, exist_ok=True)
            for f in (tmp / "out").glob("*"):
                shutil.copy2(f, args.keep / f.name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if corpus_digest() != digest:
        problems.append("the real corpus changed")
    for p in problems:
        print("FAIL " + p)
    print("OK: pages to file to importer, cleanly" if not problems else f"FAILED: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
