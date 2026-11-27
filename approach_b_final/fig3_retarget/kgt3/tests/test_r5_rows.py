"""R5.0 real-row contract tests (gvlab2: needs the DEV panels; skipped elsewhere).  Hypothetical rebasing, temporary-task roles, initially
vacant distinct destinations, move-once, original-target protection, H = 5 cap."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "r3"), str(HERE.parent / "r24"), str(HERE.parent.parent)]


def rows(dom):
    try:
        import p3 as P3
        return [(rid, row, W) for rid, row, _, W, _ in P3.panel(dom)][:6]
    except Exception:  # noqa: BLE001
        pytest.skip("DEV panels not available here")


@pytest.mark.parametrize("dom", ["2d", "3d"])
def test_rebase_moves_only_prefix_and_keeps_original_forbidden(dom):
    import views as V
    for rid, row, W in rows(dom):
        r0 = {"root_id": row["root_id"], "domain": dom, "inputs": row["inputs"]}
        o, d = map(int, W[0])
        S = V.rebase(r0, [[o, d]])
        i0, i1 = r0["inputs"], S["inputs"]
        assert i1["cells0"][o] == d and list(i1["xy0"][o]) == list(i0["cell_xy"][str(d)])
        assert all(i1["cells0"][j] == i0["cells0"][j] and i1["xy0"][j] == i0["xy0"][j] for j in range(len(i0["ids"])) if j != o)
        bad = set(map(int, i0["cells0"])) | {int(i0["goal_cell"])}
        assert not bad & set(map(int, i1["legal_cells"])), "rebased legal cells must exclude ORIGINAL occupancy and goal"
        assert int(i0["cells0"][o]) not in i1["legal_cells"], "a vacated cell never becomes legal (initially vacant only)"
        assert i1["tid"] == i0["tid"] and i1["goal_cell"] == i0["goal_cell"] and i1["q_ref"] == i0["q_ref"]


@pytest.mark.parametrize("dom", ["2d", "3d"])
def test_temporary_task_roles_and_original_target_protection(dom):
    import views as V
    for rid, row, W in rows(dom):
        r0 = {"root_id": row["root_id"], "domain": dom, "inputs": row["inputs"]}
        o, d = map(int, W[0]); t0 = int(r0["inputs"]["tid"])
        T = V.rebase(r0, [], task=(o, d))
        it = T["inputs"]
        assert it["tid"] == o and it["goal_cell"] == d and list(it["goal"]) == list(r0["inputs"]["cell_xy"][str(d)])
        if dom == "2d":
            assert it["attrs"][o][1] == 1.0 and it["attrs"][o][2] == 0.0 and it["attrs"][t0][1] == 0.0 and it["attrs"][t0][2] == 1.0
            assert all(it["attrs"][j][0] == r0["inputs"]["attrs"][j][0] and it["attrs"][j][3] == r0["inputs"]["attrs"][j][3] for j in range(len(it["attrs"])))
        else:
            assert [a[4] for a in it["attrs"]] == [float(j == o) for j in range(len(it["attrs"]))]
        assert t0 not in V.eligible(r0, protect=[o]) and o not in V.eligible(r0, protect=[o])
        assert it["cells0"] == r0["inputs"]["cells0"] and it["q_ref"] == r0["inputs"]["q_ref"]


@pytest.mark.parametrize("dom", ["2d", "3d"])
def test_grammar_move_once_distinct_initially_vacant_and_H5(dom):
    import planners as PL
    import views as V
    assert PL.CFG["H"][dom] == 5
    for rid, row, W in rows(dom):
        r0 = {"root_id": row["root_id"], "domain": dom, "inputs": row["inputs"]}
        W = [list(map(int, a)) for a in W]
        assert V.legal_seq(r0, W, 5) == (len(W) <= 5)
        o, d = W[0]
        assert not V.legal_seq(r0, [[o, d], [o, W[1][1]]], 5), "move-once"
        assert not V.legal_seq(r0, [[o, d], [W[1][0], d]], 5), "distinct destinations"
        assert not V.legal_seq(r0, [[o, d], [W[1][0], int(r0["inputs"]["cells0"][o])]], 5), "vacated cell is not a legal destination"
        assert not V.legal_seq(r0, [[int(r0["inputs"]["tid"]), d]], 5), "original target never moves"
        assert not V.legal_seq(r0, [[o, int(r0["inputs"]["goal_cell"])]], 5), "goal cell never a destination"
        free = [int(c) for c in r0["inputs"]["legal_cells"] if int(c) not in V.forbidden(r0)]
        el = V.eligible(r0)
        if len(el) >= 6 and len(free) >= 6:
            assert not V.legal_seq(r0, [[j, c] for j, c in zip(el[:6], free[:6])], 5), "H = 5 cap"
