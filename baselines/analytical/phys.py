"""Physical layer shared by the three planners: exact call accounting, budgets, caches keyed by PHYSICAL state identity.

PhysBase implements every rule once (tests drive it with a toy backend):
  reset() -> state            the initial state (q = q_ref, free gripper)
  step(state, o, d) -> state  one relocation executed from the CARRIED state (robot q / gripper / physics of the previous step, never
                              reset to q_ref, no interim connector); None = failed or UNKNOWN (capped) -- a planner failure, never a label
  terminal(state) -> 1/0/None X terminal connector to q_ref from the carried state (skipped Y when X = 0) + Y target from q_ref in the
                              canonical endpoint scene (cached by endpoint -> order independent); None = UNKNOWN
  ref_paths()                 obstacle-ignorant target plans (several grasp homotopies) and their swept cells, planned once per run
  blockers(path, state)       objects of the current hypothetical scene in that path's sweep (recomputed for every scene)
  key(state)                  physical identity = cells + moved set + achieved q + gripper (+ 2D planner-budget counters, 3D object
                              poses), NOT the order of the prefix: two orders reaching the same physical state are one state, two
                              orders with the same cells but different q are two states (E-M4M transposition fix)
Accounting: transition / connector / Y / reference-plan calls, cache hits, capped (UNKNOWN) calls, CPU and wall seconds.  Budgets: run
CPU seconds (time.process_time, the whole process = planner + physics), administrative wall seconds, per-call CPU cap (SIGVTALRM; the 2D
teacher uses SIGPROF and fin3d SIGALRM, so no conflict).  Exceeding the run budget raises Exhausted (a BaseException: teacher-side
`except Exception` cannot swallow it)."""
from __future__ import annotations

import collections
import hashlib
import json
import signal
import time

import numpy as np

from .contract import K_MAX, legality
from .geo import Geo


class Exhausted(BaseException):
    """The run's CPU / wall / call budget is spent (termination reason TIMEOUT)."""


class _Cap(BaseException):
    pass


def _vt(*_):
    raise _Cap()


class PhysBase:
    def __init__(self, row: dict, budget_s: float | None = None, wall_s: float | None = None, call_cap_s: float | None = None,
                 max_calls: int | None = None):
        self.row, self.inp, self.dom = row, row["inputs"], row["domain"]
        self.geo = Geo(row)
        self.budget_s, self.wall_s, self.call_cap_s, self.max_calls = budget_s, wall_s, call_cap_s, max_calls
        self.n = collections.Counter()
        self._t0, self._w0 = time.process_time(), time.time()
        self._steps, self._term, self._ref = {}, {}, None
        self.unknown_keys: set = set()

    # ------------------------------------------------------------------ accounting / budgets
    def cpu(self) -> float:
        return time.process_time() - self._t0

    def wall(self) -> float:
        return time.time() - self._w0

    def physical_calls(self) -> int:
        return self.n["transition_calls"] + self.n["connector_calls"] + self.n["y_calls"] + self.n["ref_plan_calls"]

    def gate(self):
        if self.budget_s is not None and self.cpu() >= self.budget_s:
            raise Exhausted("cpu")
        if self.wall_s is not None and self.wall() >= self.wall_s:
            raise Exhausted("wall")
        if self.max_calls is not None and self.physical_calls() >= self.max_calls:
            raise Exhausted("calls")

    def _timed(self, fn, cap=None):
        """fn() under a CPU timer min(call cap, remaining run budget). -> (result, capped)."""
        self.gate()
        cap = self.call_cap_s if cap is None else cap
        rem = None if self.budget_s is None else self.budget_s - self.cpu()
        lim = min(x for x in (cap, rem, 1e9) if x is not None)
        old = signal.signal(signal.SIGVTALRM, _vt)
        signal.setitimer(signal.ITIMER_VIRTUAL, max(lim, 1e-3))
        try:
            return fn(), False
        except _Cap:
            if rem is not None and lim >= rem - 1e-6:
                raise Exhausted("cpu") from None
            self.n["capped_calls"] += 1
            return None, True
        finally:
            signal.setitimer(signal.ITIMER_VIRTUAL, 0)
            signal.signal(signal.SIGVTALRM, old)

    def stats(self) -> dict:
        return {**dict(sorted(self.n.items())), "physical_calls": self.physical_calls(), "cpu_s": round(self.cpu(), 3),
                "wall_s": round(self.wall(), 3)}

    # ------------------------------------------------------------------ cached physical queries
    def reset(self):
        self.gate()
        return self._reset()

    def key(self, state):
        return self._ident(state)

    def step(self, state, o: int, d: int):
        prefix = list(self.prefix(state)) + [(int(o), int(d))]
        if len(prefix) > K_MAX or legality(self.inp, self.dom, prefix) is not None:
            self.n["illegal_rejected"] += 1                                # never sent to physics
            return None
        k = (self.key(state), int(o), int(d))
        if k in self._steps:
            self.n["transition_cache_hits"] += 1
            return self._steps[k]
        self.n["transition_calls"] += 1
        res, capped = self._timed(lambda: self._step(state, int(o), int(d)))
        if capped or res == "UNKNOWN":
            self.n["transition_unknown"] += 1
            self.unknown_keys.add(k)
            res = None
        elif res is None:
            self.n["transition_failed"] += 1
        self._steps[k] = res
        return res

    def terminal(self, state):
        """-> 1 / 0 / None (UNKNOWN). X = terminal connector from the carried state; Y = target from q_ref at the endpoint."""
        k = self.key(state)
        if k in self._term:
            self.n["terminal_cache_hits"] += 1
            return self._term[k]
        self.n["terminal_queries"] += 1
        res, capped = self._timed(lambda: self._terminal(state))
        z = None if capped else res
        if z is None:
            self.n["terminal_unknown"] += 1
        self._term[k] = z
        return z

    def ref_paths(self, cap=None) -> list[dict]:
        if self._ref is None:
            res, capped = self._timed(self._ref_paths, cap)
            self._ref = [] if capped or res is None else res
            self.n["ref_paths_verified"] = len(self._ref)
        return self._ref

    def blockers(self, path: dict, state) -> set[int]:
        """Objects of the scene `state` in the path's swept cells (plus, while unmoved, objects the path hits in the initial scene).
        The target is never a blocker; 2D fixed objects are excluded (the reference plans keep them, so the path avoids them)."""
        cells, moved = self.cells(state), {o for o, _ in self.prefix(state)}
        tid = int(self.inp["tid"])
        fixed = [bool(a[3]) for a in self.inp["attrs"]] if self.dom == "2d" else [False] * len(cells)
        out = {i for i, c in enumerate(cells) if i != tid and not fixed[i] and int(c) in path["sweep"]}
        return out | {i for i in path.get("hits", ()) if i not in moved and i != tid}

    # ------------------------------------------------------------------ state access (FullState-compatible)
    @staticmethod
    def cells(state):
        return list(state.cells)

    @staticmethod
    def prefix(state):
        return [tuple(p) for p in state.prefix]

    @staticmethod
    def q(state):
        return list(state.q_t)

    # backends implement:
    def _reset(self): raise NotImplementedError
    def _ident(self, state): raise NotImplementedError
    def _step(self, state, o, d): raise NotImplementedError          # -> state | None (physically failed) | "UNKNOWN"
    def _terminal(self, state): raise NotImplementedError           # -> 1 / 0 / None
    def _ref_paths(self): raise NotImplementedError                 # -> [{"sweep": set(cells), "hits": set(indices)}]


