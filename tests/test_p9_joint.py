"""P9-L1: exact equality-aware root likelihood (joint_likelihood.py) on toy factor tables and saved P8 structures. No teacher."""
import copy
import itertools
import math

import pytest
import torch

import abc7_train as t7
import abc8
import joint_likelihood as jl

D = torch.float64


def _states(k):
    return torch.tensor(list(itertools.product((0.0, 1.0), repeat=k)), dtype=D)


def toy_params(spec, ks=3, seed=0):
    """Learnable toy factors mirroring ABC7's energy form: scene unary / z0-zS pair / generic scene pair / scene HO; per block
    repair unary / zR-zO pair / generic repair pair / scene-repair coupling / repair HO."""
    g = torch.Generator().manual_seed(seed)
    r = lambda *s: torch.randn(*s, generator=g, dtype=D).requires_grad_()  # noqa: E731
    P = {"s": r(ks), "w_s0": r(ks), "w_gen": r(ks, ks), "ho_s": r(())}
    for i, qs in enumerate(spec):
        P |= {f"u{i}": r(len(qs)), f"w_o{i}": r(len(qs)), f"g{i}": r(len(qs), len(qs)), f"c{i}": r(ks, len(qs)), f"ho_q{i}": r(())}
    return P


def toy_tables(P, spec, ks=3, T=1.0, scale=1.0, const=None):
    Zs = _states(ks)
    gen = torch.triu(P["w_gen"], 1)
    E = -Zs @ P["s"] - Zs[:, 0] * (Zs[:, 1:] @ P["w_s0"][1:]) - ((Zs @ gen) * Zs).sum(1) - P["ho_s"] * Zs[:, 1:].prod(1)
    E = scale * E
    S = {"names": [f"s{k}" for k in range(ks)], "queries": ["seq:t:empty"] + [f"scene:t:{k}" for k in range(1, ks)],
         "logp": -E / T - torch.logsumexp(-E / T, 0), "Z": Zs}
    blocks = []
    for i, qs in enumerate(spec):
        Zq = _states(len(qs))
        gq = torch.triu(P[f"g{i}"], 1)
        Eq = (-(Zq @ P[f"u{i}"]) - Zq[:, 0] * (Zq[:, 1:] @ P[f"w_o{i}"][1:]) - ((Zq @ gq) * Zq).sum(1))[None] - Zs @ P[f"c{i}"] @ Zq.T
        Eq = scale * (Eq - P[f"ho_q{i}"] * Zs[:, -1:] * Zq.prod(1)[None])
        if const is not None:
            Eq = Eq + const[i]                                        # an r-only offset (static energy) on every z of block i
        blocks.append({"logq": -Eq / T - torch.logsumexp(-Eq / T, 1, keepdim=True), "queries": list(qs)})
    return S, blocks


NODUP = [["seq:t:a.b", "seq:t:b.x", "seq:t:a.x"], ["seq:t:c"]]
ALIAS = [["seq:t:a.b", "seq:t:b", "seq:t:a"], ["seq:t:b"], ["seq:t:c.b", "seq:t:b", "seq:t:c"], ["seq:t:a"]]
LAB = {"seq:t:empty": 0, "scene:t:1": 1, "scene:t:2": None, "seq:t:a.b": 1, "seq:t:b": 0, "seq:t:a": None, "seq:t:c": 1, "seq:t:c.b": None,
       "seq:t:b.x": 0, "seq:t:a.x": None}


def naive_product(S, blocks, lab):
    """The guide's rootwise formula WITHOUT equality (every copy an independent variable)."""
    lt = S["logp"].clone()
    for b in blocks:
        Zq = _states(len(b["queries"]))
        ok = torch.ones(len(Zq), dtype=torch.bool)
        for j, q in enumerate(b["queries"]):
            if lab.get(q) is not None:
                ok &= Zq[:, j] == lab[q]
        lt = lt + torch.logsumexp(b["logq"][:, ok], 1)
    keep = torch.ones(len(lt), dtype=torch.bool)
    for i, q in enumerate(S["queries"]):
        if lab.get(q) is not None:
            keep &= S["Z"][:, i] == lab[q]
    return torch.logsumexp(lt[keep], 0)


# ------------------------------------------------------------------ 1-3: normalization, scene invariance, exact evidence
@pytest.mark.parametrize("spec", [NODUP, ALIAS])
def test_normalization_and_scene_marginal(spec):
    S, blocks = toy_tables(toy_params(spec), spec)
    assert abs(float(torch.exp(S["logp"].detach()).sum()) - 1) < 1e-12
    for b in blocks:
        assert torch.allclose(torch.exp(b["logq"]).sum(1), torch.ones(len(S["logp"]), dtype=D), atol=1e-12)
        assert abs(float(torch.exp(S["logp"][:, None] + b["logq"]).sum()) - 1) < 1e-12
    m = jl.marginals(S, blocks)
    for i, q in enumerate(S["queries"]):                              # root model keeps P_S exactly
        assert abs(m[q] - float(torch.exp(S["logp"]) @ S["Z"][:, i])) < 1e-12


