# 13 — Platform Direction: from Phase 0 corpus to a living knowledge graph

**Status:** working draft for brainstorming, 15 October 2026. Nothing here overrides docs 00–12; where it narrows them, it says so.

## 1. Where we are

Phase 0 settled the hard questions: the report (khabar) is the atomic unit, grading is an act by an agent, no pixel without provenance, AI never asserts. What exists in code is four **separate islands**, each with its own build script and static page:

| Island | Content | In the ontology? |
|---|---|---|
| `demo/` + `ontology/examples/thawr.ttl` | One Hijrah event, end to end | Yes |
| `generation-1/` | The Prophet ﷺ + 35 Companions, kinship, Badr | Yes |
| `ontology/corpus/seed-incidents.ttl` | 57 people, 100 incidents | Yes |
| `stories-50/` | 50 stories, 171 named people, 366 links | **No** — parsed from Markdown |

All of it is `stub` / `proposed`. The same person (e.g. Abū Bakr) exists up to four times with no shared identifier.

**The gap:** a large architecture and a small, disconnected product. The next step is not more architecture — it is **one graph, one engine, one app**.

## 2. Decisions taken (15 October 2026)

| # | Question | Answer | What it forces |
|---|---|---|---|
| D1 | First audience | **The whole world** — anyone, anywhere | Accessibility and low cost of access outrank visual ambition |
| D2 | Scholarly review | **Scholars onboarded; more needed for in-depth review, later** | Reviewer time is the scarcest resource; the system must spend it well |
| D3 | Language | **English first, then Arabic.** No others early | Arabic is the *second UI*, but must not be a retrofit |
| D4 | Model | **Completely non-profit, funded by donations from Muslims worldwide** | Running cost near zero; trust and transparency are the product |

### D1 → design rules for "the whole world"

- **Reading needs no account.** No login, no paywall, no tracking, no ads.
- **Static-first.** The public site is precomputed files on a CDN. A graph database is a *build-time* tool, not a runtime dependency. This is also what makes D4 affordable and keeps the "data must outlive the app" rule.
- **Low-end Android on 3G is the reference device.** Budgets from doc 05 §7 (≤300 KB reader tier, ≤2 MB interactive tier) are enforced in CI from the first slice.
- **The text tier (L0) ships first** — every person, event, place and report has a plain, linkable, screen-reader-friendly page. The network view is an enhancement on top of it, never the only way in.
- **Installable and offline** (PWA) once the reader tier is stable.
- **Assume no shared background.** A first-time visitor who has never heard of Badr must be able to orient: short "who/what/when/where" summaries on every page, a glossary for every Arabic term.

### D2 → design rules for scarce scholars

- **AI proposes, scholars dispose.** Machine extraction fills the queue; human review is the only route to `accepted` (`mrs:as_accepted`).
- **Status is always visible to the public.** Every claim shows `proposed`, `under review` or `accepted` — honesty about coverage is a feature, not an embarrassment.
- **Review tooling optimises minutes per claim:** the claim, the exact source passage beside it, one-click accept / reject / needs-discussion, keyboard-driven, batchable by story or person.
- **Prioritise the queue** by what learners actually see most (traffic-weighted), not by corpus order.
- **Credit is recorded** per reviewer per claim (the evaluation is an act by an agent — the ontology already models this).
- The pipeline must work for **one** scholar now and **many** later without redesign.

### D3 → design rules for English-then-Arabic

- **Data is bilingual from day one** even though the UI is English: every name stored as Arabic original + English transliteration (one consistent scheme, proposed: ALA-LC with a plain-ASCII fallback for search) + common English form.
- **Every UI string is a translation key** from the first commit — no hard-coded English.
- **Layout uses logical CSS properties** (`margin-inline-start`, not `margin-left`) so RTL is a switch, not a rewrite.
- **Dates are always dual** — Hijri and Gregorian — with uncertainty shown, never a false-precision single date.
- **Search accepts any spelling:** "Abu Bakr", "Abū Bakr", "ابو بكر", "abubakr".

### D4 → design rules for a donation-funded non-profit

- **Running cost target: under $50/month** for the public site (static hosting + CDN). Expensive compute (AI extraction) runs offline, in batches, with a hard budget per run.
- **Live AI for every visitor is deferred** until there is funding for it; when it comes, answers are cached and shared, because most questions repeat.
- **Open by default:** open data licence, open source code, versioned public data releases. Donors are funding a public good; they should be able to see and download it. (Licence choice is open — §5.)
- **A transparency page:** who reviews, how claims are graded, what has been verified, what donations pay for.
- **No dark patterns in fundraising.** A quiet, dignified donate link; never interrupt learning to ask for money.

## 3. The platform, as layers

