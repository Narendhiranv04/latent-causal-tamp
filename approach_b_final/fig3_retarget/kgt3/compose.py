"""KGT3 scaling-only ordered-chunk composition (FIG3_KGT3_PREREG section 4).  Historical code paths (r24/order.py, rank.py) are untouched.

Notation: A = unordered assignment of (object, cell) actions, U = placed subset, S~_U = canonical ideal pose-edited scene (views.rebase; it
depends only on the SET U), q_ref at every chunk boundary.  A chunk C is an ordered tuple of 1..GMAX distinct actions of A minus U.
    e(U, B)  = min over orderings pi of B of  -log max(eps, pX(pi | S~_U, q_ref, original task))          (marginal X)
    F(empty) = 0,  F(V) = min over B in V, 1 <= |B| <= GMAX of  F(V - B) + e(V - B, B) (+ lam per extra chunk: historical control only)
    E(A)     = F(A) - log max(eps, Y_global(A))                                                            (primary: lam = 0)
State = (U, has_multi); for |A| > 3 the primary admissibility needs has_multi (>= 1 chunk of size >= 2).  Ordered backpointers are stored.
Tie-break everywhere: (round(E, 12), number of chunks, canonical JSON of the ordered chunks) -- no displacement / geometry term.
The grouped transition (unordered B, best internal permutation) equals the historical ordered-transition DP (r24/order.dp) for matched
constraints because the canonical scene after U is order-free (tested).  This is exact for the LEARNED energy only."""
from __future__ import annotations

import itertools, json, math

EPS = 1e-8
GMAX = 3
LAM_HIST = -math.log(0.92)          # historical R2.2 connector-compatibility penalty: a named control, never the primary score


def _t(C):
    return tuple(tuple(int(v) for v in a) for a in C)


def _key(v):
    return (round(v[0], 12), v[1], json.dumps([[list(a) for a in c] for c in v[2]]))


class Scores:
    """Batched, cached marginal-X readouts px(U, ordered chunk) on canonical scenes; shared across assignments of one root (same model).
    rebase(U) -> scene row; score(scene, [chunks]) -> [{"px": ...}].  Counts unique scores, scenes, batches."""

    def __init__(self, fz, row0, rebase, tick=None):
        self.fz, self.row0, self.rebase, self.tick = fz, row0, rebase, tick       # tick: deadline check before every model batch (R5.1)
        self.px, self.n = {}, {"x_unique": 0, "scenes": 0, "batches": 0, "requested": 0, "cache_hits": 0, "wall_s": 0.0}
        self.dp_lookups = 0

    def need(self, reqs):
        """reqs: iterable of (frozenset U, ordered chunk tuple); scores the missing ones grouped by U (one batch per scene).
        R4.0 accounting: requested (theoretical reads), cache_hits (already scored), x_unique (actual model evaluations), batches, wall_s."""
        import time
        t0, by = time.perf_counter(), {}
        for U, C in reqs:
            self.n["requested"] += 1
            if (U, C) not in self.px:
                by.setdefault(U, set()).add(C)
            else:
                self.n["cache_hits"] += 1
        for U in sorted(by, key=lambda u: json.dumps(sorted(u))):
            if self.tick:
                self.tick()
            Cs = sorted(by[U])
            S = self.rebase(self.row0, sorted([list(a) for a in U]))
            for C, x in zip(Cs, self.fz.score(S, [[list(a) for a in c] for c in Cs])):
                self.px[(U, C)] = x["px"]
            self.n["x_unique"] += len(Cs); self.n["scenes"] += 1; self.n["batches"] += 1
        self.n["wall_s"] += time.perf_counter() - t0

    def cost(self, U, C):
        return -math.log(max(EPS, self.px[(frozenset(_t(U)), _t(C))]))


def _pred(before):
    pred = {}
    for a, b in before:
        pred.setdefault(_t([b])[0], set()).add(_t([a])[0])
    return pred


def _ok(U, C, pred):
    seen = set(U)
    for a in C:
        if not pred.get(a, set()) <= seen:
            return False
        seen.add(a)
    return True


def requests(A, before=()):
    """Every (U, ordered chunk) the grouped DP over A can read (respecting precedence)."""
    A, pred, out = sorted(_t(A)), _pred(before), []
    for k in range(len(A)):
        for U in itertools.combinations(A, k):
            rem = [a for a in A if a not in U]
            for g in range(1, min(GMAX, len(rem)) + 1):
                for B in itertools.combinations(rem, g):
                    out += [(frozenset(U), p) for p in itertools.permutations(B) if not pred or _ok(U, p, pred)]
    return out


