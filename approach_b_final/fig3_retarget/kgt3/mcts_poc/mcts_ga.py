"""GA-MCTS: an MCTS-guided search over the SAME candidate domain as Fig. 3B GA (planners.ga), set-first / chunk-second.

Domain   D = the initial S1 top-4 cVAE proposals at S0, filtered by the single-action grammar exactly as planners.ga (identical code path).
Tree     node = canonical partial UNORDERED assignment A (sorted (obj, cell) tuple); canonical expansion: a child adds (o, d) whose object
         comes later than every object of A in a fixed root order pi (objects ranked by the cheap singleton guidance), so every legal set
         has exactly ONE tree path (no transpositions, no equivalent-assignment re-exploration; each set is evaluated at most once).
         Monotone constraints: move-once (distinct objects), distinct initially-vacant destinations (from D), target never in D, |A| <= H.
         Chunks <= 3, q_ref at chunk boundaries and has_multi are enforced by the unchanged terminal evaluator (compose.grouped_dp).
Search   batched UCT with virtual visits.  Every newly expanded node is evaluated ONCE with the exact GA terminal energy and backed up.
         Selection: argmax  Q/R* + c sqrt(ln N_parent / N_child)  (Q = mean backed-up reward, R* = best reward so far: scale only).
         Expansion order (cheap guidance, NEVER the terminal score): w_y log Y_global(A + a) - w_x xpair(a | A) - w_r rank_cVAE(a) + seeded
         Gumbel(tau) jitter;  xpair = min over b in A of the ordered first-chunk pair cost at S0 (GA's BOUNDED xproxy readouts); the Y prior
         is dropped when the y-readout budget passes y_prior_frac of its cap.  expand = FULL (all children before UCT) | PW (progressive
         widening: at most ceil(pw_k N^pw_alpha) children).
Terminal (identical to planners.ga): |A| <= 3 -> planners.short_options over every order (exact joint p11 of one chunk);
         |A| > 3 -> compose.grouped_dp on the shared Scores cache, E = F - log max(eps, Y_global(A)).  Reward R = exp(-E) (search only).
Selection / deadline: planners.plan itself (production NOOP gate, K <= 3 floor inside the timed region, argmin planners.ckey, select reserve);
         GA-MCTS = planners.plan(arm 'GA') with the search function swapped in-process for the call only (search_as_ga).
No ground-truth K / L_ref / witness / labels / evaluator metadata, no physical or motion-planning module, no retraining (tested)."""
from __future__ import annotations

import contextlib, hashlib, itertools, json, math, random, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
KG = HERE.parent
sys.path[:0] = [str(KG), str(KG.parent), str(KG.parent.parent)]
import compose as CP  # noqa: E402
import planners as PL  # noqa: E402
import views as V  # noqa: E402

MCFG = {"c": 0.7, "expand": "FULL", "pw_k": 2.0, "pw_alpha": 0.5, "batch": 32, "w_y": 1.0, "w_x": 1.0, "w_r": 0.25, "tau": 0.1,
        "y_prior_frac": 0.5, "seed": 0}


def domain(fz, row0, H):
    """-> (D, rank): planners.ga's D (same calls, same filter) + the cVAE rank of each destination (guidance only)."""
    el = V.eligible(row0)
    raw = fz.proposals(row0, el)
    rank = {(int(o), int(d)): i for o, v in raw.items() for i, d in enumerate(v)}
    D = {o: sorted(set(v)) for o, v in raw.items() if v}
    D = {o: [d for d in v if V.legal_seq(row0, [[o, d]], H)] for o, v in D.items()}
    return {o: v for o, v in D.items() if v}, rank


class Node:
    __slots__ = ("A", "kids", "untried", "N", "W", "done", "evaluated", "E")

    def __init__(self, A):
        self.A, self.kids, self.untried, self.N, self.W, self.done, self.evaluated, self.E = A, [], None, 0, 0.0, False, False, None


