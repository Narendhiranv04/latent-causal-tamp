#!/usr/bin/env python3
"""Full-legal-domain unordered K<=2 set search (plan.md v1.1 2.2-3.4).  Model-agnostic: the frozen X/Y scorer is injected as
score_fn(list of ordered sequences) -> [{"p11", "py", "px"}]; every call is the ORIGINAL root + COMPLETE ordered candidates.

  Oracle    budgeted cache: charges every UNIQUE ordered sequence once (no-op included), scores a set all-orders-or-nothing, batches many
            sets into one scorer call, logs (set, charge-at-scoring, batch) for allocation plots; hard limits on scores and batches
  Stage     action eligibility: FULL = every legal action from the start; SEEDED4 = T4 -> +T56 at f56 -> +TTAIL at ftail of the non-noop
            budget ((scored - 1) / (B - 1), inclusive >=), or immediately (no charge) when the eligible space is exhausted
            (EARLY_TIER_EXHAUSTION); never driven by a score, K, label or teacher
  Frontier  one priority list (frozen prior + seeded Gumbel noise => every eligible action has positive probability of coming first)
            with tier deferral: ineligible actions are parked and re-offered, in priority order, once their tier unlocks
  arms      EXACT (all sets of a pool), RAND (uniform legal sets, K1/K2 stratified), BEAM (singleton stream + beam extensions + direct-pair
            stream), MCTS (transposition DAG over canonical sets, explicit STOP, UCT + progressive widening, virtual-loss batches,
            same direct-pair stream); BEAM / MCTS take the same Stage (SEEDED4 or FULL) and the same direct-pair quota q_dir
  select    frozen xy.choose (mcts_sets.search_sets.choose == xy.choose, tested) over every fully scored ordered candidate + no-op
ADD order is never an execution order: a set is scored in every permutation and X/Y alone orders it.  No teacher, IK, planner, K or label."""
from __future__ import annotations

import collections, hashlib, itertools, math, time
from pathlib import Path

import numpy as np

