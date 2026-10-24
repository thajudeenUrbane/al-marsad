#!/usr/bin/env python3
"""Read every number the exhibition shows from the data, and write exhibition/numbers.js.

The halls never carry a typed number: each figure is a <span data-n="key"> (or data-t for a
text field) that exhibition.js fills from numbers.js. Run this after the Atlas, the review
queue or the expeditions change. `--check` rebuilds in memory and fails if numbers.js has
drifted, or if a page asks for a key that does not exist.

    .venv/bin/python exhibition/build.py                 # rebuilds the review queue (about 40 s)
    .venv/bin/python exhibition/build.py --queue review/dist/queue.json --check
"""
from __future__ import annotations

import argparse
import base64
import gzip
import json
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "numbers.js"
PAGES = [HERE / "index.html", HERE / "leave-behind.html"]
HEADER = "// Written by exhibition/build.py from the data. Do not edit by hand.\nwindow.EXHIBITION_NUMBERS = "

ATLAS = ROOT / "atlas" / "index.html"
BADR = ROOT / "expeditions" / "dist" / "data" / "badr.json"
CORPUS = ROOT / "ontology" / "corpus" / "ibn-hisham.ttl"
# Hall 4 follows one statement end to end: the date of Badr, as Ibn Isḥāq heard it from Abū Jaʿfar.
HALL4_ASSERTION = "ast:rzNVDGdNnO5m3jDhnFcbOC"
HALL4_REPORT = "rpt:4dCXayt6EwHdTVKkHKqPLS"
# Hall 2 opens one record: Khadīja bint Khuwaylid.
HALL2_PERSON = "laOMIYgqaQ5Iw6DmtiCNkY"


def atlas_payload() -> dict:
    html = ATLAS.read_text(encoding="utf-8")
    m = re.search(r'id="atlas-data"[^>]*>([A-Za-z0-9+/=]+)<', html)
    if not m:
        raise SystemExit(f"no data block in {ATLAS.relative_to(ROOT)}")
    return json.loads(gzip.decompress(base64.b64decode(m.group(1))))


def atlas_numbers(pl: dict) -> dict:
    counts = pl["meta"]["counts"]
    kinds = counts["kinds"]
    claims, preds = pl["claims"], pl["meta"]["preds"]
    by_pred: dict[str, int] = {}
    for p, st in zip(claims["p"], claims["st"]):
        if st == 1:  # a proposed statement (0 marks a record, which is not a statement)
            name = preds[p][0]
            by_pred[name] = by_pred.get(name, 0) + 1
    nodes = pl["nodes"]
    person = nodes["id"].index(HALL2_PERSON)
    chain = next(c for c in pl["chains"] if pl["reports"][c["rep"]]["label"].startswith("The day of Badr"))
    report = pl["reports"][chain["rep"]]
    link = chain["links"][0]
    return {
        "atlas": {
            "marks": counts["nodes"],
            "person_records": kinds["person"],
            "events": kinds["event"],
            "places": kinds["place"],
            "stories": kinds["story"],
            "groups": kinds["group"],
            "statements": counts["assertions"],
            "proposed": counts["status"].get("proposed", 0),
            "reviewed": counts["reviewed"],
            "chains": counts["chains"],
            "dated_events": counts["dated_events"],
            "located_places": counts["located"],
            "father_of": by_pred.get("father_of", 0),
            "participated_in": by_pred.get("participated_in", 0),
            "narrated_from": by_pred.get("narrated_from", 0),
        },
        "hall2": {"person": nodes["n"][person], "person_id": HALL2_PERSON},
        "hall4": {
            "report": report["label"],
            "citation": report["cit"],
            "chain": chain["label"],
            "terminal": nodes["n"][chain["terminal"]],
            "collector": nodes["n"][chain["collector"]],
            "mode": link[3],
        },
    }


def ttl_block(text: str, subject: str) -> str:
    m = re.search(rf"^{re.escape(subject)}\n(.*?)\s\.\n", text, re.S | re.M)
    if not m:
        raise SystemExit(f"{subject} not found in {CORPUS.relative_to(ROOT)}")
    return m.group(1)


