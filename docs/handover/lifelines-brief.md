# Lifelines brief — each person's life as a parallel line

Saved as given on 15 October 2026 (branch `lifelines`), with the session-only setup lines left out. Do not read chat history; this file is the brief.

## Read first
README.md "Standing rules"; docs/04-visualization-architecture.md (§3 visual encoding contract — follow it; "no interpolation across unknowns"); docs/05-ux-architecture.md (§2 verbs, §9 accessibility, §10 orientation); docs/06-scholarly-methodology.md (§7 computed vs significant, §10 red lines incl. "no fabricated precision"); docs/13-platform-direction.md (D3: dates always dual, uncertainty shown); docs/handover/maintainer-answers-1.md and maintainer-answers-2.md; docs/handover/slice-2a.md (site/display.py has the date/name display rules: import it).

## The maintainer's idea, in his words
"Time based. Should have a view that each person's life as parallel lines. Each line is connected by the lines of incidents on their age's length. E.g. Abū Bakr al-Ṣiddīq's line length is 63 units because that was his age. He was 2–3 years younger than the Prophet ﷺ. So the connection between them should be connecting nodes that appear at the age of each of them. We require everyone's line like this. That gives a better insight in historical reading." (Precedent: Joseph Priestley's Chart of Biography, 1765.)

## Brief — the Lifelines view
A single self-contained page `site/dist/lifelines/index.html` (inline CSS/JS/data; no external requests; ≤2 MB; system fonts) built by `site/lifelines/build_lifelines.py` (standalone; do NOT edit site/build.py or other site files). It must also work when published on its own as one HTML file.
1. **Lines:** one horizontal line per person, from birth to death. Two alignments with a toggle and a smooth morph between them (instant under prefers-reduced-motion):
   - "By date": all lines on one calendar axis (Gregorian first, Hijri beside it). An event is a vertical connector across everyone who took part, and the point on each line is that person's age at the event.
   - "By age" (the maintainer's description): every line starts at 0 = birth; an event connects the points at each participant's own age (slanted connectors), so you see e.g. "at the Hijra, the Prophet ﷺ was N and Abū Bakr N−2".
   - A units toggle: lunar (Hijri) years vs solar years. Classical sources count ages in lunar years (63 lunar ≈ 61 solar). Label which unit is shown.
2. **Data, never invented:** use only dates and ages that are recorded with a source:
   a) dates recorded in build/graph.ttl (few today);
   b) proposed external dates from Wikidata: another agent is writing ontology/corpus/external-dates.csv on branch slice-5-links (canonical_id, QID, birth/death, value, precision, calendar model, match_confidence, status proposed). Read it with `git fetch origin slice-5-links && git show origin/slice-5-links:ontology/corpus/external-dates.csv` (it may appear later: build with what exists, re-check before finishing). Use only exact/probable matches; show needs-review ones only if the visitor switches them on;
   c) birth/death/age claims from Ibn Hishām: another agent is extracting them on branch slice-4-ingest (ingest/claims/ibn-hisham.jsonl and ontology/corpus/ibn-hisham*.ttl); read them the same way when they appear.
   Every line end and every age says where it comes from (Wikidata QID, Ibn Hishām passage, graph claim) and that it is proposed, not reviewed. Ages are COMPUTED from proposed dates: label them "computed". Where sources disagree, draw the range, not one value. Precision is honoured: a year-precision date is a fuzzy segment, never a point; an unknown birth or death leaves an open, fading end, never a guessed one. People with no sourced dates go on a labelled "no dates recorded yet" list, not on the chart.
3. **Connectors:** from events with a recorded date and their recorded participants (participations and assertions in the graph). Tap a connector: the event, its date and source, everyone on it with their computed age, each claim's status. Tap a line: the person's dates with sources, events along their life, and a link to their reader page (/person/<id>/).
4. **Order and grouping:** by birth (default), by generation (ṭabaqa), by family or tribe where recorded; a filter for one event's participants or one person's circle (e.g. "the people of Badr", "around Abū Bakr"), found by label lookup, never hard-coded IDs. No ordering by importance or any computed significance.
5. **Encoding (doc 04 §3):** hue = entity type only; dashed/textured = proposed, not reviewed (today everything: say so in a calm banner and the legend); no information by colour alone. The Prophet ﷺ's line is named with ﷺ and never emphasised by a metric. No figurative depiction.
6. **Accessibility:** a table alternative (person, born, died, source, age at each event shown); keyboard reachable; touch pan/pinch on phones (390×844 must work); orientation: "showing N of M people", reset/home.
7. All UI strings in site/lifelines/i18n/en.json (inlined); CSS logical properties only; a deliberate dark look is fine (set every colour explicitly, color-scheme: dark).
8. **Tests:** site/lifelines/tests (unittest: no person drawn without a sourced date; lunar/solar age arithmetic; year-precision dates drawn as ranges; connectors only at recorded event dates; no hard-coded IDs) and a Playwright check (renders, zero external requests, ≤2 MB, toggles work, table alternative non-empty).

## Milestones
(M1, push as soon as it works) "by date" lines + connectors + tap details + banner/legend + table, with whatever sourced dates exist; (M2) "by age" alignment + morph + lunar/solar toggle; (M3) grouping/filters + needs-review toggle + Ibn Hishām ages. Push after each.

## Scope
site/lifelines/** (new), docs/handover/lifelines.md (≤60 lines; this brief as docs/handover/lifelines-brief.md). Other agents are working on site/ (search), site/observatory/ (graph view), site/interactive/ (timeline/map pages), learn/, ask/, review/, ingest/, CI: do not edit their files.

## Project rules
AI never asserts; never upgrade a status; never invent names, dates or ages; no model names or IDs in any repo file; never hard-code entity IDs.

## Finish
1. Checks: build_graph CONFORMS; the builder; the unittest suite; the Playwright check.
2. Commit messages end with the attribution lines given for the session.
3. At the end: rebase on origin/main; rebuild with the latest dates from the other branches; re-run checks; commit; push (`--force-with-lease` only on this branch after a rebase). Never push to main, never open a PR.
4. Report: branch + commit hash; a short summary (how many people have lines, from which sources, page weight); exact verification commands and results; what the data cannot show yet.
