"""V3.1-A physical arm (validation): matched goal-ablation task cVAEs (v3_1a: q2init_all / _nogoal / _notask, seeds 0-2) + FROZEN V3 D s<seed>
+ frozen V3 rule, M=4, B=4,096.  Torch-free: slim selection files + verify caches + snapshot labels.  Physically verified top-1 task success
(K1-K3), repair (exact certified K), correct no-op (K0) and abstention (NONE); per-variant seed mean +- SD; paired root-cluster bootstrap
(2,000 resamples) on per-root seed-averaged task success vs q2init_all (same roots).  Unverified selections are counted and never imputed.
usage: v31a_phys_table.py SNAPSHOT_DIR SLIM_DIR OUT_JSON CACHE[,CACHE...]"""
import collections, glob, json, sys
from pathlib import Path
import numpy as np

SNAP, SLIM, OUT, CACHES = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4].split(",")
VARS = ("q2init_all", "q2init_all_nogoal", "q2init_all_notask")


def jl(p):
    return [json.loads(l) for l in open(p)] if Path(p).exists() else []


res = {}
for d in ("2d", "3d"):
    rows = {r["root_id"]: r for r in jl(SNAP / f"data{d}.jsonl") if r["split"] == "val"}
    ver = {}
    for p in CACHES:
        if f"_{d}" not in Path(p).name and f"{d}_" not in Path(p).name:
            continue
        for v in jl(p):
            for x in v["results"]:
                xr, yr = x["x"] or {}, x["y"] or {}
                xv, yv = xr.get("x"), yr.get("y")
                if d == "3d":
                    xv = xv if xr.get("resolution", "EVALUATED") == "EVALUATED" else None
                    yv = yv if yr.get("resolution", "EVALUATED") == "EVALUATED" else None
                ver[(v["root"], json.dumps(x["seq"]))] = int(xv == 1 and yv == 1) if xv in (0, 1) and yv in (0, 1) else None
    R, per_root = {}, {}
    for var in VARS:
        seeds = []
        for s in (0, 1, 2):
            f = SLIM / d / f"v3D_task:{var}-S1_M4_B4096_s{s}_val.jsonl"
            S = collections.defaultdict(list); unv = 0
            for r in jl(f):
                row = rows[r["root_id"]]; mk, K = row["masks"], row["K_legacy"]; sel = r["selected_ordered_seq"]
                v = ver.get((r["root_id"], json.dumps(sel))) if sel else None
                succ = bool(sel) and v == 1
                if sel and v is None:
                    unv += 1
                if mk["eval_task"]:
                    S["task"].append(succ); S["task_K" + K].append(succ)
                    per_root.setdefault(var, collections.defaultdict(list))[r["root_id"]].append(float(succ))
                if mk["eval_repair"]:
                    S["repair"].append(succ and len(sel) == int(K))
                if mk["eval_noop"]:
                    S["noop"].append(r["decision"] == "NOOP")
                if mk["eval_abstain"]:
                    S["abstain"].append(r["decision"] == "ABSTAIN")
            seeds.append({k: float(np.mean(v)) for k, v in S.items()} | {"unverified": unv, "roots": sum(len(v) for k, v in S.items() if k in ("task",))})
        keys = ("task", "task_K1", "task_K2", "task_K3", "repair", "noop", "abstain")
        R[var] = {"per_seed": seeds, **{k: [float(np.mean([x[k] for x in seeds])), float(np.std([x[k] for x in seeds]))] for k in keys},
                  "unverified_total": int(sum(x["unverified"] for x in seeds))}
    g = np.random.default_rng(0)
    ref = {k: np.mean(v) for k, v in per_root["q2init_all"].items()}
    for var in VARS[1:]:
        cur = {k: np.mean(v) for k, v in per_root[var].items()}
        common = sorted(set(ref) & set(cur))
        x = np.array([cur[k] - ref[k] for k in common])
        bs = [x[g.integers(0, len(x), len(x))].mean() for _ in range(2000)]
        R[var]["task_delta_vs_q2init_all"] = {"delta": float(x.mean()), "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))], "roots": len(x)}
    res[d] = R
    print("=====", d)
    for var, x in R.items():
        dl = x.get("task_delta_vs_q2init_all")
        print(f"  {var:20s} task {100*x['task'][0]:.1f}+-{100*x['task'][1]:.1f}  K1/K2/K3 {100*x['task_K1'][0]:.0f}/{100*x['task_K2'][0]:.0f}/{100*x['task_K3'][0]:.0f}"
              f"  repair {100*x['repair'][0]:.1f}  noop {100*x['noop'][0]:.1f}  abstain {100*x['abstain'][0]:.1f}  unverified {x['unverified_total']}"
              + (f"  delta {100*dl['delta']:+.1f} [{100*dl['ci95'][0]:+.1f}, {100*dl['ci95'][1]:+.1f}]" if dl else ""))
OUT.write_text(json.dumps(res, indent=1))
