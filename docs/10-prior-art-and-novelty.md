# 10 — Prior Art and Novelty

**Method.** This document surveys what exists as of September 2026, assessed against the six capabilities this project proposes to combine: **temporal knowledge graph · historical GIS · relationship network · 3D/4D visualization · scholarly source apparatus · AI exploration.** The conclusion is stated up front and then defended, because the honest answer is more interesting than a claim of pure originality.

> **Every individual capability exists, some at a very high standard. No system combines more than three or four. Crucially, no system anywhere treats the transmitted report with its chain as the atomic unit of the data model — and that, rather than any technical component, is what is genuinely novel here.**

---

## 1. Islamic-domain projects

### 1.1 Textual corpora and computational Islamicate studies

**OpenITI (Open Islamicate Texts Initiative)** — the foundational open corpus of premodern Islamicate texts; recent releases exceed 7,000 books, roughly 1.4 billion words, ~4,300 unique works by ~1,800 authors, openly licensed via Zenodo.
*Assessment:* outstanding, essential, and **the single most valuable existing asset for this project**. It is a corpus, not a knowledge graph — no entities, relationships, events or evidence model. **This project should build on it, never duplicate it.**

**KITAB project** (ERC-funded, led by Sarah Bowen Savant) — text-reuse analysis across the Arabic tradition, with algorithms developed with David Smith.
*Assessment:* directly relevant and directly reusable. Text-reuse detection is precisely the machinery needed to construct `ReportCluster` objects (parallel and variant reports). This is prior art to *adopt*, not to compete with.

**al-Ṯurayyā Project** (Maxim Romanov and Masoumeh Seydi) — a gazetteer and geospatial model of the early Islamic world: 2,000+ toponyms and nearly as many route sections, georeferenced from Cornu's atlas and the classical Arabic geographical tradition, with shortest-path route modelling.
*Assessment:* **the most valuable existing geographic asset in this domain**, and close in spirit to this project's route model. It is a gazetteer with routing — not temporally dynamic, not evidence-graded per segment, not connected to people or events. The right relationship is alignment and contribution, not replacement.

### 1.2 Ḥadīth and isnād systems

**Hadith-Viz** — the closest existing system to one component of this architecture: reportedly ~656,000 ḥadīth across ~960 collections, ~444,000 clusters, with interactive colour-coded chain graphs, narrator biographies, reliability grades, jarḥ wa taʿdīl evaluations and death years.
*Assessment:* **genuinely impressive, and the strongest prior art for the transmission layer.** It demonstrates the isnād-as-graph at real scale with real scholarly metadata. What it is not: connected to events, geography or the Seerah; not temporally navigable as a world; not a general historical knowledge graph; not an evidence substrate for non-ḥadīth historical claims.

**Sanadset 650K** and related narrator datasets; **Multi-IsnadSet (MIS)** for Ṣaḥīḥ Muslim — published, citable datasets of ḥadīth with narrator chains.
*Assessment:* directly reusable inputs. Adopt.

**Academic isnād network analysis** — a substantial literature applying social network analysis to narrator graphs (NetworkX, Neo4j, Gephi, Cytoscape), including recent work on **knowledge-graph-plus-transformer approaches to narrator disambiguation** (*Digital Scholarship in the Humanities*, 2025).
*Assessment:* confirms both the viability of the transmission-graph approach and that **disambiguation remains an unsolved research problem** — which is why [02 §3.3](02-knowledge-architecture.md) forbids auto-merging.

### 1.3 Seerah-specific interactive projects

Several exist, and honesty requires acknowledging them rather than claiming an empty field:

| Project | What it does | What it does not do |
|---|---|---|
| **Seerah Map** (siera-kaart.nl) | 1,400 years of Islamic history via interactive maps, timelines, articles and audio | Curated content over a map; not a queryable knowledge graph; no evidence model |
| **The Interactive Seerah** | Interactive timeline of the Prophet's ﷺ life, based on *The Sealed Nectar* | Single-source narrative; timeline navigation; no relationship graph, no provenance layer |
| **Prophetic Timeline** | Web resource with a 3D map of locations and events | 3D presentation of a curated narrative; not evidence-anchored or graph-backed |
| **SeerahGPT** | AI exploration of the Seerah with stated use of authenticated sources and interactive maps | LLM over a text corpus; no structured graph; the AI narrates rather than navigating a verified substrate |
| **Greentech Apps / Hadith Collection** | 41,000+ ḥadīth, grades, chains, isnād comparison; 1.5M+ users | Excellent reference application; not a historical world model |

