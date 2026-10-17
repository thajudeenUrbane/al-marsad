# Scoring — Hijrah journey pilot

Answer key: `tests/answer-key.json` (built by `build_tests.py`). Every key answer cites the claim id(s), section and citation it rests on.
Score blind: the scorer sees learner code and form only, never condition.

## Item rubric
| Kind | Items (per half, per form) | Points | Rule |
|---|---|---|---|
| Cued recall | Q01–Q05 / Q11–Q15 | 1 per name or fact asked (5–6 per half; `cued_recall_points` in the key) | 1 if the answer matches the key; spelling and transliteration ignored (“Umar”, “ʿUmar”); a correct part-name that identifies one person counts (“ʿĀmir” for ʿĀmir b. Rabīʿa if no other ʿĀmir fits). Number/date items: “three days” = 3 days. Vague or wrong = 0. |
| Multiple choice | Q06–Q08 / Q16–Q18 | 1 each | Correct letter only. Two letters circled = 0. |
| Ordering | Q09 / Q19 | adjacent pairs, max n−1 | 1 for each neighbouring pair written in the key’s order. |
| Two reports | Q10 / Q20 | 0–2 | 2 = both names, or one name plus “there is another report”; 1 = one name only; 0 = neither. |
| Free recall | FR1, FR2 | count | Idea units: one unit = one claim of that half (`halves.*.claims_shown` in the key) that the answer states correctly (who + what, or who + where). Count each claim once; family links count; invented or wrong facts are counted separately as `intrusions` (exploratory). |
| How do we know? | SRC1, SRC2 | 0–3 | 1 names the book or author (Ibn Hishām, Ibn Isḥāq, the Sīra); 1 says it came through named narrators / a chain; 1 names the person at the end of the chain (`eyewitness` in the key). |
| Honesty cues | H1–H3 | 0–2 each | Per the `scoring` text of each item in the key. |

Position numbers match across forms: Q01 on Form A and Q01 on Form B are parallel items of the same kind and half.
Columns of `results-template.csv` follow that order (Q01–Q10 = Half 1, Q11–Q20 = Half 2).

## Inter-rater check
1. Two scorers each score a random 20% of test papers (stratified by session), blind to each other and to condition.
2. Agreement: Cohen’s κ for each open item kind (cued recall, two reports, source, honesty); intraclass correlation (ICC(2,1)) for free-recall unit counts.
3. Thresholds: κ ≥ 0.80 and ICC ≥ 0.85. Below that, the scorers meet, write the disagreement into this rubric as a decision rule, and re-score the subset.
4. Disagreements in the double-scored set are settled by discussion; the agreed score is used.

## Results file
`results-template.csv`: one row per learner × session. `world_half` is 1 or 2 (the half done in the world); `condition_first` is `world` or `reading`;
`form_sequence` is `A-B-A-B` or `B-A-B-A`; `session` is `pre`, `post`, `week1`, `month1`; `studied_between` is yes/no;
`status` is `done`, `absent` or `withdrawn`. No names and no free text.
