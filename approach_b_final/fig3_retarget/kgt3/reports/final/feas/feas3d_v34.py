#!/usr/bin/env python3
"""V3.4 3D cohort (395 roots): target-feasibility of the INITIAL scene (move t0 to its goal, no rearrangement).
Scoring is label-blind and reuses the CF/NULL audit adapters unchanged (cf_null_audit/cf_infer.py sha 259a3b57..., lock amendment 4):
  GRN  = cf_infer.grn  (yadu/GRN 986cce3a runs/s{0,1,2}/best.pt, native make_graph on the initial cells, sigmoid(action))
  Ours = cf_infer.ours (production D bundle ~/abf_v34/approach_b_bundle 3d/scorer_s{0,1,2}.pt, p_noop) -- NOT the final clean model
Labels (read only after scoring): PRIVATE_INDEX 3D K == '0' -> 1; K in {1,2,3,NONE} -> 0.  Threshold 0.5 (prespecified, lock).
    CF_GRN=<baseline_grn> python feas3d_v34.py score OUT_SCORES.jsonl ;  python feas3d_v34.py metrics OUT_SCORES.jsonl OUT.json PRED.jsonl"""
import hashlib, json, math, os, sys
from pathlib import Path
import numpy as np

FIN = Path.home() / "abf_v34/final"
CFN = Path.home() / "Desktop/boltzmann_lfd/.claude/worktrees/cf-null/approach_b_final/cf_null_audit"
PUB = Path.home() / "legolas_v34/public_3d.jsonl"
SEEDS = ("s0", "s1", "s2")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def score(outp):
    import torch
    torch.set_num_threads(4); torch.manual_seed(0)
    sys.path.insert(0, str(CFN))
    assert sha(CFN / "cf_infer.py").startswith("259a3b57e70ff527")
    import cf_infer as CI
    pub = [json.loads(l) for l in open(PUB)]
    rows, recs = [], {}
    for p in pub:                                                # public order; roots read for geometry (objects / initial_cells / goal) only
        path = FIN / "roots" / f"{p['root_id']}.json"
        rec = json.loads(path.read_text())
        rows.append(dict(qid=p["root_id"], root_id=p["root_id"], path=str(path), cells=rec["initial_cells"]))
        recs[p["root_id"]] = rec
    sc, xy0 = CI.ours("3d", rows, recs)
    g, graphs = CI.grn(rows, recs)
    pubx = {p["root_id"]: p["inputs"]["xy0"] for p in pub}
    with open(outp, "w") as f:
        for q in rows:
            k = q["qid"]
            assert np.allclose(xy0[k], pubx[k], atol=1e-9), k              # ours input == public inputs
            f.write(json.dumps({"root_id": k, **sc[k], **g[k]}) + "\n")
    print("scored", len(rows))


def wilson(k, n, z=1.959964):
    if n == 0:
        return [None, None]
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def auroc(y, p):
    from scipy.stats import rankdata
    r = rankdata(p); n1 = y.sum(); n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else float("nan")


def block(y, p, fam, tau=0.5, B=2000):
    yp = (p >= tau).astype(int)
    TP = int(((yp == 1) & (y == 1)).sum()); FP = int(((yp == 1) & (y == 0)).sum()); TN = int(((yp == 0) & (y == 0)).sum()); FN = int(((yp == 0) & (y == 1)).sum())
    n = len(y); P, N = TP + FN, TN + FP
    rng = np.random.default_rng(0)
    U = sorted(set(fam)); idx = {u: np.where(fam == u)[0] for u in U}
    bs = []
    for _ in range(B):                                         # cluster bootstrap over parent_family_id
        ii = np.concatenate([idx[U[j]] for j in rng.integers(0, len(U), len(U))])
        bs.append(auroc(y[ii], p[ii]))
    bs = np.array(bs); bs = bs[np.isfinite(bs)]
    return dict(n=n, n_pos=P, n_neg=N, TP=TP, FP=FP, TN=TN, FN=FN,
                TPR=round(TP / P, 4) if P else None, TPR_ci95_wilson=wilson(TP, P), TPR_denom=P,
                TNR=round(TN / N, 4) if N else None, TNR_ci95_wilson=wilson(TN, N), TNR_denom=N,
                precision=round(TP / (TP + FP), 4) if TP + FP else None, precision_ci95_wilson=wilson(TP, TP + FP), precision_denom=TP + FP,
                accuracy=round((TP + TN) / n, 4), accuracy_ci95_wilson=wilson(TP + TN, n),
                AUROC=round(auroc(y, p), 4), AUROC_ci95_cluster_bootstrap=[round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)] if len(bs) else None,
                n_bootstrap=int(len(bs)), threshold=tau, predicted_feasible="p >= threshold")


