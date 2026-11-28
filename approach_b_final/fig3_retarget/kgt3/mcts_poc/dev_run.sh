#!/bin/bash
# Phase-1 DEV runs on gvlab2 (CPUs 12-19 only, after r10/feas/run/DONE; CUDA 0; <= 2 concurrent GPU processes).  Outputs: $M/out/dev only.
#   dev_run.sh prep | tests | ga | prof | grid | frozen MCFG_JSON | exh | acct
M=/home/projects/long-horizon/naren_workspace/mcts_poc
source /home/projects/long-horizon/naren_workspace/fig3/env.sh
export CODE=$M/code/approach_b_final OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=0
F=/home/projects/long-horizon/naren_workspace/fig3/final
export R7_ROOT=$F/r7/runs R7_CVAE_3D=$F/r7/runs/r7_task/3d/q2init_all_s1/model.pt R6_FLOOR=final
P=$CODE/fig3_retarget/kgt3/mcts_poc; O=$M/out/dev; mkdir -p $O/grid; cd $P
CFG=$CODE/fig3_retarget/kgt3/reports/final/r8c_config.json; ROS=$O/PUBLIC_dev_3d.jsonl
[ -f /home/projects/long-horizon/naren_workspace/r10/feas/run/DONE ] || { echo "R10 feasibility not DONE: CPUs 12-19 not released"; exit 1; }
acct() {  # acct LABEL GPU(0/1) CMD... : wall / user / sys appended to $M/out/resources.jsonl
  local lab=$1 g=$2; shift 2; local t0=$(date +%s.%N)
  /usr/bin/time -f "%e %U %S" -o $O/.t_$lab.txt "$@"; local rc=$?
  read e u s < $O/.t_$lab.txt
  echo "{\"label\": \"$lab\", \"gpu\": $g, \"wall_s\": $e, \"cpu_s\": $(echo "$u + $s" | bc), \"rc\": $rc, \"start\": $t0, \"host\": \"gvlab2\"}" >> $M/out/resources.jsonl
}
case $1 in
prep)  acct prep 0 taskset -c 12 $PYG devtools.py prep $O ;;
tests) acct tests 0 taskset -c 12-13 $PYG devtools.py tests $O/TESTS.json ;;
ga)    acct ga_dev 1 taskset -c 12-13 $PYG anytime.py run $ROS $CFG $O/ga_dev.jsonl --arms GA --horizon 180 > $O/ga_dev.log 2>&1
       $PYG devtools.py parity $O/ga_dev.jsonl $F/r8c_dev/plans_3d.jsonl $O/GA_PARITY_DEV.json ;;
prof)  acct prof_dev 1 taskset -c 14-15 $PYG profile_ga.py $ROS $CFG $O/profile_dev.jsonl --horizon 180 > $O/prof.log 2>&1
       $PYG profile_ga.py summarize $O/PROFILE_GA_DEV.json $O/profile_dev.jsonl ;;
grid)  # 6 predeclared configs (TUNING_GRID.json), 2 lanes x 3 configs, horizon 30 s
       lane() { for m in "$@"; do id=$($PYG -c "import sys,json; sys.path.insert(0,'.'); import mcts_ga as M; print(M.canon_cfg({**json.loads('$m'), 'seed': 0}))")
                acct grid_$id 1 taskset -c $CPUS $PYG anytime.py run $ROS $CFG $O/grid/grid_$id.jsonl --arms GA-MCTS --seed 0 --mcfg "$m" --horizon 30 --budgets 5,10,20,30 > $O/grid/grid_$id.log 2>&1; done; }
       CPUS=12-13 lane '{"c": 0.2, "expand": "FULL"}' '{"c": 0.7, "expand": "FULL"}' '{"c": 2.0, "expand": "FULL"}' &
       CPUS=14-15 lane '{"c": 0.2, "expand": "PW"}' '{"c": 0.7, "expand": "PW"}' '{"c": 2.0, "expand": "PW"}' &
       wait; $PYG tune.py $O/ga_dev.jsonl $O/grid $O/TUNING_RESULT.json ;;
frozen) acct mcts_dev_s0 1 taskset -c 12-13 $PYG anytime.py run $ROS $CFG $O/mcts_dev_s0.jsonl --arms GA-MCTS --seed 0 --mcfg "$2" --horizon 180 > $O/mcts_dev_s0.log 2>&1 ;;
exh)   # exhaustion equivalence on DEV roots whose GA EXACT search finished quickly: GA-MCTS run to exhaustion must select the GA plan
       R=$($PYG -c "import json; print(','.join(r['root_id'] for r in map(json.loads, open('$O/ga_dev.jsonl')) if r['final']['mode']=='EXACT' and r['final']['wall_s']<12))")
       acct exh_dev 1 taskset -c 14-15 $PYG anytime.py run $ROS $CFG $O/exh_dev.jsonl --arms GA-MCTS --seed 0 --mcfg "$2" --horizon 900 --budgets 900 --roots $R > $O/exh_dev.log 2>&1 ;;
esac
