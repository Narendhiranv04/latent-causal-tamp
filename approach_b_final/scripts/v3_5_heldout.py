"""V3-5 held-out scorer comparison (plan V3 7.1 item 8): ONE shared set of physically labelled VALIDATION candidates (every (root, ordered
sequence) verified in the V2 / V3 caches; never trained on) scored by each scorer (V2 D/E/G/DIRECT vs V3 D/E/G/DIRECT, 3 seeds) ->
Z NLL, AUROC, ECE, Brier, mean p11 vs Z rate, by legacy class."""
import collections, json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np, torch
import evaluate as EV, search as S, xy as XY
ABF, V3 = Path(os.environ["ABF_ROOT"]), Path(os.environ["V3OUT"])
EV.SNAP = ABF / "snapshot/abf_9de85710c2a7103f"
out = {}
for dom in ("2d", "3d"):
    rows = {r["root_id"]: r for r in EV.rows_of(dom.upper(), "val")}
    lab = {}
    for p in (ABF / f"runs/v2/p5_{dom}/verify.jsonl", V3 / f"verify_{dom}.jsonl", V3 / f"verify_{dom}_laptop.jsonl"):
        for v in EV.jl(p):
            if v["root"] not in rows:
                continue
            for x in v["results"]:
                if not x["seq"]:
                    continue
                xv, yv = (x["x"] or {}).get("x"), (x["y"] or {}).get("y")
                if dom == "3d":
                    xv = xv if (x["x"] or {}).get("resolution", "EVALUATED") == "EVALUATED" else None
                    yv = yv if (x["y"] or {}).get("resolution", "EVALUATED") == "EVALUATED" else None
                z = 0 if (xv == 0 or yv == 0) else (1 if xv == 1 and yv == 1 else None)
                if z is not None:
                    lab[(v["root"], json.dumps(x["seq"]))] = z
    by_root = collections.defaultdict(list)
    for (rt, s), z in lab.items():
        by_root[rt].append((json.loads(s), z))
    res = {"n_candidates": len(lab), "n_roots": len(by_root), "z_rate": float(np.mean(list(lab.values())))}
    scorers = {f"V2_{a}_s{s}": ABF / f"runs/v2/p2_{dom}/{a}_s{s}/model.pt" for a in ("D", "E", "G", "DIRECT") for s in (0, 1, 2)}
    scorers.update({f"V3_{a}_s{s}": V3 / f"v3_5/p2_{dom}/{a}_s{s}/model.pt" for a in ("D", "E", "G", "DIRECT") for s in (0, 1, 2)})
    for name, path in scorers.items():
        if not path.exists():
            continue
        sc = S.Scorer(path)
        ys, ps, ks = [], [], []
        for rt, lst in by_root.items():
            pr = sc.score(S.Root(rows[rt], dom), [s for s, _ in lst])
            ys += [z for _, z in lst]; ps += [p["p11"] for p in pr]; ks += [rows[rt]["K_legacy"]] * len(lst)
        y, p = np.array(ys), np.clip(np.array(ps), 1e-6, 1 - 1e-6)
        res[name] = {"nll": float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()), "auroc": XY.auroc(y, p), "ece": XY.ece(y, p),
                     "brier": float(((p - y) ** 2).mean()), "mean_p11": float(p.mean()),
                     "nll_by_K": {K: float(-(y[np.array(ks) == K] * np.log(p[np.array(ks) == K]) + (1 - y[np.array(ks) == K]) * np.log(1 - p[np.array(ks) == K])).mean())
                                  for K in ("0", "1", "2", "3", "NONE") if (np.array(ks) == K).any()}}
    agg = {}
    for v in ("V2", "V3"):
        for a in ("D", "E", "G", "DIRECT"):
            ks_ = [k for k in res if k.startswith(f"{v}_{a}_s")]
            if ks_:
                agg[f"{v}_{a}"] = {m: [float(np.mean([res[k][m] for k in ks_])), float(np.std([res[k][m] for k in ks_]))] for m in ("nll", "auroc", "ece", "brier", "mean_p11")}
    res["mean_sd_over_seeds"] = agg
    out[dom] = res
    print(dom, res["n_candidates"], res["n_roots"], round(res["z_rate"], 3), json.dumps({k: {m: round(v[0], 3) for m, v in d.items()} for k, d in agg.items()}))
(V3 / "v3_5" / "HELDOUT_VAL_CANDIDATES.json").write_text(json.dumps(out, indent=1))
