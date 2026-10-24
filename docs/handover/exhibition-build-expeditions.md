# Exhibition build: expeditions slice

Audit items A12, B3, B4, C6 and C7 in `expeditions/`, plus the "superseded" banner on four `pages/`.
Branch `claude/exhibition-build-7a92ab`. Edited in the working tree only: nothing committed, pushed or stashed.

**Update, 2026-10-24:** `expeditions/dist/` was afterwards regenerated offline for the touched parts (see `exhibition-build-dist.md`); a full rebuild with the five downloads below is owed after the meeting. The paragraph that follows describes the state when this note was written.

**`expeditions/dist/` is NOT rebuilt.** The rebuild needs inputs that are not on this machine and would have to be downloaded (see "Why dist was not rebuilt"). dist is untouched: not hand-edited, not regex-patched, not partly updated. Until someone with the inputs rebuilds it, dist still has the old wording and `dist/app.js` is the old app.

## What changed (file and line, as of this note)

`expeditions/compile/compile.py`
- 65-89, new: `PBUH`, `_PROPHET`, `_PROPHET_TAIL`, `_HONOURED` and `honour()` (A12). It writes " ﷺ" after every "the Prophet", "the Prophet's" (sign after the possessive) and "the Prophet Muḥammad" (sign after the name) in a claim sentence. A mention that already carries ﷺ, the Arabic words or "(peace and blessings be upon him)" is left alone, so a second pass changes nothing. Nobody else gets a sign (GRAMMAR section 7: a Companion waits for a scholar to accept the companionship claim).
- 126 `Graph.cite`, 227 `count_lists` row, 446 `review_batch` item: the claim `gloss` goes through `honour()`. The claim sentences are the `gloss` fields of the extraction corpus (`ingest/claims/*.jsonl`, read-only, not touched), so the fix is made at generation, on the copy that goes into dist. The "share" test at 227 still reads the raw gloss.
- 239-240 `count_case`: passes a case's `note` and `note_class` (default "schematic") into the case data (B3, B4).
- 546-547 `text_page`: writes the note as a paragraph under the case heading, tagged with its provenance class.
- 575-576 `text_page` people sentence (C7, A12): "N named with the Prophet ﷺ&lrm;, N on the other side, N with no side recorded." The comment on 575 explains the `&lrm;`.
- 614 `channel_pack` puzzle message: the case note is added before "Before tomorrow, guess".
- 623 `channel_pack` people sentence (C7, A12): "N with the Prophet ﷺ and N on the other side."

`expeditions/app/app.js`
- 74 (C6): "the Prophet's ﷺ life".
- 228 `caseCount`: renders `c.note` as a `prov(note_class, ...)` paragraph at the top of the count panel (B3, B4).
- 350-352 `people()` (C7, A12): "with the Prophet ﷺ&lrm;, ... on the other side, and ... with no side recorded". 350 is the `&lrm;` comment.
- 355 (C7): filter labels "With the Prophet ﷺ" and "On the other side". The values `with`, `against` and `not recorded` stay as data keys (CSS `.against` depends on them); only the visible labels changed.

`expeditions/defs/expeditions.json`
- 2 `about`: now states the one exception to "no fact asserted here that the graph or text does not carry": the 313 in the Badr note.
- 136 (B3), Badr count case "The 314": `note` "313 in the well-known report, 314 in Ibn Isḥāq's list.", `note_class` "attested".
- 27 (Abyssinia, "Eighty-three men") and 56 (ʿAqaba, "Seventy-three men and two women") (B4): `note` "Three different counts: the total the text states for this list, the names the extraction found in it, and the name records at this event with no side recorded (counted separately, under who was there).", `note_class` "schematic".
- Lines 71 and 79 already read "The Hijra of the Prophet ﷺ to Madinah" at HEAD; no change needed.

`pages/` (banner, 3 inserted lines each: a comment, the banner `div`, a blank line; nothing else on the pages changed, `git diff --stat` shows 3 insertions and 0 deletions per page)
- `marsad.html` 331-332, before the sticky nav. `build-with-us.html` 116-117, `road-ahead.html` 171-172, `reviewers-brief.html` 204-205, all before `<main>`.
- Text is exactly the brief's. I parsed each page and compared the banner's text to the brief: identical on all four. The first sentence is in `<strong>`; the visible text is unchanged.
- Style, inline only: a card on the page's own palette variables (with fallbacks), `role="note"`, 0.84rem text, 1px rule border and a 3px teal left bar. Calm, no red. Width is set so the card lines up with each page's text column (measured: banner and h1 share left and right edges on the three narrow pages at 1024 px and 375 px). On `marsad.html` it is a centred card above the nav.

## Why dist was not rebuilt

