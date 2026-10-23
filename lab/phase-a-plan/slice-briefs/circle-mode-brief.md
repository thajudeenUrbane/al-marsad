# Circle mode brief — the classroom and the halaqa

Context: README "Standing rules"; lab/beyond-the-graph (N5; "Circle"; experiment 8; "Design for the teacher"); docs/handover/maintainer-answers-3.md (E1, E2, E5); lab/phase-a-plan/PLAN.md (cut list items 3–4). Do not read chat history; this file is the brief. Build on `site/world/hijrah/`.

## Build
1. **Projector mode.** The teacher drives chapters and camera full screen: large type, presenter keys (next, back, reveal), guess-first questions shown before answers. Works offline from the loaded pack.
2. **Live questions** *(cuttable to a show of hands)*. Students join from their phones by a short code, answer the same guess-first question, and the projector shows aggregate answers only. No student accounts or names. A Cloudflare Worker with a Durable Object, cost under $10 a month, a kill switch, and graceful fallback on school Wi-Fi.
3. **Majlis sheet v0** *(cuttable)*. The teacher picks claims from a chapter; the page prints them with citations and one question. No hand-typed facts.
4. **Teacher guide.** One page a teacher can follow without training.

## Done when
A teacher who has never seen the tool runs a 30-minute session from the guide in the pilot dry run. Playwright checks for projector mode (desktop) and the join page (390×844); live mode degrades to projector-only when the Worker is unreachable; steps in `scripts/check_all.sh`. Handover `docs/handover/circle-mode.md` (≤60 lines).

## Rules
No accounts for students; no personal data stored server-side; AI never asserts; no pixel without provenance; no model names or IDs in the repo.
