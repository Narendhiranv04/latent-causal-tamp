"""BXY-P17 evaluation, exactly as frozen in TRAINING_DESIGN_P17.json: inner (early-stop) rule choice per (arm, fold), out-of-fold selection
on every development root (seed means per root), references (no-op, shortest, displacement, analytic-access geometry rule, verify-first
evaluator-only ceiling), representation metrics, and the five pre-declared paired family-bootstrap contrasts on the outcome-blind population
(P15 + V21; P-min reported separately).
    python3 bxy_p17_eval.py"""
from __future__ import annotations

import collections
import json
import time
from pathlib import Path

import numpy as np
import torch

import bxy_p11 as P
import bxy_p11_1 as A
import bxy_p12_eval as E
import bxy_p13 as Q
import bxy_p17 as M
import bxy_p17_data as DATA

OUT = M.OUT
B = 10000
POP = {"OB": ("P15", "V21"), "V21": ("V21",), "PMIN": ("PMIN",)}


def finished() -> dict:
    out = {}
    for f in sorted((OUT / "runs").glob("*/RESULT.json")):
        r = json.loads(f.read_text())
        out[r["rid"]] = r | {"dir": f.parent}
    return out


def context() -> dict:
    d = M.frozen()
    V = DATA.build_all()
    by = {ev["key"]: (sv, lab, ev) for sv, lab, ev in V}
    F = finished()
    fold_of = {k: f["fold"] for f in d["folds"]["folds"] for k in f["heldout"]}
    oof, es = collections.defaultdict(dict), collections.defaultdict(dict)
    for rid, r in F.items():
        a, s, fo = r["spec"]["arm"], r["spec"]["seed"], int(r["spec"]["train"].split(".")[0][4:])
        oof[(a, s)].update(json.loads((r["dir"] / "predictions.json").read_text()))
        es[(a, fo, s)] = json.loads((r["dir"] / "predictions_es.json").read_text())
    return {"d": d, "by": by, "F": F, "oof": oof, "es": es, "fold_of": fold_of, "family": {k: v[2]["family"] for k, v in by.items()},
            "corpus": {k: v[2]["corpus"] for k, v in by.items()}}


def succ_map(ev) -> dict:
    return {c["sig"]: c["success"] for c in ev["cands"]}


def rules(C) -> dict:
    """{(arm, fold): choose_rule over the early-stop predictions pooled across the arm's seeds of that fold}."""
    out = {}
    for a in M.ARMS:
        for fo in range(M.FOLDS):
            rows = []
            for s in M.SEEDS:
                for k, pr in C["es"].get((a, fo, s), {}).items():
                    ev = C["by"][k][2]
                    if ev["y0"] is not None:
                        rows.append((k, ev["y0"], pr["cands"], succ_map(ev)))
            if rows:
                out[(a, fo)] = M.choose_rule(a, rows)
    return out


def analytic_rule(sv, rows) -> int | None:
    """Geometry-only reference: no-op if the S0 access screens are open, else the shortest admissible candidate (m, C_d, sig) whose edited
    scene has open T-pick and T-place modes and whose actions all have open picks in their ideal predecessor scenes; else abstain."""
    if all(v > 0 for v in M.phi_y(sv, sv["y0"])[10:12]):
        return next(i for i, r in enumerate(rows) if r["m"] == 0)
    ok = [i for i, (r, c) in enumerate(zip(rows, sv["cands"])) if r["admissible"] and r["m"] > 0 and all(v > 0 for v in M.phi_y(sv, c["yi"])[10:12])
          and M.phi_x(sv, c["xi"])[1] > 0]
    return min(ok, key=lambda i: (rows[i]["m"], rows[i]["cd"], rows[i]["sig"])) if ok else None


def sel(rows, ev, i, trav) -> dict:
    r = E.sel_row(rows, ev, i, trav)
    c = ev["cands"][i] if i is not None else None
    r["harmful_unnecessary"] = int(ev["y0"] == 1 and i is not None and rows[i]["m"] > 0 and c["success"] == 0)
    r["harmless_unnecessary"] = int(ev["y0"] == 1 and i is not None and rows[i]["m"] > 0 and c["success"] == 1)
    return r


