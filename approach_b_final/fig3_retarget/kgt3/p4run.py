#!/usr/bin/env python3
"""KGT3 P4 model-only planner accounting on the exposed DEV panels (NO physical verification; both domains stopped at P2).
Per root and arm: decision, plan, partition, mode (EXACT / BOUNDED), counts, wall; evaluator-only witness-assignment coverage
(in the initial D4 pool; retained / optimized by GA; selected).  The planners never see the witness.
    $PYG p4run.py DOM SPEC OUT.jsonl"""
from __future__ import annotations

import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "r3"), str(HERE.parent / "r24"), str(HERE.parent.parent)]
import evaluate  # noqa: E402,F401  (pin r3/evaluate)
import p3 as P3  # noqa: E402
import planners as PL  # noqa: E402
import rank as RK  # noqa: E402
import learn as LN  # noqa: E402

ARMS = ["REC-ORDERED", "REC-REORDER", "FLAT-INSERT", "GA", "GA-YONLY"]


def main(dom, spec, outp):
    fz, net = LN.load(dom, spec)
    fz0, base = LN.load(dom, "F0")
    fz.net = net
    done = {json.loads(l)["root_id"] for l in open(outp)} if Path(outp).exists() else set()
    with open(outp, "a") as f:
        for rid, row, A, W, meta in P3.panel(dom):
            if rid in done:
                continue
            r0 = {"root_id": row["root_id"], "domain": row["domain"], "inputs": row["inputs"]}
            fz0.reset(); fz0.caps = {}
            b0 = RK.b0(fz0, r0, PL.CFG["rule"])                    # production floor: production scorer + rules
            floor = {"seq": b0["seq"]} if b0["decision"] == "REPAIR" else None
            Wset = sorted(tuple(map(int, a)) for a in W)
            rec = {"root_id": rid, "K": meta["K"], "N": meta["N"], "spec": spec, "B0": {"decision": b0["decision"], "seq": b0["seq"]}, "arms": {}}
            for arm in ARMS:
                p = PL.plan(fz, r0, arm, floor)
                info = p["info"] or {}
                D4 = {int(o): v for o, v in (info.get("D4") or {}).items()}
                cov = {}
                if D4:
                    cov["witness_in_D4"] = all(d in D4.get(o, []) for o, d in Wset)
                    k = len(Wset)
                    if info.get("mode") == "EXACT":
                        cov["witness_optimized"] = cov["witness_in_D4"] and k <= p["H"]
                    else:
                        cov["witness_optimized"] = [list(a) for a in Wset] in [sorted(x) for x in info.get("retained", {}).get(k, [])]
                cov["selected_is_witness_set"] = bool(p["seq"]) and sorted(tuple(a) for a in p["seq"]) == Wset
                cov["selected_is_witness_order"] = bool(p["seq"]) and [tuple(a) for a in p["seq"]] == [tuple(map(int, a)) for a in W]
                tree = p.get("tree") or {}
                rec["arms"][p["arm"] if arm != "GA" else "GA"] = {"mode": p["arm"], "decision": p["decision"], "seq": p["seq"], "partition": p["partition"], "E": p["E"],
                    "kind": p["kind"], "long": p["long"], "multi_chunk": p["multi_chunk"], "wall_s": p["wall_s"], "stop": p["stop"], "n_candidates": p["n_candidates"],
                    "scores": info.get("scores"), "per_size": info.get("per_size"), "pool": info.get("pool"), "rec_counters": info.get("counters"),
                    "fz_counters": p["counters"], "coverage": cov, "by_size": info.get("by_size"), "exhausted": info.get("exhausted"),
                    "est_distinct_x": info.get("est_distinct_x"), "est_theoretical_dp_lookups": info.get("est_theoretical_dp_lookups"),
                    "assign_upper_bound": info.get("assign_upper_bound"), "n_chunks": len(p["partition"] or [])}
                print(rid, arm, p["arm"], p["decision"], p["partition"], p["wall_s"], cov, flush=True)
            f.write(json.dumps(rec, default=str) + "\n"); f.flush()


if __name__ == "__main__":
    main(*sys.argv[1:4])
