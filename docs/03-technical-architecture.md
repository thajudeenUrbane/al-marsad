# 03 — Technical Architecture

**Method note.** This document derives requirements first and selects technology second. No product name appears in §§1–4. Selection begins at §5, and every selection cites the requirement it satisfies, what it stores, how it communicates, when it is introduced, and whether it is optional.

---

## 1. The temporal engine

Time is the dimension most systems get superficially right and structurally wrong. The requirements below are non-negotiable; several eliminate popular approaches outright.

### 1.1 Requirements

| # | Requirement | Eliminates |
|---|---|---|
| T1 | Three independent time axes: **event-time**, **record-time** (D6), **system-time** | Any single-timestamp model |
| T2 | Every temporal value is an **interval with uncertainty**, never an instant | `DATE`/`TIMESTAMP` columns as the primary representation |
| T3 | **Native Hijri** storage with explicit conversion method and conversion uncertainty | Any design that normalizes to Gregorian on ingest |
| T4 | **Relative-only** temporal facts must be first-class (*after X, before Y*) with no absolute anchor | Models that require a date to place an entity in time |
| T5 | **Open-ended and floruit-only** extents (active c. 180–210 AH; died after 250 AH) | `NOT NULL` birth/death assumptions |
| T6 | Temporal queries must return **confidence-qualified** results | Boolean interval overlap as the only predicate |
| T7 | **Allen interval relations** (before, meets, overlaps, during, starts, finishes, equals) as query primitives | Simple range comparison |
| T8 | Point-in-time reconstruction of the *whole graph state*, for any of the three axes, efficiently | Mutable-in-place storage without history |

### 1.2 The temporal value type

```
TemporalExtent
  calendar          hijri | julian | gregorian | seleucid | regnal | other
  native_value      as stated in the source, verbatim
  earliest_start    ┐
  latest_start      │  the four-corner model: the interval within which the
  earliest_end      │  start falls, and the interval within which the end falls
  latest_end        ┘
  precision         day | month | year | decade | generation | period | unknown
  basis             attested | inferred | computed | conventional | disputed
  conversion        { method, uncertainty_days, converted_by }   // when not native
  relative_anchors  [ { relation: before|after|during|…, target: EntityRef } ]
  attestation[]     → Assertion
```

The **four-corner model** (earliest/latest start, earliest/latest end) is the standard way to represent an indefinite interval and it handles every case in this corpus: a precisely dated battle collapses all four corners to two values; a person known only to have been "active in the time of al-Ḥajjāj" has wide corners; a report dated only "after the death of Abū Ṭālib" is expressed through `relative_anchors` with unbounded corners.

**On calendar conversion (T3).** Hijri↔Gregorian conversion is not a pure function. Tabular Islamic calendars and actual lunar sighting diverge by a day or more, regionally and by year; historical Julian/Gregorian proleptic choices add further offset. A system that converts on ingest and stores only the result has silently manufactured precision and destroyed the original. Therefore: **store native, convert at query time, always carry `uncertainty_days`, and display the native form alongside the conversion.** This is a small amount of work at the beginning and an unrecoverable loss if skipped.

**On relative time (T4).** A large fraction of Seerah and early-Islamic chronology is relational rather than absolute. The temporal engine must therefore include a **constraint solver**: given a set of relative assertions plus whatever absolute anchors exist, compute the feasible interval for each entity and *propagate* uncertainty. This is a well-understood class of problem (temporal constraint networks). It produces two valuable outputs beyond placement: the tightest defensible bound for each entity, and **detection of inconsistent chronologies** — sets of assertions that cannot all be true, which is a genuine research finding worth surfacing to scholars.

### 1.3 What "watching history unfold" actually requires

Scrubbing the timeline is a rendering problem with an honesty constraint. Four rules:

