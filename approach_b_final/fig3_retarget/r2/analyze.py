#!/usr/bin/env python3
"""R2.1 / R2.2 analysis (evaluator side; gvlab2).  Joins frozen readouts with exact labels; family-cluster bootstrap CIs; decision rules from
R2_PREREG.json.  Writes R2_1_SCORER_{dom}.json and R2_2_CONNECTORS_{dom}.json (aggregates only; per-label rows stay private).
    python analyze.py DOM OUT_DIR"""
from __future__ import annotations

import collections, json, math, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent)]
import common as C  # noqa: E402

R21 = C.R2 / "r21"


def strat(rows, keyf, ykey, pkey):
    by = collections.defaultdict(list)
    for r in rows:
        by[keyf(r)].append(r)
    return {str(k): C.summary(v, ykey, pkey, B=400) for k, v in sorted(by.items(), key=lambda t: str(t[0]))}


def within_root(rows, ykey, pkey):
    """Concordance of pkey vs ykey within root + top-1 verified vs random over roots with mixed labels (cluster CI on the difference)."""
    by = collections.defaultdict(list)
    for r in rows:
        if r.get(ykey) in (0, 1):
            by[r["root"]].append(r)
    groups, top, rand, fam = [], [], [], []
    for rid, v in by.items():
        ys = {r[ykey] for r in v}
        if len(ys) < 2:
            continue
        groups.append([(r[ykey], r[pkey]) for r in v])
        best = max(v, key=lambda r: (r[pkey], -len(r.get("seq") or [])))
        top.append(best[ykey]); rand.append(np.mean([r[ykey] for r in v])); fam.append(v[0]["fam"])
    conc, npairs = C.concordance(groups)
    d = [t - r for t, r in zip(top, rand)]
    ci = C.cluster_boot(d, fam, lambda s: float(np.mean(s)) if s else None, B=1000) if d else None
    return {"mixed_roots": len(top), "mixed_families": len(set(fam)), "concordance": conc, "pairs": npairs,
            "top1_rate": float(np.mean(top)) if top else None, "random_rate": float(np.mean(rand)) if rand else None,
            "top1_minus_random": float(np.mean(d)) if d else None, "ci": ci}


def auroc_diff(rows_a, rows_b, ykey, pa, pb):
    """Paired / joint family-cluster bootstrap of AUROC(a) - AUROC(b)."""
    items = [("a", r) for r in rows_a] + [("b", r) for r in rows_b]
    def stat(s):
        A = [r for t, r in s if t == "a"]; Bb = [r for t, r in s if t == "b"]
        x, y = C.auroc([r[ykey] for r in A], [r[pa] for r in A]), C.auroc([r[ykey] for r in Bb], [r[pb] for r in Bb])
        return None if x is None or y is None else x - y
    return {"diff": stat(items), "ci": C.cluster_boot(items, [r["fam"] for _, r in items], stat, B=600)}


