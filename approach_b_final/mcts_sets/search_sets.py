#!/usr/bin/env python3
"""Original-root unordered-set search for K<=2 corrective repairs (plan.md 2-3).  Model-agnostic core: the frozen X/Y scorer is injected as
`score_fn(list of ordered sequences) -> list of {"p11", "py", "px"}`; every model input is the ORIGINAL root plus a COMPLETE ordered candidate.

  Pool      frozen per-object destination lists D (cVAE top-M from S0), canonical unordered assignments (sorted (obj, dest) tuples), legality
  Budget    unique ordered X/Y evaluations INCLUDING the no-op, charged before scoring; a set is scored all-orders-or-nothing (never one of two)
  arms      EXACT_K2 (all sets), RAND_SET (seeded uniform without replacement), BEAM_SET (singleton scan -> top-w beam -> pair expansion),
            UCT_SET / PW_UCT_SET (MCTS over canonical sets: ADD edges, explicit STOP, UCT, optional progressive widening)
  select    the frozen xy.choose rule (no-op gate, admission eta, argmin key with deterministic ties) over every FULLY scored ordered candidate
MCTS insertion order is never an execution order: a STOP scores every permutation of the set and the X/Y energy alone picks the order.
No physical teacher, IK, motion planner or intermediate-scene model call exists anywhere in this module."""
from __future__ import annotations

import hashlib, itertools, json, math, random, time


def h64(*a):
    return int(hashlib.sha256("|".join(map(str, a)).encode()).hexdigest()[:16], 16)


class Pool:
    """Frozen proposals D = {obj: [dest, ...]} (already legal at S0); K <= kmax unordered assignments with distinct objects and destinations."""

    def __init__(self, D, kmax=2):
        self.D = {int(o): [int(d) for d in v] for o, v in D.items() if v}
        self.objs, self.kmax = sorted(self.D), kmax
        self.rank = {(o, d): i for o, v in self.D.items() for i, d in enumerate(v)}

    def actions(self):
        return [(o, d) for o in self.objs for d in self.D[o]]

    def sets(self):
        """Every legal assignment of size 1..kmax exactly once, in construct.assignments order."""
        for k in range(1, self.kmax + 1):
            for objs in itertools.combinations(self.objs, k):
                for ds in itertools.product(*(self.D[o] for o in objs)):
                    if len(set(ds)) == k:
                        yield tuple(zip(objs, ds))

    @staticmethod
    def canon(A):
        return tuple(sorted(A))

    @staticmethod
    def legal_add(A, a):
        return all(a[0] != o and a[1] != d for o, d in A)


class Oracle:
    """Budgeted, cached scorer.  Charges each UNIQUE ordered sequence once (the no-op included) and never scores a set partially."""

    def __init__(self, score_fn, budget, disp=None):
        self.f, self.B, self.disp = score_fn, budget, disp or (lambda s: 0.0)
        self.cache, self.sets = {}, {}
        self.n = {"scored": 0, "batches": 0, "cache_hits": 0, "sets_scored": 0, "blocked": 0}
        self.noop = self._score([()])[0]

    def left(self):
        return math.inf if self.B is None else self.B - self.n["scored"]

    def _score(self, seqs):
        out = self.f([list(map(list, s)) for s in seqs]); self.n["batches"] += 1; self.n["scored"] += len(seqs)
        for s, r in zip(seqs, out):
            self.cache[s] = r
        return out

    def eval_set(self, A):
        """-> reward max_r p11(r) over all orders of A (search guidance only), or None if the budget cannot cover every unscored order."""
        A = Pool.canon(A)
        if A in self.sets:
            self.n["cache_hits"] += 1
            return self.sets[A]
        orders = list(itertools.permutations(A))
        todo = [r for r in orders if r not in self.cache]
        if len(todo) > self.left():
            self.n["blocked"] += 1
            return None
        if todo:
            self._score(todo)
        self.n["sets_scored"] += 1
        self.sets[A] = max(self.cache[r]["p11"] for r in orders)
        return self.sets[A]

    def candidates(self):
        """Every fully scored ordered candidate + the no-op, in the xy.choose row format."""
        rows = [{"seq": [], "p11": self.noop["p11"], "m": 0, "D": 0.0}]
        for A in self.sets:
            for r in itertools.permutations(A):
                rows.append({"seq": [list(x) for x in r], "p11": self.cache[r]["p11"], "py": self.cache[r].get("py"), "px": self.cache[r].get("px"),
                             "m": len(r), "D": self.disp(r)})
        return rows


def choose(rows, rule):
    """Frozen xy.choose semantics (no-op gate, eta admission, argmin (round(-log p + a m + b D, 12), m, D, signature)); None = ABSTAIN."""
    noop = rows[0]
    if rule.get("noop_gate") is not None and noop["p11"] >= rule["noop_gate"]:
        return noop
    pool = [r for r in rows if r["p11"] >= rule["eta"]]
    if not pool:
        return None
    cost = lambda r: -math.log(max(r["p11"], 1e-12)) + rule["alpha"] * r["m"] + rule["beta"] * r["D"]  # noqa: E731
    return min(pool, key=lambda r: (round(cost(r), 12), r["m"], r["D"], json.dumps(r["seq"])))


# ------------------------------------------------------------------------------------------------------------------------------ arms
def exact(pool, O, **_):
    for A in pool.sets():
        if O.eval_set(A) is None:
            return "BUDGET"
    return "EXHAUSTED"


def rand_set(pool, O, seed=0, key="", **_):
    S = list(pool.sets()); random.Random(h64("RAND", key, seed)).shuffle(S)
    for A in S:
        if O.left() < 1:
            return "BUDGET"
        O.eval_set(A)
    return "EXHAUSTED"


