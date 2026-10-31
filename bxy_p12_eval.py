"""BXY-P12 evaluation of the finished runs, exactly as preregistered in P11 + P11.1 (written before any run finished):

  tiers       PRIMARY_DEV = CROSSFIT out-of-fold on the 176 original TRAIN roots (all decisions); SUPPLEMENTARY_DEV = OOF on all 197;
              DESCRIPTIVE_VAL = SPLIT checkpoints (lambda*) on val21, the only tier with the frozen LB reference
  units       per-root metrics averaged over the available seeds, then paired root-cluster bootstrap (B = 10000) between arms; queries of a
              root are never independent samples; per-seed results reported alongside
  probability X, Y, success (x AND y of every decided X query + Y0) log loss / Brier (root-averaged and pooled), ECE10, reliability bins,
              exact joint observed-data NLL per root (XY arms, from the saved coefficients)
  selection   PRIMARY rule (gate-free cost argmin, arm gamma); secondary GATED_NOOP / ABSTAINING / LEXICOGRAPHIC and the sensitivity grid
  contrasts   coupling (vs XY-uncoupled and XY-uncoupled-SA, preregistered verdict), factorization (vs DIRECT), travel TRAINING / RANKING /
              COMBINED, order (certified vs budget), omissions (+ two-move patterns), strata, references (no-op, shortest, displacement,
              verify-first oracle, oracle availability, LB on val21)
Only labels / evaluator views of the parent process are read here; workers never saw them."""
from __future__ import annotations

import collections
import itertools
import json
import time
from pathlib import Path

import numpy as np
import torch

import bxy_data as bd
import bxy_p11 as P
import bxy_p11_1 as A
import bxy_p12_run as R

OUT = R.OUT
ARMS = tuple(P.ARMS)
XY = tuple(a for a in ARMS if P.ARMS[a]["kind"] == "xy")
LB = Path("runs/approach_b/bd2d_lb_v1")
STRATA = ("K0", "K1", "K>=2", "None")
B = 10000


# ------------------------------------------------------------------ loading
def finished() -> dict:
    """{rid: (spec, RESULT, predictions)} of every DONE run whose result record validates; nothing else is ever evaluated."""
    L = json.loads((OUT / "LEDGER.json").read_text())
    out = {}
    for rid, r in L["runs"].items():
        if r["status"] == "DONE" and R.valid_result(OUT, rid):
            rd = OUT / "runs" / R.safe(rid)
            res = json.loads((rd / "RESULT.json").read_text())
            out[rid] = (res["spec"], res, json.loads((rd / "predictions.json").read_text()))
    return out


def lb_rows(sv, seed) -> list | None:
    """Frozen LB val predictions mapped onto the canonical candidate rows by signature (LB scores only its own catalogue candidates)."""
    d = json.loads((LB / f"PREDICTIONS_s{seed}.json").read_text())["val"].get(sv["key"])
    if d is None:
        return None
    p = {c["query"].split(":", 2)[2] if c["m"] else "": c["p"] for c in d["candidates"]}
    rows = []
    for c in sv["cands"]:
        k = c["sig"] if c["m"] else ""
        rows.append(dict(c) | ({"p": float(p[k]), "J_hat": 0.0} if c["admissible"] and k in p else {"admissible": False}))
    return rows


def witnessed_travel(sv, lab, ev, sc_rows) -> dict:
    """{sig: {J, relocation, connector, target}} of the root's successful candidates with an independently replayed complete witness."""
    xr, yr = sc_rows
    out = {}
    for xi, yi, J in lab["j"]:
        c = next(c for c in sv["cands"] if (c["m"] == 0 if xi is None else c["xi"] == xi) and c["admissible"]) if any(
            (c["m"] == 0 if xi is None else c["xi"] == xi) and c["admissible"] for c in sv["cands"]) else None
        if c is None:
            continue
        tgt = yr[ev["y_keys"][yi]]["J_target"]
        tp = xr[ev["x_keys"][xi]]["travel_parts"] if xi is not None else {"J_move": [], "J_connector": 0.0}
        out[c["sig"]] = {"J": J, "relocation": float(sum(tp["J_move"])), "connector": float(tp["J_connector"]), "target": float(tgt)}
    return out


