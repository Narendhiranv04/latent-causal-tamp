#!/usr/bin/env python3
"""Recursive compose-and-rank planner (plan §2 + AUDIT §4, amendments A1-A8, A13).  Frozen K<=3 models are only called through models.py.
Top level (ITERATIVE LOOP, original task τ0): a beam of global prefixes; each round, for every prefix P, the budgeted local generator proposes
<=3-action hypotheses u for τ0 in S_P; expand(u) inserts recursively generated enabling sequences before actions whose TEMPORARY-TARGET signal
ŷ(A -> d_A | pre-scene) is low (or, as a fixed diversity fallback, before the lowest-ŷ action of u); every globally legal composed plan is a
candidate.  The recursion gate is the temporary-task Y, NEVER the magnitude of the original-target p11.  Plans are ranked by the energy
C(r) = -log h_Y(r) + λ_X Σ_j -log h_X(c_j) (+ λ_m|r|); h_Y = original-task Y-only endpoint vs S0, h_X = marginal px of canonical chunks of 3.
Arms: REC (frozen, retarget+insertion), FLAT (frozen, expand = identity: same loop/budgets, no temporary targets), RAND (random proposals /
local scores / gates via models.Random, same recursion and the same frozen final energy)."""
import itertools, json, math, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import data as DA  # noqa: E402

CFG = {"L": 8, "B_loc": 6, "B_top": 6, "B_exp": 4, "B_loc_tt": 4, "D_max": 3, "cap": 12, "theta_done": 0.5, "theta_tt": 0.5, "fallback_hi": 0.9,
       "lam_X": 1.0, "lam_m": 0.0, "eps": 1e-6, "max_local": 150, "max_ytask": 4000, "max_wall_s": 180.0, "max_rounds": 12, "noop_gate": 0.5,
       "suspect_rule": "threshold", "tt_local_per_insert": None, "tt_rel_gain": None}      # REC2 (deviation D-1) overrides the last three


class Budget:
    def __init__(self, cfg):
        self.cfg, self.t0, self.local, self.ytask, self.reason = cfg, time.time(), 0, 0, None

    def out(self):
        if self.reason:
            return True
        c = self.cfg
        self.reason = ("LOCAL_CALLS" if self.local >= c["max_local"] else "YTASK_PROBES" if self.ytask >= c["max_ytask"]
                       else "WALL" if time.time() - self.t0 >= c["max_wall_s"] else None)
        return self.reason is not None


