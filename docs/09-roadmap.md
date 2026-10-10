# 09 — Roadmap, Challenges and Risks

## 1. Phasing principle

The staged sequence given in the brief (ontology → dataset → graph → 2D → time → geography → AI → 3D → 4D → expansion) is sound, with one amendment that matters:

> **The evidence layer is not a phase. It is present from the first commit.**

Every phase below carries its evidence discipline with it. A "Phase 6: add sources" would guarantee a corpus that can never be made honest, because the join between claim and warrant would have to be reconstructed after the fact — and that reconstruction is not possible at scale.

Second amendment: **L0 ships first, not last.** The accessible, text-based tier is the foundation, not the fallback. Building it first forces the data model to be complete before the visualization can flatter it.

---

## 2. The first twelve months

| Quarter | Focus | Deliverable | Gate to proceed |
|---|---|---|---|
| **Q1** | Ontology and foundations | Ontology v0.1 (CIDOC-CRM-aligned, extensions defined); append-only log; temporal and spatial types; licence register; scholarly board convened | Board convened with cross-tradition representation; ontology reviewed by three external specialists |
| **Q2** | The Hijrah corpus | 60–120 persons, 300–800 reports, chains parsed, routes graded, disputes documented — all scholar-reviewed; L0 tier live | A specialist cannot find a claim stated above its warrant |
| **Q3** | The observatory | L1: network + timeline + map; stable precomputed layout; morph field; evidence ladder; time-scrubbing with uncertainty | Time-scrub <100 ms; positions never jump; usable on low-end Android |
| **Q4** | Navigation and release | AI layer (typed DSL, entity linking, binding validator, refusals); ViewState as citable resource; adversarial testing; **public beta** | All acceptance criteria in [08 §7](08-prototype-hijrah.md) met; adversarial results published |

**Year-one team:** ~8–12 people. Two graph/backend engineers, one graphics engineer, one frontend engineer, one data engineer, one AI engineer, one designer, one project lead, plus **2–4 funded scholarly positions** — not advisors, not volunteers, but funded contributors with dedicated time. The single most common failure of projects like this is treating scholarly labour as donated. Budget it as engineering is budgeted.

**Year-one cost centre of gravity:** roughly 40% engineering, 30% scholarly labour, 15% data acquisition and rights, 15% infrastructure and operations. If scholarly labour falls below a quarter of the budget, the project has quietly become a visualization company.

---

## 3. Three years

**Year 2 — Depth: the full Seerah**
- The complete Seerah corpus at the Hijrah's evidentiary standard — this is the year's entire substance and it is larger than it sounds
- Scholar tooling: review queues, micro-tasks, dispute authoring, identity adjudication, the credit ledger
- Multi-tradition lens switching, live
- Public API and the first versioned, DOI-assigned open data release
- Education mode: journeys, teacher tools, classroom mode, offline packs
- Mobile PWA hardened for low-end devices
- Arabic-first interface at parity with English

*Gate:* an external scholar contributes a verified record end-to-end without project staff intervening. If the contribution pipeline only works when its builders operate it, it is not a pipeline.

**Year 3 — Breadth: the Companions and the first generations**
- The ṣaḥāba and the first two ṭabaqāt — the population expands by an order of magnitude
- **The transmission layer at scale**: isnād networks across the major collections, aligned with existing datasets (Sanadset-class narrator data, isnād-parsing research, the Hadith-Viz-style corpora) rather than rebuilt
- Automated chain integrity scanning across the corpus, with anomalies queued to specialists
- L2 (3D) — **only if the Stage-4 gate in [04 §8](04-visualization-architecture.md) is met**
- Institutional partnerships: two or three universities contributing and consuming
- Comparison engine; network analytics with interpretive guards
- Story mode, on the mature evidence layer

*Gate:* a peer-reviewed publication uses the corpus as a data source and cites a pinned view.

---

## 4. Ten years

Stated as capability milestones rather than dates, because a decade-scale plan with quarterly precision is fiction.

**Years 4–5 — Geographic and civilizational expansion**
Regional histories at genuine depth, beginning with the best-sourced: the transmission networks of Iraq, Khurāsān, the Ḥijāz, Egypt, al-Andalus. The historical gazetteer matures in partnership with existing efforts rather than in competition with them. L3 and globe mode where terrain genuinely serves the question.

**Years 4–6 — Federation**
The decisive structural transition: **other institutions run their own nodes and contribute their own scoped corpora**, with shared identifiers and a shared ontology. A university with Andalusian expertise curates that region under its own scholarly authority; the network federates. This is what converts a project into infrastructure, and it is the point at which the project stops depending on its founders.

**Years 5–8 — The citation substrate**
Identifiers stable enough, and coverage deep enough, that citing this corpus in scholarship is routine. Integration with reference managers, library systems and university curricula. The open dataset becomes a standard research resource independent of the interface.

**Years 7–10 — Ambient and institutional presence**
Museum installations. XR where the conditions in [05 §8](05-ux-architecture.md) are met. Curriculum integration at scale. The corpus available in a dozen languages with human-verified translations. Continuous contribution from a global scholarly community.

**The ten-year success condition:** the system's continued existence does not depend on any individual, organization or funder. That is the definition of infrastructure, and it is the only outcome that justifies the ambition.

---

## 5. Kill criteria

Stated in advance, because projects of this ambition rarely fail loudly — they drift, absorb funding, and are quietly maintained into irrelevance.

