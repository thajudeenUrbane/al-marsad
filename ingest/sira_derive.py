#!/usr/bin/env python3
"""
Slice 11a: what the full-book pass did not record, read again from the same text.

    .venv/bin/python ingest/sira_derive.py build    # write ingest/claims/ibn-hisham-full-derived.jsonl
    .venv/bin/python ingest/sira_derive.py check    # exit 1 if the committed file is not what build writes

It needs the cached text (ingest/ibn_hisham.py fetch) and the committed full-pass files
(ingest/claims/ibn-hisham-full*.jsonl); the chunk-by-chunk extraction output is not
needed. Nothing here is a new reading of the history: every addition rests on words
the text already gives, at offsets the full pass committed.

1. Voice (maintainer F7). Who is speaking where a claim's words stand: Ibn Isḥāq, or
   Ibn Hishām adding a note. The book marks a change of speaker with "qāla Ibn Hishām"
   and "qāla Ibn Isḥāq". After a "qāla Ibn Isḥāq" the voice is his until the next marker
   (Ibn Hishām marks his own additions), in the same section or carried from earlier
   ones. A "qāla Ibn Hishām" covers only the paragraph it opens: his notes are mostly
   short ("wa-yuqāl ..."), and Ibn Isḥāq's text resumes without a new marker; beyond
   that paragraph, with no new marker, no voice is recorded rather than guessed.
2. Formula (F5). On every rel_narrated_from claim, the transmission formula as written
   (ḥaddathanī, ʿan, balaghanī ...) that introduces the person narrated from: the one
   followed by that person's name as the text writes it; with no name to go by, only a
   lone formula is taken, and otherwise none is recorded rather than guessed; with its mode where the formula fixes it: ḥaddatha, samiʿa
   and anshada = heard (tm_sama), ʿan = ʿanʿana (tm_anana); every other formula is
   left unspecified rather than guessed (akhbaranī included).
3. Poems doubted (F7). Ibn Hishām often says that most authorities on poetry deny a
   poem's attribution. Claims in a section where he says so get the qualifier
   poem_doubted_in_passage: check whether the claim rests on that poem.
4. Sides at battles (F1). Ibn Isḥāq opens his lists with their side: "the names of
   those of the Muslims who were present at Badr", "of the idolaters killed at Badr",
   "of the idolaters captured" ... (LISTS below). A person whose claim on the battle
   stands in such a list gets one claim: fought alongside, or fought against, the
   Prophet (peace and blessings be upon him), at that battle (mrs:atEvent), resting on
   the person's own listing and the list's opening words. Not for the Prophet himself,
   and not for anyone the text counts at Badr without his being there
   (share_not_present). Side claim IDs are kept from the committed file on a rebuild.
"""

import argparse
import bisect
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ibn_hisham as ih  # noqa: E402
import sira_full as sf  # noqa: E402

OUT = ih.CLAIMS_DIR / "ibn-hisham-full-derived.jsonl"
PROPHET = "The Prophet Muḥammad (peace and blessings be upon him)"

# Ibn Isḥāq's own opening words for each list, the battle (as the full pass names it),
# the side, and the opening of the NEXT list (or heading) that ends it.
LISTS = [
    {"key": "badr_muslims", "event": "Battle of Badr", "side": "with",
     "opens": "وهذه تسمية من شهد بدرا من المسلمين", "until": "واستشهد من المسلمين يوم بدر",
     "en": "Ibn Isḥāq's list of the Muslims present at Badr"},
    {"key": "badr_martyrs", "event": "Battle of Badr", "side": "with",
     "opens": "واستشهد من المسلمين يوم بدر", "until": "وقتل من المشركين يوم بدر",
     "en": "Ibn Isḥāq's list of the Muslims martyred at Badr"},
    {"key": "badr_slain", "event": "Battle of Badr", "side": "against",
     "opens": "وقتل من المشركين يوم بدر", "until": "وأسر من المشركين من قريش",
     "en": "Ibn Isḥāq's list of the idolaters killed at Badr"},
    {"key": "badr_captives", "event": "Battle of Badr", "side": "against",
     "opens": "وأسر من المشركين من قريش", "until": "### | ما قيل من الشعر في يوم بدر",
     "en": "Ibn Isḥāq's list of the idolaters captured at Badr"},
    {"key": "uhud_martyrs", "event": "Battle of Uḥud", "side": "with",
     "opens": "واستشهد من المسلمين يوم أحد", "until": "وقتل من المشركين يوم أحد",
     "en": "Ibn Isḥāq's list of the Muslims martyred at Uḥud"},
    {"key": "uhud_slain", "event": "Battle of Uḥud", "side": "against",
     "opens": "وقتل من المشركين يوم أحد", "until": "### | ذكر ما قيل من الشعر يوم أحد",
     "en": "Ibn Isḥāq's list of the idolaters killed at Uḥud"},
]
ON_EVENT = {"rel_participated_in", "rel_died_during", "rel_present_at", "rel_witnessed"}

