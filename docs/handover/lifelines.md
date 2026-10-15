# Lifelines handover

Brief: docs/handover/lifelines-brief.md, plus the maintainer's refinements relayed during the work (perpendicular connectors; M4a–M8). Nothing shown is verified history: every date, line and age is proposed and unreviewed, and the page says so in a banner, the legend and every detail.

## What exists (all under site/lifelines/)
- `build_lifelines.py` writes one self-contained page, `site/dist/lifelines/index.html` (inline CSS, script, strings and data; system fonts; no request leaves the page). Standalone: it does not use or change site/build.py; if site/dist is missing it creates it with site/build.py's marker. `--reader-base ''` drops reader-page links for publishing the page on its own.
- `calendars.py` (day numbers, Julian/Gregorian, tabular Hijri, BH years, lunar 354.367 / solar 365.2425-day ages), `lives.py` (a line: birth/death ranges, the certainly-alive stretch, open ends, ages at events), `collect.py` (the sources), `lifelines.js`, `lifelines.css` (logical properties, dark, every colour explicit), `i18n/en.json` (every UI string).
- Tests: `tests/test_lifelines.py` (40 unittest tests on fictional fixtures in tests/fixtures, plus repo checks: no entity ID in code, every script string exists, logical CSS, the site's HTML check on the page) and `tests/check_lifelines.cjs` (Playwright, 46 checks).

## Sources and rules
- Graph: event dates, 7 deaths (fields, no status), participations and "took part" assertions ("absent from" excluded), ṭabaqa, kinship, membership, places of events, chain links.
- Wikidata (ontology/corpus/external-dates.csv; until it lands on main, read from origin/slice-5-links with `git show`): one item per person (exact, else a single probable); its preferred-rank value drawn, other values listed as alternatives; with no preferred value, differing values give their range. Needs-review candidates only behind the toggle, only for people with no better match, never mixed. Earliest/latest and refine-date qualifiers widen a range, never narrow it; circa is said in words (no width invented). Century precision is listed, not drawn (it read as ages like "8–114"). Labelled "proposed: from Wikidata Q…".
- Ibn Hishām (ontology/corpus/ibn-hisham.ttl; until it lands, from origin/slice-4-ingest, IDs mapped through id-renames.csv into build/lifelines-graph.ttl): ages as given are hollow diamonds beside the age computed from dates, never merged, never converted ("years as given"); deaths during a dated event take its recorded date; a birth/death event takes that person's recorded date; dates as written are shown in words; by age, a line with no birth date is placed by its anchors, never past the last one. Persons not yet in main get no reader link.
- A year is the whole year; sources that disagree give the range; unknown ends fade over a fixed few pixels; people with no placeable date are listed. Ages are labelled computed, in completed years, as ranges.

## The view
- By date (default): CE axis with a Hijri axis beside it; dashed lines; each event a perpendicular connector from topmost to bottommost participant, a hairline for a day, a hatched band as wide as the date's uncertainty; nodes only on participants; a visible gap (background halo) where it crosses anyone else.
- By age: lines from 0, computed age labels, no slanted lines; a tap highlights the event on every line. Lunar/solar toggle. Morph between date and age (instant under reduced motion).
- Order by birth, ṭabaqa, family, tribe (disabled until membership is recorded) or transmission links; filter by an event's people or a person's circle, by name; needs-review toggle; zoom buttons, ctrl+wheel, pinch; "Showing N of M"; Reset view; URL keeps the view; table alternative also without JavaScript.
- M4a ages at one moment (an event, or a CE/AH/BH year): moment line, present / alive / possibly alive with computed ages. M4b aged under N at the Prophet's ﷺ death, years lived after, neutral wording, birth order.
- M5 by family: parents above children, spouses beside; each tie a dotted bracket beside the axis (no tie has a date, so none is placed on it), with status and source.
- M6 by place: a lane per place in order of first dated presence, plus "place not recorded"; a line steps into a lane only for the date range of a dated event there it took part in (or a dated affiliation). Undated place claims are listed, not drawn.
- M7 overlap check: for each recorded link "A received from B", computed overlap of the lives and any shared recorded place; "lives don't overlap: for scholars to review" is a flag, never a verdict; "the system flags; scholars rule" is stated on the page. Nothing is written back.
- M8 colour by generation (switch, off by default): colour and dash by recorded ṭabaqa, grey where none; shaded years where consecutive generations coexist.

## Numbers (after rebasing on main 6f85512; slice-5 966fcee, slice-4 d25926e)
145 of 320 people have a line by date (+6 only from needs-review matches); 169 have no placeable date. Drawn dates: 270 Wikidata, 14 Ibn Hishām, 6 graph. 20 ages as given. 54 events on the chart (49 of 115 events placeable). 34 kinship ties, 43 places (60 people with a dated place). 28 transmission links: 6 overlap, 1 possible, 21 cannot be checked (missing dates), none flagged yet. Generation windows: 649–711 and 713–741 CE. Page 849,901 bytes.

## For a human
- scripts/check_all.sh is CI-owned. To run these in CI, after the site build: `step "site/lifelines: build" "$PY" site/lifelines/build_lifelines.py`, `step "site/lifelines: page" browser_check site/lifelines/tests/check_lifelines.cjs`, `step "site/lifelines: tests" "$PY" -m unittest discover -s site/lifelines/tests`. check_budget already gives lifelines/ the 2 MB budget; the page passes check_html.
- In CI without the branches, the builder uses only the graph (and the two files once they are on main); it never fetches.
- Graph bounds are read as Julian dates (17 Ramaḍān 2 AH = 13 March 624 is the Julian tabular conversion); say if that is wrong.
- "Colour by generation" spends hue on ṭabaqa, which doc 04 §3 reserves for type: it is a named, off-by-default switch with dashes as well; say if it should go.

## Verify
`.venv/bin/python ontology/build_graph.py && .venv/bin/python site/lifelines/build_lifelines.py && .venv/bin/python -m unittest discover -s site/lifelines/tests && NODE_PATH="$(npm root -g)" PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers node site/lifelines/tests/check_lifelines.cjs site/dist`
