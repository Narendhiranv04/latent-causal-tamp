"""P13: factor implementation audits (exact energy decomposition, ablation isolation, keyed normalization vs brute force, symmetry,
duplicate invariance, B / C scene-block identity, gradient reach, no physical calls in scoring), the preregistered kappa estimand and
strict D / scene-edit lattice identity. Implementation evidence only: none of these tests says a factor is useful."""
import copy
import os

import pytest
import torch

os.environ.setdefault("P10C_OUT", "runs/p10c")

import abc7_models as a7  # noqa: E402
import p10c_train_eval as pc  # noqa: E402
import p13_factors as f  # noqa: E402
import unique_factor as uf  # noqa: E402
import unique_factor_keyed as ufk  # noqa: E402

ABL = {"B-F3": dict(drop=("pair_scene",)), "B-F4": dict(drop=("pair_omit",)), "B-F5q": dict(couple="quadratic"),
       "B-F5s": dict(couple="structured"), "B-F2": dict(order="none")}
ZERO = {"B-F3": {"F3_pair_scene"}, "B-F4": {"F4_pair_omit"}, "B-F5q": {"F5q_ho_scene", "F5q_ho_block"},
        "B-F5s": {"F5_scene_scene", "F5_scene_query", "F5_omit_omit", "F5q_ho_scene", "F5q_ho_block"}, "B-F2": set()}


@pytest.fixture(scope="module")
def root():
    rs = pc.prepared("blind")
    return max(rs[:20], key=lambda r: sum(len(c["seq"]) >= 2 for c in r["cands"]))         # a root with omission blocks


@pytest.fixture(scope="module")
def labelled():
    rs = [r for r in pc.prepared("trainval") if r["split"] == "validation"]
    return max(rs[:20], key=lambda r: sum(len(c["seq"]) >= 2 and c["y"] is not None for c in r["cands"]) + sum(v is not None for v in r["scene_y"].values()))


def _flat(comp):
    out = dict(comp["scene"])
    for q, b in comp["blocks"].items():
        out |= {f"{q}|{k}": v for k, v in b.items()}
    return out


def test_decomposition_equals_instance_energies(root):
    for arm in ("K-B", "K-C", "B-F3", "B-F5s"):
        m = pc.load(f"F-{arm}-s0")[0]
        with torch.no_grad():
            c = f.components(m, root)
        assert torch.allclose(sum(c["scene"].values()), c["scene_E"], atol=1e-10)
        for q, b in c["blocks"].items():
            assert torch.allclose(sum(b.values()), c["inst"]["blocks"][q]["energy"].reshape(-1), atol=1e-10)


@pytest.mark.parametrize("arm", list(ABL))
def test_ablation_removes_only_its_term(root, arm):
    torch.manual_seed(0)
    full = a7.ModelBC7("B", "full").double()
    kw = {"couple": "full"} | ABL[arm]
    abl = a7.ModelBC7("B", **kw).double()
    miss, extra = abl.load_state_dict(full.state_dict(), strict=False)
    assert not miss and {k.split(".")[0] for k in extra} <= {"pair_scene", "pair_omit", "cpl", "ho_u", "ho_s", "ho_q", "pairo", "mix"}
    with torch.no_grad():
        cf_, ca = _flat(f.components(full, root)), _flat(f.components(abl, root))
    if arm == "B-F2":                                    # order path only: the scene block is untouched
        assert all(torch.equal(cf_[k], ca[k]) for k in f.components(full, root)["scene"])
        return
    assert set(cf_) == set(ca)
    for k in cf_:
        kind = k.split("|")[-1]
        if kind in ZERO[arm]:
            assert float(ca[k].abs().max()) == 0.0
        else:
            assert torch.allclose(cf_[k], ca[k], atol=1e-12), k


def test_keyed_normalization_matches_brute_force(root):
    m = pc.load("F-K-B-s0")[0]
    with torch.no_grad():
        inst = ufk.instances(m, root)
        qs = uf.variables(inst)[:2]
        for lab in ({}, {qs[0]: 1}, {qs[0]: 0, qs[1]: 1}):
            assert abs(float(uf.log_evidence(inst, lab)[0]) - uf.brute_force(inst, lab)) < 1e-8


