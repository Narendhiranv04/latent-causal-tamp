#!/bin/bash
# Seal the public plans, THEN (evaluator) build the deduplicated physical job list with the private index.  NOT RUN in phase 1.
M=/home/projects/long-horizon/naren_workspace/mcts_poc; W=/home/projects/long-horizon/naren_workspace/r10
source /home/projects/long-horizon/naren_workspace/fig3/env.sh; export CODE=$M/code/approach_b_final PYTHONDONTWRITEBYTECODE=1
P=$CODE/fig3_retarget/kgt3/mcts_poc; E=$M/out/eval; cd $P
export R10_PUBLIC=$W/comp/PUBLIC_bench_comp_3d.jsonl
$PYG evaljobs.py merge $E || exit 1                                 # public only -> PLANS_EVAL.jsonl + SEAL
F=/home/projects/long-horizon/naren_workspace/fig3/final
R10_PRIVATE=$W/comp/PRIVATE_bench_comp_3d.jsonl R10_ARCHIVE_DIRS=$F/r8c:$F/r8c_ctrl $PY3D evaljobs.py jobs $E