1. **No hard pops.** An entity whose existence interval is uncertain fades across its uncertainty band rather than appearing at a fabricated instant. The fade *is* the uncertainty, visible without a panel.
2. **Three states, not two.** At any given time an entity is `certainly-present`, `possibly-present`, or `absent`. Rendering only present/absent is a lie for most of the corpus.
3. **Relationships have their own clocks.** A marriage, an alliance, a teaching relationship each has its own extent, independent of its participants' lifespans. Scrubbing must animate relationships, not just entities.
4. **Positions do not move.** This is the single most important rule and it is easy to get wrong — see §6.3. Time changes what is *visible*, never where things *are*.

---

## 2. The geographic engine

### 2.1 Requirements

| # | Requirement | Eliminates |
|---|---|---|
| G1 | A place is a **named concept with a history**, not a coordinate | Storing `lat/lon` as the identity of a place |
| G2 | **Name-phases over time** (Yathrib → al-Madīna) with attestation per phase | Single-name place records |
| G3 | **Uncertainty geometry**: point, region, probability surface, or unlocated | Pin-only representation |
| G4 | **Routes as segmented first-class objects**, each segment independently evidenced | Great-circle lines between endpoints |
| G5 | **Time-varying territories** with explicitly soft frontiers | Modern-style polygon borders for pre-modern polities |
| G6 | Historically appropriate basemaps; **no modern political borders** in historical views | Off-the-shelf web basemaps as the default ground |
| G7 | Spatial queries combined with temporal and evidentiary filters in one pass | Map as a separate view over a separate store |
| G8 | Interoperability with existing historical gazetteers | Bespoke place identifiers with no external alignment |

### 2.2 The place model

```
Place
  id
  name_phases[]     { name, language, script, from: TemporalExtent, to: TemporalExtent,
                      attestation[] }
  geometry_states[] { geometry: Point | Polygon | MultiPolygon | ProbabilitySurface | null,
                      confidence: certain | probable | approximate | disputed | unlocated,
                      valid_extent: TemporalExtent,
                      basis: archaeological | textual | traditional | inferred | modern_identification,
                      attestation[] }
  place_type        settlement | quarter | well | mountain | valley | oasis | route_node
                    | region | province | structure | battlefield | cemetery
  contains / within  temporally-bounded containment (a district within a city within a region)
  external_ids[]    pleiades | wikidata | geonames | althurayya | whg
```

Two observations. First, `geometry_states[]` is a **list** because places move, grow, are destroyed and are rebuilt; a single geometry field cannot express a city's changing extent across six centuries. Second, `confidence: unlocated` with `geometry: null` is a valid, common and important state — a great many toponyms in classical sources are named but not securely identified, and the system must be able to say so rather than guessing a pin.

### 2.3 Routes — the Seerah's real geographic primitive

For this corpus, movement matters more than location. The Hijrah is not two points; it is a deliberately indirect path with a southward feint, a cave interval, a coastal-route guide, and named waypoints of varying attestation. Modelling it as a line from Makkah to Madinah would erase the entire historical content of the event.

```
Route
  id
  segments[]  ordered {
      from: PlaceRef | Coordinate,  to: PlaceRef | Coordinate,
      geometry: LineString | Corridor | null,
      confidence: attested | probable | conjectural | unknown,
      traversal: TemporalExtent,       // when this segment was traversed
      mode: foot | camel | horse | ship | mixed,
      attestation[], disputes[]
  }
  actors[]    who travelled it, when — a route may be shared by many journeys
```

Segment-level confidence is what makes honest route rendering possible: attested segments draw solid, conjectural segments draw as diffuse corridors, and unknown intervals draw as explicit breaks rather than as smooth interpolation. **Interpolating a conjectural path into a confident-looking line is the most common and most invisible falsification in historical cartography**, and this model forbids it structurally.

