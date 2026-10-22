"""P9-L3a-1: unique-factor root model (unique_factor.py) vs brute force, ABC7 and the P9 PoE. Saved data only; no teacher."""
import copy
import itertools
import math

import pytest
import torch

import abc7_models as a7
import abc8
import joint_likelihood as jl
import p9_l3
import unique_factor as uf

D = torch.float64


def _S(ks=2, seed=0):
    g = torch.Generator().manual_seed(seed)
    Z = uf._states(ks)
    E = -(Z @ torch.randn(ks, generator=g, dtype=D)) - 0.7 * Z[:, 0] * Z[:, -1]
    return {"names": [f"s{i}" for i in range(ks)], "queries": ["seq:t:empty"] + [f"scene:t:{i}" for i in range(1, ks)],
            "logp": -E - torch.logsumexp(-E, 0), "Z": Z}


def toy(blocks, ks=2, seed=0, scale=1.0, grad=False):
    """Toy unique-factor instance: random unaries and random raw block energy tables (pairs + higher order are arbitrary)."""
    g = torch.Generator().manual_seed(seed)
    qs = sorted({q for b in blocks for q in b} - {"seq:t:empty"})
    unary = {q: (scale * torch.randn((), generator=g, dtype=D)).requires_grad_(grad) for q in qs}
    bl = {f"b{i}": {"queries": b, "energy": (scale * torch.randn(2 ** ks, 2 ** len(b), generator=g, dtype=D)).requires_grad_(grad)}
          for i, b in enumerate(blocks)}
    return {"S": _S(ks, seed), "unary": unary, "blocks": bl, "seq": {}}


ALIAS = [["seq:t:ab", "seq:t:b", "seq:t:a"], ["seq:t:b"], ["seq:t:cb", "seq:t:b", "seq:t:c"]]
LAB = {"seq:t:empty": 0, "scene:t:1": 1, "seq:t:ab": 1, "seq:t:b": None, "seq:t:a": 0, "seq:t:c": None, "seq:t:cb": 1}


@pytest.mark.parametrize("blocks", [[["seq:t:a"], ["seq:t:b", "seq:t:c"]], ALIAS, [["seq:t:empty", "seq:t:a"]]],
                         ids=["no_alias", "zR_and_zO_aliases", "explicit_zR_empty_tied_to_z0"])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_evidence_matches_brute_force(blocks, seed):
    inst = toy(blocks, seed=seed)
    for lab in (LAB, {q: None for q in LAB}, {"seq:t:b": 1}):
        assert abs(float(uf.log_evidence(inst, lab)[0]) - uf.brute_force(inst, lab)) < 1e-10
    assert abs(float(uf.log_evidence(inst, {})[0])) < 1e-12                       # all missing: log P = 0


def test_scene_prior_and_marginals_match_brute_force():
    inst = toy(ALIAS, seed=3)
    m = uf.prior_marginals(inst)
    for i, q in enumerate(inst["S"]["queries"]):
        assert abs(m[q] - float(torch.exp(inst["S"]["logp"]) @ inst["S"]["Z"][:, i])) < 1e-12
    for q in uf.variables(inst):
        assert abs(m[q] - math.exp(uf.brute_force(inst, {q: 1}))) < 1e-10
    assert abs(uf.conditional_marginal(inst, "seq:t:b", LAB) - math.exp(uf.brute_force(inst, LAB | {"seq:t:b": 1}) - uf.brute_force(inst, LAB))) < 1e-10


@pytest.mark.parametrize("T,scale", [(0.25, 1.0), (4.0, 1.0), (1.0, 1e3)])
def test_extreme_energy_and_temperature(T, scale):
    inst = toy(ALIAS, seed=4, scale=scale)
    ll = uf.log_evidence(inst, LAB, temp=T)[0]
    assert torch.isfinite(ll)
    if scale == 1.0:
        assert abs(float(ll) - uf.brute_force(inst, LAB, temp=T)) < 1e-9


