# Places pass brief — the Hijrah route and Makkah, located honestly

Context: README "Standing rules"; lab/beyond-the-graph (N3; "Geography is the bottleneck"); ontology/marsad.ttl (`mrs:Place`, `mrs:geometryState`); ontology/corpus/external-coordinates.csv and external-ids-althurayya.csv; lab/hijrah-night/data/places.csv; docs/handover/maintainer-answers-3.md (T3, S6, P10). Do not read chat history; this file is the brief.

## Build
1. **Certainty grades.** Each point carries a grade: exact (identified site), attested area, approximate, or unlocated; plus its source and licence. Shape it. Unlocated is a valid, displayed state, never a gap to fill.
2. **The pass.** Every place used by a Hijrah scene, and the Makkah places those scenes name: match al-Thurayya (credited, CC BY 4.0 source; our file CC BY-SA, S6) and Wikidata. A trained editor checks each match (P10); doubtful ones go to scholars.
3. **The route.** Record the eleven stops as an order from the text, with no geometry between them. The five unlocated stops (Amaj, Qudayd, Marjiḥ, Dhū Kashr, Dhū Salam) stay unlocated unless a reviewed source locates them.
4. **Contested locations.** Ghār Thawr, the lodging at Qubāʾ (two reports) and any disputed stop go to the scholars as a short batch with both readings shown.
5. **Replace** the prototype's name-matched points with graded points from the graph.
6. *(Cuttable.)* Linked Places export of the graded places.

## Done when
Every place in the Hijrah scenes has a grade and a source; the world draws dashed absence for unlocated stops and no road anywhere; checks pass in `scripts/check_all.sh`. Handover `docs/handover/places-pass.md` (≤60 lines) with counts by grade.

## Rules
No pixel without provenance; never invent coordinates; never draw a road the text does not give; credit every gazetteer; no model names or IDs in the repo.
