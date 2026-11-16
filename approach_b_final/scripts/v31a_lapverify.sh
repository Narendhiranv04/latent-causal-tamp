#!/bin/bash
# V3.1-A physical verification moved from gvlab (CPU contention) to the laptop (user-authorised 2026-11-16).  Resumes from the gvlab cache
# (copied verify_<d>.jsonl; finished roots are skipped), same slim selection files, same unchanged teachers (laptop copies parity-checked in V3-6).
W=$HOME/abf_v31_lapverify; L=$HOME/abf_v3_laptop; cd $W/code
export ABF_ROOT=$L/root V3OUT=$W/runs FIN3D_CODE=$L/gen/final3d_v4/code FIN3D_SRC=$L/gen/final3d_v4/src/dataset_bd_classquota_without_home_position_no_overpass MUJOCO_GL=disable OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
for d in 2d 3d; do D=${d^^}; [ $d = 2d ] && { WK=12; C0=0; } || { WK=10; C0=12; }
  CI=$(ls $W/ci/*_$d*.jsonl $W/ci/*${d}_verify.jsonl 2>/dev/null | sort -u | paste -sd,)
  nice -n 10 $L/env${d:0:1}d/bin/python construct.py verify $D $(ls $W/runs/slim_v31a/$d/*.jsonl | paste -sd,) $WK $C0 $CI > $W/logs/v31a_lapverify_$d.log 2>&1 &
done
wait; echo "$(date +%T) V31A_LAPVERIFY_DONE" >> $W/logs/v31a_lapverify_2d.log
