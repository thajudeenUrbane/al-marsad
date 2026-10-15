# Slice 1b handover — Turtle rewritten onto canonical IDs

Spec: docs/handover/slice-1b-brief.md. Nothing here is verified history; no status was upgraded (`proposed` stays `proposed`, `stub` stays `stub`), no Arabic name or date was invented.

## What changed
- The three Turtle files now use only `canonical_id`s from `ontology/corpus/identity.csv`. The rewrite was a lookup of each `variant_ids` entry (matched with its prefix, as a whole token, as CURIE or full IRI), never string trimming.
- 16 occurrences rewritten (thawr 6, generation-1 5, seed-incidents 5), for 6 variant IDs:
  Abu Bakr `per:…4pP` -> `…4pP1`; ʿĀʾisha `per:…T8bH1` -> `…T8bH`; al-Madina `plc:…qWsE` -> `…qWsE2`; Makkah `plc:9qWe…jKzX` -> `plc:2aSd…QwE2`; Ghar Thawr `plc:uQSW…` -> `plc:3zXc…`; Arrival at Quba `ev:DPiT…` -> `ev:6gY3…eE`.
- Decisions 1-6 (all dated 15 Oct 2026, notes in identity.csv):
  1. al-Miqdād merged: stories-50 "Al-Miqdad ibn al-Aswad" now sits on `per:6nBv…QwE1`, confidence `probable`; the row `per:aXsp…9S` is retired (it was never used in a .ttl).
  2. The two ʿUrwas kept separate. The stories-50 row (`per:XWTz…`) is now `exact` for "different". `per:9pLm…xZbA` (ʿUrwa b. al-Zubayr) stays `needs-review` because of its separate ID collision with ʿUmar (`…xZbA1`); decision 4 says other flags stay.
  3. Hijra: thawr "Departure from Makkah" and "Sheltering at Ghār Thawr" each carry `crm:P9i_forms_part_of ev:nkdS…` (the seed Hijra event). marsad.ttl and relations.ttl hold no part-of property (only `mrs:within` for places and `mrs:rel_occurred_during`, which means something else); `mrs:Event` is a subclass of `crm:E5_Event`, so CIDOC's own P9i is used and nothing new was invented. Not merged.
  4. All other `needs-review` rows are unchanged and still flagged.
  5. `ontology/tools/mint_id.py` (22-char base62 from `secrets`, unique against every IRI payload of any kind, in every .ttl and identity.csv). Rule documented in docs/02 §5.2.1. No existing ID was renamed.
  6. `mrs:Group` (subclass of `crm:E74_Group`, with Tribe/Clan/Family) already exists in marsad.ttl, so no new class was added. No Turtle file holds a group yet, so no `grp:` declaration was added to any .ttl; the namespace `https://w3id.org/marsad/id/group/` is recorded in docs/02 §5.2.1 and in the 12 group rows (still `needs-review`).
- `identity_audit.py` was rewritten: the table is now the maintained source of truth and the script CHECKS it (see its docstring); the 1a derivation code is in git at d892992.
- Rebuilt outputs are tracked in git (demo/, generation-1/ data.json and html), so the regenerated ones are committed; stories-50 output did not change.

## Counts
- identity.csv: 264 rows (was 265): 184 person, 22 place, 46 event, 12 group. Confidence exact 214, probable 18, needs-review 32 (was 213/17/35).
- 131 entity IRIs in the three Turtle files, all canonical; 6 variant IDs, none left in any .ttl.

## For a human
- thawr.ttl, generation-1.ttl and seed-incidents.ttl still each define some of the same entities (Abu Bakr, ʿĀʾisha, al-Madina, Makkah in more than one file). The IDs now agree, so merged graphs combine them; the duplicate definitions and differing labels (e.g. "al-Madīna (formerly Yathrib)" vs "al-Madīna") were left for slice 1c.
- The part-of link is a maintainer modelling decision recorded as a plain triple, with no evidence layer or status. Say whether it should become an assertion.
- 12 ID-drift pairs remain (IDs a character apart that are different entities, plus payloads shared across kinds, e.g. `plc:5dFg…WsE` retired variant vs `per:5dFg…WsE` Yahya b. Bukayr); not renamed. Whether to rename stable IRIs is open.
- docs/02 §5.2 says base58; the corpus is base62 and the tool follows the corpus. Reconcile the wording.
- stories-50/build.py does not read identity.csv yet; "Al-Miqdad" there is still its own person.
