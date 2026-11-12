#!/usr/bin/env python3
"""P4 branch-local dynamic corrective search and the one-shot comparator (plan.md 6), shared by 2D and 3D.

Node = a HYPOTHETICAL ordered prefix r (never an executed state).  Expanding r: S_r = Edit(S0, r) (object poses only); for every movable object not
yet moved, the frozen sampler is RE-QUERIED on S_r (iterative) -- or, in the one-shot comparator, the destinations sampled once from S0 are reused
(minus cells no longer legal) -- giving children r + (o, d); every child is scored in one batch by the frozen X/Y scorer, which always receives the
ORIGINAL root, the whole ordered sequence and its endpoint.  Every prefix is a stopping candidate; expansion is fair best-first (every `fair`-th pop
is the oldest unexpanded node), so a low stopping score never prunes a prefix.  Static legality (F1, analytic): destination is a declared support
cell, free in S_r, not occupied in S0 (no slot swaps) and not the target's goal cell; each object moves at most once; |r| <= 3; the target never moves.
Selection = xy.choose (no-op gate, admission threshold eta, argmin -log p11 + alpha |r| + beta D + gamma J_hat); none admitted -> ABSTAIN.
No physical teacher is called here."""
from __future__ import annotations

import heapq, itertools, json, math, time
from pathlib import Path

import numpy as np
import torch

import placement as PL
import xy as XY


class Root:
    """Learner-visible root from a snapshot row (contracts.compile_domain): object cells, attributes, legal cells, target, goal."""

    def __init__(self, row, dom):
        inp = row["inputs"]
        self.row, self.dom, self.id = row, dom, row["root_id"]
        self.ids, self.tid, self.goal = inp["ids"], inp["tid"], int(inp["goal_cell"])
        self.cells0 = [int(c) for c in inp["cells0"]]
        self.legal = [int(c) for c in inp["legal_cells"]]
        a = inp["attrs"]
        fixed = [bool(x[3]) for x in a] if dom == "2d" else [False] * len(a)
        self.movable = [i for i in range(len(self.ids)) if i != self.tid and not fixed[i]]
        self.pattr = {self.ids[i]: ((x[0], x[3], 0.0, 0.0) if dom == "2d" else (x[0], x[1], x[2], x[3])) for i, x in enumerate(a)}
        self.cell_xy = inp["cell_xy"]

    def cells(self, seq):
        c = list(self.cells0)
        for i, d in seq:
            c[i] = int(d)
        return c

    def legal_dests(self, cells):
        occ0, occ = set(self.cells0), set(cells)
        return [d for d in self.legal if d not in occ and d not in occ0 and d != self.goal]

    def displacement(self, seq):
        """D(r): summed Euclidean object displacement in units of the cell pitch (analytic)."""
        pitch = 0.08 if self.dom == "2d" else 0.075
        return sum(math.dist(self.cell_xy[str(self.cells0[i])], self.cell_xy[str(d)]) for i, d in seq) / pitch


class Sampler:
    """Frozen placement sampler (P1 checkpoint or analytical control) behind one call: propose(root, cells, obj, M, gen)."""

    def __init__(self, dom, kind, seed, data_dir, device="cuda", raw_mult=8):
        sc = json.loads((Path(data_dir) / "scalers.json").read_text())
        self.mu, self.sd = np.array(sc["mean"], np.float32), np.array(sc["std"], np.float32)
        self.m, self.dom, self.dev, self.raw_mult, self.kind = PL.load(dom, kind, seed, device), dom, device, raw_mult, kind
        self.calls = self.raw = 0

    def propose(self, root, cells, obj, M, gen):
        cd = {root.ids[i]: c for i, c in enumerate(cells)}
        F, Mk, occ, _ = PL.scene_features(self.dom, root.pattr, cd, root.ids[obj], root.legal)
        leg = np.zeros(len(occ), bool)
        leg[root.legal_dests(cells)] = True
        if not leg.any():
            return []
        T = lambda a, dt: torch.as_tensor(a[None], dtype=dt, device=self.dev)  # noqa: E731
        F = (F - self.mu) / self.sd * Mk[:, None]
        out, raw, _ = PL.propose(self.m, T(F, torch.float32), T(Mk, torch.bool), T(occ, torch.float32), T(leg, torch.bool),
                                 torch.tensor([cells[obj]], device=self.dev), M, gen, self.raw_mult)
        self.calls += 1
        self.raw += raw
        return out[0]


