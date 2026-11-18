#!/bin/bash
# V3.4 batch A frozen inference (laptop RTX 5060), then validate + seal.  No teacher call before the seals exist.
set -e; A=$HOME/abf_v34/batchA; B=$HOME/abf_v34/approach_b_bundle; cd $HOME/Desktop/boltzmann_lfd/.claude/worktrees/approach-b-v3-4-final-benchmark/approach_b_final
export ABF_ROOT=$HOME/abf_v3_laptop/root PYTHONWARNINGS=ignore OMP_NUM_THREADS=2
log(){ echo "$(date -u +%FT%TZ) $*" >> $A/predict.log; }
log start
python3 benchmark.py predict --bundle $B --input $A/public_3d.jsonl --output $A/pred_3d.jsonl --device cuda --threads 2 >> $A/predict.log 2>&1 &
for k in 0 1 2; do python3 benchmark.py predict --bundle $B --input $A/public_2d.jsonl --output $A/pred_2d.part$k.jsonl --device cuda --part $k/3 --threads 2 >> $A/predict.log 2>&1 & done
wait; cat $A/pred_2d.part*.jsonl > $A/pred_2d.jsonl
for d in 2d 3d; do python3 benchmark.py validate --public $A/public_$d.jsonl --predictions $A/pred_$d.jsonl >> $A/predict.log 2>&1; python3 benchmark.py seal $A/pred_$d.jsonl --public $A/public_$d.jsonl >> $A/predict.log 2>&1; done
log PREDICT_SEALED
