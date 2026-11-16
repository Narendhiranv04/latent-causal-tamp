#!/bin/bash
# V3-2 / V3-3 physical top-1 arms on full VALIDATION (seed 0, frozen V2 scorer + frozen V2 rule), GPU 0, one job at a time.
cd $HOME/abf_v3/code
export ABF_ROOT=$HOME/abf_v3/frozen V3OUT=$HOME/abf_v3/runs CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1
G="taskset -c 47 $HOME/abf_v3/envgpu/bin/python construct.py run"
for D in 2D 3D; do
  $G $D val v2frozen 0 4 4096                                   # Q2 cVAE S0 M4 (= V3-1 arm, all of val)
  $G $D val v2frozen 0 8 4096
  $G $D val v2frozen 0 16 4096
  $G $D val v2frozen 0 4 4096 S1 cvae
  $G $D val v2frozen 0 4 4096 S2 uniform
  $G $D val v2frozen 0 4 4096 S1 task:q2init_all
  $G $D val v2frozen 0 4 4096 S1 task:goalablated_one
  $G $D val v2frozen 0 8 4096 S1 task:q2init_all
done
echo V3_23_RUNS_DONE