### 2.4 Territory and the border problem
Pre-modern polities did not have linear borders; they had cores, spheres of influence, tributary arrangements and frontier zones. Rendering the Umayyad state as a crisp polygon in a saturated colour is an anachronism that also reads as a modern geopolitical claim. Territories are therefore modelled as **graded influence surfaces** (core / controlled / tributary / contested / frontier) and rendered as gradients that fade at the edges. Modern national borders never appear in any historical view — they are available only in a clearly-labelled "modern reference" overlay.

---

## 3. Storage requirements, derived

Before any product is named, here is what must be true of the storage layer.

| # | Requirement | Why |
|---|---|---|
| S1 | **Append-only, immutable record of every change**, attributable and reversible | Scholarly auditability; reproducible citation; vandalism recovery |
| S2 | **Bitemporal at minimum** (valid + transaction time), tri-temporal in the domain model | Reconstruct both "what was true" and "what we believed, when" |
| S3 | **Transactional integrity** across entities, relationships and evidence | A relationship must never outlive its attestation |
| S4 | **Deep traversal** (6–20 hops) at interactive latency | Isnād chains, kinship paths, influence paths |
| S5 | **Geospatial indexing** with uncertainty-aware predicates | G-series requirements |
| S6 | **Arabic-aware full-text search** — morphology, diacritics, orthographic variants | The corpus is Arabic; naive tokenization fails badly |
| S7 | **Vector similarity search** | Entity linking, near-duplicate report detection, semantic retrieval |
| S8 | **Large binary storage** | Manuscript images, audio, 3D assets, precomputed tiles |
| S9 | **Cheap, fast bulk read paths** for precomputation and export | Layout jobs, analytics, open-data releases |
| S10 | **Zero lock-in; complete export; offline usability of the corpus** | "The data must outlive the app" |

No single technology satisfies S1–S10. Any architecture claiming otherwise is selling something. The question is therefore not *which database* but *which store owns which requirement, and what is the single source of truth*.

### 3.1 The governing decision: one canonical log, many derived projections

```
                    ┌─────────────────────────────────┐
   contributions ──▶│   CANONICAL EVENT LOG (Sijill)  │  append-only, signed,
                    │   the only writable surface     │  content-addressed
                    └────────────────┬────────────────┘
                                     │  (rebuildable, always)
         ┌───────────────┬───────────┼───────────┬────────────────┐
         ▼               ▼           ▼           ▼                ▼
   ┌──────────┐   ┌───────────┐ ┌────────┐ ┌──────────┐   ┌─────────────┐
   │ Relational│   │  Graph    │ │ Search │ │  Vector  │   │  Tiles /    │
   │ + spatial │   │ projection│ │ index  │ │  index   │   │  layouts    │
   │  (system  │   │(traversal)│ │(Arabic)│ │(linking) │   │ (rendering) │
   │of record) │   └───────────┘ └────────┘ └──────────┘   └─────────────┘
   └──────────┘
```

Every store to the right of the log is a **derived, disposable projection**. Any of them can be dropped and rebuilt from the log. The consequences are worth stating explicitly, because this one decision resolves a dozen problems that would otherwise appear later:

- **No vendor lock-in.** Replacing the graph engine is a rebuild, not a migration.
- **Reproducible scholarship.** Any query can be re-executed against the log as of a past version, yielding byte-identical results. This is what makes citing a view meaningful.
- **Right tool per query.** Traversal, text, spatial and vector workloads each go to an engine built for them, with no compromise schema.
- **Survivability.** The log is a file format, not a service. It can be archived, mirrored, and read with open tooling long after any running system is gone (S10).

---

## 4. Scale, honestly assessed

The brief asks for an architecture that eventually supports 10,000+ people, 100,000+ events, millions of relationships, thousands of places. It is important to say plainly:

> **These numbers are small for a database and enormous for a display.**

