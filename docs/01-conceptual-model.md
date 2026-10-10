# 01 — Conceptual Model

## 1. The dimensions, stated honestly

The project is framed as **4D**: Entity, Relationship, Space, Time. That framing is correct as a *promise to the user* and it should be kept, because it is comprehensible and it is what the experience feels like.

But the ideal system requires seven dimensions, and the three additional ones are precisely what separate this from a well-made graph application. They must be designed in from the first schema, because none of them can be retrofitted.

### The observable four — what the user moves through

| # | Dimension | The user's question |
|---|---|---|
| **D1** | **Entity** | *What existed?* — people, events, places, books, tribes, institutions, reports, concepts |
| **D2** | **Relation** | *How was it connected?* — and connection is itself an object with its own depth |
| **D3** | **Space** | *Where?* — historical geography, routes, territories, uncertainty of location |
| **D4** | **Time** | *When, and what changed?* — the network as a moving system |

### The epistemic three — what the observable four are rendered *through*

| # | Dimension | The user's question | Why it cannot be retrofitted |
|---|---|---|---|
| **D5** | **Evidence** | *How do we know?* | If facts are stored first and sources attached later, the join is lossy and the grading has nowhere to live. Provenance must be the substrate, not an annotation. |
| **D6** | **Historiographic time** | *When was this recorded, and by whom?* | Every report has two dates — when the event occurred and when the account was written. Collapsing them destroys the ability to study the formation of the record. |
| **D7** | **Interpretation** | *According to which reading?* | Sunni, Shia and Ibadi traditions, madhhabs, and modern historical-critical scholarship differ. A system with one normative narrative baked in cannot later become plural. |

**D6 deserves emphasis: it is the most novel structural element in this architecture.**

Every historical system has event-time. Almost none treats *source-time* as a navigable axis. But in the Islamic case the sources are dense, dated and stratified: Ibn Isḥāq (d. 150/767), Ibn Hishām's recension (d. 218/833), al-Wāqidī (d. 207/822), Ibn Saʿd (d. 230/845), al-Ṭabarī (d. 310/923), and the ḥadīth collections crystallizing across the 3rd century AH. If source-time is a first-class axis, the system gains a capability no existing platform has:

> **You can hold event-time fixed and move source-time — and watch the historical record itself form.**
>
> Set the scene to the Hijrah. Now move the *record* slider from 120 AH to 310 AH. Watch which details enter the tradition when, which reports compound, which chains proliferate, where later sources add specificity that earlier ones lacked. That is not a visualization of history. It is a visualization of *historiography* — and it is a research instrument, not a teaching toy.

This single design decision converts the system from "an atlas of what happened" into "an instrument for studying how we came to know what happened." No competitor does this. It costs almost nothing to store and is impossible to add later.

### Why the dimensions must not be separate screens

The requirement that these interact dynamically rather than living on separate tabs is satisfied by one mechanic, specified fully in [04](04-visualization-architecture.md) and named here because it is conceptual before it is technical:

**Every entity carries multiple coordinate assignments simultaneously** — a network-space position, a geographic position, a temporal position, a generational position — and the view is a continuous *blend* between them. Moving from "network view" to "map view" is not a page change; it is a weighted interpolation in which every object retains its identity and you watch the same population rearrange itself under a different organizing principle.

That is the difference between four dimensions *offered* and four dimensions *integrated*.

## 2. The core inversion: history as a network of reports, not a chain of facts

### What the conventional model does
```
Year → Event → Next Event                    (the timeline model)
Book → Chapter → Page → Paragraph            (the library model)
Fact ← citation                              (the encyclopaedia model)
```
All three share a defect: they present a *settled* account and attach evidence as a courtesy. The evidence cannot be queried, compared, weighed or disagreed with, because it was never modelled as an object.

### What this system does
```
        Report (khabar)  ──transmitted-by──▶  Isnād chain  ──▶  Narrators
             │                                                      │
        asserts                                            (people, places, dates
             │                                              — the same graph)
             ▼
        Assertion  ──about──▶  Entity / Relation / Event
             │
        graded-by ──▶ Evaluation (by a named authority, in a named work)
             │
        clustered-with ──▶ parallel & conflicting reports
             │
             ▼
        Reconstructed historical world  ← what the user sees by default
```

The user still sees "the Hijrah happened in Rabīʿ al-Awwal, year 1 AH." But that statement is now a *derived projection* over an evidentiary base that remains intact underneath it, fully interrogable, honestly marked where the base is thin or contested — and revisable without rewriting the history, because the history was never hard-coded.

