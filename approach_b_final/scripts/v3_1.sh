#!/bin/bash
# V3-1 on gvlab2: direct one-shot construction vs the old V2 iterative / bounded-oneshot search, frozen V2 models + frozen V2 rule, valsub, seed 0.
# GPU 0 only (one job at a time), then physical verification of the selected repairs on CPUs $CPU0.. ($W workers, nice 10).
set -e
cd $HOME/abf_v3/code
export ABF_ROOT=$HOME/abf_v3/frozen V3OUT=$HOME/abf_v3/runs ABF_SNAPSHOT=$HOME/abf_v3/frozen/snapshot/abf_9de85710c2a7103f
export CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1
G=$HOME/abf_v3/envgpu/bin/python; E2=$HOME/abf_v2/env2d/bin/python; E3=$HOME/abf_v2/env3d/bin/python
W=${W:-6}; CPU0=${CPU0:-40}; O=$V3OUT/v3_1
for d in 2d 3d; do
  D=${d^^}
  mkdir -p $O/$d
  # old V2 searches: frozen iterative s0 (existing) + bounded oneshot s0 (re-run with the unchanged evaluate.py into a V3 directory)
  ABF_P5DIR=$O/v2baselines ABF_P2RUNS=$ABF_ROOT/runs/v2 taskset -c $CPU0 $G evaluate.py select $D oneshot 0 valsub
  taskset -c $CPU0 $G construct.py legacy $ABF_ROOT/runs/v2/p5_$d/search/full_s0_valsub.jsonl $ABF_ROOT/runs/v2/p5_$d/rule.json $O/$d/v2_iterative_s0_valsub.jsonl v2_iterative
  taskset -c $CPU0 $G construct.py legacy $O/v2baselines/p5_$d/search/oneshot_s0_valsub.jsonl $ABF_ROOT/runs/v2/p5_$d/rule.json $O/$d/v2_oneshot_s0_valsub.jsonl v2_oneshot
  for B in 512 4096; do taskset -c $CPU0 $G construct.py run $D valsub v2frozen 0 4 $B; done
done
for d in 2d 3d; do
  D=${d^^}; E=$E2; [ $d = 3d ] && E=$E3
  F=$(ls $O/$d/*.jsonl | paste -sd,)
  nice -n 10 $E construct.py verify $D $F $W $CPU0 $ABF_ROOT/runs/v2/p5_$d/verify.jsonl
done
echo V3_1_DONE
