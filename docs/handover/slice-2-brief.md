# Slice 2 brief — one explorer, reader tier first

Context: docs/13-platform-direction.md §2 (D1 depths, D3, D4) and §4 slice 2; docs/05-ux-architecture.md §3, §7, §9, §10. Read docs/handover/slice-1-summary.md and slice-1c.md first (slice 2 starts only after 1c is committed). Do not read chat history; this file is the brief.

## Goal
Every person, event, place and story in `build/graph.ttl` has a plain, linkable, accessible HTML page; any entity is one link away; works with JS off; every page is within the 300 KB reader-tier budget, checked by a script that fails the build.

Slice 2 is split into three parts, one session each, in order. Each writes `docs/handover/slice-2x.md` (≤60 lines).

## Rules for all of slice 2
- **Data comes from the graph only.** The site generator reads `build/graph.ttl` (built by `ontology/build_graph.py`). It never reads the old islands' JSON or Markdown.
- **Status is always visible.** Every claim shown carries its `assertionStatus` (proposed / under review / accepted) and every entity its coverage (`stub` etc.) as a text label, not colour alone. Never upgrade a status; never invent Arabic names, dates or summaries. Where the graph has no value, show nothing or "not yet recorded" — never a placeholder that looks like data.
- **Depth is disclosure, not a separate product** (doc 13 §2 D1). Top of each page: name, type, short who/what/when/where from graph fields. Below: the assertions with role, status and source. Below that: raw IRIs and a link to the Turtle for that entity. Nothing at the top may say more than the assertions below support.
- **Every UI string is a translation key** in `site/i18n/en.json`; no hard-coded English in templates. Data strings (names, titles) come from the graph with their language tags; show Arabic original beside the English form where the graph has it, with `lang="ar" dir="rtl"` on that element.
- **Logical CSS only** (`margin-inline-start`, `padding-block`, `inset-inline-end`, …). A grep for `left|right` in CSS property names must find nothing except in comments.
- **Dates:** show Hijri and Gregorian only as recorded in the graph, with its uncertainty; never compute or round one into a false-precision date.
- **Weight:** system font stack in the reader tier (no web fonts, no external requests). No framework. Plain HTML + one small shared CSS file; JS only as progressive enhancement.
- **Stable URLs** derived from the canonical ID payload, e.g. `/person/<id>/`, `/event/<id>/`, `/place/<id>/`, `/story/<id>/`. Never from a name.
- Output goes to `site/dist/` (gitignored). Standard library + rdflib only, in the existing `.venv`.
- Commit on the current branch; message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Do not push.

## Display decisions from the maintainer (docs/handover/maintainer-answers-1.md)
These override anything above that conflicts. Put each rule in one place in code (`site/display.py` or similar) so it can be changed later.
- **Names:** best-known form first, in **popular transliteration** (Abu Bakr as-Siddiq). Use identity.csv `preferred_name_en` when it is already in popular form. Otherwise derive the popular form mechanically from the scholarly form: strip diacritics, write ʿ and ʾ as an apostrophe or drop them, and assimilate al- before sun letters. Document the rules and test them. Show the scholarly form and any full name in the details layer, and keep it in the search index.
- **Dates:** Gregorian first, then Hijri, "622 CE (1 AH)", only as recorded, with uncertainty in plain words ("around").
- **Places:** classical name, modern name in brackets when the graph has one.
- **Possibly-same people** (identity rows marked needs-review): show them as separate people with no hint. Show nothing until a scholar rules.
- **Groups and tribes:** full pages of their own (add `/group/<id>/` and a group index).
- **The Prophet ﷺ:** a distinct, respectful page layout (no "profile card" treatment). ﷺ after every mention of him. Other honorifics (رضي الله عنه / عنها) on every mention **only where the graph records the person as a Companion and their gender**. Never guess either; list the gaps in the handover.
- **Pages read story first, chain one tap below** for the public. Study and Research show the chain (the evidence) first (round 2, R9). The home page has **three doors**: Discover (stories), Study (people, timelines), Research (sources and data) (R4). 2a built a graph-first home; 2c turns it into the three doors.
- **50 Stories are AI-generated** (maintainer answer E35). Every story page shows its status at the top in plain words ("Draft, not yet reviewed by scholars"). The details layer says it was generated with AI and its authenticity is unknown.
- **Plain-words option:** keep every Arabic term linked to the glossary in 2a. The on/off "plain words" toggle comes in 2c.
- No human figures; abstract icons are fine. The current look is a placeholder, so keep styling minimal and token-based.

