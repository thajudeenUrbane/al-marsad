# Slice 1b brief — rewrite the Turtle onto canonical IDs

Context: docs/13-platform-direction.md §4 slice 1; read docs/handover/slice-1a.md first. Do not read chat history; this file is the brief.

## Goal
The three Turtle files use only canonical IDs from ontology/corpus/identity.csv, the maintainer's decisions below are applied, and every existing build still runs.

## Decisions approved by the maintainer (15 October 2026)
1. **Merge al-Miqdād:** stories-50 "Al-Miqdad ibn al-Aswad" = Turtle "al-Miqdād b. ʿAmr" (per:6nBvCxZ4aSdF7gHjK9mQwE1). Same man; "ibn al-Aswad" is from his adoption by al-Aswad ibn ʿAbd Yaghūth. Canonical = the Turtle IRI; confidence `probable`, note the reason.
2. **Keep separate:** ʿUrwa ibn Masʿūd al-Thaqafī (Companion, envoy at Ḥudaybiyya) ≠ ʿUrwa b. al-Zubayr (Tābiʿī, narrator). Confidence `exact` for "different", note the reason.
3. **Hijra events — part-of, not merge:** thawr "Departure from Makkah" and "Sheltering at Ghār Thawr" become parts of the seed's Hijra event. Use the ontology's existing part-of relation (look in ontology/relations.ttl and marsad.ttl; CIDOC-CRM P9 / P9i if that is what is used). Do not invent a new property if one exists.
4. **All other needs-review rows stay unmerged** and visibly flagged. Do not resolve them.
5. **ID minting rule:** every new ID is random (22 chars base62 from `secrets`), checked unique against the payload of every existing IRI of *any* kind; never derived from another ID. Write a small `ontology/tools/mint_id.py` and document the rule in docs/02-knowledge-architecture.md (one short subsection). Existing IDs that collide are **not** renamed in this slice (renaming stable IRIs is a separate decision); just record the rule.
6. **Groups:** add a `grp:` prefix (`https://w3id.org/marsad/id/group/`) and a minimal group class only if marsad.ttl has nothing suitable (check CIDOC-CRM E74 Group first). Update identity.csv accordingly.

## Do
1. Set up `.venv` if missing: `python3 -m venv .venv && .venv/bin/pip install rdflib pyshacl`.
2. Rewrite ontology/examples/thawr.ttl, ontology/corpus/generation-1.ttl, ontology/corpus/seed-incidents.ttl by **lookup in identity.csv** (variant_ids → canonical_id), never by string trimming. Change generation-1 and seed together.
3. Apply decisions 1–6; update identity.csv and identity_audit.py so `--check` passes.
4. Run `.venv/bin/python ontology/validate.py` on all three files: must conform (no violations). Run demo/build.py, generation-1/build.py and stories-50/build.py: all must still succeed.
5. Do not change any status upward (`proposed` stays `proposed`, `stub` stays `stub`).

## Done when
- No variant ID appears in any .ttl; validate conforms; all three builds succeed; `identity_audit.py --check` passes.
- docs/handover/slice-1b.md (≤60 lines): what changed, counts, anything left for a human.
- Committed on the current branch, message ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Do not push.

## Rules
Unverified data stays unverified. Keep tool output short. Stop and write the handover if context nears 200k.
