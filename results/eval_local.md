# Ranking eval: `local:mlx-community/Qwen3.5-9B-MLX-4bit`

## Candidates for each job (`shortlist rank`)

| Job | NDCG@3 | NDCG@5 | P@3 | Top-1 correct |
|---|---|---|---|---|
| senior_data_engineer_gcp | 1.00 | 1.00 | 1.00 | yes |
| incident_response_engineer | 1.00 | 1.00 | 1.00 | yes |
| data_engineer_aws | 1.00 | 1.00 | 1.00 | yes |
| data_analyst | 1.00 | 0.96 | 1.00 | yes |
| frontend_engineer | 0.94 | 0.99 | 0.33 | yes |
| cloud_security_engineer | 0.84 | 0.85 | 0.67 | no |
| **mean** | **0.96** | **0.96** | **0.83** | **83%** |

## Jobs for each resume (`shortlist jobs`)

Resumes that fit at least one of the 6 jobs.

| Resume | Top pick (grade) | Best grade available | NDCG@3 |
|---|---|---|---|
| c01_priya_raman | cloud_security_engineer (2, score 100) | 3 | 0.83 |
| c03_wei_zhang | data_analyst (1, score 50) | 1 | 1.00 |
| c05_sam_okafor | data_analyst (3, score 75) | 3 | 1.00 |
| c06_rahul_menon | senior_data_engineer_gcp (3, score 100) | 3 | 1.00 |
| c08_jordan_blake | data_analyst (1, score 33) | 1 | 1.00 |
| c11_lina_haddad | frontend_engineer (1, score 6) | 1 | 1.00 |
| c12_david_kim | frontend_engineer (3, score 89) | 3 | 1.00 |
| c13_oliver_grant | data_engineer_aws (3, score 96) | 3 | 1.00 |
| c14_hannah_lee | data_analyst (3, score 88) | 3 | 0.97 |
| c15_carlos_diaz | data_analyst (3, score 71) | 3 | 1.00 |
| c16_amara_nwosu | senior_data_engineer_gcp (3, score 100) | 3 | 1.00 |
| c17_ben_carter | incident_response_engineer (2, score 47) | 2 | 1.00 |
| c18_nadia_haddad | cloud_security_engineer (3, score 94) | 3 | 1.00 |
| **mean** | **top-1 correct: 92%** | | **0.99** |

## Per-job rankings

