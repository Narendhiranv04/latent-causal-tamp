#!/usr/bin/env python3
"""G3 high-K constructor: greedy pruning from FULL occupancy (columns 3-7 support) for a fixed target / goal.  K_lb (MINK_STATIC_V2) is
monotone in occupancy, so removing one disc at a time while keeping K_lb maximal traces the best layout reachable by deletion down to
MAXOBJ = 20 objects (frozen model capacity).  Every intermediate layout with n <= 20 is written with its bound.  Ties: remove the disc with the
largest blocking-footprint-free distance to the target (keeps the corridor), then cell index.
    python prune.py T G OUT.jsonl WORKERS [KMAX=13]"""
import json, sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cert as C  # noqa: E402

H = Path(__file__).resolve().parent
T = json.loads((H / "G1/MINK_TABLE_original.json").read_text())
QC = set(json.loads((H / "G1/QCLEAR_original.json").read_text())["cells"])
KMAX = 13


def kl(args):
    cells, g = args
    n = len(cells)
    dest = [d for d in range(64) if d != g and d in QC]
    P, D, G = C.masks_fast(T, cells, [str(i) for i in range(n)], list(range(1, n)), 0, g, dest)
    b = C.bfs(n, list(range(1, n)), 0, P, D, G, KMAX)
    k = b["K_lb"]
    return (-1 if k is None else KMAX + 1 if isinstance(k, str) else k), b.get("witness_set")


def main(t, g, out, W):
    cells = [t] + [c for c in sorted(QC) if c % 8 >= 3 and c not in (t, g)]
    dist = lambda c: abs(c // 8 - t // 8) + abs(c % 8 - t % 8)  # noqa: E731
    with Pool(W) as p, open(out, "a") as f:
        k, ws = kl((cells, g))
        while len(cells) > 20:
            cand = [[c for c in cells if c != x] for x in cells[1:]]
            res = p.map(kl, [(c, g) for c in cand])
            best = max(range(len(cand)), key=lambda i: (res[i][0], dist(cells[1 + i]), -cells[1 + i]))
            cells, (k, ws) = cand[best], res[best]
            rec = {"t": t, "g": g, "n_objects": len(cells), "K_lb": k, "cells0": cells, "goal_cell": g, "witness_set": ws, "gen": "PRUNE_V1"}
            f.write(json.dumps(rec) + "\n"); f.flush()
            print(json.dumps({k_: rec[k_] for k_ in ("t", "g", "n_objects", "K_lb")}), flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    KMAX = int(a[4]) if len(a) > 4 else 13
    main(int(a[0]), int(a[1]), a[2], int(a[3]))