| Dimension | Target | Difficulty |
|---|---|---|
| Entities (10⁴–10⁶) | Trivial. A laptop handles this. | ★☆☆☆☆ |
| Relationships (10⁶–10⁸) | Routine for any modern graph engine; production systems run at trillions. | ★☆☆☆☆ |
| Deep traversal at interactive latency | Manageable with bounded-hop queries and precomputation; degrades with unbounded path search. | ★★★☆☆ |
| Arabic search quality | Genuinely hard — morphology, orthographic variance, transliteration. | ★★★★☆ |
| Entity disambiguation at corpus scale | The hardest *data* problem in the project. | ★★★★★ |
| Rendering 10⁵–10⁶ elements at 60fps, on mobile | Hard, but solved technique exists. | ★★★★☆ |
| **Layout stability across time and query changes** | **The hardest *engineering* problem in the project.** | ★★★★★ |
| **Cognitive scale — keeping it legible** | **The hardest *design* problem. No amount of engineering fixes it.** | ★★★★★ |

The strategic implication: **do not spend the early years on database scale.** It is not where the difficulty lives. Spend them on disambiguation, layout stability, Arabic retrieval and legibility — the four things that will actually determine whether the system works.

### 4.1 Layout stability — the problem nobody mentions

If the on-screen position of entities is produced by a force-directed simulation computed per view, then:
- scrubbing time re-solves the layout and everything jumps;
- filtering re-solves it and the user's mental map is destroyed;
- two users of the same query see different pictures;
- a shared or cited view is not reproducible;
- and position, being arbitrary, communicates nothing — violating the rule that every visual property must carry meaning.

**Resolution: positions are computed once, globally, server-side, and are stable.**

```
Global embedding job (offline, versioned)
  input   the full relationship graph at corpus version V
  output  a stable coordinate for every entity, in several coordinate frames:
            network-space   (graph embedding: relational proximity)
            geo-space       (lat/lon from place affiliation, with jitter resolution)
            time-space      (event-time axis × generational depth)
            isnad-space     (transmission depth from the Prophetic origin)
  guarantee  positions change only on corpus version change, never on interaction
             successive versions are anchored to minimize drift
```

Interaction then changes **visibility, opacity, colour and camera** — never position. Time-scrubbing becomes a fade, not a re-solve. Filtering becomes a dimming, not a re-layout. Two users see the same picture. A cited view reproduces exactly. And position becomes *meaningful*: proximity in network-space genuinely means relational proximity, every time.

This single decision converts the hardest engineering problem into an offline batch job. It is the most important performance decision in the architecture and it must be made at the beginning, because retrofitting stability onto a live-simulation renderer requires rewriting everything above it.

---

## 5. Technology selection

Now — and only now — products are named. Each is justified by requirement, with its role, its boundaries, and the phase at which it is introduced.

### 5.1 Recommended stack

| Layer | Selection | Requirements met | What it stores | When |
|---|---|---|---|---|
| **Canonical log** | **PostgreSQL** — append-only event tables, content-addressed payloads, signed entries | S1, S2, S3, S10 | Every contribution and revision, forever | Phase 1 |
| **System of record + spatial** | **PostgreSQL + PostGIS** — range types, exclusion constraints, GiST indexes | S2, S3, S5, G1–G8, T1–T8 | Current materialized state of entities, relations, temporal extents, geometry | Phase 1 |
| **Graph projection** | **Property-graph engine** (Neo4j, or Apache AGE to stay in-Postgres) | S4 | Derived traversal index | Phase 2–3, *when traversal depth demands it* |
| **RDF/LOD projection** | **Any standards-compliant triple store**, CIDOC-CRM serialization | Interop | Published linked-data view | Phase 4+, optional but strategically valuable |
| **Search** | **OpenSearch** with Arabic analysis (or Vespa at larger scale) | S6 | Text, matn, names, transliteration variants | Phase 2 |
| **Vectors** | **pgvector** initially; dedicated store only if it becomes a bottleneck | S7 | Embeddings for entity linking and near-duplicate detection | Phase 3 |
| **Objects** | **S3-compatible storage** | S8 | Manuscript images (IIIF), audio, 3D assets, tile bundles | Phase 1 |
| **Precompute** | **Python batch pipeline** (graph embedding, aggregation, tiling) | S9, §4.1 | Versioned layout and aggregate artifacts | Phase 3 |
| **Delivery** | **CDN-served binary tiles** (Arrow / compact custom format) | Performance | What the client actually downloads | Phase 3 |
| **API** | **GraphQL** (exploration) + **REST** (stable resources) + **bulk export** | §8 | — | Phase 2 |
| **Client** | **TypeScript PWA**, offline-capable | Mobile, offline | — | Phase 3 |
| **Rendering** | **WebGPU-first, WebGL2 fallback** — see [04](04-visualization-architecture.md) | Rendering | — | Phase 3 |