class Search:
    def __init__(self, fz, row0, cfg, sink):
        self.fz, self.row0, self.cfg, self.sink = fz, row0, cfg, sink
        self.m = {**MCFG, **(cfg.get("mcts") or {})}
        self.H = cfg["H"][row0["domain"]]
        self.B = PL.Budget(cfg)
        self.rng = random.Random(hashlib.sha256(f"GA-MCTS|{self.m['seed']}|{row0['root_id']}".encode()).hexdigest())
        self.D, self.rank = domain(fz, row0, self.H)
        self.acts = sorted((o, d) for o, v in self.D.items() for d in v)
        self.T = CP.Scores(fz, row0, V.rebase, tick=self.B.tick)
        self.best = {}                                   # size -> best candidate (planners.ckey)
        self.rstar, self.evals, self.iters, self.nodes, self.dead = 0.0, {}, 0, 1, 0
        self.tm = {"select": 0.0, "prior_y": 0.0, "eval_y": 0.0, "eval_short": 0.0, "eval_need": 0.0, "eval_dp": 0.0, "prefetch": 0.0}
        sizes = [len(v) for v in self.D.values()]
        self.info = {"mode": "MCTS", "D4": {str(o): v for o, v in self.D.items()}, "assign_upper_bound": {k: PL.elem(sizes, k) for k in range(1, self.H + 1)},
                     "per_size": {}, "by_size": {}, "exhausted": False, "mcts": dict(self.m), "scores_ref": self.T}
        sink["info"] = self.info

    # ------------------------------------------------------------------ cheap guidance (never the terminal score)
    def prefetch(self):
        req = [(frozenset(), (a,)) for a in self.acts] + [(frozenset(), (a, b)) for a in self.acts for b in self.acts if a[0] != b[0] and a[1] != b[1]]
        self.T.need(req)
        best1 = {}
        for a in self.acts:
            s = self.m["w_x"] * self.T.cost((), (a,)) + self.m["w_r"] * self.rank.get(a, 4)
            best1[a[0]] = min(best1.get(a[0], math.inf), s)
        self.pi = {o: i for i, o in enumerate(sorted(best1, key=lambda o: (best1[o], o)))}

    def xpair(self, A, a):
        if not A:
            return self.T.cost((), (a,))
        return min(min(self.T.cost((), (b, a)), self.T.cost((), (a, b))) for b in A)

    def moves(self, A):
        if len(A) >= self.H:
            return []
        top = max((self.pi[o] for o, _ in A), default=-1)
        used = {d for _, d in A}
        return [a for a in self.acts if self.pi[a[0]] > top and a[1] not in used]

    def init_children(self, n):
        mv = self.moves(n.A)
        if not mv:
            n.untried = []
            return
        kids = [tuple(sorted(n.A + (a,))) for a in mv]
        cap = (self.fz.caps or {}).get("y_unique")
        use_y = self.m["w_y"] != 0 and (cap is None or self.fz.c.get("y_unique", 0) + len(kids) <= self.m["y_prior_frac"] * cap)
        t = time.perf_counter()
        yv = self.fz.y_global(self.row0, [list(map(list, A)) for A in kids]) if use_y else [1.0] * len(kids)
        self.tm["prior_y"] += time.perf_counter() - t
        sc = []
        for a, y in zip(mv, yv):
            g = -math.log(max(1e-300, -math.log(max(1e-300, self.rng.random())))) if self.m["tau"] else 0.0
            s = self.m["w_y"] * math.log(max(CP.EPS, y)) - self.m["w_x"] * self.xpair(n.A, a) - self.m["w_r"] * self.rank.get(a, 4) + self.m["tau"] * g
            sc.append((s, a))
        n.untried = [a for _, a in sorted(sc, key=lambda t: (t[0], t[1]))]      # pop() takes the best

    # ------------------------------------------------------------------ tree policy
    def can_expand(self, n):
        if not n.untried:
            return False
        if self.m["expand"] == "FULL":
            return True
        return len(n.kids) < max(1, math.ceil(self.m["pw_k"] * max(n.N, 1) ** self.m["pw_alpha"]))

    def refresh(self, n):
        n.done = n.evaluated and n.untried is not None and not n.untried and all(k.done for k in n.kids)

    def select(self):
        n, path = self.root, [self.root]
        while True:
            if n.untried is None:
                self.init_children(n)
            if self.can_expand(n):
                a = n.untried.pop()
                c = Node(tuple(sorted(n.A + (a,))))
                n.kids.append(c); self.nodes += 1
                path.append(c)
                for x in path:
                    x.N += 1                                                 # virtual visit (reward added at backup)
                return path
            live = [k for k in n.kids if not k.done and (k.evaluated or k.untried is None or k.untried)]
            if not live:
                self.refresh(n)
                for x in reversed(path[:-1]):
                    self.refresh(x)
                return None
            lnp = math.log(max(n.N, 1))
            rs = self.rstar or 1.0
            n = max(live, key=lambda k: ((k.W / k.N / rs) if k.N else math.inf) + self.m["c"] * math.sqrt(lnp / max(k.N, 1)) + 1e-12 * self.rng.random())
            path.append(n)

    # ------------------------------------------------------------------ terminal evaluation (identical to planners.ga)
    def evaluate(self, sets):
        fz, row0 = self.fz, self.row0
        self.B.tick()
        t = time.perf_counter()
        yg = dict(zip(sets, fz.y_global(row0, [list(map(list, A)) for A in sets])))
        short = [A for A in sets if len(A) <= 3]
        long_ = [A for A in sets if len(A) > 3]
        t1 = time.perf_counter(); self.tm["eval_y"] += t1 - t
        if short:                                                            # one batched prefetch; short_options then reads the cache
            fz.score(row0, [list(map(list, o)) for A in short for o in itertools.permutations(A)])
        t2 = time.perf_counter(); self.tm["eval_short"] += t2 - t1
        if long_:
            self.T.need({r for A in long_ for r in CP.requests(A)})
        t3 = time.perf_counter(); self.tm["eval_need"] += t3 - t2
        out = {}
        for A in sets:
            self.B.tick()
            assert A not in self.evals, "set evaluated twice"
            self.evals[A] = 1
            best = None
            if len(A) <= 3:
                for c in PL.short_options(fz, row0, [list(map(list, o)) for o in itertools.permutations(A)]):
                    c.update(set=[list(a) for a in A], y_global=yg[A], n_chunks=1)
                    if best is None or PL.ckey(c) < PL.ckey(best):
                        best = c
            else:
                self.T.dp_lookups += CP.nx(len(A))
                r = CP.grouped_dp(self.T, A)
                if r:
                    F, o, p = r
                    best = PL.cand_of(o, p, F - math.log(max(CP.EPS, yg[A])), kind="ga_dp", y_global=yg[A], set=[list(a) for a in A], F=F, n_chunks=len(p))
            out[A] = best
            self.tm["eval_dp"] += time.perf_counter() - t3; t3 = time.perf_counter()
            k = len(A)
            ps = self.info["per_size"].setdefault(k, {"evaluated": 0})
            ps["evaluated"] += 1
            if best is not None and (k not in self.best or PL.ckey(best) < PL.ckey(self.best[k])):
                self.best[k] = best
                self.publish(k, best)
        return out

    def publish(self, k, c):
        """In-place incumbent update of the per-size argmin list (only a per-size argmin can win the global argmin, as in planners.ga)."""
        L = self.sink["cands"]
        sizes = [len(x["seq"]) for x in L]
        if k in sizes:
            L[sizes.index(k)] = c
        else:
            L.append(c)
        self.info["by_size"][k] = {"E": c["E"], "y_global": c.get("y_global"), "F": c.get("F"), "n_chunks": len(c["partition"])}

    # ------------------------------------------------------------------ main loop
    def run(self):
        self.B.tick()
        self.root = Node(())
        self.root.evaluated = True
        if not self.acts:
            self.root.untried, self.root.done = [], True
        else:
            t = time.perf_counter(); self.prefetch(); self.tm["prefetch"] += time.perf_counter() - t
        while not self.root.done:
            self.B.tick()
            self.iters += 1
            paths, fails = [], 0
            while len(paths) < self.m["batch"] and fails < 4 and not self.root.done:
                t = time.perf_counter(); p = self.select(); self.tm["select"] += time.perf_counter() - t
                if p is None:
                    fails += 1; self.dead += 1
                    continue
                paths.append(p)
            if not paths:
                if self.root.done:
                    break
                continue
            res = self.evaluate([p[-1].A for p in paths])
            for p in paths:
                leaf = p[-1]
                c = res[leaf.A]
                leaf.E = c["E"] if c else None
                R = math.exp(-c["E"]) if c else 0.0
                self.rstar = max(self.rstar, R)
                leaf.evaluated = True
                if leaf.untried is None and len(leaf.A) >= self.H:
                    leaf.untried = []
                for x in p:
                    x.W += R
                for x in reversed(p):
                    self.refresh(x)
        self.info["exhausted"] = bool(self.root.done)
        return self.finish()

    def finish(self):
        self.info["n_evals"] = len(self.evals); self.info["dup_evals"] = 0
        self.info["iterations"], self.info["nodes"], self.info["dead_selections"] = self.iters, self.nodes, self.dead
        self.info["scores"] = {**self.T.n, "dp_lookups": self.T.dp_lookups}
        self.info["timing"] = {k: round(v, 3) for k, v in self.tm.items()}
        self.info.pop("scores_ref", None)
        return list(self.sink["cands"]), self.info


