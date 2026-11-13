#!/bin/bash
# Laptop = transfer only: gvlab2 V2 labels -> gvlab every 5 min; final sync (labels + witness stores) + marker once gvlab2 logged ALL THREE
# completions ("2D collect done", "3D coverage done", "3D collect done"), so a restarted (boosted) job cannot trigger it early.
S=/tmp/claude-1000/-home-naren-Desktop-boltzmann-lfd/2b63770c-8b68-4a44-bb5e-cd133b6e31dc/scratchpad/g2/relay; mkdir -p $S/2d $S/3d
sync1() {
  rsync -a gvlab2.iiit.ac.in:abf_v2/root/runs/v2/3d/labels_coverage.jsonl gvlab2.iiit.ac.in:abf_v2/root/runs/v2/3d/labels_collect.jsonl $S/3d/ 2>/dev/null
  rsync -a gvlab2.iiit.ac.in:abf_v2/root/runs/v2/2d/labels_collect.jsonl $S/2d/ 2>/dev/null
  rsync -a $S/3d/ gvlab:/scratch/nav/approachb_final/runs/v2/3d/ && rsync -a $S/2d/ gvlab:/scratch/nav/approachb_final/runs/v2/2d/
}
done3() {
  rsync -a gvlab2.iiit.ac.in:abf_v2/root/logs/v2_g2.log $S/v2_g2.log 2>/dev/null || return 1
  grep -q "2D collect done" $S/v2_g2.log && grep -q "3D coverage done" $S/v2_g2.log && grep -q "3D collect done" $S/v2_g2.log
}
until done3; do sync1; sleep 300; done
sync1
rsync -a gvlab2.iiit.ac.in:abf_v2/root/runs/v2/2d/witnesses/ gvlab:/scratch/nav/approachb_final/runs/v2/2d/witnesses_g2/ 2>/dev/null
rsync -a gvlab2.iiit.ac.in:abf_v2/root/runs/v2/3d/store/ gvlab:/scratch/nav/approachb_final/runs/v2/3d/store_g2/ 2>/dev/null
ssh -o BatchMode=yes gvlab 'touch /scratch/nav/approachb_final/runs/v2/G2_SYNCED'
