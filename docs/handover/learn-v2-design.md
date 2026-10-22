# learn-v2 design: one shared journey format (revision 2)

Branch `learn-v2`, from `origin/main` f859b53. The brief is `docs/handover/learn-v2-brief.md`; this file is the design behind it, made by a three-way design panel, three judges and four skeptics (revision 2 answers them; §17 lists what changed). The handover after the build is `docs/handover/learn-v2.md`, 60 lines or fewer.

## 0. In one paragraph

A journey is a rule file in `learn/journeys/`. The v1 rule language stays as it is, plus a few optional v2 keys. One engine (`learn/journeys.py`, v1 code kept) chooses and orders the stops. One resolver (`learn/journey_export.py`, new) turns each built journey into a versioned, byte-stable JSON document, **marsad-journey v1**. That document holds:

- the ordered stops, keyed by entity pid, each with its group;
- why each stop is there, and the claims behind it. Each claim carries its exact status, its source (work and page where the record gives one), its AI flags, and a `discover` flag that says whether a public page may show it;
- narration as template keys bound to claim IDs;
- ungraded prompts, next directions and view hints, with place points and their provenance;
- the E3 order and the other sorts, the F11 exclusions, approval and story-mode state, the graph fingerprint and a per-journey content digest.

The reader Learn pages are rendered from that document at three depths. Discover (public) shows a claim only together with its work and page, and never shows review status or review language. The Sky Atlas keeps importing the v1 facade unchanged, and can later call `resolve_all(site)`. Expeditions reads the files, or runs the CLI on any graph.

Nothing in this slice touches `site/`, `ontology/`, `atlas/`, `expeditions/`, `lab/`, `ask/`, `scripts/` or `.github/`.

## 1. Binding decisions and where each is met

| Decision | Where |
|---|---|
| 1. Narration from claims; prose only after approval; AI drafts labelled | §7.1 template narration. §4.4: the prose layer is specified, deferred, and never shown at Discover. |
| 2. Track 0 method text by hand; examples by rule with source | §4.2 (deferred). The example grammar includes an absence pick. |
| 3. Teacher lessons apart, labelled, unlisted | §4.3: never repository files. `validate()` refuses `kind: teacher`. |
| 4. Practice wording; graded only from accepted claims; no multiple choice; prompts never graded | §7.3 prompts are `graded: false`. §7.4: checkpoint data comes from `practice.bank()` (accepted only), with the exact binding sentence. |
| 5. Story mode opened by the board per journey; accepted share as a guide | §3.6 `story_mode`, also computed in the facade copy. `accepted_share` is exported and shown at Study. |
| 6. 50 Stories records count, labelled; part-of proposals | §7.2: the AI-document label appears at every depth, including on set-apart lines. §15 proposals. |
| 7 / G1, G8. Discover shows no review status or language, only the source line (work and page) | §7.0: a claim is Discover-eligible only when it has a citation (work and page). §8: a separate page per depth, a key guard, and HTML checks that also scan the source text. |
| 7 / E3. People order | §6, in this order: the Prophet ﷺ; the list tiers, only from a *reviewed* list with sources; then coverage, labelled. A–Z while the list is unreviewed. The recorded side at the event is shown as a labelled group. Acceptance of Islam is a sort, where recorded. Nobody is placed last for faith without a recorded term. |
| 7 / F11. Background out of learning paths | §5: one `background(site)` hook, plus a "not placed" class. |
| 7 / W5, W6 | §7.5 next candidates and §7.6 view hints, both chosen by rule. AI may choose among them and never adds a fact. |
| 7 / H1, L1, L2 | §12 |
| 8. Rules, never by hand; no IDs; drafts until approved; software never approves | §3.5: approvals are bound to `rule_sha`. ID scan, AST scan and byte-identity tests. |
| 9. The E1 Hijrah page keeps working | §3.7 `hold_study`, plus a golden-hash test. |
| 10. Scale and the 300,000-byte budget | §13: byte split per depth. Export parts are ≤150,000 B each. |
| 11. The Atlas facade | §11: names unchanged, plus `learn/facade.lock` and a test. |

## 2. The parts

```
learn/journeys/*.json           rule files (v1 keys + optional v2 keys)           <- humans write; software never writes
learn/lists/people.json         E3 membership lists, by name, with sources        <- humans write; approval bound to content sha
learn/i18n/en.json, ar.json     every interface word; ar = journey titles/leads only in this slice
        |
learn/journeys.py               v1 engine + v2 validation + background() + side groups + e3 hook  (the Atlas imports this)
learn/journey_lists.py          lists, name matching, link counts, e3_key, acceptance records     (imported lazily)
learn/journey_export.py         resolve / resolve_all / write / atlas_projection / CLI
        |
site/dist/learn/data/           index.json, strings.json, pages.json,
                                journeys/<slug>/journey.json, part-<k>.json, research-<k>.json
site/dist/learn/<slug>/...      reader pages at three depths, rendered from the resolved dict
```

- New modules are all named `journey_*`, so none can shadow a module in `site/`, `site/observatory/`, `ask/` or `atlas/` on the Atlas's `sys.path`.
- `learn/journeys.py` stays a module.
- Each slug has its own data folder, so no slug can overwrite `index.json`, `strings.json` or `pages.json`.

## 3. Journey spec v2 (the rule language)

### 3.1 Files

| Path | What it holds |
|---|---|
| `learn/journeys/<slug>.json` | Official journeys only. `load_specs` reads only these, through a non-recursive `glob("*.json")`. |
| `learn/journeys/method/<slug>.json` | Reserved for Track 0 (deferred). `load_specs` never looks here. |
| `learn/lists/people.json` | The E3 lists. |
| `learn/proposals/hijrah-parts.json` | The decision-6 proposals, as label rules (§15). |

Teacher lessons are never files in this repository (§4.3).

### 3.2 Keys

A v1 file is a valid v2 file. Unknown keys are still refused.

Required (v1, unchanged): `slug`, `status`, `approved_by`, `title`, `lead`, `door`, `select`, `order`.

Optional (v2, validated, closed set):

| Key | Shape | Meaning |
|---|---|---|
| `kind` | `"official"` | Default `official`. Any other value is a RuleError. The message points to `method/`, or says that lessons are not repository files. |
| `lead_study` | i18n key | Used at Study and Research. `lead` must be Discover-safe: its en text holds no review word, and its ar text holds no Arabic review stem (tests). |
| `story_mode` | `{open: bool, approved_by: [approval]}` | Absent means closed (§3.6). |
| `lists` | repository-relative path `^[a-z0-9_-]+(/[a-z0-9_.-]+)*\.json$`, no `..` | Required if and only if `order` is `e3`. |
| `hold_study` | bool | §3.7. Presentation only, outside `rule_sha`. |
| `select.group_by` | `"side"` (people only) | §6.4. |

More on `lists`:

- The path is resolved against the repository root, `Path(journeys.__file__).resolve().parents[1]`, never against the working directory.
- `build(site, spec, links=None, *, lists_root=None)` lets fixtures point elsewhere. The keyword is optional, so the Atlas call does not change.
- `validate()` checks only the shape, so `load_specs` never fails on a missing file. `build()` raises RuleError for every list problem (§3.5).

Approval entries take the form `{who: maintainer|review_board, date, spec?: 12 hex, note?: str ≤300}`.

- `date` must first match `^\d{4}-\d{2}-\d{2}$`, then pass `datetime.date.fromisoformat`. So `2026-02-30` is refused. Python 3.13 accepts `20261102` and `2026-W45-1`, but the pattern refuses them before they get there.
- The same `who` may not appear twice.

Tightened checks (no shipped file is affected):

- Rule words match `^[A-Za-z][A-Za-z0-9]*$`.
- `kinds` must be distinct.
- A non-string term raises RuleError, not TypeError.
- `RESERVED_SLUGS` = (`assets`, `practice`, `data`).

### 3.3 Selectors

`named` = `{kinds, words?, phrase?, not_words?}`.

