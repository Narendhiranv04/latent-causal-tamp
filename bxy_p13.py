"""BXY-P13 failure attribution of the P12 runs (evaluator-only, read-only; no optimizer step, no teacher query, no test root).

  reproduce      re-run the committed P12 evaluator and require EVALUATION.json to match exactly (accounting excluded)
  categories     PRIMARY-rule choices on PRIMARY_DEV split into SUCCESS / NO_REPAIR_AVAILABLE / MISSED_RANKED_BELOW_NOOP /
                 MISSED_PENALTY_REJECTED / WRONG_REPAIR_X0 / WRONG_REPAIR_Y0 / WRONG_REPAIR_UNDECIDED (infeasible roots) and
                 CORRECT_NOOP / UNNECESSARY_REPAIR_OK / UNNECESSARY_REPAIR_FAIL (feasible roots)
  ranking        rank of the best verified repair by p and by PRIMARY cost, top-k recovery vs the random-order expectation, within-root AUROC
  oracles        evaluator-only substitution of observed Y0 / edited-scene Y / X into p_succ = P(Y=1) P(X=1|Y=1) and of a penalty-free
                 cost; Shapley attribution of the corrective-success gap over {Y0, Y_edit, X}. DIAGNOSTIC UPPER BOUNDS, never deployable
  y diagnostics  P(Y0) discrimination, edit contrast (does the model predict that a verified-feasible edit beats the infeasible S0?)
  loss audit     exact split of the root NLL into Y0 / edited Y / X|observed Y / X with Y marginalized, query-count dependence, read-only
                 gradient norms and cosines per component at initialization and at the restored checkpoint, P12 clipping history
  in-sample      the 75 CROSSFIT checkpoints re-scored (no_grad) on their own training roots: generalization gap vs underfitting
  geometry probe scorer-available hand-made geometry (object / goal / base positions and radii only) -> logistic regression on the same folds
Model-facing inputs are never modified; oracle values enter only evaluator-side copies of the prediction rows."""
from __future__ import annotations

import collections
import itertools
import json
import time
from math import comb
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

import bxy_p11 as P
import bxy_p12_eval as E
import bxy_p12_run as R

OUT = Path("runs/approach_b/bxy_p13_v1")
CACHE = OUT / "insample"                                   # local, git-ignored raw predictions (hashes committed)
TIER = "PRIMARY_DEV"
SUBS = ("Y0", "Y", "X")
KS = (1, 2, 3, 5)


def sig(x):
    return 1.0 / (1.0 + np.exp(-np.asarray(x, float)))


def context() -> dict:
    sc, D, Rr, I = P.load()
    V = P.build(sc=sc, D=D, R=Rr, I=I)
    by = {sv["key"]: (sv, lab, ev) for sv, lab, ev in V}
    xr, yr = {r["x_key"]: r for r in sc["x_queries"]}, {r["y_key"]: r for r in sc["y_queries"]}
    trav = {k: E.witnessed_travel(sv, lab, ev, (xr, yr)) for k, (sv, lab, ev) in by.items()}
    F_ = E.finished()
    return {"by": by, "trav": trav, "F": F_, "tiers": E.model_sets(F_, V), "R": Rr, "D": D, "design": R.design()}


def reproduce() -> dict:
    """Re-run bxy_p12_eval.evaluate() and compare with the committed EVALUATION.json (only 'accounting' may differ)."""
    new = json.loads(json.dumps(E.evaluate(), sort_keys=True, default=str))
    old = json.loads((E.OUT / "EVALUATION.json").read_text())
    new.pop("accounting"), old.pop("accounting")
    diff = [k for k in sorted(set(new["tiers"]) | set(old["tiers"])) if new["tiers"].get(k) != old["tiers"].get(k)]
    return {"identical": new == old, "differing_tiers": diff, "runs_evaluated": new["runs_evaluated"]}


# ------------------------------------------------------------------ evaluator-side rows
def rule(arm) -> dict:
    return E.rules_for(arm)["PRIMARY"]


def cost(r, ru) -> float:
    return -np.log(max(r["p"], 1e-12)) + ru["alpha"] * r["m"] + ru["beta"] * r["cd"] + ru["gamma"] * (r.get("J_hat") or 0.0)


