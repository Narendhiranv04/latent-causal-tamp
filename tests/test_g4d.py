"""G4D migration checks (Guide v1.8 §9, §16): V2 overlay, canonical sequences, prefixes,
omission vs deletion, anchored counterfactual inputs, scoped labels and effect masks,
order-scoped certificates, fixed-order verification, first-witness cost accounting and
the one-shot V2 boundary. Target callbacks are stubs: these are software checks, not
G4D evidence."""
import copy
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cases  # noqa: E402
import certificates as cert  # noqa: E402
import config as cf  # noqa: E402
import data  # noqa: E402
import effects as ef  # noqa: E402
import evaluate as ev  # noqa: E402
import geometry as ge  # noqa: E402
import ordered as od  # noqa: E402
import sequences as sq  # noqa: E402
import skill as sk  # noqa: E402
import verify as vf  # noqa: E402
from scene import scene_hash  # noqa: E402

FX = json.loads((ROOT / "fixtures.json").read_text())["fixtures"]
BAD, GOOD = (("o00", 29), ("o01", 18)), (("o01", 18), ("o00", 29))     # R4: o01 blocks o00's grasp


@pytest.fixture(scope="module")
def cfg():
    return cf.load_config(ROOT / "config.toml")


@pytest.fixture(scope="module")
def v2():
    return cf.load_config_v2(ROOT / "config_v2.toml")


@pytest.fixture(scope="module")
def robot(cfg):
    return ge.make_robot(cfg)


@pytest.fixture(scope="module")
def r4(cfg):
    s, _ = cases.build_scene(cfg, FX["G35_R4_ACCESS"])
    return s, data.make_query(cfg, "g4d_r4", s, "t0", 28, {}, "SAFE_RETREAT", data.PROTOCOL_V2)


@pytest.fixture(scope="module")
def good_plan(robot, cfg, r4):
    s, q = r4
    return vf.plan_fixed_order(robot, cfg, ev.start(s, q), GOOD, "g4d/test/good", {"plans": 0})


def test_v2_overlay_is_strict_and_leaves_every_v1_hash(cfg, v2):
    archived = json.loads((ROOT / "runs/g4a_evidence_audit/config.json").read_text())["config_hash"]
    assert cf.config_hash(cfg) == archived                         # V1 guards and archived plans unaffected
    raw = {s: dict(v) for s, v in v2.items()}
    for sec, key, val in (("protocol", "executor_may_reorder", True), ("protocol", "max_primary_target_evaluations", 2),
                          ("protocol", "target_end_policy", "HOME_REQUIRED"), ("proposal", "rank", ["move_count"]),
                          ("protocol", "target_feedback_to_selection", True), ("proposal", "source", "LEARNED")):
        bad = copy.deepcopy(raw)
        bad[sec][key] = val
        with pytest.raises(cf.ConfigError):
            cf.validate_v2(bad)
    with pytest.raises(cf.ConfigError):
        cf.validate_v2({**copy.deepcopy(raw), "sampler": {"chains": 8}})
    q = data.make_query(cfg, "x", data.initial_scene(_r2q(cfg)[1]), "t0", 45, {}, "SAFE_RETREAT", data.PROTOCOL_V2)
    v1 = data.make_query(cfg, "x", data.initial_scene(_r2q(cfg)[1]), "t0", 45, {}, "SAFE_RETREAT")
    assert q["hashes"] == v1["hashes"] and q["protocol"] != v1["protocol"] and q["schema_version"] == 1
    with pytest.raises(ValueError):
        data.make_query(cfg, "x", data.initial_scene(v1), "t0", 45, {}, None, data.PROTOCOL_V2)


def _r2q(cfg):
    s, _ = cases.build_scene(cfg, FX["G35_R2_GOAL"])
    return s, data.make_query(cfg, "g4d_r2", s, "t0", 45, {}, "SAFE_RETREAT", data.PROTOCOL_V2)


def test_canonical_sequence_rejects_duplicates_stays_targets_and_cap(r4, v2):
    s, q = r4
    act, cap = q["learner"]["action"], v2["proposal"]["move_cap"]
    assert sq.validate_sequence(s, act, (), cap) == [] and sq.validate_sequence(s, act, GOOD, cap) == []
    bad = {"duplicate": (("o00", 29), ("o00", 30)), "stay": (("o00", 28),), "target": (("t0", 29),),
           "unknown": (("o00", 99),), "onto target": (("o00", 20),), "ghost id": (("o77", 29),),
           "off-grid": (("o00", [0.1, 0.1]),), "bool": (("o00", True),),
           "cap": (("o00", 29), ("o01", 18), ("o02", 30), ("o03", 40))}
    for name, seq in bad.items():
        assert sq.validate_sequence(s, act, seq, cap), name
    assert sq.assignment(GOOD) == sq.assignment(BAD) == {"o00": 29, "o01": 18}       # derived, order-free
    assert sq.ordered_signature(s, GOOD) != sq.ordered_signature(s, BAD)              # orders stay distinct
    assert sq.canonical(GOOD) == GOOD and [a[0] for a in sq.canonical(BAD)] == ["o00", "o01"]   # never re-sorted


