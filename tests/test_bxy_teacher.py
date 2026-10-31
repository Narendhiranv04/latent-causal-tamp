"""BXY-P9 teacher / pilot tests (instructions §F). No physical teacher call: real stored BD_GEN_V1 relocation records (already certified by
the historical teacher), synthetic records, and DetPhysics instances whose planning entry points are stubbed for failure metadata."""
import copy
import json
from pathlib import Path

import numpy as np
import pytest

import bxy_data as bd

HAVE = (bd.DATA / "roots").exists()
pytestmark = pytest.mark.skipif(not HAVE, reason="local BD_GEN_V1 snapshot not present")
if HAVE:
    import bxy_pilot as P
    import bxy_teacher as T
    R = bd.roots()
    E = T.env()


def W(i):
    z = np.load(bd.DATA / "witnesses" / i[:2] / f"{i}.npz")
    return {k: z[k] for k in z.files}


def conn(qa, qb, gap=0.07):
    return {"q": np.array([qa, qb], float), "gap": np.full(2, gap), "phase": np.array(["pregrasp"]), "attached": np.array([False]),
            "held_local": np.array([]), "place_xy": np.array([])}


def one_move(clear=True):
    """(root, rec, seq, [relocation record], target record) of a historical 1-move success whose straight q_end -> q0 connector is
    certified clear (clear=True) or not (clear=False)."""
    for k, rec in R.items():
        for b in rec["labels"]["B"]:
            if b["y"] == 1 and len(b["sequence"]) == 1:
                seq, recs = [(o, int(d)) for o, d in b["sequence"]], [W(w) for w in b["witnesses"]]
                ok = T.replay_x(E, rec, seq, recs[:1], conn(recs[0]["q"][-1], T.qref(rec)))["ok"]
                if ok == clear:
                    return k, rec, seq, recs[:1], recs[1]
    raise LookupError


def test_keys_order_endpoint_context_and_omission():
    k, rec = next(iter(R.items()))
    ab, ba = [("o00", 40), ("o01", 41)], [("o01", 41), ("o00", 40)]
    assert T.xkey(k, rec, ab) != T.xkey(k, rec, ba) and T.ykey(k, rec, ab) == T.ykey(k, rec, ba)
    for mut in (lambda r: r.update(q0=[x + 0.1 for x in r["q0"]]), lambda r: r.update(goal_cell=(r["goal_cell"] + 1) % 64),
                lambda r: r["scene"].update(robot_profile_hash="other")):
        r2 = copy.deepcopy(rec)
        mut(r2)
        assert T.ykey(k, r2, ab) != T.ykey(k, rec, ab) and T.xkey(k, r2, ab) != T.xkey(k, rec, ab)   # no aliasing across q_ref/task/profile
    k2, rec2 = list(R.items())[1]
    assert T.xkey(k2, rec2, ab) != T.xkey(k, rec, ab)
    om = [a for i, a in enumerate(ab + [("o02", 42)]) if i != 1]
    assert bd.endpoint(rec, om) == {"o00": 40, "o02": 42}                                      # omitted o01 stays at its S0 pose


def test_ineligible_and_empty_are_not_attempted():
    k, rec = next((k, r) for k, r in R.items() if r["fixed_ids"] and r["roles"])
    mv = next(iter(rec["roles"]))
    for seq, why in (([("t0", 5)], "T is moved"), ([(rec["fixed_ids"][0], 5)], "non-movable"), ([(mv, 5), (mv, 6)], "duplicate"),
                     ([(mv, 99)], "legal"), ([(mv, 1)] * 7, "actions")):
        x = T.x_query(E, k, rec, seq, {})
        assert x["attempted"] is False and x["y"] is None and x["teacher_status"] == "INELIGIBLE" and why in x["why"]
    e = T.x_query(E, k, rec, [], {})
    assert e["attempted"] is False and e["y"] is None and e["teacher_status"] == "EMPTY_PREFIX_X_IS_1_BY_DEFINITION"


