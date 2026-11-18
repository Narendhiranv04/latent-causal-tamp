"""MS-MCTS (Ren & Qureshi, arXiv 2305.17175) on the K<=3 repair benchmark (2D and 3D).  Only the target T has a goal, so the stage
topology has one stage: one SS-MCTS with object of interest o_k = T, discrete buffer regions (the paper's discrete-buffer variant).

Kept: Algorithm 2 expansion -- O_b = objects blocking T's picking/placing paths; an accessible blocker (free linear picking path) gets
buffer regions from Algorithm 1; an inaccessible one makes the objects on its picking path the focus with it as their dependency; the
halting condition moves the focus to the next round's inaccessible objects; after `stuck_depth` moves without fewer blockers of T, O_b =
every feasible object; O_b empty -> the goal child (T placed at its goal), verified by the motion planner (here the X+Y terminal check).
Algorithm 1: candidate regions sorted by distance to o_i, rejected on T's paths or on a dependency object's picking path, accepted when the
motion planner verifies the relocation (here: the physical transition from the node's carried state), at most m per call.  Selection =
tuned UCB (UCB1-Tuned) on rewards normalised to [0, 1]; expansion of visited leaves; simulation = rollout choosing a random region of
Algorithm 1 until T can be placed; reward = -(accumulated Euclidean relocation distance); back-propagation of visits and reward.
FIXES (legacy msmcts.py): a rollout that reaches the objective with a verified terminal check RETURNS its plan (legacy discarded it,
:179); transposition table keyed by physical state identity (one node per physical state, duplicate children merged); picking-path
queries cached per (scene, object) (legacy cached by object cell only, :64-67); destination sets are the legal ORIGINALLY-empty cells off
T's swept cells and dependency picking paths, the goal cell excluded, with m / tries as declared hyperparameters (config/grid.json);
fixed objects and moved objects are never candidates; commit length <= 3.
T's picking/placing paths: default the paper's LINEAR paths (base -> T, T -> goal; t_paths='linear'); 'planned' / 'both' add the
obstacle-ignorant target plans (several homotopies; the usable one with fewest movable blockers is T's path).
Adapted:
objects' linear picking paths = straight segment from the robot base (public geometry); continuous Gaussian buffer proposals -> cells."""
from __future__ import annotations

import math

import numpy as np

from .common import Solver
from .contract import K_MAX, legal_dests


class Node:
    __slots__ = ("state", "key", "seq", "children", "n", "w", "w2", "expanded", "dead")

    def __init__(self, state, key, seq):
        self.state, self.key, self.seq = state, key, list(seq)
        self.children, self.n, self.w, self.w2, self.expanded, self.dead = [], 0, 0.0, 0.0, False, False


