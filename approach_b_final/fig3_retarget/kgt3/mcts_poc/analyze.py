#!/usr/bin/env python3
"""GA-MCTS BENCH_COMP analysis (evaluator; after physical verification).  All predeclared budgets are reported; no budget is chosen post hoc.
Primary (MCTS_PROTOCOL_FREEZE.json): verified success of GA-MCTS seed 0 vs GA at EACH budget 5/10/20/30/60/180 s, exact two-sided sign test
over discordant roots, Holm over the six budgets, 95% CI of the paired difference by family bootstrap (2,000 resamples, seed 0).
Secondary: success with Wilson CI per method; long (4-5 action) successes; success by L_ref; selected-plan learned energy and regret vs the
per-root best learned energy over every GA / GA-MCTS method; decisions; overruns; time to first incumbent / to final incumbent (traces);
seed robustness (s1, s2 vs GA; s0 vs s1 / s2); H3 / REC reference rows; normalized area under success vs log-budget (paired bootstrap CI).
    $PY3D analyze.py EVAL_DIR  -> EVAL_DIR/EVAL_RESULTS.json + EVAL_RESULTS.md     (env R10_PRIVATE, R10_PUBLIC, R10_ARCHIVE_DIRS)"""
from __future__ import annotations

import collections, json, math, os, statistics, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
KG = HERE.parent
sys.path[:0] = [str(HERE), str(KG), str(KG.parent), str(KG.parent.parent)]
import evaljobs as EJ  # noqa: E402

BUDGETS, SEEDS = EJ.BUDGETS, EJ.SEEDS


def sign_p(w, l):
    n = w + l
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(w, l) + 1)) / 2 ** n)


def holm(ps):
    o = sorted(range(len(ps)), key=lambda i: ps[i]); adj, run = [0.0] * len(ps), 0.0
    for r, i in enumerate(o):
        run = max(run, min(1.0, (len(ps) - r) * ps[i])); adj[i] = run
    return adj


