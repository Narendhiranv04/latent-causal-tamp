#!/bin/bash
# V3.2 matched D training on Blackwell (xy.fit arm D; fixed 60 epochs, best-VAL-NLL checkpoint; GPU 0; one CPU pinned, nice 10).
# usage: bw_fit.sh SNAPSHOT_DIR DOM SEED OUT_RUNS CPU
cd $HOME/abf_v32/code
export ABF_ROOT=$HOME/abf_v32/root XY_RUNS=$4 XY_PATIENCE=60 XY_EPOCHS=60 CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p $4
taskset -c $5 nice -n 10 $HOME/approachb_3d_learning/venv/bin/python xy.py fit $1 $2 D $3 >> $4/fit.log 2>&1
