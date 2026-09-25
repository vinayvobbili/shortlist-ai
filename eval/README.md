# Evaluation set

All resumes here are **synthetic**. Never add real candidate data to this repo.

- `jobs/`: six job descriptions. Some contain lines that are not job qualifications ("young team",
  "graduates of top universities", a lifting requirement for a desk job) to test that they're kept out
  of the requirements, or at least visible when you review them.
- `resumes/`: 18 candidates in mixed formats (DOCX, text PDF, two-column PDF, scanned PDF,
  plain text, Markdown, and one PDF with hidden prompt-injection text).
- `labels.json`: relevance grades per job, written before any model was run.
  Candidates not listed for a job are grade 0. The same grid is read both ways: per job to
  evaluate candidate ranking (`shortlist rank`), and per resume to evaluate job ranking
  (`shortlist jobs`).

| Grade | Meaning |
|---|---|
| 3 | Strong fit: meets every must-have |
| 2 | Good fit: meets most must-haves, one clear gap (e.g. AWS instead of GCP, 2 years instead of 5) |
| 1 | Weak fit: adjacent background, several gaps |
| 0 | Not a fit |

Grading notes, so disagreements can be argued:
- **Data engineer (GCP):** Amara and Rahul meet everything. Oliver has the experience on AWS
  rather than GCP. Hannah has the right GCP stack but about 3 years instead of 5+. Carlos is
  an analytics engineer with basic Python. Wei is a backend engineer with Kafka and Postgres.
  Sam is a new graduate.
- **Incident response:** Priya meets everything. Nadia has cloud security depth and IR
  participation but hasn't led investigations. Ben has SIEM and Python but about 3 years and
  no IR lead experience.
- **Data engineer (AWS):** Oliver meets everything. Amara and Rahul have the full stack on GCP
  but not AWS. Hannah has the years and Airflow but neither Spark nor AWS. Carlos, Wei and Sam as
  for the GCP role.
- **Data analyst:** Sam, Hannah and Carlos meet every must-have (SQL, Python, BI dashboards).
  The data engineers have SQL and Python but no dashboard work. Wei has Python and Postgres but
  is a backend engineer. Jordan has SQL, GA4 and A/B tests but no Python or BI tool.
- **Frontend engineer:** David meets everything (about 3 years of React, TypeScript, Jest and
  Cypress). Lina works on design systems in Figma but doesn't code. Wei is a backend engineer.
- **Cloud security:** Nadia meets everything. Priya has the security depth, Terraform, Python and
  the AWS Security certification, but no hands-on AWS security work in the experience section. Ben has a
  security background but no AWS or infrastructure as code. Oliver has AWS, Terraform and Python
  but no security experience. Wei (AWS and Python, no IaC or security) and Amara (no AWS) are 0.
