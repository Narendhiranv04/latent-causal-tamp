"""R2.4 joint execution-order and chunk-partition optimizer over a FIXED unordered assignment A (R2.4A ordering-only; reused by R2.4B).

Canonical hypothetical prefix scene: views.rebase(row0, prefix) depends only on the SET of placed actions (cell level), so the search state
is the subset S of placed actions.  A transition S -> S + C for an ORDERED chunk C of 1..3 remaining actions costs
    c(S, C) = -log max(eps, pX(C | scene(S), q_ref, ORIGINAL task))
from the frozen coupled X/Y (marginal pX; full scene, every object kept, original target and goal).  Every intermediate home return adds the
declared penalty LAM = -log 0.92 (the R2.2 connector-compatibility rate in both domains), i.e. fewer returns are preferred; the partition
that is scored is the partition that is executed.  No partial original-task Y is used as a prefix gate (enablers need not raise Y).
Exact: subset DP over 2^m states == brute force over m! orders x compositions (tests).  `before` restricts orders to linear extensions of
a precedence relation (prerequisite-constrained mode)."""
from __future__ import annotations

import itertools, json, math

import views as V

EPS = 1e-8
LAM = -math.log(0.92)


def canon(S):
    return sorted([int(o), int(d)] for o, d in S)


def _t(C):
    return tuple(tuple(int(v) for v in a) for a in C)


class Table:
    """Lazy cache of local chunk readouts on canonical prefix scenes; one batched model call per prefix set."""

    def __init__(self, fz, row0, A, maxg=3):
        self.fz, self.row0, self.maxg = fz, row0, maxg
        self.A = sorted(_t(A))
        self.r, self.scenes = {}, 0

    def fill(self, S):
        S = frozenset(S)
        rem = [a for a in self.A if a not in S]
        todo = [list(map(list, p)) for g in range(1, min(self.maxg, len(rem)) + 1) for p in itertools.permutations(rem, g) if (S, p) not in self.r]
        if todo:
            for c, x in zip(todo, self.fz.score(V.rebase(self.row0, canon(S)), todo)):
                self.r[(S, _t(c))] = x
            self.scenes += 1

    def get(self, S, C):
        k = (frozenset(S), _t(C))
        if k not in self.r:
            self.fill(S)
        return self.r[k]

    def cost(self, S, C):
        return -math.log(max(EPS, self.get(S, C)["px"]))


def _vk(v):
    return (round(v[0], 12), v[1], json.dumps([[list(a) for a in c] for c in v[2]]))


def _ok(S, C, pred):
    seen = set(S)
    for a in C:
        if not pred.get(a, set()) <= seen:
            return False
        seen.add(a)
    return True


def _pred(before):
    pred = {}
    for a, b in before:
        pred.setdefault(_t([b])[0], set()).add(_t([a])[0])
    return pred


def dp(T, lam=LAM, before=(), min_chunks=1):
    """Exact subset DP -> (E, order, partition) or None.  E = sum chunk costs + lam * (chunks - 1).  Future costs depend only on the placed
    set, so keeping the best path per intermediate set is exact; complete plans are collected separately (min_chunks)."""
    A, m, pred = T.A, len(T.A), _pred(before)
    states, full = {frozenset(): (0.0, 0, ())}, []
    for k in range(m):
        for S in sorted([s for s in states if len(s) == k], key=lambda s: json.dumps(canon(s))):
            c0, n0, path = states[S]
            rem = [a for a in A if a not in S]
            for g in range(1, min(3, len(rem)) + 1):
                for C in itertools.permutations(rem, g):
                    if pred and not _ok(S, C, pred):
                        continue
                    v = (c0 + T.cost(S, C) + (lam if n0 else 0.0), n0 + 1, path + (C,))
                    S2 = S | set(C)
                    if len(S2) == m:
                        if v[1] >= min_chunks:
                            full.append(v)
                    elif S2 not in states or _vk(v) < _vk(states[S2]):
                        states[S2] = v
    if not full:
        return None
    E, n, path = min(full, key=_vk)
    return E, [list(a) for c in path for a in c], [len(c) for c in path]


def order_cost(T, order, part, lam=LAM):
    S, E, i = set(), 0.0, 0
    for j, g in enumerate(part):
        C = order[i:i + g]
        E += T.cost(S, C) + (lam if j else 0.0)
        S |= set(_t(C)); i += g
    return E


