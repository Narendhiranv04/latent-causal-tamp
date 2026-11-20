#!/bin/bash
# P2 teacher-cost pilot on the TRAIN pilot roots only (100/domain): union of FULL_s0/UNIFORM4_r0/M1/C1_r0 REPAIR queries, 38 workers
source /home/projects/long-horizon/naren_workspace/k3abl/env.sh; cd $CODE/ablations_k3
for d in 2d 3d; do
  taskset -c $K3CPUS $PYG verify.py teach pilottrain $d 38 FULL_s0 UNIFORM4_r0 M1 C1_r0
  taskset -c $K3CPUS $PYG verify.py evaluate pilottrain $d FULL_s0 UNIFORM4_r0 M1 C1_r0
done
echo PILOT_TEACH_DONE
