#!/bin/bash
# V3.3 exhaustive scoring on girish (GPU shared).  usage: girish_ex.sh SAMPLER_STAGE SAMPLER_KIND SSEED DSEED DOM PART CPU MMAX TAG [N]
cd $HOME/abf_v33/code; p=${6/\//of}
export ABF_ROOT=$HOME/abf_v31/root V3OUT=$HOME/abf_v33/runs CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 V32_PART=$6 \
  V3_TASK_STAGE=$1 V33_SAMPLER=$2 V33_SAMPLER_SEED=$3 V32_SCORER=$HOME/abf_v32_E/train/expanded/p2_{dom}/D_s$4/model.pt
taskset -c $7 nice -n 10 $HOME/abf_v31/env/bin/python exhaustive.py run $5 val $8 ${9}_p$p ${10} >> $HOME/abf_v33/logs/ex_${9}_$5_p$p.log 2>&1
echo "$(date +%T) EX_DONE" >> $HOME/abf_v33/logs/ex_${9}_$5_p$p.log
