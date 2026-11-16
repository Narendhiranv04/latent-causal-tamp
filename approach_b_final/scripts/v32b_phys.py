"""V3.2 Phase B: physical outcomes of the FROZEN V3 model (seed 0, task cVAE q2init_all, V3 D, frozen rule) on VALIDATION, capped M4 / B=4,096
(construct.run_root) vs exact exhaustive M4 / M5 / M6 (shared M6 pass, nested prefixes).  Torch-free.  Labels come only from physical verify
records (any number of cache files); an unlabelled selected repair is UNKNOWN and is never counted as a failure: task success is reported as
[lower, upper] bounds plus the decided-only rate, and the point estimate is exact only when UNKNOWN = 0.
Outcome classes per selected repair: SUCCESS (X=1, Y=1), FAIL_Y (Y=0), FAIL_X (Y=1, X=0), UNKNOWN (missing / unresolved X or Y).
usage: v32b_phys.py SNAPSHOT_DIR V32A_RUN_DIR OUT_JSON CACHE_GLOB_2D CACHE_GLOB_3D"""
import collections, glob, json, sys
from pathlib import Path
import numpy as np

RULE = {"noop_gate": 0.5, "eta": 0.3, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}
GRID = [{"noop_gate": ng, "eta": e, "alpha": a, "beta": b, "gamma": g} for ng in (0.5, 0.8) for e in (0.0, 0.1, 0.3) for a in (0.0, 0.5)
        for b in (0.0, 0.1) for g in (0.0, 0.5, 2.0)]                          # = evaluate.GRID
RI = GRID.index(RULE)


def jl(p):
    return [json.loads(l) for l in open(p)]


def labels(d, pattern):
    lab = {}
    for p in sorted(glob.glob(pattern)):
        for l in open(p):
            try:
                v = json.loads(l)
            except json.JSONDecodeError:
                continue
            for x in v["results"]:
                xr, yr = x["x"] or {}, x["y"] or {}
                xv, yv = xr.get("x"), yr.get("y")
                if d == "3d":
                    xv = xv if xr.get("resolution", "EVALUATED") == "EVALUATED" else None
                    yv = yv if yr.get("resolution", "EVALUATED") == "EVALUATED" else None
                k = (v["root"], json.dumps(x["seq"]))
                xv, yv = (xv if xv in (0, 1) else None), (yv if yv in (0, 1) else None)
                old = lab.get(k)
                if old is not None and None not in old and None not in (xv, yv) and old != (xv, yv):
                    raise SystemExit(f"CONFLICT {k}: {old} vs {(xv, yv)}")      # conflicting decided labels -> quarantine, never vote
                if old is None or (None in old and None not in (xv, yv)):
                    lab[k] = (xv, yv)
    return lab


def outcome(sel, lab, root):
    if sel is None:
        return "ABSTAIN"
    if sel == []:
        return "NOOP"
    xv, yv = lab.get((root, json.dumps(sel)), (None, None))
    if yv == 0:
        return "FAIL_Y"
    if yv == 1 and xv == 1:
        return "SUCCESS"
    if yv == 1 and xv == 0:
        return "FAIL_X"
    return "UNKNOWN"


def boot(pairs, n=2000, seed=0):
    x = np.array(pairs, float)
    g = np.random.default_rng(seed)
    bs = [x[g.integers(0, len(x), len(x))].mean() for _ in range(n)]
    return [float(x.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]


def main():
    SNAP, RUN, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    GLOB = {"2d": sys.argv[4], "3d": sys.argv[5]}
    res = {}
    for d in ("2d", "3d"):
        rows = {r["root_id"]: r for r in jl(SNAP / f"data{d}.jsonl") if r["split"] == "val"}
        lab = labels(d, GLOB[d])
        capped = {r["root_id"]: r["selected"] for r in jl(RUN / d / "old_M4_B4096_val.jsonl")}
        ex = {r["root_id"]: r for r in jl(RUN / d / "ex_M6_val.jsonl")}
        assert set(capped) == set(ex) == set(rows), d
        arms = {"capped_M4_B4096": {k: capped[k] for k in rows}}
        for M in ("4", "5", "6"):
            dec = {k: ex[k]["per_M"][M]["decisions"][RI] for k in rows}
            arms[f"exhaustive_M{M}"] = {k: (None if v is None else v["seq"]) for k, v in dec.items()}
        R, succ = {}, {}
        for a, sel in arms.items():
            oc = {k: outcome(sel[k], lab, k) for k in rows}
            st = collections.defaultdict(collections.Counter)
            for k, o in oc.items():
                mk, K = rows[k]["masks"], rows[k]["K_legacy"]
                st["all"][o] += 1
                if mk["eval_task"]:
                    st["task"][o] += 1; st[f"task_K{K}"][o] += 1
                if mk["eval_noop"]:
                    st["noop_eval"][o] += 1
                if mk["eval_abstain"]:
                    st["abstain_eval"][o] += 1
            def rate(c, ok="SUCCESS"):
                n = sum(c.values()); u = c["UNKNOWN"]
                return {"n": n, "success": c[ok], "unknown": u, "lower": c[ok] / n if n else None, "upper": (c[ok] + u) / n if n else None,
                        "decided_only": c[ok] / (n - u) if n - u else None}
            R[a] = {"outcomes": {k: dict(v) for k, v in st.items()},
                    "task": rate(st["task"]), **{f"task_K{K}": rate(st[f"task_K{K}"]) for K in "123"},
                    "noop_correct": rate(st["noop_eval"], "NOOP"), "abstain_correct": rate(st["abstain_eval"], "ABSTAIN"),
                    "none_roots_new_verified_success": st["abstain_eval"]["SUCCESS"], "none_roots_unknown": st["abstain_eval"]["UNKNOWN"],
                    "unknown_selected_repairs": st["all"]["UNKNOWN"],
                    "changed_vs_capped": sum(sel[k] != arms["capped_M4_B4096"][k] for k in rows)}
            succ[a] = {k: oc[k] for k in rows}
        for a in list(arms)[1:]:                                                   # root-paired deltas vs capped (task roots; exact only if no UNKNOWN)
            tr = [k for k in rows if rows[k]["masks"]["eval_task"]]
            if all(succ[a][k] != "UNKNOWN" and succ["capped_M4_B4096"][k] != "UNKNOWN" for k in tr):
                R[a]["delta_task_vs_capped"] = boot([(succ[a][k] == "SUCCESS") - (succ["capped_M4_B4096"][k] == "SUCCESS") for k in tr])
                ar = [k for k in rows if rows[k]["masks"]["eval_abstain"]]
                R[a]["delta_abstain_vs_capped"] = boot([(succ[a][k] == "ABSTAIN") - (succ["capped_M4_B4096"][k] == "ABSTAIN") for k in ar])
        res[d] = R
        print("=====", d, "roots", len(rows), "labels", len(lab))
        for a, x in R.items():
            t = x["task"]; dl = x.get("delta_task_vs_capped")
            print(f"  {a:16s} task {100*t['lower']:.1f}..{100*t['upper']:.1f} (unk {t['unknown']})  K1/2/3 " +
                  "/".join(f"{100*x[f'task_K{K}']['lower']:.0f}" for K in "123") +
                  f"  noop {100*x['noop_correct']['lower']:.1f}  abst {100*x['abstain_correct']['lower']:.1f}  NONE->verified succ {x['none_roots_new_verified_success']}"
                  f"  changed {x['changed_vs_capped']}" + (f"  d {100*dl[0]:+.1f} [{100*dl[1]:+.1f}, {100*dl[2]:+.1f}]" if dl else ""))
    OUT.write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
