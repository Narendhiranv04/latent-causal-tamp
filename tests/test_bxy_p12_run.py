"""BXY-P12 runner tests: the resumable trainer equals the frozen bxy_p11.fit bitwise (uninterrupted and interrupted + resumed), authorization /
hash-drift / roster refusals, lambda* rule, fair launch order, real-data run root custody, and fault injection on SYNTHETIC roots only
(SIGTERM, crash, corrupted output, per-run CPU cap, aggregate CPU cap, wall cap across sessions, timeout, memory pressure, ramp, parent
killed -> orphan-free deterministic resume). No real-data optimizer step happens here."""
import json
import os
import signal
import subprocess as sp
import sys
import time
from pathlib import Path

import numpy as np
import pytest
import torch

import bxy_data as bd

HAVE = (bd.DATA / "roots").exists() and Path("runs/approach_b/bxy_pmin_v1/BXY_SIDECAR_V2_PMIN.json").exists() and \
    Path("runs/approach_b/bxy_p11_1_v1/TRAINING_DESIGN_P11_1.json").exists()
pytestmark = pytest.mark.skipif(not HAVE, reason="local BD_GEN_V1 snapshot / P-min sidecar / P11.1 design not present")
if HAVE:
    import bxy_p11 as P
    import bxy_p12_run as R

LIM = {"aggregate_cpu_s": 10 ** 6, "per_run_cpu_s": 10 ** 5, "workers": 8, "wall_s": 10 ** 6, "torch_threads": 1}
NORES = {"evaluation_cpu_s": 0, "evaluation_wall_s": 0}


def spec(i, arm="XY-quadratic", seed=0, lam=0.3, n=24):
    return {"id": f"split/{arm}/lam{lam}/s{seed}/{i}", "phase": "SPLIT", "arm": arm, "lambda_J": lam, "seed": seed, "train": "syn", "early_stop": "syn",
            "max_updates": n}


def runner(tmp, runs, faults=None, monkeypatch=None, limits=None, **kw):
    (tmp / "SYN_ROSTER.json").write_text(json.dumps(runs))
    if monkeypatch is not None:
        monkeypatch.setenv("BXY_P12_FAULT", json.dumps(faults or {}))
    return R.Runner(tmp, limits=(limits or LIM) | {"runs": len(runs)}, reserve=NORES, synthetic=True, tick=0.1, check_git=False,
                    mem=kw.pop("mem", lambda: 64.0), **kw)


def reference(s):
    tr, es, pr, _ = R.syn_data(s)
    m, info = R.fit_resumable(s["arm"], s["seed"], tr, es, s["lambda_J"], R.run_cfg(s, True))
    return m.state_dict(), info["history"], {sv["key"]: R.predict_root(m, sv) for sv in pr}


def same_as_reference(tmp, s):
    rd = tmp / "runs" / R.safe(s["id"])
    sd, hist, preds = reference(s)
    got = torch.load(rd / "best.pt", weights_only=False)
    return all(torch.equal(got[k], sd[k]) for k in sd) and json.loads((rd / "history.json").read_text()) == json.loads(json.dumps(hist)) and \
        json.loads((rd / "predictions.json").read_text()) == json.loads(json.dumps(preds))


# ------------------------------------------------------------------ trainer identity
@pytest.mark.parametrize("arm", ["XY-quadratic", "DIRECT"])
def test_resumable_trainer_equals_frozen_fit_and_resumes_bitwise(arm):
    tr, es, _, _ = R.syn_data({})
    cfg = P.TRAIN | {"max_updates": 14, "eval_every": 2, "batch_roots": 3, "patience_evals": 4}
    m0, r0 = P.fit(arm, 1, tr, es, 0.3, cfg)
    m1, r1 = R.fit_resumable(arm, 1, tr, es, 0.3, cfg)
    snaps = {}
    assert R.fit_resumable(arm, 1, tr, es, 0.3, cfg, hook=lambda u, s: u == 5 and snaps.setdefault(5, s()) is not None) is None
    m2, r2 = R.fit_resumable(arm, 1, tr, es, 0.3, cfg, state=snaps[5])
    for m, r in ((m1, r1), (m2, r2)):
        assert all(torch.equal(a, b) for a, b in zip(m0.state_dict().values(), m.state_dict().values()))
        assert r["history"] == r0["history"] and {k: v for k, v in r.items() if k != "history"} == {k: v for k, v in r0.items() if k != "history"}