# ------------------------------------------------------------------ per root, per prediction
def root_items(arm, pred, sv, ev) -> dict:
    v = pred["vars"]
    rows = pred["cands"]
    p0 = next(r["p"] for r in rows if r["m"] == 0)
    succ = P.success_events(ev["obs_x"], ev["obs_y"], ev["parent"], sv["y0"])
    out = {"s": [(int(y), float(p0) if q is None else float(v["psucc"][q])) for q, y in succ.items()], "x": [], "y": [], "joint": None}
    if P.ARMS.get(arm, {}).get("kind") == "xy":
        out["x"] = [(int(y), float(v["px"][q])) for q, y in ev["obs_x"].items()]
        out["y"] = [(int(y), float(v["py"][s])) for s, y in ev["obs_y"].items()]
        c = {k: torch.tensor(x, dtype=torch.float64) for k, x in pred["coeffs"].items()}
        out["joint"] = float(-P.log_evidence(c["b"], c["a"], c["w"], sv["parent"], ev["obs_x"], ev["obs_y"]))
    return out


def ll(items) -> float | None:
    if not items:
        return None
    return float(np.mean([-(y * np.log(min(max(p, 1e-12), 1 - 1e-12)) + (1 - y) * np.log(1 - min(max(p, 1e-12), 1 - 1e-12))) for y, p in items]))


def brier(items) -> float | None:
    return float(np.mean([(p - y) ** 2 for y, p in items])) if items else None


def sel_row(rows, ev, i, trav) -> dict:
    r = P.selection_row(rows, ev, i, {k: v["J"] for k, v in trav.items()})
    chosen = rows[i]["sig"] if i is not None else None
    jmin = min((v["J"] for v in trav.values()), default=None)
    r |= {"sig": chosen, "noop_correct": int(ev["y0"] is not None and (i is not None and rows[i]["m"] == 0) == (ev["y0"] == 1)),
          "missed_repair": int(ev["y0"] == 0 and i is not None and rows[i]["m"] == 0),
          "regret": (trav[chosen]["J"] - jmin) if r["success"] and chosen in trav else None,
          "parts": trav.get(chosen) if r["success"] else None}
    return r


def rules_for(arm) -> dict:
    g = A.GAMMA.get(arm, 0.0)
    out = {"PRIMARY": A.rule(arm) if arm in A.GAMMA else A.PRIMARY | {"gamma": 0.0}, "PRIMARY_gamma0": A.PRIMARY | {"gamma": 0.0},
           "GATED_NOOP": A.GATED | {"gamma": g}, "ABSTAINING": A.PRIMARY | {"gamma": g, "eta": 0.5}, "LEXICOGRAPHIC": A.PRIMARY | {"gamma": g, "alpha": 100.0}}
    s = P.SENSITIVITY
    for al, be, ga, et in itertools.product(s["alpha"], s["beta"], s["gamma"], s["eta"]):
        out[f"grid:a{al}:b{be}:g{ga}:e{et}"] = A.PRIMARY | {"alpha": al, "beta": be, "gamma": ga, "eta": et}
    return out


def choose_any(rows, rule):
    return P.choose(rows, rule)                                      # PRIMARY variants have noop_gate None; GATED keeps the frozen gate


# ------------------------------------------------------------------ assembling model sets
def model_sets(F, V) -> dict:
    """{tier: {(arm, seed): {root: prediction}}}. CROSSFIT predictions are unioned over folds (each root scored once per seed by the fold
    model that never trained or early-stopped on it). SPLIT uses the lambda* checkpoint of J-trained arms and lambda = 0 otherwise."""
    lam = json.loads((OUT / "LAMBDA_SELECTION.json").read_text())["selection"] if (OUT / "LAMBDA_SELECTION.json").exists() else {}
    keys = {sv["key"]: ev["split"] for sv, _, ev in V}
    cf, spl = collections.defaultdict(dict), collections.defaultdict(dict)
    for rid, (spec, res, pr) in F.items():
        key = (spec["arm"], spec["seed"])
        if spec["phase"] == "CROSSFIT":
            for k, v in pr.items():
                if k in cf[key]:
                    raise RuntimeError(f"{k} predicted twice for {key}")
                cf[key][k] = v
        elif spec["lambda_J"] == 0.0 or (spec["arm"] in lam and lam[spec["arm"]]["lambda"] == spec["lambda_J"]):
            spl[key] |= pr
    tiers = {"PRIMARY_DEV": {k: {r: p for r, p in v.items() if keys[r] == "train"} for k, v in cf.items()},
             "SUPPLEMENTARY_DEV": dict(cf), "DESCRIPTIVE_VAL": dict(spl)}
    return tiers