def oracle_rows(arm, pred, sv, ev, subs) -> list:
    """Copy of the prediction rows with observed outcomes substituted (evaluator only). XY: p = P(Y_s=1) P(X_q=1|Y=1) with P(Y0), P(Y_s)
    or P(X|Y=1) replaced by the observed 0/1 where observed; DIRECT: 'Y0' replaces p(empty), 'S' replaces p by the decided success."""
    rows = [dict(r) for r in pred["cands"]]
    oy, ox = ev["obs_y"], ev["obs_x"]
    if P.ARMS[arm]["kind"] == "xy":
        c = pred["coeffs"]
        b, a, w = np.array(c["b"]), np.array(c["a"]), np.array(c["w"])
        for r in rows:
            if not r["admissible"]:
                continue
            if r["m"] == 0:
                r["p"] = float(oy[sv["y0"]]) if "Y0" in subs and sv["y0"] in oy else float(sig(b[sv["y0"]]))
                continue
            py = float(oy[r["yi"]]) if "Y" in subs and r["yi"] in oy else float(sig(b[r["yi"]]))
            px = float(ox[r["xi"]]) if "X" in subs and r["xi"] in ox else float(sig(a[r["xi"]] + w[r["xi"]]))
            r["p"] = py * px
    else:
        for r, e in zip(rows, ev["cands"]):
            if r["admissible"] and ((r["m"] == 0 and "Y0" in subs) or (r["m"] > 0 and "S" in subs)) and e["success"] is not None:
                r["p"] = float(e["success"])
    return rows


def auroc(items) -> float | None:
    pos, neg = [p for y, p in items if y == 1], [p for y, p in items if y == 0]
    if not pos or not neg:
        return None
    P_, N_ = np.array(pos)[:, None], np.array(neg)[None, :]
    return float(((P_ > N_) + 0.5 * (P_ == N_)).mean())


# ------------------------------------------------------------------ one prediction of one root
def category(rows, ev, i, ru) -> str:
    c = ev["cands"]
    ok = [j for j, e in enumerate(c) if e["success"] == 1 and rows[j]["admissible"] and rows[j]["m"] > 0]
    if ev["y0"] == 1:
        return "CORRECT_NOOP" if rows[i]["m"] == 0 else ("UNNECESSARY_REPAIR_OK" if c[i]["success"] == 1 else "UNNECESSARY_REPAIR_FAIL")
    if c[i]["success"] == 1:
        return "SUCCESS"
    if not ok:
        return "NO_REPAIR_AVAILABLE"
    if rows[i]["m"] == 0:
        return "MISSED_PENALTY_REJECTED" if max(rows[j]["p"] for j in ok) > rows[i]["p"] else "MISSED_RANKED_BELOW_NOOP"
    return "WRONG_REPAIR_X0" if c[i]["x"] == 0 else "WRONG_REPAIR_Y0" if c[i]["y"] == 0 else "WRONG_REPAIR_UNDECIDED"


def ranking(rows, ev, ru) -> dict | None:
    """Infeasible roots with >= 1 verified repair: rank (1 = best, ties half) of the best verified repair among admissible repairs by p,
    and among all admissible candidates (no-op included) by PRIMARY cost; top-k hit and its random-order expectation."""
    rep = [j for j, r in enumerate(rows) if r["admissible"] and r["m"] > 0]
    ok = [j for j in rep if ev["cands"][j]["success"] == 1]
    if ev["y0"] != 0 or not ok:
        return None
    pb = max(rows[j]["p"] for j in ok)
    rank_p = 1 + sum(rows[j]["p"] > pb for j in rep if j not in ok) + 0.5 * sum(rows[j]["p"] == pb for j in rep if j not in ok)
    adm = [j for j, r in enumerate(rows) if r["admissible"]]
    cb = min(cost(rows[j], ru) for j in ok)
    rank_c = 1 + sum(cost(rows[j], ru) < cb for j in adm if j not in ok)
    n, s = len(rep), len(ok)
    return {"n_repairs": n, "n_ok": s, "rank_p": float(rank_p), "rank_cost": int(rank_c), "p_best_ok": pb,
            "p_noop": next(r["p"] for r in rows if r["m"] == 0), "p_best_fail": max((rows[j]["p"] for j in rep if j not in ok), default=None),
            **{f"top{k}_p": int(rank_p <= k) for k in KS}, **{f"top{k}_cost": int(rank_c <= k) for k in KS},
            **{f"rand_top{k}": 1 - comb(n - s, min(k, n)) / comb(n, min(k, n)) for k in KS}}


def edit_contrast(pred, sv, ev) -> dict:
    """Matched Y comparisons inside one root: edited scenes whose observed Y differs from the observed Y0 (sign agreement of P(Y_s) - P(Y0))."""
    py = pred["vars"]["py"] or None
    oy, y0 = ev["obs_y"], ev["obs_y"].get(sv["y0"])
    if py is None or y0 is None:
        return {}
    pairs = [(s, y) for s, y in oy.items() if s != sv["y0"] and y != y0]
    sc = [1.0 if (py[s] - py[sv["y0"]]) * (y - y0) > 0 else 0.5 if py[s] == py[sv["y0"]] else 0.0 for s, y in pairs]
    lg = lambda p: float(np.log(np.clip(p, 1e-9, 1 - 1e-9) / (1 - np.clip(p, 1e-9, 1 - 1e-9))))  # noqa: E731
    return {"pairs": len(sc), "agree": float(np.mean(sc)) if sc else None, "dlogit": [(lg(py[s]) - lg(py[sv["y0"]])) * (1 if y > y0 else -1) for s, y in pairs]}