class MSMCTS(Solver):
    name = "msmcts"
    DEFAULTS = {"m_regions": 2, "max_tries": 4, "stuck_depth": 2, "fail_r": 4.0, "t_paths": "linear"}

    # ------------------------------------------------------------------ paths (scene-aware)
    def t_path(self, s):
        pb = self.path_blockers(s)
        return pb[0] if pb else (None, None)

    def pick_blockers(self, s, o) -> list[int]:
        k = (tuple(self.ph.cells(s)), o)
        if k not in self._pick:
            self._pick[k] = self.ph.geo.pick_blockers(self.ph.cells(s), o)
            self.st["pick_path_queries"] += 1
        else:
            self.st["pick_path_cache_hits"] += 1
        return self._pick[k]

    def pick_sweep(self, s, o) -> set[int]:
        g = self.ph.geo
        return g.seg_cells(g.base, g.xy(self.ph.cells(s)[o]), g.rad[o])

    # ------------------------------------------------------------------ Algorithm 1
    def new_region(self, s, oi, deps, n_max, rollout=False):
        p, _ = self.t_path(s)
        banned = set(p["sweep"]) if p else set()
        for od in deps:
            banned |= self.pick_sweep(s, od)
        cells = self.ph.cells(s)
        cand = sorted((c for c in legal_dests(self.inp, cells) if c not in banned), key=lambda c: (self.ph.geo.dist(cells[oi], c), c))
        out = []
        for c in cand[:self.P["max_tries"]]:
            self.st["region_attempts"] += 1
            nxt = self.ph.step(s, oi, c)                                     # MP(p_i) from the node's carried state
            if nxt is not None:
                out.append((oi, c, nxt))
                if len(out) >= n_max:
                    break
        return out

    # ------------------------------------------------------------------ Algorithm 2
    def actions(self, s, n_max, goal=True):
        """-> ('goal', None) when O_b is empty, ('move', [(o, cell, next state)...]) or ('dead', None).  goal=False (the goal child was
        refuted by the terminal check): O_b falls back to every feasible object, the paper's no-progress rule."""
        p, tb = self.t_path(s)
        if goal and p is not None and not tb:
            return "goal", None
        el = set(self.elig(s))
        if not el:
            return "dead", None
        ob = sorted(tb or []) if p is not None else []
        if not ob or (len(self.ph.prefix(s)) >= self.P["stuck_depth"] and len(tb or ()) >= self.n_tb0):
            ob = sorted(el)                                                   # no progress / no usable T path: every feasible object
        g, cells = self.ph.geo, self.ph.cells(s)
        ob.sort(key=lambda o: (float(np.linalg.norm(g.xy(cells[o]) - g.base)), o))
        seen = set()
        while ob:
            nxt = []
            for oi in ob:
                seen.add(oi)
                pb = self.pick_blockers(s, oi)
                if not pb:                                                    # oi accessible
                    regs = self.new_region(s, oi, [], n_max)
                    if regs:
                        return "move", regs
                    continue
                for oj in [o for o in pb if o in el]:                          # objects blocking oi's picking path
                    if not self.pick_blockers(s, oj):
                        regs = self.new_region(s, oj, [oi], n_max)
                        if regs:
                            return "move", regs
                    elif oj not in seen:
                        nxt.append(oj)
            ob = list(dict.fromkeys(nxt))                                     # halting condition: next round's focus
        return "dead", None

    def node(self, state, seq):
        k = self.ph.key(state)
        if k in self.table:
            self.st["transpositions"] += 1
            return self.table[k]
        u = self.table[k] = Node(state, k, seq)
        self.st["nodes"] += 1
        return u

    def reward(self, seq) -> float:
        c0 = self.inp["cells0"]
        return -sum(self.ph.geo.dist(c0[o], c) for o, c in seq)

    def expand(self, nd):
        """-> the node itself when it achieves the objective, else None (children added)."""
        nd.expanded = True
        self.st["expansions"] += 1
        kind, acts = self.actions(nd.state, self.P["m_regions"])
        if kind == "goal":
            if self.done(nd.state, gate="always"):
                return nd
            self.st["goal_refuted"] += 1                                      # MP refutes T's placement: keep clearing
            kind, acts = self.actions(nd.state, self.P["m_regions"], goal=False)
        if kind == "dead":
            nd.dead = True
            return None
        for o, c, nxt in acts:
            ch = self.node(nxt, nd.seq + [(o, c)])
            if ch is not nd and ch not in nd.children:
                nd.children.append(ch)
        if not nd.children:
            nd.dead = True
        return None

    def simulate(self, nd):
        """Rollout of random Algorithm-1 regions until T can be placed. -> (reward in [-fail_r, 0], seq if the objective is achieved)."""
        s, seq = nd.state, list(nd.seq)
        for _ in range(K_MAX + 1):
            self.st["rollout_steps"] += 1
            kind, acts = self.actions(s, self.P["m_regions"])
            if kind == "goal":
                if self.done(s, gate="always"):
                    return self.reward(seq), seq
                self.st["goal_refuted"] += 1
                kind, acts = self.actions(s, self.P["m_regions"], goal=False)
            if kind == "dead":
                return -self.P["fail_r"], None
            o, c, s = acts[int(self.rng.integers(len(acts)))]
            seq.append((o, c))
        return -self.P["fail_r"], None

    def ucb(self, parent, c) -> float:
        if c.n == 0:
            return math.inf
        mean = c.w / c.n
        var = max(0.0, c.w2 / c.n - mean ** 2)
        lg = math.log(max(1, parent.n))
        return mean + math.sqrt(lg / c.n * min(0.25, var + math.sqrt(2 * lg / c.n)))

    def solve(self):
        s0, dec = self.start()
        if dec:
            return dec
        self.table, self._pick = {}, {}
        root = self.node(s0, [])
        self.n_tb0 = len(self.t_path(s0)[1] or ())
        while True:
            if root.dead:
                return "ABSTAIN", [], "tree exhausted"
            path, nd = [root], root
            while nd.expanded and not nd.dead:                                # selection
                live = [c for c in nd.children if not c.dead and c not in path]
                if not live:
                    nd.dead = True
                    break
                nd = max(live, key=lambda c: (self.ucb(path[-1], c), -len(c.seq), c.key))
                path.append(nd)
            if nd.dead:
                for p in reversed(path[:-1]):
                    if p.expanded and all(c.dead for c in p.children):
                        p.dead = True
                continue
            if nd.n > 0 or nd is root:                                        # expansion of a visited leaf
                if self.expand(nd) is not None:
                    return "REPAIR", nd.seq, "objective achieved"
                if nd.dead:
                    continue
                nd = nd.children[0]
                path.append(nd)
            r, plan = self.simulate(nd)
            if plan is not None:                                              # FIX: keep the successful rollout plan
                self.st["rollout_solutions"] += 1
                return "REPAIR", plan, "objective achieved in rollout"
            z = 1.0 + max(r, -self.P["fail_r"]) / self.P["fail_r"]
            for p in path:
                p.n += 1
                p.w += z
                p.w2 += z * z
