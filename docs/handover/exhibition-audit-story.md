# Exhibition audit: the story he hears (24 Oct 2026)

Read-only audit, slice "the story he hears, and what he will ask that no page answers". Branch `claude/exhibition-scholar-presentation-72dff5`. Only this file was written. Paths are relative to the repository root.

**What I read:** README.md; pages/marsad.html, build-with-us.html, road-ahead.html, README.md, and the numbers in reviewers-brief.html; docs/REVIEWERS-BRIEF.md; docs/09, 13; docs/06 (3.1, 9, 10); docs/10 and 11 (headings and searches); docs/BENEFITS-FOR-STUDIES-AND-DAWA.md (head); atlas/README.md; expeditions/README.md; lab/hijrah-night-v2/README.md; heads of lab/badr and lab/badr-world READMEs; lab/phase-a-plan/PLAN.md; lab/beyond-the-graph/index.html (text); docs/handover/maintainer-answers-3.md; the PR #33 scholar guide; the work board on `coordination`.
**What I did not do:** open any page in a browser, test any artifact link, or recompute any astronomy. "To verify" means "read in a file, not tested".

## Read this first

1. **The front pages are September; the product is October.** pages/marsad.html, build-with-us.html, road-ahead.html and docs/REVIEWERS-BRIEF.md describe "35 Companions, six events, nothing has been built". The Sky Atlas holds 8,373 marks and 15,961 claims. road-ahead.html even argues "we should not rush to bring in historians yet", which is the opposite of today's ask. **Do not send or show these four today.**
2. **The story he should hear lives in files that are not pages:** the Atlas, the expeditions, Hijrah Night v2, PLAN.md, the Beyond-the-Graph strategy. None of them says who is behind this, what it costs, who decides, or what you want from him.
3. **No public page names a person, an institution, a contact, a board or an ask.** A search of the four pages for a name, e-mail, WhatsApp or "contact" finds nothing. build-with-us ends "then let's talk" with no way to talk.
4. **One direct contradiction on the most sensitive scholar question (credit).** "Recorded under your name, permanently" (marsad.html, REVIEWERS-BRIEF) against "credited to the review board, not to you by name, unless you agree to be named later" (PR #33 scholar guide). Decide before he asks.
5. **Three things a scholar will poke in the demo:** grades such as "established" on AI-drafted statements (against red line 2, "no AI grading of authenticity"); "7,867 people" that are not yet de-duplicated; computed dates that disagree with the received dates (Badr, Thawr to Qubāʾ).
6. **What is strongest:** the project's own honesty (README banner, the public correction of 12 Sep, "The system flags. You rule."), the no-depiction rule, and a scholar ask that is small and specific (PLAN.md budgets about 19 to 20 scholar-hours for the whole of Phase A).

---

## Part 1. Numbers that are stale or disagree

Current figure first, then where the old one lives. "Entries" matters: say it aloud.

| # | Item | Stale or disagreeing figure (file) | Current figure | Source of current figure |
|---|---|---|---|---|
| 1 | People and marks | "35 Companions" (README gen-1; pages/build-with-us.html; pages/road-ahead.html); "57 people" (README seed incidents); "171 people" (README stories-50) | **8,373 marks = 7,867 person entries, 208 events, 236 places, 50 stories, 12 groups.** Entries are not de-duplicated | atlas/README.md |
| 2 | Claims and triples | "1,804 triples" (pages/marsad.html header, README); "1,804 statements" (pages/reviewers-brief.html); gen-1 "1,627 triples"; BTG "15,019 sourced relations from 1,788 sections" | **15,961 claims, every one proposed** (whole joined graph). 1,804 is the September ontology layer. BTG's 15,019 is probably the Ibn Hishām layer alone: to verify. Name the layer whenever a number is spoken | atlas/README.md; lab/beyond-the-graph/index.html |
| 3 | Events | "six real dated events" (build-with-us, road-ahead, README gen-1) | **208 event marks, 44 with a recorded date, 192 in the Sīra tour.** Hijrah Night v2: 150 stages | atlas/README.md; lab/hijrah-night-v2/README.md |
| 4 | Who was at Badr | Atlas tour "the people of Badr: 439" against expedition "the 314 (321 found)" | Two different questions (the graph's whole Badr cast, probably both sides, against Ibn Isḥāq's list of the 314). He will hear both within ten minutes. To verify what 439 counts, and have the sentence ready | atlas/README.md; expeditions/README.md |
| 5 | Documents | "Corpus 13 documents" (pages/marsad.html); README reading table stops at doc 12 | **14 numbered documents (00 to 13; doc 13 is 15 Oct)** plus REVIEWERS-BRIEF, BENEFITS-FOR-STUDIES-AND-DAWA, CHANGELOG-data | `ls docs`; docs/13-platform-direction.md |
| 6 | Self-critique count | "30 weaknesses" (README table; pages/marsad.html) | docs/11 has 31 entries. #31 was added 12 Sep after an outside reader. Not an error: say "thirty in the first design, a thirty-first found by an outside reader". It is an honesty asset | docs/11-self-critique.md; README line 38 |
| 7 | Hijrah night review load | PLAN.md W0 "timed review of the 277 prototype claims"; A3 and ENG-4 "about 300 claims"; scholar total "about 19 to 20 h" | v2 has **863 statements and a 377-item REVIEW-CHECKLIST**. The budgeted scholar time covers about a third of it. Re-estimate before quoting hours to him | lab/hijrah-night-v2/README.md; lab/phase-a-plan/PLAN.md |
| 8 | Places with coordinates | atlas/README "6 places" | BTG says "10 of 236". Pick one (Map and Globe are thin either way) | atlas/README.md; lab/beyond-the-graph/index.html |
| 9 | Phase and dates | README "Phase 0 ... September 2026"; road-ahead "step one of ten", no dates; docs/09 Q1 to Q4; BTG Phases A to D | **PLAN.md is the only dated plan: Phase A, Mon 2 Nov 2026 to Sun 24 Jan 2027, Gate A in week 12.** Pre-phase W0 is 19 Oct to 1 Nov (today is inside it) | lab/phase-a-plan/PLAN.md |
| 10 | Money | pages/marsad.html and docs/09: "~40% engineering, 30% scholarly labour ... If scholarly labour drops below a quarter, the project has quietly become a visualization company" | BTG year one: **lean $80k to 125k, full $200k to 335k.** Scholar stipends $8k to 12k (lean) and $15k to 30k (full), about 8 to 10% at the midpoints (my arithmetic), against the project's own floor of 25%. Hosting under $600 a year (agrees with docs/13 D4, under $50 a month) | lab/beyond-the-graph/index.html; docs/09; docs/13 |
| 11 | Rules overridden but not amended | docs/09 kill criterion 4 (cross-tradition board) and the review-first phasing | Round 3 D1 (one declared board is fine if every page says so) and W1 (exploration first) reverse them. docs/09 still shows the old rules. He may read docs/09 | docs/handover/maintainer-answers-3.md |
| 12 | Credit for reviewers | "recorded under your name, permanently" (pages/marsad.html; docs/REVIEWERS-BRIEF.md) | PR #33 guide: credited to the review board, not by name, unless the reviewer agrees later. Reviewer is an ID, not a name | docs/pilot/scholar-guide.md on `origin/fixes/pilot-and-corrections` |
| 13 | Status wording | Atlas welcome line says "all proposed"; Atlas lists say "awaits the scholars' review"; expeditions say "Nothing here is scholar-reviewed" | Round 3 G1/G8: public pages say nothing about being reviewed; status shows only in Study and Research. Fine for a private showing; conflicts with a public launch | atlas/i18n/en.json; docs/handover/maintainer-answers-3.md |
| 14 | Housekeeping | Work board lists PR #32 (learning lab) as in review; published Atlas artifact is dated 17 Oct | PRs #31 and #32 are merged (origin/main 3be477b). To verify the published Atlas shows today's counts; else use the local atlas/index.html | git log origin/main; pages/README.md |
| 15 | "Ten authors" | lab/hijrah-night-v2/README.md "Ten authors each read the Arabic" | These are ten AI drafting passes (round 3 G3), not ten people. A scholar will read "authors" as people. Say "ten AI drafting passes" | lab/hijrah-night-v2/README.md |

---

## Part 2. Claims a scholar could challenge, or that overstate what is built

Ordered by how likely he is to hit them. "Say instead" is wording the files already support.

1. **"No existing system exploits this" (README).** docs/10 itself says Hadith-Viz and the isnād-network literature "got there first" and lists what "should not be claimed". docs/10 names Shamela, Turath, Sunnah.com, Sanadset, Hadith-Viz; a search found no Arabic-language takhrīj or ḥadīth-database tools (for example Dorar.net or Jawāmiʿ al-Kalim). He may name one; to verify the gap. *Say instead:* "We found no system that puts the report, its chain, the grading, the place and the date in one record. The prior-art list is docs/10; tell us what we missed."
2. **pages/marsad.html capability matrix** fills every column for al-Marṣad "(proposed)" while the page footer says "Nothing here has been built". It reads as boasting and is also out of date in the other direction. Do not show the table.
3. **"7,867 people".** These are name entries. atlas/README "Known limits": one person can appear under several entries and a kunya-only merge can join two people. He will search "Abū Bakr" and see more than one. *Say:* "7,867 name entries; de-duplication is the next step."
4. **"The whole Sīra as a sky."** It is the Sīra as Ibn Hishām tells it (OpenITI machine-readable text), plus small layers (11 recorded chains, 50 Stories). No al-Wāqidī, Ibn Saʿd, Ṭabarī or ḥadīth corpus. *Say:* "the Sīra as Ibn Hishām tells it", every time.
5. **Grades on AI drafts.** Hijrah Night v2 gives every one of 863 statements a grade (established 140, supported 537, disputed 134, reconstruction 52). The drafts are AI (round 3 G3). "Established" includes "authenticated ḥadīth", while ḥadīth references were "cited from memory ... to verify" (README of the lab). docs/06 red line 2 is "No AI grading of authenticity"; the demo's own rule is "a grading, made by a named person". *Say:* "These are evidence classes an AI drafted for scholars to accept or change. None is accepted." Consider showing the "to verify" marks first.
6. **Qurʾān cards "in our own words"** (Hijrah Night v2). He may check one verse. Choose the card you show in advance; say the wording is for scholar edit.
7. **Brightness and dark marks.** The Atlas lights people by recorded generation or distance in narration; dark marks go to people a claim records as fighting or opposing the Prophet ﷺ (37); "the ten" tour follows the order of a report. Red line 5 is "No computed ranking of persons by religious significance". *Say:* "Brightness is distance in the record, never rank" (expeditions rules: "coverage, never rank"). The 37 rest on AI-proposed claims. **Before the meeting, open the opposition tour and read the 37 names**; if a later Companion is among them, know it first.
8. **AI-written text inside the sky.** README says the 50 Stories text "was generated by AI ... must not be cited". The Atlas draws the 50 Stories on its outer ring and runs a 50 Stories tour. Round 3 G2 says they are replaced gradually and kept as an AI draft. *Say that.*
9. **Computed dates that disagree with the received dates** (expeditions): no candidate gives Friday 17 Ramaḍān at Badr; none gives Monday 12 Rabīʿ I for Thawr to Qubāʾ. The crescent rule is a stand-in (30 hours past conjunction, 8 degrees up) and all dates are Julian. The README frames each as "a question for the scholars, never a correction". Keep that framing out loud. Date trap: the popular "13 March 624" for Badr is a Gregorian date; by my quick arithmetic that day is a Saturday (not tested in the tool), so do not let it become a weekday argument.
10. **"Tap on any moment and watch the real evidence unfold"** (build-with-us). The demo is one event and eight people. "Real" means real sources, still unreviewed. *Say:* "one event, eight people, the real citations."
11. **"We need historians ... then let's talk" next to "we should not rush to bring in historians yet"** (build-with-us against road-ahead). The two pages disagree with each other and with today.
12. **docs/REVIEWERS-BRIEF.md "It is not built yet" and "almost none" of the historical data.** True in September; now it undersells and will contradict the screen he is looking at.
13. **"Standing at Badr"** is present-day terrain (lab/badr: 22 km square; Hijrah Night v2 lists close-up terrain at about 1 km per cell among its known gaps; the expeditions README gives no resolution, to verify). He will not see the ancient wadi or the wells. *Say:* "present-day ground; the ancient ground is a question for you."

---

## Part 3. What a leader will ask that no page answers

For each: what the files let you say today, and the gap.

1. **Who is behind this?** *Files:* README names the repository owner and says the corpus "was compiled with AI help". The work board shows several Claude sessions building in parallel. Partner, donor and hiring drafts are "kept out of the repo". *Gap:* no name, bio, institution or contact on any page. *Say:* who you are, that it is built by one maintainer with AI help, who (if anyone) has already looked at it.
2. **How are scholars' decisions recorded?** *Files:* reviewer is an ID, not a name; three answers (ACCEPT, REJECT, NEEDS DISCUSSION); a source is required to accept a story claim (PR #33 guide). Decisions export as `marsad-review-decisions` v1 and import with `review/import_decisions.py` (the expeditions `#desk` dry run accepted an exported file unchanged). A claim moves `proposed`, `under review`, `accepted`. Grading is an act by a named agent (docs/06). *Gap:* no page shows it end to end; the guide is in open PR #33 and does not say how long a batch takes. The pilot's first batch is the AI-written 50 Stories claims, the second is "same person?" merge questions, not the Hijrah.
3. **Who has the final say?** *Files:* P6 (until the board exists both notes stay and the claim stays under review); P7 (a reviewer's change of mind goes through the board); D1 (one declared board is fine if every page says so); docs/06 section 9 (cross-tradition board, separation of powers, forkability, institutional custodianship). *Gap:* **no board exists, and no page says which tradition the first declared board stands in** (docs/13 lists multi-tradition as open). *Honest answer today:* "The board decides. It does not exist yet. Naming it is part of what I want your advice on."
4. **Will we be named?** The two documents disagree (Part 1, row 12). Pick one answer; the PR #33 wording is the safer start.
5. **Governance and red lines.** *Files:* docs/06 section 10, ten red lines; README "Standing rules" (five); REVIEWERS-BRIEF "six refusals"; docs/09 kill criteria. *Gap:* three overlapping lists and no single page. *Say the four that matter to him:* no depiction of the Prophet ﷺ, his family or the Companions (the Prophet ﷺ is the light at the centre, never a figure); no fatwā or ruling; no AI grading of authenticity; no contested matter shown as settled. Add: everything is forkable.
6. **Is AI writing the history?** *Files:* README banner; round 3 G3 ("Claude drafts, a scholar edits and approves, and the AI part is said openly"); lab README "How it was made"; AI glosses labelled in the Atlas. *Gap:* said in many places, never on one. *Say it in the first minute.*
7. **Which tradition, school or ʿaqīda?** *Files:* grading is tradition-scoped; D1 allows one declared board first. *Gap:* the first board's tradition is not stated anywhere; the multi-tradition question is open in docs/13.
8. **What does it cost and who holds the money?** *Files:* BTG year one, lean $80k to 125k or full $200k to 335k; hosting under $600 a year; round 3 M2 (what year-one money buys), M3 (quarterly totals by category), M4 (a scholar is the second keyholder), M1 (the trust's country decided later, after consultation); docs/13 open question on the legal entity. *Gap:* no single figure on any page; the scholar share (about 8 to 10%) is far under the project's own 25% floor (Part 1, row 10). He may spot that.
9. **What is the timeline?** *Files:* PLAN.md (12 weeks, 2 Nov to 24 Jan, Gate A at week 12); round 3 W3 (year-one goal is a public launch with the board named). *Gap:* no page carries it; road-ahead has ten steps without dates.
10. **What exactly do you need from me?** *Gap: nowhere.* The files do give concrete candidates (Appendix has a draft one-pager):
    - **Scholars:** introductions to one scholar for a timed review in W0 (by 1 Nov), then at least two for Gate A criterion A3 (a full chapter reviewed, mid-December). PLAN.md total scholar time is about 19 to 20 hours across Phase A.
    - **Direction:** his steer on the questions in the round 4 sheet (due W1, 2 to 8 Nov): the source line, how to classify opponents (the dark marks), the domain; and which tradition the first board declares.
    - **Funding or home:** advice and introductions on a custodian and legal form (M1, docs/13), and on the partner list in BTG (OpenITI, Usul.ai, GTAF, Ithra, Quran Foundation). Partner, donor, funding and hiring drafts are kept outside the repo (work board); bring what is ready.
11. **Where do the texts come from, and may you use them?** *Files:* OpenITI machine-readable Ibn Hishām text (git-ignored cache); S1 "keep pointers and short phrases, and write to OpenITI about permission and partnership"; LICENSING.md. *Gap:* whether OpenITI has answered is not in the files (to verify). Which print edition is not settled (S2: the Cairo edition once a scholar checks it).
12. **What if you stop?** *Files:* forkability and institutional custodianship (docs/06 section 9); everything is in git. *Gap:* one maintainer.

---

## Part 4. The walk: asset, sentence, 30-second move

Pre-open these before he sits down: demo/index.html; atlas/index.html (local file, one self-contained page, nothing fetched); the expeditions server (`python3 -m http.server 8770 --directory expeditions/dist`, then http://localhost:8770); lab/hijrah-night-v2/index.html (a built single page, 860 KB). If a published artifact is wanted instead, the links are in pages/README.md; they are private until shared and the Atlas one is dated 17 Oct.

**Step 1. The one idea.** *Asset:* demo/index.html, the note "The system flags. You rule. This is the whole design in one field", and the README banner "Draft: not reviewed by scholars". Do not use the "Nūr and Nujūm" section of pages/marsad.html as a hero without checking it: docs/11 #31 records that the Nūr/Nujūm diagram once asserted a population gradient with no warrant, and README line 38 records the correction (12 Sep). Whether the September page carries the correction is to verify.
*Must land:* "History here is a result, not a fact: every statement is a report with a chain, graded by a named person, and the system flags while you rule."
*Demo (30 s):* open the demo, click a report, read "There is no grade field on this report. There is a grading, made by a named person, in a named book, at a named page."

**Step 2. One event, all the way down.** *Asset:* demo/index.html (the Thawr event, eight people, morph network to generations to geographic).
*Must land:* "Event, people, report, grading, chain: every layer is inspectable, and where only a scholar can rule the field is left empty."
*Demo (30 s):* open the chain view of one report and read "is this chain connected? EMPTY, awaiting a scholar" (the computed contact check is shown, then stops). Then: "This same ladder sits under every claim on the next screen."
*Watch:* it is one event, not the project. Check on screen that the generations note no longer says "narrowing funnel" (README line 38; demo line 565); to verify.

**Step 3. The whole Sīra as a sky.** *Asset:* atlas/index.html (README: 8,373 marks, 15,961 claims, all proposed).
*Must land:* "Everything Ibn Hishām tells, as one sky, the Prophet ﷺ as the light at the centre, and every mark still marked proposed."
*Demo (30 s):* read the welcome count; start the tour "the Sīra as Ibn Hishām tells it (192 events)" and let two stops play; at one stop show "who was there and who was recorded absent" (the broken coral ring). Optional: open "the ten" tour and let him test it against what he knows. Pre-run it once so there are no surprises.
*Avoid:* Map, Globe and Time (6 or 10 places have coordinates, 44 events have dates); searching "Abū Bakr" (duplicates); the Arabic interface unless you say it is a draft.

**Step 4. Standing at Badr under the computed sky.** *Asset:* expeditions/dist, expedition "The eve of Badr" (slug `badr`; the hash looks like `#x-badr-0`, to verify). Fallback: lab/badr/index.html (Room 1 the valley under the computed sky on two calendar assumptions, Room 2 "The 314").
*Must land:* "Same graph, now on the ground: the sky is computed, not painted, and where the computation disagrees with the received date we ask a scholar, we do not correct."
*Demo (30 s):* enter in 3D, drag the time slider across the three candidate lunations, then open the finding "no candidate gives a Friday 17 Ramaḍān" and say the rule is a stand-in that he is invited to replace.
*Watch:* Part 2, items 9 and 13; WebGL needed; the 314 stated against 321 found is also a finding, not an error.

**Step 5. The Hijrah night.** *Asset:* lab/hijrah-night-v2/index.html (150 stages, 10 acts, 863 statements; REVIEW-CHECKLIST.md has 377 items).
*Must land:* "A whole journey, every statement with its grade and its source, disputed ones always with the reason. An AI drafted it; nothing is accepted yet."
*Demo (30 s):* jump to Act 7, "Three nights in the cave"; filter by grade to "disputed" (134); open one and read the reason and the source chip; press F for Full view, Escape to return.
*Watch:* the "established" label (Part 2, item 5); ḥadīth references are from memory, to verify; choose the Qurʾān card in advance.

**Step 6. Where scholars sit.** *Asset:* expeditions `#desk` (a claim batch, flags first, decisions exported as `marsad-review-decisions` v1) with lab/hijrah-night-v2/REVIEW-CHECKLIST.md as the long list, and the PR #33 scholar guide (docs/pilot/scholar-guide.md on `origin/fixes/pilot-and-corrections`, not on main).
*Must land:* "A scholar's work is a short queue, flags first, three answers, a source needed to accept, and the decision is exported and imported without retyping."
*Demo (30 s):* open `#desk` for one expedition, show the flags-first batch and the export. Say who decides: the board (P6, P7), which does not exist yet.
*Watch:* the credit contradiction (decide first); the pilot's first batch is the 50 Stories claims, not the Hijrah.

**Step 7. Honest status.** *Asset:* README banner and the 12 Sep correction; Atlas Research depth ("How do we know about ...", evidence summary by status, who recorded, source text); the "Not built yet" list in expeditions/README.md and "Known limits" in atlas/README.md and the Hijrah README.
*Must land:* "15,961 claims, every one proposed, none accepted; this is what exists and this is what does not."
*Demo (30 s):* in the Atlas switch to Research depth, open the evidence summary, then "How do we know about ..." for one item and read its gaps. Then say one thing the project got wrong and fixed in public (the 12 Sep Nūr/Nujūm correction).

**Step 8. The road ahead and the ask.** *Asset:* lab/phase-a-plan/PLAN.md (dates, gates, hours) and lab/beyond-the-graph/index.html (team, cost, partners, decisions), plus docs/06 section 9. **There is no page that carries the ask; the Appendix drafts one.**
*Must land:* "Twelve weeks to a first gate, a first small step with scholars within days, and three things I am asking of you."
*Demo:* none. Hand over the one-pager and agree one next action with a date (for example, one scholar for a timed review by 1 Nov, PLAN W0).

---

## Draft running order, 25 minutes

| Time | Step | Asset | Note |
|---|---|---|---|
| 0:00 to 2:00 | Frame | spoken, no screen | Who you are; AI helped; nothing is reviewed, which is why he is here; the three things you will ask at the end |
| 2:00 to 5:00 | 1 and 2 | demo/index.html | One idea, one event down to "awaiting a scholar" |
| 5:00 to 9:00 | 3 | atlas/index.html | Tour of the Sīra; absence ring; let him test "the ten" if time |
| 9:00 to 12:30 | 4 | expeditions, Badr | The sky; the question, not the correction |
| 12:30 to 16:30 | 5 | Hijrah Night v2, Act 7 | One disputed statement with its reason; Full view |
| 16:30 to 20:00 | 6 and 7 | `#desk`; Atlas Research depth | Where scholars sit; honest status; the 12 Sep correction |
| 20:00 to 25:00 | 8 | one-pager | The ask, the timeline, one next action with a date |

Rules for the room:
- Let him steer. If he stops you, follow his interest, but start step 8 no later than minute 20.
- If you are short on time, drop step 4, then step 3's second stop. Never drop steps 6 to 8.
- Lead with weaknesses. For a scholar, "nothing here is reviewed" at minute one builds trust that a polished demo cannot.
- If he asks something from Part 3 you cannot answer, say "not decided yet" and write it down; do not improvise governance.

---

## What could be fixed in a few hours today

In order of value per hour. Anything that changes a published artifact needs a republish and a link check; with a meeting this afternoon, change what you say and hand over before you change code.

1. **Write the one-pager (60 to 90 min).** Skeleton below; only you can fill the blanks. This one page answers Part 3, questions 1, 2, 3, 8, 9 and 10.
2. **Decide the credit rule (10 min), then make three documents say the same (20 min):** docs/REVIEWERS-BRIEF.md and pages/reviewers-brief.html ("recorded under your name, permanently"), pages/marsad.html, and the PR #33 guide. The PR #33 wording (board credit, named later only if the reviewer agrees) fits P6 and P7. Your call.
3. **Rehearse the four demos once on the laptop you will carry (30 min):** the "ten" tour; the opposition tour and its 37 names; searching "Abū Bakr" to see the duplicates; the expeditions server and the Badr page; Act 7 of the Hijrah; what 439 counts at Badr. Save the Atlas view codes as bookmarks.
4. **Refresh the front door (20 to 30 min):** README Status block (date, current counts from Part 1, 14 documents, add row 13 to the reading table, point to atlas/, expeditions/, lab/hijrah-night-v2/, learn/, ask/, review/) in case he looks at the repository.
5. **Pick the two numbers you will say and use only those (5 min):** 15,961 claims and 7,867 entries (Atlas), and name the layer for any other figure (Part 1, rows 2 and 8).
6. **Print the Part 3 answers as a one-sheet for yourself (15 min).**
7. **Hold back four pages:** do not send marsad.html, build-with-us.html, road-ahead.html or REVIEWERS-BRIEF today. If they must go, add one line at the top, "September 2026 version; current plan is Phase A, 2 Nov 2026 to 24 Jan 2027" (10 min each, plus republish).
8. **Optional, 1 to 2 hours, only if everything above is done:** in lab/hijrah-night-v2, show an "AI-drafted, unreviewed" mark beside the grade filter so "established" cannot be misread. Re-run `build.py` and the checks; do not do this at the last minute.
9. **Not for today:** amending docs/09 (rows 10 and 11), re-estimating PLAN.md scholar hours (row 7), merging PR #33, de-duplicating the 7,867 entries, work-board housekeeping (PR #32 row).

---

## Appendix: draft one-pager (edit freely; figures trace to Part 1)

**al-Marṣad: where we are and what we ask. 24 Oct 2026**

1. *What it is.* An evidence-anchored atlas of the Sīra as Ibn Hishām tells it. Every statement is a report with its chain and a named grading beside it. The Prophet ﷺ is the light at the centre, never a figure. Nothing is accepted until scholars accept it.
2. *What exists.* A sky of 8,373 marks and 15,961 claims (7,867 name entries, not yet de-duplicated; 208 events; 236 places); five expeditions with computed skies; the Hijrah as 150 stages and 863 statements. All AI-drafted, all proposed.
3. *What does not exist.* Any accepted claim. A formed board. A named legal home. Scholar review of any page. [maintainer: add anything else]
4. *Rules we will not break.* No depiction of the Prophet ﷺ, his family or the Companions. No fatwā. No AI grading of authenticity. No contested matter shown as settled. Everything forkable.
5. *How a decision is recorded.* The reviewer is an ID. Accept, reject or needs discussion; a source is needed to accept. Decisions are exported and imported by file. The board decides disputes. Public credit goes to the board unless the reviewer agrees to be named. [maintainer: confirm]
6. *Next twelve weeks.* Phase A, 2 Nov 2026 to 24 Jan 2027; first scholar review by 1 Nov; gate in week 12 (PLAN.md). [maintainer: trim]
7. *Money.* Year one: lean $80k to 125k, full $200k to 335k; hosting under $600 a year; the legal home and the trust's country are open. [maintainer: decide what to show]
8. *What we ask of you.* (a) Introduce one scholar for a first timed review, and two for the first full review in December. (b) Your steer on how opponents are classified, the first board's tradition, and the source line. (c) Your advice and introductions on a custodian and legal form.
9. *Who and how to reach us.* [maintainer: name, role, one contact]

---

## Not verified

- No page was opened in a browser; artifact links were not tested for a non-owner (they are private until shared, pages/README.md).
- The astronomy findings are read from expeditions/README.md. My only calculation was a weekday check of two dates; it is not a test of the tool.
- BTG figures are read from text (lab/beyond-the-graph/index.html); percentages in Part 1, row 10 are my arithmetic.
- Whether any scholar has already seen the project, whether OpenITI has replied, and what the 439 at Badr counts are not in the files.
- docs/10 coverage of Arabic-language ḥadīth tools is from a keyword search, not a full read.
