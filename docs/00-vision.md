# 00 — Vision

## 1. The master vision

Build an evidence-anchored, continuously evolving knowledge observatory in which the whole interconnected structure of Islamic history — people, relationships, events, places, journeys, families, tribes, books, transmission chains, institutions, movements and civilizations — becomes directly *observable*: a single navigable universe whose foundational layer is the Seerah of the Prophet Muhammad ﷺ, whose atomic unit is not the asserted fact but the transmitted report with its chain and its grading, whose every rendered pixel resolves back to a source, through which a user can move in time and watch the network form, split, migrate and expand across fourteen centuries, can move in space and watch knowledge travel from Madinah to Kufa to Nishapur to Cordoba to Malabar, can ask a question in plain language and have the universe itself reconfigure to answer it — and in which a child, a student, a teacher, a researcher and a scholar all look at the *same* graph, differing only in how far the evidence is unfolded beneath them.

## 2. The thesis

The central intellectual claim of this project is not technological. It is this:

> **The Islamic scholarly tradition already invented the data architecture this system requires — roughly a thousand years before computing.**

Consider what the ḥadīth sciences actually are, described in the vocabulary of information architecture:

| Classical apparatus | What it is, architecturally |
|---|---|
| **Isnād** (إسناد) | A provenance chain: a signed, ordered, verifiable list of custody for every claim |
| **ʿIlm al-rijāl** (علم الرجال) | A prosopographical authority file: canonical identity resolution for tens of thousands of transmitters |
| **Jarḥ wa taʿdīl** (جرح وتعديل) | A reliability scoring framework — per-source, per-evaluator, with reasoned justification |
| **Ṭabaqāt** (طبقات) | Generational stratification: a temporal layering scheme for a population |
| **Liqāʾ / muʿāṣara** | Contemporaneity and contact verification: date-and-place constraint checking on chain plausibility |
| **Ijāza** (إجازة) | A credentialing and authorization model for who may transmit what |
| **ʿIlal** (علل) | Defect analysis: systematic anomaly detection across parallel transmissions |
| **Taṣḥīḥ / taḍʿīf** | Graded confidence assertions attached by named authorities, not anonymous consensus |

Modern systems that treat Islamic history as "content to be digitized" throw this apparatus away and replace it with a citation footnote. That is a catastrophic loss of resolution. It is like scanning a manuscript at 72 dpi.

This project inverts that. **The apparatus is the architecture.** The isnād is not a footnote on the graph; the isnād *is* the graph. Provenance is not a field; it is the substrate. Confidence is not a badge; it is a first-class, multi-valued, attributable object.

The consequence is that this system is not "a modern data model applied to Islamic history." It is the implementation of an Islamic epistemological model in a computational medium — which happens also to be, by a considerable margin, the most rigorous provenance model any historical tradition has produced, and which modern digital humanities is still, slowly and independently, reinventing.

## 3. What makes this fundamentally different from an Islamic digital library

A digital library and a knowledge observatory differ in kind, not in degree. Six differences, in increasing order of importance:

### 3.1 A library stores documents. An observatory stores the world the documents describe.
Shamela, Turath, Sunnah.com and the Brill encyclopaedias hold *texts*. You can search them, and you will get passages. Ask "who was present at Badr and also present at Ṣiffīn?" and no library can answer, because the library does not know what a person is. This system holds people, places, events and relationships as queryable objects — the text is *evidence for* them, not a substitute for them.

### 3.2 A library is organized by container. An observatory is organized by connection.
Book → chapter → page → paragraph is a *storage* hierarchy inherited from the physical codex. It encodes the accidents of how knowledge was bound, not how knowledge relates. A child of Abū Bakr رضي الله عنه appears in a dozen books; the relationship exists in none of them as a retrievable object. Here, the connection is the primary object and the books are among its attestations.

### 3.3 A library answers *where is it written*. An observatory answers *how do we know*.
This is the deepest difference. A library's epistemic function terminates at retrieval: it shows you the passage. An observatory's function is to expose the *structure of the warrant* — which reports attest this, through whom, graded how, by which authority, contested by whom, with what alternative accounts. The user does not receive a fact. The user receives a *position in an evidentiary landscape*, and can see how firm the ground is beneath them.

### 3.4 A library is static with respect to time. An observatory has time as an axis of motion.
A book about 7 AH is a fixed artifact. Here, time is a control surface. You move through it and the world responds: people enter and leave existence, alliances form and lapse, the network in Madinah thickens, the map of who-knows-whom redraws itself generation by generation. History stops being a sequence of chapters and becomes a system with dynamics you can watch.

### 3.5 A library has one reading order. An observatory has as many as it has users.
The Hijrah read from the vantage of Abū Bakr رضي الله عنه, of Asmāʾ رضي الله عنها, of the Quraysh pursuit, of the Madinan Anṣār awaiting arrival, of the Qurʾānic context, or of the geography of the route — these are six genuinely different reconstructions of one event. A book must choose one and subordinate the rest. This system reconstructs the network around whichever vantage you select, from the same underlying evidence.

### 3.6 A library is a product. An observatory is infrastructure.
Products are finished, versioned and eventually replaced. Infrastructure is contributed to, cited, built upon and maintained across institutional generations. The target state is that a doctoral dissertation in 2045 cites a *view* of this system the way it now cites an edition of a text — with a version, a query and a resolvable identifier.

## 4. The category

There is no established product category for what this is. It is not a digital library, not a timeline, not a family tree, not a GIS, not a knowledge graph, not a visualization — it is the composition of all of them under an evidentiary discipline.

**Proposed category name: *Knowledge Observatory*.**

