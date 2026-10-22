# The aniconic immersive design grammar

**Status:** draft standard, version 0.1, 17 October 2026. For review by the maintainer and the scholars' board.
**Scope:** every visual and sonic mark in al-Marṣad's night world: the Sky, the Observatory, Hijrah Night (`lab/hijrah-night/`), Lifelines, the guided modes, and any future XR or audio work.
**Companions to this file:** `SOUND.md` (sound policy for the scholars to decide), `DESIGNER-BRIEF.md` (brief for a visual designer), `index.html` (visual specimen of each mark).

The grammar exists so that a designer, an engineer or a scholar can look at any mark on screen and answer three questions: *what does it mean, what licenses it, and what is it forbidden to say?*

---

## 1. Principles

1. **No pixel without provenance.** Every mark that encodes a fact is drawn from a recorded claim (an `mrs:Assertion` with a source). Clicking or focusing any mark opens its evidence. Marks with no evidence behind them are *decoration* and must be visibly decorative (§3.12): they never vary with data.
2. **Aniconism is absolute.** No figurative depiction of the Prophet ﷺ, his family, or the Companions, in any medium: no faces, bodies, silhouettes, hands, shadows, footprints shaped as feet, avatars, mannequins, "faceless" figures, veiled figures, generated images, motion capture, or first-person bodies in XR. People are shown only as **light**, **name** (calligraphy), **sound of narration about them** (never their own voice), and **relations**. This applies equally to opponents: no person is ever drawn as a figure.
3. **The Prophet ﷺ is the light at the centre, never a node (H4).** He is not one star among others, is never ranked, never counted in "most connected", never given a degree, a tooltip score, or an edge weight. He is the source of the light the other lights receive.
4. **The metaphor is ours (H5).** The image of the Companions as stars is our design metaphor. It is never captioned, narrated, or implied to be a hadith. Any on-screen text that explains the metaphor says so in plain words: "In this sky, we show…".
5. **AI never asserts.** Generated text may summarise or navigate; it never introduces a mark. A mark licensed only by a model output is forbidden. The interface shows the human-reviewed status of every claim.
6. **Computed ≠ significant.** Sizes, counts and positions that come from computation (degree, centrality, layout) are labelled as counts of recorded links (coverage), never as importance, rank, merit or virtue. Brightness encodes *generation* (T4), not worth.
7. **Uncertainty is drawn, not hidden.** Certainty is a first-class visual variable (§3.5). A disputed claim is never drawn as if certain; an absent claim is drawn as absence (§3.4), never filled in.
8. **Restraint and adab.** Motion is slow, sound is quiet, nothing celebrates violence. Battles are shown as events in time and place, never as spectacle. Death is shown as a light that remains (memory), not as extinction.
9. **Accessible by default.** Every mark has a text equivalent, a keyboard path, and a reduced-motion form. Colour is never the only carrier of meaning.

---

## 2. Tokens

All values are CSS custom properties; the prototype `lab/hijrah-night/template.html` already uses the first set and this grammar keeps them.

### 2.1 Colour

| Token | Value | Use |
|---|---|---|
| `--night` | `#070a15` | ground of the world; nothing is drawn darker except stones |
| `--panel` | `rgba(11,15,29,0.88)` | text panels over the sky |
| `--ink` | `#ebe6d6` | primary text |
| `--muted` | `#9ba1b6` | secondary text |
| `--faint` | `#6b7189` | tertiary text, decorative stars |
| `--line` | `rgba(235,230,214,0.13)` | hairlines, rules |
| `--light` | `#ffd486` | **reserved**: the central light (§3.1) and the light it lends; nothing else may use this hue |
| `--light-dim` | `rgba(255,212,134,0.16)` | halo of the central light; light received along a chain |
| `--person` | `#dce7ff` | a person shown as a light (§3.2) |
| `--woman-person` | `#dce7ff` | identical to `--person`; there is **no** gendered colour (§6.4) |
| `--stone` | `#7b7f8e` | stone outline (§3.3) |
| `--stone-fill` | `#1a1d28` | stone body |
| `--absence` | `rgba(155,161,182,0.55)` | dashed outline for unplaced, unlocated, unrecorded (§3.4) |
| `--chain` | `rgba(220,231,255,0.42)` | isnād links (§3.6) |
| `--constellation` | `rgba(220,231,255,0.22)` | constellation lines (§3.7) |
| `--dispute` | `#e8a090` | marker colour for a recorded dispute (never for a person) |
| `--ok` | `#95d5ac` | "reviewed" status chip only |
| `--focus` | `#ffffff` | 2 px focus ring, all interactive marks |

