# Ranking eval: `local:mlx-community/Qwen3.5-9B-MLX-4bit`

Experiment, reverted: blind profile without the "Experience (total N yrs)" line (commit `2ba1452`). The shipped code keeps the line; see the main README.

## Candidates for each job (`shortlist rank`)

| Job | NDCG@3 | NDCG@5 | P@3 | Top-1 correct |
|---|---|---|---|---|
| senior_data_engineer_gcp | 1.00 | 1.00 | 1.00 | yes |
| incident_response_engineer | 1.00 | 1.00 | 1.00 | yes |
| data_engineer_aws | 1.00 | 1.00 | 1.00 | yes |
| data_analyst | 0.87 | 0.98 | 1.00 | yes |
| frontend_engineer | 0.94 | 0.99 | 0.33 | yes |
| cloud_security_engineer | 1.00 | 1.00 | 0.67 | yes |
| **mean** | **0.97** | **0.99** | **0.83** | **100%** |

## Jobs for each resume (`shortlist jobs`)

Resumes that fit at least one of the 6 jobs.

| Resume | Top pick (grade) | Best grade available | NDCG@3 |
|---|---|---|---|
| c01_priya_raman | incident_response_engineer (3, score 100) | 3 | 1.00 |
| c03_wei_zhang | data_engineer_aws (1, score 52) | 1 | 1.00 |
| c05_sam_okafor | data_analyst (3, score 75) | 3 | 1.00 |
| c06_rahul_menon | senior_data_engineer_gcp (3, score 100) | 3 | 1.00 |
| c08_jordan_blake | data_analyst (1, score 33) | 1 | 1.00 |
| c11_lina_haddad | frontend_engineer (1, score 6) | 1 | 1.00 |
| c12_david_kim | frontend_engineer (3, score 81) | 3 | 1.00 |
| c13_oliver_grant | data_engineer_aws (3, score 96) | 3 | 1.00 |
| c14_hannah_lee | data_analyst (3, score 88) | 3 | 0.97 |
| c15_carlos_diaz | data_analyst (3, score 54) | 3 | 1.00 |
| c16_amara_nwosu | senior_data_engineer_gcp (3, score 100) | 3 | 1.00 |
| c17_ben_carter | incident_response_engineer (2, score 66) | 2 | 1.00 |
| c18_nadia_haddad | cloud_security_engineer (3, score 94) | 3 | 1.00 |
| **mean** | **top-1 correct: 100%** | | **1.00** |

## Stability across 3 requirement orderings

Run 1 lists the requirements as written; the others shuffle them (seeds 1–2). Scoring is order-independent, so differences are the model's sensitivity to an irrelevant detail, plus sampling noise for backends that sample.

| | min | mean | max |
|---|---|---|---|
| Candidate ranking: mean NDCG@3 | 0.96 | 0.97 | 0.99 |
| Candidate ranking: top-1 correct (of 6) | 5.0 | 5.7 | 6.0 |
| Job ranking: top-1 correct (of 13) | 11.0 | 12.0 | 13.0 |

Wrong top pick: run 2: cloud_security_engineer, c01_priya_raman, c11_lina_haddad; run 3: c11_lina_haddad.

- **804 of 850 requirement verdicts (95%) were identical in every ordering.**
- A (job, resume) score moved by 3.7 points on average across orderings, and at most 33.3 (c15_carlos_diaz for data_analyst).

Verdicts that changed with the ordering:

| Job | Candidate | Requirement | Verdict in each run |
|---|---|---|---|
| cloud_security_engineer | c01_priya_raman | `aws_security_experience` | partial → met → partial |
| cloud_security_engineer | c13_oliver_grant | `infrastructure_as_code` | partial → met → partial |
| cloud_security_engineer | c17_ben_carter | `incident_response_experience` | partial → met → met |
| data_analyst | c14_hannah_lee | `statistics_ab_testing` | partial → partial → not_met |
| data_analyst | c15_carlos_diaz | `advanced_excel` | not_met → not_met → partial |
| data_analyst | c15_carlos_diaz | `dbt_data_modeling` | partial → met → met |
| data_analyst | c15_carlos_diaz | `python_or_r` | not_met → partial → met |
| data_analyst | c16_amara_nwosu | `dbt_data_modeling` | partial → not_met → not_met |
| data_analyst | c16_amara_nwosu | `python_or_r` | met → partial → met |
| data_engineer_aws | c01_priya_raman | `years_experience` | not_met → met → met |
| data_engineer_aws | c03_wei_zhang | `aws_data_services` | partial → partial → not_met |
| data_engineer_aws | c03_wei_zhang | `sql` | met → partial → not_met |
| data_engineer_aws | c04_ana_torres | `years_experience` | not_met → met → met |
| data_engineer_aws | c08_jordan_blake | `years_experience` | not_met → met → met |
| data_engineer_aws | c09_elena_petrova | `years_experience` | not_met → met → met |
| data_engineer_aws | c11_lina_haddad | `years_experience` | not_met → not_met → met |
| data_engineer_aws | c12_david_kim | `sql` | partial → partial → met |
| data_engineer_aws | c12_david_kim | `years_experience` | not_met → partial → met |
| data_engineer_aws | c13_oliver_grant | `streaming_kafka` | met → met → not_met |
| data_engineer_aws | c13_oliver_grant | `terraform` | met → met → not_met |
| data_engineer_aws | c14_hannah_lee | `aws_data_services` | partial → partial → not_met |
| data_engineer_aws | c15_carlos_diaz | `python` | met → met → partial |
| data_engineer_aws | c15_carlos_diaz | `years_experience` | partial → met → met |
| data_engineer_aws | c16_amara_nwosu | `python` | met → met → partial |
| data_engineer_aws | c16_amara_nwosu | `streaming_kafka` | not_met → partial → partial |
| data_engineer_aws | c18_nadia_haddad | `streaming_kafka` | not_met → partial → not_met |
| frontend_engineer | c12_david_kim | `web_dev_experience` | partial → met → met |
| incident_response_engineer | c01_priya_raman | `malware_analysis` | met → partial → met |
| incident_response_engineer | c05_sam_okafor | `python_scripting` | met → partial → met |
| incident_response_engineer | c06_rahul_menon | `cloud_security_experience` | not_met → not_met → partial |
| incident_response_engineer | c06_rahul_menon | `python_scripting` | met → partial → met |
| incident_response_engineer | c14_hannah_lee | `cloud_security_experience` | not_met → not_met → partial |
| incident_response_engineer | c16_amara_nwosu | `cloud_security_experience` | partial → not_met → partial |
| incident_response_engineer | c17_ben_carter | `malware_analysis` | not_met → partial → partial |
| incident_response_engineer | c18_nadia_haddad | `incident_investigation_leadership` | not_met → partial → not_met |
| incident_response_engineer | c18_nadia_haddad | `security_certifications` | partial → partial → not_met |
| senior_data_engineer_gcp | c01_priya_raman | `years_experience` | not_met → met → met |
| senior_data_engineer_gcp | c03_wei_zhang | `sql` | not_met → not_met → partial |
| senior_data_engineer_gcp | c04_ana_torres | `years_experience` | not_met → met → not_met |
| senior_data_engineer_gcp | c09_elena_petrova | `years_experience` | not_met → met → not_met |
| senior_data_engineer_gcp | c11_lina_haddad | `years_experience` | not_met → met → partial |
| senior_data_engineer_gcp | c12_david_kim | `data_quality_tooling` | partial → not_met → not_met |
| senior_data_engineer_gcp | c12_david_kim | `sql` | partial → not_met → partial |
| senior_data_engineer_gcp | c14_hannah_lee | `years_experience` | partial → met → met |
| senior_data_engineer_gcp | c15_carlos_diaz | `python` | partial → met → not_met |
| senior_data_engineer_gcp | c18_nadia_haddad | `years_experience` | not_met → met → met |

