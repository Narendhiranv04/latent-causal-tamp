#!/bin/bash
# V3.1-4 GPU inference on girish-laptop (gvcstar, RTX 3080 Ti 16 GB; user-authorised, max 4 CPU workers).  Frozen V3 artifacts only, no
# training, no teachers.  Two chains (2D, 3D) in parallel, 2 cores each (= 4 workers).  Physical verification happens later on gvlab CPU.
#   0  parity   : V3 primary s0 on VALIDATION at B=128 and B=4096 -> compared with gvlab V3.1-B/C selections before anything is used
#   1  budget   : V3 primary on TEST, s0 at B=128/512/2048/4096, s1-s2 at B=4096 (V3-6 reproduction); V2 iterative s0 at 3/12/48 expansions
#   2  goal     : matched goal ablation on TEST (V3.1-A cVAEs q2init_all / _nogoal / _notask x s0-s2, frozen V3 D, frozen rule, M4 B4096)
#   3  seeds    : V3 E / G / DIRECT scorers with the task cVAE on TEST, s1-s2 (V3-6 ran them on s0 only)
H=$HOME/abf_v31; cd $H/code
export ABF_ROOT=$H/root V3OUT=$H/runs OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=disable
PY=$H/env/bin/python
chain() {  # $1 = 2D|3D, $2 = cores
  D=$1; d=${D,,}; P="taskset -c $2 nice -n 10 $PY"; R=$V3OUT/v3_5/rule_$d.json
  for B in 128 4096; do V3_TASK_STAGE=v3_3 V3_STAGE=v3_1_4_parity V3_RULE=$R $P construct.py run $D val v3D 0 4 $B S1 task:q2init_all; done
  echo "$(date +%T) $D PARITY_RUNS_DONE"
  for B in 4096 128 512 2048; do V3_TASK_STAGE=v3_3 V3_STAGE=v3_1_4 V3_RULE=$R $P construct.py run $D test v3D 0 4 $B S1 task:q2init_all; done
  for s in 1 2; do V3_TASK_STAGE=v3_3 V3_STAGE=v3_1_4 V3_RULE=$R $P construct.py run $D test v3D $s 4 4096 S1 task:q2init_all; done
  for E in 12 3 48; do
    ABF_MAX_EXP=$E ABF_P5DIR=$V3OUT/v3_1_4/v2_exp$E ABF_P2RUNS=$ABF_ROOT/runs/v2 ABF_SNAPSHOT=$ABF_ROOT/snapshot/abf_9de85710c2a7103f $P evaluate.py select $D full 0 test
    $P construct.py legacy $V3OUT/v3_1_4/v2_exp$E/p5_$d/search/full_s0_test.jsonl $ABF_ROOT/runs/v2/p5_$d/rule.json $V3OUT/v3_1_4/$d/v2_iterative_exp${E}_s0_test.jsonl v2_iterative_exp$E
  done
  echo "$(date +%T) $D BUDGET_DONE"
  for v in q2init_all q2init_all_nogoal q2init_all_notask; do for s in 0 1 2; do
    V3_TASK_STAGE=v3_1a V3_STAGE=v3_1_4_goal V3_RULE=$R $P construct.py run $D test v3D $s 4 4096 S1 task:$v
  done; done
  echo "$(date +%T) $D GOAL_DONE"
  for a in v3E v3G v3DIRECT; do for s in 1 2; do
    V3_TASK_STAGE=v3_3 V3_STAGE=v3_1_4_seeds V3_RULE=$R $P construct.py run $D test $a $s 4 4096 S1 task:q2init_all
  done; done
  echo "$(date +%T) $D SEEDS_DONE"
}
chain 2D 0,1 > $H/logs/v314_2d.log 2>&1 &
chain 3D 2,3 > $H/logs/v314_3d.log 2>&1 &
wait
echo "$(date +%T) V314_GPU_DONE" | tee -a $H/logs/v314_2d.log $H/logs/v314_3d.log
