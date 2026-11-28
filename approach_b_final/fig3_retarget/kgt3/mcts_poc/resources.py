#!/usr/bin/env python3
"""RESOURCES.json for the GA-MCTS PoC (separate from R10's budget): sums out/resources.jsonl (dev_run.sh acct entries).
    python3 resources.py /home/projects/long-horizon/naren_workspace/mcts_poc"""
import json, sys
from pathlib import Path
M = Path(sys.argv[1])
R = [json.loads(l) for l in open(M / "out" / "resources.jsonl")] if (M / "out" / "resources.jsonl").exists() else []
out = {"budget": {"cpu_h": 15.0, "gpu_process_h": 4.0}, "host": "gvlab2 (CPUs 12-19, CUDA 0)",
       "cpu_h": round(sum(r["cpu_s"] for r in R) / 3600, 3), "gpu_process_h": round(sum(r["wall_s"] for r in R if r["gpu"]) / 3600, 3),
       "entries": R, "note": "cpu_h = user+sys of every accounted process (GPU processes included); gpu_process_h = wall of GPU processes"}
(M / "RESOURCES.json").write_text(json.dumps(out, indent=1)); print(json.dumps({k: out[k] for k in ("cpu_h", "gpu_process_h")}))
