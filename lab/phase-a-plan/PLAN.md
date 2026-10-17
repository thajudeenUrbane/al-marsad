# Phase A — "Prove it": execution plan

12 weeks, Mon 2 Nov 2026 to Sun 24 Jan 2027, plus a pre-phase week (W0, 19 Oct to 1 Nov) for round 3 E1. Source: lab/beyond-the-graph (roadmap A, directions N1–N7, experiments 1–10, team and cost) and docs/handover/maintainer-answers-3.md (W1, H4, X1, G1, E1–E5, P1, F3). Every story is in `backlog.csv` (72 stories, about 162 person-days). Slice briefs for builders are in `slice-briefs/`. Hiring briefs are in `HIRING.md`.

## Goal and Gate A
Phase A answers one question with evidence: **does a guided night world of the Hijrah, built only from sourced claims, teach better than reading the same claims, on the phones learners actually have, in a format scholars approve?**

| # | Gate A criterion | How it is measured | Who | When |
|---|---|---|---|---|
| A1 | Delayed recall at 1 week beats a reading-page control by **d ≥ 0.3** | Pilot 1, within-person and counterbalanced: each learner does chapters 1–5 in one condition and 6–10 in the other. Cued-recall test built from claims, scored blind by 2 raters (κ ≥ 0.8). Paired effect size with 95% CI, preregistered before any data (EVD-3.3). Target ≥ 40 completers. | learning researcher | W10 exposure, W11 test, W12 analysis |
| A2 | **30 fps on a $150 Android phone** | Perf harness on the frozen build (beta-2): median fps per chapter ≥ 30, worst-chapter memory < 150 MB, first load < 3 MB, on all 3 test phones (experiment 3) | engineer | W11 |
| A3 | **Scholars approve the scene format** | At least 2 scholars review a full chapter as scenes and record approve / approve-with-changes in the review log. The Hijrah scenes (about 300 claims) are reviewed, with minutes per claim published | scholars | W7, confirmed W12 |

Reported but not gating: think-aloud cue comprehension (exp 4, 8 of 10 per cue); moments acceptance (exp 6, ≥ 80%); guess-first effect (exp 2, randomised per chapter inside pilot 1); circle return (exp 8, 2 of 3 teachers); 7-day return (exp 9, early signal only). The one-month recall (about 8 Feb) feeds Gate B.

**Decision rules (W12).** All three pass → Phase B. A1 between 0.1 and 0.3 with a wide CI → extend: a second cohort in Feb with the same preregistration, Phase B starts on the engine work only. A1 below 0.1 → experiment 1's stop rule: the world becomes optional and the money moves to the memory engine. A2 fails → tier 1 (2.5D map) becomes the default on such phones (experiment 3's stop rule); this does not block Phase B. A3 fails → redesign the scene format with the scholars before any new world.

## Workstreams
| Stream | Directions | Lead role | Output by W12 |
|---|---|---|---|
| **World** | N1, design grammar | 3D/web engineer + designer (0.5) | `site/world/hijrah/`, three tiers, frozen pilot build, design grammar v0 |
| **Engine** | N2, N3, scenes | data and graph engineer (part-time, AI-assisted) + editor | Moments, scenes, place grades in the graph; scene packs and question banks in CI |
| **Learning** | N4, N5 | builder sessions + engineer | Guess-first, recall, spaced review, sky; projector mode; reading-page control |
| **People** | N7, hiring, teachers | maintainer | Two hires, scholar scene review, pilot cohort, 3 circle teachers |
| **Evidence** | N6, exp 1–4, 6, 8, 9 | learning researcher (0.3) | Think-aloud ×2, perf log, pilot 1, Gate A report |

Roles in `backlog.csv`: maintainer; scholar; editor (trained, P10); data-eng; 3d-web-eng; designer; learning-researcher; builder (an AI-assisted build session working from a slice brief, reviewed by the engineer or data-eng). Builder capacity is not the limit; review of its output is.

## Epics → stories (summary; full acceptance criteria in backlog.csv)
| Epic | Stories | Days | Depends on |
|---|---|---|---|
| ENG-1 Moments (N2) | schema; trial on 28 sections; timed scholar review; full pass; Hijrah cast merges | 11.5 | — |
| ENG-2 Scenes | schema + SHACL; author ~25–30 scenes; question bank; scene packs in CI | 12 | ENG-1.1, ENG-3.2 |
| ENG-3 Places (N3) | certainty grades; Hijrah + Makkah pass; order-not-road; scholar review; LPF export (cut) | 9.5 | — |
| ENG-4 Scene review (N7) | review lane; queue in learner order; maintainer test (P1); scholars review ~300 claims | 7 | ENG-2.1 |
| WLD-1 Hijrah World (N1) | port; tiers; terrain; perf harness; grammar; depths (G1); perf fixes; a11y; offline (cut); WebGPU (cut); freeze | 33.5 | ENG-2.4 |
| WLD-2 Identity | brief + moodboard; type; UI kit; sky; sound policy; grammar note | 18 | PPL-1.3 |
| LRN-1 Memory (N4) | learner model; guess-first; recall; spaced review; sky; pilot codes | 17 | ENG-2.3 |
| LRN-2 Circle (N5) | projector; live questions (cut to show of hands); majlis sheet (cut); teacher guide | 12 | WLD-1.1 |
| LRN-3 Control | reading-page control from the same packs | 2 | ENG-2.4 |
| PPL-1..4 | hiring; scholars; teachers; partners | 13.5 | — |
| EVD-1..5 | think-aloud ×2; perf; pilot 1 (8 stories); circle; Gate A | 26 | — |