class Scorer:
    """Frozen X/Y model (+ optional frozen travel head): p11, pY, pX and J_hat for many ordered sequences of one root in one batch."""

    def __init__(self, xy_ckpt, cost_ckpt=None, device="cuda"):
        self.net, self.dev = XY.load_model(xy_ckpt, device), device
        self.cost = XY.load_model(cost_ckpt, device) if cost_ckpt else None
        self.evals = 0

    @torch.no_grad()
    def score(self, root, seqs):
        inp = root.row["inputs"]
        P = lambda c: tuple(inp["cell_xy"][str(c)])  # noqa: E731
        xs = [[(i, P(d)) for i, d in s] for s in seqs if s]
        v, _, xm = XY.make_view(root.id, inp["xy0"], inp["attrs"], inp["tid"], inp["goal"], inp["base"], inp["ctx"], [], xs, XY._NoGeo)
        b, _ = XY.collate([v], device=self.dev, dtype=torch.float32)
        pr = self.net.predict(b)
        J = self.cost.predict(b)["J"] if self.cost is not None and len(xs) else None
        self.evals += len(xs)
        out, k = [], 0
        for s in seqs:
            if not s:
                out.append({"p11": float(pr["p_noop"][0]), "J": 0.0})
                continue
            q = xm[k]
            out.append({"p11": float(pr["psucc"][q]), "py": float(pr["py"][v["parent"][q]]) if "py" in pr else None,
                        "px": float(pr["px"][q]) if "px" in pr else None, "J": float(J[q]) if J is not None else 0.0})
            k += 1
        return out


def select(cands, rule):
    """Stopping rule (xy.choose): no-op gate, admission eta, argmin -log p11 + alpha |r| + beta D + gamma J_hat -> sequence or None (ABSTAIN)."""
    rows = [{"admissible": True, "m": c["m"], "p": c["p11"], "cd": c["D"], "J_hat": c["J"], "sig": json.dumps(c["seq"])} for c in cands]
    pick = XY.choose(rows, rule)
    return None if pick is None else json.loads(rows[pick]["sig"])


def search(root, sampler, scorer, cfg, mode="iterative"):
    """-> every examined candidate (stopping candidates incl. the no-op) with p11 / J_hat / m / D, and counters.  Expansion priority (search
    control) = -log p11 of the prefix + cfg['alpha_exp'] |r|, independent of the stopping rule applied afterwards by select().
    cfg: M, max_expansions, fair, seed, alpha_exp."""
    t0 = time.time()
    gen = torch.Generator(device=sampler.dev).manual_seed(int(cfg["seed"]))
    c0 = (sampler.calls, sampler.raw, scorer.evals)
    key = lambda s: tuple(s)  # noqa: E731
    noop = scorer.score(root, [[]])[0]
    nodes = {(): {"seq": [], **noop, "m": 0, "D": 0.0}}
    oneshot = {}
    if mode == "oneshot":                                                  # proposals from S0 only, once per object
        for o in root.movable:
            oneshot[o] = sampler.propose(root, root.cells0, o, cfg["M"], gen)
    cost = lambda n: -math.log(max(n["p11"], 1e-12)) + cfg.get("alpha_exp", 0.0) * n["m"]  # noqa: E731
    heap, fifo, order, exp, pops = [(cost(nodes[()]), 0, ())], [()], itertools.count(1), set(), 0
    while (heap or fifo) and len(exp) < cfg["max_expansions"]:
        pops += 1
        if cfg["fair"] and pops % cfg["fair"] == 0 and fifo:
            k = fifo.pop(0)
        else:
            k = heapq.heappop(heap)[2] if heap else fifo.pop(0)
        if k in exp or len(k) >= 3:
            continue
        exp.add(k)
        seq = [tuple(a) for a in k]
        cells = root.cells(seq)
        moved = {i for i, _ in seq}
        kids = []
        for o in root.movable:
            if o in moved:
                continue
            ok = set(root.legal_dests(cells))
            props = sampler.propose(root, cells, o, cfg["M"], gen) if mode == "iterative" else [d for d in oneshot[o] if d in ok]
            for d in props:
                ck = key(seq + [(o, int(d))])
                if ck not in nodes:
                    kids.append(ck)
        if not kids:
            continue
        sc = scorer.score(root, [list(c) for c in kids])
        for ck, s in zip(kids, sc):
            n = {"seq": [list(a) for a in ck], **s, "m": len(ck), "D": root.displacement(ck)}
            nodes[ck] = n
            heapq.heappush(heap, (cost(n), next(order), ck))
            fifo.append(ck)
    return {"root": root.id, "mode": mode, "cands": [{"seq": n["seq"], "p11": round(n["p11"], 6), "J": round(n["J"], 5), "m": n["m"],
                                                      "D": round(n["D"], 4)} for n in nodes.values()],
            "n_candidates": len(nodes), "expansions": len(exp), "sampler_calls": sampler.calls - c0[0], "raw_draws": sampler.raw - c0[1],
            "scorer_evals": scorer.evals - c0[2], "planner_calls": 0, "wall_s": round(time.time() - t0, 4)}
