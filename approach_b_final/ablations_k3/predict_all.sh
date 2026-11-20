#!/bin/bash
# P4/P6: every registered arm x domain on SPLIT (val | test), <= 36 concurrent single-thread processes, all under taskset 0-42.
# Heavy 2D arms first (longest), then 3D.  Resumable: run.py skips roots already written.
SPLIT=$1
source /home/projects/long-horizon/naren_workspace/k3abl/env.sh; cd $CODE/ablations_k3
ARMS="${ARMS:-FULL_s0 FULL_s1 FULL_s2 E_s0 E_s1 E_s2 G_s0 G_s1 G_s2 DIRECT_s0 DIRECT_s1 DIRECT_s2 DREFIT_s0 DREFIT_s1 DREFIT_s2 UNIFORM4_r0 UNIFORM4_r1 UNIFORM4_r2 TASKFM_s0 TASKFM_s1 TASKFM_s2 NOTASK_s0 NOTASK_s1 NOTASK_s2 SAMPREF_s1 SAMPREF_s2 M1 C1_r0 C1_r1 C1_r2}"
{ for a in $ARMS; do echo "$a 2d"; done; for a in $ARMS; do echo "$a 3d"; done; } | \
  xargs -P 36 -L 1 bash -c 'taskset -c $K3CPUS $PYG run.py predict $0 $1 '"$SPLIT"' >> $K3/runs/logs/predict_'"$SPLIT"'_$0_$1.log 2>&1'
echo PREDICT_${SPLIT}_DONE
