# 12 — Final Recommended Architecture

## 1. The answer, in full

> *If we wanted to build the world's most advanced, user-friendly, interactive and experienceable system for understanding Seerah and Islamic history, what would the ideal system look like, and what architecture and technologies would actually be required to build it?*

**The ideal system is a Knowledge Observatory whose atomic unit is the transmitted report, not the historical fact.**

It stores what was transmitted, by whom, through which chain, recorded when, graded by which authority, contested by whom — and derives from that substrate a navigable historical world in which people, relationships, events, places, journeys, institutions and civilizations can be observed across fourteen centuries. It renders that world through four observable dimensions (entity, relation, space, time) which are themselves rendered *through* three epistemic ones (evidence, historiographic time, interpretation). Every visible element resolves to its warrant. Uncertainty is perceptible rather than annotated. Disagreement is displayed rather than resolved. An AI layer operates the instrument — composing queries and views, never asserting fact. A child, a teacher and a scholar look at one graph, differing only in how far the evidence is unfolded beneath them.

**The technologies required to build it are almost entirely available today.** The architecture's difficulty is not technological. It is: the discipline to model evidence first, the institutional capacity to sustain scholarly review for decades, and the restraint to keep the visualization subordinate to the corpus.

---

## 2. The consolidated architecture

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  EXPERIENCE          Explore · Learn · Study · Research — four lenses,        ║
║                      one graph · five verbs · Riḥla journeys · story mode     ║
║                      L0 Reader (universal) → L1 Network → L2 Depth → L3 4D    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  OBSERVATION         WebGPU renderer (WebGL2 fallback) · deck.gl + MapLibre   ║
║  (Marṣad)            · Cesium for globe modes · the morph field               ║
║                      ── renders only what the evidence layer publishes ──     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  NAVIGATION          intent → entity linking → typed query DSL → execution    ║
║  (AI)                → ViewState → grounded narration → audit record          ║
║                      ── binding validator · hard refusals · fully optional ── ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  PROJECTION          stable precomputed coordinate frames (network · geo ·    ║
║                      time · isnād) · aggregates · CDN tiles · versioned       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  KNOWLEDGE           entities · n-ary reified relationships · events          ║
║  (L3 — derived)      Rijāl · Buldān · Ṭabaqāt · Isnād                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  EVIDENCE (Dalīl)    assertions · attributed evaluations · disputes ·         ║
║                      report clusters · identity assertions · coverage gaps    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  RECORD (Sijill)     reports · chains · sources · witnesses · manuscripts     ║
║                      append-only · content-addressed · signed · immutable     ║
╚══════════════════════════════════════════════════════════════════════════════╝
        ▲
   INGESTION   sources → text prep → segmentation → AI extraction (proposal only)
               → disambiguation → scholarly adjudication → ijāza sign-off → commit
        ▲
   GOVERNANCE  cross-tradition board · scoped permissions · logged decisions
               · open corpus · forkable · institutional custodianship
