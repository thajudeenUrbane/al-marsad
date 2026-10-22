#!/usr/bin/env python3
"""
Expeditions: compile the joined graph into expeditions, review batches, text pages and channel packs.

    .venv/bin/python ingest/ibn_hisham.py fetch                      # the OpenITI text, once (ingest/cache/)
    node expeditions/compile/sky.cjs <hygdata_v41.csv> <astronomy-engine dir>
    .venv/bin/python expeditions/compile/compile.py                  # needs Pillow; fetches terrain tiles once

Reads, never writes, the rest of the repository: the full-book claims and their passages
(ingest/claims/), the count checks (ingest/count_checks.py), the cached text for page numbers,
and the Natural Earth land layer the site already ships (site/interactive/data/basemap.json).
Writes only under expeditions/dist/:

    data/index.json            the expeditions, in the order the text tells them
    data/<slug>.json           one expedition: world, cases, people, questions, connections
    data/stars.json            the sky's stars (computed)
    data/review-<slug>.json    the expedition's review batch, with machine flags
    text/<slug>.html           the same expedition as a plain page: no script, any phone
    channels/<slug>.txt        a seven-day message pack for the WhatsApp pilot (experiment X6)

Every element carries one provenance class: attested (a source says it), located (a gazetteer
point, proposed), computed (elevation, astronomy or arithmetic from stated assumptions) or
schematic (layout only). Nothing here is reviewed; every claim is proposed.
"""

from __future__ import annotations

import base64
import html
import json
import math
import re
import shutil
import struct
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
XROOT = HERE.parent
ROOT = XROOT.parent
sys.path.insert(0, str(ROOT / "ingest"))
import count_checks as cc  # noqa: E402
import ibn_hisham as ih  # noqa: E402
import sira_derive as sd  # noqa: E402

DEFS = json.loads((XROOT / "defs" / "expeditions.json").read_text(encoding="utf-8"))
BUILD = XROOT / "build"
CACHE = XROOT / ".cache"
DIST = XROOT / "dist"
APP = XROOT / "app"
COUNTS = json.loads((ih.CLAIMS_DIR / "ibn-hisham-full-counts.json").read_text(encoding="utf-8"))
BASEMAP = ROOT / "site" / "interactive" / "data" / "basemap.json"
SUSPECTS = ih.CLAIMS_DIR / "ibn-hisham-full-suspects.tsv"

Z, CROP, GRID = 12, 640, 160      # terrain: z12 tiles, a 640-pixel square (~22 km), 160 samples a side
TILES = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
PARTICIPATION = {"rel_participated_in", "rel_present_at"}
SOURCE = "Ibn Hishām, al-Sīra al-Nabawiyya"
EDITION = "Cairo 1955 edition (provisional, page numbers not checked in print)"


# ---------------------------------------------------------------- the graph

class Graph:
    def __init__(self):
        self.raw, self.passages, self.claims = sd.load()
        self.text = ih.Text(self.raw)
        self.pby = {p["id"]: p for p in self.passages}
        self.voice, self.sides = {}, []
        for line in sd.OUT.open(encoding="utf-8"):
            r = json.loads(line)
            if r["t"] == "annot":
                self.voice[r["claim"]] = r.get("voice")
            elif r["t"] == "side":
                self.sides.append(r)
        self.suspects = set()
        if SUSPECTS.exists():
            for line in SUSPECTS.read_text(encoding="utf-8").splitlines()[1:]:
                if line.strip():
                    self.suspects.add(line.split("\t")[0])

    def page(self, pos: int) -> str:
        p = self.text.page(pos)
        return f"vol. {p[0]}, p. {p[1]}" if p else "page not marked"

    def find(self, phrase: str) -> int:
        """The offset of a phrase in the text, allowing for line breaks and the ~~ continuation marks."""
        pat = r"[\s~]+".join(re.escape(w) for w in phrase.replace("~~", " ").split())
        m = re.search(pat, self.raw)
        if not m:
            sys.exit(f"phrase not found in the text: {phrase}")
        return m.start()

    def cite(self, c: dict) -> dict:
        p = self.pby[c["passage"]]
        return {"id": c["id"], "gloss": c.get("gloss", ""), "section": int(p["key"][1:]),
                "page": self.page(p["start"]), "voice": voice_code(self.voice.get(c["id"]))}


def voice_code(v):
    return {"ibn_ishaq": "ishq", "ibn_hisham": "hish"}.get(v, "none")


def person(x) -> str | None:
    return x["name"] if isinstance(x, dict) and x.get("kind") == "person" and x["name"] != sd.PROPHET else None


# ---------------------------------------------------------------- places and terrain

def tile_xy(lat, lon):
    n = 2 ** Z
    return (lon + 180) / 360 * n * 256, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n * 256


