# 07 — AI Architecture

**The single governing principle:**

> **The AI operates the instrument. It does not testify about the sky.**
>
> It translates intent into queries, composes views, and explains *what the corpus contains and how it is warranted*. It never generates historical fact, never grades authenticity, never interprets scripture, and never produces text that a user could mistake for a transmitted report.

This is not caution for its own sake. A hallucinated ḥadīth is not a product defect; it is a religious harm that propagates, is screenshotted, and cannot be recalled. The architecture is built so that the harmful action is *structurally unavailable*, not merely discouraged by a prompt.

---

## 1. What "AI as interface" actually means

The conventional pattern — a chat panel beside a visualization — fails in both directions: the chat cannot see the view, and the view cannot respond to the chat. Here the AI's **primary output is a `ViewState`**, not prose.

```
  user question
      │
      ▼
  ┌─────────────────────────────────────────────────────┐
  │  AI NAVIGATION LAYER                                │
  │                                                     │
  │  produces:   ① a typed query        (executable)    │
  │              ② a ViewState          (the answer)    │
  │              ③ grounded narration   (bound to IDs)  │
  │              ④ an uncertainty note  (what's missing)│
  └─────────────────────────────────────────────────────┘
      │
      ▼
  the observatory reconfigures — and the text merely narrates what is now visible
```

The answer to *"Show everyone connected to Abū Bakr رضي الله عنه during the Hijrah"* is **the universe rearranging itself**, with a sentence explaining what was selected and on what basis. The visualization is the response; the prose is the caption.

---

## 2. The pipeline

```
 ① INTENT CLASSIFICATION
    lookup · relational · temporal · spatial · comparison · path · evidential
    · historiographic · out-of-scope · prohibited
      ↓                                         prohibited → refusal path (§5)
 ② ENTITY LINKING
    mention → candidate canonical IDs (lexical + vector + graph context)
    ambiguity is surfaced to the user, never silently resolved
      ↓
 ③ QUERY PLANNING
    → a TYPED QUERY OBJECT in a constrained DSL
      never free-form generated database query text (§4)
      ↓
 ④ EXECUTION
    graph traversal + temporal filter + spatial filter + confidence floor
    + active tradition lens
      ↓
 ⑤ EVIDENCE RESOLUTION (Dalīl)
    every returned element arrives with its provenance attached — not fetched later
      ↓
 ⑥ VIEW COMPOSITION
    ViewState: focus, morph weights, time window, layers, filters, camera
      ↓
 ⑦ GROUNDED NARRATION
    every factual token bound to an entity ID or an assertion ID
    unbound factual claims are structurally impossible to emit (§3)
      ↓
 ⑧ UNCERTAINTY REPORTING
    what was excluded, what is contested, what the corpus does not cover
      ↓
 ⑨ AUDIT RECORD
    question · query · corpus version · result set · ViewState — all persisted
```

Steps ⑤ and ⑧ are not optional stages that can be skipped under time pressure. Evidence travels *with* results, and an answer that cannot state its own limits is not emitted.

---

## 3. Grounded narration — how text is made safe

Three tiers of generated text, in descending order of preference. The system uses the highest tier that can answer.

**Tier 1 — Retrieved human text (preferred).**
Scholar-authored explanation nodes, written once, reviewed, versioned, stored in the corpus. Most common questions have stable answers; those answers should be written by humans and *retrieved*, not regenerated per user. This is cheaper, faster, and safer than generation, and it improves monotonically.

**Tier 2 — Template composition.**
Structured facts from the graph rendered through reviewed templates:
> *"{person} is recorded as present at {event} ({date_expression}), attested by {n} reports across {m} chains; {grading_summary}."*

Every slot is filled from graph data with a provenance anchor. The model chooses the template and the data; it does not author the sentence.

