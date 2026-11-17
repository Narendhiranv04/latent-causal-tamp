#!/bin/bash
# NOR-Grid full laptop pipeline (no teacher calls): TRAIN tensors -> GPU training (full s0/s1/s2 + goal-free s0) -> STOP calibration on
# decided VAL endpoint Y -> VAL predictions for every pre-declared variant -> benchmark seal.  Physical verification = eval.sh, separately.
set -e; cd $(dirname $(realpath $0)); S=$HOME/sorc_grid; B=../../approach_b_final; LOG=$S/pipeline.log
export OMP_NUM_THREADS=4 PYTHONWARNINGS=ignore
log(){ echo "$(date -u +%FT%TZ) $*" | tee -a $LOG; }
for d in 2d 3d; do
  [ -f $S/tensors/full_$d.npz ] || { log "tensors $d"; nice -n 10 python3 samples.py $d $S/labels/homotopy_${d}_train.jsonl $S/tensors/full_$d.npz >> $LOG 2>&1; }
  [ -f $S/tensors/nogoal_$d.npz ] || { log "tensors nogoal $d"; NOR_GOAL=0 nice -n 10 python3 samples.py $d $S/labels/homotopy_${d}_train.jsonl $S/tensors/nogoal_$d.npz >> $LOG 2>&1; }
done
for d in 2d 3d; do
  for s in 0 1 2; do
    M=$S/models/$d/full_s$s
    [ -f $M/train_report.json ] || { log "train $d full s$s"; python3 train.py $d $S/tensors/full_$d.npz $M $s >> $LOG 2>&1; }
    [ -f $M/calibration.json ] || python3 -c "import sys;sys.path.insert(0,'.');import train as T;T.calibrate('$S/tensors/full_$d.npz','$M')" >> $LOG 2>&1
  done
  M=$S/models/$d/nogoal_s0
  [ -f $M/train_report.json ] || { log "train $d nogoal s0"; python3 train.py $d $S/tensors/nogoal_$d.npz $M 0 >> $LOG 2>&1; touch $M/NO_GOAL; }
  [ -f $M/calibration.json ] || python3 -c "import sys;sys.path.insert(0,'.');import train as T;T.calibrate('$S/tensors/nogoal_$d.npz','$M')" >> $LOG 2>&1
  touch $M/NO_GOAL
done
mkdir -p $S/eval/pred
for d in 2d 3d; do
  for v in "full_s0 full" "full_s1 full" "full_s2 full" "full_s0 osnet_only" "full_s0 rpnet_only" "full_s0 both_analytic" "full_s0 no_stop" "nogoal_s0 full"; do
    set -- $v; P=$S/eval/pred/${d}_${1}_${2}.jsonl
    [ -f $P.SEAL.json ] && continue
    log "predict $d $1 $2"
    python3 policy.py predict $S/eval/public_val_$d.jsonl $S/models/$d/$1 $P $2 cuda >> $LOG 2>&1
    python3 $B/benchmark.py validate --public $S/eval/public_val_$d.jsonl --predictions $P >> $LOG 2>&1
    python3 $B/benchmark.py seal $P --public $S/eval/public_val_$d.jsonl >> $LOG 2>&1
  done
done
log "PIPELINE_DONE"
