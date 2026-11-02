"""BXY-P27 bounded lazy search: complete coverage with unbounded budget under any cost (scores reorder, never remove), exact coverage
accounting, sound-only pruning, precise terminal statuses, hash-sealed resume without repeated verification calls, and the two required
synthetic examples (catalogue-absent winner; order / connector trap). All verification here is SYNTHETIC (no teacher)."""
import random

import pytest

import bxy_fullsearch as Q
import bxy_fullspace as S

A_ = S.toy({"A": 28, "B": 36}, target=27, goal=29, legal=[4, 5, 6, 27, 28, 29, 36])          # 3 parking cells p1..p3 = 4, 5, 6
B_ = S.toy({"A": 28, "B": 36, "C": 30}, {"W": 20}, target=27, goal=29, legal=[3, 4, 5, 20, 27, 28, 29, 30, 36, 44])


def const(seqs):
    return [0.0] * len(seqs)


def rand(seed):
    r = random.Random(seed)
    return lambda seqs: [r.random() for _ in seqs]


def length(seqs):
    return [float(len(s)) for s in seqs]


@pytest.mark.parametrize("cost,fair", [(const, 4), (rand(1), 4), (rand(2), 0), (length, 1), (lambda s: [-float(len(x)) for x in s], 3)])
def test_unbounded_search_examines_every_member_whatever_the_scores(cost, fair):
    D = S.domain(B_)
    st, res = Q.run(D, 3, cost, {}, fair=fair)
    walked = {S.xsig(s) for s in S.walk(D, 3) if not any(S.goal_dead(D, s[:i]) for i in range(1, len(s)))}
    assert res["exhausted"] and set(st["nodes"]) == walked                                # all members except sound GOAL_DEAD descendants
    cv = res["coverage"]
    assert cv["balanced"] and cv["unexplored_residual"] == 0 and cv["examined"] + cv["pruned_sound"] == sum(S.count(D, 3).values())


def test_bounded_search_accounts_for_the_residual_frontier_exactly():
    D = S.domain(B_)
    for b in (1, 3, 7, 20):
        st, res = Q.run(D, 3, rand(b), {"expansions": b})
        cv = res["coverage"]
        assert not res["exhausted"] and cv["balanced"] and cv["unexplored_residual"] > 0 and res["status"] == "SELECTED_UNVERIFIED"


def test_matches_exhaustive_oracle_on_tiny_domain():
    D = S.domain(B_)
    c = rand(7)
    vals = {}
    def memo(seqs):
        return [vals.setdefault(S.xsig(s), c([s])[0]) for s in seqs]
    ref = Q.exhaustive(D, 2, memo)
    st, _ = Q.run(D, 2, memo, {}, fair=0)
    seqs = {S.xsig(s): s for s in S.walk(D, 2)}
    ref_sel = [k for _, _, k in ref if not S.goal_blocked(D, seqs[k])]
    assert Q.ranked(st) == ref_sel                                                                # identical ranking of every selectable member


def oracle_a(q, seq):
    """Synthetic labels (Example A): Y = 1 iff A at p1 (4) and B moved; X = 1 iff B is moved before A."""
    e = dict(seq)
    if q == "Y":
        return {"y": int(e.get("A") == 4 and "B" in e), "negative_kind": "SYNTHETIC"}
    o = [x for x, _ in seq]
    return {"y": int("A" not in o or ("B" in o and o.index("B") < o.index("A"))), "negative_kind": "SYNTHETIC"}


def test_example_a_finds_the_winner_absent_from_the_old_catalogue():
    D = S.domain(A_)
    catalogue = [(("A", 4),), (("A", 4), ("B", 5))]
    assert all(not (oracle_a("Y", list(s))["y"] and oracle_a("X", list(s))["y"]) for s in catalogue)   # every catalogue repair fails
    st, res = Q.run(D, 2, length, {"verify_calls": 100}, verify=oracle_a)                   # no catalogue input at all
    seq = tuple(tuple(a) for a in st["nodes"][res["best_verified"]]["seq"])
    assert res["status"] == "FOUND_VERIFIED" and seq not in catalogue and seq[-1] == ("A", 4) and seq[0][0] == "B"
    st2, res2 = Q.run(D, 2, length, {"verify_calls": 3}, verify=oracle_a)
    assert res2["status"] == "VERIFY_BUDGET_EXHAUSTED_UNKNOWN" and res2["best_verified"] is None   # budget limit is never "no repair"


def oracle_b(q, seq):
    """Synthetic order / connector trap: [A->4] fails its terminal connector (X 0) and Y; [A->4, B->5] passes both; [B->5, A->4] fails X."""
    e = dict(seq)
    if q == "Y":
        return {"y": int(e.get("A") == 4 and e.get("B") == 5), "negative_kind": "SYNTHETIC"}
    return {"y": int([tuple(a) for a in seq] == [("A", 4), ("B", 5)]), "negative_kind": "NO_PLAN_FOUND"}


