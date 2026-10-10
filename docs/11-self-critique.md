# 11 — Self-Critique

**Method.** A first-pass architecture was drafted along conventional lines: a knowledge graph of entities and relationships, a temporal layer, a geographic layer, a source-citation feature, a 3D renderer and an AI assistant. That design was then attacked deliberately. Thirty weaknesses were identified. Each is stated below with the revision it forced, and every revision is reflected in the preceding documents.

The items marked **structural** could not have been fixed later — they would have required rebuilding the corpus. Those are the ones that justify doing this exercise before writing code rather than after.

---

## Epistemic and data-model weaknesses

**1. Facts were primary; sources were attached. — structural**
The first design stored events and entities, with citations as a property. This is the standard model and it is unrepairable: once a corpus is authored as settled statements, the evidence cannot be reconstructed, conflicting reports cannot be represented without contradiction, and confidence has nowhere to live.
→ **Inverted the model.** The report (*khabar*) with its chain became the primitive; the historical world became a derived projection ([02 §1](02-knowledge-architecture.md)). This is the single largest change in the entire architecture.

**2. Grading was a property of a report. — structural**
`report.grade = "sahih"` is a category error. Grading is contested, evaluator-dependent, tradition-dependent and historically situated.
→ **Grades became `Evaluation` objects** — acts by named authorities, in named works, with reasoning. Multiple conflicting gradings coexist natively ([02 §7](02-knowledge-architecture.md), [06 §2.2](06-scholarly-methodology.md)).

**3. Confidence was a single float. — structural**
A normalized 0–1 score across Sunni ḥadīth criticism, Shia rijāl and academic source criticism would be a fabrication with a decimal point, and it invites spurious arithmetic.
→ **Confidence became a derived band within a declared tradition lens**, always decomposed into its inputs, never normalized across incommensurable systems.

**4. One normative account of contested history. — structural**
The first design had a single "correct" timeline. For the Seerah this is largely workable; for the period after 11 AH it silently encodes one tradition's account as the truth.
→ **Added the interpretation dimension (D7)** and tradition lenses; divergence modelled as attributed `Dispute` objects; the default lens is declared openly rather than presented as neutrality ([06 §2.3](06-scholarly-methodology.md)).

**5. Sīra material forced into ḥadīth categories.**
Applying a binary ṣaḥīḥ/ḍaʿīf frame to sīra-maghāzī material misrepresents both the material and the tradition's own handling of it — most of the Seerah corpus was never intended to meet ḥadīth criteria.
→ **Added "classical historical report" as a first-class evidence state**, neither dismissed nor elevated ([06 §2.1](06-scholarly-methodology.md)).

**6. Relationships were edges with attributes. — structural**
An edge cannot carry temporal extent, spatial extent, multiple facets, its own evidence, its own disputes, and n-ary participation. "Friend" as a label is precisely the flattening this project exists to avoid.
→ **Relationships became first-class n-ary objects with facets**, focusable and citable in their own right ([02 §5](02-knowledge-architecture.md)).

**7. Absence of evidence rendered as absence in history.**
An empty region of the graph reads to users as "nothing happened there." That inference is almost always wrong and sometimes defamatory toward whole regions and communities.
→ **Added `CoverageGap` as a modelled type**, with causes distinguishing *not yet ingested* from *sources lost* from *genuinely unattested*; empty search states report coverage rather than nothing ([02 §8](02-knowledge-architecture.md), [05 §3](05-ux-architecture.md)).

**8. Only one time axis. — structural**
Event-time alone discards *when a claim was recorded*, which for this corpus is among the most informative variables available.
→ **Added record-time (D6)** as a navigable axis, and system-time for auditability. This produced an entirely unanticipated capability — watching the historical record form — that is now among the project's strongest novelty claims ([01 §1](01-conceptual-model.md)).

**9. Dates stored as timestamps. — structural**
`622-09-24` manufactures precision that the sources do not support, and the fabrication is invisible once stored.
→ **Four-corner interval model with explicit precision, basis and uncertainty**; native calendar preserved; conversion performed at query time with stated uncertainty ([03 §1.2](03-technical-architecture.md)).

**10. Relative-only dating had no home.**
Much of the corpus is dated relationally — *after the death of Abū Ṭālib, before the Hijrah* — with no absolute anchor.
→ **Relative anchors as first-class, plus a temporal constraint solver** that propagates bounds and detects inconsistent chronologies, which is itself a research output.

**11. Calendar conversion treated as a pure function.**
Hijri↔Gregorian conversion is not deterministic across sighting-based and tabular calendars, and proleptic Gregorian choices add further offset.
→ **Store native, convert late, always carry `uncertainty_days`, always display the native form.**

