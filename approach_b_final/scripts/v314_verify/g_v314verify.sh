#!/bin/bash
# V3.1-4 test physical verification, gvlab half (V3_PART hash shard of roots, disjoint from the laptop half; same teachers/code c9da937d).
# Unverified selections never count; nice 10, 16 of 24 cores (DISCO + others keep the rest).
cd /scratch/nav/abf_v3_1/code
export ABF_ROOT=/scratch/nav/approachb_final V3OUT=/scratch/nav/abf_v3_1/runs MUJOCO_GL=disable OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
C=/scratch/nav/abf_v3/caches; A=$ABF_ROOT/runs
for d in 2d 3d; do
  D=${d^^}; E=$HOME/approachb3d_v3/2d_q2_spillover/venv313/bin/python; W=9; C0=0; P=11,12,13,14,15,16,17,18,19/20
  [ $d = 3d ] && { E=$HOME/approachb3d_mock/env/bin/python; W=7; C0=9; P=12,13,14,15,16,17,18,19/20; }
  CI=$A/v2/p5_$d/verify.jsonl,$A/p5_$d/verify.jsonl,$C/final_g2_verify_$d.jsonl,$C/final_lap_verify_$d.jsonl,/scratch/nav/abf_v3/runs/verify_$d.jsonl,$C/g2_verify_$d.jsonl,$C/laptop_verify_$d.jsonl,$C/lap_extra/g2_verify_$d.jsonl,$C/lap_extra/ref_verify_$d.jsonl,$C/lap_extra/v2_verify_$d.jsonl
  V3_PART=$P nice -n 10 $E construct.py verify $D $(ls $V3OUT/slim_v314_test/$d/*.jsonl | paste -sd,) $W $C0 $CI > /scratch/nav/abf_v3_1/logs/v314verify_$d.log 2>&1 &
done
wait; echo "$(date +%T) V314_VERIFY_GVLAB_DONE" >> /scratch/nav/abf_v3_1/logs/v314verify_2d.log
