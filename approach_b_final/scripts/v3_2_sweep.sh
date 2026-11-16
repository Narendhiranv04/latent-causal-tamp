#!/bin/bash
# V3-2 teacher-free proposal sweep on all VALIDATION roots (GPU 0, after the V3-1b GPU phase has finished: one GPU job at a time).
cd $HOME/abf_v3/code
export ABF_ROOT=$HOME/abf_v3/frozen V3OUT=$HOME/abf_v3/runs CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1
until grep -q '"queries"' $HOME/abf_v3/logs/v3_1b.log; do sleep 30; done
for d in 2D 3D; do taskset -c 47 $HOME/abf_v3/envgpu/bin/python construct.py sweep $d val; done
echo V3_2_SWEEP_DONE
