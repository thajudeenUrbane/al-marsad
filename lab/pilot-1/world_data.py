"""Shared loader for the pilot kit: reads the exact data the Hijrah Night page shows.

The data is taken from the built page (lab/hijrah-night/index.html), not rebuilt, so the tests and
the reading page use the same claims, in the same order, that a learner sees in the world.
Half 1 = chapters 1-5, Half 2 = chapters 6-10 (CHAPTERS in lab/hijrah-night/build.py).
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
WORLD = ROOT / "lab" / "hijrah-night" / "index.html"
MARK = '<script id="data" type="application/json">'
HALVES = {1: range(0, 5), 2: range(5, 10)}


def load() -> dict:
    t = WORLD.read_text(encoding="utf-8")
    i = t.index(MARK) + len(MARK)
    data, _ = json.JSONDecoder().raw_decode(t[i:].replace("<\\/", "</"))
    assert len(data["chapters"]) == 10, "expected the 10 chapters of build.py"
    return data


def half_claims(data: dict, half: int) -> list[dict]:
    """Every claim a learner reads in this half, in page order (story, chain claims, family)."""
    out = []
    for n in HALVES[half]:
        ch = data["chapters"][n]
        out += ch["story"] + ch["chainClaims"] + ch["family"]
    return out
