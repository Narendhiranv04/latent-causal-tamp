"""P17 analyses (frozen before any prospective outcome is inspected).

B: root-level outcomes on DECIDED originals, separated into the no-op decision (feasible originals), the repair decision (infeasible
originals) and admission (how often a non-empty repair is chosen, and its physical precision); strict TOP1 = correct no-op OR strict repair
success (VERIFIED + replay CLEAR). Baselines ALWAYS_EMPTY, random, geometry and VERIFY_FIRST (its physical calls and CPU counted).
D: p16_eval.d_analysis on the common roots (primary Dp17 vs geometry) + effort (nodes / virtual CPU to the first verified plan)."""
from __future__ import annotations

import numpy as np

DECIDED = ("VERIFIED", "CERTIFIED_INFEASIBLE", "STATIC_INVALID")
B_PRIMARY = ("LB", "empty_always")
B_SECONDARY = (("LB", "verify_first"), ("LB+G", "LB"), ("LB+G", "LB+G|nocpl"), ("LB+G", "LB+G@LB"), ("LB+G", "LB-W"), ("LB", "FULLB"),
               ("LB", "LB-F2"), ("LB", "LC"), ("LB", "A"), ("LB", "SF"), ("LB", "P13:K-B"), ("LB+G", "empty_always"), ("LB", "geometry"))


def _ok_noop(x):
    return x["choice"].endswith(":empty") and x["status"] == "VERIFIED"


def _ok_rep(x):
    return x["choice"] not in ("ABSTAIN",) and not x["choice"].endswith(":empty") and x["status"] == "VERIFIED" and bool(x.get("replay"))


def _vf(v):
    """VERIFY_FIRST as an arm row: EMPTY if the original target certifies, else SEARCH (geometry-guided corrected search)."""
    x = v["verify_first"]
    return {"choice": "seq:x:empty" if x["choice"] == "EMPTY" else "SEARCH", "status": x["status"], "replay": x["status"] == "VERIFIED",
            "moves": x.get("moves"), "travel": x.get("travel"), "used": x.get("used"), "cpu_virtual": x.get("cpu_virtual")}


