"""BXY-P24 locked one-shot analysis (implements CONFIRM_ANALYSIS_P23_LOCK.json; frozen and hashed in P23 before any confirmation scene).

Input: one record per accepted confirmation root (label-free scorer view sv, evaluator view ev built from the engine's verified rows, the
construction record) and the SEALED frozen-ensemble predictions of D / E / A (DIRECT-GEO) / G, each with its frozen pooled rule.
Each frozen ensemble is ONE deterministic predictor, so every root contributes one binary outcome per arm (no seed replication); the
bootstrap unit is the root family (one family per confirmation root), B = 10,000, seed 0, percentile intervals, Holm within each family.
Populations: INF = initially infeasible (Y0 = 0 observed); AVAIL = INF with >= 1 teacher-verified candidate (X = 1 and Y = 1 replayed);
FEA = Y0 = 1; REP34 = AVAIL whose verified K (shortest verified candidate, every shorter admissible candidate decided) is 3 or 4.
Unobserved Y0 -> excluded from every success denominator (counted); an undecided chosen candidate counts as NOT a verified success (counted
per arm as 'unverified'). Labels: IMPROVES / POSITIVE_BELOW_THRESHOLD / GUARDRAIL_FAILED / REVERSED / NOT_ESTABLISHED (+ UNDERPOWERED flag)."""
from __future__ import annotations

import itertools
import math

import numpy as np

import bxy_p11 as P
import bxy_p12_eval as E12
import bxy_p13 as Q
import bxy_p17_eval as E
import bxy_p19_audit as A

B, SEED, ALPHA, TIE = 10000, 0, 0.05, 1e-8
ARMS = ("D:XYQ-GEO-SYM", "E:XY-UNC-SA-GEO-SYM", "A:DIRECT-GEO", "G:XYQ-GEO-SYM-ORDINV")
PRIMARY = {"D_vs_DIRECT": ("D:XYQ-GEO-SYM", "A:DIRECT-GEO"), "E_vs_DIRECT": ("E:XY-UNC-SA-GEO-SYM", "A:DIRECT-GEO"),
           "D_vs_E_coupling": ("D:XYQ-GEO-SYM", "E:XY-UNC-SA-GEO-SYM")}
ORDER = {"O1_D_vs_G_strict_order": ("D:XYQ-GEO-SYM", "G:XYQ-GEO-SYM-ORDINV", "order"),
         "O2_D_vs_G_REP34_success": ("D:XYQ-GEO-SYM", "G:XYQ-GEO-SYM-ORDINV", "rep34"),
         "O3_E_vs_G_strict_order": ("E:XY-UNC-SA-GEO-SYM", "G:XYQ-GEO-SYM-ORDINV", "order")}
GATE = {"success_gain": 0.10, "unnecessary_max_increase": 0.05}
MIN_N = {"INF": 60, "AVAIL": 30, "REP34": 30, "FEA": 30, "order_roots": 20, "K_stratum_inferential": 10}


def verified_k(ev, sv):
    """(K_catalogue, every shorter admissible candidate decided) for an initially infeasible root with a verified candidate."""
    if ev["y0"] != 0:
        return (0 if ev["y0"] == 1 else None), True
    ok = [c["m"] for c, e in zip(sv["cands"], ev["cands"]) if e["success"] == 1]
    if not ok:
        return None, True
    K = min(ok)
    return K, all(e["success"] is not None for c, e in zip(sv["cands"], ev["cands"]) if c["admissible"] and 0 < c["m"] < K)


def root_rows(r, rules) -> dict:
    """Per-arm selection outcome of one root (P.choose on the frozen ensemble rows; outcomes from the teacher-verified evaluator view)."""
    sv, ev, lab = r["sv"], r["ev"], r["lab"]
    trav = {s: {"J": J} for s, J in E.travel_of(sv, lab).items()}
    out = {}
    for arm in ARMS:
        rows = r["preds"][arm]["cands"]
        if [c["sig"] for c in rows] != [c["sig"] for c in sv["cands"]]:
            raise RuntimeError(f"{r['key']}: sealed prediction rows differ from the evaluator candidate list")
        i = P.choose(rows, rules[arm])
        out[arm] = E.sel(rows, ev, i, trav) | {"p_noop": next(c["p"] for c in rows if c["m"] == 0)}
    for nm, fn in P.REFERENCES.items():
        rows = [dict(c, p=1.0) for c in sv["cands"]]
        out[nm] = E.sel(rows, ev, fn(rows), trav)
    rows = [dict(c, p=1.0) for c in sv["cands"]]
    out["ANALYTIC_ACCESS"] = E.sel(rows, ev, E.analytic_rule(sv, rows), trav)
    vf = P.verify_first(ev, sv)
    out["VERIFY_FIRST_ORACLE"] = {"success": vf["success"], "verifications": vf["verifications"]}
    return out


