"""P5B tests: deterministic outcome-blind schedule, static-valid alternative orders, and the run harness caps (call cap, wall cap,
predeclared confirmation reserve, resume) against a MOCK teacher (no physics).   python -m pytest tests/test_p5b_physical.py -q"""
import json, os, random, sys, time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "tests"))
import p5b_physical as B  # noqa: E402
import p5_order_audit as A  # noqa: E402
from test_p5_order_audit import rand_case  # noqa: E402

TABLES = Path(os.environ.get("P5_TABLES", "/home/naren/Desktop/boltzmann_lfd/.claude/worktrees/scaling2d/scaling2d_k12/G1"))
RUNS = Path(os.environ.get("P5_RUNS", "/home/naren/kgt3_runs"))
FROZEN = HERE / "reports/p5/P5B_SCHEDULE.json"


def test_alternative_orders_static_valid():
    rng, n = random.Random(3), 0
    for _ in range(300):
        c0, acts, chk = rand_case(rng, rng.randint(2, 6))
        good = B.good_masks(c0, acts, chk)
        assert good[0] == (A.brute(c0, acts, chk) is not None)
        if not good[0]:
            continue
        for k in range(len(acts)):
            if good[1 << k] and chk.pick(c0, acts[k][0]) and chk.place(c0, acts[k][0], acts[k][1]):
                o = B.order_first(c0, acts, chk, good, k); n += 1
                assert o[0] == k and sorted(o) == list(range(len(acts))) and A.run_order(c0, acts, o, chk)["status"] == "STATIC_VALID"
    assert n > 50


@pytest.mark.skipif(not FROZEN.exists() or not (TABLES / "MINK_TABLE_original.json").exists() or not (RUNS / "p4eval/verify.jsonl").exists(),
                    reason="frozen schedule / tables / P4 verify absent")
def test_schedule_deterministic_and_scoped(tmp_path):
    out = tmp_path / "s.json"
    B.schedule(str(HERE / "reports/p5/P5A_PER_ENDPOINT.jsonl"), str(RUNS / "p4eval/verify.jsonl"), str(RUNS / "dev/dev_public/dev_public.jsonl"), str(TABLES), str(out))
    a, b = json.loads(out.read_text()), json.loads(FROZEN.read_text())
    assert a["queue"] == b["queue"] and a["selected_endpoints"] == b["selected_endpoints"]       # rebuilt == frozen pre-query schedule
    Q = b["queue"]
    assert len({e["root_id"] for e in b["selected_endpoints"]}) == 6 and max(e["rank"] for e in b["selected_endpoints"]) <= 1
    assert all(q["K_certified"] <= 6 for q in Q) and all(q["static_status"] == "STATIC_VALID" for q in Q if not q["tier"].startswith("T5"))
    assert len({(q["root_id"], json.dumps(q["seq"])) for q in Q}) == len(Q)
    assert all(sorted(map(tuple, q["seq"])) == sorted(map(tuple, json.loads(q["endpoint_signature"]))) for q in Q)
    assert b["main_calls_needed"] <= b["main_call_budget"] == B.CAPS["teacher_calls"] - B.CAPS["confirm_reserve"]


def mock_job(a):
    """Mock teacher: X verified iff the first moved object index is even; 'slow' qids sleep (wall-cap test)."""
    code, priv, kind, qid, rid, seq, outd = a
    if "slow" in rid:
        time.sleep(30)
    y = int(seq[0][0] % 2 == 0) if kind == "X" else 1
    return {"qid": qid, "kind": kind, "root_id": rid, "seq": seq, "y": y, "teacher_status": "VERIFIED" if y else "UNKNOWN_PLANNER"}


def mock_yk(code, priv, q):
    return "k", "k"


def mk_sched(tmp, qs, **caps):
    S = {"caps": {**B.CAPS, **caps}, "queue": qs, "main_call_budget": caps.get("teacher_calls", 32) - caps.get("confirm_reserve", 4)}
    f = tmp / "S.json"; f.write_text(json.dumps(S)); Path(str(f) + ".sha256").write_text(B.sha(f) + "\n")
    return f


def q(i, obj, rid="r", m=7):
    return {"qid": f"q{i:02d}", "root_id": rid, "endpoint_signature": f"sig{i}", "seq": [[obj, 50]], "m": m, "reuse_existing_X": False,
            "y_reuse_teacher": "BXY_Y_TEACHER_V2_LONG"}


