#!/usr/bin/env python3
"""
Slice 11a, a one-time fix kept for the record (docs/CHANGELOG-data.md): the full-book pass
linked 1,142 claims to events of the AI-generated 50 Stories ("The Battle of Badr", story
20) instead of the historical events of the curated corpus ("Battle of Badr"). A story is
a telling, never the event itself (docs/02; slice 1c kept them apart on purpose), so these
claims are pointed at the historical event: an existing one where the corpus has it, or a
new event, needs-review, where it has none. The story events themselves are untouched.

    .venv/bin/python ingest/fix_story_events.py          # apply (idempotent: a second run changes nothing)

Afterwards: ingest/sira_derive.py build, ingest/count_checks.py, ingest/ibn_hisham.py build all.
"""

import csv
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ibn_hisham as ih  # noqa: E402
import sira_full as sf  # noqa: E402

# story event (as the pass named it) -> historical event: an existing preferred name, or ("new", name)
FIX = {
    "The Battle of Badr": "Battle of Badr",
    "The Battle of Uhud": "Battle of Uḥud",
    "The Battle of the Trench (al-Khandaq)": "Battle of the Trench (Khandaq)",
    "The Conquest of Khaybar": "The Khaybar campaign",
    "The Battle of Mu'tah": "The expedition of Muʾta",
    "The Conquest of Makkah": "Conquest of Makkah",
    "The Treaty of Hudaybiyah": "Ḥudaybiyya and the Pledge of Riḍwān",
    "The Journey to Ta'if": "The journey to Ta'if",
    "Arrival in Madinah and the Building of the Mosque": "Arrival in Madinah and early community-building",
    "Ja'far Before the Negus of Abyssinia": "The Quraysh embassy to the Najāshī in Abyssinia",
    "The Brotherhood of the Muhajirun and Ansar": ("new", "The brotherhood of the Muhājirūn and the Anṣār (al-muʾākhāt)"),
    "The Delegation of Najran and the Mubahalah": ("new", "The delegation of the Christians of Najrān"),
    "The First Believers": ("new", "The first believers (Ibn Isḥāq's first eight)"),
    "The Slander Against Aishah (al-Ifk)": ("new", "The affair of the slander (al-ifk)"),
    "The First Adhan": ("new", "The first call to prayer (adhān)"),
    "The Pledges of Aqabah": ("new", "A pledge of al-ʿAqaba (which one, the text does not say)"),
}
NOTE = ("slice 11a (17 Oct 2026): historical event minted in place of a 50 Stories story event the full-book pass "
        "had linked its claims to (docs/CHANGELOG-data.md); not matched to any other row")


def target(v):
    return v[1] if isinstance(v, tuple) else v


def main():
    rows = list(csv.DictReader(ih.IDENTITY.open(encoding="utf-8", newline="")))
    fields = list(rows[0].keys())
    names = {(r["kind"], r["preferred_name_en"]) for r in rows}
    minter = None
    for story, v in FIX.items():
        if ("event", story) not in names:
            sys.exit(f"no story event named {story!r}")
        t = target(v)
        if isinstance(v, tuple):
            if ("event", t) not in names:
                minter = minter or sf.Minter()
                rows.append({"kind": "event", "canonical_id": minter("ev"), "preferred_name_en": t, "name_ar": "",
                             "variant_ids": "", "stories50_names": "", "source_files": "ibn-hisham-full",
                             "confidence": "needs-review", "note": NOTE})
                names.add(("event", t))
        elif ("event", t) not in names:
            sys.exit(f"no historical event named {t!r}")

    changed = 0
    for f in (sf.F_CLAIMS, ih.CLAIMS):
        lines = f.read_text(encoding="utf-8").splitlines()
        out = []
        for line in lines:
            c = json.loads(line)
            hit = False
            for k in ("subject", "object"):
                x = c.get(k)
                if isinstance(x, dict) and x.get("kind") == "event" and x.get("name") in FIX:
                    x["name"] = target(FIX[x["name"]])
                    hit = True
            if hit:
                changed += 1
                line = json.dumps(c, ensure_ascii=False)
            out.append(line)
        f.write_text("\n".join(out) + "\n", encoding="utf-8")

    ents = ih.read_jsonl(sf.F_ENTITIES)
    have = {(e["kind"], e["name"]) for e in ents}
    new = [{"kind": "event", "name": target(v)} for v in FIX.values()
           if isinstance(v, tuple) and ("event", target(v)) not in have]
    if new:
        with sf.F_ENTITIES.open("a", encoding="utf-8") as fh:
            for e in new:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    ih.IDENTITY.write_text(buf.getvalue(), encoding="utf-8")
    print(f"{changed} claims pointed at historical events; {len(new)} new events")
    return 0


if __name__ == "__main__":
    sys.exit(main())
