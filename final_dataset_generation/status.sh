#!/bin/bash
# One-shot status of the three generation hosts (read-only).
cd /home/naren/Desktop/boltzmann_lfd/final_dataset_generation
S='
import json,sys,collections as C
L=[json.loads(l) for l in open(sys.argv[1])][int(sys.argv[2]):]
out=[]
for k in ("K2_REPARK","K3_REPARK","K2_CHAIN","K3_CHAIN","K3_DOUBLE"):
    X=[x for x in L if x["kind"]==k]; a=[x for x in X if x["accepted"]]
    if X: out.append("%s %d done, %d acc %s, %.0f cpu-s/acc, err %d" % (k,len(X),len(a),dict(sorted(C.Counter("%s/%s"%(x["n_success"],x["n_orders"]) for x in a).items())),sum(x["cpu_s"] for x in X)/max(len(a),1),sum("ERROR" in (x.get("reason") or "") for x in X)))
print(len(L),"jobs |"," || ".join(out), "| cpu-h %.1f" % (sum(x["cpu_s"] for x in L)/3600))
'
echo "$(date +%H:%M) LAPTOP  $(python3 -c "$S" d2/ledger.jsonl ${1:-0}) | $(tail -1 $(ls -t d2_*.log | head -1) | cut -c1-60)"
for h in gvlab user1@10.4.25.63; do
  echo "      ${h##*@} $(ssh -o BatchMode=yes -o ConnectTimeout=15 $h "cd ~/approachb_final_gen && python3 -c '$S' d3/ledger.jsonl 0; tail -1 \$(ls -t *.log | head -1) | cut -c1-70; echo workers \$(ps -eo args | grep -c '[s]pawn_main')" 2>&1 | tr '\n' ' ')"
done
