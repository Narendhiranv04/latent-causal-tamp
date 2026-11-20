#!/usr/bin/env python3
"""G1/G2a static feasibility pilot (no physics, no model): how large a SOUND lower bound K_lb (cert.py, MINK_STATIC_V1) can 8x8 layouts reach
under the frozen grammar (<= 20 objects incl. the target, one move per object, admissible destinations)?  Deterministic seeded greedy:
target / goal on screen-valid cells, then repeatedly add one movable disc at the free cell that maximizes K_lb (ties by seeded RNG); keep
the best layout per K reached.  Output = candidate layouts only (proposals), never accepted roots: physics and certificates decide later.
    python gen_static.py TABLE.json GEOM SEED0 NSEEDS OUT.jsonl [MAXOBJ=20]"""
import json, random, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cert as C  # noqa: E402

Q_TEMPLATE = None


def kbound(T, cells, tid, goal, qclear):
    ids = [f"o{i:02d}" for i in range(len(cells))]
    r = {"ids": ids, "cells0": cells, "tid": tid, "goal_cell": goal, "legal_cells": list(range(64)), "fixed": [False] * len(cells)}
    b = C.bound(T, r, qclear)
    return b["K_lb"]


def run(T, geom, seed, qclear, maxobj, deadline):
    rng = random.Random(f"GENSTATIC|{geom}|{seed}")
    valid = [c for c in range(64) if T["pick0"][str(c)] and T["place0"][str(c)] and c in qclear]
    tc, goal = rng.sample(valid, 2)
    cells, tid, best, trace = [tc], 0, {}, []
    while len(cells) < maxobj and time.time() < deadline:
        free = [c for c in valid if c not in cells and c != goal]
        rng.shuffle(free)
        scored = []
        for c in free:
            k = kbound(T, cells + [c], tid, goal, qclear)
            kv = -1 if k is None else (99 if isinstance(k, str) else k)
            scored.append((kv, rng.random(), c))
        scored.sort(reverse=True)
        kv, _, c = scored[0]
        if kv == -1:                                     # every addition makes the relaxed goal unreachable: stop (layout infeasible)
            break
        cells.append(c)
        trace.append(kv)
        if kv not in best or len(cells) < len(best[kv]["cells0"]):
            best[kv] = {"cells0": list(cells), "tid": tid, "goal_cell": goal, "K_lb": kv}
    return best, trace


def main(table, geom, seed0, n, out, maxobj=20):
    T = json.loads(Path(table).read_text())
    qclear = set(T.get("qclear_template") or range(64))
    t0 = time.time()
    with open(out, "a") as f:
        for s in range(seed0, seed0 + n):
            best, trace = run(T, geom, s, qclear, maxobj, time.time() + 600)
            for kv, L in sorted(best.items()):
                f.write(json.dumps({"geom": geom, "seed": s, **L, "n_objects": len(L["cells0"]), "trace": trace}) + "\n")
            print(json.dumps({"seed": s, "max_K_lb": max(best) if best else None, "trace": trace, "s": round(time.time() - t0, 1)}), flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], int(a[2]), int(a[3]), a[4], int(a[5]) if len(a) > 5 else 20)