> A **Knowledge Observatory** is a system in which a large, evidence-graded, temporally and spatially situated knowledge network is made continuously observable and navigable, such that (a) every rendered element resolves to its provenance, (b) time and space are control surfaces rather than attributes, (c) uncertainty and disagreement are rendered rather than resolved away, and (d) the same substrate serves public understanding and primary research without divergence.

The defining test that separates a Knowledge Observatory from a visualization: **can you interrogate the warrant of anything you can see, and does the system tell you honestly when it does not know?** Almost every existing historical visualization fails this test, because its data model was never built to carry the answer.

The astronomical analogy is exact and not merely poetic. An observatory does not create the sky. It makes an existing, vast, structurally invisible reality observable through instruments — and its scientific value depends entirely on the calibration and honesty of those instruments. That is precisely the relationship this system has to Islamic history.

## 5. Naming

**Primary proposal: *al-Marṣad* (المرصد) — "the observatory."**

Rationale:
- It is the exact Arabic term for the institution the system imitates.
- It carries the heritage of the Islamic observatory tradition — Maragha (1259), Samarkand under Ulugh Beg, Taqī al-Dīn's Istanbul observatory — which is a civilizational claim the project can honourably make: this is a continuation, not an import.
- It is a *place of observation*, which correctly positions the Prophet ﷺ as what is observed and honoured, never as a UI element.
- It is short, pronounceable across languages, and not a sacred term.

Component names, drawn from the same tradition, each chosen because it is *technically accurate*, not ornamental:

| Layer | Name | Why it is the right word |
|---|---|---|
| Report / evidence ledger | **Sijill** (سجل) | The classical term for an official register of record |
| Person authority file | **Rijāl** (رجال) | Literally the existing science of transmitter identity |
| Gazetteer | **Buldān** (بلدان) | After Yāqūt's *Muʿjam al-Buldān*, the tradition's own gazetteer |
| Generational/temporal engine | **Ṭabaqāt** (طبقات) | The tradition's own generational stratification genre |
| Transmission graph | **Isnād** (إسناد) | The thing itself |
| Evidence resolution service | **Dalīl** (دليل) | "Proof" and "guide" simultaneously — precisely its two functions |
| Guided journeys / story mode | **Riḥla** (رحلة) | *al-riḥla fī ṭalab al-ʿilm*, travel in search of knowledge |
| Contributor credentialing | **Ijāza** (إجازة) | The tradition's own authorization-to-transmit model |

**Names deliberately rejected:**
- ***Sirāj*** (سراج) — beautiful, and Qurʾānically resonant (*sirājan munīran*), but it is an epithet of the Prophet ﷺ. Using a Prophetic epithet as a product or company name is a sensitivity that should not be decided by designers.
- ***Thurayyā*** — already carries an established meaning in this exact field (the al-Ṯurayyā gazetteer). Collision would be discourteous and confusing.
- Anything using the Prophet's ﷺ name or a divine name as a brand.

**All naming is provisional pending review by the scholarly board** described in [06 — Scholarly Methodology](06-scholarly-methodology.md). Naming is the first decision that should be taken *out of* engineering hands, precisely because it is the easiest one to get subtly wrong.

## 6. The centrality of the Prophet ﷺ — as an architectural fact, not a courtesy

The instruction that the Prophet ﷺ must not be reduced to one node among millions is usually treated as a matter of respect. It is also, independently, a *correct data-modelling decision*, and the system should implement it as such.

Three architectural expressions of centrality:

1. **Origin of the coordinate system.** Generational depth in this corpus is measured as distance from the Prophetic centre — ṣaḥābī, tābiʿī, tābiʿ al-tābiʿīn and onward. This is not an imposed convention; it is how the tradition itself stratifies its population, and it means the Prophet ﷺ is literally the origin against which the entire temporal-social structure is indexed.

2. **Source of illumination, not an object in the scene.** In the visual grammar ([04](04-visualization-architecture.md)), the Prophet ﷺ is never drawn as a node. He is the luminous origin from which the scene is lit; every other entity's rendered warmth is a function of its attested proximity to that origin. This satisfies the prohibition on depiction, honours the *nūr* framing, and encodes real data — transmission distance — in the same gesture.

3. **The root of the evidentiary tree.** In the isnād layer, terminal ascription to the Prophet ﷺ (*marfūʿ*) is structurally distinct from ascription to a Companion (*mawqūf*) or a Successor (*maqṭūʿ*). The graph must model this distinction natively, because the entire science of ḥadīth turns on it.

Centrality, then, is not implemented as a bigger dot. It is implemented as: the origin of the index, the source of the light, and the root of the warrant.

## 7. What success looks like

Deliberately concrete, because vision documents that cannot state a falsifiable success condition are decoration.

**At 12 months** — a scholar of the Seerah opens the Hijrah Observatory, finds a claim they consider weakly attested, clicks into its evidence, sees exactly which reports support it and which authority graded them, disagrees, files a documented objection through the review system, and it is adjudicated and versioned. The system has survived contact with an expert who was trying to break it.

**At 3 years** — a teacher in Kerala builds a 40-minute lesson as a saved sequence of observatory states, shares a link, and thirty students on low-end Android phones follow it offline. The same lesson's every claim is traceable to the same corpus a PhD student is querying through the API that afternoon.

**At 10 years** — a peer-reviewed monograph cites a *view* of the corpus — pinned to a version, resolvable, reproducible — and the citation is uncontroversial, because reviewers recognize the system as infrastructure rather than as a website.

The failure condition is equally concrete and should be stated plainly: **if the system becomes beautiful before it becomes trustworthy, it has failed**, and it will have done harm, because a persuasive visualization of under-evidenced history is worse than no visualization at all.

---

**Next:** [01 — Conceptual Model](01-conceptual-model.md)