def test_pairs_symmetric_and_keyed_duplicate_invariance(root):
    m = pc.load("F-K-B-s0")[0]
    with torch.no_grad():
        S = m.scene_block(root["R"], ["z0"] + sorted(n for n in root["cands"][0]["slots"] if n.startswith("zS")), root["edits"])
        W = m._pairs(S["v"], m.ctxn(root["R"].ctx), [(0, 1, "scene"), (1, 2, "couple")])
        assert torch.allclose(W, W.T)
        r2 = dict(root, cands=root["cands"] + [copy.deepcopy(c) for c in root["cands"] if len(c["seq"]) >= 2][:2])
        a, b = uf.prior_marginals(ufk.instances(m, root)), uf.prior_marginals(ufk.instances(m, r2))
    assert a.keys() == b.keys() and max(abs(a[k] - b[k]) for k in a) < 1e-12


def test_b_and_c_share_the_scene_block(root):
    torch.manual_seed(1)
    b, c = a7.ModelBC7("B", "full").double(), a7.ModelBC7("C", "full").double()
    c.load_state_dict(b.state_dict(), strict=False)
    names = ["z0"] + sorted(n for n in root["cands"][0]["slots"] if n.startswith("zS"))
    with torch.no_grad():
        assert torch.allclose(b.scene_block(root["R"], names, root["edits"])["logP"], c.scene_block(root["R"], names, root["edits"])["logP"])


def test_gradient_reaches_every_present_factor(labelled):
    root = labelled
    for arm in ("K-B", "B-F3", "B-F5q"):
        m = pc.load(f"F-{arm}-s0")[0]
        m.zero_grad()
        with ufk.installed():
            uf.total(m, [root])[0].backward()
        g = {}
        for n, p in m.named_parameters():
            g[f._group(n)] = g.get(f._group(n), 0.0) + (float(p.grad.abs().sum()) if p.grad is not None else 0.0)
        assert all(v > 0 for k, v in g.items() if k != "J_cost" or any(c.get("cost") for c in root["cands"])), (arm, g)


def test_scoring_makes_no_physical_calls(root):
    import p10_protocol as pp
    import p9_l3c as l3c
    calls = pp.instrument()
    m = pc.load("F-K-B-s0")[0]
    with torch.no_grad(), ufk.installed():
        l3c.deployed(m, root, uf.instances(m, root), 1.0, 0.5)
    assert not sum(calls.values())


def test_preregistered_kappa_estimand_differs_from_seedwise_mean():
    k, khat = 0, [0.6, -0.6, 0.3]                         # seed-mean error 0.1 < mean seed-wise error 0.5 (signs cancel)
    pre = abs(sum(khat) / 3 - k)
    sw = sum(abs(x - k) for x in khat) / 3
    assert abs(pre - 0.1) < 1e-12 and abs(sw - 0.5) < 1e-12 and pre < sw


def test_strict_lattice_identity_and_failure():
    import json
    from pathlib import Path
    plan = json.loads(Path("runs/p12/holdout/batch1/plan.json").read_text())
    k, r = next(iter(plan["roots"].items()))
    lat, why = f._strict(r, k)
    assert why is None and len(lat) == 2 ** len(r["parking"])
    bad = copy.deepcopy(r)
    it = next(i for i in bad["items"] if i.get("d_subset") == ["A"])
    it["edit"] = {list(it["edit"])[0]: -1}
    assert f._strict(bad, k)[0] is None


def test_p10b_teacher_policy_unchanged_and_p13_variant_declared():
    import p10b_dataset as pd
    import p13_pipeline as p13
    assert pd.POLICY["stop_after_censored_seed"] is True and pd.POLICY["version"] == "P10B_S100_V1"
    assert p13.TEACHER["stop_after_censored_seed"] is False and p13.TEACHER["version"] == "P13_S100_V2"
