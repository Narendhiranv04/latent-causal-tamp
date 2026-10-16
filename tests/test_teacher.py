"""G4A follow-up checks: teacher overrides isolated, identical starts per tier, in-flight
CPU guard over the process tree, reconciliation counts, call accounting, witness check."""
import copy
import json
import sys
from pathlib import Path

import numpy as np
import psutil
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config as cf  # noqa: E402
import coverage  # noqa: E402
import data  # noqa: E402
import evaluate as ev  # noqa: E402
import geometry as ge  # noqa: E402
import teacher  # noqa: E402
from scene import scene_from_dict  # noqa: E402

G4A = ROOT / "runs/g4a_evidence_audit"


@pytest.fixture(scope="module")
def cfg():
    return cf.load_config(ROOT / "config.toml")


def test_teacher_overrides_do_not_touch_deployment(cfg):
    before, toml = copy.deepcopy(cfg), (ROOT / "config.toml").read_bytes()
    b1, b2 = teacher.teacher_cfg(cfg, 2), teacher.teacher_cfg(cfg, 4)
    assert cfg == before and (ROOT / "config.toml").read_bytes() == toml
    assert (b1["planner2d"]["max_nodes"], b1["skill2d"]["max_plan_failures"], b1["skill2d"]["max_direct_pairs"]) == (8000, 8, 128)
    assert (b2["planner2d"]["max_nodes"], b2["skill2d"]["max_plan_failures"], b2["skill2d"]["max_direct_pairs"]) == (16000, 16, 256)
    for t in (b1, b2):                      # only the declared search allowances differ
        diff = {(s, k) for s in t for k in t[s] if t[s][k] != cfg[s][k]}
        assert diff == {("planner2d", "max_nodes"), ("planner2d", "max_wall_seconds"), ("skill2d", "max_plan_failures"),
                        ("skill2d", "max_direct_pairs")}
    plan = json.loads((G4A / "g4a_plan.json").read_text())
    assert cf.stable_hash({k: v for k, v in plan.items() if k != "plan_hash"}) == plan["plan_hash"]   # archive intact


def test_every_tier_starts_from_the_identical_archived_state(cfg):
    plan = teacher.make_plan(cfg, G4A, ROOT)
    assert [c["query_id"] for c in plan["cases"]] == list(teacher.ROOTS)
    assert plan["order"] == [["B1", q] for q in teacher.ROOTS] + [["B2", q] for q in teacher.ROOTS]
    for case in plan["cases"]:
        scene = scene_from_dict(case["scene"])
        q = data.make_query(cfg, case["query_id"], scene, "t0", case["goal_cell"], {}, "SAFE_RETREAT")
        assert q["hashes"] == case["hashes"] and q["learner"]["action"] == case["action"]
        st = ev.start(scene, q)
        assert list(st.q) == case["robot"]["q"] and st.gap == case["robot"]["gripper_gap_m"] and case["assignment"] == {}
        assert case["key"] == f"{case['query_id']}/audit/0/target"            # archived first-pass seed key
    assert plan["tiers"]["B0"]["grasp_family"] == plan["tiers"]["B2"]["grasp_family"] == 48


BURN = ("import subprocess, sys, time\n"
        "c = subprocess.Popen([sys.executable, '-c', 'while True: pass'])\n"
        "open(sys.argv[1], 'w').write(str(c.pid))\n"
        "t = time.time()\n"
        "while True: pass\n")


def test_cpu_guard_cancels_the_whole_tree_in_flight(tmp_path):
    pidfile = tmp_path / "child.pid"
    g = teacher.guard([sys.executable, "-c", BURN, str(pidfile)], cpu_limit=4.0, wall_limit=60.0,
                      heartbeat=tmp_path / "hb", margin=1.0, poll=0.1, cwd=tmp_path)
    child = int(pidfile.read_text())
    assert g["stop"] == "CPU_CENSORED" and 2.5 <= g["cpu_s"] <= 5.0 and g["wall_s"] < 30
    assert not psutil.pid_exists(child) or psutil.Process(child).status() == psutil.STATUS_ZOMBIE    # grandchild killed too
    w = teacher.guard([sys.executable, "-c", "import time; time.sleep(30)"], cpu_limit=100.0, wall_limit=1.0,
                      heartbeat=tmp_path / "hb", margin=1.0, poll=0.1, cwd=tmp_path)
    assert w["stop"] == "WALL_CENSORED"


def test_censored_evaluations_stay_unknown_and_never_become_negative(cfg, tmp_path, monkeypatch):
    plan = teacher.make_plan(cfg, G4A, ROOT)
    monkeypatch.setattr(teacher, "guard", lambda *a, **k: {"stop": "CPU_CENSORED", "pid": 1, "cpu_s": 10.0, "wall_s": 1.0,
                                                           "trigger_cpu_s": 870.0, "cpu_limit_s": 900.0, "overshoot_s": 0.0,
                                                           "active_phase": "carry3.1", "returncode": -9, "stderr_tail": ""})
    trace, spent, _ = teacher.run_schedule(plan, tmp_path, str(ROOT / "config.toml"), ROOT)
    assert len(trace) == 6 and all(e["status"] == data.UNKNOWN for e in trace)     # B2 still runs; no negative, no success
    assert spent == 60.0 and sum(e.get("pid") is not None for e in trace) <= teacher.LIMITS["max_evaluations"]


