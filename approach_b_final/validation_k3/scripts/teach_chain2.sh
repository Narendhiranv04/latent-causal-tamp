#!/bin/bash
# after the temporary-target teaching (CPUs 4-33) ends: budget-diagnostic queries on the same CPUs
source /home/projects/long-horizon/naren_workspace/k3val/env.sh; cd $CODE/validation_k3
while pgrep -f "queries.py teach .* 3d" > /dev/null; do sleep 30; done; sleep 120
while pgrep -f "ttarget.py teach" > /dev/null; do sleep 30; done
(TEACH_CPU0=4 $PYG queries.py teachb 3d 12) > $K3V/runs/logs/teach_b3d.log 2>&1 &
(TEACH_CPU0=16 $PYG queries.py teachb 2d 18) > $K3V/runs/logs/teach_b2d.log 2>&1 &
wait
