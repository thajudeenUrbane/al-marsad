# Exhibition for a scholar-leader: ranked gaps and build brief (2026-10-24)

The three audits are merged and ranked here, and the build that follows is described. The detail is in the
audit notes: `exhibition-audit-story.md`, `exhibition-audit-experience.md` and `exhibition-audit-scholar.md`
(finding codes A1 to C13 below refer to the scholar audit). The top findings were checked against the code
on 24 Oct. Nothing in the repo has been edited yet. The build waits for the maintainer's go-ahead.

## 1. Ranked gaps

### A. Blockers for today (on or next to the walk)

1. **There is no front door and no ask.** No page says who is behind al-Marṣad, what exists today, or what
   we are asking him for. → Build `exhibition/` (section 3).
2. **The four September pages contradict today** (marsad, build-with-us, road-ahead, reviewers-brief):
   - They say both "Nothing here has been built" and "This is real now".
   - "35 named Companions" counts the Prophet ﷺ among the 35.
   - road-ahead advises against rushing to bring in historians, the opposite of today's ask.
   - "Recorded under your name, permanently" contradicts the pilot guide merged in PR #33, which says
     decisions are credited to the review board unless the reviewer agrees to be named.

   → Don't show or send these pages. Add a "September draft, superseded" banner to each (A4).
3. **The Sky Atlas in Arabic shows an empty sky**, and the browser remembers the choice
   (`marsad-atlas-lang`). Four CSS lines fix it (experience audit §1). `atlas/` belongs to the
   sky-atlas-round3 row. → Send the fix through the Hub. Until it lands, the exhibition patches the Atlas
   at runtime.
4. **Pages garble or go blank when served.** 11 pages have no charset, so they show "AL-MARÁ¹£AD", and
   stories-50 draws nothing. Expeditions fail when opened by double-click. → `exhibition/serve.py` serves
   everything from one place with UTF-8.
5. **Honorifics on the walk path are inconsistent:**
   - The expedition claim sentences say "the Prophet" without ﷺ (37 bare against 28 with it) (A12).
   - The screens use three different honorific forms (A10).
   - There is no convention for the Companions (A11).

   → Fix the expedition templates. State one convention on the opening screen.
6. **Some screens read as the AI ruling** (A1 to A3, A13, A14):
   - The demo labels the Hijrah report "mawqūf". A narration of the Prophet's ﷺ own journey is normally
     marfūʿ, and the system should not classify at all.
   - The demo says "source composed 256 AH", which is al-Bukhārī's death year, and "attestation gap
     c. 248 years".
   - The demo promises "Three disputes" and never shows them.
   - In the Atlas, the dark marks and the fixed order read as judging and ranking people.
   - Hijrah Night shows AI grades ("established", ḥasan) and grade chips on Qurʾān cards.

   → Keep the demo and the lab off the walk. Brief the presenter on the Atlas.
7. **Some errors a scholar will spot at once** (A5 to A9, B1, B8):
   - generation-1 sorts the Ridda wars, Yamāma and Saqīfa before the death of the Prophet ﷺ, and Ḥunayn,
     Ṭāʾif and Tabūk before the Conquest. The cause is placeholder 1-January dates.
   - generation-1 labels Abū Ṭālib "Companion".
   - generation-1 prints "not asserted in this file" for Khadīja, ʿĀʾisha, Ḥamza and 24 others.
   - The data says Usāma appointed the Prophet ﷺ (subject and object are reversed).
   - The data lists Kaʿb b. Mālik at Tabūk. He is one of the three who stayed behind (9:118).
   - ʿĀʾisha and Asmāʾ are called "full sisters". They were half-sisters.
   - Abū Dujāna is said to wear "the Prophet's own headband". The sword was the Prophet's ﷺ; the red
     headband was Abū Dujāna's own.

   → Keep generation-1 off the walk. Correct the data in P1.
8. **Some numbers don't agree from screen to screen:**
   - Badr is 439 in the Atlas tour (story audit), 314 in the expedition and 313 in the well-known report.
   - ʿAqaba is 75, 74 and 77; Abyssinia is 83, 87 and 127.
   - The "7,867 people" are name records, not yet de-duplicated.

   → Add one-line notes on the walk ("313 in the well-known report, 314 in Ibn Isḥāq's list") and say
   "name records" in the exhibition (B3, B4).

### B. Fix soon (after the meeting)

- **Data and dates:**
  - B2: Uḥud day.
  - B5: Qubāʾ and the city entry are merged.
  - B6: Khadīja's acceptance of Islam is missing.
  - B7: Waraqa is recorded as a participant in the first revelation.
  - B18: "standard tradition" is the basis for 54 claims, and 100 seed items have no source.
  - B19: Yamāma AH/CE.
  - C1 to C4, C11, C12.
