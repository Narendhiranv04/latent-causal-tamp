"""P8a critical tests: factor scopes, exact conditioning, gradient reachability, matched inputs / masks (no teacher)."""
import copy
import math
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import abc7_train as t7  # noqa: E402
import abc8  # noqa: E402
import p8_eval as pe  # noqa: E402
import test_p7_models as fx  # noqa: E402


def _root(seed=0, scene=(0, 0, 0, 1)):
    return t7.prepare({"roots": [fx.fixture(seed, scene)]})[0]


def _copy_direct(src, dst):
    """Copy every shared (direct / non-coupling) parameter so two modes differ only in their cross terms."""
    sd = src.state_dict()
    dst.load_state_dict({k: v for k, v in sd.items() if k in dst.state_dict()}, strict=False)


def test_identical_direct_logits_cross_terms_move_exactly_what_they_can():
    r = _root()
    torch.manual_seed(0)
    full, struct, none = abc8.build("B-full"), abc8.build("B-structured"), abc8.build("B-none")
    _copy_direct(full, struct)
    _copy_direct(full, none)
    o = {n: t7.forward(m, r) for n, m in (("full", full), ("struct", struct), ("none", none))}
    i = next(k for k, c in enumerate(r["cands"]) if len(c["seq"]) == 4)
    pf, ps, pn = (torch.exp(o[n][i]["logP_S"]) for n in ("full", "struct", "none"))
    assert float((pf - pn).abs().max()) > 1e-4 and float((ps - pn).abs().max()) > 1e-4      # cross terms change scene beliefs
    zn = o["none"][i]
    margs = torch.stack([zn["marg"][zn["slots"].index(n)] for n in zn["order"]])
    prod = torch.prod(torch.where(zn["Z"] > 0.5, margs, 1 - margs), 1)
    assert float((torch.exp(zn["logP"]) - prod).abs().max()) < 1e-12              # none: product of marginals
    with torch.no_grad():                                                          # repair-side terms never move P_S
        for p in full.pair_omit.parameters():
            p.add_(1.0)
        for p in full.ho_q.parameters():
            p.add_(1.0)
    pf2 = torch.exp(t7.forward(full, r)[i]["logP_S"])
    assert float((pf2 - pf).abs().max()) < 1e-12


def test_structured_omission_pair_changes_a_conditional_without_generic_coupling():
    r = _root()
    torch.manual_seed(1)
    m = abc8.build("B-structured")
    i = next(k for k, c in enumerate(r["cands"]) if len(c["seq"]) == 4)
    o = t7.forward(m, r)[i]
    before = pe._cond(o["logP"], o["Z"], o["order"], {"zR": 1}, ["zO[1]"])["zO[1]"]
    with torch.no_grad():
        for p in m.pair_omit.parameters():
            p.add_(0.7)
    o2 = t7.forward(m, r)[i]
    after = pe._cond(o2["logP"], o2["Z"], o2["order"], {"zR": 1}, ["zO[1]"])["zO[1]"]
    assert abs(after - before) > 1e-4 and not hasattr(m, "cpl")


def test_exact_enumeration_all_K_and_brute_force_conditioning():
    r = _root()
    torch.manual_seed(2)
    m = abc8.build("B-full")
    seen = set()
    for c, o in zip(r["cands"], t7.forward(m, r)):
        K = len(c["slots"])
        seen.add(K)
        assert len(o["Z"]) == 2 ** K and math.isclose(float(torch.exp(o["logP"]).sum()), 1.0, abs_tol=1e-12)
        if K == 9:
            rev = {"zR": 1, "zS[A]": 0}
            got = pe._cond(o["logP"], o["Z"], o["order"], rev, ["zO[2]"])["zO[2]"]
            p = torch.exp(o["logP"])
            keep = [j for j, z in enumerate(o["Z"]) if z[o["order"].index("zR")] == 1 and z[o["order"].index("zS[A]")] == 0]
            brute = sum(float(p[j]) * float(o["Z"][j, o["order"].index("zO[2]")]) for j in keep) / sum(float(p[j]) for j in keep)
            assert abs(got - brute) < 1e-12
    assert {4, 5, 7, 8, 9} <= seen