def p1(dom):
    X, Y = [], []
    for l in open(R21 / f"P1_{dom}.jsonl"):
        r = json.loads(l)
        r["grp"] = "FIT" if r["fit"] else ("VAL" if r["split"] == "val" else "TRAINCACHE")
        r["nb"] = C.nbin(dom, r["N"])
        (X if r["t"] == "X" else Y).append(r)
    for r in X:
        r["z"] = None if r["y_end"] is None else int(r["x"] == 1 and r["y_end"] == 1)
    out = {"counts": {g: {"X": sum(r["grp"] == g for r in X), "Y": sum(r["grp"] == g for r in Y)} for g in ("VAL", "TRAINCACHE", "FIT")}}
    held = [r for r in X if r["grp"] != "FIT"]; heldY = [r for r in Y if r["grp"] != "FIT"]
    for name, rows, yrows in (("heldout", held, heldY), ("fit_reference", [r for r in X if r["grp"] == "FIT"], [r for r in Y if r["grp"] == "FIT"])):
        o = {}
        o["p11~Z_all"] = C.summary([r for r in rows if r["z"] is not None], "z", "p11")
        o["p11~Z_by_m"] = strat([r for r in rows if r["z"] is not None], lambda r: r["m"], "z", "p11")
        o["p11~Z_by_N"] = strat([r for r in rows if r["z"] is not None], lambda r: r["nb"], "z", "p11")
        o["p11~Z_by_N_m"] = strat([r for r in rows if r["z"] is not None], lambda r: (r["nb"], r["m"]), "z", "p11")
        o["pX~X_by_N"] = strat(rows, lambda r: r["nb"], "x", "px")
        o["pX~X_by_m"] = strat(rows, lambda r: r["m"], "x", "px")
        o["pX1~X|Y=1_by_N"] = strat([r for r in rows if r["y_end"] == 1], lambda r: r["nb"], "x", "px1")
        o["pX0~X|Y=0_by_N"] = strat([r for r in rows if r["y_end"] == 0], lambda r: r["nb"], "x", "px0")
        o["pY~Y_by_N"] = strat(yrows, lambda r: r["nb"], "y", "py_global")
        o["pY~Y_by_h"] = strat(yrows, lambda r: r["h"], "y", "py_global")
        o["within_root_p11~Z"] = within_root([r for r in rows if r["z"] is not None], "z", "p11")
        o["within_root_p11~Z_by_N"] = {nb: within_root([r for r in rows if r["z"] is not None and r["nb"] == nb], "z", "p11") for nb in sorted({r["nb"] for r in rows})}
        out[name] = o
    # H_N: lowest vs highest populated N bin with a defined AUROC and >= 10 mixed families (held-out, p11~Z)
    bins = [b for b, s in out["heldout"]["p11~Z_by_N"].items() if s.get("auroc") is not None and s.get("mixed_families", 0) >= 10]
    order = [f"{lo}-{hi}" for lo, hi in C.NBINS[dom]]
    bins = sorted(bins, key=order.index)
    if len(bins) >= 2:
        lo, hi = bins[0], bins[-1]
        z = [r for r in held if r["z"] is not None]
        out["H_N_natural"] = {"low_bin": lo, "high_bin": hi, **auroc_diff([r for r in z if r["nb"] == hi], [r for r in z if r["nb"] == lo], "z", "p11", "p11")}
    else:
        out["H_N_natural"] = {"status": "UNIDENTIFIABLE", "populated_bins": bins}
    out["support_by_N"] = {nb: {"Z_decided": sum(1 for r in held if r["nb"] == nb and r["z"] is not None),
                                "Z_pos": sum(1 for r in held if r["nb"] == nb and r["z"] == 1),
                                "Y_pos": sum(1 for r in heldY if r["nb"] == nb and r["y"] == 1), "Y_n": sum(1 for r in heldY if r["nb"] == nb)} for nb in order + [f">{order[-1].split('-')[1]}"]}
    # H_m: m=3 vs m=1 on held-out p11~Z
    z = [r for r in held if r["z"] is not None]
    out["H_m"] = auroc_diff([r for r in z if r["m"] == 3], [r for r in z if r["m"] == 1], "z", "p11", "p11")
    # P2: Y_global vs Y_rebased on identical endpoints (h >= 1)
    yy = [r for r in heldY if r["h"] >= 1]
    out["P2_rebase"] = {"global": C.summary(yy, "y", "py_global"), "rebased": C.summary(yy, "y", "py_rebased"),
                        "by_h": {h: {"global": C.summary([r for r in yy if r["h"] == h], "y", "py_global", B=300),
                                     "rebased": C.summary([r for r in yy if r["h"] == h], "y", "py_rebased", B=300)} for h in (1, 2, 3)},
                        "by_N": {nb: {"global": C.summary([r for r in yy if r["nb"] == nb], "y", "py_global", B=300),
                                      "rebased": C.summary([r for r in yy if r["nb"] == nb], "y", "py_rebased", B=300)} for nb in sorted({r["nb"] for r in yy})},
                        "rebased_minus_global": auroc_diff(yy, yy, "y", "py_rebased", "py_global")}
    # P4: score distributions (decided Z) by m and Y
    out["P4_scores"] = {f"m{m}_z{zv}": {"n": len(v), "p11_mean": float(np.mean(v)) if v else None, "p11_q": [float(np.percentile(v, q)) for q in (10, 50, 90)] if v else None}
                        for m in (1, 2, 3) for zv in (0, 1) for v in [[r["p11"] for r in z if r["m"] == m and r["z"] == zv]]}
    return out