**Stop, or fundamentally restructure, if:**
1. **Scholarly participation does not materialize.** If, after eighteen months, qualified scholars are not contributing at a sustainable rate, the model is wrong. No amount of engineering compensates.
2. **The corpus cannot pass adversarial review.** If specialists repeatedly find claims presented above their warrant, the evidence discipline has failed in practice and the system is doing harm.
3. **The visualization becomes the product.** If a funding cycle passes in which the corpus grows less than the interface, the project has inverted its priorities. This is the most likely failure and the hardest to notice from inside.
4. **Governance cannot achieve cross-tradition representation.** A single-tradition corpus presented as a general account of Islamic history should not be built.
5. **The AI layer cannot be made safe.** If adversarial testing continues to elicit fabricated transmitted material, ship without the AI layer. The observatory works without it by design ([07 §10](07-ai-architecture.md)).

---

## 6. The biggest technical challenges

Ranked by expected difficulty, which is *not* the order most teams would guess.

1. **Entity disambiguation across the Arabic biographical corpus.** Homonymous narrators, kunya/nasab/nisba variance, incomplete name forms. Active research problem; no automated solution is adequate; human adjudication is the bottleneck. **Hardest problem in the project.**
2. **Layout stability at scale.** Solved architecturally ([03 §4.1](03-technical-architecture.md)) but the implementation — stable embeddings that remain anchored across corpus versions while the corpus grows by orders of magnitude — is genuinely difficult.
3. **Arabic information retrieval quality.** Morphological richness, orthographic variance, diacritics, transliteration. Determines whether search feels intelligent or broken.
4. **Temporal constraint solving with propagated uncertainty**, across a corpus where most dating is relative and some of it is inconsistent.
5. **Rendering budgets on low-end mobile** while preserving the full visual semantics.
6. **Uncertainty rendering that non-specialists read correctly.** Not a technical problem in the usual sense, but it must be *verified* — through user testing — rather than assumed.
7. **Federation without fragmentation** — shared identifiers and ontology across independently governed nodes.

## 7. The biggest scholarly challenges

1. **Cross-tradition representation without false equivalence.** Presenting divergent accounts fairly, without implying that all positions carry equal evidentiary weight, and without the system adjudicating. The hardest editorial problem in the project.
2. **Sustaining scholarly labour** at the volume required, over decades, with credit structures that make it academically rational to participate.
3. **Handling sīra material honestly** — neither applying ḥadīth criteria to material never intended to meet them, nor treating it as unexamined fact.
4. **The asbāb al-nuzūl and abrogation problems** — heavily contested, juristically consequential, and structurally tempting to over-model. Restricted relation types are a partial answer; scholarly governance is the rest.
5. **Avoiding the encyclopaedia trap** — the pull toward settled summary statements, which is what users ask for and what the architecture exists to resist.
6. **Translation at scale** without machine translation, which is slow, expensive and non-negotiable.

## 8. The biggest UX challenges

1. **Making uncertainty legible without making it discouraging.** A corpus honest about doubt can read as a corpus that knows nothing. The perceptual encoding must convey *calibrated* confidence, and this requires real user research, not designer intuition.
2. **Orientation in a vast space.** Users who feel lost stop exploring; the failure is silent and shows up only as drop-off.
3. **Cognitive scale.** Keeping ~2,000 meaningful elements on screen when the corpus holds millions, without the aggregation feeling like withholding.
4. **The Explore lens on contested material** — honest hedging in plain language for an audience with no scholarly vocabulary ([06 §4](06-scholarly-methodology.md)).
5. **Resisting feature accretion.** Five verbs is a discipline that every stakeholder request will erode.
6. **Making evidence inviting rather than intimidating.** The evidence ladder is the product's core value and its steepest cliff.

## 9. The biggest risks

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| **Spectacle outruns substance** — a beautiful demo on a thin corpus | **Critical** | **High** | Evidence-first phasing; corpus-growth as the headline metric; story mode ships last |
| **Sectarian capture or perceived bias** | **Critical** | Medium | Cross-tradition governance; attributed grading; forkable open corpus; declared defaults |
| **Scholarly labour never materializes** | **Critical** | Medium-high | Funded positions; citable credit; micro-task tooling; partial verification |
| **AI generates fabricated transmitted material** | **Critical** | Low, if architected as specified | Structural prohibition; binding validator; adversarial testing; publish results |
| **Funding ends mid-build** | High | Medium-high | Open data releases from year one; static archival fallback; institutional custodianship |
| **Data rights disputes** | High | Medium | Licence register before ingestion; public-domain-first; link-don't-copy |
| **Entity disambiguation errors corrupt the corpus** | High | Medium | Never auto-merge; versioned, reversible identity assertions; sampled audit |
| **Vandalism or coordinated manipulation** | Medium | Medium | Staged trust; signed writes; public audit log; reversibility |
| **Users read the visualization as more certain than it is** | **High** | **High** | Perceptual uncertainty encoding; tested, not assumed; coverage always visible |
| **Ontology lock-in** | Medium | Medium | Versioned schema; extension mechanism; escape hatch with review |
| **Founder dependency** | High | High | Federation by year 4–6; open everything; documented succession |
| **Scope collapse into a general "Islamic history app"** | Medium | **High** | The five verbs; explicit out-of-scope lists; kill criterion #3 |

**The two risks to watch most closely** are the two rated High/High: *spectacle outrunning substance*, and *users over-reading certainty*. Both are failures that look like success from inside the project, receive positive feedback, and are discovered late. Both require an external check — adversarial scholarly review for the first, empirical user testing for the second — and neither can be assessed by the team that built the thing.

---

**Next:** [10 — Prior Art & Novelty](10-prior-art-and-novelty.md)
