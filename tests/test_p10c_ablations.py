"""P10c ablation hooks on ModelBC7: defaults unchanged, F2 order-invariance, F3 / F4 pair removal, exact inference still runs."""
import torch

import abc7_models as a7
import abc8
import p9_l3 as l3
import unique_factor as uf
import unique_factor_keyed as ufk


def _root():
    tr, va, te = l3.data()
    return next(r for r in va if any(len(c["seq"]) >= 2 for c in r["cands"]))


def test_default_build_unchanged():
    torch.manual_seed(0)
    m0 = abc8.build("B-full")
    torch.manual_seed(0)
    m1 = a7.ModelBC7("B", "full").double()
    assert list(m0.state_dict()) == list(m1.state_dict())
    assert all(torch.equal(m0.state_dict()[k], m1.state_dict()[k]) for k in m0.state_dict())


def test_f2_order_invariant_summary():
    torch.manual_seed(1)
    m, r = a7.ModelBC7("B", "full", order="none").double(), _root()
    seq = next(c["seq"] for c in r["cands"] if len(c["seq"]) >= 2)
    s1, g1, _ = m._order(r["R"], seq)
    s2, g2, _ = m._order(r["R"], list(reversed(seq)))
    assert torch.allclose(g1, g2) and torch.allclose(s1, s2)
    torch.manual_seed(1)
    mb = a7.ModelBC7("B", "full").double()
    a, _, _ = mb._order(r["R"], seq)
    b, _, _ = mb._order(r["R"], list(reversed(seq)))
    assert not torch.allclose(a, b)                    # the parent B IS order-sensitive


def test_f3_f4_pair_removal_and_exact_inference():
    r = _root()
    for drop in (("pair_omit",), ("pair_scene",)):
        m = a7.ModelBC7("B", "full", drop=drop).double()
        assert not hasattr(m, drop[0])
        with ufk.installed():
            pm = uf.prior_marginals(uf.instances(m, r))
        assert all(0.0 <= float(p) <= 1.0 for p in pm.values())
