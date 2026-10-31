"""BXY-P14: arm construction (non-GEO arms initialize exactly like bxy_p11), the trainer loop under the arm hooks equals the frozen
bxy_p12_run.fit_resumable, the CON loss, GEO leakage safety, fold custody, and fault injection of the P14 runner on SYNTHETIC roots only."""
import json
from pathlib import Path

import pytest
import torch

import bxy_data as bd

HAVE = (bd.DATA / "roots").exists() and Path("runs/approach_b/bxy_pmin_v1/BXY_SIDECAR_V2_PMIN.json").exists()
pytestmark = pytest.mark.skipif(not HAVE, reason="local BD_GEN_V1 snapshot / P-min sidecar not present")
if HAVE:
    import bxy_p11 as P
    import bxy_p12_run as R
    import bxy_p14 as H
    import bxy_p14_run as W

LIM = {"aggregate_cpu_s": 10 ** 6, "per_run_cpu_s": 10 ** 5, "workers": 4, "wall_s": 10 ** 6, "torch_threads": 1}
NORES = {"evaluation_cpu_s": 0, "evaluation_wall_s": 0}
CFG = {"max_updates": 14, "eval_every": 2, "batch_roots": 3, "patience_evals": 4}


def spec(i, arm="XYQ", seed=0, n=24):
    return {"id": f"cv/f0/{arm}/s{seed}/{i}", "phase": "CROSSFIT", "arm": arm, "lambda_J": H.ARMS[arm]["lam"], "seed": seed, "train": "fold0.train",
            "early_stop": "syn", "max_updates": n}


def runner(tmp, runs, faults=None, monkeypatch=None, limits=None, **kw):
    (tmp / "SYN_ROSTER.json").write_text(json.dumps(runs))
    if monkeypatch is not None:
        monkeypatch.setenv("BXY_P14_FAULT", json.dumps(faults or {}))
    return W.Runner14(tmp, limits=(limits or LIM) | {"runs": len(runs)}, reserve=NORES, synthetic=True, tick=0.1, check_git=False,
                      mem=kw.pop("mem", lambda: 64.0), **kw)


@pytest.mark.parametrize("arm", ["XYQ", "XYQ+CON", "DIRECT"])
def test_non_geo_arms_initialize_like_bxy_p11(arm):
    a, b = H.build_model(arm, 3).state_dict(), P.build_model(H.ARMS[arm]["base"], 3).state_dict()
    assert a.keys() == b.keys() and all(torch.equal(a[k], b[k]) for k in a)


@pytest.mark.parametrize("arm", ["XYQ", "DIRECT"])
def test_baseline_arms_train_bitwise_like_p12(arm):
    tr, es, _, _ = R.syn_data({})
    cfg = P.TRAIN | CFG
    m0, r0 = R.fit_resumable(H.ARMS[arm]["base"], 1, tr, es, 0.3, cfg)
    with H.arm_hooks(arm):
        m1, r1 = R.fit_resumable(arm, 1, tr, es, 0.3, cfg)
    assert all(torch.equal(a, b) for a, b in zip(m0.state_dict().values(), m1.state_dict().values())) and r0["history"] == r1["history"]
    assert P.build_model is not None and P.batch_loss.__name__ == "batch_loss"                     # hooks restored


def test_contrast_loss_and_con_batch_loss():
    b = torch.tensor([0.0, 2.0, -1.0], dtype=torch.float64, requires_grad=True)
    assert float(H.contrast(b, {0: 1, 1: 1})) == 0.0
    c = H.contrast(b, {0: 1, 1: 0, 2: 0})
    assert float(c) == pytest.approx(3 * (torch.nn.functional.softplus(torch.tensor(2.0)) + torch.nn.functional.softplus(torch.tensor(-1.0))).item() / 2)
    c.backward()
    assert b.grad[0] < 0 < b.grad[1]                                  # descent raises the feasible scene, lowers the infeasible ones
    tr, _, _, _ = R.syn_data({})
    m = H.build_model("XYQ+CON", 0)
    t0, rec = H.batch_loss(m, [x[0] for x in tr], [x[1] for x in tr], 0.3, kappa=0.0)
    ref, rr = P.batch_loss(m, [x[0] for x in tr], [x[1] for x in tr], 0.3)
    assert abs(float(t0) - float(ref)) < 1e-10 and rec["nll"] == pytest.approx(rr["nll"]) and "contrast" in rec


