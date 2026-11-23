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


PRIMARY = [("EXACT_K2", None), ("UCT_SET", 256), ("PW_UCT_SET", 256), ("BEAM_SET", 256), ("RAND_SET", 256)]
SECONDARY = [("UCT_SET", 64), ("PW_UCT_SET", 64), ("BEAM_SET", 64), ("RAND_SET", 64)]


def decided(lab, k):
    """A cached label decides the outcome iff Y = 0, or Y = 1 with X in {0, 1} (v32b_phys.outcome semantics)."""
    xv, yv = lab.get(k, (None, None))
    return yv == 0 or (yv == 1 and xv in (0, 1))


def picks(rec, arms):
    rs = {(x["arm"], x["budget"]): x for x in rec["results"] if x["seed"] == 0}
    return {f"{a}@{b}": rs[(a, b)] for a, b in arms}


def manifest(evalf, private, caches, out, cap=1200):
    """Evaluator side: unique (root, ordered sequence) of REPAIR decisions on primary EVAL roots (K1/K2), minus decided cached labels;
    whole-root sha256('MCTS_P3|'+root) order if the cap binds (primary first, then secondary with the remaining cap)."""
    sys.path.insert(0, str(HERE.parent / "scripts"))
    import v32b_phys as V
    lab = {}
    for c in caches:
        for k, v in V.labels("2d", c).items():
            if k not in lab or (None in lab[k] and None not in v):
                lab[k] = v
    priv = {e["root_id"]: e for e in jl(private)}
    R = [r for r in jl(evalf) if r["split"] == "EVAL" and str(priv[r["root_id"]]["K"]) in ("1", "2")]
    order = sorted(R, key=lambda r: hashlib.sha256(("MCTS_P3|" + r["root_id"]).encode()).hexdigest())
    plan, used, stat = {}, set(), collections.Counter()
    for tier, arms in (("primary", PRIMARY), ("secondary", SECONDARY)):
        for r in order:
            need = set()
            for name, x in picks(r, arms).items():
                if x["decision"] == "REPAIR":
                    k = (r["root_id"], json.dumps(x["seq"]))
                    stat[f"{tier}_repair_decisions"] += 1
                    if decided(lab, k):
                        stat[f"{tier}_cached"] += 1
                    elif k not in used:
                        need.add(k)
            if len(used) + len(need) > cap:
                stat[f"{tier}_roots_not_covered"] += 1; continue
            used |= need; plan.setdefault(r["root_id"], set()).update(need); stat[f"{tier}_roots_covered"] += 1
    jobs = []
    for rid, ks in sorted(plan.items()):
        if not ks:
            continue
        e = priv[rid]
        jobs.append({"root_id": rid, "dom": "2D", "path": e["path"], "geom": e.get("geom", "original"), "ids": e["ids"],
                     "seqs": [[[e["ids"][o], int(c)] for o, c in json.loads(k[1])] for k in sorted(ks)]})
    Path(out).write_text("".join(json.dumps(j) + "\n" for j in jobs))
    S = {"primary_roots": len(R), "new_queries": sum(len(j["seqs"]) for j in jobs), "roots_with_queries": len(jobs), "cap": cap, **stat,
         "cache_sha256": {c: hashlib.sha256(Path(c).read_bytes()).hexdigest() for c in caches}, "eval_sha256": hashlib.sha256(Path(evalf).read_bytes()).hexdigest(),
         "jobs_sha256": hashlib.sha256(Path(out).read_bytes()).hexdigest()}
    print(json.dumps(S)); return S


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "tune":
        tune(sys.argv[2])
    elif c == "model":
        r = model(sys.argv[2], None if len(sys.argv) < 4 or sys.argv[3] == "ALL" else sys.argv[3])
        Path(sys.argv[4] if len(sys.argv) > 4 else REP / "MODEL_SUMMARY.json").write_text(json.dumps(r, indent=1)); print(json.dumps(r)[:3000])
    elif c == "manifest":
        S = manifest(sys.argv[2], sys.argv[3], sys.argv[4].split(","), sys.argv[5])
        (REP / "P3_MANIFEST.json").write_text(json.dumps(S, indent=1))
