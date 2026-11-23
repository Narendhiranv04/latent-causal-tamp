#!/usr/bin/env python3
"""Analysis for the K<=2 set-search study.
  tune     DEV pilot -> per-arm hyper-parameters by a FIXED model-only criterion: mean agreement with EXACT_K2's committed decision over
           budgets {16,64,256,1024} x seeds; ties -> lower mean best-reward regret, then grid order.  Writes reports/P2_FROZEN_PARAMS.json.
  model    EVAL predictions (model-only): agreement / regret / coverage / scorer counts / wall time per arm x budget, paired by root.
  manifest sealed predictions + teacher caches -> exact unique (root, ordered sequence) query manifest, deduplicated (evaluator side).
  physical evaluator results -> verified success by K stratum, paired root bootstrap vs controls (after teacher verification only)."""
from __future__ import annotations

import collections, hashlib, json, math, random, statistics as st, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REP = HERE / "reports"


def jl(p):
    return [json.loads(l) for l in open(p)]


def key(x):
    return (x["arm"], json.dumps(x.get("params") or {}, sort_keys=True), x["budget"])


def metrics(rec):
    """Per run -> {agree, reward_regret, sel_regret, scored, sets, wall} relative to the same root's EXACT_K2."""
    ex = rec["results"][0]; out = []
    for x in rec["results"][1:]:
        agree = x["decision"] == ex["decision"] and x["seq"] == ex["seq"]
        rr = None if not ex["best_reward"] else 1 - (x["best_reward"] or 0.0) / ex["best_reward"]
        sr = (math.log(max(ex["p11"], 1e-12)) - math.log(max(x["p11"], 1e-12))) if ex["decision"] == x["decision"] == "REPAIR" else None
        out.append((x, {"agree": agree, "reward_regret": rr, "sel_regret": sr, "scored": x["scored"], "sets": x["sets_scored"],
                        "wall": x["wall_s"], "iters": x.get("iterations"), "stop": x["stop"], "exact_scored": ex["scored"]}))
    return out


def tune(pilot):
    R = jl(pilot); agg = collections.defaultdict(lambda: collections.defaultdict(list))
    for rec in R:
        for x, m in metrics(rec):
            k = (x["arm"], json.dumps(x.get("params") or {}, sort_keys=True))
            agg[k]["agree"].append(m["agree"])
            if m["reward_regret"] is not None:
                agg[k]["rr"].append(m["reward_regret"])
            agg[k][f"agree_B{x['budget']}"].append(m["agree"])
    tab, frozen = {}, {}
    for (arm, p), v in agg.items():
        tab.setdefault(arm, []).append({"params": json.loads(p), "agree": round(st.mean(v["agree"]), 4), "reward_regret": round(st.mean(v["rr"]), 4),
                                        **{b: round(st.mean(v[b]), 4) for b in sorted(v) if b.startswith("agree_B")}, "n": len(v["agree"])})
    import run as RUN
    for arm, rows in tab.items():
        order = [json.dumps(p, sort_keys=True) for p in RUN.GRID[arm]]
        best = min(rows, key=lambda r: (-r["agree"], r["reward_regret"], order.index(json.dumps(r["params"], sort_keys=True))))
        frozen[arm] = best["params"]
    REP.mkdir(exist_ok=True)
    (REP / "P2_TUNING.json").write_text(json.dumps({"criterion": __doc__.split("tune")[1].split("\n  model")[0].strip(), "roots": len(R),
                                                     "pilot_sha256": hashlib.sha256(Path(pilot).read_bytes()).hexdigest(), "table": tab}, indent=1))
    (REP / "P2_FROZEN_PARAMS.json").write_text(json.dumps(frozen, indent=1))
    print(json.dumps(frozen))


def model(evalf, split="EVAL"):
    R = [r for r in jl(evalf) if split is None or r["split"] == split]
    agg = collections.defaultdict(lambda: collections.defaultdict(list)); ex_rows = []
    for rec in R:
        ex = rec["results"][0]; ex_rows.append({"scored": ex["scored"], "wall": ex["wall_s"], "t_table": rec["t_table_s"]})
        for x, m in metrics(rec):
            k = (x["arm"], x["budget"])
            for f in ("agree", "scored", "sets", "wall"):
                agg[k][f].append(m[f])
            if m["reward_regret"] is not None:
                agg[k]["rr"].append(m["reward_regret"])
            if m["sel_regret"] is not None:
                agg[k]["sr"].append(m["sel_regret"])
            agg[k]["stop_" + m["stop"]].append(1)
            agg[k]["dec_" + x["decision"]].append(1)
    q = lambda v, p: sorted(v)[min(len(v) - 1, int(p * len(v)))]  # noqa: E731
    out = {"roots": len(R), "split": split, "EXACT_K2": {"median_scored": st.median(r["scored"] for r in ex_rows), "mean_scored": round(st.mean(r["scored"] for r in ex_rows), 1),
                                                       "p90_scored": q([r["scored"] for r in ex_rows], .9), "median_wall_s": round(st.median(r["wall"] for r in ex_rows), 4),
                                                       "p90_wall_s": round(q([r["wall"] for r in ex_rows], .9), 4)}, "arms": {}}
    for (arm, B), v in sorted(agg.items()):
        out["arms"][f"{arm}@{B}"] = {"agree_with_exact": round(st.mean(v["agree"]), 4), "mean_reward_regret": round(st.mean(v["rr"]), 4) if v["rr"] else None,
                                     "mean_sel_logp_regret_when_both_repair": round(st.mean(v["sr"]), 4) if v["sr"] else None,
                                     "median_scored": st.median(v["scored"]), "mean_sets": round(st.mean(v["sets"]), 1),
                                     "median_wall_s_replay": round(st.median(v["wall"]), 5), "p90_wall_s_replay": round(q(v["wall"], .9), 5),
                                     "stops": {k[5:]: len(x) for k, x in v.items() if k.startswith("stop_")},
                                     "decisions": {k[4:]: len(x) for k, x in v.items() if k.startswith("dec_")}, "runs": len(v["agree"])}
    return out


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "tune":
        tune(sys.argv[2])
    elif c == "model":
        r = model(sys.argv[2], None if len(sys.argv) < 4 or sys.argv[3] == "ALL" else sys.argv[3])
        Path(sys.argv[4] if len(sys.argv) > 4 else REP / "MODEL_SUMMARY.json").write_text(json.dumps(r, indent=1)); print(json.dumps(r)[:3000])