def test_lambda_selection_rule_and_blocking():
    es = {("A", l, s): {0.1: 2.0, 0.3: 1.0, 1.0: 1.0005}[l] for l in (0.1, 0.3, 1.0) for s in (0, 1, 2)}
    es |= {("B", l, s): {0.1: 1.0005, 0.3: 1.0, 1.0: 3.0}[l] for l in (0.1, 0.3, 1.0) for s in (0, 1, 2)}
    es |= {("C", l, s): 1.0 for l in (0.1, 0.3) for s in (0, 1, 2)}
    sel = R.lambda_select(es, (0.1, 0.3, 1.0), (0, 1, 2))
    assert sel["A"]["lambda"] == 0.3 and sel["B"]["lambda"] == 0.1 and sel["C"]["lambda"] is None


# ------------------------------------------------------------------ authorization, roster, custody
def test_authorization_refusals(tmp_path, monkeypatch):
    with pytest.raises(PermissionError, match="no authorization"):
        R.verify_auth(tmp_path, check_git=False)
    good = R.auth_values() | {"authorized": True}
    (tmp_path / R.AUTH_NAME).write_text(json.dumps(good | {"authorized": False}))
    with pytest.raises(PermissionError, match="does not authorize"):
        R.verify_auth(tmp_path, check_git=False)
    (tmp_path / R.AUTH_NAME).write_text(json.dumps(good | {"limits": R.LIMITS | {"aggregate_cpu_s": 10 ** 9}}))
    with pytest.raises(PermissionError, match="limits"):
        R.verify_auth(tmp_path, check_git=False)
    (tmp_path / R.AUTH_NAME).write_text(json.dumps(good))
    assert R.verify_auth(tmp_path, check_git=False)["authorized"]
    real = R.auth_values
    monkeypatch.setattr(R, "auth_values", lambda: real() | {"sources": {**real()["sources"], "bxy_p11.py": "drift"}})
    with pytest.raises(PermissionError, match="sources"):
        R.verify_auth(tmp_path, check_git=False)
    monkeypatch.setattr(R, "auth_values", lambda: real() | {"p11_1_design_sha256": "0" * 64})
    with pytest.raises(PermissionError, match="p11_1_design"):
        R.verify_auth(tmp_path, check_git=False)
    with pytest.raises(PermissionError):
        R.Runner(tmp_path / "none", check_git=False)


def test_roster_identity_duplicates_and_count():
    d = R.design()
    assert len(R.check_roster(d["roster"])) == 108
    with pytest.raises(ValueError, match="duplicate"):
        R.check_roster(d["roster"][:107] + [d["roster"][0]])
    with pytest.raises(ValueError, match="107"):
        R.check_roster(d["roster"][:107])


def test_fair_launch_order():
    d = R.design()
    o = R.queue_order(d["roster"])
    by = {r["id"]: r for r in d["roster"]}
    assert len(o) == len(set(o)) == 108 and all(by[i]["phase"] == "SPLIT" for i in o[:33]) and [by[i]["seed"] for i in o[:33]] == sorted(by[i]["seed"] for i in o[:33])
    cv = [by[i] for i in o[33:]]
    blocks = [cv[i:i + 5] for i in range(0, 75, 5)]
    assert all(len({r["arm"] for r in b}) == 5 and len({(r["seed"], r["train"]) for r in b}) == 1 for b in blocks)
    assert len({b[-1]["arm"] for b in blocks}) == 5                         # no arm is always last


def test_real_run_root_custody():
    d = R.design()
    test = {k for k, r in bd.roots().items() if bd.split_of(r) == "test"}
    held = []
    for s in d["roster"]:
        x = R.root_sets(s, d)
        assert not set(x["train"]) & set(x["es"]) and not (set(x["train"]) | set(x["es"]) | set(x["predict"])) & test
        if s["phase"] == "CROSSFIT":
            assert not (set(x["train"]) | set(x["es"])) & set(x["predict"])
            held += x["predict"] if s["arm"] == "DIRECT" and s["seed"] == 0 else []
        else:
            assert x["predict"] == x["es"] == sorted(d["custody"]["val"]) and len(x["train"]) == 176
    assert sorted(held) == sorted(d["custody"]["train"] + d["custody"]["val"])
    tr, es, pr, sets = R.real_data(next(s for s in d["roster"] if s["phase"] == "CROSSFIT"))
    assert all(isinstance(sv, dict) and "R" in sv for sv in pr) and not {sv["key"] for sv in pr} & {x[0]["key"] for x in tr + es}
    for sv in pr:
        P.check_scorer(sv)


