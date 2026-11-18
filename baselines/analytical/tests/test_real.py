"""Real-root physics checks in both domains (TRAIN roots; subprocess with the domain's physics python and env.sh variables)."""
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(os.environ.get("AB_OUT", Path.home() / "analytical_baselines"))
CASES = {"2d": "2d-conv-plus2d-w0005-s017", "3d": "3ds66-lap-w0017-s016"}


@pytest.mark.slow
@pytest.mark.parametrize("dom", ["2d", "3d"])
def test_real_root(dom):
    if os.environ.get("ANALYTICAL_SKIP_SLOW"):
        pytest.skip("slow checks disabled")
    pub = OUT / f"smoke/public_train_{dom}.jsonl"
    if not pub.exists() or "ABF_ROOT" not in os.environ:
        pytest.skip("source baselines/analytical/env.sh and build the smoke index first")
    py = os.environ["PY2D"] if dom == "2d" else os.environ["PY3D"]
    out = OUT / "tests"
    out.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["nice", "-n", "10", py, "-m", "baselines.analytical.tests.real_checks", dom, CASES[dom], str(pub), str(out)],
                       cwd=ROOT, capture_output=True, text=True, timeout=3000)
    assert r.returncode == 0, r.stderr[-3000:]
    res = json.loads(r.stdout.strip().splitlines()[-1])
    (out / f"real_checks_{dom}.json").write_text(json.dumps(res, indent=1))
    assert res["parent_untouched"] and res["restore_equal_after_branch"] and res["carried_q_differs_from_qref"]
    assert res["two_orders_executed"] and res["second_move_starts_at_carried_q"]
    if res["two_orders_executed"]:
        assert res["same_endpoint"] and res["keys_differ_or_transposition"] and res["y_order_independent"]
        assert res["connector_calls_for_two_terminals"] == (2 if res["keys_differ"] else 1)
    assert res["deterministic_replay"] and res["private_fields_irrelevant"]
