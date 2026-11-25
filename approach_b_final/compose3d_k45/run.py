#!/usr/bin/env python3
"""Planner-only inference for B0-B4 on PUBLIC 3D rows (frozen 3D bundle; no labels, K, witnesses, teacher or evaluator imports).
    python run.py parity PUBLIC_DEV N              B0 == sealed V3.4 EXACT4 parity predictions on N exposed DEV roots (decision, moves)
    python run.py predict PUBLIC OUT.jsonl [ARMS]  one committed plan per root and arm (caches reset per root x arm: uncached timing)"""
from __future__ import annotations

import json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import compose as CP  # noqa: E402
import recursive as RC  # noqa: E402
import scene as SC  # noqa: E402
from models import Frozen, sync  # noqa: E402

ARMS = ["B0", "B1", "B2", "B3", "B4"]


def run_root(fz, row, arms=ARMS):
    rule = fz.man["config"]["rule"]
    out = []
    for arm in arms:
        fz.reset(); fz.caps = {"x_unique": CP.BUDGET["x_unique"], "y_unique": CP.BUDGET["y_unique"]}
        t0 = sync(fz)
        if arm == "B0":
            r = CP.b0(fz, row, rule)
        elif arm in ("B1", "B3"):
            D = fz.proposals(row, SC.eligible(row))
            short = CP.short_candidates(fz, row, D)
            sl, cov = CP.shared_shortlist(fz, row, D)
            r = (CP.b1 if arm == "B1" else CP.b3)(fz, row, rule, D, short, sl)
            r["coverage"] = cov
            r["shortlist"] = {str(k): [[list(map(int, a)) for a in A] for A, _ in v] for k, v in sl.items()}
        elif arm == "B2":
            r = CP.b2(fz, row, rule)
        else:
            r = RC.b4(fz, row, rule)
        r["latency_s"] = round(sync(fz) - t0, 4)
        r["counters"] = dict(fz.c)
        out.append(r)
    return out


def parity(pub, n):
    fz = Frozen()
    ref = {r["root_id"]: r for r in map(json.loads, open(Path.home() / "abf_v34/parity/pred_val_3d_gpu.jsonl"))}
    rows = [json.loads(l) for l in open(pub)]
    rows = [r for r in rows if r["root_id"] in ref]
    picks = []
    for want in ("REPAIR3", "REPAIR2", "REPAIR1", "NOOP", "ABSTAIN"):      # deterministic: first root of each archived decision kind, then fill
        for r in rows:
            e = ref[r["root_id"]]
            k = e["decision"] + (str(len(e["moves"])) if e["decision"] == "REPAIR" else "")
            if k == want and r not in picks:
                picks.append(r); break
    picks = (picks + [r for r in rows if r not in picks])[:int(n)]
    res = []
    for r in picks:
        fz.reset()
        x = CP.b0(fz, r, fz.man["config"]["rule"])
        e = ref[r["root_id"]]
        seq = [[m["object_index"], m["destination_cell"]] for m in e["moves"]]
        D = fz.proposals(r, SC.eligible(r))
        same = x["decision"] == e["decision"] and (x["seq"] or []) == seq
        res.append({"root_id": r["root_id"], "archived": [e["decision"], seq, e["score_p11"]], "b0": [x["decision"], x["seq"], x["score"]],
                    "decision_equal": same, "score_abs_diff": None if x["score"] is None or e["score_p11"] is None else abs(x["score"] - e["score_p11"]),
                    "archived_proposals_equal": {str(o): v for o, v in D.items()} == {k: v for k, v in e["proposals"].items()} if e.get("proposals") else None})
    print(json.dumps(res, indent=1))
    return res


def predict(pub, out, arms=None):
    arms = arms.split(",") if arms else ARMS
    fz = Frozen()
    rows = [json.loads(l) for l in open(pub)]
    done = {json.loads(l)["root_id"] for l in open(out)} if Path(out).exists() else set()
    with open(out, "a") as f:
        for r in rows:
            if r["root_id"] in done:
                continue
            rec = {"root_id": r["root_id"], "plans": run_root(fz, r, arms), "device": fz.torch.cuda.get_device_name(0)}
            f.write(json.dumps(rec) + "\n"); f.flush()
            print(r["root_id"], [(p["arm"], p["decision"], len(p["seq"] or []), p["latency_s"]) for p in rec["plans"]], flush=True)


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "parity":
        parity(sys.argv[2], sys.argv[3])
    elif c == "predict":
        predict(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