def hall4_assertion() -> dict:
    block = ttl_block(CORPUS.read_text(encoding="utf-8"), HALL4_ASSERTION)
    obj = re.search(r'mrs:assertionObject "([^"]+)"@ar', block).group(1)
    status = re.search(r"mrs:assertionStatus mrs:as_(\w+)", block).group(1)
    gloss = re.search(r'rdfs:comment "([^"]+)"', block).group(1)
    label, _, text = gloss.partition(": ")
    if HALL4_REPORT not in block:
        raise SystemExit(f"{HALL4_ASSERTION} no longer comes from {HALL4_REPORT}")
    return {"object_ar": obj, "status": status, "gloss_label": label, "gloss": text}


def badr_numbers() -> dict:
    d = json.loads(BADR.read_text(encoding="utf-8"))
    sky, people = d["sky"], d["people"]
    weekdays = [c["weekday"] for c in sky["candidates"]]
    return {
        "title": d["title"],
        "with": people["with"],
        "other_side": people["against"],
        "unrecorded": people["unrecorded"],
        "rows": len(people["rows"]),
        "date_en": sky["text_en"],
        "date_ar": sky["text_ar"],
        "page": sky["page"],
        "tabular": sky["tabular"],
        "candidates": len(weekdays),
        "candidate_weekdays": " and ".join(weekdays),
        "friday_candidates": weekdays.count("Friday"),
        "work": d["source"]["work"],
    }


def queue_numbers(queue_path: Path | None) -> dict:
    sys.path.insert(0, str(ROOT / "review"))
    import pilot_pack  # noqa: E402  (review/ is a folder of scripts, not a package)

    if queue_path is None:
        import build_queue  # noqa: E402
        import common  # noqa: E402

        queue_path = Path(tempfile.mkdtemp()) / "queue.json"
        if build_queue.main(["--ontology", str(common.ONTOLOGY), "--out", str(queue_path)]):
            raise SystemExit("could not build the review queue")
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    picked = pilot_pack.default_batches(queue)
    by_id = {b["batch"]: b for b in queue["claims"] + queue["identity"]}
    story = [by_id[b] for b in picked if by_id[b]["kind"] == "story"]
    identity = [by_id[b] for b in picked if by_id[b] in queue["identity"]]
    s = queue["summary"]
    return {
        "queue_statements": s["claims"],
        "queue_batches": sum(s["claim_batches"].values()),
        "identity_questions": s["identity_units"],
        "merge_proposals": s["merge_units"],
        "pilot_story_batches": len(story),
        "pilot_statements": sum(len(b["units"]) for b in story),
        "pilot_identity": sum(len(b["units"]) for b in identity),
        "tradition_default": queue["tradition"]["label"],
    }


def build(queue_path: Path | None) -> dict:
    pl = atlas_payload()
    numbers = atlas_numbers(pl)
    numbers["hall4"].update(hall4_assertion())
    numbers["badr"] = badr_numbers()
    numbers["review"] = queue_numbers(queue_path)
    return numbers


def render(numbers: dict) -> str:
    return HEADER + json.dumps(numbers, ensure_ascii=False, indent=1, sort_keys=True) + ";\n"


def flat(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(flat(v, f"{prefix}{k}."))
        else:
            out[prefix + k] = v
    return out


def missing_keys(numbers: dict) -> list[str]:
    keys, bad = flat(numbers), []
    for page in PAGES:
        if not page.exists():
            continue
        for key in re.findall(r'data-[nt]="([^"]+)"', page.read_text(encoding="utf-8")):
            if key not in keys:
                bad.append(f"{page.name}: {key}")
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--queue", type=Path, help="use this review queue file instead of rebuilding it")
    ap.add_argument("--check", action="store_true", help="fail if numbers.js has drifted from the data")
    args = ap.parse_args(argv)
    numbers = build(args.queue)
    text = render(numbers)
    bad = missing_keys(numbers)
    if bad:
        print("pages ask for numbers that do not exist:\n  " + "\n  ".join(bad))
        return 1
    if args.check:
        old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if old != text:
            was = flat(json.loads(old[len(HEADER):].rstrip(";\n"))) if old.startswith(HEADER) else {}
            now = flat(numbers)
            for k in sorted(set(was) | set(now)):
                if was.get(k) != now.get(k):
                    print(f"  {k}: {was.get(k)!r} -> {now.get(k)!r}")
            print("exhibition/numbers.js has drifted from the data: run exhibition/build.py")
            return 1
        print(f"OK: exhibition/numbers.js matches the data ({len(flat(numbers))} values)")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(flat(numbers))} values)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
