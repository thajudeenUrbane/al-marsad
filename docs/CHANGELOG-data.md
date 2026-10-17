# Data changelog

Changes to how the data is recorded, as distinct from what it claims: modelling fixes, re-pointed links and cleared bookkeeping flags (maintainer answers round 3, G6). A change to what a source is taken to say goes to the review queue instead. The newest entries come first. Every claim named here is still `proposed`.

## 17 October 2026 — slice 11a

- **Khadīja and Fāṭima.** `ontology/corpus/generation-1.ttl` recorded Khadīja bint Khuwaylid as "father of" Fāṭima bint Muḥammad. The registry had no "mother of" when the file was written, so the nearest term was used and the basis text said so. The claim now uses `rel_mother_of` and its basis text records the change. The prototype pages (`generation-1/`) and the Ask test question g18 follow.
- **Story events are not historical events.** The full-book pass over Ibn Hishām linked 1,141 claims to 16 events of the AI-generated 50 Stories (for example story 20, "The Battle of Badr") instead of the corpus's historical events ("Battle of Badr"). A story is a telling, never the event itself (slice 1c kept them apart on purpose). Those claims now point at the historical event. Ten already existed: Badr, Uḥud, the Trench, Khaybar, Muʾta, the conquest of Makkah, al-Ḥudaybiya, the journey to al-Ṭāʾif, the arrival in Madinah, and the Quraysh embassy to the Najāshī. Six were minted, each needs-review:
  - the brotherhood of the Muhājirūn and the Anṣār;
  - the delegation of the Christians of Najrān;
  - the first believers (Ibn Isḥāq's first eight);
  - the affair of the slander (al-ifk);
  - the first call to prayer;
  - "a pledge of al-ʿAqaba (which one, the text does not say)", for two claims whose words do not say which pledge.
  The mapping and the tool are in `ingest/fix_story_events.py`. The story events are unchanged.
- **Bookkeeping flags cleared** (maintainer P9). 20 identity rows were needs-review only because of the slice-1a ID collisions that slice 1d fixed. They now carry the confidence their own evidence gives: exact, or probable for the two label merges (ʿĀʾisha, Makkah). The 12 groups of the 50 Stories stay needs-review, and their question for scholars is now whether each is a real tribe, clan or group the sources name. The tool is `ontology/tools/clear_bookkeeping_flags.py`, and each row's note records the change.
- **Added, not changed.** Read again from the same text by rule (`ingest/sira_derive.py`), all proposed:
  - 537 side claims at Badr and Uḥud;
  - narration formulas on 1,135 links;
  - the speaker (Ibn Isḥāq or Ibn Hishām) on 12,863 claims;
  - a qualifier on 60 claims in passages where Ibn Hishām doubts a poem.
