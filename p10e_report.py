"""P10b-P10e figures and report tables (recorded data only; P6.7 conventions via p6_viz: motion only from recorded witnesses,
CERTIFIED as static panels with certificate kind, BUDGET / UNKNOWN as NO VERIFIED TRACE, edits HYPOTHETICAL, proposals PROPOSED)."""
from __future__ import annotations

import json
from pathlib import Path

import config as cf
import geometry as ge
import p6_viz as pv
from scene import scene_from_dict
from viz import COLORS, plt

DST = Path("visualizations/p10b")


def _rd(p):
    return json.loads(Path(p).read_text())


def _roles(ax, s, ids):
    inv = {v: k for k, v in ids.items()}
    for o in s.objects:
        if o.id in inv:
            ax.text(o.xy_m[0], o.xy_m[1] + 0.03, inv[o.id], ha="center", fontsize=8, weight="bold", color="#c0392b", zorder=12)


def _status_tag(ax, st, kind=None):
    txt = {"VERIFIED_FEASIBLE": "VERIFIED (recorded witness)", "CERTIFIED_INFEASIBLE": f"CERTIFIED ({kind})",
           "BUDGET_INFEASIBLE": "BUDGET (operational) - NO VERIFIED TRACE", "UNKNOWN": "UNKNOWN - NO VERIFIED TRACE"}.get(st, st)
    pv._tag(ax, txt, pv.COL.get(st, "#999"), size=6)


def p10b0_designs() -> None:
    """Dev-seed H10_3 / H10_4 designs (PROPOSED) + dev H7 / H8 pilot roots and P10a H1 / H3 / H4 roots with actual statuses."""
    import p10_scenes as ps
    import p10b_dataset as d
    import p10b_scenes as pb
    DST.mkdir(parents=True, exist_ok=True)
    cfg = cf.load_config("config.toml")
    robot = ge.make_robot(cfg)
    cx = ps.Ctx(cfg, robot)
    f, ax = plt.subplots(2, 4, figsize=(22, 11))
    for j, fam in enumerate(("H10_3", "H10_4")):
        rec = next(r for a in range(400) for r in [pb.try_root(cx, {"family": fam, "seed": d.DEV_SEED0 + 7000 + j, "index": -1, "wave": 0}, a, set())[0]] if r)
        s, ids, dest = rec["scene"], rec["ids"], rec["dest"]
        main = pb.CATALOGUE[fam][0].split()
        pv._panel(ax[0, j], cfg, robot, s, rec["goal_cell"], f"DEV {fam} (seed {rec['seed']}, attempt {rec['attempt']}): main repair {' -> '.join(main)}")
        _roles(ax[0, j], s, ids)
        pv._arrows(ax[0, j], s, [(ids[t], dest[t][0]) for t in main], COLORS["hypothetical"])
        pv._tag(ax[0, j], "PROPOSED, NOT EXECUTED (development seed; never in the dataset)", COLORS["hypothetical"], size=6)
    dev = _rd("runs/p10b/dev_h7h8/plan.json")
    rec = d.records("runs/p10b/dev_h7h8", ("dev",))
    for j, k in enumerate(("p10b_2026124000", "p10b_2026124003")):
        r = dev["roots"][k]
        s = scene_from_dict(r["scene"])
        tok = {q["token"]: q for q in dev["queries"] if q["root"] == k}
        q = tok["M"]
        x = rec[q["query"]]
        pv._panel(ax[0, 2 + j], cfg, robot, s, r["goal_cell"], f"DEV {r['family']} {k[-4:]}: physical 'M' -> {x['teacher_status'][:9]}; "
                  f"edit A -> {rec[tok['edit:A']['query']]['teacher_status'][:9]}")
        _roles(ax[0, 2 + j], s, r["ids"])
        pv._arrows(ax[0, 2 + j], s, [tuple(a) for a in q["sequence"]], pv.COL[x["teacher_status"]])
        _status_tag(ax[0, 2 + j], x["teacher_status"], (x.get("static_certificate") or {}).get("kind"))
    pa = _rd("runs/p10/p10a/plan.json")
    dec = _rd("runs/p10/p10a/decisions.json")
    for j, (k, want) in enumerate((("p10a_2026102801", "edit:A+B"), ("p10a_2026102803", "B A"), ("p10a_2026102804", "C A"))):
        r = pa["roots"][k]
        s = scene_from_dict(r["scene"])
        import p10_collect as pc
        q = next(q for q in pa["queries"] if q["root"] == k and pc._tok(pa, q) == want)
        x = dec[q["query"]]
        pv._panel(ax[1, j], cfg, robot, s, r["goal_cell"], f"P10a {r['mechanism']} {k[-2:]}: '{want}' -> {x['teacher_status'][:9]}")
        _roles(ax[1, j], s, r["ids"])
        if q["sequence"]:
            pv._arrows(ax[1, j], s, [tuple(a) for a in q["sequence"]], COLORS["valid"])
        _status_tag(ax[1, j], x["teacher_status"])
    ax[1, 3].axis("off")
    ax[1, 3].text(0, 0.95, "Recorded witness trajectories for the P10a roots:\nvisualizations/p10/roots/<root>_evidence.gif\n\n"
                  "Top row: development seeds only (P10b-0).\nH7: edit VERIFIED vs physical relocation CERTIFIED\n(FIRST_MOVER placement screen; scope ASSIGNMENT).\n"
                  "H8: original CERTIFIED by the sector checker;\nbarrier removal VERIFIED (edit and relocation).", fontsize=9, va="top")
    pv.png(f, DST / "P10b0_designs_and_dev_pilot.png", "P10b-0: H10 designs (PROPOSED), dev H7 / H8 pilot statuses, P10a H1 / H3 / H4 VERIFIED repairs")
    cf.write_json(DST / "INDEX_p10b0.json", pv.INDEX)


