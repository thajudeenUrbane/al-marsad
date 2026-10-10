# 04 — Visualization Architecture

**The governing constraint, before anything else:** the visualization layer may render only what the evidence layer publishes. It holds no private data, no decorative entities, no interpolated routes, no assumed dates. *No pixel without provenance.* Every technique below is subordinate to that rule, and any technique that cannot respect it is excluded regardless of how impressive it looks.

---

## 1. The four tiers

Not three. The fourth — L0 — is added because without it the system excludes the largest part of its intended audience and every user with a screen reader.

### L0 — The Reader
Plain, fast, semantic HTML. Text, structured lists, static maps, tables of evidence. Full keyboard navigation, full screen-reader support, works on a five-year-old Android phone over 3G, works offline, works with JavaScript disabled.

L0 is not a fallback or a degraded mode. **It is a complete rendering of the knowledge — every entity, every relationship, every piece of evidence is reachable.** What it lacks is only the spatial intuition the higher tiers provide. It is also, not incidentally, the tier search engines index and the tier that will still work in twenty years.

*Justification:* a system about a tradition whose scholarship was historically carried by the least-equipped students cannot make evidence conditional on a GPU.

### L1 — The Network (2D)
The canonical working tier. Network graph, timeline and map, coordinated, in one view. GPU-accelerated 2D rendering, semantic zoom, stable positions. Everything the system can do is available here.

*This is the tier where most of the value lives and most of the development effort should go.* It is fast, legible, mobile-viable, and dense with information. The higher tiers are enhancements to it, not successors.

### L2 — The Depth (3D)
3D is justified **only when the third axis carries information that cannot be expressed in two.** Three cases qualify:

| Use | Z-axis encodes |
|---|---|
| **Transmission depth** | Distance from the Prophetic origin — isnād generations stacked in depth, which is the natural shape of the object |
| **Time as extrusion** | A network extruded along time, so that a person is a *strand* and a relationship a *surface* — making duration directly visible |
| **Network over terrain** | Social/transmission structure suspended above real geography, showing where a network physically sat |

3D used for any other reason — depth-of-field, parallax, "immersiveness" — is rejected. It costs legibility, performance and accessibility, and buys nothing.

### L3 — The Observatory (4D)
The integrated state: network, geography, time and evidence simultaneously present and mutually responsive. Moving the time control moves the world; selecting a person re-illuminates the network, the map and the evidence together; asking a question reconfigures all of it at once.

L3 is not a separate application. It is L1 and L2 with the morph field (§2) fully unlocked and the camera free.

### Transitions are the product
Users do not switch tiers; they *move*, and the system follows. Every transition is an animated interpolation preserving object identity — you always see *the same things* rearranging, never a new screen loading. This is the mechanic that makes it feel like one universe rather than a set of tools, and it is the direct answer to "do not treat these as separate screens."

---

## 2. The morph field — the core mechanic

This is the most important idea in the visualization architecture.

Every entity carries **several stable coordinate assignments simultaneously** (computed offline per [03 §4.1](03-technical-architecture.md)):

```
  network-space   relational proximity from a graph embedding
  geo-space       real geography from place affiliation
  time-space      event-time × generational depth
  isnad-space     transmission distance from the Prophetic origin
  affinity-space  optional: tribal, doctrinal, or school clustering
```

The rendered position of any entity is a **weighted blend** of these frames:

```
position(e) = Σ wᵢ · coordᵢ(e)        with Σ wᵢ = 1
```

The interface exposes the weights as a continuous control. Pull toward geo-space and the network drifts onto the map, people sliding to the cities they lived in. Pull toward time-space and the same population reorganizes into generations. Pull toward isnad-space and it becomes a transmission tree radiating from the luminous origin. Blend two and you get genuinely new readings — *a network laid out by relational proximity but coloured and lit by geography* reveals, for instance, that a doctrinal cluster is geographically dispersed, which is a finding, not a graphic.

Why this matters architecturally:

