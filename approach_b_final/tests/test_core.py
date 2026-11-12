"""Pre-fit invariants (plan.md 4.5, 6.3).  CPU, synthetic, float64.   python -m pytest -q tests"""
import json, sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import xy as XY  # noqa: E402

torch.manual_seed(0)


def view(goal=(0.3, 0.3), seqs=(), edits=()):
    xy0 = [(0.1, 0.1), (0.2, 0.1), (0.3, 0.1), (0.1, 0.3)]
    attrs = [[0.024, 0.0, 1.0, 0.0], [0.024, 0.0, 1.0, 0.0], [0.024, 0.0, 1.0, 0.0], [0.024, 1.0, 0.0, 0.0]]
    return XY.make_view("r", xy0, attrs, 3, goal, (0.0, 0.0), [0.0] * 6 + list(goal), list(edits), list(seqs), XY._NoGeo)


AB = [(0, (0.5, 0.5)), (1, (0.6, 0.5))]
BA = [AB[1], AB[0]]


def coeffs(arm, v):
    torch.manual_seed(1)
    net = XY.XYNet(arm, 4, 8).double().eval()
    b, _ = XY.collate([v])
    return net, b, net.coeffs(b)


def test_exact_math_vs_bruteforce():
    st = XY.selftest()
    assert st["pass"], st


def test_ab_ba_share_endpoint_distinct_x():
    v, _, xm = view(seqs=[AB, BA])
    assert len(v["x_seqs"]) == 2 and v["parent"][0] == v["parent"][1] and xm == [0, 1]


def test_alternative_order_does_not_change_endpoint_py():
    _, _, c1 = coeffs("D", view(seqs=[AB])[0])
    _, _, c2 = coeffs("D", view(seqs=[AB, BA])[0])
    assert torch.allclose(c1["b"], c2["b"])


def test_goal_changes_y_unary():
    _, _, c1 = coeffs("D", view(goal=(0.3, 0.3), seqs=[AB])[0])
    _, _, c2 = coeffs("D", view(goal=(0.5, 0.1), seqs=[AB])[0])
    assert not torch.allclose(c1["b"], c2["b"])


def test_order_sensitivity_D_and_invariance_G():
    _, _, d = coeffs("D", view(seqs=[AB, BA])[0])
    _, _, g = coeffs("G", view(seqs=[AB, BA])[0])
    assert abs(float(d["a"][0] - d["a"][1])) > 1e-9
    assert torch.allclose(g["a"][0], g["a"][1]) and torch.allclose(g["w"][0], g["w"][1])


def test_E_is_uncoupled():
    _, _, e = coeffs("E", view(seqs=[AB])[0])
    assert float(e["w"].abs().max()) == 0.0


def test_empty_root_noop_only():
    v, _, _ = view()
    net, b, c = coeffs("D", v)
    p = net.predict(b)
    assert len(c["a"]) == 0 and 0.0 < float(p["p_noop"][0]) < 1.0


def test_missing_labels_marginalize():
    v, ym, xm = view(seqs=[AB, BA])
    lab = XY.labels_for(v, ym, xm, {}, {0: 1})
    net, b, c = coeffs("D", v)
    _, lb = XY.collate([v], [lab])
    ev = XY.batched_log_evidence(c["b"], c["a"], c["w"], b["parent"], lb["y_obs"], lb["x_obs"], b["s_root"], 1)
    ref = XY.log_evidence(c["b"], c["a"], c["w"], v["parent"], {}, {0: 1})
    assert torch.allclose(ev[0], ref)


def test_search_legality_and_requery():
    import search as S

    class FakeSampler:
        dev = "cpu"
        calls = raw = 0

        def __init__(self):
            self.seen = []

        def propose_many(self, root, cells, objs, M, gen):
            self.calls += len(objs)
            self.seen.append(tuple(cells))
            return {o: root.legal_dests(cells)[:M] for o in objs}

    class FakeScorer:
        evals = 0

        def score(self, root, seqs):
            self.evals += len(seqs)
            return [{"p11": 0.5 if s else 0.1, "J": 0.0} for s in seqs]

    row = {"root_id": "r", "inputs": {"ids": ["o0", "o1", "o2", "t0"], "tid": 3, "goal_cell": 9, "cells0": [0, 1, 2, 3],
                                      "legal_cells": list(range(16)), "attrs": [[0.024, 0, 1, 0]] * 3 + [[0.024, 1, 0, 0]],
                                      "cell_xy": {str(c): [0.08 * (c % 4), 0.08 * (c // 4)] for c in range(16)}}}
    root = S.Root(row, "2d")
    root.cell_xy = row["inputs"]["cell_xy"]
    fs = FakeSampler()
    out = S.search(root, fs, FakeScorer(), {"M": 2, "max_expansions": 30, "fair": 3, "seed": 0}, mode="iterative")
    for c in out["cands"]:
        objs = [i for i, _ in c["seq"]]
        assert len(c["seq"]) <= 3 and len(set(objs)) == len(objs) and 3 not in objs
        assert all(d not in (0, 1, 2, 3, 9) for _, d in c["seq"])
    assert len(set(fs.seen)) > 1                                   # re-queried on edited scenes
    fs1 = FakeSampler()
    S.search(root, fs1, FakeScorer(), {"M": 2, "max_expansions": 30, "fair": 3, "seed": 0}, mode="oneshot")
    assert set(fs1.seen) == {tuple(root.cells0)}                   # one-shot samples from S0 only
