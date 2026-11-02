"""BXY-P25: the final evidence is derived from, and consistent with, the single locked P24 evaluation (no second look, no relabelling)."""
import json
from pathlib import Path

import numpy as np
import pytest

import bxy_p25_final as F

EV = Path("runs/approach_b/bxy_p24_v1/EVALUATION_P24.json")
pytestmark = pytest.mark.skipif(not (F.OUT / "DECISION_P25.json").exists(), reason="P25 artifacts missing")


def test_decision_manifest_matches_the_locked_evaluation():
    ev = json.loads(EV.read_text())
    dec = json.loads((F.OUT / "DECISION_P25.json").read_text())
    assert dec["source_evaluation_sha256"] == F.C.sha_file(EV)
    pr = ev["row"]["primary"]
    assert dec["confirmatory"]["D_vs_DIRECT_U"] == pr["D_vs_DIRECT"]["label"] == "NOT_ESTABLISHED"
    assert dec["confirmatory"]["E_vs_DIRECT_U"] == pr["E_vs_DIRECT"]["label"]
    assert dec["confirmatory"]["order"] == {k: v["label"] for k, v in ev["row"]["order"].items()}
    assert all(sum(v.values()) == ev["row"]["populations"]["INF"] for v in dec["failure_breakdown_INF"].values())


def test_ablations_reproduce_sealed_ensemble_and_sealed_scores():
    A = json.loads((F.OUT / "ABLATIONS_P25.json").read_text())
    ev = json.loads(EV.read_text())["row"]
    assert A["reproduction"]["max_abs_diff_vs_sealed"] <= F.TOL and A["source_evaluation_sha256"] == F.C.sha_file(EV)
    for a in F.ARMS:                                                       # rescoring the sealed predictions gives the locked numbers back
        assert abs(A["sealed_15"][a]["U"] - ev["arms"][a]["U"]) < 1e-4 and abs(A["sealed_15"][a]["unnecessary"] - ev["arms"][a]["unnecessary"]) < 1e-4
        assert len(A["single_member"][a]) == 15


def test_ens_is_the_frozen_mean_rule():
    cands = [{"sig": "empty", "m": 0, "cd": 0.0, "xi": None, "yi": 0, "admissible": True},
             {"sig": "o00>1", "m": 1, "cd": 1.0, "xi": 0, "yi": 1, "admissible": True},
             {"sig": "o01>2", "m": 1, "cd": 1.0, "xi": 1, "yi": 2, "admissible": False}]
    prs = [{"cands": [{"p": p0, "J_hat": 1.0}, {"p": p1, "J_hat": 2.0, "px": 0.5}, {}], "vars": {"px": [0.1 * i, 0.2], "py": None}}
           for i, (p0, p1) in enumerate([(0.2, 0.4), (0.4, 0.8)])]
    e = F.ens(prs, cands, [0, 1])
    assert e["cands"][0]["p"] == pytest.approx(0.3) and e["cands"][1]["p"] == pytest.approx(0.6) and "p" not in e["cands"][2]
    assert np.allclose(e["vars"]["px"], [0.05, 0.2]) and e["vars"]["py"] is None
    assert F.ens(prs, cands, [1])["cands"][1]["px"] == 0.5


def test_md_tables_strip_markup():
    t = F._md_tables("## Sec\n\n| a | **b** |\n|---|---|\n| [x](y.md) | `z` |\n\ntext\n")
    assert t == [("Sec", [["a", "b"], ["x", "z"]])]
