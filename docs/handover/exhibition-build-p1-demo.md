# Exhibition build, P1: the demo page (A1 to A3, B9) and the stories-50 charset

Branch `claude/exhibition-p1`, cut from `main`. One commit, not pushed. Touches only `demo/` and
`stories-50/` (plus this note). Nothing in `ontology/`, `demo/build.py` or `demo/data.json` changed:
the data stays as the ontology holds it, and the page frames it.

Sources: `docs/handover/exhibition-audit-scholar.md` (rows A1, A2, A3, B9 and list item 4) and
`docs/handover/exhibition-build-brief.md` (P1). Those two files live in the exhibition worktree, not on
this branch.

## At a glance

| Finding | What the page does now | Left for the maintainer or a scholar |
|---|---|---|
| A1 ascription | Shows "for a scholar to decide". The class (mawqūf) is not rendered anywhere. | The value is still in `thawr.ttl`, `data.json` and the JSON embedded in `index.html`. A scholar rules on marfūʿ or mawqūf. |
| A2 source date and gap | "Source date, as recorded" with "not reviewed by a scholar". The CE year and the "attestation gap" are gone ("not computed"). | `thawr.ttl` holds 256 AH, al-Bukhārī's death year, as the composition date. A scholar and the maintainer should correct it. |
| A3 "Three disputes" | The count is removed. A note, derived from the data, says the file models three questions as disputes, none adjudicated, and that their positions are not shown. | Stating the disputes in a scholar's words needs a scholar. The positions in the example are placeholders. |
| B9 Arabic marks | Every Arabic run on the page carries `lang="ar" dir="rtl"`. | `lab/hijrah-night-v2/template.html:240` (out of scope). |
| stories-50 charset | `<meta charset="utf-8">` added to the template and the generated page. | The published copy now has the tag twice (see below). |

## A1. The ascription was the system's ruling

- Where the value comes from: `ontology/examples/thawr.ttl` line 502,
  `mrs:terminalAscription mrs:asc_mawquf`, commented as a scholar's classification. `demo/build.py`
  projects it unchanged into `demo/data.json` (`report[0].ascription`). The ontology is out of bounds, so
  it was not touched.
- What changed: `demo/index.template.html`, function `reportFacts()`. The report's panel (the node
  panel, and step 2 of the evidence ladder) now reads "ascription: for a scholar to decide", in the page's
  empty-state style, with a grey line under it: "A class is recorded in the data. It is not shown until a
  scholar has reviewed it." The value itself is never printed. The report node still carries
  `ascription`, but only so the page can tell whether a class is recorded.
- Left over:
  - The raw string `mawqūf — ascribed to a Companion` is still in `demo/data.json` and in the JSON that
    `index.html` embeds (visible in view-source, not on the page). If it must not leave the file at all,
    drop it from the SPARQL in `demo/build.py` and from the report node in the template. I did not,
    because `build.py` is a faithful projection and this is a question of display.
  - The ontology cannot simply drop the field: `ontology/shapes.ttl` (line 254) requires exactly one
    `terminalAscription` on a report.
  - Whether the Hijrah report is marfūʿ or mawqūf is for a scholar. The page now claims neither.

## A2. "Source composed 256 AH" and the attestation gap

- Where the value comes from: `ontology/examples/thawr.ttl` lines 507 to 512, `mrs:sourceDate` with
  `nativeValue "٢٥٦"`, commented "when the CONTAINING WORK was composed". 256 AH is the year al-Bukhārī
  died. The audit's reading is right: the data names it as the composition date of the work. The
  template then turned it into a CE year and subtracted 622.
- What changed, in `reportFacts()` and `ladder()` step 2:
  - "source composed" becomes "source date, as recorded", the digits followed by AH, with the grey line
    "As recorded in the data; not reviewed by a scholar."
  - The CE year and the subtraction are removed. The row now reads "attestation gap: not computed. It
    waits on a reviewed source date." `sourceStart` is no longer carried on the report node.
  - The ladder note ("The gap is shown, not buried ... first written down two centuries later") asserted
    the gap, so it is rewritten: "The model keeps two dates apart", ending with "this page computes no gap
    and draws no conclusion from it."
- Why not the audit's other option, "compiler died 256 AH": that would be a scholarly statement written
  into the page by hand, where the page says nothing is. The wording is for the scholar, so the label stays
  neutral.
- Left over:
  - The data. A scholar and the maintainer should decide what `sourceDate` holds for this report, and fix
    `thawr.ttl` (then run `demo/build.py`). If the gap is shown again, it should wait for that.
  - A small audit correction: the template in this tree printed "c. 869 CE" and "c. 247 years" (the
    year of 0869-12-09), not the 870 and 248 the audit quotes. Moot now.

## A3. "Three disputes"

- Where it came from: the number was typed into the opening line of `intro()`, not derived. The data has
  3 disputes, 7 placeholder positions and 0 adjudicated, and nothing on the page renders a dispute or a
  position.
- What changed: "Three disputes." is removed from the opening line. A new note in `intro()` is built from
  `DATA.disputes` and `DATA.adjudicated`, so it stays true if the data changes, and it is left out when
  there are no disputes: "Disputes are not drawn here. The data file models three questions as disputes,
  none of them adjudicated. This page does not show their positions: what counts as a dispute, and who
  holds which view, is for a scholar to say."