def test_frozen_pool_dedups_physically_and_keeps_empty_unique(cfg, v2, r4):
    s, q = r4
    props = [{"label": "a", "sequence": GOOD}, {"label": "a again", "sequence": [list(x) for x in GOOD]},
             {"label": "b", "sequence": BAD}, {"label": "empty again", "sequence": []}]
    pool = sq.rank_sequences(s, q["learner"]["action"], props, cfg, v2)
    assert {r["label"] for r in pool["rejected"]} == {"a again", "empty again"}
    assert sorted(r["label"] for r in pool["ranked"]) == ["a", "b"]                  # both orders, one entry each
    assert [r["label"] for r in pool["screened_out"]] == ["empty"]                      # goal provably occupied
    assert all(r["predicted_joint_travel"] is None and r["feasibility_energy"] is None for r in pool["ranked"])
    assert pool["pool_hash"] == sq.rank_sequences(s, q["learner"]["action"], props, cfg, v2)["pool_hash"]


def test_prefix_omission_and_deletion_are_different_operations(r4):
    s, _ = r4
    pre = sq.prefix_scenes(s, GOOD)
    assert len(pre) == 3 and all({o.id for o in p.objects} == {o.id for o in s.objects} for p in pre)   # no clones/deletes
    assert pre[0].get("o01").cell == 27 and pre[1].get("o01").cell == 18 and pre[1].get("o00").cell == 28
    assert pre[2].get("o00").cell == 29 and pre[2].get("o02").cell == s.get("o02").cell
    assert scene_hash(pre[0]) == scene_hash(s)
    for omitted in (["o01"], ["o00"], ["o00", "o01"]):
        assert ef.stays_at_initial(s, GOOD, omitted)
    assert sq.omit(GOOD, [0]) == (("o00", 29),) and sq.omit(((1, 2), (3, 4), (5, 6)), [1]) == ((1, 2), (5, 6))
    d = ef.deletion_diagnostic(s, ["o01"])
    assert d["scope"] == "DIAGNOSTIC_ONLY" and d["label_use"] == "NONE" and d["changed_fields"]["removed"] == ["o01"]


def test_counterfactual_inputs_keep_the_appearance_anchor_and_robot(cfg, r4):
    s, q = r4
    anchor = data.appearance_anchor(q, 64)
    base = data.learner_tensors_v2(q, cfg, anchor)
    cf_ = data.counterfactual_tensors(base, q, {"o00": s.lattice.center(29)})
    k = [o["id"] for o in q["learner"]["scene"]["objects"]].index("o00")
    changed = [key for key in base if not np.array_equal(base[key], cf_[key])]
    assert changed == ["object_xy"] and np.flatnonzero((base["object_xy"] != cf_["object_xy"]).any(1)).tolist() == [k]
    assert cf_["appearance_anchor"] == anchor["hash"] and np.array_equal(cf_["instance"], anchor["instance"])
    assert base["robot_profile"].shape == (16,) and base["robot_fk_joints"].shape == (4, 2)
    other = data.make_query(cfg, "o", ef.pose_substitution(ge.make_robot(cfg), cfg, s, q["learner"]["action"],
                                                            {"o00": 29})["scene"], "t0", 28, {}, "SAFE_RETREAT")
    with pytest.raises(ValueError):                                 # a re-rendered counterfactual is not the anchor
        data.learner_tensors_v2(q, cfg, data.appearance_anchor(other, 64))
    steps = data.prefix_tensors(base, q, s, GOOD)
    assert [x["selected_slot"] for x in steps][:2] == [k + 1, k] and len(steps) == 3
    assert np.array_equal(steps[0]["prefix_object_xy"], base["object_xy"])
    assert np.allclose(steps[2]["prefix_object_xy"][k], s.lattice.center(29))


