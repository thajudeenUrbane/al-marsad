# Slice 1c handover — 50 Stories in the ontology, one unified build

Spec: docs/handover/slice-1c-brief.md. Nothing here is verified history. No status was upgraded (every story link is `proposed` / `stub`), no Arabic name or date was invented.

## What was added
- `ontology/tools/stories50_to_ttl.py` -> `ontology/corpus/stories-50.ttl` (generated; `--check` tells if stale). Imports the parser from stories-50/build.py; resolves every person/group through identity.csv `stories50_names` only. All 171 people and 12 groups had a row: nothing minted for people/groups, no new needs-review rows.
- `ontology/build_graph.py`: loads marsad + relations + every .ttl in corpus/ and examples/, applies the merge decisions below, writes `build/graph.ttl` (gitignored), prints instances per class, runs SHACL, exits 1 on any Violation. `--query FILE` runs a SPARQL file on the result.
- `ontology/queries/abu_bakr.rq` (the proof, below); `ontology/corpus/stories-50-ids.csv` (key -> minted ID ledger, so re-running never renames an IRI).
- identity.csv: +50 `event` rows (story events, confidence `exact` as new IDs, note says not merged with any other event). identity_audit.py now also checks stories-50.ttl. docs/02 §5.2.1 updated (grp: in use, wrk: added).

## Modelling (marsad.ttl supports these; no new class or property)
- Story = `mrs:Event` (the occurrence narrated). Chosen over `mrs:Report` (needs chain, ascription, sourceDate: would force invented values). Not identified with Badr/Uhud/Hijra events etc.: that is a scholar's call.
- Prose = `mrs:Passage` (crm:E33) per story, verbatim in `crm:P190_has_symbolic_content`, in a Passage per Part, in `mrs:Work` (the doc); `mrs:Witness` = the rev 7 export of 10 Oct 2026; Work/Witness/agent are stub, "unverified secondary compilation", no adjudicator.
- Order and Part number are `skos:notation` integers (marsad.ttl has no ordinal property: proposal for a human below). Part link is `dct:isPartOf`.
- Each list entry = one `mrs:Assertion`, predicate `rel_participated_in` (the doc's intro says the lists name who "took part"), `nonReportBasis`, role text verbatim in `rdfs:comment`, `prov:wasDerivedFrom` the story passage. "(accepted Islam later)" = `mrs:qualifier mrsv:q_accepted_islam_later` (24 links; wording such as "by most accounts" stays in the role text). Groups use `grp:` + `mrs:Group`.
- A Person node is declared in stories-50.ttl only for the 121 people no other file declares (label from identity.csv, doc name as nameForm, scheme text says "as written, no scheme").

## Counts (build/graph.ttl)
12,604 triples; 184 Person (= identity.csv), 12 Group, 22 Place, 103 Event (96 named + 7 blank), 547 Assertion (380 from stories), 55 Passage, 143 Participation. 380 story assertions = 368 person + 12 group; 2 people are listed twice in one story (al-Zubayr, story 28; Usamah, story 50), kept as 2 links each (different roles).

## 1b leftovers: duplicate definitions
- Labels: only 3 entities carry two labels (al-Madina, Ghar Thawr, Arrival at Quba). All are kept; no altLabel/prefLabel (the ontology uses prefLabel for vocabulary only; PersonShape forbids auto-picking a display name). Display name = identity.csv `preferred_name_en`. SHACL is unaffected by labels.
- A real conflict surfaced: Ghar Thawr `placeType` is `cave` (thawr.ttl) and `route node` (seed-incidents.ttl); PlaceShape wants exactly one, so the union failed. Each source file must still validate alone, so neither was edited. `MERGE_DECISIONS` in build_graph.py leaves `route node` out of the unified graph (provisional; printed every run; a stale entry is an error). Maintainer to confirm.

## Proof: Abu Bakr (`per:8sT3wY6xZc2mQ7vR9nK4pP1`), one IRI, four sources
Query (full file with comments: ontology/queries/abu_bakr.rq): select `?source ?kind COUNT(DISTINCT ?node)` where `?node` is an Assertion with Abu Bakr as subject or object (kinship if the predicate's relationClass is kinship, else event/person by the other end) or an event with a `mrs:hasParticipation [mrs:participant per:8sT3…pP1]`, `?source` = label of `?node`'s `mrs:createdBy` agent, grouped by source and kind.
Result: stories-50 conversion: 16 event/story assertions. generation-1: 3 kinship ties, 1 person tie, 1 event assertion, 6 participations. seed-incidents: 9 event assertions, 3 person ties, 14 participations. thawr example: 2 participations.

## Verify
`.venv/bin/python ontology/tools/stories50_to_ttl.py --check` (up to date); `identity_audit.py --check` (passed); `ontology/validate.py` on each of the four .ttl (all CONFORM); `ontology/build_graph.py --query ontology/queries/abu_bakr.rq` (CONFORMS, exit 0, ~25 s); demo, generation-1, stories-50 `build.py` still run and change no tracked file.

## For a human
- Confirm the Ghar Thawr `placeType` decision; add an ordinal property if `skos:notation` is not acceptable.
- Is `rel_participated_in` right for narrators and for people only "connected" to a story? (Aishah "main narrator" in story 1 is one.) A governed "connected to" relation could replace it.
- Story events vs seed/generation-1 events (e.g. story 20 vs Battle of Badr) are unaligned; same for the 12 groups vs real tribes.
- The maintainer agent is labelled by role, not by name.
- The 6 advisory warnings (Dispute positions with no proponent) are pre-existing.