- At least one of `words` (any of them) or `phrase` (a contiguous token sequence) is required. `not_words` means none of them.
- Matching runs over the folded, lower-cased token *sequence* of every `rdfs:label`. Note that `tokens()` drops "ﷺ".
- A phrase match reports `Reason("named", word="<phrase joined by spaces>")`.

The other v1 selectors are unchanged: `events` (named / follow / max_links), `people` (events / participation / also_show / set_apart) and `stories` (part.words). `people` also accepts `group_by: "side"`.

### 3.4 Orders

- events: `recorded`.
- people: `prophet_first_then_name` | `name` | **`e3`** (§6).
- stories: `story`.

### 3.5 Approvals bound to the rule

One canonical byte form, used for every hash in learn:

```
canonical(obj) = json.dumps(nfc(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
sha12(obj)     = sha256(canonical(obj)).hexdigest()[:12]
```

`nfc` applies `unicodedata.normalize("NFC")` to every string, keys included. `FORMAT.md` states this with a known test vector. `index.json` exports each sha, so consumers never recompute one.

```
rule_sha(spec) = sha12({"spec": spec without status / approved_by / story_mode / hold_study,
                        "strings": {"en": {title, lead, lead_study texts}, "ar": {same keys, where present}},
                        "lists": sha12(list file's "lists" array) | "missing" | "unreadable" | null})
```

- **When the list file cannot be read or parsed**, `rule_sha` uses the sentinel and the state is draft. `load_specs` still returns the spec and never raises. `build()` raises RuleError for every list problem: missing, unreadable, invalid, or a member matching zero people or two or more. The Atlas's `except jmod.RuleError` therefore holds.
- **`state(spec)`** is `"approved"` only when `status == "approved"` **and** both roles have an approval whose `spec` equals the current `rule_sha`. Otherwise it is `"draft"`.
- **`stale_approval`** is true when approvals exist for another hash. A stale file never raises. `test_no_shipped_journey_has_a_stale_approval` fails CI instead.
- **`load_specs`** returns copies whose `status` is the computed state and whose `story_mode` is the computed one (§3.6).
- **Software never writes** `status`, `approved_by` or `story_mode`. A test proves that the build and the export leave every spec and list file byte-identical. An AST scan finds no write call aimed at `learn/journeys/` or `learn/lists/`.
- **`build_learn` prints each journey's `rule_sha`**, so the approvers know what they are approving.

An approval looks like this. People write it; code never does.

```
"status": "approved",
"approved_by": [{"who": "maintainer", "date": "2026-11-02", "spec": "<rule_sha>"},
                {"who": "review_board", "date": "2026-11-09", "spec": "<rule_sha>", "note": "rule only; claims keep their own status"}]
```

### 3.6 Story mode (decision 5)

- `story_mode.open = true` needs a `review_board` entry whose `spec` equals the current `rule_sha`. Otherwise the computed `open` is false and `stale` is true.
- The copies `load_specs` returns carry `story_mode = {open: <computed>, stale, approved_by}`, so the Atlas can gate its Play and read-aloud on `spec["story_mode"]["open"]` without loading the export. It is part of `atlas_projection` and of the `facade.lock` inputs.
- Story mode means continuous narrated playback of the narration sentences, without the evidence ladder. Consumers may offer it only when `open` is true.
- All three journeys ship closed.

### 3.7 `hold_study` (decision 9, E1)

When it is true, the journey's Study pages render exactly as v1 did. The only additions are:

- the depth links (`nav.journey-depths`);
- invisible `id="s-<pid>"` anchor spans;
- base-relative links to the same targets;
- the `data-depth`, `data-total` and `data-steps` attributes that §8 puts on every `<article>`.

Under the hold, Study shows no prompts, no next directions and no accepted share, and the AI-gloss role lines stay where v1 shows them.

**Golden check.** Before the renderer is changed, the implementer records two values in the test file (neither is an entity ID):

- the sha256 of the v1 Hijrah page, with `href` and `id` values blanked and whitespace collapsed;
- the Hijrah `content_sha` (§9) on the current graph.

While the `content_sha` still matches, the test compares the v2 Study page, with the permitted additions taken out, against that hash. `learn/tests/golden.py` `held_page()` is the one statement of that recipe: it removes `nav.journey-depths`, the empty `s-*` spans and the three `<article>` attributes, and `page_sha()` blanks every `href` and `id` value. Anything else a held page adds fails the test. Once the graph changes, the test skips with the message "re-verify E1". The invariant checks still run.

Hijrah ships with `hold_study: true`. Discover and Research pages are new and are not held.

### 3.8 The three shipped files after this slice

```
hijrah-step-by-step.json
{"slug": "hijrah-step-by-step", "status": "draft", "approved_by": [],
 "title": "journey.hijrah.title", "lead": "journey.hijrah.lead", "lead_study": "journey.hijrah.lead_study",
 "door": "study", "hold_study": true,
 "select": {"type": "events", "named": {"kinds": ["event", "story"], "words": ["Hijra", "Hijrah"]},
            "follow": ["parts", "date_anchors"], "max_links": 2},
 "order": "recorded", "story_mode": {"open": false, "approved_by": []}}

people-of-badr.json
{"slug": "people-of-badr", "status": "draft", "approved_by": [],
 "title": "journey.badr.title", "lead": "journey.badr.lead", "lead_study": "journey.badr.lead_study", "door": "study",
 "select": {"type": "people",
   "events": {"named": {"kinds": ["event", "story"], "words": ["Badr"], "not_words": ["expedition", "raid"]},
              "follow": ["parts"], "max_links": 1},
   "participation": {"records": true, "claims": ["mrs:rel_participated_in", "mrs:rel_led", "mrs:rel_present_at", "mrs:rel_witnessed"]},
   "also_show": ["mrs:rel_absent_from"], "set_apart": ["mrsv:q_accepted_islam_later"], "group_by": "side"},
 "order": "e3", "lists": "learn/lists/people.json", "story_mode": {"open": false, "approved_by": []}}

first-believers.json
The v1 file plus "story_mode": {"open": false, "approved_by": []}. Its lead is already Discover-safe, and its door stays "discover".
```

Strings:

- `journey.hijrah.lead` = "The events the record ties to the Hijrah, in the order the record supports."
- `journey.hijrah.lead_study` = today's lead, word for word.
- `journey.badr.lead` = "The people the record places at Badr, each with the records that place them there."
- `journey.badr.lead_study` = today's text.
- The Arabic texts go in `learn/i18n/ar.json` (§12).

Effects on the facade output, all in this PR, needing one Atlas rebuild:

1. The leads become Discover-safe.
2. On the joined graph, `not_words` cuts Badr's anchors from 9 to 4.
3. On the joined graph, `group_by: side` moves the 79 people recorded as fighting against the Prophet ﷺ at Badr after the others.

While the list file is unreviewed, Badr's order is otherwise the v1 order (§6.3). On the page graph, Badr's steps and order are unchanged.

### 3.9 Reserved, refused, specified for later

- **`last_if` and a `last` list key** for "died as a disbeliever". Neither is in the closed key set. `validate()` and `load_lists()` refuse them with the message "waits for round 4 Q2". `rel_fought_against`, `rel_opposed` and `q_accepted_islam_later` are refused as proxies for it.
- **`named.words_ar`, `stages` / `from_stage`, and the new `select.type` values of §4** are later slices. Each one registers in `STEP_TYPES` / `ORDERS` and in the export without changing the facade.

## 4. Step kinds

