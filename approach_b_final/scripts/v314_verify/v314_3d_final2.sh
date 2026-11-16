#!/bin/bash
# V3.1-4 test 3D verification, final leg 2 (laptop, 01:05): girish-laptop 3D leg moved here (girish CPU ~5x slower per worker); 14 workers on cpus 12-25.
W=$HOME/abf_v31_lapverify; L=$HOME/abf_v3_laptop; T=$HOME/abf_v314_verify; cd $W/code
export ABF_ROOT=$L/root V3OUT=$W/runs FIN3D_CODE=$L/gen/final3d_v4/code FIN3D_SRC=$L/gen/final3d_v4/src/dataset_bd_classquota_without_home_position_no_overpass MUJOCO_GL=disable OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
nice -n 10 $L/env3d/bin/python construct.py verify 3D $T/assign3d_lap2.jsonl 14 12 > $T/logs/v314verify_3d_final2.log 2>&1
echo "$(date +%T) V314_3D_FINAL2_LAP_DONE" >> $T/logs/v314verify_3d_final2.log
