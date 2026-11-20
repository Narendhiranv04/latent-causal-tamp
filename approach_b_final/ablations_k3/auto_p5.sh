#!/bin/bash
# start P5 (VAL seal -> lock -> teach -> evaluate) as soon as all 60 VAL prediction files are complete and no predictor still runs
cd /home/projects/long-horizon/naren_workspace/k3abl
until [ "$(bash complete.sh val)" -ge 60 ] && ! ps -u $(id -u) -o args | awk '$1 ~ /python/' | grep -q "run.py predict"; do sleep 30; done
[ -f runs/logs/p5_val.log ] || bash p5.sh val > runs/logs/p5_val.log 2>&1
