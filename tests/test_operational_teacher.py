"""G4C-LF-P4: 2D-ABC-OPNEG-v1 policy, adjudication, projections, effects, pools, plan and guards.
Pure / static only: any planner, skill, target or relocation call raises (P3a guards)."""
import copy
import hashlib
import json
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import certificates as cert  # noqa: E402
import config as cf  # noqa: E402
import data  # noqa: E402
import effects as ef  # noqa: E402
import g4c_pilot as gp  # noqa: E402
import g4d_run as gr  # noqa: E402
import geometry as ge  # noqa: E402
import operational_teacher as ot  # noqa: E402
import sector_cert  # noqa: E402
import teacher_pilot as tp  # noqa: E402
from scene import scene_from_dict  # noqa: E402

CFG = cf.load_config(ROOT / "config.toml")
ROBOT = ge.make_robot(CFG)
POL = ot.load_policy(ROOT / "teacher_opneg.toml")
ALLOWED = set(POL["policy"]["allowed_terminals"])


@pytest.fixture(autouse=True)
def zero_calls(monkeypatch):
    calls, _ = sector_cert.guard_and_count(monkeypatch.setattr)
    yield
    assert not any(calls.values()), calls


def _seed(term, clean=True, seed=1):
    return {"seed": seed, "terminal": term, "clean": clean}


@pytest.mark.parametrize("bad", ["unknown_key", "missing_key", "type", "two_seeds", "seed_cpu"])
def test_policy_schema_fails_closed(tmp_path, bad):
    txt = (ROOT / "teacher_opneg.toml").read_text()
    txt = {"unknown_key": txt.replace("workers = 1", "workers = 1\nextra = 2"),
           "missing_key": txt.replace("workers = 1\n", ""),
           "type": txt.replace("planner_max_nodes = 4000", 'planner_max_nodes = "4000"'),
           "two_seeds": txt.replace("seeds = [20261021, 20261022, 20261023]", "seeds = [20261021, 20261022]"),
           "seed_cpu": txt.replace("per_seed_cpu_s = 250.0", "per_seed_cpu_s = 300.0")}[bad]
    (tmp_path / "p.toml").write_text(txt)
    with pytest.raises(ValueError):
        ot.load_policy(tmp_path / "p.toml")
    cfg = copy.deepcopy(CFG)
    cfg["planner2d"]["max_nodes"] = 8000
    assert ot.config_mismatch(POL, cfg) and not ot.config_mismatch(POL, CFG)


def test_budget_negative_needs_every_declared_seed_clean():
    full = [_seed("SEARCH_LIMIT_PLAN_FAILURES", seed=s) for s in (1, 2, 3)]
    d = ot.adjudicate_query(None, full, POL)
    assert (d["teacher_status"], d["label_source"], d["binary_training_label"]) == (ot.BUDGET, "PLANNER_BUDGET", 0)
    assert d["proof_scope"] == f"OPERATIONAL_ONLY:{POL['policy_hash']}" and d["is_budget_relative"]
    for seeds in (full[:2], full[:2] + [_seed("NOT_CLEAN:CPU_CENSORED", False)], full[:2] + [_seed("NOT_CLEAN:ERROR", False)],
                  full[:2] + [_seed("SEARCH_LIMIT_PLAN_FAILURES+WALL_LIMIT_INVOLVED", False)], []):
        d = ot.adjudicate_query(None, seeds, POL)
        assert d["teacher_status"] == ot.UNKNOWN and d["binary_training_label"] is None and d["training_weight"] == 0.0


def test_witness_wins_and_contradiction_is_fatal():
    late = [_seed("SEARCH_LIMIT_PLAN_FAILURES", seed=1), _seed("SEARCH_LIMIT_PLAN_FAILURES", seed=2), _seed("WITNESS", seed=3)]
    d = ot.adjudicate_query(None, late, POL)
    assert d["teacher_status"] == ot.VERIFIED and d["binary_training_label"] == 1
    with pytest.raises(ot.Fatal):
        ot.adjudicate_query({"kind": "GOAL_OVERLAP", "scope": "ASSIGNMENT"}, [_seed("WITNESS")], POL)
    with pytest.raises(ot.Fatal):
        ot.adjudicate_query(None, [_seed("WITNESS"), _seed("CERTIFICATE", seed=2)], POL)
    d = ot.adjudicate_query({"kind": "LINK0_SECTOR_PICK", "scope": "ORDER"}, [], POL)
    assert (d["teacher_status"], d["proof_scope"], d["is_budget_relative"]) == (ot.CERTIFIED, "ORDER", False)