def terrain(lat, lon):
    cx, cy = tile_xy(lat, lon)
    x0, y0 = int(cx - CROP / 2), int(cy - CROP / 2)
    tx0, ty0, tx1, ty1 = x0 // 256, y0 // 256, (x0 + CROP) // 256, (y0 + CROP) // 256
    (CACHE / "tiles").mkdir(parents=True, exist_ok=True)
    mosaic = Image.new("RGB", ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256))
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            f = CACHE / "tiles" / f"t_{Z}_{tx}_{ty}.png"
            if not f.exists():
                f.write_bytes(urllib.request.urlopen(TILES.format(z=Z, x=tx, y=ty), timeout=60).read())
            mosaic.paste(Image.open(f).convert("RGB"), ((tx - tx0) * 256, (ty - ty0) * 256))
    ox, oy, px, step = x0 - tx0 * 256, y0 - ty0 * 256, mosaic.load(), CROP / GRID
    hs = []
    for j in range(GRID):
        for i in range(GRID):
            acc = k = 0
            for dj in range(0, int(step), 2):
                for di in range(0, int(step), 2):
                    r, g, b = px[ox + int(i * step) + di, oy + int(j * step) + dj]
                    acc += r * 256 + g + b / 256 - 32768
                    k += 1
            hs.append(acc / k)
    lo = min(hs)
    raw = struct.pack(f"<{len(hs)}H", *[max(0, min(65535, round(h - lo))) for h in hs])
    mpp = 40075016.686 * math.cos(math.radians(lat)) / (2 ** Z * 256)
    return {"n": GRID, "size_km": round(CROP * mpp / 1000, 3), "base_m": round(lo, 1), "max_m": round(max(hs), 1),
            "h": base64.b64encode(raw).decode(),
            "source": "Terrain Tiles on AWS Open Data (Mapzen), from SRTM and other public sources: present-day elevation"}


def geo(a, b):
    """Bearing (degrees from north) and great-circle distance (km) from a to b."""
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    y = math.sin(lo2 - lo1) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(lo2 - lo1)
    d = 2 * 6371 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))
    return round((math.degrees(math.atan2(y, x)) + 360) % 360, 1), round(d, 1)


def compass(deg):
    return ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"][int((deg + 22.5) % 360 // 45)]


def land(bbox):
    """Natural Earth land rings (public domain) that touch the box, as the site already ships them."""
    rings = json.loads(BASEMAP.read_text(encoding="utf-8"))["layers"]["land"]["rings"]
    w, s, e, n = bbox
    return [r for r in rings if any(w - 1 <= x <= e + 1 and s - 1 <= y <= n + 1 for x, y in r)]


# ---------------------------------------------------------------- cases

def count_lists(g: Graph, keys):
    """The people each requested count check's list names, by voice (the same list edges as ingest/count_checks.py)."""
    totals, out = {}, {}
    for ck in cc.CHECKS:
        after = ck["start"].startswith("after:")
        s0 = totals[ck["start"][6:]] if after else g.raw.find(ck["start"])
        t0 = g.raw.find(ck["total"], s0)
        totals[ck["key"]] = t0 + len(ck["total"])
        if ck["key"] not in keys:
            continue
        end = t0 if ck["end"] == "total" else g.raw.find(cc.TOP_HEADING, t0)
        lo = min(s0, t0)
        in_list = {p["id"] for p in g.passages if (lo <= p["start"] < end or p["start"] <= lo < p["end"]) and p["start"] < end}
        people, ids = {}, []
        for c in g.claims:
            if c["passage"] not in in_list or c["predicate"] not in ck["preds"] or sd.name(c["object"]) not in ck["events"]:
                continue
            n = person(c["subject"])
            if not n:
                continue
            ids.append(c["id"])
            row = people.setdefault(n, {"voices": set(), "share": False, "c": c})
            row["voices"].add(g.voice.get(c["id"]) or "none")
            row["share"] |= "share" in c.get("gloss", "").lower()
        rows = []
        for n, r in people.items():
            v = "ishq" if "ibn_ishaq" in r["voices"] else "hish" if "ibn_hisham" in r["voices"] else "none"
            ci = g.cite(r["c"])
            rows.append({"name": n, "voice": v, "share": r["share"], "section": ci["section"], "page": ci["page"],
                         "gloss": r["c"]["gloss"] if r["share"] else "", "claim": r["c"]["id"]})
        rows.sort(key=lambda r: r["section"])
        stated = next(x for x in COUNTS["checks"] if x["key"] == ck["key"])
        out[ck["key"]] = {"key": ck["key"], "what": ck["en"], "stated": ck["n"], "found": len(rows),
                          "voices": {v: sum(r["voice"] == v for r in rows) for v in ("ishq", "hish", "none")},
                          "total_page": g.page(stated["total_at"]["offset"]), "people": rows, "claims": ids}
    return out