# ------------------------------------------------------------------ P10b yield (non-blind roots only) and the P10b-1 gate
REQUIRED = {"H1": ["edit:A", "edit:B", "edit:A+B", ""], "H2a": ["edit:A", "edit:B", "edit:A+B", ""], "H2b": ["edit:A", "edit:B", "edit:A+B", ""],
            "H3": ["B A", "A B"], "H4": ["C A", "A", "C"], "H5": ["", "edit:A", "edit:B", "edit:A+B"], "H7": ["edit:A", "M"],
            "H8": ["", "edit:A", "M"], "H10_3": ["C B A", "B C A", "C A B", "A B C", "C B", "B A", "C A"],
            "H10_4": ["C B A E", "E C B A", "C B E A", "B C A E", "C B A", "C B E", "B A E", "C A E"]}
V, C, B = "VERIFIED_FEASIBLE", "CERTIFIED_INFEASIBLE", "BUDGET_INFEASIBLE"


def _y(st):
    return 1 if st == V else 0 if st in (C, B) else None


def root_yield(plan, rec, k) -> dict:
    r = plan["roots"][k]
    t = {q["token"]: rec[q["query"]] for q in plan["queries"] if q["root"] == k and q["query"] in rec}
    s = {x: v["teacher_status"] for x, v in t.items()}
    y = {x: _y(v) for x, v in s.items()}
    fam, proof = r["family"], lambda *xs: all(s.get(x) in (V, C) for x in xs)  # noqa: E731
    req = REQUIRED[fam]
    k4 = lambda: y["edit:A+B"] - y["edit:A"] - y["edit:B"] + y[""] if all(y.get(x) is not None for x in req) else None  # noqa: E731
    real = {"H1": lambda: k4() == 1, "H2a": lambda: k4() == -1, "H2b": lambda: k4() == 0,
            "H3": lambda: {y.get("B A"), y.get("A B")} == {0, 1}, "H4": lambda: y.get("C A") == 1 and y.get("A") is not None and y.get("C") is not None,
            "H5": lambda: y.get("") == 1 and 0 in (y.get("edit:A"), y.get("edit:B"), y.get("edit:A+B")),
            "H7": lambda: y.get("edit:A") == 1 and y.get("M") == 0, "H8": lambda: y.get("") == 0 and 1 in (y.get("edit:A"), y.get("M")),
            "H10_3": lambda: y.get("C B A") == 1, "H10_4": lambda: 1 in (y.get("C B A E"), y.get("E C B A"), y.get("C B E A"))}[fam]()
    seqs = [q for q in plan["queries"] if q["root"] == k and q["kind"] == "ORDERED_TEACHER" and q["query"] in rec]
    wl = sorted(len(q["sequence"]) for q in seqs if s.get(q["token"]) == V)
    mini = "NO_WITNESS"
    if wl:
        short = [q for q in seqs if len(q["sequence"]) < wl[0]]
        mini = "UNKNOWN" if any(_y(s[q["token"]]) is None for q in short) or any(s[q["token"]] == V for q in short) else \
            "SOUND" if all(s[q["token"]] == C for q in short) else "OPERATIONAL"
    return {"root": k, "family": fam, "split": r["split"], "realized": bool(real), "proof_grounded_required": proof(*req),
            "required_decided": sum(y.get(x) is not None for x in req), "required": len(req), "witness_lengths": wl,
            "min_verified_length": wl[0] if wl else None, "max_verified_length": wl[-1] if wl else None,
            "minimality_relative_to_catalogue": mini, "status": s}