Contrast on `--night` (computed, WCAG 2.x): `--ink` 15.8:1; `--muted` 7.7:1; `--stone` outline 4.9:1; `--faint` 4.1:1, so `--faint` is for large text (≥ 24 px, or ≥ 18.7 px bold), non-text marks and decoration only, never body text.

### 2.2 Generation by brightness (T4)

Brightness of a person-light is fixed by the generation recorded for them, not by any computed score.

| Generation | Core opacity | Halo radius | Token |
|---|---|---|---|
| Companions (ṣaḥāba) | 1.00 | 3.0 × r | `--gen-1` |
| Successors (tābiʿūn) | 0.72 | 2.2 × r | `--gen-2` |
| Successors of the Successors | 0.52 | 1.6 × r | `--gen-3` |
| Later narrators and scholars | 0.36 | 1.2 × r | `--gen-4` |
| Generation not recorded | 0.36, dashed absence ring | none | `--gen-unknown` |

Companionship is shown at gen-1 brightness **only after a scholar has accepted the companionship claim** (same gate as the honorific, H1). Until then the light is drawn at gen-unknown with a "companionship under review" note in its panel.

### 2.3 Size

| Mark | Diameter at 1× zoom | Notes |
|---|---|---|
| Central light | 28 px core, 160 px halo | never scaled by data |
| Person-light | 6 px core (all people) | **size never encodes data** in the default view |
| Person-light, "coverage" view | 6–14 px, √(recorded link count) | only in a view labelled "count of recorded links"; legend required |
| Stone | 8 × 7 px irregular heptagon | fixed |
| Place, located | 5 px ring | fixed |
| Place, unplaced | 10 px dashed ring | fixed |
| Certainty ring | core + 4 px, + 8 px | §3.5 |
| Hit target | ≥ 44 × 44 px | regardless of drawn size |

### 2.4 Type

| Token | Stack | Use |
|---|---|---|
| `--f-arabic` | Amiri, "Noto Naskh Arabic", "Geeza Pro", serif | names, honorifics, source passages |
| `--f-arabic-display` | "Aref Ruqaa" or Amiri for headings only (thuluth-style calligraphy is commissioned artwork, never a font substitute) | |
| `--f-display` | Marcellus, Palatino, Georgia, serif | Latin headings |
| `--f-body` | IBM Plex Sans, system-ui | Latin body |
| `--f-mono` | IBM Plex Mono | identifiers, citations |

### 2.5 Motion

| Token | Value | Use |
|---|---|---|
| `--t-breath` | 6 s ease-in-out, infinite | central light's halo (±6 % opacity only) |
| `--t-reveal` | 900 ms ease-out | a light appearing |
| `--t-transform` | 2400 ms ease-in-out | stone becoming a star (X1) |
| `--t-chain` | 600 ms per link | isnād drawing upward |
| `--t-camera` | ≥ 1200 ms, ease-in-out, max 30°/s rotation | any camera move |

Rules: no flashing above 1 Hz; no motion faster than the camera token; no parallax on text; no auto-playing camera sequences longer than 20 s without a pause control. Twinkle is allowed only on decorative stars (§3.12), never on a person-light (it would read as a signal).

**Reduced motion** (`prefers-reduced-motion: reduce`, and an in-app toggle that overrides the OS): breathing stops at mid-value; reveals become 150 ms opacity fades; the stone-to-star transformation becomes a cross-fade with a text label "accepted Islam, [date], [source]"; chains appear whole; camera moves become cuts. No information is carried only by motion.

---

## 3. The vocabulary

For each mark: **what it is**, **visual spec**, **may encode**, **may not encode**, **evidence required**.

### 3.1 The light (the Prophet ﷺ)

