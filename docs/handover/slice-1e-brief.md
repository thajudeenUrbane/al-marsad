# Slice 1e brief — re-mint the hand-typed IDs

Context: docs/handover/slice-1d.md (how 1d renamed 268 IDs), docs/02 §5.2.1 (the minting rule), docs/handover/maintainer-answers-1.md (O2: rename IDs that break the rule now, before anything is public). Do not read chat history; this file is the brief. Small slice: one session.

## Why
Some IDs from the very first hand-written files are not random. They share long runs of characters with each other, e.g. the Prophet ﷺ `per:2mQ7vR9nK4pT8sY3wZ6xCe` and Abū Bakr `per:8sT3wY6xZc2mQ7vR9nK4pP1`. On 15 October 2026, 17 IRI payloads shared a run of 8 or more characters with another payload. Six were identity rows: the Prophet ﷺ, Abū Bakr, Sawda bint Zamʿa, Jaʿfar b. Abī Ṭālib, Badr (place) and the Battle of Badr. The 1d audit only catches one-character near-collisions, so it missed them. Two random base62 IDs sharing an 8-character run is vanishingly unlikely (about 1 in 10^14 per position pair), so a shared run means hand-typed.

## Do
1. Find every payload that shares a run of 8+ characters with another payload of any kind (the canonical ID against its own retired variants is exempt, as in 1d). Re-mint each one with `ontology/tools/mint_id.py`.
2. Rewrite by lookup, never by trimming, the same way 1d did: every .ttl, `identity.csv` (old ID appended to `variant_ids`), `stories-50-ids.csv`, `id-renames.csv` (append; reason "hand-typed: shares an 8-character run with another ID"), `ontology/queries/abu_bakr.rq`, `build_graph.py` and anything else that names an ID. Site code and tests must not hard-code IDs. If one does, fix the test to look the entity up by name instead.
3. `identity_audit.py`: fail on any shared 8+ character run, under the same exemptions as the 1d near-collision check. `mint_id.py`: refuse a payload that shares an 8+ run with any existing payload. Test both by planting a case.
4. Regenerate whatever is generated: `stories50_to_ttl.py` if its inputs changed; the demo, generation-1 and stories-50 builds (commit tracked outputs only if they change); `site/build.py`.

## Done when
- `identity_audit.py --check` passes with 0 shared payloads, 0 near-collisions and 0 shared 8+ runs. `validate.py` conforms on every corpus file. `build_graph.py --query ontology/queries/abu_bakr.rq` conforms and still returns links from all four sources. `stories50_to_ttl.py --check` is up to date. The three old builds succeed. `site/build.py`, `site/check_budget.py`, `site/check_html.py` and `python -m unittest discover -s site/tests` all pass.
- docs/handover/slice-1e.md (≤30 lines): the IDs renamed (old → new, with names for identity rows) and the new audit rule.
- Committed on the current branch; message ends with the attribution lines you are given. Do not push.

## Rules
Never upgrade a status. Never invent names or dates. Keep tool output short.