`compile.py` reads inputs that are not in this worktree or in the main checkout (`.../AL MARSAD - Islamic History 4D Visualisation/expeditions/.cache` does not exist either):
- `expeditions/.cache/tiles/` (terrain tiles). On a first run the build fetches them from `s3.amazonaws.com/elevation-tiles-prod/terrarium` (compile.py line 60). That is the network: not allowed here.
- `ingest/cache/0213IbnHisham.SiraNabawiyya.Shamela0023833-ara1.completed` (the OpenITI text; `ingest/ibn_hisham.py fetch` downloads it).
- `expeditions/build/sky/*.json` and `stars.json` (gitignored; `sky.cjs` needs the HYG star CSV and the astronomy-engine package).
- Pillow (`PIL`), which the build imports.

To rebuild, someone with those inputs runs, from the repo root:
1. `python3 -m pip install --require-hashes -r requirements.txt`
2. `.venv/bin/python ingest/ibn_hisham.py fetch`
3. `node expeditions/compile/sky.cjs <hygdata_v41.csv> <astronomy-engine dir>`
4. `.venv/bin/python expeditions/compile/compile.py`
5. `git diff --stat expeditions/dist`, then check that only what is listed below changed, then `bash scripts/check_all.sh`.

Expected change in dist, from an offline dry run. It is not a rebuild: it loaded the edited compile.py with a stub in place of Pillow, re-rendered the plain pages and channel packs from the existing dist data, after applying `honour()` to every gloss and adding the case notes the way the new code does. The control run (edited code on unpatched data) reproduced the existing text pages and channel packs apart from the people sentence. The predicted diff is 22 text-page chunks and 10 channel-pack chunks, all intended; 69 dist glosses plus the review-pack glosses gain " ﷺ"; three count cases (Badr, Abyssinia, ʿAqaba) gain `note` and `note_class`; `dist/app.js` becomes identical to `app/app.js`. `publish.html`, `index.html`, the CSS and the other JS files are unchanged. Treat these numbers as a prediction to check against the real rebuild.

## What was verified

- `ast.parse` of compile.py, `node --check` of app.js, `json.load` of expeditions.json: all pass. `git status` shows only the files named here (plus `exhibition/`, which is the other session's, untracked).
- `honour()` run over all 16,006 corpus glosses and 1,801 dist glosses: it adds the sign after "the Prophet" (about 807 corpus glosses change), never doubles an existing sign, and a second pass changes nothing. No gloss has a digit after a sign (see the bidi note), and no other prophet is named after the word "Prophet" in the corpus.
- Scratch site (in the scratchpad, outside the repo): the edited app and the dry-run data served on localhost and looked at in the browser pane. The Badr note ("313 in the well-known report, 314 in Ibn Isḥāq's list."), the Abyssinia and ʿAqaba notes (with `data-prov="schematic"`), no note on Uḥud, the Hijrah date claim with the sign, the people sentence and the filter labels all render as intended. No console errors; no horizontal overflow at 375 px; the digits sit in the right order next to the sign on the app and on the plain page.
- Banners: viewed from scratch copies of the four pages (the Google Fonts links stripped, so nothing was fetched) in light and dark mode, at 1024 px and 375 px. Visible, aligned, no horizontal overflow.

## Beyond the brief

- The `&lrm;` after the sign where a number follows (compile.py 576, app.js 352). U+FDFA is a right-to-left letter (bidi class AL), so in "ﷺ, 131" the comma and the digits resolved right-to-left and the number showed in front of the sign. Easy to revert. A general `.pbuh` span with `unicode-bidi: isolate` (and a no-wrap so the sign never starts a line) belongs to the design grammar, not here.

## Left undone and flags

- dist is stale until the rebuild above (the main item).
- The banners are in the repo files only. The published artifact copies are not updated; whoever owns them must republish (`pages/README.md` lists the links, untouched). I did not publish anything.
- The corpus glosses are still bare; `honour()` is a generation-time fix. Fixing the corpus itself is another owner's change (about 485 bare gloss lines remain in the full corpus file). `sd.PROPHET` in `ingest/sira_derive.py` (the first-mention honorific in words) is unchanged; it appears 18 times as `subject` in the review packs.
- The 313 note says "attested", but the corpus does not carry 313. A scholar should confirm the figure, its wording and the class (the defs `about` line says so).
- The three count notes say "under who was there", which matches the app step "Who was there" but not the plain page heading "Who the text places here".
- The "314 named with the Prophet ﷺ" people stat at Badr is a separate count (side claims in the graph) that happens to equal 314. Not annotated.
- app.js 354 still reads "Opponents are listed last, as dark marks". C7's reasoning applies to it, but the wording is the scholar's call.
- `expeditions/README.md` is stale (row 14 "The 314 (321 found); which Friday" and line 21 "against him as dark marks"). Not a named file, so not edited.
- Ten corpus glosses read "Before the Prophet <wife's name> was married to ...", with the marriage elided. The sign now sits between "Prophet" and her name. Correct but it reads oddly; the fix is in the gloss ("Before the Prophet married her, ...").
- The B3 calendar wording ("computed (tabular), not a source date") is outside this brief.
- The sign is joined by an ordinary space. A no-break space or `white-space: nowrap` would stop it wrapping alone onto a line; that styling is not done.
- The Arabic parenthesis ordering in the plain page's "The text says" line looks wrong; it was already like that.
