# al-Marṣad Expeditions

A new, separate product built on the joined graph: **expeditions into evidence**. Each expedition is one place and moment of the Sīra. The learner stands on the real ground under the sky astronomy computes, then investigates a real question in the text. It is the first build of the strategy in the doc "Beyond the Graph: al-Marṣad Learning Strategy". It changes nothing else in the repository: it reads the graph, the count checks, the cached text and the site's land layer, and writes only under `expeditions/`.

Nothing here is scholar-reviewed. Names, links and dates are claims the AI extraction pass proposed from Ibn Hishām's *Sīra*.

## The five expeditions

| Expedition | Place | Investigations | What the computation found |
|---|---|---|---|
| The crossing to Abyssinia | Aksum (Wikidata, proposed) | Eighty-three men: 83 stated, 87 found | The text gives no date, so no sky is drawn |
| The night at al-ʿAqaba | the traditional site near Minā | 75 stated (73 men, 2 women), 74 found; a third of the night | Under all three candidate lunations the moon was 39–46° up and nearly full when they slipped out |
| From Thawr to Qubāʾ | Qubāʾ | 22 names on the road, 4 located, 7 claims; which Monday | No candidate lunation gives a Monday 12 Rabīʿ al-Awwal |
| The eve of Badr | Badr | The 314 (321 found); which Friday | No candidate gives a Friday 17 Ramaḍān |
| The morning at Uḥud | Jabal Uḥud | When the list agrees: 65 and 22, both match | The tabular lunation gives Saturday 30 March 625, matching the text's Saturday |

Each finding is a question for the scholars, never a correction. The crescent rule is a stated stand-in (30 hours past conjunction and 8° up at sunset), and every date is Julian.

## What each expedition holds

Enter (3D world or flat map; the time slider and three candidate lunations) · its investigations · who the text places there (with the Prophet ﷺ, against him as dark marks, or no side recorded) · explain in your own words · remember (FSRS spaced review, kept on the device) · connect (people the text places at two expeditions, joined from attested claims).

Other views:

- `#review`: questions due, your sky, and memory export, import and erase.
- `#desk`: each expedition's claims as one batch for scholars, flags first, decisions exported as `marsad-review-decisions` v1. A dry run of `review/import_decisions.py` accepted an exported file unchanged.
- `#halaqa-<slug>`: a room view for teaching, where arrow keys step through. `#follow` in a second window mirrors it.
- `#about`: the four provenance classes, the rules, sources and channel packs.
- `text/`: every expedition as a plain page, with no script, for any phone, a screen reader or a printer.
- `channels/`: seven WhatsApp messages per expedition for experiment X6. Drafts: a teacher reads each one first.

## Rules kept

- No pixel without provenance: every element is attested, located, computed or schematic, and the Provenance lens shows which.
- No depiction: there are no figures in any view.
- The guide only asks; every fact comes from a claim, a passage or a stated computation.
- Reported and converted dates are kept apart.
- Recorded links are coverage, never rank.
- Learner memory never leaves the device, and there are no accounts.
- There are no external requests at run time.

## Build

```
.venv/bin/python ingest/ibn_hisham.py fetch                  # the OpenITI text, once
npm install astronomy-engine@2.1.19 --prefix <somewhere>      # build-time only
node expeditions/compile/sky.cjs <hygdata_v41.csv> <somewhere>/node_modules/astronomy-engine
.venv/bin/pip install pillow                                 # build-time only, not in requirements.txt
.venv/bin/python expeditions/compile/compile.py              # fetches terrain tiles once into expeditions/.cache/
python3 -m http.server 8770 --directory expeditions/dist     # then open http://localhost:8770
```

`hygdata_v41.csv` comes from github.com/astronexus/HYG-Database (`hyg/CURRENT/`). `dist/publish.html` is `index.html` without its document wrapper, for publishing as a claude.ai artifact with the rest of `dist/` as supporting files.

Hand-written inputs live only in `defs/expeditions.json`. They are pointers into the graph, gazetteer points with their sources, short name and date phrases from the text, and the guide's questions.

## Checked

Every view and every step of the five expeditions, at 1280×860 and 390×844 in Chromium (WebGL through SwiftShader): no console errors, no external requests and no sideways scroll. The plain pages pass the same checks. The `dist/` folder is 1.2 MB in total, and each expedition loads only its own data file, between 97 and 209 KB.

## Not built yet

- A relay so students follow a halaqa on their own phones.
- Narrated audio.
- The language-model companion (strategy direction G, after the A2 adversarial tests).
- Reviewed gazetteer points: every point is still proposed.
- Arabic interface strings.
