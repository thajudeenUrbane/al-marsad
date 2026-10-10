# 02 — Knowledge Architecture & Ontology Specification

**Document status:** Normative specification, version **0.1.0-draft**.
**Review status:** Not yet reviewed. This document is written to be attacked by specialists; §14 lists what is most likely wrong.

**Machine-readable companions** — these are the specification; the prose below explains it.

| File | Contents |
|---|---|
| [`ontology/marsad.ttl`](../ontology/marsad.ttl) | OWL/Turtle ontology — classes, properties, controlled vocabularies |
| [`ontology/relations.ttl`](../ontology/relations.ttl) | The relation registry (§9), with inverses and restrictions |
| [`ontology/shapes.ttl`](../ontology/shapes.ttl) | SHACL constraints — the integrity invariants of §10 |
| [`ontology/examples/thawr.ttl`](../ontology/examples/thawr.ttl) | Worked example (§11), fully modelled |
| [`ontology/validate.py`](../ontology/validate.py) | Validator — `python ontology/validate.py` |

**Verified as of 11 September 2026:** all four graphs parse (1,804 triples), and the worked example **conforms — no violations**, with 4 warning-level advisories flagging stub positions that lack a named proponent. That result is reproducible with the validator above.

> **A note to reviewing scholars.** This is a data model, not a historical argument. It does not claim anything about the past. It specifies the *shape* of a container built so that what you know can be recorded without being flattened — chains preserved, gradings attributed to whoever made them, disagreement kept rather than resolved, and uncertainty carried rather than rounded away. Where the model requires a judgement that only a specialist can make, it is marked **⟨scholar⟩**. Those marks are the places your expertise would enter the system — twenty of them in this document, and the count will grow, not shrink, as the model gets more honest about what it cannot decide.

The shortest way to see what is being proposed is [the worked example](../ontology/examples/thawr.ttl): one event, one chain, one grading, one unresolved dispute, and one route segment that admits it is guessing.

---

# PART I — RATIONALE

## 1. Ontological commitments

Four commitments. Each closes off large regions of design space, and the closures are the point.

### C1 — The report is primitive; the fact is derived.
The base object is the **Khabar** (report): a unit of transmitted content with a chain. Events, biographies and relationships are *reconstructions* over clusters of reports. The system never stores "the Hijrah occurred on date D" as a bare truth; it stores the reports asserting it and derives the consensus view.

*Consequence:* the historical world is a materialized projection, rebuildable whenever evidence or grading changes. This is what lets the corpus be revised across scholarly generations rather than frozen at the moment of authorship.

### C2 — Relationships are entities, not edges.
A connection is a first-class object with identity, temporal extent, spatial extent, evidence, contestation status and its own relationships. It can be focused on, cited, disputed and versioned.

*Consequence:* there are no meaning-bearing edges in the canonical model. What look like edges in the interface are *projections* of relationship objects.

### C3 — Grading is an act by an agent, never a property of a thing.
There is no `report.grade` field anywhere in this system. There are **Evaluation** objects: *this evaluator, in this work, at this locus, assigned this grade to this report, for this stated reason.*

*Consequence:* multiple conflicting gradings coexist without contradiction. This single decision is what makes the corpus usable across Sunni, Shia, Ibadi and academic historical-critical communities simultaneously.

### C4 — Every temporal and spatial value carries its uncertainty in-band.
There is no bare `date` and no bare `lat/lon`. There are interval-with-confidence and geometry-with-confidence structures. Precision is never fabricated by the storage format.

*Consequence:* the renderer can always express doubt, because doubt is present in every value it receives. A system that stores `622-09-24` cannot later become honest.

## 2. Why report-first, stated for reviewers

The conventional model stores a fact and attaches a citation:

```
Event(Hijrah, date: 622-09) ──cited_by──▶ "Ibn Hishām, I:485"
```

This is unrepairable, for four reasons that compound:

1. **Conflicting reports must be reconciled at authoring time**, by whoever entered the data, silently, without recording that a choice was made.
2. **Grading has nowhere to live**, because the fact is not the thing that gets graded — the report is.
3. **The attestation gap is lost.** A claim about 1 AH first recorded in 220 AH is a different epistemic object from one recorded in 90 AH, and the flat model cannot express the difference.
4. **Revision requires rewriting history** rather than re-deriving it.

The report-first model:

```
Report ──has_chain──▶ TransmissionChain ──links──▶ Narrators (dated, placed)
   │
   ├──asserts──▶ Assertion ──about──▶ Event | Relationship | Entity
   ├──member_of──▶ ReportCluster (parallels, variants, corroborations)
   └──◀──assessed_by── Evaluation (by a named authority, in a named work)
                              │
                     Derived: the historical world
```

The user still reads "the Hijrah occurred in Rabīʿ al-Awwal, 1 AH." That sentence is now a *projection* with the evidence intact beneath it.

## 3. The isnād is four objects at once

An isnād — *A ← B ← C ← Companion ← the Prophet ﷺ* — is simultaneously four things, and they are the same data:

| Read as | Yields |
|---|---|
| Evidentiary chain | The warrant for a claim; the object of ḥadīth criticism |
| Social network | Who taught whom, who met whom, across generations |
| Geographic diffusion path | Each narrator has a city — knowledge moving Madinah → Kufa → Nishapur → Cordoba |
| Temporal ordering | Each narrator has dates; contact plausibility is checkable against them |

Therefore the transmission layer and the evidence layer are **one graph read two ways**. Every unit of scholarly effort spent encoding a chain pays into four capabilities at once. This is the economic argument that makes the project's scope affordable: the most expensive data to produce is also the most reusable.

---

# PART II — NORMATIVE SPECIFICATION

## 4. Conformance

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, **MAY** and **OPTIONAL** are to be interpreted as described in RFC 2119.

A dataset **conforms to this specification** if it validates without violation against [`ontology/shapes.ttl`](../ontology/shapes.ttl) at the corresponding version, and satisfies invariants I4 and I12 (§10), which are enforced at ingestion because they cannot be fully expressed in SHACL.

Constraints carry two severities, and the distinction is deliberate:

