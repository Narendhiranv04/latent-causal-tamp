#!/bin/bash
# V1 3D after the padding fix (3D NONE scenes > 8 objects crashed the sampler features): resumable searches, grid verification (cache reused),
# re-tune WITH the NONE cohort, test (3 seeds), table.  9 verification workers on CPUs 15-23.
cd /scratch/nav/approachb_final/code
export CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 ABF_SNAPSHOT=/scratch/nav/approachb_final/snapshot/abf_9de85710c2a7103f
PY=../venv/bin/python; P3D=$HOME/approachb3d_mock/env/bin/python; L=../logs/p5.log
echo "$(date -u +%T) 3D valsub search (padding fix)" >> $L
taskset -c 2 $PY evaluate.py select 3D full 0 valsub >> $L 2>&1
echo "$(date -u +%T) 3D valsub verify (padding fix)" >> $L
$P3D evaluate.py verify 3D valsub ../runs/p5_3d/grid.json 9 >> $L 2>&1
$PY evaluate.py tune 3D valsub >> $L 2>&1
echo "$(date -u +%T) 3D test searches (padding fix)" >> $L
for s in 0 1 2; do taskset -c $((2+s)) $PY evaluate.py select 3D full $s test >> $L 2>&1 & done; wait
echo "$(date -u +%T) 3D test verify (padding fix)" >> $L
$P3D evaluate.py verify 3D test ../runs/p5_3d/rule.json 9 >> $L 2>&1
$PY evaluate.py table 3D test >> $L 2>&1
echo "$(date -u +%T) 3D P5_DONE" >> $L
echo ALL_P5_DONE >> $L
