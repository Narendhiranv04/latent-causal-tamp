#!/bin/bash
# V3-1b on gvlab2: the same four arms on VALREST (validation roots outside valsub, never used to tune any stopping rule), seed 0.
set -e
cd $HOME/abf_v3/code
export ABF_ROOT=$HOME/abf_v3/frozen V3OUT=$HOME/abf_v3/runs ABF_SNAPSHOT=$HOME/abf_v3/frozen/snapshot/abf_9de85710c2a7103f
export CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1
G=$HOME/abf_v3/envgpu/bin/python; E2=$HOME/abf_v2/env2d/bin/python; E3=$HOME/abf_v2/env3d/bin/python
W=${W:-6}; CPU0=${CPU0:-40}; O=$V3OUT/v3_1
for d in 2d 3d; do
  D=${d^^}
  for arm in full oneshot; do ABF_P5DIR=$O/v2baselines ABF_P2RUNS=$ABF_ROOT/runs/v2 taskset -c $CPU0 $G evaluate.py select $D $arm 0 valrest; done
  taskset -c $CPU0 $G construct.py legacy $O/v2baselines/p5_$d/search/full_s0_valrest.jsonl $ABF_ROOT/runs/v2/p5_$d/rule.json $O/$d/v2_iterative_s0_valrest.jsonl v2_iterative
  taskset -c $CPU0 $G construct.py legacy $O/v2baselines/p5_$d/search/oneshot_s0_valrest.jsonl $ABF_ROOT/runs/v2/p5_$d/rule.json $O/$d/v2_oneshot_s0_valrest.jsonl v2_oneshot
  for B in 512 4096; do taskset -c $CPU0 $G construct.py run $D valrest v2frozen 0 4 $B; done
done
for d in 2d 3d; do
  D=${d^^}; E=$E2; [ $d = 3d ] && E=$E3
  F=$(ls $O/$d/*_valrest.jsonl | paste -sd,)
  nice -n 10 $E construct.py verify $D $F $W $CPU0 $ABF_ROOT/runs/v2/p5_$d/verify.jsonl
  F=$O/$d/v2_iterative_s0_valrest.jsonl,$O/$d/v2_oneshot_s0_valrest.jsonl,$O/$d/v2frozen_M4_B512_s0_valrest.jsonl,$O/$d/v2frozen_M4_B4096_s0_valrest.jsonl
  taskset -c $CPU0 $G construct.py summary $D $F $ABF_ROOT/runs/v2/p5_$d/verify.jsonl,$V3OUT/verify_$d.jsonl $O/SUMMARY_${d}_valrest.json v2_iterative > /dev/null
done
echo V3_1B_DONE