def root_row(arm, pred, sv, ev, rule) -> dict:
    rows, trav = pred["cands"], {s: {"J": J} for s, J in ev["travel"].items() if J is not None}
    xy = M.ARMS[arm]["base"] != "DIRECT"
    out = {"y0": ev["y0"], "corpus": ev["corpus"], "vk": ev["verified_K"], "p_noop": next(r["p"] for r in rows if r["m"] == 0),
           "available": int(ev["y0"] == 0 and any(c["success"] == 1 for c in ev["cands"]))}
    for name, ru in (("RULE", rule), ("PRIMARY", A.PRIMARY | {"gamma": 0.05 if M.ARMS[arm]["lam"] else 0.0}), ("TRAVEL_BLIND", rule | {"gamma": 0.0})):
        i = P.choose(rows, ru)
        out[name] = sel(rows, ev, i, trav) | {"cat": Q.category(rows, ev, i, ru) if i is not None else "ABSTAIN"}
    out |= {"edit": Q.edit_contrast(pred, sv, ev), **Q.within(pred, ev, sv)}
    it = E.root_items(M.ARMS[arm]["base"], pred, sv, ev)
    out["items"] = it
    out["joint_nll"] = it["joint"] if xy else None
    v = pred["vars"]
    if xy:                                                                          # edit sign by transition, order, omission
        y0, py = ev["obs_y"].get(sv["y0"]), v["py"]
        tr = {"01": [], "10": []}
        for s, y in ev["obs_y"].items():
            if s != sv["y0"] and y0 is not None and y != y0:
                d = py[s] - py[sv["y0"]]
                tr[f"{y0}{y}"].append(1.0 if d * (y - y0) > 0 else 0.5 if d == 0 else 0.0)
        out["edit_01"] = float(np.mean(tr["01"])) if tr["01"] else None
        out["edit_10"] = float(np.mean(tr["10"])) if tr["10"] else None
        oc = []
        for g in ev["order_groups"]:
            pos = [u["xi"] for u in g["members"] if u["x"] == 1]
            neg = [u["xi"] for u in g["members"] if u["x"] == 0]
            oc += [1.0 if v["px"][a] > v["px"][b] else 0.5 if v["px"][a] == v["px"][b] else 0.0 for a in pos for b in neg]
        out["order"] = float(np.mean(oc)) if oc else None
        om = []
        for o in ev["omissions"]:
            yf = ev["obs_y"].get(o["yi"])
            for t in o["omit"]:
                yo = ev["obs_y"].get(t["yi"]) if t["yi"] is not None else None
                if yf is not None and yo is not None and yf != yo:
                    d = py[o["yi"]] - py[t["yi"]]
                    om.append(1.0 if d * (yf - yo) > 0 else 0.5 if d == 0 else 0.0)
        out["omission"] = float(np.mean(om)) if om else None
    return out


def tables(C, R_) -> dict:
    T = {}
    for (a, s), P_ in C["oof"].items():
        T[(a, s)] = {k: root_row(a, pr, C["by"][k][0], C["by"][k][2], R_[(a, C["fold_of"][k])]["rule"]) for k, pr in P_.items() if (a, C["fold_of"][k]) in R_}
    return T


METRICS = {"succ_inf": lambda nm: lambda d: d[nm]["success"] if d["y0"] == 0 else None,
           "unnecessary": lambda nm: lambda d: d[nm]["false_repair"] if d["y0"] == 1 else None,
           "harmful_unnecessary": lambda nm: lambda d: d[nm]["harmful_unnecessary"] if d["y0"] == 1 else None,
           "success": lambda nm: lambda d: d[nm]["success"] if d["y0"] is not None else None,
           "abstain": lambda nm: lambda d: float(d[nm]["abstain"]),
           "m_success": lambda nm: lambda d: d[nm]["m"] if d[nm]["success"] else None,
           "J_success": lambda nm: lambda d: d[nm]["J"] if d[nm]["success"] and d[nm]["J"] is not None else None,
           "joint_nll": lambda nm: lambda d: d["joint_nll"], "auc_y": lambda nm: lambda d: d.get("auc_y"),
           "edit_01": lambda nm: lambda d: d.get("edit_01"), "edit_10": lambda nm: lambda d: d.get("edit_10"),
           "order": lambda nm: lambda d: d.get("order"), "omission": lambda nm: lambda d: d.get("omission")}


