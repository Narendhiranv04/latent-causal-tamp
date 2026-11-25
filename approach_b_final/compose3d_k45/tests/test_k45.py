"""Contract tests (plan.md 5).  Real-bundle tests use exposed 3D DEV public rows and skip without CUDA / files."""
import itertools, json, math, sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import scene as SC  # noqa: E402
import compose as CP  # noqa: E402
import recursive as RC  # noqa: E402

DEV = Path.home() / "k45_private/dev/public_val_3d.jsonl"


@pytest.fixture(scope="module")
def fz():
    import torch
    if not DEV.exists() or not torch.cuda.is_available():
        pytest.skip("no DEV rows / CUDA")
    from models import Frozen
    return Frozen()


@pytest.fixture(scope="module")
def rows():
    if not DEV.exists():
        pytest.skip("no DEV rows")
    return [json.loads(l) for l in open(DEV)]


def big(rows, n=6):
    return next(r for r in rows if len(r["inputs"]["ids"]) >= n)


# ------------------------------------------------------------------------------------------------ scene / grammar
def test_rebase_identity_and_pose_update(rows):
    r = big(rows)
    s = SC.rebase(r, [])
    assert {k: v for k, v in s["inputs"].items() if k != "legal_cells"} == {k: v for k, v in r["inputs"].items() if k != "legal_cells"}
    mv = [i for i in range(len(r["inputs"]["ids"])) if i != r["inputs"]["tid"]][0]
    free = [c for c in range(36) if c not in SC.forbidden(r)][0]
    s = SC.rebase(r, [[mv, free]])
    assert s["inputs"]["cells0"][mv] == free and s["inputs"]["xy0"][mv] == r["inputs"]["cell_xy"][str(free)]
    for i in range(len(r["inputs"]["ids"])):
        assert s["inputs"]["attrs"][i] == r["inputs"]["attrs"][i]                        # geometry / height / target flag untouched
        if i != mv:
            assert s["inputs"]["cells0"][i] == r["inputs"]["cells0"][i]
    assert r["inputs"]["cells0"][mv] != free                                             # no aliasing of the original row


def test_retarget_flags_ctx_goal_and_height(rows):
    r = big(rows)
    inp = r["inputs"]; A = [i for i in range(len(inp["ids"])) if i != inp["tid"]][0]
    d = [c for c in range(36) if c not in SC.forbidden(r)][0]
    t = SC.rebase(r, [], task=(A, d))["inputs"]
    g, ts = SC.ctx_slots(inp)
    assert t["tid"] == A and t["goal_cell"] == d and t["goal"] == inp["cell_xy"][str(d)]
    assert [a[4] for a in t["attrs"]] == [float(i == A) for i in range(len(inp["ids"]))]
    assert t["ctx"][g] == t["goal"] and t["ctx"][ts] == [inp["attrs"][A][2], inp["attrs"][A][3], inp["attrs"][A][0]]
    assert t["ctx"][:g.start] == inp["ctx"][:g.start]                                    # q_ref sin / cos kept
    assert [a[3] for a in t["attrs"]] == [a[3] for a in inp["attrs"]]                    # height never mutated
    back = SC.rebase(r, [], task=(inp["tid"], inp["goal_cell"]))["inputs"]                # roundtrip to the original task
    assert back["ctx"] == inp["ctx"] and back["attrs"] == inp["attrs"] and back["tid"] == inp["tid"]


def test_task_features_of_retargeted_row(rows):
    import numpy as np
    import placement as PL
    r = big(rows); inp = r["inputs"]
    A = [i for i in range(len(inp["ids"])) if i != inp["tid"]][0]; d = [c for c in range(36) if c not in SC.forbidden(r)][0]
    t = SC.rebase(r, [], task=(A, d))["inputs"]
    q = [i for i in range(len(inp["ids"])) if i not in (A, inp["tid"])][0]
    f = PL.task_features("3d", t, t["cells0"], q)
    assert f[d] == 1 and f[:36].sum() == 1 and f[36 + t["cells0"][A]] == 1 and f[36:72].sum() == 1
    assert np.allclose(f[72 + 4:-1], t["ctx"])


