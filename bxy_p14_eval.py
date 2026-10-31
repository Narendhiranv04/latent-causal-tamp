"""BXY-P14 evaluation of the finished P14 runs, exactly as frozen in TRAINING_DESIGN_P14.json (written before any P14 run).

  units      out-of-fold predictions of each (arm, seed) over the 176 TRAIN roots (each root scored by the fold model that never trained or
             early-stopped on it); per-root seed means; uncertainty = paired FAMILY-cluster bootstrap (B = 10000, families resampled with
             replacement, roots of a family kept together), 95 % and Bonferroni 99 % intervals; root and family counts reported
  selection  PRIMARY (P11.1) and PONLY (penalty-free) for every arm -> training effect (arms, same rule) vs selection effect (rules, same
             checkpoints) are separated (2 x 2 per arm)
  endpoints  success on the 45 initially infeasible roots (primary), the 39 repairable ones, unnecessary repairs on the 131 feasible roots
             (guardrail), overall success, error categories, actions / displacement / witnessed travel of successful choices
  mechanism  within-root edited-Y / success / X AUROC, matched edit contrasts, Y0 AUROC, calibration, order concordance, omission signs
Labels and evaluator views are read only here (parent process); the workers never saw them."""
from __future__ import annotations

import collections
import json
import time

import numpy as np

import bxy_p11 as P
import bxy_p12_eval as E
import bxy_p12_run as R
import bxy_p13 as Q
import bxy_p14 as H

OUT = H.OUT
B = 10000


def finished() -> dict:
    L = json.loads((OUT / "LEDGER.json").read_text())
    out = {}
    for rid, r in L["runs"].items():
        if r["status"] == "DONE" and R.valid_result(OUT, rid):
            rd = OUT / "runs" / R.safe(rid)
            res = json.loads((rd / "RESULT.json").read_text())
            out[rid] = (res["spec"], res, json.loads((rd / "predictions.json").read_text()))
    return out


def context() -> dict:
    sc, D, Rr, I = P.load()
    V = P.build(splits=("train",), sc=sc, D=D, R=Rr, I=I)
    by = {sv["key"]: (sv, lab, ev) for sv, lab, ev in V}
    xr, yr = {r["x_key"]: r for r in sc["x_queries"]}, {r["y_key"]: r for r in sc["y_queries"]}
    F_ = finished()
    oof = collections.defaultdict(dict)
    for rid, (spec, res, pr) in F_.items():
        for k, v in pr.items():
            if k in oof[(spec["arm"], spec["seed"])]:
                raise RuntimeError(f"{k} predicted twice")
            oof[(spec["arm"], spec["seed"])][k] = v
    return {"by": by, "trav": {k: E.witnessed_travel(sv, lab, ev, (xr, yr)) for k, (sv, lab, ev) in by.items()}, "F": F_, "oof": dict(oof),
            "family": {k: ev["family"] for k, (_, _, ev) in by.items()}}


# ------------------------------------------------------------------ per root
def root_row(arm, pred, sv, ev, trav) -> dict:
    rows, base = pred["cands"], H.ARMS[arm]["base"]
    out = {"y0": ev["y0"], "stratum": ev["stratum"], "repairable": int(ev["y0"] == 0 and any(c["success"] == 1 for c in ev["cands"])),
           "p_noop": next(r["p"] for r in rows if r["m"] == 0), "edit": Q.edit_contrast(pred, sv, ev), **Q.within(pred, ev, sv)}
    it = E.root_items(base, pred, sv, ev)
    out |= {"ll_s": E.ll(it["s"]), "ll_x": E.ll(it["x"]), "ll_y": E.ll(it["y"]), "items": it}
    for nm, rf in H.RULES.items():
        ru = rf(arm)
        i = P.choose(rows, ru)
        s = E.sel_row(rows, ev, i, trav)
        out[nm] = {"success": s["success"], "false_repair": s["false_repair"], "noop_correct": s["noop_correct"], "m": s["m"], "cd": s["cd"],
                   "J": s["J"], "parts": s["parts"], "sig": s["sig"], "cat": Q.category(rows, ev, i, ru), "rank": Q.ranking(rows, ev, ru)}
    return out


def tables(C) -> dict:
    return {key: {k: root_row(key[0], pr, C["by"][k][0], C["by"][k][2], C["trav"][k]) for k, pr in P_.items()} for key, P_ in C["oof"].items()}


def seed_mean(T, arm, f) -> dict:
    acc = collections.defaultdict(list)
    for (a, _), t in T.items():
        if a == arm:
            for k, d in t.items():
                v = f(d)
                if v is not None:
                    acc[k].append(v)
    return {k: float(np.mean(v)) for k, v in acc.items()}