def beam_set(pool, O, w=8, **_):
    """Level 1: every singleton in (cVAE rank, object) order; keep the top-w by p11 (ties: rank, signature); level 2: every legal pair that
    extends a beam singleton, beam order then (rank, object).  Weakness (declared): a singleton with poor Y can be pruned from the beam."""
    singles = sorted(pool.actions(), key=lambda a: (pool.rank[a], a))
    got = []
    for a in singles:
        r = O.eval_set((a,))
        if r is None:
            return "BUDGET"
        got.append((r, a))
    beam = [a for r, a in sorted(got, key=lambda t: (-t[0], pool.rank[t[1]], t[1]))[:w]]
    for a in beam:
        for b in singles:
            if b != a and Pool.legal_add((a,), b):
                if O.eval_set((a, b)) is None:
                    return "BUDGET"
    return "EXHAUSTED"


class Node:
    __slots__ = ("A", "kids", "untried", "N", "W", "done", "stop")

    def __init__(self, A, untried, stop=False):
        self.A, self.kids, self.untried, self.N, self.W, self.done, self.stop = A, [], untried, 0, 0.0, False, stop


def uct(pool, O, seed=0, key="", c=0.5, pw=None, max_iter=None, **_):
    """MCTS over canonical unordered sets.  Canonical expansion follows a seeded object permutation pi (each set has exactly one tree path):
    children of A add (o, d) with pi(o) > pi(every object in A) and d unused; every non-empty A has an explicit STOP child (terminal) and a
    |A| = kmax node is terminal itself.  Reward = max p11 over the set's orders (terminal predictor, NOT an upper bound for descendants).
    pw = (k, alpha): at most floor(k * max(N, 1) ** alpha) expanded children per node.  Stops on BUDGET, EXHAUSTED or the iteration guard."""
    rng = random.Random(h64("UCT", key, seed))
    pi = {o: i for i, o in enumerate(rng.sample(pool.objs, len(pool.objs)))}

    def moves(A):
        top = max((pi[o] for o, _ in A), default=-1)
        m = [a for a in pool.actions() if pi[a[0]] > top and Pool.legal_add(A, a)] if len(A) < pool.kmax else []
        rng.shuffle(m)
        return (["STOP"] if A else []) + m if len(A) < pool.kmax else []

    root = Node((), moves(()))
    max_iter = max_iter or 50 * (O.B or 10 ** 5) + 1000
    it = 0
    while it < max_iter:
        it += 1
        if root.done:
            return "EXHAUSTED", it, root
        node, path = root, [root]
        while True:                                                     # selection / expansion
            terminal = node.stop or len(node.A) == pool.kmax
            if terminal:
                break
            cap = math.inf if pw is None else max(1, math.floor(pw[0] * max(node.N, 1) ** pw[1]))
            live = [k for k in node.kids if not k.done]
            if node.untried and (len(node.kids) < cap or not live):    # widening cap never blocks a node whose expanded kids are all done
                mv = node.untried.pop()
                child = Node(node.A, [], stop=True) if mv == "STOP" else Node(Pool.canon(node.A + (mv,)), [])
                if not child.stop:
                    child.untried = moves(child.A)
                node.kids.append(child); node = child; path.append(node)
                if child.stop or len(child.A) == pool.kmax:
                    break
                continue                                                # an ADD child is not evaluated: keep descending to a terminal
            live = [k for k in node.kids if not k.done]
            if not live:
                node.done = True
                break
            lnp = math.log(node.N + 1)
            node = max(live, key=lambda k: (k.W / k.N if k.N else math.inf) + c * math.sqrt(lnp / (k.N + 1)))
            path.append(node)
        if node.done and not (node.stop or len(node.A) == pool.kmax):
            for n in reversed(path[:-1]):                               # propagate exhaustion upward
                n.done = not n.untried and all(k.done for k in n.kids)
            continue
        r = O.eval_set(node.A)
        if r is None:                                                   # cannot afford all orders: terminal blocked for good
            node.done = True
            if O.left() < 1:
                return "BUDGET", it, root
            r = 0.0
        else:
            node.done = True                                            # terminal value is deterministic: never re-scored
        for n in path:
            n.N += 1; n.W += r
        for n in reversed(path[:-1]):
            n.done = not n.untried and all(k.done for k in n.kids)
        if O.left() < 1:
            return "BUDGET", it, root
    return "ITER_GUARD", it, root


ARMS = {"EXACT_K2": exact, "RAND_SET": rand_set, "BEAM_SET": beam_set, "UCT_SET": uct, "PW_UCT_SET": uct}


def run_arm(arm, D, score_fn, budget, rule, key, seed=0, disp=None, params=None):
    """One arm on one root -> decision record with every counter.  `key` = public root id (seeds the arm's PRNG only)."""
    t0 = time.perf_counter(); pool = Pool(D); O = Oracle(score_fn, budget, disp)
    out = ARMS[arm](pool, O, seed=seed, key=key, **(params or {}))
    stop, iters = (out[:2] if isinstance(out, tuple) else (out, None))
    pick = choose(O.candidates(), rule)
    dec = "ABSTAIN" if pick is None else "NOOP" if pick["seq"] == [] else "REPAIR"
    n_sets = sum(1 for _ in pool.sets())
    return {"arm": arm, "budget": budget, "seed": seed, "decision": dec, "seq": None if pick is None else pick["seq"],
            "p11": None if pick is None else pick["p11"], "p_noop": O.noop["p11"], "stop": stop, "iterations": iters,
            "best_reward": max(O.sets.values(), default=None), **O.n, "pool_sets": n_sets,
            "pool_ordered": sum(math.factorial(len(A)) for A in pool.sets()) + 1, "wall_s": round(time.perf_counter() - t0, 6)}
