#!/bin/bash
# V3.2 exhaustive inference on girish-laptop GPU (env ~/abf_v31/env torch 2.10 cu128; frozen root ~/abf_v31/root; nice 10, one pinned CPU).
# usage: girish_ex.sh DOM SPLIT MMAX TAG CPU [N]     (V32_SCORER / V32_PART honoured)
cd $HOME/abf_v32_E/code
export ABF_ROOT=$HOME/abf_v31/root V3OUT=$HOME/abf_v32_E/runs V3_TASK_STAGE=v3_3 CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
taskset -c $5 nice -n 10 $HOME/abf_v31/env/bin/python exhaustive.py run $1 $2 $3 $4 $6
