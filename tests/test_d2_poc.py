"""G4C-D2-P1 POC_S pre-collection checks (contract §4 Phase 1). Mocks and synthetic evidence
only: no teacher calls, no CPU burning. Exact plan identity, fail-closed validation, guarded
admission/cancellation/resume, independent judge, active z masks and denominators."""
import copy
import json
import shutil
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config as cf  # noqa: E402
import d2_poc as dp  # noqa: E402
import data  # noqa: E402
import g4b_figures as g4bf  # noqa: E402
import g4c_pilot as gp  # noqa: E402
import g4d_run as gr  # noqa: E402
import geometry as ge  # noqa: E402
from scene import scene_from_dict, scene_hash, scene_to_dict  # noqa: E402

P, N, U = data.POSITIVE, data.NEGATIVE, data.UNKNOWN
INSTR = ROOT / "instruction-phase-md/G4C_D2_P1_Witness_First_POC_S_Instructions.md"


@pytest.fixture(scope="module")
def ctx():
    calls = g4bf._instrument()
    cfg = cf.load_config(ROOT / "config.toml")
    p0 = {f: dp._sha(ROOT / dp.P0 / f) for f in ("precheck_variants.json", "precheck_queries.json", "manifest.json")}
    auth = dp.authorization_record(INSTR if INSTR.exists() else ROOT / "d2_poc.py")
    plan = dp.finalize(cfg, auth, ROOT)
    return cfg, ge.make_robot(cfg), auth, plan, calls, p0


def _rehash(a):
    a["authorization_hash"] = cf.stable_hash({k: v for k, v in a.items() if k != "authorization_hash"})
    return a


def test_plan_is_exactly_the_p0_pocs_scope_with_zero_teacher_calls(ctx):
    cfg, robot, auth, plan, calls, p0 = ctx
    assert {f: dp._sha(ROOT / dp.P0 / f) for f in p0} == p0                                     # P0 byte-identical
    frozen = [u for u in plan["units"] if not u.get("fresh_base")]
    assert len(frozen) == 68 and [sum(u["kind"] == k for u in frozen) for k in
                                  ("ORDERED_TEACHER", "SCENE_TARGET_ONLY", "ROBOT_START_TARGET_ONLY")] == [50, 16, 2]
    assert plan["call_caps"]["worst_case"] == {"relocation_skills": 46, "target_evaluations": 70}
    assert len(plan["fresh_units"]) + sum(not x["accepted"] for x in plan["fresh_ledger"]) == 2 == len(plan["fresh_ledger"])
    assert plan["units"][:len(plan["fresh_units"])] == [u for u in plan["units"] if u.get("fresh_base")]  # fresh first, no descendants
    assert all(u["sequence"] == [] for u in plan["units"] if u.get("fresh_base"))
    pq = json.loads((ROOT / dp.P0 / "precheck_queries.json").read_text())
    for k, r in plan["roots"].items():
        if r["variant"] != "fresh":
            assert r["queries"]["pool"] == pq[r["base_family"]][r["variant"]]["pool"]
    ids = {r["family_id"] for r in plan["roots"].values() if r["variant"] != "fresh"}
    assert len(ids) == 2 and all(r["split"] == plan["roots"][dp.rkey(r["base_family"], "base")]["split"] for r in plan["roots"].values()
                                 if r["variant"] != "fresh")
    assert dp.validate_plan(cfg, robot, plan, auth) == [] and not any(calls.values())


@pytest.mark.parametrize("bad", ["budget", "missing_field", "pocf_scope", "edited_record"])
def test_wrong_authorization_is_refused(ctx, bad):
    a = copy.deepcopy(ctx[2])
    if bad == "budget":
        _rehash({**a, "aggregate_cpu_s": 18001}) and a.update(_rehash({**a, "aggregate_cpu_s": 18001}))
    elif bad == "missing_field":
        del a["workers"]
        _rehash(a)
    elif bad == "pocf_scope":
        a["variants"] = a["variants"] + ["+A+B+C"]
        _rehash(a)
    else:
        a["target_eval_attempt_cap"] = 71
    assert dp.check_authorization(a)
    assert dp.validate_plan(ctx[0], ctx[1], ctx[3], a)


