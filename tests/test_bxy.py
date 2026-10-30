"""Approach B X/Y (Approach_B_Final_Methodology_2026-10-31): exact math against brute force, query identities, sidecar semantics,
legacy-LB record preservation and the neural forward on real roots (methodology §8.2 acceptance checks 1, 3, 4, 5)."""
import itertools
import json
import math
from pathlib import Path

import numpy as np
import pytest
import torch

import bxy_core as X
import bxy_data as bd

D = torch.float64
HAVE = (bd.DATA / "roots").exists() and Path("runs/approach_b/bxy/SIDECAR.json").exists()
need = pytest.mark.skipif(not HAVE, reason="local BD_GEN_V1 snapshot / sidecar not present")


def rand(nY, nX, seed):
    g = torch.Generator().manual_seed(seed)
    b, a, w = (torch.randn(n, generator=g, dtype=D) * 2 for n in (nY, nX, nX))
    parent = [int(torch.randint(nY, (1,), generator=g)) for _ in range(nX)]
    return b, a, w, parent


def test_four_state_microcase_every_observation_pattern():
    b, a, w, parent = rand(1, 1, 0)
    for oy, ox in itertools.product((None, 0, 1), repeat=2):
        obs_y, obs_x = ({0: oy} if oy is not None else {}), ({0: ox} if ox is not None else {})
        assert float(X.log_evidence(b, a, w, parent, obs_y, obs_x)) == pytest.approx(X.brute_force(b, a, w, parent, obs_y, obs_x), abs=1e-12)
    p = {(x, y): float(torch.exp(-X.energy_root(b, a, w, parent, (y,), (x,)))) for x in (0, 1) for y in (0, 1)}
    assert sum(p.values()) == pytest.approx(1.0, abs=1e-12)                                   # normalizers included: partition = 1
    u = (a + w)[0]
    assert p[(1, 1)] == pytest.approx(float(torch.sigmoid(b[0]) * torch.sigmoid(u)), abs=1e-12)  # p_succ
    lor = np.log(p[(1, 1)] * p[(0, 0)] / (p[(1, 0)] * p[(0, 1)]))
    assert lor == pytest.approx(float(w[0]), abs=1e-9)                                        # cross log-odds ratio = w / tau


@pytest.mark.parametrize("seed", range(6))
def test_root_microcases_match_enumeration(seed):
    b, a, w, parent = rand(3, 4, seed)
    rng = np.random.default_rng(seed)
    for _ in range(8):
        obs_y = {s: int(rng.integers(2)) for s in range(3) if rng.random() < 0.5}
        obs_x = {q: int(rng.integers(2)) for q in range(4) if rng.random() < 0.5}
        assert float(X.log_evidence(b, a, w, parent, obs_y, obs_x)) == pytest.approx(X.brute_force(b, a, w, parent, obs_y, obs_x), abs=1e-10)


def test_scene_marginals_invariant_to_appended_x_proposals():
    b, a, w, parent = rand(3, 2, 7)
    b2, a2, w2, p2 = rand(3, 3, 8)
    a_, w_, par_ = torch.cat([a, a2]), torch.cat([w, w2]), parent + p2
    assert torch.equal(X.marginals(b, a, w, parent)["py"], X.marginals(b, a_, w_, par_)["py"])
    obs_y = {0: 1, 2: 0}
    lp = X.log_evidence(b, a, w, parent, obs_y, {})
    assert float(lp) == pytest.approx(float(X.log_evidence(b, a_, w_, par_, obs_y, {})), abs=1e-12)        # unobserved X sum to 1
    assert float(lp) == pytest.approx(X.brute_force(b, a_, w_, par_, obs_y, {}), abs=1e-10)


def test_x_marginal_marginalizes_y_and_gradients_are_exact():
    b, a, w, parent = rand(2, 3, 3)
    m = X.marginals(b, a, w, parent)
    for q in range(3):
        assert float(m["px"][q]) == pytest.approx(math.exp(X.brute_force(b, a, w, parent, {}, {q: 1})), abs=1e-12)
        s = parent[q]
        assert float(m["psucc"][q]) == pytest.approx(math.exp(X.brute_force(b, a, w, parent, {s: 1}, {q: 1})), abs=1e-12)
    args = tuple(t.clone().requires_grad_(True) for t in (b, a, w))
    assert torch.autograd.gradcheck(lambda b_, a_, w_: X.log_evidence(b_, a_, w_, parent, {0: 1}, {0: 0, 2: 1}), args)


def test_uncoupled_is_product_and_zero_w_gives_independence():
    b, a, _, parent = rand(2, 2, 5)
    w = torch.zeros(2, dtype=D)
    full = X.log_evidence(b, a, w, parent, {parent[0]: 1}, {0: 1})
    ind = X.log_py(b[parent[0]], 1) + X.log_px(a[0], 0.0, 1, 0)                               # w = 0: X does not depend on Y
    assert float(full) == pytest.approx(float(ind), abs=1e-12)


def _rec():
    objs = [{"id": "t0", "cell": 10}, {"id": "o00", "cell": 20}, {"id": "o01", "cell": 21}, {"id": "o02", "cell": 22}]
    return {"scene": {"objects": objs}}