- **`sh:Violation`** — the model's non-negotiable discipline. Blocks conformance.
- **`sh:Warning`** — a likely error requiring a human decision. Does not block conformance, because a corpus that refuses incomplete data will never be built. But advisory counts **MUST** be tracked over time: a corpus silently accumulating them is degrading.

```bash
python ontology/validate.py                      # the worked example
python ontology/validate.py path/to/data.ttl     # your own data
```

**⟨scholar⟩ marks** identify decisions this specification deliberately declines to make, because they require domain judgement. An implementation **MUST NOT** resolve a ⟨scholar⟩ decision automatically, and **MUST** record the identity of the person who resolved it.

## 5. Namespaces, identifiers and URI policy

### 5.1 Namespace bindings

| Prefix | Namespace | Role |
|---|---|---|
| `mrs:` | `https://w3id.org/marsad/core#` | This ontology |
| `mrsid:` | `https://w3id.org/marsad/id/` | Instance identifiers |
| `crm:` | `http://www.cidoc-crm.org/cidoc-crm/` | CIDOC-CRM 7.1.3 |
| `lrmoo:` | `http://iflastandards.info/ns/lrm/lrmoo/` | LRMoo (WEMI) |
| `time:` | `http://www.w3.org/2006/time#` | OWL-Time |
| `prov:` | `http://www.w3.org/ns/prov#` | PROV-O |
| `skos:` | `http://www.w3.org/2004/02/skos/core#` | Controlled vocabularies |
| `sh:` | `http://www.w3.org/ns/shacl#` | Constraints |
| `geo:` | `http://www.opengis.net/ont/geosparql#` | Geometry |

**On `w3id.org`:** a persistent-identifier redirect service maintained by the W3C Permanent Identifier Community Group. It is used rather than a project-owned domain deliberately — identifiers in a corpus intended to be cited for decades **MUST NOT** depend on the continued existence of the organization that minted them.

### 5.2 Identifier rules

Every instance **MUST** carry a URI of the form `https://w3id.org/marsad/id/{class-token}/{opaque}` where `{opaque}` is a 22-character base58 string derived from a random 128-bit value.

1. Identifiers **MUST** be opaque. They **MUST NOT** encode names, dates, transliterations or source references. A URI containing `abu-bakr` is an assertion about identity, and identity is a ⟨scholar⟩ decision that may later be revised.
2. Identifiers **MUST NOT** be reused, reassigned or deleted. Retraction is an event; the URI persists and resolves to a tombstone recording what happened.
3. Identifiers **MUST** be minted by the canonical log, never by a client.
4. Where an external authority provides an identifier (Pleiades, Wikidata, al-Ṯurayyā, OpenITI, VIAF), it **MUST** be recorded via `mrs:externalIdentifier` — as alignment, never as the primary key.

### 5.3 Versioning of the ontology itself
`major.minor.patch`. A **major** increment may remove or redefine a class or property; a **minor** increment adds; a **patch** corrects documentation only. Every published corpus release **MUST** declare the ontology version it validates against. Removed terms **MUST** be retained as `owl:deprecated` with `mrs:supersededBy`, permanently.

## 6. Standards alignment

**CIDOC-CRM 7.1.3** (ISO 21127; 81 classes, 160 properties; February 2024) is adopted as the upper ontology. It is *event-centric by construction* — modelling the world as events in which entities participate — which is precisely the reification pattern C2 requires. Alignment buys interoperability with the museum, archive and digital-humanities ecosystem, and credibility with the institutions this project must eventually federate with.

| Our concept | Alignment | Extension required |
|---|---|---|
| Person | `crm:E21_Person` | Arabic name structure; ṭabaqa; transmitter role |
| Group / Tribe / Family | `crm:E74_Group` | Segmentary nesting; temporal membership |
| Place | `crm:E53_Place` | Name-phases; multiple time-bounded geometry states |
| Event | `crm:E5_Event` | Hijri dating; attestation-set linkage |
| Birth / Death | `crm:E67_Birth` / `crm:E69_Death` | Uncertainty-bearing dates |
| Evaluation | `crm:E13_Attribute_Assignment` | Grade vocabulary scoped per tradition |
| Identity decision | `crm:E13_Attribute_Assignment` | Merge/split with reasoning |
| Report text | `crm:E33_Linguistic_Object` | — |
| Work / Recension / Edition / Witness | `lrmoo:F1` / `F2` / `F3` / `F5` | — |
| Passage | `crm:E33_Linguistic_Object` | Canonical citation locus |
| Extraction provenance | `prov:Activity` + `prov:qualifiedAssociation` | Model id and version |
| **Report (Khabar)** | *no adequate anchor* | **New: `mrs:Report`** |
| **Isnād** | *no adequate anchor* | **New: `mrs:TransmissionChain`** |
| **Reified relationship** | *partial* | **New: `mrs:Relationship`** |

**On the three gaps.** CIDOC-CRM has no concept of a *transmitted report whose chain of custody is itself the object of scholarly assessment*. This is not an oversight in CRM; it is a genuine structural feature of Islamic historiography with no close equivalent in the European museum tradition CRM was designed around. These three classes are the ontology's substantive contribution, and they are where reviewer attention should concentrate.

**Dual serialization.** The canonical store is relational. The system publishes both an RDF/CIDOC-CRM projection (for linked-open-data interoperability) and a labelled-property-graph projection (for traversal and GraphRAG tooling). Neither is the source of truth, so neither constrains the other.

## 7. Structured value types

These are not classes of historical things. They are the compound values that make honesty possible, and they are specified first because everything else depends on them.

### 7.1 `mrs:TemporalExtent` — the four-corner model

```turtle
mrs:TemporalExtent a owl:Class .
```