def strict_order(r, arm):
    """Root-level strict order concordance: same action multiset, same endpoint, both F1-admissible and observed, X discordant; |dpx| <= 1e-8
    scores 0.5. Returns (all, certified-negative subset) means or None."""
    ev, px = r["ev"], r["preds"][arm]["vars"].get("px")
    if px is None:
        return None, None
    al, ce = [], []
    for g in ev["order_groups"]:
        for u, v in itertools.combinations(g["members"], 2):
            sa, sb = A._seq(ev["x_keys"][u["xi"]]), A._seq(ev["x_keys"][v["xi"]])
            if u["x"] == v["x"] or len(sa) != len(sb) or sorted(sa) != sorted(sb) or sa == sb:
                continue
            pos, neg = (u, v) if u["x"] == 1 else (v, u)
            d = px[pos["xi"]] - px[neg["xi"]]
            sc = 0.5 if abs(d) <= TIE else float(d > 0)
            al.append(sc)
            if neg["negative_kind"] == "CERTIFIED":
                ce.append(sc)
    return (float(np.mean(al)) if al else None), (float(np.mean(ce)) if ce else None)


def boot(a: dict, b: dict, fam: dict) -> dict:
    """Paired family bootstrap of mean(a - b) over common roots: point, 95% CI, two-sided p, and the draws (for Holm-level intervals)."""
    ks = sorted(set(a) & set(b))
    if not ks:
        return {"n": 0, "diff": None}
    fams = sorted({fam[k] for k in ks})
    s = np.array([sum(a[k] - b[k] for k in ks if fam[k] == f) for f in fams])
    n = np.array([sum(1 for k in ks if fam[k] == f) for f in fams])
    idx = np.random.default_rng(SEED).integers(0, len(fams), (B, len(fams)))
    bs = s[idx].sum(1) / n[idx].sum(1)
    p = float(min(1.0, 2 * min(np.mean(bs <= 0), np.mean(bs >= 0))))
    return {"n": len(ks), "families": len(fams), "diff": float(s.sum() / n.sum()), "a": float(np.mean([a[k] for k in ks])), "b": float(np.mean([b[k] for k in ks])),
            "ci95": [float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))], "p_two_sided": p, "_draws": bs}


def holm(tests: dict) -> dict:
    """Holm step-down on the bootstrap p-values; a rejected test also carries its Holm-level percentile interval."""
    order = sorted((k for k, t in tests.items() if t.get("diff") is not None), key=lambda k: tests[k]["p_two_sided"])
    m, going = len(order), True
    for j, k in enumerate(order):
        lev = ALPHA / (m - j)
        t = tests[k]
        t["holm_level"] = lev
        t["ci_holm"] = [float(np.quantile(t["_draws"], lev / 2)), float(np.quantile(t["_draws"], 1 - lev / 2))]
        t["holm_reject"] = bool(going and t["p_two_sided"] < lev)
        going = going and t["holm_reject"]
        t["p_holm"] = float(min(1.0, max(tests[q]["p_two_sided"] * (m - i) for i, q in enumerate(order[:j + 1]))))
    return tests


def label(main, consist, unnec, threshold=True) -> str:
    if main.get("diff") is None:
        return "NOT_ESTABLISHED"
    pos = main.get("holm_reject") and main["ci_holm"][0] > 0 and (consist is None or (consist.get("diff") is not None and consist["ci95"][0] > 0))
    if main.get("holm_reject") and main["ci_holm"][1] < 0:
        return "REVERSED"
    if not pos:
        return "NOT_ESTABLISHED"
    if unnec.get("diff") is not None and unnec["diff"] > GATE["unnecessary_max_increase"]:
        return "GUARDRAIL_FAILED"
    return "IMPROVES" if (not threshold or main["diff"] >= GATE["success_gain"]) else "POSITIVE_BELOW_THRESHOLD"


