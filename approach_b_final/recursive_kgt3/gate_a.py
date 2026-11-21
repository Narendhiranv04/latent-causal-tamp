#!/usr/bin/env python3
"""EVALUATOR-SIDE Gate A diagnosis (post hoc; kill-table relaxation labels only, no teacher, nothing fed back to any planner).
For each R0 arm re-run with candidate-pool logging:
  H1  energy vs length: per scene the arg-min length, best C per length; does a statically COMPLETE candidate exist in the pool, and where does
      it rank under the historical energy (Σ chunk X) vs the R1 energy (mean chunk X) -- counterfactual re-ranking of the SAME pool
  H2  early stop: rounds, stop reasons, fraction of short (<4) candidates with h_Y >= 0.5
  H3  threshold over-trigger: fraction of temporary-target probes with ŷ < 0.5; ŷ scale
  H4  budget starvation: local calls used before round 1 completed (REC)
    python gate_a.py P4_DIR DEV_PUBLIC DEV_PRIVATE_DIR TABLES_DIR OUT.json"""
import json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from dev_eval import Static, jl  # noqa: E402


def main(p4, dev_public, priv, tables, out):
    ST = Static(tables)
    pub = {r["root_id"]: r for r in jl(dev_public)}
    pv = {r["root_id"]: r for r in jl(Path(priv) / "dev_private.jsonl")}
    R = {}
    for arm in ("R0_FLAT", "R0_REC2", "R0_REC"):
        d = Path(p4) / arm / "traces"
        if not d.exists():
            continue
        rows = []
        for f in sorted(d.glob("*.json")):
            t = json.loads(f.read_text()); rid = t["res"]["root_id"]
            inp = pub[rid]["inputs"]; c0 = [int(c) for c in inp["cells0"]]; T0, G0, K = int(inp["tid"]), int(inp["goal_cell"]), pv[rid]["K"]
            cands = t["cands"]
            for c in cands:
                s = [tuple(x) for x in c["seq"]]
                c["complete"] = ST.endpoint_y(c0, T0, G0, s) and ST.order_valid(c0, T0, G0, s)
                c["endpoint_live"] = ST.endpoint_y(c0, T0, G0, s)
                c["C_mean"] = -math.log(max(1e-6, c["hY"])) + sum(-math.log(max(1e-6, x)) for x in c["hX"]) / max(1, len(c["hX"]))
            comp = [c for c in cands if c["complete"]]
            byC = sorted(cands, key=lambda c: (c["C"], len(c["seq"])))
            byM = sorted(cands, key=lambda c: (c["C_mean"], len(c["seq"])))
            rank_hist = min((i for i, c in enumerate(byC) if c["complete"]), default=None)
            rank_mean = min((i for i, c in enumerate(byM) if c["complete"]), default=None)
            lens = sorted({len(c["seq"]) for c in cands})
            bestC_len = {L: min(c["C"] for c in cands if len(c["seq"]) == L) for L in lens}
            short_hi = [c for c in cands if len(c["seq"]) < 4 and c["hY"] >= 0.5]
            yt = [y["y"] for y in t["log"]["ytask"]]
            r1 = t["log"]["rounds"][0] if t["log"]["rounds"] else {}
            rows.append({"root_id": rid, "K": K, "n_cands": len(cands), "max_len": max(lens) if lens else 0, "argmin_len": len(byC[0]["seq"]) if byC else 0,
                         "argmin_len_meanX": len(byM[0]["seq"]) if byM else 0, "n_complete": len(comp), "n_endpoint_live": sum(c["endpoint_live"] for c in cands),
                         "complete_rank_hist": rank_hist, "complete_rank_meanX": rank_mean, "chosen_complete": bool(byC and byC[0]["complete"]),
                         "meanX_choice_complete": bool(byM and byM[0]["complete"]), "bestC_by_len": bestC_len, "frac_short_hY_ge_0.5": len(short_hi) / max(1, sum(len(c["seq"]) < 4 for c in cands)),
                         "rounds": t["res"]["rounds"], "stop": t["res"]["stop"], "frac_ytask_lt_0.5": sum(y < 0.5 for y in yt) / max(1, len(yt)),
                         "ytask_median": sorted(yt)[len(yt) // 2] if yt else None, "local_used": t["res"]["budget"]["local"], "inserts": len(t["log"]["insert"]),
                         "complete_lens": sorted({len(c["seq"]) for c in comp})})
        n = len(rows)
        R[arm] = {"n": n, "scenes_with_complete_candidate": sum(r["n_complete"] > 0 for r in rows), "chosen_complete": sum(r["chosen_complete"] for r in rows),
                  "meanX_rerank_complete": sum(r["meanX_choice_complete"] for r in rows), "mean_cands": sum(r["n_cands"] for r in rows) / max(1, n),
                  "mean_max_len": sum(r["max_len"] for r in rows) / max(1, n), "mean_argmin_len": sum(r["argmin_len"] for r in rows) / max(1, n),
                  "mean_argmin_len_meanX": sum(r["argmin_len_meanX"] for r in rows) / max(1, n),
                  "frac_short_hY_ge_0.5": sum(r["frac_short_hY_ge_0.5"] for r in rows) / max(1, n),
                  "frac_ytask_lt_0.5": sum(r["frac_ytask_lt_0.5"] for r in rows) / max(1, n), "stops": {}, "rows": rows}
        for r in rows:
            R[arm]["stops"][r["stop"]] = R[arm]["stops"].get(r["stop"], 0) + 1
    Path(out).write_text(json.dumps(R, indent=1))
    for a, v in R.items():
        print(a, {k: v[k] for k in v if k != "rows"})


if __name__ == "__main__":
    main(*sys.argv[1:6])
