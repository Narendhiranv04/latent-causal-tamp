#!/bin/bash
source /home/projects/long-horizon/naren_workspace/k3abl/env.sh; cd $CODE/ablations_k3
ARMS="FULL_s0 FULL_s1 FULL_s2 E_s0 E_s1 E_s2 G_s0 G_s1 G_s2 DIRECT_s0 DIRECT_s1 DIRECT_s2 DREFIT_s0 DREFIT_s1 DREFIT_s2 UNIFORM4_r0 UNIFORM4_r1 UNIFORM4_r2 TASKFM_s0 TASKFM_s1 TASKFM_s2 NOTASK_s0 NOTASK_s1 NOTASK_s2 SAMPREF_s1 SAMPREF_s2 M1 C1_r0 C1_r1 C1_r2"
T="taskset -c $K3CPUS $PYG"
$T verify.py evaluate val 2d $ARMS > $K3/runs/logs/evaluate_val_2d.log 2>&1
$T analyze.py physical val 2d FULL_s0 $(echo $ARMS | sed 's/FULL_s0 //') > $K3/runs/logs/physical_val_2d.log 2>&1
$T analyze.py placement val 2d $ARMS > $K3/runs/logs/placement_val_2d.log 2>&1
echo EVAL2D_DONE
