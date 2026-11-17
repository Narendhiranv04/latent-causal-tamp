#!/bin/bash
# V3.3 VAL proposal dumps (girish GPU; same device / RNG stream as scoring).  -> ~/abf_v33/props/<arm>_s<seed>/<dom>.jsonl
cd $HOME/abf_v33/code
E="ABF_ROOT=$HOME/abf_v31/root V3OUT=$HOME/abf_v33/runs CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1"
for d in 2d 3d; do
  for a in control expanded; do for s in 0 1 2; do mkdir -p ~/abf_v33/props/${a}_s$s
    env $E V3_TASK_STAGE=v33/$a nice -n 10 $HOME/abf_v31/env/bin/python scripts/v33_proposals.py dump $d val task:scratch_all $s ~/abf_v33/props/${a}_s$s/$d.jsonl
  done; done
  mkdir -p ~/abf_v33/props/q2init_s0
  env $E V3_TASK_STAGE=v3_3 nice -n 10 $HOME/abf_v31/env/bin/python scripts/v33_proposals.py dump $d val task:q2init_all 0 ~/abf_v33/props/q2init_s0/$d.jsonl
done >> ~/abf_v33/logs/props.log 2>&1
echo "$(date +%T) PROPS_DONE" >> ~/abf_v33/logs/props.log
