"""R2.4 synthetic tests (no model, no teacher): exact subset DP == brute force, constrained orders, prerequisite edges, set scoring, chunk-label
extraction.  Declared hash-based fake readouts; never a success claim."""
from __future__ import annotations

import hashlib, itertools, json, math, sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent.parent), str(HERE.parent.parent.parent), str(HERE.parent.parent / "tests")]
import order as OD  # noqa: E402
import views as V  # noqa: E402
from test_fig3 import row  # noqa: E402


class Rand:
    """pX / pY are fixed pseudo-random functions of (moved cells, task, chunk); counts unique readouts."""

    def __init__(self, salt="r24"):
        self.salt, self.n, self.c, self._x, self._y = salt, 0, {"x_unique": 0}, {}, {}

    def _u(self, *a):
        return int(hashlib.sha256((self.salt + json.dumps(a)).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF

    def score(self, r, seqs):
        inp = r["inputs"]
        st = (inp["cells0"], inp["tid"], inp["goal_cell"])
        out = []
        for s in seqs:
            self.n += 1
            u = self._u(st, s)
            out.append({"px": 0.02 + 0.96 * u, "p11": 0.9 * u, "py": 0.5, "px1": u, "px0": u})
        return out

    def p_noop(self, r):
        inp = r["inputs"]
        return self._u(inp["cells0"], inp["tid"], inp["goal_cell"], "noop")

    def y_global(self, r0, E):
        return [self._u(sorted(map(list, e)), "Y") for e in E]


A5 = [[0, 12], [1, 13], [2, 14], [4, 16], [5, 17]]


@pytest.mark.parametrize("m", [2, 3, 4, 5])
@pytest.mark.parametrize("lam", [0.0, OD.LAM, 2.0])
def test_dp_equals_brute(m, lam):
    T = OD.Table(Rand(f"s{m}"), row(), A5[:m])
    d, b = OD.dp(T, lam=lam), OD.brute(T, lam=lam)
    assert abs(d[0] - b[0]) < 1e-9 and sorted(map(tuple, d[1])) == sorted(map(tuple, A5[:m]))
    assert abs(OD.order_cost(T, d[1], d[2], lam) - d[0]) < 1e-9 and all(1 <= g <= 3 for g in d[2]) and sum(d[2]) == m
    if m >= 2:
        d2, b2 = OD.dp(T, lam=lam, min_chunks=2), OD.brute(T, lam=lam, min_chunks=2)
        assert abs(d2[0] - b2[0]) < 1e-9 and len(d2[2]) >= 2


def test_constrained_dp_respects_edges_and_is_exact():
    T = OD.Table(Rand("c"), row(), A5)
    bef = [(A5[3], A5[0]), (A5[0], A5[2]), (A5[1], A5[2])]
    d, b = OD.dp(T, before=bef), OD.brute(T, before=bef)
    assert abs(d[0] - b[0]) < 1e-9
    pos = {tuple(a): i for i, a in enumerate(d[1])}
    assert all(pos[tuple(x)] < pos[tuple(y)] for x, y in bef)
    assert d[0] >= OD.dp(T)[0] - 1e-12                       # restriction can only cost


def test_canonical_prefix_scene_is_order_free_and_cached():
    fz = Rand("k")
    T = OD.Table(fz, row(), A5[:4])
    a = T.get([tuple(A5[0]), tuple(A5[1])], [A5[2]])
    n = fz.n
    b = T.get([tuple(A5[1]), tuple(A5[0])], [A5[2]])
    assert a == b and fz.n == n                              # same placed set -> same scene, cache hit
    r1 = V.rebase(row(), OD.canon([A5[1], A5[0]]))
    r2 = V.rebase(row(), OD.canon([A5[0], A5[1]]))
    assert r1["inputs"] == r2["inputs"] and len(r1["inputs"]["ids"]) == len(row()["inputs"]["ids"])


def test_all_orders_rank_contains_dp_optimum():
    T = OD.Table(Rand("o"), row(), A5[:4])
    ranked = OD.all_orders(T)
    assert len(ranked) == 24 and abs(ranked[0]["E"] - OD.dp(T)[0]) < 1e-9


def test_pair_edges_acyclic():
    E, D = OD.pair_edges(Rand("p"), row(), A5, delta=-1.0)   # delta < 0 forces many candidate edges -> cycle breaking exercised
    assert OD._cycle([(tuple(a), tuple(b)) for a, b, _ in E]) is None
    assert len(D) == 20


def test_kendall():
    o = [[0, 1], [2, 3], [4, 5]]
    assert OD.kendall(o, o) == 0 and OD.kendall(o, o[::-1]) == 1


def test_score_set_single_chunk_uses_exact_p11_and_multichunk_uses_y():
    import arms as AR
    fz = Rand("s")
    c = AR.score_set(fz, row(), A5[:2])
    p11 = max(x["p11"] for x in fz.score(row(), [A5[:2], A5[1::-1]]))
    T = OD.Table(fz, row(), A5[:2])
    multi = OD.dp(T, min_chunks=2)[0] - math.log(fz.y_global(row(), [A5[:2]])[0])
    assert abs(c["E"] - min(-math.log(p11), multi)) < 1e-9
    c4 = AR.score_set(fz, row(), A5[:4])
    assert len(c4["partition"]) >= 2 and sum(c4["partition"]) == 4


def test_chunk_labels_from_trace():
    import labels as LB
    order = [["a", 1], ["b", 2], ["c", 3], ["d", 4], ["e", 5]]
    ch = LB.chunks_of(order, [2, 4, 5], {"x": 0, "phase": "relocation:3"})
    assert [(c["prefix_len"], len(c["chunk"]), c["label"]) for c in ch] == [(0, 2, 1), (2, 2, 0)]
    ch = LB.chunks_of(order, [2, 5], {"x": 0, "phase": "boundary:2"})
    assert [(c["label"], c["connector_fail"]) for c in ch] == [(0, True)]
    ch = LB.chunks_of(order, [5], {"x": 0, "phase": "relocation:1"})
    assert [(len(c["chunk"]), c["label"], c["kind"]) for c in ch] == [(2, 0, "continuous_prefix_neg"), (3, 0, "continuous_prefix_neg")]
    ch = LB.chunks_of(order[:3], [1, 3], {"x": 1})
    assert [(c["prefix_len"], c["label"]) for c in ch] == [(0, 1), (1, 1)]
    assert LB.chunks_of(order, [2, 5], {"x": 0, "phase": "relocation:0", "status": "UNKNOWN_PLANNER"}, unknown=True) == []
