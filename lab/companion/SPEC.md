# Companion — specification (roadmap X1)

Standing rule: **the AI never asserts.** It may route, pick claims, and ask questions. Every
fact a learner reads is a recorded, sourced claim, shown verbatim with its citation. No rulings,
no tafsīr, no hadith grading, no judging of people. Refusals point to a qualified local scholar.

## Pipeline
1. **Intent filter** (rules first, model optional): `factual | ruling | tafsir | grading | persona |
   sectarian | out_of_scope | chit_chat`. Anything not `factual` never reaches retrieval.
2. **Typed query**: `{entities: [normalised names], predicate: rel_* | null, kind_hint}`.
   Names are normalised (diacritics, ʿ/ʾ, Arabic script → Latin aliases, ibn/b.).
3. **Claim retrieval**: lexical over `ingest/claims/ibn-hisham-full.jsonl` (subject, object,
   gloss, predicate synonyms); top-k with a score floor. Below the floor → `rephrase`.
4. **Move planner**: chooses one move from the whitelist and the claim IDs it uses.
   Recall-before-reveal: the first turn on a factual question is `ask` (claims held, not shown);
   `reveal-claim` follows the learner's attempt or "show me".
5. **Renderer**: fills fixed templates; claim text is pasted verbatim (gloss + citation from
   the passage's `mrs:canonicalCitation`, as in `lab/hijrah-night/build.py`). It never echoes
   the user's question (false premises cannot be laundered into the reply).
6. **Validator** `validate(text, shown_claims)`: removes verbatim claim spans, then rejects any
   remaining proper noun (capitalised/diacritic/Arabic-script token not in template vocabulary),
   digit, number word, or month/era name. A rejected reply is replaced by the `rephrase` template.

## Move whitelist (nothing else may be emitted)
| move | shows claims | purpose |
|---|---|---|
| `ask` | no (held) | recall prompt before reveal |
| `hint` | partial: claim's predicate/kind only | scaffold after a wrong attempt |
| `reveal-claim` | yes, verbatim | show one to three claims |
| `compare-reports` | yes, ≥2 | same subject+predicate, different reports (e.g. ages) |
| `suggest-next` | IDs only, labels from claims | guided next questions; the only child-mode input |
| `refer-to-scholar` | no | ruling / tafsīr / grading / sectarian judgement |
| `rephrase` | no | out of corpus, persona, unmatched, validator failure |

## Model output schema (an LLM may emit only this; it writes no prose)
```json
{"move": "reveal-claim", "claim_ids": ["ast:..."], "template": "reveal.default",
 "refusal": null, "next": ["ast:..."]}
```
`refusal ∈ {null, ruling, tafsir, grading, sectarian, persona, out_of_scope, child_mode}`.
Unknown move, unknown template, or a claim ID not returned by retrieval → reject, use `rephrase`.

## Refusal templates (fixed text, no names, no numbers)
- ruling: "That asks for a religious ruling. This companion only shows what the sources record. Please ask a qualified scholar you trust locally."
- tafsir: "Explaining the meaning of the Qurʾān is the work of qualified scholars. Please ask a scholar you trust locally."
- grading: "Judging the authenticity of a hadith is specialist scholarly work. Please ask a qualified scholar locally."
- sectarian: "This companion does not judge anyone's faith, rank or intentions. It can show what the sources record about a person; for judgements please ask a qualified scholar."
- persona: "I can't speak as anyone from the past. I can show you what the sources record about them instead."
- out_of_scope / unmatched: "I couldn't match that to a recorded report. Try naming one person, place or event."

## Child safety
- Under 13 (declared by parent/teacher at setup): **no open chat**. Input is chosen from
  `suggest-next` cards only; typed text gets `rephrase` + cards. No persona, no free generation.
- Data stays on device: question history, attempts and profile live in local storage; nothing
  identifying is sent. If a model is called, only the typed query (entities + predicate) is sent,
  never raw child text.
- No streaks/leaderboards; no push notifications for under-13s.

## Caching and cost kill-switch
- Cache key = normalised typed query → `(move, claim_ids)`. Rendered text is rebuilt from claims,
  so a cache never stores model prose. Pre-warm the cache with the adversarial set.
- Model calls only when the rule filter is uncertain. Hard daily budget per install and global;
  on breach, or on validator-failure rate > 2% in a rolling window, `COMPANION_LLM=off` flips the
  whole service to this no-model baseline (which is always available and always valid).

## Acceptance
Any model version must beat `companion.py` on `adversarial.jsonl` per category **with zero
validator failures**. See `results.md`.