def test_failure_metadata_distinguishes_step0_and_connector(monkeypatch, tmp_path):
    k, rec, seq, recs, _ = one_move(clear=False)
    real = T._phys

    def failing(k_, rec_, cache):
        p = real(k_, rec_, cache)
        p.edges = lambda *a: [("UNKNOWN_PLANNER", None, None, 0.0, {"planner": "stub"})]
        return p
    monkeypatch.setattr(T, "_phys", failing)
    x = T.x_query(E, k, rec, seq, {}, tmp_path)
    assert (x["attempted"], x["observed"], x["y"], x["failed_phase"], x["negative_kind"]) == (True, True, 0, "relocation:0", "NO_PLAN_FOUND")

    def no_connector(k_, rec_, cache):
        p = real(k_, rec_, cache)
        p.edges = lambda *a: [("VERIFIED", recs, np.asarray(recs[0]["q"][-1]), 1.0, {"via": "online"})]
        p._transit = lambda *a: (p._take("transit_plans") and None, "unknown")
        return p
    monkeypatch.setattr(T, "_phys", no_connector)
    x = T.x_query(E, k, rec, seq, {}, tmp_path)
    assert x["y"] == 0 and x["failed_phase"] == "connector" and x["teacher_status"] == "UNKNOWN_TRANSIT" and x["steps"]
    assert x["witness_connector"] is None and x["final_q_before_connector"] is not None                # relocation reached, no positive X


def test_connector_positive_requires_the_replayed_witness(monkeypatch, tmp_path):
    k, rec, seq, recs, _ = one_move(clear=True)
    real = T._phys

    def ok(k_, rec_, cache):
        p = real(k_, rec_, cache)
        p.edges = lambda *a: [("VERIFIED", recs, np.asarray(recs[0]["q"][-1]), 1.0, {"via": "online"})]
        return p                                                       # the REAL _transit: its straight segment is certified clear here
    monkeypatch.setattr(T, "_phys", ok)
    x = T.x_query(E, k, rec, seq, {}, tmp_path)
    assert x["y"] == 1 and x["independent_replay"] and x["connector_how"] in ("direct", "same") and x["budget_spent"]["transit_plans"] == 0
    assert np.allclose(x["final_q_after_connector"], T.qref(rec), atol=T.TOL_Q) and x["travel_parts"]["J_connector"] >= 0
    assert (tmp_path / "witnesses" / x["witness_connector"][:2] / f"{x['witness_connector']}.npz").exists()


def test_connector_world_has_every_body_and_rejects_collisions():
    import motion as mo
    k, rec, seq, recs, _ = one_move(clear=False)
    cells = {**bd.cells0(rec), **dict(seq)}
    import p16_motion as pm
    s = pm.DetPhysics(T.task_of(k, rec), None).scene(cells, T.qref(rec))
    ck = mo.checkers(E["robot"], s, "t0", None, None, E["p"]["delta"], E["p"]["eps"])[("start", False)]
    assert set(ck.world.ids) == {o.id for o in s.objects} and ck.held is None                          # target and all objects present
    q_end = recs[0]["q"][-1]
    assert ck.status_at(q_end, 0.07).status == "CLEAR" and ck.status_at(T.qref(rec), 0.07).status == "CLEAR"
    r = T.replay_x(E, rec, seq, recs, conn(q_end, T.qref(rec)))
    assert not r["ok"] and "segment not certified" in r["why"]       # endpoints clear, straight segment between them is NOT: rejected


def test_replay_rejects_tampered_witnesses():
    k, rec, seq, recs, _ = one_move(clear=True)
    good = conn(recs[0]["q"][-1], T.qref(rec))
    assert T.replay_x(E, rec, seq, recs, good)["ok"]
    bad = []
    r0 = copy.deepcopy(recs[0])
    r0["q"] = r0["q"] + 1e-3
    bad.append(([r0], good, "discontinuous"))                                                       # discontinuous robot path
    bad.append((recs, good, "placed", [(seq[0][0], (seq[0][1] + 1) % 64)]))                      # wrong destination
    r1 = copy.deepcopy(recs[0])
    r1["place_xy"] = r1["place_xy"] + 0.01
    bad.append(([r1], good, "invalid record"))                                                     # altered pose
    bad.append(([], good, "record count"))                                                         # omitted record
    r2 = copy.deepcopy(recs[0])
    r2["attached"] = np.ones_like(r2["attached"])
    bad.append(([r2], good, "invalid record"))                                                     # wrong attachment schedule
    c1 = copy.deepcopy(good)
    c1["attached"] = np.array([True])
    bad.append((recs, c1, "gripper"))                                                              # attached during the connector
    c2 = conn(recs[0]["q"][-1], T.qref(rec) + 1e-3)
    bad.append((recs, c2, "q_ref"))                                                                # connector misses q_ref
    c3 = conn(recs[0]["q"][-1], T.qref(rec), gap=0.05)
    bad.append((recs, c3, "gripper"))                                                              # wrong gap
    for case in bad:
        rs, c, why = case[:3]
        sq = case[3] if len(case) > 3 else seq
        out = T.replay_x(E, rec, sq, rs, c)
        assert not out["ok"] and why in out["why"], (why, out)


