#!/usr/bin/env python3
"""Apply the predeclared TUNING_GRID.json rule to the DEV anytime trajectories (learned energy + incumbent time only).
    python tune.py GA_DEV.jsonl GRID_DIR OUT.json      GRID_DIR/grid_<cfgid>.jsonl, one file per grid config (anytime.py output)"""
from __future__ import annotations

import json, statistics, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
E_MISS = 60.0


def jl(p):
    return [json.loads(l) for l in open(p)]


def esel(v):
    return v["E"] if v["decision"] == "REPAIR" and v["E"] is not None else (None if v["decision"] == "NOOP" else E_MISS)


def t_final(r):
    """first trace time at which the min candidate energy reaches its end-of-trajectory value (incumbent time)."""
    tr = [(t, e) for t, e in r["trace"] if e is not None]
    if not tr:
        return None
    ef = tr[-1][1]
    return next(t for t, e in tr if e <= ef + 1e-12)


def main(ga_path, grid_dir, out):
    G = json.loads((HERE / "TUNING_GRID.json").read_text())
    B = [str(b) for b in G["budgets_s"]]
    ga = {r["root_id"]: r for r in jl(ga_path) if r["arm"] == "GA"}
    runs = {}
    for f in sorted(Path(grid_dir).glob("grid_*.jsonl")):
        R = [r for r in jl(f) if r["arm"] == "GA-MCTS"]
        if R:
            runs[f.stem[5:]] = {"mcfg": R[0]["mcfg"], "rows": {r["root_id"]: r for r in R}}
    roots = sorted(ga)
    Estar = {}
    for rid in roots:
        vals = [esel(v) for v in ga[rid]["budgets"].values()] + [esel(v) for c in runs.values() if rid in c["rows"] for v in c["rows"][rid]["budgets"].values()]
        vals = [v for v in vals if v is not None]
        Estar[rid] = min(vals) if vals else None
    summ = {}
    for cid, c in runs.items():
        reg, tf, per_b = [], [], {b: [] for b in B}
        for rid in roots:
            r = c["rows"].get(rid)
            if r is None or Estar[rid] is None:
                continue
            for b in B:
                e = esel(r["budgets"][b])
                if e is None:
                    continue
                reg.append(e - Estar[rid]); per_b[b].append(e - Estar[rid])
            t = t_final(r)
            if t is not None:
                tf.append(t)
        summ[cid] = {"mcfg": {k: c["mcfg"][k] for k in ("c", "expand")}, "n_roots": len(c["rows"]), "mean_regret": statistics.mean(reg) if reg else None,
                     "regret_by_budget": {b: (statistics.mean(v) if v else None) for b, v in per_b.items()}, "median_t_final_incumbent_s": statistics.median(tf) if tf else None}
    gab = {b: statistics.mean([esel(ga[r]["budgets"][b]) - Estar[r] for r in roots if Estar[r] is not None and esel(ga[r]["budgets"][b]) is not None]) for b in B + ["60", "180"]
           if all(b in ga[r]["budgets"] for r in roots)}
    ok = [k for k in summ if summ[k]["mean_regret"] is not None and summ[k]["n_roots"] == len(roots)]
    best = min(summ[k]["mean_regret"] for k in ok)
    tied = [k for k in ok if summ[k]["mean_regret"] <= best + 0.01]
    pick = min(tied, key=lambda k: (summ[k]["median_t_final_incumbent_s"] if summ[k]["median_t_final_incumbent_s"] is not None else 1e9, summ[k]["mcfg"]["c"], summ[k]["mcfg"]["expand"] != "FULL"))
    res = {"rule": G["selection_rule"], "E_star": Estar, "configs": summ, "ga_regret_by_budget": gab, "tied": tied, "selected": pick, "selected_mcfg": runs[pick]["mcfg"]}
    Path(out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "E_star"}, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:4])
