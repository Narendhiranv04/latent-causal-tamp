#!/bin/bash
# speed-up: start the later-wave trained 2D arms (reverse order) once the frozen FULL/SAMPREF 2D files are complete (GPU memory headroom).
# run.py holds an exclusive flock per prediction file, so the main queue skips/merges safely.
source /home/projects/long-horizon/naren_workspace/k3abl/env.sh; cd $CODE/ablations_k3
P=$K3/runs/predictions
until [ $(cat $P/FULL_s0/val_2d.jsonl $P/FULL_s1/val_2d.jsonl $P/FULL_s2/val_2d.jsonl $P/SAMPREF_s1/val_2d.jsonl $P/SAMPREF_s2/val_2d.jsonl | wc -l) -ge 3755 ]; do sleep 30; done
for a in NOTASK_s2 NOTASK_s1 NOTASK_s0 TASKFM_s2 TASKFM_s1 TASKFM_s0 DREFIT_s2 DREFIT_s1 DREFIT_s0 DIRECT_s2 DIRECT_s1 DIRECT_s0; do echo $a; done | \
  xargs -P 6 -I{} bash -c "taskset -c \$K3CPUS \$PYG run.py predict {} 2d val >> \$K3/runs/logs/predict_val_{}_2d.log 2>&1"
echo EXTRA2D_DONE
