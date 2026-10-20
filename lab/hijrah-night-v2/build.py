#!/usr/bin/env python3
"""
Build Hijrah Night v2: the Hijrah as about 130 evidence-graded stages in 10 acts, over real terrain.

    python3 lab/hijrah-night-v2/build.py

Reads (committed files only):
  lab/hijrah-night-v2/acts/act*.json          the drafted stages (SCHEMA.md); validated before building
  lab/hijrah-night-v2/data/places.csv          gazetteer points with certainty
  lab/hijrah-night-v2/data/hijaz-dem.json      terrain (AWS Terrain Tiles, zoom 9)
  lab/shared/dock/dock.{css,js}                minimise panels to corner dots; full view
  ingest/claims/ibn-hisham-full*.jsonl         claims and passages, for each stage's "in the graph" drawer
  ontology/corpus/ibn-hisham-full.ttl          each section's citation (volume, page, milestone)

The stages are a draft for scholars (maintainer round 3, G3): drafted with AI from the Arabic of
Ibn Hishām and other named sources, every statement graded established / supported / disputed /
reconstruction, never presented as reviewed.
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CLAIMS = ROOT / "ingest" / "claims" / "ibn-hisham-full.jsonl"
PASSAGES = ROOT / "ingest" / "claims" / "ibn-hisham-full-passages.jsonl"
TTL = ROOT / "ontology" / "corpus" / "ibn-hisham-full.ttl"
LINEAGE = {"rel_father_of", "rel_mother_of", "rel_sibling_of", "rel_paternal_uncle_of", "rel_maternal_uncle_of",
           "rel_ancestor_of", "rel_cousin_of", "rel_grandfather_of", "rel_son_of"}


def read_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def citations() -> dict:
    text = TTL.read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r"^(psg:\w+)\n    a mrs:Passage , oa:SpecificResource ;\n(.*?)\n\n", text, re.M | re.S):
        c = re.search(r'mrs:canonicalCitation "([^"]+)"', m.group(2))
        if c:
            out[m.group(1)] = c.group(1).split("provisional), ", 1)[-1]
    return out


def show(name: str) -> str:
    if name.startswith("The Prophet Muḥammad"):
        return "The Prophet Muḥammad ﷺ"
    return re.sub(r"\s*\((?:\d+|note)\)", "", name).strip()


def sections_used(u: dict) -> set[str]:
    out = set(u.get("sections", []))
    blob = json.dumps(u, ensure_ascii=False)
    out |= set(re.findall(r'"sec":\s*"(S\d{4})"', blob))
    return out


def main() -> None:
    files = sorted((HERE / "acts").glob("act*.json"))
    check = subprocess.run([sys.executable, str(HERE / "tools" / "validate_act.py"), *map(str, files)], capture_output=True, text=True)
    print(check.stdout.strip())
    if check.returncode:
        sys.exit("validation failed; fix the act files first")
    acts = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    acts.sort(key=lambda a: a["act"])

    places = {}
    with (HERE / "data" / "places.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            places[r["key"]] = {"name": r["name"], "ar": r["arabic"], "lat": float(r["latitude"]), "lon": float(r["longitude"]),
                                "certainty": r["certainty"], "src": r["source"]}

    cites = citations()
    passages = {p["id"]: p for p in read_jsonl(PASSAGES)}
    by_key = {p["key"]: p for p in passages.values()}
    used = set().union(*(sections_used(u) for a in acts for u in a["units"]))
    cite_out = {}
    for s in sorted(used):
        p = by_key.get(s)
        cite_out[s] = {"cite": cites.get(p["id"], "") if p else "section not yet in the passages file",
                       "label": p["label"].rsplit(" (Ibn Hisham", 1)[0] if p else ""}
    claims: dict[str, list] = {}
    seen = set()
    for c in read_jsonl(CLAIMS):
        k = passages[c["passage"]]["key"]
        if k not in used or c["predicate"] in LINEAGE or (k, c["gloss"]) in seen:
            continue
        seen.add((k, c["gloss"]))
        claims.setdefault(k, []).append({"id": c["id"], "p": c["predicate"][4:].replace("_", " "), "g": c["gloss"]})

    dem = json.loads((HERE / "data" / "hijaz-dem.json").read_text(encoding="utf-8"))
    n_units = sum(len(a["units"]) for a in acts)
    n_stat = sum(len(u.get("statements", [])) for a in acts for u in a["units"])
    data = {"acts": acts, "places": places, "dem": dem, "cites": cite_out, "claims": claims,
            "counts": {"acts": len(acts), "units": n_units, "statements": n_stat,
                       "claims": sum(len(v) for v in claims.values()), "sections": len(used)}}
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    dock = ROOT / "lab" / "shared" / "dock"
    page = (HERE / "template.html").read_text(encoding="utf-8")
    page = page.replace("/*DOCK_CSS*/", (dock / "dock.css").read_text(encoding="utf-8"))
    page = page.replace("/*DOCK_JS*/", (dock / "dock.js").read_text(encoding="utf-8"))
    page = page.replace("/*DATA*/null", blob)
    (HERE / "index.html").write_text(page, encoding="utf-8")
    print(f"wrote lab/hijrah-night-v2/index.html ({len(page.encode()) // 1000} kB): {data['counts']}")


if __name__ == "__main__":
    main()
