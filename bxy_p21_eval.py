"""BXY-P21 evaluation, as frozen in TRAINING_DESIGN_P21.json: the P17 evaluator (inner rule per (arm, fold) on early-stop predictions, OOF
3-seed selection, references, representation metrics, paired family bootstrap) applied to the P21 runs, plus: availability-conditioned
success, verified-K strata K1..K4 with n, the frozen K3/K4 hypotheses H1-H4 (repairable K3/K4 K34 roots; unnecessary repairs on all
outcome-blind feasible roots), strict permutation order (all / certified) on K34 roots, and the P18 pooled rule as a read-only diagnostic.
K3 results are exploratory; K4 results are descriptive only (P20 verdict K4_PHYSICAL_DATA_NOT_ESTABLISHED).
    python3 bxy_p21_eval.py"""
from __future__ import annotations

import itertools
import json
import time

import numpy as np

import bxy_p17 as M
import bxy_p17_eval as E
import bxy_p19_audit as A
import bxy_p21_k34 as H
from bxy_p14_run import _swap

OUT = H.OUT
POP = {"OB": ("P15", "V21", "K34"), "K34": ("K34",), "V21": ("V21",), "PMIN": ("PMIN",)}


def context():
    """bxy_p17_eval.context on the P21 design / runs / data (same structure; P21 builder, P21 run tree)."""
    import collections
    d = H.frozen()
    V = H.build_all()
    by = {ev["key"]: (sv, lab, ev) for sv, lab, ev in V}
    with _swap(E, "OUT", OUT):
        F = E.finished()
    fold_of = {k: f["fold"] for f in d["folds"]["folds"] for k in f["heldout"]}
    oof, es = collections.defaultdict(dict), collections.defaultdict(dict)
    for rid, r in F.items():
        a, s, fo = r["spec"]["arm"], r["spec"]["seed"], int(r["spec"]["train"].split(".")[0][4:])
        oof[(a, s)].update(json.loads((r["dir"] / "predictions.json").read_text()))
        es[(a, fo, s)] = json.loads((r["dir"] / "predictions_es.json").read_text())
    return {"d": d, "by": by, "F": F, "oof": oof, "es": es, "fold_of": fold_of, "family": {k: v[2]["family"] for k, v in by.items()},
            "corpus": {k: v[2]["corpus"] for k, v in by.items()}}


def succ_avail(nm):
    return lambda d: d[nm]["success"] if d["y0"] == 0 and d["available"] else None


def strata(T, C, arm, pop="OB"):
    out = {}
    for K in (1, 2, 3, 4):
        keep = lambda k, K=K: C["corpus"][k] in POP[pop] and C["by"][k][2]["verified_K"] == K  # noqa: E731
        sm = E.seed_mean(T, arm, E.METRICS["succ_inf"]("RULE"), keep)
        out[f"K{K}"] = {"n": len(sm), "success": float(np.mean(list(sm.values()))) if sm else None}
    return out


def hypothesis(T, C, a1, a2):
    rep34 = lambda k: C["corpus"][k] == "K34" and C["by"][k][2]["verified_K"] in (3, 4)  # noqa: E731
    fea = lambda k: C["corpus"][k] in POP["OB"]  # noqa: E731
    s = E.family_boot(E.seed_mean(T, a1, E.METRICS["succ_inf"]("RULE"), rep34), E.seed_mean(T, a2, E.METRICS["succ_inf"]("RULE"), rep34), C["family"])
    u = E.family_boot(E.seed_mean(T, a1, E.METRICS["unnecessary"]("RULE"), fea), E.seed_mean(T, a2, E.METRICS["unnecessary"]("RULE"), fea), C["family"])
    met = bool(s["diff"] is not None and s["ci95"][0] > 0 and s["diff"] >= H.CRITERION["success_gain"] and u["diff"] <= H.CRITERION["unnecessary_max_increase"])
    return {"success_repairable_K34": s, "unnecessary_OB": u, "criterion_met": met, "label": "EXPLORATORY (K3 limited, K4 n < 10)"}


