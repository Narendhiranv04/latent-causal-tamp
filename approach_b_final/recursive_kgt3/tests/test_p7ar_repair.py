"""P7A-R tests (P7AR_PREREG section 8): injected-corridor fixtures on the REAL search code path.  Oracle: a plan is valid iff every pick,
every place and the final target have access 1 (no corridor-free approach blocked).   python -m pytest tests/test_p7ar_repair.py -q"""
import json, math, sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "tests"))
import p7ar_repair as R  # noqa: E402
from test_p6_order import code_tokens  # noqa: E402
from test_p7_repair import scene  # noqa: E402


def geo(row, blk, multi=None):
    """Injected corridors: blk {cell: set(blocker cells)} -> one corridor; multi {cell: [set, set, ...]}; others: one empty corridor."""
    CC = {x: [frozenset()] for x in range(64)}
    for x, b in blk.items():
        CC[x] = [frozenset(b)]
    for x, L in (multi or {}).items():
        CC[x] = [frozenset(b) for b in L]
    return R.Geo(row, R.CFG, CC)


def valid(g, plan):
    c = list(g.c0)
    for o, d in plan:
        occ = set(c) - {c[o]}
        if g.a(c[o], occ) < 1 or g.a(d, occ) < 1:
            return False
        c[o] = d
    return g.accT(c) == 1


def run(row, blk, A, arm, multi=None, cvae=None, cfg=None, fixed=()):
    if fixed:
        row = json.loads(json.dumps(row))
        for i in fixed:
            row["inputs"]["attrs"][i] = [0.024, 0, 1, 1]
    g = geo(row, blk, multi)
    S = R.Search(row, arm, lambda p, o, d: 0.5, cvae or {}, cfg or R.CFG, geo=g)
    top = S.search([tuple(m) for m in A], len(A))
    com = R.commit([dict(t) for t in top], lambda ps: [0.9 if valid(g, [tuple(m) for m in p]) else 0.1 for p in ps], cfg or R.CFG,
                   learned=not R.ARMS[arm].get("geom"))
    import data as DA
    for t in top:
        assert DA.check_sequence(row, t["plan"]) is None and len(t["plan"]) <= 12 and row["inputs"]["tid"] not in [o for o, _ in t["plan"]]
    return S, top, com, (com is not None and valid(g, [tuple(m) for m in com["plan"]])), g


ROW1 = scene([0, 19, 20, 45], 0, 18)                              # T0 obj0@0, goal 18; a = obj1@19; n = obj2@20


@pytest.mark.parametrize("arm", ["FULL_R", "FULL_R_GEOM"])
def test_missing_enabler_inserted_before_dependent(arm):
    S, top, com, ok, _ = run(ROW1, {18: {19}, 19: {20}}, [(1, 60)], arm)
    objs = [m[0] for m in com["plan"]]
    assert ok and 2 in objs and objs.index(2) < objs.index(1) and 2 in S.fun["suspect"] and 2 in S.fun["complete"]


def test_enabler_needs_enabler_chain():
    row = scene([0, 19, 20, 21, 45], 0, 18)
    S, top, com, ok, _ = run(row, {18: {19}, 19: {20}, 20: {21}}, [(1, 60)], "FULL_R")
    objs = [m[0] for m in com["plan"]]
    assert ok and objs.index(3) < objs.index(2) < objs.index(1)


def test_no_double_counting_potential():
    row = scene([0, 19, 17, 10, 45], 0, 18)                       # a@19 and b@17 both blocked by n@10; target goal blocked by a and b
    S, top, com, ok, g = run(row, {18: {19, 17}, 19: {10}, 17: {10}}, [(1, 60), (2, 61)], "FULL_R_GEOM")
    c, gg, A = list(g.c0), 0.0, {1, 2}
    for o, d in [tuple(m) for m in com["plan"]]:                    # independent recomputation: sum of own step terms + lam_e per enabler
        gg += g.term(g.acc(c, o, d)) + (R.CFG["lam_e"] if o not in A else 0.0); c[o] = d
    assert ok and [m[0] for m in com["plan"]].count(3) == 1 and abs(gg - com["g"]) < 1e-9 and abs(com["F"] - (gg + g.term(g.accT(c)))) < 1e-9


def test_zero_effect_nuisance_never_moved():
    row = scene([0, 19, 20, 30, 45], 0, 18)                       # z = obj3@30 sits in one of two goal corridors (the other is free)
    S, top, com, ok, _ = run(row, {19: {20}}, [(1, 60)], "FULL_R", multi={18: [{19}, set()], 0: [{30}, set()]})
    assert ok and 3 not in [m[0] for m in com["plan"]]


def test_new_destination_blockage_penalized():
    S, top, com, ok, g = run(ROW1, {18: {19}, 19: {20}, 60: {61}}, [(1, 60)], "FULL_R", cvae={2: [61, 62]})
    c = list(g.c0); bad, good = list(c), list(c); bad[2], good[2] = 61, 62
    assert g.phi(bad, [(1, 60)]) > g.phi(good, [(1, 60)])         # parking in a pending destination corridor raises the potential
    assert ok and not ([2, 61] in com["plan"] and [1, 60] in com["plan"])   # never both: either avoid 61 or re-destine a (valid plan)