def grouped_dp(T, A, need_multi=None, lam=0.0, before=()):
    """Exact subset DP over unordered chunk memberships with the best internal permutation per chunk -> (F, order, partition) or None.
    need_multi default: True iff |A| > 3.  T: Scores with every requests(A) entry available."""
    A, pred = sorted(_t(A)), _pred(before)
    m = len(A)
    need_multi = m > 3 if need_multi is None else need_multi
    best = {(frozenset(), False): (0.0, 0, ())}
    for k in range(m):
        for (U, hm) in sorted([s for s in best if len(s[0]) == k], key=lambda s: (json.dumps(sorted(s[0])), s[1])):
            c0, n0, path = best[(U, hm)]
            rem = [a for a in A if a not in U]
            for g in range(1, min(GMAX, len(rem)) + 1):
                for B in itertools.combinations(rem, g):
                    perms = [p for p in itertools.permutations(B) if not pred or _ok(U, p, pred)]
                    if not perms:
                        continue
                    cp, p = min(((T.cost(U, p), p) for p in perms), key=lambda t: (round(t[0], 12), json.dumps(t[1])))
                    v = (c0 + cp + (lam if n0 else 0.0), n0 + 1, path + (p,))
                    s2 = (U | frozenset(B), hm or g >= 2)
                    if s2 not in best or _key(v) < _key(best[s2]):
                        best[s2] = v
    full = [best[s] for s in best if len(s[0]) == m and (s[1] or not need_multi)]
    if not full:
        return None
    F, n, path = min(full, key=_key)
    return F, [list(a) for c in path for a in c], [len(c) for c in path]


def fixed_order_dp(T, order, need_multi=None, lam=0.0):
    """Prefix-index DP over chunk boundaries of a FIXED order (Fig. 3A REC-ORDERED) with has_multi -> (F, order, partition) or None."""
    order = [tuple(int(v) for v in a) for a in order]
    m = len(order)
    need_multi = m > 3 if need_multi is None else need_multi
    best = {(0, False): (0.0, 0, ())}
    for i in range(m):
        for hm in (False, True):
            if (i, hm) not in best:
                continue
            c0, n0, path = best[(i, hm)]
            for g in range(1, min(GMAX, m - i) + 1):
                C = tuple(order[i:i + g])
                v = (c0 + T.cost(order[:i], C) + (lam if n0 else 0.0), n0 + 1, path + (C,))
                s2 = (i + g, hm or g >= 2)
                if s2 not in best or _key(v) < _key(best[s2]):
                    best[s2] = v
    full = [best[s] for s in best if s[0] == m and (s[1] or not need_multi)]
    if not full:
        return None
    F, n, path = min(full, key=_key)
    return F, [list(a) for c in path for a in c], [len(c) for c in path]


def fixed_requests(order):
    order = [tuple(int(v) for v in a) for a in order]
    return [(frozenset(order[:i]), tuple(order[i:i + g])) for i in range(len(order)) for g in range(1, min(GMAX, len(order) - i) + 1)]


def compositions(m):
    if m == 0:
        yield ()
        return
    for g in range(1, min(GMAX, m) + 1):
        for rest in compositions(m - g):
            yield (g,) + rest


def brute(T, A, need_multi=None, lam=0.0, before=(), fixed=None):
    """Reference: every order (or the fixed order) x every composition, same objective and tie-break."""
    A = sorted(_t(A)); m = len(A)
    need_multi = m > 3 if need_multi is None else need_multi
    pred, out = _pred(before), []
    orders = [tuple(_t(fixed))] if fixed is not None else itertools.permutations(A)
    for o in orders:
        if pred and not _ok((), o, pred):
            continue
        for part in compositions(m):
            if need_multi and max(part) < 2:
                continue
            E, i, path = 0.0, 0, ()
            for j, g in enumerate(part):
                E += T.cost(o[:i], o[i:i + g]) + (lam if j else 0.0); path += (tuple(o[i:i + g]),); i += g
            out.append((E, len(part), path))
    if not out:
        return None
    F, n, path = min(out, key=_key)
    return F, [list(a) for c in path for a in c], [len(c) for c in path]


def nx(m):
    """R4.0: theoretical ordered-chunk evaluations of the unrestricted grouped DP over ONE assignment of size m:
    N_X(m) = sum_{g=1..3} g! C(m, g) 2^(m-g)  (N_X(8) = 15,360).  Every (U, ordered chunk) with U a subset of A minus the chunk."""
    return sum(math.factorial(g) * math.comb(m, g) * 2 ** (m - g) for g in range(1, min(GMAX, m) + 1))


def distinct_requests(e):
    """R4.0: distinct (U, ordered chunk) readouts of an EXACT search over a pool whose partial assignments of size s number e[s] (s = 1..H):
    a readout depends only on the placed SET U and the ordered chunk C, so it is shared by every assignment containing U + C.
    = sum_s e[s] * sum_{g <= min(3, s)} C(s, g) g!   (upper bound on unique model evaluations under caching)."""
    return sum(e[s] * sum(math.comb(s, g) * math.factorial(g) for g in range(1, min(GMAX, s) + 1)) for s in e)


def counts(m):
    """Complexity of the grouped DP for |A| = m (no restrictions): states, unordered transitions, ordered local evaluations (exact counts)."""
    c = math.comb
    return {"states": 2 ** m, "states_with_multi_flag": 2 ** (m + 1),
            "unordered_transitions": sum(c(m, g) * 2 ** (m - g) for g in range(1, GMAX + 1)),
            "ordered_evaluations": nx(m), "full_orders": math.factorial(m),
            "full_orders_x_compositions": math.factorial(m) * sum(1 for _ in compositions(m))}
