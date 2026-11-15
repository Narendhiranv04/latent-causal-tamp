"""V3 invariants (plan V3 8.3).  CPU, synthetic.   python -m pytest -q tests"""
import itertools, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import contracts as C  # noqa: E402

# toy root: 4 objects (0, 1, 2 movable, 3 = target), 3x3 grid, goal 8
INP = {"ids": ["a", "b", "c", "t0"], "tid": 3, "cells0": [0, 1, 2, 4], "legal_cells": list(range(9)), "goal_cell": 8,
       "attrs": [[0.02, 0.0, 1.0, 0.0], [0.02, 0.0, 1.0, 0.0], [0.02, 0.0, 1.0, 1.0], [0.02, 1.0, 0.0, 0.0]]}   # obj 2 fixed (2D attrs[3])


def test_six_orders_one_assignment():
    A = [[0, 3], [1, 5]]
    orders = [list(map(list, p)) for p in itertools.permutations(A)]
    row = {"labels": {"Y": [{"edit": sorted(A), "y": 1}, {"edit": [[0, 6]], "y": 0}],
                      "X": [{"seq": orders[0], "x": 1, "kind": "K"}, {"seq": orders[1], "x": 0, "kind": "K"}, {"seq": [[0, 6]], "x": 1, "kind": "K"}]}}
    pa = C.positive_assignments(row)
    assert len(pa) == 1                                   # Y = 0 endpoint is not a positive even with X = 1
    a = next(iter(pa.values()))
    assert a["assignment"] == sorted(A) and len(a["orders"]) == 1 and len(a["failed_orders"]) == 1


def test_assignment_key_is_order_free_and_shared_by_y():
    assert C.ekey([[1, 5], [0, 3]]) == C.ekey([[0, 3], [1, 5]])
    assert C.ekey([[0, 3]]) != C.ekey([[0, 5]])


def test_v3_grammar_rules():
    assert C.v3_grammar(INP, [[0, 3], [1, 5]]) == []
    assert "target_moved" in C.v3_grammar(INP, [[3, 5]])
    assert "fixed_moved" in C.v3_grammar(INP, [[2, 5]])
    assert "initially_occupied" in C.v3_grammar(INP, [[0, 1]])            # no slot reuse / swaps
    assert "initially_occupied" in C.v3_grammar(INP, [[0, 0]])            # stay move
    assert "goal_cell" in C.v3_grammar(INP, [[0, 8]])
    assert "shared_destination" in C.v3_grammar(INP, [[0, 3], [1, 3]])
    assert "object_twice" in C.v3_grammar(INP, [[0, 3], [0, 5]])
    assert "length" in C.v3_grammar(INP, [[0, 3], [1, 5], [0, 6], [1, 7]])
