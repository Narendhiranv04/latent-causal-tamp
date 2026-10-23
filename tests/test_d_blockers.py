"""D_BLOCKERS_V1 synthetic tests: exact normalization, gradients, permutation equivariance, partial labels, alternative / joint minimal
sets, no-blocker states, cap failure, independent enumerator cross-check, zero physical calls."""
import itertools
import math

import numpy as np
import pytest
import torch

import d_blockers as db


def _root(n=5, seed=0):
    g = np.random.default_rng(seed)
    t = np.zeros(n)
    t[0] = 1
    rec = {"inputs": {"object_xy": g.uniform(0, 0.6, (n, 2)), "visual": g.normal(size=(n, 384)), "object_radius": np.full(n, 0.024),
                      "is_active_target": t, "is_obstacle": 1 - t, "robot_fk_joints": g.uniform(-0.2, 0.4, (4, 2)),
                      "goal_xy": g.uniform(0, 0.6, 2), "robot_q": g.uniform(-1, 1, 3)}}
    return db.root_tensors(rec)


def _model(pair=True, seed=0):
    torch.manual_seed(seed)
    return db.ModelD(pair=pair).double()


def test_exact_normalization_matches_bruteforce():
    m, R = _model(), _root()
    u, a, w = m(R, [1, 2, 3, 4])
    p = torch.sigmoid(u)
    tot = p.clone()
    for b in itertools.product((0, 1), repeat=4):
        bb = torch.tensor(b, dtype=torch.float64)
        s = bb @ a + sum(w[i, j] * bb[i] * bb[j] for i in range(4) for j in range(i + 1, 4))
        zs = [torch.tensor(c, dtype=torch.float64) for c in itertools.product((0, 1), repeat=4)]
        Z = sum(torch.exp(z @ a + sum(w[i, j] * z[i] * z[j] for i in range(4) for j in range(i + 1, 4))) for z in zs)
        idx = int("".join(map(str, b)), 2)
        assert torch.isclose(db.blocker_logp(a, w)[idx], s - torch.log(Z), atol=1e-10)
        tot = tot + (1 - p) * torch.exp(s) / Z
    assert torch.isclose(tot, torch.tensor(1.0, dtype=torch.float64), atol=1e-12)


def test_gradcheck():
    a = torch.randn(3, dtype=torch.float64, requires_grad=True)
    w0 = torch.randn(3, 3, dtype=torch.float64)
    w = (w0 + w0.T).fill_diagonal_(0).requires_grad_(True)
    u = torch.randn((), dtype=torch.float64, requires_grad=True)
    assert torch.autograd.gradcheck(lambda u_, a_, w_: db.nll(u_, a_, 0.5 * (w_ + w_.T), 0, [1, 0, 1], 0.7), (u, a, w))


def test_permutation_equivariance():
    m, R = _model(), _root()
    p1, p2 = db.predict(m, R, [1, 2, 3, 4]), db.predict(m, R, [3, 1, 4, 2])
    assert math.isclose(p1["p_feasible"], p2["p_feasible"], abs_tol=1e-12)
    inv = {o: k for k, o in enumerate([3, 1, 4, 2])}
    assert all(math.isclose(p1["marg"][k], p2["marg"][inv[o]], abs_tol=1e-10) for k, o in enumerate([1, 2, 3, 4]))


def test_pairless_control_has_zero_pairs_and_independent_marginals():
    m, R = _model(pair=False), _root()
    u, a, w = m(R, [1, 2, 3])
    assert torch.count_nonzero(w) == 0
    assert np.allclose(db.predict(m, R, [1, 2, 3])["marg"], torch.sigmoid(a).detach().numpy(), atol=1e-12)


def test_partial_mask_is_feasibility_only():
    u, a, w = torch.tensor(0.3, dtype=torch.float64), torch.randn(3, dtype=torch.float64), torch.zeros(3, 3, dtype=torch.float64)
    bce = torch.nn.functional.binary_cross_entropy_with_logits(u, torch.tensor(0.0, dtype=torch.float64))
    assert torch.isclose(db.nll(u, a, w, 0, None), bce)
    assert torch.isclose(db.nll(u, a, w, 1, [1, 1, 0]), torch.nn.functional.binary_cross_entropy_with_logits(u, torch.tensor(1.0, dtype=torch.float64)))


def test_cap_fails_closed():
    with pytest.raises(db.CapError):
        _model()(_root(n=9), list(range(1, 8)))


def _st(n, feas):
    """status table where subset s is VERIFIED iff feas(s), else CERTIFIED."""
    return {frozenset(c): (db.V if feas(frozenset(c)) else db.C) for k in range(n + 1) for c in itertools.combinations(range(n), k)}


def test_minimal_sets_cases():
    alt = db.minimal_sets(2, _st(2, lambda s: len(s) >= 1))                   # redundancy: {0} or {1}
    assert alt["sets"] == [[0], [1]] and alt["mask"] == [1, 1] and alt["necessary"] == [0, 0]
    joint = db.minimal_sets(3, _st(3, lambda s: {0, 2} <= s))                 # jointly necessary pair, 1 irrelevant
    assert joint["sets"] == [[0, 2]] and joint["mask"] == [1, 0, 1] and joint["necessary"] == [1, 0, 1]
    assert db.minimal_sets(2, _st(2, lambda s: True))["type"] == "FEASIBLE_ORIGINAL"
    assert db.minimal_sets(2, _st(2, lambda s: False))["type"] == "NO_CLEARING_SET_WITHIN_POOL"
    nm = _st(2, lambda s: s == frozenset({0}))
    assert db.minimal_sets(2, nm)["type"] == "NON_MONOTONE" and db.minimal_sets(2, nm)["mask"] is None
    inc = _st(2, lambda s: s == frozenset({0, 1}))
    inc[frozenset({1})] = "UNKNOWN"
    assert db.minimal_sets(2, inc)["mask"] is None
    op = _st(2, lambda s: s == frozenset({0, 1}))
    op[frozenset({0})] = db.B
    assert db.minimal_sets(2, op)["provenance"] == "operational"


def test_independent_enumerator_agrees_on_random_monotone_tables():
    g = np.random.default_rng(1)
    for _ in range(200):
        n = int(g.integers(1, 5))
        gens = [frozenset(int(x) for x in g.choice(n, int(g.integers(1, n + 1)), replace=False)) for _ in range(int(g.integers(0, 3)))]
        feas = lambda s: any(x <= s for x in gens)  # noqa: E731
        got = db.minimal_sets(n, _st(n, feas))
        mins = {x for x in gens if not any(y < x for y in gens)}             # brute force from the generators
        if not gens:
            assert got["type"] == "NO_CLEARING_SET_WITHIN_POOL"
            continue
        if frozenset() in mins:
            assert got["type"] == "FEASIBLE_ORIGINAL"
            continue
        assert sorted(map(sorted, mins)) == sorted(got["sets"])
        assert got["mask"] == [int(any(i in x for x in mins)) for i in range(n)]


def test_zero_physical_calls_in_d_inference():
    import p10_protocol as pp
    calls = pp.instrument()
    m, R = _model(), _root()
    db.predict(m, R, [1, 2, 3])
    db.heuristic(R, [1, 2, 3])
    assert sum(calls.values()) == 0
