"""Symbolic mock of models.py (same interface) on real 8x8 learner inputs, so HypoRoot / reservation / legality code is exercised for real.
World: BLK[x] = objects that must be relocated (moved away from their S0 cell) before x can be picked; for the original target also GOALBLK.
Signals (deliberately informative, i.e. a 'good' learned model): local p11 rewards covering unmet direct blockers of the CURRENT task's target;
ytask = 1 iff the task target's blockers are all moved; y_end = 1 iff every original-target blocker is in the endpoint; px = 1 iff every action's
own blockers were moved before it (order-sensitive).  `hide` removes objects from all proposals (recall failure)."""
import copy, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class C(dict):
    def inc(self, k, n=1):
        self[k] = self.get(k, 0) + n


def make_row(n_obj, t_cell=63, goal=61, name="MOCK"):
    """8x8 scene: target t0 at t_cell, obstacles o00.. on cells 62,55,54,47,... (deterministic), goal free."""
    cells = [t_cell]
    order = [c for c in range(63, -1, -1) if c not in (t_cell, goal) and c % 8 >= 2]
    cells += order[: n_obj - 1]
    ids = ["t0"] + [f"o{i:02d}" for i in range(n_obj - 1)]
    cxy = {str(c): [0.08 * (c % 8) + 0.04, 0.08 * (c // 8) + 0.04] for c in range(64)}
    attrs = [[0.024, 1.0, 0.0, 0.0]] + [[0.024, 0.0, 1.0, 0.0] for _ in range(n_obj - 1)]
    inp = {"ids": ids, "tid": 0, "attrs": attrs, "cells0": cells, "xy0": [cxy[str(c)] for c in cells], "goal_cell": goal, "goal": cxy[str(goal)],
           "cell_xy": cxy, "legal_cells": list(range(64)), "ctx": [1.0, -1.0, -1.0, 0.0, 0.0, 0.0] + cxy[str(goal)] + [0.07], "base": [-0.14, 0.32],
           "grid": [8, 8], "q_ref": [1.5708, -1.5708, -1.5708]}
    return {"root_id": name, "domain": "2d", "inputs": inp}


class MockModels:
    name = "mock"

    def __init__(self, row0, BLK, GOALBLK=(), hide=()):
        self.row0, self.BLK, self.GB, self.hide = row0, {k: set(v) for k, v in BLK.items()}, set(GOALBLK), set(hide)
        self.c = C()

    def _moved(self, hr):
        c0 = self.row0["inputs"]["cells0"]
        return {i for i, c in enumerate(hr.cells0) if c != c0[i]}

    def blk(self, x):
        return self.BLK.get(x, set()) | (self.GB if x == 0 else set())

    def propose(self, hr):
        self.c.inc("cvae_queries", len(hr.movable))
        legal = sorted(hr.legal_dests(hr.cells0), key=lambda d: (d % 8, d // 8))    # park on the left columns first
        return {o: legal[:4] for o in hr.movable if o not in self.hide}

    def _p(self, hr, seq):
        moved, unmet = self._moved(hr), self.blk(hr.tid) - self._moved(hr)
        cov = len({o for o, _ in seq} & unmet)
        junk = len({o for o, _ in seq} - unmet)
        return 0.02 + 0.9 * cov / max(1, len(unmet)) - 0.005 * junk

    def _px(self, hr, seq):
        done = set(self._moved(hr))
        for o, _ in seq:
            if not self.blk(o) <= done:
                return 0.1
            done.add(o)
        return 0.95

    def score(self, hr, seqs, chunk=None):
        self.c.inc("local_scored", len(seqs))
        return [{"p11": self._p(hr, s), "py": self._p(hr, s), "px": self._px(hr, s)} for s in seqs]

    def ytask(self, hr):
        self.c.inc("ytask_probes")
        return 0.97 if self.blk(hr.tid) <= self._moved(hr) else 0.02

    def y_end(self, row0, seqs):
        self.c.inc("yend_probes", len(seqs))
        out = []
        for s in seqs:
            m = {o for o, _ in s}
            out.append(0.97 if self.blk(0) <= m else 0.01 + 0.2 * len(self.blk(0) & m) / max(1, len(self.blk(0))))
        return out

    def y_noop(self, row0):
        return 0.01

    def x_chunk(self, hr, seq):
        return self._px(hr, seq)
