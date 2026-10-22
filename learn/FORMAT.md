# marsad-journey v1

The shared journey format of al-Marṣad (learn-v2 design, §7 and §9–§11). One resolver,
`learn/journey_export.py`, turns every journey in `learn/journeys/` into the files below.
The reader Learn pages, the Sky Atlas's guided mode and Expeditions all play the same
files, so a journey is chosen once, reviewed once and shown everywhere.

Nothing in these files is asserted by software. Every sentence a page can show is an i18n
template key bound to claim IDs (or, later, prose that both approvers approved), and every
value is recorded data: names, labels, literals as written, citations, dates, counts, or
the rule's own words. The files are rebuilt, never committed.

## Making the files

```
.venv/bin/python learn/journey_export.py --graph build/graph-all.ttl --out DIR [--part-budget N]
                                         [--step-budget N] [--facade]
.venv/bin/python learn/journey_export.py --lock        rewrite learn/facade.lock (see "The Atlas facade")
```

`learn/build_learn.py` writes the same files to `site/dist/learn/data/`, with the same
`--step-budget` and `--part-budget`, and renders the reader pages from them. In process:

- `journey_export.resolve(site, journey, strings)` gives one built journey, unsplit, as a dict.
  `strings` is `{"en": {...}, "ar": {...}}`, as `journeys.load_i18n()` gives it, or `None`
  to read `learn/i18n/`. It is not the flat en table (`learn/i18n/en.json` alone) that the
  Atlas reads and `atlas_projection` takes. `rule_sha` binds the en and ar wording, so any
  other shape raises `TypeError` rather than give a wrong `rule_sha`, `state` and title.
- `journey_export.resolve_all(site, folder=None)` gives every journey, split, and writes them
  to `folder` when one is given. It returns `{"index", "journeys", "files", "digest", "facade",
  "plans"}`. Its `strings` takes the same shape. Without a `plans` argument it computes the
  reader's own page cuts (`render_learn.reader_plans`, `step_budget` bytes of step HTML per
  page, 220,000 by default), so `stops[].urls` and `pages.json` name the pages the reader
  build writes, on any graph.
- `journey_export.resolve_docs(site, journeys, plans=)` gives every built journey unsplit,
  with the stop URLs of the given page cuts: what the reader pages are rendered from.
- `journey_export.source_line(claim, depth, passages, t)` is the one source-line function.

In public mode `accepted` (see "The Discover rule"), `resolve_all` and `build_learn.py`
stop with a `RuleError`, the reader build before it writes or removes anything.

The CLI writes only into `--out`. That folder must be new, empty, or an earlier export (it
then holds `.marsad-journey-export`). It never writes into `learn/journeys/` or `learn/lists/`.

## Files

```
index.json                         marsad-journeys v1: graph, depth policy, rules, entity index, journeys
strings.json                       {"en": {...}, "ar": {...}}: every i18n key the export names
pages.json                         marsad-learn-pages v1: every reader page
journeys/{slug}/journey.json       marsad-journey v1: the head of one journey
journeys/{slug}/part-{k}.json      marsad-journey-part v1: steps with their own tables
journeys/{slug}/research-{k}.json  marsad-journey-research v1: glosses and trace of part k
facade.json                        with --facade: the Atlas projection (below)
```

Each slug has its own folder, so no slug can overwrite a shared file.

## Canonical form

Every file is `canonical(obj)` plus one newline. There are no timestamps. Every list is in
a fixed order whose ties end in a pid or a claim ID, so two builds of the same graph give
the same bytes, whatever the hash seed.

```
canonical(obj) = json.dumps(nfc(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
sha12(obj)     = sha256(canonical(obj)).hexdigest()[:12]
```

`nfc` applies Unicode NFC to every string, dictionary keys included. Known vector (the
input is JSON; `á` and `ź` are decomposed and come out composed):

canonical-vector input: {"b": ["Marsád", "المرصد"], "a": {"ź": 1, "y": [true, null, 2.5]}}
canonical-vector bytes: {"a":{"y":[true,null,2.5],"ź":1},"b":["Marsád","المرصد"]}
canonical-vector sha12: dbcd4070c042

