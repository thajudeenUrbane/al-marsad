# Maintainer answers, round 3 — 16–17 October 2026

Answers to the 85 open questions sheet, round 3. It was written after the ten slices and expanded after the full-book Ibn Hishām pass (branch `sira-full-pass`). The answer sheet is a private artifact. Personal answers are left out of the repo. Where round 3 changes rounds 1 or 2, round 3 wins, and the change is noted. Briefs: `slice-11-brief.md` (one graph, cleaned), `sky-guided-brief.md` (the Sky as a guided-learning world) and `reader-r3-brief.md` (display decisions).

## Direction (this changes the order of work)
- **W1. Exploration first.** "During the initial phase, we need to invest more time in exploring different perspectives, interaction methods, and visualization possibilities." The graph should be engaging and layered, from simple to advanced, so that scholars and the community are drawn in. The structured review then follows. This reverses Claude's suggestion and the phasing in doc 09 §5 (kill criterion 3). The maintainer decides product (round 1, J69). Review keeps running in parallel at low cost (P1, E1).
- **W5 and W6. The vision.** An immersive, explorable world in which people move through a period, place or event, from any angle, and the platform guides discovery rather than waiting for questions. Gamification (quests, milestones) comes gradually, without compromising accuracy. Guided learning should be explored from many angles, with AI helping learners go in depth. Under the standing rules, AI chooses the route, the camera and what to show next. Every fact still comes from a recorded claim with its source (A2: translate-only for questions).
- **W2.** The **Sky Atlas** is the view that grows, once H4 is settled (it is: see below). It needs a guided-learning mode across the whole graph. **W3.** The year-one goal is a public launch with the board named, "and more than all of this".
- **F15. Join now.** "Everything comes to a single graph." The full-book layer joins `ontology/corpus/`, with the pages redesigned to cope. Duplicate resolution (F3) and the error audit (F4) run inside the joined graph. **W7.** A versioned DOI release waits for the audit and duplicate resolution.

## The full-book graph (chapter F)
- **F1. Sides.** Use separate relations: fought with the Prophet ﷺ, and fought against him, each at an event and resting on the text's list headings.
- **F2.** Every total the text states becomes a check, and mismatches go to the review queue (Badr 314; Second ʿAqaba 73 men and 2 women; First ʿAqaba 12; Uḥud 65 and 22; Abyssinia 83 men).
- **F3.** A second AI pass proposes merges with its evidence, an editor approves, and scholars see only the hard cases.
- **F4.** An editor audits a random sample of about 400 claims, by relation type, and the error rate is published.
- **F5.** Record the transmission formula (ḥaddathanī, akhbaranī, ʿan, balaghanī, zaʿamū, qāla) on every narration link.
- **F6.** Narrator verdicts: only those the scholars select, quoted and attributed.
- **F7.** Tag each claim with its voice (Ibn Isḥāq or Ibn Hishām), and attach Ibn Hishām's doubts about poems as qualifiers.
- **F10.** An editor checks the Quraysh lines against *Nasab Quraysh* first.
- **F11.** Pre-Islamic and post-Prophetic material is a labelled background layer: in the graph and Research, kept out of learning paths at first.
- **F12.** Royal titles become offices (the Najāshī, Qayṣar, Kisrā), held by named persons where the text names them.
- **F13.** By default, Connect skips ancestors beyond three generations and says "same clan" instead.
- **F14.** Connection stories: Claude finds candidate paths, and a scholar writes or approves each story. The story says what is stated and what is only connected.
- **F16.** A maghāzī calendar: Ibn Isḥāq's dates first, with other early reports as disputes (Mūsā b. ʿUqba via al-Bukhārī, al-Wāqidī).
- **F8** (comparing recensions): not sure yet. **F9** (generations beyond ʿAdnān): scholars decide.

## Review and the scholars (chapter P)
- **P1.** The maintainer tries the tool first as a test reviewer, then the scholars. **P2.** A private web link: the maintainer does the Cloudflare setup (docs/handover/slice-2c-ci.md). **P3.** The roster is kept encrypted, in a password manager or encrypted cloud folder.
- **P4.** Ibn Hishām first. **P11** (which batch): not sure yet. Default: slice 4's Hijra passages.
- **P5.** Every AI-compiled claim needs a cited source to be accepted (as today).
- **P6.** Until the board exists, both notes are kept and the claim stays under review. **P7.** A reviewer's change of mind always goes through the board.
- **P8.** Claude prepares a merge, the maintainer approves it, and the old address redirects. **P9.** Clear the 32 bookkeeping flags, and ask the scholars whether each of the 12 groups is a real tribe or group.
- **P10.** A trained editor reviews clear external-ID matches; scholars review only the doubtful ones.

