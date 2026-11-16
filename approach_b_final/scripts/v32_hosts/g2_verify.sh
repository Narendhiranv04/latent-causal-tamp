#!/bin/bash
# V3.2 gvlab2 (cstar) teacher leg: V2 teacher envs (env2d / env3d), frozen root $HOME/abf_v3/frozen, V3.2 branch code; nice 10, pinned CPUs.
# usage: g2_verify.sh 2d|3d V3OUT FILES WORKERS CPU0 [CACHES]
d=$1; cd $HOME/abf_v32/code; mkdir -p $2
export ABF_ROOT=$HOME/abf_v3/frozen V3OUT=$2 MUJOCO_GL=disable OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
nice -n 10 $HOME/abf_v2/env${d:0:1}d/bin/python construct.py verify ${d^^} $3 $4 $5 $6 > $2/verify_$d.log 2>&1
echo "$(date +%T) G2_VERIFY_${d^^}_DONE" >> $2/verify_$d.log