- **Spec:** radial gradient, `--light` core (28 px) to transparent at 160 px; slow breath (`--t-breath`). Always at the centre of the composition or, in maps and timelines, at the place and time where the narrative stands with him. No outline, no shape, no label inside it. Name shown beside it in calligraphy with ﷺ (§7).
- **May encode:** presence at a place and time recorded in the sources; the origin of light lent to others.
- **May not encode:** any metric, rank, count, degree, edge weight, face, figure, hand, footprint, silhouette, gaze direction, or speech. It never "moves like a walker"; in journeys it advances by cross-fade from station to station.
- **Evidence:** a place-and-time claim for each station; a station with no located claim is shown as absence (§3.4), and the light waits there rather than being placed by interpolation.
- **Never:** a node in a graph view; a tooltip with statistics; a click target that opens a "profile". Its panel is a reading panel (sources about the moment), not a record card.

### 3.2 The lights (people who accepted Islam)

- **Spec:** `--person` core 6 px, halo by generation (§2.2). Lit by `--light-dim` when a relation to the Prophet ﷺ is recorded and drawn.
- **May encode:** existence of the person in the record; generation (brightness); companionship once scholar-accepted; a recorded relation (by proximity or a line, only if the line is a recorded relation).
- **May not encode:** virtue, rank, closeness to Allah, Paradise (except where the ten promised Paradise are listed as such by a sourced claim, and then only in order, §6.6, never as a glow); size by computed degree outside a labelled coverage view.
- **Evidence:** at least one sourced assertion naming the person; generation from a recorded claim; companionship from a scholar-accepted claim.

### 3.3 Stones (opponents, X1)

- **Spec:** irregular dark heptagon, `--stone-fill` body, 1 px `--stone` outline, no halo, no glow, does not receive `--light-dim`. Stones do not twinkle or breathe. Not red, not black-on-black: the body (`--stone-fill`) is near the ground by design, so the outline carries legibility (4.9:1 against `--night`, above the 3:1 non-text minimum).
- **May encode:** a recorded, sourced claim that the person opposed or fought against the Prophet ﷺ (`rel_opposed`, `rel_fought_against`, with `atEvent` where known), in the time window the claim covers.
- **May not encode:** a judgement on the person's final state (which belongs to Allah); ethnicity, tribe, or family as such; "evil". A stone is "in opposition, at this time, according to these sources" and its panel says that.
- **Transformation:** when the time cursor passes a **recorded acceptance of Islam** (dated assertion with source), the stone becomes a light over `--t-transform`: outline fades, a light rises from within, halo grows to the person's generation. The panel shows the date, the source and the review status. Reverse scrubbing reverses it.
- **Evidence:** opposition requires a sourced assertion; transformation requires a sourced, dated acceptance claim. If the date is disputed, the transformation is drawn across the disputed span with a certainty ring (§3.5). If no acceptance is recorded, the stone stays a stone, and its panel says "no acceptance of Islam is recorded in our sources" (not "never accepted Islam").
- **Ontology gap:** `ontology/relations.ttl` has no relation type for accepting Islam yet. X1 transformations cannot be licensed until one is added and reviewed.
- **Ordering:** stones and those who died as disbelievers come last in every list (E3).

### 3.4 Absence

- **Spec:** dashed outline (`--absence`, dash 3/3, 1 px), nothing inside. Text in its panel: what is missing, and where we looked.
- **May encode:** unplaced place (`lc_unlocated`), unrecorded date, unrecorded person ("a man from the Anṣār" with no name), coverage state `cs_stub`/`cs_outline`, a known gap (`mrs:CoverageGap`).
- **May not encode:** a guess. Absence is never filled by interpolation, AI, "artist's impression", or modern reconstruction.
- **Evidence:** absence needs evidence too: a coverage record or a source that mentions the thing without placing/naming it. Without that, nothing is drawn.

### 3.5 Certainty rings

- **Spec:** concentric rings around any mark that carries a dated or located claim.

| State | Ring | From ontology |
|---|---|---|
| certain | none (clean edge) | `lc_certain`, accepted assertion |
| probable | one solid ring, 1 px, 40 % opacity | `lc_probable` |
| approximate | one dotted ring, 1 px | `lc_approximate` |
| disputed | two rings, the outer in `--dispute`, with a small notch; panel lists each position | `lc_disputed`, `mrs:Dispute` |
| proposed / under review | dashed ring, "under review" in panel | `as_proposed`, `as_under_review` |
| rejected / superseded | **not drawn**; reachable from the review log only | `as_rejected`, `as_superseded` |