def test_run_caps_confirmations_and_resume(tmp_path):
    qs = [q(i, i) for i in range(10)]                       # even objects -> X positive: q00, q02, ...
    f = mk_sched(tmp_path, qs, teacher_calls=8, confirm_reserve=4, wall_s=60)
    B.run(str(f), "code", "priv", str(tmp_path / "run"), job=mock_job, yk=mock_yk, ctx_name="fork")
    L = A.jl(tmp_path / "run/ledger.jsonl")
    launches = [x for x in L if x["event"] == "LAUNCH"]
    assert len(launches) == 8                                # hard call cap (main budget 4 + confirmations 4)
    conf = [x for x in launches if x["confirm"]]
    assert len(conf) == 4 and len({x["sig"] for x in conf}) == 2 and {x["kind"] for x in conf} == {"XC", "YC"}
    assert [x["qid"] for x in launches if not x["confirm"]] == ["q00", "q01", "q02", "q03"]      # strict queue order, no adaptive picks
    B.run(str(f), "code", "priv", str(tmp_path / "run"), job=mock_job, yk=mock_yk, ctx_name="fork")
    assert sum(1 for x in A.jl(tmp_path / "run/ledger.jsonl") if x["event"] == "LAUNCH") == 8     # resume: cap persists, nothing relaunched


def test_run_wall_cap_aborts_as_unknown(tmp_path):
    f = mk_sched(tmp_path, [q(0, 1, rid="slow"), q(1, 3, rid="slow"), q(2, 5)], wall_s=2)
    t0 = time.time()
    B.run(str(f), "code", "priv", str(tmp_path / "run"), job=mock_job, yk=mock_yk, ctx_name="fork")
    L = A.jl(tmp_path / "run/ledger.jsonl")
    assert time.time() - t0 < 20 and any(x["event"] == "WALL_CAP" for x in L)
    ab = [x for x in L if x["event"] == "RESULT" and x["teacher_status"] == "ABORTED_CAP"]
    assert len(ab) == 2 and all(x["y"] is None for x in ab)


def test_y_reuse_precondition_fails_closed(tmp_path):
    f = mk_sched(tmp_path, [q(0, 0)])
    with pytest.raises(AssertionError):
        B.run(str(f), "code", "priv", str(tmp_path / "run"), job=mock_job, yk=lambda c, p, q_: ("a", "b"), ctx_name="fork")


def test_public_modules_never_import_p5b():
    for f_ in ("data.py", "models.py", "planner.py", "planner_r.py", "run_p4.py"):
        t = (HERE / f_).read_text()
        assert "p5b_physical" not in t and "teacher_long" not in t and "dev_records" not in t


def test_wall_cap_cumulative_across_resume(tmp_path):
    f = mk_sched(tmp_path, [q(0, 0), q(1, 2)], wall_s=50)
    (tmp_path / "run").mkdir()
    (tmp_path / "run/ledger.jsonl").write_text(json.dumps({"utc": "2026-11-22T00:00:00Z", "event": "BATCH_START"}) + "\n" +
                                               json.dumps({"utc": "2026-11-22T00:01:40Z", "event": "LAUNCH", "qid": "x", "kind": "X"}) + "\n")
    B.run(str(f), "code", "priv", str(tmp_path / "run"), job=mock_job, yk=mock_yk, ctx_name="fork")
    L = A.jl(tmp_path / "run/ledger.jsonl")
    assert any(x["event"] == "WALL_CAP" for x in L) and not any(x["event"] == "RESULT" for x in L)


def err_job(a):
    raise AttributeError("module 'planner' has no attribute 'plan'")


def test_worker_error_fails_closed(tmp_path):
    f = mk_sched(tmp_path, [q(i, i) for i in range(6)], workers=1)
    B.run(str(f), "code", "priv", str(tmp_path / "run"), job=err_job, yk=mock_yk, ctx_name="fork")
    L = A.jl(tmp_path / "run/ledger.jsonl")
    assert sum(1 for x in L if x["event"] == "LAUNCH") == 1 and any(x["event"] == "HARNESS_ABORT" for x in L)


def test_xclass_never_turns_unknown_into_negative():
    assert B.xclass("VERIFIED", None, 1) == "VERIFIED_FEASIBLE"
    assert B.xclass("VERIFIED", None, 0) != "VERIFIED_FEASIBLE"               # replay failure etc. is not a positive
    assert B.xclass("UNKNOWN_PLANNER", "NO_PLAN_FOUND", 0) == "UNKNOWN_PLANNER"
    assert B.xclass("CERTIFIED_INFEASIBLE", "CERTIFIED", 0) == "CERTIFIED_INFEASIBLE_SCOPED"
    assert B.xclass("ABORTED_CAP", None, None) == "UNKNOWN_ABORTED_CAP"
