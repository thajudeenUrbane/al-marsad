# 06 — Scholarly Methodology

This document governs the others. Where it conflicts with a technical, visual or product decision, it wins.

---

## 1. The epistemic stance

The system takes a deliberately **narrow** epistemic role, and stating its limits precisely is what makes the broad claims defensible.

**What the system does:**
- Records what sources say, with their chains, their locations and their variants.
- Records what named authorities have concluded about those sources, with their reasoning.
- Records where authorities disagree, and who holds which position.
- Computes structural properties of the record — attestation counts, chain continuity, contact plausibility, temporal consistency, coverage.
- Makes all of this observable, navigable and citable.

**What the system does not do:**
- Grade ḥadīth. It records gradings made by qualified humans.
- Adjudicate between scholarly positions. It presents them with their evidence.
- Issue rulings, interpret scripture, or determine doctrine.
- Assign religious, moral or spiritual rank to any person.
- Determine what is "really" true where the tradition is divided.

The distinction matters because the system's authority derives entirely from its **transparency**, never from its conclusions. It is an instrument. Instruments that begin issuing verdicts stop being trusted by the specialists whose participation they require.

---

## 2. Evidence classification

### 2.1 The eight states a claim can occupy
Required by the brief and made structural here. Note that these are **derived bands within a declared tradition-lens**, never global properties of a claim.

| State | Meaning | Renders as |
|---|---|---|
| **Established** | Multiply and independently attested; no substantive dispute | Crisp, full opacity |
| **Well-attested** | Strong attestation; minor variation in detail | Crisp, slight softening |
| **Authentic narration** | Graded authentic by named authorities within the active lens | Crisp, with grading badge |
| **Classical report** | Present in the historical tradition (sīra/maghāzī/ṭabaqāt) without ḥadīth-grade evaluation | Softer edge — *the largest category in the Seerah corpus* |
| **Scholarly interpretation** | An inference or reconstruction by a named scholar, not a transmitted report | Distinct style; attributed inline |
| **Disputed** | Substantive disagreement among authorities | Marked as contested; positions accessible |
| **Weak** | Graded weak by named authorities within the active lens | Heavily softened; grading and grader shown |
| **Unattested / unknown** | No supporting report identified | Rendered as absence, with a coverage note |

**The fourth row deserves emphasis.** A large proportion of Seerah material is *classical historical report* — transmitted in the sīra-maghāzī tradition, often without an isnād meeting ḥadīth criteria, and not intended by its compilers to meet them. Systems that apply a binary ṣaḥīḥ/ḍaʿīf frame to this material misrepresent both the material and the tradition's own handling of it. The corpus must carry this category natively and render it honestly: *this is how the historical tradition transmits it, which is a different kind of warrant from a graded ḥadīth, and it is neither dismissed nor elevated.*

### 2.2 Grading is attributed, always
Restating the architectural rule from [02 §1](02-knowledge-architecture.md), because it is the load-bearing decision of this document:

> There is no field anywhere in this system that holds "the grade of a report."
> There are only records of the form: **this evaluator, in this work, at this location, assigned this grade, for this reason.**

Consequences:
- Al-Tirmidhī's assessment and a modern evaluator's assessment of the same report coexist without contradiction.
- Sunni, Twelver Shia and Ibadi ḥadīth sciences — with different rijāl corpora and different criteria — can all be represented without one being encoded as the default truth.
- Academic historical-critical assessment is a further, separately-labelled tradition, neither privileged nor excluded.
- The user always knows *whose judgement* they are seeing, which is the actual scholarly question.

**Grades are never normalized across traditions into a shared numeric scale.** A `confidence: 0.82` spanning Sunni ḥadīth criticism and academic source criticism would be a fabrication with a decimal point. Confidence is computed *within* a declared lens and displayed as a band.

### 2.3 The tradition lens
An explicit, always-visible control. The system ships with a **declared default** — it cannot avoid having one — and the default must be stated openly rather than smuggled in as neutrality. Switching the lens changes which rijāl corpus, which evaluators and which criteria inform derived confidence. It never changes the underlying reports, which are shared.

Where traditions diverge on *events* rather than on grading — a substantial issue for the period after 11 AH — the divergence is modelled as a `Dispute` with positions attributed to their communities, and rendered as such. **The system does not have a single normative account of contested history, and does not pretend to.**

---

## 3. The verification workflow

```
  SOURCE
    │  licence cleared · provenance recorded
    ▼
  EXTRACTION (AI-assisted)                       status: proposed
    │  model + version recorded on every assertion
    ▼
  TRIAGE                                          Researcher role
    │  obvious errors removed; batched into review units
    ▼
  ADJUDICATION                                    Scholar / Reviewer role
    │  entity identity · relationship validity · dating · placement
    │  diff-based, micro-tasked, batched
    ▼
  EVALUATION                                      Scholar role, by specialism
    │  gradings attached with reasoning and citation
    ▼
  DISPUTE DOCUMENTATION                           Scholar role
    │  disagreements recorded as structured objects, not resolved by fiat
    ▼
  SIGN-OFF                                        credentialed, signed (ijāza)
    │
    ▼
  COMMIT → corpus version → publication → recomputation of derived layers
    │
    └──▶ PUBLIC CORRECTION CHANNEL ──▶ re-enters at TRIAGE
```