**This is the single most consequential decision in the entire architecture.** Everything in [02](02-knowledge-architecture.md) follows from it.

## 3. The isnād as a four-fold object

The second structural insight, and the one that makes the system's ambitions affordable:

An isnād chain — *A ← B ← C ← Companion ← the Prophet ﷺ* — is simultaneously four things, and they are the same data:

| Read as | It yields |
|---|---|
| **An evidentiary chain** | The warrant for a claim; the object of ḥadīth criticism |
| **A social network** | Who taught whom, who met whom, across generations |
| **A geographic diffusion path** | Each narrator has a city; the chain traces knowledge moving Madinah → Kufa → Baghdad → Nishapur → Cordoba |
| **A temporal ordering** | Each narrator has dates; the chain encodes generational sequence, and contact plausibility (*liqāʾ*) is checkable against it |

Therefore: **the knowledge-transmission layer and the evidence layer are not two subsystems. They are one graph read two ways.**

The practical consequence is large. "Is this report well-attested?" and "how did this teaching reach Malabar?" traverse the same edges with different projections. Every unit of scholarly effort spent encoding an isnād pays into four capabilities at once. A system that built transmission and evidence separately would do the work twice and never reconcile them.

Existing systems have each of these halves. Hadith-Viz and the isnād-network literature have chains-as-evidence. Six Degrees of Francis Bacon and Mapping the Republic of Letters have people-as-network. Nobody has fused them into a substrate where the same edge serves both — see [10](10-prior-art-and-novelty.md).

## 4. The observatory metaphor, made rigorous

The metaphor is load-bearing, so it should be stated precisely rather than atmospherically. Five commitments follow from calling this an observatory:

1. **The object precedes the instrument.** The sky is not made by the telescope. Islamic history exists independently of this system; the system's only job is to make it observable without distorting it. Every rendering decision is therefore a *measurement* decision.

2. **Calibration is a public artifact.** Observatories publish their instruments' error characteristics. This system must publish its coverage, its confidence distributions, its known gaps and its error rate — see the coverage map in [06](06-scholarly-methodology.md). A system that cannot state what it does *not* know is not an instrument.

3. **Resolution varies across the field.** Near the centre — the Seerah, the well-attested core — resolution is high. At the periphery — regional histories with sparse sources — it is low, and must *look* low. Uniform visual confidence across non-uniform evidence is the characteristic lie of historical visualization.

4. **Observation is not interpretation.** The instrument shows what is there. It does not adjudicate theology, rank Companions, or settle disputes between schools. Where the tradition disagrees, the instrument renders the disagreement rather than resolving it. This is a hard boundary, specified in [06 §7](06-scholarly-methodology.md).

5. **Observatories are institutions, not devices.** Maragha outlived its founder. The design target is an entity with governance, succession, custodianship and an open corpus — see [09](09-roadmap.md) and [11 §19](11-self-critique.md).

## 5. Nūr and Nujūm — a visual philosophy that is also a data encoding

The guiding image given for this project is that the Prophet ﷺ is *nūr* and his Companions are *nujūm*. This is treated here not as decoration but as the **formal basis of the visual grammar**, because it happens to resolve three otherwise competing requirements simultaneously.

### First, the shape this is not

An earlier draft of this section, and the demonstration prototype built from it, drew the ṭabaqāt as a **narrowing funnel** — a small ring of Companions, widening outward through progressively larger, more numerous later generations. That shape is wrong, and it was caught by exactly the kind of scrutiny this project exists to invite ([REVIEWERS-BRIEF](REVIEWERS-BRIEF.md)), so it is corrected here rather than quietly patched.

The correction, with its own sources, because a document that argues for evidence-grounding cannot assert its own numbers without any:

- The Companions of the Prophet ﷺ are estimated at **well over 100,000** — a figure attributed to Abū Zurʿah al-Rāzī and cited by al-Suyūṭī. This is the layer immediately adjacent to the origin, and it is very likely the **largest**, not the smallest, ring in the entire network.
- How many of those Companions are *documented as narrators* — the population that actually appears in the transmission graph — is itself a matter of open scholarly disagreement spanning more than an order of magnitude: **al-Ḥākim** put the number at roughly 4,000; **Abū Zurʿah al-Rāzī**, as transmitted by Ibn Ḥajar, put it at over 100,000. This disagreement is a `Dispute` object in the ontology's own terms ([02 §8.7](02-knowledge-architecture.md)), not a number this document gets to pick.
- Among documented narrators, attribution is **extremely skewed**, not evenly spread. Seven Companions — the *mukthirūn* — each transmitted over a thousand ḥadīth (Abū Hurayrah alone accounts for roughly 5,374), while most who narrated at all did so once or a handful of times.
- Companions were also densely connected **to each other** — by kinship, by co-presence at the same battles and events, by teaching relationships within the same generation — none of which a strictly generational, parent-to-child tree can represent. The relation registry already models this (`fought_alongside`, `companion_of`, kinship types, `participated_in`), and it is these lateral ties, not just downward transmission, that make the real network dense near the origin.