def test_toy_gradients_match_finite_differences():
    inst = toy(ALIAS, seed=5, grad=True)
    f = lambda: -uf.log_evidence(inst, LAB)[0]  # noqa: E731
    f().backward()
    for t in list(inst["unary"].values())[:3] + [b["energy"] for b in inst["blocks"].values()]:
        g = t.grad.clone()
        for idx in list(itertools.product(*[range(n) for n in t.shape]))[:4]:
            with torch.no_grad():
                t[idx] += 1e-6
                fp = float(f())
                t[idx] -= 2e-6
                fm = float(f())
                t[idx] += 1e-6
            assert abs((fp - fm) / 2e-6 - float(g[idx])) < 1e-6


def test_duplicated_expert_counterexample_0p8():
    """A Bernoulli expert P(x=1) = 0.8 duplicated: PoE renormalizes to 0.8^2 / (0.8^2 + 0.2^2) = 0.941...; unique factor stays 0.8."""
    S = _S(1, 0)
    lq = torch.log(torch.tensor([[0.2, 0.8]], dtype=D))
    one = {"logq": lq, "queries": ["seq:t:a"]}
    assert abs(jl.marginals(S, [one])["seq:t:a"] - 0.8) < 1e-12
    assert abs(jl.marginals(S, [one, dict(one)])["seq:t:a"] - 0.64 / 0.68) < 1e-12
    inst = {"S": S, "unary": {"seq:t:a": torch.tensor(math.log(4.0), dtype=D)}, "blocks": {}, "seq": {}}
    assert abs(uf.prior_marginals(inst)["seq:t:a"] - 0.8) < 1e-12


# ------------------------------------------------------------------ saved P8c roots with P9-L2 checkpoints
@pytest.fixture(scope="module")
def real():
    train, val, test = p9_l3.data()
    rich = [r for r in val if len(r["cands"]) > 1]
    rich += [r for r in train if len(r["cands"]) > 1][:20]
    ms = {a: p9_l3.load(a, f"runs/p9/l2/ckpt/ckpt_{a}#s0.pt") for a in ("B-full", "B-structured")}
    return {"roots": rich, "m": ms}


def _sub(r, cands):
    return r | {"cands": [c for c in r["cands"] if not c["seq"]] + cands}


@pytest.mark.parametrize("arm", ["B-full", "B-structured"])
def test_one_repair_catalogue_equals_abc7_joint_and_poe(real, arm):
    m = real["m"][arm]
    for r in real["roots"][:6]:
        for c in [c for c in r["cands"] if c["seq"]][:4]:
            rr = _sub(r, [c])
            with torch.no_grad():
                o = a7.ModelBC7.joint(m, rr["R"], c["seq"], c["slots"], rr["edits"])
                pu = uf.prior_marginals(uf.instances(m, rr))
                S, blocks, lab, _ = jl.tables(m, rr)
            for n, q, p in zip(o["slots"], c["z_q"], o["marg"].tolist()):
                assert abs(pu[q] - p) < 1e-10
            assert abs(float(uf.log_evidence(uf.instances(m, rr), lab)[0]) - float(jl.log_evidence(S, blocks, lab)[0])) < 1e-10


@pytest.mark.parametrize("arm", ["B-full", "B-structured"])
def test_unshared_catalogue_equals_poe_and_brute_force(real, arm):
    m = real["m"][arm]
    for r in real["roots"][:8]:
        used, keep = set(), []
        for c in [c for c in r["cands"] if c["seq"]]:
            qs = {q for s, q in zip(c["slots"], c["z_q"]) if s[:2] in ("zR", "zO")}
            if not qs & used:
                keep.append(c)
                used |= qs
        rr = _sub(r, keep)
        with torch.no_grad():
            inst = uf.instances(m, rr)
            S, blocks, lab, _ = jl.tables(m, rr)
            assert abs(float(uf.log_evidence(inst, lab)[0]) - float(jl.log_evidence(S, blocks, lab)[0])) < 1e-10
            pu, pp = uf.prior_marginals(inst), jl.marginals(S, blocks)
        assert max(abs(pu[q] - pp[q]) for q in pp) < 1e-10