def test_geo_head_reads_scorer_view_only():
    sv, lab = R.synthetic_root(1)
    m = H.build_model("XYQ+GEO", 0)
    b0 = m.coeffs(sv)["b"].detach().clone()
    lab2 = {k: ({q: 1 - v for q, v in lab[k].items()} if k in ("obs_x", "obs_y") else lab[k]) for k in lab}
    assert torch.equal(b0, m.coeffs(sv)["b"].detach()) and lab2 != lab           # labels never reach the coefficients
    sv2 = dict(sv, y_poses=[{}, {0: tuple(float(v) for v in sv["R"].xy0[sv["R"].tid] + torch.tensor([0.03, 0.0]))}])
    assert not torch.equal(b0[1], m.coeffs(sv2)["b"].detach()[1])
    with pytest.raises(KeyError):
        m.coeffs(dict(sv, role="minimal"))


def test_folds_hold_out_each_train_root_once_by_family():
    fo = H.folds()
    R_ = bd.roots()
    held = [k for f in fo["folds"] for k in f["heldout"]]
    assert sorted(held) == sorted(fo["roots"]) and len(held) == 176 and all(bd.split_of(R_[k]) == "train" for k in held)
    fam = {}
    for j, f in enumerate(fo["folds"]):
        assert not (set(f["train"]) & set(f["early_stop"])) and not ((set(f["train"]) | set(f["early_stop"])) & set(f["heldout"]))
        for k in f["heldout"]:
            fam.setdefault(R_[k]["ids"]["parent_family_id"], set()).add(j)
    assert all(len(v) == 1 for v in fam.values())
    assert len(H.roster()) == 75 and len({r["id"] for r in H.roster()}) == 75


def test_end_to_end_faults_on_synthetic_roots(tmp_path, monkeypatch):
    runs = [spec(0), spec(1, "XYQ+CON+GEO", 1), spec(2, "XYQ+GEO", 2), spec(3, "DIRECT")]
    faults = {runs[1]["id"]: "term@10", runs[2]["id"]: "crash@14", runs[3]["id"]: "corrupt"}
    s = runner(tmp_path, runs, faults, monkeypatch).run()
    assert s["counts"] == {"DONE": 4}, s
    L = json.loads((tmp_path / "LEDGER.json").read_text())
    reasons = {r: [a["reason"] for a in L["runs"][r]["attempts"]] for r in L["runs"]}
    assert reasons[runs[1]["id"]] == ["interrupted", "done"] and reasons[runs[2]["id"]] == ["crash(13)", "done"]
    assert reasons[runs[3]["id"]] == ["corrupt_output", "done"] and W.worker_pids(tmp_path) == []
    tr, es, pr, _ = R.syn_data({})
    with H.arm_hooks("XYQ+CON+GEO"):                                  # the resumed run equals an uninterrupted one
        m, info = R.fit_resumable("XYQ+CON+GEO", 1, tr, es, 1.0, R.run_cfg(runs[1], True))
    got = torch.load(tmp_path / "runs" / R.safe(runs[1]["id"]) / "best.pt", weights_only=False)
    assert all(torch.equal(got[k], v) for k, v in m.state_dict().items())


def test_caps_on_synthetic_roots(tmp_path, monkeypatch):
    runs = [spec(i, seed=i) for i in range(3)]
    s = runner(tmp_path / "a", runs, {}, monkeypatch, limits=LIM | {"per_run_cpu_s": 60, "aggregate_cpu_s": 61}).run() \
        if (tmp_path / "a").mkdir() is None else None
    assert [s["statuses"][r["id"]] for r in runs] == ["DONE", "NOT_LAUNCHED_BUDGET", "NOT_LAUNCHED_BUDGET"] and s["aggregate_cpu_s"] <= 61
    (tmp_path / "b").mkdir()
    r1 = [spec(0, n=10 ** 6)]
    s = runner(tmp_path / "b", r1, {r1[0]["id"]: "spin@4"}, monkeypatch, limits=LIM | {"per_run_cpu_s": 8}, grace=3).run()
    assert s["statuses"][r1[0]["id"]] == "INCOMPLETE_CPU_CAP" and not (tmp_path / "b" / "runs" / R.safe(r1[0]["id"]) / "RESULT.json").exists()


def test_authorization_required_for_real_runs(tmp_path):
    with pytest.raises(PermissionError):
        W.verify_auth(tmp_path, check_git=False)
