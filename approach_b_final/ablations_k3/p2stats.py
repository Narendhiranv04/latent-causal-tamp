import json, os, statistics as st
import numpy as np
K3 = os.environ["K3"]; out = {}
pc = lambda v, q: float(np.percentile(v, q))
for d in ("2d", "3d"):
    for a in ("FULL_s0", "UNIFORM4_r0", "M1", "C1_r0"):
        R = [json.loads(l) for l in open(f"{K3}/runs/predictions/{a}/pilot_{d}.jsonl")]
        ns = [r["n_scored"] for r in R]; t = [r["timing_s"]["total"] for r in R]; g = [r["gpu_peak_mib"] for r in R]; nm = [len(r["proposals"]) for r in R]
        out[f"{a}|{d}"] = {"n": len(R), "n_scored": {"mean": st.mean(ns), "p50": pc(ns, 50), "p90": pc(ns, 90), "p99": pc(ns, 99), "max": max(ns)},
                           "latency_s": {"mean": round(st.mean(t), 3), "p90": pc(t, 90), "p99": pc(t, 99), "max": max(t)}, "gpu_peak_mib_max": max(g),
                           "eligible_objects": {"p50": pc(nm, 50), "p90": pc(nm, 90), "p99": pc(nm, 99), "max": max(nm)},
                           "decisions": {k: sum(r["decision"] == k for r in R) for k in ("REPAIR", "NOOP", "ABSTAIN")}}
for d in ("2d", "3d"):
    V = [json.loads(l) for l in open(f"{K3}/runs/verifier_cache/verify_{d}.jsonl")]
    nq = sum(len(v["results"]) for v in V); cpu = sum(v["cpu_s"] for v in V)
    out[f"teacher|{d}"] = {"roots": len(V), "queries": nq, "cpu_s": round(cpu, 1), "cpu_s_per_query": round(cpu / nq, 2)}
json.dump(out, open(f"{K3}/runs/manifests/P2_PILOT_STATS.json", "w"), indent=1)
for k, v in out.items(): print(k, json.dumps(v))
