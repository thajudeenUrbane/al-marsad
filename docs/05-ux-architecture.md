# 05 — UX Architecture

**Governing principle: complexity inside, simplicity outside.** The user should never encounter the graph's machinery unless they ask for it. But the inverse discipline matters just as much: *simplicity must never be achieved by hiding the evidence.* Folding is permitted; removal is not.

---

## 1. The four lenses

Not four products, not four datasets, not four difficulty settings. **Four depths of unfolding over one graph.**

| Lens | Audience | What changes | What never changes |
|---|---|---|---|
| **Explore** | Children, general visitors | Vocabulary is plain; density is low; one idea at a time; evidence appears as a calm confidence badge | The badge is clickable. Evidence is one tap away. |
| **Learn** | Students, teachers | Guided journeys; comparisons; structured questions; sources named in plain language | Every claim still resolves to its report |
| **Study** | Advanced students, serious readers | Chains visible; disputes surfaced; grading shown with its evaluator; attestation gaps displayed | The same underlying objects, unfolded further |
| **Research** | Scholars, historians | Raw query access; provenance dashboards; coverage maps; exports; version pinning; contribution tools | Nothing extra is revealed — it was always there |

The lens changes **presentation and density**, never truth. A child and a professor looking at the same relationship see the same relationship; the child sees "well established," the professor sees forty-one reports across nine chains with two disputed datings.

**The rule that makes this work:** *Interrogate* (§2) is available on every element in every lens, including Explore. The moment evidence becomes a premium feature, the system has become a digital library with extra steps.

### Lens is not a wall
Users move between lenses freely and continuously — it is a slider, not an account type. A curious twelve-year-old may drop into Research on a single object and climb back out. Nothing is locked.

---

## 2. The five verbs

The entire interaction vocabulary. Every feature must reduce to a composition of these, or it does not belong in the product.

| Verb | Gesture | What happens |
|---|---|---|
| **Focus** | Select any entity or relationship | The universe reorganizes around it: its network, its events, its places, its period, its evidence — simultaneously, in one motion |
| **Trace** | Select two things | The system finds and animates the paths between them, ranked by evidentiary strength, with each hop's warrant inspectable |
| **Scrub** | Drag the time control | The world responds: presence fades in and out, relationships activate, movement occurs, institutions appear. Two axes — event-time and record-time |
| **Interrogate** | Tap "how do we know?" on anything | The evidence ladder opens: claim → assertions → reports → chains → sources → manuscript images → gradings → disputes |
| **Ask** | Natural language | The observatory reconfigures to answer, and shows its work ([07](07-ai-architecture.md)) |

Everything else — search, comparison, filtering, journeys, story mode — is a composition of these five. Holding to that discipline is what keeps a system of this complexity from accreting into a control panel.

### 2.1 Focus, specified
Selecting a person must produce, in a single coordinated motion and without further clicks:

```
      ┌─ relationships, by class, with strength and period
      ├─ events participated in, on the timeline
      ├─ places lived, travelled, died — on the map
      ├─ lifespan situated among contemporaries
      ├─ transmission position: from whom, to whom
      ├─ works authored or transmitted
      ├─ institutions and affiliations
      └─ evidence summary: how much, how strong, how contested
```

This simultaneity is the requirement. Presenting these as tabs would be the failure mode; the whole premise is that these facets are one object seen from several sides.

### 2.2 Interrogate, specified — the evidence ladder
The most important interaction in the system. Each rung is optional; users descend as far as they wish.

```
  claim        "The Prophet ﷺ and Abū Bakr رضي الله عنه sheltered in Thawr"
    ↓
  confidence   well-attested · N independent chains · no substantive dispute
    ↓
  assertions   the atomic claims, each with its report
    ↓
  reports      the akhbār, in Arabic, with translation attributed and versioned
    ↓
  chains       the isnād, rendered as a chain, each narrator resolvable
    ↓
  sources      work → recension → edition → witness → page
    ↓
  images       manuscript folio via IIIF, where available
    ↓
  gradings     who graded it, what grade, in which work, on what reasoning
    ↓
  disputes     what is contested, by whom, with what alternative
```

Two rules: the ladder is **the same at every lens** (Explore users start higher, not shallower), and **every rung is linkable** — any depth can be cited or shared directly.

---

## 3. Search

Keyword search is the floor, not the product. Four modes, unified in one input.

**1. Lookup** — a name, place, event or work. Must handle Arabic orthographic variance, transliteration variants (ʿUthmān / Uthman / Othman / عثمان), kunya and nisba forms, and partial nasab chains.

