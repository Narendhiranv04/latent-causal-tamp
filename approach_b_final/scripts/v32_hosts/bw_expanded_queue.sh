#!/bin/bash
# Blackwell share of the D-expanded 2D VAL scoring: parts 0-3 now (4 free slots), parts 4-11,22,23 once the 12 control processes have exited.
cd $HOME/abf_v32
for i in 0 1 2 3; do ./bw_eval_loop.sh expanded 2d $i/24 $((20+i)) "0 1 2" & done
while [ "$(cat logs_eval_control_*_2d_*.log 2>/dev/null | grep -c BW_EVAL)" -lt 12 ]; do sleep 30; done
c=8; for i in 4 5 6 7 8 9 10 11 22 23; do ./bw_eval_loop.sh expanded 2d $i/24 $c "0 1 2" & c=$((c+1)); done
wait; echo "$(date +%T) BW_EXPANDED_2D_ALL_DONE" >> logs_expanded_queue.log