| Property | Range | Card. | Notes |
|---|---|---|---|
| `mrs:calendar` | `mrs:Calendar` (skos) | 1 | `hijri` \| `julian` \| `gregorian` \| `seleucid` \| `regnal` \| `unknown` |
| `mrs:nativeValue` | `xsd:string` | 1 | Verbatim as the source states it. **MUST NOT** be normalized |
| `mrs:earliestStart` | `xsd:dateTime` | 0..1 | ┐ |
| `mrs:latestStart` | `xsd:dateTime` | 0..1 | │ the four corners |
| `mrs:earliestEnd` | `xsd:dateTime` | 0..1 | │ |
| `mrs:latestEnd` | `xsd:dateTime` | 0..1 | ┘ |
| `mrs:precision` | `mrs:Precision` | 1 | `day` \| `month` \| `year` \| `decade` \| `generation` \| `period` \| `unknown` |
| `mrs:temporalBasis` | `mrs:TemporalBasis` | 1 | `attested` \| `inferred` \| `computed` \| `conventional` \| `disputed` |
| `mrs:conversionMethod` | `xsd:string` | 0..1 | REQUIRED when corners are present and `calendar` ≠ the corners' calendar |
| `mrs:conversionUncertaintyDays` | `xsd:integer` | 0..1 | REQUIRED alongside `conversionMethod` |
| `mrs:relativeAnchor` | `mrs:RelativeAnchor` | 0..n | See §7.2 |
| `mrs:attestedBy` | `mrs:Assertion` | 0..n | |

**Constraints.**
- A `TemporalExtent` **MUST** have at least one of: a populated corner, or a `relativeAnchor`. An extent with neither is meaningless and **MUST** be rejected.
- `earliestStart ≤ latestStart`, `earliestEnd ≤ latestEnd`, `earliestStart ≤ latestEnd`.
- `precision` **MUST NOT** be finer than the source supports. Asserting `day` precision where the source says "in that year" is a fabrication and is the single most common data-entry error this specification exists to prevent.

**On calendar conversion.** Hijri↔Gregorian conversion is not a pure function: tabular Islamic calendars and actual lunar sighting diverge by a day or more, regionally and by year, and proleptic Gregorian choices add further offset. Implementations **MUST** store the native value, **MUST** convert at query time rather than at ingestion, and **MUST** carry `conversionUncertaintyDays`. **⟨scholar⟩** — the conversion convention adopted for a given corpus region and period is a scholarly decision and **MUST** be recorded as such.

### 7.2 `mrs:RelativeAnchor`
A large fraction of Seerah and early-Islamic chronology is relational, not absolute.

| Property | Range | Card. |
|---|---|---|
| `mrs:allenRelation` | `time:` relation | 1 |
| `mrs:anchorTarget` | `mrs:Entity` | 1 |
| `mrs:attestedBy` | `mrs:Assertion` | 1..n |

Permitted relations are the thirteen Allen interval relations, expressed through OWL-Time: `time:before`, `time:after`, `time:meets`, `time:metBy`, `time:overlaps`, `time:overlappedBy`, `time:during`, `time:contains`, `time:starts`, `time:startedBy`, `time:finishes`, `time:finishedBy`, `time:equals`.

Implementations **SHOULD** run a temporal constraint solver over the anchor network to propagate bounds, and **MUST** surface detected inconsistencies — sets of assertions that cannot all hold — rather than silently selecting among them. Detected inconsistency is a research finding, not an error to suppress.

### 7.3 `mrs:GeometryState`
A place is a named concept with a history, not a coordinate.

| Property | Range | Card. | Notes |
|---|---|---|---|
| `mrs:geometry` | `geo:Geometry` | 0..1 | **Absent is valid and common** — see below |
| `mrs:locationConfidence` | `mrs:LocationConfidence` | 1 | `certain` \| `probable` \| `approximate` \| `disputed` \| `unlocated` |
| `mrs:validExtent` | `mrs:TemporalExtent` | 1 | When this geometry held |
| `mrs:geometryBasis` | `mrs:GeometryBasis` | 1 | `archaeological` \| `textual` \| `traditional` \| `inferred` \| `modern_identification` |
| `mrs:attestedBy` | `mrs:Assertion` | 0..n | |

`locationConfidence = unlocated` with no geometry **MUST** be supported as a first-class state. A great many toponyms in classical sources are named but not securely identified; a model that forces a coordinate produces a map that lies.

### 7.4 `mrs:ArabicNameForm`
Person identity in the Arabic biographical corpus is the hardest data problem in this project (see §8.2). The name structure is specified in full because collapsing it to a display string destroys the evidence on which disambiguation depends.

| Property | Range | Card. | Notes |
|---|---|---|---|
| `mrs:ism` | `xsd:string` | 0..1 | Muḥammad |
| `mrs:kunya` | `xsd:string` | 0..1 | Abū ʿAbd Allāh |
| `mrs:nasab` | `rdf:List` of `xsd:string` | 0..1 | **Ordered** patronymic chain |
| `mrs:laqab` | `xsd:string` | 0..n | al-Ṣiddīq |
| `mrs:nisba` | `mrs:Nisba` | 0..n | Typed — see below |
| `mrs:fullFormAsAttested` | `xsd:string` | 0..1 | Verbatim, per source |
| `mrs:script` | `xsd:string` | 1 | `arab` \| `latn` |
| `mrs:transliterationScheme` | `xsd:string` | 0..1 | REQUIRED when `script = latn` |
| `mrs:attestedIn` | `mrs:Passage` | 0..n | |

`mrs:Nisba` carries `mrs:nisbaValue` and `mrs:nisbaType` ∈ {`tribal`, `geographic`, `occupational`, `doctrinal`, `patronal`}. The distinction matters: `al-Qurashī` and `al-Baṣrī` and `al-Ḥanafī` are three different kinds of claim about a person, and a system that treats them as interchangeable strings cannot use them for disambiguation.

A `Person` **MAY** hold many `ArabicNameForm`s, each attested in a different source. The system **MUST NOT** derive a single canonical display name automatically where forms conflict. **⟨scholar⟩**

### 7.5 `mrs:ConfidenceBand`
Derived, never authored. Bands, not scores.

`attested` · `well_attested` · `classical_report` · `contested` · `weakly_attested` · `unattested`

A numeric confidence value **MUST NOT** appear anywhere in the published model. A float implies a measurement precision that does not exist and invites arithmetic across incommensurable evidence. Every band **MUST** be accompanied by `mrs:confidenceDecomposition` naming the inputs that produced it: attestation count, chain continuity, evaluation set within the active lens, independent corroboration, attestation gap, and dispute status.

**Bands are computed within a declared `mrs:Tradition` lens and are meaningless without it.** See §8.5.

## 8. Class specification

Each class gives: definition, alignment, required properties, and the scholarly notes that a reviewer should attack.

