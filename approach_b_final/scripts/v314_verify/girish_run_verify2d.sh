#!/bin/bash
# girish-laptop 2D verify leg (user-authorised CPU use, max 4 workers): exact laptop teacher env (py3.13.11/numpy 2.4.6/scipy 1.18.1), same code c9da937d.
# usage: run_verify.sh V3OUT SLIM_FILES CACHES LOG
H=$HOME/abf_v314v; cd $H/code
export ABF_ROOT=$H/root V3OUT=$1 MUJOCO_GL=disable OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
mkdir -p $1; ln -sfn $H/runs/teacher2d_witnesses $1/teacher2d_witnesses; ln -sfn $H/runs/store $1/store
nice -n 10 $H/env2d/bin/python construct.py verify 2D $2 ${W:-4} 0 $3 > $4 2>&1
echo "$(date +%T) GIRISH_VERIFY_DONE" >> $4