def metrics(scp, outp, predp):
    S = {r["root_id"]: r for r in map(json.loads, open(scp))}
    for r in map(json.loads, open(Path(scp).parent / "scores_3d_v34_pig_scn.jsonl")):
        S[r["root_id"]].update(r)
    priv = {r["root_id"]: r for r in map(json.loads, open(FIN / "PRIVATE_INDEX.jsonl")) if r["domain"] == "3d"}
    gt = {}
    for b in ("batchA", "batchB"):
        for l in open(Path.home() / f"abf_v34/{b}/private_3d_gt.jsonl"):
            r = json.loads(l); gt.setdefault(r["root_id"], []).append(r)
    prod = {}
    for b in ("batchA", "batchB"):
        for l in open(Path.home() / f"abf_v34/{b}/pred_3d.jsonl"):
            r = json.loads(l); prod[r["root_id"]] = r["p_noop"]
    assert set(S) == set(priv) and len(S) == 395
    ids = sorted(S)
    y = np.array([int(priv[k]["K"] == "0") for k in ids]); fam = np.array([priv[k]["parent_family_id"] for k in ids])
    # label provenance checks
    root_lab = {}
    for k in ids:
        rec = json.loads((FIN / priv[k]["path"]).read_text())
        o = rec["labels"]["original"]; root_lab[k] = (int(o["y"]), o.get("negative_kind"), rec.get("verified_K"))
    chk = dict(K0_with_y_empty=sum(1 for k in ids if priv[k]["K"] == "0" and any("y_empty" in g for g in gt.get(k, []))),
               K0_y_empty_eq_1=sum(1 for k in ids if priv[k]["K"] == "0" and all(g.get("y_empty") == 1 for g in gt.get(k, []) if "y_empty" in g)),
               root_original_y_agrees=int(sum(root_lab[k][0] == y[i] for i, k in enumerate(ids))),
               root_verified_K_agrees=int(sum(str(root_lab[k][2]) == (priv[k]["K"] if priv[k]["K"] != "NONE" else "None") for k in ids)),
               neg_budget_limited_NO_PLAN_FOUND=int(sum(root_lab[k][1] == "NO_PLAN_FOUND" for k in ids)),
               ours_s0_vs_production_pred_p_noop_maxabs=float(max(abs(S[k]["ours_s0"] - prod[k]) for k in ids)))
    cls = {}
    for k in ids:
        cls.setdefault(priv[k]["K"], []).append(k)
    meths = {"PIGINet_noimg": "piginet_", "GRN": "grn_", "SCNet": "scnet_", "Ours_productionD": "ours_"}
    C2 = Path(__file__).parent / "ckpt2"
    ck = {"GRN": {s: sha(Path(os.environ["CF_GRN"]) / "runs" / s / "best.pt") for s in SEEDS},
          "PIGINet_noimg": {s: sha(C2 / f"piginet_shelf/runs/noimg_{s}/best.pt") for s in SEEDS},
          "SCNet": {s: sha(C2 / f"scn_shelf/runs/adam_{s}/best.pt") for s in SEEDS},
          "Ours_productionD": {s: sha(Path.home() / f"abf_v34/approach_b_bundle/3d/scorer_{s}.pt") for s in SEEDS}}
    strict = np.array([root_lab[k][1] != "NO_PLAN_FOUND" for k in ids])
    out = dict(task="V3.4 3D cohort: is t0 -> goal feasible in the INITIAL scene (no rearrangement)",
               label="1 iff PRIVATE_INDEX K == '0' (verified K0; root labels.original.y = 1); 0 for K1/K2/K3/NONE",
               n=len(ids), n_pos=int(y.sum()), n_neg=int(len(y) - y.sum()), class_counts={c: len(v) for c, v in sorted(cls.items())},
               label_checks=chk, ci="Wilson 95% for proportions; AUROC 95% = 2000-replicate cluster bootstrap over parent_family_id (181 families), seed 0",
               methods={})
    for m, pre in meths.items():
        d = dict(checkpoint_sha256=ck[m], seeds={})
        for s in SEEDS:
            p = np.array([S[k][pre + s] for k in ids])
            d["seeds"][s] = block(y, p, fam)
            d["seeds"][s]["per_class_pred_feasible"] = {c: f"{int(sum(S[k][pre + s] >= .5 for k in v))}/{len(v)}" for c, v in sorted(cls.items())}
            d["seeds"][s]["sensitivity_excl_budget_limited_negatives"] = {kk: vv for kk, vv in block(y[strict], p[strict], fam[strict], B=0).items()
                                                                           if kk in ("n", "TP", "FP", "TN", "FN", "TNR", "AUROC")}
        d["primary"] = "s0"
        d["seed_mean_sd"] = {k: [round(float(np.mean([d["seeds"][s][k] for s in SEEDS])), 4), round(float(np.std([d["seeds"][s][k] for s in SEEDS], ddof=1)), 4)]
                             for k in ("TPR", "TNR", "precision", "accuracy", "AUROC")}
        out["methods"][m] = d
    out["methods"]["GRN"]["adapter"] = "cf_infer.grn: build_graphs.make_graph(rec, initial cells, goal) -> sigmoid(action head); yadu/GRN 986cce3a; torch_geometric 2.5.2"
    out["methods"]["Ours_productionD"]["adapter"] = "cf_infer.ours: XYNet.predict p_noop (empty-edit Y) on contracts.view3d == public inputs; label 'production D (not the final clean model)'"
    out["methods"]["PIGINet_noimg"]["adapter"] = "cf_infer.piginet: native 'move T' sample on the initial state, plan [(t0, start, goal)], train.predict(use_image=False) = sigmoid(plan head); image variant excluded (no renders)"
    out["methods"]["SCNet"]["adapter"] = "cf_infer.scnet: max over the target's 32 teacher grasps of P(grasp works); scene_cloud 8192 pts seeded sha256('CFSCN|root_id'); grasps/shift via cf_scnroots.py (env3d, shelf66_v3 teacher)"
    json.dump(out, open(outp, "w"), indent=1)
    with open(predp, "w") as f:
        for i, k in enumerate(ids):
            r = dict(root_id=k, K=priv[k]["K"], y=int(y[i]), label_negative_kind=root_lab[k][1])
            for m, pre in meths.items():
                for s in SEEDS:
                    r[f"{pre}{s}"] = round(S[k][pre + s], 6); r[f"{pre}{s}_pred"] = int(S[k][pre + s] >= .5)
            f.write(json.dumps(r) + "\n")
    print(json.dumps({m: {kk: out["methods"][m]["seeds"]["s0"][kk] for kk in ("TP", "FP", "TN", "FN", "TPR", "TNR", "AUROC")} for m in meths}), json.dumps(chk))


def score_b(outp):
    """PIGINet-noimg + SCNet via cf_infer.piginet / cf_infer.scnet (unchanged); needs CF_PIG, CF_SCN, CF_SCN_ROOTS."""
    import torch
    torch.set_num_threads(4); torch.manual_seed(0)
    sys.path.insert(0, str(CFN))
    assert sha(CFN / "cf_infer.py").startswith("259a3b57e70ff527")
    import cf_infer as CI
    rows = [json.loads(l) for l in open(Path(__file__).parent / "manifest_3d_v34.jsonl")]
    recs = {q["qid"]: json.loads(Path(q["path"]).read_text()) for q in rows}
    a, _ = CI.piginet(rows, recs)
    b, _ = CI.scnet(rows, recs)
    with open(outp, "w") as f:
        for q in rows:
            f.write(json.dumps({"root_id": q["qid"], **a[q["qid"]], **b[q["qid"]]}) + "\n")
    print("scored", len(rows))


if __name__ == "__main__":
    if sys.argv[1] == "score_b":
        score_b(sys.argv[2]); sys.exit()
    {"score": lambda: score(sys.argv[2]), "metrics": lambda: metrics(*sys.argv[2:5])}[sys.argv[1]]()