FORMULAS = [  # (key, pattern on a whole word, mode)
    ("haddatha", r"[وف]?حدث(?:ني|نا|ه|هم|ت)", "sama"),
    ("akhbara", r"[وف]?أخبر(?:ني|نا|ه|هم)", "unspecified"),
    ("samia", r"[وف]?سمع(?:ت|نا)?", "sama"),
    ("anshada", r"[وف]?أنشد(?:ني|نا)", "sama"),
    ("an", r"[وف]?عن", "anana"),
    ("balagha", r"[وف]?بلغ(?:ني|نا|ه)", "unspecified"),
    ("zaama", r"[وف]?زعم(?:وا|ت)?", "unspecified"),
    ("dhakara", r"[وف]?ذكر", "unspecified"),
    ("qala", r"[وف]?قال", "unspecified"),
]
WORD = r"(?<![ء-ي])(?:%s)(?![ء-ي])"
FORMULA_RE = [(k, re.compile(WORD % p), m) for k, p, m in FORMULAS]
VOICE_RE = [("ibn_hisham", re.compile(r"قال\s+ابن\s+هشام")), ("ibn_ishaq", re.compile(r"قال\s+ابن\s+إسحاق"))]
DOUBT_RE = re.compile(r"أهل\s+العلم\s+بالشعر\s+ينكر")
LOOKBACK = 40  # characters before a claim's words searched for its formula


def para_end(raw, pos):
    """End of the paragraph a marker opens: the next OpenITI paragraph ("# ") or heading."""
    ends = [x for x in (raw.find("\n#", pos + 1),) if x >= 0]
    return min(ends) if ends else len(raw)


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


MARKUP = re.compile(r"PageV\d+P\d+|\bms\d+|\[\d+\]|~~|#|[\u064b-\u065f\u0670]")
KIN = {"ابيه", "امه", "جده", "عمه", "اخيه", "امراته", "ابيها", "امها"}  # "from his father" etc.
KIN_ANY = {"ابيه", "امه", "جده", "عمه", "اخيه", "امراته", "ابيها", "امها", "عمي", "ابي", "امي", "جدي"}
SHORT_HEADS = {"بن", "ابي", "ابو", "ام", "عبد", "بنت"}


def norm(x):
    x = MARKUP.sub(" ", x)
    x = re.sub("[أإآٱ]", "ا", x).replace("ة", "ه").replace("ى", "ي")
    return ["بن" if w == "ابن" else w for w in re.sub(r"[^\u0621-\u064a ]", " ", x).split()]  # ibn = b.


def name_keys(forms):
    """The opening words a mention of the person would start with: the name with the father's
    ("Muḥammad b. Jaʿfar") when the form gives one, else the first two words when the first is
    ibn, abū, umm, ʿabd ... (which alone would match many people), else the first word."""
    keys = set()
    for f in forms:
        w = norm(f)
        if not w:
            continue
        if len(w) >= 3 and w[1] in {"بن", "بنت"}:
            keys.add(tuple(w[:3]))
        elif w[0] in SHORT_HEADS and len(w) > 1:
            keys.add(tuple(w[:2]))
        else:
            keys.add((w[0],))
    return keys


def introduces(tokens, keys):
    """Do these words (what follows a formula, up to the next formula) name one of these people,
    either first or in a list joined by "wa" ("al-Zuhrī wa-Yazīd wa-ʿĀṣim")?"""
    for i, w in enumerate(tokens):
        if i and not w.startswith("و") and tokens[i - 1] not in KIN_ANY:
            continue
        for key in keys:
            first = key[0]
            if w == first or (i and w == "و" + first):
                if tuple(tokens[i + 1:i + len(key)]) == key[1:]:
                    return True
    return False


