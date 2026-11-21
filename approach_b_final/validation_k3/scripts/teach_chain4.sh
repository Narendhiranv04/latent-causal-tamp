#!/bin/bash
# k3val C3b: blocked temporary-target queries -- 2D now on CPUs 4-15, 3D on 16-33 once the first 3D temporary-target run ends
source /home/projects/long-horizon/naren_workspace/k3val/env.sh; cd $CODE/validation_k3
(TEACH_CPU0=4 $PYG ttarget.py teach 2d 12 _b) > $K3V/runs/logs/teach_tt2d_b.log 2>&1 &
while ps -eo args | grep -q "[t]target.py teach 3d 18$"; do sleep 30; done
(TEACH_CPU0=16 $PYG ttarget.py teach 3d 18 _b) > $K3V/runs/logs/teach_tt3d_b.log 2>&1 &
wait
