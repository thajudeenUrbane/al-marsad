# Slice 8 handover: ask the graph

Spec: docs/handover/slice-8-brief.md. Nothing shown is verified history. No status was upgraded, no data edited, no name, date or answer invented. No model is called anywhere; the page says so under every answer.

## What exists (all under ask/)
- `DSL.md`: the typed query language (docs/07 §4): grammar, 17 operations (participants, people, absent, events, stories, relatives, connected, between, path, when, where, about, both/either/except, count, reviewed), time semantics, the answer object, refusals, question shapes, spelling, the docs/05 §3 and docs/07 examples.
- `dsl.py`: parser, validator (closed operation table, types, names resolved to one entity or a loud error, year ranges, depth/op limits), executor, plain-language rendering. Each row carries the numbers of the claims behind it; each claim its status (assertions) or "no review recorded" (participations, event places).
- `translate.py`: refusal classifier (runs first: fabrication, depiction, grading, interpretation, ruling, judgement, ranking, speculation), 33 question shapes, spelling-tolerant linking, ambiguity put back to the visitor, never guessed. `Translator` interface + `ModelTranslator` placeholder (raises; never registered; contract in DSL.md).
- `normalise.py`: name keys built on the site's normaliser, `site/names.py` (`normalise`, `skeleton_words`, `fold`), imported; a six-level match score (literal vs sound-alike).
- `index.py`: compact index read through `site/model.py`, so answers rest on the same claims as the reader pages. `present.py`: answer → HTML.
- `build_ask.py` (standalone, run after site/build.py): `site/dist/ask/` = the page, 45 pre-built answer pages `q/<slug>/` (work with JS off, citable), `ask.js`, `ask.css`, `ask-index.json.gz` (56 KB; declared in `data-fetch`, so check_budget counts it; unpacked with `DecompressionStream`). Fails over 2 MB.
- `static/ask.js`: line-by-line browser port of normalise/dsl/translate/present (and of names.normalise/skeleton_words, using names.RULES from the index). Lazy: the index loads only when the visitor starts. Question kept in `#q=` (never sent to the server).
- `golden/questions.jsonl`: 68 questions, all labelled "pending scholar check": 51 with expected query and rows (by recorded label, resolved at test time; rows computed independently from the raw RDF), 17 refusals; 45 marked `cache` become the pre-built pages.
- `i18n/en.json` (every UI string), `templates/` (no literal text), logical CSS only.

## Numbers (graph after slices 1e, 2b, 6-7, 10)
314 entities, 737 claims (549 proposed assertions, 188 links/participations with no status), 0 accepted. ask/ 737,127 bytes; ask page 146,554 bytes with CSS, JS and index; heaviest answer page 196,618 ("Who met both Abu Bakr and Umar?"). Parity: 604 questions + every entity name.

## Decisions made here (say if you disagree)
1. "Who was at <place>": people in events recorded there, plus direct claims about the place (died at, migrated to...). Stories have no place, so they are offered as "other entries with a similar name", not merged.
2. Story lists ("participated in" from the 50 Stories doc) are shown with their role text and a note that a list can name someone absent or on the other side (e.g. Uthman in the Badr story).
3. "Met" is read as a recorded tie or a shared recorded event; the answer says so.
4. Time filter: only query bounds are converted (tabular civil calendar, Julian, as the graph's own conversions); rows "within" vs "overlaps" (marked), undated left out with a count.
5. A yes/no question ("Was Uthman at Badr?") gets the records, not a verdict: here a proposed "absent from Battle of Badr".

## For a human
1. Data error seen, not fixed: Khadija bint Khuwaylid is recorded as "father of" Fatima bint Muhammad (generation-1); golden g18 records it as it stands.
2. Golden set needs a scholar's check (docs/13): the expected answers are what the graph records, not what is true.
3. Integration: add to scripts/check_all.sh after the other builders: `step "ask: build" "$PY" ask/build_ask.py` and `step "ask: page works (JS on and off)" browser_check ask/tests/check_page.cjs`; uncomment `step "ask: tests" ...`. Link /ask/ from the home page and the nav.
4. ask.js carries a second JS port of names.normalise (search.js exports its engine only under Node). If search.js also exposed `makeEngine` in the browser, ask could load it instead.
5. Not yet: a small graph view (lists only today); `within(X, steps)` traversal for transmission chains; Arabic question shapes (slice 9).

## Verify
`.venv/bin/python ontology/build_graph.py` (CONFORMS); `site/build.py`, `learn/build_learn.py`, `site/interactive/build_interactive.py`, then `ask/build_ask.py`; `site/check_budget.py` and `site/check_html.py` (OK, 373+ pages incl. ask).
`.venv/bin/python -m unittest discover -s ask/tests`: 40 OK (golden set, Python/JS parity via node, static rules, DSL errors, calendar vs the graph's conversions, no status upgraded, build determinism).
`NODE_PATH=$(npm root -g) PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers node ask/tests/check_page.cjs site/dist`: OK (JS off and on).
