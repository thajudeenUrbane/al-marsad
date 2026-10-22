#!/usr/bin/env python3
"""
Build the Circle mode prototype: one self-contained page (lab/circle-mode/index.html) where a
teacher, halaqa leader or parent builds a "Majlis Sheet" from claims of the full-book Ibn Hishām pass.

    python3 lab/circle-mode/build.py

Reads (committed files only):
  ingest/claims/ibn-hisham-full.jsonl            the claims (AI-extracted, proposed, unreviewed)
  ingest/claims/ibn-hisham-full-passages.jsonl   the passages they rest on (section key, label)
  ontology/corpus/ibn-hisham-full.ttl            each passage's citation (volume, page, milestone)

Bare lineage claims (father/mother/ancestor/sibling/uncle/cousin) are dropped: they make up most
of the graph but are rarely what a circle discusses, and they keep the page small.
Every sentence about the past on a sheet is a claim's gloss with its citation. A teacher adds only
questions, or notes that the sheet marks as the teacher's own words.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CLAIMS = ROOT / "ingest" / "claims" / "ibn-hisham-full.jsonl"
PASSAGES = ROOT / "ingest" / "claims" / "ibn-hisham-full-passages.jsonl"
TTL = ROOT / "ontology" / "corpus" / "ibn-hisham-full.ttl"
OUT = HERE / "index.html"

PROPHET = "The Prophet Muḥammad (peace and blessings be upon him)"
LINEAGE = {"rel_father_of", "rel_mother_of", "rel_ancestor_of", "rel_sibling_of",
           "rel_paternal_uncle_of", "rel_maternal_uncle_of", "rel_cousin_of"}
PRED_LABEL = {
    "rel_resided_in": "stayed in", "rel_sheltered_at": "sheltered at", "rel_present_at": "present at",
    "rel_participated_in": "took part in", "rel_migrated_to": "emigrated to", "rel_migrated_from": "emigrated from",
    "rel_travelled_via": "travelled via", "rel_visited": "came to", "rel_led": "led",
    "rel_sheltered": "gave lodging to", "rel_corresponded_with": "wrote for", "rel_dated": "is dated",
    "rel_occurred_at": "took place at", "rel_mawla_of": "client (mawlā) of", "rel_died_at": "died at",
    "rel_narrated_from": "narrated from", "rel_spouse_of": "spouse of", "rel_died_during": "died during",
    "rel_killed": "killed",
}

EXAMPLE = {
    "title": "The two reports of the lodging at Qubāʾ",
    "sections": ["S0698", "S0699"],
    "preds": {"rel_sheltered", "rel_sheltered_at"},
    "questions": [
        (0, "Before we read: when a traveller arrives in a new town, why does it matter whose house they stay in?"),
        (None, "The text gives more than one name for the Prophet's ﷺ host at Qubāʾ. Which names does it give?"),
        (None, "Ibn Hishām keeps both reports instead of choosing one. What does that teach us about how he wrote?"),
    ],
}


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
    """Display form: the Prophet with ﷺ; identity suffixes such as (2) dropped."""
    if name == PROPHET:
        return "The Prophet Muḥammad ﷺ"
    return re.sub(r"\s*\((?:\d+|note)\)", "", name).strip()


def gloss(g: str) -> str:
    return g.replace("Muḥammad (peace and blessings be upon him)", "Muḥammad ﷺ")


def main() -> None:
    cites = citations()
    passages = {p["id"]: p for p in read_jsonl(PASSAGES)}
    names: list[str] = []
    name_ix: dict[str, int] = {}
    preds: list[str] = []
    pred_ix: dict[str, int] = {}
    psgs: list[list] = []
    psg_ix: dict[str, int] = {}
    persons: set[int] = set()

    def nid(n: str) -> int:
        if n not in name_ix:
            name_ix[n] = len(names)
            names.append(n)
        return name_ix[n]

    rows = []
    kept = dropped = 0
    for c in read_jsonl(CLAIMS):
        if c["predicate"] in LINEAGE:
            dropped += 1
            continue
        kept += 1
        p = passages[c["passage"]]
        if p["id"] not in psg_ix:
            psg_ix[p["id"]] = len(psgs)
            label = re.sub(r"\s*\(Ibn Hisham, Sira, section \d+\)\s*$", "", p["label"])
            psgs.append([p["key"], label, cites.get(p["id"], "")])
        if c["predicate"] not in pred_ix:
            pred_ix[c["predicate"]] = len(preds)
            preds.append(c["predicate"])
        s = nid(show(c["subject"]["name"]))
        if c["subject"].get("kind") == "person":
            persons.add(s)
        o = c["object"]
        oi = -1
        if isinstance(o, dict) and "name" in o:
            oi = nid(show(o["name"]))
            if o.get("kind") == "person":
                persons.add(oi)
        rows.append([c["id"][4:], pred_ix[c["predicate"]], s, oi, gloss(c["gloss"]), psg_ix[p["id"]]])

    rows.sort(key=lambda r: (psgs[r[5]][0], r[0]))
    by_id = {r[0]: r for r in rows}
    ex_items = []
    qs = list(EXAMPLE["questions"])
    if qs and qs[0][0] == 0:
        ex_items.append(["q", qs.pop(0)[1]])
    for r in rows:
        if psgs[r[5]][0] in EXAMPLE["sections"] and preds[r[1]] in EXAMPLE["preds"]:
            ex_items.append(["c", r[0]])
    ex_items.append(["n", "Read both reports aloud before discussing. Let the students notice the difference themselves."])
    for _, q in qs:
        ex_items.append(["q", q])
    assert any(i[0] == "c" for i in ex_items), "example claims not found"
    assert all(i[1] in by_id for i in ex_items if i[0] == "c")

    data = {
        "names": names, "persons": sorted(persons, key=lambda i: names[i]),
        "preds": [[p, PRED_LABEL.get(p, p[4:].replace("_", " "))] for p in preds],
        "psgs": psgs, "claims": rows,
        "example": {"v": 1, "title": EXAMPLE["title"], "items": ex_items},
    }
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = TEMPLATE.replace("__DATA__", blob)
    OUT.write_text(html, encoding="utf-8")
    print(f"kept {kept} claims, dropped {dropped} lineage claims; {len(psgs)} passages; "
          f"{OUT.relative_to(ROOT)} {OUT.stat().st_size / 1e6:.2f} MB")


TEMPLATE = (HERE / "template.html").read_text(encoding="utf-8")

if __name__ == "__main__":
    main()
