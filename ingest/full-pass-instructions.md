# Full-book extraction pass: instructions for one chunk

These are the instructions each extraction run follows for one chunk of Ibn Hishām's *al-Sīra al-Nabawiyya* (`ingest/sira_full.py`). They are committed so the pass can be repeated and audited.

## Your input

- `ingest/cache/full/chunks/NNN.txt`: whole sections of the text. Each section starts with a line `=== SXXXX | vol. V, p. P | heading (editors', never quote it): ...` followed by the section's text (OpenITI markup already removed).
- `ingest/cache/full/existing.tsv`: the people, places and events already in the graph (kind, preferred_name_en, name_ar, other names). **Do not read it whole; grep it** for each well-known figure you meet (e.g. `grep -i "bakr" ingest/cache/full/existing.tsv`).

## Your output

Write `ingest/cache/full/out/NNN.jsonl`, one JSON object per line, then run
`python3 ingest/sira_full.py verify NNN` and fix every problem it reports until it says `OK`.
Write the file in parts if it is long (Write the first part, then append with Bash `cat >> ... <<'EOF'`), but the final file must be complete and valid.

### Records

1. One `section` label for every section that has any record:
   `{"t":"section","sec":"S0331","label":"The Prophet's devotions at Ḥirāʾ and the first revelation"}` (short English, ≤ 90 characters, your description, no Arabic).

2. Every **named person** in the chunk, once per chunk:
   `{"t":"person","id":"p12","name":"ʿUtba b. Rabīʿa b. ʿAbd Shams","ar":"عتبة بن ربيعة بن عبد شمس","sec":"S0412","note":"of Quraysh, ʿAbd Shams"}`
   - `id`: local to this chunk (`p1`, `p2`, ...).
   - `name`: English, IJMES-style with diacritics (ā ī ū ḥ ṣ ḍ ṭ ẓ ʿ ʾ), `b.` for ibn and `bint` for bint. Give the person's ism (or kunya, if that is how they are known) and their father, plus the grandfather only if the text gives it or it is needed to tell two people apart. Spell the same person the same way every time. Use the forms already common in this graph: "ʿAbd Allāh", "ʿAbd al-Muṭṭalib", "al-ʿAbbās b. ʿAbd al-Muṭṭalib", "Abū Sufyān b. Ḥarb", "Ḥamza b. ʿAbd al-Muṭṭalib", "ʿAlī b. Abī Ṭālib", "ʿUmar b. al-Khaṭṭāb", "ʿUthmān b. ʿAffān".
   - `ar`: the person's name **copied exactly** from one section of this chunk (the fullest form the chunk gives), and `sec`: that section.
   - `note`: optional, ≤ 60 characters: clan, tribe or role, to tell them apart from namesakes (e.g. "of the Anṣār, Banū al-Najjār", "poet", "Jewish leader of Banū Qaynuqāʿ").
   - **If the person is already in `existing.tsv`** and the text makes the match clear, add `"existing":"<preferred_name_en exactly as in existing.tsv>"` (`name` and `ar` are still welcome). The Prophet ﷺ is `"existing":"The Prophet Muḥammad (peace and blessings be upon him)"`. When unsure, do not use `existing`.
   - Include everyone with a name: Companions, Quraysh, Anṣār, Jews, Christians, kings, poets, narrators in chains (حدثني فلان عن فلان), ancestors in genealogies, women, slaves and clients. A person known only by a kunya (أبو فلان, أم فلان) or a laqab is a person. Not: God, angels, prophets of earlier scripture (Ādam, Ibrāhīm, Ismāʿīl, Mūsā, ʿĪsā ...), unnamed people ("a man of Quraysh"), tribes or clans as such (Banū X, Quraysh). Pre-Islamic Arabian ancestors in genealogies (ʿAdnān, Maʿadd, Fihr, Quṣayy ...) ARE people.

3. Every **place** that a claim needs: `{"t":"place","id":"l3","name":"Badr","ar":"بدر","sec":"S0700","place_type":"settlement"}` with `place_type` one of: settlement, quarter, well, mountain, cave, valley, oasis, route_node, region, structure, battlefield, cemetery. Use `existing` the same way (Makkah, Madinah, Badr ...).

4. Every **event** that a claim needs: `{"t":"event","id":"e2","name":"The Battle of Badr","sec":"S0700"}` (an `ar` is optional for events). Give events stable, plain names, as another reader of another chunk would: "The Battle of Badr", "The Battle of Uḥud", "The Battle of the Trench", "The Treaty of al-Ḥudaybiya", "The Conquest of Makkah", "The Battle of Ḥunayn", "The expedition to Tabūk", "The First Pledge of al-ʿAqaba", "The Second Pledge of al-ʿAqaba", "The emigration to Abyssinia", "The Hijra of the Prophet ﷺ to Madinah", "The raid of Nakhla", "The Year of the Elephant" ... Prefer an `existing` event when one fits (grep for it).

5. **Claims**: every relation the text states between these entities:
   `{"t":"claim","sec":"S0412","s":"p12","p":"rel_father_of","o":"p13","quote":"عتبة بن ربيعة","gloss":"Rabīʿa is the father of ʿUtba (the name ʿUtba b. Rabīʿa)."}`
   - `quote`: the words the claim rests on, **copied exactly** from that section, contiguous, as short as possible while still containing what states the relation (usually 2 to 20 words). Never from the heading.
   - `gloss`: one short English sentence saying what the text states. It is labelled as machine-written; never present it as a translation.
   - `q`: optional list of qualifiers: `hedged` (فيما بلغني، فيما يزعمون، زعموا، والله أعلم), `text_alternative` (ويقال، ويقول قائل: one of two reports; make each its own claim), `share_not_present` (counted at Badr but absent, given a share), `editorial_brackets` (rests on words in round brackets).