def test_omission_slots_unaliased_and_prefix_keeps_omitted_object():
    r = _root()
    for c in r["cands"]:
        qs = [q for s, q in zip(c["slots"], c["z_q"])]
        assert len(set(qs)) == len(qs)
    m = abc8.build("B-full")
    c = next(c for c in r["cands"] if len(c["seq"]) == 4)
    rest = [a for k, a in enumerate(c["seq"]) if k != 1]
    _, xy, _ = m.actions(r["R"], rest)
    assert torch.equal(xy[c["seq"][1][0]], r["R"].xy0[c["seq"][1][0]])           # omitted object stays at its initial pose


def test_gradient_reachability_per_named_factor_and_objective():
    r = _root()
    torch.manual_seed(3)
    expect = {"B-full": {"pool": ["pair_scene", "pair_omit", "cpl", "ho_s", "ho_q"], "scene": ["scene", "edit_proj", "pair_scene", "cpl", "ho_s"],
                         "omit": ["pair_omit", "order_s"]},
              "B-structured": {"pool": ["pair_scene", "pair_omit"], "scene": ["scene", "pair_scene"]},
              "B-none": {"scene": ["scene", "edit_proj"], "omit": ["order_s"]}, "SF": {"scene": ["head", "edit_proj"], "omit": ["head"]}}
    for arm, terms in expect.items():
        m = abc8.build(arm)
        for term, mods in terms.items():
            m.zero_grad()
            L = t7.losses(m, r)
            assert L[term] is not None, (arm, term)
            L[term].backward()
            for mod in mods:
                g = sum(float(p.grad.norm()) for p in getattr(m, mod).parameters() if p.grad is not None)
                assert g > 0, (arm, term, mod)
        if arm in ("B-none", "SF"):
            assert t7.losses(m, r)["pool"] is None or arm == "B-none"           # SF: no energy, no pool term


def test_factorized_arms_conditionals_equal_marginals_and_inputs_masks_identical():
    r = _root()
    torch.manual_seed(4)
    for arm in ("B-none", "SF"):
        m = abc8.build(arm)
        rows = pe.conditional(m, r)
        sp = t7.scene_probs(m, r, t7.forward(m, r))
        for x in rows:
            if x["task"] in ("a", "b"):
                assert abs(x["p"] - float(sp[x["hidden"]])) < 1e-10
    roots = [_root(s) for s in range(3)]
    a, b = copy.deepcopy(roots), copy.deepcopy(roots)
    abc8.sparse_aux(a)
    abc8.sparse_aux(b)
    for x, y in zip(a, b):                                                        # hash masks identical for every arm
        assert x["scene_y"] == y["scene_y"] and [c["z"] for c in x["cands"]] == [c["z"] for c in y["cands"]]
        assert all(c["y"] is not None for c in x["cands"])                        # task labels never hidden
    s1, s2 = abc8.RootSampler(roots * 5, 4, 7), abc8.RootSampler(roots * 5, 4, 7)
    assert all(s1.next() == s2.next() for _ in range(10))


def test_kappa_capacity_and_held_out_compositional_fixture_runs_finite():
    """Capacity: three roots kappa +1 / 0 / -1. Held-out: a rule (o00 at small x => complementary, else redundant) on
    four training roots, evaluated on two new roots. Reported, not asserted as science."""
    pats = {1: (0, 0, 0, 1), 0: (0, 1, 0, 1), -1: (0, 1, 1, 1)}
    roots = t7.prepare({"roots": [fx.fixture(20 + i, p) for i, p in enumerate(pats.values())]})
    m = abc8.build("B-full")
    t7.train(m, roots, 80, 300.0, lambda *a: None, lam={"pool": 0.5}, lr=3e-3, clip=5.0)
    with torch.no_grad():
        for (k, pat), r in zip(pats.items(), roots):
            sp = t7.scene_probs(m, r, t7.forward(m, r))
            kh = float(sp["zS[A+B]"] - sp["zS[A]"] - sp["zS[B]"] + sp["z0"])
            assert np.sign(round(kh)) == k
    rule = lambda rec: pats[1] if rec["inputs"]["object_xy"][0, 0] < 0.33 else pats[-1]  # noqa: E731
    recs = [fx.fixture(40 + i) for i in range(6)]
    recs = [fx.fixture(40 + i, rule(x)) for i, x in enumerate(recs)]
    rs = t7.prepare({"roots": recs})
    m = abc8.build("B-full")
    t7.train(m, rs[:4], 60, 300.0, lambda *a: None, lam={"pool": 0.5}, lr=3e-3, clip=5.0)
    out = pe.unconditional([__import__("p7_eval").evaluate(m, r) for r in rs[4:]])
    assert out["scene_nll"] is not None and np.isfinite(out["scene_nll"])