def count_case(g, case):
    lists = count_lists(g, set(case["keys"]))
    out = {"type": "count", "title": case["title"], "lists": [lists[k] for k in case["keys"]]}
    groups = case.get("groups")
    if groups:
        # the grand list is the last key; tag each of its names with the clan lists that hold it
        member = defaultdict(list)
        for k, label in groups.items():
            for r in lists[k]["people"]:
                member[r["name"]].append(label)
        grand = lists[case["keys"][-1]]
        for r in grand["people"]:
            r["groups"] = member.get(r["name"], [])
        out["groups"] = list(groups.values())
        out["group_sum"] = sum(lists[k]["stated"] for k in groups)
        out["twice"] = [r["name"] for r in grand["people"] if len(r["groups"]) > 1]
        out["after_totals"] = [r["name"] for r in grand["people"] if not r["groups"]]
        for k in groups:          # the grand list carries the names; keep only counts for the clan lists
            lists[k]["people"] = []
    return out


def sky_for(slug):
    f = BUILD / "sky" / f"{slug}.json"
    if not f.exists():
        sys.exit(f"{f.relative_to(ROOT)} is missing: run expeditions/compile/sky.cjs first")
    return json.loads(f.read_text(encoding="utf-8"))


def date_case(g, x, case, sky):
    d = x["date"]
    claims = [g.cite(c) for c in g.claims if c["predicate"] == "rel_dated" and isinstance(c["subject"], dict)
              and sd.name(c["subject"]) in set(x["events"])]
    return {"type": "date", "title": case["title"], "weekday_text": d["weekday"], "text_en": d["text_en"], "text_ar": d["text_ar"],
            "page": g.page(g.find(d["find"])), "claims": claims, "tabular": sky["tabular"], "rule": sky["crescent_rule"],
            "candidates": [{"key": c["key"], "day": c["day"], "weekday": c["weekday"], "match": c["weekday"] == d["weekday"],
                            "crescent_evening": c["crescent_evening"], "conjunction": c["conjunction"]} for c in sky["candidates"]]}


def moment_case(g, x, case, sky):
    m = x["date"]["moment"]
    return {"type": "moment", "title": case["title"], "text_en": m["text_en"], "page": g.page(g.find(m["find"])),
            "date_text_en": x["date"]["text_en"], "date_page": g.page(g.find(x["date"]["find"])),
            "candidates": [{"key": c["key"], "day": c["day"], "night_hours": c["night_hours"], "moment_ut": c["moment_ut"],
                            "moon_alt": c["moment_moon"][0], "moon_az": c["moment_moon"][1], "illuminated": c["moon_illuminated_pct"],
                            "local_offset_minutes": c["local_offset_minutes"]} for c in sky["candidates"]]}


def route_case(g, x, case):
    r = x["route"]
    places = DEFS["places"]
    via = {}
    for c in g.claims:
        if c["predicate"] == "rel_travelled_via" and person(c["subject"]) is None and isinstance(c["object"], dict):
            via.setdefault(sd.name(c["object"]), c)
    start = r["start"]
    stages, located, prev = [], [places[start]], places[start]
    for i, s in enumerate(r["stages"], 1):
        row = {"n": i, "ar": s["ar"], "en": s["en"], "variant": s.get("variant"), "voice": s.get("voice"), "region": bool(s.get("region"))}
        c = via.get(s.get("claim_place"))
        if c:
            row["claim"] = g.cite(c)
        if s.get("place"):
            p = places[s["place"]]
            row.update(lat=p["lat"], lon=p["lon"], source=p["source"], note=s.get("note"))
            row["from_prev_km"] = geo(prev, p)[1]
            prev = p
            located.append(p)
        stages.append(row)
    total = geo(places[start], places[r["stages"][-1]["place"]])[1]
    lat = [p["lat"] for p in located]
    lon = [p["lon"] for p in located]
    bbox = [min(lon) - 0.9, min(lat) - 0.5, max(lon) + 0.9, max(lat) + 0.5]
    return {"type": "route", "title": case["title"], "page": g.page(g.find(r["find"])), "start": places[start],
            "stages": stages, "named": len(stages), "with_claims": sum("claim" in s for s in stages),
            "located": sum("lat" in s for s in stages), "straight_km": total, "bbox": bbox, "land": land(bbox)}


# ---------------------------------------------------------------- one expedition

def people_at(g, x):
    events = set(x["events"])
    rows = {}
    for c in g.claims:
        n = person(c["subject"])
        if not n or not isinstance(c["object"], dict) or sd.name(c["object"]) not in events:
            continue
        if c["predicate"] in PARTICIPATION | {"rel_died_during", "rel_absent_from"}:
            r = rows.setdefault(n, {"name": n, "side": "not recorded", "roles": set(), "claim": c["id"]})
            r["roles"].add({"rel_died_during": "died", "rel_absent_from": "absent"}.get(c["predicate"], "present"))
    for s in g.sides:
        n = person(s["subject"])
        if n and s["event"] in events:
            r = rows.setdefault(n, {"name": n, "side": "not recorded", "roles": set(), "claim": s["id"]})
            r["side"] = s["side"]
    out = sorted(rows.values(), key=lambda r: ({"with": 0, "not recorded": 1, "against": 2}[r["side"]], r["name"]))
    for r in out:
        r["roles"] = sorted(r["roles"])
    return out


