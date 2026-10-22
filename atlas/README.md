# Sky Atlas

`index.html` is the whole joined graph (slice 11a: every corpus file, the full Ibn Hishām layer included) as one sky you can turn and be guided through. It is a separate page from the earlier Sky (`sky-observatory` branch) and Sky Atlas (`sky-atlas` branch), with its own renderer and layout, and it carries every feature those pages had. One self-contained file: open it in a browser; nothing is fetched.

**8,373 marks** (7,867 people, 208 events, 236 places, 50 stories, 12 groups) and **15,961 claims**, every one `proposed`. The page says so on every view and on every record.

## What it does

**Eight views that morph into one another**, with a blend slider to stop between neighbours.
- *Sky*: the Prophet ﷺ is the light at the centre, never a mark; events on a spiral in the order Ibn Hishām's text tells them (each event's median OpenITI milestone); the 50 Stories on an outer ring; everyone else settled by their recorded links, lineage-only names outside.
- *Stories*: the 50 Stories on a dial by part, with the people they name inside.
- *Time*: recorded date ranges as bars (CE), people at their dated events, a band for a recorded generation with no date.
- *Map* and *Globe*: places at recorded coordinates on Natural Earth coastlines; on the turning globe, gold arcs join the places of the dated events in order (the order of the record, not a route) and grow with Play history.
- *Book*: the text page by page, with volume and page on the scale.
- *Transmission*: the 11 recorded chains narrator by narrator, and everyone in recorded narration in layers by distance from the Prophet ﷺ.
- *Lineage*: fourteen generations up, three down.

Every view puts what it cannot place from recorded data on a labelled shelf, never on the axis, the map, the dial or the chain.

**Moving through it.** Turn, pinch, flick (it keeps turning), double-click to fly in, viewpoints (face on, angled, edge on, from below), Slow turn (off by default), Back and Home, keys (arrows, + −, 0 fits, Enter, /, Esc). A tap answers with a ring and a short vibration. Tapping a line opens the evidence for that pair.

**Guided learning.** Tours fly the camera stop by stop: the Sīra as Ibn Hishām tells it (192 events), every dated event (44), the three journeys of `learn/journeys/` applied to this graph (the Hijrah, the people of Badr: 439, the first believers), the ten, the 50 Stories, opposition and the turning, *My tour* (from your star chart), and a tour from any record (a life, a place, an event). Each stop says why it was chosen, shows who was there and who was recorded absent, what the record says with its source, and where to go next; the whole route is drawn as a numbered gold line. Play advances on its own; *Read aloud* speaks each stop with the device's voice. Five vantage points (the Hijrah from Abū Bakr's side, the people of Badr, the first believers, family around the Prophet ﷺ, the chains of transmission). Recall cards never mark an answer wrong.

**Evidence.** Three depths (Discover, Study, Research). Every record with its status, compiler, Ibn Hishām volume and page, qualifiers, AI glosses labelled as such, claim IDs; the ladder down to report, grading and chain with transmission modes and contact checks; *How do we know about…* for an item (name as recorded, recorded by, record, dates with their precision, location, gaps); an evidence summary (by status, by who recorded, by source text); who was there and who wasn't (absence drawn on the sky as a broken coral ring); entries that share a written name, shown and never merged.

**Time.** Play history (a year at a time; each mark lights with a ring at its first dated record; undated marks hollow, never hidden), and a period scrub.

**Light.** By recorded generation (default), by distance in recorded narration (the chains and every “narrated from” claim: 181 people), or all alike. Dark marks only where a claim records fighting against or opposing the Prophet ﷺ (37); *The turning* draws as stars those with a claim qualified “accepted Islam later” (2).

**Threads and comparison.** Trace a thread: From and To with search, Swap, several shortest threads ranked by how much of each step rests on a cited page, never through the Prophet ﷺ or (unless asked) lineage-only names, each step with its claim; copy a link to the thread. Compare two records: what joins them directly, events and people both are linked to, side by side.

**Your own.** A logbook (kept in this browser), fourteen milestones and nine quests about your own exploring (never a person's rank), a star chart of saved records that becomes a tour, copy a citation of any record or list.

**Reading, teaching, scale.** Larger text, classroom mode (large type, the guide playing on its own, full screen where allowed), group nearby stars, distant-star scenery, a test load of 2,000–50,000 synthetic stars, GPU drawing on or off (a Canvas 2D renderer also covers browsers without WebGL), a drawing-speed readout.

**Words.** Search in English, transliteration or Arabic; an Index (A–Z, recorded links labelled as coverage, first named in the text, the Atlas's order: the Prophet ﷺ, the four, the ten, then recorded links); a Text tab that describes the current picture and lists every mark as a button (a live summary for screen readers too); at Research depth the view as data, a view code to copy or open, and the corpus fingerprint. The address carries the view as a link-safe code. An Arabic interface (right to left, with a note that it is a draft awaiting the scholars' review); `#ar` opens it.

## How it is built

```sh
.venv/bin/python ontology/build_graph.py    # build/graph-all.ttl (about two minutes)
.venv/bin/python atlas/build.py             # atlas/index.html (about a minute)
.venv/bin/python atlas/build.py --artifact /tmp/atlas-artifact.html   # the same page without its document skeleton, to publish as an Artifact
.venv/bin/python atlas/build.py --reader-base https://…/ --ask-url https://…/ask/   # link records to the reader pages and the bar to Ask
```

- `build.py` reads the graph through the Observatory's extractor (`site/observatory/obsdata.py`), so every claim, status, source and date matches the reader tier. It adds the layout, the text order, the journeys with the reasons for each step, the vantage points (found by name; Abū Bakr from the lists file where the full layer repeats the name), the Arabic names, the lists, the marks above and the corpus fingerprint, and writes the data gzip-packed inside the page. The output is byte for byte the same on every run.
- `layout.py`: the deterministic 3D Sky layout (about 10 s).
- `static/gl.js`: the renderer (WebGL marks and lines with a Canvas 2D fallback, the globe's body, scenery, test load, grouping, picking marks and lines, camera and touch). `static/app/01-core.js` … `08-main.js`: the page, joined in order inside one scope by the build. `static/template.html`, `static/atlas.css`.
- `i18n/en.json`, `i18n/ar.json`: every interface string; the build stops if Arabic lacks a key.
- `data/lists.json` (the four, the ten: proposed, with sources), `data/land.json` (Natural Earth 1:110m land, public domain).

Check it:

```sh
.venv/bin/python -m unittest discover -s atlas/tests
NODE_PATH="$(npm root -g)" node atlas/check.cjs     # desktop and 390 x 844: every feature, no page error, no external request
```

All of it runs in `scripts/check_all.sh`, which also checks that the committed `index.html` matches a fresh build.

## Known limits

- The full Sīra layer is not yet de-duplicated: one person can appear under several entries, and a kunya-only merge can join two people. The page shows entries with the same written name side by side and lets the Index list only those (merging is slice 11a's next step).
- 44 events carry a recorded date and 6 places recorded coordinates, so Time, Map and Globe are thin until the gazetteer and dates land. One recorded date runs to 714 CE, so Play history runs from 609 to 714.
- Slice 11's side claims (fought with or against the Prophet ﷺ at each event) are not in the graph yet; dark marks rest on the `fought_against` and `opposed` claims that are.
- Read aloud uses the device's own voices; names are spoken as written.
- The Arabic interface and the predicate labels are a draft.