## Week by week
| Week | Dates | Focus (story IDs) | Done by Friday | Risks this week |
|---|---|---|---|---|
| W0 | 19 Oct–1 Nov | E1: the class tries Hijrah Night (private preview); think-aloud round 1 (EVD-1.1); post roles (PPL-1.1); timed review of the 277 prototype claims by one scholar | Class session held; ads live; minutes per claim measured | Class date slips; scholar unavailable → maintainer times himself (P1) |
| W1 | 2–8 Nov | Moments schema (ENG-1.1); extraction trial starts (ENG-1.2); buy phones, baseline (EVD-2.1, 2.2); perf harness (WLD-1.4); researcher agreed (PPL-1.4); round 4 sheet out (PPL-2.2); scholar plan (PPL-2.1) | Schema conforms; perf baseline logged | No engineer yet: builder + maintainer run the harness |
| W2 | 9–15 Nov | Trial done; **timed scholar review of moments (ENG-1.3)**; scene schema (ENG-2.1); certainty grades (ENG-3.1); portfolio tests (PPL-1.2); pilot protocol (EVD-3.1) | Acceptance rate known; scene schema conforms | Moments < 60% accepted → editor writes moments (+4 days, critical) |
| W3 | 16–22 Nov | **Moments go/no-go**; full moments pass (ENG-1.4); place pass starts (ENG-3.2); order-not-road (ENG-3.3); hires start (PPL-1.3); design brief (WLD-2.1); port begins (WLD-1.1) | Hijrah moments in the graph; engineer and designer onboarded | Hires late → builder carries WLD-1.1; cut list items 1–3 pre-approved |
| W4 | 23–29 Nov | Scene authoring (ENG-2.2); question bank (ENG-2.3); review lane + queue (ENG-4.1, 4.2); **maintainer test-reviews ch. 1 (ENG-4.3)**; tiers + terrain (WLD-1.2, 1.3); scholars sign visual grammar (PPL-2.3); consent forms (EVD-3.2); cast merges (ENG-1.5) | Chapter 1 as scenes, reviewed by maintainer; grammar signed | Scholars disagree on stones or sound → keep neutral marks, no sound |
| W5 | 30 Nov–6 Dec | Scene packs in CI (ENG-2.4); world on scenes (WLD-1.1 done); learner model, guess-first, recall (LRN-1.1–1.3); UI kit (WLD-2.3); **scholar review batch 1, ch. 1–4** | World runs end to end from scene packs | Review lane friction → fix same week; scene count trimmed to 25 |
| W6 | 7–13 Dec | Grammar in world (WLD-1.5); depths and G1 rules (WLD-1.6); spaced review, sky (LRN-1.4, 1.5); places scholar review (ENG-3.4); **review batch 2, ch. 5–7**; ethics approval (EVD-3.2); preregistration draft (EVD-3.3) | beta-1 feature complete | Ethics review slow → submit W4, chase weekly |
| W7 | 14–20 Dec | **beta-1**; reading-page control (LRN-3.1); pilot codes (LRN-1.6); projector mode (LRN-2.1); **review batch 3, ch. 8–10**; **scholars approve scene format (PPL-2.4, A3)**; pilot dry run (EVD-3.4); perf fixes start (WLD-1.7) | Dry run done; format decision recorded | Dry run shows sessions too long → shorten chapters, not the test |
| W8 | 21–27 Dec | Reduced capacity. Think-aloud round 2 (EVD-1.2); a11y (WLD-1.8); teacher guide (LRN-2.4); live questions start (LRN-2.2); grammar note (WLD-2.6) | Cue fixes listed | Holiday absence; nothing on the critical path is scheduled here except perf |
| W9 | 28 Dec–3 Jan | Reduced capacity. Cue fixes; perf to gate (WLD-1.7); **freeze and tag beta-2 (WLD-1.11)**; **preregistration filed** (EVD-3.3); cuttables only if ahead (WLD-1.9, 1.10, LRN-2.3) | beta-2 tagged; prereg filed with its content hash | Freeze slips → pilot moves to W11, recall to W12, Gate to W13 (one week of float, no more) |
| W10 | 4–10 Jan | **Pilot 1 exposure sessions (EVD-3.5)**; circle sessions 1 (EVD-4.1) | ≥ 40 completers, orders balanced | Attendance; device failures → spare phones, tier 0 fallback recorded |
| W11 | 11–17 Jan | **One-week recall (EVD-3.6)**; **perf gate run (EVD-2.3)**; circle sessions 2 | All recall tests done; perf numbers final | Attrition > 25% → second cohort in Feb |
| W12 | 18–24 Jan | Blind scoring; **analysis (EVD-3.7)**; Gate A report and decision (EVD-5.1); one-month recall booked (EVD-3.8); Phase B slice briefs | Gate A decided and recorded in docs/handover | Analysis slips → decide on A2 and A3, A1 one week later |

