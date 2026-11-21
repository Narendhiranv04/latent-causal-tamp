#!/usr/bin/env python3
"""G3 K9/K12 feasibility search at the frozen model's object cap: fixed target / goal, exactly NOBJ objects (default 20) in the TRAIN object
support (columns 3-7, q_ref-clear), swap moves (move one obstacle to a free support cell), annealing on K_lb (MINK_STATIC_V2), seeded from a
given layout (e.g. the greedy-pruned state).  Writes every layout whose K_lb >= KMIN.
    python anneal20.py SEEDFILE(jsonl, first row) RUN_SEED STEPS OUT.jsonl [KMIN=9] [KMAX=13]"""
import json, math, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cert as C  # noqa: E402

H = Path(__file__).resolve().parent
T = json.loads((H / "G1/MINK_TABLE_original.json").read_text())
QC = set(json.loads((H / "G1/QCLEAR_original.json").read_text())["cells"])


def kl(cells, g, kmax):
    n = len(cells)
    dest = [d for d in range(64) if d != g and d in QC]
    P, D, G = C.masks_fast(T, cells, [str(i) for i in range(n)], list(range(1, n)), 0, g, dest)
    b = C.bfs(n, list(range(1, n)), 0, P, D, G, kmax)
    k = b["K_lb"]
    return (-1 if k is None else kmax + 1 if isinstance(k, str) else k), b.get("witness_set")


def main(seedf, rs, steps, out, kmin=9, kmax=13):
    L = json.loads(open(seedf).readline())
    if L.get("random_init"):                       # FINAL mode: fixed target / goal, random NOBJ-object initial layout (independent of any
        t, g, n = L["t"], L["goal_cell"], L.get("n_objects", 20)          # engineering pruning state), fresh run seed
        rng = random.Random(f"ANNEAL20R|{t}|{g}|{rs}")
        sup = [c for c in QC if c % 8 >= 3 and c not in (t, g)]
        cells = [t] + rng.sample(sup, n - 1)
    else:
        cells, g = list(L["cells0"]), L["goal_cell"]
        rng = random.Random(f"ANNEAL20|{cells[0]}|{g}|{rs}")
        sup = [c for c in QC if c % 8 >= 3 and c not in (cells[0], g)]
    cur, ws = kl(cells, g, kmax)
    best, temp, seen = cur, 0.6, set()
    with open(out, "a") as f:
        for i in range(steps):
            new = list(cells)
            free = [c for c in sup if c not in new]
            new[rng.randrange(1, len(new))] = rng.choice(free)
            s, w = kl(new, g, kmax)
            if s >= cur or rng.random() < math.exp((s - cur) / temp):
                cells, cur, ws = new, s, w
                key = tuple(sorted(cells[1:]))
                if cur >= kmin and key not in seen:
                    seen.add(key)
                    f.write(json.dumps({"t": cells[0], "g": g, "n_objects": len(cells), "K_lb": cur, "cells0": cells, "goal_cell": g, "witness_set": ws,
                                        "gen": "ANNEAL20_V1", "run_seed": rs, "step": i}) + "\n"); f.flush()
                best = max(best, cur)
            temp = max(0.05, temp * 0.999)
            if i % 200 == 0:
                print(json.dumps({"step": i, "cur": cur, "best": best}), flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], int(a[1]), int(a[2]), a[3], int(a[4]) if len(a) > 4 else 9, int(a[5]) if len(a) > 5 else 13)