**The absolute rule:** nothing moves from `proposed` to published without a credentialed human act, and the record of who performed it persists permanently and publicly.

### 3.1 Roles (the *ijāza* model)
Permissions are scoped by **specialism and period**, not granted globally — mirroring how scholarly authority actually works. A specialist in Andalusian transmission does not thereby acquire authority over Seerah chronology.

| Role | May do | May not do |
|---|---|---|
| **Reader** | Read everything; report errors | Write |
| **Contributor** | Propose entities, relationships, sources | Publish |
| **Researcher** | Ingest sources; triage; prepare review units | Sign off |
| **Reviewer** | Adjudicate within a granted scope | Attach gradings |
| **Scholar** | Attach evaluations; document disputes; sign off within scope | Act outside granted scope |
| **Editor** | Ontology changes; schema evolution; merge adjudication | Override a scholar's evaluation |
| **Translator** | Author and version translations | Alter source text |
| **Board** | Governance; scope grants; policy; naming; representation decisions | Alter the record directly |

Scopes are **granted, time-bounded, publicly listed and revocable** — the *ijāza* pattern implemented as an authorization model. Every grant and revocation is itself a logged event.

### 3.2 Scholar attention is the binding constraint
This is the project's true bottleneck, and it deserves engineering rather than administration. The realistic throughput of qualified scholarly review, measured in assertions per hour, will determine the corpus growth rate more than any technical factor.

Design responses, in order of expected impact:

1. **Micro-tasks, not documents.** A reviewer answers one bounded question at a time, with full context supplied, rather than reading a proposed record end to end.
2. **Batching by similarity.** Fifty instances of the same pattern are adjudicated together; the decision propagates with per-case review of outliers only.
3. **Diff-first review.** Show what changed and why, never the whole object.
4. **Confidence-ranked queues.** Machine-uncertain items reach humans first; high-confidence routine extractions are sampled rather than exhaustively reviewed.
5. **Citable credit, DOIs, and a public contribution ledger.** Scholars must be able to list this work on a CV. A system that consumes expert labour without producing academic credit will not retain experts.
6. **Partial verification is a valid state.** `coverage_state` allows a record to be verified in part. Demanding completeness before publication guarantees nothing is ever published.

---

## 4. Handling disagreement

Disagreement is not a defect in the data. In this domain it is often the most scholarly content available, and it is rendered as such.

```
Dispute
  question       stated precisely, in neutral terms
  positions[]    { claim, proponents[], evidence[], reasoning, tradition, era }
  significance   factual | chronological | interpretive | juristic | theological
  status         open | majority_view_exists | resolved_by_consensus | unresolvable
```

Handling by significance:

| Significance | System behaviour |
|---|---|
| **Factual** (did X occur) | Present positions with attestation; show relative evidentiary weight within the active lens |
| **Chronological** (when) | Render the contested region as contested on the timeline; do not pick a date silently |
| **Interpretive** (what it meant) | Present positions; compute nothing |
| **Juristic** | Present positions with attribution; **no computed weighting**; no default |
| **Theological** | Present positions with attribution; **no computation, no default, no ranking**; the system explicitly declines to adjudicate |

The last two rows are hard boundaries. A confidence score attached to a theological position would be a category error with serious consequences, and the schema forbids it rather than relying on editorial restraint.

**Presentation of contested material at the Explore lens** is a real design problem, not a solved one: a child should not be handed a survey of scholarly controversy, but must also not be told a contested thing is settled. The resolution adopted here: at Explore, contested claims are stated with an honest hedge in plain language — *"reports differ on exactly when this happened"* — with the detail one tap away. Silence is not an option; false confidence is not an option; plain honesty is.

---

## 5. Translation policy

The primary sources are Arabic; the audience is global; machine translation of classical Arabic religious material is unacceptably risky.

- **Arabic is canonical.** Every report's Arabic text is the object of record.
- **Translations are attributed, versioned objects** with a named translator and a reviewer, treated as scholarly contributions in their own right.
- **No machine translation of ḥadīth, Qurʾānic text, or transmitted reports** appears in any user-facing surface. Ever.
- Machine translation *may* assist with descriptive and administrative content, marked as such.
- Multiple translations of the same report coexist; the interface shows which is displayed and by whom it was made.
- Qurʾānic text is **referenced, never re-edited or paraphrased**, and is presented through established published translations with attribution.

---

## 6. Coverage and calibration — publishing the instrument's limits

An observatory that cannot state its own limits is not an instrument. The system publishes, continuously and prominently:

