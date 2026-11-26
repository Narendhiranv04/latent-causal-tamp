"""R3 tests: F1 freeze mask (Y bitwise, X moves), exact lone-X marginal likelihood, shared endpoint Y node for permutations, conflicting
duplicate local labels dropped, split / lineage leakage (data-dependent tests skip when the gvlab2 artifacts are absent)."""
from __future__ import annotations

import json, math, sys
from pathlib import Path

import pytest
import torch

HERE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent)]
import xy as XY  # noqa: E402
import train as TR  # noqa: E402
import common3 as K  # noqa: E402


def _view(n=6, seqs=None, seed=0):
    g = torch.Generator().manual_seed(seed)
    xy0 = (torch.rand(n, 2, generator=g) * 0.4).tolist()
    attrs = [[1.0, 0.0, 0.05, 0.1, float(i == 0)] for i in range(n)]
    seqs = seqs or [[(1, (0.3, 0.3))], [(2, (0.1, 0.35)), (3, (0.35, 0.05))], [(3, (0.35, 0.05)), (2, (0.1, 0.35))]]
    return XY.make_view("t", xy0, attrs, 0, (0.2, 0.2), (0.0, 0.0), [0.1] * 19, [], seqs, XY._NoGeo)


def _net():
    torch.manual_seed(0)
    return XY.XYNet("D", 5, 19).double()


def test_f1_freeze_mask_keeps_y_bitwise():
    base = _net()
    net = TR.make_net("3d", "F1", base)
    names = {n.split(".")[0] for n, p in net.named_parameters() if p.requires_grad}
    assert names == set(TR.X_ONLY)
    v, ym, xm = _view()
    lab = XY.labels_for(v, ym, xm, {}, {0: 0, 1: 1, 2: 0})
    b, L = XY.collate([v], [lab], dtype=torch.float64)
    c0 = base.coeffs(b)
    opt = torch.optim.SGD([p for p in net.parameters() if p.requires_grad], lr=0.5)
    for _ in range(3):
        nll = -XY.batched_log_evidence(*(lambda C: (C["b"], C["a"], C["w"]))(net.coeffs(b)), b["parent"], L["y_obs"], L["x_obs"], b["s_root"], 1).mean()
        opt.zero_grad(); nll.backward(); opt.step()
    c1 = net.coeffs(b)
    assert torch.equal(c0["b"], c1["b"])
    assert not torch.allclose(c0["a"], c1["a"])
    for (n, p0), (_, p1) in zip(base.named_parameters(), net.named_parameters()):
        if n.split(".")[0] not in TR.X_ONLY:
            assert torch.equal(p0, p1), n


def test_lone_x_is_marginal_bernoulli():
    v, ym, xm = _view(seqs=[[(1, (0.3, 0.3))]])
    for x in (0, 1):
        lab = XY.labels_for(v, ym, xm, {}, {0: x})
        b, L = XY.collate([v], [lab], dtype=torch.float64)
        C = _net().coeffs(b)
        le = float(XY.batched_log_evidence(C["b"], C["a"], C["w"], b["parent"], L["y_obs"], L["x_obs"], b["s_root"], 1)[0])
        py = torch.sigmoid(C["b"][b["parent"][0]]); px = float(py * torch.sigmoid(C["a"][0] + C["w"][0]) + (1 - py) * torch.sigmoid(C["a"][0]))
        assert abs(le - math.log(px if x else 1 - px)) < 1e-10


def test_permutations_share_endpoint_node():
    v, _, xm = _view()
    assert v["parent"][xm[1]] == v["parent"][xm[2]] and xm[1] != xm[2]


def test_local_views_drop_conflicts(monkeypatch):
    import views as V
    n = 6
    row = {"root_id": "r", "domain": "3d", "inputs": {"ids": [f"o{i}" for i in range(n)], "xy0": [[0.1 * i, 0.1] for i in range(n)], "cells0": list(range(n)),
           "attrs": [[1.0, 0.0, 0.05, 0.1, float(i == 0)] for i in range(n)], "tid": 0, "goal": [0.3, 0.3], "goal_cell": 20, "base": [0.0, 0.0],
           "ctx": [0.0] * 19, "q_ref": [0.0] * 7, "legal_cells": list(range(36)), "cell_xy": {str(c): [0.05 * (c % 6), 0.05 * (c // 6)] for c in range(36)}}}
    mk = lambda ch, lab, h=0, pre=(): {"root_id": "r", "fam": "f", "base": [], "prefix": list(pre), "chunk": ch, "label": lab, "h": h}  # noqa: E731
    labs = [mk([[1, 30]], 1), mk([[1, 30]], 0), mk([[2, 31]], 1), mk([[3, 32]], 0, 1, [[2, 31]])]
    out, conf = TR.local_views("3d", labs, {"r": row})
    assert conf == 1 and len(out) == 2 and sum(len(o["v"]["x_seqs"]) for o in out) == 2
    assert V.rebase(row, [[2, 31]])["inputs"]["cells0"][2] == 31


@pytest.mark.skipif(not (K.O / "scenes_31_3d.json").exists(), reason="gvlab2 artifacts")
def test_scale_splits_family_disjoint_and_clean():
    S = json.loads((K.O / "scenes_31_3d.json").read_text())
    lin = json.loads((K.O / "lineage_3d.json").read_text())
    tr = {s["fam"] for s in S if s["split"] == "TRAIN_SCALE"}; va = {s["fam"] for s in S if s["split"] == "VAL_SCALE"}
    assert not tr & va
    assert not (tr | va) & set(lin["diag_fams"]) and not (tr | va) & set(lin["dev_fams"])
    assert not {s["root_id"] for s in S} & set(lin["dev_roots"])


@pytest.mark.parametrize("arm", ["G1", "M1"])
def test_xrel_invariance_order_and_y(arm):
    import xrel
    base = _net()
    net = xrel.build(arm, base).double()
    v, ym, xm = _view(n=7)
    b, _ = XY.collate([v], dtype=torch.float64)
    C1, C0 = net.coeffs(b), base.coeffs(b)
    assert torch.equal(C1["b"], C0["b"])                                   # Y path is F0 bitwise
    assert not torch.allclose(C1["a"][xm[1]], C1["a"][xm[2]])             # order-sensitive (same endpoint, different order)
    perm = [0, 3, 1, 6, 2, 5, 4]                                           # relabel object slots (target stays 0)
    inv = {o: i for i, o in enumerate(perm)}
    xy0 = [v["xy0"][o] for o in perm]; at = [v["attrs"][o] for o in perm]
    seqs = [[(inv[i], p) for i, p in q] for q in v["x_seqs"]]
    v2, _, _ = XY.make_view("t", xy0, at, 0, v["goal"], v["base"], v["ctx"], [], seqs, XY._NoGeo)
    b2, _ = XY.collate([v2], dtype=torch.float64)
    C2 = net.coeffs(b2)
    assert torch.allclose(C1["a"], C2["a"], atol=1e-9) and torch.allclose(C1["w"], C2["w"], atol=1e-9)
    assert all(p.requires_grad is False for p in net.base.parameters())
