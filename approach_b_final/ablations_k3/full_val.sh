#!/bin/bash
source /home/projects/long-horizon/naren_workspace/k3abl/env.sh; cd $CODE
rm -f $K3/runs/predictions/FULL/val_.jsonl
for d in 2d 3d; do
  setsid nohup taskset -c $K3CPUS $PYG benchmark.py predict --bundle $K3_BUNDLE --input $K3/runs/public/public_val_${d}.jsonl --output $K3/runs/predictions/FULL/val_${d}_s0.jsonl > $K3/runs/logs/full_val_${d}.log 2>&1 < /dev/null &
done