METRICS = {"succ_inf": lambda r: (lambda d: d[r]["success"] if d["y0"] == 0 else None),
           "succ_repairable": lambda r: (lambda d: d[r]["success"] if d["repairable"] else None),
           "unnecessary": lambda r: (lambda d: d[r]["false_repair"] if d["y0"] == 1 else None),
           "success": lambda r: (lambda d: d[r]["success"]),
           "noop_correct": lambda r: (lambda d: d[r]["noop_correct"])}


def family_boot(a: dict, b: dict, fam: dict, B=B, seed=0) -> dict:
    """Paired family-cluster bootstrap of the root mean of a - b."""
    ks = sorted(set(a) & set(b))
    fams = sorted({fam[k] for k in ks})
    by = {f: [a[k] - b[k] for k in ks if fam[k] == f] for f in fams}
    s = np.array([sum(by[f]) for f in fams])
    n = np.array([len(by[f]) for f in fams])
    idx = np.random.default_rng(seed).integers(0, len(fams), (B, len(fams)))
    bs = s[idx].sum(1) / n[idx].sum(1)
    d = float(s.sum() / n.sum()) if len(ks) else None
    return {"roots": len(ks), "families": len(fams), "diff": d, "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
            "ci99": [float(np.percentile(bs, 0.5)), float(np.percentile(bs, 99.5))]}


def contrast(T, fam, A_, B_) -> dict:
    (aa, ra), (ab, rb) = A_, B_
    out = {m: family_boot(seed_mean(T, aa, METRICS[m](ra)), seed_mean(T, ab, METRICS[m](rb)), fam) for m in METRICS}
    s, u = out["succ_inf"], out["unnecessary"]
    out["IMPROVES"] = bool(s["ci95"][0] > 0 and u["diff"] <= 0.05)
    out["IMPROVES_bonferroni99"] = bool(s["ci99"][0] > 0 and u["diff"] <= 0.05)
    out["TARGET_MET"] = bool(out["IMPROVES"] and s["diff"] >= 0.10)
    return out


def summary(T, C, arm) -> dict:
    out = {"roots": len(seed_mean(T, arm, lambda d: 1.0)), "seeds": sorted(s for a, s in T if a == arm)}
    for nm in H.RULES:
        o = {m: float(np.mean(list(v.values()))) if (v := seed_mean(T, arm, METRICS[m](nm))) else None for m in METRICS}
        rows = [d[nm] for (a, _), t in T.items() if a == arm for d in t.values()]
        cats = collections.Counter(r["cat"] for r in rows)
        ninf = sum(v for c, v in cats.items() if not c.startswith(("CORRECT", "UNNEC")))
        o["categories"] = {c: v / (ninf if not c.startswith(("CORRECT", "UNNEC")) else (len(rows) - ninf)) for c, v in sorted(cats.items())}
        ok = [r for r in rows if r["success"]]
        o |= {"mean_m_choice": float(np.mean([r["m"] for r in rows])), "mean_cd_choice": float(np.mean([r["cd"] for r in rows])),
              "mean_m_success": float(np.mean([r["m"] for r in ok])) if ok else None,
              "mean_J_success": float(np.mean([r["J"] for r in ok if r["J"] is not None])) if any(r["J"] is not None for r in ok) else None,
              "mean_J_successful_corrections": float(np.mean([r["J"] for r in ok if r["J"] is not None and r["m"] > 0])) if any(
                  r["J"] is not None and r["m"] > 0 for r in ok) else None,
              "top1_repair_by_p": float(np.mean([r["rank"]["top1_p"] for r in rows if r["rank"]])) if any(r["rank"] for r in rows) else None}
        out[nm] = o
    mean = lambda f: (lambda d: float(np.mean(list(d.values()))) if d else None)(seed_mean(T, arm, f))  # noqa: E731
    out["mechanism"] = {"within_auc_y": mean(lambda d: d.get("auc_y")), "within_auc_succ": mean(lambda d: d.get("auc_succ")),
                        "within_auc_x": mean(lambda d: d.get("auc_x")),
                        "edit_agree_s0_feasible": mean(lambda d: d["edit"].get("agree") if d["y0"] == 1 else None),
                        "edit_agree_s0_infeasible": mean(lambda d: d["edit"].get("agree") if d["y0"] == 0 else None),
                        "edit_shift_by_label": edit_shifts(C, arm),
                        "y0_auroc": Q.auroc([(C["by"][k][2]["y0"], v) for k, v in seed_mean(T, arm, lambda d: d["p_noop"]).items()]),
                        "p_noop_mean": {str(y): float(np.mean([v for k, v in seed_mean(T, arm, lambda d: d["p_noop"]).items() if C["by"][k][2]["y0"] == y]))
                                        for y in (0, 1)},
                        "ll_s": mean(lambda d: d["ll_s"]), "ll_y": mean(lambda d: d["ll_y"]), "ll_x": mean(lambda d: d["ll_x"])}
    pooled = {s: [i for (a, _), t in T.items() if a == arm for d in t.values() for i in d["items"][s]] for s in ("s", "x", "y")}
    out["prob"] = {s: P.prob_metrics([("r", y, p) for y, p in v]) | {"reliability": E.reliability(v)} for s, v in pooled.items() if v}
    return out


