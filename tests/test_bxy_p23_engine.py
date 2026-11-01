"""BXY-P23 engine smoke tests with a deterministic MOCK teacher on synthetic designs in tmp directories (no real root, no teacher query):
duplicate supervisors, kill + restart with explicit recovery, partial results, duplicate workers, corrupt results, out-of-order finishes,
an exhausted root, the aggregate budget stop, mismatched scene identity, wall-cap interruption + resume, and the hash-chained ledger."""
import fcntl
import hashlib
import json
import os
import signal
import subprocess as sp
import sys
import time

import pytest

import bxy_p23_engine as E

L0 = {"cpu_s": 600.0, "root_cpu_s": 60.0, "workers": 3, "wall_s": 600.0, "min_allow": 1.0}


def make(tmp, n_roots=3, n_q=4, names=None):
    out = tmp / "eng"
    (out / "roots").mkdir(parents=True)
    D = {"root_order": [], "roots": {}}
    for j, k in enumerate(names or [f"r{j}" for j in range(n_roots)]):
        rec = {"scene": {"objects": [j]}, "goal_cell": j, "q0": [0.0, 0.0, 0.0]}
        (out / "roots" / f"{k}.json").write_text(json.dumps(rec))
        qs = {f"{k}:{s}:{i}": {"side": s, "seq": [["b0", i]]} for i in range(n_q // 2) for s in ("x", "y")}
        D["roots"][k] = {"record_sha256": E.record_sha(rec), "queries": qs}
        D["root_order"].append(k)
    (out / "DESIGN.json").write_text(json.dumps(D))
    return out


def ystar(key):
    return int(hashlib.sha256(key.encode()).hexdigest()[0], 16) % 2


def status_of(out):
    R = E.rows(out)
    return {key: r["status"] for key, r in R.items()}, R


def test_clean_run_reconstruction_and_no_relaunch(tmp_path):
    out = make(tmp_path)
    r = E.supervise(out, L0)
    st, R = status_of(out)
    assert r["halted"] is None and set(st.values()) == {"OBSERVED"} and len(st) == 12
    assert all(v["y"] == ystar(v["design_key"]) for v in R.values())
    snap = {p: p.read_bytes() for p in out.glob("results/*/*.json")}
    r2 = E.supervise(out, L0)
    assert r2["not_started"] == [] and {p: p.read_bytes() for p in out.glob("results/*/*.json")} == snap
    a = E.audit(out)
    assert a["ledger"]["ok"] and not a["inprogress_left"] and not a["reservations_left"]
    assert E.ledger(out)[0]["event"] == "supervisor_start"


def test_duplicate_supervisor_refused_in_process_and_across_processes(tmp_path):
    out = make(tmp_path)
    with E.Supervisor(out):
        with pytest.raises(E.EngineRefusal, match="DUPLICATE_SUPERVISOR"):
            E.Supervisor(out).__enter__()
        code = ("import bxy_p23_engine as E, sys\ntry:\n    E.Supervisor(sys.argv[1]).__enter__()\nexcept E.EngineRefusal as e:\n"
                "    print(e); sys.exit(9)")
        p = sp.run([sys.executable, "-c", code, str(out)], capture_output=True, text=True)
        assert p.returncode == 9 and "DUPLICATE_SUPERVISOR" in p.stdout
    with E.Supervisor(out):
        pass                                                               # released cleanly -> a new owner may start


def test_crash_restart_requires_explicit_recovery_then_resumes_unattempted_only(tmp_path):
    out = make(tmp_path, n_roots=3, n_q=6)
    code = ("import bxy_p23_engine as E, sys, json\nE.supervise(sys.argv[1], json.loads(sys.argv[2]), opts={'sleep_s': 0.4})")
    env = dict(os.environ, BXY_ENGINE_HEARTBEAT_S="0.1")
    p = sp.Popen([sys.executable, "-c", code, str(out), json.dumps(L0)], start_new_session=True, env=env)
    t0 = time.time()
    while not list(out.glob("results/*/*.json")) and time.time() - t0 < 30:
        time.sleep(0.05)
    os.killpg(p.pid, signal.SIGKILL)                                       # machine-crash analogue: supervisor and workers die together
    p.wait()
    time.sleep(0.3)
    done = {q: q.read_bytes() for q in out.glob("results/*/*.json")}
    assert done and list(out.glob("results/*/*.inprogress"))
    with pytest.raises(E.EngineRefusal, match="LIVE_OWNER_HEARTBEAT"):
        E.Supervisor(out, stale_s=60).__enter__()
    with pytest.raises(E.EngineRefusal, match="STALE_OWNER_REQUIRES_RECOVERY"):
        E.Supervisor(out, stale_s=0.0).__enter__()
    owner = json.loads((out / "SUPERVISOR.json").read_text())["owner"]
    old = E.STALE_S
    E.STALE_S = 0.0
    try:
        rec = E.recover(out, owner, "test: crash of supervisor + workers")
    finally:
        E.STALE_S = old
    assert rec["recovered_roots"]
    led = E.ledger(out)
    allow = {e["root"]: e["allow"] for e in led if e["event"] == "start"}
    assert all(0 < e["cpu_s"] <= allow[e["root"]] and e["bound"].startswith("min(") for e in led if e["event"] == "recovery")  # beat-based bound
    r = E.supervise(out, L0)
    st, R = status_of(out)
    assert r["halted"] is None and "UNATTEMPTED" not in st.values()
    assert sum(v == "CENSORED" for v in st.values()) == len(rec["recovered_roots"])            # the interrupted query of each root
    assert all(q.read_bytes() == b for q, b in done.items())                                   # finished rows never rewritten
    assert E.verify_ledger(out)["ok"]


def test_recover_refuses_while_a_worker_holds_its_root_lock(tmp_path, monkeypatch):
    out = make(tmp_path)
    (out / "reservations").mkdir()
    (out / "reservations" / "r0.json").write_text(json.dumps({"root": "r0", "owner": "dead", "allow": 10.0}))
    E.jw(out / "SUPERVISOR.json", {"owner": "dead", "state": "RUNNING", "heartbeat": time.time() - 999})
    (out / "locks").mkdir()
    fd = os.open(out / "locks" / "r0.lock", os.O_RDWR | os.O_CREAT)
    fcntl.flock(fd, fcntl.LOCK_EX)
    monkeypatch.setattr(E, "STALE_S", 1.0)
    with pytest.raises(E.EngineRefusal, match="RECOVER_WORKER_ALIVE"):
        E.recover(out, "dead", "x")
    with pytest.raises(E.EngineRefusal, match="RESERVATIONS_PRESENT|STALE_OWNER"):
        E.Supervisor(out, stale_s=1.0).__enter__()
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)
    assert E.recover(out, "dead", "x")["recovered_roots"] == ["r0"]
    assert [e["cpu_s"] for e in E.ledger(out) if e["event"] == "recovery"] == [10.0]           # no beat -> full allowance


def test_partial_results_after_worker_crash_are_censored_not_zero_and_not_relaunched(tmp_path):
    out = make(tmp_path, n_roots=2, n_q=6)
    E.supervise(out, L0, opts={"crash_at": 2})
    st, R = status_of(out)
    for k in ("r0", "r1"):
        s = [st[(k, i, side)] for (kk, i, side) in sorted(st) if kk == k]
        assert s[:2] == ["OBSERVED", "OBSERVED"] and s[2] == "CENSORED" and set(s[3:]) == {"UNATTEMPTED"}
        assert R[(k, 2, [sd for (kk, i, sd) in st if kk == k and i == 2][0])]["y"] is None
    assert E.supervise(out, L0)["not_started"] == []                       # EXIT_3 is final: no silent relaunch
    assert sum(e["event"] == "start" for e in E.ledger(out)) == 2


def test_duplicate_worker_requests_refused_without_writes(tmp_path):
    out = make(tmp_path)
    (out / "reservations").mkdir()
    (out / "reservations" / "r0.json").write_text(json.dumps({"root": "r0", "owner": "own", "allow": 10.0}))
    assert E.worker(out, "r0", "someone-else") == E.EXIT_DUPLICATE                              # not the reservation owner
    assert E.worker(out, "r1", "own") == E.EXIT_DUPLICATE                                       # no reservation at all
    fd = os.open(out / "locks" / "r0.lock", os.O_RDWR | os.O_CREAT)
    fcntl.flock(fd, fcntl.LOCK_EX)
    p = sp.run([sys.executable, E.__file__, "worker", str(out), "r0", "own", "mock", "{}"])
    assert p.returncode == E.EXIT_DUPLICATE and not list(out.glob("results/**/*.json"))
    os.close(fd)


def test_corrupt_rows_detected_and_never_overwritten(tmp_path):
    out = make(tmp_path)
    E.supervise(out, L0)
    f = sorted(out.glob("results/r1/*.json"))[0]
    d = json.loads(f.read_text())
    d["row"]["y"] = 1 - d["row"]["y"]
    f.write_text(json.dumps(d))
    st, _ = status_of(out)
    assert list(st.values()).count("CORRUPT") == 1 and E.audit(out)["corrupt_is_custody_event"]
    assert E.write_once(f, {"y": 0}) is False and json.loads(f.read_text()) == d


def test_out_of_order_finishes_account_every_root_once(tmp_path):
    mult = lambda k: 1 + int(hashlib.sha256(k.encode()).hexdigest()[:2], 16) % 3  # noqa: E731
    names = sorted([f"q{i}" for i in range(40)], key=mult, reverse=True)
    names = [names[0], next(n for n in names if mult(n) == 1), next(n for n in names if mult(n) == 2)]
    out = make(tmp_path, names=names, n_q=2)
    E.supervise(out, L0, opts={"sleep_s": 0.3})
    led = E.ledger(out)
    starts, fins = [e["root"] for e in led if e["event"] == "start"], [e["root"] for e in led if e["event"] == "finish"]
    assert sorted(starts) == sorted(fins) == sorted(names) and starts != fins
    st, R = status_of(out)
    assert set(st.values()) == {"OBSERVED"} and all(v["y"] == ystar(v["design_key"]) for v in R.values())


def test_exhausted_root_cpu_cap_censors_current_and_leaves_rest_unattempted(tmp_path):
    out = make(tmp_path, n_roots=1, n_q=6)
    E.supervise(out, L0 | {"root_cpu_s": 2.0}, opts={"burn_s": 5.0})
    st, _ = status_of(out)
    assert list(st.values()).count("CENSORED") == 1 and list(st.values()).count("UNATTEMPTED") == 5
    fin = [e for e in E.ledger(out) if e["event"] == "finish"]
    assert fin[0]["exit"] == "CPU_CAP(RLIMIT_CPU)" and fin[0]["cpu_s"] <= 2.5
    assert {r["reason"] for r in E.rows(out).values() if r["status"] == "UNATTEMPTED"} == {"CPU_CAP(RLIMIT_CPU)"}


def test_aggregate_budget_stop_never_exceeds_cap(tmp_path):
    out = make(tmp_path, n_roots=5, n_q=4)
    E.charge(out, "construction", 1.0, 1.0, "synthetic")
    r = E.supervise(out, L0 | {"cpu_s": 4.0, "root_cpu_s": 2.0, "workers": 1}, opts={"burn_s": 0.4})
    assert r["halted"] == "AGGREGATE_CPU_CAP" and r["not_started"]
    assert E.spent(out)["cpu_s"] <= 4.0 + 0.5
    st = E.rows(out)
    assert all(st[(k, i, s)]["status"] == "UNATTEMPTED" for (k, i, s) in st if k in r["not_started"])
    assert {e["root"] for e in E.ledger(out) if e["event"] == "not_started"} == set(r["not_started"])


def test_scene_identity_mismatch_stops_and_wrong_key_rows_are_unobserved(tmp_path):
    out = make(tmp_path, n_roots=3)
    (out / "roots" / "r0.json").write_text(json.dumps({"scene": "tampered"}))
    r = E.supervise(out, L0 | {"workers": 1})
    assert r["halted"] == "IDENTITY_MISMATCH" and r["not_started"] == ["r1", "r2"]
    out2 = make(tmp_path / "b", n_roots=1)
    E.supervise(out2, L0, opts={"wrong_key_at": 1})
    st, R = status_of(out2)
    bad = [v for v in R.values() if v.get("teacher_status") == "IDENTITY_MISMATCH"]
    assert len(bad) == 1 and bad[0]["status"] == "CENSORED" and bad[0]["y"] is None


def test_wall_cap_interrupts_and_resume_continues_from_first_launch(tmp_path):
    out = make(tmp_path, n_roots=2, n_q=6)
    r = E.supervise(out, L0 | {"wall_s": 1.0}, opts={"sleep_s": 0.4})
    assert r["halted"] == "WALL_CAP"
    assert E.supervise(out, L0 | {"wall_s": 1.0})["halted"] == "WALL_CAP"   # wall counted from the first launch across sessions
    r = E.supervise(out, L0)
    st, _ = status_of(out)
    assert r["halted"] is None and "UNATTEMPTED" not in st.values() and "CENSORED" in st.values()


def test_ledger_tamper_detected_and_mock_never_imports_teacher(tmp_path):
    out = make(tmp_path, n_roots=1)
    E.supervise(out, L0)
    f = out / "LEDGER.jsonl"
    lines = f.read_text().splitlines()
    e = json.loads(lines[2])
    e["cpu_s"] = 0.0
    lines[2] = json.dumps(e, sort_keys=True, separators=(",", ":"))
    f.write_text("\n".join(lines) + "\n")
    assert not E.verify_ledger(out)["ok"]
    out2 = make(tmp_path / "b", n_roots=1)
    (out2 / "reservations").mkdir()
    (out2 / "reservations" / "r0.json").write_text(json.dumps({"root": "r0", "owner": "o", "allow": 5}))
    code = "import sys, bxy_p23_engine as E\nE.worker(sys.argv[1], 'r0', 'o')\nprint(any(m in sys.modules for m in ('bxy_teacher', 'bxy_pmin', 'bd_2d')))"
    assert sp.run([sys.executable, "-c", code, str(out2)], capture_output=True, text=True).stdout.strip() == "False"
