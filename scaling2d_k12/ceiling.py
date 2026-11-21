#!/usr/bin/env python3
"""K_lb ceiling audit (G3 feasibility).  K_lb (MINK_STATIC_V2) is monotone non-decreasing in the set of occupied cells (an extra disc only adds
kills; a relaxed repair of the larger scene minus that disc is a relaxed repair of the smaller one).  Hence K_lb with EVERY allowed object
cell occupied (except target and goal) upper-bounds the certifiable minimum K of any scene with that target / goal and object support,
whatever the object count.    python ceiling.py SUPPORT(cols3|all) OUT.json WORKERS [KMAX=13]"""
import json, sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cert as C  # noqa: E402

H = Path(__file__).resolve().parent
T = json.loads((H / "G1/MINK_TABLE_original.json").read_text())
QC = set(json.loads((H / "G1/QCLEAR_original.json").read_text())["cells"])


def one(a):
    t, g, sup, kmax = a
    work = [c for c in QC if (c % 8 >= 3 or sup == "all") and c not in (t, g)]
    cells = [t] + work
    r = {"ids": [str(i) for i in range(len(cells))], "cells0": cells, "tid": 0, "goal_cell": g, "legal_cells": list(range(64)), "fixed": [False] * len(cells)}
    occ0 = set()
    dest = [d for d in range(64) if d != g and d in QC]
    P, D, G = C.masks_fast(T, cells, r["ids"], list(range(1, len(cells))), 0, g, dest)
    b = C.bfs(len(cells), list(range(1, len(cells))), 0, P, D, G, kmax)
    return {"t": t, "g": g, "support": sup, "n_objects": len(cells), "K_lb_ceiling": b["K_lb"]}


if __name__ == "__main__":
    sup, out, W = sys.argv[1], sys.argv[2], int(sys.argv[3])
    kmax = int(sys.argv[4]) if len(sys.argv) > 4 else 13
    lo = 3 if sup == "cols3" else 0
    ts = [c for c in QC if c % 8 >= max(lo, 4) and int(T["pick0"][str(c)])]
    gs = [c for c in QC if c % 8 >= lo and int(T["place0"][str(c)])]
    jobs = [(t, g, sup, kmax) for t in ts for g in gs if g != t]
    res = []
    with Pool(W) as p:
        for r in p.imap_unordered(one, jobs):
            res.append(r)
            print(json.dumps(r), flush=True)
    Path(out).write_text(json.dumps(res, indent=0))