*Assessment:* these are real, useful, and in several cases well-executed. **All of them are curated-narrative systems with visual navigation.** None inverts the fact/report relationship; none models relationships as first-class evidenced objects; none makes the historiographic dimension navigable; none permits a user to interrogate the warrant of an arbitrary visible element. The gap is not that nobody has visualized the Seerah — it is that nobody has built an *evidentiary substrate* beneath the visualization.

### 1.4 Digital libraries
**Shamela**, **Turath**, **Sunnah.com**, **Brill's Encyclopaedia of Islam**, **Qatar Digital Library**. All valuable; all libraries in the sense of [00 §3](00-vision.md) — they store documents, not the world the documents describe.

---

## 2. General digital-humanities prior art

The strongest conceptual precedents are outside the Islamic domain, and this project should learn from them directly.

**Six Degrees of Francis Bacon** — early-modern social network reconstructed from the *Oxford Dictionary of National Biography*: ~13,300 people, statistical inference of relationships via Poisson graphical lasso, and — decisively — **explicit confidence modelling**, with documented relationships visually distinguished from statistically inferred ones and the network filtered at a confidence threshold.
*Assessment:* **the most important methodological precedent for this project.** It proves that (a) uncertainty can be a first-class, rendered property of a historical network, and (b) users tolerate it. Its published design philosophy — preferring a sparse accurate network over a full error-ridden one — is exactly the posture adopted here.

**Mapping the Republic of Letters** (Stanford CESTA) — Enlightenment correspondence networks: ~55,000 letters, ~6,400 correspondents, city-to-city flows, with purpose-built visualization tools developed by historians and engineers together.
*Assessment:* the strongest precedent for **knowledge-transmission-as-geography-over-time**. Conceptually adjacent to the isnād layer, with a different corpus and no evidence-grading apparatus.

**Palladio** (Stanford Humanities + Design) — browser-based tool coordinating maps, networks, tables and timelines over humanities data, with temporal filtering that updates the map live.
*Assessment:* the direct ancestor of the L1 tier. **The morph field ([04 §2](04-visualization-architecture.md)) is the step beyond Palladio's coordinated views** — from synchronized panels to continuous interpolation within one space.