def test_atomic_substitution_at_cap_and_no_cheap_deletion():
    fill = [33, 35, 37, 39, 49, 51, 53, 55, 57, 59, 61]
    row = scene([0, 19, 20] + fill, 0, 18)
    A = [(1, 6)] + [(3 + i, d) for i, d in enumerate([24, 26, 28, 30, 40, 42, 44, 46, 56, 58, 62])]
    S, top, com, ok, _ = run(row, {18: {19}, 19: {20}}, A, "FULL_R")
    assert ok and len(com["plan"]) == 12 and 2 in [m[0] for m in com["plan"]] and S.sub_log
    kept = {m[0] for m in com["plan"]} & {o for o, _ in A}
    assert len(kept) == 11                                          # exactly one original mover substituted (atomically)
    row2 = scene([0, 19, 20, 45], 0, 18)                          # below the cap a hard move cannot be deleted (blocker is fixed)
    S, top, com, ok, _ = run(row2, {18: {19}, 19: {20}, 45: set()}, [(1, 60), (3, 62)], "FULL_R", fixed=(2,))
    assert {m[0] for m in com["plan"]} >= {1, 3} and not S.sub_log


def test_dest_only_controls():
    assert not run(ROW1, {18: {19}, 19: {20}}, [(1, 60)], "DEST_ONLY")[3]          # cannot add a mover
    row = scene([0, 19, 17, 45], 0, 18)                           # b@17 blocked by a's source AND a's original destination 9
    for arm in ("DEST_ONLY", "FULL_R"):
        S, top, com, ok, _ = run(row, {18: {19, 17}, 17: {19, 9}}, [(1, 9), (2, 60)], arm, cvae={1: [9]})
        assert ok, arm


@pytest.mark.parametrize("m", [4, 6, 9, 12])
def test_flat_strong_builds_full_length_plans(m):
    free = [33, 35, 37, 39, 49, 51, 53, 55, 57, 59, 61, 63, 47, 31]
    row = scene([0] + free[: m + 2], 0, 18)
    A = [(1 + i, d) for i, d in enumerate([24, 26, 28, 30, 40, 42, 44, 46, 56, 58, 62, 60][:m])]
    S, top, com, ok, _ = run(row, {}, A, "FLAT_STRONG")
    assert com is not None and len(com["plan"]) == m


def test_random_matched_and_full_deterministic():
    fill = [33, 35, 37, 39, 49, 51, 53]
    row = scene([0, 19, 20] + fill, 0, 18); A = [(1, 6)] + [(3 + i, d) for i, d in enumerate([24, 26, 28, 30, 40, 42, 44])]
    for arm in ("FULL_R", "RANDOM_MATCHED", "FLAT_STRONG"):
        a, b = run(row, {18: {19}, 19: {20}}, A, arm), run(row, {18: {19}, 19: {20}}, A, arm)
        assert a[2] == b[2] and a[1] == b[1], arm


def test_budget_caps_and_funnel_monotone():
    fill = [33, 35, 37, 39, 49, 51, 53]
    row = scene([0, 19, 20] + fill, 0, 18); A = [(1, 6)] + [(3 + i, d) for i, d in enumerate([24, 26, 28, 30, 40, 42, 44])]
    S, *_ = run(row, {18: {19}, 19: {20}}, A, "FULL_R", cfg=dict(R.CFG, MODEL_MAX=30))
    assert S.stop == "BUDGET_MODEL" and S.used["model"] <= 30
    S, *_ = run(row, {18: {19}, 19: {20}}, A, "FULL_R")
    f = S.fun
    assert f["generated"] <= f["suspect"] and f["complete"] <= f["survivor"] | f["complete"] and S.used["model"] > 0


def test_geom_arm_makes_no_model_calls_and_commit_without_yend():
    S, top, com, ok, _ = run(ROW1, {18: {19}, 19: {20}}, [(1, 60)], "FULL_R_GEOM")
    assert S.used["model"] == 0 and "y_end" not in com


def test_real_corridors_face_the_base():
    g = R.Geo(scene([0, 1], 0, 18), R.CFG)                         # base at (-0.14, 0.32): left of the grid
    x = 27                                                          # row 3, col 3
    assert len(g.CC[x]) == 5 and 26 in g.CC[x][2] and all(28 not in cc for cc in g.CC[x])
    assert all(y not in g.CC[x][2] for y in (29, 35, 19)) and 25 in g.CC[x][2]                     # length 2 pitches, base-facing


def test_public_module_has_no_privileged_inputs():
    src = code_tokens(HERE / "p7ar_repair.py")
    for bad in ("p5_order_audit", "p5b_physical", "p6_eval", "p7_eval", "p7ar_eval", "dev_eval", "MINK", "QCLEAR", "Static", "dev_private",
                "dev_records", "witness", "verify", "teacher", "K_certified", "K_lb", "unmoved_blockers", "roots_private", "P5B", "q23", "e3c632"):
        assert bad not in src, bad
    for f in ("data.py", "models.py", "planner.py", "planner_r.py", "run_p4.py", "p6_order.py", "p7_repair.py"):
        assert "p7ar_repair" not in code_tokens(HERE / f) and "p7ar_eval" not in code_tokens(HERE / f)
