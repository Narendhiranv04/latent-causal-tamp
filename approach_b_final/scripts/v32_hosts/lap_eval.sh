#!/bin/bash
# V3.2 Phase E exhaustive VAL scoring on the laptop GPU (V3.2-A reference env); loops seeds for one root shard.  usage: lap_eval.sh ARM DOM PART CPU "SEEDS"
cd /home/naren/Desktop/boltzmann_lfd/.claude/worktrees/approach-b-v3-2-training/approach_b_final; p=${3/\//of}
export ABF_ROOT=$HOME/abf_v3_2_audit/root V3OUT=$HOME/abf_v32/lap_eval_runs V3_TASK_STAGE=v3_3 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 V32_PART=$3
for s in $5; do
  V32_SCORER=$HOME/abf_v32/train/$1/p2_{dom}/D_s$s/model.pt taskset -c $4 nice -n 10 $HOME/miniconda3/envs/rkit-rpx-sm120/bin/python exhaustive.py run $2 val 6 ${1}_s${s}_M6_val_p$p >> $HOME/abf_v32/lap_eval_${1}_$2_p$p.log 2>&1
done
echo "$(date +%T) LAP_EVAL_${1}_${2}_p${p}_DONE" >> $HOME/abf_v32/lap_eval_${1}_$2_p$p.log
