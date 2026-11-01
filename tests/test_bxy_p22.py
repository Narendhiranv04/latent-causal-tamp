"""BXY-P22: the K0-K4 confirmation plan uses a new namespace, is never generated, leaves the P18 plan immutable; frozen checkpoints have
verified second copies."""
import hashlib
import json
from pathlib import Path

import pytest

OUT = Path("runs/approach_b/bxy_p22_v1")
pytestmark = pytest.mark.skipif(not (OUT / "CONFIRM_PLAN_K04.json").exists(), reason="P22 artifacts missing")


def test_plan_namespace_custody_and_p18_immutability():
    import bxy_p20_k34 as Z
    pl = json.loads((OUT / "CONFIRM_PLAN_K04.json").read_text())
    assert pl["namespace"] == "bxyg34confirm" and pl["namespace"] != Z.NS
    p24 = Path("runs/approach_b/bxy_p24_v1/AUTHORIZATION_P24.json")      # generated only under the user's explicit P24 authorization
    assert not any(Path("runs/approach_b").glob("**/*bxyg34confirm*")) or (p24.exists() and json.loads(p24.read_text())["approved"] is True)
    with pytest.raises(PermissionError):
        Z.generate("bxyg34confirm")
    p18 = Path(pl["p18_plan"]["path"])
    assert hashlib.sha256(p18.read_bytes()).hexdigest() == pl["p18_plan"]["sha256"]


def test_frozen_models_have_verified_second_copies():
    fz = json.loads((OUT / "FROZEN_MODELS_P22.json").read_text())
    assert set(fz["arms"]) == {"D:XYQ-GEO-SYM", "E:XY-UNC-SA-GEO-SYM", "A:DIRECT-GEO"}
    for arm, v in fz["arms"].items():
        assert v["complete"] and all(c["repo_copy_ok"] and c["backup_copy_ok"] for c in v["checkpoints"].values())
