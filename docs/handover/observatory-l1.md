# Observatory L1 handover: the interactive graph view

Brief: docs/handover/observatory-l1-brief.md. Nothing shown is verified history: every claim is `proposed`, the page says so in a banner, the legend and every status label, and no status is upgraded. No date, place, chain or name is invented; nothing is interpolated across unknowns.

## What exists (all under site/observatory/)
- `build_observatory.py` (standalone) reads build/graph.ttl through site/model.py and site/display.py (same names, dates, URLs and statuses as the reader pages) and writes **site/dist/observatory/index.html**: one file, CSS, script, strings and data inline, no external request, system fonts, **453 KB** (budget 2 MB). Works opened from disk or published alone; `--reader-base URL` points its "Read" links at the reader pages (default `../`), `--ask-url` sets the Ask link (default: `../ask/` only if site/dist/ask/index.html exists; hidden today).
- `obsdata.py` (nodes, links, claims, sources, reports, chains; no entity ID anywhere), `frames.py` (the five frames), `static/` (template, CSS with logical properties only, Canvas 2D script), `i18n/en.json` (every UI string), `tests/` (19 unittest tests), `check_observatory.cjs` (Playwright, JS on).

## The morph field (docs/04 §2): five precomputed frames, one slider, animated (instant with reduced motion)
- **Relationship**: spring layout, start points hashed from each IRI, springs 1/sqrt(deg·deg) so a story gathers its people; smaller unlinked parts in a row beneath; items with no link on a shelf. Byte-identical across builds and hash seeds (tested).
- **Time**: Gregorian-year axis; events by their recorded ranges (bars, not points); people at the dated events they took part in ("absent from" never counts) or a recorded death, gaps left empty; ṭabaqa-only people in a labelled generation band off the axis; the rest on "No date recorded".
- **Geography**: the 6 places with WKT points (equirectangular, degree grid, no basemap); events at their recorded place; people only by their own place claims or affiliations (the place recorded most often; the panel lists all); the rest on "No place recorded".
- **Stories**: the 50 Stories on a dial in reading order by part; people and groups inside near their stories; the rest on a shelf.
- **Transmission**: the one recorded chain (ʿĀʾisha → … → Yaḥyā b. Bukayr, collector al-Bukhārī with no drawn line, since none is recorded), labelled as the start of a feature that grows with Ibn Hishām's reports.

## Verbs, lenses, presets
- Focus: tap, click, Enter on the canvas, search, or any name button. The camera flies to the item's neighbourhood (positions are never re-solved); one panel (a bottom sheet on phones) shows every facet together: evidence by status / recorder / source text, relationships by class, events with dates, places, stories, time and generation.
- Interrogate: "How do we know?" on every row, link (tap a line) and item: claim → status → recorded by → source (50 Stories marked AI-generated) → basis → report → chain → grading where recorded (the Thawr example reaches all of them) → what is not yet in the graph → reader-page links.
- Trace: all shortest threads between two items over recorded links, each hop with its claims, statuses and sources; ranked by how much of each hop is a sourced claim; link to the thread. Scrub: a period dims dated items outside it; undated items are drawn hollow and counted, never hidden. Ask: hidden until an ask page exists.
- Lenses: Discover (stories view and stories first, plain words, fewer labels), Study (evidence first, all relations and statuses), Research (raw IDs, sources, counts, morph weights, the view state as JSON per docs/04 §6). The view state is also kept in the address (`#v=`), so any view, focus or thread can be shared and reopened.
- Vantage presets, each found by name and skipped if missing: the Hijrah from Abu Bakr's side; the people of Badr ("absent from" left out); the first believers; family around the Prophet ﷺ (kinship lines only); the one chain.

## Encoding contract (docs/04 §3)
Hue = type only (Okabe–Ito) plus a shape per type; line style = relationship class (solid participation, double kinship, dashed social/political, dash-dot place, arrowed transmission); texture = not reviewed (hatched marks, speckled lines: today every mark); size off; no glow, no idle motion; the Prophet ﷺ is named with ﷺ and drawn like everyone else. Orientation: "you are here" line, "Showing N of M" with what filters hide, Back, Home, type filters in the legend. Text view (generated from the view state) lists what is shown and hidden, the focus's facets, the thread, and every item as a button (a keyboard route to every node).

## Numbers (graph of 15 Oct 2026, after slice 1e)
314 items (184 people, 12 groups, 22 places, 46 events, 50 stories), 655 drawn links, 549 claims (all proposed) and 193 record links (no status of their own, shown as "no status recorded"). 44 of 46 events dated, 57 people with a ṭabaqa, 6 of 22 places located, 1 chain of 5 links. Script time per frame about 2.5 ms at 628 nodes / 1,500 links; while moving, a cheaper frame is drawn (no texture overlays or text outlines) and the full one follows.

## For a human to decide / integrate
1. site/check_budget.py applies the 300 KB reader-tier budget to every page in site/dist, so it fails on this 453 KB interactive-tier page if the observatory is built before it runs. Exempt observatory/ (2 MB tier) or build it after the budget step. site/check_html.py passes with the page present.
2. scripts/check_all.sh already has the placeholder `site/observatory: tests` line; enabling it (and `node site/observatory/check_observatory.cjs site/dist` after building) is outside this slice. site/build.py clears site/dist, so rebuild the observatory after it.
3. Placement choices worth a ruling: a person's map position is their most-recorded located place; a person's time position is their first dated event. Neither is a claim, and the panel says so.
4. The headless check ran without Arabic fonts; ﷺ renders where the system has an Arabic font.

## Verify
`.venv/bin/python ontology/build_graph.py && .venv/bin/python site/observatory/build_observatory.py` (CONFORMS; writes the page)
`.venv/bin/python -m unittest discover -s site/observatory/tests` (19 OK, includes two builds with different hash seeds)
`NODE_PATH="$(npm root -g)" PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers node site/observatory/check_observatory.cjs site/dist` (1280×900 and 390×844: renders, no external request, ≤2 MB, focus opens the panel, ladder, all frames, keyboard, trace, presets, view-state JSON, bottom sheet, no sideways scroll)
