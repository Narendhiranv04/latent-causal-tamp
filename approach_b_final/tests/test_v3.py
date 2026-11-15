"""V3 invariants (plan V3 8.3).  CPU, synthetic.   python -m pytest -q tests"""
import collections, itertools, json, sys
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


# ------------------------------------------------------------------------------------------------ V3-1 direct construction
import random  # noqa: E402
import construct as CO  # noqa: E402


def brute(D):
    out = [0, 0, 0]
    ob = sorted(D)
    for k in (1, 2, 3):
        for objs in itertools.permutations(ob, k):
            for ds in itertools.product(*(D[o] for o in objs)):
                out[k - 1] += len(set(ds)) == k
    return out


def test_toy_counts_12_96_384_and_complete_enumeration():
    D = {0: [10, 11, 12, 13], 1: [20, 21, 22, 23], 2: [30, 31, 32, 33]}          # n = 3, M = 4, disjoint sets: nothing filtered
    assert CO.counts(D) == [12, 96, 384]
    seqs, acc = CO.build(D, 10_000, "toy")
    assert acc["mode"] == "complete" and len(seqs) == 492 == len({json.dumps(s) for s in seqs})
    assert acc["built_by_len"] == [12, 96, 384]
    assert [[0, 10], [1, 20]] in [list(map(list, s)) for s in seqs] and [[1, 20], [0, 10]] in [list(map(list, s)) for s in seqs]   # orders kept


def test_counts_match_bruteforce_with_shared_destinations():
    rng = random.Random(0)
    for _ in range(30):
        D = {o: rng.sample(range(12), rng.randint(0, 5)) for o in range(rng.randint(1, 6))}
        assert CO.counts(D) == brute(D), D
        seqs, acc = CO.build(D, 10 ** 6, "x")
        assert len(seqs) == sum(brute(D))
        for s in seqs:                                                            # grammar: distinct objects and destinations, len 1..3
            assert 1 <= len(s) <= 3 and len({o for o, _ in s}) == len(s) == len({d for _, d in s})


def test_budgeted_constructor_accounting_and_whole_permutation_groups():
    D = {o: list(range(10 * o, 10 * o + 8)) for o in range(8)}                    # 8 objects x 8 dests: far above the budget
    seqs, acc = CO.build(D, 512, "root|0|8|512")
    assert acc["mode"] == "budgeted" and len(seqs) <= 512 and acc["built_by_len"][0] == 64     # every K1 action kept
    assert sum(acc["built_by_len"]) == len(seqs) and acc["valid_by_len"] == brute(D)
    groups = collections.Counter(C.ekey(s) for s in seqs if len(s) > 1)
    assert all(v == (2 if len(json.loads(k)) == 2 else 6) for k, v in groups.items())       # all orders of each sampled assignment
    assert seqs == CO.build(D, 512, "root|0|8|512")[0]                                        # deterministic, seeded per root
    assert seqs != CO.build(D, 512, "root|1|8|512")[0]


class FakeSampler:
    dev = "cpu"

    def __init__(self):
        self.calls = self.raw = self.passes = 0
        self.scenes = []

    def propose_many(self, root, cells, objs, M, gen):
        self.passes += 1; self.calls += len(objs); self.raw += 8 * M * len(objs); self.scenes.append(list(cells))
        return {o: root.legal_dests(cells)[o:o + M] for o in objs}


class FakeScorer:
    def __init__(self):
        self.evals, self.batches = 0, []

    def score(self, root, seqs):
        self.batches.append(seqs); self.evals += sum(1 for s in seqs if s)
        return [{"p11": 0.2 if not s else 0.9 / len(s) - 0.001 * s[0][1], "J": 0.0} for s in seqs]


def test_one_pass_contract_and_single_selection():
    import search as S
    row = {"root_id": "toy", "split": "val", "K_legacy": "2", "inputs": {**INP, "cell_xy": {str(c): [0.08 * (c % 3), 0.08 * (c // 3)] for c in range(9)}}}
    root = S.Root(row, "2d")
    sm, sc = FakeSampler(), FakeScorer()
    rule = {"noop_gate": 0.5, "eta": 0.3, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}
    rec = CO.run_root(root, sm, sc, 2, 4096, rule, 0)
    assert sm.passes == 1 and sm.scenes == [root.cells0]                         # ONE sampler pass, on the original scene only
    assert rec["planner_calls"] == 0 and rec["candidate_budget"]["sampler_passes"] == 1
    assert sc.batches[0] == [[]] and rec["candidate_budget"]["n_scored"] == sum(rec["candidate_budget"]["built_by_len"])
    assert rec["decision"] == "REPAIR" and len(rec["selected_ordered_seq"]) == 1                  # exactly one plan, argmin -log p11
    assert rec["selected_ordered_seq"] in [c["seq"] for c in rec["cands"]]
    assert root.movable == [0, 1]                                                 # fixed object 2 and the target are never proposed
