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

## Stability across 3 requirement orderings

Run 1 lists the requirements as written; the others shuffle them (seeds 1–2). Scoring is order-independent, so differences are the model's sensitivity to an irrelevant detail, plus sampling noise for backends that sample.

| | min | mean | max |
|---|---|---|---|
| Candidate ranking: mean NDCG@3 | 1.00 | 1.00 | 1.00 |
| Candidate ranking: top-1 correct (of 3) | 3.0 | 3.0 | 3.0 |
| Job ranking: top-1 correct (of 7) | 7.0 | 7.0 | 7.0 |
| Expected verdicts agreeing (of 44) | 41.0 | 41.0 | 41.0 |
| ... too lenient | 0.0 | 1.0 | 2.0 |
| ... too strict | 1.0 | 2.0 | 3.0 |

- **136 of 147 requirement verdicts (93%) were identical in every ordering.**
- A (job, resume) score moved by 3.2 points on average across orderings, and at most 26.6 (h02_daniel_okoye for sre_kubernetes).

Verdicts that changed with the ordering:

| Job | Candidate | Requirement | Verdict in each run |
|---|---|---|---|
| azure_security_engineer | h01_keiko_tanaka | `incident_response` | not_met → partial → not_met |
| azure_security_engineer | h05_hana_kowalski | `terraform` | partial → met → partial |
| azure_security_engineer | h06_ryan_brooks | `incident_response` | not_met → partial → not_met |
| ml_engineer | h04_chloe_bennett | `dl_framework` | partial → met → met |
| sre_kubernetes | h02_daniel_okoye | `cka` | met → not_met → met |
| sre_kubernetes | h02_daniel_okoye | `kubernetes_production` | not_met → partial → not_met |
| sre_kubernetes | h02_daniel_okoye | `observability` | not_met → partial → not_met |
| sre_kubernetes | h02_daniel_okoye | `terraform` | not_met → partial → partial |
| sre_kubernetes | h02_daniel_okoye | `years_infra` | partial → met → met |
| sre_kubernetes | h05_hana_kowalski | `python_or_go` | partial → met → met |
| sre_kubernetes | h05_hana_kowalski | `terraform` | partial → met → partial |

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
