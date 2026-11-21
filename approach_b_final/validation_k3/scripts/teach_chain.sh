#!/bin/bash
# k3val teacher chain: 2D argmax queries on CPUs 34-42 now; temporary-target queries on 4-33 after the 3D argmax chain ends.
source /home/projects/long-horizon/naren_workspace/k3val/env.sh; cd $CODE/validation_k3
(TEACH_CPU0=34 $PYG queries.py teach val 2d 9 && TEACH_CPU0=34 $PYG queries.py teach test 2d 9) > $K3V/runs/logs/teach_2d.log 2>&1 &
while pgrep -f "queries.py teach .* 3d" > /dev/null; do sleep 30; done
(TEACH_CPU0=4 $PYG ttarget.py teach 2d 12) > $K3V/runs/logs/teach_tt2d.log 2>&1 &
(TEACH_CPU0=16 $PYG ttarget.py teach 3d 18) > $K3V/runs/logs/teach_tt3d.log 2>&1 &
wait
