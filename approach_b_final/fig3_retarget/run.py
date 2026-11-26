#!/usr/bin/env python3
"""R1 model-side runner (planner only: PUBLIC rows + frozen bundle; no labels, K, witnesses, teacher or evaluator imports).
    python run.py parity DOM PUBLIC ARCHIVED N OUT.json      B0 (fig3 rank.b0) == sealed V3.4 EXACT4 GPU predictions on N exposed DEV roots
    python run.py demo DOM PUBLIC N OUT.jsonl [ARMS]          R-FIG3 / R-GATED / F-FLAT / R-TOPO model-only plans (trees kept)"""
from __future__ import annotations

import json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import rank as RK  # noqa: E402
import recursive as RC  # noqa: E402
from models import Frozen, sync  # noqa: E402

ARMS = ["R-FIG3", "R-GATED", "F-FLAT", "R-TOPO"]


def _picks(rows, ref, n):
    picks = []
    for want in ("REPAIR3", "REPAIR2", "REPAIR1", "NOOP", "ABSTAIN"):     # first root of each archived decision kind, then fill (deterministic)
        for r in rows:
            e = ref[r["root_id"]]
            if e["decision"] + (str(len(e["moves"])) if e["decision"] == "REPAIR" else "") == want and r not in picks:
                picks.append(r); break
    return (picks + [r for r in rows if r not in picks])[:int(n)]


def parity(dom, pub, archived, n, out):
    fz = Frozen(dom)
    ref = {r["root_id"]: r for r in map(json.loads, open(archived))}
    rows = [r for r in map(json.loads, open(pub)) if r["root_id"] in ref]
    res = []
    for r in _picks(rows, ref, n):
        fz.reset(); fz.caps = {}
        x = RK.b0(fz, r, fz.man["config"]["rule"])
        e = ref[r["root_id"]]
        seq = [[m["object_index"], m["destination_cell"]] for m in e["moves"]]
        sc = None if x["score"] is None or e["score_p11"] is None else abs(x["score"] - e["score_p11"])
        res.append({"root_id": r["root_id"], "archived": [e["decision"], seq, e["score_p11"]], "b0": [x["decision"], x["seq"] or [], x["score"]],
                    "decision_equal": x["decision"] == e["decision"] and (x["seq"] or []) == seq, "score_abs_diff": sc,
                    "proposals_equal": {str(o): v for o, v in x["D4"].items()} == {k: v for k, v in e["proposals"].items() if v} if e.get("proposals") else None})
    rep = {"domain": dom, "n": len(res), "decisions_equal": sum(r["decision_equal"] for r in res), "max_score_abs_diff": max((r["score_abs_diff"] or 0) for r in res),
           "proposals_equal": sum(bool(r["proposals_equal"]) for r in res), "device": fz.torch.cuda.get_device_name(0), "rows": res}
    Path(out).write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k != "rows"}))


def demo(dom, pub, n, out, arms=None):
    arms = arms.split(",") if arms else ARMS
    fz = Frozen(dom)
    rule = fz.man["config"]["rule"]
    rows = [json.loads(l) for l in open(pub)][:int(n)]
    with open(out, "w") as f:
        for r in rows:
            for arm in arms:
                t0 = sync(fz)
                p = RC.plan(fz, r, rule, arm)
                p["latency_s"] = round(sync(fz) - t0, 3)
                p["device"] = fz.torch.cuda.get_device_name(0)
                f.write(json.dumps(p) + "\n"); f.flush()
                print(r["root_id"], arm, p["decision"], p["seq"], p["partition"], p["E"] and round(p["E"], 3), p["n_inserted"], p["pool"], p["cap_stop"],
                      p["counters"]["retargeted_actions"], p["counters"]["nonempty_repairs"], p["counters"]["max_depth"], p["latency_s"], flush=True)


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "parity":
        parity(*sys.argv[2:7])
    elif c == "demo":
        demo(*sys.argv[2:6], *(sys.argv[6:7] or [None]))
