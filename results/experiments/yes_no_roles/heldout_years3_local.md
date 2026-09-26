# Ranking eval: `local:mlx-community/Qwen3.5-9B-MLX-4bit`

Superseded: years computed in code, but roles judged yes/no ("does this role count?") rather than main / touches / no (commit `c441300`, before `edb076f`). The shipped version is in `results/`; see the main README.

## Candidates for each job (`shortlist rank`)

| Job | NDCG@3 | NDCG@5 | P@3 | Top-1 correct |
|---|---|---|---|---|
| security_engineer | 1.00 | 0.96 | 0.67 | yes |
| data_engineer | 1.00 | 1.00 | 0.67 | yes |
| site_reliability_engineer | 1.00 | 0.97 | 1.00 | yes |
| **mean** | **1.00** | **0.98** | **0.78** | **100%** |

## Jobs for each resume (`shortlist jobs`)

Resumes that fit at least one of the 3 jobs.

| Resume | Top pick (grade) | Best grade available | NDCG@3 |
|---|---|---|---|
| a01_hiroshi_sato | security_engineer (3, score 96) | 3 | 1.00 |
| a02_valentina_rossi | site_reliability_engineer (3, score 92) | 3 | 1.00 |
| a03_omar_khalil | data_engineer (1, score 42) | 1 | 1.00 |
| a04_mei_lin | data_engineer (3, score 92) | 3 | 1.00 |
| a05_tunde_adebayo | data_engineer (1, score 50) | 1 | 1.00 |
| a07_kofi_asante | security_engineer (2, score 65) | 2 | 1.00 |
| a08_ingrid_larsen | data_engineer (2, score 81) | 2 | 1.00 |
| a09_marco_bianchi | site_reliability_engineer (1, score 38) | 1 | 1.00 |
| a10_ruth_okonkwo | site_reliability_engineer (3, score 100) | 3 | 1.00 |
| **mean** | **top-1 correct: 100%** | | **1.00** |

## Requirement verdicts vs. expected

**26/29 agree** · 3 too lenient · 0 too strict

| Job | Candidate | Requirement | Expected | Got | |
|---|---|---|---|---|---|
| security_engineer | a09_marco_bianchi | `years_security` | not_met | met | too lenient |
| data_engineer | a03_omar_khalil | `years_de` | not_met | met | too lenient |
| data_engineer | a05_tunde_adebayo | `years_de` | not_met | met | too lenient |

## Stability across 3 requirement orderings

Run 1 lists the requirements as written; the others shuffle them (seeds 1–2). Scoring is order-independent, so differences are the model's sensitivity to an irrelevant detail, plus sampling noise for backends that sample.

| | min | mean | max |
|---|---|---|---|
| Candidate ranking: mean NDCG@3 | 1.00 | 1.00 | 1.00 |
| Candidate ranking: top-1 correct (of 3) | 3.0 | 3.0 | 3.0 |
| Job ranking: top-1 correct (of 9) | 9.0 | 9.0 | 9.0 |
| Expected verdicts agreeing (of 29) | 26.0 | 26.0 | 26.0 |
| ... too lenient | 3.0 | 3.0 | 3.0 |
| ... too strict | 0.0 | 0.0 | 0.0 |

- **287 of 300 requirement verdicts (96%) were identical in every ordering.**
- A (job, resume) score moved by 2.6 points on average across orderings, and at most 25.0 (a07_kofi_asante for site_reliability_engineer).

Verdicts that changed with the ordering:

| Job | Candidate | Requirement | Verdict in each run |
|---|---|---|---|
| data_engineer | a04_mei_lin | `dbt` | not_met → met → met |
| data_engineer | a04_mei_lin | `kafka` | not_met → met → met |
| data_engineer | a09_marco_bianchi | `python` | partial → met → met |
| security_engineer | a01_hiroshi_sato | `cissp_oscp` | met → met → not_met |
| security_engineer | a02_valentina_rossi | `terraform` | met → partial → partial |
| security_engineer | a10_ruth_okonkwo | `python` | met → partial → met |
| security_engineer | a10_ruth_okonkwo | `terraform` | met → partial → met |
| site_reliability_engineer | a01_hiroshi_sato | `observability` | not_met → partial → partial |
| site_reliability_engineer | a05_tunde_adebayo | `kubernetes` | partial → met → met |
| site_reliability_engineer | a05_tunde_adebayo | `observability` | partial → partial → met |
| site_reliability_engineer | a07_kofi_asante | `go_or_python` | not_met → met → met |
| site_reliability_engineer | a07_kofi_asante | `linux` | not_met → met → met |
| site_reliability_engineer | a08_ingrid_larsen | `aws` | not_met → not_met → met |

## Per-job rankings

### security_engineer

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | a01_hiroshi_sato | 96 | 3 |
| 2 | a07_kofi_asante | 65 | 2 |
| 3 | a09_marco_bianchi | 25 | 1 |
| 4 | a10_ruth_okonkwo | 21 | 0 |
| 5 | a05_tunde_adebayo | 17 | 0 |
| 6 | a02_valentina_rossi | 15 | 1 |
| 7 | a03_omar_khalil | 12 | 0 |
| 8 | a04_mei_lin | 12 | 0 |
| 9 | a08_ingrid_larsen | 12 | 0 |
| 10 | a06_sarah_goldberg | 0 | 0 |

### data_engineer

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | a04_mei_lin | 92 | 3 |
| 2 | a08_ingrid_larsen | 81 | 2 |
| 3 | a05_tunde_adebayo | 50 | 1 |
| 4 | a03_omar_khalil | 42 | 1 |
| 5 | a01_hiroshi_sato | 12 | 0 |
| 6 | a07_kofi_asante | 12 | 0 |
| 7 | a10_ruth_okonkwo | 12 | 0 |
| 8 | a09_marco_bianchi | 6 | 0 |
| 9 | a02_valentina_rossi | 0 | 0 |
| 10 | a06_sarah_goldberg | 0 | 0 |

### site_reliability_engineer

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | a10_ruth_okonkwo | 100 | 3 |
| 2 | a02_valentina_rossi | 92 | 3 |
| 3 | a07_kofi_asante | 56 | 2 |
| 4 | a09_marco_bianchi | 38 | 1 |
| 5 | a01_hiroshi_sato | 35 | 0 |
| 6 | a05_tunde_adebayo | 25 | 1 |
| 7 | a03_omar_khalil | 12 | 0 |
| 8 | a04_mei_lin | 12 | 0 |
| 9 | a08_ingrid_larsen | 12 | 0 |
| 10 | a06_sarah_goldberg | 0 | 0 |