def world(x):
    places = DEFS["places"]
    a = places[x["anchor"]]
    t = terrain(a["lat"], a["lon"])
    half = t["size_km"] / 2
    labels = [{"name": a["name"], "x": 0, "z": 0, "inside": True, "class": "located", "source": a["source"], "anchor": True}]
    for key in x["labels"]:
        p = places[key]
        deg, km = geo(a, p)
        dx, dz = km * math.sin(math.radians(deg)), -km * math.cos(math.radians(deg))
        inside = abs(dx) < half * 0.95 and abs(dz) < half * 0.95
        labels.append({"name": p["name"], "x": round(dx, 3), "z": round(dz, 3), "inside": inside, "deg": deg, "km": km,
                       "compass": compass(deg), "class": "located" if inside else "computed", "source": p["source"]})
    lat0, lon0 = a["lat"], a["lon"]
    bbox = [lon0 - 3, lat0 - 2.2, lon0 + 3, lat0 + 2.2]
    for key in x["labels"]:
        p = places[key]
        bbox = [min(bbox[0], p["lon"] - 1), min(bbox[1], p["lat"] - 1), max(bbox[2], p["lon"] + 1), max(bbox[3], p["lat"] + 1)]
    return {"anchor": a, "terrain": t, "labels": labels,
            "map": {"bbox": bbox, "land": land(bbox), "points": [{"name": places[k]["name"], "lat": places[k]["lat"], "lon": places[k]["lon"]} for k in [x["anchor"]] + x["labels"]]}}


def questions(x, cases, w):
    q = []
    far = [lab for lab in w["labels"] if not lab.get("anchor")]
    if far:
        lab = far[0]
        opts = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"]
        q.append({"id": f"{x['slug']}:dir:{lab['name']}", "class": "computed", "q": f"From {w['anchor']['name']}, which way does {lab['name']} lie?",
                  "kind": "one", "opts": opts, "a": opts.index(lab["compass"]), "why": f"{lab['km']:.0f} km at a bearing of {lab['deg']:.0f}°, computed from the gazetteer points."})
    for c in cases:
        if c["type"] == "count":
            L = c["lists"][-1]
            q.append({"id": f"{x['slug']}:count:{L['key']}", "class": "attested", "q": f"What total does the text state for this list: {L['what']}?",
                      "kind": "num", "a": L["stated"], "why": f"Stated at {L['total_page']}. The extraction found {L['found']} names."})
            if c.get("groups"):
                q.append({"id": f"{x['slug']}:groups", "class": "attested", "q": "Which groups does Ibn Isḥāq's list add up from?", "kind": "one",
                          "opts": [", ".join(c["groups"]), "Quraysh, Thaqīf, Hawāzin", "Makkans, Madinans, Bedouin"], "a": 0,
                          "why": f"{' + '.join(str(l['stated']) for l in c['lists'][:-1])} = {c['group_sum']}."})
            if L["voices"]["hish"]:
                q.append({"id": f"{x['slug']}:voice", "class": "attested", "q": "Whose voice adds names that the first author did not count?", "kind": "one",
                          "opts": ["Ibn Hishām, the editor", "A modern historian", "Nobody: the list is untouched"], "a": 0,
                          "why": f"{L['voices']['hish']} names in this list are in Ibn Hishām's voice."})
        elif c["type"] == "date":
            q.append({"id": f"{x['slug']}:weekday", "class": "attested", "q": "On which weekday does the text place it?", "kind": "one",
                      "opts": ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], "a": ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"].index(c["weekday_text"]),
                      "why": f"\"{c['text_en']}\" ({c['page']})."})
            m = sum(k["match"] for k in c["candidates"])
            q.append({"id": f"{x['slug']}:weekday-match", "class": "computed", "q": "Under the simple crescent rule, did any computed lunation give that weekday?", "kind": "one",
                      "opts": ["Yes", "No"], "a": 0 if m else 1, "why": "; ".join(f"{k['key']}: {k['day']}" for k in c["candidates"]) + "."})
        elif c["type"] == "route":
            q.append({"id": f"{x['slug']}:located", "class": "computed", "q": f"The text names {c['named']} places from Makkah to Qubāʾ. How many can be placed on a map here?",
                      "kind": "num", "a": c["located"], "why": f"{c['located']} have a gazetteer point; {c['with_claims']} are recorded as claims so far."})
        elif c["type"] == "moment":
            k = next(k for k in c["candidates"] if k["key"] == "tabular")
            q.append({"id": f"{x['slug']}:moon", "class": "computed", "q": "When a third of the night had passed, was the moon up?", "kind": "one",
                      "opts": ["Yes, high and nearly full", "Yes, a thin crescent low in the west", "No, it had set"], "a": 0 if k["moon_alt"] > 10 and k["illuminated"] > 80 else 2,
                      "why": f"Computed for the tabular lunation: {k['moon_alt']:.0f}° up, {k['illuminated']:.0f}% lit."})
    return q