def find_formula(t, a, b, obj_keys, subj_keys):
    """The formula that introduces the person narrated from: the one whose following words name
    that person as the text writes it (or "his father", "his mother" ...), alone or in a list
    joined by "wa". With no such name, a single formula is taken only when it does not
    introduce the narrator himself; otherwise none is recorded rather than guessed."""
    pre_start = max(0, a - LOOKBACK)
    hits = []
    for k, rx, mode in FORMULA_RE:
        for m in rx.finditer(t, pre_start, b):
            hits.append((m.start(), m.end(), k, mode))
    hits.sort()
    following = []
    for n, (fa, fb, k, mode) in enumerate(hits):
        end = hits[n + 1][0] if n + 1 < len(hits) else fb + 120
        following.append(norm(t[fb:min(end, fb + 160)]))
    for (fa, fb, k, mode), nxt in zip(hits, following):   # the person's own name first
        if nxt and introduces(nxt, obj_keys):
            return k, fa, fb, mode
    for (fa, fb, k, mode), nxt in zip(hits, following):   # then "his father", "his mother" ...
        if nxt and nxt[0] in KIN:
            return k, fa, fb, mode
    specific = [h for h in hits if h[2] != "qala"]
    inside = [h for h in specific if h[0] >= a] or specific
    if len(inside) == 1:
        fa, fb, k, mode = inside[0]
        if not introduces(norm(t[fb:fb + 80])[:4], subj_keys):
            return k, fa, fb, mode
    return None


def load():
    src = json.loads(ih.SOURCE.read_text(encoding="utf-8"))
    raw = ih.load_text(src)
    passages = sorted((json.loads(x) for x in sf.F_PASSAGES.open(encoding="utf-8")), key=lambda p: p["start"])
    claims = [json.loads(x) for x in sf.F_CLAIMS.open(encoding="utf-8")]
    return raw, passages, claims


def arabic_forms(raw, passages):
    """English name -> the Arabic forms the text gives for that entity (new entities' attested
    names; identity.csv's Arabic name for people already in the graph)."""
    by_id = {p["id"]: p for p in passages}
    by_id.update({p["id"]: p for p in ih.read_jsonl(ih.PASSAGES)})  # slice 4's passages too
    forms = {PROPHET: ["رسول الله", "النبي"]}  # how the text names him in a chain
    for f in (sf.F_ENTITIES, ih.ENTITIES):
        for e in ih.read_jsonl(f):
            at = e.get("attested")
            if at and at["passage"] in by_id:
                p = by_id[at["passage"]]
                forms.setdefault(e["name"], []).append(raw[p["start"]:p["end"]][at["span"][0]:at["span"][1]])
    import csv
    with ih.IDENTITY.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            for f in (r.get("name_ar") or "").split(";"):
                if f.strip():
                    forms.setdefault(r["preferred_name_en"], []).append(f.strip())
    return forms


def name(x):
    return x.get("name") if isinstance(x, dict) else None


