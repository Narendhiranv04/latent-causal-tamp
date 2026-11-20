#!/usr/bin/env python3
"""G2a constructive static generator (no physics, no model): cause-of-cause layouts from the MINK grasp-screen kill tables.
Seeded per (family, K_design, slot): target t and goal g on screen-valid cells; a randomized greedy COVER of the target's live pick candidates
(cells whose single disc kills them) gives the direct blockers; each frontier object is then itself covered (its pick candidates killed by new
discs), to a family-specific depth / branching, sharing existing discs where they already cover (SHARED_SUPPORT) and adding inert distractors
(DISTRACTOR_HEAVY), within <= 20 objects and q_ref-clear cells.  Every layout is scored ONLY by the sound bound K_lb (cert.py); layouts are
proposals for later physical witness search, never accepted roots.
    python gen_cover.py TABLE.json GEOM FAMILY KDESIGN SEED0 N OUT.jsonl"""
import json, random, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cert as C  # noqa: E402

FAM = {"DEEP_CHAIN": dict(direct=(1, 2), branch=1, share=0.0, distract=0), "BRANCHING": dict(direct=(1, 2), branch=2, share=0.0, distract=0),
       "SHARED_SUPPORT": dict(direct=(2, 3), branch=1, share=0.8, distract=0), "MIXED_CAUSES": dict(direct=(1, 3), branch=2, share=0.4, distract=1),
       "DISTRACTOR_HEAVY": dict(direct=(1, 2), branch=1, share=0.2, distract=4)}


def cover(T, x, live_mask, avail, used, rng, share):
    """random greedy cover of the live pick candidates of an object at x: -> list of NEW cells (existing discs in `used` count first)."""
    kill = T["pickkill"][str(x)]
    left = {c for c in range(48) if live_mask >> c & 1}
    for p in used:                                            # candidates already killed by present discs
        left -= {c for c in list(left) if int(kill.get(str(p), 0)) >> c & 1}
    new = []
    while left:
        opts = [(sum(1 for c in left if int(kill.get(str(p), 0)) >> c & 1), rng.random(), p) for p in avail if p not in new]
        opts = [o for o in opts if o[0] > 0]
        if not opts:
            return None
        opts.sort(reverse=True)
        pick = opts[0] if rng.random() > 0.3 or len(opts) == 1 else opts[min(len(opts) - 1, rng.randrange(1, 3))]
        p = pick[2]
        new.append(p)
        left -= {c for c in list(left) if int(kill.get(str(p), 0)) >> c & 1}
    return new


def build(T, fam, kdes, seed, qclear):
    F = FAM[fam]
    rng = random.Random(f"GENCOVER|{T['geom']}|{fam}|{kdes}|{seed}")
    valid = [c for c in range(64) if int(T["pick0"][str(c)]) and int(T["place0"][str(c)]) and c in qclear]
    t, g = rng.sample(valid, 2)
    cells = [t]
    avail = lambda: [c for c in valid if c not in cells and c != g]  # noqa: E731
    frontier, depth = [t], 0
    while frontier and len(cells) < 20:
        nxt = []
        for x in frontier:
            ex = [c for c in cells if c != x] if rng.random() < F["share"] else []
            new = cover(T, x, int(T["pick0"][str(x)]), avail(), ex, rng, F["share"])
            if new is None:
                return None
            if len(cells) + len(new) > 20:
                return None
            cells += new
            nxt += new[:F["branch"]] if x != t else new
        depth += 1
        frontier = nxt
        if depth >= max(2, kdes // max(1, F["branch"])) or len(cells) >= kdes + 1:
            break
    for _ in range(F["distract"]):
        if len(cells) < 20 and avail():
            cells.append(rng.choice(avail()))
    return cells, 0, g


def main(table, geom, fam, kdes, seed0, n, out):
    T = json.loads(Path(table).read_text())
    qclear = set(range(64))
    t0, stats = time.time(), {}
    with open(out, "a") as f:
        for s in range(seed0, seed0 + n):
            b = build(T, fam, kdes, s, qclear)
            if b is None:
                stats["no_layout"] = stats.get("no_layout", 0) + 1; continue
            cells, tid, g = b
            r = {"ids": [f"o{i:02d}" for i in range(len(cells))], "cells0": cells, "tid": tid, "goal_cell": g, "legal_cells": list(range(64)), "fixed": [False] * len(cells)}
            k = C.bound(T, r, qclear)["K_lb"]
            stats[str(k)] = stats.get(str(k), 0) + 1
            f.write(json.dumps({"geom": geom, "family": fam, "K_design": kdes, "seed": s, "cells0": cells, "tid": tid, "goal_cell": g, "n_objects": len(cells), "K_lb": k}) + "\n")
    print(json.dumps({"family": fam, "K_design": kdes, "n": n, "K_lb_hist": stats, "s": round(time.time() - t0, 1)}), flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2], int(a[3]), int(a[4]), int(a[5]), a[6])
