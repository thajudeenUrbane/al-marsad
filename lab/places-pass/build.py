#!/usr/bin/env python3
"""Proposed geolocation pass for every place in the corpus (lab work, nothing is written to ontology/).

Inputs
  ontology/corpus/identity.csv               places (kind=place): id, English label, Arabic forms
  ontology/corpus/external-coordinates.csv   links already proposed by ontology/tools/link_external.py
  ingest/claims/ibn-hisham-full-entities.jsonl   place_type per name
  al-Thurayya places.geojson (CC BY 4.0)     cached at lab/places-pass/cache/thurayya-places.geojson
  Wikidata SPARQL (CC0), optional            cached at lab/places-pass/cache/wikidata-ar-labels.json

Output
  lab/places-pass/places-proposed.csv        one row per (place, candidate); unlocated places get one empty row

Usage:  python3 lab/places-pass/build.py [--offline]
  --offline uses only the cache files (fails if a cache is missing).

Normalisation follows ontology/tools/link_external.py (fold / name_key / loose_key / ar_key / ar_loose),
reduced to what toponyms need. Coordinates are never invented: every lat/lon comes from a gazetteer row.
"""
import csv
import json
import math
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CACHE = HERE / "cache"
THURAYYA_URL = "https://raw.githubusercontent.com/althurayya/althurayya.github.io/master/master/places.geojson"
WDQS = "https://query.wikidata.org/sparql"
UA = "al-marsad places-pass (https://github.com/al-marsad/al-marsad; research, 1 req/s)"
OFFLINE = "--offline" in sys.argv

# ------------------------------------------------------------------ normalisation (after link_external.py)
SPECIAL = {"ḫ": "kh", "ǧ": "j", "š": "sh", "ṯ": "th", "ḏ": "dh", "ġ": "gh", "ŧ": "a", "ẗ": "a", "ı": "i",
           "ʿ": "", "ʾ": "", "'": "", "’": "", "‘": "", "`": "", "ʻ": "", "ʼ": ""}
ARTICLE = re.compile(r"(?<![a-z])(?:al|el|l|an|ar|as|ash|at|ath|az|ad|adh)-(?=[a-z])")
PAREN = re.compile(r"\([^)]*\)")


def fold(s):
    s = "".join(SPECIAL.get(ch, ch) for ch in s)
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch)).lower()


def tok(t):
    if len(t) > 3 and t.endswith("ah"):
        t = t[:-1]
    t = t.replace("ou", "u").replace("ee", "i")
    return re.sub(r"([aiu])\1+", r"\1", t)


def name_key(s):
    s = ARTICLE.sub("", fold(PAREN.sub(" ", s)))
    return " ".join(tok(t) for t in re.split(r"[^a-z0-9]+", s) if t and t not in ("al", "el", "the"))


def loose_key(k):
    toks = [re.sub(r"(.)\1+", r"\1", t) for t in k.split()]
    if len(toks) > 1 and toks[0] in ("bilad", "ard"):
        toks = toks[1:]
    return " ".join(toks)


AR_MARKS = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭـ]")
AR_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي", "ء": ""})


def ar_key(s):
    s = AR_MARKS.sub("", s).translate(AR_MAP)
    s = re.sub(r"[^ء-ي\s]", " ", s)
    return " ".join(s.split())


def ar_loose(k):
    toks = [t[2:] if t.startswith("ال") and len(t) > 3 else t for t in k.split()]
    if len(toks) > 1 and toks[0] in ("بلاد", "ارض"):
        toks = toks[1:]
    return " ".join(toks)


