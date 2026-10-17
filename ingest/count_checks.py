#!/usr/bin/env python3
"""
Slice 11a (maintainer F2): the totals Ibn Hishām's text itself gives, checked against the graph.

    .venv/bin/python ingest/count_checks.py          # write ingest/claims/ibn-hisham-full-counts.json and print it
    .venv/bin/python ingest/count_checks.py --check  # exit 1 if the committed file is not current

Each check is one total the text states ("all of the emigrants present at Badr ...:
eighty-three men"), the list it closes (from Ibn Isḥāq's opening words to the total),
and the people the graph records in that list for that event. Only numbers the text
gives are used, never a modern figure. A list also holds names Ibn Hishām adds or that
are named in passing, so the count is split by voice (slice 11a): Ibn Isḥāq's own
total should match the people in his voice. A mismatch is a question for a reviewer
(a missed name, a duplicate, a person in the wrong list), never a correction made here.
The file commits offsets and checksums, never the text.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ibn_hisham as ih  # noqa: E402
import sira_derive as sd  # noqa: E402

OUT = ih.CLAIMS_DIR / "ibn-hisham-full-counts.json"
TOP_HEADING = "\n### | "  # a top-level heading; sub-headings are "### ||"
ABYSSINIA = {"The emigration to Abyssinia", "The migration to Abyssinia and the Negus's protection"}

# start: the list's opening words (or "after": just after another check's total);
# total: the words of the total; end: where the list ends ("total" or "heading": the next
# top-level heading after the total); n: the number the total gives; on: events, predicates.
CHECKS = [
    {"key": "badr_emigrants", "en": "Emigrants present at Badr, or given a share", "n": 83,
     "start": "وهذه تسمية من شهد بدرا من المسلمين", "total": "فجميع من شهد بدرا من المهاجرين", "end": "total",
     "events": {"Battle of Badr"}, "preds": {"rel_participated_in", "rel_present_at"}},
    {"key": "badr_aws", "en": "Aws present at Badr, or given a share", "n": 61,
     "start": "after:badr_emigrants", "total": "فجميع من شهد بدرا من الأوس", "end": "total",
     "events": {"Battle of Badr"}, "preds": {"rel_participated_in", "rel_present_at"}},
    {"key": "badr_khazraj", "en": "Khazraj present at Badr, or given a share", "n": 170,
     "start": "after:badr_aws", "total": "فجميع من شهد بدرا من الخزرج", "end": "total",
     "events": {"Battle of Badr"}, "preds": {"rel_participated_in", "rel_present_at"}},
    {"key": "badr_all", "en": "All Muslims present at Badr, or given a share", "n": 314,
     "start": "وهذه تسمية من شهد بدرا من المسلمين", "total": "ثلاث مائة رجل وأربعة عشر رجلا", "end": "total",
     "events": {"Battle of Badr"}, "preds": {"rel_participated_in", "rel_present_at"}},
    {"key": "badr_slain", "en": "Quraysh killed at Badr, as counted for Ibn Hishām", "n": 50,
     "start": "وقتل من المشركين يوم بدر", "total": "فجميع من أحصي لنا من قتلى", "end": "total",
     "events": {"Battle of Badr"}, "preds": {"rel_died_during"}},
    {"key": "badr_captives", "en": "Quraysh captured at Badr, as remembered", "n": 43,
     "start": "وأسر من المشركين من قريش", "total": "ثلاثة وأربعون رجلا", "end": "total",
     "events": {"Battle of Badr"}, "preds": {"rel_present_at", "rel_participated_in"}},
    {"key": "uhud_martyrs", "en": "Muslims martyred at Uḥud (Ibn Isḥāq)", "n": 65,
     "start": "واستشهد من المسلمين يوم أحد", "total": "فجميع من استشهد من المسلمين مع رسول الله", "end": "total",
     "events": {"Battle of Uḥud"}, "preds": {"rel_died_during"}},
    {"key": "uhud_slain", "en": "Idolaters killed at Uḥud", "n": 22,
     "start": "وقتل من المشركين يوم أحد", "total": "اثنان وعشرون رجلا", "end": "total",
     "events": {"Battle of Uḥud"}, "preds": {"rel_died_during"}},
    {"key": "aqaba_second", "en": "Those who pledged at the second ʿAqaba: 73 men and 2 women", "n": 75,
     "start": "ثلاثة وسبعين رجلا وامرأتين", "total": "ثلاثة وسبعين رجلا وامرأتين", "end": "heading",
     "events": {"The Second Pledge of al-Aqaba"}, "preds": {"rel_participated_in", "rel_present_at"}},
    {"key": "aqaba_first", "en": "The twelve men of the first ʿAqaba", "n": 12,
     "start": "وافى الموسم من الأنصار اثنا عشر", "total": "وافى الموسم من الأنصار اثنا عشر", "end": "heading",
     "events": {"The First Pledge of al-Aqaba"}, "preds": {"rel_participated_in", "rel_present_at"}},
    {"key": "abyssinia_men", "en": "Men who emigrated to Abyssinia, “if ʿAmmār was among them” (the list also names women)",
     "n": 83, "start": "وكان أول من خرج من المسلمين", "total": "ثلاثة وثمانين رجلا", "end": "total",
     "events": ABYSSINIA, "preds": {"rel_participated_in", "rel_migrated_to"}, "places": {"al-Habasha (Aksum)"}},
]


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def run():
    raw, passages, claims = sd.load()
    voice = {}
    for x in sd.OUT.open(encoding="utf-8"):
        r = json.loads(x)
        if r["t"] == "annot":
            voice[r["claim"]] = r.get("voice")
    totals = {}
    rows = []
    for ck in CHECKS:
        if ck["start"].startswith("after:"):
            s0 = totals[ck["start"][6:]]
        else:
            s0 = raw.find(ck["start"])
        t0 = raw.find(ck["total"], s0 if not ck["start"].startswith("after:") else s0)
        if s0 < 0 or t0 < 0:
            sys.exit(f"{ck['key']}: its words were not found in the text")
        totals[ck["key"]] = t0 + len(ck["total"])
        end = t0 if ck["end"] == "total" else raw.find(TOP_HEADING, t0)
        lo = min(s0, t0)
        in_list = {p["id"] for p in passages if lo <= p["start"] < end or p["start"] <= lo < p["end"]}
        if ck["end"] == "total":
            in_list = {pid for pid in in_list if next(p for p in passages if p["id"] == pid)["start"] < end}
        people = {}
        for c in claims:
            if c["passage"] not in in_list or c["predicate"] not in ck["preds"]:
                continue
            o = sd.name(c["object"])
            if o not in ck["events"] and o not in ck.get("places", set()):
                continue
            s = c["subject"]
            if not isinstance(s, dict) or s.get("kind") != "person" or s["name"] == sd.PROPHET:
                continue
            people.setdefault(s["name"], set()).add(voice.get(c["id"]) or "none")
        by_voice = {"ibn_ishaq": 0, "ibn_hisham": 0, "none": 0}
        for v in people.values():
            by_voice["ibn_ishaq" if "ibn_ishaq" in v else "ibn_hisham" if "ibn_hisham" in v else "none"] += 1
        found = len(people)
        rows.append({
            "key": ck["key"], "what": ck["en"], "stated": ck["n"],
            "found": found, "found_ibn_ishaq_voice": by_voice["ibn_ishaq"],
            "found_ibn_hisham_voice": by_voice["ibn_hisham"], "found_no_voice": by_voice["none"],
            "matches": found == ck["n"] or by_voice["ibn_ishaq"] == ck["n"],
            "total_at": {"offset": t0, "length": len(ck["total"]), "sha256": sha(ck["total"])},
            "list_sections": len(in_list),
        })
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    rows = run()
    text = json.dumps({"source": "ingest/count_checks.py (slice 11a)", "checks": rows}, ensure_ascii=False, indent=1) + "\n"
    if a.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print(f"{OUT.relative_to(ih.ROOT)} is not current: run ingest/count_checks.py")
            return 1
        print(f"{OUT.relative_to(ih.ROOT)} is up to date")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"{'check':16} {'stated':>6} {'found':>6} {'IbnIs':>6} {'IbnHi':>6} {'none':>5}  ")
    for r in rows:
        print(f"{r['key']:16} {r['stated']:6} {r['found']:6} {r['found_ibn_ishaq_voice']:6} "
              f"{r['found_ibn_hisham_voice']:6} {r['found_no_voice']:5}  {'ok' if r['matches'] else 'MISMATCH: to review'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
