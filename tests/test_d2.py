"""G4C-D2-P0 precheck checks (contract §6.3). Static geometry and replay of ARCHIVED records
only: no planner, IK search, target evaluation or teacher call. The central guard: a
collision with the recorded nominal witness is never a task-infeasibility label."""
import copy
import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config as cf  # noqa: E402
import d2  # noqa: E402
import data  # noqa: E402
import effects as ef  # noqa: E402
import g4b_figures as g4bf  # noqa: E402
import g4c  # noqa: E402
import geometry as ge  # noqa: E402
import motion as mo  # noqa: E402
import sequences as sq  # noqa: E402

FROZEN = ("runs/g4c_preflight/plan.json", "runs/g4c_pilot/pilot_plan.json", "runs/g4c_pilot/pilot_result.json",
          "runs/g4d_evidence/final_plan.json", "config.toml", "config_v2.toml")


@pytest.fixture(scope="module")
def r1():
    calls = g4bf._instrument()
    before = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FROZEN}
    cfg = cf.load_config(ROOT / "config.toml")
    robot = ge.make_robot(cfg)
    b = d2.load_base(d2.BASES[2], ROOT)
    at = d2.insertion_attempts(robot, cfg, b)
    ch = d2.choose_blockers(at)
    vs = d2.nested_variants(robot, cfg, b, ch)
    return cfg, robot, b, at, ch, vs, calls, before


def test_archived_witness_replays_and_tampering_is_rejected(r1):
    cfg, robot, b = r1[:3]
    rep = d2.replay_base(robot, cfg, b)
    assert rep["status"] == "BASE_WITNESS_REPLAYED" and all(rep["checks"].values())
    bad = copy.deepcopy(b)
    bad["arrays"]["q"] = bad["arrays"]["q"] + np.array([0.0, 0.0, 1e-4])
    with pytest.raises(ValueError):                                   # record check refuses an inconsistent attachment
        d2.replay_base(robot, cfg, bad)
    sibling, other = d2.load_base(d2.BASES[1], ROOT), d2.load_base(d2.BASES[0], ROOT)
    assert sibling["provenance"]["witness_hash"] != b["provenance"]["witness_hash"]
    assert sibling["family_id"] == b["family_id"]                    # R0/R1 share the G2_D1 lineage: same split family
    assert other["family_id"] != b["family_id"] and d2.family_split(sibling["family_id"]) == d2.family_split(b["family_id"])


def test_construction_is_deterministic(r1):
    cfg, robot, b, at, ch, vs = r1[:6]
    at2 = d2.insertion_attempts(robot, cfg, d2.load_base(d2.BASES[2], ROOT))
    assert at2 == at and d2.choose_blockers(at2) == ch
    assert [v.get("scene_hash") for v in d2.nested_variants(robot, cfg, b, ch)] == [v.get("scene_hash") for v in vs]


def test_insertions_are_legal_distinct_and_never_clone(r1):
    cfg, robot, b, at = r1[:4]
    occ = {o.cell for o in b["scene"].objects}
    d, e, _ = d2._tol(cfg)
    for a in at:
        if not a["accepted"]:
            continue
        assert a["cell"] not in occ and a["target_task_status"] == "NOT_RUN"
        s = d2.with_obstacles(b["scene"], [a["cell"]])
        assert len(s.objects) == len(b["scene"].objects) + 1 and len({o.id for o in s.objects}) == len(s.objects)
        assert s.get("t0") == b["scene"].get("t0") and s.robot == b["scene"].robot
        assert ge.Checker(robot, ge.make_world(s), d, e).status_at(np.asarray(s.robot.q_rad), s.robot.gripper_gap_m).status \
            == ge.CLEAR
    assert any(not a["accepted"] and a["reason"].startswith("occupied") for a in at)


