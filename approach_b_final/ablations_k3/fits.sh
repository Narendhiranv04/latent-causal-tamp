#!/bin/bash
# P3: all missing controls, TRAIN fit / VAL selection only, one CUDA job at a time, seeds 0/1/2; plus pipeline-reproduction refits (D s0,
# scratch_all s0) compared to the frozen curves (never used as the reference).  Log: runs/logs/fits.log (one JSON line per fit).
source /home/projects/long-horizon/naren_workspace/k3abl/env.sh; cd $CODE/ablations_k3
run() { taskset -c 0-7 $PYG arms.py fit "$@" 2>&1 | grep '^{' | sed "s/^/{\"fit\": \"$*\", \"r\": /; s/$/}/" ; }
for d in 2d 3d; do
  run xy D 0 $d
  run scratch_all 0 $d
  for s in 0 1 2; do
    for a in E G DIRECT; do run xy $a $s $d; done
    run notask $s $d
    run taskfm $s $d
  done
done
echo FITS_DONE
