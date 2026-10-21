"""P6 foundation: Z_LAYOUT_V3_R4 (K <= 9), uniform reference measure, 4-move sampler balance,
higher-order representational audit, four-action order fixture, training guards. No teacher calls."""
import itertools
import math
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import abc_models as am  # noqa: E402
import abc_train as at  # noqa: E402
import g4b  # noqa: E402
import sampler as sp  # noqa: E402
import zlayout as zl  # noqa: E402
import zlayout_r4 as z4  # noqa: E402

CAT = [{"kind": "A", "edit": {"oA": 9}, "eligible": True}, {"kind": "B", "edit": {"oB": 20}, "eligible": True},
       {"kind": "A+B", "edit": {"oA": 9, "oB": 20}, "eligible": True}]
SEQ4 = [("oA", 9), ("oB", 20), ("oC", 30), ("oD", 40)]


@pytest.mark.parametrize("m,k", [(0, 4), (1, 5), (2, 7), (3, 8), (4, 9)])
def test_active_slots_by_length_and_512_states(m, k):
    lay = z4.build("k", SEQ4[:m], CAT)
    assert lay["active_count"] == k and len(set(lay["query"].values())) == k
    if m == 4:
        assert len(z4.states(lay)) == 512
        assert [lay["query"][f"zO[{t}]"] for t in range(4)] == [f"seq:k:{z4.sig([a for i, a in enumerate(SEQ4) if i != t])}" for t in range(4)]
    with pytest.raises(ValueError):
        z4.build("k", SEQ4 + [("oE", 50)], CAT)                                       # > 4 moves
    if m == 4:
        with pytest.raises(ValueError):                                                # nuisance must stay outside the r4 layout
            z4.build("k", SEQ4, CAT + [{"kind": "nuisance", "edit": {"oN": 60}, "eligible": True}])


def test_v3_matches_v2_on_up_to_three_moves():
    for m in range(4):
        a, b = zl.build("k", SEQ4[:m], CAT), z4.build("k", SEQ4[:m], CAT)
        assert a["query"] == b["query"] and a["active_count"] == b["active_count"]


def test_uniform_measure_removes_cardinality_preference_and_keeps_conditionals():
    zero = lambda z: 0.0                                                              # noqa: E731
    e = {m: z4.exact_marginal(zero, z4.build("k", SEQ4[:m], CAT), 1.0)[0] for m in range(5)}
    raw = {m: z4.exact_marginal(zero, z4.build("k", SEQ4[:m], CAT), 1.0, "raw")[0] for m in range(5)}
    assert max(e.values()) - min(e.values()) < 1e-12                                  # equal raw energies -> equal E_bar
    assert raw[4] < raw[0] - 3.0                                                       # raw convention prefers more slots
    rng = np.random.default_rng(1)
    th = rng.normal(size=9)
    lay = z4.build("k", SEQ4, CAT)
    names = [s for s, a in zip(lay["slots"], lay["active"]) if a]
    f = lambda z: float(th @ np.array([z[n] for n in names]))                         # noqa: E731
    _, pu = z4.exact_marginal(f, lay, 0.8)
    _, pr = z4.exact_marginal(f, lay, 0.8, "raw")
    assert np.allclose([p for _, p in pu], [p for _, p in pr]) and math.isclose(sum(p for _, p in pu), 1.0)


def test_unequal_K_marginal_energy_sampler_detailed_balance_with_four_moves():
    dests = {"A": [1, 2], "B": [3], "C": [4], "D": [5]}
    dom, states = sp.Domain.make(dests, 4), g4b.reference_states(dests, 4)
    cat = [{"kind": "x", "edit": {"A": 7}, "eligible": True}]

    def energy(r):
        lay = z4.build("k", list(r), cat)
        rng = np.random.default_rng(abs(hash(r)) % 2 ** 32)
        th = rng.normal(size=lay["active_count"])
        names = [s for s, a in zip(lay["slots"], lay["active"]) if a]
        return z4.exact_marginal(lambda z: float(th @ np.array([z[n] for n in names])), lay, 1.0)[0]
    cache = {}
    cert, _, _ = g4b.certify(dom, lambda r: cache.setdefault(r, energy(r)), 1.0, states)
    assert cert["pass"] and len(states) > 60 and {len(s) for s in states} == {0, 1, 2, 3, 4}


def _quad_kl(target, steps=1500):
    Z = torch.tensor(list(itertools.product((0.0, 1.0), repeat=3)), dtype=torch.float64)
    s, w = torch.zeros(3, dtype=torch.float64, requires_grad=True), torch.zeros(3, 3, dtype=torch.float64, requires_grad=True)
    opt = torch.optim.Adam([s, w], lr=0.05)
    for _ in range(steps):
        opt.zero_grad()
        ws = torch.triu(w, 1)
        logp = torch.log_softmax(Z @ s + ((Z @ (ws + ws.T)) * Z).sum(1) / 2, 0)
        kl = (target * (target.log() - logp)).sum()
        kl.backward()
        opt.step()
    return float(kl.detach())


def _ho_kl(target, steps=3000):
    torch.manual_seed(0)
    m = am.build("B", higher_order=True)
    Z = torch.tensor(list(itertools.product((0.0, 1.0), repeat=3)), dtype=torch.float64)
    v = torch.randn(3, am.W, dtype=torch.float64, requires_grad=True)
    opt = torch.optim.Adam([v, *m.ho_u.parameters(), *m.ho.parameters()], lr=0.01)
    g = torch.zeros(am.W, dtype=torch.float64)
    for _ in range(steps):
        opt.zero_grad()
        logp = torch.log_softmax(m.ho(torch.cat([Z @ m.ho_u(v), g.expand(8, -1)], 1))[:, 0], 0)
        kl = (target * (target.log() - logp)).sum()
        kl.backward()
        opt.step()
    return float(kl.detach())


