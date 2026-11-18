#!/bin/bash
# Independent final verification through the UNCHANGED benchmark harness + finalized teachers (separate process, separate cache):
#   eval.sh DOM PRED.jsonl PUBLIC.jsonl PRIVATE_INDEX.jsonl [WORKERS=2] [CPU0=0]
# Seals PRED (sha256, read-only) BEFORE any teacher call unless already sealed; then validate -> queries -> teach -> evaluate.
# Teacher cache: $CACHE (default $AB_OUT/cache); results: PRED_results.jsonl next to PRED.  Nothing is retried after this step.
set -e
H=$(cd "$(dirname "$0")" && pwd); source "$H/env.sh"
D=$1; P=$(realpath "$2"); PUB=$(realpath "$3"); PRIV=$(realpath "$4"); W=${5:-2}; C0=${6:-0}
CACHE=${CACHE:-$AB_OUT/cache}; mkdir -p "$CACHE" "$AB_OUT/teach_out"
cd "$H/../../approach_b_final"
[ -f "$P.SEAL.json" ] || python3 benchmark.py seal "$P" --public "$PUB"
python3 benchmark.py validate --public "$PUB" --predictions "$P"
python3 benchmark.py queries --predictions "$P" --private "$PRIV" --cache "$CACHE" --out "${P%.jsonl}_jobs"
if [ -s "${P%.jsonl}_jobs_$D.jsonl" ]; then
  V3OUT=$AB_OUT/teach_out nice -n 15 "$L/env$D/bin/python" benchmark.py teach "$D" "${P%.jsonl}_jobs_$D.jsonl" "$CACHE" "$W" "$C0"
fi
python3 benchmark.py evaluate --public "$PUB" --predictions "$P" --private "$PRIV" --cache "$CACHE" --out "${P%.jsonl}_results.jsonl"
