#!/usr/bin/env python3
"""P4b isolated oracle-assignment diagnostic (run only AFTER the main predictions are sealed; outputs never reach the main planner).
Input per root: ONE private verified unordered assignment (the generator witness's set; no witness order, K label, trajectory or teacher
result).  Frozen 3D models rank every permutation: direct p11 at S0 (top-1 -> continuous), chunk score H over the declared two-group
splits (top-1 order + partition -> chunked), plus a seeded uniform random order (continuous).  Mode control (preregistered): the H-picked
order executed continuously.  Witness-boundary control: the private witness order with the canonical split (2+2 for K4, 2+3 for K5).
    python oracle.py plans PUBLIC PRIVATE_INDEX OUT.json
    python oracle.py jobs  OUT.json PUBLIC -> oracle jobs (priority: direct, chunk, random, mode-control, witness-boundary)"""
from __future__ import annotations

import hashlib, itertools, json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import compose as CP  # noqa: E402
import scene as SC  # noqa: E402

GV = "/home/projects/long-horizon/naren_workspace/k45"


def plans(public, index, out):
    from models import Frozen
    fz = Frozen()
    pub = {r["root_id"]: r for r in map(json.loads, open(public))}
    res = {}
    for e in map(json.loads, open(index)):
        rid = e["root_id"]; row = pub[rid]; ids = row["inputs"]["ids"]
        w = json.loads(Path(e["abs_path"]).read_text())["k45"]["witness"]["order"]
        A = sorted([ids.index(o), r * 6 + c] for o, (r, c) in w)                      # unordered: the witness order is NOT given
        perms = [[list(x) for x in p] for p in itertools.permutations(A)]
        fz.reset()
        sc = fz.score(row, perms)
        di = max(range(len(perms)), key=lambda i: (sc[i]["p11"], [-v for a in perms[i] for v in a]))
        yg = fz.y_global(row, [A])[0]
        hb = CP.best_composition(fz, row, [tuple(a) for a in A], yg)
        rnd = perms[int(hashlib.sha256(("K45_ORACLE_RANDOM|" + rid).encode()).hexdigest(), 16) % len(perms)]
        res[rid] = {"m": len(A), "direct": {"order": perms[di], "p11": sc[di]["p11"]}, "chunk": {"order": hb["seq"], "partition": hb["partition"], "H": hb["p"]},
                    "random": {"order": rnd}, "witness_order": [[ids.index(o), r * 6 + c] for o, (r, c) in w],
                    "direct_rank_of_chunk_order": sorted(range(len(perms)), key=lambda i: -sc[i]["p11"]).index(perms.index(hb["seq"])) + 1}
    Path(out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: {"m": v["m"], "same_order": v["direct"]["order"] == v["chunk"]["order"]} for k, v in res.items()}))


def jobs(plan_file, public):
    P = json.loads(Path(plan_file).read_text())
    ids = {r["root_id"]: r["inputs"]["ids"] for r in map(json.loads, open(public))}
    tiers = {"direct": [], "chunk": [], "random": [], "mode_control": [], "witness_boundary": []}
    for rid in sorted(P):
        p, I = P[rid], ids[rid]
        o = lambda s: [[I[int(a)], [int(d) // 6, int(d) % 6]] for a, d in s]  # noqa: E731
        m = p["m"]
        add = lambda t, seq, bounds: tiers[t].append({"key": f"oracle_{t}|{rid}|{json.dumps(o(seq))}|{json.dumps(bounds)}", "root_id": rid,  # noqa: E731
                                                       "mode": "continuous" if bounds == [m] else "chunked", "path": f"{GV}/cohort/roots/{rid}.json",
                                                       "order": o(seq), "bounds": bounds, "replay": True, "y_cells": "ENDPOINT"})
        add("direct", p["direct"]["order"], [m])
        add("chunk", p["chunk"]["order"], list(itertools.accumulate(p["chunk"]["partition"])))
        add("random", p["random"]["order"], [m])
        add("mode_control", p["chunk"]["order"], [m])
        add("witness_boundary", p["witness_order"], [2, m])
    return tiers


if __name__ == "__main__":
    if sys.argv[1] == "plans":
        plans(*sys.argv[2:5])
    elif sys.argv[1] == "jobs":
        print(json.dumps({k: len(v) for k, v in jobs(sys.argv[2], sys.argv[3]).items()}))