def test_query_identities_shared_y_reversed_order_and_omission_recompute():
    r = _rec()
    ab, ba = [("o00", 40), ("o01", 41)], [("o01", 41), ("o00", 40)]
    assert bd.ykey("k", r, ab) == bd.ykey("k", r, ba) == "Y:k:o00>40.o01>41"                 # one shared hypothetical scene
    assert bd.xkey("k", ab) != bd.xkey("k", ba)                                                 # two physical order queries
    abc = ab + [("o02", 42)]
    om = [a for i, a in enumerate(abc) if i != 1]                                               # omit the middle action: recomputed from S0
    assert bd.endpoint(r, om) == {"o00": 40, "o02": 42} and bd.xkey("k", om) == "X:k:o00>40.o02>42"
    assert bd.ykey("k", r, []) == "Y:k:empty" and X.parse("Y:k:empty") == [] and X.parse(bd.xkey("k", abc)) == abc


@need
def test_sidecar_reuses_only_semantically_matching_labels():
    R, S = bd.roots(), json.loads(Path("runs/approach_b/bxy/SIDECAR.json").read_text())
    for k, rec in R.items():
        sc = S[k]
        assert sc["y_obs"][bd.ykey(k, rec, [])] == {"y": rec["labels"]["original"]["y"], "source": "labels.original"}
        for e in rec["labels"]["D"]:
            assert sc["y_obs"][bd.ykey(k, rec, edit=e["edit"])]["y"] == e["y"]                  # recorded y, unchanged
        want = {bd.xkey(k, [(o, int(d)) for o, d in b["sequence"]][:b["failed_step"] + 1]) for b in rec["labels"]["B"] if isinstance(b["failed_step"], int)}
        assert set(sc["x_obs"]) == want and all(v["y"] == 0 for v in sc["x_obs"].values())     # only failed relocations, shortest prefix, 0
        assert not sc["conflicts"]
        assert [c["seq"] for c in sc["catalogue"][1:]] == [[list(a) for a in b["sequence"]] for b in rec["labels"]["B"]]   # order, destinations
        assert [c["y_full"] for c in sc["catalogue"][1:]] == [b["y"] for b in rec["labels"]["B"]]
        assert sc["catalogue"][0]["seq"] == [] and sc["catalogue"][0]["x"] is None             # zero-move candidate: no X variable


@need
def test_iid_splits_disjoint_by_family_and_match_generator_rule():
    R = bd.roots()
    fam = {}
    for k, rec in R.items():
        fam.setdefault(rec["ids"]["parent_family_id"], set()).add(bd.split_of(rec))
    assert all(len(v) == 1 for v in fam.values())
    old = json.loads((bd.DATA / "SPLITS.json").read_text())["splits"]["iid"]
    assert all(bd.split_of(R[k]) == v for k, v in old.items())


@need
def test_lb_records_preserve_labels_order_and_six_move_sequences():
    d = torch.load("runs/approach_b/bd2d_lb_v1/RECORDS.pt", weights_only=False)
    R = bd.roots()
    six = 0
    for x in d["roots"]:
        k, rec = x["audit"]["root"], R[x["audit"]["root"]]
        ids = x["audit"]["ids"]
        cs = x["candidates"]
        assert cs[0]["actions"] == [] and cs[0]["privileged"]["y"] == rec["labels"]["original"]["y"]
        for c, b in zip(cs[1:], rec["labels"]["B"]):
            assert [ids[i] for i, _ in c["actions"]] == [o for o, _ in b["sequence"]]
            assert [bd.endpoint(rec, [(o, d_)])[o] for o, d_ in b["sequence"]] == [int(d_) for _, d_ in b["sequence"]]
            assert c["privileged"]["y"] == b["y"]
            six += len(b["sequence"]) == 6
            if len(b["sequence"]) >= 5:
                assert "zR" in c["z_slots"] and sum(s.startswith("zO") for s in c["z_slots"]) <= len(b["sequence"])
        assert len(cs) == 1 + len(rec["labels"]["B"])                                            # nothing dropped
    assert six == 4


@need
def test_neural_forward_on_real_roots_including_six_moves():
    m = X.build("XY-quadratic")
    rts = [r for r in X.views("train", full=True) if any(len(c["seq"]) == 6 for c in r["catalogue"])]
    assert rts
    b, a, w, J = m.coeffs(rts[0])
    assert len(b) == len(rts[0]["y_keys"]) and len(a) == len(w) == len(rts[0]["x_keys"]) and torch.isfinite(torch.cat([b, a, w])).all()
    tr = X.views("train")
    full = {r["key"]: r for r in X.views("train", full=True)}
    for r in tr[:10]:                                                                           # observed-only view = full view (exact)
        lo = X.log_evidence(*m.coeffs(r)[:3], r["parent"], r["obs_y"], r["obs_x"])
        f = full[r["key"]]
        lf = X.log_evidence(*m.coeffs(f)[:3], f["parent"], f["obs_y"], f["obs_x"])
        assert float(lo) == pytest.approx(float(lf), abs=1e-9)
