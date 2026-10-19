"""G4D corrections (report 0011): episode-audit event contract, per-call relocation budget,
raw-proposal validation at public entry points, revalidated negative transfer, explicit
termination reasons, complete context identity and derived legacy omission pairs.
Target callbacks are stubs except where an archived evaluation is reproduced."""
import copy
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cases  # noqa: E402
import config as cf  # noqa: E402
import data  # noqa: E402
import effects as ef  # noqa: E402
import evaluate as ev  # noqa: E402
import geometry as ge  # noqa: E402
import legacy  # noqa: E402
import ordered as od  # noqa: E402
import sequences as sq  # noqa: E402
import skill as sk  # noqa: E402
import verify as vf  # noqa: E402
from scene import scene_from_dict  # noqa: E402

FX = json.loads((ROOT / "fixtures.json").read_text())["fixtures"]
G4A = ROOT / "runs/g4a_evidence_audit"


@pytest.fixture(scope="module")
def cfg():
    return cf.load_config(ROOT / "config.toml")


@pytest.fixture(scope="module")
def v2():
    return cf.load_config_v2(ROOT / "config_v2.toml")


@pytest.fixture(scope="module")
def robot(cfg):
    return ge.make_robot(cfg)


def _q(cfg, name, goal):
    s, _ = cases.build_scene(cfg, FX[name])
    return s, data.make_query(cfg, name, s, "t0", goal, {}, "SAFE_RETREAT", data.PROTOCOL_V2)


def stub(status=sk.UNRESOLVED):
    return lambda st, key: {"status": status, "reason": "STUB", "result": None,
                            "start": {"q": list(st.q), "gripper_gap_m": st.gap, "attachment": "free"}}


@pytest.fixture(scope="module")
def r2_episode(robot, cfg, v2):
    s, q = _q(cfg, "G35_R2_GOAL", 45)
    pool = sq.rank_sequences(s, q["learner"]["action"], [{"label": "a", "sequence": [["o03", 60]]}], cfg, v2)["ranked"]
    return s, q, pool, od.primary_v2(robot, cfg, q, s, pool, stub(), cf.robot_profile_hash(cfg))


# ------------------------------------------------------------------ 2.1 episode audit
def _fake(kinds):
    t = ev.Trace("x")
    for k in kinds:
        t.emit(k, "c", "h", certified=True, matches_commitment=True)
    return {"trace": t, "commit": None, "target": None, "achieved": None, "outcome": "X"}


@pytest.mark.parametrize("kinds", [["PROPOSE", "COMMIT", "ABORT", "TARGET_EVALUATE", "FINISH"],
                                   ["PROPOSE", "COMMIT", "COMMIT", "TARGET_EVALUATE", "FINISH"],
                                   ["PROPOSE", "TARGET_EVALUATE", "COMMIT", "FINISH"],
                                   ["PROPOSE", "COMMIT", "TARGET_EVALUATE", "TARGET_EVALUATE", "FINISH"],
                                   ["PROPOSE", "COMMIT", "ABORT", "TARGET_EVALUATE"]])
def test_illegal_event_histories_fail_the_audit(cfg, kinds):
    s, q = _q(cfg, "G35_R4_ACCESS", 28)
    a = od.episode_audit(_fake(kinds), ev.start(s, q), [], cfg)
    assert not a["protocol_compliant"] and a["decision"] == "FAIL"


def test_target_before_last_reobservation_fails(cfg, r2_episode):
    s, q, pool, out = r2_episode
    bad = copy.copy(out)
    t = ev.Trace("x")
    for e in out["trace"].events:                       # move TARGET_EVALUATE before REOBSERVE
        if e["kind"] != "TARGET_EVALUATE":
            t.events.append(e)
        if e["kind"] == "RELOCATE":
            t.events.append({**next(x for x in out["trace"].events if x["kind"] == "TARGET_EVALUATE")})
    bad["trace"] = t
    a = od.episode_audit(bad, ev.start(s, q), pool, cfg)
    assert not a["checks"]["target_after_all_relocations_and_reobservations"] and a["decision"] == "FAIL"


