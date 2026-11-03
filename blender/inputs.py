"""
Blender renders: what each render is made from, and the one fingerprint of it.

Imported by blender/badr_eve.py (inside Blender) and by blender/check_fresh.py (plain Python,
no Blender), so the render and the check agree on the inputs by construction. The fingerprint
covers only the parts of the data a render draws, plus the scripts themselves: a change to a
claim the image does not show leaves it fresh; a change to the ground, the sky, a gazetteer
point or the script makes it stale.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "expeditions" / "dist" / "data"
OUT = HERE / "out"
MANIFEST = OUT / "badr.manifest.json"
SCRIPTS = ("blender/badr_eve.py", "blender/inputs.py")
BLENDER_MAC = "/Applications/Blender.app/Contents/MacOS/Blender"
COMMAND = f"{BLENDER_MAC} -b --factory-startup --python-exit-code 1 -P blender/badr_eve.py"


def load() -> tuple[dict, dict]:
    """The Badr expedition and the star list, as the expedition's compile step wrote them."""
    badr = json.loads((DATA / "badr.json").read_text(encoding="utf-8"))
    stars = json.loads((DATA / "stars.json").read_text(encoding="utf-8"))
    return badr, stars


def used(badr: dict, stars: dict) -> dict:
    """The parts a render draws: the ground, the gazetteer points, the computed sky, the stars."""
    w = badr["world"]
    return {
        "title": badr["title"],
        "source": badr["source"],
        "anchor": w["anchor"],
        "terrain": w["terrain"],
        "labels": w["labels"],
        "sky": {k: badr["sky"][k] for k in ("method", "rule", "text_en", "page", "candidates")},
        "stars": stars,
    }


def fingerprint() -> str:
    """sha256 over the drawn data (canonical JSON) and the render scripts, in a fixed order."""
    h = hashlib.sha256()
    h.update(json.dumps(used(*load()), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    for rel in SCRIPTS:
        h.update(b"\0" + rel.encode() + b"\0" + (ROOT / rel).read_bytes())
    return h.hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
