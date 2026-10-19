"""G4D runner orchestration (report 0011) with synthetic workers in temporary directories:
CPU and wall cancellation, child-process CPU, nonzero exit, incomplete checkpoints kept,
aggregate admission, resume without repeating started or finished units, and one real
cheap unit whose checkpoints are revalidated. Correctness tests only: nothing here is a
scientific label or a collected root."""
import json
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config as cf  # noqa: E402
import data  # noqa: E402
import g4d_run  # noqa: E402
import geometry as ge  # noqa: E402

SCRIPTS = {
    "ok": "import json,sys; d=json.load(open(sys.argv[1])); open(d['unit_dir']+'/final.json','w').write('{}')",
    "burn": ("import json,sys,os; d=json.load(open(sys.argv[1])); p=d['unit_dir']+'/certificates.json';"
             "open(p+'.tmp','w').write('{\"certificates\": []}'); os.replace(p+'.tmp', p)\nwhile True: pass"),
    "child": ("import subprocess,sys,time; subprocess.Popen([sys.executable,'-c','while True: pass']); time.sleep(60)"),
    "sleep": "import time; time.sleep(60)",
    "fail": "import sys; sys.exit(3)",
    "late": "import json,sys; d=json.load(open(sys.argv[1])); open(d['unit_dir']+'/final.json','w').write('{}')",
}


def _plan(names, **lim):
    L = {"cpu_per_unit_s": 3.0, "guard_margin_s": 1.0, "cpu_aggregate_s": 60.0, "workers": 1, "wall_per_unit_s": 2.5,
         "wall_total_s": 120.0, "poll_s": 0.05, "orchestration_reserve_s": 0.5, **lim}
    return {"plan_hash": "sha256:test", "limits": L, "units": [{"unit": n, "kind": "SYNTHETIC"} for n in names]}


def _argv(log):
    def f(job):
        name = json.loads(Path(job).read_text())["unit"]["unit"]
        log.append(name)
        return [sys.executable, "-c", SCRIPTS[name], str(job)]
    return f


def _run(plan, tmp, log):
    return g4d_run.run_collection(plan, tmp, {"plan": tmp / "p.json", "config": "c", "config_v2": "v"}, tmp, _argv(log))


def test_guarded_units_cancel_account_and_keep_checkpoints(tmp_path):
    log = []
    led = _run(_plan(list(SCRIPTS)), tmp_path, log)
    u = led["units"]
    assert {k: u[k]["stop"] for k in u} == {"ok": "COMPLETED", "burn": "CPU_CENSORED", "child": "CPU_CENSORED",
                                            "sleep": "WALL_CENSORED", "fail": "ERROR", "late": "COMPLETED"}
    assert u["burn"]["checkpoints"] == ["certificates"] and u["ok"]["checkpoints"] == ["final"]   # partial evidence kept
    assert 1.5 <= u["child"]["cpu_s"] <= 3.5 and u["child"]["wall_s"] < 2.5                     # descendant CPU counted
    assert u["fail"]["returncode"] == 3 and all(x["overshoot_s"] == 0.0 for x in u.values())
    assert abs(led["unit_cpu_s"] - sum(x["cpu_s"] for x in u.values())) < 1e-6 and "enforcement_failure" not in led
    saved = json.loads((tmp_path / "ledger.json").read_text())
    assert saved["units"] == u and saved["plan_hash"] == "sha256:test"


def test_admission_respects_aggregate_and_global_wall(tmp_path):
    log = []
    led = _run(_plan(["burn", "ok", "late"], cpu_aggregate_s=5.5), tmp_path / "a", log)
    assert [led["units"][k]["stop"] for k in ("burn", "ok", "late")] == ["CPU_CENSORED", "NOT_RUN_BUDGET", "NOT_RUN_BUDGET"]
    assert log == ["burn"]
    log = []
    led = _run(_plan(["sleep", "ok"], wall_total_s=1.5), tmp_path / "b", log)
    assert led["units"]["sleep"]["stop"] == "WALL_CENSORED" and led["units"]["sleep"]["wall_s"] < 2.0
    assert led["units"]["ok"]["stop"] == "NOT_RUN_WALL" and log == ["sleep"]


def test_resume_runs_only_never_started_units_with_the_original_deadline(tmp_path):
    plan = _plan(["ok", "fail", "late"])
    (tmp_path).mkdir(exist_ok=True)
    deadline = time.time() + 100.0
    g4d_run._atomic_json(tmp_path / "ledger.json", {
        "plan_hash": plan["plan_hash"], "deadline_epoch": deadline, "started_utc": "x", "unit_cpu_s": 7.0,
        "coordinator_cpu_s": 0.5, "resumes": 0,
        "units": {"ok": {"state": "ENDED", "stop": "COMPLETED", "cpu_s": 7.0}, "fail": {"state": "STARTED"}}})
    log = []
    led = _run(plan, tmp_path, log)
    assert log == ["late"] and led["units"]["fail"]["stop"] == "INTERRUPTED_AMBIGUOUS" and led["resumes"] == 1
    assert led["deadline_epoch"] == deadline and led["unit_cpu_s"] >= 7.0 and led["units"]["ok"]["cpu_s"] == 7.0
    with pytest.raises(SystemExit):
        _run({**plan, "plan_hash": "sha256:other"}, tmp_path, [])


