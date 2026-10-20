"""G4C-P0 plan checks (G4C plan-only contract §8): deterministic hashing, intent counts,
no label leakage, historical inputs unchanged, zero planner/target/teacher calls,
fail-closed budgets, mask/lineage/catalogue invariants with mutation rejection, coverage
semantics, and compatibility of every planned unit with the G4D runner's identity checks."""
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config as cf  # noqa: E402
import g4b_figures as g4bf  # noqa: E402
import g4c  # noqa: E402
import g4d_run  # noqa: E402
import geometry as ge  # noqa: E402


@pytest.fixture(scope="module")
def built():
    cfg, v2 = cf.load_config(ROOT / "config.toml"), cf.load_config_v2(ROOT / "config_v2.toml")
    robot = ge.make_robot(cfg)
    hist = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in
            ("runs/g4a_evidence_audit/g4a_plan.json", "runs/g4d_evidence/final_plan.json", "runs/g4d_evidence/ledger.json")}
    calls = g4bf._instrument()
    plan = json.loads(json.dumps(g4c.make_plan(cfg, v2, robot, ROOT)))
    return cfg, v2, robot, plan, calls, hist


def test_plan_is_deterministic_valid_and_planner_free(built):
    cfg, v2, robot, plan, calls, hist = built
    assert g4c.validate(plan) == [] and plan["status"] == "FROZEN_PENDING_BUDGET_AUTHORIZATION"
    again = json.loads(json.dumps(g4c.make_plan(cfg, v2, robot, ROOT)))
    assert again["plan_hash"] == plan["plan_hash"]
    assert calls and not any(calls.values()), calls                      # every loaded entry point counted 0 calls
    assert hist == {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in hist}


def test_intent_mixture_independence_and_ceilings(built):
    plan = built[3]
    fams = {}
    for v in plan["roots"].values():
        fams[v["family"]] = fams.get(v["family"], 0) + 1
    assert fams == {"J0": 6, "J1": 2, "J2": 2, "J3": 4, "J4": 2, "J7": 2, "J5J6": 1, "J9": 1} and len(plan["roots"]) == 20
    assert all("scene" in v for v in plan["roots"].values())                     # no CONSTRUCTION_UNAVAILABLE needed
    assert len(plan["ledger"]) >= 20 and all(l["accepted"] or l["rejection"] for l in plan["ledger"])
    for k, v in plan["roots"].items():
        Q, c = v["queries"], v["ceilings"]
        assert len([p for p in Q["pool"] if p["origin"] == "declared"]) <= c["sequences"]
        assert len(Q["scene_queries"]) <= c["scene_edits"] and len(Q["robot_starts"]) <= 2
        assert max(p["bc_layout"]["active_count"] for p in Q["pool"]) <= 8
        assert v["lineage"] == {"family_id": k, "split": "DEVELOPMENT"}
    j9 = next(v for v in plan["roots"].values() if v["family"] == "J9")
    assert len(j9["queries"]["pool"]) == 13                                       # exhaustive tiny domain


def test_masks_omissions_and_scene_edits(built):
    plan = built[3]
    for v in plan["roots"].values():
        for p in v["queries"]["pool"]:
            L, m = p["bc_layout"], len(p["sequence"])
            act = dict(zip(L["slots"], L["active"]))
            assert act["z0"] and act["zR"] == (m >= 1) and all(act[f"zO[{t}]"] == (m >= 2) for t in range(3))
            if p["origin"].startswith("omission_of:"):
                src = [x.split(">") for x in p["origin"].split(":", 1)[1].split(".")]
                full = [[o, int(c)] for o, c in src]
                assert [a for a in full if a in p["sequence"]] == p["sequence"]          # remaining order preserved
        for q in v["queries"]["scene_queries"]:
            assert q["changed_fields"]["robot_unchanged"] and set(q["changed_fields"]["changed_objects"]) <= set(q["edit"])
    j3 = [v for v in plan["roots"].values() if v["family"] == "J3"]
    assert all(sum(p["static_status"] == "INVALID" for p in v["queries"]["pool"]) == 1 for v in j3)   # deliberate negative


@pytest.mark.parametrize("mutation", ["mask", "leak", "dup_root", "lineage", "catalogue", "budget"])
def test_malformed_plans_are_rejected(built, mutation):
    plan = copy.deepcopy(built[3])
    k = next(k for k, v in plan["roots"].items() if v["family"] == "J4")
    if mutation == "mask":
        L = plan["roots"][k]["queries"]["pool"][0]["bc_layout"]                      # the empty repair
        L["active"][L["slots"].index("zR")] = True
    elif mutation == "leak":
        plan["roots"][k]["scene"]["objects"][0]["label"] = "VERIFIED_FEASIBLE"
    elif mutation == "dup_root":
        plan["roots"]["g4c_r00"]["seed"] = plan["roots"]["g4c_r01"]["seed"]
    elif mutation == "lineage":
        plan["roots"][k]["lineage"]["family_id"] = "g4c_r00"
    elif mutation == "catalogue":
        plan["roots"][k]["queries"]["catalogue"]["queries"] = ["singleton:A"]
    else:
        plan["budget"]["aggregate_cpu_s"] = 18000
    plan["plan_hash"] = cf.stable_hash({kk: vv for kk, vv in plan.items() if kk != "plan_hash"})   # re-hashed on purpose
    assert g4c.validate(plan), mutation
    tampered = copy.deepcopy(built[3])
    tampered["units"][5]["target_key"] = "g4c/tampered/target"
    assert "plan hash mismatch" in g4c.validate(tampered)


def test_budget_admission_fails_closed(built):
    plan = copy.deepcopy(built[3])
    ok, why = g4c.admit(plan)
    assert not ok and why.startswith("NOT_ADMITTED") and all(v is None for v in plan["budget"].values())
    plan["budget"] = dict(plan["budget_request"]["full"]["requested"])
    assert not g4c.admit(plan)[0]                                                 # requested numbers are not authorization
    plan["authorization"] = {"by": "test", "scope": "synthetic"}
    assert g4c.admit(plan)[0]
    assert plan["budget_request"]["status"] == "REQUESTED_NOT_AUTHORIZED"


def test_coverage_is_plan_only_without_evidence(built):
    plan = built[3]
    rows = g4c.coverage(plan)
    assert all(r["status"] == "NOT_RUN" and r["measured_roots"] is None for r in rows)
    assert {r["threshold"]: r["plan_capacity"] for r in rows}["bc_full_mini_pool_roots"] == "SUFFICIENT_IF_ALL_DECIDE"
    ev = {"g4c_r08": {"order_contrast"}, "g4c_r10": {"order_contrast"}}
    met = {r["threshold"]: r["status"] for r in g4c.coverage(plan, ev)}
    assert met["order_contrast_roots"] == "NOT_MET" and met["zero_move_roots"] == "NOT_MET"


def test_every_unit_passes_the_g4d_runner_identity_checks(built):
    cfg, v2, robot, plan, calls, _ = built
    for u in plan["units"]:
        scene, seq, query, key = g4d_run.unit_scene(cfg, robot, plan, u)
        assert key == u["target_key"].rsplit("/target", 1)[0] and seq == u.get("sequence", [])
    assert not any(calls.values())
