#!/usr/bin/env bash
# Run the local evals once against whatever model local-llm serves, timing each set and sampling the model
# server's resident memory. Usage: scripts/compare_local_model.sh <label> [outdir]
# Writes <outdir>/<label>/<set>.md and <outdir>/<label>/summary.txt (set, seconds, peak RSS MB).
set -u
label=${1:?label}
here=$(cd "$(dirname "$0")/.." && pwd)
out=${2:-$here/results/experiments/models}/$label
mkdir -p "$out"
: > "$out/summary.txt"
echo 0 > "$out/.peak"
sample() {  # peak RSS (MB) of the model server processes while a set runs
  while :; do
    rss=0  # footprint, not RSS: MLX's Metal memory isn't in RSS. The model child listens on local-llm's port + 1.
    for p in $(pgrep -f "port 8011"); do
      mb=$(footprint "$p" 2>/dev/null | awk '/Footprint:/ {print $5; exit}')
      [ "${mb:-0}" -gt "$rss" ] && rss=$mb
    done
    [ "$rss" -gt "$(cat "$out/.peak")" ] && echo "$rss" > "$out/.peak"
    sleep 3
  done
}
sample & sampler=$!
trap 'kill $sampler 2>/dev/null' EXIT
# The main set (108 pairs) alone runs over 40 minutes per model, so it's opt-in: SETS="eval eval/heldout ..."
for set in ${SETS:-eval/heldout eval/heldout_years eval/heldout_years2 eval/heldout_years3}; do
  name=$(basename "$set")
  start=$(date +%s)
  "$here/.venv/bin/shortlist" eval --backend local --repeats 1 --no-cache --allow-failures \
    --eval-dir "$here/$set" --out "$out/$name.md" > "$out/$name.log" 2>&1
  echo "$name $(( $(date +%s) - start )) $(cat "$out/.peak")" >> "$out/summary.txt"
done
rm -f "$out/.peak"
cat "$out/summary.txt"
