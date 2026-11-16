#!/bin/bash
# gvlab2 share (V3_PART=3/4) of the V3-2/V3-3 validation verification; starts after V3-1b has finished (<= 6 teacher workers on gvlab2).
cd $HOME/abf_v3/code
export ABF_ROOT=$HOME/abf_v3/frozen V3OUT=$HOME/abf_v3/runs PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 V3_PART=3/4
until grep -qE 'V3_1B_DONE|Traceback' $HOME/abf_v3/logs/v3_1b.log; do sleep 30; done
S=$V3OUT/slim
nice -n 10 $HOME/abf_v2/env2d/bin/python construct.py verify 2D $(ls $S/2d/*.jsonl | paste -sd,) 4 40 $ABF_ROOT/runs/v2/p5_2d/verify.jsonl &
nice -n 10 $HOME/abf_v2/env3d/bin/python construct.py verify 3D $(ls $S/3d/*.jsonl | paste -sd,) 3 44 $ABF_ROOT/runs/v2/p5_3d/verify.jsonl &
wait
echo V3_23_G2_VERIFY_DONE
