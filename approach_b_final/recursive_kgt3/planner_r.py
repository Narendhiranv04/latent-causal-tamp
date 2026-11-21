#!/usr/bin/env python3
"""P4 recovery planner (P4_RECOVERY_PLAN.md).  Subclass of the historical planner.Planner (R0 = that class, unchanged).  Every change is a
switch in cfg so each variant is a minimal, separately attributable correction of the Iterative Loop -> Retarget -> Compose -> Rank method:
  R1  rank/stop:   C(r) = -log h_Y(r) + λ_X · mean_j[-log h_X(c_j)]   (length-neutral stage-X aggregate instead of a per-chunk SUM)
                   NO termination on h_Y >= θ: a high final Y only improves rank; search stops on budget, round cap, or energy stagnation
  R2  fair recursion: relative temporary-target gating (the lowest-ŷ action of each hypothesis + any action with ŷ < ρ·max ŷ of u; no absolute
                   0.5), enabler accepted iff ŷ(A->d) at least doubles (scale-free), per-round / per-frontier-plan / per-insertion local-call pacing
  R3  target-centric seeding (separate variant): temporary tasks built only from the PUBLIC target/goal and frozen-model calls --
                   pick side: T retargeted to its own frozen-cVAE destination proposals d (most reachable by ŷ);  goal side: the object O the
                   model rates most able to reach G (argmax ŷ(O->G)); both solved by the SAME recursive temporary-task machinery; the seeds are
                   added to round 0 of the iterative loop (they never bypass ranking)
  FLAT/N controls: mode 'FLAT' (no retarget/insertion) and models.Random (N) with the same R1/R2 search machinery."""
import json, math, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as DA  # noqa: E402
import planner as PLN  # noqa: E402

P4CFG = {"agg_X": "mean", "stop_on_hY": False, "stagnation_rounds": 3, "gate": "relative", "rho": 0.5, "tt_gain_ratio": 2.0,
         "pace": True, "tt_local_per_insert": 3, "target_seed": False, "max_wall_s": 600.0}