def within(pred, ev, sv) -> dict:
    rows, v = pred["cands"], pred["vars"]
    s = [(ev["cands"][j]["success"], r["p"]) for j, r in enumerate(rows) if r["admissible"] and r["m"] > 0 and ev["cands"][j]["success"] is not None]
    out = {"auc_succ": auroc(s)}
    if v["px"] is not None:
        out["auc_x"] = auroc([(y, v["px"][q]) for q, y in ev["obs_x"].items()])
        out["auc_y"] = auroc([(y, v["py"][q]) for q, y in ev["obs_y"].items() if q != sv["y0"]])
    return out


def root_diag(arm, pred, sv, ev, trav) -> dict:
    ru, rows = rule(arm), pred["cands"]
    i = P.choose(rows, ru)
    subsets = [()] + [c for n in (1, 2, 3) for c in itertools.combinations(SUBS, n)] if P.ARMS[arm]["kind"] == "xy" else [(), ("Y0",), ("S",), ("Y0", "S")]
    orc = {}
    for s in subsets:
        r2 = oracle_rows(arm, pred, sv, ev, s)
        orc["+".join(s) or "model"] = E.sel_row(r2, ev, P.choose(r2, ru), trav)["success"]
    nopen = E.sel_row(rows, ev, P.choose(rows, ru | {"alpha": 0.0, "gamma": 0.0, "beta": 0.0}), trav)
    return {"y0": ev["y0"], "stratum": ev["stratum"], "cat": category(rows, ev, i, ru), "success": E.sel_row(rows, ev, i, trav)["success"],
            "m": rows[i]["m"], "p_noop": next(r["p"] for r in rows if r["m"] == 0), "rank": ranking(rows, ev, ru), "oracle": orc,
            "nopen_success": nopen["success"], "nopen_m": rows[P.choose(rows, ru | {"alpha": 0.0, "gamma": 0.0, "beta": 0.0})]["m"],
            "edit": edit_contrast(pred, sv, ev), **within(pred, ev, sv)}


def diag_table(preds, C) -> dict:
    """{(arm, model): {root: diag}} over prediction sets {(arm, model): {root: pred}}."""
    return {key: {k: root_diag(key[0], pr, *C["by"][k][::2], C["trav"][k]) for k, pr in P_.items()} for key, P_ in preds.items()}


# ------------------------------------------------------------------ aggregation (seed / model mean per root, then mean over roots)
def per_root(T, arm, f) -> dict:
    acc = collections.defaultdict(list)
    for (a, _), t in T.items():
        if a == arm:
            for k, d in t.items():
                v = f(d)
                if v is not None:
                    acc[k].append(v)
    return {k: float(np.mean(v)) for k, v in acc.items()}


def summarize(T, C, arm) -> dict:
    m = lambda f: per_root(T, arm, f)  # noqa: E731
    mean = lambda d: (float(np.mean(list(d.values()))) if d else None, len(d))  # noqa: E731
    cats = collections.Counter(d["cat"] for (a, _), t in T.items() if a == arm for d in t.values())
    n_inf = sum(v for c, v in cats.items() if not c.startswith(("CORRECT", "UNNEC")))
    n_fea = sum(cats.values()) - n_inf
    out = {"categories": {c: {"rows": v, "share": v / (n_inf if not c.startswith(("CORRECT", "UNNEC")) else n_fea)} for c, v in sorted(cats.items())}}
    orc = sorted({s for (a, _), t in T.items() if a == arm for d in t.values() for s in d["oracle"]})
    out["oracle_succ_inf"] = {s: mean(m(lambda d, s=s: d["oracle"][s] if d["y0"] == 0 else None))[0] for s in orc}
    out["oracle_success_all"] = {s: mean(m(lambda d, s=s: d["oracle"][s]))[0] for s in orc}
    out["nopen"] = {"succ_inf": mean(m(lambda d: d["nopen_success"] if d["y0"] == 0 else None))[0],
                    "repair_rate_feasible": mean(m(lambda d: float(d["nopen_m"] > 0) if d["y0"] == 1 else None))[0],
                    "success_all": mean(m(lambda d: d["nopen_success"]))[0]}
    rk = lambda key: mean(m(lambda d: d["rank"][key] if d["rank"] else None))  # noqa: E731
    out["ranking"] = {"roots": rk("rank_p")[1], **{key: rk(key)[0] for key in ["rank_p", "rank_cost", "n_repairs", "n_ok", "p_best_ok", "p_noop"] +
                                                     [f"{p}{k}{s}" for k in KS for p, s in (("top", "_p"), ("top", "_cost"), ("rand_top", ""))]},
                      "p_best_fail": rk("p_best_fail")[0]}
    out["ranking"]["frac_best_ok_above_noop"] = mean(m(lambda d: float(d["rank"]["p_best_ok"] > d["rank"]["p_noop"]) if d["rank"] else None))[0]
    for key in ("auc_succ", "auc_x", "auc_y"):
        out[f"within_{key}"] = mean(m(lambda d, key=key: d.get(key)))
    out["edit_agree"] = mean(m(lambda d: d["edit"].get("agree")))
    for y in (0, 1):
        out[f"edit_agree_y0_{y}"] = mean(m(lambda d, y=y: d["edit"].get("agree") if d["y0"] == y else None))
    p0 = m(lambda d: d["p_noop"])
    out["y0_auroc"] = auroc([(C["by"][k][2]["y0"], v) for k, v in p0.items()])
    out["p_noop_mean"] = {str(y): float(np.mean([v for k, v in p0.items() if C["by"][k][2]["y0"] == y])) for y in (0, 1)}
    return out


