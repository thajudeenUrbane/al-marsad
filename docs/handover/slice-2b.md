# Slice 2b handover: search with spelling tolerance

Spec: docs/handover/slice-2-brief.md, part 2b. No data changed, no status upgraded, no name or Arabic text invented: an Arabic query reaches a name the graph holds only in Latin letters through a sound key, and the page says so.

## What exists (all under site/)
- `names.py`: the one place for name rules. Display (popular form, used by `display.py`, which keeps only the `EXPAND_B_TO_IBN` switch) and search (normal form, sound key, ranking) share its tables: ayn/hamza marks, sun letters, the article, b. = ibn.
- `static/search.js`: the browser port, step for step, with no table of its own; it reads `names.RULES` from `search.json`. The site's only script, loaded by the search page alone (9,973 bytes).
- `search.json` (built): `{v, rules, items: [{u: "person/<id>", n: name as shown, k: [normal keys]}]}`; 314 items, 32,199 bytes. Keys: name as shown, labels as recorded (scholarly form), Arabic and other-language names, and a person's ism, kunya, laqab, nisba and full form (not nasab: that is the father).
- `search/`: without JS, a note and every name A to Z (314 rows), the target of the search box now in every page header (`templates/search_box.html`). With JS it filters as you type, puts `?q=` in the address, and lists "Matching names" (tiers 0-3) and "Similar spellings" (4-8), each line a copy of the A-Z line (type and coverage as text).
- Empty result (docs/05 §3): "No name matches “q”", what a search looks through (counts linked to the five indexes; only 7 names in Arabic script), that none of the corpus is reviewed, and that a missing name has most likely not been added yet, which says nothing about the sources. The no-JS note carries the same coverage text, so the fallback is never a blank either.
- `check_budget.py` counts any file a page names in `data-fetch` (the index). Search page: 115,234 bytes (HTML 65,042 + CSS + JS + index).
- `check_search.cjs` (Playwright, JS on and off); `tests/test_search.py`, `tests/search_cases.json` (96 shared cases), `tests/search_parity.cjs` (runs search.js under node).

## Rules (names.py has the full list)
Normal form: drop ﷺ and ʿ ʾ ' marks; NFKD and drop combining marks (Latin diacritics, tashkil, the hamza of أ إ آ ؤ ئ); lower case; ٱ→ا ة→ه ى→ي, tatweel out, Persian/Urdu ک ی ہ to Arabic, Arabic-Indic digits to 0-9; article al-/el-/as-/ash-... and Arabic ال optional; b., bin, ibn unified, likewise bint/bt., abu/abi/aba, um/umm, abdul/abdur → abd, ابن/بن, ابو/ابي/ابا. The last word of a query stays as typed (it may be half a word).
Sound key: consonant classes (th/s/ص/ث → s, dh/z/ذ/ظ → z, kh/خ → x, sh/ش → c, q/c/ق/ك → k ...), vowels, w, y, ا و ي ع ء dropped, runs collapsed, final h dropped.
Tiers: 0 whole name, 1 start, 2 start of each word, 3 inside; 4 same sound key, 5 sound start, 6 one letter off, 7 sound at a word start, 8 sound inside. Ties: how well the name as shown matches, then key length, then A-Z.

## Results (graph after slice 1e)
- All five required queries list Abū Bakr first: "Abu Bakr", "Abū Bakr", "abubakr" at tier 0 (his kunya), "ابو بكر" and "أبو بكر" at tier 4 under "Similar spellings", with the note that Arabic is matched by sound. He is found by his recorded name in tests, never by ID.
- Also: Usman / عثمان → Uthman b. Affan; Mohammed / محمد → the Prophet ﷺ first; Medina → al-Madina; Mecca → Makkah; مكة → Makkah (recorded Arabic, tier 0); "Abu Bark" → Abū Bakr (one letter off); "zzqx" → the empty state.
- Python and JS agree on all 96 cases and on every test query over the real index (`node` v22 here).

## Name display (2a leftover)
al- now assimilates before a sun letter in every label, not only scholarly ones: 25 names changed, e.g. Anas ibn al-Nadr → Anas ibn an-Nadr, Suhayb al-Rumi → Suhayb ar-Rumi, al-Ta'if → at-Ta'if, al-Sham → ash-Sham, Ahl al-Suffah → Ahl as-Suffah. `b.` stays as recorded (`display.EXPAND_B_TO_IBN = False`); search treats b./bin/ibn alike either way. URLs are unchanged.

## For a human to decide
1. Arabic names: the graph has them for 6 places only; identity.csv `name_ar` is empty for every person. With scholar-sourced Arabic names, Arabic queries would match exactly instead of by sound.
2. The sound key merges letters on purpose (عمر finds Umar and Ammar first, then 31 similar names). Say if scholars want it stricter.
3. Plurals are English one/other, chosen in JS; the Arabic UI (slice 9) needs `Intl.PluralRules`.
4. Only names are searched, not story text.

## Verify
`.venv/bin/python ontology/build_graph.py` (CONFORMS) `&& .venv/bin/python site/build.py && .venv/bin/python site/check_budget.py && .venv/bin/python site/check_html.py` (all exit 0).
`.venv/bin/python -m unittest discover -s site/tests` (91 OK, includes the node parity tests).
`NODE_PATH="$(npm root -g)" PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers node site/check_search.cjs site/dist`: OK (five queries with JS on, header box, live typing, empty state; JS off: box submits, 314-name A-Z list, no external request). `site/check_nojs.cjs`: OK. `grep -nE "left|right" site/static/*.css`: nothing.