- **A coverage map** — what regions, periods, topics and source-classes are represented, at what depth.
- **Known gaps** with their causes, from the `CoverageGap` objects: not yet ingested / sources lost / unavailable / unlicensed / genuinely unattested.
- **Confidence distribution** across the corpus — what proportion sits in each band.
- **Verification state distribution** — how much is stub, sourced, reviewed, verified.
- **Correction statistics** — how many claims have been revised, and how quickly.
- **Known error rate** on a scholar-adjudicated golden set (§8).

This is uncomfortable information to publish. Publishing it is the single clearest signal that separates an instrument from a marketing surface, and it is what a sceptical scholar will look for first.

---

## 7. The computed-versus-significant boundary

**Network metrics describe the record. They do not describe reality, and they certainly do not describe religious standing.**

Betweenness centrality in a transmission graph measures a person's position in *the surviving, ingested, encoded record of transmission*. It is affected by how much survived, what has been digitized, whose students happened to write, and what this project has so far ingested. It is not a measure of virtue, knowledge, status or importance.

Enforced controls:

1. **No metric is on by default.** Node size encodes nothing until the user chooses a metric.
2. **The metric's name is always displayed** beside any encoding that uses it.
3. **No ranked lists of Companions**, ever, on any computed measure. The system will not produce a "top ten Companions by centrality," and this is a product-level prohibition, not a default setting.
4. **A standing interpretive caveat** accompanies every analytics view, in plain language: *this measures the record, not the reality, and not the person.*
5. **Analytics are gated to the Study and Research lenses**, where users have the context to read them correctly.

The same discipline applies to the Nūr/Nujūm luminance encoding ([01 §5](01-conceptual-model.md)): brightness is transmission distance, it is switchable, and the interface says so wherever it appears.

---

## 8. Quality assurance — how we know the system is right

There is no test suite for history. There are, however, testable proxies, and the project must run them from the beginning.

| Mechanism | What it checks |
|---|---|
| **Golden set** | A few hundred scholar-adjudicated questions with expected evidence sets; run as a regression suite on every corpus release |
| **Adversarial review** | Specialists paid specifically to *break* the corpus in their area of expertise, with findings published |
| **Extraction sampling** | Continuous random audit of AI-proposed assertions; accuracy published by model version |
| **Chain integrity checks** | Automated contact-plausibility and chronological-consistency scanning across the whole corpus; anomalies queued for humans, never auto-resolved |
| **Cross-source consistency** | Detection of claims attested in one source and contradicted in another; surfaced as candidate disputes |
| **Public correction channel** | Open to anyone; tracked with response times; corrections and their resolutions published |
| **Reproducibility checks** | Any cited view re-executed against its pinned version must return identical results |

The golden set is the most important item and the easiest to defer. It should exist before the first public release, because it is the only mechanism that detects *silent regression* — a corpus that quietly gets worse as it grows.

---

## 9. Governance

Whoever controls this corpus controls a widely-consulted account of Islamic history. That is a serious responsibility and a target for capture. Governance is therefore an architectural component, not a formality.

**Principles:**

1. **Cross-tradition board representation.** The scholarly board must include qualified representation across the major traditions whose history this corpus describes. A single-tradition board producing an ostensibly neutral corpus is the most likely failure mode.
2. **Transparent, logged decisions.** Every scope grant, policy decision and dispute resolution is public and attributable.
3. **Forkability as a structural check.** The corpus is openly licensed and fully exportable. If governance is captured, the community can fork it. This is the strongest available guarantee against capture, and it must be real — periodic full public releases, not a promise.
4. **Separation of powers.** The board sets policy and grants scope; it does not edit the record. Scholars edit within scope; they do not set policy. Engineers build; they do not adjudicate content.
5. **Institutional custodianship.** Long-term stewardship by an institution with a horizon measured in decades — a university, a foundation, a consortium. The project should assume its founders will not be the ones maintaining it, and design accordingly. The Venice Time Machine's governance rupture is an instructive precedent: technical success does not survive unresolved institutional arrangements.
6. **Declared defaults.** Wherever the system must choose — a default lens, a default dating convention, a default transliteration — the choice is stated openly rather than presented as neutrality.

---

## 10. Red lines

Non-negotiable. Any of these, if crossed, would justify halting the project rather than shipping.

1. **No AI-generated hadith, or AI-generated text presented as transmitted material.**
2. **No AI grading of authenticity.**
3. **No figurative depiction of the Prophet ﷺ, his family, or the Companions** — in any tier, any medium, any context.
4. **No fatwa, ruling, or doctrinal determination** issued by the system.
5. **No computed ranking of persons by religious significance.**
6. **No presentation of a contested matter as settled.**
7. **No fabricated precision** in a date, a location, a route or a chain.
8. **No silent modification of the record** — every change is logged, attributed and reversible.
9. **No paywall on evidence.** The provenance of a claim is never a premium feature.
10. **No visualization whose warrant cannot be inspected.**

---

**Next:** [07 — AI Architecture](07-ai-architecture.md)
