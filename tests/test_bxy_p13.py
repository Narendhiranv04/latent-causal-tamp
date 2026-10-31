"""BXY-P13: exact NLL decomposition, evaluator-only oracle substitution, attribution arithmetic, leakage guard."""
import copy
import hashlib
import json

import numpy as np
import pytest
import torch

import bxy_p11 as P
import bxy_p13 as Q


@pytest.fixture(scope="module")
def views():
    return P.build()


def _coeffs(sv, seed):
    g = torch.Generator().manual_seed(seed)
    n, q = len(sv["y_poses"]), len(sv["x_seqs"])
    return {"b": torch.randn(n, generator=g, dtype=torch.float64), "a": torch.randn(q, generator=g, dtype=torch.float64),
            "w": torch.randn(q, generator=g, dtype=torch.float64)}


def test_nll_parts_sum_to_exact_joint(views):
    for i, (sv, lab, ev) in enumerate(views[:40]):
        C = _coeffs(sv, i)
        parts = Q.nll_parts(C, sv, lab["obs_x"], lab["obs_y"])
        ref = -P.log_evidence(C["b"], C["a"], C["w"], sv["parent"], lab["obs_x"], lab["obs_y"])
        assert abs(float(sum(parts.values())) - float(ref)) < 1e-9


def _pred(sv, C):
    b, a, w = (C[k].numpy() for k in "baw")
    py, p1 = Q.sig(b), Q.sig(a + w)
    rows = []
    for c in sv["cands"]:
        r = dict(c)
        if c["admissible"]:
            r["p"] = float(py[sv["y0"]]) if c["m"] == 0 else float(py[c["yi"]] * p1[c["xi"]])
            r["J_hat"] = 0.0
        rows.append(r)
    return {"cands": rows, "vars": {"py": py.tolist(), "px": None, "psucc": None}, "coeffs": {k: v.tolist() for k, v in C.items()}}


def test_oracle_substitution_is_evaluator_side_only(views):
    sv, lab, ev = next(v for v in views if v[2]["y0"] == 0 and any(c["success"] == 1 for c in v[2]["cands"]))
    pred = _pred(sv, _coeffs(sv, 0))
    before = copy.deepcopy(pred)
    h = hashlib.sha256(json.dumps({k: v for k, v in sv.items() if k != "R"}, sort_keys=True, default=str).encode()).hexdigest()
    none = Q.oracle_rows("XY-quadratic", pred, sv, ev, ())
    assert all(abs(a["p"] - b["p"]) < 1e-12 for a, b in zip(none, pred["cands"]) if a["admissible"])
    full = Q.oracle_rows("XY-quadratic", pred, sv, ev, ("Y0", "Y", "X"))
    for r, e in zip(full, ev["cands"]):
        if r["admissible"] and e["success"] is not None:
            assert r["p"] == float(e["success"])
    i = P.choose(full, Q.rule("XY-quadratic"))
    assert ev["cands"][i]["success"] == 1                       # full oracle recovers an available verified repair
    assert pred == before                                       # the model's prediction rows are untouched
    P.check_scorer(sv)
    assert h == hashlib.sha256(json.dumps({k: v for k, v in sv.items() if k != "R"}, sort_keys=True, default=str).encode()).hexdigest()


def test_categories_cover_every_choice(views):
    seen = set()
    for i, (sv, lab, ev) in enumerate(views[:80]):
        pred = _pred(sv, _coeffs(sv, i))
        ru = Q.rule("XY-quadratic")
        j = P.choose(pred["cands"], ru)
        c = Q.category(pred["cands"], ev, j, ru)
        seen.add(c)
        assert c in ("SUCCESS", "NO_REPAIR_AVAILABLE", "MISSED_RANKED_BELOW_NOOP", "MISSED_PENALTY_REJECTED", "WRONG_REPAIR_X0", "WRONG_REPAIR_Y0",
                     "WRONG_REPAIR_UNDECIDED", "CORRECT_NOOP", "UNNECESSARY_REPAIR_OK", "UNNECESSARY_REPAIR_FAIL")
        assert (ev["y0"] == 1) == c.startswith(("CORRECT", "UNNECESSARY"))
    assert len(seen) >= 4


def test_ranking_random_expectation_and_auroc():
    rows = [{"m": 0, "admissible": True, "p": 0.9, "cd": 0, "sig": "empty", "J_hat": 0}] + \
           [{"m": 1, "admissible": True, "p": p, "cd": 1, "sig": f"o0{i}>1", "J_hat": 0} for i, p in enumerate((0.2, 0.5, 0.8))]
    ev = {"y0": 0, "cands": [{"success": 0}, {"success": 1}, {"success": 0}, {"success": 0}]}
    r = Q.ranking(rows, ev, Q.rule("XY-quadratic"))
    assert r["rank_p"] == 3 and r["rand_top1"] == pytest.approx(1 / 3) and r["top3_p"] == 1 and r["top1_p"] == 0
    assert Q.auroc([(1, 0.9), (0, 0.1), (0, 0.5)]) == 1.0 and Q.auroc([(1, 0.5), (0, 0.5)]) == 0.5 and Q.auroc([(1, 0.3)]) is None


def test_shapley_efficiency():
    v = {"model": 0.1, "Y0": 0.3, "Y": 0.5, "X": 0.2, "Y0+Y": 0.8, "Y0+X": 0.4, "Y+X": 0.7, "Y0+Y+X": 0.9}
    s = Q.shapley(v)
    assert sum(s.values()) == pytest.approx(v["Y0+Y+X"] - v["model"])


def test_geometry_features_use_scorer_tensors_only(views):
    sv = views[3][0]
    f0 = Q.geo_features(sv["R"], {})
    t = sv["R"].tid
    o = next(i for i in range(sv["R"].n) if i != t)
    f1 = Q.geo_features(sv["R"], {o: tuple(sv["R"].xy0[t].numpy() + np.array([0.05, 0.0]))})
    assert len(f0) == 8 and f1[0] < f0[0]                       # moving an obstacle next to the target reduces target clearance
