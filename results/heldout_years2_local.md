# Ranking eval: `local:mlx-community/Qwen3.5-9B-MLX-4bit`

## Candidates for each job (`shortlist rank`)

| Job | NDCG@3 | NDCG@5 | P@3 | Top-1 correct |
|---|---|---|---|---|
| devops_engineer | 1.00 | 1.00 | 1.00 | yes |
| ux_designer | 1.00 | 1.00 | 0.67 | yes |
| clinical_research_coordinator | 1.00 | 1.00 | 0.67 | yes |
| **mean** | **1.00** | **1.00** | **0.78** | **100%** |

## Jobs for each resume (`shortlist jobs`)

Resumes that fit at least one of the 3 jobs.

| Resume | Top pick (grade) | Best grade available | NDCG@3 |
|---|---|---|---|
| z01_sipho_dlamini | devops_engineer (3, score 100) | 3 | 1.00 |
| z02_ana_lucia_ferreira | devops_engineer (2, score 86) | 2 | 1.00 |
| z03_jonah_whitaker | devops_engineer (3, score 100) | 3 | 1.00 |
| z04_camille_dubois | ux_designer (2, score 83) | 2 | 1.00 |
| z05_priyanka_iyer | ux_designer (3, score 100) | 3 | 1.00 |
| z06_grace_mwangi | clinical_research_coordinator (2, score 79) | 2 | 1.00 |
| z07_daniel_osei | clinical_research_coordinator (3, score 98) | 3 | 1.00 |
| z09_ethan_brooks | ux_designer (1, score 25) | 1 | 1.00 |
| **mean** | **top-1 correct: 100%** | | **1.00** |

## Requirement verdicts vs. expected

**35/35 agree** · 0 too lenient · 0 too strict

## Stability across 3 requirement orderings

Run 1 lists the requirements as written; the others shuffle them (seeds 1–2). Scoring is order-independent, so differences are the model's sensitivity to an irrelevant detail, plus sampling noise for backends that sample.

| | min | mean | max |
|---|---|---|---|
| Candidate ranking: mean NDCG@3 | 1.00 | 1.00 | 1.00 |
| Candidate ranking: top-1 correct (of 3) | 3.0 | 3.0 | 3.0 |
| Job ranking: top-1 correct (of 8) | 8.0 | 8.0 | 8.0 |
| Expected verdicts agreeing (of 35) | 35.0 | 35.0 | 35.0 |
| ... too lenient | 0.0 | 0.0 | 0.0 |
| ... too strict | 0.0 | 0.0 | 0.0 |

- **263 of 270 requirement verdicts (97%) were identical in every ordering.**
- A (job, resume) score moved by 1.0 points on average across orderings, and at most 11.5 (z05_priyanka_iyer for devops_engineer).

Verdicts that changed with the ordering:

| Job | Candidate | Requirement | Verdict in each run |
|---|---|---|---|
| clinical_research_coordinator | z06_grace_mwangi | `ccrp` | not_met → partial → not_met |
| devops_engineer | z05_priyanka_iyer | `monitoring` | partial → not_met → not_met |
| devops_engineer | z05_priyanka_iyer | `scripting` | partial → not_met → not_met |
| ux_designer | z01_sipho_dlamini | `analytics` | not_met → met → partial |
| ux_designer | z04_camille_dubois | `presenting` | partial → met → met |
| ux_designer | z04_camille_dubois | `user_research` | met → met → partial |
| ux_designer | z09_ethan_brooks | `presenting` | not_met → partial → met |

## Per-job rankings

### devops_engineer

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | z01_sipho_dlamini | 100 | 3 |
| 2 | z03_jonah_whitaker | 100 | 3 |
| 3 | z02_ana_lucia_ferreira | 86 | 2 |
| 4 | z05_priyanka_iyer | 12 | 0 |
| 5 | z04_camille_dubois | 0 | 0 |
| 6 | z06_grace_mwangi | 0 | 0 |
| 7 | z07_daniel_osei | 0 | 0 |
| 8 | z08_rosa_delgado | 0 | 0 |
| 9 | z09_ethan_brooks | 0 | 0 |

### ux_designer

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | z05_priyanka_iyer | 100 | 3 |
| 2 | z04_camille_dubois | 83 | 2 |
| 3 | z09_ethan_brooks | 25 | 1 |
| 4 | z01_sipho_dlamini | 0 | 0 |
| 5 | z02_ana_lucia_ferreira | 0 | 0 |
| 6 | z03_jonah_whitaker | 0 | 0 |
| 7 | z06_grace_mwangi | 0 | 0 |
| 8 | z07_daniel_osei | 0 | 0 |
| 9 | z08_rosa_delgado | 0 | 0 |

### clinical_research_coordinator

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | z07_daniel_osei | 98 | 3 |
| 2 | z06_grace_mwangi | 79 | 2 |
| 3 | z01_sipho_dlamini | 0 | 0 |
| 4 | z02_ana_lucia_ferreira | 0 | 0 |
| 5 | z03_jonah_whitaker | 0 | 0 |
| 6 | z04_camille_dubois | 0 | 0 |
| 7 | z05_priyanka_iyer | 0 | 0 |
| 8 | z08_rosa_delgado | 0 | 0 |
| 9 | z09_ethan_brooks | 0 | 0 |
