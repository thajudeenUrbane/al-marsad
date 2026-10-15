# Slice 1e handover — re-mint the hand-typed IDs
Spec: docs/handover/slice-1e-brief.md. No status was upgraded (identity.csv `confidence` untouched), no name or date was invented, nothing was pushed.
## IDs renamed (16 re-minted with `mint_id.py`, old → new; all 16 are in id-renames.csv, the 8 identity rows also keep the old ID in `variant_ids`)
Rule: a live payload sharing a run of 8+ characters with another entity's payload, live or retired (1d exemptions). The brief counted 17 (six identity rows) and that count could not be reproduced: this rule finds 16, eight of them identity rows (the six named plus Umm Salama and ʿAbd al-Raḥmān, whose IDs clash with retired IDs of other entities; live against live alone gives 13, six identity).
- The Prophet Muḥammad (peace and blessings be upon him): per:2mQ7vR9nK4pT8sY3wZ6xCe → per:Vc74FSoBSMY4TBSEwjPyai
- Abū Bakr al-Ṣiddīq: per:8sT3wY6xZc2mQ7vR9nK4pP1 → per:QYWUDj7ATL1ApLn5P7gmsQ
- Sawda bint Zamʿa: per:2sDfG6hJkQ9wErT4yUmNbV1 → per:dOPyrfzvo3NIvUQShyiRsk
- Jaʿfar b. Abī Ṭālib: per:3wY6xZc2mQ7vR9nK4pT8sA1 → per:pgEqNKdrPeXOU9fcCIc5Tf
- Umm Salama bint Abī Umayya: per:7kQwE4rTyU2mNbV9cXzAsD1 → per:5sGHTje5qGKdw6c6RWyHKV
- ʿAbd al-Raḥmān b. Abī Bakr: per:8pLkJ9hGfDsA3wErT5yUqP1 → per:w6IaTbniNnbK3AO5XyjIxJ
- Badr (place): plc:6hJkQ3wErT9yUmN5bVcXzA1 → plc:nVJ91NufhjHXlwcWdPhRn1 · Battle of Badr (event): ev:5rTyU9mNbV2cXzA8sDfGhJk1 → ev:fnXxxzRKzKDFtsSvrMamC9
- No identity row: act:4bVcX7zAsD2fGhJ9kQwErTy → act:fuU3s9la4uBpODztXJBrdJ · agt:7wQzE2rTyU9mNbV4cXzAsF → agt:EoHVIA3JZBvDsQ5jyi4SvE · agt:9wErT4yUmN7bVcX2zAsDfGh → agt:C7VpyqaTGtImKPBS8frhTf · ast:6yUmN9bVcX4zAsD7fGhJkQ → ast:VbZxdNdNCgzZQDB8G6R5YI
- No identity row: chn:8hJkQ3wErT6yUmN5bVcXzA → chn:VwuN5BCUwH0f3HtpyxBwKn · dsp:7mNbV4cXzA9sDfG5hJkQwE → dsp:5XpLhaWiTOcjESmY2MlFnI · tmp:3yUmN7bVcX4zAsD8fGhJkQ → tmp:TKki0g4ygeTVQsz4V3lHwA · tmp:7yUmN5bVcX2zAsD8fGhJkQ1 → tmp:lVbfoQpPIBr52EUOKAdAkl

## The new audit rule
`identity_audit.py` check 7 now also fails when the payloads of two different entities share a run of 8 or more consecutive characters (`RUN = 8`). Same population and exemptions as the 1d near-collision check: every IRI in the four .ttl, every canonical ID and every retired variant; retired-with-retired is history; a canonical ID and its own variant never conflict. A pair already reported as one character apart is not listed twice. Each failure prints the pair and the longest shared run; the summary adds "shared 8+ character runs".
`mint_id.py` now also rejects a candidate that shares an 8+ run with any payload it knows (live IRIs, canonical IDs, retired variants), on top of the 1d rules.
Tested by planting, audit (on throw-away copies of ontology/, 9 of 9 as expected): before the re-mint it failed with 40 shared runs, after it passes; an assertion IRI sharing exactly 8 characters with Abū Bakr's payload fails, 7 passes, 19 fails; a canonical ID and its own retired variant sharing 18 pass; two retired IDs of different entities sharing 20 pass; a retired ID sharing 14 with another entity's live ID fails; one-character and identical payloads still fail under their own heads.
Tested by planting, `mint_id.py` (random source fixed, 7 of 7): an 8-run candidate is rejected and the next clean one returned, a 7-run one accepted, runs copied from a retired ID (the old Prophet ID) and from a live one rejected, 300 real draws clean.

## Rewritten by lookup, regenerated, verified
Rewritten on whole tokens (CURIE or full IRI), never by trimming: the four .ttl (425 replacements), identity.csv (8 rows: new canonical ID, old appended to `variant_ids`, a slice-1e note), stories-50-ids.csv (22 keys embed a renamed person ID and were rewritten; the 380 assertion IDs did not change), id-renames.csv (16 rows appended, 284 in all), queries/abu_bakr.rq, generation-1/build.py (`GEN1_AGENT`). build_graph.py, site/ and its tests name none of the 16.
Regenerated: stories50_to_ttl.py (output identical to the rewritten file), demo/{data.json,index.html}, generation-1/{data.json,seed-data.json,index.html,at-scale.html,wider-network.html}; stories-50/ came out unchanged. Every rewritten or regenerated file other than the three tables equals its previous version once the 16 new IDs are mapped back, so only IDs changed.
Verify: `.venv/bin/python ontology/tools/identity_audit.py --check` (0 shared, 0 near, 0 runs) · `ontology/tools/stories50_to_ttl.py --check` (up to date) · `ontology/validate.py` on examples/thawr.ttl and corpus/{generation-1,seed-incidents,stories-50}.ttl (all CONFORM) · `ontology/build_graph.py --query ontology/queries/abu_bakr.rq` (CONFORMS, 12,641 triples; stories 16, generation-1 5 + 6 participations, seed 12 + 14, thawr 2, as in 1d) · demo, generation-1, stories-50 `build.py` · `site/build.py` (321 pages), `site/check_budget.py`, `site/check_html.py`, `python -m unittest discover -s site/tests` (64 tests): all pass.

## For a human
- pages/marsad.html (line 596, an SVG label) still shows the retired chain ID `chn:8hJkQ3wErT6yUmN5bVcXzA`: a published page outside this slice's files, so its figure now differs from thawr.ttl.
- docs/02 §5.2.1 still says the audit fails on shared and one-character-apart payloads and that 268 IDs are in id-renames.csv; it should also name the 8-character run and these 16 (docs were out of scope).
- Retired IDs that have no identity row (the other 8, and 1d's) are not compared with new IDs by either tool, as in 1d; only the exact old ID is barred from the .ttl (check 8). Old IDs quoted in identity.csv notes, slice-1b/1c/1d.md and the brief are history and were not edited.