def _mut(plan, bad, robot, cfg):
    p = copy.deepcopy(plan)
    seq = [u for u in p["units"] if u["kind"] == "ORDERED_TEACHER" and len(u["sequence"]) >= 2]
    k = dp.rkey("g4d_R1", "+A")
    if bad == "67_units":
        p["units"].pop(-1)
        p["frozen_units"].pop(-1)
    elif bad == "69_units":
        p["units"].append({**p["units"][-1], "unit": p["units"][-1]["unit"] + "x"})
        p["frozen_units"].append(p["units"][-1]["unit"])
    elif bad == "extra_pocf_variant":
        r = copy.deepcopy(p["roots"][k])
        p["roots"][dp.rkey("g4d_R1", "+A+B+C")] = {**r, "variant": "+A+B+C"}
    elif bad == "wrong_lineage":
        p["roots"][k]["family_id"] = cf.stable_hash("g4c_r00")
    elif bad == "mutated_robot":
        s = scene_from_dict(p["roots"][k]["scene"])
        s2 = s.__class__(**{**s.__dict__, "robot": s.robot.__class__(**{**s.robot.__dict__, "q_rad": tuple(x + 0.01 for x in s.robot.q_rad)})})
        p["roots"][k]["scene"], p["roots"][k]["scene_hash"] = scene_to_dict(s2), scene_hash(s2)
    elif bad == "noncanonical_sequence":
        u = seq[0]
        u["sequence"] = u["sequence"][::-1] + [u["sequence"][0]]
    elif bad == "changed_catalogue":
        q = p["roots"][k]["queries"]["catalogue"]
        q["queries"] = q["queries"][::-1] + [{"kind": "late:o99"}]
    elif bad == "leaked_teacher_data":
        seq[0]["expected_label"] = "POSITIVE"
    elif bad == "reordered_units":
        i = len(p["fresh_units"])
        p["units"][i], p["units"][i + 1] = p["units"][i + 1], p["units"][i]
    elif bad == "changed_intervention":
        next(u for u in p["units"] if u["kind"] == "SCENE_TARGET_ONLY")["intervened_scene_hash"] = "sha256:0"
    elif bad == "extra_fresh_base":
        p["units"].insert(0, {**p["units"][0], "unit": "seq:d2_fresh_x:empty"})
        p["fresh_units"].insert(0, "seq:d2_fresh_x:empty")
    return p


@pytest.mark.parametrize("bad", ["67_units", "69_units", "extra_pocf_variant", "wrong_lineage", "mutated_robot", "noncanonical_sequence",
                                 "changed_catalogue", "leaked_teacher_data", "reordered_units", "changed_intervention", "extra_fresh_base"])
def test_mutated_plan_fails_closed(ctx, bad):
    cfg, robot, auth, plan, calls, _ = ctx
    assert dp.validate_plan(cfg, robot, _mut(plan, bad, robot, cfg), auth)
    assert not any(calls.values())


def test_changed_precheck_artifact_refuses_finalization(ctx, tmp_path):
    cfg, robot, auth, plan, calls, _ = ctx
    for d in ("runs/g4c_d2_precheck", "runs/g4c_preflight", "runs/g4c_pilot/units/seq__g4c_r00__empty", "runs/g4d_evidence/units/seq__R1__empty"):
        shutil.copytree(ROOT / d, tmp_path / d)
    for f in ("runs/g4c_pilot/pilot_plan.json", "runs/g4d_evidence/final_plan.json"):
        shutil.copy(ROOT / f, tmp_path / f)
    q = json.loads((tmp_path / dp.P0 / "precheck_queries.json").read_text())
    q["g4c_r00"]["+A"]["pool"].pop()                                                             # one frozen query dropped
    (tmp_path / dp.P0 / "precheck_queries.json").write_text(json.dumps(q))
    with pytest.raises(SystemExit, match="query catalogue differs from P0"):
        dp.finalize(cfg, auth, tmp_path)
    assert not any(calls.values())


