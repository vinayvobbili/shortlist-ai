# Ranking eval: `local:mlx-community/Qwen3.5-9B-MLX-4bit`

## Candidates for each job (`shortlist rank`)

| Job | NDCG@3 | NDCG@5 | P@3 | Top-1 correct |
|---|---|---|---|---|
| sre_kubernetes | 1.00 | 1.00 | 0.67 | yes |
| ml_engineer | 1.00 | 1.00 | 0.33 | yes |
| azure_security_engineer | 1.00 | 1.00 | 0.33 | yes |
| **mean** | **1.00** | **1.00** | **0.44** | **100%** |

## Jobs for each resume (`shortlist jobs`)

Resumes that fit at least one of the 3 jobs.

| Resume | Top pick (grade) | Best grade available | NDCG@3 |
|---|---|---|---|
| h01_keiko_tanaka | sre_kubernetes (3, score 100) | 3 | 1.00 |
| h02_daniel_okoye | sre_kubernetes (1, score 37) | 1 | 1.00 |
| h03_sofia_marino | ml_engineer (3, score 93) | 3 | 1.00 |
| h04_chloe_bennett | ml_engineer (1, score 57) | 1 | 1.00 |
| h05_hana_kowalski | azure_security_engineer (3, score 97) | 3 | 1.00 |
| h06_ryan_brooks | azure_security_engineer (1, score 57) | 1 | 1.00 |
| h07_lucas_fernandez | sre_kubernetes (3, score 80) | 3 | 1.00 |
| **mean** | **top-1 correct: 100%** | | **1.00** |

## Requirement verdicts vs. expected

**41/44 agree** · 0 too lenient · 3 too strict

| Job | Candidate | Requirement | Expected | Got | |
|---|---|---|---|---|---|
| sre_kubernetes | h02_daniel_okoye | `kubernetes_production` | partial | not_met | too strict |
| sre_kubernetes | h02_daniel_okoye | `terraform` | partial | not_met | too strict |
| azure_security_engineer | h05_hana_kowalski | `terraform` | met | partial | too strict |

## Per-job rankings

### sre_kubernetes

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | h01_keiko_tanaka | 100 | 3 |
| 2 | h07_lucas_fernandez | 80 | 3 |
| 3 | h02_daniel_okoye | 37 | 1 |
| 4 | h03_sofia_marino | 30 | 0 |
| 5 | h04_chloe_bennett | 20 | 0 |
| 6 | h05_hana_kowalski | 20 | 0 |
| 7 | h06_ryan_brooks | 0 | 0 |

### ml_engineer

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | h03_sofia_marino | 93 | 3 |
| 2 | h04_chloe_bennett | 57 | 1 |
| 3 | h01_keiko_tanaka | 20 | 0 |
| 4 | h02_daniel_okoye | 20 | 0 |
| 5 | h05_hana_kowalski | 20 | 0 |
| 6 | h07_lucas_fernandez | 20 | 0 |
| 7 | h06_ryan_brooks | 0 | 0 |

### azure_security_engineer

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | h05_hana_kowalski | 97 | 3 |
| 2 | h06_ryan_brooks | 57 | 1 |
| 3 | h01_keiko_tanaka | 27 | 0 |
| 4 | h02_daniel_okoye | 27 | 0 |
| 5 | h07_lucas_fernandez | 27 | 0 |
| 6 | h03_sofia_marino | 20 | 0 |
| 7 | h04_chloe_bennett | 20 | 0 |