def test_real_roots_brute_force(real):
    m, n = real["m"]["B-full"], 0
    for r in real["roots"]:
        with torch.no_grad():
            inst = uf.instances(m, r)
        if len(uf.variables(inst)) <= 10:
            lab = jl.labels(r)
            assert abs(float(uf.log_evidence(inst, lab)[0]) - uf.brute_force(inst, lab)) < 1e-9
            n += 1
    assert n >= 5


@pytest.mark.parametrize("arm", ["B-full", "B-structured"])
def test_unique_model_invariances(real, arm):
    m = real["m"][arm]
    fn = lambda m_, r_: uf.prior_marginals(uf.instances(m_, r_))  # noqa: E731
    rows = p9_l3.sensitivity(m, real["roots"][:12], fn)
    for x in rows:
        assert x["max_abs_change_scene_prior"] < 1e-12
        if x["expected"] == "EXPECTED_INVARIANT":
            assert x["max_abs_change_repair_marginals"] < 1e-10, x
    assert any(x["case"] == "exact_duplicate" for x in rows)
    if arm == "B-structured":
        assert any(x["case"] == "alias_as_new_candidate" for x in rows)


def test_gradients_scopes_and_auxiliaries(real):
    m, r = real["m"]["B-full"], copy.deepcopy(real["roots"][0])

    def nll():
        return -uf.log_evidence(uf.instances(m, r), jl.labels(r))[0]
    for mod in ("scene", "pair_scene", "pair_omit", "cpl", "ho_s", "ho_q", "order_s", "mix"):
        ps = list(getattr(m, mod).parameters())
        g = torch.Generator().manual_seed(1)
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
    for mod in (m.unary, m.pairh, m.cost):                               # F1 and J get no outcome-likelihood gradient
        assert all(p.grad is None or float(p.grad.abs().max()) == 0 for p in mod.parameters())
    assert float(m.order_s[0].weight.grad.abs().sum()) > 0 and float(m.cpl[0].weight.grad.abs().sum()) > 0
    m.zero_grad()
    L = uf.losses(m, r)
    (L["static"] + (L["travel"] if L["travel"] is not None else 0)).backward()
    assert float(m.pairh[0].weight.grad.abs().sum()) > 0 and m.scene[0].weight.grad is None
    m.zero_grad()


def test_order_swap_identity_and_unary(real):
    m = real["m"]["B-full"]
    r = next(r for r in real["roots"] if any(len(c["seq"]) >= 2 for c in r["cands"]))
    c = next(c for c in r["cands"] if len(c["seq"]) >= 2)
    rev = p9_l3.synth(r, list(reversed(c["seq"])), c)
    rr = _sub(r, [c, rev])
    with torch.no_grad():
        inst = uf.instances(m, rr)
    assert c["query"] != rev["query"] and abs(float(inst["unary"][c["query"]]) - float(inst["unary"][rev["query"]])) > 1e-9


def test_determinism_label_isolation_and_fail_closed(real, monkeypatch):
    m, r = real["m"]["B-full"], real["roots"][1]
    a = uf.prior_marginals(uf.instances(m, r))
    s = copy.deepcopy(r)
    s["y"] = {q: None for q in s["y"]}
    for c in s["cands"]:
        c |= {"y": None, "z": [None] * len(c["z"]), "cost": None}
    assert a == uf.prior_marginals(uf.instances(m, r)) == uf.prior_marginals(uf.instances(m, s))
    monkeypatch.setattr(jl, "MAX_SCOPE", 0)
    with pytest.raises(jl.CombinatoricsError):
        uf.log_evidence(uf.instances(m, r), jl.labels(r))


def test_c_full_one_repair_equivalence(real):
    torch.manual_seed(0)
    m = abc8.build("C-full")
    r = real["roots"][0]
    c = next(c for c in r["cands"] if len(c["seq"]) >= 2)
    rr = _sub(r, [c])
    with torch.no_grad():
        o = a7.ModelBC7.joint(m, rr["R"], c["seq"], c["slots"], rr["edits"])
        pu = uf.prior_marginals(uf.instances(m, rr))
    assert max(abs(pu[q] - p) for q, p in zip(c["z_q"], o["marg"].tolist())) < 1e-10
