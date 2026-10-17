# Reader-page decisions, round 3 — brief

Context: docs/handover/maintainer-answers-3.md (G1, G7, G8, H1, H2, H6, L1, L2, L6, D1, D2, A4, T3); site/display.py (every display rule, one place each); site/i18n/en.json and ar.json. Do not read chat history; this file is the brief. Branch `reader-r3`. Small, independent changes; each one gets a test.

## Do
1. **Public display mode (G1, G8).** One build switch, `PUBLIC_MODE`: `all` (show everything) now, `accepted` (show only accepted claims) after the review period. Public (Discover) pages carry no review or "checking" language. Status labels appear only at the Study and Research depths. Until round 4 question 1 is answered, each claim on a public page keeps its source line (work and page).
2. **Honorifics (H1).** Show رضي الله عنه / عنها for a person whose companionship a scholar has accepted (an accepted claim, never the tabaqa field alone), رضي الله عنهن for the Mothers of the Believers as a group, عليه السلام for the other prophets, and رحمه الله for later scholars and narrators. Each comes from a reviewed list file with its source. Gender comes from recorded data only; where it is unknown, show no honorific rather than a guess.
3. **Names (L6).** Always "ibn" in display (`EXPAND_B_TO_IBN = True`). Search is unchanged.
4. **Arabic pages (L1, L2).** Gregorian first, digits 0–9, Gregorian month names (يناير …). These are the current defaults: confirm them in tests.
5. **Declared default (D1).** Every page footer names the review board's lens ("Sunni, across the four madhhabs, coordinated initially by Shāfiʿī scholars"). Docs/09 §5 kill criterion 4 is amended to "a declared default, said on every page; other boards later".
6. **Coverage notes (D2).** Searches for out-of-scope topics (Ghadīr Khumm, Ṣiffīn, Jamal, Saqīfa disputes) get a short "not covered yet" note with the reason, from a reviewed list.
7. **Context notes (H6).** Add a slot for a scholar-written context note on any claim, shown beneath it. The slot is empty until a scholar writes one.
8. **Prototypes (G7).** Serve only the wider-network thread among the earlier prototypes.
9. **Ask (A4).** The refusal says the site does not give rulings and suggests asking a qualified local scholar.
10. **Map (T3).** Hide the thawr example points and the straight route line from the public map, until reviewed gazetteer points replace them.

## Done when
`scripts/check_all.sh` passes, with a test for each item above. Handover `docs/handover/reader-r3.md` (≤60 lines).

## Rules
Never upgrade a status; never invent a name, list member or source; every UI string is a key in en.json and ar.json; logical CSS only.
