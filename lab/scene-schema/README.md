# Scene schema (lab draft)

Two new first-class things so the graph can drive immersive worlds, without a Scene ever authoring a fact.

- `scenes.ttl`: classes and properties (same `mrs:` namespace as `ontology/marsad.ttl`).
- `scene-shapes.ttl`: SHACL for the standing rules (SC1 to SC9).
- `examples/hijrah-cave.ttl`: "Three days in the cave" (Ibn Hishām S0685, S0686, S0688). Part A is valid; Part B (`INVALID-` IRIs) breaks every rule on purpose.
- `validate_scenes.py`: runs pyshacl and groups results by part.

## Design
- **Moment**: one beat as one Report tells it: actors, `actionType`, place, `timeCue` (verbatim, never normalised), `sequenceIndex` (order in the telling), `hedge` (the source's own hedge), anchored to a Passage span (`spanStart`/`spanEnd`/`spanSha256`). It is reified and has a status (`momentStatus`, same vocabulary as claims). Software only proposes. Any other status needs an `mrs:ReviewDecision` by a `prov:Person` (SC6). A Moment is not an Event: two tellings give two Moments.
- **Scene**: place plus `PlaceCertainty` (certain, probable, approximate, disputed or unlocated), a `TemporalExtent` window, ordered `SceneBeat`s (each holds one Moment or one claim), `SceneFigure`s, a `CameraPose`, `SceneQuestion`s, `SoundCue`s and `sceneVersion`. A Scene has no plain-text slots. Every string is a `SceneText` with `resolvesTo` pointing at claims or Moments of that same scene (SC1).
- **Figures**: `drawRole` is light, person or stone. Light belongs to the Prophet ﷺ only, and he is never shown as a node or a figure. Person means a faceless marker. Stone means named as present, with no side and no action. The rule is enforced in two ways: by `depictionConstraint dc_light_only` on his person record, and by his IRI (SC4). Each figure needs evidence that the person was present.
- **Questions**: every option, right or wrong, names the claim that decides it (SC2). A question has exactly one answer.
- **ApprovalAct**: a subclass of `mrs:ReviewDecision`, so it reuses reviewedBy, target, outcome and date. It records the `approvedVersion`. It is not an Evaluation. A stale version produces a warning (SC7).
- **Publishable** (SC3): every claim and Moment the scene uses is `as_accepted`, and a human ApprovalAct exists for the current version.
- **Unlocated** (SC5): a place with no geometry must be `pc_unlocated`, and its camera may not use absolute coordinates.
- **Journey**: ordered `JourneyStep`s. A Journey is publishable only if every one of its Scenes is (SC9). Sound is ambient, effect or silence. No voice is ever produced (SC8).

## Validation (pyshacl 0.x, run with `python lab/scene-schema/validate_scenes.py`)
- Part A: **conforms** (0 results). Its state is `ps_in_review`, not publishable, because all 7 claims are still `as_proposed` in the corpus. No approval was invented.
- Part B: **18 violations + 1 warning**, as intended. They cover SC1 (bare caption; title resolving outside the scene), SC2, SC3 (three unaccepted claims; no approval), SC4 (both directions), SC5, SC6 (inverted span; accepted with no decision; evidence from another report), SC7 (software approver, plus the stale-version warning), SC8, a beat holding both a claim and a Moment, a figure with no evidence, and vocabulary typing.

## How it maps to the build (scene packs)
1. A SPARQL query selects the Scenes whose state is `ps_publishable` and that validate against `ontology/shapes.ttl` plus `scene-shapes.ttl`.
2. Each one compiles to `scene-pack/<scene-id>.json`. The pack holds the beats in `beatIndex` order, each with its resolved text and the IDs of its claims and Moments (for "why do we know this?"). It also holds the figures by role, the camera, the questions with their evidence IDs, the sound cue assets, the approval (reviewer opaque ID and date) and the `sceneVersion`.
3. `pc_unlocated` tells the renderer not to use terrain, a map pin or an absolute camera. A Journey compiles to an ordered manifest of pack IDs.
4. The build fails if a pack's version differs from the approved version.

## Migration into ontology/
1. Move the `scenes.ttl` blocks into `marsad.ttl`: a new "SCENE LAYER" section after REVIEW DECISIONS, with the vocabularies under CONTROLLED VOCABULARIES. Bump `owl:versionInfo`.
2. Move the shapes into `shapes.ttl`, renumbering SC1–SC9 as I-numbers. Add a docs/02 section with the prose rules.
3. Add `mrs:depictionConstraint mrs:dc_light_only` to `per:Vc74FSoBSMY4TBSEwjPyai` in the corpus. This needs a maintainer decision.
4. Teach `validate.py` and `shacl_check.py` to load scene files (for example `ontology/scenes/*.ttl`), and let the review platform record Moment decisions and ApprovalActs.
5. Replace the context stubs in the example with the real corpus graph, and add the `INVALID-` part as a negative test.

## Open questions for scholars
- Should the Prophet ﷺ appear as light in every scene, or be implied without any figure in some of them (for example, scenes inside the cave)?
- Does showing ʿĀmir b. Fuhayra or Asmāʾ as "stone" when they are named but not acting misrepresent their role? Should there be a fourth role?
- Which hedges should the vocabulary list (*zaʿamū*, *fīmā balaghanī*, *Allāhu aʿlam*)? Should a hedged Moment ever appear in a question?
- When tellings conflict (for example on the number of days), should a Scene show both or choose one, and who decides?
- Should a distractor be allowed to rest on a claim from a rival report rather than on the claim it contradicts?
- Is a single approval enough, or should sourcing, depiction and questions each need their own reviewer (`approvalScope`)?
- Thawr has no geometry in the graph. Should a traditional location be added as `lc_probable`, and on which source?