def edit_shifts(C, arm) -> dict:
    """Mean raw P(Y_s) - P(Y0) over every observed edited scene, keyed by '<y0><y_s>' (all seeds' out-of-fold predictions)."""
    acc = collections.defaultdict(list)
    for (a, _), P_ in C["oof"].items():
        if a != arm:
            continue
        for k, pr in P_.items():
            py = pr["vars"]["py"]
            if py is None:
                continue
            sv, lab, _ = C["by"][k]
            y0 = lab["obs_y"][sv["y0"]]
            for q, y in lab["obs_y"].items():
                if q != sv["y0"]:
                    acc[f"{y0}{y}"].append(py[q] - py[sv["y0"]])
    return {k: {"mean": float(np.mean(v)), "n": len(v)} for k, v in sorted(acc.items())}


def evaluate() -> dict:
    t0, w0 = time.process_time(), time.time()
    C = context()
    T = tables(C)
    arms = [a for a in H.ARMS if any(k[0] == a for k in T)]
    fam = C["family"]
    roots = sorted({k for t in T.values() for k in t})
    res = {"runs_evaluated": len(C["F"]), "roots": len(roots), "families": len({fam[k] for k in roots}),
           "infeasible_roots": sum(C["by"][k][2]["y0"] == 0 for k in roots), "repairable_roots": sum(T[next(iter(T))][k]["repairable"] for k in roots),
           "arms": {a: summary(T, C, a) for a in arms}}
    res["contrasts"] = {c: contrast(T, fam, *v) for c, v in H.CONTRASTS.items() if v[0][0] in arms and v[1][0] in arms}
    res["contrasts"]["C4"] = {a: contrast(T, fam, *v) for a, v in H.C4.items() if a in arms}
    res["vs_direct"] = {f"{a}|{r}": contrast(T, fam, (a, r), ("DIRECT", "PRIMARY")) for a in arms if a != "DIRECT" for r in H.RULES}
    noop = {k: {"y0": C["by"][k][2]["y0"], "repairable": T[next(iter(T))][k]["repairable"], "NOOP": {"success": int(C["by"][k][2]["y0"] == 1), "false_repair": 0,
                                                                                                  "noop_correct": int(C["by"][k][2]["y0"] == 1)}} for k in roots}
    Tn = dict(T) | {("NOOP", 0): noop}
    res["vs_noop"] = {f"{a}|{r}": contrast(Tn, fam, (a, r), ("NOOP", "NOOP")) for a in arms for r in H.RULES}
    Tp = {k: {r: {"pred": C["oof"][k][r]} for r in v} for k, v in T.items()}
    res["order_omission"] = {a: {"order": E.strip(E.order_pairs(Tp, a, C["by"])), "omission": E.omissions(Tp, a, C["by"])["sign_agreement"]} for a in arms}
    res["runs"] = {rid: {"arm": s["arm"], "seed": s["seed"], "fold": s["train"], "best_update": r["info"]["best_update"], "updates": r["info"]["updates_run"],
                         "es_nll": r["info"]["es_nll"], "clipped": r["numerical"]["clipped_updates"], "nonfinite": r["numerical"]["nonfinite_updates"],
                         "params": r["info"]["params"]} for rid, (s, r, _) in C["F"].items()}
    res["choices"] = {f"{a}|{s}": {k: {nm: {"sig": d[nm]["sig"], "success": d[nm]["success"]} for nm in H.RULES} | {"y0": d["y0"], "p_noop": d["p_noop"]}
                                   for k, d in t.items()} for (a, s), t in T.items()}
    res["accounting"] = {"evaluation_cpu_s": time.process_time() - t0, "evaluation_wall_s": time.time() - w0}
    return res


if __name__ == "__main__":
    r = evaluate()
    (OUT / "EVALUATION_P14.json").write_text(json.dumps(r, indent=1, sort_keys=True, default=str))
    print(json.dumps(r["accounting"]))
