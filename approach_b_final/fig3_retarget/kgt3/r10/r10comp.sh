#!/bin/bash
# R10.10 composition on BENCH_COMP_3D (gvlab2).  r10comp.sh plan RUN | phys RUN W CPUSET
#   plan: public-only planner (r6.py pop r10comp, R10_PUBLIC only; private index NOT exported), 4 shards x 2 dedicated CPUs (36-43), exclusive GPU,
#         then merge + seal plans, then (evaluator) jobs with the private index.   phys: unchanged physical3d.py X_CHUNKED + endpoint Y + replay.
W=/home/projects/long-horizon/naren_workspace/r10; K=$W/code/approach_b_final/fig3_retarget/kgt3
source /home/projects/long-horizon/naren_workspace/fig3/env.sh; export CODE=$W/code/approach_b_final OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=0
RUN=$2; source $W/comp/configs/$RUN.env; export R6_OUT=$W/comp/$RUN R10_PUBLIC=$W/comp/PUBLIC_bench_comp_3d.jsonl; mkdir -p $R6_OUT; cd $K
case $1 in
plan)
  [ -f $R6_OUT/plans_r10comp.jsonl.SEAL ] && { echo "already sealed: $RUN"; exit 0; }
  echo "{\"run\": \"$RUN\", \"start\": \"$(date -u +%FT%TZ)\", \"load\": \"$(cut -d' ' -f1-3 /proc/loadavg)\"}" >> $W/comp/timing_log.jsonl
  for i in 0 1 2 3; do c=$((36+2*i)); R6_SHARD=$i/4 taskset -c $c-$((c+1)) $PYG r6.py plan r10comp $W/comp/configs/$RUN.json > $R6_OUT/plan_$i.log 2>&1 & done; wait
  $PYG r6.py merge r10comp 4 || exit 1
  echo "{\"run\": \"$RUN\", \"end\": \"$(date -u +%FT%TZ)\", \"load\": \"$(cut -d' ' -f1-3 /proc/loadavg)\"}" >> $W/comp/timing_log.jsonl
  AR=/home/projects/long-horizon/naren_workspace/fig3/final/r8c:/home/projects/long-horizon/naren_workspace/fig3/final/r8c_ctrl; for d in $W/comp/*/; do [ "$d" != "$R6_OUT/" ] && [ -f $d/phys_r10comp.jsonl ] && AR=$AR:${d%/}; done
  R10_ARCHIVE_DIRS=$AR R10_PRIVATE=$W/comp/PRIVATE_bench_comp_3d.jsonl $PY3D r6.py jobs r10comp 5000 ;;
phys)
  (cd .. && taskset -c $4 nice -n 10 $PY3D physical3d.py work $R6_OUT/jobs_r10comp.json $R6_OUT/phys_r10comp.jsonl $3 4 5000 150.0 > $R6_OUT/phys.log 2>&1) ;;
analyze)
  AR=/home/projects/long-horizon/naren_workspace/fig3/final/r8c:/home/projects/long-horizon/naren_workspace/fig3/final/r8c_ctrl; for d in $W/comp/*/; do [ -f $d/phys_r10comp.jsonl ] && AR=$AR:${d%/}; done
  R10_ARCHIVE_DIRS=$AR R10_PRIVATE=$W/comp/PRIVATE_bench_comp_3d.jsonl $PY3D r6.py analyze r10comp ;;
esac
