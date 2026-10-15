# Slice 5 brief — connect outward

Context: README "Standing rules"; docs/13-platform-direction.md §4 slice 5; docs/02-knowledge-architecture.md (identity and IDs, §5.2 rule 4: external IDs are alignment, never the primary key); docs/handover/maintainer-answers-1.md and maintainer-answers-2.md; LICENSING.md (tables that map al-Marṣad IDs to external IDs are CC0); ontology/corpus/identity.csv; ontology/marsad.ttl. Do not read chat history; this file is the brief. Branch: `slice-5-links`. Other slices run in parallel (search, CI, review queue, Ibn Hishām ingestion, timeline/map, graph observatory, learning paths, ask-the-graph).

## Goal
Doc 13: ≥80 % of people and places carry an external ID candidate; links render on pages later (rendering happens at integration; this slice is data and tooling only).

## Do
1. `ontology/tools/link_external.py`: for each person, place and work in identity.csv / the graph, find candidates: Wikidata items for people and places; al-Thurayya gazetteer entries for places; OpenITI author/work URIs for authors and works present in the graph.
2. Output `ontology/corpus/external-ids.csv`: canonical_id, kind, system (wikidata / althurayya / openiti), external_id, external_label, evidence (which fields matched: name forms, Arabic name, dates, description), confidence (exact / probable / needs-review), status (always `proposed`). At most one `exact` per system per entity; ambiguous candidates are all listed as needs-review. A match is a proposal for scholars, never an identity decision: no merges, no edits to identity.csv. Never invent an ID: every external_id must come from a real response received.
3. RDF only if marsad.ttl has a fitting way to state a proposed link without asserting it as fact (e.g. an Assertion with status proposed); otherwise keep CSV only and explain in the handover. A TTL, if added, must validate.
4. Report coverage per kind and confidence; list notable ambiguities (people sharing a name, places with many candidates). Coordinates found for places are useful for the map: record them in the CSV or a sibling CSV as proposed data with their source, never written into the corpus as fact.

## Network
query.wikidata.org/sparql works: descriptive User-Agent naming the project, batch with VALUES, about one request per second, retry with backoff on 429/5xx, cache responses under build/cache/ (gitignored). The Wikidata web API (www.wikidata.org/w/api.php) rate-limits hard: prefer SPARQL. raw.githubusercontent.com works (al-Thurayya: github.com/althurayya; OpenITI metadata: github.com/OpenITI); api.github.com is blocked.

## Done when
- The CSV covers ≥80 % of people and places with at least a needs-review candidate, or the handover explains honestly why not.
- `ontology/build_graph.py` CONFORMS; the tool re-runs from cache deterministically (same CSV).
- Handover `docs/handover/slice-5.md` (≤60 lines).

## Scope
`ontology/tools/link_external.py` (new), `ontology/corpus/external-ids.csv` (+ optional sibling CSV/.ttl) (new), `docs/handover/slice-5*.md`. Do not edit identity.csv or `ontology/tools/identity_audit.py`. Entities are keyed by canonical ID; slice 1e (re-minting 16 hand-typed IDs) lands on main meanwhile: after rebasing at the end, re-run the tool (or remap via `ontology/corpus/id-renames.csv`) so the CSV uses current IDs.

## Rules
AI never asserts. Never upgrade a status. Never invent names, IDs or data. No model names or IDs in any repo file. Commit and push the branch after each major step (WIP commits are fine); commit messages end with the attribution lines given in the session. At the end: rebase on origin/main, re-run the tool from cache, re-run the checks, push the branch (`--force-with-lease` only on this branch). Never push to main, never open a PR.