def shapley(orc: dict) -> dict:
    """Shapley values of {Y0, Y, X} for the oracle corrective-success function v(S) (v = orc['+'.join(S)], v(empty) = orc['model'])."""
    v = lambda S: orc["+".join(s for s in SUBS if s in S) or "model"]  # noqa: E731
    out = {}
    for i in SUBS:
        rest = [s for s in SUBS if s != i]
        out[i] = float(sum(comb(2, len(S)) ** -1 / 3 * (v(set(S) | {i}) - v(set(S))) for n in range(3) for S in itertools.combinations(rest, n)))
    return out


def paired_oracle(T, arm, s) -> dict:
    a = per_root(T, arm, lambda d: d["oracle"][s] if d["y0"] == 0 else None)
    b = per_root(T, arm, lambda d: d["oracle"]["model"] if d["y0"] == 0 else None)
    return P.cluster_boot(a, b, B=E.B)


# ------------------------------------------------------------------ exact NLL decomposition (torch; used for values and gradients)
def nll_parts(Cf, sv, ox, oy) -> dict:
    """-log_evidence split exactly: Y0 term, edited-Y terms and X terms of observed-Y scenes (additive), and the marginalized terms of
    scenes whose Y is unobserved (X children only). The sum equals -bxy_p11.log_evidence (tested)."""
    b, a, w = Cf["b"], Cf["a"], Cf["w"]
    lp = lambda u, y: -F.softplus(-u) if y == 1 else -F.softplus(u)  # noqa: E731
    z = torch.zeros((), dtype=b.dtype)
    out = {"y0": z, "y_edit": z, "x_obs_y": z, "x_mix": z}
    kids = collections.defaultdict(list)
    for q in ox:
        kids[sv["parent"][q]].append(q)
    for s in range(len(b)):
        if s in oy:
            out["y0" if s == sv["y0"] else "y_edit"] = out["y0" if s == sv["y0"] else "y_edit"] - lp(b[s], oy[s])
            for q in kids[s]:
                out["x_obs_y"] = out["x_obs_y"] - lp(a[q] + w[q] * oy[s], ox[q])
        elif kids[s]:
            col = [lp(b[s], y) + sum(lp(a[q] + w[q] * y, ox[q]) for q in kids[s]) for y in (0, 1)]
            out["x_mix"] = out["x_mix"] - torch.logsumexp(torch.stack(col), 0)
    return out


def direct_parts(Cf, sv, lab) -> dict:
    lg = lambda q: Cf["b"][sv["y0"]] if q is None else Cf["a"][q]  # noqa: E731
    bce = lambda q, y: F.binary_cross_entropy_with_logits(lg(q), torch.tensor(float(y), dtype=Cf["b"].dtype))  # noqa: E731
    z = torch.zeros((), dtype=Cf["b"].dtype)
    return {"y0": sum((bce(q, y) for q, y in lab["succ"].items() if q is None), z), "succ_repair": sum((bce(q, y) for q, y in lab["succ"].items() if q is not None), z)}


def loss_census(C) -> dict:
    """Per-root query counts and the P12 OOF coefficient NLL split (XY arms), PRIMARY_DEV."""
    preds = C["tiers"][TIER]
    out = {}
    for arm in E.XY:
        rows = []
        for (a, s), P_ in preds.items():
            if a != arm:
                continue
            for k, pr in P_.items():
                sv, lab, ev = C["by"][k]
                Cf = {n: torch.tensor(pr["coeffs"][n], dtype=torch.float64) for n in ("b", "a", "w")}
                parts = {n: float(v) for n, v in nll_parts(Cf, sv, lab["obs_x"], lab["obs_y"]).items()}
                rows.append({"root": k, "n_x": len(lab["obs_x"]), "n_y": len(lab["obs_y"]), **parts})
        tot = {n: float(np.sum([r[n] for r in rows])) for n in ("y0", "y_edit", "x_obs_y", "x_mix")}
        nq = np.array([r["n_x"] + r["n_y"] for r in rows])
        nl = np.array([sum(r[n] for n in tot) for r in rows])
        out[arm] = {"share_of_nll": {n: v / sum(tot.values()) for n, v in tot.items()}, "mean_terms_per_root": {"x": float(np.mean([r["n_x"] for r in rows])),
                    "y_edit": float(np.mean([r["n_y"] - 1 for r in rows])), "y0": 1.0}, "corr_root_nll_vs_queries": float(np.corrcoef(nq, nl)[0, 1]),
                    "mean_root_nll": float(nl.mean()), "y0_nll_per_term": tot["y0"] / len(rows),
                    "y_edit_nll_per_term": tot["y_edit"] / max(1, sum(r["n_y"] - 1 for r in rows)),
                    "query_quartiles": [float(x) for x in np.percentile(nq, [25, 50, 75])]}
    return out


