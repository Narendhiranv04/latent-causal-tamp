#!/usr/bin/env python3
"""Full original-root legal action domain + frozen S1 cVAE destination prior (plan.md 2.1-2.2).

  legal     A_legal = {(o, d): o movable non-target, d in Root.legal_dests(cells0)} -- public static rule (legal, not originally occupied,
            not goal), common to every object; derived from the public root, NEVER from the cVAE
  raw       frozen S1 Monte-Carlo marginal p_cvae(d | o, S0) over EVERY legal cell (placement.marginal, n_z = 64, the archived generator
            seed and batch) -- the exact tensor whose top-6 is the archived proposal list (asserted in run.py p0 / P2 parity)
  ranks     per object: archived top-6 order first (torch.topk on the same tensor), then every other legal cell by (-p, cell id)
  tiers     T4 = ranks 1-4, T56 = ranks 5-6, TTAIL = all other legal cells (including p = 0 / cells unseen by the MC draws)
  prior     pi(o, d) = (1 - eps) p_norm(d | o) / |O| + eps / |A_legal| -- expansion preference only, never a success estimate
No K, label, mask, teacher field or intermediate scene enters anything here."""
from __future__ import annotations

import math

TIER = {1: "T4", 2: "T56", 3: "TTAIL"}


class Domain:
    """raw = {obj: {dest: p}} over every legal dest (p may be 0); D6 = {obj: archived top-6 list}; eps = uniform-floor weight (1 = uniform)."""

    def __init__(self, raw, D6, eps=0.25):
        assert 0 < eps <= 1
        self.objs = sorted(int(o) for o in raw)
        self.L = sorted({int(d) for v in raw.values() for d in v})
        self.eps, self.D6 = eps, {int(o): [int(d) for d in D6.get(o, D6.get(str(o), []))] for o in self.objs}
        self.acts, self.rank, self.tier, self.raw, self.pi = [], {}, {}, {}, {}
        nA = sum(len(raw[o]) for o in raw)
        for o in self.objs:
            p = {int(d): float(v) for d, v in raw[o].items()}
            Z = sum(p.values())
            top = [d for d in self.D6[o] if d in p]
            assert len(top) == len(self.D6[o]), "archived proposal outside the public legal domain"
            rest = sorted((d for d in p if d not in set(top)), key=lambda d: (-p[d], d))
            for r, d in enumerate(top + rest):
                a = (o, d)
                self.acts.append(a); self.rank[a] = r; self.raw[a] = p[d]
                self.tier[a] = 1 if r < 4 else 2 if r < len(top) else 3
                pn = p[d] / Z if Z > 0 else 1.0 / len(p)
                self.pi[a] = (1 - eps) * pn / len(self.objs) + eps / nA
        self.acts.sort(key=lambda a: (self.tier[a], self.rank[a], a))

    def D(self, m):
        """Archived top-m pool {obj: [dest]} (m = 4: production EXACT4 pool, m = 6: EXACT6)."""
        return {o: v[:m] for o, v in self.D6.items() if v[:m]}

    def eligible(self, level):
        return [a for a in self.acts if self.tier[a] <= level]

    def n_pairs(self):
        """Exact number of legal unordered K2 sets over the FULL domain (analytic; nothing materialized)."""
        n, L = len(self.objs), len(self.L)
        return math.comb(n, 2) * L * (L - 1)

    def strata(self, A):
        """Rank stratum of a set: TOP4_ONLY / ONE_OFF4 / TWO_OFF4, and BEYOND6 if any action is in TTAIL."""
        off = sum(self.tier[a] > 1 for a in A)
        s = "TOP4_ONLY" if off == 0 else "ONE_OFF4" if off == 1 else "TWO_OFF4"
        return s + ("|BEYOND6" if any(self.tier[a] == 3 for a in A) else "")


def cvae_raw(root, samp, seed=0, n_z=64):
    """Frozen S1 marginal for every movable object of the ORIGINAL root, built exactly as search.Sampler.propose_many builds its single
    batched placement call (same features, scalers, task context, legal mask, object order, CUDA generator seed) -> (raw, D6, decoder evals).
    D6 = torch.topk of the same log-marginal exactly as placement.propose_rule(S1) (parity asserted against exhaustive.proposals)."""
    import numpy as np
    import torch
    import placement as PL
    objs, cells = list(root.movable), root.cells0
    legal = root.legal_dests(cells)
    if not objs or not legal:
        return {o: {} for o in objs}, {o: [] for o in objs}, 0
    cd = {root.ids[i]: c for i, c in enumerate(cells)}
    Fs, Ms, Os, Ls = [], [], [], []
    for o in objs:
        F, Mk, occ, _ = PL.scene_features(samp.dom, root.pattr, cd, root.ids[o], root.legal)
        lg = np.zeros(len(occ), bool); lg[legal] = True
        if isinstance(samp.m, PL.TaskCVAE):
            occ = np.concatenate([occ, PL.task_features(samp.dom, root.row["inputs"], cells, o, getattr(samp.m, "task_on", True))])
        Fs.append((F - samp.mu) / samp.sd * Mk[:, None]); Ms.append(Mk); Os.append(occ); Ls.append(lg)
    T = lambda a, dt: torch.as_tensor(np.stack(a), dtype=dt, device=samp.dev)  # noqa: E731
    gen = torch.Generator(device=samp.dev).manual_seed(seed)
    lgm = T(Ls, torch.bool)
    p, ev = PL.marginal(samp.m, T(Fs, torch.float32), T(Ms, torch.bool), T(Os, torch.float32), lgm, torch.tensor([cells[o] for o in objs], device=samp.dev), n_z, gen)
    lg = torch.where(lgm & (p > 0), p.clamp(min=1e-30).log(), torch.full_like(p, -float("inf")))
    val, idx = lg.topk(min(6, lg.shape[1]), -1)
    D6 = {o: [int(d) for d, v in zip(ix, vv) if v > -float("inf")] for o, ix, vv in zip(objs, idx.tolist(), val.tolist())}
    pc = p.double().cpu().numpy()
    raw = {o: {int(d): float(pc[j, d]) for d in legal} for j, o in enumerate(objs)}
    return raw, D6, ev * len(objs)
