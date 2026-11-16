#!/bin/bash
# V3.1-4 test 3D verification, final leg (gvlab): explicit root list from the pooled 3-host rebalance (00:41); 7 workers (2D leg still on 0-8), nice 10.
cd /scratch/nav/abf_v3_1/code
export ABF_ROOT=/scratch/nav/approachb_final V3OUT=/scratch/nav/abf_v3_1/runs MUJOCO_GL=disable OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
nice -n 10 $HOME/approachb3d_mock/env/bin/python construct.py verify 3D /scratch/nav/abf_v3_1/runs/assign3d_gv.jsonl 7 9 > /scratch/nav/abf_v3_1/logs/v314verify_3d_final.log 2>&1
echo "$(date +%T) V314_3D_FINAL_GV_DONE" >> /scratch/nav/abf_v3_1/logs/v314verify_3d_final.log
