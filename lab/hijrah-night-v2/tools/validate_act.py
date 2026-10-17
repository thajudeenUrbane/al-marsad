#!/usr/bin/env python3
"""Validate act files against SCHEMA.md.  python3 lab/hijrah-night-v2/tools/validate_act.py acts/act07.json [...]"""
import csv, json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
KEYS = {r["key"] for r in csv.DictReader(open(HERE / "data/places.csv", encoding="utf-8"))}
SECS = {json.loads(l)["key"] for l in open(ROOT / "ingest/claims/ibn-hisham-full-passages.jsonl", encoding="utf-8")}
GRADES = {"established", "supported", "disputed", "reconstruction"}
ROLES = {"prophet", "person", "group", "stone", "group-stone"}
SKY = {"night", "dawn", "day", "midday", "dusk"}
ARABIC = re.compile(r"[؀-ۿ]{2,}(?:\s+[؀-ۿ]{2,}){6,}")  # 7+ Arabic words in a row = running text
def loc(v, where, errs):
    if isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v): return
    if isinstance(v, str) and (v in KEYS or v.startswith("~")): return
    errs.append(f"{where}: unknown place {v!r}")
def stmt(s, where, errs):
    if not isinstance(s, dict) or not s.get("text"): errs.append(f"{where}: statement needs text"); return
    g = s.get("grade")
    if g not in GRADES: errs.append(f"{where}: bad grade {g!r}")
    src = s.get("sources") or []
    if g == "reconstruction":
        if not s.get("basis"): errs.append(f"{where}: reconstruction needs basis")
    elif not src: errs.append(f"{where}: {g} needs sources")
    if g == "disputed" and not s.get("note") and not any(x.get("note") for x in src): errs.append(f"{where}: disputed needs a note")
    if g == "established" and not (any(x.get("type") in ("quran", "hadith") for x in src) or len(src) >= 2): errs.append(f"{where}: established needs quran/hadith or 2 sources")
    for x in src:
        t = x.get("type")
        if t == "ibn-hisham" and x.get("sec") not in SECS and not re.fullmatch(r"S\d{4}", str(x.get("sec"))): errs.append(f"{where}: bad section {x.get('sec')}")
        if t not in ("ibn-hisham", "quran", "hadith", "other"): errs.append(f"{where}: bad source type {t}")
        if t == "quran" and not re.fullmatch(r"\d{1,3}:\d{1,3}(-\d{1,3})?", str(x.get("ref"))): errs.append(f"{where}: bad quran ref {x.get('ref')}")
    if ARABIC.search(s["text"]): errs.append(f"{where}: looks like running Arabic text")
def check(path):
    errs, d = [], json.load(open(path, encoding="utf-8"))
    for k in ("act", "title", "units"):
        if k not in d: errs.append(f"missing {k}")
    ids = set()
    for i, u in enumerate(d.get("units", [])):
        w = f"{u.get('id', i)}"
        if u.get("id") in ids: errs.append(f"{w}: duplicate id")
        ids.add(u.get("id"))
        for k in ("id", "title", "sky", "camera", "statements", "sections"):
            if k not in u: errs.append(f"{w}: missing {k}")
        if u.get("sky") not in SKY: errs.append(f"{w}: bad sky")
        cam = u.get("camera", {}); loc(cam.get("target"), w + ".camera", errs)
        for k in ("dist", "pitch", "heading"):
            if not isinstance(cam.get(k), (int, float)): errs.append(f"{w}: camera.{k} missing")
        if u.get("place"): loc(u["place"].get("key"), w + ".place", errs)
        for r in u.get("route", []): loc(r, w + ".route", errs)
        for L in u.get("lights", []):
            if L.get("role") not in ROLES: errs.append(f"{w}: bad light role {L.get('role')}")
            if L.get("role") == "prophet" and "Prophet" not in L.get("name", ""): errs.append(f"{w}: prophet role only for the Prophet ﷺ")
        st = u.get("statements", [])
        if not 3 <= len(st) <= 10: errs.append(f"{w}: {len(st)} statements (want 4–9)")
        for j, s in enumerate(st): stmt(s, f"{w}.s{j}", errs)
        for q in u.get("quran", []):
            if not re.fullmatch(r"\d{1,3}:\d{1,3}(-\d{1,3})?", str(q.get("ref"))) or not q.get("gist"): errs.append(f"{w}: bad quran item")
        for dd in u.get("discover", []):
            if dd.get("camera"): loc(dd["camera"].get("target"), w + ".discover", errs)
            if dd.get("reveal"): stmt(dd["reveal"], w + ".discover", errs)
        q = u.get("question")
        if q:
            if q.get("kind") not in ("predict", "recall", "reflect"): errs.append(f"{w}: bad question kind")
            if q.get("kind") != "reflect" and not any(o.get("ok") for o in q.get("options", [])): errs.append(f"{w}: question has no right option")
        for s in u.get("sections", []):
            if not re.fullmatch(r"S\d{4}", s): errs.append(f"{w}: bad section {s}")
    return errs, len(d.get("units", []))
bad = 0
for p in sys.argv[1:]:
    e, n = check(p)
    print(f"{p}: {n} units, {len(e)} problems"); [print("  -", x) for x in e[:40]]; bad += bool(e)
sys.exit(1 if bad else 0)