def ar_variants(form):
    """Arabic forms as quoted in the text carry clitics and case endings: بالطائف, بفدك, نجدا, ذا/ذي."""
    k = ar_key(form)
    out = {ar_loose(k)}
    if k.startswith("بال") and len(k) > 5:
        out.add(ar_loose(k[1:]))
    elif k.startswith("ب") and len(k) > 3 and not k.startswith(("بئر", "بطن", "بقيع", "بدر", "بحر", "بصر",
                                                                "بواط", "بيت", "بين", "بلقا", "بحرين", "بطحا")):
        out.add(ar_loose(k[1:]))
    if k.endswith("ا") and len(k) > 3 and not k.endswith(("اا",)):
        out.add(ar_loose(k[:-1]))
    for a, b in (("ذا ", "ذو "), ("ذي ", "ذو ")):
        if k.startswith(a):
            out.add(ar_loose(b + k[len(a):]))
    return {v for v in out if v}


def haversine(la1, lo1, la2, lo2):
    r = math.pi / 180
    h = math.sin((la2 - la1) * r / 2) ** 2 + math.cos(la1 * r) * math.cos(la2 * r) * math.sin((lo2 - lo1) * r / 2) ** 2
    return 2 * 6371.0 * math.asin(min(1.0, math.sqrt(h)))


# ------------------------------------------------------------------ region plausibility
# Seerah events default to Arabia (al-Thurayya regions Jazirat al-Arab / Badiyat al-Arab / Yemen; or the
# bounding box below). Places the text itself puts elsewhere are listed with their expected macro-region.
ARABIA_BOX = (12.0, 33.0, 34.0, 60.0)  # lat_min, lat_max, lon_min, lon_max
HIJAZ_BOX = (19.0, 29.5, 36.0, 42.5)
ELSEWHERE = {
    "sham": ["Bayt al-Maqdis", "Bayt al-Maqdis (2)", "al-Masjid al-Aqṣā", "Ḥimṣ", "Buṣrā", "Ghazza (Gaza)",
             "ʿAmwās", "Ajnādayn", "al-Balqāʾ", "Māʾab", "Maʿān", "Mu'ta", "Ayla", "al-Dārūm",
             "ʿAfrāʾ (a water in Palestine)", "Marj al-Ṣuffar", "al-Sham", "al-Shām", "Jurash", "Madyan",
             "al-Aqaba", "al-Batrāʾ", "Ḥismā"],
    "iraq": ["al-Ḥīra", "al-Kūfa", "al-Qādisiyya", "Maysān", "ʿAyn al-Tamr", "al-ʿIrāq", "Safawān", "al-Ḥaḍr"],
    "jazira": ["al-Mawṣil", "Mosul", "Nisibis", "al-Jazīra"],
    "iran": ["Iṣfahān"],
    "anatolia": ["ʿAmmūriya", "Land of the Rūm"],
    "habasha": ["al-Habasha (Aksum)"],
}
EXPECT = {lab: reg for reg, labs in ELSEWHERE.items() for lab in labs}
REGION_OK = {
    "arabia": {"Jazirat al-Arab", "Badiyat al-Arab", "Yemen"},
    "sham": {"Sham", "Badiyat al-Arab"}, "iraq": {"Iraq", "Badiyat al-Arab"}, "jazira": {"Aqur"},
    "iran": {"Jibal", "Faris", "Khuzistan"}, "anatolia": {"Rihab", "Aqur", "Sham"}, "habasha": set(),
}
# Labels that name no single point (placeholders, whole regions used as fronts)
NO_POINT = {"Route waypoint (unidentified)", "Jazirat al-Arab (various fronts)", "The coast (al-sāḥil)",
            "Land of the Rūm", "Sayf al-Baḥr"}


def in_box(lat, lon, box):
    return box[0] <= lat <= box[1] and box[2] <= lon <= box[3]


def region_fit(expect, lat, lon, region_code=None):
    if expect == "arabia":
        if region_code in REGION_OK["arabia"] or in_box(lat, lon, ARABIA_BOX):
            return "hijaz" if in_box(lat, lon, HIJAZ_BOX) else "arabia"
        return None
    if region_code in REGION_OK.get(expect, ()):
        return expect
    boxes = {"sham": (29, 37.5, 33, 40), "iraq": (29, 34.5, 42, 49), "jazira": (35, 38.5, 38, 44.5),
             "iran": (28, 36, 46, 56), "anatolia": (36, 42, 26, 40), "habasha": (3, 18, 33, 44)}
    return expect if in_box(lat, lon, boxes[expect]) else None


