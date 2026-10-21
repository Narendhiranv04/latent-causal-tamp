"""P7a: ABC7 factor mapping, exact joint, root consistency, ablation switches, kappa fixtures (no teacher)."""
import itertools
import math
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import abc7_models as a7  # noqa: E402
import abc7_train as t7  # noqa: E402
import zlayout_r4 as z4  # noqa: E402

IDS = ["o00", "o01", "o02", "o03", "t0"]
CELL = {"o00": 9, "o01": 20, "o02": 30, "o03": 40}
SEQS = [[], ["o00"], ["o01"], ["o00", "o01"], ["o01", "o00"], ["o02", "o00", "o01"], ["o00", "o01", "o02", "o03"],
        ["o01", "o02", "o03"], ["o00", "o02", "o03"], ["o00", "o01", "o03"], ["o00", "o01", "o02"]]


def xy(c):
    return [0.04 + 0.08 * (c % 8), 0.04 + 0.08 * (c // 8)]


def fixture(seed, scene=(0, 0, 0, 1), feasible=lambda s: {"o00", "o01"} <= set(s)):
    """One synthetic root: edits A = o00, B = o01, A+B; scene labels (z0, zA, zB, zAB); repair labels by `feasible`."""
    rng = np.random.default_rng(seed)
    pos = rng.uniform(0.1, 0.55, size=(5, 2)).astype(np.float32)
    inputs = {"object_xy": pos, "object_radius": np.full(5, 0.024, np.float32), "is_active_target": np.array([0, 0, 0, 0, 1], np.float32),
              "is_obstacle": np.array([1, 1, 1, 1, 0], np.float32), "robot_q": rng.uniform(-2, 2, 3).astype(np.float32),
              "goal_xy": rng.uniform(0.1, 0.6, 2).astype(np.float32), "robot_fk_joints": rng.normal(size=(4, 2)).astype(np.float32),
              "visual": rng.normal(size=(5, 384)).astype(np.float32)}
    cat = [{"kind": "A", "edit": {"o00": 9}, "eligible": True}, {"kind": "B", "edit": {"o01": 20}, "eligible": True},
           {"kind": "A+B", "edit": {"o00": 9, "o01": 20}, "eligible": True}]
    lab = {f"seq:k{seed}:empty": scene[0]} | {f"scene:k{seed}:{z4.sig(sorted(q['edit'].items()))}": y for q, y in zip(cat, scene[1:])}
    for s in SEQS[1:]:
        lab[f"seq:k{seed}:{z4.sig([(o, CELL[o]) for o in s])}"] = int(feasible(s))
    cands = []
    for s in SEQS:
        seq = [(o, CELL[o]) for o in s]
        lay = z4.build(f"k{seed}", seq, cat)
        q = lay["query"]
        z = [lab.get(x) for x in q.values()]
        cands.append({"actions": [(IDS.index(o), xy(c)) for o, c in seq], "z_slots": list(q), "z_queries": list(q.values()),
                      "privileged": {"query": q.get("zR", q["z0"]), "y": lab[q.get("zR", q["z0"])], "source": "WITNESS", "weight": 1.0,
                                     "cost": 1.0 + len(s) if s else None, "z": z, "z_source": ["WITNESS"] * len(z),
                                     "static": {"unary": [None] * 5, "pair": {f"{a}|{b}": None for i, a in enumerate(IDS) for b in IDS[i + 1:]}}}})
    edits = [{"kind": q["kind"], "poses": {IDS.index(o): xy(c) for o, c in q["edit"].items()}, "eligible": True,
              "privileged": {"query": f"scene:k{seed}:{z4.sig(sorted(q['edit'].items()))}", "y": y, "source": "WITNESS"}}
             for q, y in zip(cat, scene[1:])]
    return {"inputs": inputs, "candidates": cands, "edits": edits, "audit": {"root": f"k{seed}", "split": "train", "source": "SYN", "ids": IDS}}


@pytest.fixture(scope="module")
def roots():
    return t7.prepare({"roots": [fixture(0)]})


def test_exact_joint_512_states_and_root_consistent_scene_block(roots):
    torch.manual_seed(0)
    r = roots[0]
    for name in ("B", "C", "B-quadratic", "B-structured", "B-no-coupling"):
        m = a7.build(name)
        outs = t7.forward(m, r)
        main = next(o for c, o in zip(r["cands"], outs) if len(c["seq"]) == 4)
        assert len(main["Z"]) == 512 and math.isclose(float(torch.exp(main["logP"]).sum()), 1.0, abs_tol=1e-12)
        sm = [o["scene_marg"] for o in outs]
        for k in sm[0]:                                   # identical root-level scene beliefs for every repair
            assert max(float(x[k]) for x in sm) - min(float(x[k]) for x in sm) < 1e-12
        assert all(o["J"].shape == () and o["E"].shape == () for o in outs)


def test_methodology_joint_pool_equals_brute_force(roots):
    """L_joint over all (v, z) of the fully decided pool == ranking CE + (-log P(z* | r)) (decomposition used)."""
    torch.manual_seed(1)
    r, m = roots[0], a7.build("B")
    outs = t7.forward(m, r)
    full = [(c, o) for c, o in zip(r["cands"], outs) if all(z is not None for z in c["z"])]
    E = [(o["E"] - a7.T * o["logP"]) for _, o in full]           # E(v, z) for every z of every v
    lse = torch.logsumexp(torch.cat([-e / a7.T for e in E]), 0)
    rank = torch.log_softmax(torch.stack([-o["E"] / a7.T for _, o in full]), 0)
    for i, (c, o) in enumerate(full):
        idx = int("".join(str(int(c["z"][c["slots"].index(n)])) for n in o["order"]), 2)
        brute = -(-E[i][idx] / a7.T - lse)
        assert math.isclose(float(brute), float(-rank[i] - o["logP"][idx]), rel_tol=0, abs_tol=1e-10)
        assert math.isclose(float(-a7.T * torch.logsumexp(-E[i] / a7.T, 0)), float(o["E"]), abs_tol=1e-10)   # Ebar_R(r)


def test_ablation_switches_remove_exactly_what_they_name(roots):
    r = roots[0]
    has = lambda m, n: hasattr(m, n)  # noqa: E731
    full, quad, struct, none = (a7.build(n) for n in ("B", "B-quadratic", "B-structured", "B-no-coupling"))
    assert has(full, "ho_q") and has(full, "cpl") and has(full, "pair_omit")
    assert not has(quad, "ho_q") and has(quad, "cpl") and has(quad, "pair_scene")
    assert not has(struct, "cpl") and not has(struct, "ho_q") and has(struct, "pair_omit")
    assert not any(has(none, n) for n in ("cpl", "ho_q", "ho_s", "pair_scene", "pair_omit"))
    outs = t7.forward(none, r)
    for c, o in zip(r["cands"], outs):                            # independent fields: joint = product of marginals
        p = torch.exp(o["logP"])
        mz = torch.stack([o["marg"][c["slots"].index(n)] for n in o["order"]])
        prod = torch.prod(torch.where(o["Z"] > 0.5, mz, 1 - mz), 1)
        assert float((p - prod).abs().max()) < 1e-12
    b, c_ = a7.build("B"), a7.build("C")
    assert has(b, "pairo") and not has(b, "gru") and has(c_, "gru") and not has(c_, "pairo")   # no double order factor
    L = t7.losses(full, r)
    L["pool"].backward()
    assert sum(float(p.grad.norm()) for p in full.pair_omit.parameters()) > 0
    assert sum(float(p.grad.norm()) for p in full.ho_q.parameters()) > 0


def test_edit_evidence_is_distinct_and_permutation_invariant(roots):
    torch.manual_seed(2)
    r, m = roots[0], a7.build("B")
    R = r["R"]
    v = {k: m.scene_vec(R, m.edited(R, p)) for k, p in [("none", {})] + sorted(r["edits"].items())}
    base = v["none"].norm()
    for a, b in itertools.combinations(v, 2):
        assert float((v[a] - v[b]).norm() / base) > 0.05                      # P6 audit: 0.0004-0.0023
    rec = fixture(0)
    perm = [3, 1, 0, 2, 4]
    rp = {**rec, "inputs": {k: (v_[perm] if k in ("object_xy", "object_radius", "is_active_target", "is_obstacle", "visual") else v_)
                            for k, v_ in rec["inputs"].items()}}
    R2 = t7.prepare({"roots": [rp]})[0]["R"]
    inv = {o: perm.index(o) for o in range(5)}
    for k, p in r["edits"].items():
        a = m.scene_vec(R, m.edited(R, p))
        b = m.scene_vec(R2, m.edited(R2, {inv[i]: q for i, q in p.items()}))
        assert float((a - b).abs().max()) < 1e-10


@pytest.mark.parametrize("name", ["B", "C", "B-no-coupling", "A"])
def test_tiny_overfit_kappa_plus_zero_minus(name):
    """Three independent roots with kappa = +1, 0, -1: predicted root-level scene marginals fit the labels."""
    torch.manual_seed(0)
    pats = {+1: (0, 0, 0, 1), 0: (0, 1, 0, 1), -1: (0, 1, 1, 1)}
    roots = t7.prepare({"roots": [fixture(10 + i, p) for i, p in enumerate(pats.values())]})
    m = a7.build(name)
    t7.train(m, roots, 150, 300.0, lambda *a: None, lam={"pool": 0.5}, lr=3e-3, clip=5.0)
    with torch.no_grad():
        for (kappa, pat), r in zip(pats.items(), roots):
            sp = t7.scene_probs(m, r, t7.forward(m, r))
            p = [float(sp[k]) for k in ("z0", "zS[A]", "zS[B]", "zS[A+B]")]
            assert max(abs(a - b) for a, b in zip(p, pat)) < 0.25, (kappa, p)
            kh = p[3] - p[1] - p[2] + p[0]
            assert np.sign(round(kh)) == kappa, (kappa, kh)


def test_order_sensitivity_and_finite_difference_gradient(roots):
    torch.manual_seed(3)
    r = roots[0]
    for name in ("B", "C"):
        m = a7.build(name)
        ab = next(c for c in r["cands"] if [i for i, _ in c["seq"]] == [0, 1])
        ba = next(c for c in r["cands"] if [i for i, _ in c["seq"]] == [1, 0])
        s1 = m.order(r["R"], ab["seq"])[0]
        s2 = m.order(r["R"], ba["seq"])[0]
        assert abs(float(s1 - s2)) > 1e-6
    m = a7.build("B")
    p = m.cpl[0].bias
    loss = lambda: t7.total(m, roots)[0]  # noqa: E731
    loss().backward()
    g = float(p.grad[0])
    with torch.no_grad():
        p[0] += 1e-6
        up = float(loss())
        p[0] -= 2e-6
        dn = float(loss())
        p[0] += 1e-6
    assert abs((up - dn) / 2e-6 - g) < 1e-5 * max(1.0, abs(g))