Every hash in the files (`rule_sha`, `content_sha`, list `sha`, the export digest) uses this
form. `index.json` gives each journey's shas, so a consumer never has to recompute one.

## Versions

- `format` and `version` are on every file. This is version 1.
- Consumers ignore keys they do not know. An added key keeps version 1. A renamed or
  removed key, or a changed meaning, makes version 2, and version 1 is still written beside
  it for one release.
- `graph = {file, fingerprint, triples}`. `fingerprint` is exactly the Atlas's
  `obsdata.ObsData.fingerprint()`: sha256 over the sorted N3 lines of every triple without a
  blank node, 12 hex digits. It cannot see blank-node data: participation records, roles,
  relative date anchors.
- `content_sha` (per journey) is `sha12` of the unsplit resolved journey: stops, steps,
  claims, passages, entities, terms, glosses, trace and order data. It leaves out the layout
  (page URLs, part lists, the graph block), the approval layer (state, approvals, story
  mode, rule_sha), the wording (title, leads, rule sentences) and the `next` items, which
  name other journeys. It changes when a participation or its role changes, even when the
  fingerprint does not. Use it in link tokens, for example the Atlas's
  `tour.j_{slug}.s-{pid}` with `c={content_sha}`, and check it on restore.

## References

| Kind | Form | Note |
|---|---|---|
| Entity | `{kind}/{pid}` | kind is person, group, place, event or story |
| Claim | `assertion/{local name}` | equals the Atlas's ObsData claim `id` and Expeditions' `ast:{id}` |
| Participation | `participation/{event pid}/{person pid}/{role local or none}` | a record stored on an event |
| Plain link | `link/{pk}/{subject pid}/{object pid}` | pk is took_place_at or part_of |
| Passage | `passage/{local}` | |
| Term | `pk:{key}`, `q:{qualifier}`, `role:{role}`, `voice:{voice}`, `lc:{confidence}`, `gb:{basis}` | labels in `terms` |

The stop key is the entity pid. Readers anchor a stop as `id="s-{pid}"`.

## The Discover rule

A claim's `discover` flag is true if and only if:

1. it has a citation: a passage with `mrs:canonicalCitation`, which gives a work and a locator; and
2. no status recorded on it is `rejected` or `superseded`.

When the public mode is `accepted` (round 4 question 1), its status must also be exactly
`accepted`. Until the resolver can do that, the export stops with an error in that mode
instead of publishing.

Participation records, plain links and claims resting only on a basis text have no
citation, so they are never Discover-eligible. **At its public depth, a consumer shows a
claim only when `discover` is true, and only with its short source line.** It never shows
a status, a review word, a basis text, a recorded-by agent, a note, a gloss, a claim ID or a
rejected or superseded claim there. The other claims are counted into "{n} more records at
Study" (`learn.narr.more`). A stop with no eligible claim gets `learn.discover.no_work`.
`index.json` `depth_policy` states all of this per depth.

## index.json

```
{"format": "marsad-journeys", "version": 1,
 "graph": {"file", "fingerprint", "triples"}, "public_mode": "all" | "accepted",
 "depths": ["discover", "study", "research"],
 "depth_policy": {depth: {"status", "draft_note", "coverage_state", "accepted_share", "source",
                          "claims", "basis", "recorded_by", "notes", "gloss", "claim_ids",
                          "order_notes", "rejected", "ai_document_label", "narration", "prompts",
                          "claim_list", "next"}},
 "background_rule": {"marker", "after_source", "after_bound", "before", "not_placed"},
 "lists": {"file", "state", "applied", "sha", "sources_complete"} | null,
 "sorts": {"default", "az", "links": i18n keys,
           "accepted_islam": {"t", "rule": {"kinds", "phrase"}, "needs": "citation", "undated"}},
 "view_vocabulary": [...], "narration_order": [...],
 "texts": {name: i18n key}, "labels": {"status": {...}, "coverage": {...}, "type": {...}, ...},
 "reasons": {reason kind: i18n key}, "order_notes": {"part" | "recorded" | "unrecorded": i18n key},
 "strings": "strings.json", "pages": "pages.json",
 "entities": {pid: [[slug, stop key, n or null], ...]},
 "journeys": [{"slug", "kind", "state", "stale_approval", "rule_sha", "content_sha", "listed",
               "title", "lead", "lead_study", "door", "type", "order", "order_applied", "groups",
               "steps", "apart", "excluded", "accepted_share", "story_mode": {"open", "stale"},
               "parts", "file", "urls": {depth: [page urls]}}]}
```

