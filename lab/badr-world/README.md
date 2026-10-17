# Badr world (lab prototype 2)

A second night world on the Hijrah Night engine (`lab/hijrah-night/`): the expedition of Badr
walked over real Ḥijāz terrain, built only from claims of the full-book Ibn Hishām pass
(`ingest/claims/ibn-hisham-full.jsonl`) and the slice 11a side claims
(`ingest/claims/ibn-hisham-full-derived.jsonl`, `t == "side"`, event "Battle of Badr").

Drawing rules: the Prophet ﷺ is the warm light, never a figure. A person listed with him at
Badr (Ibn Isḥāq's list of the Muslims present) is a small light and becomes a star in "Your sky".
A person listed among the idolaters slain or captured is a dark stone, never a star.
Anyone with no side claim stays a grey stone (neutral), never a star.

## Chapters (10, 43 sections)
1. Abū Sufyān's caravan (S0897-S0898) · 2. Quraysh go out (S0904-S0906)
3. The march out of Madinah (S0909-S0912) · 4. The road to Badr (S0913-S0918, order quiz on S0914)
5. At the water of Badr (S0919-S0925) · 6. The shelter and the ranks (S0926-S0940)
7. The duels (S0932-S0933) · 8. The fighting (S0937-S0948)
9. The slain and the well (S0949-S0953, predict quiz) · 10. The captives and the return (S0954-S0960)
Every quiz answer and distractor is a claim (the build's `quiz()`), shown with its citation.

## Counts (current build)
448 claims shown (story, family, chains, sides); people drawn per chapter: 25 with,
37 against, 34 neutral. Places: 8 al-Thurayya points (al-Madīna, Badr, Makkah, Dhū al-Ḥulayfa,
Malal, al-Sayāla, al-Rawḥāʾ, al-Ṣafrāʾ), name-matched for this prototype; the other 18 stages
of the road are named but not drawn.

## Build
    python3 lab/badr-world/build.py      # writes lab/badr-world/index.html
Checked in headless Chromium (SwiftShader): all 10 chapters, no page errors (`screenshot.png`).

## Known gaps
- Name variants split one person: "Muʿawwidh b. al-Ḥārith" (no side, grey) vs "Mu'awwidh ibn Afra'"
  (with); "Abū Jahl b. Hishām" vs "Abū al-Ḥakam b. Hishām". Entity resolution would fix this.
- People in the text but not in a Badr list (e.g. ʿUqba b. Abī Muʿayṭ, ʿIkrima, Abū Sufyān,
  ʿAbd al-Raḥmān b. Abī Bakr, whom the text puts "with the polytheists") stay neutral by rule.
- Many Badr sections have few or no claims (S0900-S0901, S0908, S0911, S0916, S0926, S0928);
  the roll-call lists (S1015-S1147) feed sides but are not chapters. News reaching Makkah
  (S0956-S0957) is not a chapter yet.
- al-Sayāla / al-Rawḥāʾ / al-Ṣafrāʾ points are name matches, not reviewed locations.
- Dead Hijrah-specific branches (hosts, council, Qubāʾ) remain in template.html, unused.