### Predicates (s → o; p = person, l = place, e = event)

- Kinship (p → p): `rel_father_of`, `rel_mother_of`, `rel_sibling_of`, `rel_spouse_of`, `rel_divorced_from`, `rel_paternal_uncle_of`, `rel_maternal_uncle_of`, `rel_cousin_of`, `rel_ancestor_of` (only for "of the descendants of", not for each generation of a nasab), `rel_adopted_by`.
  - **A nasab is a chain of claims**: "عتبة بن ربيعة بن عبد شمس" gives Rabīʿa father_of ʿUtba and ʿAbd Shams father_of Rabīʿa (three people, two claims, each quote the pair it rests on: "عتبة بن ربيعة", "ربيعة بن عبد شمس"). "وأمه فلانة" gives mother_of. "أخو بني فلان" is not kinship.
- Social and political (p → p): `rel_mawla_of` (s is the mawlā/client of o), `rel_ally_of` (ḥalīf), `rel_pledged_allegiance_to`, `rel_party_to_treaty_with`, `rel_opposed`, `rel_fought_alongside`, `rel_fought_against`, `rel_killed` (s killed o), `rel_captured` (s captured o), `rel_manumitted` (s freed o), `rel_protected` (jiwār), `rel_sheltered` (s hosted o), `rel_corresponded_with`, `rel_sent_delegation_to`, `rel_appointed` (s appointed o, e.g. over Madinah in his absence, or as commander), `rel_succeeded`. `rel_governed` is p → l.
- Transmission (p → p): `rel_narrated_from` (s narrated from o): one claim for each link of a chain as written, "حدثني يحيى بن عباد عن أبيه" gives Yaḥyā narrated_from his father (and father_of). Ibn Isḥāq is `"existing":"Ibn Isḥāq (Muḥammad b. Isḥāq)"` and Ibn Hishām is `"existing":"Ibn Hishām (ʿAbd al-Malik b. Hishām)"`. "قال ابن إسحاق" alone is not a claim; "قال ابن إسحاق: حدثني فلان" gives Ibn Isḥāq narrated_from فلان.
- Places (p → l): `rel_born_at`, `rel_died_at`, `rel_buried_at`, `rel_resided_in`, `rel_migrated_from`, `rel_migrated_to`, `rel_travelled_via`, `rel_visited`, `rel_sheltered_at`.
- Participation (p → e): `rel_participated_in` (was among those at it: the lists of who was at Badr, Uḥud, ʿAqaba, the emigrants to Abyssinia are the core of the network: make one claim for every name in such a list), `rel_led` (p → e or p → p), `rel_witnessed`, `rel_present_at`, `rel_absent_from`.
- Events: `rel_occurred_at` (e → l), `rel_occurred_during` (e → e), `rel_part_of` (e → e), `rel_preceded` (e → e).
- Lifelines: `rel_born_during` (p → e), `rel_died_during` (p → e: killed at Badr = died_during Badr, and also `rel_killed` if the killer is named), `rel_age_at` (p → e, plus `"age_quote":"<exact words of the age>"` and `"years":[63]`, one number per alternative, only numbers the text gives), `rel_dated` (e → literal: `"o_quote":"<exact time expression>"` in place of `o`).

### Notes from the pilot chunk

- Madinah is `"existing":"al-Madīna"`, Makkah `"existing":"Makkah"`, Abyssinia `"existing":"al-Habasha (Aksum)"`, Syria `"existing":"al-Sham"`, Ṭāʾif `"existing":"al-Ta'if"`.
- A person who is NAMED is always a person record, even with no claim (e.g. Ibn ʿAbbās named after an unnamed link, a person a poem addresses): the aim is every named person in the book.
- Emigrants to Madinah: `rel_migrated_to` Madinah. Emigrants to Abyssinia: `rel_participated_in` "The emigration to Abyssinia" and `rel_migrated_to` Abyssinia.
- Lodging lists ("نزل فلان على فلان"): `rel_sheltered` host → guest; quote the words naming the guest and the host if they are close together.
- A bare ancestor name (ʿAmr, Kaʿb ...) in one lineage is not the same person as the same bare name in another lineage unless the text shows it: keep them apart, with a note "father of X".
- Helper scripts, if you write any, go in `ingest/cache/full/work/` (create it), never elsewhere in the repository.

## Rules (red lines)

- **Only what the text states.** Never add what you know from elsewhere, never complete an ascription, never infer a relation the words do not say. If a relation is uncertain, leave it out.
- Every `ar`, `quote`, `age_quote` and `o_quote` must be an exact copy of characters in that section (the verify step checks). Copy letters exactly; do not add or remove hamzas or diacritics.
- Poetry: take named people and the relations the verses or their introduction state plainly ("قال حسان بن ثابت يرثي حمزة": Ḥassān is a person; Ḥamza is a person; Ḥamza died_during Uḥud only if that is stated). Do not mine verses for anything figurative.
- Ibn Hishām's linguistic notes: take the people they name (narrators, poets) and nothing else.
- Be complete. Go section by section to the end of the chunk. A long list of names (Badr, the emigrants, the people of ʿAqaba, the slain) must give every name, each with its claims.
- No model or product names anywhere in what you write.