# ------------------------------------------------------------------ inputs
def fetch(url, data=None, accept=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **({"Accept": accept} if accept else {})})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def load_thurayya():
    p = CACHE / "thurayya-places.geojson"
    if not p.exists():
        if OFFLINE:
            sys.exit("missing cache " + str(p))
        CACHE.mkdir(exist_ok=True)
        p.write_bytes(fetch(THURAYYA_URL))
    rows = []
    for f in json.loads(p.read_text(encoding="utf-8"))["features"]:
        c = f["properties"]["cornuData"]
        lon, lat = f["geometry"]["coordinates"][:2]
        lat_keys = {name_key(c.get(k) or "") for k in ("toponym_translit", "toponym_translit_other", "toponym_search")}
        ar = {ar_loose(ar_key(x)) for k in ("toponym_arabic", "toponym_arabic_other") for x in re.split(r"[،,;]", c.get(k) or "")}
        rows.append({"system": "althurayya", "id": c["cornu_URI"], "label": c["toponym_translit"],
                     "label_ar": c["toponym_arabic"], "lat": float(lat), "lon": float(lon),
                     "region": c.get("region_code", ""), "type": c.get("top_type_hom", ""),
                     "lat_keys": {k for k in lat_keys if k} | {loose_key(k) for k in lat_keys if k},
                     "ar_keys": {k for k in ar if k}})
    return rows


def load_places():
    types = {}
    for line in open(REPO / "ingest/claims/ibn-hisham-full-entities.jsonl", encoding="utf-8"):
        o = json.loads(line)
        if o.get("kind") == "place":
            types[o["name"]] = o.get("place_type", "")
    places = []
    for r in csv.DictReader(open(REPO / "ontology/corpus/identity.csv", encoding="utf-8")):
        if r["kind"] != "place":
            continue
        ar = [a for a in r["name_ar"].split(";") if a.strip()]
        places.append({"id": r["canonical_id"], "label": r["preferred_name_en"], "ar": ar,
                       "type": types.get(r["preferred_name_en"], ""), "confidence": r["confidence"]})
    return places


def load_existing():
    out = {}
    for r in csv.DictReader(open(REPO / "ontology/corpus/external-coordinates.csv", encoding="utf-8")):
        out.setdefault(r["canonical_id"], []).append(r)
    return out


