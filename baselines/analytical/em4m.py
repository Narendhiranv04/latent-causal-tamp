"""E-M4M (Saxena & Likhachev, ICAPS 2023, arXiv 2303.13385) Algorithm 1 on the K<=3 pick-and-place repair benchmark (2D and 3D).

Kept: gamma_OoI = the target task planned with every movable ignored (Line 28); NGR = its swept cells (Line 29); best-first search over
vertices; DONE(v) once per vertex (Lines 5-10, here the search-time X+Y terminal check); EXPANDSTATE(v) = MAPF over the NGR objects with
the invalid goals kappa(v) (Lines 13-14), every object moved by the MAPF solution tried once from v (Lines 18-24), a failed action adds its
goal to INVALIDGOALS(v) (Line 26), v re-expanded while new goals can be excluded (then the valid goals are 'hallucinated' invalid, then v
closes); negative cache = goals near invalid ones penalised; Naive-Bayes priority (phi1 NGR fraction occupied, phi2 objects in NGR).
Adapted (ADAPTATIONS.md): push -> one physically executed pick-and-place relocation (RepairEnv transition from the carried state); CBS ->
its optimal goal assignment (4-connected lattice distances around the other objects + negative-cache penalty, exact Hungarian); goals =
legal ORIGINALLY-empty cells outside the NGR (never the goal cell); phi3 (mass x friction) dropped (kinematic domains); K <= 3.
FIX (legacy em4m2d.py:186-192): vertices are keyed by PHYSICAL state identity (phys.key: cells + moved set + achieved q + gripper ...),
not by the sorted object cells; a successor with an existing key is the same physical state (safe transposition, dropped); successors
with the same cells but a different arm state are different vertices (no overwrite of q / seq)."""
from __future__ import annotations

import heapq
import itertools
import math
from dataclasses import dataclass, field

import numpy as np

from .common import Solver
from .contract import K_MAX, legal_dests
from .geo import hungarian

PRIOR, BETA_A, BETA_B, LAMBDA_NUM_OBJS = 0.3084358524, 0.3403101839, 45.0750087432, 1.5634743875   # mamo_search.cpp createDists()
COST_MULT, INVALID_W = 1000, 5
BIG = 10 ** 12


def beta_logpdf(x, a, b):
    return (a - 1) * math.log(x) + (b - 1) * math.log1p(-x) - (math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b))


@dataclass
class Vertex:
    state: object
    key: str
    seq: list
    priority: float = 0.0
    noops: int = 0
    closed: bool = False
    checked: bool = False
    invalid: dict = field(default_factory=dict)        # INVALIDGOALS(v): object -> {cell: failures}
    valid: set = field(default_factory=set)
    kappa: set | None = None
    version: int = 0


