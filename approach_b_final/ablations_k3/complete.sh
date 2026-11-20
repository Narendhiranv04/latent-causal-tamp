#!/bin/bash
# prints the number of (arm, domain) prediction files of SPLIT that are complete (expect 60)
S=$1; W=/home/projects/long-horizon/naren_workspace/k3abl; n=0
declare -A N=([val_2d]=751 [val_3d]=364 [test_2d]=749 [test_3d]=370)
for a in FULL_s0 FULL_s1 FULL_s2 E_s0 E_s1 E_s2 G_s0 G_s1 G_s2 DIRECT_s0 DIRECT_s1 DIRECT_s2 DREFIT_s0 DREFIT_s1 DREFIT_s2 UNIFORM4_r0 UNIFORM4_r1 UNIFORM4_r2 TASKFM_s0 TASKFM_s1 TASKFM_s2 NOTASK_s0 NOTASK_s1 NOTASK_s2 SAMPREF_s1 SAMPREF_s2 M1 C1_r0 C1_r1 C1_r2; do
  for d in 2d 3d; do f=$W/runs/predictions/$a/${S}_$d.jsonl; [ -f $f ] && [ $(wc -l < $f) -eq ${N[${S}_$d]} ] && n=$((n+1)); done; done
echo $n