**Venice Time Machine** (EPFL / Ca' Foscari) — the most ambitious comparable project: ~190,000 documents scanned, ~8 TB, handwriting recognition at scale, and a Phase II (2020–2028) explicitly aimed at a "Venice Mirror World," a 4D model of the city across time.
*Assessment:* **the closest thing in existence to this project's ambition**, in a different domain. Two lessons: the technical vision is achievable at scale, and **its 2019 suspension over archive-access and institutional agreements is the clearest available warning that governance, not technology, is what kills projects of this size** ([06 §9](06-scholarly-methodology.md)).

**Seshat: Global History Databank** — 414 societies, 30+ regions, 200+ variables, 10,000 years, in 100-year steps, with an ontology that explicitly supports **variable uncertainty, temporal scoping, annotations and bibliographic references**.
*Assessment:* the best precedent for *structured uncertainty with citations at scale*. It is variable-centric rather than entity-and-relationship-centric — a database for quantitative hypothesis-testing, not an explorable world.

**Pelagios Network / Pleiades / World Historical Gazetteer** — linked-open-data infrastructure for historical places; Pleiades provides stable URIs for ~34,000 ancient places; 800,000+ annotations link 30 projects.
*Assessment:* **the model to imitate for the geographic layer and for federation generally.** It demonstrates that lightweight shared identifiers, rather than a central database, are what make historical data infrastructure federate.

**Chronas** — interactive historical map with a time slider showing political boundaries across 5,000 years, plus markers for cities, battles, artifacts and people. **ChronoZoom** — zoomable big-history timeline.
*Assessment:* good precedents for temporal-geographic navigation UX; both present curated data without an evidence apparatus, and Chronas renders pre-modern polities with crisp modern-style borders — precisely the anachronism [03 §2.4](03-technical-architecture.md) rejects.

**CIDOC-CRM (ISO 21127)** — the event-centric international standard for cultural heritage information integration.
*Assessment:* adopted as the upper ontology. Its event-centric modelling already solves relationship reification; extending it is far wiser than inventing a schema.

**Genealogical platforms** (WikiTree ~6.7M profiles, FamilySearch, Wikidata's genealogy graph) — prove that person-relationship graphs scale to millions with public contribution.
*Assessment:* useful scale precedent; weak on events, evidence and time-uncertainty.

---

## 3. Technology prior art

**GraphRAG** — graph-structured retrieval for LLMs matured substantially through 2024–26, with an extensive research literature on multi-hop reasoning over knowledge graphs and on mitigating retrieval drift from imperfect graphs.
*Assessment:* the AI architecture ([07](07-ai-architecture.md)) adopts this pattern, with a domain advantage: **this corpus's graph is scholar-verified rather than model-extracted**, which removes GraphRAG's dominant failure mode.

**WebGPU graph rendering** — GraphWaGu (the first WebGPU graph visualization system, with GPU-parallel layout and rendering) and GraphPU (Rust/WebGPU, millions of nodes and edges in real time) demonstrate the rendering scale required is achievable.
*Assessment:* validates the WebGPU-first decision in [04 §5](04-visualization-architecture.md).

**deck.gl / kepler.gl / CesiumJS** — large-scale GPU geospatial rendering; kepler.gl renders millions of points with time animation; CesiumJS provides first-class time-dynamic 4D visualization.
*Assessment:* the geographic tiers are well served by existing, mature libraries.

**Bitemporal graph databases** — bitemporality is consolidated in relational systems (and native in XTDB-class databases), but remains an active research area for graph databases as of 2025.
*Assessment:* confirms the decision in [03 §5.2](03-technical-architecture.md) to keep temporal logic in the relational core rather than depending on a graph engine to provide it.

**Neo4j Infinigraph** (2025) — distributed graph architecture at 100 TB+ scale; earlier demonstrations at 200B+ nodes and 1T+ relationships.
*Assessment:* confirms that database scale is **not** this project's constraint, and that adopting a graph engine can safely be deferred until latency evidence demands it.

---

## 4. The capability matrix

| System | Temporal KG | Historical GIS | Relationship network | 3D/4D | **Scholarly source apparatus** | AI exploration |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| OpenITI / KITAB | ○ | ○ | ○ | ○ | ◐ *(corpus provenance)* | ◐ |
| al-Ṯurayyā | ○ | **●** | ◐ | ○ | ◐ | ○ |
| Hadith-Viz | ◐ | ○ | **●** | ○ | **●** *(ḥadīth only)* | ○ |
| Seerah Map / Interactive Seerah | ◐ | ◐ | ○ | ○ | ○ | ○ |
| Prophetic Timeline | ◐ | ◐ | ○ | ◐ | ○ | ○ |
| SeerahGPT | ○ | ◐ | ○ | ○ | ◐ | **●** |
| Six Degrees of Francis Bacon | ◐ | ○ | **●** | ○ | **●** *(confidence)* | ○ |
| Republic of Letters | ◐ | **●** | **●** | ○ | ◐ | ○ |
| Palladio | ◐ | **●** | **●** | ○ | ○ | ○ |
| Venice Time Machine | **●** | **●** | ◐ | **●** | ◐ | ◐ |
| Seshat | **●** | ◐ | ○ | ○ | **●** *(citations + uncertainty)* | ○ |
| Pelagios / WHG | ◐ | **●** | ◐ | ○ | ◐ | ○ |
| Chronas | ◐ | **●** | ○ | ○ | ○ | ○ |
| **This proposal** | **●** | **●** | **●** | **●** | **●** | **●** |

● present · ◐ partial · ○ absent

**The honest reading of this table:** the last row is not novel because every cell is filled — it is novel because of *what fills the fifth column*. Several systems have a source apparatus. None has one in which the **report with its chain is the primitive** and everything else is derived from it.

---

## 5. What is genuinely novel

Six claims, in descending order of confidence.

### 5.1 The report-first data model — **strongest claim**
No surveyed system treats the transmitted report with its chain as the atomic unit from which events, biographies and relationships are derived. Every system stores facts and attaches sources. This inversion is the project's core contribution, and it is the one thing that cannot be added later to any of the systems above.

### 5.2 The isnād as a four-fold object
Treating the transmission chain as simultaneously evidentiary chain, social network, geographic diffusion path and temporal ordering — one encoding, four capabilities. Hadith-Viz has chains-as-evidence; Republic of Letters has knowledge-transmission-as-geography; nobody has unified them in a single substrate where the same edge serves both readings.

### 5.3 Historiographic time as a navigable axis
Holding event-time fixed while moving *record-time* — watching the historical record itself form across the 1st–3rd centuries AH. No surveyed system offers this. It is cheap to implement if designed in from the start, impossible to retrofit, and constitutes a research capability rather than a presentational feature.

### 5.4 The morph field
Continuous interpolation between network-, geographic-, temporal- and transmission-space within a single persistent scene. Palladio coordinates these views; this integrates them. The enabling decision — stable precomputed coordinate frames — is itself unusual.

### 5.5 Tradition-scoped, attributed grading as a structural feature
Grades as acts by named evaluators rather than properties of reports, with tradition lenses that never normalize across incommensurable epistemic systems. Seshat has uncertainty; Six Degrees has confidence; neither has *whose judgement*, which is the question that matters in this domain.

### 5.6 The citable ViewState
Making a configuration of evidence a first-class, version-pinned, resolvable scholarly citation. A small mechanism with a large consequence: it makes visualization citable, AI answers auditable, lessons authorable, and accessibility structural — all from one object.

### What is *not* novel, and should not be claimed
- Knowledge graphs for history — well established.
- Network visualization of isnāds — Hadith-Viz and the SNA literature got there first.
- Historical GIS and gazetteers — Pelagios, Pleiades, al-Ṯurayyā, WHG.
- Uncertainty in historical networks — Six Degrees of Francis Bacon.
- Time-sliders over historical maps — Chronas and many others.
- LLMs over Islamic texts — several products already.
- 4D historical reconstruction as an ambition — Venice Time Machine.

**The novelty is the composition and the inversion, not the components.** Stating this plainly is both more accurate and more persuasive to the scholarly audience whose participation the project requires — and that audience will know the prior art better than the builders do.

---

## 6. What this project should adopt rather than rebuild

| Need | Adopt | Rationale |
|---|---|---|
| Arabic text corpus | **OpenITI** | Openly licensed, enormous, already curated |
| Text-reuse / parallel detection | **KITAB methods** | Proven on precisely this corpus |
| Historical gazetteer (Islamicate) | **al-Ṯurayyā** | Best-in-class; align and contribute |
| Place identifiers (general) | **Pleiades / WHG / Wikidata** | Federation depends on shared identifiers |
| Narrator datasets | **Sanadset, MIS, and related** | Published, citable, reusable |
| Upper ontology | **CIDOC-CRM (ISO 21127)** | Standard; event-centric; interoperable |
| Temporal relations | **OWL-Time / Allen relations** | Standard and sufficient |
| Manuscript images | **IIIF** | Universal in the heritage sector |
| Uncertainty methodology | **Six Degrees of Francis Bacon** | The precedent to follow explicitly |
| Federation model | **Pelagios** | Lightweight shared identifiers over central control |
| Rendering | **WebGPU, deck.gl, MapLibre, Cesium** | Mature; do not build a graphics stack |
| Governance cautionary tale | **Venice Time Machine** | Study the institutional failure, not just the technical success |

**The project's scarce resource is scholarly attention, not engineering.** Every component adopted rather than rebuilt converts engineering time into scholarly capacity, which is the only conversion that improves the corpus.

---

## Sources

- [Venice Time Machine — EPFL](https://actu.epfl.ch/news/venice-time-machine-blueprints-finalized/) · [Time Machine Organisation: current state of affairs](https://www.timemachine.eu/venice-time-machine-project-current-state-of-affairs/) · [EPFL removed from project (SWI)](https://www.swissinfo.ch/eng/surprise-move-_epfl-booted-from-venice-time-machine-project-/45252134)
- [Six Degrees of Francis Bacon — DHQ](https://www.digitalhumanities.org/dhq/vol/10/3/000244/000244.html)
- [Mapping the Republic of Letters — Stanford CESTA](https://cesta.stanford.edu/research/mapping-republic-letters) · [RPLVIZ](https://web.stanford.edu/group/toolingup/rplviz/)
- [Palladio — Stanford Humanities + Design](http://hdlab.stanford.edu/projects/palladio/) · [Networks, Maps, and Time (DHQ)](https://www.digitalhumanities.org/dhq/vol/15/1/000534/000534.html)
- [CIDOC CRM](https://cidoc-crm.org/) · [CIDOC CRM (ISO 21127) explained](https://casrai.org/guides/cidoc-crm-iso-21127)
- [OpenITI corpus release](https://kitab-project.org/New-Release-of-Our-Open-Access-Arabic-Corpus,-OpenITI,-version-2020/) · [KITAB corpus](https://kitab-project.org/corpus/about) · [OpenITI on Zenodo](https://zenodo.org/records/10007820)
- [al-Ṯurayyā Project](https://althurayya.github.io/) · [Review of al-Ṯurayyā](https://reviewsindh.pubpub.org/pub/al-thurayya-project)
- [Hadith-Viz](https://hadith-viz.com/howto.html) · [Sanadset 650K (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S2352340922007478) · [Multi-IsnadSet](https://www.sciencedirect.com/science/article/pii/S2352340924004086)
- [Narrator disambiguation in hadith networks — DSH (Oxford)](https://academic.oup.com/dsh/article-abstract/40/4/1085/8253513) · [Social network analysis of hadith narrators](https://www.sciencedirect.com/science/article/pii/S1319157821000215)
- [Seshat: Global History Databank](https://en.wikipedia.org/wiki/Seshat_(project)) · [Building the Seshat ontology](https://link.springer.com/chapter/10.1007/978-3-319-34129-3_42)
- [Pelagios Network](https://pelagios.org/) · [Pleiades](https://pleiades.stoa.org/docs/partners/pelagios)
- [Chronas](https://chronas.org/) · [ChronoZoom — Microsoft Research](https://www.microsoft.com/en-us/research/project/chronozoom/)
- [Seerah Map](https://siera-kaart.nl/) · [The Interactive Seerah](https://theinteractiveseerah.com/) · [Prophetic Timeline](https://prophetictimeline.com/home/TheProject.php) · [SeerahGPT](https://seerahgpt.haramai.org/) · [Greentech Hadith Collection](https://gtaf.org/apps/hadith/)
- [GraphRAG survey (arXiv)](https://arxiv.org/abs/2501.13958) · [Knowledge Graph-Guided RAG (NAACL 2025)](https://aclanthology.org/2025.naacl-long.449/)
- [GraphWaGu (WebGPU graph rendering)](https://stevepetruzza.io/pubs/graphwagu-2022.pdf) · [GraphPU](https://github.com/latentcat/graphpu)
- [CesiumJS](https://cesium.com/platform/cesiumjs/) · [kepler.gl](https://kepler.gl/) · [deck.gl](https://deck.gl/showcase)
- [Neo4j trillion-relationship scale](https://neo4j.com/press-releases/neo4j-scales-trillion-plus-relationship-graph/) · [Neo4j Infinigraph](https://www.prnewswire.com/news-releases/neo4j-launches-infinigraph-the-most-scalable-graph-database-for-unified-operational-and-analytical-workloads-at-100tb-scale-302545785.html)
- [Bitemporal property graphs (2025)](https://link.springer.com/chapter/10.1007/978-3-032-05281-0_15) · [XTDB bitemporality](https://v1-docs.xtdb.com/concepts/bitemporality/)

---

**Next:** [11 — Self-Critique](11-self-critique.md)
