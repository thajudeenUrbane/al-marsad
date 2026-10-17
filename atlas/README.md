# Sky Atlas

`index.html` is the whole joined graph (slice 11a: every corpus file, the full Ibn Hishām layer included) as one sky you can turn and be guided through. It is a new page, separate from the earlier Sky (`sky-observatory` branch) and Sky Atlas (`sky-atlas` branch): its own renderer, its own layout and its own guided-learning mode, built from the graph like the other views. One self-contained file: open it in a browser; nothing is fetched.

**8,373 marks** (7,867 people, 208 events, 236 places, 50 stories, 12 groups) and **15,961 claims**, every one `proposed`. The page says so on every view and on every record.

## What it does

- **Five views that morph into one another.** *Sky*: the Prophet ﷺ is the light at the centre, never a mark; events lie on a spiral in the order Ibn Hishām's text tells them (the median OpenITI milestone of each event's claims); the 50 Stories ring the sky; everyone else is settled by their recorded links, with people known only from lineages hanging outside. *Book*: the text from first page to last, each mark where the text first names it, with volume and page on the scale. *Time*: recorded dates (CE), people at the dated events they took part in. *Map*: places at recorded coordinates (6 of 236 so far) on Natural Earth coastlines, with their events and people gathered round them; the light hangs above the land and marks no place. *Lineage*: fourteen generations up, three down, from the kinship claims.
- **Guided tours.** The camera flies stop by stop. *The Sīra as Ibn Hishām tells it* (192 events), *Every dated event* (44), the three learning journeys of `learn/journeys/` applied to this graph by `learn/journeys.py` (the Hijrah, the people of Badr: 439, the first believers), *The ten promised Paradise*, *The 50 Stories*, and *Opposition, and the turning*. From any record: *Guide me from here* (a life in the order of the text, standing at a place, around an event). Each stop shows who was there, where, what the record says with its source, and where to go next (before and after in the text, events that share people, stand at the place, follow a life, see the lineage). Play advances on its own.
- **Three depths.** Discover (plain, few items), Study (every record with its status, compiler and Ibn Hishām volume and page), Research (OpenITI milestones, AI glosses labelled as such, claim IDs, coverage, the evidence ladder open: report, grading, chain).
- **Recall**, at Study and Research: a question about the stop, answered from the record. Nothing is ever marked wrong, because an absent record is not a false one.
- **Trace a connection** between any two records: the fewest steps (a family step counts two), never through the Prophet ﷺ, and by default never through lineage-only names. Each step shows its claim and source, under a note that no text states the connection as a whole. Connection stories appear only once a scholar approves one; none has been, so none is shown.
- **The order of people** (maintainer-answers-3, E3): the Prophet ﷺ, the four, the ten (from `data/lists.json`, proposed, matched by display name, never by ID), then by recorded links, labelled as coverage, never rank. Also A–Z, recorded links and first named in the text. People recorded as opposing the Prophet ﷺ come last.
- **Dark marks and the turning** (X1): a person is a dark stone only where a claim records them fighting against or opposing the Prophet ﷺ (37). *The turning* draws as stars those with a claim qualified "accepted Islam later" (2). Everyone else is drawn by type and generation only.
- **Logbook and milestones**, kept in the browser: people, events and places observed; fourteen milestones about the learner's own exploring (first light, a hundred stars, how do we know, along the chain, thread tracer, the whole spiral, in both tongues…). Never a ranking of a person.
- **Search** in English, scholarly transliteration or Arabic (7,915 Arabic names from `identity.csv`), an **Index** of every mark, a **Key**, and an **Arabic interface** (right to left; a draft awaiting the scholars' review). `#ar` opens it in Arabic.

## How it is built

```sh
.venv/bin/python ontology/build_graph.py    # build/graph-all.ttl (about two minutes)
.venv/bin/python atlas/build.py             # atlas/index.html (about a minute)
.venv/bin/python atlas/build.py --artifact /tmp/atlas-artifact.html   # the same page without its document skeleton, to publish as an Artifact
```

- `build.py` reads the graph through the Observatory's extractor (`site/observatory/obsdata.py`), so every claim, status, source and date matches the reader tier. It adds the layout, the text order, the journeys, the Arabic names, the lists and the marks above, and writes the data gzip-packed inside the page (the browser unpacks it with `DecompressionStream`). The output is byte for byte the same on every run.
- `layout.py`: the deterministic 3D layout (about 10 s; a grid keeps the push between marks local).
- `static/gl.js`: the WebGL renderer (marks as crisp shapes, lines, a 2D overlay for the light, names and markers, camera and touch input). `static/atlas.js`: the page. `static/template.html`, `static/atlas.css`.
- `i18n/en.json`, `i18n/ar.json`: every interface string; the build stops if Arabic lacks a key.
- `data/lists.json` (the four, the ten: proposed, with sources), `data/land.json` (Natural Earth 1:110m land, public domain).

Check it:

```sh
.venv/bin/python -m unittest discover -s atlas/tests
NODE_PATH="$(npm root -g)" node atlas/check.cjs     # desktop and 390 x 844: no page error, no external request
```

All three run in `scripts/check_all.sh`, which also checks that the committed `index.html` matches a fresh build.

## Known limits

- The full Sīra layer is not yet de-duplicated: one person can appear under several entries (for example twenty al-Zubayr rows), and a kunya-only merge can join two people. Lineages show this plainly. Merge proposals are slice 11a's next step.
- Only 44 events carry a recorded date and 6 places recorded coordinates, so the Time and Map views are thin until the gazetteer and dates land.
- The side claims of slice 11 (fought with or against the Prophet ﷺ at each event) are not in the graph yet; dark marks rest on the 40 `fought_against` and 72 `opposed` claims that are.
- The Arabic interface and the predicate labels are a draft.
