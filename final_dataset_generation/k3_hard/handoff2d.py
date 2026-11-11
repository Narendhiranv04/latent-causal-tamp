#!/usr/bin/env python3
"""Hand the unstarted TAIL of the laptop's 2D queue to gvlab (laptop side; run only after gvlab passed 2D parity).
Remaining = bulk2d jobs not in the laptop ledger.  A safety margin of in-flight / prefetched jobs at the head stays on the laptop.
gvlab share = remaining * G / (G + L) with G, L = parallel workers x relative speed.  Writes d2/claims_other_host.json (the laptop
workers skip those ids) and handoff2d_gvlab_jobs.json (to copy to gvlab).  Idempotent: re-running only adds jobs still unstarted.
  handoff2d.py GVLAB_WORKERS [GVLAB_SPEED_REL=1.0] [MARGIN=80]"""
import json, sys
from pathlib import Path

H = Path(__file__).resolve().parent
G = int(sys.argv[1]) * (float(sys.argv[2]) if len(sys.argv) > 2 else 1.0)
margin = int(sys.argv[3]) if len(sys.argv) > 3 else 80
jobs = json.loads((H / "bulk2d.json").read_text())
led = [json.loads(l) for l in (H / "d2/ledger.jsonl").read_text().splitlines()]
done = {r["job_id"] for r in led if "skipped" not in r and not str(r.get("reason", "")).startswith("ADMIN_STOP")}
cf = H / "d2/claims_other_host.json"
claimed = set(json.loads(cf.read_text())) if cf.exists() else set()
rem = [j for j in jobs if j["job_id"] not in done and j["job_id"] not in claimed]
L = 27.0
n = max(0, int(round((len(rem) - margin) * G / (G + L)))) if len(rem) > margin else 0
give = rem[len(rem) - n:] if n else []
cf.write_text(json.dumps(sorted(claimed | {j["job_id"] for j in give})))
prev = json.loads((H / "handoff2d_gvlab_jobs.json").read_text()) if (H / "handoff2d_gvlab_jobs.json").exists() else []
(H / "handoff2d_gvlab_jobs.json").write_text(json.dumps(prev + give))
print(f"remaining {len(rem)} (unstarted, unclaimed); handed to gvlab now {len(give)}; total claimed {len(claimed) + len(give)}")