None of this is a minor correction to a diagram. It means: the layer nearest the origin is not small, the size of any layer's *documented* population is itself contested rather than known, what documentation exists is dominated by a handful of hubs, and the graph is not a tree.

### The principle, corrected

```
                       ◉  the luminous origin
                          (never a node; never depicted;
                           the source from which the scene is lit)
              ✦  ·✦ ✦·  ✦   ·✦  ✦ ·✦  ✦  ·  ✦ ·  ✦✦  ·        Nujūm — the Companions.
           ·✦ ✦  ·   ✦  ✦·  ✦  · ✦✦  ·  ✦  ·✦   ✦ · ✦  ✦       By far the largest ring —
         ✦  ·  ✦✦  ·✦  ✦  ·   ✦✦  ·✦   ✦  ✦·  ✦ ·✦  ✦  ·✦      100,000+ by most estimates —
        ·✦  ✦ ·   ✦  ✦ ·✦  ✦   ·  ✦ ✦·  ✦  ·  ✦✦  ·✦  ✦ ·✦     laterally interconnected by
         ✦ ·  ✦  ✦·   ✦  ✦ ·  ✦✦  ·  ✦ ✦·  ✦  ✦·  ✦ ✦  ·✦      kinship, battles, teaching —
        (a small number of these points glow far brighter        not a tree at all — with a
         than the rest: the mukthirūn, whose transmission          handful of hub narrators
         volume dwarfs everyone else's — a skew, not a slope)      accounting for most of what
                                                                     later generations receive
      ✦ ·  ✦  ·✦  ✦  ·  ✦✦  ·✦   ✦  ✦·  ✦  ✦·         Tābiʿūn — how many of these are
                                                          individually documented, and how
                                                          densely, depends on what survived
                                                          to be written down, not on how many
                                                          people there actually were.
```

The diagram is no longer a claim about relative population size by generation — that claim was the defect. It is now a claim about three things this project can actually stand behind: the origin-adjacent ring is huge, activity within any ring is skewed rather than uniform, and rings are internally dense rather than merely feeding forward.

### The four rules it produces

**Rule 1 — The Prophet ﷺ is rendered as illumination, not as an object.**
There is no node. There is a luminous origin, and the noble name in calligraphic form where identification is needed. This satisfies the prohibition on depiction absolutely, and it satisfies "do not reduce him to one node among millions" *structurally* rather than by making a dot larger.

**Rule 2 — Luminance encodes attested transmission distance, and nothing else.**
An entity's warmth and brightness are a declared function of its generational/transmission distance from the Prophetic origin: Companion, Successor, and onward. This is real, sourced, queryable data — the ṭabaqāt classification the tradition itself assigns. The aesthetic *is* the encoding. Nothing is lit because it looks nice. **It is not a claim about how many entities occupy each ring** — that population, and how much of it survives as documented narrators, is a separate, contested question the encoding does not answer.

**Rule 3 — Aggregation is a rendering necessity, not a shape of history.**
*(Previously: "individuality decreases, structure increases, with distance" — corrected, because that phrasing asserted the very population gradient this section now rejects.)* At any zoom level, some region of the graph will be too dense to resolve as individual points — and that density can occur **within** a single ring (100,000+ Companions cannot all be distinct dots at a wide zoom) exactly as plausibly as it occurs across rings. Aggregation into constellations and clusters is a level-of-detail technique triggered by local density, not a rule that later generations are where the crowding happens. This is still the solution to the hairball problem — roughly the same number of *meaningful* elements on screen at any zoom — but it no longer smuggles in a claim about where the crowd actually is.

**Rule 4 — Uncertainty is rendered as diffusion, not as a label.**
A well-attested relationship is a clean line. A weakly attested one is diffuse, soft-edged, lower in opacity. A disputed location is a gradient field, not a pin. The user reads confidence *perceptually*, continuously, without having to open a panel — which is the only way confidence survives contact with a non-expert audience. **The 4,000-versus-100,000+ narrator-count dispute above is exactly this kind of case**: rendered as two diffuse, differently-sized possibilities, attributed to their respective scholars, not collapsed to one number.

