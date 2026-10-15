# Slice 2a handover: static generator and pages

Spec: docs/handover/slice-2-brief.md, part 2a. Nothing shown is verified history. Every claim is `proposed`, every record `stub` or `outline`. No status was upgraded; no Arabic name, date or summary was invented.

## What exists (all under site/)
- `build.py` reads build/graph.ttl only (runs ontology/build_graph.py if it is missing) and writes site/dist/ (gitignored, added to .gitignore). `model.py` is the only rdflib code and hard-codes no entity ID.
- `render.py`, `templates/` (string.Template), `i18n/en.json` (every UI string is a key; a test fails on literal text in templates or HTML-building code), `static/site.css` (logical properties, system fonts, one file, no JS).
- `display.py`: every maintainer display rule, one place each (names, the sign for the Prophet, Companion honorific, dates, sorting). `glossary.py` + `data/glossary.json`.
- Checks: `check_budget.py` (fails over 300,000 bytes per page, or any external load; prints the 5 heaviest), `check_html.py` (tags close, one h1, landmarks, skip link, unique ids, links resolve, no link in a link, licence footer), `check_nojs.cjs` (Playwright, JS off), `tests/` (64 unittest tests).
- Licence footer on every page (shared `templates/base.html`, strings are `footer.*` keys): "Text and data: CC BY-SA 4.0 · Code: AGPL-3.0 · IDs: CC0 — al-Marṣad contributors"; the two licence names link to the licence texts, the rest to LICENSING.md on GitHub. check_budget does not flag these (plain `<a href>`); check_html and a test fail any page without them.

## Numbers (graph of 15 Oct 2026)
321 HTML pages: 184 person, 12 group, 22 place, 46 event, 50 story, 5 type indexes (A-Z, counts, coverage; stories also in reading order), home, glossary. Plus 314 `entity.ttl`. Heaviest page: the Prophet's, 74,182 bytes (HTML 67,377 + CSS 6,805); then Abū Bakr's, 49,689. No JavaScript.
Abū Bakr's page (found by name in tests, never by ID): 16 stories, 31 events and incidents, 3 kinship ties, 4 other ties, each row with status and source; the details layer lists the 4 recording sources (50 Stories conversion, seed incidents, generation-1, Ghar Thawr example); his scholarly name is in details only.
Participations, "took place at" and part-of links are not Assertions: they show "Status: not recorded". Death dates and the like are fields, not claims; a note under the top facts says so.

## Display rules and where they live
Names: popular form from the graph label. A label with no scholarly mark (no diacritic, no ʿ ʾ) is shown as written; otherwise ʿ ʾ dropped at word start, apostrophe inside, diacritics stripped, al- assimilated before sun letters (Abū Bakr al-Ṣiddīq -> Abu Bakr as-Siddiq). Dates: Gregorian first, Hijri in brackets, "around" for c., converted dates carry method and ±days. Places: label as recorded, Arabic beside it. The Prophet: own layout (no fact box), sign in every name and note. Stories: draft banner at top; AI note in details. Groups: full pages and index.

## Not applied because the graph lacks the field
- Companion honorific: no person has `companionStatus` and the ontology has no gender field, so it shows nowhere. 53 people carry `tabaqa = ṣaḥābī`; I did not treat that as "recorded as a Companion". Needs a gender field and a ruling (`display.GENDER_PREDICATES`, `companion_honorific_key`).
- Modern place names (bracketed): none in the graph. al-Madina's second label "(formerly Yathrib)" and its two Arabic names appear in the name line/details only.
- Arabic names: only 6 places have them; people and groups have none in the graph. Hijri: shown only where the record has it; 7 people have a death date.
- Possibly-same people: nothing read or shown (the graph holds no identity assertions).

## For a human to decide
1. `b.` vs `ibn`: left as recorded (`display.EXPAND_B_TO_IBN = False`). Labels already free of marks keep their al- ("Anas ibn al-Nadr"), so assimilation is not uniform; say if it should be.
2. Story prose is stored verbatim; the display adds the sign after 4 mentions that lacked it (stories 2, 29, 41, 44), never in "I am the Prophet". Say if prose should be shown untouched.
3. Glossary: 7 terms defined, quoted from docs/00 §2, docs/02 §7.4 and ontology/marsad.ttl (a test checks each quote); 36 listed "definition needed" (ṣaḥābī, ḥadīth, sīra, mawlā, bayʿa, ...). No definition was written.
4. The Work note shown in the story details still says "The maintainer's Claude Doc" until slice 1d lands; the AI note is a UI string and does not depend on it. After 1d's renames URLs change (they follow the ID payload) and no redirects exist.
5. Events with the same name (two "The Battle of Hunayn") stay separate pages, as in the graph.
6. Links are directory URLs: view with `python -m http.server -d site/dist`. Hosting is out of scope.

## Verify
`.venv/bin/python ontology/build_graph.py && .venv/bin/python site/build.py && .venv/bin/python site/check_budget.py && .venv/bin/python site/check_html.py` (all exit 0).
`.venv/bin/python -m unittest discover -s site/tests` (64 OK; includes a two-process, two-hash-seed determinism check).
JS off: `NODE_PATH="$(npm root -g)" PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers node site/check_nojs.cjs site/dist` loads 9 pages (home, the person and story indexes, glossary, and one person, story, event, place and group page) with JS disabled, checks h1, nav, footer, CSS applied, coverage and status text, follows person -> story -> breadcrumb, and fails on any request off localhost: OK.
`grep -nE "left|right" site/static/site.css` finds nothing.