### 8.1 Base contract
Every instance of `mrs:Entity` — the root class — **MUST** carry:

| Property | Range | Card. | Notes |
|---|---|---|---|
| `mrs:coverageState` | `mrs:CoverageState` | 1 | `stub` \| `outline` \| `sourced` \| `reviewed` \| `verified` |
| `mrs:createdBy` / `mrs:revisedBy` | `prov:Agent` | 1 / 0..n | Signed |
| `mrs:validFrom` / `mrs:recordedAt` | `xsd:dateTime` | 1 / 1 | Bitemporal audit |

`coverageState = stub` is expected to be the majority state of any mature corpus — a name encountered in a chain, nothing more. Stubs **MUST** be visually distinguishable from verified entities at every interface tier. Pretending otherwise is the characteristic failure of ambitious history databases.

### 8.2 `mrs:Person` ⊑ `crm:E21_Person`

| Property | Range | Card. |
|---|---|---|
| `mrs:nameForm` | `mrs:ArabicNameForm` | 1..n |
| `mrs:tabaqa` | `mrs:Tabaqa` | 0..1 |
| `mrs:companionStatus` | `mrs:CompanionStatus` | 0..1 |
| `mrs:birth` / `mrs:death` | `crm:E67_Birth` / `crm:E69_Death` | 0..1 |
| `mrs:floruit` | `mrs:TemporalExtent` | 0..1 |
| `mrs:placeAffiliation` | `mrs:PlaceAffiliation` | 0..n |
| `mrs:transmitterRole` | `mrs:TransmitterRole` | 0..1 |
| `mrs:identityAssertion` | `mrs:IdentityAssertion` | 0..n |

`mrs:Tabaqa` ∈ {`sahabi`, `tabii`, `tabi_al_tabiin`, `generation_n`, `unclassified`}. This is the tradition's own stratification and is used as the origin of the generational coordinate frame.

**`mrs:companionStatus` is contested in a substantial number of cases** and therefore carries its own attestation set and may carry a `mrs:Dispute`. It **MUST NOT** be inferred from date overlap alone. **⟨scholar⟩**

`mrs:PlaceAffiliation` is a reified, temporally bounded, individually evidenced association: `{ place, affiliationType ∈ (born|resided|died|buried|taught|studied|governed), extent, attestedBy }`. A person's city is not a fact about the person; it is a fact about a period of their life.

#### The three identity rules — normative
1. **Automated processes MUST NOT merge `Person` instances.** Homonymy is pervasive; *ʿilm al-rijāl* exists largely because of it, and narrator disambiguation remains an open research problem in the published literature. Automated matching **MAY** propose only.
2. **Automated processes MUST NOT split a `Person` instance.** The inverse error is equally damaging and less visible.
3. **Every merge or split MUST be recorded as an `mrs:IdentityAssertion`** with its reasoning and its author, and **MUST** be reversible without corrupting downstream references. **⟨scholar⟩**

### 8.3 `mrs:Report` ⊑ `crm:E33_Linguistic_Object` — *the primitive*

| Property | Range | Card. | Notes |
|---|---|---|---|
| `mrs:matnText` | `rdf:langString` | 1 | Arabic, as attested in a specific witness |
| `mrs:textVariant` | `mrs:TextVariant` | 0..n | Per-witness variation with apparatus |
| `mrs:translation` | `mrs:Translation` | 0..n | Attributed and versioned — §8.9 |
| `mrs:hasChain` | `mrs:TransmissionChain` | 0..n | **0 is valid** — see below |
| `mrs:terminalAscription` | `mrs:Ascription` | 1 | `marfu` \| `mawquf` \| `maqtu` \| `other` \| `none` |
| `mrs:locatedIn` | `mrs:Passage` | 1..n | Where this report is found |
| `mrs:sourceDate` | `mrs:TemporalExtent` | 1 | **When the containing work was composed** — D6 |
| `mrs:asserts` | `mrs:Assertion` | 0..n | |
| `mrs:memberOfCluster` | `mrs:ReportCluster` | 0..n | |
| `mrs:reportGenre` | `mrs:ReportGenre` | 1 | `hadith` \| `sira_maghazi` \| `tabaqat` \| `tarikh` \| `adab` \| `other` |

**`mrs:hasChain` has minimum cardinality 0, deliberately.** A large proportion of sīra-maghāzī material is transmitted without an isnād meeting ḥadīth criteria, and was not intended by its compilers to meet them. A model requiring a chain would either exclude most of the Seerah corpus or invite fabricated chains. Both outcomes are worse than the honest one.

**`mrs:reportGenre` is normative, not descriptive.** It governs which evidence vocabulary applies. Applying ṣaḥīḥ/ḍaʿīf grading to `sira_maghazi` material misrepresents both the material and the tradition's handling of it; the model prevents this by scoping grade vocabularies to genre and tradition (§8.5).

**`mrs:attestationGap` is computed, never stored**: `sourceDate − assertedEventDate`. It is among the most informative numbers in the corpus and is surfaced directly in the interface. A claim about 1 AH first attested in a work composed in 220 AH has a 219-year gap, and a non-specialist is entitled to know that without having to ask.

`mrs:Hadith` ⊑ `mrs:Report` is defined as a `Report` with `terminalAscription = marfu`. It is a convenience subclass and carries no additional properties.

### 8.4 `mrs:TransmissionChain` (Isnād) and `mrs:TransmissionLink`

```
TransmissionChain
  mrs:hasLink        → mrs:TransmissionLink    1..n   ordered
  mrs:collector      → mrs:Person              0..1
  mrs:continuity     → mrs:Continuity          0..1   ⟨scholar⟩
  mrs:terminalNarrator → mrs:Person            0..1
```
```
TransmissionLink
  mrs:linkOrder      → xsd:integer             1
  mrs:fromNarrator   → mrs:Person              1
  mrs:toNarrator     → mrs:Person              1
  mrs:transmissionMode → mrs:TransmissionMode  1
  mrs:contactCheck   → mrs:ContactCheck        0..1   computed
```

