"""BXY-P-MIN-COLLECT runner tests: preflight refusals (missing authorization, hash mismatch, source drift, runner drift, duplicate query),
worker resume / atomicity with a stubbed teacher, supervisor fault injection with fake worker processes (crash, CPU exhaustion, wall
expiry, interruption + resume, aggregate cap, orphaned worker, projection checkpoint) and result classification (corrupt, mismatched,
missing). No physical teacher call."""
import json
import shutil
import sys

import pytest

import bxy_data as bd

HAVE = (bd.DATA / "roots").exists()
pytestmark = pytest.mark.skipif(not HAVE, reason="local BD_GEN_V1 snapshot not present")
if HAVE:
    import bxy_pmin as PM
    import bxy_pmin_collect as C
    import bxy_teacher as T


@pytest.fixture
def plan(tmp_path):
    """A copy of the frozen design + lock and a fresh authorization in a scratch output directory."""
    for f in ("PMIN_DESIGN.json", "PMIN_LOCK.json"):
        shutil.copy(C.OUT / f, tmp_path / f)
    C.authorize(tmp_path)
    return tmp_path


def test_preflight_passes_on_the_frozen_plan(plan):
    p = C.preflight(plan, check_git=False)
    assert (p["x"], p["y"], len(p["worklist"]), p["reused"]) == (2165, 1807, 197, 116)


def test_preflight_refusals(plan, monkeypatch):
    C.auth_path(plan).rename(plan / "moved.json")
    with pytest.raises(C.PreflightError, match="missing execution authorization"):
        C.preflight(plan, check_git=False)
    (plan / "moved.json").rename(C.auth_path(plan))
    a = json.loads(C.auth_path(plan).read_text())
    C.auth_path(plan).write_text(json.dumps(a | {"runner_sha256": "0" * 64}))
    with pytest.raises(C.PreflightError, match="runner_sha256"):
        C.preflight(plan, check_git=False)
    C.auth_path(plan).write_text(json.dumps(a | {"limits": dict(C.LIMITS, cpu_s=1e9)}))
    with pytest.raises(C.PreflightError, match="limits"):
        C.preflight(plan, check_git=False)
    C.auth_path(plan).write_text(json.dumps(a))
    monkeypatch.setattr(bd, "data_hash", lambda: "sha256:other")
    with pytest.raises(C.PreflightError, match="dataset"):
        C.preflight(plan, check_git=False)
    monkeypatch.undo()
    real = PM.sources
    monkeypatch.setattr(PM, "sources", lambda: dict(real(), **{"bxy_teacher.py": "drift"}))
    with pytest.raises(C.PreflightError, match="source drift"):
        C.preflight(plan, check_git=False)
    monkeypatch.undo()
    W = C.worklist(C.design(plan))
    k = next(iter(W))
    monkeypatch.setattr(C, "worklist", lambda D: dict(W, **{k: W[k] + W[k][:1]}))
    with pytest.raises(C.PreflightError, match="duplicate query"):
        C.preflight(plan, check_git=False)


def test_authorization_is_immutable(plan, monkeypatch):
    monkeypatch.setattr(C, "LIMITS", dict(C.LIMITS, workers=16))
    with pytest.raises(FileExistsError):
        C.authorize(plan)


def stub_teacher(monkeypatch, calls, fail_at=None):
    def x(E, k, rec, seq, cache, out=None, legacy=None):
        calls.append(("x", tuple(seq)))
        if fail_at is not None and len(calls) == fail_at:
            raise RuntimeError("injected crash")
        return {"root": k, "x_key": T.xkey(k, rec, seq), "attempted": True, "observed": True, "y": 0, "teacher_status": "UNKNOWN_PLANNER"}

    def y(E, k, rec, seq, cache, out=None, legacy=None):
        calls.append(("y", tuple(seq)))
        if fail_at is not None and len(calls) == fail_at:
            raise RuntimeError("injected crash")
        return {"root": k, "y_key": T.ykey(k, rec, seq), "attempted": True, "observed": True, "y": 1, "teacher_status": "VERIFIED"}
    monkeypatch.setattr(T, "x_query", x)
    monkeypatch.setattr(PM, "y_query_counted", y)