# ------------------------------------------------------------------ fault injection (synthetic roots only)
def test_end_to_end_sigterm_crash_corrupt_resume_bitwise(tmp_path, monkeypatch):
    runs = [spec(0), spec(1, seed=1), spec(2, arm="XY-uncoupled-SA", seed=2), spec(3, arm="DIRECT", lam=0.0)]
    faults = {runs[1]["id"]: "term@10", runs[2]["id"]: "crash@14", runs[3]["id"]: "corrupt"}
    s = runner(tmp_path, runs, faults, monkeypatch).run()
    assert s["counts"] == {"DONE": 4}, s
    L = json.loads((tmp_path / "LEDGER.json").read_text())
    reasons = {r: [a["reason"] for a in L["runs"][r]["attempts"]] for r in L["runs"]}
    assert reasons[runs[0]["id"]] == ["done"] and reasons[runs[1]["id"]] == ["interrupted", "done"]
    assert reasons[runs[2]["id"]] == ["crash(13)", "done"] and reasons[runs[3]["id"]] == ["corrupt_output", "done"]
    assert json.loads((tmp_path / "runs" / R.safe(runs[1]["id"]) / "RESULT.json").read_text())["resumed_from_update"] == 10
    assert json.loads((tmp_path / "runs" / R.safe(runs[2]["id"]) / "RESULT.json").read_text())["resumed_from_update"] == 12
    assert (tmp_path / "quarantine").exists() and all(same_as_reference(tmp_path, x) for x in runs)
    assert s["aggregate_cpu_s"] == pytest.approx(sum(r["cpu"] for r in L["runs"].values())) and all(a["cpu"] > 0 for r in L["runs"].values() for a in r["attempts"])
    with pytest.raises(FileExistsError):                                    # immutable result record
        open(tmp_path / "runs" / R.safe(runs[0]["id"]) / "RESULT.json", "x")
    assert R.worker_pids(tmp_path) == []


def test_per_run_cpu_cap_is_hard_and_leaves_no_result(tmp_path, monkeypatch):
    runs = [spec(0, n=10 ** 6)]
    s = runner(tmp_path, runs, {runs[0]["id"]: "spin@4"}, monkeypatch, limits=LIM | {"per_run_cpu_s": 8}, grace=3).run()
    L = json.loads((tmp_path / "LEDGER.json").read_text())["runs"][runs[0]["id"]]
    assert s["statuses"][runs[0]["id"]] == "INCOMPLETE_CPU_CAP" and L["cpu"] <= 8.0 and not (tmp_path / "runs" / R.safe(runs[0]["id"]) / "RESULT.json").exists()
    assert (tmp_path / "runs" / R.safe(runs[0]["id"]) / "state.pt").exists()


def test_aggregate_cap_reserves_before_launch(tmp_path, monkeypatch):
    runs = [spec(i, seed=i) for i in range(3)]
    s = runner(tmp_path, runs, {}, monkeypatch, limits=LIM | {"per_run_cpu_s": 60, "aggregate_cpu_s": 61}).run()
    L = json.loads((tmp_path / "LEDGER.json").read_text())
    assert [s["statuses"][r["id"]] for r in runs] == ["DONE", "NOT_LAUNCHED_BUDGET", "NOT_LAUNCHED_BUDGET"] and s["stop"] == "aggregate_cpu"
    assert s["aggregate_cpu_s"] <= 61 and max(e["running"] for e in L["events"] if e["kind"] == "launch") == 1   # never 2 reservations at once


def test_wall_cap_is_durable_across_sessions(tmp_path, monkeypatch):
    runs = [spec(0, n=10 ** 6), spec(1, seed=1)]
    s = runner(tmp_path, runs, {runs[0]["id"]: "hang@4"}, monkeypatch, limits=LIM | {"wall_s": 8, "workers": 1}).run()
    assert s["statuses"][runs[0]["id"]] == "INCOMPLETE_WALL" and s["statuses"][runs[1]["id"]] == "NOT_LAUNCHED_WALL" and s["wall_used_s"] >= 8
    s2 = runner(tmp_path, runs, {}, monkeypatch, limits=LIM | {"wall_s": 8, "workers": 1}).run()
    L = json.loads((tmp_path / "LEDGER.json").read_text())
    assert s2["stop"] == "wall" and len(L["runs"][runs[0]["id"]]["attempts"]) == 1 and len(L["sessions"]) == 2


def test_timeout_then_deterministic_retry(tmp_path, monkeypatch):
    runs = [spec(0)]
    s = runner(tmp_path, runs, {runs[0]["id"]: "hang@8"}, monkeypatch, attempt_wall=6).run()
    L = json.loads((tmp_path / "LEDGER.json").read_text())["runs"][runs[0]["id"]]
    assert s["counts"] == {"DONE": 1} and [a["reason"] for a in L["attempts"]] == ["timeout", "done"] and same_as_reference(tmp_path, runs[0])


