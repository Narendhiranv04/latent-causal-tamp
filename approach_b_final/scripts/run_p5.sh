#!/bin/bash
# P5 driver (after the GPU queue): per domain, VALIDATION tuning subset -> frozen stopping rule -> TEST.  Resumable (select/verify append).
# Searches: GPU 0 inference, 3 processes in parallel on CPUs 2-4.  Verification: the unchanged teachers on 14 workers (CPUs 10-23).
cd /scratch/nav/approachb_final/code
export CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 ABF_SNAPSHOT=/scratch/nav/approachb_final/snapshot/abf_9de85710c2a7103f
PY=../venv/bin/python; P2D=$HOME/approachb3d_v3/2d_q2_spillover/venv313/bin/python; P3D=$HOME/approachb3d_mock/env/bin/python
L=../logs/p5.log
while ! grep -q QUEUE_DONE ../logs/p3.log 2>/dev/null; do sleep 30; done
for DOM in 2D 3D; do
  dom=$(echo $DOM | tr A-Z a-z); TP=$([ $DOM = 2D ] && echo $P2D || echo $P3D)
  echo "$(date -u +%T) $DOM valsub search" >> $L
  taskset -c 2 $PY evaluate.py select $DOM full 0 valsub >> $L 2>&1
  $PY evaluate.py grid $DOM >> $L 2>&1
  echo "$(date -u +%T) $DOM valsub verify" >> $L
  $TP evaluate.py verify $DOM valsub ../runs/p5_$dom/grid.json 14 >> $L 2>&1
  $PY evaluate.py tune $DOM valsub >> $L 2>&1
  echo "$(date -u +%T) $DOM test searches" >> $L
  ARMS=$([ $DOM = 2D ] && echo "full uncoupled orderinv direct analytic flow oneshot" || echo "full")
  for s in 0 1 2; do
    i=0
    for a in $ARMS; do
      taskset -c $((2 + i % 3)) $PY evaluate.py select $DOM $a $s test >> $L 2>&1 &
      i=$((i+1)); [ $((i % 3)) -eq 0 ] && wait
    done; wait
  done
  echo "$(date -u +%T) $DOM test verify" >> $L
  $TP evaluate.py verify $DOM test ../runs/p5_$dom/rule.json 14 >> $L 2>&1
  $PY evaluate.py table $DOM test >> $L 2>&1
  echo "$(date -u +%T) $DOM P5_DONE" >> $L
done
echo ALL_P5_DONE >> $L
