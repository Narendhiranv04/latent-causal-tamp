#!/bin/bash
# Run exhaustive scoring jobs sequentially on one CPU.  usage: girish_queue.sh CPU "arm sseed dseed dom part;..."
IFS=';' read -ra J <<< "$2"
for j in "${J[@]}"; do set -- $1 $j; ~/abf_v33/girish_ex.sh v33/$2 task:scratch_all $3 $4 $5 $6 $1 4 ${2}_s$3_D$4_M4_val; done
