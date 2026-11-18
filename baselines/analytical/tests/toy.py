"""Toy fixture: a 4 x 4 grid scene with a deterministic fake physics behind the REAL PhysBase (caching, keys, budgets) and planners.

Row 0 is the target's route: t0 at cell 0, goal cell 3, blockers A (cell 1) and B (cell 2) on it, F fixed at 12, C a distractor at 10.
The achieved arm state after a relocation is 'near the last moved object', so the order of a prefix changes the carried q.  Knobs:
fail (set of (o, d) that fail), unknown (set of (o, d) that return UNKNOWN), conn_bad (last-moved objects from which the terminal
connector fails), y_ok(cells) (target feasible at the endpoint), burn_s (CPU seconds burnt per physical call)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from baselines.analytical.phys import PhysBase

IDS = ["t0", "A", "B", "F", "C"]
T, A, B, F, C = range(5)


def toy_row():
    cell_xy = {str(c): [(c % 4 + 0.5) * 0.1, (c // 4 + 0.5) * 0.1] for c in range(16)}
    attrs = [[0.02, 1.0, 0.0, 0.0], [0.02, 0.0, 1.0, 0.0], [0.02, 0.0, 1.0, 0.0], [0.02, 0.0, 0.0, 1.0], [0.02, 0.0, 1.0, 0.0]]
    cells0 = [0, 1, 2, 12, 10]
    inp = {"ids": IDS, "cells0": cells0, "xy0": [cell_xy[str(c)] for c in cells0], "attrs": attrs, "tid": 0, "goal_cell": 3,
           "goal": cell_xy["3"], "base": [0.2, -0.1], "ctx": [0.0] * 9, "grid": [4, 4], "legal_cells": list(range(16)),
           "q_ref": [0.0, 0.0, 0.0], "cell_xy": cell_xy}
    return {"root_id": "toy-0", "domain": "2d", "inputs": inp}


@dataclass
class S:
    cells: list
    prefix: list
    moved_mask: list
    q_t: list
    gripper_state: dict = field(default_factory=lambda: {"gap": 0.0})
    physics_payload: dict = field(default_factory=dict)


class ToyPhys(PhysBase):
    def __init__(self, row=None, fail=(), unknown=(), conn_bad=(), y_ok=None, burn_s=0.0, sweeps=({0, 1, 2, 3},), **kw):
        super().__init__(row or toy_row(), **kw)
        self.fail, self.unk, self.conn_bad, self.burn_s, self.sweeps = set(fail), set(unknown), set(conn_bad), burn_s, sweeps
        self.y_ok = y_ok or (lambda cells: not ({1, 2} & {c for i, c in enumerate(cells) if i != T}))
        self.y_endpoint = {}
        self.step_starts = []                                             # q at the start of every executed _step

    def _burn(self):
        t = time.process_time()
        while time.process_time() - t < self.burn_s:
            pass

    def _reset(self):
        return S(list(self.inp["cells0"]), [], [False] * 5, list(self.inp["q_ref"]))

    def _ident(self, s):
        return (tuple(s.cells), tuple(s.moved_mask), tuple(s.q_t), s.gripper_state["gap"])

    def _step(self, s, o, d):
        self._burn()
        self.step_starts.append(list(s.q_t))
        if (o, d) in self.unk:
            return "UNKNOWN"
        if (o, d) in self.fail:
            return None
        cells = list(s.cells)
        cells[o] = d
        mm = list(s.moved_mask)
        mm[o] = True
        return S(cells, list(s.prefix) + [(o, d)], mm, [float(o), float(d), 1.0])   # carried q: near the last moved object

    def _terminal(self, s):
        self._burn()
        if s.prefix:
            self.n["connector_calls"] += 1
            if int(s.q_t[0]) in self.conn_bad:
                return 0                                                  # X = 0: Y is skipped
        k = tuple(s.cells)                                                # Y keyed by the canonical endpoint (order independent)
        if k in self.y_endpoint:
            self.n["y_cache_hits"] += 1
        else:
            self.n["y_calls"] += 1
            self.y_endpoint[k] = int(self.y_ok(s.cells))
        return self.y_endpoint[k]

    def _ref_paths(self):
        return [{"sweep": set(sw), "hits": set(), "id": i} for i, sw in enumerate(self.sweeps)]
