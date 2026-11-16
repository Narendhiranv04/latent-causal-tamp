#!/bin/bash
# V3.2 E6 TEST exhaustive scoring on Blackwell (both arms x 3 seeds; scoring only, no teacher queries): 2D parts 0-15 of 24, then 3D (1 part).
cd $HOME/abf_v32; export SPLIT=test
for i in $(seq 0 15); do (for a in control expanded; do ./bw_eval_loop.sh $a 2d $i/24 $((4+i)) "0 1 2"; done) & done
wait
for a in control expanded; do ./bw_eval_loop.sh $a 3d 0/1 4 "0 1 2" & done; wait
echo "$(date +%T) BW_TEST_SCORING_DONE" >> logs_test_queue.log
