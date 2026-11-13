#!/bin/bash
# gvlab2: when 2D collection is done, restart 3D collection with 34 workers on CPUs 8-41 (resumes by root).
cd $HOME/abf_v2/root/code
export ABF_ROOT=$HOME/abf_v2/root ABF_SNAPSHOT=$HOME/abf_v2/root/snapshot/abf_9de85710c2a7103f PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1
while ! grep -q "2D collect done" ../logs/v2_g2.log; do sleep 30; done
P=$(pgrep -f "onpolicy.py label 3D collect")
[ -z "$P" ] && exit 0
K=$(pgrep -P $P); kill $P; sleep 2; kill $K 2>/dev/null; sleep 5
$HOME/abf_v2/env3d/bin/python onpolicy.py label 3D collect 34 8 >> ../logs/col3d.log 2>&1 && echo "$(date +%T) 3D collect done (boosted)" >> ../logs/v2_g2.log
grep -q "3D coverage done" ../logs/v2_g2.log && echo G2_ALL_DONE >> ../logs/v2_g2.log