def test_y_replay_from_q_ref_and_rejections():
    k, rec, seq, recs, tgt = one_move(clear=True)
    r2 = copy.deepcopy(rec)
    r2["q0"] = list(map(float, tgt["q"][0]))                         # fixture: this stored target record starts at the achieved state
    assert T.replay_y(E, r2, seq, tgt)["ok"]
    assert not T.replay_y(E, rec, seq, tgt)["ok"]                    # not from the root's q_ref: rejected (never achieved-q Y)
    t2 = copy.deepcopy(tgt)
    t2["place_xy"] = t2["place_xy"] + 0.02
    assert not T.replay_y(E, r2, seq, t2)["ok"]


def test_pair_semantics_four_states_and_no_filling(tmp_path):
    xr = lambda y: {"x_key": "X2:a", "parent_y_key": "Y2:s", "root": "a", "y": y}  # noqa: E731
    yr = lambda y: {"y_key": "Y2:s", "root": "a", "y": y}  # noqa: E731
    for x in (0, 1):
        for y in (0, 1):
            if (x, y) != (1, 1):
                p = T.pair(E, xr(x), yr(y), tmp_path)
                assert p["matched_protocol"] and p["full_joint_success"] == 0 and (p["x"], p["y"]) == (x, y)
    assert T.pair(E, xr(None), yr(1), tmp_path)["full_joint_success"] is None                       # missing never filled
    assert T.pair(E, xr(1), {**yr(1), "y_key": "Y2:other"}, tmp_path)["matched_protocol"] is False


def test_censored_is_unobserved_and_resume_never_rereads(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "OUT", tmp_path)
    d = tmp_path / "results" / "r"
    P.jw(d / "00_Y0.y.inprogress", {"started": 0})
    led = tmp_path / "L.jsonl"

    class Ru:
        ru_utime, ru_stime = 1.0, 0.5
    P.finish(("r", 300, 0.0, None), 9, Ru, None, led)               # SIGKILL by the CPU guard
    row = json.loads((d / "00_Y0.y.json").read_text())
    assert row["observed"] is False and row["y"] is None and row["teacher_status"] == "CENSORED"
    assert json.loads(led.read_text())["cpu_s"] == 1.5


def test_roster_train_only_and_worklist_predeclared():
    ros = P.roster(R)
    assert len(ros["roots"]) == 20 and all(bd.split_of(R[k]) == "train" for k in ros["roots"])
    wl = {k: P.items_for(k, R[k]) for k in ros["roots"]}
    assert sum(i["x"] for v in wl.values() for i in v["items"]) <= 60 and sum(i["y"] for v in wl.values() for i in v["items"]) <= 60
    for k, v in wl.items():
        xs = [bd.xkey(k, [tuple(a) for a in i["seq"]]) for i in v["items"] if i["x"]]
        ys = [bd.ykey(k, R[k], [tuple(a) for a in i["seq"]]) for i in v["items"] if i["y"]]
        assert len(xs) == len(set(xs)) <= 3 and len(ys) == len(set(ys)) <= 3


def test_learner_inputs_carry_no_teacher_data():
    import torch
    import learn_data as ld
    d = torch.load("runs/approach_b/bd2d_lb_v1/RECORDS.pt", weights_only=False)
    assert ld.leakage_audit(d) == []                                  # learner tensors: allowlisted inputs only
    assert set(d["roots"][0]["inputs"]) == set(ld.INPUT_KEYS)
