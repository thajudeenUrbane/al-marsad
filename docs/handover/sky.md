# The Sky: the whole graph as a three-dimensional sky

Asked for by the maintainer, 15 October 2026: "Al-Marsad as a clear sky. The Prophet ﷺ as a source of light, a high-density light; the Companions as clear stars; the dark vacuum is where the graph stands. Nothing shady or blurred, so we can touch and learn. A 4D experience: rotate, zoom, 360° views, touch each star. Include all the features of the Observatory." Nothing shown is verified history: every claim is `proposed`, the banner and legend say so, every panel row carries its status label, and no status is upgraded. No date, place, chain or name is invented.

## What exists (all under site/sky/)
- `build_sky.py` (standalone) writes **site/dist/sky/index.html**: one file, CSS, script, strings and data inline, no external request, system fonts, **~490 KB** (2 MB interactive budget; `sky` added to `INTERACTIVE_DIRS` in site/check_budget.py). New records in build/graph.ttl become new stars on the next build: nothing about any person is written in the Sky's code (tested: no entity ID in its sources).
- `skylayout.py`: the Sky frame, a 3D layout computed offline (≈4 s). The Prophet ﷺ fixed at the origin; the 50 Stories on a ring in the plane z = 0, in reading order; each person with a recorded ṭabaqa drawn to a shell for it (Companions 190, Successors 330, their successors 430); everything else settles by its recorded links only. No position reads a degree. Starts from hashed IDs, fixed order and constants, rounded to 0.1: byte-identical across builds and hash seeds (tested).
- `static/render3d.js`: the 3D renderer. `static/template.html`, `static/sky.css` (layered on observatory.css), `i18n/en.json` (only the strings that differ, layered on the Observatory's), `tests/` (13 unittest tests), `check_sky.cjs` (Playwright, JS on, desktop and phone).

## Every Observatory feature, by construction
`site/observatory/static/observatory.js` was split, with no change in behaviour (the Observatory's 19 tests and its browser check pass unchanged): the drawing, camera and canvas input moved to `render2d.js`, which defines `window.MarsadRenderer(api)`; observatory.js keeps state, emphasis, the panel and evidence ladder, trace, presets, lenses, scrub, the view state and the text view, and calls the renderer through a small interface (`start, requestDraw, animateTo, isAnimating, stopAnim, blend, refit, rebase, cameraState, applyCamera, clearCaches`). The Sky inlines `render3d.js` in place of `render2d.js`, so it has: focus with every facet; "How do we know?" down to report, chain and grading; trace between two items; the period scrub; Discover/Study/Research lenses; the five vantage presets; the view state in the address (`#v=`, camera as target/yaw/pitch/distance); the text view with every item as a button; type filters; Back/Home. The Time, Geography, Stories and Transmission frames are the Observatory's own, lying flat inside the sky (the morph blends real 3D positions; a flat frame is shown face on).

## The Sky's own
- Turn (drag, arrows), move (right-drag, Shift-drag, two fingers, Shift+arrows), zoom (wheel, pinch, +/−), flick to keep turning, double-click to fly in; viewpoints Face on / Angled / Edge on / From below; Orbit (off by default; refused under reduced motion).
- **Play history**: the period grows a year at a time from the first recorded year; each mark lights at its first dated record with a brief ring; undated marks stay drawn hollow, never hidden (the scrub's own rule).
- A tap answers with a ring (and a short vibration where the phone allows). A tap no longer lets the browser's follow-up click land on the panel that opens under the finger (fixed in render2d.js too: the same bug was there).
- Distant stars: a seeded sphere of faint pinpoints that turns with the view but never comes closer; labelled as scenery, switchable.

## Encoding: where the Sky follows docs/04 §3 and where it departs (for a ruling)
Follows: hue and shape = type only; line style = relationship class; **size off** (one size for every star, growing only with nearness); **brightness and warmth = recorded generation only** (01 §5 rule 2), switchable ("Light by generation"); the Prophet ﷺ as illumination, not a mark (rule 1), named "محمد ﷺ" and "The Prophet Muhammad ﷺ"; no idle motion (Orbit is opt-in); no interpolation; nothing placed by a count of links.

Departs, at the maintainer's explicit request ("nothing shady, nothing blurred"), so these need a ruling before the Sky replaces anything:
1. **No "not reviewed" texture and no diffusion for uncertainty** (04 §3 texture row; 01 §5 rule 4). Every mark is sharp; the status is carried by the banner, the legend and each panel row instead. Today every claim is unreviewed, so the texture says nothing that differs between marks; it will matter once some claims are reviewed.
2. **Glow**: the light has a short corona and stars with a recorded generation a tight halo. Both encode something (the origin; the generation), but 04 §3 says "no glow" in the Observatory.
3. **Decorative scenery** (the distant stars) is not data. It is labelled and switchable.
4. **Hues** are the Sky's own (white stars, gold events, lilac stories, teal places, rose groups), not Okabe–Ito; every type also has its own shape, so hue is never the only cue.

## Numbers (graph of 15 Oct 2026)
314 items: 1 light, 50 stories on the ring, 57 people on generation shells (53 Companions within 139–271 of the light, Successors 302–339), 203 placed by links, 3 with no link. 92 dated items light during Play history; 222 stay hollow.

## Verify
`.venv/bin/python ontology/build_graph.py && .venv/bin/python site/sky/build_sky.py`
`.venv/bin/python -m unittest discover -s site/sky/tests` (13 OK) and `-s site/observatory/tests` (19 OK)
`NODE_PATH="$(npm root -g)" PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers node site/sky/check_sky.cjs site/dist` (both sizes: renders, no external request, focus, ladder, every frame, keyboard, trace, presets, turning, viewpoints, Play history, option buttons, view-state JSON, bottom sheet, finger tap on a star, no sideways scroll)
All of it runs in `scripts/check_all.sh`.