- **Language:** B9 (lang/dir in the demo), B10 (mixed transliteration), C5, C6, C9.
- **Wording:**
  - B11, B12, B16, B17, C7, C8.
  - Claims to soften: "no existing system" leaves out the Arabic takhrīj tools; "whole Sīra" is Ibn Hishām
    only; computed dates sit beside received dates.
- **PLAN figures:**
  - About 19–20 scholar hours budgeted for about 300 claims, against 863 statements and a 377-item
    checklist.
  - Stipends at about 8–10% of the budget, against the project's own 25% floor.
  - docs/09 still shows rules that round 3 reversed.
  - There are 14 docs, not 13.
- **Layout:**
  - The generation-1 chart is square and its labels are clipped.
  - The reviewers-brief list is squeezed (`ol.losses span{grid-column:2}`).
  - Median text is 10.9 px on a TV, so use browser zoom 125–150%.

### C. For other owners (send through the Hub)

- **`atlas/`** (sky-atlas-round3, PR #35; learn-v2 also rebuilds it):
  - The Arabic layout fix, plus an Arabic layout test in `atlas/check.cjs`.
  - A13 wording.
  - B14: "الحاكم" for the grader.
  - The Badr 439 label.
  - A rebuild after the corpus fixes.
- **`lab/hijrah-night-v2`** (merged with PR #32; no open row):
  - A14 and B13: remove the grade chips from Qurʾān cards, add honorifics for the prophets and Jibrīl,
    and remove the Abū Ṭālib "matters" line.
  - Vendor three.js for offline use. This is a download, so it needs the maintainer's OK.
- **The board:** the rows for PR #32 and PR #33 still say "in review", but both are merged.

### Checked and clean

- No figurative depiction anywhere.
- The four caliphs and the ten are correct.
- The demo's isnād chain and the narrators' death dates are standard.
- The 22 Arabic stage names are free of errors.
- ʿAqaba's 73 men and 2 women is right.
- The AI disclosures are honest.
- Atlas (English) and Expeditions load in under 0.5 s, with no outside requests and no console errors.

## 2. Decisions (the build uses these defaults unless the maintainer changes them)

| # | Decision | Default |
|---|---|---|
| 1 | Credit rule | The pilot guide's rule (PR #33, merged): credited to the review board, by name only if the reviewer agrees. The September pages are marked superseded. |
| 2 | Hijrah Night in the walk | Out. It crosses the red lines (A14) and needs the internet. Nothing is downloaded. |
| 3 | Opening | The basmala as the customary opening formula, in naskh, without Qurʾān brackets. |
| 4 | Companion honorifics | ﷺ always for the Prophet, with the words at the first mention per screen (grammar §7). In the exhibition's own text, رضي الله عنه / عنها at the first mention of a Companion or a Mother of the Believers. Data screens keep the grammar's rule; the convention becomes a question for the scholar. |
| 5 | Atlas in Arabic | Send the four-line fix to the Hub for the Atlas owner. The exhibition injects it at runtime meanwhile. |
| 6 | Presenter's name and contact | Kept in a git-ignored `exhibition/presenter.local.json`, never in the repo. If the file is absent, the page leaves a line to fill in by hand. |
| 7 | Where and how to build | A fresh session on Opus, started after the 5-hour usage window resets. One Sonnet helper does the mechanical fixes and one Opus reviewer checks the result. |

## 3. The exhibition

A new folder, `exhibition/`, which no other row owns. It holds:

- **`serve.py`:**
  - Serves the repo root on 127.0.0.1:8770, sending `charset=utf-8` for HTML, JS, JSON and CSS.
  - Opens the browser at `/exhibition/`.
  - Makes no outside requests.
- **`index.html`:**
  - One full-screen page, driven by the keyboard: → and ← move between halls, 1–8 jump to a hall,
    P shows the presenter notes, T the timer, F toggles full screen, and Esc closes a live view.
  - Night palette, type, motion and reduced-motion follow `lab/design-grammar/GRAMMAR.md`. Gold is used
    only for the central light.
  - Arabic hall titles are set in naskh with `lang="ar" dir="rtl"`.
  - Offline fonts only: DecoType Naskh or Geeza Pro for Arabic, Palatino for display, system-ui for the
    body. Amiri, Marcellus and IBM Plex are not installed, so no Google Fonts.
- **Live views:**
  - Same-origin iframes: the Atlas in English, then Expeditions `#halaqa-badr` and Badr.
  - Each view has a still to fall back on (re-take it with playwright, or copy one from the experience
    audit's shots).
  - Each view has an "open full screen" button.
- **Numbers:** read from the data at build time (`exhibition/build.py`), never typed by hand. A test fails
  if they drift.
- **Presenter notes per hall:** what to show, what to say, what not to click, and likely questions with
  answers.
- **`leave-behind.html`:** one A4 page that prints to PDF. It covers what al-Marṣad is, what exists, the
  three asks, the credit rule, the first step and its date, and the contact.

The walk takes 25 minutes, and the ask begins by minute 20.

| Hall | Title | Min | On screen | Point |
|---|---|---|---|---|
| 0 | Opening · بسم الله الرحمن الرحيم · المرصد | 1 | The basmala, the title, one line, the presenter | Respect |
| 1 | Why · لماذا المرصد؟ | 2 | The Sīra is reported across many books. A reader cannot see where each statement comes from, how it was carried, or where scholars differ. al-Marṣad shows the source of every statement and leaves every ruling to scholars. | The problem |
| 2 | The sky of the Sīra · سماء السيرة | 6 | The live Atlas (English): the central light, one Companion's statements and their sources, the timeline | Wonder and substance |
| 3 | Badr · بدر | 5 | The live Badr expedition, then the halaqa room | Teaching |
| 4 | Where a report comes from · من أين جاء الخبر؟ | 3 | One real statement end to end: the source and page, the chain, the status "proposed", who may rule. "Software never accepts a claim on its own." | Method and adab |
| 5 | What is built, what waits · ما بُني وما ينتظر | 2 | Live numbers; 0 statements reviewed so far; the identity questions; the pilot pack ready to send | Honesty, and the need |
| 6 | What we hope for · ما نرجوه | 4 | Three asks: (1) one scholar reviews the pilot pack (50 statements and the first identity questions) by a date he chooses (we suggest 1 November); (2) his guidance on direction (the round-4 questions); (3) his advice on a custodian and on funding. Then the credit rule. | The ask |
| 7 | Close · الختام | 1 | Thanks, contact, جزاكم الله خيراً | Close |

## 4. Build order

### P0: before the meeting

Tell the maintainer as soon as P0 is ready to rehearse.

1. `serve.py`, `index.html` with the eight halls, the notes, the timer, the live views and stills, the
   numbers and the runtime Atlas Arabic patch.
2. Expeditions on the walk:
   - Add ﷺ in the claim templates (`expeditions/compile/compile.py`, `expeditions/defs/expeditions.json`).
     Never regex-replace the data.
   - Add "313 in the well-known report, 314 in Ibn Isḥāq's list".
   - Say "on the other side" instead of "against him".
   - Fix "the Prophet's ﷺ life".
   - Rebuild `dist`.
3. README: one status paragraph and "start at `exhibition/`".
4. The superseded banner on the four September pages.
5. `leave-behind.html`.
6. A browser check in `scripts/check_all.sh` (playwright):
   - Every hall renders.
   - No console errors and no outside requests.
   - Arabic runs carry lang and dir.
   - ﷺ carries an aria-label.
7. An Opus scholar's-eye review of every word in `exhibition/` and the changed expedition sentences. Then
   fix what it finds, run `bash scripts/check_all.sh`, open the PR and merge on green.

### P1: if time allows, otherwise after the meeting

- **demo:** A1 to A3 and B9.
- **stories-50:** add the charset.
- **generation-1:** A5 to A7 and B11, or a "prototype, order not yet checked" banner.
- **ontology/corpus:** correct A8, A9, B1 and B8, then rebuild generation-1 and ask the Hub for an Atlas
  rebuild.

### P2

Sections 1B and 1C.

## 5. Rules for the build session

- **Branch:** main has moved to a75cd2d (PR #33, pilot pack; it touches none of the files above). Merge it
  into `claude/exhibition-scholar-presentation-72dff5`, or branch fresh from main.
- **Board:** update the row on the `coordination` branch with the branch and the wider scope: `exhibition/`,
  `expeditions/compile`, `defs` and `dist`, README, `pages/`, `demo/`, `generation-1/`, `stories-50/`, and
  `ontology/corpus` for P1.
- **Other owners:** the open branches touch only `atlas/`, `ask/`, `learn/`, `site/`, `docs` and
  `ontology/shacl_check.py`. Don't edit `atlas/`, `ask/`, `learn/`, `site/`, `review/` or `lab/`; send
  those fixes through the Hub.
- **Design grammar (binding):**
  - No figurative depiction, no rank encoding and no battle spectacle.
  - Gold only for the central light.
  - Metaphor captions read "In this sky, we show…".
  - Arabic follows §8.
  - The Qurʾān only from a verified Uthmani source.
- **Offline:** no CDN and no Google Fonts.
- **Helpers:** at most two. Each writes its notes to `docs/handover/exhibition-build-*.md` and returns at
  most 15 lines.
- **Before pushing:** run `bash scripts/check_all.sh`.
