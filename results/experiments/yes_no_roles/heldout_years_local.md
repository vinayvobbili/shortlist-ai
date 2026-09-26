# Ranking eval: `local:mlx-community/Qwen3.5-9B-MLX-4bit`

Superseded: years computed in code, but roles judged yes/no ("does this role count?") rather than main / touches / no (commit `c441300`, before `edb076f`). The shipped version is in `results/`; see the main README.

## Candidates for each job (`shortlist rank`)

| Job | NDCG@3 | NDCG@5 | P@3 | Top-1 correct |
|---|---|---|---|---|
| backend_engineer | 0.96 | 0.96 | 1.00 | yes |
| soc_analyst | 1.00 | 1.00 | 0.67 | yes |
| fpa_analyst | 1.00 | 1.00 | 0.67 | yes |
| **mean** | **0.99** | **0.99** | **0.78** | **100%** |

## Jobs for each resume (`shortlist jobs`)

Resumes that fit at least one of the 3 jobs.

| Resume | Top pick (grade) | Best grade available | NDCG@3 |
|---|---|---|---|
| y02_kwame_mensah | backend_engineer (2, score 86) | 2 | 1.00 |
| y03_ines_carvalho | backend_engineer (3, score 77) | 3 | 1.00 |
| y04_arjun_nair | backend_engineer (3, score 100) | 3 | 1.00 |
| y05_leila_ahmadi | soc_analyst (2, score 85) | 2 | 1.00 |
| y06_marek_novak | soc_analyst (3, score 100) | 3 | 1.00 |
| y07_olivia_brennan | fpa_analyst (3, score 100) | 3 | 1.00 |
| y08_tomasz_wojcik | fpa_analyst (2, score 68) | 2 | 1.00 |
| **mean** | **top-1 correct: 100%** | | **1.00** |

## Requirement verdicts vs. expected

**35/36 agree** · 0 too lenient · 1 too strict

| Job | Candidate | Requirement | Expected | Got | |
|---|---|---|---|---|---|
| backend_engineer | y03_ines_carvalho | `relational_db` | met | partial | too strict |

## Stability across 3 requirement orderings

Run 1 lists the requirements as written; the others shuffle them (seeds 1–2). Scoring is order-independent, so differences are the model's sensitivity to an irrelevant detail, plus sampling noise for backends that sample.

| | min | mean | max |
|---|---|---|---|
| Candidate ranking: mean NDCG@3 | 0.99 | 1.00 | 1.00 |
| Candidate ranking: top-1 correct (of 3) | 3.0 | 3.0 | 3.0 |
| Job ranking: top-1 correct (of 7) | 7.0 | 7.0 | 7.0 |
| Expected verdicts agreeing (of 36) | 35.0 | 35.7 | 36.0 |
| ... too lenient | 0.0 | 0.0 | 0.0 |
| ... too strict | 0.0 | 0.3 | 1.0 |

- **123 of 126 requirement verdicts (98%) were identical in every ordering.**
- A (job, resume) score moved by 0.8 points on average across orderings, and at most 22.7 (y03_ines_carvalho for backend_engineer).

Verdicts that changed with the ordering:

| Job | Candidate | Requirement | Verdict in each run |
|---|---|---|---|
| backend_engineer | y03_ines_carvalho | `docker` | partial → met → met |
| backend_engineer | y03_ines_carvalho | `relational_db` | partial → met → met |
| backend_engineer | y03_ines_carvalho | `rest_apis` | partial → met → met |

## Per-job rankings

### backend_engineer

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | y04_arjun_nair | 100 | 3 |
| 2 | y02_kwame_mensah | 86 | 2 |
| 3 | y03_ines_carvalho | 77 | 3 |
| 4 | y07_olivia_brennan | 14 | 0 |
| 5 | y01_teresa_alvarez | 0 | 0 |
| 6 | y05_leila_ahmadi | 0 | 0 |
| 7 | y06_marek_novak | 0 | 0 |
| 8 | y08_tomasz_wojcik | 0 | 0 |
| 9 | y09_noor_rahman | 0 | 0 |

### soc_analyst

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | y06_marek_novak | 100 | 3 |
| 2 | y05_leila_ahmadi | 85 | 2 |
| 3 | y01_teresa_alvarez | 0 | 0 |
| 4 | y02_kwame_mensah | 0 | 0 |
| 5 | y03_ines_carvalho | 0 | 0 |
| 6 | y04_arjun_nair | 0 | 0 |
| 7 | y07_olivia_brennan | 0 | 0 |
| 8 | y08_tomasz_wojcik | 0 | 0 |
| 9 | y09_noor_rahman | 0 | 0 |

### fpa_analyst

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | y07_olivia_brennan | 100 | 3 |
| 2 | y08_tomasz_wojcik | 68 | 2 |
| 3 | y02_kwame_mensah | 9 | 0 |
| 4 | y03_ines_carvalho | 9 | 0 |
| 5 | y04_arjun_nair | 9 | 0 |
| 6 | y01_teresa_alvarez | 0 | 0 |
| 7 | y05_leila_ahmadi | 0 | 0 |
| 8 | y06_marek_novak | 0 | 0 |
| 9 | y09_noor_rahman | 0 | 0 |
