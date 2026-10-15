# Slice 10 brief — time and space

Read first (these are the instructions; nothing else in the repo is): README.md "Standing rules"; docs/13-platform-direction.md; docs/08-prototype-hijrah.md (especially §7, the acceptance criteria); docs/04-visualization-architecture.md; docs/05-ux-architecture.md (§7 mobile, §9 accessibility, §10 orientation); docs/handover/maintainer-answers-1.md and maintainer-answers-2.md; docs/handover/slice-2a.md (how site/ works).

## Goal
A timeline and a map over the same graph, as an interactive tier (JavaScript allowed, at most 2 MB per page) built beside the reader pages. A separate slice builds a graph "observatory" that blends network, time and geography in one canvas; these are the dedicated, detailed timeline and map pages.

## Do
1. `site/interactive/build_interactive.py` (standalone; do not edit site/build.py or other site files): reads build/graph.ttl, writes site/dist/timeline/ and site/dist/map/ plus their data JSON. Reuse site/display.py for names and dates by importing it (do not copy). Own i18n file site/interactive/i18n/en.json; own CSS with logical properties only.
2. Timeline: events and people placed only by recorded dates, uncertainty drawn honestly (ranges, not false points); undated items listed separately, never placed. Gregorian first, Hijri beside it, per the display rules.
3. Map: places only where the graph records coordinates (no geocoding; slice 5 handles gazetteers). No external tiles or requests: a simple basemap from public-domain data that is vendored (e.g. Natural Earth, heavily simplified, a few KB; record its source and licence) or none. Routes only where the graph records them.
4. No pixel without provenance: every mark links to its entity page and shows the status of the claim behind it. A text alternative generated from the data for both views (doc 05 §9). Works by touch on a phone; respects prefers-reduced-motion; keyboard reachable. No figurative depiction of anyone.
5. Tests: site/interactive/tests (unittest) and a Playwright check (JavaScript on) that both pages render, make no external requests, stay under 2 MB, and that the text alternative lists every plotted item.

## Done when
Both pages build from the graph and pass the tests; the handover says which doc 08 §7 criteria the current data meets and which it cannot meet yet, and why. Handover: docs/handover/slice-10.md (at most 60 lines).

## Scope
site/interactive/** (new) and docs/handover/slice-10*.md only. Linking these pages from the home page happens at integration (another slice is changing site/ for search at the same time).

## Rules
Never upgrade a status. Never invent names, dates, coordinates or routes. No model names or IDs in any repo file. Never hard-code entity IDs (slice 1e re-minted 16 IDs).

## Finish
1. Checks: `ontology/build_graph.py` conforms; `site/build.py`, then the interactive builder; the unit tests; the Playwright check.
2. Commit messages end with the attribution lines given to the session.
3. Rebase on origin/main, rebuild, re-run the checks, commit fixes.
4. Push the slice branch only (force-with-lease only on that branch after the rebase). Never push to main, never open a PR.
