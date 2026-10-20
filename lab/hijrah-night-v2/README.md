# Hijrah Night v2

The Hijrah as a complete, step-by-step journey: **150 stages in 10 acts, 863 graded statements**, over the real terrain of the Ḥijāz. It replaces prototype 1 (10 chapters, 277 claim glosses).

```bash
python3 lab/hijrah-night-v2/build.py                  # validates every act, then writes index.html
python3 lab/hijrah-night-v2/tools/review_checklist.py # writes REVIEW-CHECKLIST.md for scholars
```

| Act | Title | Sections of Ibn Hishām |
|---|---|---|
| 1 | Makkah under pressure | persecution, Abyssinia, the boycott, S0583–S0591 |
| 2 | Seeking a home | S0592–S0615 |
| 3 | The night pledge at ʿAqaba | S0616–S0658 |
| 4 | The ones who went ahead | S0659–S0677 |
| 5 | The plot | S0678–S0682 |
| 6 | The night of leaving | S0680–S0692, S0700 |
| 7 | Three nights in the cave | S0685–S0689 |
| 8 | The road north | S0688–S0696 |
| 9 | Arrival at Qubāʾ | S0696–S0702, S0741, S0744 |
| 10 | Into Madinah | S0703–S0723, S0860–S0861 |

## How it was made
- Ten authors each read the Arabic of their sections (`tools/section_text.py`, from the git-ignored OpenITI cache) and drafted stages to `SCHEMA.md`. This follows the maintainer's round 3, G3: Claude drafts, a scholar edits and approves, and the AI part is said openly.
- Every statement carries one grade:
  - **established:** Qurʾān, authenticated ḥadīth, or agreement of independent sources.
  - **supported:** an early narration.
  - **disputed:** always with the reason.
  - **reconstruction:** the environment only, with its basis.
- `tools/validate_act.py` rejects:
  - a missing source, grade or basis;
  - an unknown place key or invented coordinates;
  - running Arabic text;
  - the "prophet" light role for anyone other than the Prophet ﷺ.
- Grades across the whole journey: supported 537, established 140, disputed 134, reconstruction 52. The journey also has 113 questions, 116 Explore moves and 30 Qurʾān cards.
- ḥadīth and outside references were cited from memory and are all marked **to verify**. `REVIEW-CHECKLIST.md` lists 377 items: every such reference, every disputed statement and every Qurʾān link.

## What the page does
- **Navigation and orientation:** a journey navigator with progress, a mini-map, and a route ribbon. Unlocated stations, for example 19 of the 22 in S0696, are dashed and never drawn.
- **The scene:** each stage sets the camera, the people as lights, stones and groups, and the sky (night, dawn, day, midday heat, dusk; the sky is labelled a reconstruction).
- **The reading panel:**
  - statements with grade badges and source chips, and a filter by grade;
  - Qurʾān cards that give the meaning in our own words and link to the verse;
  - people cards and "Explore" moves that fly the camera and reveal a graded statement;
  - guess-first, recall and reflection questions;
  - an "In the graph" drawer with the AI-extracted claims of each section.
- **See the whole view:**
  - every panel (controls, journey list, mini-map, route, reading panel) can be minimised to a dot in a corner, and the dot can be dragged to any corner;
  - **Full view** (button or **F**) hides everything behind one dot, and **Escape** returns;
  - this comes from the shared module `lab/shared/dock/`.
- **Learner state:** your sky (people met, stages to revisit) and saved progress, both kept only in the browser.

## Known gaps
- Hadith numbering and wording are unverified until a scholar checks them.
- Some cited sections (for example S0586, S0589, S0632, S0682 and S0689) are not yet in the passages file, so their pages show "page not yet indexed".
- The places table is curated for this journey. The full pass (`lab/places-pass/`) proposes more places, and their certainty needs sign-off.
- Close-up terrain is about 1 km per cell. Gaussian-splat landforms of Thawr, Qubāʾ and Uḥud are a later step (X8).