def test_scene_substitution_holds_the_robot_and_never_makes_an_ineligible_negative(robot, cfg, r4):
    s, q = r4
    act = q["learner"]["action"]
    ok = ef.pose_substitution(robot, cfg, s, act, {"o00": 29})
    assert ok["eligible"] and ok["changed_fields"]["changed_objects"] == {"o00": ["cell", "xy_m"]}
    assert ok["changed_fields"]["robot_unchanged"] and not ok["changed_fields"]["other_fields_changed"]
    bad = ef.pose_substitution(robot, cfg, s, act, {"o00": 27})                       # onto o01: penetrating
    assert not bad["eligible"] and bad["reasons"]
    rec = ef.effect_record(ef.SCENE, ["o00"], bad["changes"], {"context_hash": "a", "status": data.NEGATIVE},
                           {"context_hash": "b", "status": data.POSITIVE}, bad["eligible"], "anchor", bad["fixed_fields"])
    assert rec["label"] == {"delta": None, "mask": False} and rec["necessary_cause"] == "UNESTABLISHED"
    rs = ef.robot_start_substitution(robot, cfg, s, act, [0.5, 0.5, 0.5])
    assert rs["eligible"] and not rs["changed_fields"]["changed_objects"] and not rs["changed_fields"]["robot_unchanged"]
    assert not ef.robot_start_substitution(robot, cfg, s, act, [4.0, 0.0, 0.0])["eligible"]       # outside limits


def test_effect_labels_and_scoped_aggregation_mask_unknowns(v2, r4):
    P, N, U = data.POSITIVE, data.NEGATIVE, data.UNKNOWN
    assert data.effect_label(N, P) == {"delta": 1, "mask": True} and data.effect_label(P, P)["delta"] == 0
    assert data.effect_label(U, P) == data.effect_label(P, U) == {"delta": None, "mask": False}
    with pytest.raises(ValueError):
        data.effect_label(data.CONTRADICTION, P)
    w = {"kind": "complete_witness", "scope": data.ORDER, "source": "t"}
    c = lambda s: {"kind": "certificate", "validated": True, "certificate": "X", "scope": s, "source": "t"}  # noqa: E731
    fail = {"kind": "order_attempt", "scope": data.TRAJECTORY, "status": "UNRESOLVED", "source": "t"}
    assert data.ordered_aggregate([fail])["label"] == U and data.ordered_aggregate([fail])["ignored_out_of_scope"] == 1
    assert data.ordered_aggregate([c(data.TRAJECTORY)])["label"] == U
    assert data.ordered_aggregate([c(data.ASSIGNMENT)])["label"] == N and data.ordered_aggregate([c(data.ORDER)])["label"] == N
    assert data.ordered_aggregate([w, fail])["label"] == P and data.ordered_aggregate([w, c(data.ORDER)])["label"] == data.CONTRADICTION
    st = {GOOD: P, (("o00", 29),): N}                                    # (o01,18) alone and empty: unknown here
    recs = ef.omission_records(r4[1], GOOD, st, v2, "anchor")
    assert [r["objects"] for r in recs] == [["o01"], ["o00"], ["o00", "o01"]]
    assert [r["label"]["delta"] for r in recs] == [1, None, None] and all(r["kind"] == ef.OMISSION for r in recs)


def test_order_first_action_certificate_covers_only_its_own_order(robot, cfg, r4):
    s, q = r4
    bad = od.certificates_for(robot, cfg, s, q["learner"], BAD)
    assert [(c["kind"], c["scope"], c["checker_accepted"]) for c in bad] == [("ORDER_FIRST_ACTION", "ORDER", True)]
    assert od.certificates_for(robot, cfg, s, q["learner"], GOOD) == []               # same endpoints, other order
    rec = {k: v for k, v in bad[0].items() if k not in ("scope", "checker_accepted", "checker_reasons")}
    cells = sq.assignment(BAD)
    for broken in ({**rec, "sequence": [list(a) for a in GOOD]}, {**rec, "candidates": 10}, {**rec, "stage": "CARRY"},
                   {**rec, "sequence": [["o00", 29], ["o00", 18]]}):
        assert not cert.check(robot, s, q["learner"], cells, broken, cfg)[0]
    assert cert.CERTIFICATE_SCOPE["ORDER_FIRST_ACTION"] == "ORDER" and cert.CERTIFICATE_SCOPE["GOAL_OVERLAP"] == "ASSIGNMENT"