**12. Places stored as coordinates. — structural**
A place is a named concept with a history, multiple names, changing extent, and frequently an unknown location.
→ **Place model with name-phases and multiple time-bounded geometry states**, including `unlocated` as a valid and common state ([03 §2.2](03-technical-architecture.md)).

**13. Routes as lines between endpoints. — structural**
The Hijrah as a line from Makkah to Madinah erases the entire historical content of the event and silently asserts a path nobody attests.
→ **Routes as segmented objects with per-segment confidence**; conjectural segments render as corridors; unknown intervals render as breaks, never as smooth interpolation ([03 §2.3](03-technical-architecture.md)).

**14. Modern borders and basemaps in historical views.**
Crisp polygons for pre-modern polities are both anachronistic and read as contemporary geopolitical claims.
→ **Graded influence surfaces with soft frontiers**; no modern political borders in any historical view ([03 §2.4](03-technical-architecture.md)).

**15. Person identity assumed tractable. — structural**
Homonymy is pervasive in the Arabic biographical corpus; naive matching merges distinct transmitters and splits single ones, and the resulting corruption is silent and compounding.
→ **Never auto-merge.** Automated matching proposes only; `IdentityAssertion` objects record decisions with reasoning; merges are versioned and reversible ([02 §3.3](02-knowledge-architecture.md)). Recognized as the project's hardest data problem ([09 §6](09-roadmap.md)).

---

## Visualization and interaction weaknesses

**16. Layout computed per view. — structural**
Force-directed simulation per query means time-scrubbing re-solves the layout, everything jumps, the user's mental map is destroyed, shared views are not reproducible, and position — being arbitrary — communicates nothing, violating the visual-semantics contract.
→ **Stable precomputed global embeddings**, versioned and anchored across corpus versions. Interaction changes visibility and camera, never position. This converted the hardest engineering problem into an offline batch job ([03 §4.1](03-technical-architecture.md)).

**17. Four dimensions as four coordinated views.**
Coordination is the state of the art (Palladio), but it still means four panels and a mental join the user must perform.
→ **The morph field**: continuous interpolation between coordinate frames in one persistent scene, affordable precisely because layout was made stable ([04 §2](04-visualization-architecture.md)).

**18. Hard appear/disappear on the timeline.**
Binary presence implies date precision the corpus does not have, for most entities.
→ **Three-state presence** (certainly / possibly / absent) with uncertainty-band fades; relationships animate on their own clocks ([03 §1.3](03-technical-architecture.md)).

**19. Node size by centrality, on by default.**
Computed prominence reads unavoidably as religious rank.
→ **No metric on by default**; metric name always displayed; **no ranked lists of Companions, ever**, as a product-level prohibition; analytics gated to Study/Research lenses with a standing interpretive caveat ([06 §7](06-scholarly-methodology.md)).

**20. The hairball.**
"Render the whole graph" is an anti-goal — a million nodes on screen is noise with a good frame rate.
→ **Query-first posture**, semantic zoom, server-side aggregation, a ceiling of ~2,000 individually meaningful elements ([03 §6.3](03-technical-architecture.md)).

**21. 3D assumed desirable.**
3D costs legibility, performance and accessibility, and the first design included it because it is impressive.
→ **3D permitted only where the z-axis carries information** — transmission depth, time extrusion, network-over-terrain — with an explicit gate: a specific question 2D cannot answer ([04 §1](04-visualization-architecture.md), [04 §8](04-visualization-architecture.md)).

**22. Cinematic mode as a headline feature.**
The most persuasive surface in the system, built over an immature corpus, would be widely shared and wrong — the project's defining failure mode.
→ **Story mode ships last**, over live data, with evidence anchored at every frame, disputed elements marked inside the cinematic, and no invented detail ([05 §5](05-ux-architecture.md)).

**23. Accessibility deferred.**
A purely visual observatory excludes blind and low-vision users, fails on low-end devices, and cannot be indexed.
→ **L0 added as a full tier containing complete knowledge**, built first; every ViewState renderable as prose; no information carried by colour alone ([05 §9](05-ux-architecture.md)).

**24. Global-South device and connectivity realities ignored.**
WebGPU and 3D assumed hardware much of the intended audience does not have.
→ **L0/L1 as the mobile product**, enforced payload budgets tested in CI against a low-end device profile, offline packs as a core feature ([05 §7](05-ux-architecture.md)).

---

## AI weaknesses

**25. AI generating historical narrative. — structural**
A hallucinated ḥadīth is a religious harm that propagates and cannot be recalled. Prompt instructions are not a control.
→ **Three tiers of text with retrieval preferred**, a deterministic **binding validator** that blocks unbound factual claims, no paraphrase of transmitted material, and hard refusal paths classified before retrieval ([07 §3](07-ai-architecture.md), [07 §5](07-ai-architecture.md)).

