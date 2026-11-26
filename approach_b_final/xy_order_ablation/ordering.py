#!/usr/bin/env python3
"""Matched execution-order analysis (plan.md 5): same root, same canonical object->destination assignment, permutations only.

Per group: model scores of every scored order (pX1 primary; pX secondary; p11 ranks identically to pX1 at fixed pY > 0), strict X labels.
  concordance   mean over (X+, X-) order pairs of [s+ > s-] + 0.5 [s+ == s-]       (mixed groups only)
  learned top   argmax pX1, ties -> canonical order (lexicographic signature)        (score-independent tie rule)
  canonical     lexicographically smallest ordered signature (blind; also the Y-only tie-break family)
  random        analytic n(X=1) / m!  (fully decided groups), bounds [n1, n1 + n_unknown] / m! otherwise
  oracle        any X = 1 among the m! orders (upper bound, not a method)"""
from __future__ import annotations

import itertools, json, math

import numpy as np


def sig(seq):
    return json.dumps([[int(o), int(d)] for o, d in seq])


def all_orders(assignment):
    return [list(map(list, p)) for p in itertools.permutations(sorted(map(tuple, assignment)))]


def canonical(orders):
    return min(orders, key=sig)


def learned_top(orders, s):
    """orders: list of seqs; s: {sig: score}.  Highest score; exact ties broken by the canonical (lexicographic) signature."""
    return min(orders, key=lambda q: (-s[sig(q)], sig(q)))


def concordance(s, x):
    """s: {sig: score}, x: {sig: 0/1} over decided orders.  -> mean pairwise concordance or None if not mixed."""
    pos = [s[k] for k, v in x.items() if v == 1 and k in s]
    neg = [s[k] for k, v in x.items() if v == 0 and k in s]
    if not pos or not neg:
        return None
    return float(np.mean([(p > n) + 0.5 * (p == n) for p in pos for n in neg]))


def group(assignment, s, x):
    """One matched group.  s: {sig: score over ALL m! orders}, x: {sig: 0/1/None}.  -> metrics dict."""
    orders = all_orders(assignment)
    m = len(assignment)
    n = math.factorial(m)
    xs = [x.get(sig(q)) for q in orders]
    n1, n0, nu = xs.count(1), xs.count(0), sum(v is None for v in xs)
    top, can = learned_top(orders, s), canonical(orders)
    rng = [round(min(s.values()), 9), round(max(s.values()), 9)]
    return {"m": m, "n_orders": n, "n_pos": n1, "n_neg": n0, "n_unknown": nu, "complete": nu == 0, "mixed": n1 > 0 and n0 > 0,
            "score_range": rng, "top_differs_from_canonical": sig(top) != sig(can),
            "learned_x": x.get(sig(top)), "canonical_x": x.get(sig(can)),
            "random_x": n1 / n if nu == 0 else None, "random_bounds": [n1 / n, (n1 + nu) / n], "oracle_any": 1 if n1 else (0 if nu == 0 else None),
            "concordance": concordance(s, {k: v for k, v in zip(map(sig, orders), xs) if v is not None})}


def cluster_boot(values, clusters, n=4000, seed=0):
    """Mean with a cluster (family) bootstrap 95 % interval.  values: list of floats; clusters: list of ids (same length)."""
    v = [(c, x) for c, x in zip(clusters, values) if x is not None]
    if not v:
        return None
    by = {}
    for c, x in v:
        by.setdefault(c, []).append(x)
    cl = list(by.values())
    g = np.random.default_rng(seed)
    bs = []
    for _ in range(n):
        idx = g.integers(0, len(cl), len(cl))
        s = [x for i in idx for x in cl[i]]
        bs.append(np.mean(s))
    return {"mean": round(float(np.mean([x for _, x in v])), 4), "ci95": [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
            "n": len(v), "clusters": len(cl)}
