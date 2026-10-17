# Sky Atlas (new): handover

**What.** Asked for by the maintainer, 17 October 2026: a new and separate Sky Atlas of al-Marṣad, with all the content developed so far and a guided-learning mode, not an extension of the earlier Sky or Sky Atlas. It lives in `atlas/` (see `atlas/README.md`) and follows `docs/handover/sky-guided-brief.md` where it applies. Branch `sky-atlas-new`, from `slice-11a-graph` (main plus the joined graph).

**Content.** The joined graph `build/graph-all.ttl`: 8,373 marks, 15,961 claims, all `proposed`, 0 reviewed. Through `site/observatory/obsdata.py`, unchanged, so statuses, sources and dates match the reader tier.

**Against the brief.**
1. Built from the graph, every string an i18n key, no external request, one file (2.2 MB with the data gzip-packed; the 2 MB site budget does not apply to a prototype island, and the page could load data in parts if it moves into `site/`).
2. H4: the Prophet ﷺ is the light at the centre in every view and never a mark; in Map it hangs above the land, in Book and Time above the scale, so it marks no place, page or date. H5: the Key says the stars are the project's metaphor, not a hadith. T4: generation by brightness only.
3. E3: default order as asked, from `atlas/data/lists.json` (proposed, with sources, matched by display name; the build stops on a name that matches none or several). Other sorts: A–Z, recorded links (labelled coverage), first named in the text. "Order of accepting Islam" is not offered: it is not recorded for most people.
4. X1: dark marks only from recorded claims (37 people); the turning toggle only where a claim says "accepted Islam later" (2). The edge cases of round 4 question 2 are not singled out: nobody is marked without a claim.
5. Guided mode: 192 events in the text's order, 44 dated events, the three journeys, the ten, the 50 Stories, opposition; tours from any record; three depths; next directions at every stop.
6. F14: connection stories appear only once approved; none is, so the page says so. Trace shows each step's claim and source.
7. W6/A2: no AI runs in the page. It chooses routes, cameras and next suggestions by fixed rules; every sentence is a claim with its source or an interface string.
8. W5: logbook and milestones (the learner's own exploring, never a person's rank); a place-centred tour ("Standing at…").

**Decisions to confirm.**
- *The text's order.* An event's place on the spiral is the median milestone of the claims that cite it. Its first mention is often an aside (Uḥud appears in an early genealogy), which put it before the Prophet's ﷺ birth. People and places in the Book view still sit at their first mention.
- *Lineage-only names* (5,554 people with only kinship claims) hang outside the events in the Sky and stay out of the tours (F11). A switch hides them.
- *Trace* never passes through the Prophet ﷺ (linked to almost everyone) or, by default, lineage-only names (F13's spirit; "same clan" wording is not yet added).
- *Recall* never marks an answer wrong: an absent claim is not a false one.
- *Lists*: the four by succession, the ten by the reports of ʿAbd al-Raḥmān b. ʿAwf (Tirmidhī, Manāqib 3747) and Saʿīd b. Zayd (Abū Dāwūd, Sunna 4649); the report numbers need checking against print.

**Known data issues the page makes visible.** Duplicates in the full layer (several al-Zubayr, Hāshim, al-Qāsim…) and kunya-only merges: in ʿAlī's lineage the light appears ten generations up through a merged name. Two Uḥud and two Badr events. These are slice 11a's merge proposals, not page bugs.

**Checks.** `atlas/tests` (11 tests), `atlas/check.cjs` (Playwright, desktop and 390 × 844: welcome, tour, search, record, study depth, lineage, trace, every view, every drawer tab, Arabic, no sideways scroll, no page error, no external request; all pass), the committed page matches a fresh build (byte-identical across hash seeds). All three are steps in `scripts/check_all.sh`.

**Published.** As an Artifact (private until shared); the link is in `pages/README.md`.
