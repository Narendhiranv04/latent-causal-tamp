#!/bin/bash
# V3-6 GPU part on gvlab2: TEST-split direct runs for the final matrix (rules frozen on validation in V3-5; nothing here is tuned).
# V3 scorers use $V3OUT/v3_5/rule_<dom>.json, V2-scorer arms keep the frozen V2 rule.  Then slim selection files for physical verification.
set -e
cd $HOME/abf_v3/code
export ABF_ROOT=$HOME/abf_v3/frozen V3OUT=$HOME/abf_v3/runs CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 V3_STAGE=v3_6
G="taskset -c 47 $HOME/abf_v3/envgpu/bin/python"
for D in 2D 3D; do d=${D,,}; R=$V3OUT/v3_5/rule_$d.json
  for s in 0 1 2; do V3_RULE=$R $G construct.py run $D test v3D $s 4 4096 S1 task:q2init_all; done              # primary, 3 seeds
  $G construct.py run $D test v2frozen 0 4 4096 S1 task:q2init_all                                               # 2x2: task sampler + V2 scorer
  V3_RULE=$R $G construct.py run $D test v3D 0 4 4096 S0 cvae                                                   # 2x2: Q2 sampler + V3 scorer
  $G construct.py run $D test v2frozen 0 4 4096 S0 cvae                                                          # 2x2: Q2 sampler + V2 scorer
  for a in v3E v3G v3DIRECT; do V3_RULE=$R $G construct.py run $D test $a 0 4 4096 S1 task:q2init_all; done     # F: factorization controls
  V3_RULE=$R $G construct.py run $D test v3D 0 4 4096 S2 uniform                                                # broad controls
  V3_RULE=$R $G construct.py run $D test v3D 0 4 4096 S0 stratified
  V3_RULE=$R $G construct.py run $D test v3D 0 4 4096 S1 task:goalablated_one                                   # repair supervision w/o goal
  for s in 0 1 2; do                                                                                            # old V2 iterative, re-generated (parity-exact on gvlab2)
    ABF_P5DIR=$V3OUT/v3_6/v2baselines ABF_P2RUNS=$ABF_ROOT/runs/v2 ABF_SNAPSHOT=$ABF_ROOT/snapshot/abf_9de85710c2a7103f $G evaluate.py select $D full $s test
    $G construct.py legacy $V3OUT/v3_6/v2baselines/p5_$d/search/full_s${s}_test.jsonl $ABF_ROOT/runs/v2/p5_$d/rule.json $V3OUT/v3_6/$d/v2_iterative_s${s}_test.jsonl v2_iterative
  done
  mkdir -p $V3OUT/slim_test/$d
  for f in $V3OUT/v3_6/$d/*_test.jsonl; do
    $HOME/abf_v3/envgpu/bin/python -c "
import json,sys
with open(sys.argv[2],'w') as g:
  for l in open(sys.argv[1]):
    r=json.loads(l); g.write(json.dumps({k:r[k] for k in ('root_id','selected_ordered_seq','decision')})+'\n')" "$f" "$V3OUT/slim_test/$d/$(basename "$f")"
  done
done
echo V3_6_RUNS_DONE
