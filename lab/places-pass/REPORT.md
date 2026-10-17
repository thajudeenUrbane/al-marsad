# Places geolocation pass (proposed, lab only)
Run `python3 lab/places-pass/build.py` (add `--offline` to use only `cache/`). Output: `places-proposed.csv`, one row per (place, candidate), with evidence, region fit, candidate grade and a place-level grade.
Sources: al-Thurayya `places.geojson` (CC BY 4.0, 2,518 features) + one batched Wikidata SPARQL lookup on the Arabic forms (272 items with P625, cached) + the links already in `ontology/corpus/external-coordinates.csv`. No coordinate is invented: each lat/lon is a gazetteer row; places without one stay `unlocated`.
## Coverage (236 places, kind=place in identity.csv)
| grade | before | after |
|---|---|---|
| exact | 5 | 11 |
| probable | 5 | 42 |
| possible | 0 | 61 |
| unlocated | 226 | 122 |
Located at exact/probable: 10 -> 53 (22%); with possible: 114 (48%). Weakest classes: route_node 39/54 unlocated,
well 13/15, valley 15/22, cemetery 3/3 (micro-toponyms absent from both gazetteers).
Grading: exact = existing exact link, or two systems agree within 5 km on both Latin and Arabic name, no homonym.
probable = Latin+Arabic match or two systems agree, in expected region. possible = one-script match, or a
homonym in region. Out-of-region matches are kept as rows but graded unlocated ("homonym, not used").
Region plausibility: Arabia by default (Hijaz box ranked first); Sham/Iraq/Jazira/Iran/Anatolia/Habasha only for
labels the text puts there (list `ELSEWHERE` in build.py). Note: Badr, Makka, al-Madina drop from exact to
probable because an in-region homonym exists (Wikidata "Badr" items, a Madina region item); review and keep.
## Hijrah route stops
| stop | status |
|---|---|
| ʿUsfān (and dup. ʿUsfān (2)) | probable, al-Thurayya USFAN_394E218N_S, Latin+Arabic |
| Amaj (and Amaj (2)) | unlocated (not in either gazetteer) |
| Qudayd | possible, matched only via an Arabic alternate of KHAYM_395E223N_S; check |
| Marjiḥ Dhū al-Ghaḍwayn, Dhū Kashr, Dhū Salam | unlocated |
| al-ʿArj (and al-ʿArj (2)) | possible, homonym: ARJ_392E238N_O vs a second in-region ʿArj |
| Qubāʾ | possible, homonym: QUBA_395E244N_S (Medina) vs QUBA_416E227N_S |
| Wādī Rānūnāʾ | unlocated (a wadi inside Medina; place by hand from Qubāʾ) |
| al-Jiʿrāna | unlocated (Arabic form bal-Jiʿrāna; no gazetteer hit) |
| Ghār Thawr | exact, Wikidata Q6025084 (existing link) |
## Key sites
Badr probable (BADR_388E237N_S; Yemeni Badr rejected by region) · Uḥud exact (Q1436040) · Khaybar probable
(KHAYBAR_392E257N_S, Latin only) · Tabūk possible (homonym, 8 km spread; town itself is uncontested, upgrade by hand) ·
al-Ḥudaybiyya unlocated (no gazetteer match; modern al-Shumaysī is a scholar call) · Khandaq has no place entity:
it is an event; the trench line must be drawn relative to al-Madīna, not geocoded.
## Hardest cases for scholars
1. Hijrah coastal route micro-toponyms (Amaj, Marjiḥ, Dhū Kashr, al-Jadājid, al-Ajrad, Dhū Salam, al-ʿAbābīd,
   al-Fāja): only an ordered sequence between ʿUsfān and al-ʿArj is defensible, not points.
2. Homonyms: ʿArj, Qubāʾ, Kharrār, Ṣafrāʾ, Nakhla vs Nakhla al-Yamāniyya, Buḥrān/Maʿdin, Badr (Hijaz vs Yemen).
3. Duplicate entities with "(2)" labels and near-duplicates (Thaniyyat al-Marra/al-Mara, Ṣuḥayrāt/Ṣukhayrāt
   al-Yamām, Mosul/al-Mawṣil, Yemen/al-Yaman, Madinah/al-Madīna): merge before geolocating.
4. Sites inside Makka/Madina (Dār al-Nadwa, Saqīfa, Baqīʿ, Shiʿb Abī Ṭālib, Naqb Banī Dīnār): need a city-plan
   layer, not a gazetteer; al-Thurayya has none of them.
## Drawing certainty in the world
- exact: a pin plus a small ring, radius 0.5 km (site) / 2 km (town); solid stroke.
- probable: ring radius 5 km, solid but lighter; label in normal weight.
- possible: ring 15-25 km (the cluster spread, at least 15), dashed; when homonyms exist draw every in-region
  candidate as a faint dashed ring with a connecting "or" glyph, never pick one silently.
- unlocated: no pin. Place the name along the route segment between its located neighbours (ordered stops),
  or in a margin list for the region; use italics and a "?" marker.
