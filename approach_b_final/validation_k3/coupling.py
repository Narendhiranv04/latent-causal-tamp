#!/usr/bin/env python3
"""Experiment A2 / A4 / B1 (labeled-node part) / D (ranking part) from the node dumps (nodes.py dump); teacher-free, frozen labels.
    python coupling.py DOM SPLIT       -> $K3V/runs/out/coupling/{DOM}_{SPLIT}.json
D-family (FULL = frozen D, DREFIT): P(X=1|Y=y) = sig(a + w y); E: sig(a) (w = 0); G: coupled, order-invariant; DIRECT: success logit a only.
Every X node of the finalized labels has its endpoint Y observed (nodes.py audit), so conditional X metrics use the observed Y."""
import collections, json, sys

import numpy as np

import vk

sig = lambda z: 1.0 / (1.0 + np.exp(-np.asarray(z, float)))  # noqa: E731
FAM = {"FULL": "D", "DREFIT": "D", "E": "E", "G": "D", "DIRECT": "DIRECT"}


def load(dom, split, model):
    R = vk.jl(vk.OUT / "nodes" / f"{dom}_{split}_{model}.jsonl")
    return [r for r in R if r["node"] == "X"], [r for r in R if r["node"] == "Y"]


def node_preds(X, fam):
    """per X node: px_y (X | observed Y), pz (p11), px1 (X | Y=1), px0 (X | Y=0)."""
    a, w, b = (np.array([r[k] for r in X]) for k in ("a", "w", "b"))
    y = np.array([r["y"] for r in X], float)
    if fam == "DIRECT":
        return {"pz": sig(a)}
    return {"px_y": sig(a + w * y), "px1": sig(a + w), "px0": sig(a), "pz": sig(b) * sig(a + w), "py": sig(b), "pz_w0": sig(b) * sig(a)}


def order_pairs(X, p):
    """same-endpoint, Y = 1, discordant observed X: (lineage, credit) per pair."""
    g = collections.defaultdict(list)
    for i, r in enumerate(X):
        if r["y"] == 1 and r["x"] in (0, 1):
            g[(r["root"], r["s"])].append(i)
    out = []
    for idx in g.values():
        for i in idx:
            for j in idx:
                if X[i]["x"] == 1 and X[j]["x"] == 0:
                    out.append((X[i]["lineage"], 1.0 if p[i] > p[j] else 0.5 if p[i] == p[j] else 0.0, X[i]["K"]))
    return out