def test_certificate_reconciliation_separates_records_duplicates_and_overlaps():
    c = lambda k, ok=True: {"kind": k, "checker_accepted": ok, "checker_reasons": []}  # noqa: E731
    row = lambda r, sig, lab, certs: {"root_id": r, "query_id": r, "signature": sig, "first_pass": lab,  # noqa: E731
                                      "diagnostic_enriched": lab, "certificates": certs}
    rows = [row("a", [["o1", 2]], data.NEGATIVE, [c("GOAL_OVERLAP"), c("TARGET_PICK")]),      # two distinct
            row("a", [["o1", 3]], data.NEGATIVE, [c("GOAL_OVERLAP"), c("GOAL_OVERLAP")]),     # duplicate record
            row("b", [], data.NEGATIVE, [c("FIRST_MOVER"), c("STATIC_ENDPOINT_INVALID", False)]),
            row("b", [["o2", 4]], data.POSITIVE, [])]
    r = coverage.certificate_reconciliation(rows)
    assert r["accepted_records"] == 5 and r["rejected_records"] == 1 and r["unique_negative_assignments"] == 3
    assert r["duplicate_records"] == 1 and r["assignments_with_two_or_more_distinct_certificates"] == 1
    assert r["certificate_combinations"] == {"GOAL_OVERLAP+TARGET_PICK": 1, "GOAL_OVERLAP": 1, "FIRST_MOVER": 1}
    assert r["negatives_without_accepted_certificate"] == 0 and r["contradictions"] == 0


def test_call_accounting_handles_no_repair_abort_and_all_stay():
    ep = lambda kinds, cells, out: {"events": [{"kind": k} for k in kinds], "outcome": out,  # noqa: E731
                                    "commit": None if cells is None else {"cells": cells}, "target": None}
    prim = {"none": ep(["PROPOSE", "STATIC_CHECK", "REPAIR_PLAN", "FINISH"], None, "NO_REPAIR_WITNESS_WITHIN_BUDGET"),
            "abort": ep(["PROPOSE", "COMMIT", "RELOCATE", "REOBSERVE", "ABORT"], {"o1": 3}, "ABORTED"),
            "stay": ep(["PROPOSE", "STATIC_CHECK", "REPAIR_PLAN", "COMMIT", "TARGET_EVALUATE", "FINISH"], {}, "SUCCESS"),
            "move": ep(["PROPOSE", "COMMIT", "RELOCATE", "REOBSERVE", "TARGET_EVALUATE", "FINISH"], {"o1": 3}, "TARGET_UNRESOLVED")}
    a = coverage.call_accounting(prim)
    assert (a["completed_repair_episodes"], a["completed_with_exactly_one_call"], a["no_repair_with_zero_calls"],
            a["aborted_episodes"], a["all_stay_commits"]) == (2, 2, 1, 1, 1) and a["invariant_holds"]
    bad = {**prim, "early": ep(["PROPOSE", "TARGET_EVALUATE", "COMMIT", "TARGET_EVALUATE", "FINISH"], {}, "SUCCESS")}
    assert not coverage.call_accounting(bad)["invariant_holds"]


def test_witness_check_requires_exact_start_and_safe_retreat(cfg):
    plan = json.loads((G4A / "g4a_plan.json").read_text())
    q = next(x for x in plan["queries"] if x["query_id"] == "g4a_r05")
    scene = scene_from_dict(q["scene"])
    query = data.make_query(cfg, "g4a_r05", scene, "t0", q["goal_cell"], {}, "SAFE_RETREAT")
    npz = np.load(G4A / "arrays.npz")
    arr = {k.split("__")[1]: npz[k] for k in npz.files if k.startswith("g4a_r05.audit0.target__")}
    robot, st, act = ge.make_robot(cfg), ev.start(scene, query), query["learner"]["action"]
    assert teacher.check_witness(robot, cfg, scene, st, act, arr)["accepted"]
    n = int(sum(p == "retreat" for p in arr["phase"]))
    cut = {**arr, "q": arr["q"][:-n], "gap": arr["gap"][:-n], "phase": arr["phase"][:-n], "attached": arr["attached"][:-n]}
    assert not teacher.check_witness(robot, cfg, scene, st, act, cut)["ends_in_safe_retreat"]
    moved = {**arr, "q": arr["q"] + np.array([1e-3, 0, 0])}
    assert not teacher.check_witness(robot, cfg, scene, st, act, moved)["starts_at_archived_state"]
