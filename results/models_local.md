# Local model comparison: `shortlist eval` on held-out set 3

Three MLX models served one at a time by `local-llm` on a 16 GB Apple Silicon Mac, each scoring
[`eval/heldout_years3/`](../eval/heldout_years3/) (10 candidates, 3 jobs, 29 expected requirement verdicts) with
`shortlist eval --backend local --repeats 1 --no-cache`, through `scripts/compare_local_model.sh`.
Raw reports: [`experiments/models/`](experiments/models/).

| Model | Verdicts agreeing (of 29) | Too lenient / strict | NDCG@3 (mean) | Top-1 correct | Wall time | Peak memory | Parse or format failures |
|---|---|---|---|---|---|---|---|
| Qwen3.5-9B-MLX-4bit (current) | 28 | 1 / 0 | 0.98 | 100% | 41 min (27 s per call) | 7.5 GB | 0 |
| Qwen3.5-9B-6bit | 27 | 2 / 0 | 1.00 | 100% | 53 min (36 s per call) | 9.7 GB | 0 |
| gemma-4-12B-it-4bit | 29 | 0 / 0 | 0.98 | 100% | 62 min (42 s per call) | 9.2 GB | 0 |

Each run is 90 model calls (about 170K tokens in, 33K to 36K out). Peak memory is the model server's footprint
(`footprint`, which counts MLX's Metal memory; RSS does not) sampled every 3 seconds.

## Reading

- The agreement spread is one verdict (28, 27, 29 of 29). The earlier three-ordering run of the 4-bit model on
  this set scored 29/29 in every ordering ([`heldout_years3_local.md`](heldout_years3_local.md)), so one verdict is
  inside the noise floor. The two Qwen misses are the same near-miss (`years_security`, marco_bianchi); the 6-bit
  adds `years_sre` for hiroshi_sato.
- Ranking quality is the same for all three (top-1 100%, NDCG@3 0.98 to 1.00).
- Gemma 4 is 50% slower per call and needs 1.7 GB more memory than the 4-bit Qwen. It also loads through
  mlx_vlm (mlx_lm has no `gemma4_unified` class), so the vision part stays in memory.
- The 6-bit Qwen is slower and larger and agreed on fewer verdicts.

## Decision

Keep Qwen3.5-9B-MLX-4bit: agreement is within one verdict of the best, and it is the fastest and smallest. The 6-bit
and Gemma 4 downloads were removed from the Hugging Face cache.

The main 18-candidate set (108 pairs) was not run: it took over 40 minutes for the 4-bit model alone.
