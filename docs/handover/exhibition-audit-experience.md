# Exhibition audit: does each showable page work and look its best on the day?

Slice: the experience (works offline, errors, speed, legibility, first impression).
Run on 2026-10-24 for the meeting with a senior Islamic scholar and community leader (laptop, maybe a TV or
projector, maybe no internet). Read only: no repository file was changed except this note.
Companion notes: `docs/handover/exhibition-audit-story.md` (story, numbers, ask).

## Bottom line

- Lead with the Sky Atlas in English, then the Expeditions (Badr, then its halaqa room). Both load in under half a
  second, make no outside requests, and showed 0 errors in every click-through.
- One real blocker: the Atlas in Arabic shows a blank sky (top bar and two note lines, nothing else). The Arabic
  button is on the first screen, so a scholar may well press it. Four lines of CSS fix it (verified, see fix 1).
- Eleven pages (everything except the atlas and the expeditions) are written for the claude.ai wrapper and have no
  doctype, charset or viewport line. Double-clicked in Chrome they are fine. Served by `python3 -m http.server`,
  ten of them print garbled letters (AL-MARÁ¹£AD) and stories-50 draws a blank chart.
- The Expeditions need a tiny local server. Double-clicked they say "Something did not load".
- The lab is dead without internet (three.js comes from a CDN). Do not show `bench/capacity-test.html`.

## How this was tested (short)

- Chrome for Testing 145 through Playwright, headless, software WebGL, at 1440x900 and 1920x1080, plus 125% and 150%
  browser-zoom passes (what a TV needs). Outside requests were blocked to imitate a venue with no internet.
- Every page was opened three ways: over `python3 -m http.server` (as-is), by double-click (`file://`), and
  "wrapped" (a doctype, charset and viewport line added in front, as the claude.ai wrapper does).
- Load = time to the browser load event on this Mac, indicative only (software rendering; first-paint time was not
  captured). Smallest text = the smallest rendered size on screen (SVG text scaled to screen pixels); median is
  weighted by number of characters. Console and page errors are the same at both screen sizes unless stated.
- I clicked through the main interactions on atlas, expeditions, lab (online), demo, generation-1 (all three),
  stories-50 and marsad: all clean, 0 errors.

## Page by page

Open by: dbl = double-click the file in Chrome; srv = local server (command in fix 2); web = needs internet.
Verdict: SHOW, SHOW WITH CARE, DON'T SHOW.

