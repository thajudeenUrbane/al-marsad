"""Build the whole-graph question bank for the memory engine (roadmap N4).

Every option in every question is a claim: the right answer is right because a
claim says so, and a wrong option is wrong because a *different* claim places
that name somewhere else. The learner is shown that claim after answering.

    python3 lab/memory-engine/build_bank.py      ->  lab/memory-engine/bank.json

Question types
  present   event -> which person does the text record there?
  where     person -> place (resided_in / migrated_to / sheltered_at)
  order     the travelled_via stops of one traveller in one section, in text order
  dispute   same slot, two different fillers in one section: "the text gives two reports"
  event     person -> which event?
  family    a small, capped lineage set (father_of / mother_of) for well-attested people
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CLAIMS = ROOT / "ingest" / "claims" / "ibn-hisham-full.jsonl"
PASSAGES = ROOT / "ingest" / "claims" / "ibn-hisham-full-passages.jsonl"
TTL = ROOT / "ontology" / "corpus" / "ibn-hisham-full.ttl"
OUT = HERE / "bank.json"

PROPHET = "The Prophet Muḥammad (peace and blessings be upon him)"
MAX_DISTRACTORS = 3
PER_EVENT_CAP = 8          # present-questions per event, so Badr does not swamp the bank
FAMILY_CAP = 150
FAMILY_MIN_MENTIONS = 6    # a person must appear in this many non-lineage claims to get a family card

PRESENT = {"rel_participated_in", "rel_present_at", "rel_witnessed"}
WHERE = {"rel_resided_in": "stayed", "rel_migrated_to": "emigrated to", "rel_sheltered_at": "sheltered"}
LINEAGE = {"rel_father_of", "rel_mother_of", "rel_sibling_of", "rel_ancestor_of",
           "rel_paternal_uncle_of", "rel_maternal_uncle_of", "rel_cousin_of"}
# Slots that should hold one filler; two fillers in one section = two reports.
# (predicate, fixed side, wording)
DISPUTE_SLOTS = {
    "rel_sheltered": ("object", "Who gave lodging to {x}?"),
    "rel_killed": ("object", "Who killed {x}?"),
    "rel_died_at": ("subject", "Where did {x} die?"),
    "rel_born_at": ("subject", "Where was {x} born?"),
    "rel_buried_at": ("subject", "Where was {x} buried?"),
    "rel_sheltered_at": ("subject", "Where did {x} shelter?"),
    "rel_occurred_at": ("subject", "Where did {x} take place?"),
}


def read_jsonl(p: Path) -> list[dict]:
    with p.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def citations() -> dict:
    """Passage id -> canonical citation, as lab/hijrah-night/build.py reads them."""
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


def mid(name: str) -> str:
    """Display form for use mid-sentence: a leading article is lower-cased."""
    return re.sub(r"^The ", "the ", show(name))


def norm(name: str) -> str:
    """Grouping key: display form, no leading article, case-folded."""
    return re.sub(r"^the\s+", "", show(name).casefold())


def seeded(*parts: str) -> random.Random:
    return random.Random(int(hashlib.sha256("|".join(parts).encode()).hexdigest()[:16], 16))


def secno(key: str) -> int:
    return int(key[1:]) if key[1:].isdigit() else 0


def main() -> None:
    cites = citations()
    passages = {p["id"]: p for p in read_jsonl(PASSAGES)}
    claims = [c for c in read_jsonl(CLAIMS) if isinstance(c.get("object"), dict) and "name" in c["object"]]
    sec = {c["id"]: passages[c["passage"]]["key"] for c in claims}

    mentions = Counter()            # non-lineage salience of each entity
    for c in claims:
        if c["predicate"] not in LINEAGE and c["predicate"] != "rel_narrated_from":
            mentions[norm(c["subject"]["name"])] += 1
            mentions[norm(c["object"]["name"])] += 1

    def opt(text: str, c: dict, correct: bool) -> dict:
        p = passages[c["passage"]]
        return {"text": text, "correct": correct, "claim": c["id"], "gloss": c["gloss"],
                "cite": cites.get(p["id"], p["label"]), "section": p["key"]}

    bank: list[dict] = []
    seen: set[str] = set()

    def emit(qtype: str, stem: str, options: list[dict], concepts: list[str], signals: dict, **extra) -> None:
        texts = [o["text"] for o in options]
        if len(set(map(str.casefold, texts))) != len(texts) or not any(o["correct"] for o in options):
            return
        key = qtype + "|" + stem + "|" + "|".join(sorted(o["text"] for o in options if o["correct"]))
        if key in seen:
            return
        seen.add(key)
        seeded(key).shuffle(options) if qtype != "order" else None
        # Difficulty heuristic in [0,1]: near distractors, rare answers, more options = harder.
        d = 0.25
        d += 0.25 * signals.get("near_distractors", 0) / max(1, MAX_DISTRACTORS)
        d += 0.25 * (1 if signals.get("answer_mentions", 99) <= 2 else 0.5 if signals.get("answer_mentions", 99) <= 6 else 0)
        d += 0.25 * min(1, (len(options) - 2) / 4)
        bank.append({"id": "q:" + hashlib.sha256(key.encode()).hexdigest()[:12], "type": qtype, "stem": stem,
                     "options": options, "concepts": sorted(set(concepts)),
                     "difficulty": round(min(1.0, d), 2), "signals": signals, **extra})

    def pick(rng: random.Random, pool: list[tuple[str, dict]], anchor_sec: str, n: int = MAX_DISTRACTORS):
        """Choose distractors, preferring ones from nearby sections (harder, more instructive)."""
        by_text = {}
        for t, c in pool:
            by_text.setdefault(t, c)
        items = list(by_text.items())
        rng.shuffle(items)
        items.sort(key=lambda tc: abs(secno(sec[tc[1]["id"]]) - secno(anchor_sec)) > 40)
        chosen = items[:n]
        near = sum(1 for _, c in chosen if abs(secno(sec[c["id"]]) - secno(anchor_sec)) <= 40)
        return chosen, near

    # ---------- present: event -> person ----------
    at_event = defaultdict(list)       # norm(event) -> claims
    person_events = defaultdict(set)   # norm(person) -> {norm(event)}
    for c in claims:
        if c["predicate"] in PRESENT and c["object"]["kind"] == "event" and c["subject"]["kind"] == "person":
            at_event[norm(c["object"]["name"])].append(c)
            person_events[norm(c["subject"]["name"])].add(norm(c["object"]["name"]))
    for ev, cs in at_event.items():
        rng = seeded("present", ev)
        firsts = {}
        for c in cs:
            firsts.setdefault(norm(c["subject"]["name"]), c)
        picks = sorted(firsts.values(), key=lambda c: -mentions[norm(c["subject"]["name"])])[:PER_EVENT_CAP]
        evname = show(cs[0]["object"]["name"])
        for c in picks:
            pool = [(show(o["subject"]["name"]), o) for e2, cs2 in at_event.items() if e2 != ev for o in cs2
                    if ev not in person_events[norm(o["subject"]["name"])]]
            ds, near = pick(rng, pool, sec[c["id"]])
            if len(ds) < 2:
                continue
            emit("present", f"Which of these does the text record at {mid(cs[0]['object']['name'])}?",
                 [opt(show(c["subject"]["name"]), c, True)] + [opt(t, o, False) for t, o in ds],
                 [f"event:{evname}", f"person:{show(c['subject']['name'])}"],
                 {"near_distractors": near, "answer_mentions": mentions[norm(c["subject"]["name"])]})

    # ---------- where: person -> place ----------
    places_of = defaultdict(set)
    by_pred = defaultdict(list)
    for c in claims:
        if c["predicate"] in WHERE and c["object"]["kind"] == "place":
            places_of[norm(c["subject"]["name"])].add(norm(c["object"]["name"]))
            by_pred[c["predicate"]].append(c)
    for pred, cs in by_pred.items():
        for c in cs:
            who = norm(c["subject"]["name"])
            rng = seeded("where", c["id"])
            pool = [(show(o["object"]["name"]), o) for p2 in WHERE for o in by_pred[p2]
                    if norm(o["object"]["name"]) not in places_of[who] and norm(o["subject"]["name"]) != who]
            ds, near = pick(rng, pool, sec[c["id"]])
            if len(ds) < 2:
                continue
            emit("where", f"Where does the text say {show(c['subject']['name'])} {WHERE[pred]}?",
                 [opt(show(c["object"]["name"]), c, True)] + [opt(t, o, False) for t, o in ds],
                 [f"person:{show(c['subject']['name'])}", f"place:{show(c['object']['name'])}"],
                 {"near_distractors": near, "answer_mentions": mentions[norm(c["object"]["name"])]})

    # ---------- order: travelled_via stops in one section ----------
    trips = defaultdict(list)
    for c in claims:
        if c["predicate"] == "rel_travelled_via":
            trips[(sec[c["id"]], norm(c["subject"]["name"]))].append(c)
    for (s, _), cs in trips.items():
        stops, names = [], set()
        for c in sorted(cs, key=lambda c: c["span"][0]):
            n = norm(c["object"]["name"])
            if n not in names:
                names.add(n)
                stops.append(c)
        if len(stops) < 3:
            continue
        stops = stops[:7]
        emit("order", f"Put {mid(stops[0]['subject']['name'])}'s stops in the order the text gives them ({s}).",
             [dict(opt(show(c["object"]["name"]), c, True), rank=i) for i, c in enumerate(stops)],
             [f"person:{show(stops[0]['subject']['name'])}"] + [f"place:{show(c['object']['name'])}" for c in stops],
             {"near_distractors": MAX_DISTRACTORS, "answer_mentions": 99, "stops": len(stops)})

    # ---------- dispute: two reports in one section ----------
    slots = defaultdict(list)
    for c in claims:
        if c["predicate"] in DISPUTE_SLOTS:
            fixed, _ = DISPUTE_SLOTS[c["predicate"]]
            slots[(sec[c["id"]], c["predicate"], norm(c[fixed]["name"]))].append(c)
    for (s, pred, _), cs in slots.items():
        fixed, wording = DISPUTE_SLOTS[pred]
        free = "subject" if fixed == "object" else "object"
        fillers = {}
        for c in cs:
            fillers.setdefault(norm(c[free]["name"]), c)
        if len(fillers) < 2:
            continue
        reports = list(fillers.values())[:3]
        rng = seeded("dispute", s, pred, cs[0][fixed]["name"])
        taken = set(fillers)
        pool = [(show(o[free]["name"]), o) for o in claims if o["predicate"] == pred and norm(o[free]["name"]) not in taken
                and sec[o["id"]] != s]
        ds, near = pick(rng, pool, s, n=max(1, MAX_DISTRACTORS - len(reports) + 1))
        x = show(cs[0][fixed]["name"])
        emit("dispute", wording.format(x=mid(cs[0][fixed]["name"])) + " Choose every answer the text gives.",
             [opt(show(c[free]["name"]), c, True) for c in reports] + [opt(t, o, False) for t, o in ds],
             [f"{cs[0][fixed]['kind']}:{x}"] + [f"{c[free]['kind']}:{show(c[free]['name'])}" for c in reports],
             {"near_distractors": near, "answer_mentions": 99, "reports": len(reports)},
             note="The text gives more than one report here; both are recorded, neither is erased.")

    # ---------- event: person -> which event ----------
    for who, evs in person_events.items():
        mine = [c for ev in evs for c in at_event[ev] if norm(c["subject"]["name"]) == who]
        if not mine or mentions[who] < 3:
            continue
        c = max(mine, key=lambda c: len(at_event[norm(c["object"]["name"])]) * -1)  # rarest event = most telling
        rng = seeded("event", who)
        pool = [(show(cs2[0]["object"]["name"]), cs2[0]) for ev, cs2 in at_event.items() if ev not in evs]
        ds, near = pick(rng, pool, sec[c["id"]])
        if len(ds) < 2:
            continue
        emit("event", f"Which event does the text record {mid(c['subject']['name'])} at?",
             [opt(show(c["object"]["name"]), c, True)] + [opt(t, o, False) for t, o in ds],
             [f"person:{show(c['subject']['name'])}", f"event:{show(c['object']['name'])}"],
             {"near_distractors": near, "answer_mentions": len(at_event[norm(c["object"]["name"])])})

    # ---------- family: small capped lineage set ----------
    parent_of = defaultdict(list)   # (pred, norm(child)) -> claims
    for c in claims:
        if c["predicate"] in ("rel_father_of", "rel_mother_of"):
            parent_of[(c["predicate"], norm(c["object"]["name"]))].append(c)
    fam = sorted(((k, v) for k, v in parent_of.items() if mentions[k[1]] >= FAMILY_MIN_MENTIONS),
                 key=lambda kv: -mentions[kv[0][1]])
    nfam = 0
    for (pred, child), cs in fam:
        if nfam >= FAMILY_CAP:
            break
        c = cs[0]
        parents = {norm(o["subject"]["name"]) for o in cs}
        rng = seeded("family", pred, child)
        pool = [(show(o["subject"]["name"]), o) for (p2, ch2), cs2 in parent_of.items() if p2 == pred and ch2 != child
                for o in cs2[:1] if norm(o["subject"]["name"]) not in parents]
        ds, near = pick(rng, pool, sec[c["id"]])
        if len(ds) < 2:
            continue
        rel = "father" if pred == "rel_father_of" else "mother"
        before = len(bank)
        emit("family", f"Whom does the text name as the {rel} of {mid(c['object']['name'])}?",
             [opt(show(c["subject"]["name"]), c, True)] + [opt(t, o, False) for t, o in ds],
             [f"person:{show(c['object']['name'])}", f"person:{show(c['subject']['name'])}"],
             {"near_distractors": near, "answer_mentions": max(mentions[child], mentions[norm(c["subject"]["name"])])})
        nfam += len(bank) - before

    counts = dict(Counter(q["type"] for q in bank))
    bands = Counter("easy" if q["difficulty"] < 0.45 else "medium" if q["difficulty"] < 0.7 else "hard" for q in bank)
    out = {"source": "Ibn Hishām, al-Sīra al-Nabawiyya (full-book claims)", "rule": "recall before reveal",
           "counts": counts, "difficulty_bands": dict(bands), "total": len(bank),
           "concepts": len({k for q in bank for k in q["concepts"]}), "questions": bank}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1000} kB)  total={len(bank)}  {counts}  {dict(bands)}")


if __name__ == "__main__":
    main()
