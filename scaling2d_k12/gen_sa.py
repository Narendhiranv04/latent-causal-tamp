#!/usr/bin/env python3
"""G2a static pilot by simulated annealing (no physics, no model): seeded layouts (target + goal fixed per seed, <= 20 discs) are perturbed by
add / remove / move-one-disc steps and scored by the SOUND bound K_lb (cert.py, MINK_STATIC_V1).  Records the first layout reaching each K_lb
(and the bound's minimal goal set).  These are proposals for physical witness search only; acceptance needs a verified witness of length K_lb.
    python gen_sa.py TABLE.json SEED0 N STEPS OUT.jsonl [MAXOBJ=20]"""
import json, math, random, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cert as C  # noqa: E402


def score(T, cells, goal, qc):
    r = {"ids": [f"o{i:02d}" for i in range(len(cells))], "cells0": cells, "tid": 0, "goal_cell": goal, "legal_cells": list(range(64)), "fixed": [False] * len(cells)}
    b = C.bound(T, r, qc)
    k = b["K_lb"]
    return (-1 if k is None else 99 if isinstance(k, str) else k), b


def run(T, seed, steps, maxobj, qc):
    """v2: every initial disc on a q_ref-clear cell (start state collision-free); acceptance on K_lb - 0.02 * n_objects (sparser at equal K)."""
    rng = random.Random(f"GENSA2|{T['geom']}|{seed}")
    orall = lambda d: __import__("functools").reduce(lambda a, b: a | int(b), d.values(), 0)  # noqa: E731
    blockable = [x for x in range(64) if int(T["pick0"][str(x)]) and not int(T["pick0"][str(x)]) & ~orall(T["pickkill"][str(x)])]
    t = rng.choice([x for x in blockable if x in qc])
    g = rng.choice([c for c in range(64) if c != t and int(T["place0"][str(c)])])
    cells = [t] + rng.sample([c for c in qc if c not in (t, g)], rng.randint(6, 12))
    cur, b = score(T, cells, g, qc)
    best, firsts, temp = cur, {}, 1.0
    for i in range(steps):
        new = list(cells)
        free = [c for c in qc if c not in new and c != g]
        op = rng.random()
        if op < 0.35 and len(new) < maxobj:
            new.append(rng.choice(free))
        elif op < 0.55 and len(new) > 2:
            new.pop(rng.randrange(1, len(new)))
        else:
            new[rng.randrange(1, len(new))] = rng.choice(free)
        s, bb = score(T, new, g, qc)
        e_new, e_cur = s - 0.02 * len(new), cur - 0.02 * len(cells)
        if s >= 0 and (e_new >= e_cur or rng.random() < math.exp((e_new - e_cur) / temp)):
            cells, cur, b = new, s, bb
            if s >= 0 and (s not in firsts or len(cells) < firsts[s]["n_objects"]):
                firsts[s] = {"cells0": list(cells), "tid": 0, "goal_cell": g, "K_lb": s, "witness_set": bb.get("witness_set"), "step": i, "n_objects": len(cells)}
            best = max(best, s)
        temp = max(0.05, temp * 0.999)
    return best, firsts


def main(table, seed0, n, steps, out, maxobj=20, qclear=None):
    T = json.loads(Path(table).read_text())
    qc = set(json.loads(Path(qclear).read_text())["cells"]) if qclear else set(range(64))
    with open(out, "a") as f:
        for s in range(seed0, seed0 + n):
            t0 = time.time()
            best, firsts = run(T, s, steps, maxobj, qc)
            for k, L in sorted(firsts.items()):
                f.write(json.dumps({"geom": T["geom"], "seed": s, **L}) + "\n"); f.flush()
            print(json.dumps({"seed": s, "best_K_lb": best, "reached": sorted(firsts), "s": round(time.time() - t0, 1)}), flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], int(a[1]), int(a[2]), int(a[3]), a[4], int(a[5]) if len(a) > 5 else 20, a[6] if len(a) > 6 else None)
