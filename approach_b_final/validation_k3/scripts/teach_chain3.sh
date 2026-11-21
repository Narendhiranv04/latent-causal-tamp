#!/bin/bash
# k3val: after the temporary-target teaching ends, restart the 2D argmax teaching on CPUs 4-42 (resumes from the cache), then the budget queries.
source /home/projects/long-horizon/naren_workspace/k3val/env.sh; cd $CODE/validation_k3
while ps -eo args | grep -q "[t]target.py teach"; do sleep 30; done
for p in $(ps -eo pid,args | awk '/[t]each_chain.sh/{print $1}'); do kill $p; done
for p in $(ps -eo pid,args | awk '/[q]ueries.py teach (val|test) 2d/{print $1}'); do pkill -TERM -P $p; kill $p; done
sleep 20
TEACH_CPU0=4 $PYG queries.py teach val 2d 39 >> $K3V/runs/logs/teach_2d.log 2>&1
TEACH_CPU0=4 $PYG queries.py teach test 2d 39 >> $K3V/runs/logs/teach_2d.log 2>&1
(TEACH_CPU0=4 $PYG queries.py teachb 3d 12) > $K3V/runs/logs/teach_b3d.log 2>&1 &
(TEACH_CPU0=16 $PYG queries.py teachb 2d 27) > $K3V/runs/logs/teach_b2d.log 2>&1 &
wait
