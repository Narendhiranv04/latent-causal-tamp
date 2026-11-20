#!/bin/bash
# v2: when every fastgeom1 union query is cached (the main teach would next start the 'original' group already handled by teach_orig.sh), stop
# exactly that main teach tree + p5.sh/auto_p5.sh; after teach_orig finishes, re-run p5.sh val (seal/lock skip; teach = uncached only; 3D; evaluate)
source /home/projects/long-horizon/naren_workspace/k3abl/env.sh; cd $K3
left() { $PYG -c "
import json
U=[json.loads(l) for l in open('runs/verification/val/jobs_union_2d.jsonl')]
have={(v['root'],json.dumps(x['seq'])) for v in map(json.loads,open('runs/verifier_cache/verify_2d.jsonl')) for x in v['results']}
print(sum((j['root_id'],json.dumps([[j['ids'].index(o),c] for o,c in s])) not in have for j in U if j['geom']=='fastgeom1' for s in j['seqs']))"; }
until [ "$(left)" = "0" ]; do sleep 20; done
T=$(ps -u $(id -u) -o pid,args | awk '$2 ~ /python/ && /benchmark.py teach 2d/ && /jobs_union_2d.jsonl/ {print $1}')
P=$(ps -u $(id -u) -o pid,args | awk '$2 == "bash" && $3 == "p5.sh" {print $1}')
A=$(ps -u $(id -u) -o pid,args | awk '$2 == "bash" && $3 == "auto_p5.sh" {print $1}')
echo "$(date +%T) stopping main teach $T p5 $P auto $A" >> runs/logs/guard_val2d.log
[ -n "$A" ] && kill $A; [ -n "$P" ] && kill $P
for t in $T; do pkill -TERM -P $t; kill $t; done
until grep -q TEACH_ORIG_DONE runs/logs/teach_orig_val2d.log; do sleep 20; done
mv runs/logs/p5_val.log runs/logs/p5_val.part1.log
bash p5.sh val > runs/logs/p5_val.log 2>&1