def build():
    raw, passages, claims = load()
    by_id = {p["id"]: p for p in passages}
    forms = arabic_forms(raw, passages)
    starts = [p["start"] for p in passages]

    # voice markers across the whole text, in order
    markers = sorted((m.start(), v) for v, rx in VOICE_RE for m in rx.finditer(raw))
    mpos = [m[0] for m in markers]
    doubted = {p["id"] for p in passages if DOUBT_RE.search(raw[p["start"]:p["end"]])}

    old_sides = {}
    if OUT.exists():
        for x in OUT.open(encoding="utf-8"):
            r = json.loads(x)
            if r["t"] == "side":
                old_sides[(r["subject"]["name"], r["event"], r["side"])] = r["id"]

    out = []
    for c in claims:
        p = by_id[c["passage"]]
        t = raw[p["start"]:p["end"]]
        a, b = c["span"]
        rec = {"t": "annot", "claim": c["id"]}
        at = p["start"] + a
        i = bisect.bisect_left(mpos, p["start"] + b) - 1
        if i >= 0:
            pos, voice = markers[i]
            if voice == "ibn_ishaq":
                rec["voice"] = voice
                rec["voice_basis"] = "section" if pos >= p["start"] else "carried"
            elif at < para_end(raw, pos):
                rec["voice"] = voice
                rec["voice_basis"] = "section" if pos >= p["start"] else "carried"
        if c["predicate"] == "rel_narrated_from":
            f = find_formula(t, a, b, name_keys(forms.get(name(c["object"]), [])),
                             name_keys(forms.get(name(c["subject"]), [])))
            if f:
                k, fa, fb, mode = f
                rec["formula"] = {"key": k, "mode": mode, "span": [fa, fb], "span_sha256": sha(t[fa:fb])}
        if c["passage"] in doubted:
            rec["qualifiers"] = ["poem_doubted_in_passage"]
        out.append(rec)

    # sides
    minter = None
    report = []
    seen = set()  # one side claim per person, battle and side: the first list that gives it
    for L in LISTS:
        o = raw.find(L["opens"])
        u = raw.find(L["until"], o + 1)
        if o < 0 or u < 0:
            sys.exit(f"list {L['key']}: opening or end words not found in the text")
        j = bisect.bisect_right(starts, o) - 1
        op = passages[j]
        if not (op["start"] <= o < op["end"]):
            sys.exit(f"list {L['key']}: its opening words are in no committed passage")
        # every section from the one holding the opening words up to, not including, the one
        # holding the next list's opening (a section's body can start a few characters before it)
        in_list = {p["id"] for p in passages if op["start"] <= p["start"] < u and not p["start"] <= u < p["end"]}
        n = 0
        for c in claims:
            if c["passage"] not in in_list or c["predicate"] not in ON_EVENT or name(c["object"]) != L["event"]:
                continue
            s = c["subject"]
            if not isinstance(s, dict) or s.get("kind") != "person" or s["name"] == PROPHET:
                continue
            if "share_not_present" in c.get("qualifiers", []):
                report.append(f"{L['key']}: no side claim for {s['name']} (counted at Badr, not present)")
                continue
            k = (s["name"], L["event"], L["side"])
            if k in seen:
                continue
            seen.add(k)
            cid = old_sides.get(k)
            if cid is None:
                minter = minter or sf.Minter()
                cid = minter("ast")
            ot = raw[op["start"]:op["end"]]
            oa = o - op["start"]
            ob = oa + len(L["opens"])
            out.append({
                "t": "side", "id": cid, "list": L["key"], "side": L["side"], "event": L["event"],
                "subject": {"kind": "person", "name": s["name"]},
                "predicate": "rel_fought_alongside" if L["side"] == "with" else "rel_fought_against",
                "object": {"kind": "person", "name": PROPHET},
                "passage": c["passage"], "span": c["span"], "span_sha256": c["span_sha256"],
                "basis_claim": c["id"],
                "list_opening": {"passage": op["id"], "span": [oa, ob], "span_sha256": sha(ot[oa:ob])},
                "gloss": (f"{s['name']} is listed in {L['en']}, so the text places him "
                          f"{'with' if L['side'] == 'with' else 'against'} the Prophet ﷺ at "
                          f"{L['event'].replace('Uhud', 'Uḥud').replace('The ', 'the ', 1)}."),
            })
            n += 1
        report.append(f"{L['key']}: {n} side claims ({L['side']}, {L['event']})")
    return out, report


def dump(rows):
    return "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=["build", "check"])
    a = ap.parse_args()
    rows, report = build()
    text = dump(rows)
    if a.cmd == "check":
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print(f"{OUT.relative_to(ih.ROOT)} is not current: run ingest/sira_derive.py build")
            return 1
        print(f"{OUT.relative_to(ih.ROOT)} is up to date")
        return 0
    OUT.write_text(text, encoding="utf-8")
    annots = [r for r in rows if r["t"] == "annot"]
    print(f"wrote {OUT.relative_to(ih.ROOT)}: {len(annots)} claims annotated, "
          f"{sum(1 for r in annots if 'voice' in r)} with a voice "
          f"({sum(1 for r in annots if r.get('voice') == 'ibn_hisham')} Ibn Hishām), "
          f"{sum(1 for r in annots if 'formula' in r)} formulas, "
          f"{sum(1 for r in annots if r.get('qualifiers'))} in sections with a doubted poem")
    for line in report:
        print("  " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
