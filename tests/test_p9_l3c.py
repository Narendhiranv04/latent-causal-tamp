"""P9-L3c/L3d: identity fail-closed, per-family decomposition, deployed selector, keyed instantiation, visual-zero control.
Saved data and existing checkpoints only; no teacher, IK or planner."""
import copy
import math

import pytest
import torch

import abc7_models as a7
import abc8
import joint_likelihood as jl
import p9_l3 as l3
import p9_l3c as l3c
import p9_l3d as l3d
import unique_factor as uf
import unique_factor_keyed as ufk

D = torch.float64


@pytest.fixture(scope="module")
def S():
    calls = l3c.instrument()
    train, val, test = l3.data()
    roots = [r for r in val if len(r["cands"]) > 1] + [r for r in train if len(r["cands"]) > 1][:12]
    ms = {a: l3c._arm(a) for a in ("B-full", "B-structured", "C-full")}
    return {"roots": roots, "val": val, "m": ms, "calls": calls}


def _sub(r, cands):
    return r | {"cands": [c for c in r["cands"] if not c["seq"]] + cands}


def test_conflicting_id_fails_closed_and_unguarded_dedup_is_silent(S):
    r = S["roots"][0]
    x = l3c.conflicting_id(r)
    assert x["wrapper"].startswith("FAIL_CLOSED")
    rr = copy.deepcopy(r)
    c = copy.deepcopy(next(c for c in rr["cands"] if c["seq"]))
    c["seq"][0] = (c["seq"][0][0], tuple(float(v) + 0.08 for v in c["seq"][0][1]))
    rr["cands"].append(c)
    with pytest.raises(jl.IdentityError):
        l3c.checked()(S["m"]["B-full"][0], rr)
    with pytest.raises(jl.IdentityError):
        ufk.instances(S["m"]["B-full"][0], rr)
    assert len(uf.instances(S["m"]["B-full"][0], rr)["blocks"]) == len({c["query"] for c in r["cands"] if c["seq"]})


@pytest.mark.parametrize("arm", ["B-full", "C-full"])
def test_components_sum_to_unique_block(S, arm):
    m = S["m"][arm][0]
    for r in S["roots"][:4]:
        inst = uf.instances(m, r)
        for c in [c for c in r["cands"] if c["seq"]][:4]:
            comp = l3c.components(m, r, c)
            assert torch.allclose(sum(comp.values()), inst["blocks"][c["query"]]["energy"], atol=1e-10)


def test_deployed_selector_matches_lexicographic_rule(S):
    m, tau, thr = S["m"]["B-full"]
    for r in S["val"]:
        ch, rows = l3c.deployed(m, r, uf.instances(m, r), tau, thr)
        keep = sorted((x for x in rows if 1 / (1 + math.exp(-x["u"] / tau)) >= thr), key=lambda x: (x["m"], x["J_pred"], x["C_d"], x["energy"], x["query"]))
        assert ch == (keep[0]["query"] if keep else None)


@pytest.mark.parametrize("arm", ["B-full", "B-structured", "C-full"])
def test_keyed_exact_normalized_and_scene_consistent(S, arm):
    m, n = S["m"][arm][0], 0
    for r in S["roots"]:
        with torch.no_grad():
            inst = ufk.instances(m, r)
            pm = uf.prior_marginals(inst)
        for i, q in enumerate(inst["S"]["queries"]):
            assert abs(pm[q] - float(torch.exp(inst["S"]["logp"]) @ inst["S"]["Z"][:, i])) < 1e-12
        assert abs(float(uf.log_evidence(inst, {})[0])) < 1e-12
        if len(uf.variables(inst)) <= 9:
            lab = jl.labels(r)
            assert abs(float(uf.log_evidence(inst, lab)[0]) - uf.brute_force(inst, lab)) < 1e-9
            n += 1
    assert n >= 3


@pytest.mark.parametrize("arm", ["B-full", "C-full"])
def test_keyed_vs_abc7_single_candidate(S, arm):
    m = S["m"][arm][0]
    one, multi = 0, 0
    for r in S["roots"][:8]:
        for c in [c for c in r["cands"] if c["seq"]][:5]:
            rr = _sub(r, [c])
            with torch.no_grad():
                o = a7.ModelBC7.joint(m, rr["R"], c["seq"], c["slots"], rr["edits"])
                pk = uf.prior_marginals(ufk.instances(m, rr))
            d = max(abs(pk[q] - p) for q, p in zip(c["z_q"], o["marg"].tolist()))
            if len(c["seq"]) == 1:
                assert d < 1e-10                                   # identical factor set for a one-move candidate
                one += 1
            else:
                multi += d > 1e-6                                  # documented: scene-omission pairs keyed by the omission itself
    assert one >= 3 and multi >= 1


