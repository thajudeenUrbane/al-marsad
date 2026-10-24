# Pilot 1 — Does the Hijrah journey help learners remember?

Status: draft protocol for a private classroom preview. Preregister (section 9) before the first pre-test.

## 1. Research question
Compared with reading the same claims on a plain page, does walking the Hijrah in the Hijrah Night world
(`lab/hijrah-night/index.html`: terrain, guess-first, quizzes, two-report and dashed-stop cues) improve what learners
**still remember one week later**? We measure delayed learning, not engagement: time on page, clicks and enjoyment are not outcomes.

## 2. Design
- **Within-person, counterbalanced.** The 10 chapters (`CHAPTERS` in `lab/hijrah-night/build.py`) are split into
  **Half 1 = chapters 1–5** (S0659–S0688: the ones who went ahead, three remain, the council, the night of leaving, the cave) and
  **Half 2 = chapters 6–10** (S0691–S0703: four set out, Surāqa, the road north, Qubāʾ, the first Friday).
- Each learner does one half **in the world** and the other half **as a reading page** (`reading-A.html` = Half 1,
  `reading-B.html` = Half 2), with exactly the same claims in the same order (built by `build_reading_page.py` from the world's own data).
- Four groups, randomised (block randomisation within class, blocks of 4): which half is in the world (1 or 2) × which condition comes first.
  Half 1 is always studied before Half 2 (story order); the order factor is which *condition* comes first.
- Test forms A and B (`tests/`) are parallel; each covers both halves. Form sequence pre → immediate → 1 week → 1 month is
  A‑B‑A‑B or B‑A‑B‑A, randomised independently of condition.
- **n ≈ 30–60** learners (one or two classes). With n = 40 and a within-person correlation ≈ 0.5, a paired design detects
  d_z ≈ 0.45 at 80% power (α = .05, two-sided). This is a pilot: the decision rule (section 8) uses the estimate and its interval, not only p.

## 3. Participants
Learners aged **11–16** in the maintainer's class(es). Inclusion: can read English at the level of the reading page; parent/guardian consent
and the child's own assent (`CONSENT.md`). No exclusions on prior knowledge (the pre-test measures it).

## 4. Sessions
| When | What | Time |
|---|---|---|
| Day 0, before | Pre-test (Form X) | 15 min |
| Day 0 | Study block 1: first half, in its assigned condition | 25 min |
| Day 0 | 5-min break (no talk about the story) | 5 min |
| Day 0 | Study block 2: second half, other condition | 25 min |
| Day 0 | Immediate post-test (Form Y) | 15 min |
| Day 7 (±1) | Delayed test (Form X) — **primary** | 15 min |
| Day 30 (±3) | Delayed test (Form Y) | 15 min |

If one lesson is too short, run the pre-test the day before. Each study block is 25 minutes, timed by the teacher; learners who finish early
re-read their page/world (no other material). Learners are asked not to study the Hijrah between sessions; ask at each delayed test
(“Did you read or watch anything about the Hijrah since last time?” yes/no) and record it.

## 5. Outcomes
- **Primary:** 1-week **cued recall** per half: points on the cued-recall items (5 items per half per form, 5–6 points; see `cued_recall_points` in the key), as a proportion.
- **Secondary:**
  - free recall (idea units that match a claim of that half; `SCORING.md`);
  - sequence ordering (adjacent pairs correct);
  - all core items (cued recall + multiple choice + ordering + two reports; 13 points per half);
  - source awareness, “how do we know?” (0–3 per half);
  - understanding of the honesty cues (dashed stops, two reports, AI-extracted; 0–2 each). These are person-level items, not split by half,
    so they cannot be compared within person: report descriptively, by which half was in the world (dashed stops occur only in Half 2).
  - Immediate and 1-month versions of the primary outcome; forgetting (immediate − 1 week).

## 6. Procedure notes
- Same device type for both conditions. Headphones not needed. The world's local progress store should be cleared for each learner
  (fresh browser profile or private window) so a shared machine does not carry another child's answers.
- The teacher reads the same short script for both conditions: “Read carefully; you will be asked about it later.” No mention of which is new.
- Tests on paper, scored blind to condition (scorer sees only the code and form).

## 7. Analysis plan
- Unit: learner × half × session. Score = proportion of points.
- **Primary model** (1-week cued recall):
  `score ~ condition + half + order + form + pretest_half + (1 | learner) + (1 | class)` (linear mixed model; binomial GLMM on item
  responses as a robustness check with `(1 | item)`).
- **Effect size:** d = (world − reading) / SD of the reading-condition 1-week scores, with 95% CI (bootstrap over learners); also report d_z.
- Secondary outcomes: same model, Holm correction across secondary outcomes; honesty cues descriptive only.
- Missing data: analyse all available; if > 20% miss the 1-week test, add a sensitivity analysis (multiple imputation by pre-test and immediate score).
- Check carry-over: condition × order interaction; if large, also report first-block-only (between-person) estimate.

## 8. Decision rule
| Primary 1-week d (world − reading) | Decision |
|---|---|
| **≥ 0.3** and CI lower bound > 0 | **Pass**: keep building the world; plan a larger, preregistered study. |
| 0.1 – 0.3, or CI includes 0 | **Unclear**: revise (guess-first, spacing) and rerun a pilot before building more. |
| **< 0.1** | **Stop**: the world does not add learning over a good reading page; do not scale it as a learning tool. |
A harm check overrides all: if the world is worse on source awareness or honesty-cue understanding by d ≤ −0.3, do not scale it.

## 9. Preregistration outline (OSF or AsPredicts, before data)
1. Hypothesis: the world beats the reading page on 1-week cued recall (d ≥ 0.3).
2. Design, randomisation, conditions, materials (commit hash of `lab/hijrah-night/` and `lab/pilot-1/`).
3. Primary outcome and its exact scoring (`tests/answer-key.json`, `SCORING.md`).
4. Model, effect size, decision rule (sections 7–8).
5. Sample size and stopping (one or two classes; no peeking-based stopping).
6. Exclusions: learner absent from a study block; test completed with help. Nothing else.
7. Secondary and exploratory analyses, labelled as such.

## 10. Ethics and safeguarding (minors)
- **Approval:** school leadership sign-off; the designated safeguarding lead is informed. If results may be published, seek research-ethics review first.
- **Consent and assent:** written parent/guardian consent and the child's own assent (`CONSENT.md`). A child who says no does not take part,
  whatever the parent said; they do the normal lesson and the class’s usual reading.
- **Data minimisation:** each learner gets a random code (e.g. P07). Only the teacher holds the code–name list, on paper, kept apart from the data,
  destroyed after the 1-month test is scored. The data sheet (`results-template.csv`) holds codes, ages in years, scores — no names,
  no dates of birth, no free text beyond the test answers.
- **No recordings:** no audio, video, screenshots or screen recording; no analytics added to the pages; the world's in-browser store is cleared.
- **Withdrawal:** any child or parent can withdraw at any time, without a reason and without any effect on marks; their data are deleted
  on request until the results are anonymised (one month after the last test).
- **Not graded:** test scores never count towards marks or reports.
- **Content care:** the material is a religious history; the teacher stays available for questions, and learners are told the claims are
  AI-extracted and not yet checked by a scholar.
- **Data storage:** school-managed storage only; deleted (paper shredded) 12 months after the pilot unless consent for longer was given.