## Per-job rankings

### senior_data_engineer_gcp

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | c06_rahul_menon | 100 | 3 |
| 2 | c16_amara_nwosu | 100 | 3 |
| 3 | c13_oliver_grant | 68 | 2 |
| 4 | c14_hannah_lee | 66 | 2 |
| 5 | c15_carlos_diaz | 39 | 1 |
| 6 | c03_wei_zhang | 32 | 1 |
| 7 | c05_sam_okafor | 27 | 1 |
| 8 | c01_priya_raman | 14 | 0 |
| 9 | c08_jordan_blake | 14 | 0 |
| 10 | c17_ben_carter | 14 | 0 |
| 11 | c18_nadia_haddad | 14 | 0 |
| 12 | c12_david_kim | 9 | 0 |
| 13 | c02_marcus_bell | 0 | 0 |
| 14 | c04_ana_torres | 0 | 0 |
| 15 | c09_elena_petrova | 0 | 0 |
| 16 | c10_tom_reyes | 0 | 0 |
| 17 | c11_lina_haddad | 0 | 0 |
| - | c07_grace_whitfield | failed: ValueError: c07_grace_whitfield.pdf has no text layer (scann | - |

### incident_response_engineer

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | c01_priya_raman | 100 | 3 |
| 2 | c17_ben_carter | 66 | 2 |
| 3 | c18_nadia_haddad | 56 | 2 |
| 4 | c03_wei_zhang | 22 | 0 |
| 5 | c13_oliver_grant | 22 | 0 |
| 6 | c16_amara_nwosu | 22 | 0 |
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

### data_engineer_aws

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | c13_oliver_grant | 96 | 3 |
| 2 | c16_amara_nwosu | 73 | 2 |
| 3 | c06_rahul_menon | 70 | 2 |
| 4 | c14_hannah_lee | 66 | 1 |
| 5 | c03_wei_zhang | 52 | 1 |
| 6 | c15_carlos_diaz | 39 | 1 |
| 7 | c18_nadia_haddad | 36 | 0 |
| 8 | c05_sam_okafor | 27 | 1 |
| 9 | c01_priya_raman | 23 | 0 |
| 10 | c08_jordan_blake | 14 | 0 |
| 11 | c17_ben_carter | 14 | 0 |
| 12 | c12_david_kim | 7 | 0 |
| 13 | c02_marcus_bell | 0 | 0 |
| 14 | c04_ana_torres | 0 | 0 |
| 15 | c09_elena_petrova | 0 | 0 |
| 16 | c10_tom_reyes | 0 | 0 |
| 17 | c11_lina_haddad | 0 | 0 |
| - | c07_grace_whitfield | failed: ValueError: c07_grace_whitfield.pdf has no text layer (scann | - |

### data_analyst

| Rank | Candidate | Score | Gold grade |
|---|---|---|---|
| 1 | c14_hannah_lee | 88 | 3 |
| 2 | c05_sam_okafor | 75 | 3 |
| 3 | c13_oliver_grant | 58 | 2 |
| 4 | c15_carlos_diaz | 54 | 3 |
| 5 | c16_amara_nwosu | 54 | 2 |
| 6 | c03_wei_zhang | 50 | 1 |
| 7 | c06_rahul_menon | 50 | 2 |
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
| 1 | c12_david_kim | 81 | 3 |
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
| 1 | c18_nadia_haddad | 94 | 3 |
| 2 | c01_priya_raman | 88 | 2 |
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
