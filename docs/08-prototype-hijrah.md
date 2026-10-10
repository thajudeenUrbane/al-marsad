# 08 — Prototype: The Hijrah

## 1. Why the Hijrah

Chosen not for its significance but for its **structural density**. In a single bounded event, the Hijrah exercises every architectural component the full platform requires:

| Component | How the Hijrah exercises it |
|---|---|
| People | A small, well-attested cast with deep relationships |
| Relationships | Kinship, companionship, patronage, protection, enmity, employment — nearly every relation class |
| Events | Nested: the decision, the plot, the departure, the cave, the pursuit, the journey, the arrival |
| Geography | Two cities, an indirect route, a cave, named waypoints — with varying attestation |
| Movement | Multiple parties moving simultaneously in different directions, under pursuit |
| Time | Days and hours matter; and the dating is *itself* contested — an honest test of the temporal model |
| Sources | Sīra, maghāzī, ḥadīth collections, ṭabaqāt — several genres with different warrant types |
| Qurʾānic context | Direct, and the connection is itself a scholarly question |
| Knowledge transmission | The reports travel through identifiable chains; several key narrators are participants |
| Uncertainty | Route segments, timings and details range from firmly established to genuinely disputed |

If the architecture can represent the Hijrah honestly and make it explorable, it can represent anything else in the corpus. If it cannot, no amount of scale will rescue it.

**It is also, critically, a hard case for honesty.** The emotionally powerful version of this story is smooth, cinematic and certain. The evidentiarily accurate version has soft edges, contested timings, and route segments nobody can confirm. The prototype succeeds only if it is *more* moving for being honest — which is the thesis of the whole project, tested early.

---

## 2. What the prototype must prove

Five propositions, in priority order. Anything not serving one of these is out of scope.

1. **The evidence layer works.** Every visible element resolves through the full ladder to a source, and uncertainty is visible without being consulted.
2. **The four dimensions integrate.** Selecting a person changes the network, the map, the timeline and the evidence panel in one motion. The morph between network-space and geo-space is continuous and comprehensible.
3. **Time is navigable and honest.** Scrubbing produces motion, appearance and change — with uncertainty rendered as uncertainty. Positions never jump.
4. **AI navigates rather than narrates.** A natural-language question reconfigures the view, shows its query, and attaches its evidence.
5. **It is legible to a non-specialist and credible to a specialist** — the same build, without a mode switch.

### What it must not be
Not a dashboard. Not a slideshow. Not a map with pins and popups. **The user must feel they have entered a structure and are moving through it.** The opening frame is not a menu; it is the network, quiet, at rest, with one point of entry.

---

## 3. Dataset scope

Deliberately small and deliberately *deep*. Depth of evidence is the point; breadth is not.

| Object | Target | Notes |
|---|---|---|
| Persons | 60–120 | The Hijrah cast plus immediate network: both households, the guide, the pursuers, Madinan receivers, key narrators of the reports |
| Relationships | 300–600 | Fully faceted, each with attestation |
| Events | 40–80 | Nested, from the decision through the arrival at Qubāʾ and entry into Madinah |
| Places | 25–50 | Makkah and quarters, Thawr, route waypoints, Qubāʾ, Madinah and quarters |
| Route segments | 15–30 | **Each individually graded for confidence** — the honesty showcase |
| Reports (akhbār) | 300–800 | Arabic text, chain, source location, cluster membership |
| Chains | 150–400 | Fully parsed narrator sequences |
| Evaluations | As attested | Attributed gradings from named authorities |
| Disputes | 8–20 | Real disagreements — dating, route detail, sequence of events |
| Coverage gaps | Explicit | What this prototype deliberately does not cover |

**Source base:** the sīra-maghāzī tradition (Ibn Isḥāq/Ibn Hishām, al-Wāqidī, Ibn Saʿd), the relevant ḥadīth material, and al-Ṭabarī — with public-domain and openly-licensed texts (OpenITI and equivalents) preferred, and a fully-populated licence register from day one.