### 5.2 Why PostgreSQL is the centre and not a graph database

This is the least fashionable decision in the document and the one most likely to be challenged, so the reasoning is given in full.

A graph database is *better at traversal* and *worse at everything else this project needs*: transactional multi-entity integrity, temporal range constraints, geospatial operations, mature backup and point-in-time recovery, and — decisively — the ability to be the boring, stable, auditable substrate that a multi-decade scholarly corpus requires. Traversal is one requirement out of ten (S4). Making the traversal engine the system of record subordinates nine requirements to one.

Postgres, meanwhile, provides in one system: ACID guarantees (S3), native range types with exclusion constraints for temporal modelling (S2), the best open geospatial implementation in existence via PostGIS (S5), vector search via pgvector (S7), and an operational track record measured in decades (S10). Graph traversal is then added as a *projection* when the workload justifies it — at which point the choice of graph engine is reversible, because it owns nothing.

**When a graph engine should be introduced:** when recursive CTEs in Postgres stop meeting latency targets for the traversal patterns that actually matter — typically isnād chains beyond ~6 hops across a corpus of >10⁵ reports, or path-finding between arbitrary persons. Not before. Neo4j's Infinigraph architecture (2025) demonstrates the ceiling is far above this project's needs, so there is no scale-driven urgency to adopt early; adopt on latency evidence, not on anticipation.

### 5.3 Alternative stacks and their trade-offs

**Alternative A — RDF/SPARQL-native (triple store as system of record).**
*For:* native reification, OWL reasoning, first-class CIDOC-CRM, natural fit with the linked-open-data ecosystem this project should federate into, and the best story for interoperability with Pelagios-style infrastructure.
*Against:* weak geospatial support relative to PostGIS; awkward temporal modelling; smaller talent pool; query performance harder to reason about; tooling for application development is thinner.
*Verdict:* **adopt as a published projection, not as the core.** This captures nearly all the interoperability benefit at a fraction of the operational cost.

**Alternative B — Graph-database-native (Neo4j as system of record).**
*For:* the most natural expression of the domain; excellent traversal; strong visualization tooling; the shortest path to an impressive early demo.
*Against:* reified relationships become verbose; temporal interval logic must be hand-built; geospatial capability is far behind PostGIS; the system of record becomes a single vendor's product, which is a poor foundation for a corpus meant to outlive the organization.
*Verdict:* **use as a projection.** The demo advantage is real and is the main argument for adopting it earlier than strictly necessary.

**Alternative C — Document store (MongoDB/Elastic as primary).**
*For:* fast to start; flexible schema during ontology churn; good text search.
*Against:* no referential integrity — fatal for a corpus whose value is precisely its referential integrity; relationships degrade into denormalized copies; auditability must be built from nothing.
*Verdict:* **reject for the core.** Reasonable only for the search projection, which is what OpenSearch is doing in the recommended stack.