`mrs:TransmissionMode` ∈ {`sama`, `qiraa`, `ijaza`, `munawala`, `wijada`, `anana`, `unspecified`}.
`mrs:Continuity` ∈ {`muttasil`, `munqati`, `mudal`, `muallaq`, `mursal`}.

**`mrs:continuity` is a ⟨scholar⟩ determination and MUST NOT be computed.** This is the sharpest boundary in the specification.

**`mrs:contactCheck` is computed and is not a grading.** Because every narrator carries dates and place affiliations, the system can automatically evaluate, for each adjacent pair, whether a meeting is chronologically and geographically plausible — the classical *liqāʾ / muʿāṣara* analysis, executed continuously across the whole corpus:

```
ContactCheck
  mrs:checkResult   ∈ { plausible | implausible | indeterminate }
  mrs:checkBasis    ∈ { lifespan_overlap | place_overlap | both | insufficient_data }
  mrs:computedAt    → xsd:dateTime
  mrs:corpusVersion → xsd:string
```

An implementation **MUST NOT** present a `contactCheck` result as a judgement on a chain's authenticity, and **MUST NOT** allow it to influence a derived confidence band. It is a flag raised for specialist attention. The system flags; the scholar rules.

### 8.5 `mrs:Evaluation` ⊑ `crm:E13_Attribute_Assignment`

This class is the structural expression of C3 and the reason the corpus can serve multiple traditions.

| Property | Range | Card. |
|---|---|---|
| `mrs:evaluator` | `prov:Agent` | 1 |
| `mrs:evaluationTarget` | `mrs:Report` \| `mrs:TransmissionChain` \| `mrs:Person` \| `mrs:Assertion` | 1 |
| `mrs:grade` | `skos:Concept` | 1 |
| `mrs:gradeScheme` | `skos:ConceptScheme` | 1 |
| `mrs:tradition` | `mrs:Tradition` | 1 |
| `mrs:justification` | `xsd:string` | 0..1 |
| `mrs:locatedIn` | `mrs:Passage` | 1 |
| `mrs:evaluationDate` | `mrs:TemporalExtent` | 0..1 |

**Normative constraints:**
- An `Evaluation` **MUST** identify its evaluator and **MUST** cite the locus where the evaluation is recorded. An uncited grade is not admissible.
- Grades **MUST** be drawn from a `skos:ConceptScheme` scoped to a single `mrs:Tradition`.
- **Grade concepts from different traditions MUST NOT be declared `skos:exactMatch`.** Sunni ḥadīth grading, Twelver Shia grading (with a different rijāl basis) and academic historical-critical assessment are different epistemic systems. `skos:relatedMatch` **MAY** be asserted with explicit scholarly justification. **⟨scholar⟩**
- Implementations **MUST NOT** compute a grade, normalize grades to a numeric scale, or aggregate grades across traditions.

`mrs:Tradition` is an instance-level vocabulary: `sunni_hadith`, `twelver_shia_hadith`, `ibadi`, `zaydi`, `academic_historical`, and others as the corpus extends. **⟨scholar⟩** — which traditions the corpus represents, and which is the declared default, is a governance decision (see [06 §9](06-scholarly-methodology.md)), not an engineering one.

### 8.6 `mrs:Relationship` — the reified connection

| Property | Range | Card. |
|---|---|---|
| `mrs:relationType` | `mrs:RelationType` | 1 |
| `mrs:hasParticipation` | `mrs:Participation` | **2..n** |
| `mrs:relTemporalExtent` | `mrs:TemporalExtent` | 0..1 |
| `mrs:relSpatialExtent` | `mrs:Place` \| `mrs:Route` | 0..1 |
| `mrs:contextEvent` | `mrs:Event` | 0..n |
| `mrs:attestedBy` | `mrs:Assertion` | **1..n** |
| `mrs:hasFacet` | `mrs:Relationship` | 0..n |
| `mrs:dispute` | `mrs:Dispute` | 0..1 |
| `mrs:confidenceBand` | `mrs:ConfidenceBand` | 0..1 (derived) |

`mrs:Participation` binds `{ mrs:participant → mrs:Entity, mrs:participantRole → mrs:Role }`.

**Participation is n-ary, not binary.** Binary edges cannot express "A and B concluded a treaty in the presence of C, mediated by D" without a decomposition that loses the event's unity. Treaties, battles, delegations, teaching sessions and marriages are all naturally n-ary.

**`mrs:attestedBy` has minimum cardinality 1.** A relationship with no attestation **MUST NOT** exist. This is the model's most important single constraint and is enforced in SHACL.

#### Facets — why "friend" is a category error
A relationship aggregates the concrete, individually-evidenced interactions that constitute it. The connection between the Prophet ﷺ and Abū Bakr رضي الله عنه is not a labelled line; it is a composite object:

```
Relationship
  ├─ facet: kinship          father-in-law-of
  ├─ facet: precedence       among the earliest to accept Islam   → Dispute
  ├─ facet: companionship    ṣuḥba, ~23 years                     → 400+ assertions
  ├─ facet: co_travel        Hijrah: Thawr → Qubāʾ                → Event, Route, Qurʾānic context
  ├─ facet: delegation       led the Ḥajj of 9 AH
  ├─ facet: trust            entrusted with prayer leadership     → Dispute (interpretive)
  └─ facet: transmission     narrated_from ×N                     → into the isnād layer
```

Each facet is itself an `mrs:Relationship` with its own extent, evidence and disputes. Selecting the connection in the interface opens *the relationship as a place*, with its own timeline, map and evidence set.

### 8.7 `mrs:Dispute` and `mrs:Position`

| Property | Range | Card. |
|---|---|---|
| `mrs:disputeSubject` | `mrs:Entity` | 1 |
| `mrs:disputeQuestion` | `xsd:string` | 1 |
| `mrs:hasPosition` | `mrs:Position` | **2..n** |
| `mrs:disputeSignificance` | `mrs:Significance` | 1 |
| `mrs:disputeStatus` | `mrs:DisputeStatus` | 1 |

`mrs:Position` carries `{ positionClaim, proponent 1..n, positionEvidence 0..n, positionReasoning, tradition, era }`.

`mrs:Significance` ∈ {`factual`, `chronological`, `interpretive`, `juristic`, `theological`}.

**Normative handling by significance:**