- It makes the four dimensions **interact** rather than occupy separate tabs — exactly as required.
- It preserves object identity across every view, so the user never loses their place.
- It is cheap: all frames are precomputed; morphing is vertex interpolation on the GPU.
- It makes position *meaningful at every intermediate state*, since every frame is itself meaningful.
- It is fully reproducible — the weights are part of the citable view-state object (§6).

No existing historical visualization system does this. Palladio offers network, map and timeline as separate coordinated views; the morph is the step beyond coordination, and it is affordable precisely because layout was made stable and offline.

---

## 3. Visual semantics — the encoding contract

Every visual property is assigned exactly one meaning, documented, consistent everywhere, and switchable where it could mislead. Nothing is styled for appearance alone.

| Property | Encodes | Notes |
|---|---|---|
| **Position** | The active morph blend | Never arbitrary; never re-solved per interaction |
| **Luminance / warmth** | Transmission distance from the Prophetic origin | The Nūr/Nujūm grammar; **switchable**; never "importance" |
| **Opacity** | Evidentiary confidence, or temporal presence | The two never apply to the same element at once |
| **Edge sharpness** | Confidence — crisp = attested, diffuse = conjectural | Carries uncertainty perceptually rather than through labels |
| **Colour (hue)** | Categorical type only — person, place, event, work | Colour-blind-safe palette; never a scalar quantity |
| **Size** | A declared, named metric, off by default | Whenever on, the metric's name is displayed adjacent |
| **Line weight** | Attestation volume — how many reports support it | Explicitly *not* "strength of friendship" or significance |
| **Line style** | Relationship class — kinship, transmission, conflict, travel | |
| **Motion** | Only genuine historical movement or temporal change | No ambient drift, no idle animation, no decorative pulsing |
| **Texture / grain** | Reserved for "AI-proposed, not yet verified" | Makes unverified content visibly distinct at a glance |

Three prohibitions with the force of the encoding contract:

1. **No node is sized by centrality by default.** Computed prominence must never read as religious or scholarly rank ([06 §7](06-scholarly-methodology.md)).
2. **No glow without meaning.** Illumination is a data channel here; spending it decoratively corrupts the channel.
3. **No interpolation across unknowns.** A gap in evidence renders as a gap, not as a smooth curve. This applies to routes, timelines and network paths alike.

---

## 4. The representation policy

Binding, and applies to every tier including XR and any future medium.

**Absolutely prohibited:**
- Any figurative depiction of the Prophet ﷺ — including silhouette, outline, obscured figure, back-view, light-in-human-shape, or an avatar standing in for him.
- Any figurative depiction of the Prophet's ﷺ family or the Companions رضي الله عنهم.
- Voice performance of the Prophet ﷺ, or dramatized speech attributed to him.
- Speculative interior reconstruction of the Prophet's ﷺ household, the Rawḍa, or the interior of the Kaʿba.
- AI-generated imagery of any sacred person, place or object.

**The affirmative visual language:**
- **Light** — the primary expressive device, formally tied to transmission distance (§3).
- **Calligraphic name-forms** — where identification is needed, in classical Arabic hands, treated with the care due to them.
- **Position and structure** — relationship expressed spatially rather than pictorially.
- **Abstract geometry** — drawn from the tradition's own non-figurative visual language, used structurally rather than ornamentally.
- **Geography and built form** — places, routes and structures may be represented, at documented confidence, subject to §4.1.

### 4.1 Built environment and sacred sites
Reconstruction of physical structures is the highest-risk visual work in the project, combining archaeological uncertainty with religious sensitivity.

- Every reconstruction carries a **visible confidence classification**: archaeologically attested / textually described / conjectural / schematic.
- Conjectural elements are rendered in a **deliberately non-photoreal** register. Photorealism asserts certainty; where the evidence is textual, the rendering must not out-claim the evidence.
- **No reconstruction of a sacred interior**, at any confidence level.
- Every built asset requires **scholarly board sign-off** before publication, and carries its evidence set like any other object.