def test_higher_order_audit_parity_needs_the_residual():
    Z = np.array(list(itertools.product((0, 1), repeat=3)))
    target = torch.tensor(np.exp(-3.0 * (Z.sum(1) % 2)), dtype=torch.float64)
    target = target / target.sum()
    assert _quad_kl(target) > 0.15                                                      # pairwise binary energy: representation limit
    assert _ho_kl(target) < 0.01                                                         # masked MLP residual: representable


def _rec4():
    rng = np.random.default_rng(2)
    ids = ["oA", "oB", "oC", "oD", "t0"]
    n = 5
    xy = np.array([[0.2, 0.3], [0.4, 0.5], [0.6, 0.1], [0.1, 0.6], [0.5, 0.3]], np.float32)
    inputs = {"object_xy": xy, "object_radius": np.full(n, 0.024, np.float32), "is_active_target": np.array([0, 0, 0, 0, 1], np.float32),
              "is_obstacle": np.array([1, 1, 1, 1, 0], np.float32), "robot_q": np.array([1.57, 1.57, 1.57], np.float32),
              "goal_xy": np.array([0.2, 0.6], np.float32), "robot_fk_joints": rng.normal(size=(4, 2)).astype(np.float32),
              "visual": rng.normal(size=(n, 384)).astype(np.float32)}
    cell = lambda d: [0.04 + 0.08 * (d % 8), 0.04 + 0.08 * (d // 8)]  # noqa: E731
    cands = []
    for perm in itertools.permutations(range(4)):
        seq = [SEQ4[i] for i in perm]
        y = int(perm.index(0) < perm.index(1))                                             # A before B (12 vs 12)
        lay = z4.build("k", seq, [])
        cands.append({"actions": [(ids.index(o), cell(d)) for o, d in seq], "z_slots": list(lay["query"]), "z_queries": list(lay["query"].values()),
                      "privileged": {"query": lay["query"]["zR"], "y": y, "source": "WITNESS", "weight": 1.0, "cost": None,
                                     "z": [0, y] + [None] * 4, "z_source": ["WITNESS"] * 2 + [None] * 4, "static": {"unary": [None] * n,
                                                                            "pair": {f"{a}|{b}": None for i, a in enumerate(ids) for b in ids[i + 1:]}}}})
    return {"inputs": inputs, "candidates": cands, "edits": [], "audit": {"root": "k", "split": "train", "source": "SYN", "ids": ids}}


@pytest.mark.parametrize("name", ["A", "A-no-order", "B", "C"])
def test_four_action_order_fixture(name):
    torch.manual_seed(0)
    roots = at.prepare({"roots": [_rec4()]})
    m = am.build(name, measure="uniform") if name in ("B", "C") else am.build(name)
    at.train(m, roots, 60, 300.0, print, lr=3e-3, clip=1.0)
    at.losses(m, roots[0])
    ps = np.array([float(c["_p"].detach()) for c in roots[0]["cands"]])
    ys = np.array([c["y"] for c in roots[0]["cands"]])
    if name == "A-no-order":
        assert np.ptp(ps) < 1e-9                                                          # provably order-invariant
    else:
        assert ps[ys == 1].min() > ps[ys == 0].max()                                      # 24 permutations separated


def test_guards_capacity_geometry_only_and_gradient_paths():
    a, c = am.build("A", extra=515), am.build("C", higher_order=True, measure="uniform")
    na, nc = sum(p.numel() for p in a.parameters()), sum(p.numel() for p in c.parameters())
    assert abs(na - nc) / nc < 0.01
    g = am.build("B", vision=False)
    assert g.vproj is None
    rec = _rec4()
    r1, r2 = am.Root(rec), am.Root({**rec, "inputs": {**rec["inputs"], "visual": rec["inputs"]["visual"] * 0 + 5}})
    assert torch.equal(g.encode(r1, r1.xy0), g.encode(r2, r2.xy0))                       # visual input ignored
    roots = at.prepare({"roots": [_rec4()]})
    h = at.train(am.build("C", higher_order=True, measure="uniform"), roots, 3, 60.0, print, clip=1.0)
    assert all(x["grad_post"] <= 1.0 + 1e-9 for x in h if "grad_post" in x)
    m = am.build("C", higher_order=True)
    L = at.losses(m, roots[0])
    sum(v for v in L.values() if v is not None).backward()
    assert sum(float(p.grad.norm()) for p in m.ho.parameters()) > 0                      # residual receives gradient
    assert not hasattr(am.build("C-no-coupling", higher_order=True), "ho")
    for name in ("B", "C"):                                                               # travel cost J stays a scalar
        mm = am.build(name, higher_order=True, measure="uniform")
        for c in roots[0]["cands"][:2]:
            o = mm.joint(roots[0]["R"], c["seq"], c["slots"], roots[0]["edits"])
            assert o["J"].shape == () and o["E_bar"].shape == ()
    bad = at.prepare({"roots": [_rec4()]})
    bad[0]["R"].xy0[0, 0] = float("nan")
    hist = at.train(am.build("A"), bad, 5, 60.0, print, clip=1.0)
    assert hist[-1].get("nonfinite")
