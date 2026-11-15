# Ranking eval: `local:local-server`

## Candidates for each job (`shortlist rank`)

| Job | NDCG@3 | NDCG@5 | P@3 | Top-1 correct |
|---|---|---|---|---|
| security_engineer | 0.95 | 0.94 | 0.67 | yes |
| data_engineer | 1.00 | 1.00 | 0.67 | yes |
| site_reliability_engineer | 1.00 | 0.97 | 1.00 | yes |
| **mean** | **0.98** | **0.97** | **0.78** | **100%** |

## Jobs for each resume (`shortlist jobs`)

Resumes that fit at least one of the 3 jobs.

| Resume | Top pick (grade) | Best grade available | NDCG@3 |
|---|---|---|---|
| a01_hiroshi_sato | security_engineer (3, score 100) | 3 | 1.00 |
| a02_valentina_rossi | site_reliability_engineer (3, score 92) | 3 | 1.00 |
| a03_omar_khalil | data_engineer (1, score 29) | 1 | 1.00 |
| a04_mei_lin | data_engineer (3, score 100) | 3 | 1.00 |
| a05_tunde_adebayo | data_engineer (1, score 38) | 1 | 1.00 |
| a07_kofi_asante | site_reliability_engineer (2, score 81) | 2 | 1.00 |
| a08_ingrid_larsen | data_engineer (2, score 81) | 2 | 1.00 |
| a09_marco_bianchi | site_reliability_engineer (1, score 38) | 1 | 0.92 |
| a10_ruth_okonkwo | site_reliability_engineer (3, score 100) | 3 | 1.00 |
| **mean** | **top-1 correct: 100%** | | **0.99** |

## Requirement verdicts vs. expected

**29/29 agree** · 0 too lenient · 0 too strict

## Per-job rankings

### security_engineer

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | a01_hiroshi_sato | 100 | 3 |
| 2 | a07_kofi_asante | 65 | 2 |
| 3 | a10_ruth_okonkwo | 21 | 0 |
| 4 | a05_tunde_adebayo | 17 | 0 |
| 5 | a02_valentina_rossi | 15 | 1 |
| 6 | a03_omar_khalil | 12 | 0 |
| 7 | a04_mei_lin | 12 | 0 |
| 8 | a08_ingrid_larsen | 12 | 0 |
| 9 | a09_marco_bianchi | 12 | 1 |
| 10 | a06_sarah_goldberg | 0 | 0 |

### data_engineer

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | a04_mei_lin | 100 | 3 |
| 2 | a08_ingrid_larsen | 81 | 2 |
| 3 | a05_tunde_adebayo | 38 | 1 |
| 4 | a03_omar_khalil | 29 | 1 |
| 5 | a07_kofi_asante | 12 | 0 |
| 6 | a09_marco_bianchi | 12 | 0 |
| 7 | a10_ruth_okonkwo | 12 | 0 |
| 8 | a01_hiroshi_sato | 6 | 0 |
| 9 | a02_valentina_rossi | 0 | 0 |
| 10 | a06_sarah_goldberg | 0 | 0 |

### site_reliability_engineer

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | a10_ruth_okonkwo | 100 | 3 |
| 2 | a02_valentina_rossi | 92 | 3 |
| 3 | a07_kofi_asante | 81 | 2 |
| 4 | a09_marco_bianchi | 38 | 1 |
| 5 | a01_hiroshi_sato | 35 | 0 |
| 6 | a05_tunde_adebayo | 31 | 1 |
| 7 | a03_omar_khalil | 12 | 0 |
| 8 | a04_mei_lin | 12 | 0 |
| 9 | a08_ingrid_larsen | 12 | 0 |
| 10 | a06_sarah_goldberg | 0 | 0 |