def wilson(k, n, z=1.96):
    if not n:
        return None
    p, d = k / n, 1 + z * z / n
    c, h = (p + z * z / (2 * n)) / d, z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0.0, c - h), min(1.0, c + h)]


def _strip(t):
    return {k: v for k, v in t.items() if k != "_draws"}


def evaluate(R: list, rules: dict) -> dict:
    """R: [{"key", "family", "sv", "lab", "ev", "rec", "preds": {arm: {"cands", "vars"}}}] for EVERY accepted root (none dropped)."""
    T, info = {}, {}
    for r in R:
        T[r["key"]] = root_rows(r, rules)
        K, decided = verified_k(r["ev"], r["sv"])
        kc = (r["rec"].get("construction") or {}).get("K_cert")
        info[r["key"]] = {"y0": r["ev"]["y0"], "K": K if decided else None, "K_undecided": not decided, "K_cert": kc,
                          "certified": bool(K is not None and decided and K >= 2 and kc == K), "family": r["family"],
                          "available": int(r["ev"]["y0"] == 0 and any(c["success"] == 1 for c in r["ev"]["cands"])),
                          "gen_family": r["rec"]["spec"]["family"], "K_intent": r["rec"]["spec"]["K_intent"]}
    fam = {k: v["family"] for k, v in info.items()}
    INF = [k for k, v in info.items() if v["y0"] == 0]
    AV = [k for k in INF if info[k]["available"]]
    FEA = [k for k, v in info.items() if v["y0"] == 1]
    REP34 = [k for k in AV if info[k]["K"] in (3, 4)]
    col = lambda arm, ks, f="success": {k: float(T[k][arm][f]) for k in ks}  # noqa: E731
    pops = {"roots": len(R), "y0_unobserved": sum(v["y0"] is None for v in info.values()), "INF": len(INF), "AVAIL": len(AV), "FEA": len(FEA), "REP34": len(REP34)}
    out = {"populations": pops, "underpowered": {p: pops[p] < n for p, n in MIN_N.items() if p in pops}}
    fam_p = {}
    for nm, (a1, a2) in PRIMARY.items():
        fam_p[nm] = {"U": boot(col(a1, INF), col(a2, INF), fam), "C": boot(col(a1, AV), col(a2, AV), fam),
                     "unnecessary": boot(col(a1, FEA, "false_repair"), col(a2, FEA, "false_repair"), fam)}
    holm({nm: v["U"] for nm, v in fam_p.items()})
    out["primary"] = {nm: {"U_unconditional": _strip(v["U"]), "C_availability_conditioned": _strip(v["C"]), "unnecessary": _strip(v["unnecessary"]),
                           "label": label(v["U"], v["C"], v["unnecessary"])} for nm, v in fam_p.items()}
    sec = {nm: {"S": boot(col(a1, REP34), col(a2, REP34), fam), "unnecessary": fam_p[nm]["unnecessary"]} for nm, (a1, a2) in PRIMARY.items()}
    holm({nm: v["S"] for nm, v in sec.items()})
    out["secondary_K34"] = {nm: {"REP34_conditional": _strip(v["S"]), "label": label(v["S"], None, v["unnecessary"]),
                                 "underpowered": pops["REP34"] < MIN_N["REP34"]} for nm, v in sec.items()}
    so = {arm: {k: strict_order(r, arm) for r in R for k in [r["key"]]} for arm in ARMS if arm != "A:DIRECT-GEO"}
    odr = {}
    for nm, (a1, a2, kind) in ORDER.items():
        if kind == "order":
            x = {k: v[0] for k, v in so[a1].items() if v[0] is not None}
            y = {k: v[0] for k, v in so[a2].items() if v[0] is not None}
            odr[nm] = {"T": boot(x, y, fam), "unnecessary": {"diff": None}, "threshold": False,
                       "certified": _strip(boot({k: v[1] for k, v in so[a1].items() if v[1] is not None}, {k: v[1] for k, v in so[a2].items() if v[1] is not None}, fam))}
        else:
            odr[nm] = {"T": boot(col(a1, REP34), col(a2, REP34), fam), "unnecessary": boot(col(a1, FEA, "false_repair"), col(a2, FEA, "false_repair"), fam), "threshold": True}
    holm({nm: v["T"] for nm, v in odr.items()})
    out["order"] = {nm: {"test": _strip(v["T"]), "certified_subset": v.get("certified"), "unnecessary": _strip(v["unnecessary"]) if v["unnecessary"].get("diff") is not None else None,
                         "label": label(v["T"], None, v["unnecessary"], v["threshold"])} for nm, v in odr.items()}
    out["order_concordance_level"] = {arm: {"all_mean": _mean([v[0] for v in so[arm].values()]), "certified_mean": _mean([v[1] for v in so[arm].values()]),
                                            "roots": sum(v[0] is not None for v in so[arm].values())} for arm in so}
    arms = list(ARMS) + list(P.REFERENCES) + ["ANALYTIC_ACCESS"]
    out["arms"] = {a: {"U": _mean([T[k][a]["success"] for k in INF]), "C": _mean([T[k][a]["success"] for k in AV]),
                       "unnecessary": _mean([T[k][a]["false_repair"] for k in FEA]), "harmful_unnecessary": _mean([T[k][a]["harmful_unnecessary"] for k in FEA]),
                       "noop_correct_K0": _mean([T[k][a]["noop_correct"] for k in FEA]), "unverified_choice": sum(T[k][a]["unverified"] for k in INF),
                       "abstain_INF": sum(bool(T[k][a]["abstain"]) for k in INF),
                       "U_wilson": wilson(sum(T[k][a]["success"] for k in INF), len(INF)), "C_wilson": wilson(sum(T[k][a]["success"] for k in AV), len(AV))} for a in arms}
    out["oracle_verify_first"] = {"U": _mean([T[k]["VERIFY_FIRST_ORACLE"]["success"] for k in INF]), "mean_verifications_INF": _mean([T[k]["VERIFY_FIRST_ORACLE"]["verifications"] for k in INF]),
                                  "note": "evaluator-only upper bound with teacher verification calls; never deployed or learned"}
    st = {}
    for K in (1, 2, 3, 4):
        for cert in (False, True):
            ks = [k for k in AV if info[k]["K"] == K and (info[k]["certified"] or not cert)]
            st[f"K{K}{'_certified' if cert else ''}"] = {"n": len(ks), "inferential": len(ks) >= MIN_N["K_stratum_inferential"],
                                                         **{a: {"success": _mean([T[k][a]["success"] for k in ks]), "wilson": wilson(sum(T[k][a]["success"] for k in ks), len(ks))} for a in ARMS}}
    out["strata_availability_conditioned"] = st
    out["calibration_y0"] = {a: {"auroc": Q.auroc([(info[k]["y0"], T[k][a]["p_noop"]) for k in INF + FEA]), "brier": E12.brier([(info[k]["y0"], T[k][a]["p_noop"]) for k in INF + FEA])}
                             for a in ARMS}
    both = {a: [k for k in AV if T[k][a]["success"] and T[k]["A:DIRECT-GEO"]["success"] and T[k][a]["J"] is not None and T[k]["A:DIRECT-GEO"]["J"] is not None] for a in ARMS}
    out["travel_matched_successes"] = {a: {"n": len(ks), "J_arm": _mean([T[k][a]["J"] for k in ks]), "J_direct": _mean([T[k]["A:DIRECT-GEO"]["J"] for k in ks])} for a, ks in both.items()}
    out["coverage"] = {"by_generator_family": _count(info, "gen_family"), "K_undecided_roots": sum(v["K_undecided"] for v in info.values()),
                       "verified_K": {str(K): sum(v["K"] == K for v in info.values()) for K in range(7)},
                       "certified_K": {str(K): sum(v["certified"] and v["K"] == K for v in info.values()) for K in (2, 3, 4)}}
    out["per_root"] = {k: {"info": info[k], **{a: {kk: T[k][a].get(kk) for kk in ("chosen", "sig", "success", "false_repair", "m", "J")} for a in ARMS}} for k in sorted(T)}
    return out


def _mean(v):
    v = [x for x in v if x is not None]
    return float(np.mean(v)) if v else None


def _count(info, f):
    out = {}
    for v in info.values():
        d = out.setdefault(str(v[f]), {"roots": 0, "INF": 0, "AVAIL": 0})
        d["roots"] += 1
        d["INF"] += v["y0"] == 0
        d["AVAIL"] += v["available"]
    return out