# ------------------------------------------------------------------ read-only checkpoint analyses
def load_model(rid) -> P.Model:
    spec = json.loads((E.OUT / "runs" / R.safe(rid) / "RESULT.json").read_text())["spec"]
    m = P.build_model(spec["arm"])
    m.load_state_dict(torch.load(E.OUT / "runs" / R.safe(rid) / "best.pt", weights_only=True))
    return m.eval()


def cv_runs(C, arms=None) -> dict:
    return {rid: spec for rid, (spec, _, _) in C["F"].items() if spec["phase"] == "CROSSFIT" and (arms is None or spec["arm"] in arms)}


def fold_sets(C, spec) -> dict:
    return R.root_sets(spec, C["design"])


def insample(C, arms=None) -> dict:
    """{(arm, (seed, fold)): {root: pred}} on each CROSSFIT model's own TRAINING roots restricted to the 176 TRAIN roots (no_grad)."""
    torch.set_num_threads(1)
    CACHE.mkdir(parents=True, exist_ok=True)
    out = {}
    for rid, spec in sorted(cv_runs(C, arms).items()):
        f = CACHE / f"{R.safe(rid)}.json"
        if f.exists():
            pr = json.loads(f.read_text())
        else:
            m = load_model(rid)
            pr = {k: R.predict_root(m, C["by"][k][0]) for k in fold_sets(C, spec)["train"] if C["by"][k][2]["split"] == "train"}
            f.write_text(json.dumps(pr))
        out[(spec["arm"], (spec["seed"], spec["train"]))] = pr
    return out


def grad_audit(C, arm, n_batches=4, seed=0) -> dict:
    """Read-only gradients of the batch objective and of each NLL component on random 12-root training batches of every CROSSFIT model
    of `arm`, at initialization (the seeded fresh model) and at the restored checkpoint. No optimizer exists here."""
    torch.set_num_threads(1)
    res = {"init": [], "best": []}
    lam = 0.0
    for rid, spec in sorted(cv_runs(C, [arm]).items()):
        lam = float(json.loads((E.OUT / "runs" / R.safe(rid) / "RESULT.json").read_text())["lambda_J"] or 0.0)
        keys = [k for k in fold_sets(C, spec)["train"]]
        rng = np.random.default_rng(seed)
        for state in ("init", "best"):
            m = P.build_model(arm, spec["seed"]) if state == "init" else load_model(rid)
            m.train()
            for _ in range(n_batches):
                idx = sorted(rng.choice(len(keys), size=P.TRAIN["batch_roots"], replace=False).tolist())
                comp = collections.defaultdict(list)
                jp, jo = [], []
                for i in idx:
                    sv, lab, _ = C["by"][keys[i]]
                    Cf = m.coeffs(sv)
                    parts = nll_parts(Cf, sv, lab["obs_x"], lab["obs_y"]) if m.family == "xy" else direct_parts(Cf, sv, lab)
                    for n, v in parts.items():
                        comp[n].append(v)
                    jp += [Cf["J0"] if a is None else Cf["J"][a] for a, _, _ in lab["j"]]
                    jo += [j for *_, j in lab["j"]]
                L = {n: torch.stack(v).mean() for n, v in comp.items()}
                L = {n: v for n, v in L.items() if v.requires_grad}           # a component absent from every batch root is a constant
                if lam and P.ARMS[arm]["travel"] and jp:
                    L["travel"] = lam * F.huber_loss(torch.log1p(torch.stack(jp)), torch.log1p(torch.tensor(jo, dtype=torch.float64)), reduction="sum") / len(jp)
                ps = [p for p in m.parameters() if p.requires_grad]
                G = {n: torch.cat([g.reshape(-1) if g is not None else torch.zeros(p.numel(), dtype=torch.float64) for g, p in
                                   zip(torch.autograd.grad(v, ps, retain_graph=True, allow_unused=True), ps)]) for n, v in L.items()}
                tot = sum(G.values())
                res[state].append({"total_norm": float(tot.norm()), "loss": {n: float(v) for n, v in L.items()},
                                   "norm": {n: float(g.norm()) for n, g in G.items()},
                                   "cos_to_rest": {n: float(F.cosine_similarity(g, tot - g, 0)) for n, g in G.items()}})
    agg = {}
    for st, rows in res.items():
        names = sorted({n for r in rows for n in r["norm"]})
        agg[st] = {"batches": len(rows), "total_norm_median": float(np.median([r["total_norm"] for r in rows])),
                   "frac_over_clip": float(np.mean([r["total_norm"] > P.TRAIN["clip_norm"] for r in rows])),
                   "norm_median": {n: float(np.median([r["norm"][n] for r in rows])) for n in names},
                   "loss_mean": {n: float(np.mean([r["loss"][n] for r in rows])) for n in names},
                   "cos_to_rest_median": {n: float(np.median([r["cos_to_rest"][n] for r in rows])) for n in names}}
    return {"lambda_J": lam, "summary": agg, "batches": res}