def test_valid_episodes_pass_and_tampered_or_missing_evidence_does_not(robot, cfg, v2, r2_episode):
    s, q, pool, out = r2_episode
    a = out["audit"]
    assert a["decision"] == "PASS" and a["protocol_compliant"] and a["target_calls"] == 1
    assert "target_trajectory_starts_at_invocation" not in a["checks"]          # stub returns no trajectory
    moved = {**out, "achieved": replace(out["achieved"], scene=replace(out["achieved"].scene, objects=tuple(
        replace(o, xy_m=(o.xy_m[0] + 0.004, o.xy_m[1]), cell=None) if o.id == "o01" else o for o in out["achieved"].scene.objects)))}
    m = od.episode_audit(moved, ev.start(s, q), pool, cfg)
    assert not m["checks"]["achieved_state_matches_commitment"] and m["decision"] == "FAIL"
    gone = {k: v for k, v in out.items() if k != "target_invocations"}
    assert od.episode_audit(gone, ev.start(s, q), pool, cfg)["decision"] == "UNKNOWN"     # missing evidence never passes
    s0, q0 = _q(cfg, "G35_R0_D1REF", 45)                                                 # valid empty repair
    pool0 = sq.rank_sequences(s0, q0["learner"]["action"], [], cfg, v2)["ranked"]
    e = od.primary_v2(robot, cfg, q0, s0, pool0, stub(sk.VERIFIED), "h")
    assert e["commit"]["order"] == [] and e["audit"]["decision"] == "PASS" and e["audit"]["target_calls"] == 1
    assert "RELOCATE" not in [x["kind"] for x in e["trace"].events]


def test_abort_and_no_witness_are_compliant_but_unsuccessful(robot, cfg, v2, r2_episode):
    s, q, pool, _ = r2_episode

    def deviate(k, st):
        objs = tuple(replace(o, xy_m=(o.xy_m[0] + 0.006, o.xy_m[1]), cell=None) if o.id == "o03" else o for o in st.scene.objects)
        return {"state": replace(st, scene=replace(st.scene, objects=objs)), "attachment": "free", "attached_id": None}
    calls = []
    ab = od.primary_v2(robot, cfg, q, s, pool, lambda st, k: calls.append(1), "h", executor=deviate)
    assert ab["outcome"] == "ABORTED" and not calls and ab["audit"]["protocol_compliant"] and ab["audit"]["target_calls"] == 0
    tight = copy.deepcopy(cfg)
    tight["repair2d"]["max_relocations"] = 0
    nw = od.primary_v2(robot, tight, q, s, pool, lambda st, k: calls.append(1), "h")
    assert nw["outcome"] == "NO_REPAIR_WITNESS_WITHIN_BUDGET" and nw["audit"]["protocol_compliant"] and not calls


# ------------------------------------------------------------------ 2.2 per-call relocation budget
def _fake_relocate(log, fail_at=None):
    def f(robot, cfg, state, oid, cell, key, q_goal=None):
        log.append(oid)
        if fail_at is not None and len(log) - 1 == fail_at:
            return sk.SkillResult(sk.UNRESOLVED, "STUB_FAIL"), None
        return sk.SkillResult(sk.VERIFIED, "STUB"), replace(state, moved=state.moved + (oid,))
    return f


def test_relocation_allowance_is_checked_before_every_call(cfg, monkeypatch):
    s, q = _q(cfg, "G35_R4_ACCESS", 28)
    c = copy.deepcopy(cfg)
    c["repair2d"]["max_relocations"] = 10
    seq = (("o01", 18), ("o00", 29), ("o02", 30))
    for used0, calls_expected, stop in ((9, 1, "RELOCATION_BUDGET"), (10, 0, "RELOCATION_BUDGET"), (7, 3, "WITNESS_FOUND")):
        log, used = [], {"plans": used0}
        monkeypatch.setattr(vf, "relocate", _fake_relocate(log))
        p = vf.plan_fixed_order(None, c, ev.start(s, q), seq, "k", used)
        assert (len(log), p["relocation_plans"], p["stop"]) == (calls_expected, calls_expected, stop)
        assert used["plans"] == used0 + calls_expected <= 10
        assert (p["witness"] is None) == (stop != "WITNESS_FOUND")
    assert len(p["attempts"][0].states) == 3
    log, used = [], {"plans": 9}
    near = vf.plan_fixed_order(None, c, ev.start(s, q), seq, "k", used)
    assert near["attempts"][0].states and near["witness"] is None              # partial prefix kept as diagnostic only
    log, used = [], {"plans": 10}
    e = vf.plan_fixed_order(None, c, ev.start(s, q), (), "k", used)
    assert e["witness"] is not None and e["relocation_plans"] == 0 and used["plans"] == 10      # empty needs no call
    log, used = [], {"plans": 0}
    monkeypatch.setattr(vf, "relocate", _fake_relocate(log, fail_at=1))
    f = vf.plan_fixed_order(None, c, ev.start(s, q), seq, "k", used)
    assert f["stop"] == "ACTION_1_UNRESOLVED" and used["plans"] == 2 and f["witness"] is None   # failed call charged


