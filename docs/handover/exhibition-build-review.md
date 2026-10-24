# Exhibition: scholar's-eye review (2026-10-24)

Review of every word in `exhibition/index.html` (halls and `.notes`), `exhibition/leave-behind.html`,
`exhibition/README.md`, the texts in `exhibition/numbers.js`, and the expedition sentences changed on this
branch (`git diff 02da6c2 -- expeditions/compile/compile.py expeditions/defs/expeditions.json`).
Line numbers are those of the files before this review's edits. "Fixed" means the text was changed here;
"Left" means it is for the maintainer or for another owner (nothing under `expeditions/`, `atlas/`, `review/`
or the data was edited).

## Findings

### Numbers (checked, clean)

- Every figure in the halls and the leave-behind is a `data-n`/`data-t` key, and `build.py --check` says OK.
  The sky line adds up: 7,867 + 214 + 236 + 50 + 12 = 8,379 marks. 16,498 statements = 16,498 proposed.
- Badr date, `index.html:160` and `:176`, `README.md:51`: the text says Friday 17 Ramaḍān (`badr.page`
  vol. 1, p. 626). The crescent rule's three candidate months give Monday 13 February, Tuesday 13 March and
  Thursday 12 April 624 (`expeditions/dist/data/badr.json`), so "none of the 3 candidate days is a Friday"
  and the README's "None agrees" are right; "None agrees." is the expedition's own result line
  (`expeditions/dist/app.js:291`). The tabular date (Tuesday 13 March 624) is also the crescent rule's
  middle candidate, so "Both are our assumptions" holds. Left: the hall says "none" in typed words; if the
  rule ever changes, `badr.friday_candidates` would no longer match the prose (no test ties them).
- 313 / 314, `index.html:160`, `:174`: 314 is the total Ibn Isḥāq states for his list (it agrees with
  `badr.with` = 314, though that key counts people placed with him, a different count). 313 is not in the
  data; it is the well-known report (al-Barāʾ's "313, the number of Ṭālūt's men", in al-Tirmidhī; al-Bukhārī
  has "three hundred and ten-odd"). `expeditions/defs/expeditions.json` already flags it for a scholar.
  A likely question, not an error: Ibn Isḥāq's 314 counts those given a share of Badr who were not present
  (ʿUthmān رضي الله عنه, and others). Left as is.
- Page references: vol. 1, p. 626 (the Badr account) and vol. 1, p. 240 (Ibn Isḥāq's report from
  Abū Jaʿfar, in the account of the first revelation and the "day of the criterion", 8:41) are the two
  places the date appears; the hall 5 bridge ("appears earlier in the book too") is right. Both pages are
  provisional, as the screens say.

### Honorifics

- H1, `index.html:54` (hall 2): "Ibn Hishām’s Sīra", his first mention on that screen, had no رحمه الله.
  **Fixed:** "the Sīra of Ibn Hishām رحمه الله", in the same `.nw` + `.hon lang="ar"` markup as hall 5
  (the possessive was recast so the honorific does not sit before "’s").
- H2, `leave-behind.html:94`: the same sentence, the only mention of Ibn Hishām on the page. **Fixed** the
  same way.
- H3, `index.html:160` (hall 4): "314 in Ibn Isḥāq’s list", his only mention on that screen, had no
  رحمه الله. **Fixed:** "314 in the list of Ibn Isḥāq رحمه الله." (one short line longer).
- H4, hall 5 (`index.html:195`, `:199`): the first mentions of Abū Jaʿfar, Ibn Isḥāq and Ibn Hishām on that
  screen are inside the AI gloss and the citation (data), so رحمه الله comes at the second mention, in the
  chain line. That is normal for a quoted gloss and a bibliographic citation. Left.
