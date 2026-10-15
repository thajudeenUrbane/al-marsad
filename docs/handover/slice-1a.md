# Slice 1a handover — identity audit

Outputs (all unverified data; no status upgraded, no .ttl or stories-50 file touched):
- `ontology/tools/identity_audit.py` — `.venv/bin/python ontology/tools/identity_audit.py` writes the table; `--check` confirms it re-creates byte-for-byte; `--list` prints every IRI with labels and files.
- `ontology/corpus/identity.csv` — one row per entity, columns as in the brief. IDs are written as `per:` / `plc:` / `ev:` (and `grp:` for groups).
- Needs `rdflib` (`python3 -m venv .venv && .venv/bin/pip install rdflib pyshacl`).

## Counts
- 137 entity IRIs found in the three files (65 per, 25 plc, 47 ev). Every one appears exactly once in the table, as a canonical_id or in variant_ids. The script asserts this.
- 265 rows: 185 person, 22 place, 46 event, 12 group.
- Merges: 6 (137 IRIs became 131 rows) — see below.
- New IDs minted: 134 (122 stories-50 persons with no counterpart in the Turtle, 12 groups). Minted from a hash of the stories-50 slug, 22 chars, so re-runs give the same IDs.
- stories-50: 171 people = 49 mapped to an existing ID + 122 new. 14 Turtle persons have no stories-50 counterpart (the Prophet, Abu Talib, Hafsa, Sawda, Umm Kulthum, Zayd b. Thabit, al-Bukhari and others).
- Confidence: exact 213, probable 17, needs-review 35 (18 person, 5 place, 12 group). Meaning is in the script docstring.

## The six merges (same label, different IRI; canonical = most files, tie = thawr)
- per `3jLd…T8bH` (thawr) + `…T8bH1` (generation-1): ʿĀʾisha. Canonical `…T8bH`.
- per `8sT3…4pP` (thawr) + `…4pP1` (generation-1): Abu Bakr. Canonical `…4pP`.
- plc al-Madina: `5dFg…qWsE` (thawr) + `…qWsE2` (generation-1, seed). Canonical is `…qWsE2` (two files). Arabic names kept: المدينة;يثرب.
- plc Makkah: `9qWe…jKzX` (thawr) + `2aSd…QwE2` (generation-1, seed). Canonical `…QwE2`.
- plc Ghar Thawr: `3zXc…LqW` (thawr) + `uQSWiqCgjHmrPQaKnBERUn` (seed). Canonical `3zXc…` (tie, thawr).
- ev Arrival at Quba: `6gY3…eE` (thawr) + `DPiT3Qift9Qbxga9AiaDog` (seed). Canonical `6gY3…` (tie, thawr).

## ID-drift cases (near-identical IRIs of one kind: 15 pairs)
Only 3 are the same entity; 12 are DIFFERENT entities whose IDs differ by one trailing character.
- Same entity (drift): ʿĀʾisha `…T8bH` / `…T8bH1`; Abu Bakr `…4pP` / `…4pP1`; al-Madina `…qWsE` / `…qWsE2`.
- The brief's two cases are not all the same person: `3jLd…T8b1` is ʿAlī b. Abī Ṭālib (not ʿĀʾisha), so `T8b1` vs `T8bH`/`T8bH1` is a collision. `2wErT…DsA` is al-Layth b. Saʿd (thawr) but `…DsA1` is Muṣʿab b. ʿUmayr (generation-1, seed): different people.
- Other different-entity pairs: Ibn Shihab/Hamza, Yahya b. Bukayr/al-Zubayr, al-Bukhari/al-Miqdad b. Amr, ʿUqayl/Saʿd b. Muʿadh, ʿUrwa/ʿUmar, Anas/ʿUthman (`6gY3…E1` vs `8gY3…E1`), places waypoint/Makkah, waypoint/Hudaybiyya, Makkah/Uhud.
- Pattern: generation-1 appears to mint new IDs by taking a thawr ID and appending a digit (or changing one character), so a trailing digit does NOT mean "same entity". Trimming or fuzzy-matching IDs would merge different people. Rewrite by label-checked mapping (identity.csv), never by string trimming.
- 22 more cross-kind pairs share an opaque payload under different prefixes (e.g. place `5dFg…WsE` Madina vs person `5dFg…WsE` Yahya b. Bukayr). Distinct IRIs, so harmless to the graph, but the "opaque unique ID" assumption does not hold across kinds.
- All 16 Turtle persons and 5 places caught in these collisions are `needs-review`, with the partner IRI named in the note. The other 2 person needs-review rows are the new-ID flags in item 3 below.

## Surprising / for a human
1. The seed file references generation-1 IRIs without redefining them (e.g. `per:…E1`), so labels come only from generation-1. Any slice 1b rewrite must change both files together.
2. Two thawr places are both labelled "Route waypoint (unidentified)". Not merged on name (a placeholder label says nothing); each stays its own row, needs-review.
3. al-Miqdad: stories-50 "Al-Miqdad ibn al-Aswad" is not mapped to the Turtle "al-Miqdād b. ʿAmr". They may name one figure (a different patronymic for the same man), but that is a scholar's call, so it is a new ID flagged needs-review. Same flag for "Urwah ibn Mas'ud al-Thaqafi" vs "ʿUrwa b. al-Zubayr" (probably different people).
4. Likely event overlap, not merged: thawr "Departure from Makkah" and "Sheltering at Ghar Thawr" vs seed "The Hijra: departure from Makkah, via Ghar Thawr". Decide whether these are one event or a part-of relation.
5. The Prophet ﷺ is a person in the Turtle files (label includes "peace and blessings be upon him") and is not among the 171 stories-50 people. Left as is.
6. The 12 groups get provisional `grp:` IDs; no `grp:` prefix or mrs:Group instance exists yet. Decision needed in slice 1b. Note: `GROUPS` in stories-50/build.py has "early Companions gathered with him" in lower case, while data.json has it capitalised.
7. Arabic names are filled only where the Turtle already holds them (mrs:phaseName @ar, places only: Makkah, Madina, Ghar Thawr, Badr, Uhud, Hudaybiyya). Nothing invented; all persons and events are blank.
8. Stories-50 matching: 45 of the 49 matched on the normalised full name; 4 went through a name variant and are `probable` (Abu Dujana, al-Najashi, Nusayba, Umm Salama). Short forms (Abu Bakr, Ali, Umar and so on) were already folded in by build.py ALIASES.

## For slice 1b
- Read identity.csv; rewrite by lookup on variant_ids and stories50_names, not by pattern.
- Check `--check` still passes after any change to the three Turtle files or data.json, or regenerate and review the diff.
