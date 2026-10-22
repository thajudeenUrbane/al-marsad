# Designer brief: the night world of al-Marṣad

**For:** a visual designer (identity, interface and motion), 12 weeks.
**From:** the al-Marṣad maintainer. **Read first:** `GRAMMAR.md` (binding), `SOUND.md`, `index.html` (specimen), and the prototype `lab/hijrah-night/template.html`.

## 1. What al-Marṣad is

An evidence-anchored learning platform for the Sīra (the life of the Prophet ﷺ). Every fact on screen comes from a recorded claim with a source, and every mark can be opened to show it. Its visual world is a **night sky**: the Prophet ﷺ is the light at the centre, those who accepted Islam are lights, opponents are dark stones that may turn to stars when a recorded acceptance of Islam is reached, unknowns are drawn as honest absence, and the chains of transmission rise like threads of light.

## 2. Goals

1. A coherent, beautiful, **aniconic** identity: no figurative depiction of any person, ever.
2. Make evidence and uncertainty legible and calm: certainty, dispute and absence are designed, not hidden.
3. One system from a child's first story to a researcher's isnād view.
4. Trust from scholars: every mark defensible in front of the board.

## 3. Audiences

| Audience | Needs | What the night world gives them |
|---|---|---|
| Children (7–12), with parent or teacher | wonder, simple stories, nothing frightening | guided journeys (Hijrah Night), lights appearing, names in calligraphy, no battle imagery |
| Teens and general learners | narrative, places and time, who was who | the Sky, Lifelines, maps with honest uncertainty |
| Teachers and imams | reliable references, printable sheets | panels with sources, consistent honorifics, classroom mode |
| Students of knowledge | Arabic texts, chains, positions in disputes | isnād chains, dispute rings, Arabic-first panels |
| Researchers | coverage, data, review status | coverage view (labelled counts), review status, exports |

Arabic and English are both first-class; layouts must mirror for RTL.

## 4. Constraints (non-negotiable)

- **Aniconism:** no faces, bodies, silhouettes, hands, footprints shaped as feet, avatars, figures in mosques, crowds, armies or caravans of people. Camels, tents, palms and landscapes are allowed **without riders or people**. Check every icon, illustration, loading screen and social card.
- **The light is reserved:** `--light` (#ffd486) is for the Prophet ﷺ and the light he lends. Do not use it for buttons, links or brand accents.
- **No metric on the light**, no rank or virtue encoded by size or glow; brightness = generation only.
- **Honorifics** always rendered per `GRAMMAR.md` §7; never dropped for space.
- **The stars metaphor** is ours; never typeset as a hadith or with hadith styling.
- **No AI-generated imagery** anywhere (including mood boards shared outside the team and marketing).
- **No instruments** in any motion piece's sound; see `SOUND.md`.
- **Accessibility:** WCAG 2.2 AA; reduced-motion versions of all motion; 44 px targets; full keyboard paths.
- **Performance:** the sky must run on a mid-range phone; SVG/Canvas first, WebGL optional; no external fonts beyond the agreed open-licence set.
- **Licensing:** all type and assets under licences compatible with the repo's `LICENSING.md`; credit everything.

## 5. Deliverables (12 weeks)

| Weeks | Deliverable |
|---|---|
| 1–2 | Immersion: read the grammar, the prototype, sit with the maintainer and one scholar. **Audit** of the prototype against the grammar (one page). Mood references (non-figurative only). |
| 3–4 | **Identity:** wordmark (Arabic and Latin, "al-Marṣad / المرصد"), a non-figurative mark (observatory, astrolabe or star-geometry derived), colour system refined from the tokens (light and dark night variants, print variant), type system with Arabic pairing tests. |
| 5–6 | **Mark library:** final drawings and motion specs for every vocabulary item: light, lights by generation, stones and transformation, absence, certainty rings (all six states), chains, constellations, places, decoration. Each with reduced-motion form. Delivered as SVG + tokens JSON + Figma library. |
| 7–8 | **Key screens:** Sky (child and researcher density), Hijrah Night journey (3 stations), a person panel (light, stone, disputed), an isnād panel, Lifelines, mobile and RTL versions. |
| 9 | **Calligraphy commission brief:** name panels for the Prophet ﷺ (hilye-style text panel) and for the Companions; identify calligraphers, licence terms. |
| 10 | **Motion:** 3 short pieces (≤ 30 s): the sky waking, a stone becoming a star (X1) with its evidence panel, a chain rising. Silent masters, plus a sound brief per piece. |
| 11 | **Scholar review round:** present to the board; log each decision; revise. |
| 12 | **Handover:** updated `index.html` specimen, design tokens, Figma library, usage guide, social and print templates (no figures), and a list of open questions. |

## 6. References to study

- **Ottoman hilye** (especially Hâfiz Osman): describing the Prophet ﷺ in text, arranged with dignity; our model for name-panels and for "portrait by words".
- ***The Message*** (1976, Moustapha Akkad): restraint in showing presence through the camera and the reactions of a scene, without depicting him. Study the restraint; our camera is the reader's, never a person's.
- ***Notes on Blindness*** (VR, 2016): people present as light and binaural sound; the model for presence without figures.
- ***Never Alone*** (2014): community voices and cultural insight videos woven into play; the model for scholar voices.
- Islamic geometric star patterns and astrolabe engraving: construction lines as a visual source for chains and constellations.
- Manuscript practice: rubrication, marginal glosses, isnād layout in hadith manuscripts; how a page shows source and commentary.
- Night photography of the Ḥijāz (credited, with no people) for palette and horizon.
- Data visualisation of uncertainty (dashed, hatched, ringed encodings) for certainty rings.

## 7. Working arrangements

- Weekly 45-minute review with the maintainer; scholar touchpoints at weeks 2, 6 and 11.
- Every artefact names its source (for data) and its licence (for assets).
- Questions about what may be shown go to the board through the maintainer, never decided by the designer alone. When unsure, show less.
