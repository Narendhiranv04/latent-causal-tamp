#!/usr/bin/env python3
"""K<=3 ablation tables from immutable artifacts only (sealed predictions, verification results, frozen snapshot labels, checkpoints).
    python analyze.py physical SPLIT DOM REF ARM...    paired physical success vs REF (lineage-cluster bootstrap 2,000, seed 0), per K
    python analyze.py scorer SPLIT DOM CKPT_TAG=PATH... common-Z NLL/Brier/AUROC/AUPRC/ECE, Y/X diagnostics, same-endpoint order ranking
    python analyze.py placement SPLIT DOM ARM...       ingredient recall@M, known-assignment-in-pool, candidate counts, sampler cost
Outputs JSON next to $K3/runs/tables/.  Order ranking = same-endpoint, Y = 1, discordant finalized-X pairs (mixes geometric / robot-state /
planner / connector order effects; NOT a handoff-only metric)."""
import collections, hashlib, json, math, os, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
K3 = Path(os.environ["K3"])
SNAP = Path(os.environ["ABF_ROOT"]) / "snapshot/abf_9de85710c2a7103f"
VER, PRED, TAB = K3 / "runs/verification", K3 / "runs/predictions", K3 / "runs/tables"
B, SEED = 2000, 0


def jl(p):
    return [json.loads(l) for l in open(p)] if Path(p).exists() else []


def snap(dom, split):
    return {r["root_id"]: r for r in map(json.loads, open(SNAP / f"data{dom}.jsonl")) if r["split"] == split}


def cluster_boot(vals, groups, n=B, seed=SEED):
    """mean of vals with a cluster bootstrap over groups -> [point, lo, hi] (x100)."""
    vals, groups = np.asarray(vals, float), np.asarray(groups)
    if not len(vals):
        return [None, None, None]
    ug = np.unique(groups)
    idx = {g: np.nonzero(groups == g)[0] for g in ug}
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(n):
        pick = np.concatenate([idx[g] for g in ug[rng.integers(0, len(ug), len(ug))]])
        bs.append(vals[pick].mean())
    return [round(100 * vals.mean(), 2), round(100 * float(np.percentile(bs, 2.5)), 2), round(100 * float(np.percentile(bs, 97.5)), 2)]


def correct(x, kind):
    m, o = x["masks"], x["outcome"]
    if kind == "task":
        return None if not m.get("eval_task") or o == "UNKNOWN" else float(o == "SUCCESS")
    if kind == "noop":
        return None if not m.get("eval_noop") else float(o == "NOOP")
    return None if not m.get("eval_abstain") else float(o == "ABSTAIN")


def physical(split, dom, ref, arms):
    R = {a: {x["root_id"]: x for x in jl(VER / split / f"results_{a}_{dom}.jsonl")} for a in [ref] + arms}
    out = {}
    for a in [ref] + arms:
        X = list(R[a].values())
        row = {"n_roots": len(X), "outcomes": dict(collections.Counter(x["outcome"] for x in X)),
               "unknown_task": sum(1 for x in X if x["masks"].get("eval_task") and x["outcome"] == "UNKNOWN")}
        for kind, Ks in (("task", ("1", "2", "3")), ("noop", ("0",)), ("abstain", ("NONE",))):
            for K in Ks + (("all",) if kind == "task" else ()):
                sel = [x for x in X if (K == "all" and x["K"] in Ks) or x["K"] == K]
                v = [(correct(x, kind), x["group"], x["root_id"]) for x in sel]
                v = [t for t in v if t[0] is not None]
                row[f"{kind}_K{K}"] = {"n": len(v), "rate_ci": cluster_boot([t[0] for t in v], [t[1] for t in v])}
                if a != ref:                                      # paired difference on identical roots (both decided)
                    pr = [(correct(x, kind), correct(R[ref][x["root_id"]], kind), x["group"]) for x in sel if x["root_id"] in R[ref]]
                    pr = [t for t in pr if t[0] is not None and t[1] is not None]
                    row[f"{kind}_K{K}"]["paired_diff_vs_ref"] = {"n": len(pr), "diff_ci": cluster_boot([t[0] - t[1] for t in pr], [t[2] for t in pr])}
        att = [x for x in X if x["decision"] == "REPAIR"]
        row["selected_repairs"] = dict(collections.Counter(x["outcome"] for x in att))
        out[a] = row
    TAB.mkdir(parents=True, exist_ok=True)
    (TAB / f"physical_{split}_{dom}.json").write_text(json.dumps({"ref": ref, "bootstrap": {"n": B, "seed": SEED, "cluster": "layout_root_id lineage"}, "arms": out}, indent=1))
    print(json.dumps({a: {k: v["rate_ci"] for k, v in r.items() if isinstance(v, dict) and "rate_ci" in v} for a, r in out.items()}, indent=1))