def review_batch(g, x, cases, people, exposure):
    events = set(x["events"])
    ids = set(exposure)
    for c in g.claims:
        if isinstance(c["object"], dict) and sd.name(c["object"]) in events:
            ids.add(c["id"])
        if isinstance(c["subject"], dict) and sd.name(c["subject"]) in events:
            ids.add(c["id"])
    two = set()
    after = set()
    for c in cases:
        if c["type"] == "count" and c.get("groups"):
            two |= set(c["twice"])
            after |= set(c["after_totals"])
    by_id = {c["id"]: c for c in g.claims}
    mismatch = set()
    for c in cases:
        if c["type"] == "count":
            for L in c["lists"]:
                if L["found"] != L["stated"]:
                    mismatch |= set(L["claims"])
    items = []
    for i in sorted(ids):
        c = by_id.get(i)
        if not c:
            continue
        s, o = c["subject"], c["object"]
        sn = (sd.name(s) if isinstance(s, dict) else str(s)) or ""
        on = (sd.name(o) if isinstance(o, dict) else str(o)) or "" if o is not None else ""
        flags = []
        if g.voice.get(i) in (None, "none"):
            flags.append("voice not tagged")
        if sn in two:
            flags.append("name in two clan lists")
        if sn in after:
            flags.append("after the last clan total")
        if re.search(r"\(\d\)", sn + on):
            flags.append("numbered name: identity question")
        if "share" in c.get("gloss", "").lower():
            flags.append("counted without being present")
        if i in g.suspects:
            flags.append("listed in the suspects file")
        if i in mismatch:
            flags.append("in a list whose count does not match")
        ci = g.cite(c)
        items.append({"id": i, "predicate": c["predicate"].replace("rel_", "").replace("_", " "), "subject": sn, "object": on,
                      "gloss": c.get("gloss", ""), "section": ci["section"], "page": ci["page"], "voice": ci["voice"],
                      "flags": flags, "seen_in": exposure.get(i, 0)})
    items.sort(key=lambda r: (-r["seen_in"], -len(r["flags"]), r["section"]))
    return {"slug": x["slug"], "title": x["title"], "format_note": "Decisions export as marsad-review-decisions version 1 (docs/handover/slice-3a.md), for review/import_decisions.py.",
            "count": len(items), "flagged": sum(bool(r["flags"]) for r in items), "items": items}


def compile_one(g, x, order):
    w = world(x)
    sky = sky_for(x["slug"]) if x["date"] else None
    cases = []
    for case in x["cases"]:
        if case["type"] == "count":
            cases.append(count_case(g, case))
        elif case["type"] == "date":
            cases.append(date_case(g, x, case, sky))
        elif case["type"] == "moment":
            cases.append(moment_case(g, x, case, sky))
        elif case["type"] == "route":
            cases.append(route_case(g, x, case))
    people = people_at(g, x)
    exposure = defaultdict(int)
    for c in cases:
        for L in c.get("lists", []):
            for i in L["claims"]:
                exposure[i] += 1
        for k in c.get("claims", []):
            exposure[k["id"]] += 2
        for s in c.get("stages", []):
            if "claim" in s:
                exposure[s["claim"]["id"]] += 2
    data = {
        "slug": x["slug"], "order": order, "title": x["title"], "short": x["short"], "era": x["era"],
        "notice": x["notice"], "world": w, "cases": cases,
        "sky": ({"scene": sky["scene"], "tabular": sky["tabular"], "rule": sky["crescent_rule"], "method": sky["method"],
                 "text_en": x["date"]["text_en"], "text_ar": x["date"]["text_ar"], "page": g.page(g.find(x["date"]["find"])),
                 "candidates": sky["candidates"]} if sky else {"none": x.get("no_date_note", "")}),
        "people": {"with": sum(p["side"] == "with" for p in people), "against": sum(p["side"] == "against" for p in people),
                   "unrecorded": sum(p["side"] == "not recorded" for p in people), "rows": people},
        "source": {"work": SOURCE, "edition": EDITION},
    }
    data["questions"] = questions(x, cases, w)
    batch = review_batch(g, x, cases, people, exposure)
    for L in (c for c in cases if c["type"] == "count"):
        for li in L["lists"]:
            li.pop("claims")
    data["review"] = {"count": batch["count"], "flagged": batch["flagged"]}
    return data, batch


def connections(all_data):
    seen = defaultdict(list)
    for d in all_data:
        for p in d["people"]["rows"]:
            if "present" in p["roles"] or p["side"] != "not recorded":
                seen[p["name"]].append(d["slug"])
    for d in all_data:
        rows = [{"name": n, "also": [s for s in slugs if s != d["slug"]]} for n, slugs in seen.items() if d["slug"] in slugs and len(slugs) > 1]
        rows.sort(key=lambda r: (-len(r["also"]), r["name"]))
        d["connections"] = rows