def strict_order(C, arm):
    st = {"all": [0, 0.0], "certified": [0, 0.0]}
    roots = set()
    for s in M.SEEDS:
        for k, pr in C["oof"].get((arm, s), {}).items():
            ev = C["by"][k][2]
            if ev["corpus"] != "K34":
                continue
            px = pr["vars"]["px"]
            for g in ev["order_groups"]:
                for u, v in itertools.combinations(g["members"], 2):
                    a, b = A._seq(ev["x_keys"][u["xi"]]), A._seq(ev["x_keys"][v["xi"]])
                    if u["x"] == v["x"] or len(a) != len(b) or sorted(a) != sorted(b) or a == b:
                        continue
                    pos, neg = (u, v) if u["x"] == 1 else (v, u)
                    d = px[pos["xi"]] - px[neg["xi"]]
                    sc = 0.5 if abs(d) <= A.TIE else float(d > 0)
                    roots.add(k)
                    for sub in ("all", "certified") if neg["negative_kind"] == "CERTIFIED" else ("all",):
                        st[sub][0] += 1
                        st[sub][1] += sc
    return {sub: {"pairs_x_seeds": n, "concordance": c / n if n else None} for sub, (n, c) in st.items()} | {"roots": len(roots)}


def evaluate() -> dict:
    t0 = time.process_time()
    C = context()
    R_ = E.rules(C)
    T = E.tables(C, R_)
    arms = [a for a in M.ARMS if any(k[0] == a for k in T)]
    with _swap(E, "POP", POP):
        Rf = E.references(C)
        res = {"runs_evaluated": len(C["F"]), "roots": {p: sum(C["corpus"][k] in POP[p] for k in C["by"]) for p in POP},
               "infeasible": {p: sum(C["corpus"][k] in POP[p] and C["by"][k][2]["y0"] == 0 for k in C["by"]) for p in POP},
               "available": {p: sum(C["corpus"][k] in POP[p] and C["by"][k][2]["y0"] == 0 and any(c["success"] == 1 for c in C["by"][k][2]["cands"]) for k in C["by"]) for p in POP},
               "rules": {f"{a}|f{fo}": v for (a, fo), v in R_.items()},
               "arms": {p: {a: E.summary(T, C, a, p) | {"succ_avail": (float(np.mean(list(v.values()))) if (v := E.seed_mean(T, a, succ_avail("RULE"), lambda k, p=p: C["corpus"][k] in POP[p])) else None)}
                            for a in arms} for p in POP},
               "references": {p: E.ref_summary(Rf, C, p) for p in POP},
               "contrasts": {p: {c: E.contrast(T, C, a1, a2, p) for c, (a1, a2) in M.CONTRASTS.items() if a1 in arms and a2 in arms} for p in ("OB", "K34", "PMIN")},
               "strata": {p: {a: strata(T, C, a, p) for a in arms} for p in ("OB", "K34")},
               "hypotheses_K34": {h: hypothesis(T, C, a1, a2) for h, (a1, a2) in H.HYPOTHESES.items() if a1 in arms and a2 in arms and h.endswith("K34")},
               "strict_order_K34": {a: strict_order(C, a) for a in arms if not a.startswith("A:")}}
    import bxy_p18 as Z
    fz = json.loads((Z.OUT / "FROZEN_MODELS.json").read_text())
    T18 = E.tables(C, {(a, f): {"rule": fz["arms"][a]["rule"]["rule"]} for a in M.ARMS for f in range(M.FOLDS)})
    res["P18_pooled_rule_diagnostic_OB"] = {a: {"succ_inf": float(np.mean(list(E.seed_mean(T18, a, E.METRICS["succ_inf"]("RULE"), lambda k: C["corpus"][k] in POP["OB"]).values()))),
                                                "unnecessary": float(np.mean(list(E.seed_mean(T18, a, E.METRICS["unnecessary"]("RULE"), lambda k: C["corpus"][k] in POP["OB"]).values())))}
                                            for a in arms}
    res["accounting"] = {"eval_cpu_s": round(time.process_time() - t0, 1)}
    return res


if __name__ == "__main__":
    r = evaluate()
    (OUT / "EVALUATION_P21.json").write_text(json.dumps(r, indent=1, sort_keys=True, default=str))
    print(json.dumps({p: {a: {k: v for k, v in s["RULE"].items() if k in ("succ_inf", "unnecessary", "n_inf")} | {"succ_avail": s["succ_avail"]}
                          for a, s in r["arms"][p].items()} for p in ("OB", "K34")}, indent=1, default=str))
