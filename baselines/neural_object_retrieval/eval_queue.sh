#!/bin/bash
# Post-seal verification queue for one domain (laptop): seeds on full VALIDATION, ablations on the registered VALSUB (VALSUB_REGISTRATION.json).
# usage: eval_queue.sh DOM WORKERS CPU0
D=$1; W=$2; C=$3; E=$HOME/sorc_grid/eval; P=$E/pred
run(){ f=$1; [ -f ${f%.jsonl}_results.jsonl ] && return; echo "$(date -u +%FT%TZ) start $(basename $f)" >> $E/queue_$D.log; ./eval.sh $D $f $W $C >> $E/queue_$D.log 2>&1; }
for v in full_s1_full full_s2_full; do run $P/${D}_${v}.jsonl; done
export PRIV=$E/private_valsub_$D.jsonl PUB=$E/public_valsub_$D.jsonl
for v in full_s0_osnet_only full_s0_rpnet_only full_s0_both_analytic nogoal_s0_full full_s0_no_stop; do run $P/${D}_${v}__valsub.jsonl; done
echo "$(date -u +%FT%TZ) QUEUE_DONE $D" >> $E/queue_$D.log
