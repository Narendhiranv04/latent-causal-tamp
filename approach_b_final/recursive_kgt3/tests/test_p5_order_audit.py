"""P5A static same-endpoint order audit: synthetic oracles + brute force (m<=6), and real kill-table / private witness controls (evaluator
only; skipped when the private files are absent; witness sequences are never printed).   python -m pytest tests/test_p5_order_audit.py -q"""
import json, os, random, sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import p5_order_audit as A  # noqa: E402

TABLES = Path(os.environ.get("P5_TABLES", "/home/naren/Desktop/boltzmann_lfd/.claude/worktrees/scaling2d/scaling2d_k12/G1"))
DEV = Path(os.environ.get("P5_DEV", "/home/naren/kgt3_runs/dev"))


class Syn:
    """Oracle checker: pick of object i is dead iff any other object sits in pblk[i]; place at d dead iff any other object sits in qblk[d]."""
    def __init__(s, T0, goal, pblk=None, qblk=None):
        s.T0, s.goal, s.pb, s.qb = T0, goal, pblk or {}, qblk or {}

    def _oth(s, cells, i):
        return {c for j, c in enumerate(cells) if j != i and c is not None}

    def pick(s, cells, i):
        return not (s._oth(cells, i) & s.pb.get(i, set()))

    def place(s, cells, i, d):
        return not (s._oth(cells, i) & s.qb.get(d, set()))

    def final(s, cells):
        return s.pick(cells, s.T0) and s.place(cells, s.T0, s.goal)

    def blockers(s, cells, i, d=None):
        S_ = s.pb.get(i, set()) if d is None else s.qb.get(d, set())
        return [j for j, c in enumerate(cells) if j != i and c in S_]


def rand_case(rng, m):
    n = m + 3; c0 = list(range(n)); T0, goal = n - 1, 99           # objects 0..m-1 move, m..n-2 never move, n-1 = target
    acts = [(i, 50 + i) for i in range(m)]
    cells_all = list(range(n)) + [50 + i for i in range(m)]
    k = rng.choice([1, 1, 2])                                       # mixed blocking density so both outcomes occur at every m
    mov = list(range(m)) + [50 + i for i in range(m)]                # target pick / goal place: blocked only by mover cells (src or dest)
    pb = {i: set(rng.sample(cells_all, rng.randint(0, k))) - {c0[i]} for i in range(n - 1)} | {T0: set(rng.sample(mov, rng.randint(0, 1)))}
    qb = {d: set(rng.sample(cells_all, rng.randint(0, k))) - {d} for d in [50 + i for i in range(m)]} | {goal: set(rng.sample(mov, rng.randint(0, 1)))}
    return c0, acts, Syn(T0, goal, pb, qb)


@pytest.mark.parametrize("m", [1, 2, 3, 4, 5, 6])
def test_dp_equals_brute_force(m):
    rng, pos = random.Random(m), 0
    for _ in range(300):
        c0, acts, chk = rand_case(rng, m)
        dp, b = A.subset_dp(c0, acts, chk), A.brute(c0, acts, chk)
        assert dp["exists"] == (b is not None)
        if dp["exists"]:                                            # reconstructed order is itself valid and a permutation
            pos += 1
            assert sorted(dp["order"]) == list(range(m)) and A.run_order(c0, acts, dp["order"], chk)["status"] == "STATIC_VALID"
        assert dp["nodes"] <= 2 ** m and dp["tests"] <= m * 2 ** (m - 1)
    assert 10 <= pos <= 290                                          # both outcomes exercised


def test_order_swap_same_endpoint():
    chk = Syn(3, 99, pblk={0: {1}})                                 # 0 is blocked by 1 at its source cell 1 -> move 1 first
    c0, acts = [0, 1, 2, 3], [(0, 50), (1, 51)]
    assert A.run_order(c0, acts, [0, 1], chk) == {**A.run_order(c0, acts, [0, 1], chk), "status": "FAIL_PICK", "step": 0}
    r = A.classify(c0, acts, chk)
    assert r["exists"] and r["dp"]["order"] == [1, 0] and r["reason_codes"] == ["NONE"]


def test_unavoidable_cycle():
    chk = Syn(3, 99, pblk={0: {1}, 1: {0}})                         # each blocks the other's pick at its source: no linear extension
    r = A.classify([0, 1, 2, 3], [(0, 50), (1, 51)], chk)
    assert not r["exists"] and r["reason_codes"] == ["ORDER_CONFLICT"] and not r["never_executable"]
    assert r["dp"]["frontier"] == {"PICK_DEAD": 2} and r["dp"]["max_depth"] == 0


def test_pickup_only_blockage():
    chk = Syn(3, 99, pblk={0: {2}})                                 # blocked by never-moved object 2 -> irreparable by permutation
    r = A.classify([0, 1, 2, 3], [(0, 50), (1, 51)], chk)
    assert not r["exists"] and r["reason_codes"] == ["PICK_NEVER_STRUCTURAL"]
    n = r["never_executable"][0]
    assert n["object"] == 0 and not n["pick_ever"] and n["place_ever"] and n["unmoved_blockers"] == [2] and n["cause"] == "NEEDS_EXTRA_MOVERS"
    chk = Syn(3, 99, pblk={0: {1, 51}})                             # blocked by mover 1 at source AND at its destination
    r = A.classify([0, 1, 2, 3], [(0, 50), (1, 51)], chk)
    assert r["reason_codes"] == ["PICK_NEVER_MOVERS"]
    chk = Syn(3, 99, pblk={0: {3}})                                 # blocked by the never-moved target itself
    assert A.classify([0, 1, 2, 3], [(0, 50), (1, 51)], chk)["never_executable"][0]["cause"] == "TARGET_OR_BASE"


