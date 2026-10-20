"""G4C-P1 pilot pre-collection checks (contract §3). Mocks and synthetic fixtures only:
no CPU burning, no teacher calls. Authorization and finalization fail closed; the
runner's admission, cancellation and resume semantics under the pilot envelope; the
judge rejects false positives/negatives; scene edits and omissions keep their invariants;
B/C full-pool completeness; denominators and the 20-root gate stay unevaluated."""
import copy
import hashlib
import json
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config as cf  # noqa: E402
import data  # noqa: E402
import effects as ef  # noqa: E402
import g4b_figures as g4bf  # noqa: E402
import g4c_pilot as gp  # noqa: E402
import g4d_run as gr  # noqa: E402
import geometry as ge  # noqa: E402
from scene import scene_from_dict  # noqa: E402

P, N, U = data.POSITIVE, data.NEGATIVE, data.UNKNOWN
INSTR = ROOT / "instruction-phase-md/G4C_P1_5Root_Pilot_Collection_Instructions.md"


@pytest.fixture(scope="module")
def ctx():
    calls = g4bf._instrument()
    cfg = cf.load_config(ROOT / "config.toml")
    parent = json.loads((ROOT / gp.PARENT).read_text())
    raw = hashlib.sha256((ROOT / gp.PARENT).read_bytes()).hexdigest()
    auth = gp.authorization_record(INSTR if INSTR.exists() else ROOT / "g4c_pilot.py")
    plan = gp.finalize(copy.deepcopy(parent), auth, cfg, ROOT)
    return cfg, parent, auth, plan, calls, raw


def test_finalize_preserves_parent_and_the_59_frozen_units(ctx):
    cfg, parent, auth, plan, calls, raw = ctx
    assert hashlib.sha256((ROOT / gp.PARENT).read_bytes()).hexdigest() == raw and all(v is None for v in parent["budget"].values())
    assert {r: sum(u["root"] == r for u in plan["units"]) for r in gp.PILOT} == {"g4c_r00": 2, "g4c_r08": 10, "g4c_r10": 11,
                                                                                  "g4c_r14": 19, "g4c_r19": 17}
    frozen = [u for u in parent["units"] if u["root"] in gp.PILOT]
    assert json.dumps(plan["units"]) == json.dumps(frozen)                    # identities, order and seed keys byte-identical
    assert plan["roots"] == {k: parent["roots"][k] for k in gp.PILOT} and plan["parent_plan_hash"] == gp.PARENT_HASH
    assert plan["limits"]["cpu_aggregate_s"] == 10800 and plan["limits"]["cpu_per_unit_s"] == 900
    assert plan["call_caps"]["structural_maxima"] == {"relocation_skills": 60, "target_evaluations": 59}
    assert not any(calls.values())


@pytest.mark.parametrize("bad", ["aggregate", "missing", "full_scope", "parent_hash", "extra_unit", "budget_in_parent"])
def test_wrong_authorization_or_plan_is_refused_before_any_teacher_call(ctx, bad):
    cfg, parent, auth, plan, calls, _ = ctx
    a, p = copy.deepcopy(auth), copy.deepcopy(parent)
    if bad == "aggregate":
        a["aggregate_cpu_s"] = 18000
    elif bad == "missing":
        del a["workers"]
    elif bad == "full_scope":
        a["roots"] = {k: 1 for k in parent["roots"]}
    elif bad == "parent_hash":
        p["units"][0]["target_key"] = "g4c/x/target"
    elif bad == "extra_unit":
        p["units"].append({**p["units"][3], "unit": "seq:g4c_r08:extra"})
    else:
        p["budget"]["aggregate_cpu_s"] = 10800
    if bad not in ("parent_hash", "budget_in_parent", "extra_unit"):
        a["authorization_hash"] = cf.stable_hash({k: v for k, v in a.items() if k != "authorization_hash"})
    with pytest.raises(SystemExit):
        gp.finalize(p, a, cfg, ROOT)
    assert not any(calls.values())


def test_tampered_source_binding_is_detected(ctx, tmp_path):
    plan = copy.deepcopy(ctx[3])
    plan["plan_hash"] = cf.stable_hash({k: v for k, v in plan.items() if k != "plan_hash"})
    assert gr.verify_sources(plan, ROOT) == []
    plan["source"]["files"]["ordered.py"] = "sha256:0"
    assert "ordered.py" in gr.verify_sources(plan, ROOT)


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
    monkeypatch.setattr(gr.teacher, "guard", lambda *a, **k: seen.append(a[1:4]) or fake(*a, **k))
    return gr.run_collection(plan, out, {"plan": out / "p.json", "config": "c", "config_v2": "v"}, ROOT,
                             lambda job: ["true"]), seen


