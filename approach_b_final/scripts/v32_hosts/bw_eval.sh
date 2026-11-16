#!/bin/bash
# V3.2 Phase E exhaustive VALIDATION inference for a trained scorer arm (frozen sampler s0, all 72 rules, M4/M5/M6 nested); one pinned CPU / process.
# usage: bw_eval.sh ARM SEED DOM PART CPU      (ARM = control | expanded; scorer = train/<ARM>/p2_<dom>/D_s<SEED>/model.pt)
cd $HOME/abf_v32/code
p=${4/\//of}
export ABF_ROOT=$HOME/abf_v32/root V3OUT=$HOME/abf_v32/runs V3_TASK_STAGE=v3_3 CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export V32_SCORER=$HOME/abf_v32/train/$1/p2_{dom}/D_s$2/model.pt V32_PART=$4
taskset -c $5 nice -n 10 $HOME/approachb_3d_learning/venv/bin/python exhaustive.py run $3 val 6 ${1}_s$2_M6_val_p$p > $HOME/abf_v32/logs_eval_${1}_s$2_$3_p$p.log 2>&1
echo "$(date +%T) BW_EVAL_${1}_s$2_$3_p${p}_DONE" >> $HOME/abf_v32/logs_eval_${1}_s$2_$3_p$p.log
