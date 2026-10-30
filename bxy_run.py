"""Approach B X/Y phases 5-7: training (LB's optimiser / batches / clip / validation cadence / early stopping), validation-only selection
of lambda_J and of the cost/risk rule, then ONE frozen test evaluation of LB, XY-uncoupled, XY-quadratic, XY-quadratic-noJ (3 seeds).

Selection (methodology §6.3): admit p_succ(r) >= eta (zero-move candidate always scored, never dropped), choose argmin
C(r) = -log p_succ(r) + alpha m(r) + beta C_d(r) + gamma J_hat(r), deterministic catalogue-order tie break, abstain if nothing is admitted.
Outcome of a choice = the recorded full-execution check of that candidate (B y; original y for the empty repair), never shown to a scorer."""
from __future__ import annotations

import copy
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

import bxy_core as X
import config as cf

OUT = Path("runs/approach_b/bxy")
LB_OUT = Path("runs/approach_b/bd2d_lb_v1")
PITCH = 0.08                                                     # C_d normalizing length L (one cell)
GRID = {"eta": (0.0, 0.05, 0.1, 0.2, 0.3, 0.5), "alpha": (0.0, 0.25, 0.5, 1.0), "beta": (0.0, 0.1, 0.25), "gamma": (0.0, 0.25, 0.5, 1.0)}
LAMBDA_J = (0.1, 0.3, 1.0)


# ------------------------------------------------------------------ training
def fit(arm, seed, tr, va, lam_j, updates=3000, every=20, patience=15, tol=1e-3):
    torch.manual_seed(seed)
    np.random.seed(seed)
    m = X.build(arm)
    opt = torch.optim.AdamW(m.parameters(), lr=1e-3, weight_decay=1e-4)
    rng, n = np.random.default_rng(seed), len(tr)
    p = np.full(n, 1.0 / n)                                      # = abc8.RootSampler when every root is in one kappa group (as for LB here)
    hist, best, stale = [], (float("inf"), None, -1), 0
    for u in range(updates):
        batch = sorted(rng.choice(n, size=min(12, n), replace=False, p=p).tolist())
        opt.zero_grad()
        tot, rec = X.total(m, [tr[i] for i in batch], lam_j)
        if not torch.isfinite(tot):
            hist.append({"update": u, "nonfinite": True})
            break
        tot.backward()
        pre = float(torch.nn.utils.clip_grad_norm_(m.parameters(), 10.0))
        opt.step()
        rec |= {"update": u, "total": float(tot.detach()), "grad_pre": pre, "clipped": pre > 10.0}
        if (u + 1) % every == 0:
            with torch.no_grad():
                rec["val"] = X.total(m, va, 0.0)[1]["nll"]
            if rec["val"] < best[0] * (1 - tol) if np.isfinite(best[0]) else True:
                best, stale = (rec["val"], copy.deepcopy(m.state_dict()), u + 1), 0
            else:
                stale += 1
        hist.append(rec)
        if stale >= patience:
            break
    m.load_state_dict(best[1])
    return m.eval(), {"history": hist, "best_update": best[2], "val_root_nll": best[0], "updates_run": len(hist), "stopped_early": stale >= patience,
                      "params": sum(q.numel() for q in m.parameters()), "lambda_J": lam_j}