def p10b1_gate(batch="runs/p10b/batch1") -> dict:
    import numpy as np
    import p10b_dataset as d
    plan = _rd(f"{batch}/plan.json")
    rec = d.records(batch)
    ys = [root_yield(plan, rec, k) for k in plan["roots"] if plan["roots"][k]["split"] != "blind"]
    dl = d.d_labels(plan, rec)
    pools = [x for x in dl.values() if x["n"] > 0]
    complete = [x for x in pools if x["mask"] is not None]
    att = [a for l in open(f"{batch}/teacher_calls.jsonl") for a in [json.loads(l)] if a["seeds"]]
    qc = [a["unit_cpu_s"] for a in att]
    dec = sum(x["required_decided"] for x in ys) / max(1, sum(x["required"] for x in ys))
    w3 = [x["root"] for x in ys if x["family"] == "H10_3" and x["realized"]]
    w4 = [x["root"] for x in ys if x["family"] == "H10_4" and x["realized"]]
    checks = {"required_contrasts_decided_ge_70pct": dec >= 0.70,
              "proof_grounded_H1": any(x["realized"] and x["proof_grounded_required"] for x in ys if x["family"] == "H1"),
              "proof_grounded_H3": any(x["realized"] and x["proof_grounded_required"] for x in ys if x["family"] == "H3"),
              "witnessed_3move_ge_2": len(w3) >= 2, "witnessed_4move_ge_2": len(w4) >= 2,
              "complete_D_masks_ge_50pct": len(complete) >= 0.5 * max(1, len(pools)),
              "independent_mask_check": all(x.get("independent_check", True) for x in complete),
              "caps": all(d.spent(c)[0] <= d.CAPS[c] for c in d.CAPS)}
    h10_blocked = not (checks["witnessed_3move_ge_2"] and checks["witnessed_4move_ge_2"])
    core = [c for c in checks if not c.startswith("witnessed")]
    out = {"stage": "P10b-1", "plan_hash": plan["plan_hash"], "roots": len(plan["roots"]), "unavailable": plan["unavailable"],
           "required_decided_fraction": dec, "realized_by_family": {f: [x["realized"] for x in ys if x["family"] == f] for f in REQUIRED},
           "witnessed_3move": w3, "witnessed_4move": w4, "d_mask_types": {t: sum(x["type"] == t for x in pools) for t in sorted({x["type"] for x in pools})},
           "d_complete": len(complete), "d_pools": len(pools), "d_proof_grounded": sum(x["provenance"] == "proof_grounded" for x in complete),
           "query_cpu": {"teacher_queries": len(qc), "median": float(np.median(qc)) if qc else 0.0, "p95": float(np.percentile(qc, 95)) if qc else 0.0,
                         "max": max(qc) if qc else 0.0}, "status_counts": {s: sum(r["teacher_status"] == s for r in rec.values()) for s in {r["teacher_status"] for r in rec.values()}},
           "checks": checks, "H10": "BLOCKED" if h10_blocked else "GO", "decision": "GO" if all(checks[c] for c in core) else "STOP",
           "roots_detail": ys, "d_labels": {k: {x: v[x] for x in ("type", "mask", "necessary", "sets", "provenance", "roles", "status") if x in v}
                                            for k, v in dl.items()}}
    cf.write_json(Path("runs/p10b/P10B1_GATE.json"), out)
    return out


