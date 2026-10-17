# Sky guided-learning brief — the Sīra as a world to explore

Context: README "Standing rules"; docs/00-vision.md and docs/04-visualization-architecture.md (the light, the encoding contract); docs/handover/maintainer-answers-3.md (W1, W2, W5, W6, H4, H5, T4, E3, E6, X1, F11, F14); branches `sky-atlas` and `sky-observatory` (the Sky and the Sky Atlas as built). Do not read chat history; this file is the brief. Build on the joined graph of slice 11 once it lands; until then, on main's graph.

## The maintainer's direction, in short
Exploration first (W1): the graph should be engaging, intuitive and layered, from simple to advanced, so that scholars and the community are drawn in. The Sky Atlas is the view that grows (W2). It needs a **guided-learning mode across the whole graph**: people should be able to enter a period, place or event, look from any angle, and be guided from one discovery to the next (W5, W6), not only answer questions they already know to ask.

## Build
1. **Bring the Sky Atlas into the repository** as `site/sky/`, merging the work on `sky-observatory` and `sky-atlas`. It is built from the graph like the Observatory. Every string is an i18n key, there are no external requests, and the 2 MB budget holds (data loaded in parts if needed).
2. **The light (H4).** The Prophet ﷺ is the light at the centre, never a node, in every view. Change the Observatory to match. The stars image is our metaphor and is never quoted as a hadith (H5). Generation is shown by brightness only (T4).
3. **Order of people (E3).** The default order is the Prophet ﷺ, al-Khulafāʾ al-Rāshidūn, the ten promised Paradise, then by number of recorded links. Other sorts: A–Z, order of accepting Islam where recorded, recorded links. Plus search. "Recorded links" is labelled as coverage in the sources, never rank. The membership lists (the four, the ten) come from a reviewed list file with its source, not hard-coded IDs.
4. **Opponents and the turning (X1, E3).** Those recorded as fighting against the Prophet ﷺ (slice 11's side claims) are drawn as dark marks, never stars or light. Those who died as disbelievers come last in lists. A time toggle turns a dark mark into a star at the person's recorded acceptance of Islam. Draw only what the claims state. A person with no recorded side or conversion stays neutral and is listed as "not recorded", never guessed. Edge cases (Abū Ṭālib, the munāfiqūn, people whose Islam is disputed) wait for the scholars' ruling (maintainer-answers-3, round 4 question 2) and are shown neutral until then.
5. **Guided mode.** A guide walks the camera through every documented event and journey (E6: all Seerah events, starting with the listed journeys). At each stop it shows who was there, where, what is recorded, and the source, then offers next directions: people, places, earlier and later events, connection stories. Three depths (Discover, Study, Research), simple first.
6. **Connection stories (F14).** Claude proposes candidate paths, and a scholar writes or approves each story. Only approved stories appear. Each says what the text states and what the graph only connects.
7. **AI help (W6).** Within the standing rules: AI may choose the route, the camera and the next suggestion, and may turn a learner's question into a query (A2: after published adversarial tests). It never writes a fact. Every sentence a learner reads comes from a claim or an approved story, with its source.
8. **Later, kept in mind (W5):** quests, discovery milestones and achievements, without compromising accuracy. A place-centred mode, standing at Badr or in Makkah and seeing who was there and when.

## Done when
The Sky in `site/sky/` builds from the graph. Guided mode covers the listed journeys and every dated event. The opponent and turning toggles follow only recorded claims. A Playwright check passes at 390×844 and on desktop, with no external requests. Handover `docs/handover/sky-guided.md` (≤60 lines), with screenshots of the guided mode.

## Rules
No pixel without provenance; no depiction; AI never asserts; computed ≠ significant; never hard-code entity IDs; no model names or IDs in the repo.
