#!/usr/bin/env python3
"""R2.3 controlled search attribution (planner = PUBLIC rows + frozen bundle only; evaluator joins witnesses / labels afterwards).
Arms (identical CFG ceilings, caches reset per root x arm, realized counters logged):
  B0          released EXACT4 K<=3 (unchanged)
  R-FIG3      R1 reference (admit = beats_empty on temporary pY)
  R-FIG3-ALL  admit = all (no admission rule)                                    [ablation, R2.1: admission discards 21 % of 3D enablers]
  R-FIG3-RP   R-FIG3 + RECOMPUTE_PARENT: after nested insertion, the variant score uses the temporary no-op pY of the parent recomputed on the
              ACTUAL post-insertion pre-parent scene (counted readout) instead of the pre-recursion group pY   [declared ablation]
  R-GATED     legacy B4 gates;  F-FLAT  no retargeting;  R-TOPO  R-FIG3 + SEED-edge relaxation
Funnel (logged per root x arm, model side): every proposal set produced (union of (object, cell)), every ranked pool candidate, final.
    python search.py plan DOM PUBLIC.jsonl OUT.jsonl [ARMS]"""
from __future__ import annotations

import json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent)]
import rank as RK  # noqa: E402
import recursive as RC  # noqa: E402
import views as V  # noqa: E402
from models import Frozen, sync  # noqa: E402

ARMS = ["B0", "R-FIG3", "R-FIG3-ALL", "R-FIG3-RP", "R-GATED", "F-FLAT", "R-TOPO"]
_PLACE = RC.place


def place_rp(ctx, P, E, a, pending, depth, ancestors, node):
    """R-FIG3-RP: identical to RC.place except that non-empty variants are re-scored with the parent's temporary no-op pY on the actual
    post-insertion scene (counted temporary readout); the R1 module itself is not modified."""
    out = _PLACE(ctx, P, E, a, pending, depth, ancestors, node)
    res = []
    for i, (Pv, Ev, s) in enumerate(out):
        if i == 0 or len(Pv) == len(P) + 1:
            res.append((Pv, Ev, s)); continue
        T = V.rebase(ctx.row0, Pv[:-1], task=a, reserved=[d for _, d in pending] + [d for _, d in ancestors])
        y = ctx.ytemp(T)
        res.append((Pv, Ev, y if y is not None else s))
        ctx.n["rp_rescored"] = ctx.n.get("rp_rescored", 0) + 1
    return res


def run_arm(fz, row, arm, rule):
    log = {"ranked": []}
    orig = RK.best_partition

    def logged(fz_, row0, seq, ymode="global"):
        r = orig(fz_, row0, seq, ymode)
        log["ranked"].append([list(map(int, a)) for a in seq])
        return r
    RK.best_partition = logged
    try:
        t0 = sync(fz)
        if arm == "B0":
            fz.reset(); fz.caps = {}
            r = RK.b0(fz, row, rule)
            p = {"decision": r["decision"], "seq": r["seq"], "partition": [len(r["seq"])] if r["seq"] else None, "E": None, "counters": dict(fz.c), "cap_stop": None,
                 "pool": None, "tree": None}
        else:
            base = "R-FIG3" if arm in ("R-FIG3-ALL", "R-FIG3-RP") else arm
            cfg = {"admit": "all"} if arm == "R-FIG3-ALL" else {}
            RC.place = place_rp if arm == "R-FIG3-RP" else _PLACE
            p = RC.plan(fz, row, rule, base, cfg)
        lat = round(sync(fz) - t0, 3)
    finally:
        RK.best_partition = orig; RC.place = _PLACE
    props = sorted({(int(o), int(d)) for D in fz._p.values() for o, ds in D.items() for d in ds})
    s0 = fz._p.get((V.skey(row), tuple(V.eligible(row))))
    return {"arm": arm, "decision": p["decision"], "seq": p["seq"], "partition": p["partition"], "E": p.get("E"), "latency_s": lat, "cap_stop": p.get("cap_stop"),
            "pool": p.get("pool"), "counters": p["counters"], "n_ranked": len(log["ranked"]), "ranked": log["ranked"][:400],
            "proposals_union": props, "d4_s0": {str(o): v[:4] for o, v in (s0 or {}).items()}}


def plan(dom, pub, out, arms=None):
    arms = arms.split(",") if arms else ARMS
    fz = Frozen(dom)
    rule = fz.man["config"]["rule"]
    with open(out, "a") as f:
        for l in open(pub):
            row = json.loads(l)
            for arm in arms:
                r = run_arm(fz, row, arm, rule)
                r["root_id"] = row["root_id"]; r["device"] = fz.torch.cuda.get_device_name(0)
                f.write(json.dumps(r) + "\n"); f.flush()
                print(row["root_id"][-20:], arm, r["decision"], r["seq"], r["partition"], r["latency_s"], r["cap_stop"], flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "plan":
        plan(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else None)