@pytest.mark.parametrize("spec", [NODUP, ALIAS])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_evidence_equals_brute_force(spec, seed):
    S, blocks = toy_tables(toy_params(spec, seed=seed), spec)
    ll, n, sh = jl.log_evidence(S, blocks, LAB)
    assert abs(float(ll) - jl.brute_force(S, blocks, LAB)) < 1e-10
    if spec is NODUP:                                                 # no reuse: exactly the guide's rootwise product
        assert sh == 0 and abs(float(ll) - float(naive_product(S, blocks, LAB))) < 1e-12
    else:                                                             # reuse: the naive product double-counts seq:t:b
        assert sh == 2 and abs(float(ll) - float(naive_product(S, blocks, LAB))) > 1e-3


def test_marginals_equal_brute_force_and_copies_agree():
    S, blocks = toy_tables(toy_params(ALIAS, seed=3), ALIAS)
    m = jl.marginals(S, blocks)
    for q in ("seq:t:b", "seq:t:a", "seq:t:a.b"):
        p1 = math.exp(jl.brute_force(S, blocks, {q: 1}))
        assert abs(m[q] - p1) < 1e-10
    assert abs(sum(math.exp(jl.brute_force(S, blocks, {"seq:t:b": y})) for y in (0, 1)) - 1) < 1e-12


def test_empty_repair_slot_tied_to_z0():
    spec = [["seq:t:empty"], ["seq:t:a"]]                             # an explicit zR[empty] slot must BE z0
    S, blocks = toy_tables(toy_params(spec, seed=4), spec)
    lab = {"seq:t:empty": 1, "seq:t:a": 0}
    assert abs(float(jl.log_evidence(S, blocks, lab)[0]) - jl.brute_force(S, blocks, lab)) < 1e-10
    m = jl.marginals(S, blocks)
    assert abs(m["seq:t:empty"] - float(torch.exp(S["logp"]) @ S["Z"][:, 0])) < 1e-12


def test_contradictory_copies_fail_closed():
    r = {"key": "t", "cands": [{"z_q": ["seq:t:b"], "z": [1]}, {"z_q": ["seq:t:a.b", "seq:t:b"], "z": [None, 0]}], "y": {}}
    with pytest.raises(jl.IdentityError):
        jl.labels(r)


# ------------------------------------------------------------------ 4: gradients (finite differences, signs)
def test_gradients_match_finite_differences_for_every_factor_group():
    P = toy_params(ALIAS, seed=5)

    def f():
        S, b = toy_tables(P, ALIAS)
        return -jl.log_evidence(S, b, LAB)[0]
    f().backward()
    groups = {"scene unary": "s", "z0-zS pair": "w_s0", "generic scene pair": "w_gen", "scene HO": "ho_s", "repair unary": "u0",
              "zR-zO pair": "w_o0", "generic repair pair": "g0", "scene-repair coupling": "c0", "repair HO": "ho_q0"}
    for name, k in groups.items():
        t, g = P[k], P[k].grad.clone()
        for idx in list(itertools.product(*[range(n) for n in t.shape]))[:6]:
            with torch.no_grad():
                t[idx] += 1e-6
                fp = float(f())
                t[idx] -= 2e-6
                fm = float(f())
                t[idx] += 1e-6
            assert abs((fp - fm) / 2e-6 - float(g[idx])) < 1e-6, (name, idx)
        assert float(g.abs().sum()) > 0, name


def test_gradient_signs_of_unaries():
    spec = [["seq:t:a"]]
    P = toy_params(spec, seed=6)
    for y, sign in ((1, -1), (0, 1)):
        for k in P.values():
            k.grad = None
        S, b = toy_tables(P, spec)
        (-jl.log_evidence(S, b, {"seq:t:a": y, "scene:t:1": y})[0]).backward()
        assert sign * float(P["u0"].grad[0]) > 0 and sign * float(P["s"].grad[1]) > 0


# ------------------------------------------------------------------ 5: static cancellation, rank energy
def test_r_only_offset_cancels_from_outcome_likelihood():
    c = torch.tensor([0.7, -3.0, 11.0, 0.2], dtype=D, requires_grad=True)
    P = toy_params(ALIAS, seed=7)
    S0, b0 = toy_tables(P, ALIAS)
    S1, b1 = toy_tables(P, ALIAS, const=c)
    ll = jl.log_evidence(S1, b1, LAB)[0]
    ll.backward()
    assert abs(float(ll) - float(jl.log_evidence(S0, b0, LAB)[0])) < 1e-12 and float(c.grad.abs().max()) < 1e-14
    assert all(torch.allclose(x["logq"], y["logq"], atol=1e-12) for x, y in zip(b0, b1))
    assert float(jl.rank_energy(torch.tensor(1.0, dtype=D), 0.5) - jl.rank_energy(torch.tensor(0.0, dtype=D), 0.5)) == 1.0