def test_example_b_prefix_failure_and_wrong_order_do_not_prune_the_winner():
    D = S.domain(A_)
    a, b = (("A", 4), ("B", 5)), (("B", 5), ("A", 4))
    assert S.ysig(D, a) == S.ysig(D, b) and S.xsig(a) != S.xsig(b)
    cost = lambda seqs: [{(("A", 4),): 0.0, b: 0.1, a: 0.2}.get(tuple(s), 1.0 + len(s)) for s in seqs]  # noqa: E731
    st, res = Q.run(D, 2, cost, {"verify_calls": 50}, verify=oracle_b)
    assert res["status"] == "FOUND_VERIFIED" and res["best_verified"] == S.xsig(a)
    V = st["verify"]
    assert V["y"][S.ysig(D, [("A", 4)])]["y"] == 0 and S.xsig(b) in V["x"] and V["x"][S.xsig(b)]["y"] == 0
    assert list(V["y"]).count(S.ysig(D, a)) == 1                                            # one shared Y query for both orders


def test_exhausted_and_censored_statuses():
    D = S.domain(A_)
    st, res = Q.run(D, 1, length, {"verify_calls": 10 ** 6}, verify=lambda q, s: {"y": 0, "negative_kind": "CERTIFIED"})
    assert res["status"] == "EXHAUSTED_DEFINED_SPACE" and res["exhausted"] and res["negative_kinds"] == {"CERTIFIED": res["teacher_calls"]}
    st, res = Q.run(D, 2, length, {"expansions": 1, "verify_calls": 10 ** 6}, verify=lambda q, s: {"y": 0, "negative_kind": "NO_PLAN_FOUND"})
    assert res["status"] == "BUDGET_EXHAUSTED_UNKNOWN"
    st, res = Q.run(D, 1, length, {"verify_calls": 5}, verify=lambda q, s: None)
    assert res["status"] == "TEACHER_CENSORED"


def test_resume_is_identical_and_never_repeats_a_verification(tmp_path):
    D = S.domain(B_)
    calls = []
    def ver(q, s):
        calls.append((q, S.xsig(s)))
        return {"y": 0, "negative_kind": "NO_PLAN_FOUND"}
    full, rf = Q.run(D, 3, length, {"expansions": 40, "verify_calls": 30}, verify=ver)
    n_full = len(calls)
    calls.clear()
    st, r1 = Q.run(D, 3, length, {"expansions": 15, "verify_calls": 10}, verify=ver)
    Q.save(st, tmp_path / "s.json")
    st = Q.load(tmp_path / "s.json")
    st, r2 = Q.run(D, 3, length, {"expansions": 40, "verify_calls": 30}, verify=ver, st=st)
    assert len(calls) == n_full == 30 and len(set(calls)) == len(calls)                    # no verification call repeated across resume
    assert set(st["nodes"]) == set(full["nodes"]) and r2["coverage"] == rf["coverage"]
    (tmp_path / "s.json").write_text((tmp_path / "s.json").read_text().replace('"expanded": 15', '"expanded": 16'))
    with pytest.raises(ValueError):
        Q.load(tmp_path / "s.json")


def test_goal_dead_is_the_only_pruning_and_blocked_nodes_are_still_expanded():
    D = S.domain(S.toy({"A": 29, "B": 21}, target=27, goal=29, legal=[3, 4, 21, 27, 29]))   # A rests ON the goal
    st, res = Q.run(D, 2, const, {})
    assert st["nodes"]["empty"]["blocked"] and "B>3" in st["nodes"] and "B>3.A>4" in st["nodes"]  # blocked root still expanded
    dead = [k for k, n in st["nodes"].items() if n["dead"]]
    assert "A>3.B>29" in dead and all(not st["nodes"][k]["open"] for k in dead)
    assert res["coverage"]["balanced"] and res["selected"] not in ("empty", None)


def test_no_silent_truncation_at_legacy_catalogue_caps():
    import json
    from pathlib import Path
    rec = json.loads(sorted(Path("runs/approach_b/bxy_p20_v1/k3/roots").glob("*.json"))[0].read_text())
    D = S.domain(rec)
    st, res = Q.run(D, 4, length, {"expansions": 1})
    assert res["coverage"]["examined"] == 1 + len(D["movable"]) * S.free0(D) > 60 and res["coverage"]["balanced"]   # > MAX_CANDS 24, MAX_QUERIES 60


def test_k3_enumeration_equals_brute_force_over_objects_and_cells():
    import itertools
    import bxy_f1 as F1
    import bxy_teacher as T
    D = S.domain(B_)
    cells = sorted(set(B_["scene"]["legal_cells"]) | {0, 63})                                # legal cells + two illegal ones
    acts = [(o["id"], c) for o in B_["scene"]["objects"] for c in cells]                    # target and fixed wall included
    ref = {s for s in itertools.product(acts, repeat=3) if F1.screen(B_, list(s))["x_ok"] and T.eligible(B_, list(s)) is None}
    assert ref == {s for s in S.walk(D, 3) if len(s) == 3} and len(ref) == S.count(D, 3)[3]
