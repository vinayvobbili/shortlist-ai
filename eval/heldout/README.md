# Held-out set

All data here is **synthetic**. It was written and committed **before** any model was run on it,
and before the scorer change it tests. Use it to check changes, not to tune them: after you
look at the results, it is no longer held out, so add fresh cases for the next change.

```bash
shortlist eval --backend local --eval-dir eval/heldout --out results/heldout_local.md
```

## What it tests

On the dev set, the scorer treated a certification or a skills-list keyword as hands-on
experience. This set checks that failure in both directions:

- **Too lenient:** each job has a candidate whose certifications and skills list match the job
  but whose work history doesn't (a systems administrator with CKA and Terraform certificates,
  an analyst with ML certificates, an IT support specialist with Azure security certificates).
- **Too strict:** a skills-list entry should still count when a requirement only names a tool
  ("Python or Go", "KQL", "Terraform" as a nice-to-have). Real experience should count when the
  resume uses a different word: "production EKS clusters" is running Kubernetes in production.

## Files

- `jobs/*.json`: reviewed requirements (what `shortlist requirements` produces after a person
  edits it), so requirement ids are fixed.
- `resumes/`: seven candidates.
- `labels.json`: relevance grades (0–3), same rubric as the dev set. Unlisted pairs are 0.
- `verdicts.json`: the expected verdict for selected (job, candidate, requirement) triples.
  Ambiguous ones are left out on purpose (e.g. whether 6 years as a systems administrator counts
  as "infrastructure engineering").

## Verdict rules used for the gold labels

- A requirement for **hands-on, production or professional experience** is met only by work
  history that shows it. A certification or a skills-list entry alone is `partial`.
- A requirement that just **names a skill or tool** is met by a skills-list entry.
- A requirement **for a certification** is met by that certification.