**26. Model-generated database queries.**
Arbitrary query surface, injection and resource risk, silently-wrong queries returning plausible results, and nothing to show the user.
→ **Typed query DSL**, statically validated, storage-independent, and **rendered back to the user in plain language** so the AI's reasoning is inspectable ([07 §4](07-ai-architecture.md)).

**27. No model provenance on extracted assertions.**
When a model is later found to have a systematic error, the assertions it produced cannot be located — the bug is unrecoverable.
→ **`extraction_method`, `extraction_model` and version recorded on every assertion**, making targeted re-review possible ([07 §7](07-ai-architecture.md)).

**28. The system depended on its AI layer.**
A single vendor dependency at the centre of a decades-scale scholarly instrument, and an unusable product in deployments where AI is judged inappropriate.
→ **Every AI action has a manual equivalent.** The observatory is fully usable with the AI layer disabled ([07 §10](07-ai-architecture.md)).

---

## Institutional and sustainability weaknesses

**29. Governance treated as administration.**
Whoever controls this corpus controls a widely-consulted account of Islamic history — a target for sectarian, institutional or state capture. The Venice Time Machine's suspension over institutional arrangements demonstrates that governance, not technology, is what kills projects at this scale.
→ **Governance as an architectural component**: cross-tradition board, separation of powers, logged decisions, scope-based *ijāza* permissions, and **forkability as a structural check** backed by real periodic open releases ([06 §9](06-scholarly-methodology.md)).

**30. Scholarly labour assumed available.**
The first design treated review as an administrative step. Scholar attention is the project's actual binding constraint, and expert labour without academic credit does not persist.
→ **Review-interface design as first-order engineering**: micro-tasks, batching, diff-first review, confidence-ranked queues, partial verification as a valid state, and **funded scholarly positions budgeted alongside engineering** with citable credit and DOIs ([06 §3.2](06-scholarly-methodology.md), [09 §2](09-roadmap.md)).

---

## Three weaknesses that remain unresolved

Honesty requires listing what the revisions did not fix.

**A. Explore-lens presentation of contested material.**
A child should not receive a survey of scholarly controversy, but must not be told a contested thing is settled. The adopted answer — plain-language hedging with detail one tap away — is reasonable but **unvalidated**. It needs empirical testing with real children and real teachers, and it may well be wrong.

**B. Whether non-specialists read uncertainty encoding correctly.**
The entire honesty architecture rests on users perceiving diffuse edges and reduced opacity as *calibrated doubt* rather than as visual noise or poor rendering. This is an empirical claim about perception that the project asserts and has not tested. If it is false, the architecture is sound and the product still misleads.

**C. Cross-tradition representation without false equivalence.**
Presenting divergent accounts fairly, without implying equal evidentiary weight, and without the system adjudicating, is genuinely unsolved. The architecture provides the mechanisms — attributed positions, tradition lenses, declared defaults — but the editorial judgement is irreducibly human and will be contested regardless of how carefully it is exercised.

These three should be stated publicly in the project's own documentation rather than discovered by critics.

---

## Post-publication corrections

Errors caught after Phase 0's first publication, logged rather than silently patched — because [06 §8](06-scholarly-methodology.md) requires exactly this of the corpus itself, and the architecture document is not exempt from its own standard.

**31. The Nūr/Nujūm diagram asserted a population gradient it had no warrant for. — caught by external review, 12 September 2026**
[01 §5](01-conceptual-model.md) originally drew the ṭabaqāt as a narrowing funnel — a small ring of Companions widening into "more numerous" later generations — and the demonstration prototype ([demo/index.template.html](../demo/index.template.html)) and the synthetic capacity test ([bench/capacity-test.html](../bench/capacity-test.html)) both built the same shape into working code. A reviewer pointed out the obvious fact this had missed: the Companions are estimated at well over 100,000 (Abū Zurʿah al-Rāzī, via al-Suyūṭī) — almost certainly the *largest* ring in the network, not the smallest — and real transmission activity within that ring is extremely skewed (the seven *mukthirūn* alone account for a disproportionate share of what survives) and densely cross-linked by kinship, shared battles and shared teachers, none of which a strictly generational feed-forward tree can represent.
→ **Corrected the diagram, the rule it justified, and every artifact built from it.** Rule 3 in [01 §5](01-conceptual-model.md) no longer claims a population shape by generation; it now states only that aggregation is a rendering necessity wherever local density demands it, which can occur *within* the origin-adjacent ring as plausibly as across rings. The demo's on-screen text and the capacity test's generator were both rewritten to stop implying a small, narrow origin (see the demo and bench sections of [README.md](../README.md)).

This entry exists because the catch is more useful recorded than hidden. It is also the methodology working exactly as designed: [REVIEWERS-BRIEF.md](REVIEWERS-BRIEF.md) exists to produce findings like this one before the corpus is built on top of the assumption, and this is the first one it produced.

---

**Next:** [12 — Final Architecture](12-final-architecture.md)