def test_placement_only_blockage():
    chk = Syn(3, 99, qblk={50: {2}})
    r = A.classify([0, 1, 2, 3], [(0, 50), (1, 51)], chk)
    assert not r["exists"] and r["reason_codes"] == ["PLACE_NEVER_STRUCTURAL"] and r["never_executable"][0]["pick_ever"]
    chk = Syn(3, 99, qblk={50: {1, 51}})
    assert A.classify([0, 1, 2, 3], [(0, 50), (1, 51)], chk)["reason_codes"] == ["PLACE_NEVER_MOVERS"]


def test_joint_never():
    chk = Syn(3, 99, pblk={0: {51}}, qblk={50: {1}})                # pick live only before 1 moves, place live only after
    r = A.classify([0, 1, 2, 3], [(0, 50), (1, 51)], chk)
    assert r["reason_codes"] == ["JOINT_NEVER"] and not r["exists"]


def test_final_target():
    chk = Syn(3, 99, qblk={99: {50}})                               # every move legal, but a destination blocks the goal placement
    r = A.classify([0, 1, 2, 3], [(0, 50), (1, 51)], chk)
    assert not r["exists"] and r["dp"]["reach_full"] and r["reason_codes"] == ["FINAL_TARGET_DEAD"]
    assert A.run_order([0, 1, 2, 3], [(0, 50), (1, 51)], [0, 1], chk)["status"] == "FAIL_FINAL_TARGET"


def test_all_legal_control():
    m = 6; chk = Syn(m + 2, 99); c0, acts = list(range(m + 3)), [(i, 50 + i) for i in range(m)]
    r = A.classify(c0, acts, chk)
    assert r["exists"] and r["dp"]["order"] == list(range(m)) and r["dp"]["nodes"] == 2 ** m and r["dp"]["tests"] == m * 2 ** (m - 1)
    assert r["brute_force_agrees"] and r["dp"]["frontier"] == {}


def test_deterministic_reconstruction():
    rng = random.Random(7)
    for _ in range(40):
        c0, acts, chk = rand_case(rng, 5)
        a, b = A.classify(c0, acts, chk), A.classify(c0, acts, chk)
        assert a == b
        perm = acts[::-1]                                          # listing order of the same assignment does not change existence
        assert A.subset_dp(c0, perm, chk)["exists"] == a["exists"]


def test_legality_grammar():
    import data as DA
    row = {"inputs": {"tid": 0, "goal_cell": 9, "cells0": [1, 2, 3], "attrs": [[0, 0, 0, 0]] * 3, "legal_cells": list(range(16))}}
    assert DA.check_sequence(row, [[1, 5], [2, 6]]) is None
    for seq, why in (([[0, 5]], "TARGET_MOVED"), ([[1, 5], [1, 6]], "OBJECT_TWICE"), ([[1, 9]], "GOAL_CELL"), ([[1, 3]], "ORIGINALLY_OCCUPIED"),
                     ([[1, 5], [2, 5]], "OCCUPIED_NOW"), ([[1, 40]], "ILLEGAL_CELL")):
        assert DA.check_sequence(row, seq) == why


def test_failure_family_and_never_promote_hY():
    assert A.failure_family(["PICK_NEVER_STRUCTURAL", "FINAL_TARGET_DEAD"]) == "FINAL_TARGET+PICKUP_BLOCKED_BY_UNMOVED"
    src = Path(A.__file__).read_text()
    assert '"teacher", "VERIFIED_Y1"' in src and "hY" not in src.split("if ys == {1}:")[1].split("illegal =")[0].replace("hY is recorded only", "")


def test_public_modules_never_import_audit():
    for f in ("data.py", "models.py", "planner.py", "planner_r.py", "run_p4.py"):
        t = (HERE / f).read_text()
        assert "p5_order_audit" not in t and "import dev_eval" not in t and "from dev_eval" not in t and "MINK_TABLE" not in t


@pytest.mark.skipif(not (TABLES / "MINK_TABLE_original.json").exists() or not (DEV / "dev_public/dev_public.jsonl").exists(), reason="kill tables / DEV absent")
def test_real_tables_dp_equals_brute_force():
    from dev_eval import Static
    ST, rng, n = Static(TABLES), random.Random(0), 0
    for r in A.jl(DEV / "dev_public/dev_public.jsonl"):
        inp = r["inputs"]; c0 = [int(c) for c in inp["cells0"]]; T0, G0 = int(inp["tid"]), int(inp["goal_cell"]); chk = A.Chk(ST, T0, G0)
        free = [c for c in inp["legal_cells"] if c not in c0 and c != G0]
        for m in range(1, 7):
            objs = rng.sample([i for i in range(len(c0)) if i != T0], m); acts = list(zip(objs, rng.sample(free, m)))
            dp = A.subset_dp(c0, acts, chk)
            assert dp["exists"] == (A.brute(c0, acts, chk) is not None); n += 1
            assert chk.final(c0) == ST.feasible(c0, T0, G0)
    assert n == 25 * 6


@pytest.mark.skipif(not (TABLES / "MINK_TABLE_original.json").exists() or not (DEV / "dev_private/dev_private.jsonl").exists(), reason="private DEV absent")
def test_private_witness_control():
    """EVALUATOR-ONLY control: every certified DEV witness is static-valid in its own order and found by the DP (booleans only)."""
    from dev_eval import Static
    W = A.witness_control(Static(TABLES), {r["root_id"]: r for r in A.jl(DEV / "dev_public/dev_public.jsonl")}, DEV / "dev_private")
    assert W["n"] == 25 and W["witness_order_static_valid"] == 25 and W["witness_assignment_dp_exists"] == 25 and W["brute_agree_or_m_gt_6"] == 25
