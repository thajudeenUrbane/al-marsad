#!/usr/bin/env python3
"""Print the Arabic text of Ibn Hishām sections for drafting (reads the git-ignored cache only).

    python3 lab/hijrah-night-v2/tools/section_text.py S0680 [S0681 ...]
    python3 lab/hijrah-night-v2/tools/section_text.py --range S0678 S0703

Sections missing from the passages file (e.g. S0682, S0684, S0687, S0689, S0690) are printed as the
text between the previous and the next known section, marked GAP. Never copy this text into committed files.
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "lab/moments-trial/cache/source.txt"
P = sorted((json.loads(l) for l in open(ROOT / "ingest/claims/ibn-hisham-full-passages.jsonl", encoding="utf-8")), key=lambda p: p["key"])
text = SRC.read_text(encoding="utf-8")
by = {p["key"]: p for p in P}
def show(k):
    if k in by:
        p = by[k]; print(f"===== {k} · {p['label']}\n{text[p['start']:p['end']]}\n")
        return
    n = int(k[1:]); prev = max((p for p in P if int(p["key"][1:]) < n), key=lambda p: p["key"]); nxt = min((p for p in P if int(p["key"][1:]) > n), key=lambda p: p["key"])
    print(f"===== {k} · GAP between {prev['key']} and {nxt['key']} (not in the passages file)\n{text[prev['end']:nxt['start']]}\n")
a = sys.argv[1:]
if a and a[0] == "--range":
    lo, hi = int(a[1][1:]), int(a[2][1:]); keys = [f"S{n:04d}" for n in range(lo, hi + 1)]
    seen_gap = set()
    for k in keys: show(k)
else:
    for k in a: show(k)
