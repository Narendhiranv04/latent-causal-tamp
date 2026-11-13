#!/bin/bash
# Laptop = transfer + remote launch only.  V2 valsub verification on gvlab2 (40 workers, CPUs 6-45), results back to gvlab.
S=/tmp/claude-1000/-home-naren-Desktop-boltzmann-lfd/2b63770c-8b68-4a44-bb5e-cd133b6e31dc/scratchpad/g2/v2val; mkdir -p $S
GV=gvlab:/scratch/nav/approachb_final; G2=gvlab2.iiit.ac.in
for d in 2d 3d; do
  D=$(echo $d | tr a-z A-Z)
  until ssh -o BatchMode=yes gvlab "test -e /scratch/nav/approachb_final/runs/v2/p5_$d/SEARCH_READY"; do sleep 30; done
  mkdir -p $S/$d
  rsync -a $GV/runs/v2/p5_$d/search $GV/runs/v2/p5_$d/grid.json $GV/runs/v2/p5_$d/verify.jsonl $S/$d/
  ssh -o BatchMode=yes $G2 "mkdir -p abf_v2/root/runs/v2/p5_$d"
  rsync -a $S/$d/ $G2:abf_v2/root/runs/v2/p5_$d/
  E=$([ $d = 2d ] && echo env2d || echo env3d)
  echo "$(date +%T) $D verify start on gvlab2"
  ssh -o BatchMode=yes $G2 "bash -c 'cd ~/abf_v2/root/code && ABF_ROOT=\$HOME/abf_v2/root ABF_SNAPSHOT=\$HOME/abf_v2/root/snapshot/abf_9de85710c2a7103f ABF_P5DIR=\$HOME/abf_v2/root/runs/v2 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 ../../$E/bin/python evaluate.py verify $D valsub ../runs/v2/p5_$d/grid.json 40 >> ../logs/v2val_$d.log 2>&1'"
  echo "$(date +%T) $D verify done on gvlab2"
  rsync -a $G2:abf_v2/root/runs/v2/p5_$d/verify.jsonl $S/$d/verify.jsonl && rsync -a $S/$d/verify.jsonl $GV/runs/v2/p5_$d/verify.jsonl
  if [ $d = 2d ]; then rsync -a $G2:abf_v2/root/runs/teacher2d_witnesses/ $S/w2d/ 2>/dev/null; rsync -a $S/w2d/ $GV/runs/teacher2d_witnesses/ 2>/dev/null
  else rsync -a $G2:abf_v2/root/runs/p5_3d/verify_store/ $S/w3d/ 2>/dev/null; rsync -a $S/w3d/ $GV/runs/p5_3d/verify_store/ 2>/dev/null; fi
  ssh -o BatchMode=yes gvlab "touch /scratch/nav/approachb_final/runs/v2/p5_$d/VERIFIED"
done
echo V2VAL_RELAY_DONE