# ------------------------------------------------------------------ aggregation
def per_root_tables(preds, by, trav) -> dict:
    """preds {(arm, seed): {root: pred}} -> {(arm, seed): {root: metrics}}."""
    out = {}
    for (arm, seed), P_ in preds.items():
        t = {}
        for k, pr in P_.items():
            sv, lab, ev = by[k]
            it = root_items(arm, pr, sv, ev)
            rows = pr["cands"]
            sel = {nm: sel_row(rows, ev, choose_any(rows, ru), trav[k]) for nm, ru in rules_for(arm).items()}
            t[k] = {"ll_s": ll(it["s"]), "br_s": brier(it["s"]), "ll_x": ll(it["x"]), "br_x": brier(it["x"]), "ll_y": ll(it["y"]), "br_y": brier(it["y"]),
                    "joint": it["joint"], "items": it, "sel": sel, "stratum": ev["stratum"], "y0": ev["y0"], "split": ev["split"]}
        out[(arm, seed)] = t
    return out


def seed_mean(T, arm, f) -> dict:
    """{root: mean over available seeds of f(root metrics)} (None values skipped)."""
    acc = collections.defaultdict(list)
    for (a, s), t in T.items():
        if a != arm:
            continue
        for k, m in t.items():
            v = f(m)
            if v is not None:
                acc[k].append(v)
    return {k: float(np.mean(v)) for k, v in acc.items()}


METRICS = {"ll_s": lambda m: m["ll_s"], "br_s": lambda m: m["br_s"], "ll_x": lambda m: m["ll_x"], "ll_y": lambda m: m["ll_y"], "joint": lambda m: m["joint"],
           "succ_inf": lambda m: m["sel"]["PRIMARY"]["success"] if m["y0"] == 0 else None,
           "succ_inf_g0": lambda m: m["sel"]["PRIMARY_gamma0"]["success"] if m["y0"] == 0 else None,
           "succ": lambda m: m["sel"]["PRIMARY"]["success"], "false_repair": lambda m: m["sel"]["PRIMARY"]["false_repair"] if m["y0"] == 1 else None,
           "noop_correct": lambda m: m["sel"]["PRIMARY"]["noop_correct"],
           "J": lambda m: m["sel"]["PRIMARY"]["J"], "J_g0": lambda m: m["sel"]["PRIMARY_gamma0"]["J"]}


def arm_summary(T, arm) -> dict:
    out = {"roots": len(seed_mean(T, arm, lambda m: 1.0)), "seeds": sorted(s for a, s in T if a == arm)}
    for nm, f in METRICS.items():
        v = seed_mean(T, arm, f)
        out[nm] = {"mean": float(np.mean(list(v.values()))) if v else None, "roots": len(v)}
    for rule in ("PRIMARY", "PRIMARY_gamma0", "GATED_NOOP", "ABSTAINING", "LEXICOGRAPHIC"):
        rows = [m["sel"][rule] for (a, s), t in T.items() if a == arm for m in t.values()]
        out[f"selection:{rule}"] = P.selection_summary(rows) | {"noop_correct": float(np.mean([r["noop_correct"] for r in rows])) if rows else None,
                                                                 "missed_repair_on_infeasible": float(np.mean([r["missed_repair"] for r in rows if r["initially_feasible"] == 0]))
                                                                 if any(r["initially_feasible"] == 0 for r in rows) else None,
                                                                 "mean_regret": float(np.mean([r["regret"] for r in rows if r["regret"] is not None]))
                                                                 if any(r["regret"] is not None for r in rows) else None}
    pooled = {s: [i for (a, _), t in T.items() if a == arm for m in t.values() for i in m["items"][s]] for s in ("s", "x", "y")}
    out["prob"] = {s: P.prob_metrics([("r", y, p) for y, p in v]) | {"reliability": reliability(v)} for s, v in pooled.items() if v}
    out["per_seed"] = {str(s): {"ll_s": float(np.mean([m["ll_s"] for m in t.values() if m["ll_s"] is not None])),
                                "succ_inf": float(np.mean([m["sel"]["PRIMARY"]["success"] for m in t.values() if m["y0"] == 0])) if any(m["y0"] == 0 for m in t.values()) else None,
                                "roots": len(t)} for (a, s), t in sorted(T.items()) if a == arm}
    parts = [m["sel"]["PRIMARY"]["parts"] for (a, s), t in T.items() if a == arm for m in t.values() if m["sel"]["PRIMARY"]["parts"]]
    out["travel_parts_of_successful_choices"] = {k: float(np.mean([p[k] for p in parts])) for k in ("J", "relocation", "connector", "target")} if parts else None
    out["travel_parts_successful_corrections"] = {k: float(np.mean([p[k] for p in parts if p["relocation"] > 0])) for k in ("J", "relocation", "connector", "target")} \
        if any(p["relocation"] > 0 for p in parts) else None
    out["strata"] = {st: {"roots": len({k for (a, s), t in T.items() if a == arm for k, m in t.items() if m["stratum"] == st}),
                          "ll_s": _mean([m["ll_s"] for (a, s), t in T.items() if a == arm for m in t.values() if m["stratum"] == st]),
                          "succ_inf": _mean([m["sel"]["PRIMARY"]["success"] for (a, s), t in T.items() if a == arm for m in t.values() if m["stratum"] == st and m["y0"] == 0]),
                          "infeasible_roots": len({k for (a, s), t in T.items() if a == arm for k, m in t.items() if m["stratum"] == st and m["y0"] == 0}),
                          "false_repair": _mean([m["sel"]["PRIMARY"]["false_repair"] for (a, s), t in T.items() if a == arm for m in t.values() if m["stratum"] == st and m["y0"] == 1])}
                     for st in STRATA}
    return out


