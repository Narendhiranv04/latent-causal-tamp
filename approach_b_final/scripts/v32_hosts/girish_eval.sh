#!/bin/bash
# V3.2 Phase E exhaustive VAL scoring of a trained arm on girish GPU; loops seeds for one root shard.  usage: girish_eval.sh ARM DOM PART CPU "SEEDS"
cd $HOME/abf_v32_E/code; p=${3/\//of}
export ABF_ROOT=$HOME/abf_v31/root V3OUT=$HOME/abf_v32_E/runs V3_TASK_STAGE=v3_3 CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 V32_PART=$3
for s in $5; do
  V32_SCORER=$HOME/abf_v32_E/train/$1/p2_{dom}/D_s$s/model.pt taskset -c $4 nice -n 10 $HOME/abf_v31/env/bin/python exhaustive.py run $2 val 6 ${1}_s${s}_M6_val_p$p >> $HOME/abf_v32_E/eval_${1}_$2_p$p.log 2>&1
done
echo "$(date +%T) GIRISH_EVAL_${1}_${2}_p${p}_DONE" >> $HOME/abf_v32_E/eval_${1}_$2_p$p.log
