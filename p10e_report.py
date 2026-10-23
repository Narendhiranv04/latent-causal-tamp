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