def test_memory_gate_ramp_and_pressure(tmp_path, monkeypatch):
    assert R.mem_gate(2.0, 0, 2) and not R.mem_gate(2.7, 1, 2) and not R.mem_gate(64, 2, 2) and R.mem_gate(4.4, 3, 4)
    runs = [spec(i, seed=i, n=40) for i in range(4)]
    seq = iter([64.0] * 30 + [0.5] + [64.0] * 10 ** 6)
    s = runner(tmp_path, runs, {}, monkeypatch, mem=lambda: next(seq)).run()
    L = json.loads((tmp_path / "LEDGER.json").read_text())
    ramp = next((e["t"] for e in L["events"] if e["kind"] == "ramp"), float("inf"))
    assert all(e["running"] <= 2 for e in L["events"] if e["kind"] == "launch" and e["t"] < ramp) and s["counts"] == {"DONE": 4}
    assert any(e["kind"] == "memory_pressure" for e in L["events"]) and any(a["reason"] == "memory" for r in L["runs"].values() for a in r["attempts"])
    assert all(same_as_reference(tmp_path, x) for x in runs)


def test_parent_killed_workers_stop_and_resume_without_orphans(tmp_path, monkeypatch):
    runs = [spec(0, n=400)]
    (tmp_path / "SYN_ROSTER.json").write_text(json.dumps(runs))
    code = (f"import bxy_p12_run as R; R.Runner({str(tmp_path)!r}, limits={json.dumps(LIM | {'runs': 1})}, reserve={json.dumps(NORES)}, synthetic=True, "
            f"tick=0.1, check_git=False, mem=lambda: 64.0).run()")
    p = sp.Popen([sys.executable, "-c", code], env=os.environ | {"BXY_P12_FAULT": "{}"})
    hb = tmp_path / "runs" / R.safe(runs[0]["id"]) / "heartbeat.json"
    for _ in range(600):
        if hb.exists():
            break
        time.sleep(0.1)
    p.send_signal(signal.SIGKILL)
    p.wait()
    for _ in range(300):
        if not R.worker_pids(tmp_path):
            break
        time.sleep(0.1)
    assert R.worker_pids(tmp_path) == []                                     # PDEATHSIG: no orphan keeps running
    L0 = json.loads((tmp_path / "LEDGER.json").read_text())
    assert L0["runs"][runs[0]["id"]]["status"] == "RUNNING"
    s = runner(tmp_path, runs, {}, monkeypatch).run()
    L = json.loads((tmp_path / "LEDGER.json").read_text())
    assert s["counts"] == {"DONE": 1} and [a["reason"] for a in L["runs"][runs[0]["id"]]["attempts"]] == ["parent_lost", "done"]
    assert any(e["kind"] == "reconciled" for e in L["events"]) and same_as_reference(tmp_path, runs[0])


def test_orphan_worker_is_terminated_by_exact_pid(tmp_path, monkeypatch):
    runs = [spec(0, n=10 ** 6)]
    (tmp_path / "SYN_ROSTER.json").write_text(json.dumps(runs))
    (tmp_path / "runs").mkdir()
    w = sp.Popen([sys.executable, str(Path(R.__file__).resolve()), "worker", "--out", str(tmp_path.resolve()), "--rid", runs[0]["id"], "--attempt", "2",
                  "--parent", str(os.getpid()), "--synthetic"])
    for _ in range(300):
        if R.worker_pids(tmp_path):
            break
        time.sleep(0.05)
    assert R.worker_pids(tmp_path) == [w.pid]
    r = runner(tmp_path, runs, {}, monkeypatch)
    r.reconcile()
    w.wait(timeout=60)
    assert R.worker_pids(tmp_path) == [] and any(e["kind"] == "orphan_terminated" and e["pid"] == w.pid for e in r.L["events"])


def test_synthetic_mode_never_touches_the_real_output():
    with pytest.raises(RuntimeError, match="synthetic"):
        R.worker(R.OUT, "x", 1, os.getppid(), synthetic=True)


def test_real_prediction_path_without_any_optimizer_step():
    """Production data / prediction / serialization path with max_updates = 0 (no optimizer step on real data)."""
    d = R.design()
    s = next(x for x in d["roster"] if x["phase"] == "CROSSFIT" and x["arm"] == "XY-quadratic")
    tr, es, pr, sets = R.real_data(s)
    m, info = R.fit_resumable(s["arm"], s["seed"], tr, es, 0.3, P.TRAIN | {"max_updates": 0})
    assert info["updates_run"] == 0 and info["best_update"] == 0
    preds = json.loads(json.dumps({sv["key"]: R.predict_root(m, sv) for sv in pr[:5]}))
    assert all(len(v["cands"]) == len(sv["cands"]) and len(v["vars"]["psucc"]) == len(sv["x_seqs"]) == len(v["coeffs"]["a"]) for v, sv in zip(preds.values(), pr[:5]))