def summarize(dom, split):
    models = [f"{m}_s{s}" for m in ("FULL", "DREFIT", "E", "G", "DIRECT") for s in (0, 1, 2)]
    D = {m: load(dom, split, m) for m in models}
    X0 = D["FULL_s0"][0]
    for m in models:                                                          # node alignment across models
        assert [(r["root"], r["q"]) for r in D[m][0]] == [(r["root"], r["q"]) for r in X0], m
    x = np.array([r["x"] for r in X0], float); y = np.array([r["y"] for r in X0], float); z = x * y
    lin = np.array([r["lineage"] for r in X0]); K = np.array([r["K"] for r in X0]); L = np.array([r["len"] for r in X0])
    P = {m: node_preds(D[m][0], FAM[m.rsplit("_s", 1)[0]]) for m in models}
    out = {"n_x_nodes": len(X0), "n_roots": len({r["root"] for r in X0}), "label_rates": {"x|y=0": float(x[y == 0].mean()), "x|y=1": float(x[y == 1].mean()),
           "n_y0": int((y == 0).sum()), "n_y1": int((y == 1).sum()), "z": float(z.mean())}}
    # ---- A2: learned coupling of the D-family checkpoints
    A2 = {}
    for m in models:
        if FAM[m.rsplit("_s", 1)[0]] != "D":
            continue
        w = np.array([r["w"] for r in D[m][0]]); dp = P[m]["px1"] - P[m]["px0"]
        def st(mask):
            return {"n": int(mask.sum()), "w_mean": float(w[mask].mean()), "w_sd": float(w[mask].std()), "w_q": [float(q) for q in np.percentile(w[mask], [5, 25, 50, 75, 95])],
                    "frac_w_pos": float((w[mask] > 0).mean()), "dp_mean": float(dp[mask].mean()), "absdp_mean": float(np.abs(dp[mask]).mean()),
                    "frac_absdp_gt_0.1": float((np.abs(dp[mask]) > 0.1).mean()), "px0_mean": float(P[m]["px0"][mask].mean()), "px1_mean": float(P[m]["px1"][mask].mean())}
        row = {"all": st(np.ones(len(w), bool))}
        for k in ("1", "2", "3"):
            if (K == k).any():
                row[f"K{k}"] = st(K == k)
        for l in (1, 2, 3):
            if (L == l).any():
                row[f"len{l}"] = st(L == l)
        for yy in (0, 1):
            row[f"endpoint_y{yy}"] = st(y == yy)
        for xx in (0, 1):
            row[f"x{xx}"] = st(x == xx)
        g = collections.defaultdict(list)                                     # within-endpoint (orderings) vs between-endpoint spread of w
        for i, r in enumerate(D[m][0]):
            g[(r["root"], r["s"])].append(w[i])
        multi = [np.std(v) for v in g.values() if len(v) >= 2]
        row["w_within_endpoint_sd_mean"] = float(np.mean(multi)) if multi else None
        row["w_between_endpoint_sd"] = float(np.std([np.mean(v) for v in g.values()]))
        row["n_multi_order_endpoints"] = len(multi)
        A2[m] = row
    out["A2"] = A2
    # ---- A4: conditional X, Y, Z, order -- per model (seed) and paired D-family vs E
    per = {}
    for m in models:
        p = P[m]
        r_ = {"z": {"nll": float(vk.bce(z, p["pz"]).mean()), "brier": float(((p["pz"] - z) ** 2).mean()), "ece": vk.ece(z, p["pz"]),
                    "auroc": vk.auroc(z, p["pz"]), "auprc": vk.auprc(z, p["pz"])}}
        op = order_pairs(D[m][0], p["pz"])
        r_["order"] = {"pairs": len(op), "acc": float(np.mean([t[1] for t in op])) if op else None}
        if "px_y" in p:
            for yy in (0, 1):
                mk = y == yy
                r_[f"x|y={yy}"] = {"n": int(mk.sum()), "nll": float(vk.bce(x[mk], p["px_y"][mk]).mean()), "brier": float(((p["px_y"][mk] - x[mk]) ** 2).mean()),
                                   "ece": vk.ece(x[mk], p["px_y"][mk]), "auroc": vk.auroc(x[mk], p["px_y"][mk])}
            Yn = D[m][1]
            ed = [r for r in Yn if r["y"] is not None and not r["noop"]]; no = [r for r in Yn if r["y"] is not None and r["noop"]]
            for nm, S in (("y_edited_endpoints", ed), ("y_noop", no)):
                yy_, pb = np.array([r["y"] for r in S], float), sig([r["b"] for r in S])
                r_[nm] = {"n": len(S), "nll": float(vk.bce(yy_, pb).mean()), "brier": float(((pb - yy_) ** 2).mean()), "ece": vk.ece(yy_, pb), "auroc": vk.auroc(yy_, pb)}
        r_["by_K"] = {k: {"n": int((K == k).sum()), "z_nll": float(vk.bce(z[K == k], p["pz"][K == k]).mean()), "z_auroc": vk.auroc(z[K == k], p["pz"][K == k]),
                          **({"x|y=1_nll": float(vk.bce(x[(K == k) & (y == 1)], p["px_y"][(K == k) & (y == 1)]).mean()) if ((K == k) & (y == 1)).any() else None,
                              "x|y=0_nll": float(vk.bce(x[(K == k) & (y == 0)], p["px_y"][(K == k) & (y == 0)]).mean()) if ((K == k) & (y == 0)).any() else None}
                             if "px_y" in p else {})} for k in ("1", "2", "3") if (K == k).any()}
        per[m] = r_
    out["per_model"] = per
    paired = {}
    for ref in ("FULL", "DREFIT"):
        for other in ("E",):
            res = {}
            pr = lambda fam, key: np.mean([P[f"{fam}_s{s}"][key] for s in (0, 1, 2)], 0)  # noqa: E731
            for nm, mk, key, lab in (("x|y=0 nll", y == 0, "px_y", x), ("x|y=1 nll", y == 1, "px_y", x), ("z nll", np.ones(len(x), bool), "pz", z)):
                d_ref = np.mean([vk.bce(lab, P[f"{ref}_s{s}"][key]) for s in (0, 1, 2)], 0)
                d_oth = np.mean([vk.bce(lab, P[f"{other}_s{s}"][key]) for s in (0, 1, 2)], 0)
                res[nm] = {"n": int(mk.sum()), "diff_other_minus_ref": vk.cluster_boot((d_oth - d_ref)[mk], lin[mk], scale=1.0)}
                for k in ("1", "2", "3"):
                    mk2 = mk & (K == k)
                    if mk2.any():
                        res[f"{nm} K{k}"] = {"n": int(mk2.sum()), "diff_other_minus_ref": vk.cluster_boot((d_oth - d_ref)[mk2], lin[mk2], scale=1.0)}
            paired[f"{other}_vs_{ref}"] = res
    out["A4_paired_seedmean"] = paired
    # ---- D (ranking part) / A5 (labeled nodes): which score ranks success on the same nodes; frozen FULL s0..2
    rk = {}
    for m in ("FULL_s0", "FULL_s1", "FULL_s2"):
        p = P[m]
        cand = {"p11": p["pz"], "p11_w0": p["pz_w0"], "Y_only": p["py"], "X_marg": p["py"] * p["px1"] + (1 - p["py"]) * p["px0"], "X_given_Y1": p["px1"]}
        rk[m] = {k: {"z_auroc": vk.auroc(z, v), "z_auprc": vk.auprc(z, v), "order_acc": (lambda op: float(np.mean([t[1] for t in op])) if op else None)(order_pairs(D[m][0], v))}
                 for k, v in cand.items()}
        rk[m]["p11_vs_w0_absdiff_mean"] = float(np.abs(p["pz"] - p["pz_w0"]).mean())
    out["score_variants_ranking"] = rk
    vk.wjson(vk.OUT / "coupling" / f"{dom}_{split}.json", out)
    print(json.dumps({"label_rates": out["label_rates"], "A2_FULL_s0_all": A2["FULL_s0"]["all"], "paired": paired}, indent=1, default=float)[:6000])


if __name__ == "__main__":
    summarize(sys.argv[1], sys.argv[2])
