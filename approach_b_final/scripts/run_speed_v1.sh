#!/bin/bash
# V1 rebalance (user: speed up): after V1 2D is done, stop the old driver and run V1 3D unchanged except 9 verification workers (CPUs 15-23);
# raise the V2 allocation to 9 workers (CPUs 6-14).
cd /scratch/nav/approachb_final/code
export CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 ABF_SNAPSHOT=/scratch/nav/approachb_final/snapshot/abf_9de85710c2a7103f
PY=../venv/bin/python; P3D=$HOME/approachb3d_mock/env/bin/python; L=../logs/p5.log
while ! grep -q "2D P5_DONE" $L; do sleep 20; done
for p in $(pgrep -f "[r]un_p5.sh"); do kill $p; done; sleep 2
for p in $(pgrep -f "[e]valuate.py select 3D"); do kill $p; done
echo "{\"workers\": 9, \"lo\": 6}" > ../runs/v2/ALLOC
echo "$(date -u +%T) 3D valsub search (rebalanced driver, 9 verify workers)" >> $L
taskset -c 2 $PY evaluate.py select 3D full 0 valsub >> $L 2>&1
$PY evaluate.py grid 3D >> $L 2>&1
echo "$(date -u +%T) 3D valsub verify" >> $L
$P3D evaluate.py verify 3D valsub ../runs/p5_3d/grid.json 9 >> $L 2>&1
$PY evaluate.py tune 3D valsub >> $L 2>&1
echo "$(date -u +%T) 3D test searches" >> $L
for s in 0 1 2; do taskset -c $((2+s)) $PY evaluate.py select 3D full $s test >> $L 2>&1 & done; wait
echo "$(date -u +%T) 3D test verify" >> $L
$P3D evaluate.py verify 3D test ../runs/p5_3d/rule.json 9 >> $L 2>&1
$PY evaluate.py table 3D test >> $L 2>&1
echo "$(date -u +%T) 3D P5_DONE" >> $L
echo ALL_P5_DONE >> $L