# ------------------------------------------------------------------ 6, 8: masks, extremes, padding, double counting
def test_all_missing_gives_zero_and_partial_masks_marginalize():
    S, blocks = toy_tables(toy_params(ALIAS, seed=8), ALIAS)
    ll, n, _ = jl.log_evidence(S, blocks, {q: None for q in LAB})
    assert n == 0 and abs(float(ll)) < 1e-12
    one = {"seq:t:b": 1}
    assert abs(float(jl.log_evidence(S, blocks, one)[0]) - math.log(jl.marginals(S, blocks)["seq:t:b"])) < 1e-12


@pytest.mark.parametrize("T,scale", [(0.25, 1.0), (4.0, 1.0), (1.0, 1e3)])
def test_extreme_energies_and_temperature(T, scale):
    S, blocks = toy_tables(toy_params(ALIAS, seed=9), ALIAS, T=T, scale=scale)
    ll = jl.log_evidence(S, blocks, LAB)[0]
    assert torch.isfinite(ll) and abs(float(torch.exp(S["logp"]).sum()) - 1) < 1e-12
    if scale == 1.0:
        assert abs(float(ll) - jl.brute_force(S, blocks, LAB)) < 1e-9


def test_uncoupled_extra_slot_changes_nothing_and_scene_counted_once():
    P = toy_params([["seq:t:a"]], seed=10)
    S, b = toy_tables(P, [["seq:t:a"]])
    pad = {"logq": (b[0]["logq"][:, :, None] + torch.full((1, 1, 2), math.log(0.5), dtype=D)).reshape(len(S["logp"]), 4), "queries": ["seq:t:a", "seq:t:pad"]}
    lab = {"seq:t:a": 1, "scene:t:1": 0}
    assert abs(float(jl.log_evidence(S, b, lab)[0]) - float(jl.log_evidence(S, [pad], lab)[0])) < 1e-12
    scene_only = {"seq:t:empty": 1, "scene:t:2": 0}
    ref = float(jl.log_evidence(S, [], scene_only)[0])
    for k in (1, 3, 6):                                               # k candidate blocks never re-charge scene evidence
        many = [{"logq": b[0]["logq"], "queries": [f"seq:t:r{i}"]} for i in range(k)]
        assert abs(float(jl.log_evidence(S, many, scene_only)[0]) - ref) < 1e-12


def test_combinatorics_fail_closed(monkeypatch):
    spec = [[f"seq:t:{i}", f"seq:t:{i + 1}"] for i in range(8)] + [[f"seq:t:{i}"] for i in range(9)]
    S, blocks = toy_tables(toy_params(spec, seed=11), spec)
    monkeypatch.setattr(jl, "MAX_SCOPE", 1)
    with pytest.raises(jl.CombinatoricsError):
        jl.log_evidence(S, blocks, {})


# ------------------------------------------------------------------ saved P8 structures and a real P8c checkpoint
@pytest.fixture(scope="module")
def real():
    roots = t7.prepare(torch.load("runs/p8/c_training/dataset.pt", weights_only=False))
    rich = max((r for r in roots if r["split"] == "train" and len(r["cands"]) <= 12),
               key=lambda r: (len({q for c in r["cands"] for q in c["z_q"]}) - len(r["cands"]), len(r["cands"])))
    model = abc8.build("B-full")
    model.load_state_dict(torch.load("runs/p8/c_training/ckpt_B-full#s0.pt", weights_only=True))
    return {"roots": roots, "rich": rich, "model": model}


def test_real_root_normalization_scene_consistency_and_aliases(real):
    S, blocks, lab, outs = jl.tables(real["model"], real["rich"])
    assert abs(float(torch.exp(S["logp"]).sum()) - 1) < 1e-10 and S["queries"][0].endswith(":empty")
    for o in outs:
        assert len(o["slots"]) <= 9 and abs(float(torch.exp(o["logP"]).sum()) - 1) < 1e-10
        assert all(abs(float(o["scene_marg"][n]) - float(outs[0]["scene_marg"][n])) < 1e-12 for n in S["names"])
    assert len({len(b["queries"]) for b in blocks}) > 1                # different omission layouts, same P_S
    ll, n, sh = jl.log_evidence(S, blocks, lab)
    assert sh > 0 and n > 0 and torch.isfinite(ll)
    m = jl.marginals(S, blocks)
    assert all(abs(m[q] - float(torch.exp(S["logp"]) @ S["Z"][:, i])) < 1e-12 for i, q in enumerate(S["queries"]))