@pytest.mark.parametrize("arm", ["B-full", "B-structured", "C-full"])
def test_keyed_invariant_whenever_modelled_outcomes_unchanged(S, arm):
    m, checked = S["m"][arm][0], 0
    for r in S["roots"]:
        with torch.no_grad():
            base = ufk.instances(m, r)
            pb = uf.prior_marginals(base)
            cs, _ = l3.cases(r, True)
            for name, (_, rr) in cs.items():
                if name in ("renamed_ids", "related_candidate"):
                    continue
                inst = ufk.instances(m, rr)
                if set(uf.variables(inst)) == set(uf.variables(base)):          # the same physical outcomes are modelled
                    pn = uf.prior_marginals(inst)
                    assert max(abs(pn[q] - pb[q]) for q in pb) < 1e-10, (r["key"], name)
                    checked += name == "alias_as_new_candidate"
    assert checked >= 2


def test_keyed_genuinely_new_relation_changes_beliefs(S):
    m = S["m"]["B-full"][0]
    ch = []
    for r in S["roots"]:
        cs, _ = l3.cases(r, True)
        if "related_candidate" in cs:
            with torch.no_grad():
                pb, pn = (uf.prior_marginals(ufk.instances(m, x)) for x in (r, cs["related_candidate"][1]))
            ch.append(max(abs(pn[q] - pb[q]) for q in pb))
    assert ch and max(ch) > 1e-3


def test_keyed_gradients_and_zero_outcome_gradient_to_static_and_travel(S):
    m, r = S["m"]["B-full"][0], S["roots"][0]

    def nll():
        return -uf.log_evidence(ufk.instances(m, r), jl.labels(r))[0]
    for mod in ("scene", "pair_scene", "pair_omit", "cpl", "ho_s", "ho_q", "order_s", "mix"):
        ps = list(getattr(m, mod).parameters())
        g = torch.Generator().manual_seed(2)
        d = [torch.randn(p.shape, generator=g, dtype=D) for p in ps]
        m.zero_grad()
        nll().backward()
        ad = sum(float((p.grad * v).sum()) for p, v in zip(ps, d) if p.grad is not None)
        with torch.no_grad():
            for p, v in zip(ps, d):
                p += 1e-6 * v
            fp = float(nll())
            for p, v in zip(ps, d):
                p -= 2e-6 * v
            fm = float(nll())
            for p, v in zip(ps, d):
                p += 1e-6 * v
        assert abs((fp - fm) / 2e-6 - ad) < 1e-5 * max(1.0, abs(ad)), mod
    m.zero_grad()
    nll().backward()
    for mod in (m.unary, m.pairh, m.cost):
        assert all(p.grad is None or float(p.grad.abs().max()) == 0 for p in mod.parameters())
    m.zero_grad()
    with ufk.installed():
        L = uf.losses(m, r)
    L["static"].backward()
    assert float(m.pairh[0].weight.grad.abs().sum()) > 0
    m.zero_grad()


def test_keyed_adds_no_parameters_and_keeps_higher_order(S):
    m, r = S["m"]["B-full"][0], S["roots"][1]
    assert sum(p.numel() for p in m.parameters()) == 698154
    with torch.no_grad():
        base = float(uf.log_evidence(ufk.instances(m, r), jl.labels(r))[0])
        w = list(m.ho_q.parameters())[-2]
        w += 0.05
        moved = float(uf.log_evidence(ufk.instances(m, r), jl.labels(r))[0])
        w -= 0.05
    assert abs(moved - base) > 1e-6


def test_visual_zero_control_same_architecture_zero_weight_gradient(S):
    torch.manual_seed(0)
    a = abc8.build("B-full")
    torch.manual_seed(0)
    b = abc8.build("B-full")
    assert sum(p.numel() for p in a.parameters()) == sum(p.numel() for p in b.parameters())
    assert all(torch.equal(x, y) for x, y in zip(a.state_dict().values(), b.state_dict().values()))
    r = l3d.mask_visual([copy.deepcopy(S["roots"][0])])[0]
    assert float(r["R"].vis.abs().sum()) == 0 and float(S["roots"][0]["R"].vis.abs().sum()) > 0
    uf.losses(b, r)["nll"].backward()
    assert float(b.vproj.weight.grad.abs().max()) == 0 and float(b.vproj.bias.grad.abs().max()) > 0


def test_determinism_no_physical_calls_and_fail_closed(S, monkeypatch):
    m, r = S["m"]["C-full"][0], S["roots"][2]
    assert uf.prior_marginals(ufk.instances(m, r)) == uf.prior_marginals(ufk.instances(m, r))
    assert sum(S["calls"].values()) == 0
    monkeypatch.setattr(jl, "MAX_SCOPE", 0)
    with pytest.raises(jl.CombinatoricsError):
        uf.log_evidence(ufk.instances(m, r), jl.labels(r))