| Kind | In this slice | Selection | Data today |
|---|---|---|---|
| events (v1) | yes | Named words, phrase and not_words, then breadth-first along parts / wholes / date_anchors / event_claims up to max_links. Kahn order. **New:** background IRIs are never seeds and are never walked through (§5). | Page graph: Hijrah 7 steps, 66 claims about them, 40 with a work and page (9 of them from 50 Stories). 2 steps have no cited claim. Joined graph: 9 steps, 68 of 94 claims cited, 2 steps uncited. |
| people (v1 + e3 + side groups) | yes | Participation records and whitelisted claims at the anchors. also_show never chooses anyone. set_apart by qualifier. **New:** order e3 and group_by side. | Page graph: Badr 92 steps (+2 apart, both from 50 Stories story 20), 3 anchors, 103 of 133 records cited, 1 step uncited. Joined graph with not_words: 438 steps (+1), 4 anchors. 314 people are recorded as fighting alongside the Prophet ﷺ and 79 as fighting against him, all cited. |
| stories (v1) | yes | The 50 Stories in a part whose title has a word, in reading order. | first-believers: 13 stories, 79 claims, all cited, all from the AI-generated document. |
| method (Track 0) | specified (§4.2) | Hand-written tool text; examples by rule. | none |
| teacher lesson | specified (§4.3) | Hand-picked; never in the repository. | none |
| list, life, place, period, dated, text_order, opposition, route, family, chain, dispute, compare | later slices | See below. | |

Later kinds, so the format reserves room for them:

- **list**: the members of a reviewed list.
- **life**: one person's moments in `site/thread.py` order.
- **place**: events at a place. Unlocated places are listed, never drawn.
- **period**: events wholly inside two rule-named, dated boundaries.
- **dated**: dated, non-background events.
- **text_order**: the median OpenITI milestone.
- **opposition**: recorded fought_against / opposed claims, neutral.
- **route**: `rel_travelled_via` in text order, "order, not road".
- **family**: kinship within 1–2 links.
- **chain**: TransmissionChains.
- **dispute**, **compare**: with the coverage caveat.

life, period and family ship only after slice 11b's background marker covers events dated only to the year 632, and covers people.

### 4.2 Method format (deferred)

```
learn/journeys/method/<slug>.json:
{slug, kind: "method", status, approved_by, title, lead,
 steps: [{text: "method.<slug>.<name>",
          example?: {journey: <official slug>,
                     pick: "first_claim_with" | "first_step_without" | "first_step",
                     predicate?: <mrs: term>}}]}
```

- An example resolves from that journey's export, and only to a Discover-eligible claim (§7.0) shown with its source line.
- For `first_step_without`, it resolves to a computed absence sentence ("No claim in this record gives a date for {name}.").
- No resolvable example is a RuleError.
- `test_method_text_names_no_entity_and_no_digit` ships with this kind.

### 4.3 Teacher lessons (deferred)

A lesson is a file that a teacher keeps outside this repository and gives to a future CLI (`--lesson PATH`):

```
{slug, kind: "teacher", title_text, teacher: <role label>, claims: ["assertion/<id>", ...]}
```

- Every resolved stop carries `label_key: "learn.teacher.label"` ("A teacher's lesson, not reviewed").
- A lesson is never returned by `load_specs`, `resolve_all` or `index.json`, and never shown at Discover.
- Listing needs a board decision.
- In this slice, `validate()` refuses `kind: teacher`, and a test checks that no file under `learn/` holds one.

### 4.4 Prose layer (decision 1, deferred)

```
learn/prose/<slug>.json: {items: [{id, at, text: {en, ar?}, author: "ai"|"human", sha256, approved_by: [{who, date, sha256}]}]}
```

- An item is approved only when both roles have approved its current `sha256`.
- Unapproved items show only at Study and Research, labelled `learn.prose.ai_draft`. They never show at Discover.
- The validator allows at most 600 characters and no pid. Every digit run and every capitalised name token must occur in the labels or literals of the anchor claims.
- Hijrah Night's drafted stages could attach only through a passage section key, which is a data proposal for slice 11.

## 5. Background (F11)

`journeys.background(site) -> {iri: reason}` is the single hook, cached on `Links` and computed once per Site. Its rules, in order:

1. **marker**: slice 11b's background marker, once 11b names the property. Until then `BACKGROUND_MARKER = None`.
2. **after_prophet**: an event or story whose every recorded extent starts after the *after bound*. The after bound comes from the first of these that applies:
   - (a) the event the Prophet ﷺ is recorded as dying during: a `rel_died_during` claim of any status, with exactly one dated event;
   - (b) the dated event whose whole token sequence (`tokens()` order, which drops "ﷺ") equals `death of the prophet` (exactly one);
   - (c) the fallback constant `0632-12-31`.

   On the page graph, (b) matches "Death of the Prophet ﷺ", day precision, 632-06-06 to 632-06-08. A whole-label comparison after `fold()` would miss it, because `fold()` keeps ﷺ. On the joined graph, (a) gives the same date.
3. **not_placed**: an event whose every extent is coarser than a day and contains the after bound. On both graphs these are seven year-632 events, including the Farewell Pilgrimage and Usāma's appointment (an accepted cost until 11b's marker).
4. **before**: every extent ends before `0570-01-01`. There is no edge class at this bound.

How the engine uses it:

- `select_events` never seeds from or walks through a background IRI. `build_people` drops background anchors. `build_stories` skips background stories.
- Whatever a rule would otherwise have chosen goes to `Journey.excluded = [(iri, reason)]`, which is listed at Research only.
- `index.json` reports `after_source` (`recorded_death` | `named_event` | `fallback`). The page graph reports `named_event`.

**Lineage-only people are not background.** On the page graph, 11 people have only kinship claims, among them four Mothers of the Believers. Person background comes only from the 11b marker. No shipped journey has a background step or a not-placed step on either graph.

## 6. People order (E3)

`learn/journey_lists.py` is imported lazily by `build_people`, only when `order == "e3"`.

### 6.1 The list file

`learn/lists/people.json`, format `marsad-lists` v1:

```
{"format": "marsad-lists", "version": 1, "about": "...", "status": "proposed", "approved_by": [],
 "lists": [{"key": "rashidun", "members": [display names], "order": "succession", "source": null},
           {"key": "ten", "members": [...], "order": "as listed in the report", "source": "<the Atlas's text>"}]}
```

- **Members** are copied verbatim from the Atlas's `atlas/data/lists.json` (sky-atlas-new): names only, never IDs.
- **The ten** keep the Atlas's source (al-Tirmidhī no. 3747; Abū Dāwūd no. 4649; the numbers are to be checked against print).
- **The rāshidūn's source is not copied.** The Atlas's source points to the graph's own succession events. Those events are F11 background or not-placed, and their claims carry no source edition. The field is `null` until the board gives a work and page for the succession order.
- **The file is reviewed** only when (i) both roles have an approval `{who, date, sha}` whose `sha` equals `sha12(lists)`, **and** (ii) every list has a non-empty `source` with no review word in it. Otherwise its state is `proposed`.

### 6.2 Matching

`match_members(site, names)` compares `names.normalise(member)` against `names.normalise` of every person's display name, scholarly label and other labels.

- Each member must match exactly one person. Zero, or two or more, raise RuleError, naming the member and the count.
- All 14 of 14 members match uniquely on both graphs, also with `display.EXPAND_B_TO_IBN = True`.

### 6.3 The key

| List state | Key, inside each group (§6.4) |
|---|---|
| Not reviewed (today) | (not the Prophet ﷺ, `display.sort_key(name)`, pid): the v1 `prophet_first_then_name` order. |
| Reviewed | Tier 0: the Prophet ﷺ (`Entity.prophet`, a label rule). Tier 1: rāshidūn, in list order. Tier 2: the rest of the ten, in list order. Tier 3: everyone else, by `-links`, then `sort_key(name)`, then pid. |

- Why A–Z until the list is reviewed: E3's default is the whole sequence of Prophet, rāshidūn, the ten, then the most connected. Applying only its last part reorders the Companions by a computed count (ʿAlī 2nd, ʿUthmān 8th on the joined graph). That is an order E3 does not describe, and readers can take it as a ranking.
- `links = len(site.claims[iri])`: assertions, participation records and links. It is always called coverage, never rank.
- The same key sorts the set-apart people.

### 6.4 Side groups (`group_by: "side"`)

A person goes to the **against** group when both of these hold:

- they are the *subject* of a `rel_fought_against` claim with `mrs:atEvent` among the anchors, whose object is the Prophet ﷺ, that has a citation and whose status is not rejected or superseded;
- they are the subject of no such `rel_fought_alongside` claim.

