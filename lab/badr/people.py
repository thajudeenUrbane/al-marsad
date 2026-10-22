#!/usr/bin/env python3
"""
Lab: Badr. The people Ibn Isḥāq's Badr lists name, by list and by voice, from the joined graph's claims.

    .venv/bin/python lab/badr/people.py      # writes lab/badr/data/people.json (needs ingest/cache, see ibn_hisham.py fetch)

Uses the same list boundaries as ingest/count_checks.py, but keeps the names. Nothing here is reviewed:
every row is a proposed claim with its passage. Names only; the Arabic text stays out of the repo.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ingest"))
import count_checks as cc  # noqa: E402
import sira_derive as sd  # noqa: E402

OUT = Path(__file__).resolve().parent / "data" / "people.json"
KEYS = ["badr_emigrants", "badr_aws", "badr_khazraj", "badr_all", "badr_slain", "badr_captives"]


def main():
    raw, passages, claims = sd.load()
    pby = {p["id"]: p for p in passages}
    voice = {}
    for x in sd.OUT.open(encoding="utf-8"):
        r = json.loads(x)
        if r["t"] == "annot":
            voice[r["claim"]] = r.get("voice")
    totals, out = {}, {}
    for ck in cc.CHECKS:
        after = ck["start"].startswith("after:")
        s0 = totals[ck["start"][6:]] if after else raw.find(ck["start"])
        t0 = raw.find(ck["total"], s0)
        totals[ck["key"]] = t0 + len(ck["total"])
        if ck["key"] not in KEYS:
            continue
        end = t0 if ck["end"] == "total" else raw.find(cc.TOP_HEADING, t0)
        lo = min(s0, t0)
        in_list = {p["id"] for p in passages if (lo <= p["start"] < end or p["start"] <= lo < p["end"]) and p["start"] < end}
        people = {}
        for c in claims:
            if c["passage"] not in in_list or c["predicate"] not in ck["preds"]:
                continue
            if sd.name(c["object"]) not in ck["events"]:
                continue
            s = c["subject"]
            if not isinstance(s, dict) or s.get("kind") != "person" or s["name"] == sd.PROPHET:
                continue
            row = people.setdefault(s["name"], {"name": s["name"], "voices": set(), "claims": [], "share": False})
            row["voices"].add(voice.get(c["id"]) or "none")
            g = c.get("gloss", "")
            if "share" in g.lower():
                row["share"] = True
            p = pby[c["passage"]]
            row["claims"].append({"id": c["id"], "gloss": g, "section": p["key"], "label": p["label"]})
        rows = []
        for r in people.values():
            v = r.pop("voices")
            r["voice"] = "ibn_ishaq" if "ibn_ishaq" in v else "ibn_hisham" if "ibn_hisham" in v else "none"
            r["claims"] = r["claims"][:2]
            rows.append(r)
        rows.sort(key=lambda r: min(c["section"] for c in r["claims"]))
        out[ck["key"]] = {"what": ck["en"], "stated": ck["n"], "people": rows}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    for k, v in out.items():
        print(k, v["stated"], len(v["people"]), sum(r["share"] for r in v["people"]))


if __name__ == "__main__":
    main()
