"""V3-6 final TEST table (rules frozen on validation; nothing tuned here).  Per arm: seed-averaged per-root outcomes from the physically verified
selections -> task / K1-K3 / repair / no-op / abstain, budgets, latency; paired root-cluster bootstrap (2,000) vs the primary arm and vs V2 iterative."""
import collections, json, os, sys
from pathlib import Path
import numpy as np
ABF, V3 = Path(os.environ["ABF_ROOT"]), Path(os.environ["V3OUT"])
P = "task:q2init_all-S1_M4_B4096"
ARMS = [("V3 primary: task cVAE + V3 D (coupled)", [f"v3D_{P}_s{s}_test" for s in (0, 1, 2)]),
        ("Old V2 iterative search (Q2 cVAE + V2 D)", [f"v2_iterative_s{s}_test" for s in (0, 1, 2)]),
        ("E: task cVAE + V2 D (frozen)", [f"v2frozen_{P}_s0_test"]),
        ("E: Q2 cVAE + V3 D", ["v3D_M4_B4096_s0_test"]),
        ("E: Q2 cVAE + V2 D (V3-1 direct)", ["v2frozen_M4_B4096_s0_test"]),
        ("F: task cVAE + V3 E (uncoupled)", [f"v3E_{P}_s0_test"]),
        ("F: task cVAE + V3 G (order-invariant)", [f"v3G_{P}_s0_test"]),
        ("F: task cVAE + V3 DIRECT", [f"v3DIRECT_{P}_s0_test"]),
        ("Control: uniform + V3 D", ["v3D_uniform-S2_M4_B4096_s0_test"]),
        ("Control: band-stratified + V3 D", ["v3D_stratified-S0_M4_B4096_s0_test"]),
        ("Control: goal-ablated repair cVAE + V3 D", ["v3D_task:goalablated_one-S1_M4_B4096_s0_test"])]


def jl(p):
    return [json.loads(l) for l in open(p)] if Path(p).exists() else []


def main():
    out = {}
    for dom in ("2d", "3d"):
        rows = {r["root_id"]: r for r in map(json.loads, open(ABF / "snapshot/abf_9de85710c2a7103f" / f"data{dom}.jsonl")) if r["split"] == "test"}
        ver = {}
        for p in (ABF / f"runs/v2/p5_{dom}/verify.jsonl", V3 / f"verify_{dom}.jsonl", V3 / f"verify_{dom}_laptop.jsonl", V3 / f"verify_{dom}_gvlab.jsonl"):
            for v in jl(p):
                for x in v["results"]:
                    xr, yr = x["x"] or {}, x["y"] or {}
                    xv, yv = xr.get("x"), yr.get("y")
                    if dom == "3d":
                        xv = xv if xr.get("resolution", "EVALUATED") == "EVALUATED" else None
                        yv = yv if yr.get("resolution", "EVALUATED") == "EVALUATED" else None
                    ver[(v["root"], json.dumps(x["seq"]))] = int(xv == 1 and yv == 1) if xv in (0, 1) and yv in (0, 1) else None
        per, res = {}, {}
        for name, files in ARMS:
            recs = [jl(V3 / "v3_6" / dom / f"{f}.jsonl") for f in files]
            if not all(recs):
                continue
            acc = collections.defaultdict(lambda: collections.defaultdict(list))
            unver, lat, nsc = 0, [], []
            for rs in recs:
                for r in rs:
                    rt, sel, mk = r["root_id"], r["selected_ordered_seq"], rows[r["root_id"]]["masks"]
                    v = ver.get((rt, json.dumps(sel))) if sel else None
                    unver += bool(sel) and v is None
                    if os.environ.get("INTERIM") and sel and v is None:
                        continue                                           # interim view: pending verification excluded, never counted as failure
                    succ = float(bool(sel) and v == 1)
                    if mk["eval_task"]:
                        acc["task"][rt].append(succ)
                    if mk["eval_repair"]:
                        acc["repair"][rt].append(float(succ and len(sel) == int(rows[rt]["K_legacy"])))
                    if mk["eval_noop"]:
                        acc["noop"][rt].append(float(r["decision"] == "NOOP"))
                    if mk["eval_abstain"]:
                        acc["abstain"][rt].append(float(r["decision"] == "ABSTAIN"))
                    lat.append(r["wall_s"]["total"]); nsc.append(r["candidate_budget"]["n_scored"])
            m = {k: {rt: float(np.mean(v)) for rt, v in d.items()} for k, d in acc.items()}
            per[name] = m
            res[name] = {"seeds": len(files), **{k: float(np.mean(list(d.values()))) for k, d in m.items()}, "n_task": len(m["task"]),
                         **{f"task_K{K}": float(np.mean([v for rt, v in m["task"].items() if rows[rt]["K_legacy"] == K])) for K in "123"},
                         "unverified": unver, "latency_s_median": float(np.median(lat)), "n_scored_median": float(np.median(nsc))}
        g = np.random.default_rng(0)
        ref = ARMS[0][0]
        for name in res:
            for base in (ref, ARMS[1][0]):
                if name == base or base not in per:
                    continue
                for key in ("task", "abstain"):
                    c = sorted(set(per[name][key]) & set(per[base][key]))
                    d = np.array([per[name][key][r] - per[base][key][r] for r in c])
                    bs = [d[g.integers(0, len(d), len(d))].mean() for _ in range(2000)]
                    res[name][f"delta_{key}_vs_{'primary' if base == ref else 'v2iter'}"] = [float(d.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
        out[dom] = res
        print("=====", dom)
        for name, r in res.items():
            dp, dv = r.get("delta_task_vs_primary"), r.get("delta_task_vs_v2iter")
            f = lambda t: "—" if not t else f"{100 * t[0]:+.1f} [{100 * t[1]:+.1f}, {100 * t[2]:+.1f}]"  # noqa: E731
            print(f"{name:45s} task {100 * r['task']:.1f}  K {100 * r['task_K1']:.0f}/{100 * r['task_K2']:.0f}/{100 * r['task_K3']:.0f}  rep {100 * r['repair']:.1f}  "
                  f"noop {100 * r['noop']:.1f}  abst {100 * r['abstain']:.1f}  unv {r['unverified']}  lat {r['latency_s_median']:.2f}  vsP {f(dp)}  vsV2 {f(dv)}")
    (V3 / "v3_6" / ("TABLE_TEST_INTERIM.json" if os.environ.get("INTERIM") else "TABLE_TEST.json")).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
