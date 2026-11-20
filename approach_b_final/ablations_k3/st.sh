#!/bin/bash
# status: fits, prediction counts per arm/split/domain, load, GPU
W=/home/projects/long-horizon/naren_workspace/k3abl; date +%H:%M; tail -2 $W/runs/logs/fits.log | cut -c1-160
for s in val test; do for d in 2d 3d; do echo -n "$s $d: "; for f in $W/runs/predictions/*/${s}_${d}.jsonl; do [ -f $f ] && echo -n "$(basename $(dirname $f))=$(wc -l < $f) "; done; echo; done; done
echo load $(cut -d' ' -f1 /proc/loadavg) procs $(ps -u $(id -u) -o args | awk '$1 ~ /python/' | grep -c run.py); nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader
