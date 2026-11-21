#!/usr/bin/env python3
"""BXY_X_TEACHER_V2_LONG / BXY_Y_TEACHER_V2_LONG: separately versioned <= 12-relocation extension of the frozen 2D teacher
(bxy_teacher c18ac91c89b9 / p16_motion 43f4c38c6418 / p15_search 9c2af1373798).  No frozen file is modified.

  len(seq) <= 6 : the frozen bxy_teacher.x_query / y_query, called unchanged (byte-identical rows; 'teacher' stays V1).
  7 <= len <= 12: the SAME frozen x_query / y_query code path with exactly two substitutions for the duration of the call:
      eligible -> long_eligible  : bd_core.check_sequence's 7-action cap raised to MAX_REL + 1 = 13; every other eligibility rule unchanged
                                   (movable objects only, never the target, no object twice, legal destinations).
      _phys    -> LongPhysics    : p16_motion.DetPhysics with the IDENTICAL budget dict (bd_2d.QB, so str(budget) and every planner RNG key
                                   are unchanged); only the accounting of 'online_moves' changes: a fresh allowance of QB['online_moves']
                                   per relocation (DetPhysics.edges call) under an explicit total cap ONLINE_TOTAL.  The frozen X uses
                                   exactly one online move per relocation (idx = None: no edge library), so for <= 8 relocations the
                                   result equals the frozen computation; beyond 8 the frozen shared budget would censor relocation 9.
  Unchanged: geometry, collision checks, grasp candidates, skill planner + node budgets, certificates, carried robot state, the terminal
  connector (transit_plans budget unchanged, one connector), independent replay_x / replay_y, Y = bd_2d.t_goal from q_ref.
    python teacher_long.py selftest      (needs the frozen 2D environment booted through mink.boot)"""
import contextlib, json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mink as MK  # noqa: E402

MAX_REL = 12
X_LONG, Y_LONG = "BXY_X_TEACHER_V2_LONG", "BXY_Y_TEACHER_V2_LONG"
_C = {}


def _classes():
    if "LongPhysics" in _C:
        return _C
    import bd_2d
    import p16_motion as pm
    total = MAX_REL * bd_2d.QB["online_moves"]

    class LongPhysics(pm.DetPhysics):
        """Per-relocation online-move allowance (budget dict unchanged); explicit total cap; everything else inherited."""
        ONLINE_PER_REL, ONLINE_TOTAL = bd_2d.QB["online_moves"], total

        def __init__(self, *a, total_cap=None, **k):
            super().__init__(*a, **k)
            self._rel_used, self._online_total, self._cap = 0, 0, total if total_cap is None else total_cap

        def edges(self, cells, q, o, d):
            self._rel_used = 0                               # a new relocation decision starts here (x_query: one edges call per relocation)
            return super().edges(cells, q, o, d)

        def _take(self, k):
            if k != "online_moves":
                return super()._take(k)
            if self._rel_used >= self.ONLINE_PER_REL or self._online_total >= self._cap or self.truncated():
                self.exhausted.add(k)
                return False
            self._rel_used += 1; self._online_total += 1; self.used[k] += 1
            return True
    _C["LongPhysics"] = LongPhysics
    return _C


def long_eligible(rec, seq):
    """bxy_teacher.eligible with the action cap raised to MAX_REL corrective relocations (+ the final target action)."""
    movable = set(rec["roles"])
    if any(o == "t0" for o, _ in seq):
        return "the target T may not be a corrective relocation"
    if len(seq) > MAX_REL:
        return f"{len(seq)} relocations > {MAX_REL}"
    if any(o not in movable for o, _ in seq):
        return "moves a non-movable object (target or fixed structure)"
    if len({o for o, _ in seq}) != len(seq):
        return "duplicate relocation of one object"
    if any(int(d) not in rec["scene"]["legal_cells"] for _, d in seq):
        return "destination outside the legal supported cells"
    return None


@contextlib.contextmanager
def _patched(BT, total_cap=None):
    import bd_2d
    LP = _classes()["LongPhysics"]
    old = (BT.eligible, BT._phys)
    BT.eligible = long_eligible
    BT._phys = lambda k, rec, cache: LP(BT.task_of(k, rec), None, budget=dict(bd_2d.QB), cache=cache, total_cap=total_cap)
    try:
        yield
    finally:
        BT.eligible, BT._phys = old


def _meta(row, kind, n):
    row = dict(row)
    row["teacher"] = (X_LONG if kind == "X" else Y_LONG) if n > 6 else row.get("teacher")
    row["teacher_long"] = {"version": X_LONG if kind == "X" else Y_LONG, "max_relocations": MAX_REL, "dispatch": "frozen" if n <= 6 else "long",
                           "online_moves_per_relocation": _classes()["LongPhysics"].ONLINE_PER_REL, "online_moves_total_cap": _classes()["LongPhysics"].ONLINE_TOTAL}
    return row


def x_query(E, k, rec, seq, cache, out=None, total_cap=None):
    import bxy_teacher as BT
    seq = [(o, int(d)) for o, d in seq]
    if len(seq) <= 6 and total_cap is None:
        return _meta(BT.x_query(E, k, rec, seq, cache, out=out), "X", len(seq))
    with _patched(BT, total_cap):
        return _meta(BT.x_query(E, k, rec, seq, cache, out=out), "X", len(seq))


def y_query(E, k, rec, seq, cache, out=None):
    import bxy_teacher as BT
    seq = [(o, int(d)) for o, d in seq]
    if len(seq) <= 6:
        return _meta(BT.y_query(E, k, rec, seq, cache, out=out), "Y", len(seq))
    with _patched(BT):
        return _meta(BT.y_query(E, k, rec, seq, cache, out=out), "Y", len(seq))


def frozen_bypass_x(E, k, rec, seq, cache):
    """PARITY REFERENCE ONLY: the frozen x_query with ONLY the eligibility cap lifted (frozen shared budget kept)."""
    import bxy_teacher as BT
    old = BT.eligible
    BT.eligible = long_eligible
    try:
        return BT.x_query(E, k, rec, [(o, int(d)) for o, d in seq], cache)
    finally:
        BT.eligible = old
