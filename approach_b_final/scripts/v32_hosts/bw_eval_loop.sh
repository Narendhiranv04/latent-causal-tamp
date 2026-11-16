#!/bin/bash
# loop seeds for one root shard on Blackwell.  usage: bw_eval_loop.sh ARM DOM PART CPU "SEEDS"
for s in $5; do $HOME/abf_v32/bw_eval.sh $1 $s $2 $3 $4; done