def scorer(split, dom, specs):
    """Learned-scorer metrics on the frozen original labels of SPLIT (selected-assignment orders, omissions, empty endpoints)."""
    import torch
    import xy as XY
    rows_by = {}
    items = XY.load_domain(SNAP, dom.upper())[split]
    out = {}
    for tag, path in (s.split("=", 1) for s in specs):
        net = XY.load_model(path, "cuda")
        rows, noop = XY.predict_split(net, items, "cuda")
        m = XY.metrics(rows, noop)
        z = [r for r in rows if r["z"] is not None]
        grp = {it["root"]["root_id"]: it["root"]["layout_root_id"] for it in items}
        p = np.clip(np.array([r["p11"] for r in z]), 1e-6, 1 - 1e-6)
        y = np.array([r["z"] for r in z])
        nll = -(y * np.log(p) + (1 - y) * np.log(1 - p))
        rootw = collections.Counter(r["root"] for r in z)                         # per-root weighting: each root contributes total weight 1
        w = np.array([1.0 / rootw[r["root"]] for r in z])
        g = [grp[r["root"]] for r in z]
        m["nll_z_rootweighted"] = float((nll * w).sum() / w.sum())
        m["brier_z_rootweighted"] = float((((p - y) ** 2) * w).sum() / w.sum())
        m["nll_z_ci"] = cluster_boot(nll, g)
        # order ranking with root-cluster CI: per-root pair accuracies
        pr = collections.defaultdict(list)
        G = collections.defaultdict(list)
        for r in rows:
            if r["y"] == 1 and r["x"] in (0, 1):
                G[(r["root"], r["parent"])].append(r)
        for (root, _), rs in G.items():
            for a_ in rs:
                for b_ in rs:
                    if a_["x"] == 1 and b_["x"] == 0:
                        pr[root].append(1.0 if a_["p11"] > b_["p11"] else 0.5 if a_["p11"] == b_["p11"] else 0.0)
        pv = [v for rt in pr for v in pr[rt]]
        m["order_rank_ci"] = cluster_boot(pv, [grp[rt] for rt in pr for _ in pr[rt]]) if pv else None
        m["order_rank_roots"] = len(pr)
        m["arm_family"] = XY.ARMS[torch.load(path, map_location="cpu", weights_only=False)["arm"]]["family"]
        m["y_x_metrics"] = "NA (DIRECT outputs no Y / X marginals)" if m["arm_family"] == "direct" else "auroc_y / auroc_x above (px = MARGINAL X, not X|Y=1)"
        out[tag] = m
        rows_by[tag] = rows
    TAB.mkdir(parents=True, exist_ok=True)
    (TAB / f"scorer_{split}_{dom}.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({t: {k: m[k] for k in ("nll_z", "nll_z_ci", "brier_z", "auroc_z", "ece_z", "order_acc", "order_pairs", "order_rank_ci", "auroc_y", "auroc_x")} for t, m in out.items()}, indent=1, default=float))


def placement(split, dom, arms):
    """Teacher-free proposal diagnostics against the frozen labels: known successful assignments = selected-assignment / omission sequences with
    finalized X = 1 and Y = 1 (diagnostic only; never used to build candidates)."""
    S = snap(dom, split)
    out = {}
    for a in arms:
        P = {r["root_id"]: r for r in jl(PRED / a / f"{split}_{dom}.jsonl")}
        rec, cov, has, ns, ev, t, gp, sup = [], [], 0, [], [], [], [], []
        for rid, r in S.items():
            if rid not in P or r["K_legacy"] not in ("1", "2", "3"):
                continue
            Y = {json.dumps(sorted(map(list, y["edit"]))): y["y"] for y in r["labels"]["Y"]}
            succ = [q["seq"] for q in r["labels"]["X"] if q["x"] == 1 and Y.get(json.dumps(sorted(map(list, q["seq"])))) == 1]
            if not succ:
                continue
            has += 1
            prop = {int(o): set(v) for o, v in P[rid]["proposals"].items()}
            ing = {(o, d) for s in succ for o, d in s}
            rec.append(sum(d in prop.get(o, ()) for o, d in ing) / len(ing))
            cov.append(float(any(all(d in prop.get(o, ()) for o, d in s) for s in succ)))
        for x in P.values():
            ns.append(x["n_scored"]); ev.append(x.get("sampler_evals", 0)); t.append(x["timing_s"]["total"]); gp.append(x["gpu_peak_mib"])
            sup.append(x.get("hist_support_lt_M", 0))
        q = lambda v, f: float(np.percentile(v, f)) if v else None  # noqa: E731
        out[a] = {"roots_with_known_success": has, "ingredient_recall": float(np.mean(rec)) if rec else None,
                  "known_assignment_in_pool": float(np.mean(cov)) if cov else None, "n_scored": {"mean": float(np.mean(ns)), "p50": q(ns, 50), "p90": q(ns, 90), "p99": q(ns, 99), "max": max(ns)},
                  "sampler_evals_mean": float(np.mean(ev)), "latency_s": {"p50": q(t, 50), "p90": q(t, 90), "p99": q(t, 99)}, "gpu_peak_mib_max": max(gp),
                  "fm_hist_support_lt4_contexts": int(sum(sup))}
    TAB.mkdir(parents=True, exist_ok=True)
    (TAB / f"placement_{split}_{dom}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    c, a = sys.argv[1], sys.argv[2:]
    {"physical": lambda: physical(a[0], a[1], a[2], a[3:]), "scorer": lambda: scorer(a[0], a[1], a[2:]), "placement": lambda: placement(a[0], a[1], a[2:])}[c]()