### senior_data_engineer_gcp

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | c06_rahul_menon | 100 | 3 |
| 2 | c16_amara_nwosu | 100 | 3 |
| 3 | c13_oliver_grant | 68 | 2 |
| 4 | c14_hannah_lee | 59 | 2 |
| 5 | c15_carlos_diaz | 36 | 1 |
| 6 | c03_wei_zhang | 32 | 1 |
| 7 | c01_priya_raman | 27 | 0 |
| 8 | c05_sam_okafor | 27 | 1 |
| 9 | c17_ben_carter | 27 | 0 |
| 10 | c18_nadia_haddad | 27 | 0 |
| 11 | c04_ana_torres | 14 | 0 |
| 12 | c08_jordan_blake | 14 | 0 |
| 13 | c09_elena_petrova | 14 | 0 |
| 14 | c12_david_kim | 14 | 0 |
| 15 | c02_marcus_bell | 0 | 0 |
| 16 | c10_tom_reyes | 0 | 0 |
| 17 | c11_lina_haddad | 0 | 0 |
| - | c07_grace_whitfield | failed: ValueError: c07_grace_whitfield.pdf has no text layer (scann | - |

### incident_response_engineer

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | c01_priya_raman | 100 | 3 |
| 2 | c18_nadia_haddad | 53 | 2 |
| 3 | c17_ben_carter | 47 | 2 |
| 4 | c03_wei_zhang | 19 | 0 |
| 5 | c05_sam_okafor | 19 | 0 |
| 6 | c06_rahul_menon | 19 | 0 |
| 7 | c13_oliver_grant | 19 | 0 |
| 8 | c14_hannah_lee | 19 | 0 |
| 9 | c16_amara_nwosu | 19 | 0 |
| 10 | c15_carlos_diaz | 9 | 0 |
| 11 | c02_marcus_bell | 0 | 0 |
| 12 | c04_ana_torres | 0 | 0 |
| 13 | c08_jordan_blake | 0 | 0 |
| 14 | c09_elena_petrova | 0 | 0 |
| 15 | c10_tom_reyes | 0 | 0 |
| 16 | c11_lina_haddad | 0 | 0 |
| 17 | c12_david_kim | 0 | 0 |
| - | c07_grace_whitfield | failed: ValueError: c07_grace_whitfield.pdf has no text layer (scann | - |

### data_engineer_aws

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | c13_oliver_grant | 96 | 3 |
| 2 | c06_rahul_menon | 68 | 2 |
| 3 | c16_amara_nwosu | 66 | 2 |
| 4 | c14_hannah_lee | 59 | 1 |
| 5 | c03_wei_zhang | 46 | 1 |
| 6 | c15_carlos_diaz | 39 | 1 |
| 7 | c01_priya_raman | 36 | 0 |
| 8 | c18_nadia_haddad | 36 | 0 |
| 9 | c05_sam_okafor | 27 | 1 |
| 10 | c17_ben_carter | 27 | 0 |
| 11 | c04_ana_torres | 14 | 0 |
| 12 | c08_jordan_blake | 14 | 0 |
| 13 | c12_david_kim | 14 | 0 |
| 14 | c02_marcus_bell | 0 | 0 |
| 15 | c09_elena_petrova | 0 | 0 |
| 16 | c10_tom_reyes | 0 | 0 |
| 17 | c11_lina_haddad | 0 | 0 |
| - | c07_grace_whitfield | failed: ValueError: c07_grace_whitfield.pdf has no text layer (scann | - |

### data_analyst

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | c14_hannah_lee | 88 | 3 |
| 2 | c05_sam_okafor | 75 | 3 |
| 3 | c15_carlos_diaz | 71 | 3 |
| 4 | c13_oliver_grant | 58 | 2 |
| 5 | c03_wei_zhang | 50 | 1 |
| 6 | c06_rahul_menon | 50 | 2 |
| 7 | c16_amara_nwosu | 50 | 2 |
| 8 | c08_jordan_blake | 33 | 1 |
| 9 | c01_priya_raman | 25 | 0 |
| 10 | c17_ben_carter | 25 | 0 |
| 11 | c18_nadia_haddad | 25 | 0 |
| 12 | c12_david_kim | 12 | 0 |
| 13 | c04_ana_torres | 8 | 0 |
| 14 | c02_marcus_bell | 0 | 0 |
| 15 | c09_elena_petrova | 0 | 0 |
| 16 | c10_tom_reyes | 0 | 0 |
| 17 | c11_lina_haddad | 0 | 0 |
| - | c07_grace_whitfield | failed: ValueError: c07_grace_whitfield.pdf has no text layer (scann | - |

### frontend_engineer

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | c12_david_kim | 89 | 3 |
| 2 | c11_lina_haddad | 6 | 1 |
| 3 | c01_priya_raman | 0 | 0 |
| 4 | c02_marcus_bell | 0 | 0 |
| 5 | c03_wei_zhang | 0 | 1 |
| 6 | c04_ana_torres | 0 | 0 |
| 7 | c05_sam_okafor | 0 | 0 |
| 8 | c06_rahul_menon | 0 | 0 |
| 9 | c08_jordan_blake | 0 | 0 |
| 10 | c09_elena_petrova | 0 | 0 |
| 11 | c10_tom_reyes | 0 | 0 |
| 12 | c13_oliver_grant | 0 | 0 |
| 13 | c14_hannah_lee | 0 | 0 |
| 14 | c15_carlos_diaz | 0 | 0 |
| 15 | c16_amara_nwosu | 0 | 0 |
| 16 | c17_ben_carter | 0 | 0 |
| 17 | c18_nadia_haddad | 0 | 0 |
| - | c07_grace_whitfield | failed: ValueError: c07_grace_whitfield.pdf has no text layer (scann | - |

### cloud_security_engineer

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | c01_priya_raman | 100 | 2 |
| 2 | c18_nadia_haddad | 94 | 3 |
| 3 | c13_oliver_grant | 28 | 1 |
| 4 | c16_amara_nwosu | 28 | 0 |
| 5 | c17_ben_carter | 28 | 1 |
| 6 | c03_wei_zhang | 19 | 0 |
| 7 | c05_sam_okafor | 19 | 0 |
| 8 | c06_rahul_menon | 19 | 0 |
| 9 | c14_hannah_lee | 19 | 0 |
| 10 | c15_carlos_diaz | 9 | 0 |
| 11 | c02_marcus_bell | 0 | 0 |
| 12 | c04_ana_torres | 0 | 0 |
| 13 | c08_jordan_blake | 0 | 0 |
| 14 | c09_elena_petrova | 0 | 0 |
| 15 | c10_tom_reyes | 0 | 0 |
| 16 | c11_lina_haddad | 0 | 0 |
| 17 | c12_david_kim | 0 | 0 |
| - | c07_grace_whitfield | failed: ValueError: c07_grace_whitfield.pdf has no text layer (scann | - |
