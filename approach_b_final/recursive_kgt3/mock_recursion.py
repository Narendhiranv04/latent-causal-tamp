#!/usr/bin/env python3
"""MOCK-ONLY demonstration of the proposed recursion (no neural model, no physics, no dataset).  A symbolic world:
  PB[X]  = objects that must already be relocated before X can be picked (pick blockers); GB = objects blocking the goal placement of T.
  Ŷ(task=(X, d), moved M) = 1 iff PB[X] ⊆ M (and GB ⊆ M for the original target) -- a PERFECT mock of the learned Y head.
  Mock local K<=3 generator for task τ in scene M: proposes the currently unmet direct blockers of τ's object (up to 3), ranked,
  plus distractors; RECALL is controlled by `hide` (objects the mock proposer never surfaces).  Mock stage X: a chunk is executable iff
  every action's object is pickable at its time (dependencies satisfied in order).
The search is exactly the AUDIT.md pseudocode: solve(S, τ) -> local hypotheses u (<=3) -> expand(u): for each action (A, d_A) whose
temporary task Ŷ_(A,d_A) is low, recursively solve the temporary task and insert the enabling sequence before it -> iterative loop on the
same task while capacity remains -> global legality (each object once, original target never moved) -> final original-task Ŷ.
    python mock_recursion.py"""
import itertools, json

T = "T"


class World:
    def __init__(self, PB, GB, distract=("Z1", "Z2", "Z3"), hide=()):
        self.PB, self.GB, self.distract, self.hide = PB, set(GB), list(distract), set(hide)
        self.calls = {"local": 0, "y_probe": 0, "x_chunk": 0}

    def blockers(self, X):
        return set(self.PB.get(X, ())) | (self.GB if X == T else set())

    def Y(self, X, moved):                                   # mock learned Y for task (X, d_X) in the scene after `moved`
        self.calls["y_probe"] += 1
        return float(self.blockers(X) <= set(moved))

    def local(self, X, moved, reserved, cap):                # mock frozen cVAE + D: ranked local hypotheses of length <= min(3, cap)
        self.calls["local"] += 1
        need = sorted(o for o in self.blockers(X) - set(moved) - set(reserved) if o not in self.hide)
        pool = need + [z for z in self.distract if z not in moved and z not in reserved]
        out = []
        for k in range(min(3, cap), 0, -1):                  # prefer hypotheses covering more unmet blockers (stands in for higher p11)
            for u in itertools.combinations(pool, k):
                out.append(list(u))
        out.sort(key=lambda u: (-len(set(u) & set(need)), len(u)))
        return out[:6]                                       # local beam B = 6

    def X_ok(self, seq):                                     # mock stagewise X over the whole order (dependency respected)
        self.calls["x_chunk"] += 1
        moved = set()
        for o in seq:
            if not self.blockers(o) <= moved:
                return False
            moved.add(o)
        return True


def solve(W, X, moved, reserved, cap, depth, Dmax=4, trace=None):
    """-> list of enabling sequences s (objects, global order) such that Ŷ(X | moved + s) = 1; [] if none within budget."""
    if W.Y(X, moved):
        return [[]]
    if depth > Dmax or cap <= 0:
        return []
    found = []
    for u in W.local(X, moved, reserved, cap):
        for s in expand(W, u, moved, reserved | {X}, cap, depth, Dmax, trace):
            m2 = list(moved) + s
            if W.Y(X, m2):
                found.append(s)
            elif len(s) < cap:                               # iterative loop on the SAME task from the edited scene
                for t in solve(W, X, m2, reserved | set(s), cap - len(s), depth + 1, Dmax, trace):
                    found.append(s + t)
        if found:
            break                                            # first local hypothesis that yields a solution (fixed budget, deterministic)
    if trace is not None:
        trace.append({"task": X, "depth": depth, "moved_before": len(moved), "solutions": [len(f) for f in found[:3]]})
    return found


def expand(W, u, moved, reserved, cap, depth, Dmax, trace):
    res = [[]]
    for A in u:
        nxt = []
        for p in res:
            m = list(moved) + p
            if W.Y(A, m):                                    # temporary task (A -> d_A) predicted feasible now
                nxt.append(p + [A])
                continue
            room = cap - len(p) - 1 - (len(u) - u.index(A) - 1)
            for e in solve(W, A, m, reserved | set(u) | {T}, room, depth + 1, Dmax, trace):
                if not (set(e) & (set(p) | {A, T})):         # global legality: each object at most once, target never a mover
                    nxt.append(p + e + [A])
        res = nxt[:4]                                        # expansion beam 4
    return res


def run(name, PB, GB, hide=(), cap=12):
    W = World(PB, GB, hide=hide)
    tr = []
    sols = solve(W, T, [], {T}, cap, 0, trace=tr)
    best = min(sols, key=len) if sols else None
    rep = {"case": name, "found": best is not None, "plan": best, "length": len(best) if best else None,
           "final_Y": W.Y(T, best) if best else 0.0, "stage_X_ok": W.X_ok(best) if best else None, "calls": W.calls,
           "stop": "SOLVED" if best else "NO_CANDIDATE"}
    print(json.dumps(rep))
    return rep


if __name__ == "__main__":
    # K6: T blocked by B, C (pick) and D (goal place); B needs E, E needs H; D needs F.   valid order H,E,B,C,F,D
    K6 = dict(PB={"T": ["B", "C"], "B": ["E"], "E": ["H"], "D": ["F"]}, GB=["D"])
    # K12: T direct blockers A,B,C (pick) + L (goal); A needs D,E; D needs G; B needs F; F needs H,I; C needs J; J needs K
    K12 = dict(PB={"T": ["A", "B", "C"], "A": ["D", "E"], "D": ["G"], "B": ["F"], "F": ["H", "I"], "C": ["J"], "J": ["K"]}, GB=["L"])
    out = [run("K6", **K6), run("K12", **K12),
           run("K12_recall_miss_K", **K12, hide=("K",)),          # the enabling action K is never proposed -> must fail
           run("K12_cap11", **K12, cap=11)]                       # capacity below the minimum -> must fail
    W = World(**K12)
    good = ["G", "D", "E", "A", "H", "I", "F", "B", "K", "J", "C", "L"]
    bad = ["A", "G", "D", "E", "H", "I", "F", "B", "K", "J", "C", "L"]  # SAME endpoint (same moved set), wrong order
    print(json.dumps({"same_endpoint_Y": [W.Y(T, good), W.Y(T, bad)], "stage_X": [W.X_ok(good), W.X_ok(bad)]}))