def _h(*parts) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p if isinstance(p, bytes) else json.dumps(p, sort_keys=True, default=str).encode())
    return h.hexdigest()[:32]


class RealPhys(PhysBase):
    """The DISCO-Grid stage-2 stateful adapter (RepairEnv: unchanged 2D BXY / 3D fin3d+bwlphys physics) + NOR-Grid reference paths."""

    def __init__(self, env, row: dict, n_ref: int = 6, n_ref_try: int = 12, ref_cap_s: float | None = 120.0, **kw):
        super().__init__(row, **kw)
        self.env, self.n_ref, self.n_ref_try, self.ref_cap_s = env, n_ref, n_ref_try, ref_cap_s

    def _reset(self):
        return self.env.reset(self.row["root_id"])

    def _ident(self, s):
        pay = s.physics_payload
        if s.domain == "2d":
            return _h(s.cells, s.moved_mask, np.round(np.asarray(s.q_t, float), 7).tobytes(), round(float(s.gripper_state["gap"]), 7),
                      pay.get("used", {}))
        return _h(s.cells, s.moved_mask, np.round(np.asarray(s.q_t, float), 6).tobytes(), s.gripper_state.get("held"),
                  np.round(np.asarray(pay.get("qpos", []), float), 6).tobytes(), np.round(np.asarray(pay.get("qvel", []), float), 6).tobytes())

    def _step(self, s, o, d):
        sr = self.env.transition(s, (o, d))
        acc = sr.accounting or {}
        if acc.get("grasp_attempts_reported"):
            self.n["grasp_attempts"] += int(acc["grasp_attempts_reported"])
        if sr.status == "EXECUTED":
            return sr.next_state
        self.n["fail_" + str(sr.failure_kind)] += 1
        return "UNKNOWN" if sr.status == "UNRESOLVED" else None

    def _terminal(self, s):
        r = self.env.terminal_query(s, evaluate_y_on_x_fail=False)
        acc = r.accounting or {}
        for k in ("connector_calls", "y_calls", "y_cache_hits"):
            self.n[k] += int(acc.get(k) or 0)
        self.n["terminal_x_" + str(r.x_terminal)] += 1
        if r.x_terminal == 1:
            self.n["terminal_y_" + str(r.y_target)] += 1
        return r.z_outcome

    def ref_paths(self, cap=None):
        return super().ref_paths(self.ref_cap_s if cap is None else cap)

    def _ref_paths(self):
        import homotopy as HO                                           # NOR-Grid (read-only import), modules injected from the env
        be = self.env.backend
        be.boot()
        rid = self.row["root_id"]
        rec = self.env._raw_by_id[rid]
        HO.N_OK, HO.N_TRY = self.n_ref, self.n_ref_try
        if self.dom == "2d":
            be._sync_geom(rec)
            import bd_2d, bd_2d_exact, p14_sweep_index
            HO._M.update(A=bd_2d, E=bd_2d_exact, SX=p14_sweep_index, G=bd_2d.env())
            r = HO.root_paths(rec)
        else:
            HO._M.update(A=be.A, TS=be.S)
            r = HO.root_paths3d(rec)
        self.n["ref_plan_calls"] += int(r.get("n_tried", 0))
        ids = self.inp["ids"]
        return [{"sweep": {int(c) for c in p["sweep"]}, "hits": {ids.index(b) for b in p.get("blockers", []) if b in ids},
                 "id": i} for i, p in enumerate(r["paths"]) if p["status"] == "VERIFIED"]