| Page | Open by | Works offline | Errors (console / page) | Load | Smallest / median text px | Verdict | Top visual fixes |
|---|---|---|---|---|---|---|---|
| `atlas/index.html` (English) | dbl or srv | yes (0 outside requests) | 0 / 0 | 0.34 s, ready 0.7 s | 10.5 (12 for real labels) / 14 | SHOW. Lead with it | None blocking. Keep the language on English. The 1920 first screen is the best first impression on the site. |
| `atlas/index.html#ar` or the Arabic button | dbl or srv | yes | 0 / 0, silent | 0.2-0.5 s | 10.5 / 15 | DON'T SHOW until fix 1 | Blank sky: the stage collapses to 0 px tall. The choice is remembered (`marsad-atlas-lang`), so the atlas reopens in Arabic after anyone presses it. |
| `expeditions/dist/index.html` (home, `#about`) | srv | yes (0 outside requests) | 0 / 0 over srv; by double-click 2 errors and "Something did not load" | 0.1-0.3 s | 11.8 / 13.8 (about 11.2 / 16) | SHOW (server needed) | Content column is about 1150 px wide, so it looks small and centred on 1920. Zoom to 125%. |
| `#x-badr-1` Badr expedition | srv | yes | 0 / 0 | 0.12 s, ready 0.3-0.4 s | 11.8 (12.2) / 13.1 | SHOW | Left column is empty below the 3D pane on 1920x1080 while the right column runs on. The Provenance lens button (top right) works. Real moonlit terrain, cited sources. |
| `#halaqa-badr` room view | srv | yes | 0 / 0 | 0.12 s | 12.2 / 14.4 | SHOW | The guide's question sits below the fold (scroll, or Next). Arrow keys step through (`#halaqa-badr-2`). Best layout of the set. |
| `expeditions/dist/text/badr.html` | dbl works | yes | 0 / 0 | 0.15-0.27 s | 11.5 / 16 | Fallback only | Plain page. Use it if the 3D room fails. |
| `pages/marsad.html` | dbl | yes (fonts fall back) | 0 / 0 | 0.3-0.6 s | 5.8 / 15 | SHOW | About 700 characters of diagram labels are 6-7 px and the nav is 11.2 px: raise them, or scroll past the diagrams on a TV. |
| `pages/road-ahead.html` | dbl | yes | 0 / 0 | 0.1-0.5 s | 10.4 / 15.7 | SHOW | None. |
| `pages/reviewers-brief.html` | dbl | yes | 0 / 0 | 0.1-0.5 s | 8.5 / 15.3 | SHOW WITH CARE (SHOW after fix 4) | "What we lose" explanations squeezed into a 27 px column. 8.5 px "Source:" captions. This is the page that asks the scholar for corrections. |
| `pages/build-with-us.html` | dbl | yes, except its two claude.ai links (private until shared) | 0 / 0 | 0.1-0.4 s | 9.8 / 13.6 | SHOW WITH CARE | Pale small mono captions. Test the "Try it" link signed out before anyone clicks it. |
| `demo/index.html` | dbl | yes | 0 / 0 | 0.2-0.6 s | 9.9 / 10.9 (77% under 12 px) | SHOW WITH CARE | Zoom to 125-150% on a TV. Label collision ("Report: Hijrah vi..." over "Route waypoint 2"). Truncated "Sheltering at Ghar...". |
| `generation-1/index.html` | dbl | yes | 0 / 0 | 0.2-0.6 s | 9.9 / 10.9 (85% under 12 px) | SHOW WITH CARE (SHOW after fix 5) | The chart is a square: 1039 px tall at 1440x900 and 1519 px at 1920x1080, so only 80% / 66% is on screen. Ten edge labels are clipped. |
| `generation-1/at-scale.html` | dbl | yes | 0 / 0 | 0.2-0.6 s | 9.9 (10.4) / 13.1 (45% under 12 px) | SHOW WITH CARE | Small chart in a big black canvas, overlapping labels at top and bottom, the card covers the lower left. Drag smoothness could not be judged (software rendering). |
| `generation-1/wider-network.html` | dbl | yes | 0 / 0 | 0.3-0.6 s | 9.6 / 13.3 | SHOW WITH CARE | Right pane is empty until a person is clicked: click Abu Bakr first. Grey mono text on near-black. |
| `stories-50/index.html` | dbl only | yes by double-click. Over the python server: blank chart | 0 / 0 by double-click. Over the python server: 1 page error | 0.6-0.7 s | 9.5 / 12.8 | SHOW (double-click only) | None once opened the right way. |
| `bench/capacity-test.html` | dbl | yes | 0 / 0 | 0.3-0.5 s | 10.2 / 10.4 (98.5% under 12 px) | DON'T SHOW | A hazard-tape synthetic capacity test, not a visitor page. |
| `lab/hijrah-night-v2/index.html` | web | NO: three.js is loaded from cdn.jsdelivr.net, panels stay empty, 1 page error "THREE is not defined" | online 0 / 0; offline 0 / 1 | online 8.8-9.7 s (878 KB, sandbox); offline loads in 0.2-1.0 s but is dead | 10.5 / 15 (12.5 online) | SHOW WITH CARE, only with internet (fix 3) | Online it works end to end (Begin, Next x3 clean). Fonts fall back gracefully. |
| `site/`, `review/` | n/a | n/a | n/a | n/a | n/a | Not tested | No built HTML in the repo (templates only; `site/dist`, `review/dist` and `build/graph.ttl` are absent). I did not attempt a build. |

Notes on the table:
- "yes (fonts fall back)": the eleven wrapper-style pages and the lab ask Google Fonts for a stylesheet; offline it
  fails and the page falls back to Georgia, Helvetica and a system mono. The atlas and the expeditions ask for nothing.
- The Arabic atlas, the lab offline, and the expeditions by double-click are the three silent or ugly failures.
- No emoji on any showable page (only plain check marks, crosses and trigram symbols).

## Five things to fix before the meeting (ranked)

### 1. Atlas in Arabic shows a blank sky

- Cause: `.app` in `atlas/index.html` (line 52) is a 3-row grid, `grid-template-rows: auto auto 1fr`. Arabic un-hides the
  note band `#lang-note` (line 401, toggled at line 3766) as a fourth child, so the stage lands in an implicit row and
  collapses (canvases 0 px tall). There is no console error. The language is saved in localStorage
  `marsad-atlas-lang` (written at line 3767, read at line 3848).
