# Slice 1a brief — identity audit and canonical ID table

Context: docs/13-platform-direction.md §4, slice 1 ("One graph"). This is the first half.

## Goal
Every person, place and event in the project gets exactly one canonical ID, recorded in one reviewable table.

## Inputs
- ontology/examples/thawr.ttl, ontology/corpus/generation-1.ttl, ontology/corpus/seed-incidents.ttl (IDs are opaque, e.g. per:3jLd4kNqR7mZpW2vXcT8bH)
- stories-50/build.py (ALIASES / GROUPS / SPLITS tables) and stories-50/data.json (171 people, no IDs yet)
- ontology/marsad.ttl for which label properties hold names

## Known problem
IDs drift between files for what looks like the same person: per:3jLd4kNqR7mZpW2vXcT8b1 / ...bH1 / ...bH, and per:2wErT5yUqP8pLkJ9hGfDsA vs ...DsA1. Find every such case for per:, plc:, ev:.

## Do
1. `python3 -m venv .venv && .venv/bin/pip install rdflib pyshacl` (.venv is gitignored).
2. Write ontology/tools/identity_audit.py: loads the three Turtle files, lists every per:/plc:/ev: IRI with its labels and which files use it, and flags (a) near-identical IRIs, (b) different IRIs sharing a normalised label (strip diacritics, ʿ, ʾ, "al-", ibn/b., case).
3. Produce ontology/corpus/identity.csv with columns: kind, canonical_id, preferred_name_en, name_ar (blank if unknown — do NOT invent Arabic), variant_ids (;-separated), stories50_names (;-separated), source_files, confidence (exact|probable|needs-review), note.
   - Canonical ID rule: keep the IRI used in the most files; on a tie, the one in thawr.ttl.
   - Map every stories-50 person to an existing canonical ID where one clearly exists; otherwise mint a new opaque ID in the same style (22-23 chars, [A-Za-z0-9]) and mark confidence accordingly.
   - stories-50 GROUPS stay out of the person rows (add them as kind=group).
4. Do NOT edit any .ttl file or the stories-50 build. Rewriting comes in slice 1b.

## Done when
- identity.csv exists, the audit script re-creates it deterministically, and every stories-50 person and every IRI in the three files appears exactly once.
- docs/handover/slice-1a.md written: counts (rows, merges, new IDs, needs-review), the list of ID-drift cases, anything surprising. Max 60 lines.
- Changes committed on the current branch (platform-direction), message ending with the line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Do not push.

## Rules
Everything is unverified data; never upgrade any status. Keep tool output short (pipe through head/tail). Stop and write the handover if context nears 200k.