def b_analysis(rows) -> dict:
    """rows: {root: {'family', 'b': b_root output (+ 'verify_first')}}."""
    import p16_eval as p16e
    R = {k: v for k, v in rows.items() if v["b"]["y0_status"] in DECIDED}
    arm_rows = {k: dict(v["b"]["arms"], **({"verify_first": _vf(v["b"])} if "verify_first" in v["b"] else {})) for k, v in R.items()}
    feas = [k for k in R if R[k]["b"]["y0_status"] == "VERIFIED"]
    inf = [k for k in R if k not in feas]
    arms = sorted({a for v in arm_rows.values() for a in v})
    ok = lambda k, a: _ok_noop(arm_rows[k][a]) if k in feas else _ok_rep(arm_rows[k][a])  # noqa: E731
    per = {}
    for a in arms:
        ks = [k for k in R if a in arm_rows[k]]
        f, i = [k for k in feas if k in ks], [k for k in inf if k in ks]
        ch = lambda k: arm_rows[k][a]["choice"]  # noqa: E731
        rep = lambda k: ch(k) not in ("ABSTAIN",) and not ch(k).endswith(":empty")  # noqa: E731
        succ_rep = [k for k in i if _ok_rep(arm_rows[k][a])]
        used = [arm_rows[k][a].get("used") or {} for k in ks]
        per[a] = {"n": len(ks), "strict_top1": float(np.mean([ok(k, a) for k in ks])) if ks else None,
                  "noop": {"feasible_n": len(f), "correct": sum(_ok_noop(arm_rows[k][a]) for k in f), "unnecessary_relocation": sum(rep(k) for k in f),
                           "abstain": sum(ch(k) == "ABSTAIN" for k in f)},
                  "repair": {"infeasible_n": len(i), "success": len(succ_rep), "wrong_noop": sum(ch(k).endswith(":empty") for k in i),
                             "abstain": sum(ch(k) == "ABSTAIN" for k in i), "attempted": sum(rep(k) for k in i),
                             "moves_mean": float(np.mean([arm_rows[k][a]["moves"] for k in succ_rep])) if succ_rep else None,
                             "travel_mean": float(np.mean([arm_rows[k][a]["travel"] for k in succ_rep])) if succ_rep else None},
                  "admission": {"repairs_chosen": sum(rep(k) for k in ks), "rate": float(np.mean([rep(k) for k in ks])) if ks else None,
                                "precision": float(np.mean([arm_rows[k][a]["status"] == "VERIFIED" for k in ks if rep(k)])) if any(rep(k) for k in ks) else None,
                                "on_feasible": sum(rep(k) for k in f), "on_infeasible": sum(rep(k) for k in i)},
                  "physical_calls_mean": {c: float(np.mean([u.get(c, 0) for u in used])) for c in ("motion_checks", "online_moves", "goal_plans", "transit_plans")},
                  "cpu_virtual_mean": float(np.mean([arm_rows[k][a]["cpu_virtual"] for k in ks])) if a == "verify_first" and ks else None}
    a, b = B_PRIMARY
    common = lambda x, y: [k for k in R if x in arm_rows[k] and y in arm_rows[k]]  # noqa: E731
    prim = p16e.paired([ok(k, a) for k in common(a, b)], [ok(k, b) for k in common(a, b)]) if a in arms and b in arms else None
    sec = {}
    for x, y in B_SECONDARY:
        if x in arms and y in arms:
            ks = common(x, y)
            sec[f"{x}_vs_{y}|strict_top1"] = p16e.paired([ok(k, x) for k in ks], [ok(k, y) for k in ks])
            sec[f"{x}_vs_{y}|noop"] = p16e.paired([_ok_noop(arm_rows[k][x]) for k in ks if k in feas], [_ok_noop(arm_rows[k][y]) for k in ks if k in feas])
            sec[f"{x}_vs_{y}|repair"] = p16e.paired([_ok_rep(arm_rows[k][x]) for k in ks if k in inf], [_ok_rep(arm_rows[k][y]) for k in ks if k in inf])
    h = p16e.holm({k: v["p"] for k, v in sec.items() if k.endswith("|strict_top1")})
    for k in sec:
        sec[k]["p_holm_top1_family"] = h.get(k)
    fam = {}
    for k, v in R.items():
        fam.setdefault(v["family"], []).append(k)
    by_family = {f: {x: float(np.mean([ok(k, x) for k in ks if x in arm_rows[k]])) for x in arms} | {"n": len(ks)} for f, ks in fam.items()}
    return {"decided_roots": len(R), "undecided_originals": len(rows) - len(R), "feasible": len(feas), "infeasible": len(inf), "per_arm": per,
            "primary": {"pair": list(B_PRIMARY), "strict_top1": prim}, "secondary": sec, "by_family": by_family}


def d_analysis(rows, unions=None, primary=("Dp17", "geometry")) -> dict:
    """rows: {root: {'family', 'guides': {guide: d_root output}}} -> p16_eval.d_analysis + effort to the first verified plan + by family."""
    import p16_eval as p16e
    out = p16e.d_analysis(rows, primary=primary, unions=unions)
    guides = sorted({g for v in rows.values() for g in v["guides"]})
    ks = [k for k, v in rows.items() if all(g in v["guides"] for g in guides)]
    eff = {}
    for g in guides:
        first = [(rows[k]["guides"][g]["log"].get("anytime") or [{}])[0] for k in ks if rows[k]["guides"][g]["found"]]
        eff[g] = {"nodes_to_first_mean": float(np.mean([x.get("nodes", np.nan) for x in first])) if first else None,
                  "cpu_to_first_mean": float(np.mean([x.get("cpu_s", np.nan) for x in first])) if first else None}
    fam = {}
    for k in ks:
        fam.setdefault(rows[k]["family"], []).append(k)
    ok = lambda k, g: bool(rows[k]["guides"][g]["found"] and rows[k]["guides"][g]["replay"])  # noqa: E731
    out["effort_first_plan"] = eff
    out["by_family"] = {f: {g: sum(ok(k, g) for k in kk) for g in guides} | {"n": len(kk)} for f, kk in fam.items()}
    return out