# ---------------------------------------------------------------- plain pages and channel packs

TEXT_CSS = """body{margin:0;overflow-wrap:break-word;background:#0b1020;color:#e8edf5;font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans","Noto Naskh Arabic",sans-serif}
main{max-width:46rem;margin:0 auto;padding:24px max(16px,env(safe-area-inset-right,0px)) 64px max(16px,env(safe-area-inset-left,0px))}
a{color:#cfe3ff}h1{font-size:1.8rem;margin:.2em 0}h2{font-size:1.2rem;margin-top:2em;border-top:1px solid #2b3858;padding-top:1em}
.k{color:#a6b2c6;font-size:.8rem;text-transform:uppercase;letter-spacing:.08em}.m{color:#a6b2c6}.c{font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;padding:0 5px;border-radius:3px;color:#0b1020;margin-right:6px}
.attested{background:#e6b450}.located{background:#2cb98f}.computed{background:#6cb6ff}.schematic{background:#9aa3b5}
table{border-collapse:collapse;width:100%;font-size:.92rem}td,th{text-align:left;padding:4px 6px;border-bottom:1px solid #2b3858;vertical-align:top}
.wrap{overflow-x:auto}ul.names{columns:2;font-size:.9rem}[lang=ar]{font-family:"Noto Naskh Arabic","Amiri",serif;font-size:1.1em}
@media print{body{background:#fff;color:#000}a{color:#000}.m{color:#333}}"""


def tag(cls):
    return f'<span class="c {cls}">{cls}</span>'


def text_page(d, all_data):
    e = html.escape
    w, out = d["world"], []
    out.append(f'<p class="k">al-Marṣad Expeditions · plain version</p><h1>{e(d["title"])}</h1>')
    out.append(f'<p class="m">This page carries every fact the interactive expedition shows, with no script. Nothing here is scholar-reviewed: names and links are claims an AI extraction pass proposed from {SOURCE}, {EDITION}. <a href="../index.html#x-{d["slug"]}">Open the interactive version</a>.</p>')
    a = w["anchor"]
    out.append(f'<h2>The place</h2><p>{tag("located")}{e(a["name"])}: {a["lat"]:.4f}, {a["lon"]:.4f}. <span class="m">{e(a["source"])}.</span></p><ul>')
    for lab in w["labels"][1:]:
        out.append(f'<li>{tag("computed")}{e(lab["name"])} lies {lab["km"]:.0f} km to the {lab["compass"]} (bearing {lab["deg"]:.0f}°), straight-line from gazetteer points.</li>')
    out.append(f'</ul><p>{tag("computed")}Ground: present-day elevation, {w["terrain"]["size_km"]:.0f} km square, {w["terrain"]["base_m"]:.0f} to {w["terrain"]["max_m"]:.0f} m.</p>')
    s = d["sky"]
    out.append("<h2>The date and the sky</h2>")
    if "none" in s:
        out.append(f"<p>{e(s['none'])}</p>")
    else:
        out.append(f'<p>{tag("attested")}The text says: “{e(s["text_en"])}” <span lang="ar" dir="rtl">({e(s["text_ar"])})</span>, {e(s["page"])}. English is an AI draft.</p>')
        out.append(f'<p>{tag("computed")}The modern tabular calendar points to {e(s["tabular"])}. One sky per candidate lunation:</p><div class="wrap"><table><tr><th>Lunation</th><th>Day (Julian)</th><th>Moon lit</th></tr>')
        for c in s["candidates"]:
            out.append(f'<tr><td>{c["key"]}</td><td>{e(c["day"])}</td><td>{c["moon_illuminated_pct"]:.0f}%</td></tr>')
        out.append(f'</table></div><p class="m">{e(s["rule"])} {e(s["method"])}.</p>')
    for c in d["cases"]:
        out.append(f"<h2>Case: {e(c['title'])}</h2>")
        if c["type"] == "count":
            for L in c["lists"]:
                v = L["voices"]
                out.append(f'<p>{tag("attested")}{e(L["what"])}: the text states <b>{L["stated"]}</b> ({e(L["total_page"])}). {tag("computed")}The extraction found <b>{L["found"]}</b> names'
                           + (f': {v["ishq"]} in Ibn Isḥāq\'s voice, {v["hish"]} in Ibn Hishām\'s, {v["none"]} untagged.' if L["people"] else ".") + "</p>")
            if c.get("groups"):
                out.append(f'<p>{tag("computed")}The clan totals add to {c["group_sum"]}. {len(c["twice"])} names sit in two clan lists; {len(c["after_totals"])} come after the last clan total.</p>')
            L = c["lists"][-1]
            out.append('<details><summary>Every name in the list</summary><ul class="names">' + "".join(
                f'<li>{e(r["name"])} <span class="m">({ {"ishq": "Ibn Isḥāq", "hish": "Ibn Hishām", "none": "untagged"}[r["voice"]] }, {e(r["page"])})</span></li>' for r in L["people"]) + "</ul></details>")
        elif c["type"] == "date":
            for k in c["claims"]:
                out.append(f'<p>{tag("attested")}{e(k["gloss"])} <span class="m">(section {k["section"]}, {e(k["page"])})</span></p>')
            out.append("<ul>" + "".join(f'<li>{tag("computed")}{k["key"]} lunation: {e(k["day"])} {"(matches the text)" if k["match"] else ""}</li>' for k in c["candidates"]) + "</ul>")
            out.append('<p class="m">The weekday in the text and the computed weekday are kept apart. A mismatch is a question for the scholars, never a correction.</p>')
        elif c["type"] == "moment":
            out.append(f'<p>{tag("attested")}“{e(c["text_en"])}” ({e(c["page"])}).</p><ul>')
            for k in c["candidates"]:
                out.append(f'<li>{tag("computed")}{k["key"]} lunation, {e(k["day"])}: at a third of the night the Moon was {k["moon_alt"]:.0f}° up and {k["illuminated"]:.0f}% lit.</li>')
            out.append("</ul>")
        elif c["type"] == "route":
            out.append(f'<p>{tag("attested")}The text names {c["named"]} places on the road ({e(c["page"])}). {tag("computed")}{c["located"]} can be placed; {c["with_claims"]} are recorded as claims so far. Thawr to Qubāʾ is {c["straight_km"]:.0f} km in a straight line; any road is longer.</p>')
            out.append('<div class="wrap"><table><tr><th>#</th><th>Place</th><th>Arabic</th><th>Status</th></tr>' + "".join(
                f'<tr><td>{s["n"]}</td><td>{e(s["en"])}{" <span class=m>(" + e(s["variant"]) + ")</span>" if s.get("variant") else ""}</td><td lang="ar" dir="rtl">{e(s["ar"])}</td><td>'
                + (tag("located") if "lat" in s else ('<span class="m">a region</span>' if s["region"] else '<span class="m">named, not located</span>'))
                + ("claim " if "claim" in s else "") + "</td></tr>" for s in c["stages"]) + "</table></div>")
    p = d["people"]
    out.append(f'<h2>Who the text places here</h2><p>{tag("attested")}{p["with"]} named with the Prophet ﷺ, {p["against"]} against him, {p["unrecorded"]} with no side recorded.</p>')
    if d["connections"]:
        names = {x["slug"]: x["short"] for x in all_data}
        out.append(f'<h2>Connections</h2><p>{tag("computed")}Joined from attested claims: people this text places at this event and at another expedition\'s event.</p><ul>')
        for r in d["connections"][:30]:
            out.append(f'<li>{e(r["name"])}: also {", ".join(e(names[s]) for s in r["also"])}</li>')
        out.append("</ul>")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(d["short"])} · plain version</title><style>{TEXT_CSS}</style></head>
