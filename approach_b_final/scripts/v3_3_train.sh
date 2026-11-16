#!/bin/bash
# V3-3 task-conditioned cVAE variants (GPU 0, strictly after the V3-2 sweep: one GPU job at a time).
cd $HOME/abf_v3/code
export ABF_ROOT=$HOME/abf_v3/frozen V3OUT=$HOME/abf_v3/runs CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1
until grep -qE 'V3_2_SWEEP_DONE|Traceback' $HOME/abf_v3/logs/v3_2_sweep.log; do sleep 30; done
for d in 2d 3d; do for v in scratch_one scratch_all q2init_one q2init_all combined_one goalablated_one; do for s in 0 1 2; do
  [ -f $V3OUT/v3_3/$d/${v}_s$s/curve.json ] || taskset -c 47 $HOME/abf_v3/envgpu/bin/python placement.py fit_task $d $v $s
done; done; done
echo V3_3_TRAIN_DONE