def _mean(v):
    return float(np.mean(v)) if v else None


def reliability(items, n=10) -> list:
    y, p = np.array([i[0] for i in items], float), np.array([i[1] for i in items], float)
    b = np.minimum((p * n).astype(int), n - 1)
    return [{"bin": i, "n": int((b == i).sum()), "p_mean": float(p[b == i].mean()), "y_mean": float(y[b == i].mean())} for i in range(n) if (b == i).any()]


def paired(T, a, b, metric, Tb=None, flip=False) -> dict:
    """Paired root-cluster bootstrap of mean(metric_a - metric_b) over the roots both define (seed means first)."""
    ma, mb = (metric, metric) if isinstance(metric, str) else metric
    fa, fb = METRICS[ma], METRICS[mb]
    x, y = seed_mean(T, a, fa), seed_mean(Tb or T, b, fb)
    return P.cluster_boot(x, y, B=B)


def seeds_improve(T, a, ctrl) -> int:
    """Number of seeds s where arm a (seed s) has lower root-mean success log loss than ctrl (seed s) on their common roots."""
    n = 0
    for s in P.SEEDS:
        ta, tc = T.get((a, s)), T.get((ctrl, s))
        if not ta or not tc:
            continue
        ks = [k for k in ta if k in tc and ta[k]["ll_s"] is not None and tc[k]["ll_s"] is not None]
        n += bool(ks) and np.mean([ta[k]["ll_s"] - tc[k]["ll_s"] for k in ks]) < 0
    return n


# ------------------------------------------------------------------ order and omission (root-grouped)
def order_pairs(T, arm, by, use="psucc") -> dict:
    out = {"certified": collections.defaultdict(list), "budget_policy": collections.defaultdict(list)}
    for (a, s), t in T.items():
        if a != arm:
            continue
        for k in t:
            pr = t[k]["pred"]
            if use == "px" and pr["vars"]["px"] is None:
                continue
            px = dict(enumerate(pr["vars"][use]))
            for g in by[k][2]["order_groups"]:
                for i, u in enumerate(g["members"]):
                    for v in g["members"][i + 1:]:
                        if u["x"] == v["x"]:
                            continue
                        pos, neg = (u, v) if u["x"] == 1 else (v, u)
                        sc = 1.0 if px[pos["xi"]] > px[neg["xi"]] else 0.5 if px[pos["xi"]] == px[neg["xi"]] else 0.0
                        out["certified" if neg["negative_kind"] == "CERTIFIED" else "budget_policy"][(k, pos["xi"], neg["xi"])].append(sc)
    res = {}
    for kind, d in out.items():
        per_root = collections.defaultdict(list)
        for (k, _, _), v in d.items():
            per_root[k].append(float(np.mean(v)))
        r = {k: float(np.mean(v)) for k, v in per_root.items()}
        res[kind] = {"pairs": len(d), "roots": len(r), "concordance_root_mean": _mean(list(r.values())), "per_root": r,
                     "ci95": boot_mean(r)}
    return res


