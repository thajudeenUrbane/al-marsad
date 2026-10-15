# The ask DSL

A typed query language for asking the graph questions (docs/07 §4). A plain question is turned into one of these queries by fixed rules (`ask/translate.py`); the query is checked against a closed table of operations, run over the graph, and shown back to the visitor in plain words. Nothing here is generated database query text, and no model is called at run time.

Code: `ask/dsl.py` (parser, validator, executor, plain wording), `ask/translate.py` (question → query, refusals), `ask/present.py` (answer → HTML), `ask/static/ask.js` (the same three, ported for the browser; `ask/tests/test_parity.py` keeps them identical).

```
participants(event "Battle of Badr")
both(people(at: place "Badr"), people(at: place "Uḥud"))
events(at: place "al-Madīna", from: 1 AH, to: 5 AH)
path(person "Bilāl b. Rabāḥ", person "ʿĀʾisha bint Abī Bakr")
```

## Grammar

```
query    = call
call     = name "(" [ arg { "," arg } ] ")"
arg      = name ":" value          keyword argument (after all unnamed ones)
         | value
value    = call | ref | year | number | word
ref      = kind string             an entry named by a recorded name
         | kind "#" id             an entry named by its ID payload
kind     = "person" | "group" | "place" | "event" | "story"
year     = number ("AH" | "CE")    e.g. 5 AH, 627 CE
string   = '"' ... '"'             \" and \\ escape
```

Names are case-insensitive; IDs are not. A query is at most 2,000 characters, 12 operations and 6 levels deep.

**Names.** `person "Abū Bakr al-Ṣiddīq"` matches an entry whose recorded name (any label, or a recorded kunya or laqab) has the same name key as the string (see *Spelling* below), within that kind. No match or more than one match is an error, never a guess. When the translator writes a query it quotes the entry's primary label if that label names it alone, and uses `kind #id` otherwise (two places are both labelled "Route waypoint (unidentified)").

## Operations

Each list-returning operation gives rows; each row is an entry plus the numbers of the claims that put it there. A claim is an assertion (it has a review status: proposed, under review, accepted, …), a participation (who took part in an event, in what role; no status of its own), or a link (where an event took place, what it is part of; no status of its own). Claims rejected or replaced by scholars are never used as support; a note counts them.

| Operation | Takes | Returns | Rows and the claims behind them |
|---|---|---|---|
| `participants(T, as: leader)` | T: an event or story, or an `events(...)` query | people and groups | everyone with a participation or an assertion (other than a recorded absence) whose object is T. `as: leader` keeps the "led" assertions and the "leader" role. Recorded absences are listed apart. |
| `people(at: P, from:, to:)` | P: a place | people and groups | `participants` of the events recorded at P, plus people named in a claim about P itself (died at, migrated to, sheltered at, …). With a period, only dated events count. |
| `absent(T)` | as `participants` | people | the "absent from" assertions on T. |
| `events(at: P, involving: X, from: Y, to: Y)` | at least one filter | events | events whose recorded place is P (a link or an "occurred at" assertion), in which X has a claim, dated in the period. |
| `stories(involving: X)` | a person or group | stories | the 50 Stories narratives whose list names X. |
| `relatives(P, tie: …)` | a person; tie: any, parent, father, mother, child, spouse, sibling | people | the kinship assertions touching P, shown as recorded (no inverse is invented). |
| `connected(X, via: …)` | a person or group; via: any, ties, events | people and groups | ties: any assertion between X and another person or group. events: people recorded in the same (non-story) event as X, with both claims. |
| `between(X, Y)` | a person or group; an event, story or place | the claims | every claim joining X and Y; for a place, also the events recorded there. A recorded absence is shown as it stands: the answer is the record, not yes or no. |
| `path(A, B, max: 1–4)` | two entries | a chain | the shortest chain of recorded claims from A to B (breadth-first, claims in a fixed order), at most `max` steps (default 3). |
| `when(E)` | an event, story or person | dates | the recorded date of an event, or the recorded death of a person, worded by the site's date rules. Dates are fields, not claims. |
| `where(E)` | an event or story | places | the recorded place of E. |
| `about(X)` | any entry | a summary | how many claims touch X, by kind, with their statuses, and a link to its page. |
| `both(A, B)`, `either(A, B)`, `except(A, B)` | two lists of the same kind | that kind | intersection, union, difference; claims from both sides are kept. `except` notes that absence from the second list only means no such claim is recorded. |
| `count(S)` | a list | a number and the list | the number of rows, with the note "this counts records in the graph, not people in history". |
| `reviewed(S)` | a list | the same | keeps only claims accepted by scholars (the confidence floor of docs/07 §2). Today nothing is accepted, so this returns nothing, and says why. |

A value of the wrong type, an unknown operation or keyword, a missing filter, a start year after the end year, a year out of range (1–1500 AH, 500–2100 CE) or a path between an entry and itself stops the query before it runs, with a message (`error.*` in `ask/i18n/en.json`).

## Time

Only query bounds are converted, never an event's date. An AH year becomes a span of Julian-calendar days by the tabular Islamic calendar (civil epoch, 1 Muharram 1 AH = 16 July 622), the convention of the graph's own stored conversions (a test checks every converted day in the graph falls in the year these bounds give). An event is *within* the period when its recorded bounds are inside it, and *overlaps* when they cross it; overlapping rows are marked "recorded date too broad to tell", and undated events are left out with a count. A year without AH or CE is read as AH up to 200 (and the answer says so), as CE from 500.

## Plain words