# ------------------------------------------------------------------ blind evaluation (after runs/p10b/UNSEALED; frozen predictions read-only)
ORDER_PAIRS = {"H3": [("B A", "A B")], "H10_3": [("C B A", x) for x in ("B C A", "C A B", "A B C")],
               "H10_4": [(a, "B C A E") for a in ("C B A E", "E C B A", "C B E A")]}


def _sign_p(d):
    """Exact two-sided sign test on nonzero paired differences."""
    from scipy.stats import binomtest
    n, k = sum(x != 0 for x in d), sum(x > 0 for x in d)
    return float(binomtest(k, n).pvalue) if n else 1.0


def _contrast(per, a, b, better="higher"):
    import p10_eval as pe
    ks = sorted(set(per.get(a, {})) & set(per.get(b, {})))
    d = [per[a][k] - per[b][k] for k in ks]
    if not d:
        return {"roots": 0, "status": "NO_DECIDED_ROOTS"}
    return {"roots": len(d), "mean": float(sum(d) / len(d)), "ci95": pe.boot(d), "sign_p": _sign_p(d), "better": better,
            "a_better_roots": sum((x > 0) if better == "higher" else (x < 0) for x in d), "b_better_roots": sum((x < 0) if better == "higher" else (x > 0) for x in d),
            "status": "UNDERPOWERED (< 5 roots)" if len(d) < 5 else "OK"}


def _arm_mean(snap, split, regime, fn):
    """{arm: {root: seed-mean of fn(arm-run-entry, root)}} over runs of one regime (None values skipped)."""
    out = {}
    for n, a in snap["arms"].items():
        if a["regime"] != regime:
            continue
        for k, x in a["roots"].get(split, {}).items():
            v = fn(x, k)
            if v is not None:
                out.setdefault(a["arm"], {}).setdefault(k, []).append(v)
    return {arm: {k: sum(v) / len(v) for k, v in d.items()} for arm, d in out.items()}