def clip_history(C) -> dict:
    """P12 training histories: clipping by phase, gradient norm vs batch NLL."""
    out = {}
    for arm in E.ARMS:
        g, early, late, nll = [], [], [], []
        for rid, (spec, res, _) in C["F"].items():
            if spec["arm"] != arm:
                continue
            h = json.loads((E.OUT / "runs" / R.safe(rid) / "history.json").read_text())
            for r in h:
                if "grad_pre" in r:
                    g.append(r["grad_pre"])
                    nll.append(r["nll"])
                    (early if r["update"] < 100 else late).append(r["grad_pre"] > P.TRAIN["clip_norm"])
        out[arm] = {"updates": len(g), "clipped": float(np.mean(np.array(g) > P.TRAIN["clip_norm"])), "clipped_first100": float(np.mean(early)),
                    "clipped_after100": float(np.mean(late)), "grad_pre_quartiles": [float(x) for x in np.percentile(g, [25, 50, 75])],
                    "corr_grad_vs_batch_nll": float(np.corrcoef(g, nll)[0, 1])}
    return out


# ------------------------------------------------------------------ geometry probe (scorer-available inputs only)
def seg_dist(p, a, b) -> np.ndarray:
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1)


def geo_features(Rt, edit: dict) -> list:
    """Hand-made clearances of one (edited) scene from the scorer's own tensors: object centres / radii / target flag, robot base, goal."""
    xy = Rt.xy0.numpy().copy()
    for o, p in edit.items():
        xy[int(o)] = p
    r, t = Rt.flags[:, 0].numpy(), Rt.tid
    base, goal = Rt.base.numpy(), Rt.goal.numpy()
    o = [i for i in range(len(xy)) if i != t]
    if not o:
        return [1.0, 1.0, 1.0, 1.0, 0.0, 0.0, float(np.linalg.norm(xy[t] - base)), float(np.linalg.norm(goal - xy[t]))]
    P_, ro = xy[o], r[o]
    d_t = np.linalg.norm(P_ - xy[t], axis=1) - ro - r[t]
    return [float(d_t.min()), float((seg_dist(P_, base, xy[t]) - ro).min()), float((seg_dist(P_, xy[t], goal) - ro).min()),
            float((np.linalg.norm(P_ - goal, axis=1) - ro).min()), float((d_t < 0.06).sum()), float((d_t < 0.12).sum()),
            float(np.linalg.norm(xy[t] - base)), float(np.linalg.norm(goal - xy[t]))]