Every query is shown back as a sentence built from templates (`plain.*` keys): `both(people(at: place "Badr"), people(at: place "Uḥud"))` reads "those in both lists: people and groups recorded at Badr; and people and groups recorded at Uhud". The query itself is shown under the answer and can be edited and run again: a question that starts with an operation name and a bracket is run as a query.

## The answer object

`translate.answer(question)` returns a dict with `q`, `version` (a hash of the index) and `outcome`:

- `answer`: `dsl` (canonical text), `plain`, `result` (rows with claim numbers, notes, and for some operations `absent` and `searched`), `refs` (entries in the query), `notes` (from the translator) and `alts` (other entries with a similar name, each with the query it would run).
- `refusal` with `refusal` (the class); `unsupported` with `reason`; `ambiguous` with `mention` and `options` (each entry with the query it would run); `not_found` with `mention`, `kinds` and similar `others`; `invalid` with `dsl` and `error`; `empty`; `too_long`.

Same question and same graph give the same object, in Python and in the browser.

## Refusals

Classified before any translation or lookup, by patterns in `rules.json` ("refusals"), in this order: fabrication (writing hadith, reports, stories), depiction (pictures of, or how someone looked), grading (is this report authentic), interpretation (meaning or lessons of scripture), ruling (fatwa, halal/haram, "can I…" with a fiqh verb), judgement (who was right, is someone in paradise or a hypocrite), ranking (greatest, best, most important or most connected, better than, top ten, who had the most…), speculation (probably, might have, guess). Each refusal gives its reason and what the tool can do instead (`refusal.<class>.reason` / `.offer`). The golden set tests every class, and questions that must not be refused (a historical event called the Ridda, "Can you tell me…", "Draw a map of the Hijra route").

## Question shapes

`rules.json` "shapes", first match wins. Who was at X (a place: `people`; an event or story: `participants`); at both X and Y (with or without "both"); at X but not Y; how many at X; who was absent from X; who led X; who is in the story X; was / did / is it true that X was at Y (`between`); children, sons, daughters, father, mother, parents, wives, husbands, siblings, relatives of X; who met / is connected to both X and Y; how is X connected to Y; who is connected to X; everyone connected to X during Y; what happened at P (optionally involving X); events involving X; what happened in a period; which stories mention X; when did X die; when / where was X; tell me about X; a bare name. A period ("between 1 and 5 AH", "in 8 AH") can be added to place and event questions, and "reviewed claims only" to list questions.

## Spelling

Names are matched on the site's own search form, `names.normalise` from `site/names.py` (slice 2b), imported: marks and apostrophes dropped, lower case, Arabic letter forms unified, the article (al-, as-, ash- …, Arabic al-) left out, b./bin/ibn and abi/aba/abu made one. Ask first takes off "(pbuh)"-style honorifics and a possessive 's, then leaves out "the" and joins Abd Allah / Abdallah / Abdullah. Close spellings meet through the site's sound key (`names.skeleton_words`) or one letter's difference. A mention scores against each recorded name: 6 the same words; 5 the same words spelled differently (one letter off, or the same sound key of three consonants or more: Hudaybiyah and al-Ḥudaybiyya, Usman and Uthman); 4 the start of the name; 3 the start, spelled differently (Mecca and Makkah); 2 a run of words inside the name, or equal without spaces (abubakr); 1 all its words somewhere in the name. The best score wins; a tie between kinds goes to the kind the question expects (a place or event before a story); a tie within a kind is put back to the visitor as a choice, listing every entry of that kind within one level of the best (Fatima: two Fāṭimas and a Fatimah).

In the browser, `ask.js` repeats `names.normalise` and `names.skeleton_words` step for step, with the site's own tables (`names.RULES`, written into the index), as `site/static/search.js` does; the parity test compares the keys of every name in the graph.

## The examples in docs/05 §3 and docs/07

| Example | Query |
|---|---|
| People who met both Abū Bakr and ʿUmar | `both(connected(person "Abū Bakr al-Ṣiddīq"), connected(person "ʿUmar b. al-Khaṭṭāb"))`. The graph records no meetings, so "met" is read as a recorded tie or a shared recorded event; the sentence and a note say so. |
| Events in Madinah between 1 and 5 AH involving members of the Anṣār | `events(at: place "al-Madīna", involving: …, from: 1 AH, to: 5 AH)`. The graph has no Anṣār group, so the answer reports that name as not found rather than dropping it. |
| Everyone connected to Abū Bakr during the Hijrah | `both(connected(person "Abū Bakr al-Ṣiddīq"), participants(event "The Hijra: departure from Makkah, via Ghar Thawr"))` |
| Scholars connected to this teacher within three generations | Not yet: the graph holds 5 transmission links. `path(A, B, max: 3)` covers a chain between two people; a `within(X, steps)` traversal is the next operation to add once transmission data exists. |
| Narrators active in both Kufa and Basra | Not yet: neither city is in the graph and only one place affiliation is recorded. Once they are, `both(people(at: place "Kufa"), people(at: place "Basra"))`, with affiliations read into `people`. |

## A later, model-backed translator

`translate.Translator` is the interface; `translate.ModelTranslator` is a placeholder that raises `NotImplementedError` and is never registered (docs/13 D4). A translator receives the folded question only after the refusal classifier has passed it, returns query text (never prose) or `None`, and its query is parsed and validated like any other; an invalid one falls through to the next translator. It must be measured on `ask/golden/questions.jsonl` before use, and its name and version recorded with the question, the query and the graph version.