def test_envelope_cancellation_admission_and_resume_with_mocks(ctx, tmp_path, monkeypatch):
    plan = {**ctx[3], "units": ctx[3]["units"][:4]}
    led, seen = _run(plan, tmp_path / "a", monkeypatch, [("COMPLETED", 5.0), ("CPU_CENSORED", 870.4), ("COMPLETED", 3.0),
                                                          ("COMPLETED", 2.0)])
    assert [v["stop"] for v in led["units"].values()] == ["COMPLETED", "CPU_CENSORED", "COMPLETED", "COMPLETED"]
    assert all(c == 900.0 and w <= 1800.0 for c, w, _ in seen) and "enforcement_failure" not in led
    led, _ = _run(plan, tmp_path / "b", monkeypatch, [("COMPLETED", 905.0)])                  # overshoot past the hard cap
    assert "enforcement_failure" in led and len(led["units"]) == 1
    base = {"plan_hash": plan["plan_hash"], "deadline_epoch": time.time() + 14400, "started_utc": "x", "resumes": 0,
            "unit_cpu_s": 9900.0, "coordinator_cpu_s": 0.0, "units": {}}
    led, seen = _run(plan, tmp_path / "c", monkeypatch, [], base)                               # 9900 + 900 + 60 > 10800
    assert {v["stop"] for v in led["units"].values()} == {"NOT_RUN_BUDGET"} and not seen
    led, seen = _run(plan, tmp_path / "d", monkeypatch, [], {**base, "unit_cpu_s": 0.0, "deadline_epoch": time.time() - 1})
    assert {v["stop"] for v in led["units"].values()} == {"NOT_RUN_WALL"} and not seen
    first = plan["units"][0]["unit"]
    led, seen = _run(plan, tmp_path / "e", monkeypatch, [("COMPLETED", 1.0)] * 3,
                     {**base, "unit_cpu_s": 0.0, "units": {first: {"state": "STARTED"}}})
    assert led["units"][first]["stop"] == "INTERRUPTED_AMBIGUOUS" and len(seen) == 3            # never rerun


def _ev(unit, label=U, witness=False, checks=True, retreat=True, certs=(), stop="COMPLETED", cost=None):
    c = {k: checks for k in ("target_start_equality", "achieved_state_consistency", "joint_continuity")}
    return {"unit": unit["unit"], "kind": unit["kind"], "root": unit["root"], "sequence": unit.get("sequence", []),
            "label": label, "stop": stop, "checks": c, "certificates": [dict(x) for x in certs],
            "evidence": [{"kind": "complete_witness"}] if witness else [], "relocation": None, "cost": cost,
            "target": {"witness_check": {"accepted": True, "ends_in_safe_retreat": retreat}} if witness else None}


def test_judge_rejects_false_positives_and_false_negatives(ctx):
    u = ctx[3]["units"][3]
    assert gp.adjudicate(_ev(u, P, True))["label"] == P
    assert gp.adjudicate(_ev(u, P, True, checks=False))["label"] == U                # invocation/continuity mismatch
    assert gp.adjudicate(_ev(u, P, True, retreat=False))["label"] == U               # no safe retreat
    assert gp.adjudicate(_ev(u, P, False))["label"] == U                             # self-reported success only
    assert gp.adjudicate(_ev(u, N, certs=[{"kind": "ORDER_FIRST_ACTION", "scope": "ORDER", "accepted": True}]))["label"] == N
    assert gp.adjudicate(_ev(u, N, certs=[{"kind": "ORDER_FIRST_ACTION", "scope": "ORDER", "accepted": False}]))["label"] == U
    assert gp.adjudicate(_ev(u, N, certs=[{"kind": "X", "scope": "TRAJECTORY", "accepted": True}]))["label"] == U
    assert gp.adjudicate(_ev(u, U, stop="CPU_CENSORED"))["label"] == U
    both = _ev(u, P, True, certs=[{"kind": "GOAL_OVERLAP", "scope": "ASSIGNMENT", "accepted": True}])
    assert gp.adjudicate(both)["label"] == data.CONTRADICTION