def test_tampered_source_or_plan_hash_is_detected(ctx):
    plan = copy.deepcopy(ctx[3])
    assert gr.verify_sources(plan, ROOT) == []
    plan["source"]["files"]["d2.py"] = "sha256:0"
    assert "d2.py" in gr.verify_sources(plan, ROOT) and "final plan hash" in gr.verify_sources(plan, ROOT)


def _fake_guard(results):
    it = iter(results)

    def g(argv, cpu_limit, wall_limit, hb, margin, poll, cwd):
        r = next(it)
        return {"stop": r[0], "returncode": 0 if r[0] == "COMPLETED" else -9, "cpu_s": r[1], "wall_s": 1.0,
                "trigger_cpu_s": cpu_limit - margin, "cpu_limit_s": cpu_limit, "overshoot_s": max(0.0, r[1] - cpu_limit),
                "active_phase": None, "stderr_tail": "", "_limits": (cpu_limit, wall_limit, margin)}
    return g


def _run(plan, out, monkeypatch, results, seed_ledger=None):
    out.mkdir(parents=True, exist_ok=True)
    if seed_ledger:
        gr._atomic_json(out / "ledger.json", seed_ledger)
    seen = []
    fake = _fake_guard(results)
    monkeypatch.setattr(gr.teacher, "guard", lambda *a, **k: seen.append((a[1], a[2], a[4])) or fake(*a, **k))
    return gr.run_collection(plan, out, {"plan": out / "p.json", "config": "c", "config_v2": "v"}, ROOT, lambda job: ["true"]), seen


def test_guard_envelope_cancellation_over_budget_and_ambiguous_resume(ctx, tmp_path, monkeypatch):
    plan = {**ctx[3], "units": ctx[3]["units"][:4]}
    led, seen = _run(plan, tmp_path / "a", monkeypatch, [("COMPLETED", 5.0), ("CPU_CENSORED", 870.4), ("COMPLETED", 3.0), ("COMPLETED", 2.0)])
    assert [v["stop"] for v in led["units"].values()] == ["COMPLETED", "CPU_CENSORED", "COMPLETED", "COMPLETED"]
    assert all(c == 900.0 and w <= 1800.0 and m == 30.0 for c, w, m in seen) and "enforcement_failure" not in led
    led, _ = _run(plan, tmp_path / "b", monkeypatch, [("COMPLETED", 905.0)])                     # overshoot past the hard cap
    assert "enforcement_failure" in led and len(led["units"]) == 1
    base = {"plan_hash": plan["plan_hash"], "deadline_epoch": time.time() + 23400, "started_utc": "x", "resumes": 0,
            "unit_cpu_s": 17100.0, "coordinator_cpu_s": 0.0, "units": {}}
    led, seen = _run(plan, tmp_path / "c", monkeypatch, [], base)                                 # 17100 + 900 + 60 > 18000
    assert {v["stop"] for v in led["units"].values()} == {"NOT_RUN_BUDGET"} and not seen
    led, seen = _run(plan, tmp_path / "d", monkeypatch, [], {**base, "unit_cpu_s": 0.0, "deadline_epoch": time.time() - 1})
    assert {v["stop"] for v in led["units"].values()} == {"NOT_RUN_WALL"} and not seen
    first = plan["units"][0]["unit"]
    led, seen = _run(plan, tmp_path / "e", monkeypatch, [("COMPLETED", 1.0)] * 3,
                     {**base, "unit_cpu_s": 0.0, "units": {first: {"state": "STARTED"}}})
    assert led["units"][first]["stop"] == "INTERRUPTED_AMBIGUOUS" and len(seen) == 3             # never rerun
    with pytest.raises(SystemExit):                                                               # other plan's ledger
        _run(plan, tmp_path / "f", monkeypatch, [], {**base, "plan_hash": "sha256:other"})


