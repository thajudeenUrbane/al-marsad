# Hijrah Night v2: the narrative unit

The experience is about 130 **units** in 10 **acts**. Each act is one file: `acts/actNN.json`.
A unit is one stop of the journey: a place, a moment, people, sourced statements, a camera, and something to do.

## Evidence grades (every statement carries exactly one)

| grade | meaning | needs |
|---|---|---|
| `established` | Agreed by the Qurʾān, rigorously authenticated ḥadīth, or the unanimous early sources | ≥1 source of type `quran` or `hadith`, or ≥2 independent sources |
| `supported` | Narrated in an early source (Ibn Isḥāq/Ibn Hishām, al-Wāqidī, Ibn Saʿd, al-Ṭabarī, ḥadīth collections) and not contradicted | ≥1 source |
| `disputed` | Sources differ, or the chain is weak, or later popular tradition | ≥1 source **and** a `note` naming the disagreement or weakness |
| `reconstruction` | Environment only: terrain, light, distance, season, the look of the land. **Never a person's action, word or feeling.** | `basis` (e.g. "terrain data", "computed distance between gazetteer points") |

Never invent events, speech, feelings or motives. If the sources do not say it, do not write it. Hedges in the source (yuqāl, fīmā dhakarū, zaʿamū) make a statement `disputed` or are stated in the text ("Ibn Isḥāq reports, with the hedge 'it is said', that…").

## Sources

```json
{"type": "ibn-hisham", "sec": "S0680"}                      // the build adds volume, page and OpenITI milestone
{"type": "quran", "ref": "9:40"}                             // surah:ayah or surah:ayah-ayah
{"type": "hadith", "ref": "al-Bukhārī 3905", "grade": "ṣaḥīḥ", "verify": true}   // sunnah.com numbering
{"type": "other", "ref": "Ibn Saʿd, al-Ṭabaqāt al-Kabīr", "note": "…", "verify": true}
```
Cite a ḥadīth number only if you are confident of it; otherwise give collection + chapter and set `"verify": true`. All `hadith` and `other` sources are checked by a scholar before release.

## Unit

```json
{
  "id": "a07-u04",
  "title": "Trackers at the mouth of the cave",
  "kicker": "Day 2 or 3 in the cave",
  "when": {"label": "Rabīʿ al-Awwal, year 1 of the Hijra (622 CE)", "grade": "supported"},
  "place": {"key": "thawr", "note": "optional"},
  "sky": "night | dawn | day | midday | dusk",
  "camera": {"target": "thawr", "dist": 4, "pitch": 28, "heading": 300},
  "lights": [{"name": "The Prophet Muḥammad ﷺ", "role": "prophet"}, {"name": "Abū Bakr", "role": "person"}, {"name": "the trackers of Quraysh", "role": "group-stone"}],
  "route": ["makkah", "thawr"],
  "statements": [
    {"text": "…", "grade": "supported", "sources": [{"type": "ibn-hisham", "sec": "S0686"}]},
    {"text": "…", "grade": "reconstruction", "basis": "terrain data"}
  ],
  "quran": [{"ref": "9:40", "gist": "Meaning in your own words, one or two sentences. Not a translation.", "context": "Why it is linked to this moment, with its grade and source", "grade": "established"}],
  "people": [{"name": "Asmāʾ bint Abī Bakr", "who": "Abū Bakr's daughter, ʿĀʾisha's sister", "here": "Brought food each evening"}],
  "discover": [{"label": "Look toward Makkah", "camera": {"target": "makkah", "dist": 12, "pitch": 20, "heading": 10}, "reveal": {"text": "…", "grade": "reconstruction", "basis": "computed distance"}}],
  "question": {"kind": "predict | recall | reflect", "q": "…", "options": [{"text": "…", "ok": true, "why": "…", "sources": [{"type": "ibn-hisham", "sec": "S0686"}]}]},
  "matters": "One or two sentences on why this stage matters. Interpretive; shown under 'Reflection'.",
  "sections": ["S0686"]
}
```

Rules:
- `place.key`, `camera.target`, `route[]`, `discover[].camera.target` use keys from `data/places.csv`, or `[lon, lat]` only for a wide view with no claim of location, or an **unlocated** key of the form `"~name"` (e.g. `"~amaj"`), which is shown dashed and never drawn on the map. Never invent coordinates.
- `camera.dist` in km: 0.8–3 close, 4–15 local, 30–120 region, 200–500 overview. `pitch` 10–80 degrees, `heading` 0–360.
- `lights`: role `prophet` (the light, never a figure; only the Prophet ﷺ), `person`, `group` (a gathering of believers), `stone` (named, side not drawn), `group-stone` (a group acting against the Prophet ﷺ in this moment, e.g. the watchers, trackers, pursuers), `assembly` (a tribe, clan or crowd named without a side: neutral grey). Never draw a whole tribe or community dark for context, and never an individual: named people with no recorded side are `stone`. No depiction of anyone, ever.
- 4–9 statements per unit, each 1–3 plain sentences. No statement repeats another unit's. Each unit must add something new.
- At least one `discover` per unit where it adds value; a `question` in about half the units (mix predict, recall, reflect; options must be grounded).
- `sections`: every Ibn Hishām section the unit rests on.
- Honorific ﷺ after "the Prophet" or "the Messenger of Allah" once per statement. Arabic names in ALA-LC style as in the claims file.
- English only in committed files; never copy the Arabic running text (licence). Short Arabic names and terms are fine.