<body><main>{"".join(out)}<h2>Sources</h2><p class="m">{SOURCE}, OpenITI 0213IbnHisham.SiraNabawiyya.Shamela0023833-ara1 ({EDITION}); al-Thurayya Gazetteer (CC BY 4.0); Wikidata (CC0); Terrain Tiles (Mapzen); astronomy-engine (MIT); HYG star catalogue (CC BY-SA 4.0). <a href="index.html">All expeditions</a>.</p></main></body></html>
"""


def text_index(all_data):
    items = "".join(f'<li><a href="{d["slug"]}.html">{html.escape(d["title"])}</a> <span class="m">· {html.escape(d["era"])}</span></li>' for d in all_data)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Expeditions · plain version</title><style>{TEXT_CSS}</style></head>
<body><main><p class="k">al-Marṣad Expeditions</p><h1>Every expedition, as plain text</h1><p class="m">For any phone, any connection, a screen reader or a printer. Nothing is reviewed yet.</p><ul>{items}</ul></main></body></html>
"""


def channel_pack(d):
    s, w = d["sky"], d["world"]
    msgs = []
    a = w["anchor"]
    far = [lab for lab in w["labels"] if not lab.get("anchor")]
    msgs.append(f"{d['title']}. Today we stand at {a['name']}." + (f" {far[0]['name']} is {far[0]['km']:.0f} km to the {far[0]['compass']}, in a straight line." if far else ""))
    if "none" not in s:
        msgs.append(f"The text says: \"{s['text_en']}\" ({SOURCE}, {s['page']}). Question for tomorrow: what would the moon have looked like that night?")
        k = next(c for c in s["candidates"] if c["key"] == "tabular")
        msgs.append(f"Computed, not reported: on the modern calendar's reckoning ({k['day']}) the moon was {k['moon_illuminated_pct']:.0f}% lit. The date conversion itself is uncertain, so scholars keep the reported date and the converted one apart.")
    else:
        msgs.append(s["none"])
    for c in d["cases"]:
        if c["type"] == "count":
            L = c["lists"][-1]
            msgs.append(f"A puzzle: the text gives a total of {L['stated']} for this list ({L['what']}). Before tomorrow, guess: does the list of names hold more, fewer or exactly {L['stated']}?")
            msgs.append(f"Answer: the reading of the list found {L['found']} names. " + ("They agree. Agreement is evidence too." if L["found"] == L["stated"] else "They differ. Scholars keep three things apart: what happened, the text, and our reading of the text."))
        elif c["type"] == "route":
            msgs.append(f"The text names {c['named']} places on the road from Makkah to Qubāʾ. Only {c['located']} can be placed on a map today. Guess which.")
        elif c["type"] == "date" and c["weekday_text"]:
            hit = [k for k in c["candidates"] if k["match"]]
            msgs.append(f"The text gives the weekday: {c['weekday_text']}. " + (f"One computed lunation agrees ({hit[0]['day']})." if hit else "None of the three computed lunations falls on that weekday under a simple crescent rule: a question for the scholars."))
    p = d["people"]
    total = p["with"] + p["against"] + p["unrecorded"]
    msgs.append(f"The text names {total} people at this event" + (f": {p['with']} with the Prophet ﷺ and {p['against']} against him." if p["against"] else "."))
    q = d["questions"][:3]
    msgs.append("Three questions, from memory:\n" + "\n".join(f"{i + 1}. {x['q']}" for i, x in enumerate(q)))
    msgs = msgs[:7]
    body = "\n\n".join(f"Day {i + 1}\n{m}" for i, m in enumerate(msgs))
    return f"# {d['title']}: seven messages for the WhatsApp pilot (experiment X6)\n# Draft. Not reviewed. A teacher reads each one before it is sent.\n\n{body}\n"


