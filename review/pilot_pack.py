#!/usr/bin/env python3
"""
Build the scholars' pilot pack: a few review batches and a short guide, as one zip file.

    .venv/bin/python review/pilot_pack.py                                # the default pack (below)
    .venv/bin/python review/pilot_pack.py --batches story-01,identity-p1 # these batches
    .venv/bin/python review/pilot_pack.py --list                         # every batch and its size

The default pack is the first sitting the maintainer chose (22 October 2026): the 50 Stories
batches, in order, until they hold at least 50 claims, then the first batch of identity
questions ("same person?", "is this a real group?"). Round 3 P1: the maintainer tries it
first as a test reviewer, then the scholars.

Writes review/dist/pilot/ (the review pages for the chosen batches only, with their queue)
and review/dist/pilot-pack.zip (those pages plus GUIDE.txt, from docs/pilot/scholar-guide.md).
Both are gitignored. Reads the graph; changes nothing in it. The steps around the pack:
docs/pilot/maintainer-steps.md.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_pages as bp  # noqa: E402
import build_queue  # noqa: E402
import common as c  # noqa: E402

GUIDE = c.ROOT / "docs" / "pilot" / "scholar-guide.md"
MIN_STORY_CLAIMS = 50
# A fixed date inside the zip, so the same pages give the same file.
ZIP_DATE = (2026, 1, 1, 0, 0, 0)


def default_batches(queue: dict) -> list[str]:
    chosen, claims = [], 0
    for b in queue.get("claims") or []:
        if b.get("kind") != "story":
            continue
        chosen.append(b["batch"])
        claims += len(b["units"])
        if claims >= MIN_STORY_CLAIMS:
            break
    identity = queue.get("identity") or []
    if identity:
        chosen.append(identity[0]["batch"])
    return chosen


def select(queue: dict, batch_ids: list[str]) -> dict:
    known = {b["batch"] for b in (queue.get("claims") or []) + (queue.get("identity") or [])}
    missing = [b for b in batch_ids if b not in known]
    if missing:
        raise ValueError(f"no such batch: {', '.join(missing)} (see --list)")
    wanted = set(batch_ids)
    out = dict(queue)
    out["claims"] = [b for b in queue.get("claims") or [] if b["batch"] in wanted]
    out["identity"] = [b for b in queue.get("identity") or [] if b["batch"] in wanted]
    # Count checks are questions for an editor, not for the scholars' first sitting.
    out["count_checks"] = []
    return out


def write_zip(pages: Path, zip_path: Path) -> list[str]:
    names = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(pages.iterdir()):
            if p.suffix in (".html", ".js"):
                z.writestr(zipfile.ZipInfo(p.name, ZIP_DATE), p.read_bytes(), zipfile.ZIP_DEFLATED)
                names.append(p.name)
        z.writestr(zipfile.ZipInfo("GUIDE.txt", ZIP_DATE), GUIDE.read_bytes(), zipfile.ZIP_DEFLATED)
        names.append("GUIDE.txt")
    return names


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--batches", help="comma-separated batch names (default: the first sitting, see above)")
    ap.add_argument("--queue", type=Path, help="use this queue file instead of rebuilding it from the graph")
    ap.add_argument("--out", type=Path, default=bp.DIST, help="output folder (default review/dist)")
    ap.add_argument("--ontology", type=Path, default=c.ONTOLOGY, help="ontology folder, for the queue")
    ap.add_argument("--list", action="store_true", help="list every batch and its size, then stop")
    args = ap.parse_args(argv)

    queue_path = args.queue
    if queue_path is None:
        queue_path = args.out / "queue.json"
        code = build_queue.main(["--ontology", str(args.ontology), "--out", str(queue_path)])
        if code:
            return code
    queue = json.loads(Path(queue_path).read_text(encoding="utf-8"))

    if args.list:
        for b in (queue.get("claims") or []) + (queue.get("identity") or []):
            print(f"{b['batch']:<40} {len(b['units']):>3}  {b.get('title', '')}")
        return 0

    batch_ids = [b.strip() for b in args.batches.split(",") if b.strip()] if args.batches else default_batches(queue)
    try:
        picked = select(queue, batch_ids)
    except ValueError as e:
        print(f"error: {e}")
        return 2

    pages = args.out / "pilot"
    if pages.exists():
        for p in pages.iterdir():
            p.unlink()
    pages.mkdir(parents=True, exist_ok=True)
    (pages / "queue.json").write_text(json.dumps(picked, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    bp.build(picked, pages)
    zip_path = args.out / "pilot-pack.zip"
    names = write_zip(pages, zip_path)

    claims = sum(len(b["units"]) for b in picked["claims"])
    questions = sum(len(b["units"]) for b in picked["identity"])
    print(f"batches: {', '.join(batch_ids)}")
    print(f"{claims} claim(s) and {questions} identity question(s); {len(names)} files in {zip_path} "
          f"({zip_path.stat().st_size:,} bytes); pages in {pages}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