def test_real_unit_checkpoints_are_revalidated(tmp_path):
    """A cheap real unit (R4 bad order: first-action certificate, no planning) through the
    actual worker under the guard; its evidence is rebuilt from re-checked checkpoints."""
    cfg, v2 = cf.load_config(ROOT / "config.toml"), cf.load_config_v2(ROOT / "config_v2.toml")
    pend = json.loads((ROOT / "runs/g4d_migration/g4d_plan.json").read_text())
    unit = next(u for u in pend["units"] if u["unit"] == "seq:R4:o00>29.o01>18")
    plan = {**pend, "plan_hash": "sha256:t", "limits": {**g4d_run.LIMITS, "cpu_aggregate_s": 1000.0}, "units": [unit]}
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    led = g4d_run.run_collection(plan, tmp_path, {"plan": tmp_path / "plan.json", "config": ROOT / "config.toml",
                                                  "config_v2": ROOT / "config_v2.toml"}, ROOT)
    u = led["units"][unit["unit"]]
    assert u["stop"] == "COMPLETED" and u["checkpoints"] == ["certificates", "final"]
    ev_ = g4d_run.unit_evidence(cfg, v2, ge.make_robot(cfg), plan, unit, tmp_path / u["dir"])
    assert ev_["label"] == data.NEGATIVE and [(c["kind"], c["scope"], c["accepted"]) for c in ev_["certificates"]] == \
        [("ORDER_FIRST_ACTION", "ORDER", True)]
    assert ev_["calls"] == {"relocation_planner": 0, "target_evaluations": 0}
    cp = tmp_path / u["dir"] / "certificates.json"
    rec = json.loads(cp.read_text())
    rec["certificates"][0]["sequence"] = [["o01", 18], ["o00", 29]]          # tampered checkpoint is not reused
    cp.write_text(json.dumps(rec))
    bad = g4d_run.unit_evidence(cfg, v2, ge.make_robot(cfg), plan, unit, tmp_path / u["dir"])
    assert bad["label"] == data.UNKNOWN and not bad["certificates"][0]["accepted"]


def test_real_relocation_and_target_checkpoints_are_revalidated(tmp_path):
    """R2 o03->60 through the real worker (test seed keys, temporary directory): the
    relocation witness, cost and target witness are each checkpointed and re-checked;
    a tampered relocation record is no longer a witness."""
    import numpy as np
    cfg, v2 = cf.load_config(ROOT / "config.toml"), cf.load_config_v2(ROOT / "config_v2.toml")
    pend = json.loads((ROOT / "runs/g4d_migration/g4d_plan.json").read_text())
    unit = {**next(u for u in pend["units"] if u["unit"] == "seq:R2:o03>60"), "relocation_key": "test/R2/o03>60/reloc",
            "target_key": "test/R2/o03>60/target"}
    plan = {**pend, "plan_hash": "sha256:t2", "limits": {**g4d_run.LIMITS, "cpu_aggregate_s": 2000.0}, "units": [unit]}
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    led = g4d_run.run_collection(plan, tmp_path, {"plan": tmp_path / "plan.json", "config": ROOT / "config.toml",
                                                  "config_v2": ROOT / "config_v2.toml"}, ROOT)
    u = led["units"][unit["unit"]]
    assert u["stop"] == "COMPLETED" and {"certificates", "relocation", "final"} <= set(u["checkpoints"])
    robot = ge.make_robot(cfg)
    ev_ = g4d_run.unit_evidence(cfg, v2, robot, plan, unit, tmp_path / u["dir"])
    assert ev_["relocation"]["complete_witness"] and ev_["cost"]["label_available"] and ev_["cost"]["recomputed_J"] > 0
    assert ev_["checks"]["joint_continuity"] and ev_["calls"]["relocation_planner"] == 1
    if "target_witness" in u["checkpoints"]:                  # outcome-dependent: a witness must re-check fully
        assert ev_["label"] == data.POSITIVE and ev_["checks"]["target_start_equality"]
        assert ev_["target"]["witness_check"]["accepted"]
    else:
        assert ev_["label"] == data.UNKNOWN
    z = dict(np.load(tmp_path / u["dir"] / "relocation.npz"))
    z["r0__q"] = z["r0__q"] + np.array([1e-3, 0, 0])
    np.savez_compressed(tmp_path / u["dir"] / "relocation.npz", **z)
    bad = g4d_run.unit_evidence(cfg, v2, robot, plan, unit, tmp_path / u["dir"])
    assert not bad["relocation"]["complete_witness"] and not bad["cost"]["label_available"] and bad["label"] == data.UNKNOWN
