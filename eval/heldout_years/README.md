# Held-out set: years of experience

All data here is **synthetic**. It was written and committed **before** any model was run on it and
before the change it tests. After you look at the results, it is no longer held out.

```bash
shortlist eval --backend local --eval-dir eval/heldout_years --repeats 3 --out results/heldout_years_local.md
```

## What it tests

On the dev set, run with shuffled requirement orders, the scorer often marked "3+ years of
professional data engineering experience" as met for candidates whose years were in another field
(a nurse's 10 years). The blind profile opens the experience section with the total across all
roles, and the model used that number. Each job here has an "N+ years of *X*" must-have, and the
candidates cover three cases:

- **Long careers in unrelated fields** (teacher, 12 years; warehouse supervisor, 14): zero years in
  *X*, so `not_met` for every job, however large the total.
- **Career-changers** with a long earlier career and fewer years in *X* than asked (retail manager
  to backend developer, help desk to SOC, chef to FP&A): `partial`.
- **Years that only clear the bar when roles are added up** (two backend roles of about 3 years
  each, then a management role): `met`. This checks that removing the total doesn't make the model
  under-count.

## Files

- `jobs/*.json`: reviewed requirements with fixed ids.
- `resumes/`: nine candidates.
- `labels.json`: relevance grades (0–3); unlisted pairs are 0.
- `verdicts.json`: the expected verdict for every years requirement against every candidate (27),
  plus 9 other requirements to catch collateral changes.

## Verdict rules used for the gold labels

- Only years in the field the requirement names count. Other work, however long, doesn't.
- Some years in the field but fewer than asked: `partial`. None: `not_met`.
- The career-changers' relevant roles are current, so their durations grow. The labels assume the
  eval runs before September 2027, when the shortest of them (the SOC analyst's) reaches 3 years.

## Results so far

Used once, to test removing the "Experience (total N yrs)" line from the blind profile (commit
`2ba1452`, reverted). Expected verdicts matched 34.3 of 36 on average both with and without the
line. See the main README's "A fix that didn't work". **This set has now been seen**, so the next
change needs fresh cases.
