#!/bin/bash
# V3-5 on gvlab2: V3 snapshot (V2 + V3-4 TRAIN labels), retrain D / E / G / DIRECT x 3 seeds (unchanged xy.fit, V2 hyper-parameters, GPU 0),
# held-out label-set evaluation (xy eval / report on the base validation labels).
set -e
cd $HOME/abf_v3/code
export ABF_ROOT=$HOME/abf_v3/frozen V3OUT=$HOME/abf_v3/runs CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1
G=$HOME/abf_v3/envgpu/bin/python; T=task:q2init_all-S1_M4_B4096_s0
ls -d $V3OUT/snapshot/abf_v3_* >/dev/null 2>&1 || taskset -c 47 $G onpolicy.py v3snapshot "{\"2D\": \"$T\", \"3D\": \"$T\"}"
SNAP=$(ls -d $V3OUT/snapshot/abf_v3_* | tail -1); echo SNAP $SNAP
for dom in 2D 3D; do for arm in D E G DIRECT; do for s in 0 1 2; do
  [ -f $V3OUT/v3_5/p2_${dom,,}/${arm}_s$s/curve.json ] || XY_RUNS=$V3OUT/v3_5 taskset -c 46,47 $G xy.py fit $SNAP $dom $arm $s
done; done; done
for dom in 2D 3D; do XY_RUNS=$V3OUT/v3_5 taskset -c 46,47 $G xy.py eval $SNAP $dom val; XY_RUNS=$V3OUT/v3_5 taskset -c 46,47 $G xy.py report $dom val; done
echo V3_5_FIT_DONE