**Tier 3 — Constrained free generation.**
Permitted only for *navigational and descriptive* content — explaining what a view shows, what a query did, why a result set is empty. Under three constraints:
- Every factual token must bind to an entity or assertion ID; a **binding validator** runs post-generation and blocks unbound factual claims.
- No transmitted content may be paraphrased. Reports are quoted verbatim from the corpus or not shown.
- Output is labelled as system-composed and is never styled to resemble source material.

**The validator is the critical component.** It is a deterministic post-processing step, not a prompt instruction: parse the generated text, extract factual claims, verify each resolves to a corpus object in the current result set, and block or strip anything that does not. Prompts are guidance; validators are architecture.

---

## 4. Why a constrained query DSL, not generated Cypher/SPARQL

The common pattern is to have the model emit database query text. It is rejected here.

| Generated query text | Typed query object |
|---|---|
| Arbitrary query surface; hard to constrain | Closed set of composable operations |
| Injection and resource-exhaustion risk | Statically validated before execution |
| Silently wrong queries return plausible results | Malformed intent fails loudly |
| Hard to show the user what was asked | **Renderable back to the user in plain language** |
| Couples the AI layer to a storage engine | Storage-independent; survives projection changes |

The DSL covers the actual question space: find, filter (type/time/place/confidence/lens), traverse (bounded), path-find, aggregate, compare, and resolve-evidence. Anything outside it is not silently approximated — it is reported as unsupported, which is honest and also a roadmap signal.

Critically, the typed query is **shown to the user**, in readable form: *"I searched for people with an attested relationship to Abū Bakr, active between 0 and 2 AH, present in Makkah or on the Hijrah route, at confidence ≥ classical report."* The user can correct it directly. This makes the AI's reasoning inspectable rather than mysterious, which is the only acceptable posture for an instrument used in scholarship.

---

## 5. Hard boundaries and the refusal path

Classified at intent detection (①) and refused before any retrieval:

| Request | Response |
|---|---|
| "Is this hadith authentic?" | Shows recorded gradings by named authorities; **states explicitly that the system does not grade** |
| "What is the ruling on…" | Refuses; directs to qualified scholars; may show what the corpus records about positions and their proponents |
| "What does this verse mean?" | Refuses interpretation; may show recorded contexts and attributed classical commentary as *records*, clearly framed |
| "Write a hadith about…" | **Hard refusal.** No generation of anything resembling transmitted material, under any framing |
| "Show me an image of the Prophet ﷺ" | **Hard refusal**, with a plain explanation of why |
| "Who was the greatest Companion?" | Refuses to rank; may show what the corpus records about attested virtues, attributed to their sources |
| "Fill in what probably happened" | Refuses to speculate; shows the coverage gap and what is actually attested |

Refusals must be **substantive**, never boilerplate — explaining the boundary and offering what the system *can* legitimately do. A refusal that merely declines teaches the user nothing; a refusal that explains the epistemic boundary teaches them how the discipline works.

---

## 6. Retrieval architecture

The graph is the retrieval substrate, in the GraphRAG pattern that matured through 2024–26 — with a domain-specific advantage: **this corpus's graph is scholar-verified, not LLM-extracted.** The dominant weakness of GraphRAG systems is that the graph is itself a model artifact and inherits model errors. Here the graph's construction is human-adjudicated ([06 §3](06-scholarly-methodology.md)), so retrieval quality is bounded by scholarship rather than by extraction accuracy.

| Retrieval mode | Used for |
|---|---|
| **Structural traversal** | Relational questions — the primary mode; exact, explainable, verifiable |
| **Vector similarity** | Entity linking, near-duplicate report detection, "find reports like this" |
| **Lexical/Arabic search** | Name and phrase lookup, with morphological and orthographic variance handling |
| **Hybrid re-ranking** | Combining the above for ambiguous natural-language questions |

**Embeddings are used for *finding*, never for *asserting*.** A vector match proposes a candidate; the graph confirms or denies it. No answer rests on semantic similarity alone.

---

## 7. AI in the ingestion pipeline

