#!/usr/bin/env python3
"""
Build the pilot's parallel test forms A and B from the claims the Hijrah Night page shows.

    python3 lab/pilot-1/build_tests.py

Writes lab/pilot-1/tests/form-A.md, tests/form-B.md and tests/answer-key.json.

Each form has the same shape, for each half of the journey (Half 1 = chapters 1-5,
Half 2 = chapters 6-10): five cued-recall items, three multiple-choice items whose wrong
options are other claims of the same half, one ordering item and one "two reports" item.
That is 20 core items per form. Each form also has a free-recall prompt per half, one
"how do we know?" item per half and three honesty-cue items (shared by both forms).

Questions are written by hand and assert nothing. Every answer, every distractor and every
ordering is taken from a claim, and the build stops if a claim is missing from the half the
learner saw. Claims are named here by the last six characters of their id; the key gives the
full id, section and citation.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from world_data import HALVES, half_claims, load

HERE = Path(__file__).resolve().parent
OUT = HERE / "tests"

# kind: cr = cued recall (answer field of the claim: s, o, or a phrase that must occur in the gloss)
#       mc = multiple choice (right claim + distractor claims; option text from field)
#       order = put in the order the text gives (claims listed in the right order)
#       two = two reports (both claims are correct; full credit needs both and the word that they differ)
#       src = how do we know? (the chain of narration shown for that section)
ITEMS = {
    ("A", 1): [
        {"kind": "cr", "q": "Who was the first emigrant to reach Madinah after Abū Salama?", "claims": ["6ch56L"], "field": "s"},
        {"kind": "cr", "q": "Two companions stayed behind in Makkah with the Prophet ﷺ. Name them.", "claims": ["b5bTrI", "jTP8uu"], "field": "s"},
        {"kind": "cr", "q": "In which building did Quraysh gather to talk about the Prophet ﷺ?", "claims": ["6BPfTg"], "field": "o"},
        {"kind": "cr", "q": "How long did the Prophet ﷺ stay in the cave with Abū Bakr?", "claims": ["1EaT3w"], "phrase": "three days"},
        {"kind": "cr", "q": "Where did Umm Salama go every morning to sit and weep?", "claims": ["jXKZiy"], "field": "o"},
        {"kind": "mc", "q": "At Qubāʾ, ʿAbdullāh b. Jaḥsh stayed as a guest with…", "claims": ["sgXtE2"], "field": "s",
         "distract": ["G83FJl", "bbdzhJ", "fLBJvP"]},
        {"kind": "mc", "q": "ʿUmar and ʿAyyāsh met in the morning at an agreed place. Which place?", "claims": ["yBmczi"], "field": "o",
         "distract": ["aqtZ0g", "jXKZiy", "fLBJvP"]},
        {"kind": "mc", "q": "Who is named among the men gathered at the Prophet's door on the night of leaving?", "claims": ["5uFX7p"], "field": "s",
         "distract": ["b5bTrI", "lFFnFY", "TGQWXr"]},
        {"kind": "order", "q": "Put these emigrants in the order the text says they reached Madinah.", "claims": ["XLFXE1", "6ch56L", "mSLw04"], "field": "s"},
        {"kind": "two", "q": "With whom did Ṭalḥa b. ʿUbaydullāh stay when he reached Madinah? Write everything the text records.",
         "claims": ["rNLzNH", "KPYQXI"], "field": "s"},
        {"kind": "src", "q": "How do we know that Umm Salama went out every morning to weep at al-Abṭaḥ? Who first told it?",
         "claims": ["jXKZiy"], "chain": "S0660"},
    ],
    ("B", 1): [
        {"kind": "cr", "q": "Who was the first emigrant of his clan (Makhzūm) to reach Madinah, a year before the pledge of ʿAqaba?", "claims": ["XLFXE1"], "field": "s"},
        {"kind": "cr", "q": "Who escorted Umm Salama until he brought her to Madinah?", "claims": ["mweWlv"], "phrase": "ʿUthmān b. Ṭalḥa"},
        {"kind": "cr", "q": "What was the name of the cave where the Prophet ﷺ and Abū Bakr sheltered?", "claims": ["GdC0R9"], "field": "o"},
        {"kind": "cr", "q": "ʿĀmir b. Fuhayra was the client (mawlā) of whom?", "claims": ["TGQWXr"], "field": "o"},
        {"kind": "cr", "q": "From which land had Abū Salama come back to the Prophet ﷺ in Makkah?", "claims": ["w9ueWe"], "field": "o"},
        {"kind": "mc", "q": "At Qubāʾ, ʿUmar b. al-Khaṭṭāb stayed as a guest with…", "claims": ["t4NMiW"], "field": "s",
         "distract": ["m988Be", "bbdzhJ", "fLBJvP"]},
        {"kind": "mc", "q": "Where did Khubayb b. Isāf live?", "claims": ["fLBJvP"], "field": "o",
         "distract": ["yBmczi", "jXKZiy", "aqtZ0g"]},
        {"kind": "mc", "q": "Who is named among the nobles of Quraysh at the council in Dār al-Nadwa?", "claims": ["NTb7kR"], "field": "s",
         "distract": ["jTP8uu", "XLFXE1", "m988Be"]},
        {"kind": "order", "q": "Put these moments in the order the text tells them.", "claims": ["s3Gzks", "6BPfTg", "5uFX7p", "GdC0R9"], "field": "g"},
        {"kind": "two", "q": "The text gives more than one report about where Ṭalḥa b. ʿUbaydullāh stayed in Madinah. What are they?",
         "claims": ["rNLzNH", "KPYQXI"], "field": "s"},
        {"kind": "src", "q": "How do we know that Quraysh met in Dār al-Nadwa? Whose report does the text pass on?",
         "claims": ["6BPfTg"], "chain": "S0679"},
    ],
    ("A", 2): [
        {"kind": "cr", "q": "Four set out on the journey. Who was the fourth, their guide?", "claims": ["SvJZlO"], "field": "s"},
        {"kind": "cr", "q": "What did the Prophet ﷺ write for Surāqa?", "claims": ["wJAwfM"], "phrase": "document"},
        {"kind": "cr", "q": "On what day of the week and in which month does the text date the arrival at Qubāʾ?", "claims": ["MivdFW"], "phrase": "Rabīʿ al-awwal, a Monday"},
        {"kind": "cr", "q": "Where did the Prophet ﷺ pray the Friday prayer?", "claims": ["r1HWVt"], "phrase": "valley of Rānūnāʾ"},
        {"kind": "cr", "q": "How long did ʿAlī stay in Makkah?", "claims": ["DAHOK8"], "phrase": "three nights and days"},
        {"kind": "mc", "q": "Where did Surāqa later meet the Prophet ﷺ?", "claims": ["8ZSY3V"], "field": "o",
         "distract": ["j1RVhy", "r1HWVt", "KsSPtp"]},
        {"kind": "mc", "q": "Which of these was one of the four who travelled?", "claims": ["RwkfdN"], "field": "s",
         "distract": ["DAHOK8", "dEl0ms", "smkTlG"]},
        {"kind": "mc", "q": "Where did Abū Bakr stay when they reached Madinah?", "claims": ["KsSPtp"], "field": "o",
         "distract": ["r1HWVt", "8ZSY3V", "uKefgP"]},
        {"kind": "order", "q": "Put these stops on the road north in the order Ibn Hishām gives them.",
         "claims": ["F13Q1a", "j1RVhy", "veJ2aF", "0n9xNi"], "field": "o"},
        {"kind": "two", "q": "With whom did the Prophet ﷺ stay at Qubāʾ? Write everything the text records.",
         "claims": ["smkTlG", "9AzKvc"], "field": "s"},
        {"kind": "src", "q": "How do we know about Surāqa's pursuit? Who first told the story?", "claims": ["wJAwfM"], "chain": "S0693"},
    ],
    ("B", 2): [
        {"kind": "cr", "q": "Among which clan did the Prophet ﷺ arrive at Qubāʾ?", "claims": ["gr1YVE"], "phrase": "Banū ʿAmr b. ʿAwf"},
        {"kind": "cr", "q": "With whom did ʿAlī stay at Qubāʾ?", "claims": ["6Q1RTn"], "field": "s"},
        {"kind": "cr", "q": "Where did Sahl b. Ḥunayf die?", "claims": ["uKefgP"], "field": "o"},
        {"kind": "cr", "q": "Who was the guide who took the Prophet ﷺ and his companion out on the road north?", "claims": ["6vXirs"], "field": "s"},
        {"kind": "cr", "q": "From the verses, which city did they understand to be the Prophet's destination?", "claims": ["8kyea4"], "field": "o"},
        {"kind": "mc", "q": "Where did the Prophet ﷺ stay among Banū ʿAmr b. ʿAwf before the first Friday?", "claims": ["vDijZF"], "field": "o",
         "distract": ["KsSPtp", "8ZSY3V", "F13Q1a"]},
        {"kind": "mc", "q": "Which of these places did the Prophet ﷺ pass on the road north?", "claims": ["j1RVhy"], "field": "o",
         "distract": ["8ZSY3V", "KsSPtp", "uKefgP"]},
        {"kind": "mc", "q": "Who stayed in Makkah three nights and days after the Prophet ﷺ left?", "claims": ["DAHOK8"], "field": "s",
         "distract": ["KsSPtp", "RwkfdN", "8ZSY3V"]},
        {"kind": "order", "q": "Put these stops on the road north in the order Ibn Hishām gives them.",
         "claims": ["pEwVZe", "YcKoC9", "Y95eMR", "0n9xNi"], "field": "o"},
        {"kind": "two", "q": "With whom did Abū Bakr stay when they reached Madinah? Write everything the text records.",
         "claims": ["dEl0ms", "9B83WI"], "field": "s"},
        {"kind": "src", "q": "How do we know who the four travellers were? Who first told it?", "claims": ["SvJZlO"], "chain": "S0692"},
    ],
}

HONESTY = [
    {"id": "H1", "cue": "dashed stops",
     "q": "On the road north, some stops were drawn with a dashed outline, or marked “no reviewed location yet”. What does that tell you?",
     "answer": "The place is named in the text, but nobody has yet checked where it is, so it is not drawn on the map.",
     "full": "says the text names the place AND its location is not known/checked/reviewed",
     "part": "says only that it is uncertain, or only that it is not on the map"},
    {"id": "H2", "cue": "two reports",
     "q": "Sometimes the text gives two different reports about the same thing. What should a careful reader do?",
     "answer": "Keep both reports, notice that the sources differ, and not pretend that only one is certain.",
     "full": "keeps both / says the sources differ and we should not pick one without evidence",
     "part": "notices there are two, but says to choose one (or to ignore one)"},
    {"id": "H3", "cue": "AI-extracted",
     "q": "Every sentence was marked “proposed (AI-extracted, not yet reviewed)”. What does that mean for how much you trust it?",
     "answer": "A computer program pulled the sentence out of the Arabic book and a scholar has not checked it yet, so it may contain mistakes; you can check it against the book and page given.",
     "full": "AI/computer made it from the book AND not yet checked by a scholar, so it could be wrong / should be checked",
     "part": "only one of the two ideas"},
]

TITLES = {h: None for h in HALVES}


def main() -> None:
    data = load()
    chapters = data["chapters"]
    for h, rng in HALVES.items():
        TITLES[h] = [chapters[n]["title"] for n in rng]
    pools = {h: half_claims(data, h) for h in HALVES}

    def get(h: int, tail: str) -> dict:
        hits = [c for c in pools[h] if c["id"].endswith(tail)]
        ids = {c["id"] for c in hits}
        assert len(ids) == 1, f"claim …{tail} not found once in Half {h} (found {len(ids)})"
        return hits[0]

    def text(c: dict, it: dict) -> str:
        if "phrase" in it:
            assert it["phrase"] in c["g"], f"phrase {it['phrase']!r} not in gloss of {c['id']}"
            return it["phrase"]
        return c[it.get("field", "s")]

    key = {"source": "lab/hijrah-night/index.html (claims of ingest/claims/ibn-hisham-full.jsonl)",
           "halves": {f"Half {h}": {"chapters": [n + 1 for n in rng], "titles": TITLES[h],
                                     "claims_shown": [c["id"] for c in dict((c["id"], c) for c in pools[h]).values()]}
                      for h, rng in HALVES.items()},
           "forms": {}, "honesty": HONESTY}
    used = {}
    for form in ("A", "B"):
        rnd = random.Random(f"pilot-1-form-{form}")
        md = [f"# Hijrah journey — test Form {form}",
              "",
              "Name code: ________  Date: ________  Session: pre / after / 1 week / 1 month (circle one)",
              "",
              "There are no trick questions. If you do not know, write “don’t know” — that is a useful answer too. "
              "Please work on your own and do not look anything up.",
              ""]
        items_out = []
        # Part 1: free recall first, before any cue
        md += ["## Part 1 — What do you remember? (about 5 minutes)", ""]
        for h in HALVES:
            iid = f"{form}-FR{h}"
            md += [f"**{iid}.** Write down everything you remember about this part of the journey: "
                   f"{'; '.join(TITLES[h])}. Short notes are fine.", "", "&nbsp;", "", "&nbsp;", ""]
            items_out.append({"id": iid, "half": h, "kind": "free_recall", "scoring": "idea units; see SCORING.md",
                              "claim_ids": key["halves"][f"Half {h}"]["claims_shown"]})
        n = 0
        for h in HALVES:
            md += [f"## Part {h + 1} — {TITLES[h][0]} … {TITLES[h][-1]}", ""]
            for it in ITEMS[(form, h)]:
                if it["kind"] == "src":
                    continue
                n += 1
                iid = f"{form}{n:02d}"
                cl = [get(h, t) for t in it["claims"]]
                rec = {"id": iid, "half": h, "kind": {"cr": "cued_recall", "mc": "multiple_choice", "order": "ordering",
                                                        "two": "two_reports"}[it["kind"]],
                       "question": it["q"], "claim_ids": [c["id"] for c in cl],
                       "sections": sorted({c["sec"] for c in cl}),
                       "citations": sorted({c["cite"] for c in cl}), "evidence": [c["g"] for c in cl]}
                if it["kind"] == "cr":
                    rec["answer"] = [text(c, it) for c in cl]
                    rec["points"] = len(cl)
                    md += [f"**{iid}.** {it['q']}", "", "Answer: ______________________________", ""]
                elif it["kind"] == "mc":
                    wrong = [get(h, t) for t in it["distract"]]
                    opts = [(text(cl[0], it), cl[0]["id"], True)] + [(text(w, it), w["id"], False) for w in wrong]
                    assert len({o[0] for o in opts}) == len(opts), f"{iid}: duplicate option text"
                    rnd.shuffle(opts)
                    letters = "abcd"
                    rec["options"] = [{"letter": letters[i], "text": o[0], "claim_id": o[1], "correct": o[2]}
                                      for i, o in enumerate(opts)]
                    rec["answer"] = [letters[i] for i, o in enumerate(opts) if o[2]]
                    rec["points"] = 1
                    rec["claim_ids"] = [o[1] for o in opts]
                    md += [f"**{iid}.** {it['q']} (circle one)", ""] + \
                          [f"- ({letters[i]}) {o[0]}" for i, o in enumerate(opts)] + [""]
                elif it["kind"] == "order":
                    right = [text(c, it) for c in cl]
                    shown = right[:]
                    while shown == right:
                        rnd.shuffle(shown)
                    rec["shown"] = shown
                    rec["answer"] = right
                    rec["points"] = len(right) - 1
                    rec["scoring"] = "1 point per adjacent pair in the right order (max n-1); see SCORING.md"
                    md += [f"**{iid}.** {it['q']} Write 1 for the first, 2 for the next, and so on.", ""] + \
                          [f"- ___ {s}" for s in shown] + [""]
                elif it["kind"] == "two":
                    rec["answer"] = [text(c, it) for c in cl]
                    rec["points"] = 2
                    rec["scoring"] = ("2 = both names, or one name plus saying there is another report; "
                                      "1 = one name only; 0 = neither")
                    md += [f"**{iid}.** {it['q']}", "", "Answer: ______________________________", "",
                           "______________________________", ""]
                items_out.append(rec)
                for c in cl:
                    used.setdefault(c["id"], set()).add(form)
        md += ["## Part 4 — How do we know?", ""]
        for h in HALVES:
            it = next(i for i in ITEMS[(form, h)] if i["kind"] == "src")
            cl = [get(h, t) for t in it["claims"]]
            chain = next(c for n2 in HALVES[h] for c in chapters[n2]["chains"] if c["sec"] == it["chain"])
            iid = f"{form}-SRC{h}"
            md += [f"**{iid}.** {it['q']}", "", "Answer: ______________________________", "",
                   "______________________________", ""]
            items_out.append({"id": iid, "half": h, "kind": "source_awareness", "question": it["q"],
                              "claim_ids": [c["id"] for c in cl], "sections": [it["chain"]],
                              "citations": sorted({c["cite"] for c in cl}),
                              "chain_shown": chain["names"], "eyewitness": chain["names"][-1], "points": 3,
                              "scoring": "1 names the book or its author (Ibn Hishām / Ibn Isḥāq / the Sīra); "
                                         "1 says it was passed on by named people (a chain of narrators); "
                                         "1 names the person at the end of the chain"})
        md += ["## Part 5 — Reading carefully", ""]
        for hq in HONESTY:
            iid = f"{form}-{hq['id']}"
            md += [f"**{iid}.** {hq['q']}", "", "Answer: ______________________________", ""]
            items_out.append({"id": iid, "half": None, "kind": "honesty_cue", "cue": hq["cue"], "question": hq["q"],
                              "answer": hq["answer"], "points": 2,
                              "scoring": f"2 = {hq['full']}; 1 = {hq['part']}; 0 = otherwise"})
        md += ["", "Thank you. You can stop here."]
        (OUT / f"form-{form}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        core = [i for i in items_out if i["kind"] in ("cued_recall", "multiple_choice", "ordering", "two_reports")]
        key["forms"][form] = {"core_items": len(core),
                              "core_points": {f"Half {h}": sum(i["points"] for i in core if i["half"] == h) for h in HALVES},
                              "cued_recall_points": {f"Half {h}": sum(i["points"] for i in core
                                                                      if i["half"] == h and i["kind"] == "cued_recall")
                                                     for h in HALVES},
                              "items": items_out}
    shared = sorted(k for k, v in used.items() if v == {"A", "B"})
    key["shared_target_claims"] = shared
    key["note"] = ("Ṭalḥa's two reports (S0670) are the only two-report passage in Half 1, so that item is an anchor "
                   "shared by both forms. Other target claims are disjoint between forms except those listed in "
                   "shared_target_claims (al-ʿArj closes both route orderings; a few Half 2 facts recur because "
                   "Half 2 has few claims).")
    OUT.mkdir(exist_ok=True)
    (OUT / "answer-key.json").write_text(json.dumps(key, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for f in ("A", "B"):
        print(f"Form {f}: {key['forms'][f]['core_items']} core items, points {key['forms'][f]['core_points']}")
    print(f"target claims shared by both forms: {len(shared)}")


if __name__ == "__main__":
    main()