def test_worker_order_atomic_resume_and_crash_marker(plan, monkeypatch):
    D = C.design(plan)
    k = min((r for r, v in C.worklist(D).items() if len(v) >= 3), key=lambda r: len(C.worklist(D)[r]))
    qs = C.worklist(D)[k]
    calls = []
    stub_teacher(monkeypatch, calls, fail_at=2)
    with pytest.raises(RuntimeError, match="injected"):
        C.worker(k, plan)
    d = plan / "results" / k
    assert (d / f"0000.{qs[0]['side']}.json").exists() and len(list(d.glob("*.inprogress"))) == 1   # crash leaves its marker
    C.censor(plan, k, "EXIT_1")
    r = json.loads((d / f"0001.{qs[1]['side']}.json").read_text())
    assert r["teacher_status"] == "CENSORED" and r["observed"] is False and r["y"] is None and r["design_key"] == qs[1]["key"]
    calls.clear()
    stub_teacher(monkeypatch, calls)
    C.worker(k, plan)
    assert len(calls) == len(qs) - 2                                                     # finished and censored queries never re-run
    R = C.rows(plan, D)
    mine = [R[(k, i, q["side"])] for i, q in enumerate(qs)]
    assert [m["design_key"] for m in mine] == [q["key"] for q in qs] and [m["item"] for m in mine] == list(range(len(qs)))
    assert all(m["runner"] == C.VERSION for m in mine)


def test_rows_classify_missing_corrupt_and_mismatched(plan, monkeypatch):
    D = C.design(plan)
    k = next(iter(C.worklist(D)))
    qs = C.worklist(D)[k]
    calls = []
    stub_teacher(monkeypatch, calls)
    C.worker(k, plan)
    d = plan / "results" / k
    (d / f"0000.{qs[0]['side']}.json").write_text("{not json")
    r1 = json.loads((d / f"0001.{qs[1]['side']}.json").read_text())
    (d / f"0001.{qs[1]['side']}.json").write_text(json.dumps(r1 | {f"{qs[1]['side']}_key": "X2:wrong"}))
    R = C.rows(plan, D)
    assert R[(k, 0, qs[0]["side"])]["teacher_status"] == "CORRUPT_RESULT" and R[(k, 0, qs[0]["side"])]["y"] is None
    assert R[(k, 1, qs[1]["side"])]["teacher_status"] == "CORRUPT_RESULT"
    other = next(r for r in C.worklist(D) if r != k)
    assert R[(other, 0, C.worklist(D)[other][0]["side"])]["teacher_status"] == "NOT_ATTEMPTED"


FAKE = {"ok": "pass",
        "crash": "import sys,json,pathlib; d=pathlib.Path(sys.argv[2])/'results'/sys.argv[1]; d.mkdir(parents=True,exist_ok=True); "
                 "(d/'0000.x.inprogress').write_text(json.dumps({'key':'K'})); sys.exit(3)",
        "spin": "import sys,json,pathlib; d=pathlib.Path(sys.argv[2])/'results'/sys.argv[1]; d.mkdir(parents=True,exist_ok=True); "
                "(d/'0000.x.inprogress').write_text(json.dumps({'key':'K'}))\nwhile True: pass",
        "sleep": "import sys,json,time,pathlib; d=pathlib.Path(sys.argv[2])/'results'/sys.argv[1]; d.mkdir(parents=True,exist_ok=True); "
                 "(d/'0000.x.inprogress').write_text(json.dumps({'key':'K'})); time.sleep(60)",
        "term": "import os,sys,json,time,signal,pathlib; d=pathlib.Path(sys.argv[2])/'results'/sys.argv[1]; d.mkdir(parents=True,exist_ok=True); "
                "(d/'0000.x.inprogress').write_text(json.dumps({'key':'K'})); os.kill(os.getppid(), signal.SIGTERM); time.sleep(60)"}


def fake(out, kind):
    return lambda k: [sys.executable, "-c", FAKE[kind if isinstance(kind, str) else kind(k)], k, str(out)]


L0 = {"cpu_s": 100.0, "root_cpu_s": 50.0, "workers": 2, "wall_s": 60.0, "min_allow": 1.0}


def censored(out, k):
    return json.loads((out / "results" / k / "0000.x.json").read_text())


