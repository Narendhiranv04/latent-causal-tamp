"""P6 frozen construction and plan: schedule, splits, strata, annulus rule, caps, V3 layouts (static; no teacher)."""
import collections
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config as cf  # noqa: E402
import geometry as ge  # noqa: E402
import operational_teacher as ot  # noqa: E402
import p6_run as pr  # noqa: E402
import p6_scenes as p6  # noqa: E402
import zlayout_r4 as z4  # noqa: E402


def test_schedule_is_predeclared_and_balanced():
    assert len(p6.ROOTS) == 16 and len({r["seed"] for r in p6.ROOTS}) == 16
    for b in range(1, 5):
        assert sorted(r["family"] for r in p6.ROOTS if r["batch"] == b) == p6.FAMS
    for f in p6.FAMS:
        assert collections.Counter(r["split"] for r in p6.ROOTS if r["family"] == f) == {"train": 2, "validation": 1, "holdout": 1}
    assert len({r["stratum"] for r in p6.ROOTS}) == 4 and len(p6.STRATA) >= 4


@pytest.fixture(scope="module")
def built():
    cfg = cf.load_config(ROOT / "config.toml")
    robot = ge.make_robot(cfg)
    roots, ledger, info = p6.construct(cfg, robot, set())
    pol = ot.load_policy(ROOT / "teacher_opneg.toml")
    return cfg, robot, roots, ledger, info, p6.plan(cfg, robot, pol, roots)


def test_construction_respects_intent_annulus_and_uniqueness(built):
    cfg, robot, roots, ledger, info, plan = built
    scr = p6.Screens(cfg, robot)
    assert info["cpu_s"] < p6.CONSTRUCTION_CPU_S and len(roots) == 16
    assert len({(r["target_cell"], r["goal_cell"]) for r in roots}) == 16
    for r in roots:
        assert all(p["ok"] for p in r["predicates"])
        cells = [o.cell for o in r["scene"].objects] + [r["goal_cell"]] + [c for v in r["dest"].values() for c in v]
        assert all(c in scr.valid for c in cells)                                     # outside the link-0 annulus
        assert list(r["scene"].robot.q_rad) == p6.STRATA[r["stratum"]]
        assert r["ref_scene"].robot.q_rad == r["scene"].robot.q_rad


def test_plan_caps_layouts_and_query_identity(built):
    cfg, robot, roots, ledger, info, plan = built
    assert len(plan["queries"]) <= pr.CAPS["max_queries"] and len(plan["units"]) == 3 * len(plan["queries"]) <= pr.CAPS["max_seed_attempts"]
    per = collections.Counter(q["lineage"] for q in plan["queries"])
    assert max(per.values()) <= 24 and len(per) == 16
    assert len({q["query"] for q in plan["queries"]}) == len(plan["queries"])
    for k, r in plan["roots"].items():
        if r["variant"] != "obstructed":
            continue
        for p in r["queries"]["pool"]:
            lay = p["z_layout"]
            z4.verify(lay)
            assert p["canonical"] and all(not s.startswith("zS[nuisance") for s in lay["query"])
            if p["role"] in ("main", "original", "single", "swap"):
                assert set(lay["query"].values()) <= {q["query"] for q in plan["queries"] if q["lineage"] == k}
        if r["family"] == "F3":
            main = next(p for p in r["queries"]["pool"] if p["role"] == "main")
            assert len(main["sequence"]) == 4 and main["z_layout"]["active_count"] == 9
    q = pr.order(plan, roots[0]["root"])
    assert q[0]["role"] == "reference" and q[1]["role"] == "main"


def test_censoring_rule_and_kind_kappa():
    assert pr.censored_twice([{"stop": "CPU_CENSORED"}, {"stop": "CPU_CENSORED"}])
    assert not pr.censored_twice([{"stop": "CPU_CENSORED"}, {"stop": "COMPLETED"}, {"stop": "CPU_CENSORED"}])
    root = {"family": "F2", "queries": {"scene_queries": [{"kind": "A", "edit": {"o00": 5}}, {"kind": "B", "edit": {"o01": 6}},
                                                          {"kind": "A+B", "edit": {"o00": 5, "o01": 6}}]}}
    rec = lambda y: {"binary_training_label": y, "label_source": "WITNESS" if y else "CERTIFICATE"}  # noqa: E731
    records = {"seq:k:empty": rec(0), "scene:k:o00>5": rec(0), "scene:k:o01>6": rec(0), "scene:k:o00>5.o01>6": rec(1)}
    assert pr.kappas({"roots": {"k": root}}, records)[0]["kappa"] == 1
    json.dumps(pr.CAPS)