class Planner:
    def __init__(self, row0, models, arm="REC", cfg=None, log=None):
        self.row0, self.M, self.arm = row0, models, arm
        self.cfg = {**CFG, **(cfg or {})}
        self.B = Budget(self.cfg)
        self.log = log if log is not None else {"local": [], "ytask": [], "insert": [], "rounds": []}
        self.cands = {}

    # ---------------------------------------------------------------- learned signals
    def hr(self, P, task=None, reserved=(), rcells=()):
        return DA.HypoRoot(self.row0, P, task, reserved, rcells)

    def ytask(self, P, A, d, reserved, rcells):
        self.B.ytask += 1
        h = self.hr(P, (A, d), reserved, rcells)
        y = self.M.ytask(h)
        self.log["ytask"].append({"P": [list(x) for x in P], "A": A, "d": d, "y": y})
        return y

    def local(self, h, cap, task_tag):
        """Budgeted local K<=3 generator (A4): K1 over all movers; K2/K3 over the top-L movers by their best K1 p11; fair over first movers."""
        self.B.local += 1
        D = self.M.propose(h)
        D = {o: v for o, v in D.items() if v}
        if not D or cap <= 0:
            return []
        k1 = [[(o, d)] for o, v in D.items() for d in v]
        s1 = self.M.score(h, k1)
        best = {}
        for s, r in zip(k1, s1):
            best[s[0][0]] = max(best.get(s[0][0], -1.0), r["p11"])
        top = sorted(best, key=lambda o: (-best[o], o))[: self.cfg["L"]]
        cand = list(zip(k1, s1))
        DL = {o: D[o] for o in top}
        for k in range(2, min(3, cap) + 1):
            seqs = [list(p) for a in _assign(DL, k) for p in itertools.permutations(a)]
            cand += list(zip(seqs, self.M.score(h, seqs))) if seqs else []
        cand.sort(key=lambda x: (-x[1]["p11"], len(x[0]), json.dumps(x[0])))
        out, firsts = [], {}
        for s, r in cand:                                  # fairness: at most 2 hypotheses per first mover in the returned beam
            if firsts.get(s[0][0], 0) >= 2:
                continue
            firsts[s[0][0]] = firsts.get(s[0][0], 0) + 1
            out.append(s)
            if len(out) >= (self.cfg["B_loc"] if task_tag == "T0" else self.cfg["B_loc_tt"]):
                break
        self.log["local"].append({"task": task_tag, "P_len": len(h.prefix), "n_movers": len(D), "k1_best": {str(o): round(best[o], 6) for o in best},
                                  "top_L": top, "beam": [[list(x) for x in s] for s in out], "n_scored": len(cand)})
        return out

    # ---------------------------------------------------------------- recursion
    def _tt_ok(self, y, y0):
        g = self.cfg["tt_rel_gain"]
        return y >= self.cfg["theta_tt"] or (g is not None and y0 is not None and y - y0 >= g)

    def _sub_out(self):
        lim = self.cfg["tt_local_per_insert"]
        return lim is not None and getattr(self, "_sub0", None) is not None and self.B.local - self._sub0 >= lim

    def solve_tt(self, P, A, d, reserved, rcells, cap, depth, y0=None):
        """Enabling sequence e (after P) such that ŷ(A -> d | P+e) >= θ_tt (REC2: or ŷ gain >= tt_rel_gain over ŷ before insertion);
        [] if none within budget/depth (REC2: also a per-insertion local-call cap).  First success wins."""
        y = self.ytask(P, A, d, reserved, rcells)
        if y0 is None:
            y0 = y
            if y >= self.cfg["theta_tt"]:
                return [[]]
        if depth > self.cfg["D_max"] or cap <= 0 or self.B.out() or self._sub_out():
            return []
        h = self.hr(P, (A, d), reserved, rcells)
        for u in self.local(h, min(3, cap), f"TT{A}"):
            for s in self.expand(P, u, reserved | {A}, rcells | {d}, cap, depth):
                if DA.check_sequence(self.row0, P + s) is not None:
                    continue
                if self._tt_ok(self.ytask(P + s, A, d, reserved, rcells), y0):
                    return [s]
                if len(s) < cap and depth < self.cfg["D_max"] and not self._sub_out():
                    t = self.solve_tt(P + s, A, d, reserved | {i for i, _ in s}, rcells, cap - len(s), depth + 1, y0)
                    if t:
                        return [s + t[0]]
                if self.B.out() or self._sub_out():
                    return []
        return []

    def expand(self, P, u, reserved, rcells, cap, depth):
        if self.arm == "FLAT":
            return [list(u)]
        ys0 = {a: self.ytask(P, a[0], a[1], reserved | {x for x, _ in u if x != a[0]}, rcells | {y for _, y in u if y != a[1]}) for a in u}
        amin = min(u, key=lambda a: ys0[a])
        res = [[]]
        for j, a in enumerate(u):
            A, d = a
            nxt = []
            for p in res:
                pend = {x for x, _ in u[j + 1:]}; pend_c = {y for _, y in u[j + 1:]}
                rv = reserved | pend | {x for x, _ in p} | {A}
                y = ys0[a] if not p else self.ytask(P + p, A, d, rv - {A}, rcells | pend_c)
                if self.cfg["suspect_rule"] == "min":       # REC2: relative ranking -- only the lowest-ŷ action of u is repaired
                    suspect = a == amin and y < self.cfg["fallback_hi"]
                else:
                    suspect = y < self.cfg["theta_tt"] or (a == amin and y < self.cfg["fallback_hi"])
                if suspect and not self.B.out():
                    room = cap - len(p) - (len(u) - j)
                    outer = getattr(self, "_sub0", None)
                    if depth == 0:
                        self._sub0 = self.B.local                # per-insertion sub-budget starts at a top-level insertion
                    E = self.solve_tt(P + p, A, d, rv, rcells | pend_c, room, depth + 1) if room > 0 else []
                    if depth == 0:
                        self._sub0 = outer
                    for e in E:
                        if e:
                            nxt.append(p + e + [a])
                            self.log["insert"].append({"P_len": len(P), "before": [A, d], "enabling": [list(x) for x in e], "y_before": y})
                nxt.append(p + [a])
            seen, res = set(), []
            for q in nxt:
                k = json.dumps(q)
                if k not in seen and len(P) + len(q) <= self.cfg["cap"]:
                    seen.add(k); res.append(q)
            res = res[: self.cfg["B_exp"]]
        return res

    # ---------------------------------------------------------------- ranking
    def energy(self, seqs):
        hY = self.M.y_end(self.row0, seqs)
        out = []
        for s, y in zip(seqs, hY):
            hx = []
            for j in range(0, len(s), 3):
                hx.append(self.M.x_chunk(self.hr(s[:j]), s[j:j + 3]))
            e, l = self.cfg["eps"], self.cfg["lam_X"]
            C = -math.log(max(e, y)) + l * sum(-math.log(max(e, x)) for x in hx) + self.cfg["lam_m"] * len(s)
            out.append({"hY": y, "hX": hx, "C": C, "C_Yonly": -math.log(max(e, y)), "C_Xonly": sum(-math.log(max(e, x)) for x in hx)})
        return out

    def run(self):
        c = self.cfg
        p_noop = self.M.y_noop(self.row0)
        frontier, rounds = [[]], 0
        while frontier and rounds < c["max_rounds"] and not self.B.out():
            nxt = []
            for P in frontier:
                h = self.hr(P)
                for u in self.local(h, min(3, c["cap"] - len(P)), "T0"):
                    for s in self.expand(P, u, set(), set(), c["cap"] - len(P), 0):
                        r = P + s
                        if DA.check_sequence(self.row0, r) is not None or json.dumps(r) in self.cands:
                            continue
                        self.cands[json.dumps(r)] = None
                        nxt.append(r)
                    if self.B.out():
                        break
                if self.B.out():
                    break
            if not nxt:
                break
            en = self.energy(nxt)
            for r, e in zip(nxt, en):
                self.cands[json.dumps(r)] = e
            done = [r for r, e in zip(nxt, en) if e["hY"] >= c["theta_done"]]
            live = sorted([(e["C"], len(r), json.dumps(r), r) for r, e in zip(nxt, en) if e["hY"] < c["theta_done"] and len(r) < c["cap"]])
            frontier, firsts = [], {}
            for _, _, _, r in live:                         # beam with diversity: <= 2 frontier plans per first action
                k = json.dumps(r[:1])
                if firsts.get(k, 0) >= 2:
                    continue
                firsts[k] = firsts.get(k, 0) + 1
                frontier.append(r)
                if len(frontier) >= c["B_top"]:
                    break
            rounds += 1
            self.log["rounds"].append({"round": rounds, "new": len(nxt), "done": len(done), "frontier": [[list(x) for x in r] for r in frontier],
                                       "best_C": min(e["C"] for e in en), "best_hY": max(e["hY"] for e in en)})
        scored = {k: v for k, v in self.cands.items() if v is not None}
        pick = lambda key: min(scored.items(), key=lambda kv: (kv[1][key], len(json.loads(kv[0])), kv[0]))[0] if scored else None  # noqa: E731
        if p_noop >= c["noop_gate"]:
            decision, seq = "NOOP", []
        elif scored:
            decision, seq = "REPAIR", json.loads(pick("C"))
        else:
            decision, seq = "ABSTAIN", []
        stop = self.B.reason or ("FRONTIER_EMPTY" if not frontier else "MAX_ROUNDS")
        alt = {k: (json.loads(pick(k)) if scored else None) for k in ("C_Yonly", "C_Xonly")}
        return {"root_id": self.row0["root_id"], "arm": self.arm, "decision": decision, "seq": seq, "p_noop": p_noop,
                "energy": scored.get(json.dumps(seq)) if seq else None, "alt_Yonly": alt["C_Yonly"], "alt_Xonly": alt["C_Xonly"],
                "n_candidates": len(scored), "rounds": rounds, "stop": stop, "budget": {"local": self.B.local, "ytask": self.B.ytask,
                "wall_s": round(time.time() - self.B.t0, 2)}, "model_calls": dict(self.M.c), "cfg": self.cfg}


def _assign(D, k):
    ob = sorted(o for o, v in D.items() if v)
    for objs in itertools.combinations(ob, k):
        for ds in itertools.product(*(D[o] for o in objs)):
            if len(set(ds)) == k:
                yield tuple(zip(objs, ds))
