#!/bin/bash
# V3.4 batch A: (after seals) teacher queries for sealed REPAIR predictions + P4 ground truth Y(empty) for every K0 root, unchanged teachers.
# usage: verify.sh DOM WORKERS CPU0
set -e; D=$1; W=$2; C0=$3; A=$HOME/abf_v34/batchA; L=$HOME/abf_v3_laptop; cd $HOME/Desktop/boltzmann_lfd/.claude/worktrees/approach-b-v3-4-final-benchmark/approach_b_final
log(){ echo "$(date -u +%FT%TZ) $*" >> $A/verify_$D.log; }
mkdir -p $A/cache; log start
python3 benchmark.py queries --predictions $A/pred_$D.jsonl --private $A/private_$D.jsonl --cache $A/cache --out $A/jobs >> $A/verify_$D.log 2>&1
python3 - "$A" "$D" <<'PY'
import json, sys
from pathlib import Path
A, d = Path(sys.argv[1]), sys.argv[2]
jf = A / f"jobs_{d}.jsonl"
jobs = {j["root_id"]: j for j in map(json.loads, open(jf))} if jf.exists() else {}
n = 0
for e in map(json.loads, open(A / f"private_{d}.jsonl")):
    if e["K"] == "0":                                                   # P4: one Y(empty) query per K0 root
        j = jobs.setdefault(e["root_id"], {"root_id": e["root_id"], "dom": d.upper(), "path": str((A / e["path"]).resolve()),
                                           "geom": e.get("geom", "original"), "seqs": [], "ids": e["ids"]})
        if [] not in j["seqs"]:
            j["seqs"].append([]); n += 1
with open(jf, "w") as f:
    for j in jobs.values():
        f.write(json.dumps(j) + "\n")
print(json.dumps({"dom": d, "jobs_roots": len(jobs), "k0_empty_queries": n, "queries": sum(len(j["seqs"]) for j in jobs.values())}))
PY
ABF_ROOT=$L/root V3OUT=$A/teach_out FIN3D_CODE=$L/gen/final3d_v4/code FIN3D_SRC=$L/gen/final3d_v4/src/dataset_bd_classquota_without_home_position_no_overpass \
MUJOCO_GL=disable OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES= \
nice -n 10 $L/env$D/bin/python benchmark.py teach $D $A/jobs_$D.jsonl $A/cache $W $C0 >> $A/verify_$D.log 2>&1
log TEACH_DONE