**2. Structured query** — filters composed visually: type, period, region, relationship, confidence floor, tradition lens, attestation threshold.

**3. Relational query** — the class books cannot answer:
- *"People who met both Abū Bakr and ʿUmar رضي الله عنهما"*
- *"Scholars connected to this teacher within three generations"*
- *"Events in Madinah between 1 and 5 AH involving members of the Anṣār"*
- *"Narrators active in both Kufa and Basra"*

**4. Natural language** — routed through the AI navigation layer, which composes a structured query and shows it ([07](07-ai-architecture.md)).

### The empty-state rule
A search returning nothing must never render as a blank. It must report **coverage**: what was searched, what the corpus contains for that region/period/topic, and whether the absence means *not ingested*, *sources lost*, or *genuinely unattested* — reading directly from the `CoverageGap` objects in [02 §8](02-knowledge-architecture.md). An honest "we have not yet covered 4th-century Khurāsān" builds more trust than a blank page destroys.

---

## 4. Comparison

A dedicated mode, because comparison is how historical understanding actually forms.

| Comparison | What is shown |
|---|---|
| **Year vs year** | Two synchronized observatory states side by side, or superimposed with difference highlighting |
| **Person vs person** | Overlapping networks, shared contacts, divergent trajectories, relative attestation volume |
| **Region vs region** | Density of people, institutions, transmission activity, with coverage caveats attached |
| **Centre vs centre** | Madinah, Kufa, Basra, Baghdad, Nishapur, Cordoba — as knowledge networks over time |
| **Period vs period** | Structural change: how a network's shape, reach and connectivity altered |
| **Source vs source** | *The historiographic comparison* — the same event as Ibn Isḥāq has it and as al-Wāqidī has it, with differences marked (D6 in action) |

**The mandatory caveat.** Any quantitative comparison carries a visible coverage warning, because differences in the corpus overwhelmingly reflect differences in *what has been ingested and what survived*, not differences in historical reality. "Cordoba shows fewer scholars than Baghdad" is, in the early corpus, a statement about the dataset. The interface must say so, every time, unprompted.

---

## 5. Guided journeys (Riḥla) and story mode

### Journeys
A journey is an ordered sequence of `ViewState` objects with narration, questions and checkpoints. Because the ViewState is a first-class citable object ([04 §6](04-visualization-architecture.md)), the entire journey system requires **no separate authoring engine** — it is a list, a text field per step, and a player.

Launch set:
- The Life of the Prophet ﷺ — the spine
- The Hijrah — the prototype journey ([08](08-prototype-hijrah.md))
- The Companions around the Prophet ﷺ
- Women in the Seerah — as a first-class journey, not an appendix
- How ḥadīth travelled — Madinah to the great collections
- The formation of the schools
- Islamic civilization across centuries
- How Islam reached Malabar — a regional journey, demonstrating the model generalizes

At any step the user may **leave the path** and explore freely, then return. Guided and free exploration are the same surface.

### Story mode
Cinematic sequencing over **live data** — a scripted camera path through the same corpus, never a pre-rendered video. Four binding rules:

1. **Pause always reveals evidence.** At any frame, stopping exposes the evidence behind what is on screen.
2. **Disputed elements are marked inside the cinematic**, not only in the footnotes. If a route segment is conjectural, it looks conjectural while the camera flies along it.
3. **No invented detail.** No weather, no crowds, no incidental action that the corpus does not attest. Absence renders as darkness, not as set dressing.
4. **It ships last.** Story mode is the most persuasive surface in the system; it may not precede a mature evidence layer ([04 §8](04-visualization-architecture.md)).

---

## 6. The four interfaces

### 6.1 Student
- Explore/Learn lenses; journeys; bookmarks; a personal "what I have explored" map
- **Question prompts, not quizzes** — "who else was present?", "how do we know this?"
- Offline packs for a journey or region
- Zero account required to read; account only to save

### 6.2 Teacher
- **Journey builder** — assemble a lesson as a sequence of states with narration and questions; share by link; no technical skill needed, because a state is captured by pressing a button while exploring
- Classroom mode: a presenter view driving follower devices
- Print/export a journey as a static handout, with citations, that works with no devices at all
- Coverage and confidence briefing per topic, so a teacher knows in advance where the evidence is thin before a student finds it
- **Discussion prompts on genuine scholarly disputes** — teaching disagreement as normal rather than embarrassing

