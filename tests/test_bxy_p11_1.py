"""BXY-P11.1 amendment tests: gate-free primary cost rule (no-op as an ordinary candidate), the gated secondary ablation, per-arm gamma,
evaluation tiers (train176 OOF primary), travel decomposition contrasts and the successor design / lock. No training, no teacher call."""
import itertools
import json

import numpy as np
import pytest

import bxy_data as bd

HAVE = (bd.DATA / "roots").exists() and __import__("pathlib").Path("runs/approach_b/bxy_pmin_v1/BXY_SIDECAR_V2_PMIN.json").exists()
pytestmark = pytest.mark.skipif(not HAVE, reason="local BD_GEN_V1 snapshot / P-min sidecar not present")
if HAVE:
    import bxy_p11 as P
    import bxy_p11_1 as A


def rows_(*spec):
    return [{"sig": s, "m": m, "cd": cd, "admissible": ad, "p": p, "J_hat": j, "xi": None, "yi": None} for s, m, cd, ad, p, j in spec]


def cost(r, g=0.05):
    return -np.log(r["p"]) + 0.1 * r["m"] + g * r["J_hat"]


def test_primary_selects_the_lower_cost_correction_over_a_likely_noop():
    r = rows_(("empty", 0, 0, True, 0.55, 1.0), ("b>2", 1, 1, True, 0.95, 1.0))
    assert cost(r[1]) < cost(r[0])                                           # .051 + .1 + .05 < .598 + .05
    assert A.choose(r) == 1 and A.choose(r, A.rule("XY-quadratic-noJ")) == 1
    assert A.choose_gated(r, "XY-quadratic") == 0                            # the superseded gate would have forced the no-op
    assert P.choose(r) == 0                                                  # frozen P11 default unchanged (secondary ablation)


def test_noop_is_an_ordinary_candidate_and_wins_on_cost():
    assert A.choose(rows_(("empty", 0, 0, True, 0.9, 1.0), ("b>2", 1, 1, True, 0.95, 1.0))) == 0   # .105 < .051 + .1
    assert A.choose(rows_(("empty", 0, 0, True, 0.3, 1.0), ("b>2", 1, 1, True, 0.31, 1.0))) == 0  # .1 move penalty
    lo = rows_(("empty", 0, 0, True, 1e-6, 1.0), ("b>2", 1, 1, True, 1e-5, 1.0))
    assert A.choose(lo) == 1                                                 # eta = 0: never abstains


def test_gamma_by_arm_and_travel_tradeoff():
    assert {a: A.rule(a)["gamma"] for a in A.GAMMA} == A.GAMMA
    assert A.GAMMA["XY-quadratic-noJ"] == A.GAMMA["DIRECT"] == A.GAMMA["LB"] == 0 and A.GAMMA["XY-quadratic"] == 0.05
    r = rows_(("empty", 0, 0, True, 0.1, 1.0), ("a>2", 1, 1, True, 0.80, 9.0), ("b>3", 1, 1, True, 0.78, 1.0))
    assert A.choose(r, A.rule("XY-quadratic")) == 2 and A.choose(r, A.rule("XY-quadratic", gamma=0.0)) == 1
    assert A.rule("XY-quadratic", gamma=0.0)["noop_gate"] is None


def test_ties_deterministic_permutation_invariant_and_f1_first():
    tie = rows_(("empty", 0, 0, True, 0.1, 1.0), ("z>2", 1, 1, True, 0.6, 1.0), ("a>2", 1, 1, True, 0.6, 1.0), ("q>5", 1, 2, True, 0.6, 1.0),
                ("x>9", 1, 0, False, 0.999, 0.0))
    for perm in itertools.permutations(tie):
        assert list(perm)[A.choose(list(perm))]["sig"] == "a>2"              # (m, C_d, signature); inadmissible never chosen
    two = rows_(("empty", 0, 0, True, 0.1, 1.0), ("b>2", 2, 1, True, 0.9 * np.exp(-0.1), 1.0), ("a>2", 1, 1, True, 0.9 * np.exp(-0.2), 1.0))
    assert cost(two[1]) == pytest.approx(cost(two[2]), abs=1e-12) and two[A.choose(two)]["sig"] == "a>2"   # equal cost -> fewer moves


