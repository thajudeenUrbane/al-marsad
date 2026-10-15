# Lifelines handover

Brief: docs/handover/lifelines-brief.md, plus the maintainer's refinements relayed during the work (perpendicular connectors; M4a–M8). Nothing shown is verified history: every date, line and age is proposed and unreviewed, and the page says so in a banner, the legend and every detail.

## What exists (all under site/lifelines/)
- `build_lifelines.py` writes one self-contained page, `site/dist/lifelines/index.html` (inline CSS, script, strings and data; system fonts; no request leaves the page). Standalone: it does not use or change site/build.py; if site/dist is missing it creates it with site/build.py's marker so a later site build may replace it. `--reader-base ''` drops reader-page links for publishing the page on its own.
- `calendars.py` (day numbers, Julian/Gregorian, tabular Hijri, BH years, lunar 354.367 / solar 365.2425-day ages), `lives.py` (what a line is: birth/death ranges, the certainly-alive stretch, open ends, ages at events), `collect.py` (the sources), `lifelines.js`, `lifelines.css` (logical properties, dark, every colour explicit), `i18n/en.json` (every UI string).
- Tests: `tests/test_lifelines.py` (unittest, fictional fixtures in tests/fixtures) and `tests/check_lifelines.cjs` (Playwright).

## Sources and rules
- Graph (build/graph.ttl): event dates, 7 deaths (fields, no status), participations and "took part" assertions ("absent from" is excluded), ṭabaqa, kinship and membership claims.
- Wikidata (ontology/corpus/external-dates.csv; until it lands on main, read from origin/slice-5-links with `git show`): one item per person (exact, else a single probable); its preferred-rank value is drawn and other values are listed as alternatives; with no preferred value, differing values are drawn as their range. Needs-review candidates only behind the toggle, only for people with no better match, never mixed. Earliest/latest and refine-date qualifiers widen a range, never narrow it. Century precision is listed, not drawn.
- Ibn Hishām (ontology/corpus/ibn-hisham.ttl; until it lands, from origin/slice-4-ingest, IDs mapped through id-renames.csv into build/lifelines-graph.ttl): ages as given (hollow diamonds, never converted, beside the computed age, never merged); deaths during a dated event take the event's recorded date; a birth/death event takes that person's recorded date; dates as written are shown in words; by age, a line with no birth date is placed by its anchors and never drawn past the last one.
- Precision: a year is the whole year, a month the whole month; sources that disagree give the range; an unknown end fades over a fixed few pixels. People with no placeable date are listed under "No dates recorded yet". Ages are always labelled computed, in completed years, as ranges.

## The view
- By date (default): one CE axis with a Hijri axis beside it; each person a dashed line (proposed); each event a perpendicular connector from the topmost to the bottommost participant, a hairline for a day and a hatched band as wide as the date's uncertainty; a node only where it meets a participant; a visible gap (a background halo) where it crosses anyone else.
- By age (secondary): every line starts at 0; nodes with computed age labels, no slanted lines; a tap highlights the same event on every line. Lunar/solar toggle, labelled. Morph between the two (instant under reduced motion).
- Order by birth, ṭabaqa, recorded kinship, or tribe (disabled until membership is recorded); filter by an event's participants or a person's circle, found by name; needs-review toggle; zoom buttons, ctrl+wheel and pinch; "Showing N of M"; Reset view (brings the Prophet's ﷺ line into view, no emphasis); URL keeps the view.
- M4a ages at one moment (from an event or a CE/AH/BH year): a moment line, who was present, alive or possibly alive, with computed ages. M4b aged under N at the Prophet's ﷺ death, with years lived after (neutral wording, by birth order).
- Table alternative (also without JavaScript), legend, sources, "what this view cannot show yet".

## Numbers (15 Oct 2026, slice-5 39261be, slice-4 1f4b2cd)
138 of 210 people have a line by date (+7 only from needs-review matches); 65 have no placeable date; 53 events on the chart; page about 0.7 MB.

## Not done / for a human
- scripts/check_all.sh is CI-owned: to run these checks in CI add `"$PY" site/lifelines/build_lifelines.py`, `"$PY" -m unittest discover -s site/lifelines/tests` and `node site/lifelines/tests/check_lifelines.cjs site/dist`. The page passes site/check_html.py; at 0.7 MB it is over the reader-tier 300 KB budget that site/check_budget.py applies, so build it after those checks or teach the budget the 2 MB interactive tier.
- Graph bounds are read as Julian dates (the graph's 17 Ramaḍān 2 AH = 13 March 624 is the Julian tabular conversion); say if that is wrong.
- Circa (P1480) is shown in words; no width is invented for it.

## Verify
`.venv/bin/python ontology/build_graph.py && .venv/bin/python site/lifelines/build_lifelines.py && .venv/bin/python -m unittest discover -s site/lifelines/tests && NODE_PATH="$(npm root -g)" PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers node site/lifelines/tests/check_lifelines.cjs site/dist`