def _ev(stop="COMPLETED", reloc=None, target=None, seq=(("o04", 49),), witness=False, cps=("final",)):
    c = {k: witness for k in ("target_start_equality", "achieved_state_consistency", "joint_continuity")}
    return ({"unit": "u", "sequence": [list(a) for a in seq], "relocation": reloc, "certificates": [], "checks": c,
             "evidence": [{"kind": "complete_witness"}] if witness else [], "checkpoints": list(cps),
             "target": {"witness_check": {"accepted": True, "ends_in_safe_retreat": True}, **(target or {})} if witness else target},
            {"stop": stop, "returncode": 0 if stop == "COMPLETED" else -9, "cpu_s": 1.0})


def test_seed_terminal_classification():
    ok = {"complete_witness": False, "records_recertified": True, "normalized_reasons": ["SEARCH_LIMIT_PLAN_FAILURES"]}
    assert ot.seed_terminal(*_ev(reloc=ok), ALLOWED)["clean"]
    wall = {**ok, "normalized_reasons": ["SEARCH_LIMIT_PLAN_FAILURES+WALL_LIMIT_INVOLVED"]}
    assert not ot.seed_terminal(*_ev(reloc=wall), ALLOWED)["clean"]
    assert not ot.seed_terminal(*_ev(reloc={**ok, "records_recertified": False}), ALLOWED)["clean"]
    assert ot.seed_terminal(*_ev(stop="CPU_CENSORED", reloc=ok), ALLOWED)["terminal"] == "NOT_CLEAN:CPU_CENSORED"
    assert not ot.seed_terminal(*_ev(reloc=ok, cps=("relocation",)), ALLOWED)["clean"]          # no final checkpoint
    assert not ot.seed_terminal(*_ev(seq=(("o04", 49),), reloc=None), ALLOWED)["clean"]
    unconfirmed = ot.seed_terminal(*_ev(seq=(), target={"normalized_reason": "WITNESS"}), ALLOWED)
    assert unconfirmed["terminal"] == "UNCONFIRMED_WITNESS" and not unconfirmed["clean"]     # failed safe-retreat recheck
    assert ot.seed_terminal(*_ev(seq=(), witness=True), ALLOWED)["terminal"] == "WITNESS"
    # a failed target after ONE relocation witness is one seed's terminal, never an order-wide negative
    one = ot.seed_terminal(*_ev(reloc={**ok, "complete_witness": True}, target={"normalized_reason":
                                                                               "SCHEDULE_COMPLETED_NO_WITNESS_UNCERTIFIED_REJECTIONS"}), ALLOWED)
    assert one["clean"] and ot.adjudicate_query(None, [one], POL)["teacher_status"] == ot.UNKNOWN


def test_budget_negative_is_never_a_certificate():
    fake = {"kind": "BUDGET_INFEASIBLE", "scope": f"OPERATIONAL_ONLY:{POL['policy_hash']}", "accepted": True}
    e, _ = _ev(seq=())
    assert gp.adjudicate({**e, "certificates": [fake]})["label"] == data.UNKNOWN
    ok, why = cert.check(None, None, None, {}, {"kind": "BUDGET_INFEASIBLE"}, CFG)
    assert not ok and "not a sound certificate kind" in why[0]
    assert ot.BUDGET not in cert.CERTIFICATE_SCOPE and "PLANNER_BUDGET" != ot.SOURCE[ot.CERTIFIED]


@pytest.fixture(scope="module")
def plan():
    before = {r: hashlib.sha256((tp.SRC[r] / tp.PLAN_FILE[r]).read_bytes()).hexdigest() for r in tp.SRC}
    p = tp.build_plan(CFG, POL)
    assert before == {r: hashlib.sha256((tp.SRC[r] / tp.PLAN_FILE[r]).read_bytes()).hexdigest() for r in tp.SRC}
    return p


