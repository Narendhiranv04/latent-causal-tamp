#!/bin/bash
# V3.1-4 verification progress, final phase: 3D legs (explicit lists, since 00:41) + remaining 2D legs; per-leg ETA from the change since the previous call.
cnt='import json,sys
n=0
for i,l in enumerate(open(sys.argv[1])):
  if i>=int(sys.argv[2]):
    try: n+=len(json.loads(l)["results"])
    except Exception: pass
print(n)'
l3=$(python3 -c "$cnt" ~/abf_v31_lapverify/runs/verify_3d.jsonl 757)
g3=$(ssh -o ConnectTimeout=10 gvlab "python3 -c '$cnt' /scratch/nav/abf_v3_1/runs/verify_3d.jsonl 678" 2>/dev/null)
r3=$(ssh -o ConnectTimeout=10 girish "python3 -c '$cnt' /home/longhorizon/abf_v314v/prod/verify_3d.jsonl 0" 2>/dev/null)
r2=$(ssh -o ConnectTimeout=10 girish "python3 -c '$cnt' /home/longhorizon/abf_v314v/prod/verify_2d.jsonl 0" 2>/dev/null)
lap2=$(kill -0 58842 2>/dev/null && echo running || echo done); gv2=$(ssh -o ConnectTimeout=10 gvlab 'kill -0 2712003 2>/dev/null && echo running || echo done')
a=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
echo "$(date +%H:%M) 3D left $((458+133+r3-l3-g3-r3)) (lap $l3/458, gv $g3/133, girish stopped at $r3) | 2D: lap $lap2, gv $gv2, girish $r2/1565 | lap mem ${a}MB"
python3 ~/abf_v314_verify/eta.py $l3 ${g3:-0} ${r3:-0}