def blind_eval(split="blind", out="runs/p10d/BLIND_EVAL.json") -> dict:
    import numpy as np
    import p10_eval as pe
    import p10b_dataset as d
    import p10c_train_eval as pc
    import d_blockers as db
    snap = _rd("runs/p10d/predictions.json")
    P, rec, dl = {}, {}, {}
    for b in pc.batches():
        plan = _rd(b / "plan.json")
        P |= plan["roots"]
        r = d.records(b, ("train", "validation") + (("blind",) if split == "blind" else ()))
        rec |= r
        dl |= d.d_labels(plan, r)
    blind = [k for k, r in P.items() if r["split"] == split]
    tok = {k: {c["token"]: c["query"] for c in P[k]["items"]} for k in blind}
    y = lambda q: rec[q]["binary_training_label"] if q in rec else None  # noqa: E731
    pg = lambda *qs: all(rec[q]["teacher_status"] in (V, C) for q in qs)  # noqa: E731
    res = {"blind_roots": len(blind), "status_counts": {s: sum(rec[q["query"]]["teacher_status"] == s for k in blind for q in P[k]["items"] if q["query"] in rec)
                                                        for s in (V, C, B, "UNKNOWN", "NOT_RUN")}}
    # P2 H1 kappa
    def kap(x, k):
        if P[k]["family"] != "H1":
            return None
        t = tok[k]
        qs = [t["edit:A+B"], t["edit:A"], t["edit:B"], t[""]]
        if any(y(q) is None for q in qs) or not pg(*qs):
            return None
        m = x["marginals"]
        if any(q not in m for q in qs):
            return None
        return -abs((m[qs[0]] - m[qs[1]] - m[qs[2]] + m[qs[3]]) - (y(qs[0]) - y(qs[1]) - y(qs[2]) + y(qs[3])))
    # P3 order
    def order(x, k):
        sc = []
        for a, b_ in ORDER_PAIRS.get(P[k]["family"], []):
            qa, qb = tok[k].get(a), tok[k].get(b_)
            if qa and qb and {y(qa), y(qb)} == {0, 1} and pg(qa, qb) and qa in x["marginals"] and qb in x["marginals"]:
                good, bad = (qa, qb) if y(qa) else (qb, qa)
                sc.append(float(x["marginals"][good] > x["marginals"][bad]))
        return sum(sc) / len(sc) if sc else None
    # P4 omission necessity
    def omis(x, k):
        sc = []
        for c in P[k]["items"]:
            if c["kind"] != "ORDERED_TEACHER" or len(c["sequence"]) < 2 or y(c["query"]) != 1:
                continue
            for t in range(len(c["sequence"])):
                o = f"seq:{k}:" + (".".join(f"{a}>{b_}" for i, (a, b_) in enumerate(c["sequence"]) if i != t) or "empty")
                if y(o) is not None and o in x["marginals"]:
                    sc.append(float((x["marginals"][o] < 0.5) == (y(o) == 0)))
        return sum(sc) / len(sc) if sc else None
    ep = {"P2_H1": _arm_mean(snap, split, "full", kap), "P3_ORDER": _arm_mean(snap, split, "full", order),
          "P4_OMISSION": _arm_mean(snap, split, "full", omis)}
    res["P2_H1"] = {"primary_K-B_vs_A": _contrast(ep["P2_H1"], "K-B", "A"), "K-C_vs_A": _contrast(ep["P2_H1"], "K-C", "A"),
                    "K-B_vs_SF": _contrast(ep["P2_H1"], "K-B", "SF"), "per_arm_mean_neg_abs_err": {a: float(np.mean(list(v.values()))) for a, v in ep["P2_H1"].items()}}
    res["P3_ORDER"] = {"primary_K-C_vs_K-B": _contrast(ep["P3_ORDER"], "K-C", "K-B"), "K-B_vs_A": _contrast(ep["P3_ORDER"], "K-B", "A"),
                       "K-B_vs_SF": _contrast(ep["P3_ORDER"], "K-B", "SF"), "per_arm_accuracy": {a: float(np.mean(list(v.values()))) for a, v in ep["P3_ORDER"].items()}}
    res["P4_OMISSION"] = {"primary_K-B_vs_SF": _contrast(ep["P4_OMISSION"], "K-B", "SF"), "K-B_vs_A": _contrast(ep["P4_OMISSION"], "K-B", "A"),
                          "per_arm_accuracy": {a: float(np.mean(list(v.values()))) for a, v in ep["P4_OMISSION"].items()}}
    # common per-event metrics and paired per-root NLL (full regime), by provenance
    def nll_root(x, k, src=None):
        v = [(x["marginals"][q], y(q)) for q in (c["query"] for c in P[k]["items"]) if y(q) is not None and q in x["marginals"]
             and (src is None or (rec[q]["label_source"] == "PLANNER_BUDGET") == (src == "operational"))]
        return float(np.mean([-np.log(min(max(p if t else 1 - p, 1e-9), 1)) for p, t in v])) if v else None
    for regime in ("full", "short"):
        per = _arm_mean(snap, split, regime, nll_root)
        res[f"root_nll_{regime}"] = {"per_arm": {a: float(np.mean(list(v.values()))) for a, v in per.items()},
                                     "contrasts": {f"{a}-{b_}": _contrast(per, a, b_, "lower") for a, b_ in (("K-B", "A"), ("K-B", "SF"), ("K-C", "K-B"), ("A", "SF"))}}
    rows = []
    for n, a in snap["arms"].items():
        for k in blind:
            for q, p in a["roots"][split].get(k, {}).get("marginals", {}).items():
                if y(q) is not None:
                    rows.append({"arm": a["arm"], "regime": a["regime"], "p": p, "y": y(q), "root": k, "source": rec[q]["label_source"]})
    res["common_metrics"] = {f"{arm}|{rg}": {s: pe.metrics([x for x in rows if x["arm"] == arm and x["regime"] == rg and
                                                            (s == "all" or (x["source"] == "PLANNER_BUDGET") == (s == "operational"))])
                                             for s in ("all", "proof_grounded", "operational")} for arm, rg in sorted({(x["arm"], x["regime"]) for x in rows})}
    # length: per-root NLL on 3-/4-move H10 roots, full vs short, and the order / omission endpoints of the short regime
    h10 = lambda fn: (lambda x, k: fn(x, k) if P[k]["family"].startswith("H10") else None)  # noqa: E731
    res["length_extrapolation"] = {rg: {"nll": {a: float(np.mean(list(v.values()))) for a, v in _arm_mean(snap, split, rg, h10(nll_root)).items()},
                                        "order": {a: float(np.mean(list(v.values()))) for a, v in _arm_mean(snap, split, rg, h10(order)).items()},
                                        "omission": {a: float(np.mean(list(v.values()))) for a, v in _arm_mean(snap, split, rg, h10(omis)).items()}}
                                   for rg in ("full", "short")}
    # H9 appearance invariance (blind originals vs recoloured variants; same query ids)
    inv = {}
    for n, a in snap["arms"].items():
        if a["regime"] != "full":
            continue
        dv = [abs(p - a["roots"][split][k]["marginals"].get(q, p)) for k, x in a["roots"].get("h9", {}).items() if k in a["roots"][split]
              for q, p in x["marginals"].items()]
        inv.setdefault(a["arm"], []).extend(dv)
    res["H9_mean_abs_change"] = {a: float(np.mean(v)) for a, v in inv.items() if v}
    # ablation matrix (full regime): endpoints per arm
    res["ablation_matrix"] = {a: {"root_nll": res["root_nll_full"]["per_arm"].get(a), "H1": res["P2_H1"]["per_arm_mean_neg_abs_err"].get(a),
                                  "order": res["P3_ORDER"]["per_arm_accuracy"].get(a), "omission": res["P4_OMISSION"]["per_arm_accuracy"].get(a)}
                              for a in sorted({x["arm"] for x in snap["arms"].values()})}
    res["D"] = d_eval(snap, P, dl, rec, blind, tok, split)
    res["split"] = split
    cf.write_json(Path(out), res)
    return res


