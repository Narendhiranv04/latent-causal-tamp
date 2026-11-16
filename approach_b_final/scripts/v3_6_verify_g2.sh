#!/bin/bash
# gvlab2 share (V3_PART=3/4) of the V3-6 3D test verification, as soon as the 3D test selections exist (6 workers, nice 10).
cd $HOME/abf_v3/code
export ABF_ROOT=$HOME/abf_v3/frozen V3OUT=$HOME/abf_v3/runs PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 V3_PART=3/4
until grep -q V3_6_RUNS_DONE $HOME/abf_v3/logs/v3_6_runs.log; do sleep 30; done
S=$V3OUT/slim_test/3d
nice -n 10 $HOME/abf_v2/env3d/bin/python construct.py verify 3D $(ls $S/*.jsonl | paste -sd,) 6 40 $ABF_ROOT/runs/v2/p5_3d/verify.jsonl
echo V3_6_G2_VERIFY_DONE
