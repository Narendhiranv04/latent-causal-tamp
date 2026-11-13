#!/bin/bash
# V2 chain (user decision + speed-up): coverage -> collection -> V2 snapshot -> retrain (GPU 0) -> V2 validation only.
cd /scratch/nav/approachb_final/code
export CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 ABF_SNAPSHOT=/scratch/nav/approachb_final/snapshot/abf_9de85710c2a7103f
PY=../venv/bin/python; P2D=$HOME/approachb3d_v3/2d_q2_spillover/venv313/bin/python; P3D=$HOME/approachb3d_mock/env/bin/python; L=../logs/v2.log
$PY onpolicy.py supervise 3D:coverage >> $L 2>&1
for d in 2D 3D; do $PY onpolicy.py coverage $d >> $L 2>&1; done
echo V2_COVERAGE_DONE >> $L
$PY onpolicy.py supervise 2D:collect 3D:collect >> $L 2>&1
echo V2_COLLECT_DONE >> $L
$PY onpolicy.py snapshot ALL >> $L 2>&1
SV2=$(ls -d ../snapshot/abf_v2_* | tail -1)
for dom in 2D 3D; do for arm in D E G DIRECT; do for s in 0 1 2; do
  [ -e ../runs/v2/p2_$(echo $dom | tr A-Z a-z)/${arm}_s$s/curve.json ] && continue
  XY_RUNS=../runs/v2 taskset -c 0-1 nice -n 5 $PY xy.py fit $SV2 $dom $arm $s >> ../logs/v2_p2.log 2>&1
done; done; done
echo V2_RETRAIN_DONE >> $L
for dom in 2D 3D; do XY_RUNS=../runs/v2 $PY xy.py eval $SV2 $dom val >> ../logs/v2_p2.log 2>&1; XY_RUNS=../runs/v2 $PY xy.py report $dom val >> ../logs/v2_p2.log 2>&1; done
export ABF_P5DIR=../runs/v2 ABF_P2RUNS=../runs/v2
for dom in 2D 3D; do d=$(echo $dom | tr A-Z a-z); TP=$([ $dom = 2D ] && echo $P2D || echo $P3D)
  mkdir -p ../runs/v2/p5_$d; [ -e ../runs/v2/p5_$d/verify.jsonl ] || cp ../runs/p5_$d/verify.jsonl ../runs/v2/p5_$d/verify.jsonl 2>/dev/null
  taskset -c 5 $PY evaluate.py select $dom full 0 valsub >> $L 2>&1
  $PY evaluate.py grid $dom >> $L 2>&1
  W=$(python3 -c "import json;print(json.load(open(\"../runs/v2/ALLOC\"))[\"workers\"])")
  $TP evaluate.py verify $dom valsub ../runs/v2/p5_$d/grid.json $W >> $L 2>&1
  $PY evaluate.py tune $dom valsub >> $L 2>&1
done
echo V2_VAL_DONE >> $L
