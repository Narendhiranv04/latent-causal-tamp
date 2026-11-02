"""BXY-P26 universal domain: the lazy enumerator equals an independent brute force (F1 X rules + teacher eligibility over every object x
every lattice cell), is label-free, keeps negatives, and identifies X by order and Y by endpoint."""
import copy
import itertools
import json
from pathlib import Path

import pytest

import bxy_f1 as F1
import bxy_fullspace as S
import bxy_teacher as T

DEV = sorted(Path("runs/approach_b/bxy_p20_v1/k3/roots").glob("*.json"))
TOYS = [S.toy({"A": 29}, target=27, goal=29),                                          # 1-action goal blockage
        S.toy({"A": 28, "B": 36}, {"W": 20}, target=27, goal=29),                       # order contrast, one fixed wall
        S.toy({"A": 28, "B": 36, "C": 30}, {"W": 20}, target=27, goal=29, legal=[3, 20, 27, 28, 29, 30, 36, 44, 45, 46])]  # restricted lattice


def brute(rec, K, objs=None):
    """Independent reference: every (object, cell) tuple of length <= K over ALL scene objects and ALL lattice cells, kept iff the historical
    bxy_f1 X screen admits it and bxy_teacher.eligible accepts it (no code shared with bxy_fullspace)."""
    objs = objs or sorted(o["id"] for o in rec["scene"]["objects"])
    acts = [(o, c) for o in objs for c in range(64)]
    out = {()}
    for m in range(1, K + 1):
        for s in itertools.product(acts, repeat=m):
            if F1.screen(rec, list(s))["x_ok"] and T.eligible(rec, list(s)) is None:
                out.add(s)
    return out


@pytest.mark.parametrize("i", range(len(TOYS)))
def test_enumerator_equals_brute_force_m0_to_2(i):
    rec = TOYS[i]
    D = S.domain(rec)
    mine = list(S.walk(D, 2))
    assert len(mine) == len(set(mine)) and set(mine) == brute(rec, 2)
    assert {m: sum(len(s) == m for s in mine) for m in range(3)} == S.count(D, 2)


def test_dev_root_m1_all_objects_and_m2_movables_equal_brute_force():
    rec = json.loads(DEV[0].read_text())
    D = S.domain(rec)
    assert set(S.walk(D, 1)) == brute(rec, 1)                                           # targets / fixed / every cell offered
    m2 = {s for s in S.walk(D, 2) if len(s) == 2}
    assert m2 == {s for s in brute(rec, 2, list(D["movable"])) if len(s) == 2} and len(m2) == S.count(D, 2)[2]


def test_counts_and_endpoints_exact_at_k3():
    for rec in TOYS:
        D = S.domain(rec)
        seqs = list(S.walk(D, 3))
        assert {m: sum(len(s) == m for s in seqs) for m in range(4)} == S.count(D, 3)
        ys = {}
        for s in seqs:
            ys.setdefault(len(s), set()).add(S.ysig(D, s))
        assert {m: len(ys.get(m, ())) for m in range(4)} == S.count_endpoints(D, 3)


def test_object_id_permutation_invariance():
    rec = TOYS[2]
    ren = {"A": "Z1", "B": "Y2", "C": "X3", "W": "V0"}
    r2 = copy.deepcopy(rec)
    for o in r2["scene"]["objects"]:
        o["id"] = ren.get(o["id"], o["id"])
    r2["fixed_ids"] = [ren[i] for i in rec["fixed_ids"]]
    back = {v: k for k, v in ren.items()}
    a = set(S.walk(S.domain(rec), 3))
    b = {tuple((back[o], d) for o, d in s) for s in S.walk(S.domain(r2), 3)}
    assert a == b


def test_privileged_fields_cannot_change_the_universe():
    rec = json.loads(DEV[0].read_text())
    base = list(S.walk(S.domain(rec), 2))
    m = copy.deepcopy(rec)
    m["construction"] = {"options": [], "intended": [], "K_cert": 0, "neutral_cells": [], "harmful_cells": [{"cell": 0}]}
    m["roles"] = {o: "distractor" for o in rec["roles"]}
    m["spec"], m["catalogue_v21"], m["design_v21"], m["intended_blockers"] = {"K_intent": 0}, [], {}, []
    assert list(S.walk(S.domain(m), 2)) == base
    assert list(S.walk(S.domain({k: rec[k] for k in S.READ}), 2)) == base                 # nothing outside READ is needed
    assert set(S.domain(rec)["movable"]) == set(rec["roles"])                           # = the teacher's movable set (keys only)


def test_grammar_vacated_cells_order_and_out_of_domain_reasons():
    D = S.domain(TOYS[1])                                                               # A@28, B@36, W@20 fixed, t0@27, goal 29
    seqs = set(S.walk(D, 2))
    assert (("B", 0), ("A", 36)) in seqs and (("A", 36), ("B", 0)) not in seqs           # vacated cell usable only after the vacate
    assert S.classify(D, [("A", 36), ("B", 28)]) == "DEST_OCCUPIED"                     # simultaneous swap is out of domain
    assert S.classify(D, [("t0", 5)]) == "TARGET_MOVED" and S.classify(D, [("W", 5)]) == "FIXED_MOVED"
    assert S.classify(D, [("A", 5), ("A", 6)]) == "DUPLICATE_OBJECT" and S.classify(D, [("A", 28)]) == "NULL_RELOCATION"
    assert S.classify(D, [("A", 64)]) == "DEST_NOT_LEGAL" and S.classify(D, [("A", 1)] * 7) == "LENGTH"
    assert all(o not in ("t0", "W") for s in seqs for o, _ in s)
    assert (("A", 29),) in seqs and (("A", 63),) in seqs and (("B", 0),) in seqs         # goal-harmful and far edits are members
    assert all(S.classify(D, s) is None for s in seqs)


def test_order_permutations_share_y_and_differ_in_x():
    rec = TOYS[1]
    D = S.domain(rec)
    a, b = (("A", 5), ("B", 6)), (("B", 6), ("A", 5))
    assert a in set(S.walk(D, 2)) and b in set(S.walk(D, 2))
    assert S.ysig(D, a) == S.ysig(D, b) and S.xsig(a) != S.xsig(b)
    assert T.ykey("r", rec, list(a)) == T.ykey("r", rec, list(b)) and T.xkey("r", rec, list(a)) != T.xkey("r", rec, list(b))
    assert S.ysig(D, a) == T.ykey("r", rec, list(a)).split(":", 3)[3]


def test_goal_rules_terminal_and_subtree_soundness():
    D = S.domain(TOYS[2])
    seqs = list(S.walk(D, 3))
    for s in seqs:
        assert S.goal_blocked(D, s) == (not F1.screen(TOYS[2], list(s))["complete_ok"])   # = F1 terminal screen on members
        if S.goal_dead(D, s):
            assert all(S.goal_blocked(D, t) for t in seqs if t[:len(s)] == s)
    assert S.goal_blocked(D, ()) is False and S.goal_blocked(S.domain(TOYS[0]), ()) is True


def test_example_a_catalogue_absent_sequences_are_members():
    rec = S.toy({"A": 28, "B": 36}, target=27, goal=29)
    D = S.domain(rec)
    old = {(("A", 4),), (("A", 4), ("B", 5))}
    new = set(S.walk(D, 2))
    assert old <= new and (("B", 6), ("A", 4)) in new and (("A", 5), ("B", 4)) in new and (("A", 29),) in new
    assert len(new - old) == sum(S.count(D, 2).values()) - 2