def test_nominal_diagnostic_uses_the_full_robot_not_only_the_target_path(r1):
    cfg, robot, b, at = r1[:4]
    a = b["arrays"]
    tp = np.array([mo.target_xy(robot, a, ph, q, b["scene"].get("t0").xy_m) for q, _, ph in mo.samples(a, 400)])
    link = [x for x in at if x["accepted"] and x["role"] in ("arm_link_sweep_blocker", "grasp_access_blocker")]
    far = [x for x in link if min(np.hypot(*(tp - b["scene"].lattice.center(x["cell"])).T)) > 0.06]
    assert far, "some blocker is hit only by robot bodies, far from the carried-target path"
    assert any(x["accepted"] and x["role"] == "transport_path" for x in at)      # carried-target collisions also detected
    for x in far:
        assert x["first_interruption"]["pair"].split("|")[0] != "held"
    clear = next(x for x in at if x["accepted"] and x["blocks_nominal_witness"] == "NO")
    diag = d2.nominal_diagnostic(robot, cfg, d2.with_obstacles(b["scene"], [clear["cell"]]), a)
    assert diag["blocks_nominal_witness"] == "NO" and not diag["unresolved_segments"]


def test_nominal_obstruction_is_never_a_feasibility_label(r1):
    vs = r1[5]
    assert d2.root_release_label(True, None, None) == "NOT_RUN"
    assert d2.root_release_label(True, False, False) == "UNKNOWN"                  # blocked path + failed search != NEG
    assert d2.root_release_label(True, True, False) == "REROUTABLE_POSITIVE"       # abstract alternative-path control
    assert d2.root_release_label(False, True, False) == "POSITIVE" and d2.root_release_label(True, False, True) == "NEGATIVE"
    assert d2.root_release_label(True, True, True) == "CONTRADICTION"
    for v in vs:
        assert v.get("target_task_status", "NOT_RUN") == "NOT_RUN"
        assert v["status"] in ("PRECHECK_STATIC", "CONSTRUCTION_UNAVAILABLE")
        assert "label" not in v and v.get("nominal", {}).get("target_task_status", "NOT_RUN") == "NOT_RUN"


def test_nested_variants_preserve_ids_robot_goal_and_earlier_obstacles(r1):
    vs = {v["variant"]: v for v in r1[5] if v["status"] == "PRECHECK_STATIC"}
    base = r1[2]["scene"]
    A, AB = vs["+A"], vs["+A+B"]
    assert A["added"]["A"] == AB["added"]["A"] and AB["scene"].get(A["added"]["A"]["id"]).cell == A["added"]["A"]["cell"]
    for v in vs.values():
        assert v["scene"].robot == base.robot and v["goal_cell"] == r1[2]["goal_cell"]
        assert {o.id: o for o in base.objects}.items() <= {o.id: o for o in v["scene"].objects}.items()
    assert vs["+A+S"]["added"]["S"]["role"] == "staging_slot_occupant"


def test_queries_scene_edits_and_omissions(r1):
    cfg, robot = r1[0], r1[1]
    vs = {v["variant"]: v for v in r1[5] if v["status"] == "PRECHECK_STATIC"}
    v = vs["+A+B+C"]
    Q = d2.variant_queries(robot, cfg, v)
    for p in Q["pool"]:
        assert p["status"] == "NOT_RUN" and p["bc_layout"] == g4c.layout(p["sequence"], Q["catalogue"])
        assert p["bc_layout"]["active_count"] <= 8 and len({o for o, _ in p["sequence"]}) == len(p["sequence"])
        if p["origin"].startswith("omission_of:"):
            full = [[o, int(c)] for o, c in (x.split(">") for x in p["origin"].split(":", 1)[1].split("."))]
            assert [x for x in full if x in p["sequence"]] == p["sequence"]
            omitted = [o for o, c in full if [o, c] not in p["sequence"]]
            assert ef.stays_at_initial(v["scene"], [tuple(x) for x in full], omitted)
    pairs = [tuple(map(tuple, p["sequence"])) for p in Q["pool"] if len(p["sequence"]) == 2 and p["origin"] == "declared"]
    rev = [x for x in pairs if x[::-1] in pairs]
    assert rev and all(sq.ordered_signature(v["scene"], x) != sq.ordered_signature(v["scene"], x[::-1]) for x in rev)
    act = data.make_query(cfg, "d2", v["scene"], "t0", v["goal_cell"], {}, "SAFE_RETREAT", data.PROTOCOL_V2)["learner"]["action"]
    for q in Q["scene_queries"]:
        sub = ef.pose_substitution(robot, cfg, v["scene"], act, q["edit"])
        assert sub["changed_fields"]["robot_unchanged"] and sub["scene"].robot == v["scene"].robot
    o = Q["participants"][0]
    clash = ef.pose_substitution(robot, cfg, v["scene"], act, {o: v["scene"].get(Q["participants"][1]).cell})
    assert not clash["eligible"]                                                  # overlapping edit rejected, not negative
    S = d2.variant_queries(robot, cfg, vs["+A+S"])
    P = vs["+A+S"]["added"]["S"]["cell"]
    a_ = vs["+A+S"]["added"]["A"]["id"]
    assert [[a_, P]] in [p["sequence"] for p in S["pool"]] and any(len(p["sequence"]) == 2 and p["sequence"][0] == [a_, P]
                                                                    for p in S["pool"])