# ---------------------------------------------------------------- main

def main():
    g = Graph()
    for sub in ("data", "text", "channels"):
        (DIST / sub).mkdir(parents=True, exist_ok=True)
    all_data, batches = [], []
    for order, x in enumerate(DEFS["expeditions"], 1):
        d, b = compile_one(g, x, order)
        all_data.append(d)
        batches.append(b)
    connections(all_data)
    index = {"title": "al-Marṣad Expeditions", "source": {"work": SOURCE, "edition": EDITION},
             "classes": {"attested": "a source says it", "located": "a gazetteer point, proposed", "computed": "from elevation, astronomy or arithmetic, under stated assumptions", "schematic": "layout only, claims nothing"},
             "expeditions": [{"slug": d["slug"], "order": d["order"], "title": d["title"], "short": d["short"], "era": d["era"],
                              "anchor": d["world"]["anchor"]["name"], "dated": "none" not in d["sky"], "questions": len(d["questions"]),
                              "review": d["review"], "people": d["people"]["with"] + d["people"]["against"] + d["people"]["unrecorded"]} for d in all_data]}
    write = lambda p, obj: p.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    write(DIST / "data" / "index.json", index)
    shutil.copy(BUILD / "sky" / "stars.json", DIST / "data" / "stars.json")
    for d, b in zip(all_data, batches):
        write(DIST / "data" / f"{d['slug']}.json", d)
        write(DIST / "data" / f"review-{d['slug']}.json", b)
        (DIST / "text" / f"{d['slug']}.html").write_text(text_page(d, all_data), encoding="utf-8")
        (DIST / "channels" / f"{d['slug']}.txt").write_text(channel_pack(d), encoding="utf-8")
        size = (DIST / "data" / f"{d['slug']}.json").stat().st_size
        print(f"{d['slug']:10} {size / 1024:6.0f} KB  people {len(d['people']['rows']):4}  questions {len(d['questions'])}  "
              f"review {b['count']} ({b['flagged']} flagged)  connections {len(d['connections'])}")
    (DIST / "text" / "index.html").write_text(text_index(all_data), encoding="utf-8")
    # the app: copied as written; index.html also as a publish copy without its document wrapper
    for f in APP.iterdir():
        shutil.copy(f, DIST / f.name)
    page = (APP / "index.html").read_text(encoding="utf-8")
    bare = page
    for tag_ in ("<!doctype html>\n", '<html lang="en" dir="ltr">\n', "<head>\n", '<meta charset="utf-8">\n',
                 '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n', "</head>\n", "<body>\n", "</body>\n", "</html>\n"):
        if tag_ not in bare:
            sys.exit(f"app/index.html: expected {tag_!r}")
        bare = bare.replace(tag_, "", 1)
    (DIST / "publish.html").write_text(bare, encoding="utf-8")
    total = sum(f.stat().st_size for f in DIST.rglob("*") if f.is_file())
    print(f"dist: {total / 1024:.0f} KB in {sum(1 for f in DIST.rglob('*') if f.is_file())} files")


if __name__ == "__main__":
    main()