**Every record scholar-reviewed before inclusion.** At this scale that is achievable, and it establishes the workflow ([06](06-scholarly-methodology.md)) at a size where it can be debugged. A prototype built on unreviewed data would prove nothing about the thing being prototyped.

---

## 4. The experience

### 4.1 Entry
Darkness. A quiet field of points — the network at rest, positioned in network-space, lit by transmission distance from the luminous origin. No chrome, no menu, no modal. One line of text:

> *The Hijrah. 622 CE / 1 AH. Begin where you like.*

The user can immediately: click any point, scrub time, pull the morph control, or ask a question. **There is no tutorial.** The five verbs are discoverable because there are only five.

### 4.2 Focus — selecting a person
Selecting Abū Bakr رضي الله عنه produces, in one continuous motion:
- his immediate network illuminating, the rest receding to context;
- his events marking on the timeline;
- his places lighting on the map beneath;
- his lifespan situating among contemporaries;
- an evidence summary: how much, how strong, how contested;
- his position in the transmission of the Hijrah reports themselves — *he is both participant and, through his descendants and associates, a source*.

That last point is the prototype's best demonstration of the four-fold isnād reading ([02 §3](02-knowledge-architecture.md)): the same person is simultaneously an actor in the event and a node in the evidentiary chain that transmits it. One graph, two readings, visible at once.

### 4.3 Scrub — time
Dragging the time control across the days of the journey:
- the two parties move along their routes, at attested pace where known and as diffuse uncertainty where not;
- the pursuit parties move separately, on their own evidence;
- Makkah's network dims as the Madinan network brightens — the migration visible as a *structural* change, not just a moving dot;
- relationships activate and lapse on their own clocks;
- contested intervals render as contested — the timeline's disputed regions are visibly marked.

A second control switches to **record-time**: hold the event fixed and move the sources from Ibn Isḥāq's horizon to al-Ṭabarī's, watching which details enter the tradition when. Even at prototype scale, with four or five source strata, this is a capability no existing system offers, and it is the clearest demonstration that this is a research instrument.

### 4.4 Interrogate — the route
The prototype's decisive moment. The user clicks the route segment approaching Thawr:

```
  segment: Makkah → Thawr
  confidence: attested        ▓▓▓▓▓▓▓▓░░
  ── 14 reports, 6 chains, 3 collections
  ── graded: ṣaḥīḥ per [evaluator, work, location]
  ── no substantive dispute
     [ open the reports ]  [ see the chains ]  [ view the manuscript ]
```

Then a segment in the middle of the desert route:

```
  segment: [waypoint] → [waypoint]
  confidence: conjectural     ▓▓░░░░░░░░
  ── the sources name the endpoints; the path between them is inferred
  ── 2 reports, both via a single chain
  ── al-Wāqidī gives a different waypoint sequence  → [ see the dispute ]
  ── rendered as a corridor, not a line, because the corridor is what we know
```

**This is the whole project in one interaction.** The user learns, viscerally, that the confident-looking arrow on every map they have ever seen was a choice someone made, and that this system declines to make it silently.

### 4.5 Trace
*"Show me the connection between Asmāʾ رضي الله عنها and the events at the cave."* The system finds the paths, animates them, ranks them by evidentiary strength, and lets the user inspect each hop's warrant. What a book conveys in a paragraph of prose becomes a structure the user can inspect hop by hop.

### 4.6 Ask
Five questions the prototype must answer well:
1. *"Who was involved in the Hijrah?"* — the cast, by role, with attestation levels.
2. *"Show everyone connected to Abū Bakr رضي الله عنه during the Hijrah."* — the requested capability, exactly.
3. *"How do we know about the cave?"* — the evidence ladder, opened by language.
4. *"What do sources disagree about here?"* — disputes surfaced as a set.
5. *"Who first recorded this, and when?"* — the historiographic dimension, by question.

Each answer reconfigures the view, displays its typed query in plain language, and attaches its evidence.

---

## 5. Explicitly out of scope

Stated because prototypes fail by accretion, not by omission.

