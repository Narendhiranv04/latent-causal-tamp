#!/bin/bash
# V3-5b on gvlab2 (after the fits): held-out candidate comparison; valsub direct runs of the primary arm (task cVAE q2init_all S1 M4 B4096 +
# V3 D) under the frozen V2 rule (candidates stored), union of the 72 grid rules' selections -> slim file for physical verification.
set -e
cd $HOME/abf_v3/code
export ABF_ROOT=$HOME/abf_v3/frozen V3OUT=$HOME/abf_v3/runs CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1
G=$HOME/abf_v3/envgpu/bin/python
until grep -qE 'V3_5_FIT_DONE|Traceback' $HOME/abf_v3/logs/v3_5.log; do sleep 30; done
grep -q V3_5_FIT_DONE $HOME/abf_v3/logs/v3_5.log
taskset -c 46,47 $G scripts/v3_5_heldout.py
mkdir -p $V3OUT/slim_tune/2d $V3OUT/slim_tune/3d
for D in 2D 3D; do d=${D,,}
  V3_STAGE=v3_5 taskset -c 47 $G construct.py run $D valsub v3D 0 4 4096 S1 task:q2init_all
  taskset -c 47 $G construct.py gridslim "$V3OUT/v3_5/$d/v3D_task:q2init_all-S1_M4_B4096_s0_valsub.jsonl" $ABF_ROOT/runs/v2/p5_$d/grid.json $V3OUT/slim_tune/$d/grid_union.jsonl
done
echo V3_5B_DONE