- Fix, verified at runtime in both languages (add after the `.app` rule):
  ```css
  .app{grid-template-rows:auto auto auto 1fr}
  #lang-note{grid-row:2}
  .app>p.band:not(#lang-note){grid-row:3}
  #stage{grid-row:4}
  ```
- Until then: never press the Arabic button or open `#ar`. If it was pressed on the demo laptop, press English (or clear
  `marsad-atlas-lang`). `atlas/check.cjs` has no Arabic layout test; add one (stage taller than 300 px in Arabic).
- Evidence: before, `<audit scratchpad>/audit-experience/shots/atlas-ar-1440.png`; after, `<audit scratchpad>/audit-experience/shots/diag-atlas-ar-with-css-fix.png` and
  `<audit scratchpad>/audit-experience/shots/diag-atlas-en-with-css-fix.png`.

### 2. Open the pages the right way, or make them robust

- Eleven files have no `<!doctype>`, no charset and no viewport (they get them from the claude.ai wrapper): the four
  `pages/*.html`, `demo/index.html`, the three `generation-1/*.html`, `stories-50/index.html`, `bench/capacity-test.html`
  and `lab/hijrah-night-v2/index.html`. Over `python3 -m http.server` (which sends no charset) Chrome reads them as
  windows-1252 in quirks mode: "AL-MARÁ¹£AD" for "AL-MARSAD", "GhÄr Thawr", "Â€”" for an em dash, in ten of the eleven
  (all but bench). `stories-50` also stops on "Invalid regular expression: /[Ì€-Í¯]/g" and draws a blank chart.
  Double-click in Chrome (UTF-8 is detected) and the claude.ai wrapper are both fine.
- On the day: double-click these files in Chrome, never serve them with the python server. For the expeditions run
  from the repository root, and keep it running:
  `python3 -m http.server 8770 --directory expeditions/dist`, then open `http://localhost:8770/#x-badr-1` and
  `http://localhost:8770/#halaqa-badr`. Fallback: double-click `expeditions/dist/text/badr.html`.
- Durable, one line at the top of each of the eleven files:
  `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">`.
  Verified by adding it in the "wrapped" run (all eleven render correctly). Not yet checked: how the claude.ai wrapper
  treats a page that already has a doctype, so test one before republishing artifacts.
- Chrome only was tested. Safari and Firefox over `file://` are untested and may garble these files.
- Evidence: `<audit scratchpad>/audit-experience/shots/gen1-1920.png` (garbled and 66% visible, as served), `<audit scratchpad>/audit-experience/shots/marsad-1440.png`,
  `<audit scratchpad>/audit-experience/shots/stories50-1440.png` (blank chart), `<audit scratchpad>/audit-experience/shots/exp-home-file-1440.png` (expeditions by double-click).

### 3. The lab is dead offline

- `lab/hijrah-night-v2/index.html` line 402 loads `https://cdn.jsdelivr.net/npm/three@0.149.0/build/three.min.js`.
  Offline, `THREE` is undefined and the panels stay empty. There is no vendored copy in the repository.
- Fix, for the maintainer (I downloaded nothing): save that file (about 600 KB) next to the page and change the
  `src` on line 402 to `three.min.js`. Or open the page once online in the same Chrome profile just before leaving
  (jsDelivr caches for a long time, so a reload often works offline; not guaranteed). Or leave the lab out when offline.
- Evidence: offline `<audit scratchpad>/audit-experience/shots/lab-hijrah-v2-wrapped-1440.png`; online `<audit scratchpad>/audit-experience/shots/lab-hijrah-v2-wrapped-online-1920.png`.

### 4. reviewers-brief: the "what we lose" explanations are squeezed into a sliver

- Cause: `ol.losses li` (lines 97-107) is a two-column grid, `1.7rem minmax(0,1fr)`, but holds three items
  (`::before`, `<b>`, `<span>`), so each `<span>` lands in the 1.7rem column (27 px wide). Markup at lines 225-230.
- Fix, verified (the paragraph goes from 27 px to 557 px wide): add `ol.losses span{grid-column:2}`.
- Also raise the 8.5 px "Source:" captions. This is the page that asks the scholar where the atlas is wrong.
- Evidence: `<audit scratchpad>/audit-experience/shots/reviewers-brief-wrapped-1440.png` before, `<audit scratchpad>/audit-experience/shots/diag-reviewers-brief-with-css-fix.png` after.

