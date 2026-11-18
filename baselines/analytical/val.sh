#!/bin/bash
# Frozen VALIDATION run of the analytical baselines (run only when instructed).  Shards are independent; distribute them across hosts.
#   val.sh run DOM I K [METHODS=em4m,mosegman,msmcts] [CONFIG=paper] [SEEDS=0] [BUDGET=300]
#        -> $AB_OUT/val/shards/DOM_I_of_K   (resumable: re-running skips finished roots)
#   val.sh finish DOM K [CUTS="60"] [WORKERS=2] [CPU0=0]
#        copy every DOM_*_of_K shard dir into $AB_OUT/val/shards first, then: merge (exactly one prediction per VAL root) ->
#        budget cuts -> seal -> independent verification (eval.sh) of every run dir -> summarize.
# Inputs: $AB_OUT/eval/public_val_DOM.jsonl (copy of ~/abf_v34/parity, existing VAL split) and private_val_DOM.jsonl (copy of
# ~/sorc_grid/eval).  2D uses $PY2D (python3), 3D uses $PY3D (MuJoCo 3.16).  One process per shard; OMP_NUM_THREADS=1, nice 10.
set -e
H=$(cd "$(dirname "$0")" && pwd); source "$H/env.sh"; cd "$H/../.."
CMD=$1; D=$2
PUB=$AB_OUT/eval/public_val_$D.jsonl; PRIV=$AB_OUT/eval/private_val_$D.jsonl
PY=$PY2D; [ "$D" = 3d ] && PY=$PY3D
if [ "$CMD" = run ]; then
  I=$3; K=$4; M=${5:-em4m,mosegman,msmcts}; C=${6:-paper}; S=${7:-0}; B=${8:-300}
  OUT=$AB_OUT/val/shards/${D}_${I}_of_${K}; mkdir -p "$OUT"
  exec nice -n 10 "$PY" -m baselines.analytical.run run --domain "$D" --public "$PUB" --out "$OUT" --methods "$M" --config "$C" \
       --seeds "$S" --budget "$B" --part "$I/$K" >> "$OUT/run.log" 2>&1
elif [ "$CMD" = finish ]; then
  K=$3; CUTS=${4:-60}; W=${5:-2}; C0=${6:-0}; MG=$AB_OUT/val/merged_$D
  python3 -m baselines.analytical.run merge --domain "$D" --public "$PUB" --out "$MG" $AB_OUT/val/shards/${D}_*_of_${K}
  for c in $CUTS; do python3 -m baselines.analytical.run cut --out "$MG" --budget "$c"; done
  for p in "$MG"/*/predictions_$D.jsonl; do
    bash "$H/eval.sh" "$D" "$p" "$PUB" "$PRIV" "$W" "$C0"
    (cd approach_b_final && python3 benchmark.py summarize --private "$PRIV" --out "$(dirname "$p")/SUMMARY_$D.json" "${p%.jsonl}_results.jsonl")
  done
  python3 -m baselines.analytical.report "$MG" "$D"
else
  echo "usage: val.sh run DOM I K [...] | val.sh finish DOM K [...]"; exit 2
fi