def test_real_static_gets_no_outcome_gradient_but_static_bce_and_travel_do(real):
    m, r = real["model"], real["rich"]
    m.zero_grad()
    S, blocks, lab, _ = jl.tables(m, r)
    (-jl.log_evidence(S, blocks, lab)[0]).backward()
    for mod in (m.unary, m.pairh, m.cost):
        assert all(p.grad is None or float(p.grad.abs().max()) == 0 for p in mod.parameters())
    assert float(m.scene[0].weight.grad.abs().sum()) > 0 and float(m.order_s[0].weight.grad.abs().sum()) > 0
    m.zero_grad()
    L = jl.losses(m, r)
    L["static"].backward()
    assert float(m.pairh[0].weight.grad.abs().sum()) > 0 and m.scene[0].weight.grad is None
    m.zero_grad()
    if L["travel"] is not None:
        jl.losses(m, r)["travel"].backward()
        assert float(m.cost[0].weight.grad.abs().sum()) > 0 and m.scene[0].weight.grad is None
    e = next(o for c, o in zip(r["cands"], t7.forward(m, r)) if not c["seq"])
    assert float(e["J"]) == 0.0


def test_real_directional_derivatives_per_factor_module(real):
    m, r = real["model"], copy.deepcopy(real["rich"])
    r["cands"] = r["cands"][:6]

    def f():
        S, b, lab, _ = jl.tables(m, r)
        return -jl.log_evidence(S, b, lab)[0]
    for mod in ("scene", "pair_scene", "pair_omit", "cpl", "ho_s", "ho_q", "order_s", "mix"):
        ps = list(getattr(m, mod).parameters())
        g = torch.Generator().manual_seed(0)
        d = [torch.randn(p.shape, generator=g, dtype=D) for p in ps]
        m.zero_grad()
        f().backward()
        ad = sum(float((p.grad * v).sum()) for p, v in zip(ps, d) if p.grad is not None)
        with torch.no_grad():
            for p, v in zip(ps, d):
                p += 1e-6 * v
            fp = float(f())
            for p, v in zip(ps, d):
                p -= 2e-6 * v
            fm = float(f())
            for p, v in zip(ps, d):
                p += 1e-6 * v
        assert abs((fp - fm) / 2e-6 - ad) < 1e-5 * max(1.0, abs(ad)), mod


def test_real_no_leakage_of_ids_labels_or_status(real):
    m, r = real["model"], real["rich"]
    a = jl.tables(m, r)
    s = copy.deepcopy(r)
    s |= {"key": "scrambled", "split": "test"}
    s["y"] = {q: None for q in s["y"]}
    s["scene_y"] = {q: None for q in s["scene_y"]}
    for c in s["cands"]:
        c |= {"y": None, "src": "WITNESS", "cost": None, "z": [None] * len(c["z"])}
    b = jl.tables(m, s)
    assert torch.equal(a[0]["logp"], b[0]["logp"]) and all(torch.equal(x["logq"], y["logq"]) for x, y in zip(a[1], b[1]))


def test_real_order_representation_and_omission_prefix(real):
    m, r = real["model"], real["rich"]
    seq = next(c["seq"] for c in r["cands"] if len(c["seq"]) >= 2)
    m._memo = None
    s1, _, xy1 = m._order(r["R"], seq)
    s2, _, xy2 = m._order(r["R"], list(reversed(seq)))
    assert torch.allclose(xy1, xy2) and abs(float(s1) - float(s2)) > 1e-9
    seen, enc = [], m.encode
    m.encode = lambda R, xy: (seen.append(xy.clone()), enc(R, xy))[1]
    try:
        m._order(r["R"], seq[1:])                                       # omit action 0: its object never moves
    finally:
        del m.encode
    i0 = seq[0][0]
    assert seen and all(torch.equal(xy[i0], r["R"].xy0[i0]) for xy in seen)


def test_real_label_status_and_matched_label_access(real):
    ds = torch.load("runs/p8/c_training/dataset.pt", weights_only=False)
    for rec in ds["roots"]:
        for c in rec["candidates"]:
            for y, s in zip(c["privileged"]["z"], c["privileged"]["z_source"]):
                assert s not in ("UNRESOLVED", None) or y is None      # UNKNOWN / NOT_RUN never become zeros
    sf = abc8.build("SF")
    r = real["rich"]
    S, blocks, _, _ = jl.tables(real["model"], r)
    lg = jl.factorized_logits(sf, r, t7.forward(sf, r))
    assert set(lg) == set(S["queries"]) | {q for b in blocks for q in b["queries"]}
    assert jl.losses(sf, r)["n_obs"] == jl.log_evidence(S, blocks, jl.labels(r))[1]