def d_eval(snap, P, dl, rec, blind, tok, split="blind") -> dict:
    import numpy as np
    import p10_eval as pe
    import p10d_execute as px
    out, per = {}, {}
    gt = {k: dl[k] for k in blind if dl[k]["mask"] is not None and dl[k]["n"] > 0}
    out["masks"] = {"blind_roots_with_pool": sum(dl[k]["n"] > 0 for k in blind), "complete": len(gt),
                    "types": {t: sum(dl[k]["type"] == t for k in blind) for t in sorted({dl[k]["type"] for k in blind})},
                    "proof_grounded": sum(x["provenance"] == "proof_grounded" for x in gt.values()),
                    "by_true_blockers": {n: sum(sum(x["mask"]) == n for x in gt.values()) for n in range(5)}}
    for arm in ("D", "D-pairless"):
        lam, thr = snap["baselines"][f"{arm}_lambda_B"], snap["baselines"][f"{arm}_threshold"]
        runs = [x for x in snap["d"].values() if x["arm"] == arm and x["lambda_B"] == lam]
        for k, g in gt.items():
            f1s, ex, jac, card = [], [], [], []
            for x in runs:
                p = x["roots"][split][k]
                pred = [int(p["p_feasible"] < 0.5 and v >= thr) for v in p["marg"]]
                f1s.append(px.f1_score(g["mask"], pred))
                ex.append(float(pred == g["mask"]))
                u = sum(a or b for a, b in zip(pred, g["mask"]))
                jac.append(sum(a and b for a, b in zip(pred, g["mask"])) / u if u else 1.0)
                card.append(abs(sum(pred) - sum(g["mask"])))
            per.setdefault(arm, {})[k] = {"f1": float(np.mean(f1s)), "exact": float(np.mean(ex)), "jaccard": float(np.mean(jac)), "card_err": float(np.mean(card))}
        fz = [(np.mean([x["roots"][split][k]["p_feasible"] for x in runs]), dl[k]["y0"]) for k in blind if dl[k]["y0"] is not None and k in runs[0]["roots"][split]] if runs else []
        out[f"{arm}_feasibility"] = pe.metrics([{"p": p, "y": t, "root": i} for i, (p, t) in enumerate(fz)])
    heur = snap["baselines"]["heuristic"][split]
    per["heuristic"] = {k: {"f1": px.f1_score(g["mask"], heur[k]), "exact": float(heur[k] == g["mask"])} for k, g in gt.items()}
    for name in per:
        out[name] = {m: float(np.mean([v[m] for v in per[name].values()])) for m in ("f1", "exact")} | {"roots": len(per[name])}
        out[name] |= {"by_true_blockers": {n: float(np.mean([per[name][k]["f1"] for k in gt if sum(gt[k]["mask"]) == n]))
                                           for n in range(5) if any(sum(gt[k]["mask"]) == n for k in gt)}}
    f1 = {a: {k: v["f1"] for k, v in d_.items()} for a, d_ in per.items()}
    out["primary_D_vs_pairless_F1"] = _contrast(f1, "D", "D-pairless")
    out["D_vs_heuristic_F1"] = _contrast(f1, "D", "heuristic")
    # feasibility: D vs A/B/C/SF z0 (empty-repair marginal) on the same blind roots (seed mean, full regime)
    z0 = {}
    for x in snap["arms"].values():
        if x["regime"] == "full" and x["arm"] in ("A", "SF", "K-B", "K-C"):
            for k in blind:
                p = x["roots"][split].get(k, {}).get("marginals", {}).get(f"seq:{k}:empty")
                if p is not None and dl[k]["y0"] is not None:
                    z0.setdefault(x["arm"], {}).setdefault(k, []).append(p)
    out["z0_feasibility"] = {a: pe.metrics([{"p": float(np.mean(v)), "y": dl[k]["y0"], "root": k} for k, v in d_.items()]) for a, d_ in z0.items()}
    # faithful B / C counterfactual attribution: pool = the two edit roles and parking subsets == zS[A], zS[B], zS[A+B]
    sup = [k for k, g in gt.items() if dl[k]["n"] == 2 and all(tok[k].get(t) and any(c["query"] == tok[k][t] and c.get("d_subset") for c in P[k]["items"])
                                                               for t in ("edit:A", "edit:B", "edit:A+B"))]
    att = {}
    for x in snap["arms"].values():
        if x["regime"] != "full" or x["arm"] not in ("K-B", "K-C", "A", "SF"):
            continue
        for k in sup:
            m = x["roots"][split][k]["marginals"]
            roles = dl[k]["roles"]
            st = {frozenset(): m.get(f"seq:{k}:empty")}
            for t in ("edit:A", "edit:B", "edit:A+B"):
                it = next(c for c in P[k]["items"] if c["query"] == tok[k][t])
                st[frozenset(roles.index(r) for r in it["d_subset"])] = m.get(tok[k][t])
            if None in st.values():
                continue
            g = __import__("d_blockers").minimal_sets(2, {s: (V if p >= 0.5 else C) for s, p in st.items()})
            pred = g["mask"] if g["mask"] is not None else [0, 0]
            att.setdefault(x["arm"], []).append(__import__("p10d_execute").f1_score(gt[k]["mask"], pred))
    out["BC_counterfactual_attribution"] = {"supported_roots": len(sup), "unsupported_roots": len(gt) - len(sup),
                                            "f1_seed_pooled": {a: float(np.mean(v)) for a, v in att.items()}}
    return out


