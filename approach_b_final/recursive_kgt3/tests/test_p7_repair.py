"""P7A repair beam: deterministic synthetic fixtures (mock oracle phi / y_end, no frozen model), invariants, budget accounting,
leakage.   python -m pytest tests/test_p7_repair.py -q"""
import json, sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "tests"))
import p7_repair as R  # noqa: E402
from test_p6_order import code_tokens  # noqa: E402


def scene(cells, T0, G0, root="fx"):
    return {"root_id": root, "inputs": {"cell_xy": {str(c): [0.04 + 0.08 * (c % 8), 0.04 + 0.08 * (c // 8)] for c in range(64)}, "cells0": cells,
                                        "tid": T0, "goal_cell": G0, "legal_cells": list(range(64)), "attrs": [[0.024, 0, 1, 0]] * len(cells),
                                        "base": [-0.14, 0.32], "ids": [f"o{i:02d}" for i in range(len(cells))]}}


class Oracle:
    """Static oracle: pick of o dead if another object occupies a cell in pb[o]; place at d dead if another object occupies qb[d]."""
    def __init__(s, row, pb, qb):
        s.c0, s.T0, s.G0, s.pb, s.qb = row["inputs"]["cells0"], row["inputs"]["tid"], row["inputs"]["goal_cell"], pb, qb

    def cells(s, plan):
        c = list(s.c0)
        for o, d in plan:
            c[o] = d
        return c

    def live(s, cells, o, d):
        oth = {x for i, x in enumerate(cells) if i != o}
        return not (oth & s.pb.get(o, set())) and not (oth & s.qb.get(d, set()))

    def phiY(s, plan, o, d):
        return 0.9 if s.live(s.cells(plan), o, d) else 0.01

    def yend(s, seqs):
        return [0.9 if s.live(s.cells(q), s.T0, s.G0) else 0.05 for q in seqs]

    def valid(s, plan):
        c = list(s.c0)
        for o, d in plan:
            if not s.live(c, o, d):
                return False
            c[o] = d
        return s.live(c, s.T0, s.G0)


def solve(row, orc, A, arm, cvae=None, cfg=None):
    rp = R.Repair(row, orc.phiY, orc.yend, cvae or {}, arm, cfg or R.CFG, mode="Y")
    out = rp.run(A)
    import data as DA
    for t in out["top"]:                                        # invariants on every returned candidate
        assert DA.check_sequence(row, t["plan"]) is None and len(t["plan"]) <= 12 and row["inputs"]["tid"] not in [o for o, _ in t["plan"]]
    return out, (bool(out["top"]) and orc.valid([tuple(m) for m in out["top"][0]["plan"]]))


# T0 = obj0 at cell 0; goal G0 = 18 (row 2, col 2)
def f1():          # missing pickup enabler: a (19) blocks the goal; a's pick is blocked by n (20), which is NOT in A
    row = scene([0, 19, 20, 45], 0, 18); return row, Oracle(row, {1: {20}}, {18: {19}}), [(1, 60)]


def f2():          # destination-induced: b (17) blocked by a at its source (19)... and by a's original destination 9
    row = scene([0, 19, 17, 45], 0, 18); return row, Oracle(row, {2: {19, 9}}, {18: {19, 17}}), [(1, 9), (2, 60)]


def f3():          # two-level chain: a (19) <- n1 (20) <- n2 (21)
    row = scene([0, 19, 20, 21, 45], 0, 18); return row, Oracle(row, {1: {20}, 2: {21}}, {18: {19}}), [(1, 60)]


def f4():          # redundant original mover r (40) plays no role
    row = scene([0, 19, 40, 45], 0, 18); return row, Oracle(row, {}, {18: {19}}), [(1, 60), (2, 62)]


def f5():          # 12-move cap: a needs enabler n; 11 redundant movers -> 13 > 12, a replacement is forced
    fill = [33, 35, 37, 39, 49, 51, 53, 55, 57, 59, 61]
    row = scene([0, 19, 20] + fill, 0, 18)
    A = [(1, 6)] + [(3 + i, d) for i, d in enumerate([24, 26, 28, 30, 40, 42, 44, 46, 56, 58, 62])]
    return row, Oracle(row, {1: {20}}, {18: {19}}), A


@pytest.mark.parametrize("fx", [f1, f2, f3, f4, f5])
def test_full_solves_fixture(fx):
    row, orc, A = fx()
    out, ok = solve(row, orc, A, "FULL", cvae={1: [9]})
    assert ok, (fx.__name__, out["top"][:1], out["stop"])


def test_enabler_absent_from_original_set_is_discovered():
    row, orc, A = f1(); out, ok = solve(row, orc, A, "FULL")
    top = out["top"][0]
    assert ok and top["added"] and top["added"][0][0] == 2 and 2 not in [o for o, _ in A] and 2 in out["suspects_S0"]
    assert [m[0] for m in top["plan"]].index(2) < [m[0] for m in top["plan"]].index(1)       # enabler inserted BEFORE the dependent move


def test_chain_and_cap_replacement():
    row, orc, A = f3(); out, ok = solve(row, orc, A, "FULL")
    order = [m[0] for m in out["top"][0]["plan"]]
    assert ok and order.index(3) < order.index(2) < order.index(1)
    row, orc, A = f5(); out, ok = solve(row, orc, A, "FULL")
    t = out["top"][0]
    assert ok and len(t["plan"]) == 12 and t["dropped"] and 2 in [m[0] for m in t["plan"]]


def test_matched_controls_fail_where_expected():
    for fx in (f1, f3, f5):                                       # no enabler possible without object-set change
        row, orc, A = fx(); assert not solve(row, orc, A, "DEST_ONLY")[1], fx.__name__
    row, orc, A = f2()
    assert solve(row, orc, A, "DEST_ONLY", cvae={1: [9]})[1]       # destination change suffices
    assert not solve(row, orc, A, "OBJSET_ONLY", cvae={1: [9]})[1]  # original destinations kept -> blocked
    assert solve(row, orc, A, "FULL", cvae={1: [9]})[1]


def test_rebuild_when_first_pass_cannot_complete():
    row = scene([0, 19, 33, 35, 45], 0, 18); orc = Oracle(row, {}, {18: {19}})
    cfg = dict(R.CFG, layers=2)                                   # 3 required moves cannot complete in 2 layers; the target-near core can
    out, ok = solve(row, orc, [(1, 60), (2, 62), (3, 63)], "FULL", cfg=cfg)
    assert out["rebuilt"] and ok and [m[0] for m in out["top"][0]["plan"]] == [1]


def test_budget_is_respected_and_matched():
    row, orc, A = f5()
    for arm in ("FULL", "DEST_ONLY", "OBJSET_ONLY", "FLAT", "RANDOM"):
        cfg = dict(R.CFG, PHI_MAX=40, Y_MAX=10)
        out, _ = solve(row, orc, A, arm, cfg=cfg)
        assert out["used"]["phi"] <= 40 + 4 * cfg["keep"] and out["used"]["y"] <= 10 + 4 * cfg["keep"], (arm, out["used"])


def test_deterministic():
    row, orc, A = f5()
    assert solve(row, orc, A, "FULL")[0] == solve(row, orc, A, "FULL")[0]
    assert solve(row, orc, A, "RANDOM")[0] == solve(row, orc, A, "RANDOM")[0]


def test_public_module_has_no_privileged_inputs():
    src = code_tokens(HERE / "p7_repair.py")
    for bad in ("p5_order_audit", "p5b_physical", "p6_eval", "p7_eval", "dev_eval", "MINK", "QCLEAR", "Static", "dev_private", "dev_records",
                "witness", "verify", "teacher", "K_certified", "unmoved_blockers", "P5B", "q23", "e3c632"):
        assert bad not in src, bad
    for f in ("data.py", "models.py", "planner.py", "planner_r.py", "run_p4.py", "p6_order.py"):
        assert "p7_repair" not in code_tokens(HERE / f) and "p7_eval" not in code_tokens(HERE / f)