Where AI provides the most value in this project — not at the interface, but upstream.

| Task | Suitability | Control |
|---|---|---|
| **Isnād/matn separation** | **Excellent** — well-defined, high-volume, tractable | Sampled audit |
| **Narrator chain parsing** | **Very good** — structured, repetitive | Sampled audit; anomalies escalate |
| **Named entity recognition** | Good | All output `proposed` |
| **Candidate entity linking** | Moderate — the hard case ([02 §3.3](02-knowledge-architecture.md)) | **Never auto-merged**; human adjudication mandatory |
| **Relationship extraction** | Moderate | Human adjudication mandatory |
| **Date/place extraction** | Good, with a caveat: models fabricate precision | Uncertainty preserved; precision claims reviewed |
| **Text-reuse and parallel detection** | **Excellent** — the KITAB project has demonstrated this at scale on the Arabic corpus | Feeds `ReportCluster` construction |
| **Translation of transmitted material** | **Prohibited** ([06 §5](06-scholarly-methodology.md)) | — |
| **Grading** | **Prohibited** | — |

Every AI-produced assertion carries `extraction_method`, `extraction_model` and version. This has a consequence worth planning for: when a model is later found to have a systematic error, **every assertion it produced can be identified and re-reviewed**. Without model provenance, a discovered extraction bug is unrecoverable — you cannot find what it touched.

---

## 8. AI-generated content strategy

| Content type | Policy |
|---|---|
| Transmitted reports, ḥadīth, Qurʾānic text | **Never generated.** Quoted from corpus or absent |
| Translations of the above | **Never machine-generated** in user-facing surfaces |
| Historical narrative prose | Not generated as fact; Tier 1 or Tier 2 only |
| View and query explanations | Tier 3 permitted, validated, labelled |
| Journey and lesson drafts | AI may draft; a human reviews before publication; AI-drafted status visible |
| Imagery of sacred persons/places | **Never generated** |
| Abstract/diagrammatic visuals | Generated from data only, deterministically — not by a generative model |
| Descriptive metadata, summaries of *coverage* | Permitted, labelled |

**The labelling rule:** anything machine-composed is visibly marked as such, at every tier, permanently. Not in a settings page — adjacent to the content.

---

## 9. Evaluation

The AI layer requires its own regression suite, distinct from the corpus golden set.

| Measure | Target |
|---|---|
| Intent classification accuracy | Especially on the prohibited class — **false negatives here are the critical failure** |
| Entity linking precision/recall | Measured against a scholar-adjudicated set |
| Query-plan correctness | Does the typed query actually express the question? Human-rated |
| Binding-validator catch rate | Adversarially tested with deliberately provocative prompts |
| Refusal appropriateness | Both over- and under-refusal measured; over-refusal degrades usefulness and is not "safe" |
| Citation accuracy | Every citation in generated output must resolve and must actually support the claim |
| Reproducibility | Same question + same corpus version → same ViewState |

**Adversarial testing is mandatory before any public release**, specifically targeting attempts to elicit fabricated ḥadīth, sectarian framing, ranking judgements, and depiction. These tests are written by people trying to break it, not by the people who built it, and the results are published.

---

## 10. What the AI layer must never become

- **A voice of authority on Islamic history.** It is a research and navigation assistant. Its tone, defaults and copy must reinforce this continuously — never oracular, always instrumental.
- **A substitute for scholars.** Where a question requires scholarly judgement, the correct output is the evidence plus a clear statement that judgement is required.
- **An invisible layer.** Every AI action is inspectable: the query is shown, the evidence is attached, the audit record persists.
- **The system's dependency.** The observatory must remain fully usable with the AI layer disabled. Every AI-driven action has a manual equivalent — search, filter, focus, trace. If the AI fails, becomes too expensive, or is judged inappropriate for a given deployment, the instrument still works.

---

**Next:** [08 — Prototype: The Hijrah](08-prototype-hijrah.md)