def test_fixed_order_verifier_follows_the_order_and_costs_the_first_witness(robot, cfg, v2, r4, good_plan):
    s, q = r4
    s0 = ev.start(s, q)
    bad = vf.plan_fixed_order(robot, cfg, s0, BAD, "g4d/test/bad", {"plans": 0})
    assert bad["witness"] is None and len(bad["attempts"]) == 1 and bad["attempts"][0].order == BAD
    assert bad["stop"] == "ACTION_0_UNRESOLVED" and bad["order_scope"] == "THIS_ORDER_ONLY"
    w = good_plan["witness"]
    assert w is not None and w.order == GOOD and [st.moved for st in w.states] == [("o01",), ("o01", "o00")]
    c = od.cost_record(robot, v2, s0, w, cf.robot_profile_hash(cfg))
    assert c["label_available"] and c["J"] > 0 and abs(c["J"] - sum(c["per_record"])) < 1e-12
    assert abs(sum(c["per_phase"].values()) - c["J"]) < 1e-9 and c["start_q"] == list(s0.q)
    assert set(c["per_phase"]) >= {"pregrasp", "approach", "carry", "retreat"} and "return_home" not in c["per_phase"]
    e = vf.plan_fixed_order(robot, cfg, s0, (), "g4d/test/empty", {"plans": 0})
    assert od.cost_record(robot, v2, s0, e["witness"], "h")["J"] == 0.0                   # exactly zero
    assert not od.cost_record(robot, v2, s0, None, "h")["label_available"]
    with pytest.raises(ValueError):
        vf.plan_fixed_order(robot, cfg, s0, (("o00", 29), ("o00", 30)), "x", {"plans": 0})


def test_joint_travel_accounting_continuity_and_wrap(robot):
    a = {"q": np.array([[0, 0, 0], [0.5, 0, 0], [0.5, -0.25, 0]]), "gap": np.array([0.07, 0.07, 0.05]),
         "phase": np.array(["pregrasp", "close_attach"])}
    b = {"q": np.array([[0.5, -0.25, 0], [0.5, -0.25, 1.0]]), "gap": np.array([0.05, 0.07]), "phase": np.array(["carry"])}
    jt = od.joint_travel(robot, [a, b])
    lim = np.array([hi - lo for lo, hi in robot.limits])
    assert jt["available"] and abs(jt["J"] - (0.5 / lim[0] + 0.25 / lim[1] + 1.0 / lim[2])) < 1e-12
    jump = {**b, "q": b["q"] + np.array([0.01, 0, 0])}
    assert not od.joint_travel(robot, [a, jump])["available"]                         # discontinuous transition
    assert not od.joint_travel(robot, [a, {**b, "gap": np.array([0.07, 0.07])}])["available"]
    long = {"q": np.array([[3.1, 0, 0], [-3.1, 0, 0]]), "gap": np.array([0.07, 0.07]), "phase": np.array(["carry"])}
    assert abs(od.joint_travel(robot, [long])["J"] - 6.2 / lim[0]) < 1e-12           # real joint-linear travel, no shortcut
    out = {**long, "q": np.array([[3.1, 0, 0], [3.3, 0, 0]])}
    assert not od.joint_travel(robot, [out])["available"]                             # outside limits: not established


def test_primary_v2_commits_the_proposed_order_and_calls_the_target_once(robot, cfg, v2, r4, good_plan, monkeypatch):
    s, q = r4
    pool = sq.rank_sequences(s, q["learner"]["action"], [{"label": "bad", "sequence": BAD},
                                                         {"label": "good", "sequence": GOOD}], cfg, v2)["ranked"]
    pool.sort(key=lambda r: r["label"])                      # bad first: relocation fails before any commitment
    calls = []
    stub = lambda st, key: calls.append(st) or {"status": sk.UNRESOLVED, "reason": "STUB", "result": None}  # noqa: E731
    real = vf.plan_fixed_order
    monkeypatch.setattr(vf, "plan_fixed_order", lambda r, c, s0, seq, key, used: good_plan if tuple(seq) == GOOD
                        else real(r, c, s0, seq, key, used))
    out = od.primary_v2(robot, cfg, q, s, pool, stub, cf.robot_profile_hash(cfg))
    a = out["audit"]
    assert out["commit"]["rank"] == 1 and out["commit"]["order"] == [list(x) for x in GOOD]
    assert len(calls) == 1 and out["outcome"] == "TARGET_UNRESOLVED" and a["protocol_compliant"] and a["commits"] == 1
    assert a["decision"] == "PASS" and all(a["checks"][k] for k in (
        "committed_order_equals_proposed", "joint_continuity", "achieved_state_matches_commitment",
        "target_invocation_equals_achieved"))
    assert [r["object"] for r in a["reobserve"]] == ["o01", "o00"] and a["reobserve"][-1]["moved"] == ["o01", "o00"]
    assert all(r["commanded_xy"] == r["achieved_xy"] and r["attachment"] == "free" for r in a["reobserve"])
    assert calls[0].q == out["achieved"].q and [e["kind"] for e in out["trace"].events].count("REPAIR_PLAN") == 2

    def swapped(r, c, s0, cand, key, used):                  # a planner that silently reorders is never committed
        p = dict(good_plan)
        return {**p, "witness": good_plan["witness"]} if tuple(cand["sequence"]) == BAD else p
    calls.clear()
    out2 = ev.primary_episode(robot, cfg, q, s, [{**pool[0], "cells": dict(pool[0]["assignment"])}], stub, "h",
                              planner=swapped)
    assert out2["outcome"] == "ABORTED" and not calls and out2["commit"] is None