The default for the early corpus is **schematic** — plan-level, abstracted, honest. A beautifully rendered 7th-century Madinah that is 60% invention would be the most damaging single artifact this project could produce, precisely because it would be the most shared.

---

## 5. Rendering engine analysis

Evaluated against this project's actual requirements, not general capability.

### 5.1 The requirements that decide it
| # | Requirement | Weight |
|---|---|---|
| E1 | Runs in a browser, no install, linkable and citable | **Decisive** |
| E2 | Works on low-end mobile over poor connectivity | **Decisive** |
| E3 | Renders 10⁵–10⁶ elements interactively | High |
| E4 | Fine control over custom visual semantics (§3) | High |
| E5 | Accessible fallback path (L0/L1) | **Decisive** |
| E6 | Time-dynamic geospatial capability | High |
| E7 | Long-term maintainability by a small team | High |
| E8 | XR capability | Low — later, optional |

E1, E2 and E5 eliminate any engine that cannot ship as a web page. That single filter decides most of the analysis before performance is even considered.

### 5.2 Comparison

| Engine | Strengths | Weaknesses | Verdict |
|---|---|---|---|
| **WebGPU** (custom renderer) | Compute shaders for layout and aggregation; modern binding model; instancing at the scale required; full control of visual semantics; matured into production viability through 2025–26 | Requires real graphics engineering; fallback path must be maintained; older devices lack support | **Core renderer.** The only option satisfying E3+E4 without leaving the web |
| **WebGL2** | Universal support; well-understood | Lower ceiling; no compute; more CPU-side work | **Mandatory fallback.** Not the primary target |
| **Three.js** | Mature, huge ecosystem, fast to build with, good WebGPU backend | Scene-graph-per-object collapses around 10⁴ nodes; abstraction fights custom instanced rendering | **Scene composition and 3D assets only — not the graph renderer.** A `Mesh` per person does not scale |
| **deck.gl** (+ MapLibre) | Purpose-built for large geospatial data in the browser; GPU layers; composes well with custom layers; mobile-viable | Opinionated around geospatial framing; less natural for abstract network space | **Adopt for the geographic layers.** Strongest fit for L1's map |
| **CesiumJS** | Genuine globe with terrain; **first-class time-dynamic support** (clock, CZML) which is rare and directly relevant | Heavy; mobile cost; cartographic aesthetic hard to bend toward restraint; globe framing is often the wrong frame for regional history | **Adopt selectively** for globe-scale and terrain-accurate modes. Not the default view |
| **Unreal Engine** | Best-in-class visual fidelity; excellent for cinematics and high-end XR | Fails E1, E2, E5 outright; enormous asset pipeline cost; wrong tool for data-driven abstract visualization; pulls the project toward spectacle | **Reject for the product.** Reserve for offline cinematic rendering and museum/XR installations |
| **Unity** | Broad XR reach; large talent pool | Same web/mobile failures as Unreal, with less fidelity upside | **Reject for the product.** Consider only for a standalone XR title |
| **Native apps** | Best device performance | Fails linkability and citability; multiplies maintenance | **Reject.** PWA instead |

### 5.3 The recommended rendering architecture
```
  ┌─────────────────────────────────────────────────────────────┐
  │ L0  semantic HTML — no rendering engine, complete knowledge  │
  ├─────────────────────────────────────────────────────────────┤
  │ L1  custom WebGPU renderer (WebGL2 fallback)                 │
  │     · instanced points/lines for the network                 │
  │     · deck.gl + MapLibre for geographic layers               │
  │     · compute shaders for aggregation and morph blending     │
  ├─────────────────────────────────────────────────────────────┤
  │ L2  same renderer, depth axis enabled;                       │
  │     Three.js only for discrete 3D assets in the scene        │
  ├─────────────────────────────────────────────────────────────┤
  │ L3  above + CesiumJS globe mode where terrain/globe is needed│
  └─────────────────────────────────────────────────────────────┘
     offline: Blender (§7) produces assets; Unreal optional for film/XR
```

One renderer, one data path, one visual grammar, across all tiers. Tiers differ in what they enable, never in what they know.

