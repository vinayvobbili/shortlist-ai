# Held-out set: years of experience, round 2

All data here is **synthetic**. It was written and committed **before** any model was run on it and
before the change it tests. After you look at the results, it is no longer held out.

```bash
shortlist eval --backend local --eval-dir eval/heldout_years2 --repeats 3 --out results/heldout_years2_local.md
```

## What it tests

[`../heldout_years/`](../heldout_years/) has been seen, so this is a fresh set for the next attempt:
computing years requirements in code, with the model judging only whether each role is in the
named field. It targets the two conditions where the scorer failed:

- **Long requirement lists** (ten per job), with the "N+ years of *X*" requirement in the middle.
  On the dev set, that's where the model dropped the field from the requirement and counted every
  year.
- **Career-changers:** a long earlier career outside *X*, then fewer years in *X* than asked
  (accountant to DevOps, print designer to UX, hospital nurse to clinical research). Expected:
  `partial`.

It also has long unrelated careers (flight attendant, 15 years; art teacher learning UX), expected
`not_met`, and relevant years that only clear the bar when two roles are added up (infrastructure
engineer then SRE, about 2½ + 2 years against "4+"), expected `met`.

## Files

- `jobs/*.json`: reviewed requirements with fixed ids.
- `resumes/`: nine candidates.
- `labels.json`: relevance grades (0–3); unlisted pairs are 0.
- `verdicts.json`: the expected verdict for every years requirement against every candidate (27),
  plus 8 other requirements to catch collateral changes.

## Verdict rules used for the gold labels

- Only years in the field the requirement names count. Other work, however long, doesn't.
- Some years in the field but fewer than asked: `partial`. None: `not_met`.
- The career-changers' relevant roles are current, so their durations grow. The labels assume the
  eval runs before October 2027, when the shortest of them (the research coordinator's) reaches 2 years.
