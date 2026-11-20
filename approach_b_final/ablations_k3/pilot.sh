#!/bin/bash
# P2 pilot predictions (no teacher): FULL_s0, UNIFORM4_r0, M1, C1_r0 x {2d,3d} on the TRAIN+VAL pilot split
source /home/projects/long-horizon/naren_workspace/k3abl/env.sh; cd $CODE/ablations_k3
for d in 2d 3d; do for a in FULL_s0 UNIFORM4_r0 M1 C1_r0; do
  setsid nohup taskset -c $K3CPUS $PYG run.py predict $a $d pilot > $K3/runs/logs/pilot_${a}_${d}.log 2>&1 < /dev/null &
done; done
