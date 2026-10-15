# Slice 1c brief — 50 Stories into the ontology, one unified build

Context: docs/13-platform-direction.md §4 slice 1. Read docs/handover/slice-1b.md first (1c starts only after 1b is committed).

## Goal
One command builds one graph from every corpus file, including the 50 stories, and validates it.

## Do
1. Write `ontology/tools/stories50_to_ttl.py`: reads stories-50/source/50-stories.md (reuse the parsing in stories-50/build.py — import it, do not copy it) plus identity.csv, and writes `ontology/corpus/stories-50.ttl`:
   - each story as an event (or narrative unit — pick what marsad.ttl supports and say why in the handover), with title, order, part, and its prose kept as a source text attributed to the maintainer's doc (rev 7, 10 October 2026) as an unverified secondary compilation;
   - each person link as an assertion with role text from the doc, `assertionStatus = proposed`, coverage `stub`;
   - the "accepted Islam later" marker kept as a qualifier, not dropped;
   - people and groups by canonical ID from identity.csv only.
2. Write `ontology/build_graph.py`: loads marsad.ttl, relations.ttl and every file in ontology/corpus/ + examples/, writes `build/graph.ttl` (gitignored) and prints counts per class; exits non-zero if SHACL validation has violations.
3. Check the merge works: Abū Bakr's canonical IRI must link to his stories, incidents and kinship ties from all sources in one SPARQL query. Put that query in the handover as proof.

## Done when
- `build_graph.py` runs clean (conforms) and the Abū Bakr query returns links from all four sources.
- docs/handover/slice-1c.md (≤60 lines) and docs/handover/slice-1-summary.md (≤30 lines, for the maintainer: what "one graph" now means, what is still unverified, what needs a scholar).
- Committed on the current branch, message ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Do not push.

## Rules
Never upgrade a status. Never invent Arabic names or dates. Keep tool output short. Stop and write the handover if context nears 200k.