def test_reservations_and_grammar(rows):
    import search as S
    r = big(rows); inp = r["inputs"]
    mv = [i for i in range(len(inp["ids"])) if i != inp["tid"]]
    free = [c for c in range(36) if c not in SC.forbidden(r)]
    s = SC.rebase(r, [[mv[0], free[0]]], reserved=[free[1]])
    R = S.Root(s, "3d"); L = set(R.legal_dests(R.cells0))
    assert inp["cells0"][mv[0]] not in L                                                 # vacated original cell never reused
    assert inp["goal_cell"] not in L and free[1] not in L and free[0] not in L
    assert SC.legal_seq(r, [[mv[0], free[0]], [mv[1], free[1]]])
    assert not SC.legal_seq(r, [[mv[0], free[0]], [mv[0], free[1]]])                     # moved twice
    assert not SC.legal_seq(r, [[inp["tid"], free[0]]])                                  # original target
    assert not SC.legal_seq(r, [[mv[0], inp["cells0"][mv[1]]]])                          # originally occupied
    assert not SC.legal_seq(r, [[mv[0], inp["goal_cell"]]])
    assert SC.eligible(r, used=[mv[0]], pending=[mv[1]], task_obj=mv[2]) == [i for i in range(len(inp["ids"])) if i not in (inp["tid"], mv[0], mv[1], mv[2])]


def test_splits_groups_and_order_counts():
    assert SC.splits(4) == [(1, 3), (2, 2), (3, 1)] and SC.splits(5) == [(2, 3), (3, 2)] and SC.splits(3) == [(3,)]
    seq = [[i, 10 + i] for i in range(5)]
    assert [len(g) for g in SC.groups(seq, (2, 3))] == [2, 3]
    assert len(list(itertools.permutations(seq))) * len(SC.splits(5)) == 240 and 24 * 3 == 72


def test_respecting_orders():
    seq = [[1, 5], [2, 6], [3, 7]]
    o = RC.respecting(seq, [(0, "BEFORE", 1)])
    assert all(o_.index([1, 5]) < o_.index([2, 6]) for o_ in o) and len(o) == 3


def test_choose_gate_and_abstain(rows):
    r = big(rows)
    rule = {"noop_gate": 0.5, "eta": 0.3}
    assert CP.choose(r, [{"seq": [], "p": 0.6}, {"seq": [[1, 2]], "p": 0.99}], rule)[1] == "NOOP_GATE"
    assert CP.choose(r, [{"seq": [], "p": 0.1}, {"seq": [[1, 2]], "p": 0.2}], rule)[0] is None
    assert CP.choose(r, [{"seq": [], "p": 0.1}, {"seq": [[1, 2]], "p": 0.4}, {"seq": [[1, 2], [3, 4]], "p": 0.4}], rule)[0]["seq"] == [[1, 2]]


# ------------------------------------------------------------------------------------------------ synthetic B4 chain (stub models)
class Stub:
    """Toy: object 2 -> cell 30 is blocked (temporary pY low) unless object 3 has moved; original-target Y needs object 2 moved."""
    def __init__(self):
        self.c = {"x_unique": 0, "y_unique": 0, "proposal_calls": 0, "latent_draws": 0, "batches": 0, "cache_hits": 0}

    def proposals(self, row, objs, m=4):
        return {o: [c for c in (30, 31, 32, 33) if c in row["inputs"]["legal_cells"]][:m] for o in objs}

    def p_noop(self, row):
        inp = row["inputs"]
        if inp["tid"] == 2:
            return 0.9 if inp["cells0"][3] != 13 else 0.1
        return 0.05

    def score(self, row, seqs):
        return [{"p11": 0.5, "px": 0.8, "py": 0.6, "px1": 0.8, "px0": 0.5} if s else {"p11": self.p_noop(row)} for s in seqs]

    def y_global(self, row0, eps):
        return [0.9 if any(int(o) == 2 for o, _ in e) else 0.1 for e in eps]


def toy():
    cells0 = [0, 12, 2, 13, 5]
    inp = {"ids": ["t0", "a", "b", "c", "d"], "cells0": cells0, "xy0": [[0.0, 0.0]] * 5, "attrs": [[1, 0, .02, .15, float(i == 0)] for i in range(5)],
           "tid": 0, "goal": [0.0, 0.0], "goal_cell": 35, "base": [0, 0], "ctx": [0.0] * 19, "grid": [6, 6], "legal_cells": list(range(36)),
           "q_ref": [0.0] * 7, "cell_xy": {str(c): [c * 0.1, 0.0] for c in range(36)}}
    return {"root_id": "toy", "domain": "3d", "inputs": inp}


def test_insertion_precedes_parent_and_limits():
    r = toy(); cx = RC.Ctx(Stub(), r, 1e18)
    vs, py0 = RC.insert(cx, [], [], [2, 30], [], 1)
    assert py0 == 0.1
    ins = [v for v in vs if v[2]["inserted"]]
    assert ins and all(v[0][-1] == [2, 30] and v[2]["inserted"][0][0] == 3 for v in ins)
    assert any(e[1] == "BEFORE" for v in ins for e in v[1])
    assert [v for v in vs if v[2]["inserted"] is None]                                    # no-insertion sibling kept
    vs2, _ = RC.insert(cx, [[1, 31], [4, 32], [3, 33], [0, 34]][:3], [], [2, 30], [], 1)   # 4 used: room 0 -> no insertion
    assert all(v[2]["inserted"] is None for v in vs2)
    vs3, p3 = RC.insert(cx, [], [], [2, 30], [], 1)                                        # same key again -> cycle guard
    assert p3 is None and vs3[0][2].get("cycle")