| Significance | System behaviour |
|---|---|
| `factual` | Positions with attestation; relative evidentiary weight **MAY** be shown within a declared lens |
| `chronological` | The contested interval **MUST** render as contested; the system **MUST NOT** silently select a date |
| `interpretive` | Positions presented; **no computation** |
| `juristic` | Positions with attribution; **no computed weighting; no default** |
| `theological` | Positions with attribution; **no computation, no default, no ranking.** The system explicitly declines to adjudicate |

The last two rows are enforced in SHACL: a `Dispute` with `significance ∈ {juristic, theological}` **MUST NOT** carry a `confidenceBand` on any of its positions. This is a schema-level prohibition rather than an editorial guideline, because editorial guidelines erode.

### 8.8 `mrs:Place`, `mrs:Route`, `mrs:RouteSegment`

```
Place ⊑ crm:E53_Place
  mrs:namePhase      → mrs:NamePhase      1..n    { name, language, script, extent, attestedBy }
  mrs:geometryState  → mrs:GeometryState  0..n    §7.3
  mrs:placeType      → mrs:PlaceType      1
  mrs:within         → mrs:Place          0..n    temporally bounded
  mrs:externalIdentifier → xsd:anyURI     0..n    Pleiades | al-Ṯurayyā | WHG | Wikidata
```

`namePhase` is `1..n` because Yathrib and al-Madīna are the same place under different names in different periods, and conflating them loses the historical fact that the name changed.

```
Route
  mrs:hasSegment     → mrs:RouteSegment   1..n    ordered

RouteSegment
  mrs:segmentOrder   → xsd:integer        1
  mrs:segmentFrom / mrs:segmentTo → mrs:Place | geo:Geometry   1 / 1
  mrs:segmentGeometry → geo:Geometry      0..1
  mrs:segmentConfidence → mrs:SegmentConfidence  1   attested | probable | conjectural | unknown
  mrs:traversal      → mrs:TemporalExtent 0..1
  mrs:travelMode     → mrs:TravelMode     0..1
  mrs:attestedBy     → mrs:Assertion      0..n
```

**Segment-level confidence is mandatory and is the model's most visible act of honesty.** The Hijrah is not a line from Makkah to Madinah; it is a deliberately indirect path with a southward feint, a cave interval, a guide engaged for the coastal route, and named waypoints of varying attestation. Modelling it as an endpoint-to-endpoint line would erase the entire historical content of the event and silently assert a path nobody attests.

Implementations **MUST NOT** interpolate a continuous geometry across segments whose `segmentConfidence` is `unknown`. Unknown intervals render as breaks. Smoothing a gap into a confident curve is the most common and most invisible falsification in historical cartography.

### 8.9 Sources: the WEMI chain

| Class | Alignment | Example |
|---|---|---|
| `mrs:Work` | `lrmoo:F1_Work` | *al-Sīra* of Ibn Isḥāq, as an abstract composition |
| `mrs:Recension` | `lrmoo:F2_Expression` | Ibn Hishām's recension |
| `mrs:Edition` | `lrmoo:F3_Manifestation` | A modern critical edition |
| `mrs:Witness` | `lrmoo:F5_Item` | A specific manuscript or printed copy |
| `mrs:Passage` | `crm:E33_Linguistic_Object` | A citable locus within a witness or edition |

The four-level distinction is not pedantry. "Ibn Isḥāq says X" is almost always shorthand for "Ibn Hishām's recension of Ibn Isḥāq, in a given edition, at a given page, says X" — and the difference between those two statements is frequently where a historiographic argument lives.

`mrs:Passage` carries `mrs:canonicalCitation` (a stable citation string), `mrs:iiifReference` (0..1, for manuscript imaging) and `mrs:inWitness`.

`mrs:Translation` carries `{ translatedText, translator → prov:Agent (1), reviewer → prov:Agent (0..n), translationVersion, sourcePassage }`. **A `Translation` MUST have a human `translator`.** Machine translation of transmitted material **MUST NOT** be published in any user-facing surface (see [06 §5](06-scholarly-methodology.md)); this is enforced by requiring the translator to be a `prov:Person`, not a `prov:SoftwareAgent`.

### 8.10 `mrs:Assertion` and extraction provenance

| Property | Range | Card. |
|---|---|---|
| `mrs:fromReport` | `mrs:Report` | 0..1 |
| `mrs:nonReportBasis` | `xsd:string` | 0..1 |
| `mrs:predicate` | `mrs:RelationType` | 1 |
| `mrs:assertionSubject` / `mrs:assertionObject` | `mrs:Entity` \| literal | 1 / 1 |
| `mrs:qualifier` | `mrs:Qualifier` | 0..n |
| `mrs:assertionStatus` | `mrs:AssertionStatus` | 1 |
| `prov:wasGeneratedBy` | `prov:Activity` | 1 |

`mrs:AssertionStatus` ∈ {`proposed`, `under_review`, `accepted`, `rejected`, `superseded`}.

Exactly one of `fromReport` or `nonReportBasis` **MUST** be present.

**Extraction provenance is modelled with PROV-O's qualified pattern**, which exists precisely for this:

```turtle
mrsid:assertion/Ab3… prov:wasGeneratedBy mrsid:activity/x7… .
mrsid:activity/x7… a prov:Activity ;
    prov:qualifiedAssociation [
        a prov:Association ;
        prov:agent mrsid:agent/model-v2 ;    # the extraction model
        prov:hadRole mrs:role/extractor ] ;
    prov:qualifiedAssociation [
        a prov:Association ;
        prov:agent mrsid:agent/scholar-14 ;  # the human who accepted it
        prov:hadRole mrs:role/adjudicator ] .
```

Recording the model identity and version is not bureaucratic. **When a model is later found to have a systematic error, every assertion it produced must be locatable for re-review.** Without model provenance, a discovered extraction bug is unrecoverable — you cannot find what it touched.

### 8.11 `mrs:CoverageGap` — modelling what is *not* known

| Property | Range | Card. |
|---|---|---|
| `mrs:gapScope` | `mrs:GapScope` | 1 |
| `mrs:gapDescription` | `xsd:string` | 1 |
| `mrs:gapCause` | `mrs:GapCause` | 1 |
| `mrs:knownSource` | `xsd:string` | 0..n |