## Critical path
Moments schema (W1) → extraction trial (W1–2) → timed scholar review and go/no-go (W2–3) → full moments pass (W3) → scene authoring with the place pass (W4–5) → scene packs and world on scenes (W5) → scholar scene review, 3 batches (W5–7) → beta-1 and dry run (W7) → perf fixes and freeze (W8–9) → preregistration filed (W9) → pilot exposure (W10) → 1-week recall (W11) → analysis and Gate (W12).

Near-critical chains: **hiring** (ads W0 → engineer starts W3 → tiers and perf W4–9 → A2 in W11) and **consent** (forms W4 → ethics W6 → pilot W10). Total float is about one week, and it sits in the holiday weeks (W8–9). Spend it only on the freeze.

## Maintainer and scholars, week by week (hours)
| Week | Maintainer (h) | Maintainer does | Scholars (h) | Scholars do |
|---|---|---|---|---|
| W0 | 8 | Class preview (E1); post roles; round 4 sheet | 4–5 | Timed review of the 277 prototype claims (one scholar) |
| W1 | 6 | Phones; researcher; scholar plan and stipends; round 4 | 0.5 | Round 4 Q1 (source line) and Q2 (opponents, edge cases) |
| W2 | 8 | Portfolio tests and interviews | 2 | Timed review of trial moments (exp 6) |
| W3 | 6 | Offers; moments go/no-go; cut items pre-approved | 1 | Hijrah-cast edge cases (Surāqa's turning, Abū Jahl, neutral cases) |
| W4 | 6 | Test-reviews chapter 1 (P1); recruits cohort; ethics submission | 1.5 | Sign off visual grammar and sound policy |
| W5 | 3 | Weekly sheet (M5); unblock | 2 | Batch 1: ch. 1–4 (~120 claims and moments) |
| W6 | 3 | Weekly sheet; teachers for circle | 3 | Batch 2: ch. 5–7; contested places |
| W7 | 5 | Dry run; format decision meeting | 3 | Batch 3: ch. 8–10; **approve scene format (A3)** |
| W8 | 2 | Holiday; read think-aloud results | 0 | — |
| W9 | 3 | Approve freeze; sign preregistration | 0.5 | Check the frozen build's changes |
| W10 | 6 | Attends pilot sessions; logistics | 0 | — |
| W11 | 4 | Recall sessions | 0 | — |
| W12 | 6 | Gate A decision; Phase B order | 1 | Confirm format decision; read report |
| **Total** | **≈ 66 h** | | **≈ 19–20 h** | ≈ 300 claims at ~1 min plus ~150 moments at ~2 min, sign-offs |

## Cut list (in this order; each item is pre-approved in W3)
1. WebGPU renderer (WLD-1.10): WebGL2 only.
2. Offline chapter pack (WLD-1.9): online only for the pilot; carry spare phones with the pack loaded.
3. Majlis sheet (LRN-2.3): to Phase B.
4. Live questions on students' phones (LRN-2.2): projector mode plus show of hands.
5. Linked Places export (ENG-3.5): to Phase B.
6. Makkah places beyond those the Hijrah scenes use (part of ENG-3.2).
7. Sky visuals (LRN-1.5 polish, WLD-2.4): a plain list of people met, with due reviews.
8. Scene count: 30 → 20 scenes, keeping all 10 chapters (fewer claims to review).
9. Design grammar write-up (WLD-2.6): to Phase B; the scholars' sign-off stays.
10. Circle test (EVD-4.1): to Phase B; exp 8 then runs with Phase B's teachers.

**Never cut:** claim resolution in the build (no hand-typed facts); scene review before the pilot; the reading-page control; preregistration before data; consent; the perf harness; the light as never a node (H4); stones only from recorded claims (X1).

## Rules carried into every slice
No pixel without provenance; no depiction; AI never asserts; computed ≠ significant; never hard-code entity IDs; no model names or IDs in repo files. Pilot data about learners stays outside the repo; only aggregate results are committed. G1: Discover shows no review language, Study and Research show status, and the source line stays on every claim until round 4 Q1 says otherwise. Each slice adds its check to `scripts/check_all.sh` and ends with a handover note in `docs/handover/` (≤ 60 lines).