def test_teacher_keeps_scopes_and_never_turns_unknown_into_negative(robot, cfg, v2, r4, good_plan, monkeypatch):
    s, q = r4
    real = vf.plan_fixed_order
    monkeypatch.setattr(vf, "plan_fixed_order", lambda r, c, s0, seq, key, used: good_plan if tuple(seq) == GOOD
                        else real(r, c, s0, seq, key, used))
    unk = lambda st, key: {"status": sk.UNRESOLVED, "reason": "STUB_BUDGET", "result": None}  # noqa: E731
    g = od.teach_sequence(robot, cfg, v2, q, s, GOOD, unk, "g4d/test/teach", "h")
    assert g["ordered_feasibility_status"] == data.UNKNOWN and g["relocation_attempt_status"] == vf.RELOCATED
    assert g["cost"]["label_available"] and g["target_attempt_status"] == sk.UNRESOLVED
    assert (g["simulation_status"], g["hardware_status"]) == ("NOT_RUN", "NOT_AUTHORIZED")
    b = od.teach_sequence(robot, cfg, v2, q, s, BAD, unk, "g4d/test/teach_bad", "h")
    assert b["ordered_feasibility_status"] == data.NEGATIVE and b["target_attempt_status"] == "NOT_RUN"
    assert b["relocation_attempt_status"] == "NOT_RUN" and b["cost"] is None
    with pytest.raises(ValueError):
        od.teach_sequence(robot, cfg, v2, q, s, (("o00", 28),), unk, "x", "h")         # stay entry


def test_proposal_side_cannot_reach_planner_or_target():
    code = ("import sys; sys.path.insert(0, %r); import sequences; "
            "print(sorted(m for m in ('verify', 'evaluate', 'planner', 'skill', 'ordered', 'certificates') if m in sys.modules))")
    out = subprocess.run([sys.executable, "-c", code % str(ROOT)], capture_output=True, text=True, check=True).stdout
    assert out.strip() == "[]"


class _Npz(dict):
    @property
    def files(self):
        return list(self)


def test_legacy_witness_validation_rejects_tampered_records(cfg, robot):
    """Archived G4A first-pass witness: validated for its exact recorded order; a moved
    waypoint, a swapped target record or a different end policy is rejected."""
    import g4d
    g4a = ROOT / "runs/g4a_evidence_audit"
    plan = json.loads((g4a / "g4a_plan.json").read_text())
    tasks, scenes = json.loads((g4a / "result.json").read_text())["tasks"], json.loads((g4a / "scenes.json").read_text())
    npz = np.load(g4a / "arrays.npz")
    tag = "g4a_r02.audit2"                                                 # a two-move first-pass positive
    arrs = _Npz({k: npz[k] for k in npz.files if k.startswith(tag)})
    q = next(x for x in plan["queries"] if x["query_id"] == "g4a_r02")
    cells = {tasks[f"{tag}.m{k}"]["target"]: None for k in range(2)}
    row = next(r for r in json.loads((g4a / "candidate_labels.json").read_text())
               if r["query_id"] == "g4a_r02" and set(dict(r["signature"])) == set(cells) and r["first_pass"] == data.POSITIVE)
    cells = dict(row["signature"])
    ok = g4d.legacy_positive(cfg, robot, q, tag, cells, tasks, scenes, arrs)
    assert ok["v2_status"] == data.POSITIVE and [o for o, _ in ok["recorded_sequence"]] == [tasks[f"{tag}.m0"]["target"],
                                                                                           tasks[f"{tag}.m1"]["target"]]
    assert ok["legacy_cost"]["usable_as_v2_cost_label"] is False
    bad = _Npz(arrs)
    bad[f"{tag}.m1__q"] = arrs[f"{tag}.m1__q"] + np.array([1e-4, 0, 0])
    assert g4d.legacy_positive(cfg, robot, q, tag, cells, tasks, scenes, bad)["v2_status"] == data.UNKNOWN
    home = {**q, "action": {k: v for k, v in q["action"].items() if k not in ("end_policy",)}}
    assert g4d.legacy_positive(cfg, robot, home, tag, cells, tasks, scenes, arrs)["v2_status"] == data.UNKNOWN