### The mandatory disclaimer that rides with it

Because this grammar is powerful, it is dangerous, and one guard must be built in at the UI level, not left to documentation:

> **Brightness is transmission distance. It is not merit, rank, virtue or religious standing — and it is not population size.**

A Successor is not "dimmer" as a person, and a ring being visually smaller at a given zoom is not a claim that fewer people occupied it. The encoding measures one documented, mundane quantity: distance in the chain of transmission. This must be stated in the interface wherever the encoding appears, and the metric must be user-switchable so that no single visual reading can harden into an implied theology — or into an implied demography. See [06 §7](06-scholarly-methodology.md) on the computed-versus-significant boundary.

## 6. The conceptual architecture of the whole system

Seven layers, each independently maintainable, each with a single responsibility. Data flows up; queries flow down; nothing skips a layer.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  L7  EXPERIENCE            Explore · Learn · Study · Research            │
│      four lenses on one graph; guided riḥla; cinematic mode              │
├──────────────────────────────────────────────────────────────────────────┤
│  L6  OBSERVATION (Marṣad)  the morph field: network ⇄ map ⇄ time ⇄ depth │
│      renders only what L3 publishes · "no pixel without provenance"      │
├──────────────────────────────────────────────────────────────────────────┤
│  L5  NAVIGATION (AI)       language → intent → typed query → view state  │
│      operates the instrument; never asserts fact                         │
├──────────────────────────────────────────────────────────────────────────┤
│  L4  PROJECTION            precomputed layouts · aggregates · tiles      │
│      stable embeddings so time-scrubbing never moves the world           │
├──────────────────────────────────────────────────────────────────────────┤
│  L3  KNOWLEDGE             entities · reified relations · events         │
│      the reconstructed historical world — a *derived* view               │
├──────────────────────────────────────────────────────────────────────────┤
│  L2  EVIDENCE (Dalīl)      assertions · evaluations · disputes · clusters│
│      grading attributed to named authorities; disagreement preserved     │
├──────────────────────────────────────────────────────────────────────────┤
│  L1  RECORD (Sijill)       reports · isnāds · sources · manuscripts      │
│      append-only, versioned, signed — the immutable base                 │
└──────────────────────────────────────────────────────────────────────────┘
        ▲
        │  INGESTION: text → AI proposal → scholar adjudication → ijāza
        │  (nothing enters L1 unsigned; nothing reaches L3 unreviewed)
```

Two properties of this stack matter more than its contents:

- **L3 is derived, not authored.** The historical world is a *projection* of the evidence, rebuildable from L1+L2 at any time. Change a grading and the world updates. This is what makes the system revisable across scholarly generations rather than frozen at the moment of authorship.
- **L6 cannot reach past L3.** The renderer has no private data, no hardcoded routes, no decorative entities. If it is on screen, it came through the evidence layer and carries its provenance with it.

## 7. The five verbs

The entire interaction model reduces to five verbs. Everything else is a composition of them. Naming them at the conceptual level keeps the interface from accreting features.

| Verb | What it does | Available at every tier |
|---|---|---|
| **Focus** | Make an entity the centre; the universe reorganizes around it | ✓ |
| **Trace** | Find and follow the path between two things — people, ideas, places | ✓ |
| **Scrub** | Move in time (event-time or record-time) and watch the system respond | ✓ |
| **Interrogate** | Ask of anything visible: *how do we know this?* | ✓ |
| **Ask** | Pose a question in language; the observatory reconfigures to answer | ✓ |

**Interrogate must be available on every element in every tier, including the child's view.** The moment evidence becomes a "pro feature," the system has become a digital library with extra steps.

## 8. What the user should feel

Stated as design intent, because it constrains real decisions:

- **Calm, not busy.** The default state is quiet and dark, like a sky. Information arrives on demand. Nothing pulses, spins or glows for attention.
- **Vast, but never lost.** At all times: where am I, when am I, what am I looking at, how do I get back. Orientation is a hard requirement of any observatory.
- **Honest.** When the system does not know, it must look like not-knowing, not like a gap in the data.
- **Reverent without being ornate.** Restraint is the register. The subject supplies the gravity; the interface should not attempt to add any.
- **Discoverable.** The core reward is the moment a user sees a connection they could not have found in a book. The system should manufacture that moment as often as the evidence honestly allows.

---

**Next:** [02 — Knowledge Architecture](02-knowledge-architecture.md)