def _frozen_search_sets():
    """The completed study's search_sets.py, loaded by explicit path (never via sys.path: mcts_sets/run.py would shadow this run.py)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("mcts_search_sets", Path(__file__).resolve().parent.parent / "mcts_sets" / "search_sets.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


_SS = _frozen_search_sets()
Pool, choose = _SS.Pool, _SS.choose                     # frozen K<=2 grammar enumeration + frozen xy.choose semantics (tested == xy.choose)


def h64(*a):
    return int(hashlib.sha256("|".join(map(str, a)).encode()).hexdigest()[:16], 16)


def canon(A):
    return tuple(sorted(A))


def legal_add(A, a):
    return all(a[0] != o and a[1] != d for o, d in A)


class Oracle:
    def __init__(self, score_fn, budget, disp=None, max_batches=None, max_wall=None):
        self.f, self.B, self.disp, self.maxb = score_fn, budget, disp or (lambda s: 0.0), max_batches
        self.deadline = None if max_wall is None else time.perf_counter() + max_wall
        self.cache, self.sets, self.log, self.bs = {}, {}, [], []
        self.n = collections.Counter()
        self.noop = self._score([()], limits=False)[0]                  # the no-op token is always scored (charged, never refused)

    def left(self):
        return math.inf if self.B is None else self.B - self.n["scored"]

    def frac(self):
        return 0.0 if self.B is None else (self.n["scored"] - 1) / max(self.B - 1, 1)

    def _score(self, seqs, limits=True):
        if limits and self.maxb is not None and self.n["batches"] >= self.maxb:
            raise BudgetStop("BATCH_LIMIT")
        if limits and self.deadline is not None and time.perf_counter() > self.deadline:
            raise BudgetStop("WALL_LIMIT")
        out = self.f([list(map(list, s)) for s in seqs])
        assert len(out) == len(seqs)
        self.n["batches"] += 1; self.n["scored"] += len(seqs); self.bs.append(len(seqs))
        for s, r in zip(seqs, out):
            self.cache[s] = r
        return out

    def eval_many(self, As):
        """Score every set of As that fits (all orders or nothing; in the given order) in ONE scorer call -> {A: R(A) or None}."""
        todo, seqs, want, res = [], [], set(), {}
        for A in map(canon, As):
            if A in self.sets or A in res:
                self.n["cache_hits"] += 1; res[A] = self.sets.get(A); continue
            new = [r for r in itertools.permutations(A) if r not in self.cache and r not in want]
            if len(seqs) + len(new) > self.left():
                self.n["blocked"] += 1; res[A] = None; continue
            todo.append(A); seqs += new; want.update(new); res[A] = None
        n0 = self.n["scored"]
        if seqs:
            self._score(seqs)
        b = self.n["batches"]
        for A in todo:
            self.sets[A] = res[A] = max(self.cache[r]["p11"] for r in itertools.permutations(A))
            self.n["sets_scored"] += 1; self.log.append((A, n0, b))          # n0 = charge when this batch was assembled
        return res

    def candidates(self):
        rows = [{"seq": [], "p11": self.noop["p11"], "m": 0, "D": 0.0}]
        for A in self.sets:
            for r in itertools.permutations(A):
                rows.append({"seq": [list(x) for x in r], "p11": self.cache[r]["p11"], "py": self.cache[r].get("py"),
                             "px": self.cache[r].get("px"), "m": len(r), "D": self.disp(r)})
        return rows


class BudgetStop(Exception):
    pass


class Stage:
    def __init__(self, dom, O, sched=None):
        self.tier, self.O, self.sched = dom.tier, O, sched
        self.level = 3 if sched is None else 1
        self.events = [] if sched is None else [(1, O.n["scored"], "START")]

    def update(self):
        if self.sched is None:
            return False
        f = self.O.frac(); t = 1 + (f >= self.sched[0]) + (f >= self.sched[1])
        if t > self.level:
            self.level = t; self.events.append((t, self.O.n["scored"], "BUDGET_FRACTION")); return True
        return False

    def early(self):
        if self.level >= 3:
            return False
        self.level += 1; self.events.append((self.level, self.O.n["scored"], "EARLY_TIER_EXHAUSTION")); return True

    def ok(self, a):
        return self.tier[a] <= self.level


class Frontier:
    """Priority list with tier deferral.  pop(level) -> next eligible action in priority order (deferred ones first: they precede ptr)."""
    __slots__ = ("seq", "tier", "ptr", "defer")

    def __init__(self, seq, tier):
        self.seq, self.tier, self.ptr, self.defer = seq, tier, 0, {2: collections.deque(), 3: collections.deque()}

    def _next(self, level, take):
        c = [(self.defer[t][0], t) for t in (2, 3) if t <= level and self.defer[t]]
        if c:
            pos, t = min(c)
            if take:
                self.defer[t].popleft()
            return self.seq[pos]
        while self.ptr < len(self.seq):
            a = self.seq[self.ptr]; t = self.tier[a]
            if t <= level:
                if take:
                    self.ptr += 1
                return a
            self.defer[t].append(self.ptr); self.ptr += 1
        return None

    def pop(self, level):
        return self._next(level, True)

    def peek(self, level):
        return self._next(level, False)


def priority(dom, rng, acts=None):
    """Frozen-prior Gumbel order: argsort(log pi + G).  Every action has positive probability of every position (nonzero exploration)."""
    acts = dom.acts if acts is None else acts
    k = np.log([dom.pi[a] for a in acts]) + rng.gumbel(size=len(acts))
    return [acts[i] for i in np.argsort(-k, kind="stable")]


def direct_pair(dom, stage, rng, O, busy, tries=32):
    """Direct pair proposal from the eligible prior product (does NOT depend on any singleton score)."""
    el = [a for a in dom.acts if stage.ok(a)]
    if len(el) < 2:
        return None
    p = np.array([dom.pi[a] for a in el]); p /= p.sum()
    for _ in range(tries):
        i, j = rng.choice(len(el), 2, replace=False, p=p)
        A = canon((el[i], el[j]))
        if legal_add((el[i],), el[j]) and A not in O.sets and A not in busy:
            return A
    return None


def progress(O, batch):
    """Score a batch; False = nothing new could be paid for while < 2 units remain (only pairs were left: stop, never spin)."""
    n0 = O.n["scored"]; O.eval_many(batch)
    return O.n["scored"] > n0 or O.left() >= 2


# ------------------------------------------------------------------------------------------------------------------------------------ arms
def exact(dom, O, pool=None, chunk=2048, **_):
    """Every legal set of `pool` ({obj: [dest]}, default the full domain) in construct.assignments order, batched."""
    pool = pool or {o: [d for (oo, d) in dom.acts if oo == o] for o in dom.objs}
    buf = []
    for A in Pool(pool).sets():
        buf.append(A)
        if len(buf) >= chunk:
            if any(v is None for v in O.eval_many(buf).values()):
                return "BUDGET"
            buf = []
    if buf and any(v is None for v in O.eval_many(buf).values()):
        return "BUDGET"
    return "EXHAUSTED"


def rand(dom, O, rng, nb=16, **_):
    """Uniform legal sets over the FULL domain, K1 / K2 strata alternated (one each per draw pair), no prior, batched."""
    acts = dom.acts; n1 = len(acts); busy = set()
    while O.left() >= 1:
        batch = []
        for j in range(nb):
            for _ in range(64):
                if j % 2 == 0:
                    A = (acts[rng.integers(n1)],)
                else:
                    i, k = rng.choice(n1, 2, replace=False); A = canon((acts[i], acts[k]))
                    if not legal_add((acts[i],), acts[k]):
                        continue
                if A not in O.sets and A not in busy:
                    batch.append(A); busy.add(A); break
        if not batch:
            return "EXHAUSTED"
        if not progress(O, batch):
            return "BUDGET"
    return "BUDGET"


def beam(dom, O, stage, rng, w=8, nb=16, q_dir=0.25, q_single=0.5, **_):
    """Batched prior-aware sliding beam.  Per batch of nb sets: round(q_dir nb) direct pairs (prior product, singleton-score free), then
    singletons from the priority stream and beam extensions (top-w scored singletons whose eligible partner list is not used up x partners
    in priority order, round-robin) split q_single : 1 - q_single; an empty stream yields its slots to the others; empty everything ->
    early tier unlock or EXHAUSTED.  Sliding membership makes every legal pair reachable once the domain is unlocked."""
    singles = Frontier(priority(dom, rng), dom.tier); ext, busy = {}, set()
    while O.left() >= 1:
        stage.update()
        nd = int(round(q_dir * nb)); ns = int(round(q_single * (nb - nd))); batch = []
        for _ in range(nd):
            A = direct_pair(dom, stage, rng, O, busy)
            if A:
                batch.append(A); busy.add(A)
        for _ in range(ns):
            a = singles.pop(stage.level)
            if a is None:
                break
            batch.append((a,))
        live, i = [], 0                                         # sliding beam: top-w scored singletons whose partner list is not used up
        for _, a in sorted(((r, A[0]) for A, r in O.sets.items() if len(A) == 1), key=lambda t: (-t[0], dom.rank[t[1]], t[1])):
            if a not in ext or ext[a].peek(stage.level) is not None:
                live.append(a)
                if len(live) == w:
                    break
        while len(batch) < nb and live:
            a = live[i % len(live)]
            if a not in ext:
                ext[a] = Frontier([b for b in priority(dom, np.random.default_rng(h64("EXT", a, rng.integers(1 << 30)))) if legal_add((a,), b)], dom.tier)
            while True:
                b = ext[a].pop(stage.level)
                if b is None or canon((a, b)) not in O.sets and canon((a, b)) not in busy:
                    break
            if b is None:
                live.remove(a); continue
            batch.append(canon((a, b))); busy.add(canon((a, b))); i += 1
        while len(batch) < nb:
            a = singles.pop(stage.level)
            if a is None:
                break
            batch.append((a,))
        if not batch:
            if stage.early():
                continue
            return "EXHAUSTED"
        if not progress(O, batch):
            return "BUDGET"
    return "BUDGET"


class Node:
    __slots__ = ("A", "N", "W", "vl", "kids", "keys", "fr", "done", "stop", "pend", "stopnode")

    def __init__(self, A, stop=False):
        self.A, self.N, self.W, self.vl, self.kids, self.keys = A, 0, 0.0, 0, [], set()
        self.fr, self.done, self.stop, self.pend, self.stopnode = None, False, stop, False, None


def mcts(dom, O, stage, rng, c=0.3, pw=(1.0, 0.5), nb=16, q_dir=0.25, kmax=2, max_iter=None, **_):
    """UCT + progressive widening over a transposition DAG of canonical sets (one node per set: no duplicated terminal sets; every legal
    pair is reachable from either of its singletons).  Children: STOP first (K1), then ADD in node-specific prior-Gumbel order, eligible
    tier only (Frontier).  Widening cap max(1, floor(k (N + 1)^alpha)); an exhausted node may still widen.  Batches of nb leaves with
    virtual loss; round(q_dir nb) leaves per batch come from the direct-pair stream (inserted root -> {a} -> {a, b}).  On a tier unlock
    every non-terminal node is reopened.  Terminal values are deterministic: a scored set is never re-scored."""
    T, seed = {}, int(rng.integers(1 << 30))
    root = T[()] = Node(())
    max_iter = max_iter or 50 * (O.B or 10 ** 5) + 1000
    stats = collections.Counter()

    def node(A):
        if A not in T:
            T[A] = Node(A)
        return T[A]

    def terminal(n):
        return n.stop or len(n.A) == kmax

    def can_expand(n):
        if terminal(n):
            return False
        if n.A and n.stopnode is None:
            return True
        if n.fr is None:
            n.fr = Frontier([a for a in priority(dom, np.random.default_rng(h64("NODE", seed, n.A))) if legal_add(n.A, a)], dom.tier)
        while True:
            a = n.fr.peek(stage.level)
            if a is None or canon(n.A + (a,)) not in n.keys:
                return a is not None
            n.fr.pop(stage.level)

    def expand(n):
        if n.A and n.stopnode is None:
            n.stopnode = Node(n.A, stop=True); n.kids.append(n.stopnode); return n.stopnode
        ch = node(canon(n.A + (n.fr.pop(stage.level),))); n.kids.append(ch); n.keys.add(ch.A); stats["expanded"] += 1
        return ch

    def live(n):
        return [k for k in n.kids if not k.done and not k.pend]

    def descend():
        n, path = root, [root]
        while not terminal(n):
            cap = math.inf if pw is None else max(1, math.floor(pw[0] * (n.N + n.vl + 1) ** pw[1]))
            lv = live(n); ce = can_expand(n)
            if ce and (len(n.kids) < cap or not lv):
                n = expand(n); path.append(n); continue
            if not lv:
                if not ce and not any(k.pend for k in n.kids):
                    n.done = True
                return None, path
            lnp = math.log(n.N + n.vl + 1)
            n = max(lv, key=lambda k: (k.W / (k.N + k.vl) if k.N + k.vl else math.inf) + c * math.sqrt(lnp / (k.N + k.vl + 1)))
            path.append(n)
        return n, path

    def settle(path):
        for n in reversed(path):
            if not terminal(n) and not n.pend:
                n.done = not can_expand(n) and all(k.done for k in n.kids)

    it = 0
    while it < max_iter and O.left() >= 1:
        if stage.update():
            for n in T.values():
                n.done = False if not terminal(n) else n.done
            stats["reopen_events"] += 1
        leaves, paths, nd = [], [], int(round(q_dir * nb))
        for j in range(nb):
            it += 1
            if j < nd:
                A = direct_pair(dom, stage, rng, O, {l.A for l in leaves})
                if A is None:
                    continue
                a = A[0] if (A[0],) in T or (A[1],) not in T else A[1]
                n1 = node((a,)); pair = node(A)
                if n1.A not in root.keys:
                    root.kids.append(n1); root.keys.add(n1.A)
                if A not in n1.keys:
                    n1.kids.append(pair); n1.keys.add(A)
                leaf, path = pair, [root, n1, pair]; stats["direct"] += 1
            else:
                leaf, path = descend()
            if leaf is None or leaf.pend or leaf.done:
                settle(path)
                continue
            leaf.pend = True; leaves.append(leaf); paths.append(path)
            for n in path:
                n.vl += 1
        if not leaves:
            if root.done or not live(root) and not can_expand(root):
                if stage.early():
                    for n in T.values():
                        n.done = False if not terminal(n) else n.done
                    continue
                return "EXHAUSTED", it, root, T, stats
            continue
        n0 = O.n["scored"]; res = O.eval_many([l.A for l in leaves])
        if O.n["scored"] == n0 and O.left() < 2:
            return "BUDGET", it, root, T, stats
        for leaf, path in zip(leaves, paths):
            r = res.get(canon(leaf.A)); leaf.pend = False; leaf.done = True
            for n in path:
                n.vl -= 1
                if r is not None:
                    n.N += 1; n.W += r
            settle(path[:-1])
    return ("BUDGET" if O.left() < 1 else "ITER_GUARD"), it, root, T, stats


# ------------------------------------------------------------------------------------------------------------------------------- driver
ARMS = {"EXACT4": ("exact", {"m": 4}), "EXACT6": ("exact", {"m": 6}), "EXACT_FULL": ("exact", {}), "RAND_FULL": ("rand", {}),
        "BEAM_SEEDED4": ("beam", {"seeded": True}), "BEAM_FULL": ("beam", {}), "BEAM_FULL_UNIFORM": ("beam", {"uniform": True}),
        "PW_MCTS_SEEDED4": ("mcts", {"seeded": True}), "PW_MCTS_FULL": ("mcts", {}), "PW_MCTS_UNIFORM": ("mcts", {"uniform": True})}


def run_arm(arm, dom, score_fn, budget, rule, key, seed=0, disp=None, params=None, udom=None, max_batches=None, max_wall=None):
    """One arm on one root -> decision record.  params: sched (f56, ftail), w, c, pw, nb, q_dir, q_single.  udom = eps = 1 Domain (uniform)."""
    kind, fixed = ARMS[arm]; p = dict(params or {})
    d = udom if fixed.get("uniform") else dom
    t0 = time.perf_counter(); O = Oracle(score_fn, None if kind == "exact" else budget, disp, max_batches, max_wall)
    rng = np.random.default_rng(h64(arm.split("_")[0], key, seed))     # BEAM_* / PW_MCTS_* share their family stream across seeded / full
    st = Stage(dom, O, p.get("sched") if fixed.get("seeded") else None)
    extra, iters = {}, None
    try:
        if kind == "exact":
            stop = exact(dom, O, dom.D(fixed["m"]) if "m" in fixed else None)
        elif kind == "rand":
            stop = rand(dom, O, rng, nb=p.get("nb", 16))
        elif kind == "beam":
            stop = beam(d, O, st, rng, **{k: v for k, v in p.items() if k in ("w", "nb", "q_dir", "q_single")})
        else:
            stop, iters, root, T, stats = mcts(d, O, st, rng, **{k: (tuple(v) if k == "pw" and v else v) for k, v in p.items() if k in ("c", "pw", "nb", "q_dir")})
            extra = {"nodes": len(T), **{f"mcts_{k}": v for k, v in stats.items()}}
    except BudgetStop as e:
        stop = str(e)
    pick = choose(O.candidates(), rule)
    dec = "ABSTAIN" if pick is None else "NOOP" if pick["seq"] == [] else "REPAIR"
    tiers = collections.Counter(max(dom.tier[a] for a in A) for A in O.sets)
    acts = {a for A in O.sets for a in A}
    first_off4 = next((s for A, s, _ in O.log if any(dom.tier[a] > 1 for a in A)), None)
    return {"arm": arm, "budget": budget, "seed": seed, "decision": dec, "seq": None if pick is None else pick["seq"],
            "p11": None if pick is None else pick["p11"], "p_noop": O.noop["p11"], "stop": stop, "iterations": iters, **dict(O.n),
            "best_reward": max(O.sets.values(), default=None), "pick_stratum": dom.strata(canon([tuple(x) for x in pick["seq"]])) if dec == "REPAIR" else None,
            "pick_max_rank": max(dom.rank[tuple(x)] for x in pick["seq"]) + 1 if dec == "REPAIR" else None,
            "sets_by_max_tier": {str(k): v for k, v in sorted(tiers.items())}, "actions_scored": len(acts),
            "actions_scored_off4": sum(dom.tier[a] > 1 for a in acts), "objects_scored": len({a[0] for a in acts}),
            "first_off4_at": first_off4, "tier_events": st.events, "batch_sizes": [min(O.bs[1:], default=0), max(O.bs[1:], default=0)],
            "params": p, "wall_s": round(time.perf_counter() - t0, 6), "final_level": st.level,
            "scored_sets": [[list(a) for a in A] for A, _, _ in O.log] if kind != "exact" else None, **extra}