def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n; d = 1 + z * z / n
    return [(p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d, (p + z * z / (2 * n) + z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d]


def boot(fam, pairs, n=2000, seed=0, stat=None):
    """pairs: {root: (a, b)}; fam: {root: family}; 95% CI of mean(b - a) (x100 for success) resampling families."""
    g = np.random.default_rng(seed)
    F = collections.defaultdict(list)
    for r, v in pairs.items():
        F[fam[r]].append(v)
    keys = sorted(F)
    arr = [np.array(F[k], float) for k in keys]
    bs = []
    for _ in range(n):
        s = np.concatenate([arr[i] for i in g.integers(0, len(keys), len(keys))])
        bs.append(100 * (s[:, 1].mean() - s[:, 0].mean()))
    return [round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2)]


def auc(succ_by_b):
    """normalized area under success(b) over log(b), b in BUDGETS (trapezoid)."""
    x = [math.log(b) for b in BUDGETS]; y = [succ_by_b[b] for b in BUDGETS]
    return sum((x[i + 1] - x[i]) * (y[i] + y[i + 1]) / 2 for i in range(len(x) - 1)) / (x[-1] - x[0])


def main(ev):
    import r6
    ev = Path(ev)
    P = {r["root_id"]: r["methods"] for r in EJ.jl(ev / "PLANS_EVAL.jsonl")}
    assert EJ.sha(ev / "PLANS_EVAL.jsonl") == (ev / "PLANS_EVAL.jsonl.SEAL").read_text().strip(), "plans not sealed"
    sel = json.loads((ev / "selection_eval.json").read_text())
    R = {r["key"]: r for r in EJ.jl(ev / "phys_eval.jsonl")}
    A = {v["src"]: v["rec"] for v in r6.archive_r10().values()}
    Pv = {r["root_id"]: r for r in EJ.jl(os.environ["R10_PRIVATE"])}
    meta = {rid: m for rid, _, m in r6.roots("r10comp")}
    fam = {rid: str(Pv[rid].get("r10_family") or Pv[rid].get("r10_template") or Pv[rid].get("family") or rid) for rid in P}
    byjob = {}
    for s in sel:
        if s["status"] == "QUEUED" and s["job"] in R and not R[s["job"]].get("censored"):
            byjob[s["job"]] = {**r6.res("3d", R[s["job"]]), "src": "NEW"}
        elif s["status"] == "REUSED":
            byjob[s["job"]] = {**r6.res("3d", A[s["src"]]), "src": s["src"]}
    per = collections.defaultdict(dict)
    for s in sel:
        m = P[s["root_id"]][s["method"]]
        if s["status"] == "NO_REPAIR":
            v = {"succ": False, "outcome": "NO_REPAIR:" + str(s["decision"])}
        elif s.get("job") not in byjob:
            v = {"succ": False, "outcome": "UNRUN_OR_CENSORED"}
        else:
            v = dict(byjob[s["job"]]); v["outcome"] = v.get("x_outcome")
        v.update(L_pred=len(s["seq"] or []), E=m.get("E"), decision=m["decision"], overrun_s=m.get("overrun_s"), L_ref=meta[s["root_id"]]["L_ref"])
        per[s["root_id"]][s["method"]] = v
    roots = sorted(per)
    n = len(roots)
    labs = EJ.methods()
    best_E = {r: min([per[r][l]["E"] for l in labs if l not in ("H3", "REC") and per[r][l]["E"] is not None and per[r][l]["decision"] == "REPAIR"] or [None], key=lambda x: (x is None, x)) for r in roots}
    summ = {}
    for l in labs:
        rr = [per[r][l] for r in roots]
        k = sum(x["succ"] for x in rr)
        reg = [per[r][l]["E"] - best_E[r] for r in roots if per[r][l]["E"] is not None and best_E[r] is not None and per[r][l]["decision"] == "REPAIR"]
        ov = [x["overrun_s"] for x in rr if x.get("overrun_s") is not None]
        summ[l] = {"n": n, "succ": k, "rate": k / n if n else None, "wilson95": wilson(k, n), "succ_long": sum(x["succ"] and x["L_pred"] > 3 for x in rr),
                   "by_L_ref": {L: [sum(x["succ"] for x in rr if x["L_ref"] == L), sum(1 for x in rr if x["L_ref"] == L)] for L in sorted({x["L_ref"] for x in rr})},
                   "decisions": dict(collections.Counter(x["decision"] for x in rr)), "outcomes": dict(collections.Counter(str(x["outcome"]) for x in rr)),
                   "E_median": statistics.median([x["E"] for x in rr if x["E"] is not None]) if any(x["E"] is not None for x in rr) else None,
                   "regret_mean": statistics.mean(reg) if reg else None, "regret_median": statistics.median(reg) if reg else None,
                   "overrun_max_s": max(ov) if ov else None, "overrun_n_gt0": sum(o > 0 for o in ov), "L_pred": dict(collections.Counter(x["L_pred"] for x in rr))}

    def paired(a, b):
        w = sum(per[r][b]["succ"] and not per[r][a]["succ"] for r in roots); lo = sum(per[r][a]["succ"] and not per[r][b]["succ"] for r in roots)
        return {"a": a, "b": b, "b_wins": w, "b_losses": lo, "p_sign": sign_p(w, lo), "diff_pp": 100 * (summ[b]["succ"] - summ[a]["succ"]) / n,
                "ci95_family_bootstrap_pp": boot(fam, {r: (per[r][a]["succ"], per[r][b]["succ"]) for r in roots})}
    prim = [paired(f"GA@{b}", f"GA-MCTS-s0@{b}") for b in BUDGETS]
    for p, h in zip(prim, holm([p["p_sign"] for p in prim])):
        p["p_holm"] = h
    sec = {f"seed{s}": [paired(f"GA@{b}", f"GA-MCTS-s{s}@{b}") for b in BUDGETS] for s in (1, 2)}
    sec["REC_vs_MCTS_s0"] = [paired("REC", f"GA-MCTS-s0@{b}") for b in BUDGETS]
    sec["H3_vs_MCTS_s0"] = [paired("H3", f"GA-MCTS-s0@{b}") for b in BUDGETS]
    sec["seed_agreement_s0_s1_s2"] = {b: sum(len({per[r][f"GA-MCTS-s{s}@{b}"]["succ"] for s in SEEDS}) == 1 for r in roots) / n for b in BUDGETS}
    # anytime summaries
    au = {}
    for lab in ["GA"] + [f"GA-MCTS-s{s}" for s in SEEDS]:
        au[lab] = auc({b: summ[f"{lab}@{b}"]["rate"] for b in BUDGETS})
    gb = np.random.default_rng(0); keys = sorted(set(fam.values())); byf = collections.defaultdict(list)
    for r in roots:
        byf[fam[r]].append(r)
    bs = []
    for _ in range(2000):
        rs = [r for i in gb.integers(0, len(keys), len(keys)) for r in byf[keys[i]]]
        f = lambda lab: auc({b: sum(per[r][f"{lab}@{b}"]["succ"] for r in rs) / len(rs) for b in BUDGETS})  # noqa: E731
        bs.append(100 * (f("GA-MCTS-s0") - f("GA")))
    au["diff_s0_minus_GA_pp"] = 100 * (au["GA-MCTS-s0"] - au["GA"]); au["ci95_pp"] = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
    tt = {}
    traj = collections.defaultdict(dict)
    for f in sorted(ev.glob("any_s*.part*.jsonl")):
        for r in EJ.jl(f):
            traj["GA" if r["arm"] == "GA" else f"GA-MCTS-s{r['seed']}"][r["root_id"]] = r
    for lab, T in traj.items():
        first = [next((t for t, e in r["trace"] if e is not None), None) for r in T.values()]
        fin = []
        for r in T.values():
            tr = [(t, e) for t, e in r["trace"] if e is not None]
            if tr:
                fin.append(next(t for t, e in tr if e <= tr[-1][1] + 1e-12))
        walls = [r["final"]["wall_s"] for r in T.values()]
        tt[lab] = {"t_first_median_s": statistics.median([x for x in first if x is not None]) if any(x is not None for x in first) else None,
                   "t_final_incumbent_median_s": statistics.median(fin) if fin else None, "t_final_incumbent_p90_s": float(np.percentile(fin, 90)) if fin else None,
                   "plan_wall_mean_s": statistics.mean(walls), "budget_stops": sum(bool(r["final"]["budget_stop"]) for r in T.values()),
                   "exhausted": sum(bool(r["final"].get("exhausted")) for r in T.values()), "recon_final_ok": sum(bool(r["recon_final_ok"]) for r in T.values()),
                   "deadline_overrun_max_s": max(r["final"]["deadline_overrun_s"] or 0 for r in T.values())}
    out = {"n_roots": n, "summary": summ, "primary_paired": prim, "secondary_paired": sec, "auc_log_budget": au, "timing": tt,
           "completion": {"queued": sum(s["status"] == "QUEUED" for s in sel), "verified_new": sum(1 for s in sel if s["status"] == "QUEUED" and s["job"] in byjob),
                          "reused": sum(s["status"] == "REUSED" for s in sel), "cpu_h_new": sum(r.get("cpu_s", 0) for r in R.values()) / 3600},
           "per_root": per, "families": len(set(fam.values()))}
    (ev / "EVAL_RESULTS.json").write_text(json.dumps(out, indent=1, default=str))
    L = ["| Method | Success | Wilson 95% | Long | Regret (mean) | Overrun>0 |", "|---|---|---|---|---|---|"]
    for l in labs:
        s = summ[l]; w = s["wilson95"]
        L.append(f"| {l} | {s['succ']}/{n} | {100*w[0]:.1f}-{100*w[1]:.1f} | {s['succ_long']} | {s['regret_mean'] if s['regret_mean'] is None else round(s['regret_mean'], 3)} | {s['overrun_n_gt0']} |")
    L += ["", "| Budget | GA | GA-MCTS s0 | wins-losses | p (sign) | p (Holm) | diff pp [95% family CI] |", "|---|---|---|---|---|---|---|"]
    for b, p in zip(BUDGETS, prim):
        L.append(f"| {b} s | {summ[p['a']]['succ']} | {summ[p['b']]['succ']} | {p['b_wins']}-{p['b_losses']} | {p['p_sign']:.3g} | {p['p_holm']:.3g} | {p['diff_pp']:+.1f} {p['ci95_family_bootstrap_pp']} |")
    (ev / "EVAL_RESULTS.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main(sys.argv[1])