**Alternative D — Datomic/XTDB-style immutable bitemporal database.**
*For:* bitemporality and immutable history are *native* rather than constructed — precisely matching S1 and S2; the "as of" query model is exactly what reproducible citation needs.
*Against:* small ecosystems; limited geospatial; operational risk for a project expected to run for decades; hiring difficulty.
*Verdict:* **the most intellectually aligned option, and the recommended architecture deliberately reproduces its core idea** (immutable log + derived views) on mainstream infrastructure. Worth a serious evaluation spike in Phase 1; adopt only if the team has genuine depth in it.

**Alternative E — Build on Wikibase (the Wikidata engine).**
*For:* statement-level qualifiers and references are built in — closer to this project's needs than most alternatives; mature multilingual support; free federation with Wikidata; proven contribution workflows.
*Against:* the data model cannot express isnād chains or tradition-scoped grading without heavy abuse of qualifiers; performance at query time is a known weakness; governance model is wrong for a credentialed scholarly corpus.
*Verdict:* **reject as the core; federate with it.** Publish identifiers to Wikidata and consume its identifiers; do not host the corpus there.

---

## 6. Performance strategy

Performance here is not about the database. It is about what reaches the screen and when.

### 6.1 The rendering budget
| Target | Value |
|---|---|
| Initial meaningful paint, 3G, low-end Android | < 2.5 s |
| Core reader tier (L0) payload | < 300 KB |
| Interactive network tier payload | < 2 MB before user action |
| Frame budget, mid-range mobile | 16.6 ms (60fps); degrade to 30fps before dropping fidelity |
| Elements on screen, maximum *meaningful* | ~2,000 individually resolvable; aggregate beyond |
| Time-scrub response | < 100 ms — achievable only because positions are stable (§4.1) |

### 6.2 Techniques, in order of impact
1. **Stable precomputed layout** (§4.1) — eliminates the single largest per-interaction cost.
2. **Semantic zoom with server-side aggregation** — the client never receives what it will not draw. Tribe → clan → family → person unfolds on demand.
3. **Spatial and temporal tiling** — the corpus is partitioned by region × period into cacheable, CDN-served tiles.
4. **GPU-instanced rendering** — one draw call per class of element, not per element. A scene-graph object per node fails at ~10⁴; instancing carries 10⁶.
5. **Level-of-detail on edges before nodes** — edges dominate both visual clutter and vertex count; they are the first thing to aggregate.
6. **Progressive fidelity** — structure first, then labels, then detail. Never block on the expensive layer.
7. **Query-result caching keyed by corpus version** — the corpus changes rarely; caches can be long-lived and confidently invalidated.
8. **Offline packs** — a region/period bundle downloadable for full offline use, which is a functional requirement for much of the intended audience, not a nicety.

### 6.3 The anti-pattern, stated explicitly
**Never render the whole graph.** A million nodes on screen is not an achievement; it is noise with a high frame rate. The system's default posture is *query-first*: the user sees an answer to a question, not a corpus. "Show me everything" is available, deliberately unimpressive, and clearly labelled as an overview rather than a reading surface.

---

## 7. Security, integrity and trust

The threat model is unusual. The primary risk is not data theft — the corpus is intended to be open. It is **corruption of the record** and **capture of the narrative**.

| Threat | Control |
|---|---|
| Malicious or sectarian content injection | No anonymous writes to the core; staged trust; all writes signed; public audit log |
| Silent alteration of the record | Append-only log; content-addressed entries; cryptographic chaining; nothing is ever updated in place |
| Editorial capture by a faction | Governance charter with cross-tradition board representation; transparent dispute records; forkable open corpus ([06](06-scholarly-methodology.md)) |
| AI-generated content entering as fact | `extraction_method` on every assertion; AI output is `proposed` until a credentialed human accepts it; model + version recorded |
| Credential compromise | Hardware-key-backed sign-off for verification roles; scoped, revocable permissions (the *ijāza* model) |
| Citation rot | Immutable version pinning; permanent identifiers; every cited view resolvable against a historical corpus version |
| Loss of the institution | Open schema; periodic full public data releases; static export usable with no running services |
| Legal/licensing exposure | Per-source licence register; public-domain-first corpus; "link, don't copy" for rights-restricted material; enforced quotation limits |

