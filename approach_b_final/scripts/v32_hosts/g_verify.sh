#!/bin/bash
# V3.2 gvlab teacher leg (unchanged teachers, V3.1 code c9da937d, nice 10).  usage: g_verify.sh 2d|3d V3OUT FILES WORKERS CPU0 [CACHES]
d=$1; cd /scratch/nav/abf_v3_1/code; mkdir -p $2
export ABF_ROOT=/scratch/nav/approachb_final V3OUT=$2 MUJOCO_GL=disable OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
E=$HOME/approachb3d_v3/2d_q2_spillover/venv313/bin/python; [ $d = 3d ] && E=$HOME/approachb3d_mock/env/bin/python
nice -n 10 $E construct.py verify ${d^^} $3 $4 $5 $6 > $2/verify_$d.log 2>&1
echo "$(date +%T) G_VERIFY_${d^^}_DONE" >> $2/verify_$d.log