def batch_figures(batch="runs/p10b/batch1", tag="P10b1") -> None:
    """Atlas (anchor status), recorded 3- / 4-move witness GIFs (H10), D parking-subset panels (non-blind roots only)."""
    import p10b_dataset as d
    import effects as ef
    DST.mkdir(parents=True, exist_ok=True)
    cfg = cf.load_config("config.toml")
    robot = ge.make_robot(cfg)
    plan, rec = _rd(f"{batch}/plan.json"), d.records(batch)
    ks = [k for k, r in plan["roots"].items() if r["split"] != "blind"]
    n = (len(ks) + 7) // 8
    f, ax = plt.subplots(n, 8, figsize=(32, 4.2 * n), squeeze=False)
    for a, k in zip(ax.flat, ks):
        r = plan["roots"][k]
        s = scene_from_dict(r["scene"])
        anc = next(q for q in plan["queries"] if q["root"] == k and q["anchor"])
        st = rec[anc["query"]]["teacher_status"]
        pv._panel(a, cfg, robot, s, r["goal_cell"], f"{k[-3:]} {r['family']} {r['split'][:5]} {r['stratum']}")
        _roles(a, s, r["ids"])
        if anc["sequence"]:
            pv._arrows(a, s, [tuple(x) for x in anc["sequence"]], pv.COL.get(st, "#999"))
        _status_tag(a, st, (rec[anc["query"]].get("static_certificate") or {}).get("kind"))
    for a in ax.flat[len(ks):]:
        a.axis("off")
    pv.png(f, DST / f"{tag}_atlas.png", f"{tag}: every non-blind root at q0 with its anchor query and adjudicated status")
    frames = []
    for k in ks:
        r = plan["roots"][k]
        if not r["family"].startswith("H10"):
            continue
        s = scene_from_dict(r["scene"])
        for q in [q for q in plan["queries"] if q["root"] == k and len(q["sequence"]) >= 3 and rec[q["query"]]["teacher_status"] == V][:1]:
            w = pv.witness(Path(batch), rec[q["query"]])
            for qq, g, pos, mv in pv.trace_frames(robot, s, [tuple(a) for a in q["sequence"]], w[1], w[2], n_move=10, n_target=12):
                fg, a = plt.subplots(figsize=(5, 5))
                pv._panel(a, cfg, robot, s, r["goal_cell"], f"{k[-3:]} {r['family']}: '{q['token']}' ({len(q['sequence'])} moves)\nRECORDED witness", q=qq, gap=g, pos=pos, held=mv)
                pv._tag(a, "VERIFIED - recorded trajectory", COLORS["valid"])
                frames.append(pv._rgb(fg))
    if frames:
        pv.gif(DST / f"{tag}_long_repairs.gif", frames, f"{tag}: recorded 3- / 4-relocation witnesses (H10)")
    dl = d.d_labels(plan, rec)
    show = [k for k in ks if dl[k]["n"] >= 2 and dl[k]["type"] == "MINIMAL_SETS"][:4]
    if show:
        f, ax = plt.subplots(len(show), 1, figsize=(16, 3.2 * len(show)), squeeze=False)
        for a, k in zip(ax[:, 0], show):
            x, r = dl[k], plan["roots"][k]
            s = scene_from_dict(r["scene"])
            subs = sorted(x["status"], key=lambda t: (t != "(original)", len(t), t))
            a.axis("off")
            for i, t in enumerate(subs):
                ia = a.inset_axes([i / len(subs), 0, 0.95 / len(subs), 0.85])
                ed = {} if t == "(original)" else {o: r["parking"][o] for o in r["parking"] if {v: kk for kk, v in r["ids"].items()}[o] in t.split("+")}
                se = ef.pose_substitution(robot, cfg, s, {"target_id": "t0"}, ed)["scene"] if ed else s
                pv._panel(ia, cfg, robot, se, r["goal_cell"], f"park {t}", )
                ia.set_xticks([]); ia.set_yticks([]); ia.set_xlabel(""); ia.set_ylabel("")
                pv._tag(ia, x["status"][t][:9], pv.COL.get(x["status"][t], "#999"), size=5)
            a.set_title(f"{k} {r['family']}: D pool {x['roles']} -> minimal sets {[[x['roles'][i] for i in m] for m in x['sets']]}, mask {x['mask']} "
                        f"({x['provenance']}); HYPOTHETICAL parking edits (labels only, never executed)", fontsize=9)
        pv.png(f, DST / f"{tag}_D_masks.png", f"{tag}: D blocker ground truth from all parking subsets (target-only edits)")
    cf.write_json(DST / f"INDEX_{tag}.json", pv.INDEX)