def seed_mean(T, arm, f, keep) -> dict:
    acc = collections.defaultdict(list)
    for (a, _), t in T.items():
        if a == arm:
            for k, d in t.items():
                if keep(k):
                    v = f(d)
                    if v is not None:
                        acc[k].append(float(v))
    return {k: float(np.mean(v)) for k, v in acc.items()}


def family_boot(a, b, fam, seed=0) -> dict:
    ks = sorted(set(a) & set(b))
    if not ks:
        return {"n": 0, "diff": None, "ci95": None, "ci99": None}
    fams = sorted({fam[k] for k in ks})
    s = np.array([sum(a[k] - b[k] for k in ks if fam[k] == f) for f in fams])
    n = np.array([sum(1 for k in ks if fam[k] == f) for f in fams])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(fams), (B, len(fams)))
    bs = s[idx].sum(1) / n[idx].sum(1)
    return {"n": len(ks), "families": len(fams), "diff": float(s.sum() / n.sum()), "a": float(np.mean([a[k] for k in ks])), "b": float(np.mean([b[k] for k in ks])),
            "ci95": [float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))], "ci99": [float(np.quantile(bs, 0.005)), float(np.quantile(bs, 0.995))]}


def summary(T, C, arm, pop) -> dict:
    keep = lambda k: C["corpus"][k] in POP[pop]  # noqa: E731
    out = {}
    for nm in ("RULE", "PRIMARY", "TRAVEL_BLIND"):
        out[nm] = {m: (float(np.mean(list(v.values()))) if (v := seed_mean(T, arm, METRICS[m](nm), keep)) else None) for m in METRICS}
        out[nm]["n_inf"] = len(seed_mean(T, arm, METRICS["succ_inf"](nm), keep))
        out[nm]["n_fea"] = len(seed_mean(T, arm, METRICS["unnecessary"](nm), keep))
        cats = collections.Counter(d[nm]["cat"] for (a, _), t in T.items() if a == arm for k, d in t.items() if keep(k))
        out[nm]["categories"] = dict(cats)
    pr = [(it_y, p) for (a, _), t in T.items() if a == arm for k, d in t.items() if keep(k) for it_y, p in d["items"]["y"]]
    out["prob_y"] = P.prob_metrics([("r", y, p) for y, p in pr]) if pr else None
    y0 = [(C["by"][k][2]["y0"], d["p_noop"]) for (a, _), t in T.items() if a == arm for k, d in t.items() if keep(k) and C["by"][k][2]["y0"] is not None]
    out["y0_auroc"] = Q.auroc(y0)
    out["y0_brier"] = E.brier(y0)
    return out


def contrast(T, C, a1, a2, pop, nm="RULE") -> dict:
    keep = lambda k: C["corpus"][k] in POP[pop]  # noqa: E731
    out = {m: family_boot(seed_mean(T, a1, METRICS[m](nm), keep), seed_mean(T, a2, METRICS[m](nm), keep), C["family"]) for m in METRICS}
    s, u, ll = out["succ_inf"], out["unnecessary"], out["joint_nll"]
    if s["diff"] is not None:
        out["IMPROVES_WITHIN_GUARDRAIL"] = bool(s["ci95"][0] > 0 and s["diff"] >= 0.10 and u["diff"] <= 0.05)
        out["PROMISING_BUT_GUARDRAIL_FAILED"] = bool(s["ci95"][0] > 0 and not out["IMPROVES_WITHIN_GUARDRAIL"])
        out["SUPERIOR_TO_DIRECT_criterion"] = bool(s["ci95"][0] > 0 and u["diff"] <= 0.02 and u["ci95"][1] <= 0.05)
    out["NLL_FAVOURS_FIRST"] = bool(ll["diff"] is not None and ll["ci95"][1] < 0)
    o = out["order"]
    out["ORDER_FAVOURS_FIRST"] = bool(o["diff"] is not None and o["ci95"][0] > 0)
    return out