def search(fz, row0, mode, cfg=None, log=None, sink=None):
    """planners.ga-compatible signature (mode ignored: GA-MCTS has one mode).  -> candidates, info; fills `sink` progressively."""
    cfg = {**PL.CFG, **(cfg or {})}
    sink = sink if sink is not None else {"cands": [], "info": {}}
    S = Search(fz, row0, cfg, sink)
    try:
        return S.run()
    except BaseException:
        S.info["n_evals"] = len(S.evals); S.info["iterations"], S.info["nodes"] = S.iters, S.nodes
        S.info["timing"] = {k: round(v, 3) for k, v in S.tm.items()}
        raise


@contextlib.contextmanager
def search_as_ga(fn):
    """Process-local, call-scoped swap of planners.ga (restored in finally; the planners module file is never modified)."""
    orig = PL.ga
    PL.ga = fn
    try:
        yield orig
    finally:
        PL.ga = orig


def plan(fz, row0, floor, cfg=None, mcfg=None, search_fn=None):
    """One GA-MCTS plan under planners.plan's exact end-to-end semantics (floor + search + selection inside one deadline)."""
    cfg = {**(cfg or {}), "mcts": {**MCFG, **(mcfg or {})}}
    with search_as_ga(search_fn or search):
        out = PL.plan(fz, row0, "GA", floor, cfg)
    out["arm"] = "GA-MCTS"
    return out


def canon_cfg(m):
    return hashlib.sha256(json.dumps({**MCFG, **m}, sort_keys=True).encode()).hexdigest()[:12]