def boot_mean(r: dict) -> list | None:
    if not r:
        return None
    d = np.array(list(r.values()))
    bs = d[np.random.default_rng(0).integers(0, len(d), (B, len(d)))].mean(1)
    return [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]


def omissions(T, arm, by) -> dict:
    preds = [t[k]["pred"] for (a, s), t in T.items() if a == arm for k in t]
    evs = [by[k][2] for (a, s), t in T.items() if a == arm for k in t]
    om = P.omission_metric(preds, evs)
    pat = collections.defaultdict(lambda: {"n": 0, "roots": set(), "p_full": [], "p_o1": [], "p_o2": []})
    for pr, ev in zip(preds, evs):
        sf = lambda q: None if q is None else (0 if 0 in (ev["obs_x"].get(q), ev["obs_y"].get(ev["parent"][q])) else  # noqa: E731
                                               1 if (ev["obs_x"].get(q), ev["obs_y"].get(ev["parent"][q])) == (1, 1) else None)
        for o in ev["omissions"]:
            if len(o["omit"]) != 2 or any(t["xi"] is None for t in o["omit"]):
                continue
            f, o1, o2 = o["xi"], o["omit"][0]["xi"], o["omit"][1]["xi"]
            lab = (sf(f), sf(o1), sf(o2))
            if None in lab:
                continue
            key = f"full={lab[0]} omit_first={lab[1]} omit_second={lab[2]}"
            d = pat[key]
            d["n"] += 1
            d["roots"].add(ev["key"])
            ps = pr["vars"]["psucc"]
            d["p_full"].append(ps[f])
            d["p_o1"].append(ps[o1])
            d["p_o2"].append(ps[o2])
    return {"sign_agreement": om, "two_move_patterns": {k: {"n_seed_rows": v["n"], "roots": len(v["roots"]), "mean_p_full": _mean(v["p_full"]),
                                                            "mean_p_omit_first": _mean(v["p_o1"]), "mean_p_omit_second": _mean(v["p_o2"])}
                                                        for k, v in sorted(pat.items())}}


# ------------------------------------------------------------------ references
def references(roots, by, trav) -> dict:
    out = {}
    for nm, f in P.REFERENCES.items():
        rows = [sel_row(by[k][0]["cands"], by[k][2], f(by[k][0]["cands"]), trav[k]) for k in roots]
        out[nm] = P.selection_summary(rows) | {"noop_correct": _mean([r["noop_correct"] for r in rows])}
    vf = [P.verify_first(by[k][2], by[k][0]) for k in roots]
    inf = [k for k in roots if by[k][2]["y0"] == 0]
    out["VERIFY_FIRST (oracle)"] = {"success": _mean([v["success"] for v in vf]), "success_infeasible": _mean([P.verify_first(by[k][2], by[k][0])["success"] for k in inf]),
                                    "mean_verifications": _mean([v["verifications"] for v in vf]),
                                    "mean_verifications_infeasible": _mean([P.verify_first(by[k][2], by[k][0])["verifications"] for k in inf])}
    out["ORACLE_AVAILABILITY"] = {"infeasible_roots": len(inf), "available": _mean([int(any(c["success"] == 1 for c in by[k][2]["cands"])) for k in inf])}
    return out


def ref_root_metric(roots, by, trav, nm, metric) -> dict:
    f = P.REFERENCES[nm]
    out = {}
    for k in roots:
        r = sel_row(by[k][0]["cands"], by[k][2], f(by[k][0]["cands"]), trav[k])
        if metric == "succ_inf" and by[k][2]["y0"] == 0:
            out[k] = float(r["success"])
        elif metric == "false_repair" and by[k][2]["y0"] == 1:
            out[k] = float(r["false_repair"])
    return out