---

## 6. The view-state object

A small idea with large consequences, and arguably the most useful single artifact the system produces for scholarship.

```
ViewState {
  corpus_version    pinned — guarantees reproducibility
  focus[]           entity/relationship references
  time              { axis: event | record, window, instant }
  morph_weights     { network, geo, time, isnad, affinity }
  camera            position, orientation, zoom
  layers[]          which data layers are active
  filters           tradition lens, confidence floor, types, regions
  evidence_mode     folded | expanded
  annotations[]     optional user/teacher overlay
}
```

It is serializable, shareable, permanently resolvable, and **citable**. Its consequences:

- **A view becomes a citation primitive.** A monograph can cite a configuration of evidence the way it cites an edition — resolvable, version-pinned, reproducible.
- **AI answers become auditable.** The assistant's reply *is* a ViewState plus grounded text; anyone can inspect exactly what was shown and re-run it ([07](07-ai-architecture.md)).
- **Lessons are just sequences of ViewStates.** The entire guided-journey and story-mode system reduces to an ordered list with narration — no separate authoring engine required ([05](05-ux-architecture.md)).
- **Accessibility is structural.** Because a ViewState is data, it can be rendered as prose or as a structured document for L0 and screen readers. The visual and non-visual tiers are the *same state*, differently expressed.

---

## 7. Blender's role

Blender is a **build-time asset factory, driven by the data. It is never a source of truth and never in the runtime path.**

**Legitimate uses:**
1. **Procedural asset generation** — historical structures, terrain treatments and abstract forms generated from corpus data via headless `bpy` scripts in CI, so assets regenerate when the data changes.
2. **Optimization and export** — producing compressed glTF/Draco assets sized for web delivery.
3. **Cinematic rendering** — offline high-fidelity sequences for film, museum installation or promotional material, where real-time constraints do not apply.
4. **Cartographic relief** — baked terrain and shading treatments for map layers.

**Explicitly excluded:**
- Hand-authored "historical scenes" that encode claims not present in the corpus. If an asset asserts something, that assertion belongs in the evidence layer first, and the asset is generated from it.
- Any figurative content (§4).
- Any runtime dependency.

The test for any Blender output: *if the corpus changes, does this asset regenerate correctly and automatically?* If not, it is hand-authored content masquerading as data, and it will drift out of agreement with the evidence — silently, and in the most visible part of the product.

---

## 8. The 2D → 3D → 4D evolution

Sequencing matters as much as design here, because building in the wrong order produces a system that cannot be made honest later.

| Stage | What is built | What must be true before starting |
|---|---|---|
| **Stage 1 — L0 + L1 static** | Reader tier; network, timeline and map as coordinated views | Evidence layer is real; positions are stable; confidence bands render |
| **Stage 2 — L1 morph** | The morph field; continuous transitions; semantic zoom | Coordinate frames precomputed and versioned |
| **Stage 3 — Time dynamics** | Scrubbing both event-time and record-time; uncertainty-aware fades | Temporal constraint solver in place; three-state presence implemented |
| **Stage 4 — L2 depth** | Isnād depth, time extrusion, network-over-terrain | A demonstrated question that 2D cannot answer |
| **Stage 5 — L3 observatory** | Full integration; free camera; globe mode | All of the above stable on mobile |
| **Stage 6 — Riḥla / story mode** | Scripted camera paths over live data | Evidence anchoring proven; pause-to-interrogate works everywhere |

**The gate on Stage 4 is a policy, not a schedule.** 3D may only begin when a specific analytical question has been identified that two dimensions genuinely cannot answer. Without that gate, 3D arrives because it is exciting, and the project acquires a demo it must then maintain forever.

**Story mode is deliberately last.** It is the most persuasive surface in the system and therefore the most dangerous one to build before the evidence discipline is proven. A cinematic Hijrah rendered over an immature corpus would be compelling, widely shared, and wrong — the exact failure this architecture is built to prevent.

---

**Next:** [05 — UX Architecture](05-ux-architecture.md)
