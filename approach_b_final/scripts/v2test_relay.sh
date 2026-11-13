#!/bin/bash
# Laptop = transfer + remote launch only: V2 2D TEST verification on gvlab2 (40 workers), results back to gvlab.
S=/tmp/claude-1000/-home-naren-Desktop-boltzmann-lfd/2b63770c-8b68-4a44-bb5e-cd133b6e31dc/scratchpad/g2/v2test; mkdir -p $S
GV=gvlab:/scratch/nav/approachb_final; G2=gvlab2.iiit.ac.in
until ssh -o BatchMode=yes gvlab "test -e /scratch/nav/approachb_final/runs/v2/p5_2d/TEST_SEARCH_READY"; do sleep 30; done
rsync -a $GV/runs/v2/p5_2d/search $GV/runs/v2/p5_2d/rule.json $GV/runs/v2/p5_2d/verify.jsonl $S/
rsync -a $S/ $G2:abf_v2/root/runs/v2/p5_2d/
rsync -a $GV/runs/p1_2d/analytic_choice.json $S/ac.json
echo "$(date +%T) 2D test verify start on gvlab2"
ssh -o BatchMode=yes $G2 "bash -c 'cd ~/abf_v2/root/code && ABF_ROOT=\$HOME/abf_v2/root ABF_SNAPSHOT=\$HOME/abf_v2/root/snapshot/abf_9de85710c2a7103f ABF_P5DIR=\$HOME/abf_v2/root/runs/v2 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 ../../env2d/bin/python evaluate.py verify 2D test ../runs/v2/p5_2d/rule.json 40 >> ../logs/v2test_2d.log 2>&1'"
echo "$(date +%T) 2D test verify done on gvlab2"
rsync -a $G2:abf_v2/root/runs/v2/p5_2d/verify.jsonl $S/verify.jsonl && rsync -a $S/verify.jsonl $GV/runs/v2/p5_2d/verify.jsonl
rsync -a $G2:abf_v2/root/runs/teacher2d_witnesses/ $S/w2d/ 2>/dev/null; rsync -a $S/w2d/ $GV/runs/teacher2d_witnesses/ 2>/dev/null
ssh -o BatchMode=yes gvlab "touch /scratch/nav/approachb_final/runs/v2/p5_2d/TEST_VERIFIED"
echo V2TEST_RELAY_DONE
