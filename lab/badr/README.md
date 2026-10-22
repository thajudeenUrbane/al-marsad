# Badr Lab

A prototype expedition, not part of the public site. Published at https://claude.ai/artifact/B9LbaVeunTtBXakE7uDnD9 (private until shared). The strategy it tests is in the doc "Beyond the Graph: al-Marṣad Learning Strategy".

Room 1 stands in the valley of Badr (present-day terrain, 22 km square) under the computed sky for the eve of 17 Ramaḍān 2 AH, under two calendar assumptions. Room 2 is "The 314", an investigation of Ibn Isḥāq's list against its own totals. Room 3 asks again after two days. The Provenance lens marks every element as attested, located, computed or schematic.

Nothing here is reviewed: names are proposed claims from the full-book pass.

## Build

    .venv/bin/python ingest/ibn_hisham.py fetch       # the OpenITI text, once
    .venv/bin/python lab/badr/people.py               # data/people.json
    node lab/badr/sky.cjs <hygdata_v41.csv> <node_modules/astronomy-engine>   # data/sky.json
    python3 lab/badr/build.py                         # needs Pillow; fetches terrain tiles into cache/ once

`build.py` writes `index.html` (open it directly) and `artifact.html` (the same page without the document wrapper, for publishing).

Inputs: HYG v4.1 star catalogue (CC BY-SA 4.0), astronomy-engine 2.1.19 (MIT), AWS Terrain Tiles, al-Thurayya rows (CC BY 4.0).

## What it found

- 83 + 61 + 170 = 314, so the text's totals agree. The graph finds 321 names: 279 in Ibn Isḥāq's voice, 22 in Ibn Hishām's, 20 untagged. Four names sit in two clan lists, and four come after the last clan total.
- "Friday, the morning of 17 Ramaḍān": with the month starting at the first visible crescent (30 h past conjunction, 8° up at sunset), the Feb–Mar 624 lunation gives Tuesday 13 March 624 (Julian) and the next gives Thursday 12 April 624. Neither is a Friday. A question for the scholars, not a result.