class EM4M(Solver):
    name = "em4m"
    DEFAULTS = {"ngr": "min", "box": 1, "transposition": "physical"}    # transposition 'cells_legacy' = the legacy defect (tests only)

    def vkey(self, s):
        return self.ph.key(s) if self.P["transposition"] == "physical" else str(sorted(enumerate(self.ph.cells(s))))

    def ngr_objects(self, s) -> list[int]:
        el = set(self.elig(s))
        b = set().union(*(self.ph.blockers(p, s) for p in self.gamma))
        return sorted(b & el)

    def priority(self, s) -> float:
        tid = int(self.inp["tid"])
        occ = [c for i, c in enumerate(self.ph.cells(s)) if i != tid and c in self.ngr]
        phi1 = len(occ) / max(1, len(self.ngr))
        if phi1 == 0:
            return math.inf
        x = min(max(phi1, 1e-12), 1 - 1e-12)
        phi2 = len(self.ngr_objects(s))
        return math.log(PRIOR) + beta_logpdf(x, BETA_A, BETA_B) + math.log(LAMBDA_NUM_OBJS) - LAMBDA_NUM_OBJS * phi2

    def push(self, v):
        v.version += 1
        heapq.heappush(self.open, (-v.priority, -len(v.seq), -v.noops, float(self.rng.random()), next(self.cnt), v.version, v))

    def top(self):
        while self.open:
            v, ver = self.open[0][-1], self.open[0][-2]
            if v.closed or ver != v.version:
                heapq.heappop(self.open)
                continue
            return v
        return None

    # ------------------------------------------------------------------ MAPF (CBS's optimal goal assignment)
    def next_kappa(self, v):
        if v.kappa is None:
            return set()
        inv = {(o, g) for o, gs in v.invalid.items() for g in gs}
        if inv - v.kappa:
            return v.kappa | inv
        if v.valid - v.kappa:
            self.st["hallucinated"] += len(v.valid - v.kappa)
            return v.kappa | inv | v.valid
        return None

    def penalty(self, v, o, kappa_o) -> dict:
        w = {c: INVALID_W * n for c, n in v.invalid.get(o, {}).items()}
        for c in kappa_o:
            w.setdefault(c, 1)
        rows, cols = self.inp["grid"]
        pen = {}
        for c, n in w.items():
            r0, k0 = divmod(c, cols)
            for dr in range(-self.P["box"], self.P["box"] + 1):
                for dk in range(-self.P["box"], self.P["box"] + 1):
                    d = math.hypot(dr, dk)
                    if d >= 1 and 0 <= r0 + dr < rows and 0 <= k0 + dk < cols:
                        q = (r0 + dr) * cols + k0 + dk
                        pen[q] = pen.get(q, 0.0) + n / math.ceil(d)
        return {c: math.ceil(p * COST_MULT) for c, p in pen.items()}

    def mapf(self, v, agents, kappa):
        cells = self.ph.cells(v.state)
        goals = [c for c in legal_dests(self.inp, cells) if c not in self.ngr]
        if len(goals) < len(agents):
            return None
        C = np.full((len(agents), len(goals)), BIG, dtype=float)
        for i, o in enumerate(agents):
            ko = {g for a, g in kappa if a == o}
            d = self.ph.geo.lattice_dist(cells[o], [c for j, c in enumerate(cells) if j not in agents])
            pen = self.penalty(v, o, ko)
            for j, g in enumerate(goals):
                if g in d and g not in ko:
                    C[i, j] = COST_MULT * d[g] + pen.get(g, 0)
        sol = hungarian(C)
        if any(C[i, j] >= BIG for i, j in sol):
            return None
        return {agents[i]: goals[j] for i, j in sol}

    # ------------------------------------------------------------------ search
    def expand(self, v):
        agents = self.ngr_objects(v.state)
        if len(v.seq) >= K_MAX or not agents:
            v.closed = True
            self.st["closed_no_moves"] += 1
            return
        kappa = self.next_kappa(v)
        if kappa is None:
            v.closed = True
            self.st["closed_no_new_goals"] += 1
            return
        sol = self.mapf(v, agents, kappa)
        v.kappa = kappa
        if sol is None:
            v.closed = True
            self.st["closed_no_mapf"] += 1
            return
        failed = False
        for o in agents:                                                   # Line 18: every object the MAPF solution moves
            g = sol[o]
            self.st["candidates"] += 1
            nxt = self.ph.step(v.state, o, g)                               # Lines 20-21: executed from v's carried state
            if nxt is None:                                                 # Line 26
                v.invalid.setdefault(o, {})[g] = v.invalid.get(o, {}).get(g, 0) + 1
                failed = True
                self.st["invalid_actions"] += 1
                continue
            self.st["valid_actions"] += 1
            v.valid.add((o, g))
            k = self.vkey(nxt)
            if k in self.vertices:                                          # same physical state reached by another order
                self.st["transpositions"] += 1
                continue
            u = Vertex(nxt, k, v.seq + [(o, g)], self.priority(nxt))
            self.vertices[k] = u
            self.push(u)
            self.st["generated"] += 1
        if failed:
            v.noops += 1
        self.push(v)

    def solve(self):
        s0, dec = self.start()
        if dec:
            return dec
        bl = self.path_blockers(s0) or [(p, self.ph.blockers(p, s0)) for p in self.paths]
        self.gamma = [p for p, _ in bl] if self.P["ngr"] == "union" else [bl[0][0]]
        self.ngr = set().union(*(p["sweep"] for p in self.gamma))
        self.open, self.cnt, self.vertices = [], itertools.count(), {}
        root = Vertex(s0, self.vkey(s0), [], self.priority(s0), checked=True)   # the start check is DONE(root)
        self.vertices[root.key] = root
        self.push(root)
        while True:
            v = self.top()
            if v is None:
                return "ABSTAIN", [], "OPEN exhausted"
            if not v.checked:
                v.checked = True
                if self.done(v.state):
                    return "REPAIR", v.seq, "done"
            heapq.heappop(self.open)
            self.st["expansions"] += 1
            self.expand(v)
