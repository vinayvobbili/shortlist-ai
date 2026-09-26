# Held-out set: years of experience, round 3 (adjacent roles)

All data here is **synthetic**. It was written and committed **before** any model was run on it and
before the change it tests. After you look at the results, it is no longer held out.

```bash
shortlist eval --backend local --eval-dir eval/heldout_years3 --repeats 3 --out results/heldout_years3_local.md
```

## What it tests

Computing years in code fixed the scorer counting every year of a career. But the per-role question
("is this role in the field?", yes or no) counted roles that only touch the field: a platform
engineer as security engineering because the clusters get patched, an ML engineer as
infrastructure because the models run on Kubernetes. Those cases came from
[`../heldout/`](../heldout/), which has been seen, so this set is new. Each job has candidates
whose **main work** is the field and candidates whose work **touches** it:

| Job ("N+ years of *X*") | Main work in *X* | Touches *X* |
|---|---|---|
| Security engineer (3+) | security engineer; SRE turned security engineer | platform engineer who patches and manages IAM roles; IT auditor who runs access reviews; network engineer who configures firewalls |
| Data engineer (4+) | "Software Engineer, Data Platform" building Spark pipelines; analyst turned data engineer | backend engineer who publishes Kafka events; ML engineer who builds feature pipelines |
| Site reliability (3+) | SRE; the same platform engineer | ML engineer who deploys on Kubernetes |

It also checks the other direction: a title that doesn't name the field ("Software Engineer, Data
Platform") must still count when the work is squarely in it, and one role can count for one job
(platform engineering as infrastructure) and not another (as security engineering).

## Files

- `jobs/*.json`: reviewed requirements, ten per job, the years requirement mid-list.
- `resumes/`: ten candidates.
- `labels.json`: relevance grades (0–3); unlisted pairs are 0.
- `verdicts.json`: the expected years verdict for every candidate against every job (29), except
  whether network engineering counts as infrastructure engineering, which is left out as ambiguous.

## Verdict rules used for the gold labels

- Only years whose **main work** is in the named field count. A role that touches the field
  doesn't count, however long.
- Some such years but fewer than asked: `partial`. None: `not_met`.
- Current roles grow; the labels assume the eval runs before October 2027.
