#!/bin/bash
# V3.2 laptop teacher leg (unchanged teachers, laptop envs parity-checked V3-6/V3.1-4; code = V3.1 c9da937d construct/evaluate).
# usage: lap_verify.sh 2d|3d V3OUT FILES WORKERS CPU0 [CACHES]
d=$1; W=$HOME/abf_v31_lapverify; L=$HOME/abf_v3_laptop; cd $W/code; mkdir -p $2
export ABF_ROOT=$L/root V3OUT=$2 FIN3D_CODE=$L/gen/final3d_v4/code FIN3D_SRC=$L/gen/final3d_v4/src/dataset_bd_classquota_without_home_position_no_overpass MUJOCO_GL=disable OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
nice -n 10 $L/env${d:0:1}d/bin/python construct.py verify ${d^^} $3 $4 $5 $6 > $2/verify_$d.log 2>&1
echo "$(date +%T) LAP_VERIFY_${d^^}_DONE" >> $2/verify_$d.log
