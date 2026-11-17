#!/bin/bash
# V3.3 girish teacher leg (CPU; exact parity-checked envs ~/abf_v314v, code c9da937d).  usage: girish_verify.sh 2d|3d V3OUT FILES W CPU0 [CACHES...]
d=$1; H=$HOME/abf_v314v; cd $H/code; mkdir -p $2
export ABF_ROOT=$H/root V3OUT=$2 FIN3D_CODE=$H/gen/final3d_v4/code FIN3D_SRC=$H/gen/final3d_v4/src/dataset_bd_classquota_without_home_position_no_overpass MUJOCO_GL=disable OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
ln -sfn $H/runs/teacher2d_witnesses $2/teacher2d_witnesses; ln -sfn $H/runs/store $2/store
nice -n 10 $H/env${d:0:1}d/bin/python construct.py verify ${d^^} $3 $4 $5 "${@:6}" > $2/verify_$d.log 2>&1
echo "$(date +%T) GIRISH_VERIFY_${d^^}_DONE" >> $2/verify_$d.log
