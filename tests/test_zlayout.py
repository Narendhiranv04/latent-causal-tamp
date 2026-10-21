"""P5.0: Z_LAYOUT_V2 correctness. No planner calls; pure math plus stored P4 evidence."""
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import operational_teacher as ot  # noqa: E402
import sampler as sp  # noqa: E402
import zlayout as zl  # noqa: E402

CAT = [{"kind": "singleton:o04", "edit": {"o04": 49}, "eligible": True}, {"kind": "singleton:o05", "edit": {"o05": 41}, "eligible": True},
       {"kind": "joint:o04+o05", "edit": {"o04": 49, "o05": 41}, "eligible": True}]


def test_two_move_repair_has_exactly_seven_distinct_slots_and_p4_pool_maps_cleanly():
    lay = zl.build("d2_g4c_r00_AB", [["o04", 49], ["o05", 41]], CAT)
    assert lay["active_count"] == 7 and len(set(lay["query"].values())) == 7
    assert lay["query"]["zO[0]"] == "seq:d2_g4c_r00_AB:o05>41" and lay["query"]["zO[1]"] == "seq:d2_g4c_r00_AB:o04>49"
    plan = json.loads((ROOT / "runs/g4c_lf_p4/pilot/pilot_plan.json").read_text())
    root = plan["roots"]["d2_g4c_r00_AB"]
    entry = next(p for p in root["queries"]["pool"] if p["sequence"] == [["o04", 49], ["o05", 41]])
    cat = [{"kind": q["kind"], "edit": q["edit"], "eligible": q["eligible"]} for q in root["queries"]["scene_queries"]]
    v2 = zl.from_v1("d2_g4c_r00_AB", entry["sequence"], entry["bc_layout"], cat)
    assert v2["v1_active"] == 8 and v2["v1_dropped_duplicates"] == ["zO[2]"] and v2["active_count"] == 7
    recs = json.loads((ROOT / "runs/g4c_lf_p4/pilot/decisions.json").read_text())
    pool = ot.pool("d2_g4c_r00_AB", root, entry["sequence"], recs)                 # the stored 8-slot evidence view
    assert {s["query"] for s in pool["slots"]} == set(v2["query"].values())       # same 7 physical queries, no loss


@pytest.mark.parametrize("seq,count", [([], 4), ([["o04", 49]], 5), ([["o04", 49], ["o05", 41]], 7),
                                       ([["o04", 49], ["o05", 41], ["o06", 3]], 8)])
def test_active_rule_by_length(seq, count):
    lay = zl.build("k", seq, CAT)
    assert lay["active_count"] == count and not any(a and s == "zO[2]" for s, a in zip(lay["slots"], lay["active"])
                                                    if len(seq) == 2)


def test_alias_version_hash_and_bound_refusals():
    with pytest.raises(ValueError):
        zl.build("k", [["o04", 49]], CAT + [{"kind": "dup", "edit": {"o04": 49}, "eligible": True}])   # two slots, one query
    with pytest.raises(ValueError):
        zl.build("k", [["o04", 49], ["o04", 50]], CAT)                                           # not move-once
    lay = zl.build("k", [["o04", 49], ["o05", 41]], CAT)
    for bad in ({**lay, "version": "V1"}, {**lay, "active": [True] * len(lay["slots"])}, {**lay, "root": "other"}):
        with pytest.raises(ValueError):
            zl.verify(bad)
    big = CAT + [{"kind": f"x{i}", "edit": {f"q{i}": i}, "eligible": True} for i in range(3)]
    with pytest.raises(ValueError):
        zl.build("k", [["o04", 49], ["o05", 41]], big)                                          # 10 active > 8


def _joint(theta, lay):
    names = [s for s, a in zip(lay["slots"], lay["active"]) if a]
    def E(z):
        v = np.array([z[n] for n in names], float)
        return float(theta[: len(v)] @ v + 0.5 * v @ np.outer(theta[8:8 + len(v)], theta[8:8 + len(v)]) @ v)
    return E


def test_exact_marginal_matches_brute_force_and_inactive_placeholders_change_nothing():
    rng = np.random.default_rng(3)
    theta = rng.normal(size=16)
    lay = zl.build("k", [["o04", 49], ["o05", 41]], CAT)
    e, rows = zl.exact_marginal(_joint(theta, lay), lay, 0.7)
    names = [s for s, a in zip(lay["slots"], lay["active"]) if a]
    brute = [-_joint(theta, lay)(dict(zip(names, b))) / 0.7 for b in itertools.product((0, 1), repeat=len(names))]
    assert len(rows) == 2 ** 7 and math.isclose(e, -0.7 * sp.logsumexp(brute), rel_tol=1e-12)
    assert math.isclose(sum(p for _, p in rows), 1.0, abs_tol=1e-12)
    padded = {**lay, "slots": lay["slots"] + ["zX"], "active": lay["active"] + [False], "fixed": lay["fixed"] + [0]}
    padded["hash"] = zl.stable_hash({k: v for k, v in padded.items() if k != "hash"})
    e2, rows2 = zl.exact_marginal(_joint(theta, lay), padded, 0.7)
    assert e2 == e and [p for _, p in rows2] == [p for _, p in rows]                 # inactive slot: no state, no energy


def test_marginal_energy_gradient_by_finite_difference():
    lay = zl.build("k", [["o04", 49], ["o05", 41]], CAT)
    theta = np.random.default_rng(5).normal(size=16)
    f = lambda th: zl.exact_marginal(_joint(th, lay), lay, 1.0)[0]              # noqa: E731
    e, rows = zl.exact_marginal(_joint(theta, lay), lay, 1.0)
    names = [s for s, a in zip(lay["slots"], lay["active"]) if a]
    analytic = sum(p * z[names[0]] for z, p in rows)                            # dE_bar/dtheta_0 = E_p[z_0]
    numeric = (f(theta + np.eye(16)[0] * 1e-6) - f(theta - np.eye(16)[0] * 1e-6)) / 2e-6
    assert abs(analytic - numeric) < 1e-6
