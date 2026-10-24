# Pilot pack: the maintainer's steps

Decided 22 October 2026: first the 50 Stories claims, then the "same person?" questions, sent to the scholars on WhatsApp. Round 3 P1: you try it first as a test reviewer.

## 1. Make the pack
```
.venv/bin/python review/pilot_pack.py
```
It writes `review/dist/pilot-pack.zip`: the review pages for the first story batches (at least 50 claims), the first batch of identity questions, and `GUIDE.txt` (from `docs/pilot/scholar-guide.md`). `--list` shows every batch; `--batches story-01,identity-p1` picks others. Nothing in the graph changes.

## 2. Add yourself, then each scholar, to the roster
On your machine only (`review/roster.csv` is gitignored; round 3 P3: keep a copy in your password manager or encrypted folder):
```
cp review/roster.example.csv review/roster.csv      # once
.venv/bin/python ontology/tools/mint_id.py agt     # one ID per person
```
One row per person. For the pilot, the scope is `source:stories-50; topic:identity`, and the role is `scholar`. Your own test row works the same way. Mark it in the name column (for example "Maintainer (test)") and revoke it afterwards with `revoked_on`.

## 3. Try it yourself first
Unzip the pack and open `index.html` in a phone browser, or serve it with `python -m http.server -d review/dist/pilot` and open `http://localhost:8000/index.html#reviewer=<your ID>`. Decide a few claims, tap **Send my decisions**, then import your file in a dry run (step 5). Note anything confusing.

## 4. Send it to the scholars
Send each scholar the zip, `GUIDE.txt` as a message, and their reviewer ID. A link is more reliable than a file opened from WhatsApp (handover 3b, point 1): once the site is on Cloudflare (`docs/handover/slice-2c-ci.md`, round 3 P2), put the pages there behind Cloudflare Access and send `…/index.html#reviewer=<ID>`.

## 5. Bring the decisions in
Save each file you receive in `review/inbox/` (a `.txt` from Android is fine). Then:
```
.venv/bin/python review/import_decisions.py --dry-run   # check: it prints the roster name per file
.venv/bin/python review/import_decisions.py
.venv/bin/python ontology/build_graph.py && .venv/bin/python site/build.py
```
Decided claims leave the queue. "Needs discussion" stays under review until the board exists (round 3 P6).

## Record
After the first real sitting, note in this file: how long it took, how many claims were decided, and what confused the reviewer. This is still open in slice 3b's "done when".