def p3(dom):
    d = json.loads((R21 / f"P3_c3b_{dom}.json").read_text())
    cands = [{**c, "fam": r["fam"], "root": r["root_id"], "nonempty": bool(c["group"]), "ex": r["root_id"]} for r in d["rows"] for c in r["cands"]]
    dec = [c for c in cands if c["y"] in (0, 1)]
    ne = [c for c in dec if c["nonempty"]]
    out = {"examples": d["n"], "retarget_parity_failures": d["retarget_parity_failures"], "blocked_at_S0": sum(r["y_tt_S0"] == 0 for r in d["rows"]),
           "Ytau_retargeted": C.summary(dec, "y", "py"), "Ytau_original_context": C.summary(dec, "y", "py_origctx"),
           "retargeted_minus_origctx": auroc_diff(dec, dec, "y", "py", "py_origctx")}
    tp = sum(c["admit_beats_empty"] and c["y"] == 1 for c in ne); fn = sum((not c["admit_beats_empty"]) and c["y"] == 1 for c in ne)
    fp = sum(c["admit_beats_empty"] and c["y"] == 0 for c in ne); tn = sum((not c["admit_beats_empty"]) and c["y"] == 0 for c in ne)
    ver = [c for c in ne if c["y"] == 1 and c["x"] == 1]
    out["admission_beats_empty"] = {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "fn_rate_enabling": fn / max(1, tp + fn), "fp_rate_nonenabling": fp / max(1, fp + tn),
                                    "verified_enablers": len(ver), "verified_enablers_discarded": sum(not c["admit_beats_empty"] for c in ver)}
    out["admission_admit_all"] = {"fn_rate_enabling": 0.0, "fp_rate_nonenabling": 1.0}
    groups = collections.defaultdict(list)
    for c in ne:
        groups[c["ex"]].append(c)
    conc, npairs = C.concordance([[(c["y"], c["dpy"]) for c in v] for v in groups.values()])
    zc, zp = C.concordance([[(int(c["y"] == 1 and c["x"] == 1), c["p11"]) for c in v] for v in groups.values()])
    top = [max(v, key=lambda c: c["p11"]) for v in groups.values() if any(c["y"] == 1 and c["x"] == 1 for c in v)]
    out["RETARGET_dpy_concordance_enabling_vs_not"] = {"concordance": conc, "pairs": npairs,
                                                       "ci": C.cluster_boot(list(groups.values()), [v[0]["fam"] for v in groups.values()],
                                                                            lambda s: C.concordance([[(c["y"], c["dpy"]) for c in v] for v in s])[0], B=600)}
    out["p11_concordance_verified_enabler"] = {"concordance": zc, "pairs": zp}
    out["top1_p11_is_verified_enabler"] = {"n": len(top), "rate": float(np.mean([c["y"] == 1 and c["x"] == 1 for c in top])) if top else None,
                                           "random": float(np.mean([np.mean([c["y"] == 1 and c["x"] == 1 for c in groups[t["ex"]]]) for t in top])) if top else None}
    out["N"] = C.summary([{"y": 1, "p": 1, "fam": 0}], "y", "p")["n"] and sorted({r["N"] for r in d["rows"]})
    return out


def staged(dom):
    d = json.loads((R21 / f"H_C_staged_{dom}.json").read_text())
    by = collections.defaultdict(list)
    for r in d:
        by[C.nbin(dom, r["N"])].append(r)
    return {nb: {"roots": len(v), "top1_in_staged": float(np.mean([r["top1_in_staged"] for r in v])), "top8_recall": float(np.mean([r["top8_recall"] for r in v])),
                 "n_exhaustive_median": float(np.median([r["n_exhaustive"] for r in v])), "n_staged_median": float(np.median([r["n_staged"] for r in v]))}
            for nb, v in sorted(by.items())}


def k45():
    d = json.loads((R21 / "OOD_k45_3d.json").read_text())
    for r in d:
        r["fam"] = r["root"]; r["z"] = None if r["x"] is None or r["y"] is None else int(r["x"] == 1 and r["y"] == 1)
    cont = [r for r in d if r["mode"] == "continuous"]
    return {"n": len(d), "continuous": {"p11~Z": C.summary([r for r in cont if r["z"] is not None], "z", "p11", B=400), "pX~X": C.summary(cont, "x", "px", B=400)},
            "by_m": {m: C.summary([r for r in cont if r["m"] == m and r["z"] is not None], "z", "p11", B=400) for m in (4, 5)},
            "within_root_p11~Z_continuous": within_root([{**r, "seq": None} for r in cont if r["z"] is not None], "z", "p11")}


if __name__ == "__main__":
    dom, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    res = {"dom": dom, "P1_P2_P4": p1(dom), "P3_C3b": p3(dom), "H_C_staged": staged(dom)}
    if dom == "3d":
        res["OOD_m45"] = k45()
    (out / f"R2_1_model_only_{dom}.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: (v if k != "P1_P2_P4" else {kk: v[kk] for kk in ("counts", "H_N_natural", "H_m", "support_by_N")}) for k, v in res.items()}, default=str)[:6000])
