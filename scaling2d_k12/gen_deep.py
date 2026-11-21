#!/usr/bin/env python3
"""G2 generator v3 (no physics, no model): simulated annealing on the GRAMMAR-COMPLETE sound bound K_lb (cert.py MINK_STATIC_V2, dest_mode
'any_legal') with a PARKING-CELL PRIOR.

Parking prior (park_rank): TRAIN-only physical relocation reliability per destination cell (G1/PARK_PRIOR_TRAIN.json; columns 0-2 next to
the base have ~0 failures, the far column 13-20 %), then the kill-table blocking footprint.  Objects are placed only in columns 3-7 (the TRAIN
object support of the frozen model), so the most reliable parking cells (columns 0-2) are never occupied at construction.
Seeding: target in columns 5-7 (deep), goal in columns 4-7, initial discs between base and target.
Moves: add / remove / move one disc (<= MAXOBJ = 20 objects: frozen model capacity).  Score K_lb - 0.02 n (sparser at equal K).
Output: every new (K_lb, layout) best per seed with the bound's witness set; layouts are proposals only (acceptance needs a teacher witness).
    python gen_deep.py TABLE QCLEAR SEED0 N STEPS OUT.jsonl [KMAX=12]"""
import functools, json, math, os, random, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cert as C  # noqa: E402

MAXOBJ, N_PARK = 20, 10


PRIOR = json.loads((Path(__file__).resolve().parent / "G1/PARK_PRIOR_TRAIN.json").read_text())


def p_fail(kind, c):
    """TRAIN-only smoothed relocation failure rate (dest = as destination, pick_source = object picked from c); Beta(1, 9) prior mean 0.1."""
    s, f = PRIOR[kind][str(c)]
    return (f + 1.0) / (s + f + 10.0)


def park_rank(T, qc, goal=None):
    """PARKING-CELL PRIOR: physical reliability first (TRAIN relocation failure rate as a destination), then low blocking footprint (kill tables),
    then more live place candidates.  q_ref-blocking cells and the goal excluded."""
    pc = lambda v: bin(int(v)).count("1")  # noqa: E731
    foot = {c: sum(pc(T["pickkill"][str(x)].get(str(c), 0)) + pc(T["placekill"][str(x)].get(str(c), 0)) for x in range(64) if x != c) for c in range(64)}
    return sorted((c for c in range(64) if c in qc and c != goal and pc(T["place0"][str(c)])), key=lambda c: (round(p_fail("dest", c), 2), foot[c], -pc(T["place0"][str(c)]), c))


def score(T, cells, goal, qc, kmax):
    r = {"ids": [str(i) for i in range(len(cells))], "cells0": cells, "tid": 0, "goal_cell": goal, "legal_cells": list(range(64)), "fixed": [False] * len(cells)}
    b = C.bound(T, r, qc, "any_legal")
    k = b["K_lb"]
    return (-1 if k is None else kmax + 1 if isinstance(k, str) else k), b


def run(T, qc, seed, steps, kmax):
    rng = random.Random(f"GENDEEP3|{T['geom']}|{seed}")
    col = lambda c: c % 8  # noqa: E731
    lo = 0 if os.environ.get("GEN_ALLCOLS") else 3                               # reference arm B only: objects anywhere
    work = [c for c in qc if col(c) >= lo and int(T["pick0"][str(c)])]          # objects only in the TRAIN support (columns 3-7)
    t = rng.choice([c for c in work if col(c) >= 5])
    g = rng.choice([c for c in work if c != t and col(c) >= 4 and int(T["place0"][str(c)])])
    park = set()                                                                 # columns 0-2 (most reliable parking) are never occupied
    free = lambda cells: [c for c in work if c not in cells and c != g and c not in park]  # noqa: E731
    near = [c for c in free([t]) if col(c) <= col(t)]
    cells = [t] + rng.sample(near, min(len(near), rng.randint(10, 16)))
    cur, b = score(T, cells, g, qc, kmax)
    firsts, temp = {}, 1.0
    for i in range(steps):
        new = list(cells)
        op = rng.random()
        fr = free(new)
        if op < 0.35 and len(new) < MAXOBJ and fr:
            new.append(rng.choice(fr))
        elif op < 0.5 and len(new) > 2:
            new.pop(rng.randrange(1, len(new)))
        elif fr:
            new[rng.randrange(1, len(new))] = rng.choice(fr)
        s, bb = score(T, new, g, qc, kmax)
        e_new, e_cur = s - 0.02 * len(new), cur - 0.02 * len(cells)
        if s >= 0 and (e_new >= e_cur or rng.random() < math.exp((e_new - e_cur) / temp)):
            cells, cur = new, s
            if s >= 1 and (s not in firsts or len(cells) < firsts[s]["n_objects"]):
                firsts[s] = {"cells0": list(cells), "tid": 0, "goal_cell": g, "K_lb": s, "witness_set": bb.get("witness_set"), "step": i,
                             "n_objects": len(cells), "park_reserved": sorted(park), "bound": "MINK_STATIC_V2"}
        temp = max(0.03, temp * 0.9993)
    return max(firsts) if firsts else -1, firsts


def main(table, qclear, seed0, n, steps, out, kmax=12):
    T = json.loads(Path(table).read_text())
    qc = set(json.loads(Path(qclear).read_text())["cells"])
    with open(out, "a") as f:
        for s in range(seed0, seed0 + n):
            t0 = time.time()
            best, firsts = run(T, qc, s, steps, kmax)
            for k, L in sorted(firsts.items()):
                if k >= 4:
                    f.write(json.dumps({"geom": T["geom"], "seed": s, "gen": "GENDEEP3", **L}) + "\n"); f.flush()
            print(json.dumps({"seed": s, "best": best, "s": round(time.time() - t0, 1)}), flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], int(a[2]), int(a[3]), int(a[4]), a[5], int(a[6]) if len(a) > 6 else 12)
