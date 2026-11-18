"""Shared solver scaffolding: one committed decision per root, termination reasons, the common start step and the task check.

Every planner (i) plans the obstacle-ignorant target task once (several grasp homotopies; no verified plan -> ABSTAIN, the target cannot
reach its goal even with every movable removed), (ii) checks the task in the initial scene (NOOP if X = Y = 1 there; the papers' first
step), (iii) searches over physically executed relocations, and (iv) commits REPAIR only for a prefix whose search-time terminal check
(connector from the carried state + Y) returned success.  Budget exhaustion -> ABSTAIN with termination TIMEOUT; nothing is retried
after the independent final verification (benchmark.py, separate process + caches)."""
from __future__ import annotations

import collections
from dataclasses import dataclass, field

import numpy as np

from .contract import eligible
from .phys import Exhausted

COMMON = {"start_check": "always", "done_gate": "always", "t_paths": "planned"}
LINEAR_ID = 1000


@dataclass
class Decision:
    kind: str                                   # REPAIR | NOOP | ABSTAIN
    prefix: list = field(default_factory=list)  # [(object index, destination cell)]
    reason: str = ""
    termination: str = ""                       # SOLVED | EXHAUSTED | TIMEOUT
    stats: dict = field(default_factory=dict)


class Solver:
    name = "base"
    DEFAULTS: dict = {}

    def __init__(self, phys, seed: int = 0, **params):
        unknown = set(params) - set(COMMON) - set(self.DEFAULTS)
        assert not unknown, f"unknown hyperparameters {unknown}"
        self.ph, self.inp, self.dom = phys, phys.inp, phys.dom
        self.P = {**COMMON, **self.DEFAULTS, **params}
        self.rng = np.random.default_rng(seed)
        self.st = collections.Counter()

    # ------------------------------------------------------------------ driver
    def run(self) -> Decision:
        try:
            kind, prefix, reason = self.solve()
            if kind == "REPAIR" and not prefix:                            # the objective holds with no move
                kind, reason = "NOOP", reason + " (empty plan)"
            term = "SOLVED" if kind in ("REPAIR", "NOOP") else "EXHAUSTED"
        except Exhausted as e:
            kind, prefix, reason, term = "ABSTAIN", [], f"budget exhausted ({e.args[0] if e.args else ''})", "TIMEOUT"
        return Decision(kind, [tuple(map(int, p)) for p in prefix], reason, term, {"search": dict(self.st), "phys": self.ph.stats()})

    def start(self):
        """-> (s0, None) to search, or (s0, (kind, prefix, reason)) when the start step decides."""
        s0 = self.ph.reset()
        mode = self.P["t_paths"]
        assert mode in ("planned", "linear", "both"), mode
        self.paths = self.ph.ref_paths() if mode != "linear" else []
        if mode != "linear" and not self.paths:
            return s0, ("ABSTAIN", [], "no obstacle-ignorant target plan")
        if mode != "planned":
            self.paths = self.paths + [self.linear_path()]
        if self.P["start_check"] == "always" or self.clear(s0):
            self.st["start_checks"] += 1
            if self.ph.terminal(s0) == 1:
                return s0, ("NOOP", [], "task feasible in the initial scene")
        return s0, None

    def linear_path(self) -> dict:
        """T's LINEAR picking + placing paths (MS-MCTS's construction): segments robot base -> T and T -> goal, swept by T's disc."""
        g, tid = self.ph.geo, int(self.inp["tid"])
        t = g.xy(self.inp["cells0"][tid])
        sweep = g.seg_cells(g.base, t, g.rad[tid]) | g.seg_cells(t, np.asarray(self.inp["goal"], float), g.rad[tid])
        return {"sweep": sweep, "hits": set(), "id": LINEAR_ID}

    # ------------------------------------------------------------------ task-path screens (recomputed in every hypothetical scene)
    def elig(self, s) -> list[int]:
        return eligible(self.inp, self.dom, self.ph.prefix(s))

    def path_blockers(self, s) -> list[tuple[dict, set]]:
        """(path, blockers) for every reference path whose blockers can all still be moved, fewest blockers first."""
        el = set(self.elig(s))
        out = [(p, b) for p in self.paths for b in [self.ph.blockers(p, s)] if b <= el]
        return sorted(out, key=lambda x: (len(x[1]), x[0]["id"]))

    def clear(self, s) -> bool:
        return any(not self.ph.blockers(p, s) for p in self.paths)

    def done(self, s, gate=None) -> bool:
        """The task from this state (X terminal connector + Y).  gate 'screen': only when some reference path is already clear."""
        if (gate or self.P["done_gate"]) == "screen" and not self.clear(s):
            self.st["done_gated"] += 1
            return False
        self.st["done_checks"] += 1
        return self.ph.terminal(s) == 1

    def solve(self):
        raise NotImplementedError
