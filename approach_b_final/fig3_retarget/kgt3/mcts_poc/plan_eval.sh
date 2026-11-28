#!/bin/bash
# GA-MCTS BENCH_COMP evaluation: PUBLIC-ONLY planning of the 99 roots (gvlab2).  NOT RUN in phase 1.
# Expectation: an EXCLUSIVE GPU window on CUDA 0 (no other GPU process; timing claims are only valid then) and 8 dedicated CPUs
# (4 shards x 2 CPUs, CPUSET_BASE..+7, default 36 = the R10 GPU lanes once R10 is idle).  Each stage is resumable (append + skip done roots).
#   plan_eval.sh s0      GA anytime + GA-MCTS anytime seed 0 (primary)          ~ 99 x (GA <= 180 s + MCTS 180 s) / 4 shards  ~ 2.2 h wall
#   plan_eval.sh s12     GA-MCTS anytime seeds 1 and 2                           ~ 99 x 2 x 180 s / 4 shards                    ~ 2.5 h wall
#   plan_eval.sh ref     H3 + REC (r6.py plan r10comp, R8C config)               ~ 99 x 9 s / 4 shards                          ~ 4 min
#   plan_eval.sh all     s0, then ref, then s12
M=/home/projects/long-horizon/naren_workspace/mcts_poc
source /home/projects/long-horizon/naren_workspace/fig3/env.sh
export CODE=$M/code/approach_b_final OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=0
F=/home/projects/long-horizon/naren_workspace/fig3/final
export R7_ROOT=$F/r7/runs R7_CVAE_3D=$F/r7/runs/r7_task/3d/q2init_all_s1/model.pt R6_FLOOR=final
unset R10_PRIVATE R8B_ROSTER                                      # the planner never sees the private index
P=$CODE/fig3_retarget/kgt3/mcts_poc; E=$M/out/eval; mkdir -p $E/r6; cd $P
ROS=/home/projects/long-horizon/naren_workspace/r10/comp/PUBLIC_bench_comp_3d.jsonl
CFG=$CODE/fig3_retarget/kgt3/reports/final/r8c_config.json; FZ=$P/MCTS_PROTOCOL_FREEZE.json
B=${CPUSET_BASE:-36}
$PYG freeze.py check $FZ || { echo "FREEZE MISMATCH: refusing to plan"; exit 1; }
MC=$($PYG -c "import json; m=json.load(open('$FZ'))['mcts_config']; m.pop('seed', None); print(json.dumps(m))")
log() { echo "{\"stage\": \"$1\", \"$2\": \"$(date -u +%FT%TZ)\", \"load\": \"$(cut -d' ' -f1-3 /proc/loadavg)\", \"gpu\": \"$(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader | tr '\n' ';')\"}" >> $E/timing_log.jsonl; }
s0() { log s0 start
  for i in 0 1 2 3; do c=$((B+2*i)); taskset -c $c-$((c+1)) $PYG anytime.py run $ROS $CFG $E/any_s0.part$i.jsonl --arms GA,GA-MCTS --seed 0 --mcfg "$MC" --horizon 180 --shard $i/4 > $E/any_s0.part$i.log 2>&1 & done; wait; log s0 end; }
s12() { for s in 1 2; do log s$s start
  for i in 0 1 2 3; do c=$((B+2*i)); taskset -c $c-$((c+1)) $PYG anytime.py run $ROS $CFG $E/any_s$s.part$i.jsonl --arms GA-MCTS --seed $s --mcfg "$MC" --horizon 180 --shard $i/4 > $E/any_s$s.part$i.log 2>&1 & done; wait; log s$s end; done; }
ref() { log ref start
  for i in 0 1 2 3; do c=$((B+2*i)); R6_OUT=$E/r6 R6_ARMS=H3,REC-ORDERED R10_PUBLIC=$ROS R6_SHARD=$i/4 taskset -c $c-$((c+1)) $PYG ../r6.py plan r10comp $CFG > $E/r6/plan_$i.log 2>&1 & done; wait
  R6_OUT=$E/r6 R6_ARMS=H3,REC-ORDERED R10_PUBLIC=$ROS $PYG ../r6.py merge r10comp 4; log ref end; }
case $1 in s0) s0 ;; s12) s12 ;; ref) ref ;; all) s0; ref; s12 ;; *) echo "usage: plan_eval.sh s0|s12|ref|all"; exit 2 ;; esac
