"""V3.1-4 final TEST tables (everything frozen on validation; nothing tuned here).  Torch-free: selection files + verify caches + snapshot labels.
  budget : V3 primary (task cVAE q2init_all + V3 D + frozen rule, M=4) s0 at B = 128 / 512 / 2,048 / 4,096 vs V2 iterative s0 at 3 / 12 / 48 expansions
  goal   : matched goal-ablation task cVAEs (V3.1-A q2init_all / _nogoal / _notask) + frozen V3 D s<seed>, B=4,096, seeds 0-2
  seeds  : coupled V3 D vs uncoupled E / order-invariant G / DIRECT, seeds 0-2 (s0 = V3-6 run; s1-2 = V3.1-4 runs)
Per arm: per-seed task / K1-K3 / repair / no-op / abstain from physically verified top-1 selections (unverified counted, never imputed), seed mean +- SD,
median latency / scored candidates where recorded; paired root-cluster bootstrap (2,000) on seed-averaged per-root outcomes vs the named reference.
usage: v314_test_table.py SNAPSHOT_DIR V314_DIR V36_SLIM_DIR OUT_JSON CACHES_2D CACHES_3D   (CACHES_* = comma lists)"""
import collections, json, sys
from pathlib import Path
import numpy as np

SNAP, V314, V36, OUT = map(Path, sys.argv[1:5])
CACHES = {"2d": sys.argv[5].split(","), "3d": sys.argv[6].split(",")}
P = "task:q2init_all-S1_M4_B4096"


def jl(p):
    return [json.loads(l) for l in open(p)] if Path(p).exists() else []


def groups(d):
    full = lambda st, f: V314 / "full" / st / d / f"{f}_test.jsonl"  # noqa: E731
    return {
        "budget": ("V2 iterative exp12", [
            *[(f"V3 primary B={B}", [full("v3_1_4", f"v3D_task:q2init_all-S1_M4_B{B}_s0")]) for B in (128, 512, 2048, 4096)],
            *[(f"V2 iterative exp{e}", [full("v3_1_4", f"v2_iterative_exp{e}_s0")]) for e in (3, 12, 48)]]),
        "goal": ("q2init_all", [(v, [full("v3_1_4_goal", f"v3D_task:{v}-S1_M4_B4096_s{s}") for s in (0, 1, 2)])
                                for v in ("q2init_all", "q2init_all_nogoal", "q2init_all_notask")]),
        "seeds": ("V3 D (coupled, primary)", [("V3 D (coupled, primary)", [full("v3_1_4", f"v3D_{P}_s{s}") for s in (0, 1, 2)])] +
                  [(n, [V36 / d / f"{a}_{P}_s0_test.jsonl"] + [full("v3_1_4_seeds", f"{a}_{P}_s{s}") for s in (1, 2)])
                   for a, n in (("v3E", "E (uncoupled)"), ("v3G", "G (order-invariant)"), ("v3DIRECT", "DIRECT"))])}


res = {}
for d in ("2d", "3d"):
    rows = {r["root_id"]: r for r in jl(SNAP / f"data{d}.jsonl") if r["split"] == "test"}
    ver = {}
    for p in CACHES[d]:
        for v in jl(p):
            for x in v["results"]:
                xr, yr = x["x"] or {}, x["y"] or {}
                xv, yv = xr.get("x"), yr.get("y")
                if d == "3d":
                    xv = xv if xr.get("resolution", "EVALUATED") == "EVALUATED" else None
                    yv = yv if yr.get("resolution", "EVALUATED") == "EVALUATED" else None
                ver[(v["root"], json.dumps(x["seq"]))] = int(xv == 1 and yv == 1) if xv in (0, 1) and yv in (0, 1) else None
    res[d] = {}
    for gname, (ref, arms) in groups(d).items():
        R, per = {}, {}
        for name, files in arms:
            missing = [str(f) for f in files if not Path(f).exists()]
            if missing:
                R[name] = {"missing": missing}
                continue
            seeds, acc, lat, nsc = [], collections.defaultdict(lambda: collections.defaultdict(list)), [], []
            for f in files:
                S, unv = collections.defaultdict(list), 0
                for r in jl(f):
                    rt, sel = r["root_id"], r["selected_ordered_seq"]
                    mk, K = rows[rt]["masks"], rows[rt]["K_legacy"]
                    v = ver.get((rt, json.dumps(sel))) if sel else None
                    unv += bool(sel) and v is None
                    succ = float(bool(sel) and v == 1)
                    for key, on, val in (("task", mk["eval_task"], succ), ("repair", mk["eval_repair"], float(succ and K.isdigit() and len(sel) == int(K))),
                                         ("noop", mk["eval_noop"], float(r["decision"] == "NOOP")),
                                         ("abstain", mk["eval_abstain"], float(r["decision"] == "ABSTAIN"))):
                        if on:
                            S[key].append(val); acc[key][rt].append(val)
                    if mk["eval_task"]:
                        S["task_K" + K].append(succ)
                    if "wall_s" in r:
                        lat.append(r["wall_s"]["total"]); nsc.append(r["candidate_budget"]["n_scored"])
                seeds.append({k: float(np.mean(v)) for k, v in S.items()} | {"unverified": unv, "n_task": len(S["task"])})
            keys = ("task", "task_K1", "task_K2", "task_K3", "repair", "noop", "abstain")
            R[name] = {"seeds": len(files), "per_seed": seeds, **{k: [float(np.mean([s[k] for s in seeds])), float(np.std([s[k] for s in seeds]))] for k in keys},
                       "unverified_total": int(sum(s["unverified"] for s in seeds))}
            if lat:
                R[name] |= {"latency_s_median": float(np.median(lat)), "n_scored_median": float(np.median(nsc)), "n_scored_mean": float(np.mean(nsc))}
            per[name] = {k: {rt: float(np.mean(v)) for rt, v in dd.items()} for k, dd in acc.items()}
        g = np.random.default_rng(0)
        for name in per:
            if name == ref or ref not in per:
                continue
            for key in ("task", "abstain"):
                c = sorted(set(per[name][key]) & set(per[ref][key]))
                x = np.array([per[name][key][r] - per[ref][key][r] for r in c])
                bs = [x[g.integers(0, len(x), len(x))].mean() for _ in range(2000)]
                R[name][f"delta_{key}_vs_ref"] = {"ref": ref, "delta": float(x.mean()), "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))], "roots": len(c)}
        res[d][gname] = R
        print(f"===== {d} {gname} (ref: {ref})")
        for name, x in R.items():
            if "missing" in x:
                print(f"  {name:28s} MISSING {x['missing']}"); continue
            dl = x.get("delta_task_vs_ref")
            print(f"  {name:28s} task {100*x['task'][0]:.1f}+-{100*x['task'][1]:.1f}  K {100*x['task_K1'][0]:.0f}/{100*x['task_K2'][0]:.0f}/{100*x['task_K3'][0]:.0f}"
                  f"  rep {100*x['repair'][0]:.1f}  noop {100*x['noop'][0]:.1f}  abst {100*x['abstain'][0]:.1f}  unv {x['unverified_total']}"
                  + (f"  lat {x['latency_s_median']:.2f}s  nsc {x['n_scored_median']:.0f}" if "latency_s_median" in x else "")
                  + (f"  d {100*dl['delta']:+.1f} [{100*dl['ci95'][0]:+.1f}, {100*dl['ci95'][1]:+.1f}]" if dl else ""))
OUT.write_text(json.dumps(res, indent=1))