```

**Storage:** one canonical append-only log in PostgreSQL; PostGIS as the spatial system of record; graph, search, vector and tile stores as **derived, disposable projections** — each rebuildable, none owning anything.

---

## 3. The ten decisions that define this architecture

If everything else were forgotten, these are what matter.

| # | Decision | What it prevents |
|---|---|---|
| 1 | **The report is primitive; the fact is derived** | An unrepairable corpus that cannot represent disagreement |
| 2 | **Grading is an attributed act, never a property** | Encoding one tradition's judgements as truth |
| 3 | **Relationships are n-ary objects with facets** | Flattening history into labelled lines |
| 4 | **Three time axes, including record-time** | Losing the ability to study how the record formed |
| 5 | **Every temporal and spatial value carries its uncertainty in-band** | Fabricated precision that cannot later be undone |
| 6 | **Stable precomputed layout; interaction never moves anything** | Incoherent, irreproducible, meaningless visualization |
| 7 | **One canonical log; all stores are derived projections** | Vendor lock-in; unreproducible scholarship; data that dies with the app |
| 8 | **AI navigates; it never asserts** | Fabricated transmitted material — the project's worst outcome |
| 9 | **L0 is a complete tier, built first** | A system that is universal only in principle |
| 10 | **Governance, forkability and funded scholarship are architecture** | Capture, drift, and the quiet death of an unfunded corpus |

Decisions 1–6 are **structural** — unavailable later at any price ([11](11-self-critique.md)).

---

## 4. The buildability ledger

Assessed honestly against September 2026 technology.

### Possible today, with known methods
- The complete data model — reports, chains, reified relationships, tri-temporal extents, uncertainty geometry, attributed evaluations, disputes, coverage gaps
- Append-only signed log; derived graph/search/vector/tile projections
- Temporal constraint solving with uncertainty propagation
- Historical GIS with per-segment route confidence and graded territorial surfaces
- L0 and L1 tiers in full, including the morph field
- Stable precomputed embeddings at corpus scale
- WebGPU rendering of 10⁵–10⁶ elements, with WebGL2 fallback
- The AI navigation layer exactly as specified — typed DSL, entity linking, binding validator, refusals
- Automated chain integrity and contact-plausibility scanning
- Isnād/matn segmentation and chain parsing at corpus scale
- Text-reuse detection for report clustering (demonstrated by KITAB)
- The full scholarly workflow, credit ledger, and citable ViewState

**Nothing in the core system requires a technology that does not exist.** This is worth stating plainly: the project is not blocked on research.

### Possible with significant engineering
- Layout stability *anchored across corpus versions* as the corpus grows by orders of magnitude
- Arabic retrieval at a quality that feels intelligent rather than adequate
- Full L2/L3 integration at 60fps on mid-range mobile
- Federation across independently governed institutional nodes with shared identifiers
- Offline packs for arbitrary region-period slices
- Review tooling efficient enough to keep scholarly throughput from being the sole constraint
- Cinematic story mode that remains genuinely evidence-anchored frame by frame

### Experimental / emerging
- Narrator disambiguation at corpus scale with acceptable precision — an **open research problem**, and the project's hardest
- Reliable relationship extraction from classical Arabic prose
- Automatic detection of contradictions across sources at scale
- Bitemporal graph databases (relational bitemporality is mature; graph is not — hence keeping temporal logic relational)
- Uncertainty encodings validated to be read correctly by non-specialists — **an empirical question, not a technical one**
- XR interfaces for network comprehension that outperform a screen

### Requires future advances, or may never be appropriate
- Fully automated extraction trustworthy enough to bypass scholarly review — **and it should be noted that this is not a goal.** Human adjudication is not a temporary limitation to be engineered away; it is the source of the corpus's authority
- Machine translation of transmitted material at publishable quality — prohibited on policy grounds regardless of capability
- Automated adjudication of scholarly disagreement — outside the system's remit permanently

**The honest summary:** the system described here can be built now. The parts that cannot are the parts that *should not* be automated.

---

## 5. Where effort actually goes

A deliberate correction to the intuition that this is primarily an engineering project.

| Area | Share of difficulty | Share of budget it will demand |
|---|---|---|
| Scholarly corpus construction and review | **~45%** | ~30% and rising |
| Data disambiguation and integrity | ~15% | ~10% |
| Visualization engineering | ~15% | ~20% |
| Backend and infrastructure | ~10% | ~15% |
| AI layer | ~5% | ~10% |
| Governance, rights, sustainability | ~10% | ~15% |

If the engineering share ever exceeds the scholarly share for more than one funding cycle, kill criterion #3 has been triggered ([09 §5](09-roadmap.md)).

---

## 6. The first six months, concretely

If work began tomorrow:

1. **Convene the scholarly board** before writing schema. Cross-tradition representation, specialism-scoped, funded. Nothing else on this list is safe to do first.
2. **Write the ontology** as a CIDOC-CRM extension; circulate to three external specialists; publish it openly.
3. **Build the record layer** — append-only log, temporal types, spatial types, evaluation objects. Nothing above it yet.
4. **Establish the licence register** and secure the source base, OpenITI-first.
5. **Encode the Hijrah corpus** by hand, with scholars, at full evidentiary depth. Slowly. This is the year's real work and it will feel too slow.
6. **Ship L0** — the reader tier, complete, before any visualization exists.
7. **Build the golden set** of scholar-adjudicated questions, before there is anything to regress.

Only then the renderer. **The discipline being enforced is that the corpus must be embarrassing to look at before it is impressive**, because every project of this kind that inverted the order produced a beautiful surface over a hollow core, and none of them recovered.

---

## 7. Closing

The Islamic scholarly tradition spent centuries building an apparatus for answering one question with more rigour than any comparable tradition achieved: **how do we know this, and from whom?** It produced chains of transmission, a science of identifying and assessing transmitters, graded confidence attributed to named authorities, generational stratification, credentialed authorization to transmit, and a literature of documented disagreement.

That apparatus is, described in modern terms, a provenance architecture — and a better one than most contemporary systems implement.

The opportunity is not to visualize Islamic history. Others have done that, some well. The opportunity is to build the first system whose **data model is the tradition's own epistemology**, executed at a scale and with an immediacy that the codex could never permit — so that the structure which has always been present in the sources, but observable only to those who had read tens of thousands of pages, becomes observable to anyone, without becoming any less true.

An observatory does not create the sky. It makes an existing, vast, structurally invisible reality observable — and its worth depends entirely on the honesty of its instruments.

That is the whole of the proposal.

---

*End of the Phase 0 architecture corpus. Return to the [index](../README.md).*