def test_frozen_plan_scope_keys_and_static_validity(plan):
    assert len(plan["queries"]) == 12 and len(plan["units"]) == 36 and len(plan["roots"]) == 2
    keys = [u["target_key"] for u in plan["units"]]
    assert len(set(keys)) == 36 and all(f"seed{u['seed']}" in u["target_key"] for u in plan["units"])
    swap = [u for u in plan["units"] if u["query"] in ("seq:g4c_r19:o01>28.o00>27", "seq:g4c_r19:o00>27.o01>28")]
    assert len({u["relocation_key"] for u in swap}) == 6                     # swapped orders: independent schedules
    for u in plan["units"][::3]:
        gr.unit_scene(CFG, ROBOT, plan, u)                                   # hash / identity checks, no planner
    om = next(u for u in plan["units"] if u["query"] == "seq:d2_g4c_r00_AB:o04>49")
    s, seq, _, _ = gr.unit_scene(CFG, ROBOT, plan, om)
    assert seq == [["o04", 49]] and s.get("o05").cell == 42                    # omitted o05 stays at its S0 pose
    root = plan["roots"]["d2_g4c_r00_AB"]
    s0 = scene_from_dict(root["scene"])
    act = data.make_query(CFG, "x", s0, "t0", root["goal_cell"], {}, "SAFE_RETREAT", data.PROTOCOL_V2)["learner"]["action"]
    sub = ef.pose_substitution(ROBOT, CFG, s0, act, {"o04": 49})
    assert sub["changed_fields"]["robot_unchanged"] and set(sub["changed_fields"]["changed_objects"]) == {"o04"}


def test_no_teacher_or_policy_field_reaches_the_learner(plan):
    root = plan["roots"]["g4c_r19"]
    q = data.make_query(CFG, "g4c_r19", scene_from_dict(root["scene"]), "t0", root["goal_cell"], {}, "SAFE_RETREAT", data.PROTOCOL_V2)
    txt = json.dumps(q["learner"], default=str)
    banned = ("BUDGET", "OPNEG", "policy_id", "policy_hash", "teacher", "seed", "label_source", "WITNESS", "g4c_r19",
              *map(str, POL["policy"]["seeds"]))           # ("domain_policy" is the scene's own placement-domain field)
    assert not any(w in txt for w in banned)


def _rec(q, status, kind="seq", edit=None, seq=()):
    d = ot.adjudicate_query({"kind": "X", "scope": "ASSIGNMENT"} if status == ot.CERTIFIED else None,
                            [_seed("WITNESS")] if status == ot.VERIFIED else
                            [_seed("SEARCH_LIMIT_PLAN_FAILURES", seed=s) for s in (1, 2, 3)] if status == ot.BUDGET else [], POL)
    return {**d, "query": {"query": q, "edit": edit, "sequence": [list(a) for a in seq], "kind": kind}}


def _ab(**over):
    k = "d2_g4c_r00_AB"
    r = {f"seq:{k}:empty": _rec(f"seq:{k}:empty", ot.BUDGET),
         f"scene:{k}:o04>49": _rec("a", ot.VERIFIED, "scene", {"o04": 49}),
         f"scene:{k}:o05>41": _rec("b", ot.BUDGET, "scene", {"o05": 41}),
         f"scene:{k}:o04>49.o05>41": _rec("j", ot.VERIFIED, "scene", {"o04": 49, "o05": 41}),
         f"seq:{k}:o04>49.o05>41": _rec("r", ot.VERIFIED, seq=(("o04", 49), ("o05", 41))),
         f"seq:{k}:o04>49": _rec("ra", ot.VERIFIED, seq=(("o04", 49),)),
         f"seq:{k}:o05>41": _rec("rb", ot.BUDGET, seq=(("o05", 41),))}
    r.update(over)
    return r


def test_effects_masks_kappa_and_operational_scope(plan):
    roots = {"d2_g4c_r00_AB": plan["roots"]["d2_g4c_r00_AB"]}
    e = ot.effects(_ab(), roots)
    deltas = {tuple(sorted(x["edit"])): x["delta"] for x in e["scene"]}
    assert deltas == {("o04",): 1, ("o05",): 0, ("o04", "o05"): 1}
    ks = {x["kind"]: x for x in e["kappa"]}
    assert ks["scene"]["kappa"] == 0 and ks["omission"]["kappa"] == 0 and ks["scene"]["operational"]
    unk = ot.effects(_ab(**{"scene:d2_g4c_r00_AB:o05>41": _rec("b", ot.UNKNOWN, "scene", {"o05": 41})}), roots)
    assert not any(x["kind"] == "scene" for x in unk["kappa"])                  # an UNKNOWN side masks kappa
    pl = ot.pool("d2_g4c_r00_AB", roots["d2_g4c_r00_AB"], [["o04", 49], ["o05", 41]], _ab())
    assert pl["complete"] and pl["operational"]
    rec = _ab()
    del rec["seq:d2_g4c_r00_AB:o05>41"]
    assert not ot.pool("d2_g4c_r00_AB", roots["d2_g4c_r00_AB"], [["o04", 49], ["o05", 41]], rec)["complete"]