## 2a — static generator and pages
1. `site/build.py`: runs or reads `build/graph.ttl`, writes one page per person, event, place, story, plus an index page per type (A–Z, with counts and coverage) and a home page that orients a first-time visitor (what this is, what is verified and what is not, links to the four indexes). Templates in `site/templates/` using `string.Template` or a tiny helper — no Jinja unless it is already installed.
2. Each entity page: the depth layout above; every linked entity is a link to its page; breadcrumbs and a persistent "home" link (doc 05 §10).
3. A glossary page for Arabic terms that appear in the graph labels (only terms with a definition already present in the repo docs; list the rest as "definition needed").
4. `site/check_budget.py`: for every page, sums HTML + every same-site CSS/JS/image it references; fails (non-zero exit) above 300 KB, prints the five heaviest pages. Also fails on any external URL in `src`/`href` of a stylesheet or script.
5. Semantic HTML: one `h1`, landmarks, skip link, `lang` attributes; check a sample with `python -m html.parser` or a small validator script for unclosed tags.

Done when: `build_graph.py && site/build.py && site/check_budget.py` runs clean; Abū Bakr's page lists his stories, incidents and kinship ties from all sources; pages render with JS disabled (check one page with Playwright, JS off, screenshot into the handover folder is not needed — record the check in the note).

## 2b — search with spelling tolerance
1. Build-time search index (`site/dist/search.json`, keep it small: id, type, display names, normalised keys).
2. One normaliser used at build and in the browser: case-fold, strip diacritics and ʿ ʾ ' marks, unify `b.`/`bin`/`ibn`, optional `al-`/`el-`, Arabic normalisation (alif forms → ا, ة → ه, ى → ي, strip tashkīl and tatweel). Port the same rules to JS; a Python test feeds both implementations the same cases and compares output (run the JS with `node` if available, else document how it was checked).
3. Must find Abū Bakr from: "Abu Bakr", "Abū Bakr", "abubakr", "ابو بكر", "أبو بكر".
   Also make the popular display form consistent (a 2a leftover): apply sun-letter assimilation to every `al-`, including labels written without scholarly marks (today "Anas ibn al-Nadr" keeps `al-` while "Abū Bakr al-Ṣiddīq" becomes "as-Siddiq"). Keep `b.` as recorded unless the maintainer asks otherwise (`display.EXPAND_B_TO_IBN`). Display and search must share these rules.
4. No-JS fallback: the search box submits to the A–Z index pages. Empty result follows doc 05 §3 empty-state rule: say what was searched and that the corpus is small and unverified — never a blank.
5. Search JS + index count toward the budget for the page that loads them.

## 2c — thread view, CI, retiring the islands
1. Port the "follow the thread" interaction from `generation-1/wider-network.template.html` as a progressive enhancement on entity pages (works only on top of the plain links; with JS off the page is complete).
2. GitHub Actions workflow: set up Python, install rdflib + pyshacl, run `ontology/build_graph.py`, `site/build.py`, `site/check_budget.py`, and the 2b normaliser test. Any failure fails the job.
3. **Deploy to Cloudflare Pages** (decided 15 October 2026). After the checks pass on a push to `main`, the workflow deploys `site/dist/` with Cloudflare's `wrangler pages deploy` (pin its version). It runs only when the `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` repository secrets exist; otherwise it prints that the deploy was skipped and still passes. Never deploy from a pull request. Going public is the maintainer's decision: they create the Cloudflare account, the Pages project and the secrets. Write those steps in the handover, plus how to keep the site private to scholars and the team first (Cloudflare Access in front of the Pages project).
4. **Three doors and the plain-words option** (maintainer-answers-2.md R4, R9; round 1 B11). The home page offers Discover, Study and Research. Discover lands on stories, story first. Study and Research land on the same entity pages at the evidence (for example an `#evidence` anchor), so there is still one page per entity and one citable URL, and it works with JS off. No accounts. Add the on/off "plain words" option for Arabic terms (glossary-backed; JS only as an enhancement; the default is readable without it).
5. An "Experiments" page linking the old demo, generation-1 and stories-50 pages, labelled as earlier prototypes. Do not delete them.
6. `docs/handover/slice-2-summary.md` (≤30 lines, for the maintainer): what a visitor can now do, page counts, page weights, what is still unverified.

## Out of scope for slice 2
Arabic UI strings and RTL switch (slice 9 — but nothing in 2 may block it), PWA/offline, a custom domain (the name may change), network/timeline/map views, review tooling.

## Stop rule
Keep tool output short. Stop and write the handover if context nears 200k.
