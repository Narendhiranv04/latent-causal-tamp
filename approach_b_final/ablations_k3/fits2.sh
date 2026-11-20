#!/bin/bash
# P3b: D refits s1/s2 (environment-control diagnostic arm DREFIT), after fits.sh
source /home/projects/long-horizon/naren_workspace/k3abl/env.sh; cd $CODE/ablations_k3
until grep -q FITS_DONE $K3/runs/logs/fits.log; do sleep 20; done
run() { taskset -c 0-7 $PYG arms.py fit "$@" 2>&1 | grep '^{' | sed "s/^/{\"fit\": \"$*\", \"r\": /; s/$/}/" ; }
for d in 2d 3d; do for s in 1 2; do run xy D $s $d; done; done
echo FITS2_DONE