### 6.3 Scholar
- Review queues with diff-based adjudication and micro-task batching ([06](06-scholarly-methodology.md))
- Evaluation authoring: attach gradings with reasoning and citation
- Dispute documentation: record a disagreement as a structured object rather than prose
- Identity adjudication: the merge/split queue, which will be the highest-volume scholarly task
- Signed contributions under the *ijāza* model, with a permanent, citable credit ledger
- Watchlists on entities and topics within their specialism

### 6.4 Researcher
- Query console — structured and raw, with query sharing
- Bulk export: Parquet, CSV, RDF, version-pinned and DOI-assigned
- Python client and notebook integration; the corpus must be usable *away from this website*
- Provenance and coverage dashboards; attestation-gap analysis
- Network analytics with the mandatory interpretive guard ([06 §7](06-scholarly-methodology.md))
- Version pinning and reproducible citation for everything

---

## 7. Mobile strategy

Mobile is the **primary** platform for the largest part of the intended audience, not a secondary target.

- **PWA, not native.** Preserves linkability and citability; one codebase; installable; offline-capable. Native apps only if platform distribution proves essential, and then as shells over the same core.
- **L0 and L1 are the mobile product.** L2/L3 are available on capable devices; nothing essential lives there.
- **Offline packs are a core feature.** A region-and-period bundle — corpus subset, tiles, images — downloadable over wifi and fully usable without connectivity.
- **Budgets are enforced in CI**, not aspirational: sub-300 KB reader tier, sub-2 MB interactive tier, tested on a low-end device profile in the build pipeline. A performance regression fails the build.
- **Touch-first interaction design** for all five verbs; the timeline scrub in particular must work with a thumb.
- **RTL and Arabic typography as a first-class layout target**, not a localization pass. Arabic is a primary language of this system, not a translation of it.

---

## 8. XR — possibilities and discipline

**Position: XR is a legitimate later capability and a dangerous early one.** It is listed here with its conditions rather than its ideas, because the ideas are easy and the conditions are what will be forgotten.

**Where XR genuinely adds value:**
- **Standing inside the network.** Transmission depth and generational structure are genuinely easier to apprehend in stereo space than on a screen. This is XR's one clear analytical advantage.
- **Scale intuition** for geography and journey distance — what a 400 km flight over the Hijaz actually implies.
- **Museum and institutional installations**, where a curated, supervised context mitigates the risks.

**Where it must not go:**
- No first-person "witnessing" of sacred events. No standing in the Prophet's ﷺ presence. No embodiment of Companions. The representation policy ([04 §4](04-visualization-architecture.md)) applies in full and without exception in XR, where the pressure to violate it will be strongest because the medium rewards presence.
- No XR-exclusive knowledge. Anything learnable in XR must be learnable at L0.

**Conditions for beginning:** the L0–L3 tiers mature, the representation policy tested against a scholarly board, and a specific question identified that XR answers better. Absent all three, XR is a funding demo with a long maintenance tail.

**AR** has a narrower but real use: on-site at historical locations, overlaying attested information about place and event — with location confidence displayed, and with sacred-site behaviour governed by the same policy.

---

## 9. Accessibility

Not a compliance exercise. A system whose thesis is *making the invisible observable* has a particular obligation to users who cannot see it.

- **L0 is the accessibility guarantee** — complete knowledge, semantic markup, full keyboard navigation, screen-reader-coherent structure.
- **Every ViewState is renderable as prose.** Because the state is structured data, "what is on screen" can always be expressed as a described scene and a structured list. Visual and non-visual users share one state, not two products.
- **No information carried by colour alone** — confidence uses opacity, sharpness and explicit labels as well as hue.
- **Motion respects `prefers-reduced-motion`**, with all transitions replaceable by discrete states.
- **Text alternatives for every map, network and chain view**, generated from the data rather than authored.
- **Arabic and RTL** treated as primary, with correct shaping, diacritic handling and font fallbacks.

---

## 10. Orientation — never lost in a universe

A vast navigable space creates a specific, well-documented failure: users lose their place and stop exploring. Five permanent affordances:

1. **A persistent "you are here"** — entity, period, region, active lens, always visible.
2. **Breadcrumbs of exploration** — the path taken, re-traversable in both directions.
3. **Undo for navigation** — every view change is reversible, including AI-driven reconfigurations.
4. **Home is one gesture** — return to the Prophetic centre from anywhere, always.
5. **Scale indicators** — how much of the corpus is currently visible, and what is being hidden by the active filters. A user must never mistake a filtered view for the whole.

---

**Next:** [06 — Scholarly Methodology](06-scholarly-methodology.md)