# ------------------------------------------------------------------------------------------------ real frozen 3D bundle
def test_b0_parity_and_determinism(fz, rows):
    ref = {r["root_id"]: r for r in map(json.loads, open(Path.home() / "abf_v34/parity/pred_val_3d_gpu.jsonl"))}
    rr = [r for r in rows if r["root_id"] in ref and ref[r["root_id"]]["decision"] == "REPAIR"][:2]
    for r in rr:
        fz.reset(); a = CP.b0(fz, r, fz.man["config"]["rule"]); fz.reset(); b = CP.b0(fz, r, fz.man["config"]["rule"])
        e = ref[r["root_id"]]
        assert a["seq"] == b["seq"] and a["seq"] == [[m["object_index"], m["destination_cell"]] for m in e["moves"]]
        assert abs(a["score"] - e["score_p11"]) < 1e-5


def test_y_global_equals_full_py_and_order_invariance(fz, rows):
    r = big(rows); inp = r["inputs"]
    mv = [i for i in range(len(inp["ids"])) if i != inp["tid"]]; free = [c for c in range(36) if c not in SC.forbidden(r)]
    s1, s2 = [[mv[0], free[0]], [mv[1], free[1]]], [[mv[1], free[1]], [mv[0], free[0]]]
    fz.reset(); sc = fz.score(r, [s1, s2]); yg = fz.y_global(r, [s1])[0]
    assert abs(sc[0]["py"] - sc[1]["py"]) < 1e-9 and abs(yg - sc[0]["py"]) < 1e-5
    for x in sc:
        assert abs(x["p11"] - x["py"] * x["px1"]) < 1e-12 and abs(x["px"] - (x["py"] * x["px1"] + (1 - x["py"]) * x["px0"])) < 1e-12


def test_long_sequences_run_and_cache_task_isolation(fz, rows):
    r = big(rows, 7); inp = r["inputs"]
    mv = [i for i in range(len(inp["ids"])) if i != inp["tid"]]; free = [c for c in range(36) if c not in SC.forbidden(r)]
    s5 = [[mv[i], free[i]] for i in range(min(5, len(mv)))]
    fz.reset(); x = fz.score(r, [s5])[0]
    assert all(math.isfinite(v) for v in x.values())
    t = SC.rebase(r, [], task=(mv[0], free[0]))
    a, b = fz.score(r, [[[mv[1], free[1]]]])[0], fz.score(t, [[[mv[1], free[1]]]])[0]
    assert a != b                                                                         # different task -> different cache entry / value


def test_caps_enforced_before_batch(fz, rows):
    from models import CapReached
    r = big(rows); inp = r["inputs"]
    mv = [i for i in range(len(inp["ids"])) if i != inp["tid"]]; free = [c for c in range(36) if c not in SC.forbidden(r)]
    fz.reset(); fz.caps = {"x_unique": 1}
    with pytest.raises(CapReached):
        fz.score(r, [[[mv[0], free[0]]], [[mv[0], free[1]]]])
    assert fz.c["x_unique"] == 0
    fz.caps = {}


def test_planner_modules_never_touch_private_or_teacher():
    for f in ("run.py", "compose.py", "recursive.py", "scene.py", "models.py"):
        src = (HERE / f).read_text().split('"""', 2)[-1]
        for bad in ("evaluate_k45", "generate", "fin3d", "k45_private/confirm", "witness", "verified_K", "PRIVATE"):
            assert bad not in src, (f, bad)


def test_outcome_statuses():
    import evaluate_k45 as EV
    ok = {"resolution": "EVALUATED"}
    assert EV.outcome({"X": {**ok, "x": 1}, "Y": {**ok, "y": 1}}) == "SUCCESS"
    assert EV.outcome({"X": {**ok, "x": 0}, "Y": {"resolution": "UNRESOLVED_ADMIN"}}) == "FAIL_X"
    assert EV.outcome({"X": {"resolution": "UNRESOLVED_ADMIN"}, "Y": {**ok, "y": 1}}) == "UNKNOWN"
    assert EV.outcome({"X": {**ok, "x": 1}, "Y": {**ok, "y": 0}}) == "FAIL_Y" and EV.outcome(None) == "UNKNOWN"
