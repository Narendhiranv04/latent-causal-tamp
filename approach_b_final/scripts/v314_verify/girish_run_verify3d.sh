#!/bin/bash
# girish-laptop 3D verify leg: exact laptop 3D teacher env (py3.13.11, mujoco/numpy as laptop env3d), same code c9da937d, same final3d_v4 generator.
# usage: W=.. C0=.. run_verify3d.sh V3OUT SLIM_FILES CACHES LOG
H=$HOME/abf_v314v; cd $H/code
export ABF_ROOT=$H/root V3OUT=$1 FIN3D_CODE=$H/gen/final3d_v4/code FIN3D_SRC=$H/gen/final3d_v4/src/dataset_bd_classquota_without_home_position_no_overpass MUJOCO_GL=disable OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
mkdir -p $1; ln -sfn $H/runs/store $1/store
nice -n 10 $H/env3d/bin/python construct.py verify 3D $2 ${W:-4} ${C0:-0} $3 > $4 2>&1
echo "$(date +%T) GIRISH_VERIFY3D_DONE" >> $4