def test_primary_refuses_a_gated_rule():
    with pytest.raises(ValueError):
        A.choose(rows_(("empty", 0, 0, True, 0.5, 1.0)), A.GATED)


def test_evaluation_tiers_and_oof_coverage():
    sc, D, R, _ = P.load()
    t = A.eval_roots(D, R)
    assert (len(t["PRIMARY_DEV"]), len(t["SUPPLEMENTARY_DEV"]), len(t["DESCRIPTIVE_VAL"]), t["CONFIRMATORY"]) == (176, 197, 21, [])
    assert not set(t["PRIMARY_DEV"]) & set(t["DESCRIPTIVE_VAL"]) and set(t["PRIMARY_DEV"]) | set(t["DESCRIPTIVE_VAL"]) == set(t["SUPPLEMENTARY_DEV"])
    held = [k for f in P.folds(D, R)["folds"] for k in f["heldout"]]
    assert sorted(held) == t["SUPPLEMENTARY_DEV"]                           # every root out-of-fold exactly once
    assert not {k for k in t["SUPPLEMENTARY_DEV"] if bd.split_of(R[k]) == "test"}


def test_travel_contrasts_isolate_training_and_ranking():
    c = {x["id"]: x for x in A.TRAVEL_CONTRASTS}
    assert c["TRAVEL_TRAINING"]["a"][1] == c["TRAVEL_TRAINING"]["b"][1] == 0.0 and c["TRAVEL_TRAINING"]["a"][0] != c["TRAVEL_TRAINING"]["b"][0]
    assert c["TRAVEL_RANKING"]["a"][0] == c["TRAVEL_RANKING"]["b"][0] and c["TRAVEL_RANKING"]["a"][1] != c["TRAVEL_RANKING"]["b"][1]
    assert c["TRAVEL_COMBINED"]["a"] == ("XY-quadratic", 0.05) and c["TRAVEL_COMBINED"]["b"] == ("XY-quadratic-noJ", 0.0)


def test_successor_design_keeps_roster_folds_and_parent():
    d = A.design()
    base = json.loads(A.P11_DESIGN.read_text())
    assert d["parent"]["design_sha256"] == A.P11_DESIGN_SHA and d["roster"] == base["roster"] and len(d["roster"]) == 108
    assert d["folds"] == base["folds"] and d["training"] == base["training"] and d["arms"] == base["arms"] and d["objective"] == base["objective"]
    assert d["selection"]["primary"]["noop_gate"] is None and d["selection"]["secondary_ablations"]["GATED_NOOP"]["noop_gate"] == 0.5
    assert d["evaluation"]["tier_roots"] == {"PRIMARY_DEV": 176, "SUPPLEMENTARY_DEV": 197, "DESCRIPTIVE_VAL": 21, "CONFIRMATORY": 0}
    assert d["budget"] == base["budget"]


def test_successor_freeze_refuses_rewrite(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "OUT", tmp_path)
    lock = A.freeze()
    assert not lock["authorized"] and lock["parent_design_sha256"] == A.P11_DESIGN_SHA and A.freeze()["design_sha256"] == lock["design_sha256"]
    (tmp_path / "TRAINING_DESIGN_P11_1.json").write_text("{}")
    with pytest.raises(FileExistsError):
        A.freeze()
    real = A.PM.sources
    (tmp_path / "TRAINING_DESIGN_P11_1.json").unlink()
    A.freeze()
    monkeypatch.setattr(A.PM, "sources", lambda entry: {**real(entry), "bxy_p11_1.py": "drift"})
    with pytest.raises(RuntimeError, match="source drift"):
        A.assert_frozen(check_git=False)