```
 ┌────────────────────────────────────────────────────────────────┐
 │  LEARN      paths through the graph · quizzes · teacher journeys │  slices 6–7
 ├────────────────────────────────────────────────────────────────┤
 │  EXPLORE    reader pages (L0) · thread view · network · timeline │  slice 2
 │             · map                                                │
 ├────────────────────────────────────────────────────────────────┤
 │  ASK        plain question → typed query → graph view + sources  │  slice 8
 ├────────────────────────────────────────────────────────────────┤
 │  REVIEW     scholar queue · accept/reject · credit ledger        │  slice 3
 ├────────────────────────────────────────────────────────────────┤
 │  GRAPH      one store · one ID per entity · SHACL-validated      │  slice 1
 │             · external IDs (Wikidata, al-Thurayya, OpenITI)      │  slice 5
 ├────────────────────────────────────────────────────────────────┤
 │  INGEST     AI extraction from OpenITI texts, anchored to the    │  slice 4
 │             exact passage, status = proposed                     │
 └────────────────────────────────────────────────────────────────┘
```

## 4. Build slices

Each slice is small enough for one focused session, ends in something runnable, and writes a handover note to `docs/handover/<slice>.md`.

| # | Slice | Done when |
|---|---|---|
| 1 | **One graph.** Convert `stories-50` into Turtle; give every person/place/event one canonical ID; merge duplicates across all four islands with a reviewable identity table; one build validates everything with SHACL. | One `corpus/` builds to one graph, conforms, and Abū Bakr exists once with every story, incident and kinship tie attached. |
| 2 | **One explorer, reader tier first.** Static generator → a page per person, event, place, story; the existing thread view ("walk the graph") on top; search with spelling tolerance; i18n keys; logical CSS. | Any entity is one link away; works with JS off; passes the 300 KB budget; old demo pages either retired or linked as "experiments". |
| 3 | **Review queue.** A local review tool for scholars over the proposed claims; decisions written back as evaluations with reviewer + date. | One scholar can review 50 claims in a sitting; public pages show updated status after rebuild. |
| 4 | **AI-assisted ingestion.** Pick one source (proposed: Ibn Hishām's *Sīra* via OpenITI); Claude proposes reports and assertions with the exact passage span; everything lands as `proposed`. | 200 proposed claims from one text, each with a clickable source passage, flowing into the slice 3 queue. |
| 5 | **Connect outward.** Wikidata QIDs for people, al-Thurayya for places, OpenITI URIs for texts. | ≥80 % of people and places carry an external ID; links render on pages. |
| 6 | **Learning paths.** Curated journeys as ordered graph walks (e.g. "the Hijrah, day by day", "the people of Badr"); progress kept on the device. | Three journeys live, built from graph data, not hand-written pages. |
| 7 | **Practice.** Questions generated from graph relationships ("who was at both Badr and Ḥudaybiyyah?"), answers linked to sources; only from `accepted` claims. | Quiz bank generated at build time; no unreviewed claim can appear in a question. |
| 8 | **Ask the graph.** Plain-language question → typed query DSL (doc 07) → a graph view with sources; refusal path for rulings and interpretation. | Golden-set of scholar-checked questions passes; answers cached. |
| 9 | **Arabic interface.** RTL switch, Arabic UI strings, Arabic search. | Full parity of the reader tier in Arabic. |
| 10 | **Time and space.** Timeline scrubbing and map over the same graph. | Doc 08 §7 acceptance criteria. |

Slices 1–3 are the foundation and should go in that order. After that, 4–9 can be reordered by what donors and users ask for.

## 5. Open questions for brainstorming

1. **Licences.** Data: CC BY-SA 4.0 or CC BY 4.0? Code: MIT or AGPL-3.0? (AGPL keeps forks open; MIT invites wider reuse.)
2. **Name and home.** Is *al-Marṣad* the public name? Who is the legal non-profit entity that receives donations?
3. **Review scope of the current scholars.** Which tradition(s), which periods, how many hours a week — this sizes slice 3 and the queue priority.
4. **Multiple traditions.** Doc 06 supports evaluations from several traditions side by side. Is that in scope from the start, or does the first release follow one review board's grading with others added later?
5. **Who writes the 50 stories' successors?** The stories are the friendliest door into the graph. Should every future story be authored *from* the graph (reports first, story second), so it is reviewable claim by claim?
6. **Children.** "The whole world" includes children. Is a dedicated young-learner mode a near-term goal or a later one?
7. **Hosting.** Static host choice (GitHub Pages, Cloudflare Pages, Netlify) — all free at this scale; Cloudflare has the widest global edge.

## 6. What stays non-negotiable

The standing rules in the README apply unchanged: no pixel without provenance, no depiction, AI never asserts, computed ≠ significant, the data must outlive the app.