def train(arm, seed, lam_j, tag=None) -> dict:
    tr, va = X.views("train"), X.views("val")
    c0, w0 = time.process_time(), time.time()
    m, rec = fit(arm, seed, tr, va, lam_j)
    name = tag or f"{arm}-s{seed}"
    ck = OUT / "ckpt" / f"{name}.pt"
    for d in ("ckpt", "train"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    torch.save(m.state_dict(), ck)
    import p17_eval as pe
    res = {"arm": arm, "seed": seed, **{k: v for k, v in rec.items() if k != "history"}, "train_cpu_s": round(time.process_time() - c0, 1),
           "train_wall_s": round(time.time() - w0, 1), "checkpoint": pe.sha(ck), "train_roots": len(tr), "val_roots": len(va)}
    cf.write_json(OUT / "train" / f"{name}.json", res | {"history": [{k: h.get(k) for k in ("update", "total", "nll", "travel", "val")} for h in rec["history"]]})
    return res


def load(arm, name):
    m = X.build(arm)
    m.load_state_dict(torch.load(OUT / "ckpt" / f"{name}.pt", weights_only=True))
    return m.eval()


# ------------------------------------------------------------------ predictions (no label enters a score)
def cd(rt, seq):
    c0 = rt["cells0"]
    return sum(np.hypot(d % 8 - c0[o] % 8, d // 8 - c0[o] // 8) * PITCH for o, d in seq) / PITCH


@torch.no_grad()
def predict_xy(m, rts) -> dict:
    out = {}
    for rt in rts:
        b, a, w, _ = m.coeffs(rt)
        mg = X.marginals(b, a, w, rt["parent"])
        xi, yi = {q: i for i, q in enumerate(rt["x_keys"])}, {q: i for i, q in enumerate(rt["y_keys"])}
        rows = []
        for c in rt["catalogue"]:
            seq = [(o, int(d)) for o, d in c["seq"]]
            if seq:
                i = xi[c["x"]]
                p, px, jh = float(mg["psucc"][i]), float(mg["px"][i]), float(torch.nn.functional.softplus(m.cost(m.order(rt["R"], rt["x_seqs"][i])[1])[0]))
            else:
                p, px, jh = float(mg["py"][yi[c["y"]]]), 1.0, 0.0           # zero-move: X = 1 by definition, p_succ = P(Y_0 = 1)
            rows.append({"seq": c["seq"], "role": c["role"], "m": len(seq), "cd": cd(rt, seq), "p": p, "px": px, "py": float(mg["py"][yi[c["y"]]]),
                         "w": float(w[xi[c["x"]]]) if seq else None, "J_hat": jh, "y_full": c["y_full"], "travel": c["travel"], "y_key": c["y"], "x_key": c["x"]})
        out[rt["key"]] = {"cands": rows, "K": rt["verified_K"], "y": {q: float(mg["py"][i]) for q, i in yi.items()},
                          "x": {q: float(mg["px"][i]) for q, i in xi.items()}, "w_all": [float(v) for v in w]}
    return out


def predict_lb(seed, split) -> dict:
    """LB prior marginals saved by bxy_lb (candidate queries in catalogue order; scene / original queries)."""
    import bxy_data as bd
    P = json.loads((LB_OUT / f"PREDICTIONS_s{seed}.json").read_text())[split]
    R, out = bd.roots(), {}
    for k, v in P.items():
        rec = R[k]
        cat = bd.catalogue(rec)
        rows = [{"seq": [list(a) for a in c["seq"]], "role": c["role"], "m": len(c["seq"]), "cd": cd({"cells0": bd.cells0(rec)}, c["seq"]), "p": r["p"],
                 "J_hat": 0.0, "y_full": c["y_full"], "travel": c["travel"]} for c, r in zip(cat, v["candidates"])]
        y = {bd.ykey(k, rec, edit={p.split(">")[0]: int(p.split(">")[1]) for p in s["query"].split(":", 2)[2].split(".")}): s["p"] for s in v["scene"]}
        out[k] = {"cands": rows, "K": rec["verified_K"], "y": y | {bd.ykey(k, rec, []): v["candidates"][0]["p"]}}
    return out


# ------------------------------------------------------------------ selection rule and evaluation
def choose(cands, eta, alpha, beta, gamma):
    best = None
    for i, c in enumerate(cands):
        if c["p"] < eta:
            continue
        cost = -np.log(max(c["p"], 1e-12)) + alpha * c["m"] + beta * c["cd"] + gamma * c["J_hat"]
        if best is None or cost < best[0] - 1e-12:
            best = (cost, i)
    return None if best is None else best[1]


def select_eval(P, rule) -> dict:
    rows = []
    for k, v in sorted(P.items()):
        i = choose(v["cands"], **rule) if isinstance(rule, dict) else rule(v["cands"])
        cs = v["cands"]
        ok = [c for c in cs if c["y_full"] == 1]
        c = cs[i] if i is not None else None
        rows.append({"root": k, "K": v["K"], "chosen": i, "success": int(c is not None and c["y_full"] == 1), "abstain": c is None,
                     "m": c["m"] if c else None, "cd": c["cd"] if c else None, "travel": c["travel"] if c and c["y_full"] == 1 else None,
                     "optimal": int(c is not None and c["y_full"] == 1 and c["m"] == min(x["m"] for x in ok)), "available": int(bool(ok)),
                     "false_repair": int(cs[0]["y_full"] == 1 and c is not None and c["m"] > 0)})
    f = lambda key: float(np.mean([r[key] for r in rows]))  # noqa: E731
    mm = [r["m"] for r in rows if r["m"] is not None]
    feas = [r for r in rows if P[r["root"]]["cands"][0]["y_full"] == 1]
    return {"roots": len(rows), "success": f("success"), "abstain": f("abstain"), "optimal": f("optimal"), "available": f("available"),
            "mean_m": float(np.mean(mm)) if mm else None, "mean_cd": float(np.mean([r["cd"] for r in rows if r["cd"] is not None])) if mm else None,
            "mean_travel_success": float(np.mean([r["travel"] for r in rows if r["travel"] is not None])) if any(r["travel"] for r in rows) else None,
            "false_repair_rate_on_original_feasible": float(np.mean([r["false_repair"] for r in feas])) if feas else None, "rows": rows}


def tune(P, gammas=GRID["gamma"]) -> dict:
    """Validation-only grid: max success, then fewer moves, then less displacement, then grid order."""
    best = None
    for eta, al, be, ga in itertools.product(GRID["eta"], GRID["alpha"], GRID["beta"], gammas):
        r = {"eta": eta, "alpha": al, "beta": be, "gamma": ga}
        e = select_eval(P, r)
        key = (-e["success"], e["mean_m"] if e["mean_m"] is not None else 9, e["mean_cd"] if e["mean_cd"] is not None else 99)
        if best is None or key < best[0]:
            best = (key, r, {k: v for k, v in e.items() if k != "rows"})
    return {"rule": best[1], "val": best[2]}


BASELINES = {"NOOP": lambda cs: 0, "SHORTEST_NONEMPTY": lambda cs: min(range(len(cs)), key=lambda i: (cs[i]["m"] == 0 and len(cs) > 1, cs[i]["m"], i))}


def verify_first(P) -> dict:
    """Oracle reference: verify candidates in (moves, catalogue) order until the recorded check passes; cost = verifications."""
    n, ok = [], []
    for v in P.values():
        order = sorted(range(len(v["cands"])), key=lambda i: (v["cands"][i]["m"], i))
        hit = next((j for j, i in enumerate(order) if v["cands"][i]["y_full"] == 1), None)
        ok.append(hit is not None)
        n.append(hit + 1 if hit is not None else len(order))
    return {"success": float(np.mean(ok)), "mean_verifications": float(np.mean(n))}


def prob_metrics(y, p) -> dict:
    import bxy_lb as L
    out = L.metrics(y, p)
    if out.get("n"):
        y, p = np.asarray(y, float), np.asarray(p, float)
        bins = np.minimum((p * 10).astype(int), 9)
        out["ece10"] = float(sum(abs(p[bins == k].mean() - y[bins == k].mean()) * (bins == k).mean() for k in range(10) if (bins == k).any()))
    return out


def y_obs(split) -> dict:
    S = json.loads(Path("runs/approach_b/bxy/SIDECAR.json").read_text())
    import bxy_data as bd
    return {k: S[k]["y_obs"] for k, rec in bd.roots().items() if bd.split_of(rec) == split}


def metrics(P, split, xy=True) -> dict:
    Yo = y_obs(split)
    yy = [(v["y"], P[k]["y"].get(q)) for k, d in Yo.items() for q, v in d.items() if k in P and P[k]["y"].get(q) is not None]
    cands = [c for v in P.values() for c in v["cands"] if c["m"]]
    out = {"Y_observed": prob_metrics([a for a, _ in yy], [b for _, b in yy]),
           "psucc_vs_full_execution_check": prob_metrics([c["y_full"] for c in cands], [c["p"] for c in cands])}
    if xy:
        S = json.loads(Path("runs/approach_b/bxy/SIDECAR.json").read_text())
        xo = [(v["y"], P[k]["x"][q]) for k in P for q, v in S[k]["x_obs"].items() if q in P[k]["x"]]
        out["X_observed(all 0)"] = {"n": len(xo), "mean_p": float(np.mean([b for _, b in xo])) if xo else None,
                                    "brier": float(np.mean([(b - a) ** 2 for a, b in xo])) if xo else None, "auroc": "N/A (one class)"}
        w = np.array([x for v in P.values() for x in v["w_all"]])
        out["w"] = {"n": int(len(w)), "mean": float(w.mean()) if len(w) else None, "sd": float(w.std()) if len(w) else None,
                    "frac_abs_gt_0.5": float((abs(w) > 0.5).mean()) if len(w) else None}
    return out


def order_pairs(P) -> dict:
    """Same-endpoint different-order candidate pairs (one shared Y, two X) with discordant recorded checks: does the score rank the passing order first?"""
    n, conc, pairs = 0, 0, 0
    for v in P.values():
        cs = v["cands"]
        for i, j in itertools.combinations(range(len(cs)), 2):
            a, b = cs[i], cs[j]
            if a["m"] and a["m"] == b["m"] and sorted(map(tuple, a["seq"])) == sorted(map(tuple, b["seq"])) and a["seq"] != b["seq"]:
                pairs += 1
                if a["y_full"] != b["y_full"]:
                    n += 1
                    conc += (a["p"] > b["p"]) == (a["y_full"] > b["y_full"])
    return {"same_endpoint_reordered_pairs": pairs, "discordant": n, "ranked_correctly": conc}


def boot(rows_a, rows_b, key="success", B=2000, seed=0):
    a, b = np.array([r[key] for r in rows_a], float), np.array([r[key] for r in rows_b], float)
    rng = np.random.default_rng(seed)
    d = [np.mean((a - b)[rng.integers(0, len(a), len(a))]) for _ in range(B)]
    return {"diff": float(np.mean(a - b)), "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]}


# ------------------------------------------------------------------ phase orchestration
SEEDS = (0, 1, 2)
XY_ARMS = ("XY-uncoupled", "XY-quadratic", "XY-quadratic-noJ")


def lam_star() -> float:
    """lambda_J of the coupled arm chosen by validation joint NLL (smaller lambda on ties); compared against lambda_J = 0 by the noJ arm."""
    v = {l: json.loads((OUT / "train" / f"XY-quadratic-lam{l}-s0.json").read_text())["val_root_nll"] for l in LAMBDA_J}
    return min(v, key=lambda l: (round(v[l], 9), l)), v


def name(arm, seed):
    return f"{arm}-s{seed}"


def jobs():
    """Remaining phase-7 trainings (seed 0 of XY-quadratic is the selected lambda run)."""
    lam, _ = lam_star()
    return [(arm, s, 0.0 if arm.endswith("noJ") else lam) for arm in XY_ARMS for s in SEEDS if not (arm == "XY-quadratic" and s == 0)]


def ckpt_name(arm, seed):
    lam, _ = lam_star()
    return f"XY-quadratic-lam{lam}-s0" if (arm, seed) == ("XY-quadratic", 0) else name(arm, seed)


def freeze() -> dict:
    """Validation only: per (arm, seed) the selection rule; LB uses gamma = 0 (its travel head is untrained, lambda_travel = 0)."""
    import p17_eval as pe
    lam, lv = lam_star()
    fr = {"lambda_J": lam, "lambda_J_val_nll": lv, "selection_grid": GRID, "models": {}}
    va = X.views("val", full=True)
    for s in SEEDS:
        fr["models"][f"LB-s{s}"] = {"checkpoint": pe.sha(LB_OUT / "ckpt" / f"BXY-LB-s{s}.pt"), **tune(predict_lb(s, "val"), gammas=(0.0,))}
        for arm in XY_ARMS:
            n = ckpt_name(arm, s)
            fr["models"][name(arm, s)] = {"checkpoint": pe.sha(OUT / "ckpt" / f"{n}.pt"), "ckpt": n,
                                          **tune(predict_xy(load(arm, n), va), gammas=(0.0,) if arm.endswith("noJ") else GRID["gamma"])}
    fr["frozen_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    cf.write_json(OUT / "FROZEN.json", fr)
    return fr


def final() -> dict:
    """The single test evaluation; refuses to run unless FROZEN.json exists (test never used before)."""
    fr = json.loads((OUT / "FROZEN.json").read_text())
    te = X.views("test", full=True)
    res, P = {"frozen": str(OUT / "FROZEN.json"), "arms": {}}, {}
    for key, cfgm in fr["models"].items():
        arm, s = key.rsplit("-s", 1)
        P[key] = predict_lb(int(s), "test") if arm == "LB" else predict_xy(load(arm, cfgm["ckpt"]), te)
        sel = select_eval(P[key], cfgm["rule"])
        res["arms"][key] = {"rule": cfgm["rule"], "selection": {k: v for k, v in sel.items() if k != "rows"}, "rows": sel["rows"],
                            "metrics": metrics(P[key], "test", xy=arm != "LB"), "order_pairs": order_pairs(P[key]),
                            "by_K": {str(k): float(np.mean([r["success"] for r in sel["rows"] if str(r["K"]) == str(k)]))
                                     for k in sorted({str(r["K"]) for r in sel["rows"]})}}
    any_p = next(iter(P.values()))
    res["baselines"] = {n_: {k: v for k, v in select_eval(any_p, f).items() if k != "rows"} for n_, f in BASELINES.items()}
    res["baselines"]["VERIFY_FIRST(oracle checks)"] = verify_first(any_p)
    res["paired_bootstrap"] = {}
    for s in SEEDS:
        a = lambda k: res["arms"][f"{k}-s{s}"]["rows"]  # noqa: E731
        res["paired_bootstrap"][f"s{s}"] = {"XY-quadratic - LB": boot(a("XY-quadratic"), a("LB")), "XY-quadratic - XY-uncoupled": boot(a("XY-quadratic"), a("XY-uncoupled")),
                                            "XY-quadratic - XY-quadratic-noJ": boot(a("XY-quadratic"), a("XY-quadratic-noJ"))}
    cf.write_json(OUT / "EVAL_P7.json", res)
    cf.write_json(OUT / "PREDICTIONS_P7_test.json", P)
    return res


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "train":
        print(json.dumps({k: v for k, v in train(sys.argv[2], int(sys.argv[3]), float(sys.argv[4]), sys.argv[5] if len(sys.argv) > 5 else None).items()}, indent=1))
    elif cmd == "jobs":
        print("\n".join(f"{a} {s} {l}" for a, s, l in jobs()))
    elif cmd == "freeze":
        print(json.dumps({k: v["rule"] for k, v in freeze()["models"].items()}, indent=1))
    elif cmd == "final":
        r = final()
        print(json.dumps({k: v["selection"] | {"Y": v["metrics"]["Y_observed"]} for k, v in r["arms"].items()}, indent=1, default=str))