`mrs:GapCause` ∈ {`not_yet_ingested`, `sources_lost`, `sources_unavailable`, `sources_unlicensed`, `genuinely_unattested`}.

Absence in a database is read by users as absence in history. That inference is almost always wrong and, applied to whole regions or communities, is sometimes defamatory. `gapCause` carries the weight: "we have not ingested the Andalusian material" and "no source survives" are radically different statements, and the interface **MUST** distinguish them — including in empty search results, which **MUST** report coverage rather than returning nothing.

## 9. The relation registry

Relation types are `skos:Concept` instances in the scheme `mrs:RelationScheme`, each declaring `mrs:inverseRelation`, `mrs:relationClass` and `mrs:symmetric`.

**Kinship** — `father_of`, `mother_of`, `son_of`, `daughter_of`, `sibling_of`, `spouse_of`, `divorced_from`, `paternal_uncle_of`, `maternal_uncle_of`, `cousin_of`, `ancestor_of`, `descendant_of`, `adopted_by`, **`mawla_of`**

> `mawla_of` (client/patron) is structurally essential to early Islamic social history and is frequently mis-modelled as kinship. It is its own relation class, is directional, and is ambiguous in the sources between patron and client direction — which is a ⟨scholar⟩ determination per instance.

**Social & political** — `companion_of`, `ally_of`, `pledged_allegiance_to`, `party_to_treaty_with`, `opposed`, `fought_alongside`, `fought_against`, `captured`, `manumitted`, `protected` (jiwār), `sheltered`, `corresponded_with`, `sent_delegation_to`, `appointed`, `succeeded`, `deposed`

**Transmission** — `narrated_from`, `narrated_to`, `heard_from`, `read_to`, `licensed_by`, `transmitted_book_of`, `taught_at`, `studied_at`, `studied_under`, `authored`, `abridged`, `commented_on`, `refuted`, `transmitted_recension_of`, `influenced`, `cited`

**Spatial & mobility** — `born_at`, `died_at`, `buried_at`, `resided_in`, `migrated_from`, `migrated_to`, `travelled_via`, `visited`, `governed`, `besieged`, `founded`, `rebuilt`, `endowed`

**Participation** — `participated_in`, `led`, `witnessed`, `present_at`, **`absent_from`**, `occurred_at`, `occurred_during`, `preceded`, `followed`, `concurrent_with`, `caused`, `responded_to`

> `absent_from` is modelled explicitly because absence is frequently the historically contested claim, and a model that can only record presence cannot represent the dispute.

**Textual & evidentiary** — `mentioned_in`, `subject_of`, `attested_by`, `contradicted_by`, `corroborated_by`, `variant_of`, **`abrogates`** ⟨restricted⟩, **`revealed_concerning`** ⟨restricted⟩

> **Restricted relations.** `abrogates` (naskh) and `revealed_concerning` (asbāb al-nuzūl) are juristic determinations, heavily contested, and structurally tempting to over-apply. They **MUST NOT** be asserted by extraction pipelines under any circumstances, **MUST** carry an `Evaluation` from a named authority, and **MUST** be attributed rather than stated. Enforced in SHACL.

**Escape hatch.** `mrs:unclassified_relation` records the intended meaning in free text and enqueues it for ontology review. A schema with no escape hatch produces silent data loss at ingestion; an escape hatch that is never reviewed produces a garbage tier. Both failure modes **MUST** be instrumented, and the size of the unclassified queue **MUST** appear on the corpus health dashboard.

## 10. Integrity constraints

Enforced in the database and in SHACL, not in application code.

| # | Constraint | Rationale |
|---|---|---|
| I1 | No `Relationship` without ≥1 `Assertion` | The model's core discipline |
| I2 | No `Assertion` without a `Report` **xor** a recorded non-report basis | No orphan claims |
| I3 | No `Evaluation` without an identified evaluator **and** a citable locus | Uncited grades inadmissible |
| I4 | No `TemporalExtent` narrower than its evidence supports | Precision is a claim requiring warrant |
| I5 | No hard deletion of any entity | Retraction is an event; the record persists |
| I6 | `Translation` of transmitted material requires a human translator | Policy, enforced structurally |
| I7 | Restricted relations require an `Evaluation`; never machine-asserted | §9 |
| I8 | `Dispute` with juristic/theological significance carries no confidence band | §8.7 |
| I9 | Grade concepts across traditions never `skos:exactMatch` | §8.5 |
| I10 | `contactCheck` never contributes to a derived confidence band | §8.4 |
| I11 | Every `Person` merge/split has an `IdentityAssertion` with a human author | §8.2 |
| I12 | Instance URIs never encode names, dates or transliterations | §5.2 |

I4 and I12 cannot be fully expressed in SHACL and **MUST** be enforced at ingestion.

## 11. Worked example — the shelter at Thawr

*Illustrative. The chain and dates below are given to demonstrate the model's shape and **have not been scholar-verified**; under this specification they would carry `assertionStatus = proposed` and `coverageState = outline` until adjudicated. Demonstrating that distinction is part of the example.*

Full Turtle: [`ontology/examples/thawr.ttl`](../ontology/examples/thawr.ttl).

```
EVENT  mrsid:event/7Fq…  "Sheltering at Ghār Thawr"
  ├─ type            mrs:Event
  ├─ participation   { Prophet ﷺ, role: principal }
  │                  { Abū Bakr رضي الله عنه, role: companion }
  ├─ place           mrsid:place/Th2…  Ghār Thawr
  │                    namePhase   "غار ثور" @ar
  │                    geometry    Point(…)   confidence: probable
  │                                            basis: traditional
  │                                            ⟨scholar⟩ modern identification
  ├─ temporalExtent  calendar:    hijri
  │                  nativeValue: "ثلاث ليال"  ("three nights")
  │                  precision:   day
  │                  basis:       attested
  │                  relativeAnchor: { after,  departure from Makkah }
  │                                  { before, arrival at Qubāʾ }
  │                  ⟨scholar⟩ absolute corners disputed → Dispute/Chr-04
  └─ attestedBy      → Assertion/A1, A2, A3
```

The assertion and its warrant:

