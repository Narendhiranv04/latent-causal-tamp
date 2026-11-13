#!/bin/bash
# Sequential GPU-0 queue (one job at a time): P1 2D (already running) -> P1 3D -> P2 2D/3D (D E G DIRECT x seeds 0-2) -> P3 2D/3D (seeds 0-2).
# Resumable: every step is skipped when its curve.json exists.
cd /scratch/nav/approachb_final/code
export CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1
SNAP=../snapshot/abf_9de85710c2a7103f
while pgrep -f "[r]un_p1.sh 2d" >/dev/null; do sleep 30; done
./run_p1.sh 3d
for dom in 2D 3D; do for arm in D E G DIRECT; do for s in 0 1 2; do
  d=../runs/p2_$(echo $dom | tr A-Z a-z)/${arm}_s$s; [ -e $d/curve.json ] && continue
  taskset -c 0-1 nice -n 5 ../venv/bin/python xy.py fit $SNAP $dom $arm $s >> ../logs/p2.log 2>&1
done; done; done
echo P2_DONE >> ../logs/p2.log
for dom in 2D 3D; do for s in 0 1 2; do
  d=../runs/p3_$(echo $dom | tr A-Z a-z)/cost_s$s; [ -e $d/curve.json ] && continue
  taskset -c 0-1 nice -n 5 ../venv/bin/python cost.py fit $dom $SNAP $s >> ../logs/p3.log 2>&1
done; done
echo QUEUE_DONE >> ../logs/p3.log