def references(C) -> dict:
    """Non-learned references on every development root (single deterministic choice per root): NOOP, SHORTEST_ADMISSIBLE, DISPLACEMENT_RANK,
    ANALYTIC_ACCESS (geometry rule), VERIFY_FIRST (evaluator-only ceiling; cost = verifications)."""
    out = collections.defaultdict(dict)
    for k, (sv, lab, ev) in C["by"].items():
        if ev["y0"] is None:
            continue
        rows = [dict(c, p=1.0) for c in sv["cands"]]
        trav = {s: {"J": J} for s, J in ev["travel"].items() if J is not None}
        for nm, fn in P.REFERENCES.items():
            out[nm][k] = sel(rows, ev, fn(rows), trav)
        out["ANALYTIC_ACCESS"][k] = sel(rows, ev, analytic_rule(sv, rows), trav)
        vf = P.verify_first(ev, sv)
        out["VERIFY_FIRST"][k] = {"success": vf["success"], "verifications": vf["verifications"], "y0": ev["y0"]}
    return out


def ref_summary(Rf, C, pop) -> dict:
    keep = lambda k: C["corpus"][k] in POP[pop]  # noqa: E731
    res = {}
    for nm, t in Rf.items():
        ks = [k for k in t if keep(k)]
        inf = [t[k]["success"] for k in ks if C["by"][k][2]["y0"] == 0]
        fea = [t[k].get("false_repair", 0) for k in ks if C["by"][k][2]["y0"] == 1]
        res[nm] = {"succ_inf": float(np.mean(inf)) if inf else None, "unnecessary": float(np.mean(fea)) if fea and nm != "VERIFY_FIRST" else None,
                   "n_inf": len(inf), "n_fea": len(fea)}
        if nm == "VERIFY_FIRST":
            res[nm]["mean_verifications"] = float(np.mean([t[k]["verifications"] for k in ks]))
    return res


def evaluate() -> dict:
    t0 = time.process_time()
    C = context()
    R_ = rules(C)
    T = tables(C, R_)
    arms = [a for a in M.ARMS if any(k[0] == a for k in T)]
    Rf = references(C)
    res = {"runs_evaluated": len(C["F"]), "roots": {p: sum(C["corpus"][k] in POP[p] for k in C["by"]) for p in POP},
           "infeasible": {p: sum(C["corpus"][k] in POP[p] and C["by"][k][2]["y0"] == 0 for k in C["by"]) for p in POP},
           "repairable": {p: sum(C["corpus"][k] in POP[p] and C["by"][k][2]["y0"] == 0 and any(c["success"] == 1 for c in C["by"][k][2]["cands"]) for k in C["by"]) for p in POP},
           "rules": {f"{a}|f{fo}": v for (a, fo), v in R_.items()},
           "arms": {p: {a: summary(T, C, a, p) for a in arms} for p in POP},
           "references": {p: ref_summary(Rf, C, p) for p in POP},
           "contrasts": {p: {c: contrast(T, C, a1, a2, p) for c, (a1, a2) in M.CONTRASTS.items() if a1 in arms and a2 in arms} for p in POP},
           "travel_blind_contrast": {p: {a: contrast(T, C, a, a, p) for a in []} for p in POP}}
    res["accounting"] = {"eval_cpu_s": round(time.process_time() - t0, 1)}
    return res


if __name__ == "__main__":
    r = evaluate()
    (OUT / "EVALUATION_P17.json").write_text(json.dumps(r, indent=1, sort_keys=True, default=str))
    print(json.dumps({p: {a: {k: v for k, v in s["RULE"].items() if k in ("succ_inf", "unnecessary", "n_inf")} for a, s in r["arms"][p].items()} for p in r["arms"]}, indent=1))