**Integrity invariants** enforced in the database, not in application code:
- No `Relationship` may exist without at least one `Assertion`.
- No `Assertion` may exist without a `Report` or an explicitly recorded non-report basis.
- No `Evaluation` may exist without an identified evaluator and a citable location.
- No entity may be hard-deleted; retraction is an event, and the record of the retraction persists.
- No temporal extent may be narrower than its evidence supports — precision is a claim requiring warrant.

---

## 8. API architecture

Three surfaces with different contracts, because three audiences have irreconcilable needs.

**1. Exploration API (GraphQL).** Serves the client. Shaped for arbitrary, nested, user-driven queries. Every response includes provenance alongside content — provenance is never a second request, because an API that makes evidence optional produces clients that omit it.

**2. Resource API (REST, versioned, permanent).** Stable, citable identifiers for every entity, relationship, report, evaluation and dispute. Content-negotiated: JSON-LD (CIDOC-CRM), plain JSON, HTML. These URLs are intended to appear in footnotes for decades and must therefore never break.

**3. Research API (bulk).** Full or filtered corpus export as Parquet/CSV/RDF dumps, versioned and DOI-assigned, plus a query endpoint for analytical work and a Python client for notebook use. Researchers must be able to take the data away entirely — a scholarly infrastructure that requires its own website to be usable is not infrastructure.

**Cross-cutting contracts:**
- Every response carries the **corpus version** it was computed against.
- Every claim-bearing field carries a **provenance reference**.
- Every confidence value carries its **decomposition**.
- Every result set carries **coverage metadata** — what was searched, and what is known to be missing from it.
- A **view-state object** is a first-class, resolvable, citable resource (see [04 §6](04-visualization-architecture.md) and [07](07-ai-architecture.md)). This is the primitive that makes a *visualization* citable in scholarship.

---

## 9. Data ingestion pipeline

```
  ① SOURCE ACQUISITION
     public-domain corpora (OpenITI and similar) · institutional partnerships
     · manuscript imaging (IIIF) · licensed editions (metadata only where rights forbid text)
     ↓  every source enters the licence register before a single byte is processed
  ② TEXT PREPARATION
     OCR/HTR for manuscripts · normalization (orthography, diacritics) preserving the original
     · structural markup (work → recension → edition → passage)
     ↓
  ③ SEGMENTATION
     report boundary detection · isnād/matn separation
     ↓  isnād–matn separation is a well-defined, tractable NLP task and the
        highest-leverage automation in the pipeline
  ④ EXTRACTION  (AI-assisted, proposal-only)
     narrator sequence parsing · named entity recognition · candidate entity linking
     · relationship proposal · date and place extraction
     ↓  everything emitted is status=proposed, tagged with model id + version
  ⑤ DISAMBIGUATION
     candidate identity resolution against the rijāl authority file
     ↓  never auto-merged; ambiguous cases queue for human adjudication
  ⑥ SCHOLARLY REVIEW  ([06](06-scholarly-methodology.md))
     micro-task adjudication · diff review · grading attachment · dispute documentation
     ↓  signed under the ijāza model
  ⑦ COMMIT
     append to canonical log · rebuild projections · version the corpus
     ↓
  ⑧ PUBLISH
     recompute layouts and tiles · invalidate caches · release notes · DOI on major versions
```

**The pipeline's governing rule:** the boundary between ④ and ⑥ is absolute. Nothing crosses from machine proposal to published knowledge without a credentialed human act, and the record of who performed that act persists permanently. Throughput will be limited by ⑥ — scholar attention is the scarcest resource in the entire project — which is why [06](06-scholarly-methodology.md) treats review-interface design as a first-order engineering problem rather than an administrative afterthought.

---

**Next:** [04 — Visualization Architecture](04-visualization-architecture.md)