class PlannerR(PLN.Planner):
    def __init__(self, row0, models, arm="REC", cfg=None, log=None):
        super().__init__(row0, models, arm, {**P4CFG, **(cfg or {})}, log)
        self._allow = None                               # local-call allowance of the current top-level unit (pacing)

    # ------------------------------------------------------------------ budget pacing (R2)
    def _out_unit(self):
        return self._allow is not None and self.B.local >= self._allow

    # ------------------------------------------------------------------ R2 relative recursion gate and subgoal acceptance
    def _tt_ok(self, y, y0):
        if self.cfg["gate"] != "relative":
            return super()._tt_ok(y, y0)
        return y0 is not None and y >= self.cfg["tt_gain_ratio"] * max(y0, 1e-6)

    def solve_tt(self, P, A, d, reserved, rcells, cap, depth, y0=None):
        if self.cfg["gate"] != "relative":
            return super().solve_tt(P, A, d, reserved, rcells, cap, depth, y0)
        y = self.ytask(P, A, d, reserved, rcells)
        if y0 is None:
            y0 = y
        if depth > self.cfg["D_max"] or cap <= 0 or self.B.out() or self._sub_out() or self._out_unit():
            return []
        h = self.hr(P, (A, d), reserved, rcells)
        for u in self.local(h, min(3, cap), f"TT{A}"):
            for s in self.expand(P, u, reserved | {A}, rcells | {d}, cap, depth):
                if DA.check_sequence(self.row0, P + s) is not None:
                    continue
                if self._tt_ok(self.ytask(P + s, A, d, reserved, rcells), y0):
                    return [s]
                if self.B.out() or self._sub_out() or self._out_unit():
                    return []
        return []

    def expand(self, P, u, reserved, rcells, cap, depth):
        if self.arm == "FLAT" or self.cfg["gate"] != "relative":
            return super().expand(P, u, reserved, rcells, cap, depth)
        ys0 = {a: self.ytask(P, a[0], a[1], reserved | {x for x, _ in u if x != a[0]}, rcells | {y for _, y in u if y != a[1]}) for a in u}
        if self.cfg.get("ref_gate", False):              # P4-A1: harder than a typical action in the SAME hypothetical scene
            ref = self.scene_ref(P)
            suspect = {a for a in u if ys0[a] < ref}
        else:
            top = max(ys0.values())
            amin = min(u, key=lambda a: ys0[a])
            suspect = {a for a in u if a == amin or ys0[a] < self.cfg["rho"] * top}
        res = [[]]
        for j, a in enumerate(u):
            A, d = a
            nxt = []
            for p in res:
                pend = {x for x, _ in u[j + 1:]}; pend_c = {y for _, y in u[j + 1:]}
                rv = reserved | pend | {x for x, _ in p} | {A}
                if a in suspect and not self.B.out() and not self._out_unit():
                    room = cap - len(p) - (len(u) - j)
                    outer = getattr(self, "_sub0", None)
                    if depth == 0:
                        self._sub0 = self.B.local
                    E = self.solve_tt(P + p, A, d, rv, rcells | pend_c, room, depth + 1) if room > 0 else []
                    if depth == 0:
                        self._sub0 = outer
                    for e in E:
                        if e:
                            nxt.append(p + e + [a])
                            self.log["insert"].append({"P": [list(x) for x in P], "p": [list(x) for x in p], "before": [A, d],
                                                       "enabling": [list(x) for x in e], "y_before": ys0[a], "depth": depth})
                nxt.append(p + [a])
            seen, res = set(), []
            for q in nxt:
                k = json.dumps(q)
                if k not in seen and len(P) + len(q) <= self.cfg["cap"]:
                    seen.add(k); res.append(q)
            res = res[: self.cfg["B_exp"]]
        return res

    def scene_ref(self, P):
        """Scene-relative reference (P4-A1): median over movable objects o of ŷ(o -> its top frozen-cVAE destination) in scene S_P."""
        if not hasattr(self, "_ref"):
            self._ref = {}
        k = json.dumps(sorted(map(tuple, P)))
        if k not in self._ref:
            h = self.hr(P)
            D = self.M.propose(h)
            ys = [self.ytask(P, o, v[0], set(), set()) for o, v in D.items() if v]
            ys.sort()
            self._ref[k] = ys[len(ys) // 2] if ys else 0.0
        return self._ref[k]

    # ------------------------------------------------------------------ R1 energy (length-neutral stage-X aggregate)
    def energy(self, seqs):
        out = super().energy(seqs)
        if self.cfg["agg_X"] != "mean":
            return out
        e, l = self.cfg["eps"], self.cfg["lam_X"]
        for o in out:
            mx = sum(-math.log(max(e, x)) for x in o["hX"]) / max(1, len(o["hX"]))
            o["C_Xonly"] = mx
            o["C"] = -math.log(max(e, o["hY"])) + l * mx + self.cfg["lam_m"] * 0
        return out

    # ------------------------------------------------------------------ R3 target-centric seeds (public target/goal + frozen calls only)
    def target_seeds(self):
        inp = self.row0["inputs"]
        T0, G0 = int(inp["tid"]), int(inp["goal_cell"])
        base = self.hr([])
        seeds = []
        # pick side: frozen cVAE destinations for T itself (T as the queried object), most reachable by temporary-task ŷ
        import torch
        gen = torch.Generator(device=self.M.samp.dev).manual_seed(0) if hasattr(self.M, "samp") else None
        legal = base.legal_dests(base.cells0)
        if hasattr(self.M, "samp") and self.M.name == "frozen":
            DT = self.M.samp.propose_many(base, base.cells0, [T0], 6, gen).get(T0, [])[:4]
        else:
            import random
            DT = random.Random(f"R3|{self.row0['root_id']}").sample(legal, min(4, len(legal)))
        if DT:
            yd = {d: self.ytask([], T0, d, set(), set()) for d in DT}
            dstar = max(DT, key=lambda d: (yd[d], -d))
            e = self.solve_tt([], T0, dstar, set(), {G0}, self.cfg["cap"] - 1, 1)
            self.log["seeds"].append({"side": "pick", "T_dest_proposals": DT, "y": yd, "chosen": dstar, "enabling": e[0] if e else None})
            if e and e[0]:
                seeds.append(e[0])
        # goal side: object most able (by frozen ŷ) to reach G; its enablers are goal-side repairs
        cand = [o for o in base.movable]
        yg = {o: self.ytask([], o, G0, set(), set()) for o in cand}
        if yg:
            ostar = max(cand, key=lambda o: (yg[o], -o))
            e = self.solve_tt([], ostar, G0, {T0}, set(), self.cfg["cap"] - 1, 1)
            self.log["seeds"].append({"side": "goal", "O_star": ostar, "y_O_to_G_top": sorted(yg.values())[-3:], "enabling": e[0] if e else None})
            if e and e[0]:
                seeds.append(e[0])
        if len(seeds) == 2 and not ({o for o, _ in seeds[0]} & {o for o, _ in seeds[1]}):
            seeds.append(seeds[0] + seeds[1])
        return [s for s in seeds if DA.check_sequence(self.row0, s) is None]

    # ------------------------------------------------------------------ R1/R2 loop: frontier / completion / ranking / decision separated
    def run(self):
        c = self.cfg
        p_noop = self.M.y_noop(self.row0)
        frontier, rounds, best_hist, seeds = [[]], 0, [], []
        if c["target_seed"] and not self.B.out():
            seeds = self.target_seeds()
        while frontier and rounds < c["max_rounds"] and not self.B.out():
            nxt = list(seeds) if rounds == 0 else []
            per_plan = None
            if c["pace"]:
                left = max(1, c["max_rounds"] - rounds)
                per_round = max(1, (c["max_local"] - self.B.local) // left)
                per_plan = max(1, per_round // max(1, len(frontier)))
            for P in frontier:
                self._allow = self.B.local + per_plan if per_plan else None
                h = self.hr(P)
                for u in self.local(h, min(3, c["cap"] - len(P)), "T0"):
                    for s in self.expand(P, u, set(), set(), c["cap"] - len(P), 0):
                        r = P + s
                        if DA.check_sequence(self.row0, r) is not None or json.dumps(r) in self.cands:
                            continue
                        self.cands[json.dumps(r)] = None
                        nxt.append(r)
                    if self.B.out() or self._out_unit():
                        break
                self._allow = None
                if self.B.out():
                    break
            uniq = {}
            for r in nxt:
                if self.cands.get(json.dumps(r)) is None:
                    uniq.setdefault(json.dumps(r), r)
            nxt = list(uniq.values())
            for r in nxt:
                self.cands[json.dumps(r)] = None
            if not nxt:
                break
            en = self.energy(nxt)
            for r, e in zip(nxt, en):
                self.cands[json.dumps(r)] = e
            stop_hY = c["stop_on_hY"]
            live = sorted([(e["C"], len(r), json.dumps(r), r) for r, e in zip(nxt, en)
                           if len(r) < c["cap"] and (not stop_hY or e["hY"] < c["theta_done"])])
            frontier, firsts = [], {}
            for _, _, _, r in live:
                k = json.dumps(r[:1])
                if firsts.get(k, 0) >= 2:
                    continue
                firsts[k] = firsts.get(k, 0) + 1
                frontier.append(r)
                if len(frontier) >= c["B_top"]:
                    break
            rounds += 1
            scored = [v for v in self.cands.values() if v is not None]
            best_hist.append(min(v["C"] for v in scored))
            self.log["rounds"].append({"round": rounds, "new": len(nxt), "frontier": [[list(x) for x in r] for r in frontier],
                                       "best_C": best_hist[-1], "best_hY": max(e["hY"] for e in en), "local_used": self.B.local,
                                       "len_hist": {str(L): sum(1 for r in nxt if len(r) == L) for L in sorted({len(r) for r in nxt})}})
            S = c["stagnation_rounds"]
            if S and len(best_hist) > S and best_hist[-1] >= best_hist[-1 - S] - 1e-9:
                self.B.reason = self.B.reason or "STAGNATION"
                break
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
