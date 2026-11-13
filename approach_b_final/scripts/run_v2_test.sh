#!/bin/bash
# V2 frozen test (rules tuned on validation only): searches on gvlab GPU 0 (6 processes), 3D verification here (14 workers, CPUs 6-19),
# 2D verification on gvlab2 via the laptop relay (marker runs/v2/p5_2d/TEST_VERIFIED), tables.
cd /scratch/nav/approachb_final/code
export CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 ABF_SNAPSHOT=/scratch/nav/approachb_final/snapshot/abf_9de85710c2a7103f
export ABF_P5DIR=/scratch/nav/approachb_final/runs/v2 ABF_P2RUNS=/scratch/nav/approachb_final/runs/v2
PY=../venv/bin/python; P3D=$HOME/approachb3d_mock/env/bin/python; L=../logs/v2_test.log
J=""; for a in full uncoupled orderinv direct analytic flow oneshot; do for s in 0 1 2; do J="$J 2D:$a:$s"; done; done
for s in 0 1 2; do J="$J 3D:full:$s"; done
i=0
for j in $J; do IFS=: read D A S <<< "$j"
  taskset -c $((2 + i % 6)) $PY evaluate.py select $D $A $S test >> $L 2>&1 &
  i=$((i+1)); [ $((i % 6)) -eq 0 ] && wait
done; wait
touch ../runs/v2/p5_2d/TEST_SEARCH_READY
echo "$(date +%T) V2 test searches done" >> $L
$P3D evaluate.py verify 3D test ../runs/v2/p5_3d/rule.json 14 >> $L 2>&1
$PY evaluate.py table 3D test >> $L 2>&1
echo "$(date +%T) V2 3D table done" >> $L
while [ ! -e ../runs/v2/p5_2d/TEST_VERIFIED ]; do sleep 30; done
$PY evaluate.py table 2D test >> $L 2>&1
echo V2_TEST_DONE >> $L
