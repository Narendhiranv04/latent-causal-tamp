#!/bin/bash
# NOR-Grid sealed VALIDATION evaluation through the UNCHANGED benchmark harness + teachers (laptop only).
# usage: eval.sh DOM SEALED_PRED.jsonl WORKERS CPU0      (predictions must already be sealed with benchmark.py seal)
set -e; D=$1; P=$(realpath $2); W=$3; C0=$4; E=$HOME/sorc_grid/eval; L=$HOME/abf_v3_laptop
B=$(realpath $(dirname $0)/../../approach_b_final); cd $B
python3 benchmark.py queries --predictions $P --private $E/private_val_$D.jsonl --cache $E/cache --out ${P%.jsonl}_jobs
if [ -s ${P%.jsonl}_jobs_$D.jsonl ]; then
  mkdir -p $E/teach_out
  ABF_ROOT=$L/root V3OUT=$E/teach_out FIN3D_CODE=$L/gen/final3d_v4/code FIN3D_SRC=$L/gen/final3d_v4/src/dataset_bd_classquota_without_home_position_no_overpass \
  MUJOCO_GL=disable OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES= \
  nice -n 15 $L/env${D}/bin/python benchmark.py teach $D ${P%.jsonl}_jobs_$D.jsonl $E/cache $W $C0
fi
python3 benchmark.py evaluate --public $E/public_val_$D.jsonl --predictions $P --private $E/private_val_$D.jsonl --cache $E/cache --out ${P%.jsonl}_results.jsonl