### 5. The dark chart pages on a big screen

- `generation-1/index.html`: `svg#scene` is `width:100%;height:auto;min-height:640px` over a square `viewBox="0 0 800 800"`,
  so the chart is as tall as it is wide and runs off the screen. Fix, verified at runtime (100% of the chart visible at
  both sizes, and 0 of 101 labels clipped, down from 10): `svg#scene{height:calc(100vh - 80px);min-height:0}` and set
  `viewBox="-25 50 850 700"` (the drawing's own box is x -15..815, y 60..740).
- Text size: demo and generation-1 have a median of 10.9 px (about 80% of text under 12 px). On a TV press Cmd and + to
  125-150%. That helps `demo/index.html`; it does not fix generation-1 by itself.
- `generation-1/wider-network.html`: open with a person already selected (click Abu Bakr) so the right pane is not empty.
- `generation-1/at-scale.html`: fine to show, but small; zoom in or drag the sky closer.
- Evidence: `<audit scratchpad>/audit-experience/shots/diag-gen1-with-fix-1920.png` (after) against `<audit scratchpad>/audit-experience/shots/gen1-wrapped-1920.png` (before).

## Run sheet for the day (suggested)

1. Before leaving, with internet: start the expeditions server (fix 2), confirm `#x-badr-1` and `#halaqa-badr` load;
   open the lab once if you plan to show it; set the atlas language to English.
2. Turn Wi-Fi fully off for a rehearsal. A half-connected network (captive portal, hanging DNS) could stall the
   render-blocking Google Fonts stylesheet on the eleven wrapper-style pages. I blocked requests outright, which fails
   fast, so the hanging case is reasoned, not tested.
3. Chrome tabs, in order: Atlas (double-click) > `localhost:8770/#x-badr-1` > `#halaqa-badr` > `pages/marsad.html` >
   `demo/index.html` > `stories-50/index.html` > generation-1 pages (at-scale, then the main chart after fix 5, then
   wider-network with Abu Bakr clicked) > `pages/road-ahead.html`, `pages/build-with-us.html`,
   `pages/reviewers-brief.html` as reading pages > the lab last, only if online. Never open `bench/`.
4. On a TV or projector: full screen, then Cmd and + to 125-150%.

## Caveats

- Chromium only (Chrome for Testing 145). Safari and Firefox untested.
- Headless software rendering: load times are indicative and first-paint time is null; frame rates and drag
  smoothness are not judged. The lab's online load time comes from a sandbox network.
- The two claude.ai links on build-with-us were not opened (published artifacts are private until shared).
- `site/` and `review/` were not built, so their pages are untested.
- Every page requests `/favicon.ico` (none declares an icon): a harmless 404 in the console on a plain server.
- The fixes in 1, 4 and 5 were validated by injecting CSS at runtime only; nothing was written to the repository.

## Screenshots

Folder: `<audit scratchpad>/audit-experience/shots/` (143 files). Naming: `<page>-<width>.png` as served by the python server (garbled for the wrapper-style
pages), `-wrapped-` as the claude.ai wrapper renders them, `-file-` by double-click, `-full` the whole page,
`probe-*` after clicking through, `diag-*` diagnostics and verified fixes.

First impressions at 1920x1080:
- `<audit scratchpad>/audit-experience/shots/atlas-1920.png`
- `<audit scratchpad>/audit-experience/shots/exp-home-1920.png`
- `<audit scratchpad>/audit-experience/shots/exp-badr-1920.png`
- `<audit scratchpad>/audit-experience/shots/exp-halaqa-badr-1920.png`
- `<audit scratchpad>/audit-experience/shots/marsad-wrapped-1920.png`
- `<audit scratchpad>/audit-experience/shots/road-ahead-wrapped-1920.png`
- `<audit scratchpad>/audit-experience/shots/reviewers-brief-wrapped-1920.png`
- `<audit scratchpad>/audit-experience/shots/build-with-us-wrapped-1920.png`
- `<audit scratchpad>/audit-experience/shots/demo-wrapped-1920.png`
- `<audit scratchpad>/audit-experience/shots/gen1-wrapped-1920.png`
- `<audit scratchpad>/audit-experience/shots/gen1-at-scale-wrapped-1920.png`
- `<audit scratchpad>/audit-experience/shots/gen1-wider-wrapped-1920.png`
- `<audit scratchpad>/audit-experience/shots/stories50-wrapped-1920.png`
- `<audit scratchpad>/audit-experience/shots/bench-wrapped-1920.png`
- `<audit scratchpad>/audit-experience/shots/lab-hijrah-v2-wrapped-online-1920.png`
- `<audit scratchpad>/audit-experience/shots/lab-hijrah-v2-1920.png` (offline, dead)

Problems and fixes:
- `<audit scratchpad>/audit-experience/shots/atlas-ar-1440.png`, `<audit scratchpad>/audit-experience/shots/atlas-ar-1920.png`, `<audit scratchpad>/audit-experience/shots/diag-atlas-ar-with-css-fix.png`, `<audit scratchpad>/audit-experience/shots/diag-atlas-en-with-css-fix.png`
- `<audit scratchpad>/audit-experience/shots/gen1-1920.png`, `<audit scratchpad>/audit-experience/shots/marsad-1440.png`, `<audit scratchpad>/audit-experience/shots/stories50-1440.png`, `<audit scratchpad>/audit-experience/shots/exp-home-file-1440.png`
- `<audit scratchpad>/audit-experience/shots/reviewers-brief-wrapped-1440.png`, `<audit scratchpad>/audit-experience/shots/diag-reviewers-brief-with-css-fix.png`
- `<audit scratchpad>/audit-experience/shots/diag-gen1-with-fix-1440.png`, `<audit scratchpad>/audit-experience/shots/diag-gen1-with-fix-1920.png`
- `<audit scratchpad>/audit-experience/shots/lab-hijrah-v2-wrapped-1440.png`, `<audit scratchpad>/audit-experience/shots/probe-online-lab-03-next3.png`
- `<audit scratchpad>/audit-experience/shots/diag-exp-lens-on.png`, `<audit scratchpad>/audit-experience/shots/exp-text-badr-1440.png`

TV zoom passes:
- `<audit scratchpad>/audit-experience/shots/demo-wrapped-zoom1.5-1280.png`, `<audit scratchpad>/audit-experience/shots/demo-wrapped-zoom1.25-1536.png`
- `<audit scratchpad>/audit-experience/shots/gen1-wrapped-zoom1.5-1280.png`, `<audit scratchpad>/audit-experience/shots/gen1-wrapped-zoom1.25-1536.png`
- `<audit scratchpad>/audit-experience/shots/gen1-at-scale-wrapped-zoom1.5-1280.png`, `<audit scratchpad>/audit-experience/shots/gen1-wider-wrapped-zoom1.5-1280.png`
- `<audit scratchpad>/audit-experience/shots/stories50-wrapped-zoom1.5-1280.png`, `<audit scratchpad>/audit-experience/shots/bench-wrapped-zoom1.5-1280.png`

Click-throughs:
- `<audit scratchpad>/audit-experience/shots/probe-atlas-01-start.png` to `<audit scratchpad>/audit-experience/shots/probe-atlas-07-sky.png`, `<audit scratchpad>/audit-experience/shots/probe-atlasar-01-start.png` to `<audit scratchpad>/audit-experience/shots/probe-atlasar-03-after-click.png`
- `<audit scratchpad>/audit-experience/shots/probe-exp-01-home.png` to `<audit scratchpad>/audit-experience/shots/probe-exp-08-uhud.png`
- `<audit scratchpad>/audit-experience/shots/probe-file-demo-after-node-click.png`, `<audit scratchpad>/audit-experience/shots/probe-file-gen1-after-person-click.png`, `<audit scratchpad>/audit-experience/shots/probe-file-atscale-after-drag.png`,
  `<audit scratchpad>/audit-experience/shots/probe-file-wider-after-person-click.png`, `<audit scratchpad>/audit-experience/shots/probe-file-wider-incidents-tab.png`,
  `<audit scratchpad>/audit-experience/shots/probe-file-stories-after-search.png`, `<audit scratchpad>/audit-experience/shots/probe-file-marsad-end.png`

Scripts and raw results (outside the repository): `<audit scratchpad>/audit-experience/audit.cjs` (harness), `<audit scratchpad>/audit-experience/probe.cjs`,
`<audit scratchpad>/audit-experience/probe-file.cjs`, `<audit scratchpad>/audit-experience/results-file.json`, `<audit scratchpad>/audit-experience/results-http.json`, `<audit scratchpad>/audit-experience/results-wrapped-part.json`.
