#!/bin/bash
# P1 fits, sequential on GPU 0 only; skips fits whose curve.json exists (resumable).  usage: run_p1.sh DOM
cd /scratch/nav/approachb_final/code
export CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1
for kind in cvae fm; do for s in 0 1 2; do
  [ -e ../runs/p1_$1/${kind}_s$s/curve.json ] && continue
  taskset -c 0-1 nice -n 5 ../venv/bin/python placement.py fit $1 ../data/q2_$1 $kind $s >> ../logs/p1_$1.log 2>&1
done; done
echo "P1_$1_DONE" >> ../logs/p1_$1.log