# ------------------------------------------------------------------ 2.3 raw proposals at public entry points
BAD_RAW = {"bool": [["o00", True]], "fraction": [["o00", 29.9]], "integral float": [["o00", 29.0]], "short": [["o00"]],
           "int id": [[1, 29]], "not a list": "o00>29", "duplicate": [["o00", 29], ["o00", 30]], "stay": [["o00", 28]],
           "target": [["t0", 29]], "cap": [["o00", 29], ["o01", 18], ["o02", 30], ["o03", 40]], "string cell": [["o00", "29"]]}


def test_raw_proposals_are_rejected_before_conversion_everywhere(robot, cfg, v2, monkeypatch):
    s, q = _q(cfg, "G35_R4_ACCESS", 28)
    act = q["learner"]["action"]
    pool = sq.rank_sequences(s, act, [{"label": k, "sequence": v} for k, v in BAD_RAW.items()], cfg, v2)
    assert {r["label"] for r in pool["rejected"]} == set(BAD_RAW) and not pool["ranked"]
    called = []
    monkeypatch.setattr(vf, "relocate", lambda *a, **k: called.append(1))
    for k, raw in BAD_RAW.items():
        with pytest.raises(ValueError):
            od.teach_sequence(robot, cfg, v2, q, s, raw, stub(), "x", "h")
    assert not called
    with pytest.raises(TypeError):
        sq.canonical([["o00", True]])
    with pytest.raises(ValueError):
        vf.plan_fixed_order(robot, cfg, ev.start(s, q), (("o00", 29.0),), "k", {"plans": 0})
    assert sq.parse_sequence(s, act, [["o01", 18], ["o00", 29]], 3) == ((("o01", 18), ("o00", 29)), [])


# ------------------------------------------------------------------ 2.4 revalidated negative transfer
def _neg(kind):
    plan, rows = json.loads((G4A / "g4a_plan.json").read_text()), json.loads((G4A / "candidate_labels.json").read_text())
    r = next(r for r in rows if r["first_pass"] == data.NEGATIVE and [c["kind"] for c in r["certificates"]] == [kind])
    return next(x for x in plan["queries"] if x["query_id"] == r["query_id"]), {o: d for o, d in r["signature"]}


@pytest.mark.parametrize("kind", ["GOAL_OVERLAP", "TARGET_PICK"])
def test_negative_transfer_reruns_the_checker_and_rejects_mismatches(robot, cfg, kind):
    q, cells = _neg(kind)
    ok = legacy.revalidate_negative(robot, cfg, q, cells, [kind])
    assert ok["v2_status"] == data.NEGATIVE and ok["certificates"][0]["new_checker_accepted"]
    base = {"observation_hash": q["hashes"]["observation"], "action_context_hash": q["hashes"]["action_context"],
            "assignment": [[o, d] for o, d in sorted(cells.items())]}
    for bad in ({**base, "observation_hash": "sha256:0"}, {**base, "action_context_hash": "sha256:0"},
                {**base, "assignment": [["o00", 63]]}):
        r = legacy.revalidate_negative(robot, cfg, q, cells, [kind], stamp=bad)
        assert r["v2_status"] == data.UNKNOWN and r["migration"] == "TRANSFER_REJECTED"
    home = {**q, "action": {k: v for k, v in q["action"].items() if k != "end_policy"}}
    r = legacy.revalidate_negative(robot, cfg, home, cells, [kind])
    assert r["v2_status"] == data.UNKNOWN and not r["scope_checks"]["end_policy"]
    assert legacy.revalidate_negative(robot, cfg, q, cells, ["PLANNER_EXHAUSTION"])["v2_status"] == data.UNKNOWN