def _ev(u, witness=False, checks=True, certs=(), stop="COMPLETED", cost=None):
    c = {k: checks for k in ("target_start_equality", "achieved_state_consistency", "joint_continuity")}
    return {"unit": u["unit"], "kind": u["kind"], "root": u["root"], "sequence": u.get("sequence", []), "stop": stop, "checks": c,
            "certificates": [dict(x) for x in certs], "evidence": [{"kind": "complete_witness"}] if witness else [], "relocation": None,
            "cost": cost, "calls": {"relocation_planner": len(u.get("sequence", [])), "target_evaluations": 1},
            "target": {"witness_check": {"accepted": True, "ends_in_safe_retreat": True}} if witness else None}


CERT = {"GOAL": {"kind": "GOAL_OVERLAP", "scope": "ASSIGNMENT", "accepted": True},
        "PICK": {"kind": "TARGET_PICK", "scope": "ASSIGNMENT", "accepted": True},
        "ORDER": {"kind": "ORDER_FIRST_ACTION", "scope": "ORDER", "accepted": True}}


def test_synthetic_judge_dry_run(ctx):
    plan = ctx[3]
    ev = {u["unit"]: _ev(u) for u in plan["units"]}
    j = dp.judge(plan, ev)
    assert j["label_counts"] == {U: len(plan["units"])} and len(j["labels"]) == len(plan["units"])  # UNKNOWN never dropped
    assert {j["questions"][q] for q in ("Q2", "Q3", "Q4", "Q5")} == {"NOT_MET"} and j["questions"]["Q1"] == "MET"
    k = dp.rkey("g4d_R1", "+A")
    pool = plan["roots"][k]["queries"]["pool"]
    nonempty = [p["sequence"] for p in pool if p["sequence"]]
    ev2 = dict(ev)
    ev2[f"seq:{k}:empty"] = _ev({"unit": f"seq:{k}:empty", "kind": "ORDERED_TEACHER", "root": k}, certs=[CERT["PICK"]])
    ev2[f"seq:{k}:{gp._sig(nonempty[0])}"] = _ev({"unit": f"seq:{k}:{gp._sig(nonempty[0])}", "kind": "ORDERED_TEACHER", "root": k,
                                                  "sequence": nonempty[0]}, witness=True)
    j2 = dp.judge(plan, ev2)
    assert j2["questions"]["Q2"] == "MET" and j2["questions"]["Q3"] == "MET" and j2["roots"][k]["no_repair"] == "NEGATIVE"
    g = dp.rkey("g4c_r00", "+G")
    ev3 = {**ev, f"seq:{g}:empty": _ev({"unit": f"seq:{g}:empty", "kind": "ORDERED_TEACHER", "root": g}, certs=[CERT["GOAL"]])}
    j3 = dp.judge(plan, ev3)
    assert j3["questions"]["Q2"] == "TRIVIAL_ONLY" and j3["trivial_negatives"] == 1 and j3["nontrivial_negatives"] == 0
    b = dp.rkey("g4c_r00", "+A")
    ev4 = {**ev, f"seq:{b}:empty": _ev({"unit": f"seq:{b}:empty", "kind": "ORDERED_TEACHER", "root": b}, witness=True)}
    assert dp.judge(plan, ev4)["roots"][b]["no_repair"] == "REROUTABLE_POSITIVE"                 # nominal blocked, still witnessed
    bad = {**ev, f"seq:{b}:empty": _ev({"unit": f"seq:{b}:empty", "kind": "ORDERED_TEACHER", "root": b}, certs=[
        {"kind": "ALL_CONNECTORS_BLOCKED", "scope": "TRAJECTORY", "accepted": True}])}
    assert dp.judge(plan, bad)["roots"][b]["no_repair"] == "UNKNOWN"                              # invalid negative scope
    con = {**ev, f"seq:{b}:empty": _ev({"unit": f"seq:{b}:empty", "kind": "ORDERED_TEACHER", "root": b}, witness=True,
                                       certs=[CERT["PICK"]])}
    assert data.CONTRADICTION in dp.judge(plan, con)["label_counts"]
    miss = {**ev, f"seq:{b}:empty": _ev({"unit": f"seq:{b}:empty", "kind": "ORDERED_TEACHER", "root": b}, witness=True, checks=False)}
    assert dp.judge(plan, miss)["labels"][f"seq:{b}:empty"]["label"] == U                         # missing/mismatched target invocation


