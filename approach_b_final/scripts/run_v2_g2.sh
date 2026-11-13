#!/bin/bash
# gvlab2: V2 labelling with the unchanged teachers (parity with gvlab 12/12 2D, 3/3 3D).  44 of 48 cores.
cd $HOME/abf_v2/root/code
export ABF_ROOT=$HOME/abf_v2/root ABF_SNAPSHOT=$HOME/abf_v2/root/snapshot/abf_9de85710c2a7103f PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1
E2=$HOME/abf_v2/env2d/bin/python; E3=$HOME/abf_v2/env3d/bin/python; L=../logs/v2_g2.log
($E3 onpolicy.py label 3D coverage 8 0 >> ../logs/cov3d.log 2>&1 && echo "$(date +%T) 3D coverage done" >> $L) &
($E2 onpolicy.py label 2D collect 18 8 >> ../logs/col2d.log 2>&1 && echo "$(date +%T) 2D collect done" >> $L) &
($E3 onpolicy.py label 3D collect 18 26 >> ../logs/col3d.log 2>&1 && echo "$(date +%T) 3D collect done" >> $L) &
wait
echo G2_ALL_DONE >> $L
