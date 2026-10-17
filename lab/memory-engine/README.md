# Memory engine (roadmap N4)

A whole-graph question bank plus a scheduler, built on the hijrah-night pattern: **every option is a claim**.
The right answer is right because a claim says so; a wrong option is wrong because a *different* claim puts
that name somewhere else, and after answering the learner sees that claim (gloss + citation + claim id).

- `build_bank.py` → `bank.json` (from `ingest/claims/ibn-hisham-full.jsonl`; citations read from the corpus TTL as in hijrah-night)
- `scheduler.js` — dependency-free; FSRS-style items + Bayesian Knowledge Tracing per concept; `Learner` session API
- `test.mjs` — `node --test lab/memory-engine/test.mjs` (7 tests, all pass)

## Bank (1,103 questions, 809 concepts)
| type | n | built from |
|---|---|---|
| present | 339 | event → person (participated_in / present_at / witnessed); distractors recorded at another event, ≤8 per event |
| event | 332 | person → event; distractors are events the person is never recorded at |
| where | 228 | person → place via resided_in / migrated_to / sheltered_at |
| family | 150 | capped lineage set (father_of / mother_of), only for people with ≥6 non-lineage claims |
| dispute | 46 | one slot, two fillers in one section (lodging, killer, death/burial place…): "the text gives two reports"; choose all |
| order | 8 | travelled_via stops of one traveller in one section, in text order |

Bare lineage is otherwise skipped. Questions are deduped on (type, stem, answers); ≤3 distractors; shuffles are seeded,
so rebuilds are stable. Difficulty in [0,1] (bands: 182 easy / 707 medium / 214 hard) from: distractors from nearby
sections (≤40 sections away — same story, more confusable), rarity of the answer in the graph, number of options.

Samples:
- *Who gave lodging to Ṭalḥa b. ʿUbaydullāh? Choose every answer the text gives.* → Khubayb b. Isāf **and** Asʿad b. Zurāra
  (two reports, both shown); distractor Aws b. Thābit — "ʿUthmān b. ʿAffān lodged with Aws b. Thābit."
- *Which of these does the text record at the Year of the Elephant?* → al-Aswad b. Maqṣūd; distractor Abū Ṭalḥa — "Abū Ṭalḥa attended Badr."
- *Put the Prophet ﷺ's stops in the order the text gives them (S0696).* → ʿUsfān, Amaj, Qudayd, … al-ʿArj.

## Scheduler
- **Items (questions):** FSRS-4 forgetting curve R = (1 + t/9S)⁻¹ and default weights; stability/difficulty updates as FSRS-4,
  simplified (no same-day steps, no fuzz). Next review when predicted recall falls to 0.9; a miss returns tomorrow.
- **Concepts (person/place/event):** BKT with P(L₀)=0.2, learn 0.15, slip 0.1, guess = correct options ÷ options.
  Every question updates all concepts it touches; mastered at P(known) ≥ 0.95.

## Recall before reveal
`Learner.ask()` returns the stem only. `reveal()` and `answer()` refuse until `commitRecall(text)` is called (an empty
"I don't know" is allowed). Options are shown without evidence; the claims appear only after answering. Free recall that
matches the answer grades *easy*, recognition only *good* — retrieval effort is what makes memory last (testing effect).

## Why no leaderboards
The evidence on gamification is mixed at best: points, badges and leaderboards raise short-term activity but meta-analyses
find small, unstable effects on learning, and rankings shift motivation from understanding to standing (overjustification;
demotivating for most of the board). For a sacred history, speed-and-score framing also invites guessing over reading the
source. So the only reward is the text itself, and the only progress display is personal.

## How the sky shows mastery
Each concept is a star. Brightness = BKT P(known) (`star()`): unseen stars stay dark, *faint* < 0.6, *learning*, then
*mastered* ≥ 0.95. Over time the learner's own sky fills in where they know the Sīra — no one else's sky is shown.
