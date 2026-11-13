#!/bin/bash
# V2 (continued): remaining fits -> V2 val X/Y eval -> V2 valsub searches + grid on gvlab; verification is run on gvlab2 by the laptop relay,
# which then touches runs/v2/p5_<d>/VERIFIED; tune here.
cd /scratch/nav/approachb_final/code
export CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 ABF_SNAPSHOT=/scratch/nav/approachb_final/snapshot/abf_9de85710c2a7103f
PY=../venv/bin/python; L=../logs/v2.log; SV2=../snapshot/abf_v2_7d146b53e4b92fe4
while pgrep -f "[x]y.py fit" > /dev/null; do sleep 15; done
for dom in 2D 3D; do for arm in D E G DIRECT; do for s in 0 1 2; do
  [ -e ../runs/v2/p2_$(echo $dom | tr A-Z a-z)/${arm}_s$s/curve.json ] && continue
  XY_RUNS=../runs/v2 taskset -c 0-1 nice -n 5 $PY xy.py fit $SV2 $dom $arm $s >> ../logs/v2_p2.log 2>&1
done; done; done
echo V2_RETRAIN_DONE >> $L
for dom in 2D 3D; do XY_RUNS=../runs/v2 $PY xy.py eval $SV2 $dom val >> ../logs/v2_p2.log 2>&1; XY_RUNS=../runs/v2 $PY xy.py report $dom val >> ../logs/v2_p2.log 2>&1; done
export ABF_P5DIR=../runs/v2 ABF_P2RUNS=../runs/v2
for dom in 2D 3D; do d=$(echo $dom | tr A-Z a-z)
  mkdir -p ../runs/v2/p5_$d; [ -e ../runs/v2/p5_$d/verify.jsonl ] || cp ../runs/p5_$d/verify.jsonl ../runs/v2/p5_$d/verify.jsonl
  taskset -c 5 $PY evaluate.py select $dom full 0 valsub >> $L 2>&1
  $PY evaluate.py grid $dom >> $L 2>&1
  touch ../runs/v2/p5_$d/SEARCH_READY
done
for dom in 2D 3D; do d=$(echo $dom | tr A-Z a-z)
  while [ ! -e ../runs/v2/p5_$d/VERIFIED ]; do sleep 30; done
  $PY evaluate.py tune $dom valsub >> $L 2>&1
done
echo V2_VAL_DONE >> $L