def test_release_rules_bc_pools_and_family_splits(r1):
    assert d2.pool_release({"empty": "POSITIVE", "r1": "NEGATIVE"}, ["empty", "r1"]) == "DECIDED_COMPLETE"
    assert d2.pool_release({"empty": "POSITIVE", "r1": "UNKNOWN"}, ["empty", "r1"]) == "PARTIAL_OBSERVATION"
    assert d2.pool_release({"empty": "POSITIVE"}, ["empty", "r1"]).startswith("INVALID")    # no silent drop
    assert not d2.substantive_pool({"empty": "POSITIVE"}) and not d2.substantive_pool({"empty": "NEGATIVE", "r1": "POSITIVE"})
    assert d2.substantive_pool({"empty": "NEGATIVE", "r1": "POSITIVE", "r2": "NEGATIVE"})
    assert d2.substantive_pool({"r1": "POSITIVE", "r2": "POSITIVE"}) and not d2.substantive_pool({"r1": "NEGATIVE", "r2": "NEGATIVE"})
    fid = r1[2]["family_id"]
    assert len({d2.family_split(fid) for _ in r1[5]}) == 1                      # every descendant inherits the family split
    assert {d2.family_split(f"fam{i}") for i in range(60)} == {"train", "validation", "test"}


def test_privileged_construction_fields_never_reach_learner_tensors(r1):
    cfg = r1[0]
    v = next(x for x in r1[5] if x["variant"] == "+A+B")
    q = data.make_query(cfg, "d2", v["scene"], "t0", v["goal_cell"], {}, "SAFE_RETREAT", data.PROTOCOL_V2)
    anchor = data.appearance_anchor(q, 64)
    t0 = data.learner_tensors_v2(q, cfg, anchor)
    poisoned = {**q, "oracle_only": {"base_witness": r1[2]["arrays"]["q"].tolist(), "nominal_sweep": v["nominal"],
                                     "family_id": v["family_id"], "construction_role": "grasp_access_blocker", "seed": 7}}
    t1 = data.learner_tensors_v2(poisoned, cfg, anchor)
    assert all(np.array_equal(t0[k], t1[k]) for k in t0)
    qb = data.make_query(cfg, "d2", r1[2]["scene"], "t0", v["goal_cell"], {}, "SAFE_RETREAT", data.PROTOCOL_V2)
    tb = data.learner_tensors_v2(qb, cfg, data.appearance_anchor(qb, 64))
    assert tb["object_xy"].shape != t0["object_xy"].shape                       # the real obstructed scene is what the learner sees


def test_generator_has_no_teacher_path_and_made_no_calls(r1):
    calls, before = r1[6], r1[7]
    assert not any(calls.values())
    code = ("import sys; sys.path.insert(0, %r); import d2; print(sorted(m for m in ('verify', 'evaluate', 'ordered', "
            "'teacher', 'g4d_run', 'g4c_pilot', 'certificates') if m in sys.modules))")
    out = subprocess.run([sys.executable, "-c", code % str(ROOT)], capture_output=True, text=True, check=True).stdout
    assert out.strip() == "[]"
    assert before == {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FROZEN}
