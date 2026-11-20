#!/bin/bash
# P5 (SPLIT=val) / P6 (SPLIT=test): seal -> protocol lock (before any teacher call on SPLIT) -> union teach (40 workers) -> evaluate -> tables/figures
set -e
SPLIT=$1
source /home/projects/long-horizon/naren_workspace/k3abl/env.sh; cd $CODE/ablations_k3
ARMS="FULL_s0 FULL_s1 FULL_s2 E_s0 E_s1 E_s2 G_s0 G_s1 G_s2 DIRECT_s0 DIRECT_s1 DIRECT_s2 DREFIT_s0 DREFIT_s1 DREFIT_s2 UNIFORM4_r0 UNIFORM4_r1 UNIFORM4_r2 TASKFM_s0 TASKFM_s1 TASKFM_s2 NOTASK_s0 NOTASK_s1 NOTASK_s2 SAMPREF_s1 SAMPREF_s2 M1 C1_r0 C1_r1 C1_r2"
T="taskset -c $K3CPUS $PYG"
[ "$(bash $K3/complete.sh $SPLIT)" -eq 60 ] || { echo "INCOMPLETE predictions for $SPLIT"; exit 1; }
for d in 2d 3d; do $T verify.py seal $SPLIT $d $ARMS > /dev/null; done
echo SEALED
[ -f $K3/runs/manifests/FINAL_ABLATION_PROTOCOL_LOCK_${SPLIT}.json ] || $T lock.py $SPLIT $ARMS
echo LOCKED
for d in 2d 3d; do $T verify.py teach $SPLIT $d 40 $ARMS; done
echo TAUGHT
for d in 2d 3d; do
  $T verify.py evaluate $SPLIT $d $ARMS > $K3/runs/logs/evaluate_${SPLIT}_$d.log 2>&1
  $T analyze.py physical $SPLIT $d FULL_s0 $(echo $ARMS | sed 's/FULL_s0 //') > $K3/runs/logs/physical_${SPLIT}_$d.log 2>&1
  $T analyze.py placement $SPLIT $d $ARMS > $K3/runs/logs/placement_${SPLIT}_$d.log 2>&1
done
$T figs_k3.py $SPLIT
echo P5_DONE_$SPLIT
