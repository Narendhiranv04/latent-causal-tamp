"""BXY-P18: the confirmatory plan is derived from development realization only, uses a new namespace, never generates a root, and leaves the
P15 plan immutable; compliance checklist is complete."""
import hashlib
from pathlib import Path

import pytest

import bxy_p16 as G
import bxy_p18 as Z

pytestmark = pytest.mark.skipif(not (G.wdir("wC") / "SUMMARY.json").exists(), reason="P16 waves missing")
P15_PLAN_SHA = "30fac794"


def test_plan_namespace_and_custody():
    pl = Z.plan(Z.development_rates())
    assert pl["namespace"] == "bxyg21confirm" and pl["namespace"] not in G.NS.values()
    assert pl["expected"]["repairable"] >= 60 and pl["expected"]["K_ge2"] >= 24
    assert "model" not in pl["basis"].lower().replace("no model output was used", "")
    with pytest.raises(PermissionError):
        G.generate("bxyg21confirm")
    assert not any(Path("runs/approach_b").glob("**/*bxyg21confirm*"))


def test_p15_plan_immutable():
    h = hashlib.sha256(Path("runs/approach_b/bxy_p15_v1/CONFIRM_PLAN.json").read_bytes()).hexdigest()
    assert h.startswith(P15_PLAN_SHA)
    assert Z.plan(Z.development_rates())["supersedes"]["runs/approach_b/bxy_p15_v1/CONFIRM_PLAN.json"] == h


def test_development_rates_deterministic_and_compliance_complete():
    assert Z.development_rates() == Z.development_rates()
    c = Z.compliance()
    assert len(c) >= 20 and all(set(r) == {"methodology", "implementation", "evidence", "status"} for r in c)


@pytest.mark.skipif(not Path("runs/approach_b/bxy_p17_v1/runs/cv__f2__D__s1/best.pt").exists(), reason="local checkpoints absent")
def test_frozen_member_reproduces_stored_heldout_prediction():
    import json
    import bxy_p11 as P
    import bxy_p17 as M
    import bxy_p17_data as D
    V = {ev["key"]: sv for sv, lab, ev in D.build_all()}
    k = sorted(M.frozen()["folds"]["folds"][2]["heldout"])[0]
    m = Z.load_member("D:XYQ-GEO-SYM", "cv/f2/D/s1")
    stored = json.loads(Path("runs/approach_b/bxy_p17_v1/runs/cv__f2__D__s1/predictions.json").read_text())[k]["cands"]
    now = P.predict_all(m, V[k])["cands"]
    assert all(abs(a.get("p", 0) - b.get("p", 0)) < 1e-12 for a, b in zip(stored, now))