# ------------------------------------------------------------------ main
def evaluate() -> dict:
    t0, w0 = time.process_time(), time.time()
    sc, D, Rr, I = P.load()
    V = P.build(sc=sc, D=D, R=Rr, I=I)
    by = {sv["key"]: (sv, lab, ev) for sv, lab, ev in V}
    xr, yr = {r["x_key"]: r for r in sc["x_queries"]}, {r["y_key"]: r for r in sc["y_queries"]}
    trav = {k: witnessed_travel(sv, lab, ev, (xr, yr)) for k, (sv, lab, ev) in by.items()}
    F = finished()
    tiers = model_sets(F, V)
    res = {"runs_evaluated": len(F), "tiers": {}}
    for tier, preds in tiers.items():
        T = per_root_tables(preds, by, trav)
        for (a, s), t in T.items():
            for k in t:
                t[k]["pred"] = preds[(a, s)][k]
        roots = sorted({k for t in T.values() for k in t})
        arms = sorted({a for a, _ in T}, key=lambda a: ARMS.index(a))
        out = {"roots": len(roots), "infeasible_roots": sum(by[k][2]["y0"] == 0 for k in roots),
               "arms": {a: arm_summary(T, a) for a in arms}}
        comp = {}
        if {"XY-quadratic", "XY-uncoupled", "XY-uncoupled-SA"} <= set(arms):
            c = {ctrl: {"ll_s": paired(T, "XY-quadratic", ctrl, "ll_s"), "succ_inf": paired(T, "XY-quadratic", ctrl, "succ_inf"),
                        "br_s": paired(T, "XY-quadratic", ctrl, "br_s"), "joint": paired(T, "XY-quadratic", ctrl, "joint"),
                        "false_repair": paired(T, "XY-quadratic", ctrl, "false_repair"), "seeds_improving": seeds_improve(T, "XY-quadratic", ctrl)}
                 for ctrl in ("XY-uncoupled", "XY-uncoupled-SA")}
            seeds_ok = sum(1 for s in P.SEEDS if all(seeds_improve({k: v for k, v in T.items() if k[1] == s}, "XY-quadratic", ctrl) for ctrl in c)) >= 2
            c["verdict"] = P.verdict(c["XY-uncoupled"]["ll_s"], c["XY-uncoupled-SA"]["ll_s"], c["XY-uncoupled"]["succ_inf"], c["XY-uncoupled-SA"]["succ_inf"], seeds_ok)
            c["seeds_ok"] = seeds_ok
            comp["coupling"] = c
        if {"XY-quadratic", "DIRECT"} <= set(arms):
            d = {"ll_s": paired(T, "XY-quadratic", "DIRECT", "ll_s"), "succ_inf": paired(T, "XY-quadratic", "DIRECT", "succ_inf"),
                 "br_s": paired(T, "XY-quadratic", "DIRECT", "br_s"), "false_repair": paired(T, "XY-quadratic", "DIRECT", "false_repair")}
            d["factorized_preferred"] = bool(d["ll_s"]["ci95"][1] < 0.02 and d["succ_inf"]["ci95"][0] > -0.05)
            comp["factorization"] = d
        if {"XY-quadratic", "XY-quadratic-noJ"} <= set(arms):
            tr = {"TRAVEL_TRAINING": {"ll_s": paired(T, "XY-quadratic", "XY-quadratic-noJ", "ll_s"),
                                      "succ_inf": paired(T, "XY-quadratic", "XY-quadratic-noJ", ("succ_inf_g0", "succ_inf")),
                                      "J": paired(T, "XY-quadratic", "XY-quadratic-noJ", ("J_g0", "J"))},
                  "TRAVEL_RANKING": {"succ_inf": paired(T, "XY-quadratic", "XY-quadratic", ("succ_inf", "succ_inf_g0")),
                                     "J": paired(T, "XY-quadratic", "XY-quadratic", ("J", "J_g0"))},
                  "TRAVEL_COMBINED": {"ll_s": paired(T, "XY-quadratic", "XY-quadratic-noJ", "ll_s"), "succ_inf": paired(T, "XY-quadratic", "XY-quadratic-noJ", "succ_inf"),
                                      "J": paired(T, "XY-quadratic", "XY-quadratic-noJ", "J")}}
            tr["TRAVEL_TRAINING"]["supported"] = bool(tr["TRAVEL_TRAINING"]["ll_s"]["ci95"][1] < 0.02 and tr["TRAVEL_TRAINING"]["succ_inf"]["ci95"][0] > -0.05)
            jr = tr["TRAVEL_RANKING"]["J"]
            tr["TRAVEL_RANKING"]["supported"] = bool(jr["roots"] and jr["ci95"][1] < 0 and tr["TRAVEL_RANKING"]["succ_inf"]["ci95"][0] > -0.05)
            jc = tr["TRAVEL_COMBINED"]["J"]
            tr["TRAVEL_COMBINED"]["retain_lambda_star"] = bool(tr["TRAVEL_COMBINED"]["ll_s"]["ci95"][1] < 0.02 and jc["roots"] and jc["ci95"][1] < 0)
            comp["travel"] = tr
        refs = references(roots, by, trav)
        comp["vs_references"] = {a: {nm: {"succ_inf": P.cluster_boot(seed_mean(T, a, METRICS["succ_inf"]), ref_root_metric(roots, by, trav, nm, "succ_inf"), B=B),
                                          "false_repair": P.cluster_boot(seed_mean(T, a, METRICS["false_repair"]), ref_root_metric(roots, by, trav, nm, "false_repair"), B=B)}
                                     for nm in P.REFERENCES} for a in arms}
        out |= {"comparisons": comp, "references": refs,
                "order": {a: {"psucc": strip(order_pairs(T, a, by, "psucc")), "px": strip(order_pairs(T, a, by, "px")) if a in XY else None} for a in arms},
                "order_paired_psucc_certified": {ctrl: P.cluster_boot(order_pairs(T, "XY-quadratic", by)["certified"]["per_root"], order_pairs(T, ctrl, by)["certified"]["per_root"], B=B)
                                                 for ctrl in arms if ctrl != "XY-quadratic" and "XY-quadratic" in arms},
                "omissions": {a: omissions(T, a, by) for a in arms},
                "sensitivity_grid": {a: {nm: P.selection_summary([m["sel"][nm] for (b, s), t in T.items() if b == a for m in t.values()])
                                         for nm in rules_for(a) if nm.startswith("grid:")} for a in arms},
                "per_root": {a: {k: {"ll_s": v} for k, v in seed_mean(T, a, METRICS["ll_s"]).items()} for a in arms},
                "choices": {f"{a}|{s}": {k: {"sig": m["sel"]["PRIMARY"]["sig"], "success": m["sel"]["PRIMARY"]["success"], "y0": m["y0"],
                                             "p_noop": next(r["p"] for r in m["pred"]["cands"] if r["m"] == 0)} for k, m in t.items()} for (a, s), t in T.items()}}
        if tier == "DESCRIPTIVE_VAL":
            out["LB"] = lb_eval(roots, by, trav, T)
        res["tiers"][tier] = out
    res["accounting"] = {"evaluation_cpu_s": time.process_time() - t0, "evaluation_wall_s": time.time() - w0}
    return res