def best_partition_for(T, order, lam=LAM, min_chunks=1):
    """Best composition of a FIXED order (prefix-index DP) -> (E, partition)."""
    m = len(order)
    parts = [p for p in V.partitions(m) if len(p) >= min_chunks]
    return min(((order_cost(T, order, p, lam), p) for p in parts), key=lambda t: (round(t[0], 12), len(t[1]), t[1])) if parts else None


def brute(T, lam=LAM, before=(), min_chunks=1):
    """Exhaustive reference for dp (tests): every order x every composition."""
    pred, out = _pred(before), []
    for o in itertools.permutations(T.A):
        if pred and not _ok(set(), o, pred):
            continue
        for p in V.partitions(len(o)):
            if len(p) >= min_chunks:
                out.append((order_cost(T, list(o), p, lam), len(p), tuple(_t(o[sum(p[:j]):sum(p[:j + 1])]) for j in range(len(p)))))
    if not out:
        return None
    E, n, path = min(out, key=_vk)
    return E, [list(a) for c in path for a in c], [len(c) for c in path]


def all_orders(T, lam=LAM):
    """Every order with its best partition, sorted by E (order-recovery ranks)."""
    out = []
    for o in itertools.permutations(T.A):
        E, p = best_partition_for(T, list(o), lam)
        out.append({"order": [list(a) for a in o], "E": E, "partition": list(p)})
    return sorted(out, key=lambda r: (round(r["E"], 12), len(r["partition"]), json.dumps(r["order"])))


def pair_edges(fz, row0, A, delta=0.05):
    """Model-discovered pairwise prerequisites by retargeting (depth 1, inside A): d(a->b) = pY_temp(b | S0 + a) - pY_temp(b | S0), temporary
    task b = (object of b -> its destination), other destinations of A reserved.  Edge a->b iff d(a->b) > delta and d(a->b) > d(b->a);
    cycles broken by removing the weakest edge.  -> (edges [(a, b, d)], deltas)."""
    A = sorted(_t(A))
    y = {}
    for b in A:
        res = [d for o, d in A if (o, d) != b]
        y[(None, b)] = fz.p_noop(V.rebase(row0, [], task=list(b), reserved=res))
        for a in A:
            if a != b:
                y[(a, b)] = fz.p_noop(V.rebase(row0, [list(a)], task=list(b), reserved=[d for d in res if d != a[1]]))
    D = {(a, b): y[(a, b)] - y[(None, b)] for a in A for b in A if a != b}
    E = [(a, b, D[(a, b)]) for (a, b) in D if D[(a, b)] > delta and D[(a, b)] > D[(b, a)]]
    while True:
        cyc = _cycle([(a, b) for a, b, _ in E])
        if not cyc:
            break
        w = min((e for e in E if (e[0], e[1]) in cyc), key=lambda e: (e[2], json.dumps([e[0], e[1]])))
        E.remove(w)
    return [[list(a), list(b), d] for a, b, d in E], {json.dumps([list(a), list(b)]): v for (a, b), v in D.items()}


def _cycle(edges):
    g = {}
    for a, b in edges:
        g.setdefault(a, []).append(b)
    color, stack = {}, []

    def dfs(u):
        color[u] = 1; stack.append(u)
        for v in g.get(u, []):
            if color.get(v) == 1:
                i = stack.index(v)
                cyc = stack[i:] + [v]
                return {(cyc[j], cyc[j + 1]) for j in range(len(cyc) - 1)}
            if not color.get(v):
                r = dfs(v)
                if r:
                    return r
        color[u] = 2; stack.pop()
        return None
    for u in sorted(g):
        if not color.get(u):
            r = dfs(u)
            if r:
                return r
    return None


def kendall(o1, o2):
    """Normalized pairwise disagreement between two orders of the same action set (0 = identical, 1 = reversed)."""
    p1 = {_t([a])[0]: i for i, a in enumerate(o1)}; p2 = {_t([a])[0]: i for i, a in enumerate(o2)}
    ks = sorted(p1)
    pairs = [(a, b) for a, b in itertools.combinations(ks, 2)]
    return sum((p1[a] < p1[b]) != (p2[a] < p2[b]) for a, b in pairs) / len(pairs) if pairs else 0.0