def test_scene_edits_and_omissions_keep_their_invariants(ctx):
    cfg, parent, auth, plan, *_ = ctx
    robot = ge.make_robot(cfg)
    for u in plan["units"]:
        if u["kind"] == "SCENE_TARGET_ONLY":
            s = scene_from_dict(plan["roots"][u["root"]]["scene"])
            act = data.make_query(cfg, "x", s, "t0", plan["roots"][u["root"]]["goal_cell"], {}, "SAFE_RETREAT",
                                  data.PROTOCOL_V2)["learner"]["action"]
            sub = ef.pose_substitution(robot, cfg, s, act, u["edit"])
            assert sub["changed_fields"]["robot_unchanged"] and sub["scene"].robot == s.robot
            assert set(sub["changed_fields"]["changed_objects"]) == set(u["edit"])
    r14 = plan["roots"]["g4c_r14"]
    for p in r14["queries"]["pool"]:
        if p["origin"].startswith("omission_of:"):
            full = [[o, int(c)] for o, c in (x.split(">") for x in p["origin"].split(":", 1)[1].split("."))]
            omitted = [o for o, _ in full if [o, dict(map(tuple, full))[o]] not in p["sequence"]]
            assert [a for a in full if a in p["sequence"]] == p["sequence"]
            assert ef.stays_at_initial(scene_from_dict(r14["scene"]), [tuple(a) for a in full], omitted)


def _labels(plan, label, override=None):
    lab = {u["unit"]: {"label": label} for u in plan["units"]}
    lab.update(override or {})
    return lab


def test_bc_pool_completeness_rules(ctx):
    plan = ctx[3]
    r19 = plan["roots"]["g4c_r19"]
    full = gp.bc_pool("g4c_r19", r19, _labels(plan, P))
    assert full["qualifies"] and full["decided_slots"] == full["active_slots"] > 0
    one = gp.bc_pool("g4c_r19", r19, _labels(plan, P, {"scene:g4c_r19:" + next(
        gp._sig(sorted(q["edit"].items())) for q in r19["queries"]["scene_queries"]): {"label": U}}))
    assert not one["qualifies"] and len({m["unit"] for m in one["missing"]}) == 1
    empty_only = gp.bc_pool("g4c_r19", r19, _labels(plan, P, {"seq:g4c_r19:empty": {"label": N}}))
    assert empty_only["qualifies"]                                                    # decided NEGATIVE still decides
    other = {f"seq:g4c_r14:{k.split(':', 2)[2]}": v for k, v in _labels(plan, P).items() if k.startswith("seq:g4c_r19")}
    assert not gp.bc_pool("g4c_r19", r19, other)["qualifies"]                         # no cross-root label reuse
    bad = copy.deepcopy(r19)
    bad["queries"]["pool"][0]["bc_layout"]["active"][-1] = True                       # changed mask
    assert not gp.bc_pool("g4c_r19", bad, _labels(plan, P))["qualifies"]
    scr = copy.deepcopy(r19)
    scr["queries"]["catalogue"]["queries"] = scr["queries"]["catalogue"]["queries"][::-1]   # scrambled catalogue
    assert not gp.bc_pool("g4c_r19", scr, _labels(plan, P))["qualifies"]


def test_denominators_and_full_gate_stay_unevaluated(ctx):
    cfg, parent, auth, plan, *_ = ctx
    ev = {u["unit"]: _ev(u, U) for u in plan["units"]}
    j = gp.judge(plan, parent, ev)
    assert len(j["labels"]) == 59 and j["label_counts"] == {U: 59}                    # COMPLETED is not POSITIVE
    assert all(row["status"] == "NOT_EVALUATED_FULL_SET / PILOT_ONLY" for row in j["full_gate"])
    assert all(not r["zero_move_positive"] and not r["nonempty_positive"] for r in j["roots"].values())
    ev2 = dict(ev)
    ev2[plan["units"][0]["unit"]] = {**_ev(plan["units"][0]), "label": "NOT_RUN"}
    assert gp.judge(plan, parent, ev2)["label_counts"] == {U: 58, "NOT_RUN": 1}


def test_adjudicator_agrees_with_the_archived_g4d_judgement():
    """Real evidence records (archived G4D units, same unit_evidence shape): identical labels."""
    ev = json.loads((ROOT / "runs/g4d_evidence/unit_evidence.json").read_text())
    got = {k: gp.adjudicate(e)["label"] for k, e in ev.items()}
    assert got == {k: e["label"] for k, e in ev.items()}
    assert sorted(set(got.values())) == [N, U, P] or sorted(set(got.values())) == sorted({N, U, P})