```
ASSERTION  mrsid:assertion/A1
  predicate     mrs:sheltered_at
  subject       Prophet ﷺ          object  Ghār Thawr
  fromReport    mrsid:report/B-3905
  status        proposed
  wasGeneratedBy  Activity → { agent: extraction-model-v2, role: extractor }
                             ⟨awaiting adjudicator⟩

REPORT  mrsid:report/B-3905
  reportGenre       hadith
  terminalAscription mawquf          ⟨scholar⟩ classification of this matn
  sourceDate        hijri, d. 256 AH  (composition of the containing work)
  locatedIn         Passage → Witness → Edition → Recension → Work
  hasChain          mrsid:chain/C-1
  attestationGap    computed: ~255 years   ← surfaced in the interface

CHAIN  mrsid:chain/C-1
  link 1  ʿĀʾisha رضي الله عنها (d. 58)  →  ʿUrwa b. al-Zubayr (d. 94)   mode: sama
          contactCheck: plausible  [lifespan_overlap + place_overlap]
  link 2  ʿUrwa (d. 94)      →  Ibn Shihāb al-Zuhrī (d. 124)             mode: sama
          contactCheck: plausible  [both]
  link 3  al-Zuhrī (d. 124)  →  ʿUqayl b. Khālid (d. 144)                mode: sama
          contactCheck: plausible  [both]
  link 4  ʿUqayl (d. 144)    →  al-Layth b. Saʿd (d. 175)                mode: sama
          contactCheck: plausible  [both]
  link 5  al-Layth (d. 175)  →  Yaḥyā b. Bukayr (d. 231)                 mode: sama
          contactCheck: plausible  [both]
  continuity  ⟨scholar⟩  — NOT computed, NOT inferred from the checks above

EVALUATION  mrsid:eval/E-1
  evaluator    al-Bukhārī (d. 256)
  target       Report/B-3905
  grade        sahih         scheme: sunni_hadith_grades
  tradition    sunni_hadith
  locatedIn    Passage/…     ← the locus in the Ṣaḥīḥ
  basis        inclusion in the Ṣaḥīḥ    ⟨scholar⟩ whether inclusion constitutes
                                          an explicit grading is itself a position
```

Note what the model refuses to do. Five contact checks return `plausible`, and the chain's `continuity` remains **unset**, awaiting a scholar. The system has assembled every input a specialist would want and has declined to draw the conclusion. That refusal is the specification's central behaviour, and if it is ever relaxed the corpus loses its authority.

And a dispute, preserved rather than resolved:

```
DISPUTE  mrsid:dispute/D-11
  question       "Who brought provisions to the cave, and on whose instruction?"
  significance   factual
  status         open
  position 1     ʿAbd Allāh b. Abī Bakr      proponents […]  evidence […]
  position 2     Asmāʾ bint Abī Bakr         proponents […]  evidence […]
  position 3     ʿĀmir b. Fuhayra            proponents […]  evidence […]
  ⟨scholar⟩      positions are not mutually exclusive; the model does not assume they are
```

## 12. Governance of the ontology

| Change | Authority | Process |
|---|---|---|
| New instance of an existing class | Contributor | Standard review |
| New relation type | Editor | Ontology review queue; published in a minor release |
| New class | Board + ≥2 external specialists | Major or minor release with a public comment period |
| Change to a ⟨scholar⟩ boundary | **Board only** | Public justification required |
| Change to an integrity constraint (§10) | **Board only** | Public justification required |
| New `Tradition` or grade scheme | **Board only** | Requires a qualified representative of that tradition |

Ontology changes **MUST** be versioned, **MUST** carry migration notes, and **MUST NOT** silently alter the meaning of existing data.

## 13. Scope of version 0.1

**Specified normatively:** `Entity`, `Person`, `ArabicNameForm`, `Nisba`, `PlaceAffiliation`, `Report`, `Hadith`, `TransmissionChain`, `TransmissionLink`, `ContactCheck`, `Assertion`, `Evaluation`, `Dispute`, `Position`, `ReportCluster`, `IdentityAssertion`, `CoverageGap`, `Relationship`, `Participation`, `Event`, `Journey`, `Place`, `NamePhase`, `GeometryState`, `Route`, `RouteSegment`, `Work`, `Recension`, `Edition`, `Witness`, `Passage`, `Translation`, `TextVariant`, `TemporalExtent`, `RelativeAnchor`, `Tradition`, plus the vocabularies.

**Reserved — URIs minted, definitions deferred:** `Institution`, `Dynasty`, `Polity`, `Territory`, `Concept`, `IntellectualMovement`, `Structure`, `QuranicPassage`, `TeachingEvent`, `Battle`, `Treaty`, `Period`.

Reserving the URI now prevents a future collision; specifying the class now would mean specifying things nobody will implement for two years, and they would be wrong by then.

## 14. Where this specification is most likely wrong

Offered to reviewers as a starting point for attack, because a spec that does not name its weak points wastes the reviewer's time finding them.

1. **`Report` as `crm:E33_Linguistic_Object`** may be the wrong CRM anchor. A report is arguably closer to a *transmission event* than to a linguistic object, and a CRM specialist may well prefer the event modelling.
2. **`terminalAscription` as a single value** may be inadequate. A matn with mixed ascription — partly prophetic, partly the narrator's comment (*mudraj*) — is common, and the model currently forces one classification per report.
3. **`ReportCluster` is underspecified.** The distinction between *mutābaʿāt* and *shawāhid* is not yet modelled, and it matters for corroboration.
4. **Genre boundaries leak.** `reportGenre` treats sīra, ḥadīth and tārīkh as disjoint, and the same report frequently appears across all three with different apparatus.
5. **`Tabaqa` as a flat vocabulary** ignores that the classical *ṭabaqāt* works subdivide generations considerably, and that assignment is itself contested.
6. **The `mawlā` direction problem** may require its own class rather than a directional relation.
7. **`PlaceAffiliation` may be too coarse** for narrators who moved repeatedly, which is most of the interesting ones.
8. **Shia rijāl integration is asserted but not designed.** The model claims tradition-scoping supports it; whether it actually does requires a specialist in Twelver rijāl to confirm, and that review has not happened.

---

**Next:** [03 — Technical Architecture](03-technical-architecture.md)
