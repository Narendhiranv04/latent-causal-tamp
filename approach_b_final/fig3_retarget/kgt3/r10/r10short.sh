#!/bin/bash
# R10.9 short-horizon predictions on gvlab2 (public rows only): 4 GPU lanes x 2 CPUs (36-43), one RTX 5090, resumable (r10eval skips done roots).
#   r10short.sh JOBLIST       JOBLIST lines: "ARM DOM PUBLIC_JSONL"
W=/home/projects/long-horizon/naren_workspace/r10; REL=$W/release/LEGOLAS_FINAL_v1; K=$W/code/approach_b_final/fig3_retarget/kgt3
source /home/projects/long-horizon/naren_workspace/fig3/env.sh; source /home/projects/long-horizon/naren_workspace/k3abl/env.sh
export FIG3_BUNDLE=/home/projects/long-horizon/naren_workspace/k45/inf/bundle CODE=$W/code/approach_b_final
export R7_ROOT=$W/runs R7_FREEZE_DIR=$W/runs R10_Q2=$REL/q2 K3=$W/k3 CR_RUNS=$W/cr CR_SCALERS_DIR=$REL/q2 CR_BUNDLE=$K3_BUNDLE CUDA_VISIBLE_DEVICES=0
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1
OUT=$W/k3eval/runs/predictions; L=$W/logs/short; mkdir -p $OUT $L
one() { local lane=$1 arm=$2 dom=$3 pub=$4; local c=$((36 + 2 * lane)); [ -f $W/STOP_SHORT ] && return; local t0=$(date +%s)
  ( cd $K/r10 && taskset -c $c-$((c+1)) nice -n 5 $PYG r10eval.py predict $arm $dom $pub $OUT >> $L/${arm}_${dom}_$(basename $pub .jsonl).log 2>&1 ); local rc=$?
  echo "{\"arm\": \"$arm\", \"dom\": \"$dom\", \"public\": \"$(basename $pub)\", \"rc\": $rc, \"s\": $(( $(date +%s) - t0 )), \"lane\": $lane, \"end\": \"$(date -u +%FT%TZ)\"}" >> $L/jobs.jsonl; }
export -f one; export W L OUT K PYG
lane() { local i=$1; while true; do
    line=$(flock $L/.lock bash -c "head -1 $L/queue; sed -i 1d $L/queue"); [ -z "$line" ] && break; one $i $line; done; }
cp $1 $L/queue
lane 0 & lane 1 & lane 2 & lane 3 & wait
echo "R10SHORT_DONE $(date -u +%FT%TZ)" >> $L/jobs.jsonl
