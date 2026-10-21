"""G4E-ABC model mathematics on synthetic learner-view fixtures (no teacher, no DINOv2 download)."""
import copy
import itertools
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import abc_models as am  # noqa: E402
import abc_train as at  # noqa: E402
import learn_data as ld  # noqa: E402
import zlayout as zl  # noqa: E402

torch.manual_seed(0)
CAT = [{"kind": "singleton:A", "edit": {"oA": 9}, "eligible": True}, {"kind": "singleton:B", "edit": {"oB": 20}, "eligible": True},
       {"kind": "joint:A+B", "edit": {"oA": 9, "oB": 20}, "eligible": True}]


def _rec(labels=True):
    rng = np.random.default_rng(1)
    ids, n = ["oA", "oB", "oC", "t0"], 4
    xy = np.array([[0.2, 0.3], [0.4, 0.5], [0.6, 0.1], [0.5, 0.3]], np.float32)
    inputs = {"object_xy": xy, "object_radius": np.full(n, 0.024, np.float32), "is_active_target": np.array([0, 0, 0, 1], np.float32),
              "is_obstacle": np.array([1, 1, 1, 0], np.float32), "robot_q": np.array([1.57, 1.57, 1.57], np.float32),
              "goal_xy": np.array([0.2, 0.6], np.float32), "robot_fk_joints": rng.normal(size=(4, 2)).astype(np.float32),
              "visual": rng.normal(size=(n, 384)).astype(np.float32)}
    seqs = [[], [("oA", 9)], [("oB", 20)], [("oA", 9), ("oB", 20)], [("oB", 20), ("oA", 9)]]
    ys = [0, 0, 0, 0, 1]
    cands = []
    for s, y in zip(seqs, ys):
        lay = zl.build("k", s, CAT)
        q = lay["query"]
        lab = {"seq:k:empty": 0, "seq:k:oA>9": 0, "seq:k:oB>20": 0, "seq:k:oA>9.oB>20": 0, "seq:k:oB>20.oA>9": 1,
               "scene:k:oA>9": 0, "scene:k:oB>20": 0, "scene:k:oA>9.oB>20": 1}
        cands.append({"actions": [(ids.index(o), [0.04 + 0.08 * (d % 8), 0.04 + 0.08 * (d // 8)]) for o, d in s],
                      "z_slots": list(q), "z_queries": list(q.values()),
                      "privileged": {"query": q.get("zR", q["z0"]), "y": y if labels else None, "source": "WITNESS" if y else "PLANNER_BUDGET",
                                     "weight": 1.0, "cost": (0.5 * len(s) if s and labels else None),
                                     "z": [lab[x] if labels else None for x in q.values()], "z_source": ["WITNESS"] * len(q),
                                     "static": {"unary": [1] * n if labels else [None] * n,
                                                "pair": {f"{a}|{b}": (1 if labels else None) for i, a in enumerate(ids) for b in ids[i + 1:]}}}})
    edits = [{"kind": c["kind"], "poses": {ids.index(o): [0.04 + 0.08 * (d % 8), 0.04 + 0.08 * (d // 8)] for o, d in c["edit"].items()},
              "eligible": True, "privileged": {"query": f"scene:k:{zl.sig(sorted(c['edit'].items()))}", "y": ({"singleton:A": 0, "singleton:B": 0,
                                                                                                                "joint:A+B": 1}[c["kind"]] if labels else None),
                                               "source": "WITNESS"}} for c in CAT]
    return {"inputs": inputs, "candidates": cands, "edits": edits, "audit": {"root": "k", "split": "train", "source": "SYN", "ids": ids}}


@pytest.mark.parametrize("name", ["B", "C", "B-no-coupling"])
def test_exact_joint_partition_marginals_and_states(name):
    m, r = am.build(name), at.prepare({"roots": [_rec()]})[0]
    c = r["cands"][3]
    o = m.joint(r["R"], c["seq"], c["slots"], r["edits"])
    K = len(c["slots"])
    assert o["E_states"].shape == (2 ** K,) and K == 7                               # V2: 7 active, no no-op slot
    brute = []
    for bits in itertools.product((0, 1), repeat=K):
        z = torch.tensor(bits, dtype=torch.float64)
        brute.append(float(-(o["E_static"] - z @ o["s"] - 0.5 * z @ o["W"] @ z).detach()))
    lse = np.logaddexp.reduce(np.array(brute))
    assert abs(float(o["lse"].detach()) - lse) < 1e-9
    p = np.exp(np.array(brute) - lse)
    assert np.allclose(p @ np.array(list(itertools.product((0, 1), repeat=K))), o["marg"].detach().numpy(), atol=1e-12)
    assert float(o["W"].diagonal().abs().sum()) == 0.0 and torch.allclose(o["W"], o["W"].T)


def test_masked_fields_give_no_loss_and_zero_gradient():
    m = am.build("C")
    r = at.prepare({"roots": [_rec(labels=False)]})[0]
    L = at.losses(m, r)
    assert all(v is None for v in L.values())
    rl = at.prepare({"roots": [_rec()]}, certified_only=True)[0]                       # budget-sourced labels masked
    assert all(c["y"] in (None, 1) for c in rl["cands"]) and rl["y"]["seq:k:empty"] is None


def test_coupling_receives_gradient_only_when_present():
    r = at.prepare({"roots": [_rec()]})[0]
    for name, expect in (("B", True), ("C", True), ("B-no-coupling", False), ("C-no-coupling", False)):
        m = am.build(name)
        L = at.losses(m, r)
        assert L["pool"] is not None
        sum(v for v in L.values() if v is not None).backward()
        g = sum(float(p.grad.norm()) for p in m.cpl.parameters() if p.grad is not None)
        assert (g > 0) == expect, name


def test_order_sensitivity_capacity_and_no_double_counting():
    r = at.prepare({"roots": [_rec()]})[0]
    ab, ba = r["cands"][3]["seq"], r["cands"][4]["seq"]
    a, a0 = am.build("A"), am.build("A-no-order")
    assert abs(float(a.seq(r["R"], ab)["u"] - a.seq(r["R"], ba)["u"])) > 1e-9
    assert abs(float(a0.seq(r["R"], ab)["u"] - a0.seq(r["R"], ba)["u"])) < 1e-12        # shuffled order gets no credit
    b, c = am.build("B"), am.build("C")
    assert hasattr(b, "pairo") and not hasattr(b, "gru") and hasattr(c, "gru") and not hasattr(c, "pairo")
    sb = [float(b.order(r["R"], s)[0]) for s in (ab, ba)]
    assert abs(sb[0] - sb[1]) > 1e-9                                                     # prefix-pair order factor


def test_pair_energy_symmetric_and_static_permutation_invariant():
    m = am.build("A")
    rec = _rec()
    R = am.Root(rec)
    e1, _, lp = m.static(R, R.xy0)
    perm = [2, 0, 3, 1]
    rec2 = copy.deepcopy(rec)
    per_object = ("object_xy", "object_radius", "is_active_target", "is_obstacle", "visual")
    rec2["inputs"] = {k: (v[perm] if k in per_object else v) for k, v in rec["inputs"].items()}
    R2 = am.Root(rec2)
    e2, _, _ = m.static(R2, R2.xy0)
    assert abs(float(e1 - e2)) < 1e-9


def test_marginal_energy_gradient_matches_finite_difference():
    m, r = am.build("B"), at.prepare({"roots": [_rec()]})[0]
    c = r["cands"][3]
    p = m.scene[2].bias
    f = lambda: float(m.joint(r["R"], c["seq"], c["slots"], r["edits"])["E_bar"])   # noqa: E731
    e = m.joint(r["R"], c["seq"], c["slots"], r["edits"])["E_bar"]
    (g,) = torch.autograd.grad(e, p)
    with torch.no_grad():
        p += 1e-6
        up = f()
        p -= 2e-6
        dn = f()
        p += 1e-6
    assert abs(float(g[0]) - (up - dn) / 2e-6) < 1e-5


@pytest.mark.parametrize("name", ["A", "B", "C"])
def test_tiny_overfit_and_order_pair_fit(name):
    torch.manual_seed(0)
    m, roots = am.build(name), at.prepare({"roots": [_rec()]})
    hist = at.train(m, roots, 60, 120.0, print)
    assert hist[-1]["total"] < 0.6 * hist[0]["total"]
    r = roots[0]
    at.losses(m, r)
    assert r["cands"][4]["_p"] > r["cands"][3]["_p"]                                  # witnessed order beats its swap


def test_leakage_audit_flags_extra_input_keys():
    ds = {"roots": [_rec()]}
    assert ld.leakage_audit(ds) == []
    bad = copy.deepcopy(ds)
    bad["roots"][0]["inputs"]["teacher_label"] = np.zeros(1)
    assert ld.leakage_audit(bad)
