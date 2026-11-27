#!/bin/bash
# R7 clean-training queue on Blackwell (shared host): 4 GPU lanes x 2 CPUs (16-23), nice 10, STOP file drains between jobs.
W=~/legolas_r7; cd $W/code/approach_b_final/fig3_retarget/kgt3
export ABF_ROOT=$W/abf V3OUT=$W/runs XY_RUNS=$W/runs/xy R7_OUT=$W/runs R7_PACK_DIR=$W/pack R2_NW=$W/nw CUDA_VISIBLE_DEVICES=0
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1
PY=~/approachb_3d_learning/venv/bin/python; L=$W/logs; mkdir -p $L
job() { local cpus=$1; shift; [ -f $W/STOP ] && return; local t0=$(date +%s)
  taskset -c $cpus nice -n 10 $PY r7.py "$@" >> $L/$(echo "$@" | tr ' ' _).log 2>&1; echo "{\"job\": \"$*\", \"rc\": $?, \"s\": $(( $(date +%s) - t0 )), \"end\": \"$(date -u +%FT%TZ)\"}" >> $L/jobs.jsonl; }
waitb() { until [ -f $XY_RUNS/p2_$1/D_s$2/curve.json ] || [ -f $W/STOP ]; do sleep 30; done; }
lane1() { for d in 3d 2d; do for s in 0 1 2; do job 16-17 stageB $d $s; done; done; }
lane2() { for s in 0 1 2; do job 18-19 stageA 3d $s; done; for s in 0 1; do job 18-19 stageA 2d $s; done; }
lane3() { job 20-21 stageA 2d 2; for d in 3d 2d; do for s in 0 1 2; do waitb $d $s; for c in ORDINV UNCOUPLED DIRECT; do job 20-21 xfit $d G 1 $s $c; done; done; done; }
lane4() { for d in 3d 2d; do for s in 0 1 2; do waitb $d $s; for r in G M A; do for x in 1 0; do job 22-23 xfit $d $r $x $s; done; done; done; done; }
lane1 & lane2 & lane3 & lane4 & wait; echo "R7Q_DONE $(date -u +%FT%TZ)" >> $L/jobs.jsonl
