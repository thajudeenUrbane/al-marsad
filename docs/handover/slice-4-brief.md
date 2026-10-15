# Slice 4 brief — AI-assisted ingestion of Ibn Hishām's Sīra

Saved as given on 15 October 2026 (branch `slice-4-ingest`), with the session-only setup lines left out. Do not read chat history; this file is the brief.

## Read first
README.md "Standing rules"; docs/13-platform-direction.md (§4 slice 4); docs/07-ai-architecture.md (§7 AI in the ingestion pipeline, §10); docs/06-scholarly-methodology.md (§2, §3, §10 red lines); docs/02-knowledge-architecture.md (the report as atomic unit, §5.2.1 ID rule); docs/handover/maintainer-answers-1.md and maintainer-answers-2.md; LICENSING.md; ontology/marsad.ttl, ontology/shapes.ttl, ontology/relations.ttl.

## Goal
At least 200 proposed claims from one text, each with an exact source passage span, ready for the slice 3 review queue. The maintainer chose Ibn Hishām's *al-Sīra al-Nabawiyya* (E32); the edition will be specified by the scholars later (E33), so record exactly which digital edition was used and flag it as provisional. English is translated in-house with scholar review (E34): any English gloss added is `proposed` AI text, clearly labelled, never a translation of record.

## Do
1. Find the text in OpenITI (Ibn Hishām died 218 AH, so the 0225AH repository; or the OpenITI RELEASE). Record the OpenITI URI, version and the base edition named in its metadata.
2. **Licence.** Read the licence of that OpenITI text and of the corpus. Our data is CC BY-SA 4.0 and must stay redistributable. If the text's licence is not compatible (e.g. NonCommercial) or unclear, do NOT commit the text: keep it in a gitignored cache (download script + checksum), and commit only passage pointers (URI, version, character offsets or milestones) plus the claims. Write the licence finding in the handover.
3. Choose passages touching what the graph already has (the Hijra, Badr, the first believers), so reviewers see connected claims. Model passages and reports as marsad.ttl and shapes.ttl require (Report, Passage, Witness, Work, chains, Assertion with fromReport or nonReportBasis). An ascription such as "qāla Ibn Isḥāq" is recorded exactly as written, never completed.
4. The extracting model is the agent doing this slice. Each claim: subject, predicate from ontology/relations.ttl (add one only if none fits, following the file's pattern), object, the exact Arabic span (offsets into the passage) and its passage. Status `proposed`, coverage `stub`, created by a generic software agent labelled "AI extraction pass (slice 4)" with the date. **No model names or IDs anywhere in the repo.** Resolve people, places and events to existing canonical IDs via ontology/corpus/identity.csv only when the text makes the match clear; otherwise mint a new ID with ontology/tools/mint_id.py and append an identity.csv row with confidence `needs-review` and the Arabic name exactly as in the text. Never merge or split existing people. Never invent names, dates or citations.
5. `ingest/ibn_hisham.py` rebuilds the corpus TTL from the (cached) text plus the extraction output `ingest/claims/ibn-hisham.jsonl` (one claim per line, with span), so the TTL is reproducible and each claim reviewable.
6. Spot-check 20 claims against their spans; list doubtful ones in the handover.

## Done when
ontology/corpus/ibn-hisham.ttl (or similar) validates; build_graph CONFORMS with it; ≥200 proposed claims each with an exact span pointer; handover docs/handover/slice-4.md (≤60 lines: source, edition, licence finding, counts, what needs a scholar).

## Scope
ingest/** (new), ontology/corpus/ibn-hisham*.ttl (new), appended rows at the END of ontology/corpus/identity.csv, ontology/relations.ttl only if truly needed, one .gitignore line for the cache, docs/handover/slice-4*.md. Do NOT edit ontology/tools/identity_audit.py; if the audit must learn about the new file, say so in the handover. Never hard-code entity IDs in code: slice 1e (re-minting 16 hand-typed IDs, including the Prophet ﷺ, Abū Bakr and Badr) is landing on main at the same time; resolve through identity.csv by name so a re-run after rebasing picks up new IDs.

## Finish
1. Checks: `ontology/build_graph.py` CONFORMS; `ontology/validate.py` on the new TTL; the script reproduces the TTL byte-for-byte.
2. Commit messages end with the attribution lines given for the session.
3. Rebase on origin/main; resolve conflicts (identity.csv: keep both sides' rows); re-run the script so IDs follow any renames (ontology/corpus/id-renames.csv maps old → new); re-run the checks; commit fixes.
4. Push the branch only (`--force-with-lease` only on this branch after the rebase). Never push to main, never open a PR.
5. Report: branch and commit hash; a short summary (source, edition, licence finding, claim counts by predicate, new vs existing entities); the exact verification commands and results; anything left for a human.

## Working alongside
Other slices run at the same time: search (site/), CI, the review queue (review/, ontology vocabulary additions), external ID links, timeline/map, the graph observatory, learning paths, and ask-the-graph.