- `depth_policy` numbers are caps: Discover shows 3 narration sentences and 1 prompt;
  Study 6 sentences and a 40-claim list; Research 80 of each. `null` means no cap.
- `background_rule` is the F11 rule as applied to this graph. `after_source` is
  `recorded_death`, `named_event` or `fallback`.
- `entities` is the entity index: every journey each stop is in, with its number (null when set apart).
- `reasons` gives the sentence for each kind in `steps[].reasons` and `steps[].links`
  (`learn.why.{kind}`). Its slots are `other` (the entity), `word` (a `named` reason) and
  `label` (an `event_claim` reason, the relation label as recorded). The reader wraps
  `word` and `label` in `texts.quote`. A reason other than `named` with no claims behind it
  rests on a plain link in the record (`texts.plain_link`). A `part` reason (a stories step,
  `learn.why.part`) has the slots `word`, the part's recorded title, and `work`, the story's
  work (its entity's `work`), wrapped in `texts.ai_document` when the reason has
  `ai_document`. `named` and `part` are the reasons the rule computes; the others rest on
  claims. The reader heads the two lists `texts.why_heading` and `texts.links_heading`.
- `order_notes` gives the sentence for `steps[].order.note`. Its slot `n` is the step number
  of `order.ref`. Order notes are Study and above (`depth_policy.order_notes`).
- `texts.apart_heading` and `texts.apart_lead` head the set-apart people; at Discover the
  lead is `texts.apart_lead_discover`, which says that only records with a work and page
  are shown there.
- `title`, `lead` and `lead_study` are `{key, en, ar}`. `ar` is null where there is no Arabic
  text yet. `lead` is Discover-safe; `lead_study` is for Study and Research.

## journeys/{slug}/journey.json, the head

```
{"format": "marsad-journey", "version": 1, slug, kind, state, stale_approval, rule_sha, content_sha,
 approved_by, listed, title, lead, lead_study, door, type, "select": the rule as written, order, order_applied,
 "lists": {file, state, applied, sha, sources_complete, stale_approval, sources: [{key, text}]} | null,
 graph, accepted_share: {accepted, of, no_status}, story_mode: {open, stale, approved_by}, hold_study,
 order_conflict, mixes_stories_and_events, universe, part_labels,
 "groups": [{"key": "main" | "against", "t", "lead", "from", "to"}],
 "anchors": [refs], "excluded": [{"ref", "reason"}],
 "checkpoint": {"items": [question ids], "graded_from": "accepted", "feedback": {"miss", "see"}},
 "rule_text": [{"t", "d", "slots"?}], "ai_documents": [work labels], "ai_note": {"discover", "study"} | null,
 "stops": [{"key", "ref", "n", "group", "part", "urls": {depth: url}, "sort"?: {"default", "az", "links", "accepted_islam"}}],
 "set_apart": [{"key", "ref", "part", "urls", "because": [{"qualifier", "claims"}]}],
 "entities": {ref: {"kind", "name"}}, "parts": [...], "research": [...],
 "reader": {"url": "learn/{slug}/", "anchor": "s-{key}"}}
```

- `state` is `approved` only when the file says so and both the maintainer and the review
  board approved the current `rule_sha`. Software never writes an approval, a status or a
  story-mode decision; `state`, `stale_approval` and `story_mode` are computed.
- `story_mode.open`: continuous narrated playback (for example the Atlas's Play with
  read-aloud) may be offered only when it is true.
- `order_applied` is the order used: `e3`, `e3_pending` (the E3 list file is not reviewed,
  so the order is the Prophet ﷺ, then A to Z) or the rule's own order.
- `groups` cut the stops into runs by number (`from` and `to` are stop numbers, inclusive).
  `against` holds the people recorded as fighting against the Prophet ﷺ at the anchors, in
  a cited record, and not as fighting alongside him there. It is the record's side at that
  event only, never a statement about faith, and never "last".
- `rule_text` lists the order sentences of the rule box with the depth each starts at
  (`d`). Keys with review language start at Study. An item with `"only": "discover"` is
  shown at Discover alone: the Discover form of an order sentence whose Study form refers
  to the order notes (`learn.order.recorded_discover` beside `learn.order.recorded`).
- `stops[].sort` (people journeys): positions in the default order, A to Z, by coverage
  (how many records about the person the graph holds, never rank), and the rank of the
  acceptance-of-Islam sort (null when no cited record gives it).
- `stops[].urls` and `stops[].part` say where each stop is; no consumer computes paths.
- `entities` names every stop, anchor and excluded entity, enough for a contents list.
- `checkpoint.items` are practice question IDs (the reader's `practice/bank.json`) about
  the journey's stops and anchors. Practice questions are made only from accepted claims.
  When a learner's answer misses, the feedback is `learn.check.not_both` ("The record does
  not place them at both, as far as reviewed claims go."), with `learn.check.see_record`
  linking to the person's page `#evidence`. It never says "wrong".

## part-{k}.json

```
{"format": "marsad-journey-part", "version": 1, slug, part, "graph": {"fingerprint"}, content_sha,
 "steps": [Step], "claims": {id: Claim}, "passages": {ref: Passage}, "entities": {ref: Entity},
 "terms": {ref: {"en", "ar"?}}}
```

A part is self-contained: every reference in it resolves in its own tables. Parts are cut
greedily in stop order (the stops, then the set-apart people), and each part and its
research file stay within `PART_BUDGET` = 150,000 bytes (`--part-budget`). A single stop
over the budget stops the export with an error naming it.

**Step**

```
{"key", "ref", "n" (null when set apart), "group": "main" | "against" | "apart",
 "reasons": [{"kind", "other"?, "word"?, "label"?, "ai_document"?, "claims": [ids]}], "links": [same],
 "order"?: {"note": "part" | "recorded" | "unrecorded", "ref"},
 "records": [ids], "contrary": [ids],
 "side": [{"pk", "at", "with", "claims": [ids]}], "side_conflict"?: true,
 "claims"?: {"ids": [ids in list order], "total"},
 "counts": {"records", "discover"},
 "narration": [{"t", "c": [ids], "d", ...slots}],
 "prompts": [{"id", "t", "slots", "answer": {"claims": [ids]} | {"href"}, "graded": false, "d"}],
 "next": [{"t", "ref", "href", "d", "only"?, "journey"?, "n"?, "urls"?}],
 "hints": {"views", "focus", "light", "chosen_by": "rule"},
 "e3"?: {"tier", "pos", "links", "accepted_islam": [{"event", "earliest", "latest", "precision", "claims"}]}}
```

- `reasons` kinds are the v1 kinds: named, part_of, has_part, date_after, date_before,
  date_related, dated_after_this, dated_before_this, dated_related_this, event_claim, part.
- `side` holds only claims whose subject is this stop's person; `with` is the other party.
- `claims` (events and stories steps) is the claim list, at most 80 in list order, with the
  total. `counts.records` counts every claim behind the step; `counts.discover` the eligible ones.
- `d` on an item is the shallowest depth that may show it: `discover` when at least one of
  its claims is eligible (or, for a prompt, when its answer is a link), else `study`.

**Narration.** One item per distinct sentence. Identical sentences (same template and the
same slots) merge, keeping every claim, so a fact backed twice shows two source lines.
Items are ordered by the rank of their predicate key in `index.json` `narration_order`,
then the rest by key, then citation, then claim ID. Slots are references: `subject`,
`object`, `event` (entities), `text` (`{value, lang}`, a literal as written), `role`,
`relation` (terms) and `markers` (`[{"t": "learn.narr.marker", "marker": q-ref}]`, appended
for a record that carries a marker the rule sets apart). The templates (`learn.narr.*`)
are attributive: "The record says...", "The record places...", "The story ... names ...".
Narration never reads an assertion's comment.

**Prompts** are never graded. `learn.prompt.event_who`, `event_when`, `event_where`,
`person_elsewhere` (a link to the person's page `#evidence`), `person_contrary` and
`story_names`, shown under `learn.prompt.note`. Their IDs are `{slug}:{stop key}:{prompt}`.

**Next** directions are fixed by rule: the entity page (`learn.next.page`, `#evidence`),
the stop's records at Study (`learn.next.study`, shown at Discover only: `"only": "discover"`)
and the same entity in another journey (`learn.next.also_in`). A consumer may choose among
them and never adds one.

**Hints** come from a closed vocabulary (`index.json` `view_vocabulary`) by rule: an event
with a recorded date gets `time`; an event whose one place has a single located point gets
`map`; a story gets `stories`; a person with kinship claims gets `lineage`; otherwise `sky`.
On the Prophet's ﷺ step `focus` is null and `light` is true. Hints carry no fact.

**Claim**

```
{"kind": "assertion" | "participation" | "link", "pk", "s": ref, "o": ref | "text": {"value", "lang"},
 "status": "proposed" | "under_review" | "accepted" | "rejected" | "superseded" | null, "statuses"?: [...],
 "discover": bool, "passage"?, "basis"?, "recorded_by"?: [{"label", "software"}],
 "note"?: {"text", "ai_document"}, "ai_document"?: true, "software"?: true,
 "role"?: role local (participations only), "qualifiers"?: [locals], "voice"?, "at_event"?: ref}
```

- `status` is exact, never folded. A claim recorded with several statuses also has
  `statuses`, the full sorted list, and `status` is then the most cautious of them
  (rejected, superseded, under review, proposed, accepted, in that order).
- `pk`: an assertion's predicate local name, with `rel_`; `took_part` for a participation;
  `took_place_at` or `part_of` for a plain link. The Atlas's ObsData `pk` is this with `rel_`
  removed for an assertion (`rel_participated_in` is `participated_in`). For the other two
  record kinds, participations and plain links, it is the same key: `took_part`,
  `took_place_at` and `part_of` (three keys for two kinds). Only ObsData's translated `p`
  label is built from the `claim.*` i18n keys.
- `role` is only the participation role. An assertion's comment is never a role.
- `note` is an assertion comment that is not an AI gloss, for example the 50 Stories
  document's own notes. Study and above.
- `basis` (the recorded non-report basis) and `recorded_by` are Study and above.
- An assertion comment that starts with "AI gloss (" is a gloss. It is never in a head or
  part file, only in `research-{k}.json`, and is shown at Research under `learn.gloss.label`.
- `ai_document`: the claim's passage is from an AI-generated work (its creator is a
  software agent, or its title starts "50 Stories"). `software`: a software agent recorded it.

**Passage** `{"cite": full citation | null, "short": Discover form | null, "work", "ai_document", "story"?: ref}`

**Entity** `{"kind", "name", "scholarly", "subtype"?, "prophet"?, "links", "coverage_state"?, "dates"?, "places"?, "number"?, "part_label"?, "work"?, "ai_document"?, "geo"?}`

- `name` is the display name (popular form, the honorific sign after the Prophet's ﷺ name);
  `scholarly` is the label as recorded. `links` is how many records about it the graph holds.
- `dates`: `[{native, calendar, earliest, latest, precision, basis, relative?, disputed?, "text": {"en", "ar"}}]`.
  `text` is Gregorian first, with digits 0–9 and, in `ar`, Arabic Gregorian month names.
- `geo` (places): `{"lon", "lat", "confidence", "basis", "recorded_by"}` for a single WKT
  point (WKT order: lon, then lat), `{"many": n}` when several different points are
  recorded (none is chosen), `{"unlocated": true, "basis"}`; no `geo` without a geometry state.

## The source line

`source_line(claim, depth, passages, t)`:

- **Discover**: only for an eligible claim, the short form: the work and its first locator
  (`vol. N, p. N`, `pp. N–N` or `Part N, story N`), with parenthesised remarks left out and
  everything after the first ";" cut. Example: "Ibn Hishām, al-Sīra al-Nabawiyya, vol. 1, p. 485".
  There is no fallback at Discover.
- **Study and Research**: the full citation, else the basis text, else who recorded it
  (`claim.recorded_by`), else `common.not_recorded`.
- A claim from an AI-generated document gets `learn.source.ai_document` ("{source} (a
  document generated with AI)") at every depth. A journey with such material has
  `ai_documents`, and its note is `learn.ai_source_note` at Discover, `learn.ai_note` at Study.

## research-{k}.json

`{"format": "marsad-journey-research", "version": 1, slug, part, "glosses": {claim id: text}, "trace": {stop key: {"hop"}}}`

## strings.json and pages.json

`strings.json` is `{"en": {...}, "ar": {...}}`: every i18n key the export names, with the
`.one` and `.other` forms of plural keys. That includes the keys of `index.json` `texts`,
`labels`, `sorts`, `reasons` and `order_notes`. With `terms`, the data reads without the app.

`pages.json` is `{"format": "marsad-learn-pages", "version": 1, "pages": [{"path", "file",
"kind": "journey" | "index" | "practice", "journey"?, "depth", "page", "pages", "door"?, "first", "last"}]}`.
A journey's door depth is at `learn/{slug}/`; the other depths are at `learn/{slug}/{depth}/`;
page k of a split depth is at `.../p{k}/`. `first` and `last` are the stop keys on the page.
Each depth is cut at its own weight: greedily in stop order (the stops, then the set-apart
people), at most 220,000 bytes of step HTML a page (`--step-budget`), page 1 less its
contents list; a page holds at least one stop. Page 1 of a split depth lists every stop and
carries the anchor `s-{key}` of each stop on another page, so `learn/{slug}/#s-{key}`
resolves without JavaScript.

## How to use it

- **Reader pages** are rendered from the same resolved journeys, one static page per depth
  (or several, when a depth is split). Every page's `<article>` carries `data-depth`,
  `data-total` and `data-steps` (the journey's stop keys), and `nav.journey-depths` links
  to the page of each depth that holds its first stop.
- **Sky Atlas**: call `journey_export.resolve_all(site)`, or read `site/dist/learn/data/`.
  At its public depth, show only `discover` claims, each with `passages[...].short`; gate
  Play and read-aloud on `story_mode.open`; restore tokens with `content_sha`.
- **Expeditions**: read `index.json`, then each `journeys/{slug}/journey.json` and its part
  files, or run the CLI on any graph. `assertion/{id}` is your `ast:{id}`. Places carry
  `geo` with its provenance, so a point can be drawn without the graph. A learn journey
  needs its own route (for example `#j-{slug}~{pid}`) beside `#x-{slug}`.
- Apply the Discover rule at every public depth, and the depth policy for the others.

## The Atlas facade

`atlas/build.py` imports `learn/journeys.py` directly (the v1 facade: `load_specs`,
`build`, `build_all`, `RuleError`, `Journey.steps / set_apart / anchors`, `Step.iri /
reasons / records / contrary`, `Reason.kind / other / word / label`, the Claim fields).
`journey_export.atlas_projection(journey, strings)` reproduces the record its
`load_journeys` builds, with IRIs in place of node numbers, plus `story_mode.open`.
`learn/facade.lock` holds `{"facade_version", "inputs", "engine"}`: `inputs` is sha12 of
what the Atlas sees of the shipped rule files (their facade fields, en title and lead, the
computed status and story mode, the list file's content and state); `engine` is sha12 of
the projection of fixed fixture rules on `fixtures.facade_graph()`. When either changes,
the Atlas page needs a rebuild: rebuild `atlas/index.html` (`atlas/build.py` on
`build/graph-all.ttl`) and run `learn/journey_export.py --lock`.