def test_supervisor_crash_and_cpu_exhaustion_are_censored(tmp_path):
    r = C.supervise(tmp_path, ["a", "b"], dict(L0, root_cpu_s=2.0), fake(tmp_path, lambda k: "crash" if k == "a" else "spin"), poll=0.05, gates=False)
    ev = {e["root"]: e for e in C.ledger(tmp_path) if e["event"] == "finish"}
    assert ev["a"]["exit"] == "EXIT_3" and ev["b"]["exit"] == "CPU_CAP(RLIMIT_CPU)" and ev["b"]["cpu_s"] <= 2.0 + 1e-6
    assert censored(tmp_path, "a")["teacher_status"] == censored(tmp_path, "b")["teacher_status"] == "CENSORED"
    assert r["halted"] is None and not list(tmp_path.rglob("*.inprogress"))


def test_supervisor_aggregate_cap_is_hard_from_the_first_worker(tmp_path):
    r = C.supervise(tmp_path, ["a", "b", "c"], dict(L0, cpu_s=2.5, root_cpu_s=50.0, workers=1), fake(tmp_path, "spin"), poll=0.05, gates=False)
    starts = [e for e in C.ledger(tmp_path) if e["event"] == "start"]
    assert starts[0]["allow"] == 2.5 and r["spent_cpu_s"] <= 2.5 + 1e-6 and r["halted"] == "AGGREGATE_CPU_CAP"
    assert r["roots_not_started"] == ["b", "c"] or r["roots_not_started"] == ["c"]


def test_supervisor_wall_cap_and_interrupt_resume(tmp_path):
    r = C.supervise(tmp_path, ["a"], dict(L0, wall_s=1.5), fake(tmp_path, "sleep"), poll=0.05, gates=False)
    assert r["halted"] == "WALL_CAP" and censored(tmp_path, "a")["censor_reason"] == "WALL_CAP"
    r2 = C.supervise(tmp_path, ["a"], dict(L0, wall_s=1.5), fake(tmp_path, "ok"), poll=0.05, gates=False)
    assert r2["halted"] == "WALL_CAP" and len([e for e in C.ledger(tmp_path) if e["event"] == "start"]) == 1   # wall is global across resumes
    t2 = tmp_path / "int"
    r = C.supervise(t2, ["a", "b"], dict(L0, workers=1), fake(t2, "term"), poll=0.05, gates=False)
    assert r["halted"] == "INTERRUPTED" and r["roots_not_started"] == ["b"] and censored(t2, "a")["censor_reason"] == "INTERRUPTED"
    r = C.supervise(t2, ["a", "b"], dict(L0, workers=1), fake(t2, "ok"), poll=0.05, gates=False)
    fin = [e for e in C.ledger(t2) if e["event"] == "finish"]
    assert r["halted"] is None and [e["root"] for e in fin] == ["a", "a", "b"] and fin[-1]["exit"] is None
    r = C.supervise(t2, ["a", "b"], dict(L0, workers=1), fake(t2, "ok"), poll=0.05, gates=False)
    assert len([e for e in C.ledger(t2) if e["event"] == "start"]) == 3                 # deterministic resume: nothing re-run


def test_supervisor_orphan_charged_and_projection_checkpoint(tmp_path):
    (tmp_path / "results" / "a").mkdir(parents=True)
    (tmp_path / "results" / "a" / "0000.x.inprogress").write_text(json.dumps({"key": "K"}))
    C.append(tmp_path, {"event": "start", "root": "a", "allow": 7.0, "pid": 1, "t": 0})
    r = C.supervise(tmp_path, ["a"], dict(L0, root_cpu_s=7.5), fake(tmp_path, "ok"), poll=0.05, gates=False)
    fin = [e for e in C.ledger(tmp_path) if e["event"] == "finish"]
    assert fin[0]["exit"] == "ORPHAN_CHARGED_ALLOWANCE" and fin[0]["cpu_s"] == 7.0 and censored(tmp_path, "a")["censor_reason"] == "SUPERVISOR_LOST"
    assert r["spent_cpu_s"] >= 7.0
    t2 = tmp_path / "cp"
    ks = [f"r{i:02d}" for i in range(25)]
    r = C.supervise(t2, ks, dict(L0, workers=1, cpu_s=1000.0), fake(t2, "ok"), est={k: 1e-6 if i < 20 else 1e3 for i, k in enumerate(ks)}, poll=0.01, gates=False)
    assert r["halted"].startswith("PROJECTION_CHECKPOINT") and len([e for e in C.ledger(t2) if e["event"] == "start"]) == 20


def test_ramp_schedule():
    assert [max(n for f, n in C.RAMP if d >= f) for d in (0, 3, 4, 11, 12, 100)] == [2, 2, 4, 4, 8, 8]