## The public site (chapter G)
- **G1 and G8. Public display.** Public pages do not say they are being reviewed or checked. For a period, public pages show everything, while review takes its time. After review, public pages show only accepted content, with no labels. Status appears only in the Study and Research depths. **This changes round 2 R8** (a label on every claim, also in shared images) and the doc 13 D2 rule that status is always visible to the public. Held until confirmed: every claim on a public page still shows its source line (work and page), which is provenance and not review status, so "no pixel without provenance" is kept. Round 4 question 1.
- **G2.** The 50 Stories are replaced gradually by stories built from accepted claims, and the originals stay in Research as an AI draft. **G3.** Claude drafts, a scholar edits and approves, and the AI part is said openly.
- **G4.** The maintainer wants a list of domain ideas to check. **G5.** Addresses never change: merges and renames redirect. **G6.** Claude fixes modelling errors (for example, Khadīja recorded as "father of" Fāṭima) with a public changelog; content changes go to the review queue. **G7.** Keep only the wider-network thread among the prototypes.

## Honour and display (chapters H and L)
- **H1.** رضي الله عنه / عنها for Companions once a scholar accepts their companionship; رضي الله عنهن for the Mothers of the Believers; عليه السلام for the other prophets; رحمه الله for later scholars and narrators.
- **H2.** Story prose is stored as written and shown with ﷺ. **H3.** The Prophet's ﷺ page is one long page, loaded in parts.
- **H4.** The Prophet ﷺ is the light at the centre, never a node (as docs 00 and 04 say). The Observatory changes accordingly. **H5.** The stars image is our own metaphor and is never quoted as a hadith.
- **H6.** Sensitive claims appear like every claim (the source's words, the passage, the status in the deeper depths) plus a short context note written by a scholar. **H7.** Each scholar decides what they review: "initially there will be a lot of reports to review; later it will be solved."
- **L1.** Gregorian first everywhere, Arabic pages included (Claude had suggested Hijri first there). **L2.** Digits 0–9 and Gregorian month names (يناير، فبراير …). **L3.** One of the current scholars reviews the Arabic interface soon. **L4.** Malayalam and Urdu come after the Seerah corpus is well reviewed. **L5.** Arabic names as written in Ibn Hishām, where he names them. **L6.** Always "ibn".

## Time, learning, Ask, sources, scope, money
- **T1.** Wikidata dates stay as a labelled stand-in until classical dates are recorded. **T2.** Lifelines defaults to lunar years. **T3.** Replace the example map points with reviewed gazetteer points (al-Thurayya, credited) and drop the straight line. **T4.** Generation is shown by brightness, as in the Sky.
- **E1.** A class tries the Hijrah journey this month, in a private preview. **E2.** Test how readers understand status, with both the class and academic contacts. **E4** (practice): not sure yet. **E5.** Accounts only for researchers' workspaces. **E6.** All the events and journeys in the Seerah are to be documented; the listed journeys first.
- **E3. Order and representation of people.** The default order is the Prophet ﷺ, then al-Khulafāʾ al-Rāshidūn, then the ten promised Paradise (al-ʿashara al-mubashsharūn), then the most-connected Companions. Other sorts are available (most connected, A–Z, order of accepting Islam), with search. Those who died as disbelievers come last. Badr may use the 50 Stories records until they are reviewed. **X1.** Enemies of the Prophet ﷺ are shown differently, as dark things, not stars or light. The maintainer's idea: a time toggle shows dark stones becoming stars when a person accepts Islam. Rules held with it: "most connected" is labelled as a count of recorded links (coverage, not rank: README "Computed ≠ significant"), and who counts as an opponent, and when someone accepted Islam, come only from recorded claims with sources. Edge cases go to the scholars (round 4 question 2). X1 also accepts splitting thread.json past about 200 KB; the other X1 defaults stand.
- **A1.** Collect real questions and have a scholar check the 68. **A2.** A model may translate questions into queries only after published adversarial tests. **A3.** Records, never a verdict. **A4.** A refusal suggests asking a qualified local scholar.
- **S1.** Keep pointers and short phrases, and write to OpenITI about permission and partnership. **S2.** The Cairo edition, once a scholar checks it against print. **S3.** The next source: the scholars choose. **S4.** Kodampuzha's work is a checklist of events and people to cover. **S5.** Translations: AI drafts, a scholar approves, labelled until approved. **S6.** Move the 18 al-Thurayya rows into a credited CC BY-SA file.
- **D1.** Amend doc 09 kill criterion 4: one declared board is fine if every page says so; others come later. **D2.** Out-of-scope searches get a coverage note. **D3.** Kerala comes after the Seerah, as the first regional study. **D4.** Outside academics review after the first accepted claims.
- **M1.** The trust's country: decided later, after consultation. **M2.** Year-one money goes to stipends, translation, AI runs, domain and legal, a designer, books, and tech development. **M3.** Quarterly totals by category. **M4.** One of the scholars is the second keyholder. **M5.** A short sheet every week or two, ★ first.

## Round 4 (short, next sheet)
1. On public pages with no review language, does each claim still show its source line?
2. Who classifies opponents and conversions, and how are the edge cases shown: Abū Ṭālib, the munāfiqūn (ʿAbd Allāh b. Ubayy), the Jewish clans of Madinah, people whose Islam is disputed, and anyone with no recorded conversion date?
3. A domain from Claude's list. Still open: P11, E4, F8, F9, S3, M1.
