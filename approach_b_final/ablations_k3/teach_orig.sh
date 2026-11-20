#!/bin/bash
# parallel 2D VAL teach of the 'original'-geometry union jobs while the main teach finishes its fastgeom1 tail (same cache, append-only)
source /home/projects/long-horizon/naren_workspace/k3abl/env.sh; cd $CODE
V=$K3/runs/verification/val
$PYG -c "
import json
J=[json.loads(l) for l in open('$V/jobs_union_2d.jsonl')]
open('$V/jobs_union_2d_original.jsonl','w').writelines(json.dumps(j)+'\n' for j in J if j['geom']=='original')
print(sum(j['geom']=='original' for j in J))"
taskset -c $K3CPUS $PY2D benchmark.py teach 2d $V/jobs_union_2d_original.jsonl $K3/runs/verifier_cache 30 10
echo TEACH_ORIG_DONE
