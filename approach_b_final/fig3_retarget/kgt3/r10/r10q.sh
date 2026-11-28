#!/bin/bash
# R10.2 clean-training queue on gvlab2 (single RTX 5090; 4 GPU lanes x 2 CPUs on 36-43, nice 10; STOP file drains between jobs).
# Same frozen R7 recipes; inputs = LEGOLAS_FINAL_v1 canonical snapshot / Q2 / local split.  Resumable (jobs.jsonl; r7.py skips finished X fits).
W=/home/projects/long-horizon/naren_workspace/r10; REL=$W/release/LEGOLAS_FINAL_v1; C=$W/code/approach_b_final; K=$C/fig3_retarget/kgt3
SNAP=$(ls -d $REL/snapshot/abf_r10_*)
source /home/projects/long-horizon/naren_workspace/fig3/env.sh
export ABF_ROOT=$W/abf V3OUT=$W/runs XY_RUNS=$W/runs/xy R7_OUT=$W/runs R7_PACK_DIR=$W/pack K3=$W/k3 CR_RUNS=$W/cr CUDA_VISIBLE_DEVICES=0
export R10_SNAP=$SNAP R7_TRAIN_SNAP=$SNAP R7_VAL_SNAP=$SNAP CR_TRAIN_SNAP=$SNAP CR_VAL_SNAP=$SNAP CR_SCALERS_DIR=$REL/q2 R10_LOCAL_SPLIT=$REL/views/local_split.json
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1
mkdir -p $ABF_ROOT/snapshot $W/runs $W/pack $W/k3 $W/cr $W/logs/train; ln -sfn $REL/q2 $ABF_ROOT/data; ln -sfn $SNAP $ABF_ROOT/snapshot/$(basename $SNAP)
L=$W/logs/train
job() { local cpus=$1 dir=$2; shift 2; [ -f $W/STOP_TRAIN ] && return; local t0=$(date +%s) n=$(echo "$@" | tr ' /' '__')
  ( cd $dir && taskset -c $cpus nice -n 10 $PYG "$@" >> $L/$n.log 2>&1 ); local rc=$?
  echo "{\"job\": \"$*\", \"rc\": $rc, \"s\": $(( $(date +%s) - t0 )), \"end\": \"$(date -u +%FT%TZ)\"}" >> $L/jobs.jsonl; }
waitf() { until [ -f "$1" ] || [ -f $W/STOP_TRAIN ]; do sleep 20; done; }
lane1() { for d in 3d 2d; do for s in 0 1 2; do job 36-37 $K r7.py stageB $d $s; done; done
          for d in 3d 2d; do job 36-37 $K r7.py dump $d $W/pack/pack_$d.pt; done; }
lane2() { for s in 0 1 2; do for d in 3d 2d; do job 38-39 $K r7.py stageA $d $s; job 38-39 $K r7.py ablA $d $s q2init_all_notask; done; done; }
lane3() { for d in 3d 2d; do for s in 0 1 2; do job 40-41 $C/ablations_k3 arms.py fit taskfm $s $d; done; done
          for d in 3d 2d; do for s in 0 1 2; do job 40-41 $C/complete_repair_cvae train.py fit $d $s --tag r10; done; done
          for d in 3d 2d; do waitf $W/pack/pack_$d.pt; for s in 0 1 2; do waitf $XY_RUNS/p2_$d/D_s$s/curve.json
            for c in ORDINV UNCOUPLED DIRECT; do job 40-41 $K r7.py xfit $d G 1 $s $c; done; done; done; }
lane4() { for d in 3d 2d; do waitf $W/pack/pack_$d.pt; for s in 0 1 2; do waitf $XY_RUNS/p2_$d/D_s$s/curve.json
            for r in G M A; do for x in 1 0; do job 42-43 $K r7.py xfit $d $r $x $s; done; done; done; done; }
lane1 & lane2 & lane3 & lane4 & wait
for d in 3d 2d; do job 36-37 $K r7.py select $d; done
echo "R10Q_DONE $(date -u +%FT%TZ)" >> $L/jobs.jsonl
