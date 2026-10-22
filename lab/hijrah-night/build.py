#!/usr/bin/env python3
"""
Build the Hijrah Night prototype: one self-contained page (lab/hijrah-night/index.html)
that walks the Hijrah over real terrain, using only claims of the full-book Ibn Hishām pass.

    python3 lab/hijrah-night/build.py

Reads (committed files only):
  ingest/claims/ibn-hisham-full.jsonl            the claims (AI-extracted, proposed)
  ingest/claims/ibn-hisham-full-passages.jsonl   the passages they rest on
  ontology/corpus/ibn-hisham-full.ttl            each passage's citation (volume, page, milestone)
  lab/hijrah-night/data/places.csv               reviewed or name-matched gazetteer points
  lab/hijrah-night/data/hijaz-dem.json           terrain, from the AWS Terrain Tiles (Mapzen) at zoom 9

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
TTL = ROOT / "ontology" / "corpus" / "ibn-hisham-full.ttl"
PLACES = HERE / "data" / "places.csv"
DEM = HERE / "data" / "hijaz-dem.json"
TEMPLATE = HERE / "template.html"
OUT = HERE / "index.html"

PROPHET = "The Prophet Muḥammad (peace and blessings be upon him)"

STORY = {"rel_resided_in", "rel_sheltered_at", "rel_present_at", "rel_participated_in", "rel_migrated_to",
         "rel_migrated_from", "rel_travelled_via", "rel_visited", "rel_led", "rel_sheltered",
         "rel_corresponded_with", "rel_dated", "rel_occurred_at", "rel_mawla_of", "rel_died_at"}
CHAIN = {"rel_narrated_from"}
FAMILY = {"rel_father_of", "rel_mother_of", "rel_sibling_of", "rel_paternal_uncle_of"}
PRESENT = {"rel_resided_in", "rel_sheltered_at", "rel_participated_in", "rel_present_at", "rel_visited",
           "rel_migrated_to", "rel_led"}
PRED_LABEL = {
    "rel_resided_in": "stayed in", "rel_sheltered_at": "sheltered at", "rel_present_at": "present at",
    "rel_participated_in": "took part in", "rel_migrated_to": "emigrated to", "rel_migrated_from": "emigrated from",
    "rel_travelled_via": "travelled via", "rel_visited": "came to", "rel_led": "guided",
    "rel_sheltered": "gave lodging to", "rel_corresponded_with": "wrote for", "rel_dated": "is dated",
    "rel_occurred_at": "took place at", "rel_mawla_of": "client (mawlā) of", "rel_died_at": "died at",
    "rel_narrated_from": "narrated from", "rel_father_of": "father of", "rel_mother_of": "mother of",
    "rel_sibling_of": "sibling of", "rel_paternal_uncle_of": "paternal uncle of",
}

# Curation. Sections are keys of the edition's sections (S0678 = section 678).
# light: where the Prophet's light rests in this chapter (a name_in_claims from places.csv),
# None when the text does not place the moment, or "route" for the stop-by-stop walk.
CHAPTERS = [
    {"id": "ahead", "title": "The ones who went ahead",
     "sections": ["S0659", "S0660", "S0661", "S0665", "S0669", "S0670", "S0672"],
     "pose": ["Quba'", 9, 52, 200], "light": "Makkah", "hosts": True,
     "ask": "The emigrants left Makkah before the Prophet ﷺ. Where did they stay when they reached Madinah?"},
    {"id": "remain", "title": "Three remain in Makkah", "sections": ["S0678"],
     "pose": ["Makkah", 14, 38, 20], "light": "Makkah",
     "predict": {"q": "Before you read on: who does the text say stayed behind in Makkah with the Prophet ﷺ?",
                 "pred": "rel_resided_in", "object": "Makkah", "exclude_prophet": True,
                 "distract": [["S0665", "rel_migrated_to", "ʿUmar b. al-Khaṭṭāb"],
                              ["S0661", "rel_migrated_to", "ʿĀmir b. Rabīʿa"]]}},
    {"id": "council", "title": "The council at Dār al-Nadwa", "sections": ["S0679"],
     "pose": ["Makkah", 7, 48, 120], "light": "Makkah",
     "ask": "What does it tell us that the text names each person at the council, one by one?"},
    {"id": "night", "title": "The night of leaving", "sections": ["S0680", "S0681", "S0683"],
     "pose": ["Makkah", 5, 26, 300], "light": "Makkah",
     "ask": "This section reaches Ibn Isḥāq through named narrators. Why would a historian want to know who told whom?"},
    {"id": "cave", "title": "Three days in the cave", "sections": ["S0685", "S0686", "S0688"],
     "pose": ["Ghār Thawr", 6, 30, 330], "light": "Ghār Thawr",
     "check": {"q": "Who does the text say sheltered in the cave at Thawr?", "pred": "rel_sheltered_at",
               "object": "Ghār Thawr",
               "distract": [["S0700", "rel_resided_in", "ʿAlī b. Abī Ṭālib"],
                            ["S0665", "rel_migrated_to", "ʿUmar b. al-Khaṭṭāb"]]}},
    {"id": "four", "title": "Four set out", "sections": ["S0691", "S0692"],
     "pose": ["Ghār Thawr", 26, 40, 300], "light": "Ghār Thawr",
     "check": {"q": "Ibn Hishām names four who travelled. Choose them.", "pred": "rel_participated_in",
               "object": "The Hijra of the Prophet ﷺ to Madinah", "sections": ["S0691"],
               "distract": [["S0700", "rel_resided_in", "ʿAlī b. Abī Ṭālib"],
                            ["S0665", "rel_migrated_to", "ʿUmar b. al-Khaṭṭāb"]]}},
    {"id": "suraqa", "title": "Surāqa's pursuit", "sections": ["S0693", "S0694", "S0695"],
     "pose": [39.2, 22.75, 210, 58, 0], "light": None,
     "where": "The text does not place this moment on the map, so the light is not drawn.",
     "ask": "Surāqa later met the Prophet ﷺ at al-Jiʿrāna. What changes when you know how a pursuer's story ends?"},
    {"id": "road", "title": "The road north", "sections": ["S0696"], "only": ["rel_travelled_via", "rel_led"],
     "pose": [39.45, 22.9, 330, 62, 0], "light": "route",
     "order": {"q": "Put the places in the order Ibn Hishām gives them.", "section": "S0696"}},
    {"id": "quba", "title": "Arrival at Qubāʾ",
     "sections": ["S0696", "S0697", "S0698", "S0699", "S0700", "S0701"],
     "skip": ["rel_travelled_via", "rel_led"],
     "pose": ["Quba'", 6, 34, 160], "light": "Quba'", "hosts": True,
     "dispute": {"q": "With whom did the Prophet ﷺ lodge at Qubāʾ?", "section": "S0698",
                 "pred": "rel_sheltered", "object": PROPHET,
                 "distract": [["S0699", "rel_sheltered", "Khubayb b. Isāf"]]}},
    {"id": "friday", "title": "The first Friday", "sections": ["S0702", "S0703"],
     "pose": ["al-Madīna", 9, 40, 200], "light": "al-Madīna",
     "where": "Wādī Rānūnāʾ has no reviewed location yet, so the light rests on al-Madīna.",
     "ask": "Of everything in this journey, which moment would you explain first to someone who has never heard of it, and which claim would you show them?"},
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
        # who is drawn: people the story claims put somewhere in this chapter
        people, council, hosts = {}, [], {}
        for c in raw:
            pr, sn = c["predicate"], c["subject"]["name"]
            on = c["object"].get("name") if isinstance(c["object"], dict) else None
            if pr == "rel_present_at" and on and ("council" in on or "watch" in on):
                council.append(show(sn))
            elif pr in PRESENT and c["subject"].get("kind", "person") == "person":
                if not (ch.get("hosts") and pr == "rel_migrated_to"):
                    people.setdefault(show(sn), "prophet" if sn == PROPHET else "person")
            elif pr == "rel_sheltered" and on:
                if ch.get("hosts"):
                    hosts.setdefault(show(sn), []).append(show(on))
                else:
                    people.setdefault(show(on), "prophet" if on == PROPHET else "person")
                    people.setdefault(show(sn), "person")
        if ch.get("hosts"):
            for c in raw:
                if c["predicate"] == "rel_migrated_to":
                    nm = show(c["subject"]["name"])
                    if not any(nm in g for g in hosts.values()):
                        hosts.setdefault("", []).append(nm)
        item = {"id": ch["id"], "title": ch["title"], "pose": ch["pose"], "light": ch["light"],
                "where": ch.get("where"), "ask": ch.get("ask"),
                "sections": [{"key": s, "label": by_key[s]["label"].rsplit(" (Ibn Hisham", 1)[0],
                              "cite": cites.get(by_key[s]["id"], "")} for s in ch["sections"] if s in by_key],
                "story": story, "chains": chains,
                "family": [c for c in claims if c["p"] in FAMILY],
                "chainClaims": [c for c in claims if c["p"] in CHAIN],
                "people": [{"name": n, "role": r} for n, r in people.items()],
                "council": list(dict.fromkeys(council)),
                "hosts": [{"host": h, "guests": list(dict.fromkeys(g))} for h, g in hosts.items()]}

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

    # the route: Makkah, Thawr, the stops of S0696 in the order given, Qubāʾ, al-Madīna
    via = [c for c in claims_by_sec["S0696"] if c["predicate"] == "rel_travelled_via"]
    route = [{"key": "Makkah"}, {"key": "Ghār Thawr"}] + [{"key": c["object"]["name"], "claim": c["id"]} for c in via] \
        + [{"key": "Quba'"}, {"key": "al-Madīna"}]
    for r in route:
        r["name"] = places[r["key"]]["name"] if r["key"] in places else show(r["key"])
        r["placed"] = r["key"] in places

    dem = json.loads(DEM.read_text(encoding="utf-8"))
    n_claims = sum(len(c["story"]) + len(c["family"]) + len(c["chainClaims"]) for c in out_ch)
    data = {"chapters": out_ch, "places": places, "route": route, "dem": dem,
            "counts": {"chapters": len(out_ch), "claims": n_claims,
                       "sections": len({s["key"] for c in out_ch for s in c["sections"]})}}
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = TEMPLATE.read_text(encoding="utf-8").replace("/*DATA*/null", blob)
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(page.encode()) // 1000} kB): {data['counts']}")


if __name__ == "__main__":
    main()