def test_order_contrast_and_substantive_pool_rules(ctx):
    plan = ctx[3]
    for k, r in plan["roots"].items():
        units = [u for u in plan["units"] if u["root"] == k]
        ev = {u["unit"]: _ev(u, witness=True) for u in plan["units"]}
        j = dp.judge(plan, ev)
        R = j["roots"][k]
        ne = [p for p in r["queries"]["pool"] if p["sequence"]]
        assert R["bc_pool"]["qualifies"] and R["substantive_complete_pool"] == (len(ne) >= 2)
        if units and ne:
            ev[f"seq:{k}:{gp._sig(ne[0]['sequence'])}"] = _ev(units[0], stop="CPU_CENSORED")
            R2 = dp.judge(plan, ev)["roots"][k]
            assert not R2["bc_pool"]["qualifies"] and not R2["substantive_complete_pool"]          # one UNKNOWN slot breaks it
    k = dp.rkey("g4d_R1", "+A+S")
    pool = [p["sequence"] for p in plan["roots"][k]["queries"]["pool"]]
    pair = next((a, b) for a in pool for b in pool if len(a) == 2 and a == b[::-1])
    ev = {u["unit"]: _ev(u) for u in plan["units"]}
    ua, ub = f"seq:{k}:{gp._sig(pair[0])}", f"seq:{k}:{gp._sig(pair[1])}"
    ev[ua] = _ev({"unit": ua, "kind": "ORDERED_TEACHER", "root": k, "sequence": pair[0]}, witness=True)
    ev[ub] = _ev({"unit": ub, "kind": "ORDERED_TEACHER", "root": k, "sequence": pair[1]}, certs=[CERT["GOAL"]])
    assert dp.judge(plan, ev)["questions"]["Q4"] == "NOT_MET"                                     # assignment scope is not an order proof
    ev[ub] = _ev({"unit": ub, "kind": "ORDERED_TEACHER", "root": k, "sequence": pair[1]}, certs=[CERT["ORDER"]])
    assert dp.judge(plan, ev)["questions"]["Q4"] == "MET"
    ev[ua] = _ev({"unit": ua, "kind": "ORDERED_TEACHER", "root": k, "sequence": pair[0]}, stop="CPU_CENSORED")
    assert dp.judge(plan, ev)["questions"]["Q4"] == "NOT_MET"                                     # one side UNKNOWN


def test_corrupted_cost_is_not_a_label(ctx):
    plan = ctx[3]
    k = dp.rkey("g4d_R1", "+A")
    s = next(p["sequence"] for p in plan["roots"][k]["queries"]["pool"] if p["sequence"])
    uid = f"seq:{k}:{gp._sig(s)}"
    ev = {u["unit"]: _ev(u) for u in plan["units"]}
    ev[uid] = _ev({"unit": uid, "kind": "ORDERED_TEACHER", "root": k, "sequence": s}, cost={"label_available": False, "recomputed_J": None})
    assert dp.judge(plan, ev)["roots"][k]["costs"] == []
    ev[uid]["cost"] = {"label_available": True, "recomputed_J": 0.7}
    assert [c["J_first"] for c in dp.judge(plan, ev)["roots"][k]["costs"]] == [0.7]


def test_learner_view_carries_no_construction_privilege(ctx):
    cfg, robot, auth, plan, *_ = ctx
    for k, r in plan["roots"].items():
        q = data.make_query(cfg, k, scene_from_dict(r["scene"]), "t0", r["goal_cell"], {}, "SAFE_RETREAT", data.PROTOCOL_V2)
        txt = json.dumps(q["learner"], default=str)
        assert not any(w in txt for w in ("nominal", "blocks_", "construction", "role", "family_id", "split"))
