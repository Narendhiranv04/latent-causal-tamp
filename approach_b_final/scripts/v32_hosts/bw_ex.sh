#!/bin/bash
# V3.2 Blackwell exhaustive inference (frozen sampler s0; scorer from $V32_SCORER or frozen V3 D s0); GPU 0, pinned CPUs, nice 10.
# usage: bw_ex.sh DOM SPLIT MMAX TAG CPU [N]
cd $HOME/abf_v32/code
export ABF_ROOT=$HOME/abf_v32/root V3OUT=${V3OUT:-$HOME/abf_v32/runs} V3_TASK_STAGE=v3_3 CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
taskset -c $5 nice -n 10 $HOME/approachb_3d_learning/venv/bin/python exhaustive.py run $1 $2 $3 $4 $6
