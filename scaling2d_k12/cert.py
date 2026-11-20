#!/usr/bin/env python3
"""MINK_STATIC_V1 certificate: exact minimum number of relocations of the grasp-screen RELAXATION (mink.py tables), a sound lower bound on the
minimum length of any admissible repair that the frozen 2D teacher can verify.  Pure Python, no physics.

Abstract state M = set of already-relocated movable objects (deletion relaxation: a relocated object is treated as removed; its new disc can
only add kills, so ignoring it only enlarges the feasible set).  Relocating o from M is allowed iff
  (a) some declared pick candidate c of o at its initial cell is killed by no disc present (target, fixed, unmoved movables minus o), and
  (b) some admissible destination d (legal, never initially occupied, not the goal, single disc at d leaves q_ref clear) has a place candidate
      killed by no present disc other than o.
Goal at M iff the target's pick at its cell and its place at the goal both have a live candidate in Present(M).  K_lb = min |M| over goal M
reachable through allowed relocations (any order; one move per object; target last) = BFS over subsets.  Sound only for: the frozen teacher
(idx = None), this geometry implementation, the declared 48-candidate grasp family and the admissible-destination grammar.
    python cert.py bound TABLE.json ROOT.json        -> certificate JSON on stdout
    python cert.py check CERT.json                   re-run the BFS from the stored bitmasks (independent checker)"""
import json, sys


def masks(T, cells0, ids, movable, tgt, goal, dest_ok):
    """-> per object: list of blocker bitmasks for each live pick candidate; per object: list over (d, c) of place blocker bitmasks; target
    goal-place blocker bitmasks.  Bit i = object i present kills that candidate (computed from the universal tables)."""
    pk, pl = T["pickkill"], T["placekill"]
    n = len(ids)

    def pick_sets(i):
        x, out = str(cells0[i]), []
        for c in range(48):
            if not (T["pick0"][x] >> c) & 1:
                continue
            out.append(sum(1 << j for j in range(n) if j != i and (pk[x].get(str(cells0[j]), 0) >> c) & 1))
        return out

    def place_sets(d, i):
        out = []
        for c in range(48):
            if not (T["place0"][str(d)] >> c) & 1:
                continue
            out.append(sum(1 << j for j in range(n) if j != i and (pl[str(d)].get(str(cells0[j]), 0) >> c) & 1))
        return out
    mini = lambda S: sorted({s for s in S if not any(t != s and t & s == t for t in S)})  # noqa: E731  minimal antichain (sound: same OR-test)
    P = {i: mini(pick_sets(i)) for i in movable + [tgt]}
    D = {i: mini([m for d in dest_ok for m in place_sets(d, i)]) for i in movable}
    G = mini(place_sets(goal, tgt))
    return P, D, G


def bfs(n, movable, tgt, P, D, G, kmax=12):
    full = (1 << n) - 1
    live = lambda S, present: any(m & present == 0 for m in S)  # noqa: E731
    layer, seen, counts = {0}, {0}, []
    for k in range(kmax + 1):
        counts.append(len(layer))
        for M in sorted(layer):
            pres = full & ~M
            if live(P[tgt], pres) and live(G, pres):
                return {"K_lb": k, "witness_set": [i for i in range(n) if M >> i & 1], "layer_counts": counts}
        nxt = set()
        for M in layer:
            pres = full & ~M
            for o in movable:
                if M >> o & 1:
                    continue
                po = pres & ~(1 << o)
                if live(P[o], po) and live(D[o], po):
                    N = M | (1 << o)
                    if N not in seen:
                        seen.add(N); nxt.add(N)
        if not nxt:
            return {"K_lb": None, "reason": "GOAL_UNREACHABLE_IN_RELAXATION", "layer_counts": counts}
        layer = nxt
    return {"K_lb": f">{kmax}", "layer_counts": counts}


def bound(T, root, qclear):
    """root: {ids, cells0, tid, goal_cell, legal_cells, fixed (bool list)}; qclear: set of cells where a single disc leaves q_ref clear."""
    ids, cells0, tgt, goal = root["ids"], root["cells0"], root["tid"], root["goal_cell"]
    movable = [i for i in range(len(ids)) if i != tgt and not root["fixed"][i]]
    occ0 = set(cells0)
    dest_ok = [d for d in root["legal_cells"] if d not in occ0 and d != goal and d in qclear]
    P, D, G = masks(T, cells0, ids, movable, tgt, goal, dest_ok)
    res = bfs(len(ids), movable, tgt, P, D, G)
    return {"version": "MINK_STATIC_V1", "geom": T["geom"], "root_id": root.get("root_id"), "n_objects": len(ids), "movable": movable, "target": tgt,
            "dest_ok": dest_ok, "P": {str(k): v for k, v in P.items()}, "D": {str(k): v for k, v in D.items()}, "G": G, **res}


def check(c):
    P = {int(k): v for k, v in c["P"].items()}
    D = {int(k): v for k, v in c["D"].items()}
    r = bfs(c["n_objects"], c["movable"], c["target"], P, D, c["G"])
    return r["K_lb"] == c["K_lb"], r


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "bound":
        T, R = json.loads(open(a[1]).read()), json.loads(open(a[2]).read())
        print(json.dumps(bound(T, R, set(R["qclear"]))))
    elif a[0] == "check":
        print(check(json.loads(open(a[1]).read())))
    else:
        raise SystemExit(__doc__)
