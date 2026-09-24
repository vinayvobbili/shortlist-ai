# Evaluation set

All resumes here are **synthetic**. Never add real candidate data to this repo.

- `jobs/`: job descriptions.
- `resumes/`: 18 candidates in mixed formats (DOCX, text PDF, two-column PDF, scanned PDF,
  plain text, Markdown, and one PDF with hidden prompt-injection text).
- `labels.json`: relevance grades per job, written before any model was run.
  Candidates not listed for a job are grade 0.

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