- Anything beyond the Hijrah's immediate network and period
- 3D (L2) and globe mode (L3) — **the prototype is L0 + L1 only**
- Story/cinematic mode
- Contribution and review interfaces (the workflow runs offline for the prototype)
- Multi-tradition lens switching — one declared lens, openly stated, with the architecture in place
- Mobile-native anything — responsive web only
- Accounts, social features, gamification
- Any built-environment 3D reconstruction

**3D is excluded deliberately and on principle.** If the prototype is compelling in 2D, the architecture is validated. If it needs 3D to be compelling, the architecture has failed and 3D would only conceal that.

---

## 6. Technical scope

Deliberately the thin slice of the full stack, with no shortcuts that would have to be undone.

| Layer | Prototype build |
|---|---|
| Storage | PostgreSQL + PostGIS; append-only log from day one |
| Graph | Recursive CTEs in Postgres — **no graph database yet**; the corpus is far too small to justify one |
| Search | Postgres full-text with Arabic configuration; OpenSearch deferred |
| Layout | Offline precomputed coordinate frames, versioned — **built correctly from the start**, as this is unretrofittable |
| Rendering | WebGPU with WebGL2 fallback; deck.gl + MapLibre for the map layer |
| L0 | Full semantic HTML tier — built *first*, not last |
| AI | Typed-query DSL, intent classification, entity linking, binding validator, refusal paths |
| API | GraphQL exploration endpoint; ViewState as a resolvable resource |
| Ingestion | Manual and semi-automated; AI-assisted parsing with full human review |

**The two things that must be built properly even at prototype scale**, because they cannot be retrofitted: the **append-only evidence log** and the **stable precomputed layout**. Everything else can be replaced later without disturbing what sits above it.

---

## 7. Acceptance criteria

The prototype ships when all of the following are true.

**Evidentiary**
- [ ] Every visible element resolves through the full evidence ladder to a citable source
- [ ] Route segments render at their real, individually assessed confidence
- [ ] At least eight genuine scholarly disputes are represented and explorable
- [ ] Coverage gaps are declared and visible
- [ ] A specialist reviewer, given a day, finds no claim presented above its warranted confidence

**Experiential**
- [ ] A new user reaches a meaningful exploration within 30 seconds, with no instructions
- [ ] Selecting a person updates network, map, timeline and evidence in one motion
- [ ] Time-scrubbing is smooth (<100 ms), and positions never jump
- [ ] The morph between network-space and geo-space is continuous and comprehensible
- [ ] Interrogate is reachable from every visible element

**Technical**
- [ ] L0 tier fully functional, screen-reader coherent, usable with JavaScript disabled
- [ ] Interactive tier under 2 MB before user action
- [ ] Usable on a low-end Android device over 3G
- [ ] All five AI questions (§4.6) answered correctly, with queries shown and evidence attached
- [ ] All prohibited-intent tests refused correctly under adversarial prompting
- [ ] Any ViewState URL reproduces its exact view against its pinned corpus version

**The single overriding test:**
> A scholar of the Seerah explores it for an hour, trying to find something stated more confidently than the evidence supports — **and fails.**

If that test passes, the architecture is validated and the project can proceed to scale. If it fails, no amount of visual sophistication makes the system worth building.

---

## 8. What the prototype proves about the full platform

| Prototype element | What it validates for the whole |
|---|---|
| Report-first data model | The entire epistemic foundation ([02](02-knowledge-architecture.md)) |
| Segment-level route confidence | That honest uncertainty is *more* compelling than false certainty |
| Stable precomputed layout | The scalability path ([03 §4.1](03-technical-architecture.md)) |
| Morph field | That the four dimensions can genuinely integrate |
| Record-time axis | That historiography is navigable — the novel research capability |
| Evidence ladder at all lenses | That rigour and accessibility are not in tension |
| Typed-query AI with shown queries | That AI can navigate without asserting |
| L0 tier | That the system is honestly universal, not universal in principle |

Every one of these generalizes without modification from 100 people to 100,000. That is the prototype's real purpose: not to demonstrate the Hijrah, but to demonstrate that **the architecture does not change when the corpus grows** — only the data does.

---

**Next:** [09 — Roadmap](09-roadmap.md)
