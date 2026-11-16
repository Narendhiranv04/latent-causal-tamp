#!/bin/bash
# V3.1-4 test physical verification, laptop half (V3_PART hash shard disjoint from gvlab; user-authorised 2026-11-16 "use gvlab CPUs and my laptop CPU").
# Same unchanged teachers (laptop copies parity-checked in V3-6), same code c9da937d; new labels append to ~/abf_v31_lapverify/runs/verify_<d>.jsonl.
W=$HOME/abf_v31_lapverify; L=$HOME/abf_v3_laptop; T=$HOME/abf_v314_verify; cd $W/code
export ABF_ROOT=$L/root V3OUT=$W/runs FIN3D_CODE=$L/gen/final3d_v4/code FIN3D_SRC=$L/gen/final3d_v4/src/dataset_bd_classquota_without_home_position_no_overpass MUJOCO_GL=disable OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
for d in 2d 3d; do D=${d^^}; [ $d = 2d ] && { WK=12; C0=0; P=0,1,2,3,4,5,6,7,8,9,10/20; } || { WK=11; C0=12; P=0,1,2,3,4,5,6,7,8,9,10,11/20; }
  V3_PART=$P nice -n 10 $L/env${d:0:1}d/bin/python construct.py verify $D $(ls $T/runs/slim_test/$d/*.jsonl | paste -sd,) $WK $C0 $(cat $T/caches_$d.txt) > $T/logs/v314verify_$d.log 2>&1 &
done
wait; echo "$(date +%T) V314_VERIFY_LAP_DONE" >> $T/logs/v314verify_2d.log