def test_projections_reject_mixed_policy_and_keep_unknown_out_of_supervision():
    r = _ab(**{"seq:d2_g4c_r00_AB:o05>41": _rec("rb", ot.UNKNOWN, seq=(("o05", 41),))})
    p = ot.projections(r, POL["policy_hash"])
    assert len(p["raw"]) == 7 and len(p["admitted"]) == 6 and "seq:d2_g4c_r00_AB:o05>41" in p["excluded"]
    assert {v["y"] for v in p["admitted"].values()} == {0, 1}
    r["seq:d2_g4c_r00_AB:empty"] = {**r["seq:d2_g4c_r00_AB:empty"], "policy_hash": "sha256:other"}
    with pytest.raises(ValueError):
        ot.projections(r, POL["policy_hash"])
    swap = ot.effects({"seq:k:a>1.b>2": _rec("x", ot.VERIFIED, seq=(("a", 1), ("b", 2)))}, {"k": {}})["swap"]
    assert swap == []                                                         # one order never labels its permutation


def test_seed_rounds_respect_guards_and_never_turn_unrun_into_negative(plan, tmp_path, monkeypatch):
    seen = []

    def fake(argv, cpu, wall, hb, margin, poll, cwd):
        seen.append((cpu, wall, margin))
        return {"stop": "CPU_CENSORED", "returncode": -9, "cpu_s": cpu - margin + 0.1, "wall_s": 1.0, "trigger_cpu_s": cpu - margin,
                "cpu_limit_s": cpu, "overshoot_s": 0.0, "active_phase": None, "stderr_tail": ""}
    monkeypatch.setattr(gr.teacher, "guard", fake)
    P = POL["policy"]
    rp = {"units": plan["units"][:3], "limits": {"cpu_per_unit_s": P["per_seed_cpu_s"], "guard_margin_s": P["per_seed_guard_margin_s"],
          "wall_per_unit_s": P["per_seed_wall_s"], "cpu_aggregate_s": 600.0, "wall_total_s": 7200.0, "poll_s": 0.25,
          "orchestration_reserve_s": 60.0, "workers": 1}}
    rp["plan_hash"] = cf.stable_hash(rp)
    t = time.time()
    led = gr.run_collection(rp, tmp_path, {"plan": tmp_path / "p.json", "config": "c", "config_v2": "v"}, ROOT, lambda job: ["true"])
    assert all(c == 250.0 and w <= 600.0 and m == 10.0 for c, w, m in seen) and time.time() - t < 30
    stops = [v["stop"] for v in led["units"].values()]
    assert stops[0] == "CPU_CENSORED" and "NOT_RUN_BUDGET" in stops              # 240 + 250 + 60 > 600
    d = ot.adjudicate_query(None, [ot.seed_terminal({"checkpoints": []}, led["units"][plan["units"][0]["unit"]], ALLOWED)], POL)
    assert d["teacher_status"] == ot.UNKNOWN


def test_loss_masks_cost_only_for_repairs():
    r = _ab()
    r["seq:d2_g4c_r00_AB:o04>49.o05>41"]["J_first"] = 2.5
    r["scene:d2_g4c_r00_AB:o04>49"]["J_first"] = 0.0                       # worker's empty-repair cost inside a scene edit
    m = ot.loss_masks(r)
    assert m["scene:d2_g4c_r00_AB:o04>49"]["cost_J"] is None and not m["scene:d2_g4c_r00_AB:o04>49"]["cost_mask"]
    assert m["seq:d2_g4c_r00_AB:empty"]["cost_J"] == 0.0 and m["seq:d2_g4c_r00_AB:o04>49.o05>41"]["cost_J"] == 2.5
    assert m["seq:d2_g4c_r00_AB:o05>41"]["cost_J"] is None                     # no recorded relocation witness: no cost label
    assert m["seq:d2_g4c_r00_AB:empty"]["budget_relative"] and m["seq:d2_g4c_r00_AB:empty"]["y"] == 0