def load_wikidata(places):
    """One SPARQL request: items whose Arabic label equals one of our Arabic forms and that carry P625."""
    p = CACHE / "wikidata-ar-labels.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    if OFFLINE:
        return []
    forms = set()
    for pl in places:
        for a in pl["ar"]:
            for v in ar_variants(a):
                forms.add(v)
                if " " not in v and not v.startswith("ال"):
                    forms.add("ال" + v)
        for a in pl["ar"]:  # raw spellings too: Wikidata labels keep ة, أ, إ
            r = AR_MARKS.sub("", a).strip()
            raw = {r, r[1:] if r.startswith("بال") else r, r[:-1] if r.endswith("ا") and len(r) > 3 else r}
            for x in list(raw):
                raw |= {x.replace("ه", "ة") if x.endswith("ه") else x}
                if not x.startswith("ال") and " " not in x:
                    raw.add("ال" + x)
            forms |= raw
    rows = []
    forms = sorted(forms)
    for i in range(0, len(forms), 120):
        vals = " ".join('"%s"@ar' % f for f in forms[i:i + 120])
        q = ("SELECT ?item ?l ?en ?c WHERE { VALUES ?l { %s } ?item rdfs:label ?l ; wdt:P625 ?c . "
             "OPTIONAL { ?item rdfs:label ?en FILTER(LANG(?en)='en') } }" % vals)
        try:
            raw = fetch(WDQS, urllib.parse.urlencode({"query": q}).encode(), "application/sparql-results+json")
            rows += json.loads(raw)["results"]["bindings"]
        except Exception as e:  # network is optional; the pass still runs on al-Thurayya alone
            print("wikidata batch failed:", e, file=sys.stderr)
        time.sleep(1.1)
    out = []
    for b in rows:
        m = re.match(r"Point\(([-\d.eE]+) ([-\d.eE]+)\)", b["c"]["value"])
        if not m:
            continue
        out.append({"id": b["item"]["value"].rsplit("/", 1)[-1], "label_ar": b["l"]["value"],
                    "label": b.get("en", {}).get("value", ""), "lat": float(m.group(2)), "lon": float(m.group(1))})
    CACHE.mkdir(exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    return out


# ------------------------------------------------------------------ matching
def place_keys(pl):
    base = re.sub(r"\s*\((?:\d+)\)$", "", pl["label"])
    lat = {name_key(base)}
    inner = re.findall(r"\(([^)]*)\)", base)
    lat |= {name_key(x) for x in inner if not re.search(r"\b(a|of|well|valley|various)\b", x)}
    lat = {k for k in lat if k}
    lat |= {loose_key(k) for k in lat}
    ar = set()
    for a in pl["ar"]:
        ar |= ar_variants(a)
    return lat, ar


def candidates(pl, th_lat, th_ar, wd, existing):
    expect = EXPECT.get(re.sub(r"\s*\(\d+\)$", "", pl["label"]), EXPECT.get(pl["label"], "arabia"))
    lat_keys, ar_keys = place_keys(pl)
    found = {}
    for k in lat_keys:
        for t in th_lat.get(k, ()):
            found.setdefault(t["id"], [t, set()])[1].add("latin-name")
    for k in ar_keys:
        for t in th_ar.get(k, ()):
            found.setdefault(t["id"], [t, set()])[1].add("arabic-form")
    cands = []
    for t, ev in found.values():
        cands.append(dict(t, evidence=set(ev)))
    for w in wd:
        if ar_loose(ar_key(w["label_ar"])) in ar_keys:
            ev = {"arabic-form"}
            if w["label"] and (name_key(w["label"]) in lat_keys or loose_key(name_key(w["label"])) in lat_keys):
                ev.add("latin-name")
            cands.append(dict(w, system="wikidata", region="", type="", evidence=ev))
    for r in existing.get(pl["id"], []):
        if r["system"] == "wikidata" and not any(c["system"] == "wikidata" and c["id"] == r["external_id"] for c in cands):
            cands.append({"system": "wikidata", "id": r["external_id"], "label": "", "label_ar": "",
                          "lat": float(r["latitude"]), "lon": float(r["longitude"]), "region": "", "type": "",
                          "evidence": {"linked-by-link_external(" + r["link_confidence"] + ")"}})
    for c in cands:
        c["fit"] = region_fit(expect, c["lat"], c["lon"], c["region"] or None)
        for r in existing.get(pl["id"], []):
            if r["external_id"] == c["id"]:
                c["prior"] = r["link_confidence"]
                c["evidence"].add("linked-by-link_external(" + r["link_confidence"] + ")")
    return expect, cands


def cluster(cands, km=25):
    groups = []
    for c in sorted(cands, key=lambda c: -len(c["evidence"])):
        for g in groups:
            if haversine(g[0]["lat"], g[0]["lon"], c["lat"], c["lon"]) <= km:
                g.append(c)
                break
        else:
            groups.append([c])
    return groups


def grade_place(pl, expect, cands):
    """Returns (place_grade, chosen-group index, note) and sets c['grade'] on each candidate."""
    if pl["label"] in NO_POINT:
        for c in cands:
            c["grade"] = "unlocated"
        return "unlocated", None, "label names no single point (placeholder or open region)"
    good = [c for c in cands if c["fit"]]
    for c in cands:
        if not c["fit"]:
            c["grade"] = "unlocated"
            c["note"] = "outside expected region (%s); homonym, not used" % expect
    if not good:
        return "unlocated", None, ("no gazetteer candidate" if not cands else
                                   "only out-of-region homonyms (%d)" % len(cands))
    groups = cluster(good)
    groups.sort(key=lambda g: (-max(len(c["evidence"]) for c in g),
                               -len({c["system"] for c in g}),
                               -sum(1 for c in g if c["fit"] == "hijaz")))
    best = groups[0]
    systems = {c["system"] for c in best}
    ev = set().union(*(c["evidence"] for c in best))
    both = "latin-name" in ev and "arabic-form" in ev
    prior = {c.get("prior") for c in best}
    spread = max((haversine(a["lat"], a["lon"], b["lat"], b["lon"]) for a in best for b in best), default=0)
    homonym = len(groups) > 1
    if "exact" in prior and not homonym:
        g = "exact"
    elif len(systems) >= 2 and both and spread <= 5 and not homonym:
        g = "exact"
    elif (both or len(systems) >= 2 or "probable" in prior) and not homonym:
        g = "probable"
    elif both and homonym and len(systems) >= 2:
        g = "probable"
    else:
        g = "possible"
    for c in best:
        c["grade"] = g
    for grp in groups[1:]:
        for c in grp:
            c["grade"] = "possible"
            c["note"] = "competing homonym in region"
    note = []
    if homonym:
        note.append("HOMONYM: %d distinct in-region locations" % len(groups))
    if spread > 5:
        note.append("chosen cluster spreads %.0f km" % spread)
    if not both:
        note.append("single-script match only (%s)" % ",".join(sorted(ev)))
    return g, best, "; ".join(note)


def main():
    places = load_places()
    existing = load_existing()
    th = load_thurayya()
    th_lat, th_ar = {}, {}
    for t in th:
        for k in t["lat_keys"]:
            th_lat.setdefault(k, []).append(t)
        for k in t["ar_keys"]:
            th_ar.setdefault(k, []).append(t)
    wd = load_wikidata(places)
    out = []
    summary = {}
    for pl in places:
        expect, cands = candidates(pl, th_lat, th_ar, wd, existing)
        g, best, note = grade_place(pl, expect, cands)
        summary[g] = summary.get(g, 0) + 1
        best_ids = {id(c) for c in best} if best else set()
        cands.sort(key=lambda c: (id(c) not in best_ids, {"exact": 0, "probable": 1, "possible": 2}.get(c.get("grade"), 3)))
        base = {"canonical_id": pl["id"], "label": pl["label"], "label_ar": ";".join(pl["ar"]),
                "place_type": pl["type"], "expected_region": expect, "place_grade": g,
                "homonym_flag": "yes" if "HOMONYM" in note else "", "place_note": note}
        if not cands:
            out.append(dict(base, rank="", candidate_system="", candidate_id="", candidate_label="",
                            candidate_label_ar="", latitude="", longitude="", candidate_region="",
                            candidate_type="", region_fit="", evidence="", candidate_grade="unlocated",
                            candidate_note=""))
        for i, c in enumerate(cands, 1):
            out.append(dict(base, rank=i, candidate_system=c["system"], candidate_id=c["id"],
                            candidate_label=c["label"], candidate_label_ar=c["label_ar"],
                            latitude="%.5f" % c["lat"], longitude="%.5f" % c["lon"],
                            candidate_region=c["region"], candidate_type=c["type"], region_fit=c["fit"] or "no",
                            evidence="+".join(sorted(c["evidence"])), candidate_grade=c.get("grade", "unlocated"),
                            candidate_note=c.get("note", "")))
    cols = ["canonical_id", "label", "label_ar", "place_type", "expected_region", "place_grade", "homonym_flag",
            "place_note", "rank", "candidate_system", "candidate_id", "candidate_label", "candidate_label_ar",
            "latitude", "longitude", "candidate_region", "candidate_type", "region_fit", "evidence",
            "candidate_grade", "candidate_note"]
    with open(HERE / "places-proposed.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    print("places:", len(places), "rows:", len(out), "wikidata items:", len(wd))
    print("place grades:", dict(sorted(summary.items())))


if __name__ == "__main__":
    main()