Everyone else is in the **main** group, the Prophet ﷺ included. Someone with both is placed in main and flagged `side_conflict`, shown at Study (none today).

- The groups follow one another: main, then against. Each group is ordered by §6.3.
- The rule box says so at every depth with `learn.rule.group_side`, after the order sentence: "People recorded as fighting against the Prophet ﷺ at these events, in a record that gives a work and page, and not recorded as fighting alongside him there, are listed after the others, under their own heading. The order above applies inside each group." It is shown whenever the rule has `group_by: "side"`, also when the group is empty.
- The against group's heading is `learn.group.against`: "Recorded as fighting against the Prophet ﷺ at this event".
- Its lead is `learn.group.against_lead`: "The record lists these people among those who fought against the Prophet ﷺ here, each with its source. This is the record's side at this event only. It says nothing about anyone's faith or later life."
- The grouping is the event's recorded side (F1: the text's list headings). It is **not** the E3 "died as disbelievers, last" rule, and it is never called last.
- On the page graph the group is empty. On the joined graph it holds 79 people, all cited to Ibn Hishām's list headings. Among them are some recorded elsewhere as accepting Islam later (for example Suhayl b. ʿAmr), which is why the group says nothing about faith.

### 6.5 Other sorts (exported, not rendered on reader pages in this slice)

Each people stop carries `sort: {default, az, links, accepted_islam}` in the journey head.

`accepted_islam` comes from recorded claims with sources only:

- The person is the subject of a `took_part` or `rel_participated_in` record **with a citation** at an event whose label holds the phrase `acceptance of islam` (`ACCEPTANCE_RULE`, a named rule exported in `index.json`, never an ID).
- Order: people at a dated event by its earliest start, with equal extents sharing a rank. Then people recorded only at undated events, grouped by event in name order and labelled `learn.sort.undated`. Then `null` ("not recorded").
- Page graph: 49 people have a cited acceptance record. Only 3 of them are at dated events (Abu Bakr, ʿAlī and Zayd, all 609–611, tied). The other 46 are at "The early acceptance of Islam in Makkah (Ibn Ishaq's list after the first eight)". 29 of the 92 Badr steps have one.
- The data per stop is `e3.accepted_islam: [{event, earliest, latest, precision, claims}]`.

### 6.6 Nobody is placed last for faith

There is no recorded term for "died as a disbeliever", so no last tier exists (§3.9). The Study rule box says so (`learn.order.e3_no_last`).

### 6.7 Text

| Key | When | Depths | Text |
|---|---|---|---|
| `learn.order.prophet_first_then_name` (v1) | e3 while the list is not reviewed | all | The v1 sentence. |
| `learn.order.e3_pending` | e3 while the list is not reviewed | Study, Research | "This journey uses the E3 order. Its list file ({file}) is {state}, so al-Khulafāʾ al-Rāshidūn and the ten are not placed yet." |
| `learn.order.e3` | reviewed | all | |
| `learn.order.e3_sources` | reviewed | all (Discover-safe) | The lists' sources, each in a `.source` span. |
| `learn.order.e3_links` | reviewed | all | "Then everyone else by how many records about them this record holds (statements, participation records and links), most first. That number shows how much is recorded (coverage), not rank or importance." |
| `learn.order.e3_lists` | reviewed | Study, Research | The list file, its state and its sha. |
| `learn.rule.group_side` | `group_by: "side"` | all (Discover-safe) | The groups and that the order applies inside each (§6.4). |

### 6.8 Verified

On the page graph, with the shipped list treated as reviewed on a fixture copy: the Prophet ﷺ, Abu Bakr, ʿUmar, ʿUthmān, ʿAlī, Ṭalḥa, al-Zubayr, ʿAbd al-Raḥmān b. ʿAwf, Saʿd, Saʿīd b. Zayd, Abū ʿUbayda, then Bilāl (20), Ḥamza (17), Zayd b. Ḥāritha (15).

On the joined graph, coverage with the tiers off would have put Abu Jahl 9th, ʿUtba b. Rabīʿa 12th and Umayya b. Khalaf 16th. This revision avoids that twice over: the A–Z fallback, and the side group.

## 7. Layers per step

Every layer item is data: `{t: i18n key, c: [claim ids], d: min depth, ...slots as refs}`. Names, dates and labels are filled at render time from the graph through `display.py`. No layer prints free text other than recorded data (names, literals as written, citations, basis, term labels) or, later, approved prose.

### 7.0 Claim fields and Discover eligibility

**Discover-eligible.** A claim is Discover-eligible (`discover: true` in the export) if and only if:

- it has a citation, meaning a passage with `mrs:canonicalCitation`, which gives a work and a locator; **and**
- its status is not `rejected` or `superseded`.

Once `PUBLIC_MODE` is `accepted`, its status must also be `accepted` (§8).

Participation records and plain links have no citation. Neither do claims resting only on `nonReportBasis`. None of these is ever eligible.

Discover shows a claim only when it is eligible, and only with its short source line. Uneligible claims are counted into "{n} more records at Study". Consumers (Atlas, Expeditions) must apply the same flag at their public depth.

**Fields with a fixed meaning.**

