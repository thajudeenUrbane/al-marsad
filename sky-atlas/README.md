# Sky Atlas

`index.html` is the Sky (the whole graph as a sky you can turn) with six additions on top. Everything the Sky already had is kept: the five views and the morph, the lenses, focus, trace, vantage points, Play history, the evidence ladder, the legend and the text view.

It is a single self-contained page. Open `index.html` in a browser; nothing is fetched.

## What it adds

1. **Guided journeys.** The three learning journeys (`learn/journeys/`) as camera tours: the Hijrah step by step, the first believers, the people of Badr. The camera flies stop by stop (Previous, Play, Next, End journey), the journey's stars stay lit, and numbered gold markers show the stops. Each stop says why it was chosen. The page applies the journeys' selection rules to its own data. The Hijrah rule's `date_anchors` needs relative dates that the Sky's data does not carry, so that journey has 5 stops.
2. **Light by chain distance.** A switch that replaces generation light while it is on: brightness follows how far a person is from the Prophet ﷺ in a recorded narration chain (docs/01 §5). The graph has one chain so far, so 7 stars light up.
3. **Groups of stars, and faster drawing.** "Group nearby stars" merges stars that share a screen cell into a ring with a count until you zoom in; tap a group to fly into it. Emphasised stars never merge, and every group is the same size. "Faster drawing (GPU)" draws the distant scenery and the test load with WebGL. "Many stars (test load)" adds 2,000, 10,000 or 50,000 synthetic test stars in the generation shells, with a frame-time readout. Test stars are not records: they never appear in search, the panel or the text view.
4. **Globe.** An orthographic globe for the Geography view. Coastlines come from Natural Earth 1:110m land (public domain), via the `world-atlas` package. Places sit at their recorded coordinates (6 of 22 so far), with their events around them. Gold arcs join the places of the record's dated events, one after another, and grow with Play history. An arc shows the order of the record, not a route. The text view lists the places still waiting for coordinates.
5. **Who was there, and who wasn't.** Focusing an event opens a facet listing those recorded as present and those recorded as absent (`absent_from`), each absence with its recorded basis. On the sky, the absent carry a broken coral ring with a stroke through it. A person's panel lists the events they are recorded as absent from. Absence is shown only where a record states it.
6. **Arabic interface.** The العربية button switches the page to right to left and remembers the choice (`#lang=ar` also works). The Arabic strings are a draft, reusing the terms in `site/i18n/ar.json`, and await review by the scholars. Names stay as recorded: only 6 places carry Arabic names in the data. Some axis labels in the flat views stay in English.

## How it is built

The Sky's own source (`site/sky/`) is not in this repository yet, so the build starts from the published Sky page:

- `source/sky-base.html`: the published Sky page, as it was when this was built.
- `source/build.py`: applies the additions and writes `index.html`. Each replacement must match exactly once, or the build stops.
- `source/r_add.js`: renderer additions (chain light, journey trail, absence marks, groups, test load, WebGL layer, globe).
- `source/app_pre.js` and `source/app_post.js`: app additions (chain distance, presence, journeys, globe data, language switch).
- `source/body.html` and `source/add.css`: the page body (with translation hooks and the new controls) and the added styles.
- `source/new_en.json`, `source/ar.json`, `source/new_ar.json`: the new English strings, the Arabic for the Sky's existing strings, and the Arabic for the new ones.
- `source/land_rings.json`: the Natural Earth coastlines as rings of longitude and latitude.

Rebuild with:

```sh
python3 sky-atlas/source/build.py
```

Check it in a browser (needs Playwright and Chromium; screenshots go to the system temporary folder):

```sh
node sky-atlas/source/check_features.cjs   # journeys, presence, chain light, test load, GPU, globe, Arabic, 390 px phone width
node sky-atlas/source/check_existing.cjs   # vantage points, trace, lenses, Play history, views
```

Each check exits non-zero on a page error. Neither is part of `scripts/check_all.sh` yet.

When the Sky's source lands in `site/sky/`, these additions should move into it, and this folder can go.