def geometry_probe(C) -> dict:
    """Logistic regression on geo_features of every observed Y scene, trained on each P12 fold's TRAIN-root training set and scored on its
    held-out TRAIN roots (the same folds as the P12 OOF predictions); compared with XY-quadratic OOF P(Y) on the identical scenes."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    rows = {}
    for k, (sv, lab, ev) in C["by"].items():
        if ev["split"] == "train":
            rows[k] = [(s, y, geo_features(sv["R"], sv["y_poses"][s])) for s, y in lab["obs_y"].items()]
    pred = {}
    for rid, spec in sorted(cv_runs(C, ["XY-quadratic"]).items()):
        if spec["seed"] != 0:
            continue
        st = fold_sets(C, spec)
        tr = [(y, f) for k in st["train"] if k in rows for _, y, f in rows[k]]
        clf = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000)).fit([f for _, f in tr], [y for y, _ in tr])
        for k in st["predict"]:
            if k in rows:
                pred[k] = {s: float(clf.predict_proba([f])[0, 1]) for s, _, f in rows[k]}
    net = collections.defaultdict(lambda: collections.defaultdict(list))
    for (a, _), P_ in C["tiers"][TIER].items():
        if a == "XY-quadratic":
            for k, pr in P_.items():
                for s in C["by"][k][1]["obs_y"]:
                    net[k][s].append(pr["vars"]["py"][s])

    def stats(score):
        y0 = [(C["by"][k][1]["obs_y"][C["by"][k][0]["y0"]], score(k)[C["by"][k][0]["y0"]]) for k in pred]
        ye = [(y, score(k)[s]) for k in pred for s, y in C["by"][k][1]["obs_y"].items() if s != C["by"][k][0]["y0"]]
        ag = []
        for k in pred:
            sv, lab, _ = C["by"][k]
            e = edit_contrast({"vars": {"py": [score(k).get(i, 0.5) for i in range(len(sv["y_poses"]))]}}, sv, {"obs_y": lab["obs_y"]})
            if e.get("agree") is not None:
                ag.append(e["agree"])
        return {"y0_auroc": auroc(y0), "y_edit_auroc_pooled": auroc(ye), "edit_contrast_agree_root_mean": float(np.mean(ag)), "edit_roots": len(ag)}
    return {"roots": len(pred), "features": ["min target clearance", "min clearance to base-target segment", "min clearance to target-goal segment",
                                              "min goal clearance", "n within 0.06 of target", "n within 0.12 of target", "|base-target|", "|target-goal|"],
            "probe_logreg": stats(lambda k: pred[k]), "xy_quadratic_oof": stats(lambda k: {s: float(np.mean(v)) for s, v in net[k].items()})}


# ------------------------------------------------------------------ main
def run() -> dict:
    t0, w0 = time.process_time(), time.time()
    C = context()
    rep = reproduce()
    oof = diag_table(C["tiers"][TIER], C)
    ins = insample(C)
    ins_t = diag_table(ins, C)
    roots = sorted({k for t in oof.values() for k in t})
    res = {"reproduction": rep, "roots": len(roots), "infeasible_roots": sum(C["by"][k][2]["y0"] == 0 for k in roots), "oof": {}, "insample": {}, "shapley": {}, "oracle_paired": {}}
    for arm in E.ARMS:
        res["oof"][arm] = summarize(oof, C, arm)
        res["insample"][arm] = summarize(ins_t, C, arm)
        if P.ARMS[arm]["kind"] == "xy":
            res["shapley"][arm] = shapley(res["oof"][arm]["oracle_succ_inf"])
            res["oracle_paired"][arm] = {s: paired_oracle(oof, arm, s) for s in res["oof"][arm]["oracle_succ_inf"] if s != "model"}
    T_oof = {k: {r: {"pred": C["tiers"][TIER][k][r]} for r in v} for k, v in oof.items()}
    T_in = {k: {r: {"pred": ins[k][r]} for r in v} for k, v in ins_t.items()}
    res["order_omission"] = {arm: {"oof": {"order": E.strip(E.order_pairs(T_oof, arm, C["by"])), "omission": E.omissions(T_oof, arm, C["by"])["sign_agreement"]},
                                   "insample": {"order": E.strip(E.order_pairs(T_in, arm, C["by"])), "omission": E.omissions(T_in, arm, C["by"])["sign_agreement"]}}
                             for arm in E.ARMS}
    res["loss_census"] = loss_census(C)
    res["clip_history"] = clip_history(C)
    res["grad_audit"] = {arm: grad_audit(C, arm) for arm in ("XY-quadratic", "XY-quadratic-noJ", "DIRECT")}
    res["geometry_probe"] = geometry_probe(C)
    res["insample_cache_sha256"] = {f.name: P.sha(f) for f in sorted(CACHE.glob("*.json"))}
    res["accounting"] = {"cpu_s": time.process_time() - t0, "wall_s": time.time() - w0}
    return res, oof, ins_t


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    res, oof, ins_t = run()
    (OUT / "DIAGNOSTICS.json").write_text(json.dumps({k: v for k, v in res.items() if k != "grad_audit"} |
                                                     {"grad_audit": {a: {kk: vv for kk, vv in g.items() if kk != "batches"} for a, g in res["grad_audit"].items()}},
                                                     indent=1, sort_keys=True, default=str))
    (OUT / "GRAD_AUDIT_BATCHES.json").write_text(json.dumps({a: g["batches"] for a, g in res["grad_audit"].items()}, default=str))
    (OUT / "PER_ROOT_OOF.json").write_text(json.dumps({f"{a}|{s}": t for (a, s), t in oof.items()}, sort_keys=True, default=str))
    print(json.dumps(res["accounting"]), json.dumps(res["reproduction"]))


# ------------------------------------------------------------------ frozen P14 hypotheses (written after the P13 evidence, before any P14 code / run)
HYPOTHESES = {
    "version": "BXY_P14_HYPOTHESES_V1",
    "bottlenecks_ranked": [
        {"id": "B1_EDITED_Y_CONTRAST", "evidence": "edited-Y Shapley share 0.36-0.42 of the corrective gap; within-root edited-Y AUROC 0.42-0.48 OOF and "
         "only 0.55-0.58 on the models' own training roots; P(Y_edit) - P(Y0) ~ +0.12..+0.16 whatever the recorded labels (edit-contrast agreement "
         "0.00-0.06 on S0-feasible roots); a hand-made 8-clearance probe reaches pooled edited-Y AUROC 0.69 vs 0.59"},
        {"id": "B2_Y0_GENERALIZATION", "evidence": "Y0 Shapley share 0.13-0.28; Y0 AUROC 0.83-0.89 on training roots vs 0.65-0.71 OOF; the probe reaches "
         "0.77 OOF; Y0 is 1 of ~20 terms per root (5.6 % of the joint NLL)"},
        {"id": "B3_SELECTION_PENALTY", "evidence": "27-33 % of travel-arm choices on infeasible roots reject a verified repair whose p exceeds P(Y0) "
         "(MISSED_PENALTY_REJECTED; 13 % at gamma = 0); a penalty-free rule doubles-to-triples corrective success but repairs 55-65 % of feasible "
         "roots under the P12 models (because of B1's constant edit bonus)"}],
    "not_targeted": {"X": "Shapley share ~0.09, within-root X AUROC 0.72", "clipping": "0 % of batches exceed the clip norm at initialization, ~65 % "
                     "at the restored checkpoints, dominated by X|Y terms of sharpened logits; no evidence that clipping limits the fit",
                     "query_normalization": "Y0 under-fit is not the problem (training-root AUROC 0.83-0.89); re-weighting would not address generalization"},
    "interventions": {
        "CON": {"targets": "B1 (and Y0-vs-edit contrasts of B2)", "kind": "training objective (auxiliary, NOT the exact likelihood)",
                "definition": "per root, all pairs (s, t) of observed Y nodes (Y0 included) with y_s = 1, y_t = 0: l_root = n_obsY(root) * mean_pairs "
                "softplus(-(b_s - b_t)); L = L_joint + lambda_J L_J + kappa * mean over the batch roots of l_root (roots without a discordant pair "
                "contribute 0)", "kappa": 1.0},
        "GEO": {"targets": "B1 / B2 representation", "kind": "geometry-aware control on the Y unary only",
                "definition": "b_s = scene(v_s, c) + mlp(8 -> 128 -> 1)(phi(S_s)); phi = bxy_p13.geo_features of the (edited) scene from the scorer's own "
                "tensors (object centres / radii / target flag, robot base, goal), distances / 0.08 m (cell units), counts raw; no label, witness, "
                "teacher or catalogue field"},
        "PONLY": {"targets": "B3", "kind": "selection only (no training)", "definition": "argmin -log p over F1-admissible candidates incl. the no-op "
                  "(alpha = beta = gamma = 0, eta = 0, no gate), ties by (m, C_d, signature)"}},
    "arms": {"DIRECT": "bxy_p11 DIRECT, retrained", "XYQ": "bxy_p11 XY-quadratic, lambda_J = 1.0 (P12 lambda*), original objective",
             "XYQ+CON": "XYQ + CON", "XYQ+GEO": "XYQ + GEO", "XYQ+CON+GEO": "XYQ + CON + GEO"},
    "protocol": {"roots": "the 176 original TRAIN roots only (val21 and the 34 exposed test roots excluded)", "folds": "5 family-grouped folds over "
                 "the 176 roots (bxy_p11.folds procedure, early-stop subset inside each training part)", "seeds": [0, 1, 2], "runs": 75,
                 "training": "bxy_p11.TRAIN unchanged; early stopping on the exact joint NLL (XY) / success BCE (DIRECT) for every arm"},
    "selection_rules": {"PRIMARY": "P11.1 PRIMARY (alpha 0.1, beta 0, gamma 0.05 for lambda_J-trained XY arms, 0 for DIRECT)", "PONLY": "see PONLY"},
    "endpoints": {"primary": "verified success on the 45 initially infeasible roots (seed mean per root, OOF)", "co_report": "the 39 repairable infeasible roots",
                  "guardrail": "unnecessary repair rate on the 131 initially feasible roots"},
    "contrasts": {"C1": "XYQ+CON vs XYQ (PRIMARY)", "C2": "XYQ+GEO vs XYQ (PRIMARY)", "C3": "XYQ+CON+GEO vs XYQ (PRIMARY)",
                  "C4": "PONLY vs PRIMARY on the same checkpoints, every arm", "C5": "XYQ+CON+GEO with PONLY vs XYQ with PRIMARY (pre-specified combination)"},
    "decision": {"IMPROVES": "paired root-cluster bootstrap (B = 10000) delta success on infeasible roots: CI95 lower > 0, AND delta unnecessary-repair "
                 "point estimate <= +0.05", "TARGET_MET": "IMPROVES and delta success point estimate >= +0.10", "multiplicity": "five pre-specified "
                 "contrasts; 95 % CIs reported plus whether each survives Bonferroni (99 % CI); development evidence only",
                 "no_post_hoc_change": "criteria, arms, coefficients and rules are not changed after any P14 result"},
    "budget": {"aggregate_cpu_s": 45000, "per_run_cpu_s": 1500, "workers": 4, "wall_s": 21600, "runs": 75}}


def freeze_hypotheses() -> str:
    f = OUT / "P14_HYPOTHESES.json"
    txt = json.dumps(HYPOTHESES, indent=1, sort_keys=True)
    if f.exists() and f.read_text() != txt:
        raise FileExistsError("P14 hypotheses already frozen with different content")
    f.write_text(txt)
    return P.sha(f)