- H5, hall 5: the page script puts "(peace and blessings be upon him)" after the first ﷺ outside the notes,
  which on hall 5 is inside the AI gloss ("the Messenger of God ﷺ (peace and blessings be upon him) met
  …"). Acceptable, but it is the exhibition's words inside a labelled machine gloss. Left (judgement call).
- Checked, clean: ﷺ always carries the marked span and sits in `.nw` with the word before it; the words
  appear once per screen (halls 1, 2, 3 by hand, hall 5 by script; halls 4, 6, 7, 8 do not mention him);
  Khadīja carries رضي الله عنها on the hall 3 button; Abū Ṭālib and ʿAbd Allāh b. Ubayy carry none, which
  is right; no one carries an honorific wrongly. The notes (presenter only) do not add Companion honorifics,
  e.g. the search term "Abū Bakr" (`index.html:124`, `README.md:57`), which is reasonable for a search string.

### Claims

- C1, `index.html:130` (hall 3 notes, "Why this order?"): "then the four caliphs, then the ten promised
  Paradise" counts the four twice: the four caliphs are among the ten. **Fixed:** "then the other six of the
  ten promised Paradise".

- C2, Atlas, hall 3 "One record: Khadīja" (data, not editable here): her record in the Atlas side panel
  (decoded from `atlas/index.html`) includes "Khadīja bint Khuwaylid is the wife or husband of The Prophet
  Muḥammad ﷺ." (a template), "Before the Prophet Khadīja was married to Abū Hāla b. Mālik." (no comma, so
  it can read as "the Prophet Khadīja"; the same pattern in 10 glosses, one per wife), and glosses with a
  bare "the Prophet" and no ﷺ ("Khadīja bore the Prophet all his children except Ibrāhīm"; "Khadīja sent
  the Prophet with her slave called Maysara"). The Atlas only wraps a ﷺ that is already in the text; the
  honour pass was added to the expeditions only. **Fixed (steer only)** in hall 3's notes (`:119`, `:124`):
  open "The Messenger of God ﷺ married Khadīja bint Khuwaylid", and do not open the earlier-marriage lines
  or "the wife or husband of". **Left for the corpus/Atlas owner:** recast the 10 glosses as "Before her
  marriage to the Prophet ﷺ, <wife> was married to …", replace the "wife or husband of" template, and add
  ﷺ to the Atlas glosses as `expeditions/compile/compile.py` `honour()` does.
- C3, `numbers.js` `hall2.person` = "Khadija bint Khuwaylid" (the Atlas node name, no macrons), while the
  hall 3 button says "Khadīja bint Khuwaylid رضي الله عنها". The key is not shown on any hall, so the only
  place the scholar sees "Khadija" is the Atlas itself (node names are unaccented throughout:
  "Abu Hala b. Malik", "Fatima bint Za'ida"). Ruling: keep the button as it is (it follows the exhibition's
  transliteration); report the Atlas node names to the corpus owner. Left.

- C4, `index.html:176` (hall 4 notes): "the crescent rule gives Monday and Tuesday and Thursday" did not say
  these are three alternative months. **Fixed:** "the crescent rule, over the 3 possible months, gives …"
  (the 3 is `data-n="badr.candidates"`).
- C5, `index.html:314` (hall 7 notes): "three answers per statement" could be heard as three answers to give.
  **Fixed:** "one of three answers for each statement".
- C6, `README.md:49`: "AI drew the statements" overstated the AI's part against hall 2 ("drawn from the text
  with AI help"). **Fixed:** "AI helped draw the statements from the text and wrote the glosses".
- C7, `expeditions/defs/expeditions.json` (this branch): the Badr note "313 in the well-known report, 314 in
  Ibn Isḥāq's list." is shown with `note_class: "attested"`, the class for what the text attests
  (`expeditions/dist/app.js:228`). The 313 is not in the text (the file's own "about" says so). **Left for
  the maintainer (expeditions):** show it as "schematic" or as an outside report, not as attested.
- C8, the step label "Who was there" (`expeditions/dist/app.js:123`; hall 4 notes `index.html:170`,
  `README.md:59`) against the plain version's heading "Who the text places here" (`compile.py` `text_page`).
  Ruling: the notes rightly quote "Who was there", because that is the button the presenter must not
  click. **Left for the maintainer (expeditions):** rename the step to "Who the text places here"; "was
  there" is wrong for the people counted without being present (the app itself marks them "absent" and
  "counted without being present", e.g. ʿUthmān رضي الله عنه at Badr). The new count note's "under who was
  there" would follow the rename.
- C9, `numbers.js` `hall4.mode` = "samā‘" (U+2018 quotation mark, not ʿ U+02BF), shown on hall 5's chain line.
  Data from the Atlas. **Left for the Atlas/corpus owner:** "samāʿ".
- C10, expedition sentences (this branch): `honour()` gives "the Prophet's ﷺ face", "the Prophet Muḥammad ﷺ"
  and leaves a mention that already has ﷺ; this matches the brief's own form ("the Prophet's ﷺ own
  journey"). "On the other side" for "against him" is better. No issue found in the 61 dist sentences
  that name him.

- C11, the pilot pack's origin. Hall 6's notes (`index.html:270`, "If asked") say the 52 pilot statements come
  from the 50 Stories, which an AI wrote, but the presenter's script only said so when asked, and hall 2's answer
  to "Is AI writing the history?" (`:85`) began with a flat "No.". **Fixed (presenter's words only):** hall 6
  "Say" (`:266`) now tells him to say where the pack comes from, the hall 2 answer names the exception, and the
  README's hall 6 row (`README.md:53`) says the same. The screens are unchanged: see J1.

## Judgement calls (left open)

- J1 (**decide before the meeting**). No screen the scholar sees says where the pilot pack comes from: hall 6
  (`index.html:249`), the first request in hall 7 (`:288`) and the leave-behind (`:122`, `:138`) say only
  "pilot pack". Hall 2 (`:75`) and the leave-behind (`:110`) say "the statements were drawn from the text with AI
  help", and that does not hold for statements taken from stories an AI wrote. A possible line for hall 6 and the
  leave-behind (both have room): "A pilot pack, ready to send: 52 statements from the 50 Stories (written by AI;
  each needs a source and page) and the first 50 identity questions."
- J2. "Who classifies opponents and conversions" (`index.html:128` notes, `:294` hall 7, `leave-behind.html:142`).
  "Conversions" is normal academic English, but the same item already says "accepting Islam"; one option is "Who
  decides who is shown as an opponent, and when someone accepted Islam". Listing the Jewish clans of Madinah next
  to the munāfiqūn is fair as a question. The presenter can add that they were parties to the Madinah covenant
  and that some accepted Islam (ʿAbd Allāh b. Salām رضي الله عنه).
- J3. The draft tradition shown in hall 7 (`:295`) and on the leave-behind (`:143`) is "Sunni, across the four
  madhhabs, coordinated initially by Shāfiʿī scholars" (`review.tradition_default`, data). Put it to him as a
  draft and a question, especially if his madhhab differs. Left.
- J4. Hall 1's notes (`:26`, `:35`): in the data, a Companion's honorific waits until a scholar accepts the
  claim of companionship, so he may see Companions in the Atlas without رضي الله عنه. The notes already have
  the answer. Left.
- J5. Hall 5: "(peace and blessings be upon him)" lands inside the AI gloss (H5). Left.
- J6. Hall 5's mursal answer (`:223`-`:224`) is careful and right (Abū Jaʿfar al-Bāqir is a Successor; the
  grading is his). Keep it.