def strip(d: dict) -> dict:
    return {k: {kk: vv for kk, vv in v.items() if kk != "per_root"} for k, v in d.items()}


def lb_eval(roots, by, trav, T) -> dict:
    """Frozen LB (historical protocol) on val21: selection among the canonical admissible candidates it scored (gamma = 0), and
    catalogue-candidate success log loss vs the P12 SPLIT arms on the identical matched candidate set."""
    out = {}
    for s in P.SEEDS:
        sel, items, matched = [], [], {}
        for k in roots:
            rows = lb_rows(by[k][0], s)
            if rows is None:
                continue
            sel.append(sel_row(rows, by[k][2], P.choose(rows, A.PRIMARY | {"gamma": 0.0}), trav[k]))
            for r, e in zip(rows, by[k][2]["cands"]):
                if r["admissible"] and e["success"] is not None:
                    items.append((k, e["success"], r["p"]))
                    matched.setdefault(k, set()).add(r["sig"])
        out[f"s{s}"] = {"selection": P.selection_summary(sel) | {"noop_correct": _mean([r["noop_correct"] for r in sel])},
                        "catalogue_success_logloss_root": _mean(list(P.per_root(items).values())), "matched_candidates": len(items)}
        cmp = {}
        for (a, ss), t in T.items():
            if ss != s:
                continue
            it = [(k, e["success"], r["p"]) for k in matched for r, e in zip(t[k]["pred"]["cands"], by[k][2]["cands"]) if r["sig"] in matched[k] and e["success"] is not None]
            cmp[a] = _mean(list(P.per_root(it).values()))
        out[f"s{s}"]["same_candidates_logloss_by_arm"] = cmp
    return out


if __name__ == "__main__":
    r = evaluate()
    (OUT / "EVALUATION.json").write_text(json.dumps(r, indent=1, sort_keys=True, default=str))
    print(json.dumps(r["accounting"]))