# ------------------------------------------------------------------ 3 termination events and context identity
def test_completed_schedule_is_not_reported_as_a_search_limit(robot, cfg):
    """Archived g4a_r14 all-stay (report 0009: every pregrasp connector certified blocked,
    gray-band grasp rejections): historical reason PLANNER_BUDGET, explicit end event
    SCHEDULE_COMPLETED_NO_WITNESS; still UNRESOLVED."""
    q = next(x for x in json.loads((G4A / "g4a_plan.json").read_text())["queries"] if x["query_id"] == "g4a_r14")
    s = scene_from_dict(q["scene"])
    query = data.make_query(cfg, "g4a_r14", s, "t0", q["goal_cell"], {}, "SAFE_RETREAT")
    t = ev.evaluate_target(robot, cfg, ev.start(s, query), query["learner"]["action"], "g4a_r14/audit/0/target")
    assert t["status"] == sk.UNRESOLVED and t["reason"] == "PLANNER_BUDGET"
    assert t["termination"] == "SCHEDULE_COMPLETED_NO_WITNESS"
    assert od.normalized_reason(t["status"], t["termination"]).startswith("SCHEDULE_COMPLETED_NO_WITNESS")
    tiny = copy.deepcopy(cfg)
    tiny["planner2d"]["max_nodes"], tiny["skill2d"]["max_plan_failures"], tiny["skill2d"]["max_direct_pairs"] = 20, 1, 0
    s1, q1 = _q(cfg, "G35_R1_D1BLOCK", 45)
    r = sk.plan_skill(robot, s1, "t0", 45, tiny, "tiny", q_goal=None)
    assert r.termination == "SEARCH_LIMIT_PLAN_FAILURES" and r.reason == "PLANNER_BUDGET"
    assert od.normalized_reason(sk.VERIFIED, "WITNESS_RECHECKED", True) == "WITNESS+WALL_LIMIT_INVOLVED"
    assert od.normalized_reason(sk.INFEASIBLE, "PICK_SCREEN_EXHAUSTED") == "PICK_SCREEN_EXHAUSTED_CERTIFIED"


def test_context_identity_separates_scenes_and_robot_states(robot, cfg, v2):
    s, q = _q(cfg, "G35_R4_ACCESS", 28)
    s2 = ef.robot_start_substitution(robot, cfg, s, q["learner"]["action"], [0.5, 0.5, 0.5])["scene"]
    q2 = data.make_query(cfg, "G35_R4_ACCESS", s2, "t0", 28, {}, "SAFE_RETREAT", data.PROTOCOL_V2)
    seq = (("o01", 18), ("o00", 29))
    a, b = ef.omission_records(q, seq, {}, v2, "A"), ef.omission_records(q2, seq, {}, v2, "A")
    assert all(x["reference"]["context_hash"] != y["reference"]["context_hash"] for x, y in zip(a, b))
    assert ef.omission_records(q, seq, {}, v2, "B")[0]["alternative"]["context_hash"] != a[0]["alternative"]["context_hash"]
    pa = sq.rank_sequences(s, q["learner"]["action"], [{"label": "x", "sequence": seq}], cfg, v2)["ranked"][0]
    pb = sq.rank_sequences(s2, q2["learner"]["action"], [{"label": "x", "sequence": seq}], cfg, v2)["ranked"][0]
    assert pa["initial_context_hash"] != pb["initial_context_hash"]


# ------------------------------------------------------------------ 4 derived legacy omission pair (review example)
def test_g4a_r02_omission_example_is_derived_from_both_revalidated_sides(robot, cfg, v2):
    rv = legacy.revalidate(cfg, robot, G4A)
    om = legacy.omission_pairs(cfg, v2, rv, {"candidate_labels.json": "h"})
    p = next(x for x in om["pairs"] if x["query_id"] == "g4a_r02" and x["conditioning"] == [["o00", 41], ["o07", 42]]
             and x["objects"] == ["o00"])
    assert p["alternative"]["status"] == data.POSITIVE and p["reference"]["status"] == data.NEGATIVE
    assert p["label"] == {"delta": 1, "mask": True} and p["evidence_class"] == "DERIVED_LEGACY"
    assert p["alternative"]["evidence"][0] == "g4a_r02.audit2" and p["reference"]["evidence"][:2] == ["g4a_r02.audit9",
                                                                                                       "GOAL_OVERLAP"]
    assert p["reference"]["sequence"] == [["o07", 42]] and not rv["contradictions"]