- J7. Hall 5's chain (`:204`) ends "in the recension of Ibn Hishām"; Ibn Hishām had the Sīra from Ziyād
  al-Bakkāʾī, from Ibn Isḥāq. A likely question. The answer: the screen gives the chain as the text gives it for
  this report; the route of the book itself (Ibn Isḥāq, al-Bakkāʾī, Ibn Hishām) is a separate layer, not yet in
  the data. Left.
- J8. The glosses say "Messenger of God" while the screens and the aria-labels say "Allah" (data). Some scholars
  prefer "Messenger of Allah" in English. Left for the corpus owner.
- J9. The expedition's "None agrees" text (`expeditions/dist/app.js`, shown in hall 4) gives "perhaps the calendar
  was still being intercalated" as one possible reason. That is nasīʾ (9:37), a sensitive point, though it is
  offered only as a "perhaps". Be ready for it, or ask the expeditions owner to drop that clause. Left.
- J10. Hall 2 (`:72`): "open to check, copy and correct". The text's licence allows copying only for
  non-commercial use. Minor. Left.
- J11. The Arabic رضي الله عنها in `README.md:50` has no `lang` (Markdown, presenter only). Left.
- C3 ruling, restated: keep "Khadīja" with macrons on the button; the unaccented "Khadija" is the Atlas node name
  (data), for the corpus owner.

## Must change before the meeting (other owners; not editable here)

1. Atlas, Khadīja's record (C2): the "wife or husband of" template, "Before the Prophet <wife> was married to …"
   (10 glosses, no comma), and no ﷺ in the Atlas glosses. Hall 3's notes now steer the click to the marriage
   statement and away from these lines; that covers the walk only if the presenter keeps to it.
2. Expeditions: the Badr 313 note is classed "attested" (C7), and the step "Who was there" (C8) should be
   renamed "Who the text places here" (the presenter is told not to click it).
3. J1: whether the screens say where the pilot pack comes from.

## Checks run after the edits

- `.venv/bin/python exhibition/build.py --queue review/dist/queue.json --check`: OK (48 values).
- Leave-behind (scratch `lb.cjs`, file://): content 258.1 of 275 mm, "pages: 1". Its CSS is untouched.
- Hall fit, with check.cjs's own test, run from a scratch script over file:// (no server): all 8 halls fit at
  1920 × 1080 and 1280 × 800. The tightest are halls 3 and 4, 25 px spare at 1280 × 800. `check.cjs` itself was
  not run, because it starts `serve.py`; `bash scripts/check_all.sh` should confirm before the push.
