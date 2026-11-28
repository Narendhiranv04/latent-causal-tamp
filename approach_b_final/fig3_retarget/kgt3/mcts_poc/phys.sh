#!/bin/bash
# Unchanged physical verification contract (physical3d.py work: X_CHUNKED + endpoint Y + replay) on the deduplicated jobs.  NOT RUN in phase 1.
#   phys.sh W CPU_LO      e.g. phys.sh 8 12  -> 8 workers pinned to CPUs 12..19 (physical3d sets its own affinity CPU_LO..CPU_LO+W-1)
M=/home/projects/long-horizon/naren_workspace/mcts_poc
source /home/projects/long-horizon/naren_workspace/fig3/env.sh; export CODE=$M/code/approach_b_final PYTHONDONTWRITEBYTECODE=1
E=$M/out/eval; cd $CODE/fig3_retarget
[ "$(sha256sum $E/jobs_eval.json | cut -d' ' -f1)" = "$(cat $E/jobs_eval.json.SEAL)" ] || { echo "jobs not sealed"; exit 1; }
nice -n 10 $PY3D physical3d.py work $E/jobs_eval.json $E/phys_eval.jsonl ${1:-8} ${2:-12} 5000 ${3:-30.0} > $E/phys.log 2>&1