- **May encode:** the reviewed certainty of the claim behind the mark.
- **May not encode:** hadith grading, a person's reliability (jarḥ wa taʿdīl) or a scholar's opinion of a person. Narrator evaluation (`mrs:Evaluation`) is text in the panel, attributed to the critic, never a ring, colour or size.

### 3.6 Chains (isnād)

- **Spec:** a vertical chain of person-lights joined by `--chain` lines rising from the reader (bottom) toward the source (top). Each link is drawn at `--t-chain`. A link whose contact is unverified (`mrs:ContactCheck` not passed) is dashed; a gap (inqiṭāʿ) is an absence mark between lights.
- **May encode:** the recorded transmission chain of a specific report, link by link, as the collection gives it; the ascription level (`asc_marfu`, `asc_mawquf`, `asc_maqtu`) as a text label at the top.
- **May not encode:** a hadith grade invented or computed by us. A grade is shown only as text, quoted from a named critic with a source. Lines never thicken by "strength".
- **Marfūʿ chains** end in the central light's halo, not in a node.

### 3.7 Constellations

- **Spec:** thin `--constellation` lines among person-lights, appearing only after the narrative has passed through an event; they remain as **memory** (the prototype's idea). Labelled with the event name in Arabic and Latin.
- **May encode:** recorded co-participation in a recorded event (`mrs:Participation`), e.g. those recorded at Badr, Uḥud, the Pledge of Riḍwān.
- **May not encode:** inferred groups, clusters from community detection, "factions", similarity. Computed clusters may exist in research views only, labelled "computed grouping, not a historical group".
- **Evidence:** each line needs a participation claim for both ends. Lists like the people of Badr follow the reviewed list; until reviewed, the 50 Stories records may be used (E3) with a visible "unreviewed list" note.

### 3.8 Calligraphy (names)

- **Spec:** names are set in `--f-arabic` beside the light, never inside it, never forming a body or a face. Commissioned calligraphic name-panels in the hilye tradition (text describing, not depicting) are allowed for the Prophet ﷺ and for the Companions; they must be complete texts with a source, and may never be arranged into a figure (no zoomorphic or anthropomorphic calligraphy).
- **May encode:** name, kunya, nasab, laqab, with their sources; the honorific (§7).
- **May not encode:** shape of a person; emotional state; a quotation not in the sources.

### 3.9 Time and season

- **Spec:** the sky turns with the lunar calendar. Hijri months are the primary scale (T2); Gregorian equivalents are secondary and labelled approximate. Moon phase may be drawn for a dated night **only** when the date is recorded and the phase is computed (labelled "computed from the recorded date"). Seasons (heat of summer for Tabūk, etc.) appear as ground tone only when a source states them.
- **May not encode:** a precise hour or date not in the sources. Undated events sit in a dated span with an absence edge.

### 3.10 Weather

- **Spec:** weather is drawn only when a source describes it (the rain before Badr, the wind at the Trench). It is atmospheric (particle haze, dimming), never theatrical (no lightning strikes on people, no storm spectacle).
- **Evidence:** a sourced passage; the panel quotes it. With no source the sky is clear and neutral.
- **May not encode:** divine favour or anger as a visual effect. Where the sources speak of angels or miracles, the grammar shows **text only** (the passage), never an image or effect.

### 3.11 Sound

See `SOUND.md`. In the grammar's terms: sound is a mark like any other, needs provenance (recordings credited, passages sourced), and never gives a voice to the Prophet ﷺ or the Companions in the first person.

### 3.12 Decoration

- Background stars, the horizon line, the dust band: drawn in `--faint` at < 0.5 opacity, never interactive, never varying with data, never in `--light` or `--person` hues. A "decoration only" note appears in the specimen and the about panel.

---

## 4. Claim types and the marks they license

| Claim (ontology) | Licenses | Requires review status |
|---|---|---|
| Person mentioned in a source (`mrs:Assertion`, `fromReport`) | a light at `--gen-unknown`, or an absence mark if unnamed | proposed or better (drawn with dashed ring until accepted) |
| Generation recorded | brightness | accepted |
| Companionship (`rel_companion_of`) | gen-1 brightness; رضي الله عنه/عنها | **scholar-accepted** |
| Opposition (`rel_opposed`, `rel_fought_against` + `atEvent`) | stone for the time span | accepted |
| Acceptance of Islam (relation type to be added) | stone → light transformation at the date | accepted; disputed dates drawn with rings |
| Participation (`mrs:Participation`) | constellation line | accepted, or "unreviewed list" note |
| Transmission (`mrs:TransmissionChain`, `TransmissionLink`, `ContactCheck`) | chain, links solid/dashed | as recorded in the collection |
| Place location (`LocationConfidence`, `GeometryState`) | place ring + certainty ring | any; certainty drawn |
| Coverage state (`cs_*`), `mrs:CoverageGap` | absence mark | any |
| Dispute (`mrs:Dispute`, `mrs:Position`) | dispute ring; positions listed | any; positions attributed |
| Weather / season passage | atmosphere | accepted passage |
| Computed metric (degree, layout) | size only in a labelled coverage view | n/a; always labelled "computed" |
| Model output | **nothing** | never |

---

## 5. Forbidden

1. Any figurative depiction of the Prophet ﷺ, his family, the Companions, the other prophets عليهم السلام, or angels: faces, bodies, silhouettes, shadows, hands, feet, veiled or faceless figures, avatars, mannequins, rigged models, generated images, rotoscope, motion capture.
2. First-person embodiment of any of these people in XR or games (no "see through their eyes", no hands in view). The POV camera of *The Message* (1976) is a reference for restraint only: our camera is the **reader's** and the sky's, never a Companion's or the Prophet's ﷺ.
3. Voicing the Prophet ﷺ or any Companion in the first person (see `SOUND.md`).
4. The central light as a graph node, ranked item, or statistic.
5. Quoting the stars metaphor as hadith.
6. Encoding virtue, rank or Paradise by size, glow, colour or position (except E3 list order, which is a reviewed rule, not an encoding).
7. Gendered colours, shapes or hiding of women as marks (§6.4).
8. Interpolated positions, dates, routes or straight-line routes presented as paths (T3).
9. Battle spectacle: blood, weapons, wounds, impacts, slow-motion deaths, kill counts.
10. Musical instruments in any soundtrack (except the duff, and only if the scholars choose a policy that allows it; see `SOUND.md`).
11. Any mark whose only basis is a model output.
12. Gamified rewards tied to sacred content (points for Companions, "unlocking" a Companion).

---

## 6. Edge cases for the scholars

Each has a proposed default. None ships without a scholar's decision recorded in the review log.

1. **Abū Ṭālib.** Uncle and protector of the Prophet ﷺ; the sources the platform relies on record that he did not accept Islam, and some report otherwise. *Default:* neither stone nor light: a **warm unlit mark** (a stone outline that receives `--light-dim` on its protecting side, no halo), with his protection (`rel_protected`) drawn as a recorded relation and the dispute listed with positions. He is never drawn as an opponent. No honorific of companionship. Needs ruling.
2. **Munāfiqūn.** Hypocrisy is a matter of the heart; the Qurʾān names no individual. *Default:* no person is drawn as a munāfiq. Persons whom sources *report* were counted among them (e.g. ʿAbd Allāh ibn Ubayy) are shown as people of Madina at gen-unknown brightness, without honorific, with the report attributed in the panel ("X reports that…"). No special mark, no stone, unless an opposition claim (§3.3) licenses one for a specific act and time.
3. **Disputed Islam or companionship.** Drawn with the dispute ring; honorific withheld until a scholar accepts companionship; panel lists the positions and their sources.
4. **Women's names.** Women are lights exactly as men are, same colour, same size, same generation rule. Names are shown as the sources give them (often kunya or "daughter of"). *Default:* full name displayed; the scholars may choose kunya-first display for some groups; the Mothers of the Believers always with رضي الله عنهن (group) or رضي الله عنها (individual). No "hidden" or veiled mark, no gendered icon.
5. **Children.** Children recorded in the sources (e.g. those who met the Prophet ﷺ as children) are lights; companionship status follows the scholars' definition. Children who died in infancy: a light at gen-unknown brightness, no stone, no judgement mark, ever. Children of opponents are never stones.
6. **The ten promised Paradise and order (E3).** Order is a list rule: the Prophet ﷺ (outside the list, as the light), al-Khulafāʾ al-Rāshidūn, the ten, then most-connected (labelled count of recorded links). No mark encodes "promised Paradise".
7. **The family of the Prophet ﷺ (ahl al-bayt).** Lights like other Companions; no special halo hue (only `--light` is reserved). Relations to him drawn as recorded relations. Needs ruling on whether a distinct name-panel style is wanted.
8. **Those whose Islam came late (e.g. at the Conquest).** Stone until the recorded date, then light; their later service is never diminished by the earlier stone. The time toggle defaults to the reader's chosen moment, not to "before".
9. **Those who left Islam and returned (ridda).** Not drawn as stones by default; dispute and narrative in text. Needs ruling.
10. **Other prophets عليهم السلام** (e.g. in the Isrāʾ and Miʿrāj narrative). Text and calligraphy only; no lights, no marks in the sky.

---

## 7. Honorific rendering (H1)

| Who | Arabic | Latin text | When |
|---|---|---|---|
| The Prophet | ﷺ (U+FDFA) or صلى الله عليه وسلم | "(peace and blessings be upon him)" on first mention per screen, then ﷺ | always, every mention, including labels, alt text and screen-reader text |
| A Companion | رضي الله عنه / رضي الله عنها | "(may Allah be pleased with him/her)" | only once a scholar accepts the companionship claim |
| Mothers of the Believers | رضي الله عنهن (group), رضي الله عنها (one) | as above | always |
| Other prophets | عليه السلام / عليهم السلام | "(peace be upon him/them)" | always |
| Later scholars and narrators | رحمه الله / رحمها الله | "(may Allah have mercy on him/her)" | deceased only |

Rules:
- The honorific follows the name on the same line; it never wraps alone (`white-space: nowrap` on the name-plus-honorific span).
- Size: 0.85 em of the name, same colour, same weight. Never decorative-coloured, never animated.
- Screen readers: the honorific is spoken in full (not "U+FDFA"); provide `aria-label` with the words in the interface language.
- Labels in dense views may not drop honorifics; if space is short, abbreviate the *name* (kunya) not the honorific.
- Never place ﷺ on a stone, a chain line or a count.

---

## 8. Arabic typography

- **Direction and bidi:** every Arabic run is wrapped with `dir="rtl"` and `lang="ar"`; mixed lines use `<bdi>` around names. Never rely on implicit bidi.
- **Shaping:** never letter-space Arabic (`letter-spacing: 0`), never justify by stretching glyph spacing; use kashīda only from the font's own justification, and never in names.
- **Diacritics:** names show full ḥarakāt only where the source vocalises them; otherwise none. Never add vocalisation by guesswork or by a model.
- **Size:** Arabic set 1.15–1.25× the Latin size beside it (Naskh reads small); minimum 16 px on screen, 20 px in XR at 1 m.
- **Line height:** 1.7–1.9 for Naskh; 2.0 for vocalised Qurʾānic text.
- **Qurʾānic text:** set only from a verified Uthmani text source (credited), in a dedicated Qurʾān font (e.g. KFGQPC Uthmanic Script, licence permitting), within ornate brackets ﴿ ﴾, with sūra:āya reference. Never paraphrased, never animated letter by letter, never placed on the ground or under feet in XR.
- **Transliteration:** ALA-LC-style with macrons and ʿ/ʾ (as the platform already uses), always beside, never replacing, the Arabic.
- **Numerals:** Arabic-Indic digits in Arabic runs; Western digits in Latin runs; Hijri years marked "AH".
- **Calligraphy:** commissioned pieces are credited works with provenance; never auto-generated; never distorted into figures.

---

## 9. Conformance checklist (for each new view)

- [ ] Every data mark opens its evidence on click and keyboard focus.
- [ ] The central light is not in any node list, count or ranking.
- [ ] No size or glow encodes computed data outside a labelled coverage view.
- [ ] Certainty rings present for every dated/located claim.
- [ ] Stones and transformations each cite a reviewed claim.
- [ ] Honorifics follow §7, including screen-reader text.
- [ ] Reduced-motion form verified.
- [ ] No instrument in any audio; every recording credited.
- [ ] No figurative element anywhere, including loading screens, icons and social cards.
