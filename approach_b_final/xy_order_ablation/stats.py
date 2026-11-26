#!/usr/bin/env python3
"""Small statistics helpers (protocol.json 'statistics'): discrimination / calibration metrics, within-root concordance, whole-family
bootstrap with equal-K-stratum weighting, paired family-level sign-flip randomization test, Holm."""
from __future__ import annotations

import collections, math

import numpy as np


def auroc(s, y):
    s, y = np.asarray(s, float), np.asarray(y, int)
    P, N = (y == 1).sum(), (y == 0).sum()
    if not P or not N:
        return None
    order = np.argsort(s, kind="mergesort")
    r = np.empty(len(s)); r[order] = np.arange(1, len(s) + 1)
    for v in np.unique(s):                                                 # average ranks for ties
        m = s == v
        r[m] = r[m].mean()
    return float((r[y == 1].sum() - P * (P + 1) / 2) / (P * N))


def auprc(s, y):
    s, y = np.asarray(s, float), np.asarray(y, int)
    if not (y == 1).any() or not (y == 0).any():
        return None
    o = np.argsort(-s, kind="mergesort")
    tp = np.cumsum(y[o] == 1)
    prec = tp / np.arange(1, len(y) + 1)
    return float((prec * (y[o] == 1)).sum() / (y == 1).sum())


def calib(s, y):
    s, y = np.clip(np.asarray(s, float), 1e-12, 1 - 1e-12), np.asarray(y, int)
    return {"n": int(len(y)), "prevalence": round(float(y.mean()), 4) if len(y) else None, "mean_score": round(float(s.mean()), 4) if len(y) else None,
            "auroc": auroc(s, y), "auprc": auprc(s, y), "brier": round(float(((s - y) ** 2).mean()), 5) if len(y) else None,
            "log_loss": round(float(-(y * np.log(s) + (1 - y) * np.log(1 - s)).mean()), 5) if len(y) else None}


def within_root(groups):
    """groups: {root: (family, [(score, label)])} -> root-balanced concordance over roots with both classes, family-cluster CI."""
    vals, fams = [], []
    for root, (fam, sl) in groups.items():
        pos = [s for s, l in sl if l == 1]
        neg = [s for s, l in sl if l == 0]
        if pos and neg:
            vals.append(float(np.mean([(p > n) + 0.5 * (p == n) for p in pos for n in neg]))); fams.append(fam)
    return cluster_mean(vals, fams)


def cluster_mean(vals, fams, n=4000, seed=0):
    if not vals:
        return None
    by = collections.defaultdict(list)
    for f, v in zip(fams, vals):
        by[f].append(v)
    cl = list(by.values())
    g = np.random.default_rng(seed)
    bs = [np.mean([x for i in g.integers(0, len(cl), len(cl)) for x in cl[i]]) for _ in range(n)]
    return {"mean": round(float(np.mean(vals)), 4), "ci95": [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
            "roots": len(vals), "families": len(cl)}


def strat_rate(rows):
    """rows: [(K, value 0/1)] -> mean over present strata of the stratum means (equal-K weighting)."""
    by = collections.defaultdict(list)
    for K, v in rows:
        by[K].append(v)
    return float(np.mean([np.mean(v) for v in by.values()])) if by else float("nan")


def paired(a, b, n_boot=4000, n_perm=20000, seed=0):
    """a, b: {root: (K, family, success 0/1)} over the same roots (UNKNOWN / UNQUERIED already 0 = not verified).
    -> equal-K-stratum weighted difference, whole-family bootstrap CI, family sign-flip randomization p (plus-one)."""
    roots = sorted(set(a) & set(b))
    fam = collections.defaultdict(list)
    for r in roots:
        fam[a[r][1]].append(r)
    F = list(fam.values())
    est = lambda fs: strat_rate([(a[r][0], a[r][2]) for f in fs for r in f]) - strat_rate([(a[r][0], b[r][2]) for f in fs for r in f])  # noqa: E731
    pt = est(F)
    g = np.random.default_rng(seed)
    bs = np.array([est([F[i] for i in g.integers(0, len(F), len(F))]) for _ in range(n_boot)])
    # sign flip: swapping arm labels within a family negates that family's paired differences
    K = [[a[r][0] for r in f] for f in F]
    da = [[a[r][2] for r in f] for f in F]
    db = [[b[r][2] for r in f] for f in F]

    def stat(flip):
        xa, xb = [], []
        for k, fa, fb, s in zip(K, da, db, flip):
            for kk, u, v in zip(k, fa, fb):
                xa.append((kk, v if s else u)); xb.append((kk, u if s else v))
        return strat_rate(xa) - strat_rate(xb)
    obs = abs(pt)
    hits = sum(abs(stat(g.integers(0, 2, len(F)).astype(bool))) >= obs - 1e-12 for _ in range(n_perm))
    va, vb = [a[r][2] for r in roots], [b[r][2] for r in roots]
    return {"n": len(roots), "families": len(F), "delta_pp": round(100 * pt, 2),
            "ci95_pp": [round(100 * float(np.percentile(bs, 2.5)), 2), round(100 * float(np.percentile(bs, 97.5)), 2)],
            "p_perm": (hits + 1) / (n_perm + 1), "wins": sum(x > y for x, y in zip(va, vb)), "losses": sum(x < y for x, y in zip(va, vb))}


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - r) * ps[i]))
        adj[i] = run
    return adj