- Left over:
  - The audit's other option, to state the three disputes in a scholar's words, needs a scholar. Nothing
    was written by hand.
  - The data itself: `thawr.ttl` is marked "ILLUSTRATIVE ONLY. NOT SCHOLAR-VERIFIED" (line 32), and its
    own comment near line 600 says the positions in the second dispute are not necessarily mutually
    exclusive. Whether these are disputes at all is for a scholar.
  - The unused `.positions` CSS is still in the template. It is harmless.

## B9. Arabic without language and direction

- Where the Arabic comes from: `demo/data.json` (the report's date digits, the event's native duration
  "ثلاث ليال", four place name phases) and the symbol ﷺ, twice in the template. Nothing else on the page
  is Arabic.
- What changed in `demo/index.template.html`:
  - A helper `ar()` escapes text and wraps each Arabic run, including Arabic-Indic digits and ﷺ, in
    `<span class="ar" lang="ar" dir="rtl">`. It is used for place names, node headings, the facts list and
    the duration. It is for text between tags only; a comment above it says so.
  - The ﷺ in the intro note is wrapped by hand in the same span.
  - The ﷺ drawn in the SVG carries `lang="ar" dir="rtl"` and also `direction="rtl"`, because `dir` has no
    effect in SVG and `direction` is what SVG honours. It stays centred.
  - `F()` (the facts-list row builder) moved out of `select()` so the ladder can share it with the node
    panel.
- Checked: the only Arabic characters in the template source are ﷺ (the SVG text, the intro note and
  two code comments). Every other Arabic string reaches the page from `data.json` through `ar()`. In the
  generated page, none of the 22 panel states (intro, 15 nodes, 4 ladder steps, 3 route segments) has
  Arabic outside a `lang="ar" dir="rtl"` span.
- Left over:
  - `lab/hijrah-night-v2/template.html:240` (`<div class="ar">الهجرة</div>`) has no `lang`. It is in
    `lab/`, which this task may not touch.
  - The ﷺ in `stories-50` (two places) has no `lang` or `dir`. The task for that page was the charset
    only. The same `ar()` idea would do it.
  - B10 (the transliteration `'A'isha` in the report label) is a different row and was not touched.

## stories-50 charset

- `stories-50/index.template.html` now starts with `<meta charset="utf-8">`, and
  `stories-50/index.html` was regenerated with `stories-50/build.py`. These are the only two HTML files in
  `stories-50/`. The generated diff is that one line. `data.json` is unchanged.
- Side effect, outside this task: `site/experiments.py` `wrap()` makes the published copy under
  `site/dist/experiments/` and adds its own `<meta charset="utf-8">`. The stories-50 copy now has two.
  Browsers ignore the second, and `site/check_html.py` does not flag it, but it is untidy. The fix belongs
  in `site/` (skip the tag when the fragment already has one); I did not touch `site/`.
- The demo template is also a fragment without a charset. The published copy gets one from `wrap()`, but
  `demo/index.html` opened straight from disk has none. One line in the demo template would fix that. It
  was not asked for, so it is not done.

## Checks run

From `scripts/check_all.sh`, with the project's venv Python:

- `ontology/tools/stories50_to_ttl.py --check`: "stories-50.ttl is up to date".
- `demo/build.py` and `stories-50/build.py`: run again after the last edit; the tree did not change, so
  the committed pages are what a fresh build writes. The `islands_current` check (no diff and no
  untracked files in `demo generation-1 stories-50 sira-network atlas` after a fresh build of all five)
  was clean with the changes staged.
- The demo and stories-50 pages are copied into the published site, so I also ran `site/build.py` (exit
  0), `site/check_html.py` (1014 pages, OK), `site/check_budget.py` (OK) and `site/tests` (143 tests, OK).

Not run: every Playwright step (`atlas`, `site`, `learn`, `ask` browser checks). Playwright and its
Chromium are not installed here and downloads were not allowed. No browser check in `check_all.sh`
covers `demo/` or `stories-50/`, so none of them could have caught these changes anyway.

Instead, for the demo page:

- A throwaway stub-DOM run of the page's own script over all 22 panel states: no Arabic outside
  `lang="ar" dir="rtl"`, no ascription value, none of the old claims ("source composed", a CE year, a
  count of years, "Three disputes"). The same run on the old page gave 12 failures, so it does catch them.
  The script is not committed.
- A one-shot headless Chrome screenshot of the intro, the report node and ladder step 2 (a local file, no
  server). The new wording and the Arabic digits render as intended. One thing the pictures show that was
  already there and is not part of the audit: the label of the report node ("Report: Hijrah, vi...")
  overlaps the label "Route waypoint 2". The layout was not touched.

A browser check for the demo (open it, select the report node, read the panel) would catch this kind of
regression in future; nothing in `check_all.sh` opens `demo/index.html` today.

## Decisions for the maintainer

1. Correct or replace `sourceDate` 256 AH in `ontology/examples/thawr.ttl` with a scholar (A2).
2. A scholar to rule on the report's ascription, then decide whether the page may show it (A1).
3. Whether to drop `ascription` from the SPARQL in `demo/build.py` so the string leaves the page source (A1).
4. Whether `site/experiments.py` `wrap()` should skip a charset tag that is already there.