| Field | Holds | Where it goes |
|---|---|---|
| `role` | The **participation** role only, as its vocabulary key. Its label is in `terms`. | Part files. An assertion never has `role`. |
| `gloss` | An assertion's `rdfs:comment` that starts with the AI-gloss prefix `AI gloss (` (stored with the prefix stripped). | Only `research-<k>.json` `glosses[id]`. Never in a head or part file. Shown at Research, labelled `learn.gloss.label`. |
| `note` | Any other assertion comment (for example the 50 Stories document's own notes). It carries `ai_document` when its work is AI-generated. | The part, with min depth `study`. Never at Discover. |
| `basis` and `recorded_by` | The claim's basis text and the agents who recorded it. | Exported with min depth `study`. Never at Discover. |

Narration never reads an assertion comment, and never reads `Claim.role` for an assertion (`site/model.py:289` fills it with the comment).

### 7.1 Narration (decision 1)

Per step, `narration` is an ordered list of `{t, c, d}`. The input:

- **people steps:** `Step.side` first, then `Step.records`, then `contrary`;
- **stories steps:** `Step.records`;
- **events steps:** every claim about the entity.

**Merging.** Identical sentences merge into one that keeps every claim, so a fact backed twice shows two source lines. Sentences are identical when they share the same template, subject, object, literal text and participation role key.

**Order.** By the rank of the predicate key in `NARRATION_ORDER`: rel_dated, took_place_at, rel_occurred_at, part_of, rel_part_of, rel_led, rel_sheltered_at, took_part, rel_participated_in, rel_present_at, rel_witnessed, rel_absent_from, rel_preceded, rel_followed, rel_fought_alongside, rel_fought_against, rel_died_during. Then the rest by key, then citation, then claim ID.

**Depth.** An item has `d: "discover"` when at least one of its claims is Discover-eligible. At Discover it shows only those claims' sources. Otherwise it has `d: "study"`.

**Templates.** They are attributive: records, never a verdict (A3). Keys are `learn.narr.<pk>`:

| Key | Sentence |
|---|---|
| took_part / rel_participated_in | "The record says {subject} took part in {object}." |
| took_part_role | "... ({role})." Here `{role}` is the participation role label. |
| rel_led | "The record says {subject} led {object}." |
| rel_present_at | "The record places {subject} at {object}." |
| rel_witnessed | "The record says {subject} witnessed {object}." |
| rel_absent_from | "The record says {subject} was absent from {object}." |
| part_of / rel_part_of | "The record counts {subject} as part of {object}." |
| took_place_at / rel_occurred_at | "The record places {subject} at {object}." |
| rel_sheltered_at | "The record says {subject} sheltered at {object}." |
| rel_dated | "The source gives the date of {subject} in these words: {text}." |
| rel_preceded / rel_followed | "The record says {subject} came before {object}." / "... came after {object}." |
| rel_fought_alongside / rel_fought_against | "The record places {subject} among those who fought alongside {object} at {event}." / "... fought against {object} at {event}." |
| rel_died_during | "The record says {subject} died during {object}." |
| **story** | "The story {object} names {subject}." Used whenever the object is a story entity. |
| **marker** | `learn.narr.marker`: "Marked in the source: {marker}." Appended to the sentence of a set-apart record. |
| **default** | "The record links {subject} to {object}: {relation}." `{relation}` is the graph's label, from `terms`. |

**Caps.** Discover: 3 eligible sentences, then `learn.narr.more`. Study: 6. Research: up to the same 80 claims as its claim list. At Research, each sentence links to its claim rows (`#c-<local>`) and does not repeat the source line.

### 7.2 Source line

`source_line(claim, depth)` is one function.

**Discover** (`DEPTH_POLICY["discover"]["source"] = "citation_short"`):

- Only an eligible claim gets a source line at Discover, so there is no fallback there.
- Short form: the work (the citation up to the first " ("), plus the first locator matching `(vol\. N, )?pp?\. N[–N]` or `Part N, story N`, cut at ";". Example: "Ibn Hishām, al-Sīra al-Nabawiyya, vol. 1, p. 485". All 156 citations on the page graph (two works) match.
- If a citation does not match, the short form is the citation cut at the first ";" with its parentheses removed, and a test lists it.

**Study and Research:** the full form, with the fallback order citation → `nonReportBasis` → recorded by → `common.not_recorded`.

**AI-generated work** (its creator is a software agent, or its label starts with "50 Stories"; see `display.AI_GENERATED_WORK_LABEL_PREFIXES`):

- The source line gets `learn.source.ai_document` ("{source} (a document generated with AI)") at **every** depth, set-apart lines and `part` reasons included.
- Discover's journey note is `learn.ai_source_note`: "Parts of this journey come from {work}, a document generated with AI."
- Study keeps `learn.ai_note`.

### 7.3 Prompts (ungraded, any status; decision 4; W5)

| Key | Step | Answer |
|---|---|---|
| `learn.prompt.event_who` | event | its people claims |
| `learn.prompt.event_when` | event | rel_dated claims |
| `learn.prompt.event_where` | event | place claims |
| `learn.prompt.person_elsewhere` | person | a link to `<person page>#evidence` (every entity page has it; 155 of 320 person pages have no `#s-events`) |
| `learn.prompt.person_contrary` | person | contrary claims |
| `learn.prompt.story_names` | story | the story's records |

- IDs are `<slug>:<step key>:<prompt>`. Every prompt has `graded: false`.
- A prompt gets `d: "discover"` only if its answer has an eligible claim or is a link. At Discover the answer shows only eligible claims.
- Prompts render as `<details>` with no form controls, under `learn.prompt.note`: "These questions are not marked. Open one to see what the record holds, with its sources."
- Discover shows one prompt. Study and Research show all of them, unless `hold_study`.

### 7.4 Checkpoint (decision 4)

```
checkpoint = {items: [practice question ids whose subject lies inside the steps and anchors],
              graded_from: "accepted",
              feedback: {miss: "learn.check.not_both", see: "learn.check.see_record"}}
```

- `learn.check.not_both` is exactly "The record does not place them at both, as far as reviewed claims go." (test).
- `see_record` links to the person's page `#evidence`.
- The checkpoint is empty today (0 accepted). The free-recall JS is deferred.
- `learn.practice.how_no_choice` is reworded so that it no longer says "wrong".

### 7.5 Next directions (W6)

The candidates are fixed by rule:

- the entity page (`learn.next.page`, `#evidence`);
- the same entity in another journey (`learn.next.also_in`, from the entity index);
- at Discover only, its records at Study (`learn.next.study`, `<study url>#s-<pid>`).

Discover shows at most 3. Consumers' AI may choose among them, and never add one.

### 7.6 View hints (export only)

```
hints = {views: [...], focus: ref | null, light: bool, chosen_by: "rule"}
```

- The vocabulary is closed: sky, stories, time, map, globe, book, chains, lineage.
- Rule: an event with a recorded date gets time. An event whose place has a single located point (`geo.lon` and `geo.lat`, §10) gets map. A story gets stories. A person with kinship claims gets lineage. Otherwise sky.
- On the Prophet's ﷺ step, focus is null and light is true (H4).
- Hints carry no facts, and reader pages do not link into views.

## 8. Depths and G1/G8

Each depth is its own static page, because CSS-hidden text is still public.

**URLs**

- `learn/<slug>/` is the door depth, page 1. Hijrah and Badr open at Study; first-believers opens at Discover.
- `learn/<slug>/<depth>/` holds the other two depths.
- Pages k ≥ 2 live at `.../p<k>/`.
- Every page has `nav.journey-depths`: three links with `aria-current`. Each link points to the page at that depth holding this page's first stop, plus `#s-<pid>`, so the split may differ from one depth to another.
- A split journey also has a pager and a contents list.
- `<article data-depth data-total data-steps>`.

**Discover (public)**

- **Shows:** h1, `lead`, the scale line, and the rule in plain words. For e3 that is the text from §6.7. Graph term labels sit in `.term`. Then each step:
  - name link and kind;
  - the facts line: When and Where as entity fields, Gregorian first, shown as the reader's public entity pages show them (open decision);
  - the computed reasons only (`named`, or `part` with the AI-document label);
  - up to 3 narration `li.sentence` items, each with its `.source`;
  - if the step has no eligible claim, the line `learn.discover.no_work`: "No record behind this stop gives a work and page. Its {n} records are at Study." (with a link);
  - otherwise `learn.narr.more`;
  - 1 prompt;
  - next.
- **Group headings**, at every depth.
- **Set-apart people:** heading, `learn.apart.lead_discover`, then each eligible record as an `li.sentence` (narration plus `learn.narr.marker`) with its `.source` and the AI-document label, or `learn.discover.no_work`.
- `learn.ai_source_note` when AI material is present.
- **Never shown:** status, banners, `story.banner`, coverage state, legend, status counts, accepted share, glosses, notes, basis texts, recorded-by agents, claim IDs, order notes, list state, checkpoint wording, or any rejected or superseded claim.

**Study:** today's page, plus:

- the depth nav and anchors;
- `accepted_share`;
- the E3 list state and sources;
- all prompts and next directions;
- `note` lines (with the AI label);
- claim lists capped at 40 per step, then "{n} more on its page" pointing to `#evidence`.

Glosses move to Research. With `hold_study`, the v1 rendering is kept (§3.7).

**Research:** Study, plus:

- claim IDs (`span.claim-id`, `id="c-<local>"`);
- glosses labelled `learn.gloss.label`;
- recorded-by agents with the software flag;
- 80 claims per step;
- links to the journey's data files;
- `rule_sha`, `content_sha` and the graph fingerprint;
- the excluded list.

**Enforcement, four ways**

1. **Key guard.** `Strings.at("discover")` raises `ReviewLanguageAtDiscover` at build time for any key in `DISCOVER_FORBIDDEN`:
   - prefixes: status., coverage., learn.state., learn.legend., learn.claims., learn.named.summary., learn.accepted_share., learn.order.e3_lists, learn.order.e3_pending, learn.research., learn.gloss., learn.check., learn.prose., learn.teacher.;
   - keys: learn.draft_banner, learn.approved_banner, learn.ai_note, learn.rule.separate_records, story.banner, claim.recorded_by.

   The template cache is keyed by (name, depth), and each template's `[[key]]` list is checked when it loads. A Discover render after a Research render therefore sees the same keys as a fresh one (test).
2. **String tests.** The en text of every key a Discover render uses is checked against `REVIEW_WORDS`:
   - review, reviewed, reviewing, check, checked, checking, proposed, accepted, approved, approval, draft, status, scholar, scholars, board, verified, unverified, authenticity, pending.

   The ar text of exported titles and leads, and of every ar key a Discover render uses, is checked against `AR_REVIEW_STEMS`:
   - مراجع, مسود, حالة, مقترح, مقبول, علماء, تحقق, اعتماد.
3. **HTML test of each Discover page:**
   - no class token `status` (a `\bstatus\b` search in class attributes), no `coverage-*`, no draft banner, no `claim-id`;
   - REVIEW_WORDS absent from **all** text, `.source` included, except inside `a`, `.term` and `.data` spans. Each such exempt span must equal a graph datum (an entity name, a term or qualifier label, or a literal);
   - every `.source` text equals `source_line(c, "discover")` for an eligible claim on that page;
   - on the real graph, no Discover page contains any `nonReportBasis` text or any recorded-by agent label of its journey's claims.
4. **`check_nojs.cjs`,** per `article[data-depth]`:
   - Discover: no `.status`, and every `li.sentence` (narration and set-apart) has a `.source`;
   - Study and Research: "Status:" in every `li.claim`, and the draft banner.

**`PUBLIC_MODE`.** `public_mode()` reads `display.PUBLIC_MODE` once reader-r3 adds it, else `$MARSAD_PUBLIC_MODE`, else `"all"`.

- `accepted` stops `build_learn` with a RuleError until `resolve(accepted_only=True)` exists (fail-closed).
- Round 4 Q1 changes one entry of `DEPTH_POLICY`.

**The index** `learn/` is depth-neutral (Discover-level):

- Removed: `learn.index.draft_note`, `how_status`, `how_doors`.
- Added: `learn.index.how_depths`.
- Reworded: `learn.index.lead`, `learn.index.practice_lead`.
- Cards keep the title, lead, step count, the three depth links and `data-steps`.
- Practice pages are unchanged.

## 9. Stop keys, URLs, versions, view links

**Stop key** = the entity pid. It is used as:

- the reader anchor `id="s-<pid>"`. `li id="step-N"` stays, numbered across pages, and so does `data-step="<pid>"`;
- the export `key`;
- the learn.js progress unit. Its key `al-marsad.learn.progress.v1` is unchanged, so E1 progress survives every depth and page.

Page 1 of a split journey carries `nav.journey-contents`, so `learn/<slug>/#s-<pid>` and every cross-page link resolve with JS off.

The export gives each stop its URL per depth (`stops[].urls`) and its data part. No consumer computes paths.

**Versions**

- `graph = {file, fingerprint, triples}`. The `fingerprint` uses exactly `obsdata.fingerprint()`'s algorithm: non-blank-node triples, sha256, 12 hex. It is kept for equality with the Atlas (page graph `808a048b0c16`). It cannot see blank-node data: participation records, roles and relative anchors.
- **`content_sha`** per journey = `sha12` of the canonical unsplit resolved journey (stops, steps, claims, passages, entities, terms, order data), without urls, part lists, `graph` and itself. It changes when a participation or its role changes, even when the fingerprint does not (fixture test). `build_learn` prints it, and it goes in link tokens.

**Proposed to consumers**

- **Atlas:** the token `tour.j_<slug>.s-<pid>` plus `c=<content_sha>`, checked on restore.
- **Expeditions:** this is a change on their side, not a fit. Their router accepts only `^x-([a-z]+)(?:-(\d+))?$`: letters-only slugs and numeric steps. A learn journey needs a new route such as `#j-<slug>~<pid>`, and channel messages `{journey, key}`, kept apart from the expedition slugs.

G5 redirects for merged pids come with slice 11b. A `was` alias list per stop is reserved.

## 10. Export contract: marsad-journey v1

`build_learn` writes it to `site/dist/learn/data/` (rebuilt, never committed). For any graph:

```
.venv/bin/python learn/journey_export.py --graph build/graph-all.ttl --out DIR [--part-budget N] [--facade] [--lock]
```

In process: `journey_export.resolve(site, journey, strings) -> dict` (unsplit) and `resolve_all(site, folder=None) -> dict`.

**JSON conventions**

- Every file is written as `canonical()` plus a final newline. No timestamps.
- Consumers ignore unknown keys. An added key keeps version 1. A rename or removal means version 2, with version 1 still written beside it for one release.

**References**

| Kind | Form | Note |
|---|---|---|
| Entity | `"<kind>/<pid>"` | |
| Claim | `"assertion/<local name>"` | Equals the Atlas's ObsData claim `id` and Expeditions' `ast:<id>`. |
| Participation | `"participation/<event pid>/<person pid>/<role local or none>"` | |
| Plain link | `"link/<pk>/<s pid>/<o pid>"` | |
| Passage | `"passage/<local>"` | |
| Term | `"pk:<key>"`, `"q:<qualifier local>"`, `"role:<role local>"` | |

**`index.json`**

```
{"format": "marsad-journeys", "version": 1,
 "graph": {"file", "fingerprint", "triples"}, "public_mode": "all",
 "depths": ["discover", "study", "research"],
 "depth_policy": {"discover": {"status": false, "draft_note": false, "coverage_state": false, "accepted_share": false,
                               "source": "citation_short", "claims": "discover_flag_only", "basis": false, "recorded_by": false,
                               "notes": false, "gloss": false, "claim_ids": false, "order_notes": false, "rejected": false,
                               "ai_document_label": true, "narration": 3, "prompts": 1, "claim_list": 0},
                  "study": {"status": true, "draft_note": true, "coverage_state": true, "accepted_share": true, "source": "full",
                            "claims": "all", "basis": true, "recorded_by": true, "notes": true, "gloss": false,
                            "claim_ids": false, "order_notes": true, "rejected": true, "narration": 6, "prompts": null, "claim_list": 40},
                  "research": {... "gloss": true, "claim_ids": true, "narration": 80, "claim_list": 80}},
 "background_rule": {"marker": null, "after_source", "after_bound", "before": "0570-01-01", "not_placed": "..."},
 "lists": {"file", "state", "applied", "sha", "sources_complete"},
 "sorts": {"default": "learn.sort.default", "az": "learn.sort.az", "links": "learn.sort.links",
           "accepted_islam": {"t": "learn.sort.accepted_islam", "rule": {"kinds": ["event"], "phrase": ["acceptance", "of", "islam"]}, "needs": "citation"}},
 "view_vocabulary": [...], "strings": "strings.json", "pages": "pages.json",
 "entities": {"<pid>": [["<slug>", "<step key>", <n>]]},
 "journeys": [{"slug", "kind", "state", "stale_approval", "rule_sha", "content_sha", "listed": true,
               "title": {"key", "en", "ar"}, "lead": {...}, "lead_study": {...} | null,
               "door", "type", "order", "order_applied": "e3|e3_pending|<v1 order>", "groups", "steps", "apart", "excluded",
               "accepted_share": {"accepted", "of", "no_status"}, "story_mode": {"open", "stale"},
               "file": "journeys/<slug>/journey.json", "urls": {depth: [page urls]}}]}
```

**`journeys/<slug>/journey.json`** (the head)

```
{"format": "marsad-journey", "version": 1, slug, kind, state, stale_approval, rule_sha, content_sha, approved_by, listed,
 title, lead, lead_study, door, "select": <verbatim>, order, order_applied,
 "lists": {file, state, applied, sha, sources: [{key, text|null}]} | null,
 graph, accepted_share, story_mode: {open, approved_by, stale}, hold_study,
 order_conflict, mixes_stories_and_events, universe, part_labels,
 "groups": [{"key": "main"|"against", "t": key|null, "lead": key|null, "from": n, "to": n}],
 "anchors": [refs], "excluded": [{"ref", "reason"}], "checkpoint": {...},
 "stops": [{"key", "ref", "n", "group", "part", "urls": {depth: "<page url>#s-<key>"},
            "sort": {"default", "az", "links", "accepted_islam": n|null}}],
 "set_apart": [{"key", "ref", "part", "because": [{"qualifier", "claims": [ids]}]}],
 "parts": ["part-1.json", ...], "research": ["research-1.json", ...],
 "reader": {"url": "learn/<slug>/", "anchor": "s-{key}"}}
```

**`part-<k>.json`**

- At most `PART_BUDGET` = 150,000 bytes. Cut greedily in stop order, deterministically. Self-contained.
- A part holds at least one stop. A single stop over budget fails the build with a RuleError naming it (fail-closed; fixture test).

```
{"format": "marsad-journey-part", "version": 1, slug, part, "graph": {"fingerprint"}, "content_sha",
 "steps": [Step], "claims": {id: Claim}, "passages": {ref: Passage}, "entities": {ref: Entity}, "terms": {ref: {"en", "ar"?}}}
```

**Step**

```
{"key", "ref", "n", "group",
 "reasons": [{"kind", "other"?, "word"?, "label"?, "claims": [ids]}], "links": [same],
 "order": {"note": "part|recorded|unrecorded", "ref"},              (absent on step 1)
 "records": [ids], "contrary": [ids],
 "side": [{"pk", "at": ref, "with": ref, "claims": [ids]}],         (claims whose subject is this stop's person only)
 "side_conflict"?: true,
 "claims": {"ids": [cap order], "total"},                           (events and stories steps)
 "narration": [{"t", "c": [ids], "d"}],
 "prompts": [{"id", "t", "slots", "answer": {"claims": [ids]} | {"href"}, "graded": false, "d"}],
 "next": [{"t", "ref" | "journey", "href", "d"}],
 "hints": {"views", "focus", "light", "chosen_by": "rule"},
 "e3"?: {"tier", "pos", "links", "accepted_islam": [{"event", "earliest", "latest", "precision", "claims"}]}}
```

Because `side` holds only claims whose subject is the stop's person, the Prophet's ﷺ step stays small. On the joined graph he is the object of 445 side claims and the subject of none. Copying every claim that touches him would make a single part of 266 KB.

**Claim**

```
{"kind": "assertion|participation|link",
 "pk": <assertion: predicate local name with "rel_"; participation: "took_part"; link: "took_place_at" | "part_of">,
 "s": ref, "o": ref | "text": {"value", "lang"},
 "status": "proposed|under_review|accepted|rejected|superseded" | null,   (exact, never folded)
 "discover": bool,
 "passage"?, "basis"?, "recorded_by"?: [{"label", "software"}], "note"?: {"text", "ai_document"},
 "ai_document"?: true, "software"?: true,
 "role"?: <participation role local; participations only>, "qualifiers"?: [qualifier locals], "voice"?, "at_event"?: ref}
```

ObsData's `pk` is this `pk` with "rel_" removed. `FORMAT.md` gives the mapping. Labels for pk, qualifiers and roles are in `terms`, taken from `skos:prefLabel` or `rdfs:label`.

**Passage**

```
{"cite": <full>, "short": <Discover form>, "work": <work label>, "ai_document": bool}
```

**Entity**

```
{"kind", "name", "scholarly", "prophet"?, "links"?: <count>, "coverage_state"?: <key, Study and above>,
 "dates"?: [{native, calendar, earliest, latest, precision, basis, "text": {"en", "ar"}}],
 "places"?: [refs], "number"?, "part_label"?,
 "geo"?: {"lon", "lat", "confidence", "basis", "recorded_by"} | {"many": n} | {"unlocated": true, "basis"}}
```

- `geo` follows `obsdata._node_place`: the `geometryState` → `geo:asWKT` point (WKT order: lon, then lat), with `locationConfidence` and `geometryBasis` keys and the place's recorded-by agents. Several different points give `many`, and none is chosen. `lc_unlocated` gives `unlocated`. A place with no geometry state has no `geo`.
- This gives Expeditions a point with its provenance, so it can draw without loading the graph. Only 9 places on the page graph have a geometry state.
- `text` comes from `display.format_extent`: Gregorian first, digits 0–9, Arabic Gregorian month names.

**`research-<k>.json`**

```
{"format": "marsad-journey-research", "version": 1, slug, part, "glosses": {id: text}, "trace": {key: {"hop"}}}
```

**`strings.json`** `{"en": {...}, "ar": {...}}` holds every i18n key the export references. Together with `terms`, the data reads without the app.

**`pages.json`**

```
{"format": "marsad-learn-pages", "version": 1, "pages": [{"path", "kind", "journey"?, "depth", "page", "pages", "door"?, "first", "last"}]}
```

`learn/FORMAT.md` documents this contract, with no entity IDs.

## 11. The v1 facade and the facade lock

**Unchanged for `atlas/build.py:124-153`**

- `journeys.load_specs`, `build(site, spec, links=None)`, `build_all`, `RuleError`.
- `Journey.steps`, `set_apart`, `anchors`.
- `Step.iri`, `reasons`, `records`, `contrary`.
- `Reason.kind` (the v1 kinds only), `other`, `word`, `label`.
- `Claim.subject`, `object`, `predicate`, `predicate_is_key`.
- `spec["slug"]`, `["title"]`, `["lead"]`, `["select"]["type"]`, `["status"]` (computed).

**Added, with defaults only**

- `spec["story_mode"]` (computed).
- `Step.e3`, `Step.side`, `Step.group`.
- `Journey.excluded`, `Journey.groups`.
- The keyword-only `lists_root`.
- `FACADE_VERSION = 2`.
- `learn/i18n/en.json` stays a flat key → text object (the Atlas reads it as one).

**Output that changes on purpose:** see §3.8.

**Lock.** `journey_export.atlas_projection(journey, strings)` reproduces the record that `load_journeys` builds, with IRIs in place of node indices, plus `story_mode.open`. `learn/facade.lock` holds `{"facade_version": 2, "inputs": sha12, "engine": sha12}`:

- **inputs:** the facade-visible spec fields, their en title and lead, the computed `story_mode.open`, and the list content.
- **engine:** the projection of fixed fixture specs on `fixtures.facade_graph()`: events; people e3 with a reviewed fixture list; people with side groups; stories.

`test_facade_lock_is_current` fails with: "The Atlas reads this. Rebuild atlas/index.html (atlas/build.py on build/graph-all.ttl) and run learn/journey_export.py --lock."

## 12. Arabic

In this slice:

- `learn/i18n/ar.json` holds only `journey.<x>.title / lead / lead_study`.
  - Titles and leads are copied from the Atlas's `atlas/i18n/ar.json` (`tour.j_<slug>.*`). Its leads are already Discover-safe.
  - `lead_study` is an interface draft awaiting L3 review.
  - A parity test checks keys and placeholders, and the AR_REVIEW_STEMS test covers title and lead.
- The export carries title and lead as `{key, en, ar}`.
- Dates carry `text.ar`: Gregorian first, digits 0–9 (a test rejects U+0660–0669 and U+06F0–06F9), Gregorian month names.
- `rel_dated` literals keep their `lang`.
- `terms` carries `ar` labels where the graph has them (`relations.ttl` has none today).

Deferred: `ar/learn/` twins, hreflang, LRI/PDI isolation, plural categories, Arabic narration templates, `named.words_ar`.

## 13. Scale and budget

**Measured**

| | Page graph | Joined graph |
|---|---|---|
| Site load | 1.3–1.6 s | 32–43 s |
| Fingerprint | 0.1 s | 3–4.5 s |
| v1 Study HTML: first-believers / Hijrah / Badr | 48,744 / 62,631 / 141,690 B | 48,744 / 86,831 / about 673,598 B |
| Badr step HTML at Research weight (skeptic estimates) | 215–292 KB | 1.05–1.29 MB |
| Split export prototype (Badr) | one part | about 28 KB head + parts of ≤102 KB (side claims of the stop's own subject only) |

**Reader pages**

- `STEP_HTML_BUDGET = 220,000` bytes of step HTML per page. Assets are 23,968 B. Against `check_budget`'s 300,000, that leaves room.
- **The split is computed per depth, at that depth's own weight**: greedy in stop order and deterministic. The contents list counts against page 1. `<ol start>` continues the numbering.
- The stops and their order are the same at every depth. Only the page cut points differ. Depth links and `stops[].urls` find the right page.
- Caps keep any single step far below a page: Discover 3 sentences and 1 prompt; Study 40 claims; Research 80.

**Expected** (printed by the build and the LEARN_JOINED smoke test; never asserted as constants):

- Page graph: one page per depth for Hijrah and first-believers. Badr gets one page at Discover and Study, and one or two at Research.
- Joined graph: Badr about 3 pages at Discover, 4–5 at Study, 5–7 at Research.

**Export:** parts are cut at ≤150,000 B, each with its own tables.

Slice 11b needs no learn code change. `LEARN_JOINED=1` is the gate.

## 14. Determinism and what a change touches

- Every collection is sorted, with ties ending in pid or claim ID. `Site.entities` is never iterated. Synthetic IDs are built from pids and role locals. `canonical()` is used everywhere.
- `test_build_is_deterministic_across_processes` runs twice under PYTHONHASHSEED 1 and 2 (dircmp):
  - with the default budgets;
  - with `--step-budget 30000 --part-budget 20000`, so that multi-page, cross-page-link, contents and multi-part output are compared byte for byte.
- `build_learn` prints:
  - the summary lines;
  - `rule_sha` and `content_sha` per journey;
  - page counts per depth;
  - "export: learn/data, 3 journeys, N files, digest <sha12>";
  - "atlas facade (page graph) <sha12>: if this changed, rebuild atlas/index.html".

## 15. Decision-6 proposals (for the board; never written into the graph here)

`learn/proposals/hijrah-parts.json` (`marsad-claim-proposals` v1, status proposed). Each subject and object is a `named` rule that must resolve to exactly one event on the page graph (test). Each proposal carries a basis that states the open question.

1. "Arrival in Madinah and early community-building" `rel_part_of` "The Hijra: departure from Makkah, via Ghar Thawr".
2. "The Second Pledge of al-Aqaba" `rel_part_of` the same.
3. "The Second Pledge of al-Aqaba" `rel_preceded` "Departure from Makkah".
4. "Arrival in Madinah..." `rel_followed` "Arrival at Quba'".
5. "The council of Quraysh at Dar an-Nadwa before the Hijra" `rel_preceded` "The Hijra: departure...".

Simulated effects (scratch graph, unchanged engine):

- **1–2 alone** take Hijrah from 7 to 9 steps, but list Arrival in Madinah (step 3) **before** Departure from Makkah (step 5).
- **1–4** put the route events in order: beginning → the Hijra → Second Pledge → Departure → Thawr → Qubāʾ → Arrival in Madinah. The story "The Hijrah and the Cave of Thawr" and the Dār al-Nadwa council stay at steps 8 and 9 under "the record gives no order".
- **5** is needed to move the council before the departure.

So the board sees 1–5 together for the order question. On the joined graph, the six Hijra events have no part-of links between them, so the board must also choose the whole, or the merges.

## 16. From the three candidate designs (round 1)

The base is the additive design. These grafts were adopted:

- approvals bound to `rule_sha`;
- facade.lock;
- Discover-safe facade leads;
- the `Strings.at` guard;
- one source-line function;
- glosses at Research only;
- `pages.json`;
- a fail-closed `public_mode()`;
- a recorded-death F11 signal with the not-placed class;
- attributive narration with the story template;
- en/ar titles and leads;
- `not_words` and `phrase`;
- ungraded prompts, next candidates and hints;
- `hold_study`;
- rule-resolved proposals;
- pid stop keys;
- byte-split parts;
- claim caps;
- the entity index;
- the prose validator.

One graft was refused on evidence: lineage-only people as background (§5).

## 17. Revision 2: what the skeptics found and what changed

Each item was checked against f859b53 and both graphs with scratch probes (not kept in the repository).

1. **The Discover source fallback put review language and software agents on public pages** (blocking). Confirmed: `render_learn.py:122-136` falls back to basis and then agents; participations and links have no citation; 2 Hijrah steps and 1 Badr step have no cited claim. **Fixed:** §7.0 Discover eligibility, the citation-only short form (§7.2), the absence line, and source text scanned by the tests (§8.3).
2. **E3 coverage with the tiers off put opponents among the top Companions on the joined graph** (blocking). Confirmed: Abu Jahl is 9th, and 79 people are recorded only as fighting against him at the four anchors. **Fixed:** the A–Z fallback until the list is reviewed (§6.3), side groups at the event (§6.4), and side built only from the stop's own claims.
3. **Set-apart lines at Discover had no source.** Fixed: they are `li.sentence` items with a source and the AI-document label.
4. **`role` mixed AI glosses into narration and parts.** Confirmed at `model.py:289`. Fixed: the field table in §7.0, and the no-gloss-in-parts test.
5. **"Nothing records an order of accepting Islam" was false.** Fixed: the `accepted_islam` sort from cited records (§6.5).
6. **The export had no place location.** Fixed: `Entity.geo`.
7. **Badr exceeds the budget at Research weight if the split is shared.** Fixed: a split per depth, lighter Research narration, and counts derived from `pages.json`.
8. **`#s-events` is missing on 155 person pages.** Fixed: links go to `#evidence`.
9. **Side was symmetric.** Fixed: claims are taken from the subject side only (`with` gives the other party).
10. **The fingerprint cannot see blank nodes.** Confirmed in `obsdata.py:550-555`. Fixed: `content_sha`.
11. **Exact corpus numbers in CI tests.** Fixed: real-graph tests state invariants; exact numbers stay on fixtures; E1 uses the golden hash gated on `content_sha`.
12. **Minor findings, all adopted:**
    - F11 (b) by token sequence;
    - §15 wording;
    - the `story_mode` facade copy;
    - list sentinels, RuleError and the path base;
    - `terms`;
    - `links` / `coverage_state` naming;
    - per-slug data folders;
    - the template cache keyed by depth;
    - the class-token test;
    - pinned `canonical()`;
    - date regex then `fromisoformat`;
    - Arabic stems;
    - NODE_PATH in the browser test;
    - small-budget determinism;
    - the E3 Discover sources key;
    - the coverage wording;
    - no rejected or superseded claims at Discover;
    - the rāshidūn source not copied;
    - the Expeditions route stated as their change.

## 18. Verified facts (scratch probes, f859b53)

**Page graph:** 320 people, 65 events, 47 places, 50 stories, 953 claims, 0 accepted.

- **Journeys:** first-believers 13, Hijrah 7, Badr 92 (+2 apart, 3 anchors).
- **F11:**
  - The 7 events wholly after 632 and the 7 coarse year-632 events are as listed in round 1.
  - "Death of the Prophet ﷺ" folds to `death of the prophet ﷺ`, so it is matched by its tokens.
- **Citations:** 156 citations, all in the short-form pattern.
- **Acceptance of Islam:** 49 people have a cited record; 3 of them are at dated events.

**Joined graph:**

- **Journeys:** Hijrah 9; Badr 439 (+1) with 9 anchors, or 438 (+1) with 4 anchors under not_words.
- **Side claims at the 4 anchors:** 314 alongside and 79 against. All are cited and proposed, all have the Prophet ﷺ as object, and none has him as subject.
- **Deaths:** 17 of the against-only people are recorded as dying during the anchors.

**Both graphs:**

- The list names match 14 of 14 uniquely, also with `EXPAND_B_TO_IBN`.
- Every person page has `#evidence`.

## 19. Risks

1. **Atlas island coupling.** Whichever of learn-v2 and PR #31 merges second rebuilds `atlas/index.html` once. `facade.lock` shows when.
2. **The E1 page during the class month.** `hold_study` and the golden hash protect it. Merging after the class session is safer still.
3. **Provisional F11.** It misses undated background material until 11b's marker, and it excludes two pre-death events recorded only to the year 632.
4. **Narration exposes modelling errors as plain statements.** The attributive wording and the source lines keep this honest. Fixes go through review.
5. **E3 tiers stay off until the board approves the list file**, and the rāshidūn need a source first.
6. **Discover becomes thin where the record has no work and page.** Two Hijrah stops show only their name, date and the absence line. That is honest, but sparse.
7. **The export is a public contract.** Versioning discipline is needed.
8. **Test churn.** check_nojs, the page lists and `family_keys` change on purpose.
9. **CI does not scan the learn-v2 handover notes on docs-only PRs.** `paths-ignore` `docs/handover/[a-r]*.md` matches them. The ID scan still runs on every PR that touches learn/.
10. **PR size.** The cut line: prompts, next, hints, geo and the other sorts can move to learn-v2b without a format change, because the keys are reserved.
