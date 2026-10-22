#!/usr/bin/env python3
"""
Build the Badr world: one self-contained page (lab/badr-world/index.html) that walks the
expedition of Badr over real terrain, reusing the Hijrah Night engine and using only claims
of the full-book Ibn Hishām pass, plus the side claims of slice 11a (derived file).

    python3 lab/badr-world/build.py

Reads (committed files only):
  ingest/claims/ibn-hisham-full.jsonl            the claims (AI-extracted, proposed)
  ingest/claims/ibn-hisham-full-passages.jsonl   the passages they rest on
  ontology/corpus/ibn-hisham-full.ttl            each passage's citation (volume, page, milestone)
  ingest/claims/ibn-hisham-full-derived.jsonl    side claims at Badr (t == "side")
  lab/badr-world/data/places.csv                 name-matched al-Thurayya gazetteer points
  lab/badr-world/data/hijaz-dem.json           terrain, from the AWS Terrain Tiles (Mapzen) at zoom 9

What the page may say is decided here, not in the template. Every sentence a learner reads
about the past is a claim's gloss with its citation. The only text written by hand is in
CHAPTERS below: chapter titles, which sections each chapter draws on, where the camera
looks, and the questions (questions assert nothing; their answers come from claims).
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CLAIMS = ROOT / "ingest" / "claims" / "ibn-hisham-full.jsonl"
PASSAGES = ROOT / "ingest" / "claims" / "ibn-hisham-full-passages.jsonl"
DERIVED = ROOT / "ingest" / "claims" / "ibn-hisham-full-derived.jsonl"
EVENT = "Battle of Badr"
TTL = ROOT / "ontology" / "corpus" / "ibn-hisham-full.ttl"
PLACES = HERE / "data" / "places.csv"
DEM = HERE / "data" / "hijaz-dem.json"
TEMPLATE = HERE / "template.html"
OUT = HERE / "index.html"

PROPHET = "The Prophet Muḥammad (peace and blessings be upon him)"

STORY = {"rel_resided_in", "rel_sheltered_at", "rel_present_at", "rel_participated_in", "rel_migrated_to",
         "rel_migrated_from", "rel_travelled_via", "rel_visited", "rel_led", "rel_sheltered",
         "rel_corresponded_with", "rel_dated", "rel_occurred_at", "rel_mawla_of", "rel_died_at",
         "rel_killed", "rel_captured", "rel_fought_against", "rel_fought_alongside", "rel_died_during",
         "rel_appointed", "rel_absent_from", "rel_opposed", "rel_ally_of"}
CHAIN = {"rel_narrated_from"}
FAMILY = {"rel_father_of", "rel_mother_of", "rel_sibling_of", "rel_paternal_uncle_of"}
PRESENT = {"rel_participated_in", "rel_present_at", "rel_visited", "rel_led", "rel_died_during",
           "rel_killed", "rel_captured", "rel_fought_against", "rel_travelled_via", "rel_died_at",
           "rel_appointed", "rel_absent_from"}
# predicates whose object is also a person in the scene
PAIRED = {"rel_killed", "rel_captured", "rel_fought_against", "rel_appointed"}
PRED_LABEL = {
    "rel_resided_in": "stayed in", "rel_sheltered_at": "sheltered at", "rel_present_at": "present at",
    "rel_participated_in": "took part in", "rel_migrated_to": "emigrated to", "rel_migrated_from": "emigrated from",
    "rel_travelled_via": "travelled via", "rel_visited": "came to", "rel_led": "guided",
    "rel_sheltered": "gave lodging to", "rel_corresponded_with": "wrote for", "rel_dated": "is dated",
    "rel_occurred_at": "took place at", "rel_mawla_of": "client (mawlā) of", "rel_died_at": "died at",
    "rel_narrated_from": "narrated from", "rel_father_of": "father of", "rel_mother_of": "mother of",
    "rel_sibling_of": "sibling of", "rel_paternal_uncle_of": "paternal uncle of", "rel_killed": "killed",
    "rel_captured": "captured", "rel_fought_against": "fought against", "rel_fought_alongside": "fought alongside",
    "rel_died_during": "died during", "rel_appointed": "appointed", "rel_absent_from": "stayed away from",
}

# Curation. Sections are keys of the edition's sections (S0919 = section 919).
# light: where the Prophet's light rests (a name_in_claims from places.csv), None when the
# text does not place the moment, or "route" for the stage-by-stage walk.
CHAPTERS = [
    {"id": "caravan", "title": "Abū Sufyān's caravan", "sections": ["S0897", "S0898"],
     "pose": ["Badr", 150, 52, 20], "light": None,
     "where": "The text does not place this moment on the map, so the light is not drawn.",
     "ask": "The caravan, not an army, is what the Muslims first set out for. What changes when the goal of a journey changes on the way?"},
    {"id": "quraysh", "title": "Quraysh go out", "sections": ["S0904", "S0905", "S0906"],
     "pose": ["Makkah", 40, 45, 340], "light": None,
     "where": "The Prophet ﷺ is not in these sections, so the light is not drawn.",
     "ask": "Abū Lahab sent another man in his place. What does the text let us say about him, and what does it not?"},
    {"id": "out", "title": "The march out of Madinah", "sections": ["S0909", "S0910", "S0912"],
     "pose": ["al-Madīna", 14, 40, 200], "light": "al-Madīna",
     "ask": "Before leaving, the Prophet ﷺ named who would lead the prayer and who would govern Madinah. Why name both?"},
    {"id": "road", "title": "The road to Badr", "sections": ["S0913", "S0914", "S0915", "S0918"],
     "only": ["rel_travelled_via"], "pose": [39.2, 24.1, 170, 58, 20], "light": "route",
     "order": {"q": "Put the stages in the order Ibn Hishām gives them.", "section": "S0914"}},
    {"id": "water", "title": "At the water of Badr", "sections": ["S0919", "S0920", "S0924", "S0925"],
     "pose": ["Badr", 7, 38, 160], "light": "Badr",
     "check": {"q": "Whom does the text say the Prophet ﷺ sent to the water of Badr for news?", "pred": "rel_visited",
               "object": "Badr", "sections": ["S0919"],
               "distract": [["S0919", "rel_participated_in", "Abū Jahl b. Hishām"],
                            ["S0898", "rel_visited", "Ḍamḍam b. ʿAmr al-Ghifārī"]]}},
    {"id": "shelter", "title": "The shelter and the ranks",
     "sections": ["S0926", "S0927", "S0929", "S0934", "S0935", "S0936", "S0940"],
     "pose": ["Badr", 5, 30, 40], "light": "Badr",
     "check": {"q": "Who does the text say was with the Prophet ﷺ in the shelter at Badr?", "pred": "rel_present_at",
               "object": "Battle of Badr", "sections": ["S0934", "S0936"],
               "distract": [["S0948", "rel_present_at", "ʿAbd al-Raḥmān b. Abī Bakr"],
                            ["S0933", "rel_participated_in", "ʿUbayda b. al-Ḥārith"]]}},
    {"id": "duels", "title": "The duels", "sections": ["S0932", "S0933"],
     "pose": ["Badr", 4, 26, 250], "light": "Badr",
     "check": {"q": "Who does the text say finished ʿUtba b. Rabīʿa?", "pred": "rel_killed",
               "object": "ʿUtba b. Rabīʿa", "sections": ["S0933"],
               "distract": [["S0946", "rel_killed", "ʿAbd Allāh b. Masʿūd"],
                            ["S0941", "rel_killed", "al-Mujadhdhar b. Ziyād al-Balawī"]]}},
    {"id": "fighting", "title": "The fighting",
     "sections": ["S0937", "S0938", "S0941", "S0942", "S0943", "S0946", "S0947", "S0948"],
     "pose": ["Badr", 6, 34, 120], "light": "Badr",
     "check": {"q": "Who does the text say struck Abū Jahl down?", "pred": "rel_fought_against",
               "object": "Abū Jahl b. Hishām", "sections": ["S0946"],
               "distract": [["S0942", "rel_captured", "ʿAbd al-Raḥmān b. ʿAwf"],
                            ["S0933", "rel_killed", "ʿAlī b. Abī Ṭālib"]]}},
    {"id": "slain", "title": "The slain and the well", "sections": ["S0949", "S0950", "S0951", "S0952", "S0953"],
     "pose": ["Badr", 5, 44, 300], "light": "Badr",
     "predict": {"q": "Before you read on: whom does Zayd's announcement name among the slain of Quraysh?",
                 "pred": "rel_died_during", "object": "Battle of Badr", "sections": ["S0953"],
                 "distract": [["S0904", "rel_absent_from", "Abū Lahab b. ʿAbd al-Muṭṭalib"],
                              ["S0929", "rel_present_at", "Ḥakīm b. Ḥizām b. Khuwaylid b. Asad"]]}},
    {"id": "return", "title": "The captives and the return", "sections": ["S0954", "S0955", "S0958", "S0959", "S0960"],
     "pose": ["al-Ṣafrāʾ", 30, 46, 330], "light": "al-Ṣafrāʾ",
     "where": "The light rests at al-Ṣafrāʾ, the defile the text names on the way back.",
     "check": {"q": "Who does the text say captured Suhayl b. ʿAmr?", "pred": "rel_captured",
               "object": "Suhayl ibn Amr", "sections": ["S0958"],
               "distract": [["S0960", "rel_captured", "Khirāsh b. al-Ṣimma"],
                            ["S0955", "rel_captured", "ʿAbd Allāh b. Salama"]]}},
]


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


def main() -> None:
    cites = citations()
    passages = {p["id"]: p for p in read_jsonl(PASSAGES)}
    by_key = {p["key"]: p for p in passages.values()}
    claims_by_sec: dict[str, list] = {}
    for c in read_jsonl(CLAIMS):
        k = passages[c["passage"]]["key"]
        claims_by_sec.setdefault(k, []).append(c)

    # sides at Badr (slice 11a): name -> (side, claim). Two different sides for one name: neutral.
    sides: dict[str, tuple] = {}
    for c in read_jsonl(DERIVED):
        if c.get("t") == "side" and c["event"] == EVENT:
            nm = c["subject"]["name"]
            if nm in sides and sides[nm][0] != c["side"]:
                sides[nm] = ("conflict", None)
            else:
                sides.setdefault(nm, (c["side"], c))

    def role(nm: str) -> str:
        if nm == PROPHET:
            return "prophet"
        s = sides.get(nm, (None,))[0]
        return {"with": "with", "against": "against"}.get(s, "neutral")

    places = {}
    with PLACES.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            places[r["name_in_claims"]] = {"name": r["display"], "ar": r["arabic"], "lat": float(r["latitude"]),
                                           "lon": float(r["longitude"]), "src": r["source"], "status": r["status"]}

    def cl(c: dict) -> dict:
        p = passages[c["passage"]]
        o = c["object"]
        return {"id": c["id"], "p": c["predicate"], "pl": PRED_LABEL.get(c["predicate"], c["predicate"][4:].replace("_", " ")),
                "s": show(c["subject"]["name"]), "o": show(o["name"]) if isinstance(o, dict) and "name" in o else None,
                "g": c["gloss"], "sec": p["key"], "psg": p["id"], "cite": cites.get(p["id"], ""), "span": c["span"]}

    def find(sec: str, pred: str, name: str) -> dict | None:
        for c in claims_by_sec.get(sec, []):
            if c["predicate"] == pred and (c["subject"]["name"] == name or show(c["subject"]["name"]) == name):
                return cl(c)
        return None

    out_ch = []
    for ch in CHAPTERS:
        raw = [c for s in ch["sections"] for c in claims_by_sec.get(s, [])]
        if "only" in ch:
            raw = [c for c in raw if c["predicate"] in ch["only"]]
        if "skip" in ch:
            raw = [c for c in raw if c["predicate"] not in ch["skip"]]
        claims = [cl(c) for c in raw]
        story, seen = [], set()
        for c in claims:  # one line per sentence: a gloss shared by two claims is shown once
            if c["p"] in STORY and (c["g"], c["sec"]) not in seen:
                seen.add((c["g"], c["sec"]))
                story.append(c)
        chains = []
        for s in ch["sections"]:
            edges = [(show(c["subject"]["name"]), show(c["object"]["name"])) for c in claims_by_sec.get(s, [])
                     if c["predicate"] in CHAIN and isinstance(c["object"], dict)]
            if not edges:
                continue
            nxt = {}
            for a, b in edges:
                nxt.setdefault(a, b)
            tops = [a for a, _ in edges if a not in {b for _, b in edges}]
            for t in dict.fromkeys(tops):
                path, seen = [t], {t}
                while path[-1] in nxt and nxt[path[-1]] not in seen:
                    path.append(nxt[path[-1]])
                    seen.add(path[-1])
                chains.append({"sec": s, "names": path})
        # who is drawn: people these claims put in the scene; their side only from a side claim
        people, side_claims = {}, []
        for c in raw:
            pr, s = c["predicate"], c["subject"]
            if pr not in PRESENT or s.get("kind", "person") != "person":
                continue
            names = [s["name"]]
            if pr in PAIRED and isinstance(c["object"], dict) and c["object"].get("kind", "person") == "person":
                names.append(c["object"]["name"])
            for nm in names:
                if show(nm) not in people:
                    people[show(nm)] = role(nm)
                    if sides.get(nm, (None, None))[1]:
                        side_claims.append(cl(sides[nm][1]))
        item = {"id": ch["id"], "title": ch["title"], "pose": ch["pose"], "light": ch["light"],
                "where": ch.get("where"), "ask": ch.get("ask"),
                "sections": [{"key": s, "label": by_key[s]["label"].rsplit(" (Ibn Hisham", 1)[0],
                              "cite": cites.get(by_key[s]["id"], "")} for s in ch["sections"] if s in by_key],
                "story": story, "chains": chains,
                "family": [c for c in claims if c["p"] in FAMILY],
                "chainClaims": [c for c in claims if c["p"] in CHAIN],
                "people": [{"name": n, "role": r} for n, r in people.items()],
                "council": [], "hosts": [], "sides": side_claims}

        def quiz(spec: dict, kind: str) -> dict:
            secs = spec.get("sections", ch["sections"])
            right = []
            for s in secs:
                for c in claims_by_sec.get(s, []):
                    if c["predicate"] == spec["pred"] and isinstance(c["object"], dict) and \
                            c["object"].get("name") == spec["object"]:
                        if spec.get("exclude_prophet") and c["subject"]["name"] == PROPHET:
                            continue
                        if kind == "dispute" or not any(r["name"] == show(c["subject"]["name"]) for r in right):
                            right.append({"name": show(c["subject"]["name"]), "ok": True, "why": cl(c)})
            wrong = []
            for sec, pred, name in spec.get("distract", []):
                w = find(sec, pred, name)
                if w:
                    wrong.append({"name": w["s"], "ok": False, "why": w})
            opts = right + wrong
            opts.sort(key=lambda o: o["name"].lstrip("ʿʾ").lower())
            return {"q": spec["q"], "options": opts}

        if "predict" in ch:
            item["predict"] = quiz(ch["predict"], "predict")
        if "check" in ch:
            item["check"] = quiz(ch["check"], "check")
        if "dispute" in ch:
            item["dispute"] = quiz(ch["dispute"], "dispute")
        if "order" in ch:
            stops = [cl(c) for c in claims_by_sec[ch["order"]["section"]] if c["predicate"] == "rel_travelled_via"]
            item["order"] = {"q": ch["order"]["q"], "stops": stops}
        out_ch.append(item)

    # the route: al-Madīna, then the stages of S0913-S0918 in the order given (the last is Badr)
    via = [c for s in ("S0913", "S0914", "S0915", "S0918") for c in claims_by_sec[s] if c["predicate"] == "rel_travelled_via"]
    route = [{"key": "al-Madīna"}] + [{"key": c["object"]["name"], "claim": c["id"]} for c in via]
    for r in route:
        r["name"] = places[r["key"]]["name"] if r["key"] in places else show(r["key"])
        r["placed"] = r["key"] in places

    dem = json.loads(DEM.read_text(encoding="utf-8"))
    n_claims = sum(len(c["story"]) + len(c["family"]) + len(c["chainClaims"]) + len(c["sides"]) for c in out_ch)
    data = {"chapters": out_ch, "places": places, "route": route, "dem": dem,
            "counts": {"chapters": len(out_ch), "claims": n_claims,
                       "sections": len({s["key"] for c in out_ch for s in c["sections"]}),
                       "with": sum(p["role"] == "with" for c in out_ch for p in c["people"]),
                       "against": sum(p["role"] == "against" for c in out_ch for p in c["people"]),
                       "neutral": sum(p["role"] == "neutral" for c in out_ch for p in c["people"])}}
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = TEMPLATE.read_text(encoding="utf-8").replace("/*DATA*/null", blob)
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(page.encode()) // 1000} kB): {data['counts']}")


if __name__ == "__main__":
    main()
