"""BXY-P10-PREREG tests: F1 analytic screen, V2 learner interface (pilot sidecar, read-only), complete-travel cost convention, P-min design
freezing / guards, instrumented Y counters. No physical teacher call (stubs and stored records only), no training."""
import collections
import copy
import json

import pytest
import torch

import bxy_data as bd

HAVE = (bd.DATA / "roots").exists()
pytestmark = pytest.mark.skipif(not HAVE, reason="local BD_GEN_V1 snapshot not present")
if HAVE:
    import bxy_f1 as F1
    import bxy_pmin as PM
    import bxy_teacher as T
    import bxy_v2 as V
    R = bd.roots()
    K, REC = next((k, r) for k, r in R.items() if bd.split_of(r) == "train" and len(r["roles"]) >= 3 and r["fixed_ids"])
    MV = sorted(REC["roles"])
    C0 = bd.cells0(REC)
    TGT = next(o["id"] for o in REC["scene"]["objects"] if o["kind"] == "target")
    FREE = [c for c in REC["scene"]["legal_cells"] if c not in C0.values() and c != REC["goal_cell"]]


def rules(f, side="x"):
    return [v["rule"] for v in f[f"{side}_violations"]]


def test_f1_occupancy_target_goal_fixed_support_and_null():
    a, b, c = MV[:3]
    f = F1.screen(REC, [(a, C0[b])])                                                    # onto a staying object
    assert rules(f) == ["DEST_OCCUPIED"] and not f["y_ok"] and rules(f, "y") == ["PAIR_OVERLAP"] and not f["complete_ok"]
    f = F1.screen(REC, [(a, FREE[0]), (b, FREE[0])])                                    # one endpoint assigned twice
    assert rules(f) == ["DEST_OCCUPIED"] and f["x_violations"][0]["step"] == 1 and not f["y_ok"]
    assert rules(F1.screen(REC, [(a, C0[TGT])])) == ["DEST_OCCUPIED"]                  # onto T
    f = F1.screen(REC, [(a, REC["goal_cell"])])                                          # onto T's goal: legal scene, task impossible
    assert f["x_ok"] and f["y_ok"] and f["goal_blocked"] == [a] and not f["complete_ok"]
    assert rules(F1.screen(REC, [(REC["fixed_ids"][0], FREE[0])])) == ["ID_FIXED"]
    assert rules(F1.screen(REC, [(TGT, FREE[0])]))[0] == "ID_TARGET"
    assert rules(F1.screen(REC, [("zz", FREE[0])])) == ["ID_UNKNOWN"]
    r2 = copy.deepcopy(REC)
    r2["scene"]["legal_cells"] = [x for x in r2["scene"]["legal_cells"] if x != FREE[0]]
    assert rules(F1.screen(r2, [(a, FREE[0])])) == ["DEST_NOT_LEGAL"]                   # unsupported cell
    assert "NULL_RELOCATION" in rules(F1.screen(REC, [(a, C0[a])]))
    assert rules(F1.screen(REC, [(a, FREE[0]), (a, FREE[1])])) == ["DUPLICATE_OBJECT"]
    assert rules(F1.screen(REC, [(m, FREE[i]) for i, m in enumerate((MV * 3)[:7])]))[0] == "LENGTH"


def test_f1_order_specific_and_omission_identity():
    a, b = MV[:2]
    ok, rev = [(a, FREE[0]), (b, C0[a])], [(b, C0[a]), (a, FREE[0])]                    # b takes a's vacated cell
    assert F1.screen(REC, ok)["complete_ok"] and rules(F1.screen(REC, rev)) == ["DEST_OCCUPIED"]
    assert F1.screen(REC, rev)["y_ok"] and bd.endpoint(REC, ok) == bd.endpoint(REC, rev)  # same legal endpoint: Y stays admissible
    om = [x for i, x in enumerate(ok) if i != 0]                                         # omission recomputed from S0: a never left
    assert rules(F1.screen(REC, om)) == ["DEST_OCCUPIED"] and bd.endpoint(REC, om) == {b: C0[a]}


def test_f1_never_erases_motion_negatives_and_matches_teacher_static_labels():
    sc = json.loads(V.PILOT.read_text())
    neg = [r for r in sc["x_queries"] if r["y"] == 0]
    assert len(neg) == 8 and all(F1.screen(R[r["root"]], [tuple(a) for a in r["ordered_actions"]])["x_ok"] for r in neg)   # F2 stays F2
    assert all(F1.screen(R[r["root"]], [tuple(a) for a in r.get("ordered_actions") or []])["x_ok"] for r in sc["x_queries"])
    for k, r in R.items():
        if bd.split_of(r) not in ("train", "val"):
            continue
        for b in r["labels"]["B"]:
            f = F1.screen(r, [(o, int(d)) for o, d in b["sequence"]])
            if b.get("reason") == "STATIC_INVALID":
                assert not f["x_ok"] and f["x_violations"][0]["step"] == b["failed_step"]          # every teacher static invalid, same step
            if f["x_ok"]:
                assert b.get("reason") != "STATIC_INVALID"


def test_v2_adapter_pilot_labels_identity_and_shared_y():
    sc = V.load()
    assert V.check_identity(sc, R) == []
    rts = V.views("train")
    ox = [v for rt in rts for v in rt["obs_x"].values()]
    oy = [v for rt in rts for v in rt["obs_y"].values()]
    assert (sum(ox), len(ox) - sum(ox), sum(oy), len(oy) - sum(oy)) == (49, 8, 29, 30)
    assert sum(len(rt["y_keys"]) - len(rt["obs_y"]) for rt in rts) == 11                  # X-only parents: unobserved, never 0
    assert all(k.startswith("X2:") for rt in rts for k in rt["x_keys"]) and all(k.startswith("Y2:") for rt in rts for k in rt["y_keys"])
    rt = next(r for r in rts if r["key"].endswith("s047"))
    assert max(collections.Counter(rt["parent"]).values()) >= 2                           # reversed orders share one Y node
    assert V.views("val") == [] and V.views("test") == []


def test_v2_absence_conflict_and_tamper(tmp_path):
    sc = json.loads(V.PILOT.read_text())
    s2 = copy.deepcopy(sc)
    s2["x_queries"][0] |= {"observed": False, "y": None, "teacher_status": "CENSORED"}
    s2["y_queries"][0] |= {"attempted": False, "observed": False, "y": None, "teacher_status": "NOT_ATTEMPTED_BUDGET"}
    O = V.observations(s2)
    k0 = s2["x_queries"][0]["root"]
    assert s2["x_queries"][0]["x_key"] not in O[k0]["x"] and (s2["x_queries"][0]["x_key"], "CENSORED") in O[k0]["absent"]
    assert s2["y_queries"][0]["y_key"] not in O[s2["y_queries"][0]["root"]]["y"]
    s3 = copy.deepcopy(sc)
    dup = copy.deepcopy(s3["x_queries"][0])
    dup["y"] = 1 - dup["y"]
    s3["x_queries"].append(dup)
    with pytest.raises(V.ConflictError):
        V.observations(s3)
    s4 = copy.deepcopy(sc)
    s4["y_queries"][0]["q_ref_hash"] = "000000000000"
    s4["x_queries"][0]["ordered_actions"] = s4["x_queries"][0]["ordered_actions"][::-1] + [["o00", 0]]
    assert len(V.check_identity(s4, R)) == 2
    s5 = dict(sc, version="BXY_SIDECAR_V1")
    (tmp_path / "s.json").write_text(json.dumps(s5))
    with pytest.raises(ValueError):
        V.load(tmp_path / "s.json")


def test_v2_inputs_carry_no_teacher_data():
    import learn_data as ld
    d = torch.load(V.RECORDS, weights_only=False)
    assert ld.leakage_audit(d) == []
    for rt in V.views("train", full=True):
        assert all(isinstance(i, int) and len(c) == 2 and all(isinstance(z, float) for z in c) for s in rt["x_seqs"] for i, c in s)
        assert all(isinstance(i, int) and len(c) == 2 for p in rt["y_poses"] for i, c in p.items())


def test_complete_travel_convention_noop_and_ablation():
    rts = V.views("train")
    items = [(rt["key"], a) for rt in rts for a, _ in rt["j_items"]]
    assert sum(a is None for _, a in items) == 6 and sum(a is not None for _, a in items) == 23    # Y0 no-op witnesses + full successes
    sc = json.loads(V.PILOT.read_text())
    assert len(items) == sum(1 for p in sc["paired"] if p["full_joint_success"] == 1) + sum(
        1 for r in sc["y_queries"] if r["y"] == 1 and not r["hypothetical_poses"])                # failures never carry a J label
    torch.manual_seed(0)
    m = V.build("XY-quadratic")
    full = {rt["key"]: rt for rt in V.views("train", full=True)}
    j0 = {}
    for k in list(full)[:4]:
        rows = V.predict(m, full[k])
        assert rows[0]["m"] == 0 and rows[0]["admissible"] and rows[0]["J_hat"] > 0        # no-op charged its target travel, not 0
        j0[k] = rows[0]["J_hat"]
    assert len({round(v, 9) for v in j0.values()}) > 1                                  # scene-dependent, not a constant
    rt = rts[0]
    nll0, tr0 = V.root_loss(m, rt, 0.0)
    assert tr0 is None and torch.isfinite(nll0)                                          # lambda_J = 0: likelihood only
    rows = V.predict(m, full[rt["key"]])
    rule = {"eta": 0.0, "alpha": 0.1, "beta": 0.0, "gamma": 0.0}
    i = V.choose(rows, **rule)
    rows2 = [dict(r, J_hat=r["J_hat"] * 50 + 3) if r["admissible"] else r for r in rows]
    assert V.choose(rows2, **rule) == i                                                  # gamma = 0: travel cannot change the choice


def test_f1_screen_precedes_scoring_and_keeps_noop():
    rows = [{"m": 0, "admissible": True, "p": 0.2, "cd": 0.0, "J_hat": 1.0},
            {"m": 1, "admissible": False, "p": 0.99},
            {"m": 2, "admissible": True, "p": 0.6, "cd": 1.0, "J_hat": 2.0}]
    assert V.choose(rows, 0.0, 0.0, 0.0, 0.0) == 2 and V.choose(rows, 0.7, 0.0, 0.0, 0.0) is None
    assert V.choose(rows[:2], 0.0, 0.0, 0.0, 0.0) == 0


def test_exact_likelihood_on_a_v2_view_matches_brute_force():
    import bxy_core as X
    torch.manual_seed(1)
    m = V.build("XY-quadratic")
    rt = min(V.views("train"), key=lambda r: len(r["y_keys"]) + len(r["x_keys"]))
    b, a, w, _ = m.coeffs(rt)
    ex = X.log_evidence(b, a, w, rt["parent"], rt["obs_y"], rt["obs_x"])
    assert abs(float(ex) - X.brute_force(b, a, w, rt["parent"], rt["obs_y"], rt["obs_x"])) < 1e-9


def test_pmin_design_custody_f1_keys_and_no_outcomes():
    D = PM.design()
    assert json.dumps(D, sort_keys=True) == json.dumps(PM.design(), sort_keys=True)     # deterministic
    assert {d["split"] for d in D["roots"].values()} == {"train", "val"} and len(D["roots"]) == 197
    for k, d in D["roots"].items():
        for key, q in d["queries"].items():
            assert set(q) <= {"side", "seq", "len", "classes", "phases", "parent_y_key", "edit", "reuse_p9"}   # no label, no status
            s = [tuple(a) for a in q["seq"]]
            f = F1.screen(R[k], s)
            assert (f["x_ok"] if q["side"] == "x" else f["y_ok"])
            assert key == (T.xkey(k, R[k], s) if q["side"] == "x" else T.ykey(k, R[k], s))
            if q["side"] == "x":
                assert q["parent_y_key"] in d["queries"] or "PREFIX_COMPLETE" in q["phases"]
            if "reversal" in q["classes"] and "PMIN_DEV_MATCHED" in q["phases"]:
                assert q["parent_y_key"] in d["queries"]                                  # shares the forward order's Y
        for key, q in d["f1_screened"].items():
            assert key not in d["queries"] and q["f1"]
    W = PM.worklist(D)
    assert all(PM.admitted(D, k, q["key"]) for k, qs in W.items() for q in qs)
    assert not any(q["reuse_p9"] for qs in W.values() for q in qs)
    some = next(k for k in D["roots"] if D["roots"][k]["f1_screened"])
    assert not PM.admitted(D, some, next(iter(D["roots"][some]["f1_screened"])))


def test_pmin_freeze_is_immutable_and_guarded(tmp_path, monkeypatch):
    D = {"version": "t", "requested_phase": PM.REQUESTED, "roots": {}, "root_order": []}
    lock = PM.freeze(tmp_path, D, {"cpu_s": 1})
    assert lock["authorized"] is False and PM.assert_frozen(tmp_path, check_git=False)["design_sha256"] == lock["design_sha256"]
    assert PM.freeze(tmp_path, D, {"cpu_s": 1})["design_sha256"] == lock["design_sha256"]             # idempotent
    with pytest.raises(FileExistsError):
        PM.freeze(tmp_path, dict(D, version="t2"), {"cpu_s": 1})
    (tmp_path / "PMIN_DESIGN.json").write_text((tmp_path / "PMIN_DESIGN.json").read_text() + " ")
    with pytest.raises(RuntimeError, match="design file"):
        PM.assert_frozen(tmp_path, check_git=False)
    (tmp_path / "PMIN_DESIGN.json").write_text(json.dumps(D, indent=1, sort_keys=True))
    real = PM.sources
    monkeypatch.setattr(PM, "sources", lambda: dict(real(), **{"bxy_teacher.py": "changed"}))
    with pytest.raises(RuntimeError, match="source drift"):
        PM.assert_frozen(tmp_path, check_git=False)
    with pytest.raises(RuntimeError, match="not committed"):
        monkeypatch.setattr(PM, "sources", real)
        PM.assert_frozen(tmp_path, check_git=True)
    t2 = tmp_path / "late"
    (t2 / "results").mkdir(parents=True)
    (t2 / "results" / "a.json").write_text("{}")
    with pytest.raises(RuntimeError, match="results already exist"):
        PM.freeze(t2, D, {})


def test_pmin_sources_cover_semantics():
    s = PM.sources()
    assert {"bxy_teacher.py", "bxy_data.py", "bxy_f1.py", "bxy_pilot.py", "bd_2d.py", "p16_motion.py", "motion.py", "geometry.py", "config.toml"} <= set(s)
    assert set(T.SOURCES) - {"config.toml"} <= set(s)                                    # superset of the P9 teacher hash set


def test_y_counters_do_not_change_the_outcome(monkeypatch, tmp_path):
    import p16_motion as pm
    E = T.env()

    def goal(self, cells, q):
        self._take("goal_plans")
        return "UNKNOWN_PLANNER", {"planner": "stub"}, 0.0
    monkeypatch.setattr(pm.DetPhysics, "goal", goal)
    seq = [tuple(a) for a in next(b["sequence"] for b in REC["labels"]["B"] if F1.screen(REC, [tuple(x) for x in b["sequence"]])["y_ok"])]
    plain = T.y_query(E, K, REC, seq, {}, tmp_path)
    cnt = PM.y_query_counted(E, K, REC, seq, {}, tmp_path)
    strip = lambda r: {k: v for k, v in r.items() if k not in ("process_cpu_s", "budget", "budget_spent", "budget_counter_source")}  # noqa: E731
    assert strip(plain) == strip(cnt) and cnt["budget_spent"]["goal_plans"] == 1 and cnt["budget_counter_source"] == "DetPhysics.used"
    import bd_2d
    assert bd_2d._phys.__name__ == "_phys"                                               # wrapper removed after the call


def test_cost_model_separate_rates_and_checkpoint():
    D = PM.design()
    c = PM.cost_model(D, B=200)
    assert c["x_queries"] == sum(q["side"] == "x" for qs in PM.worklist(D).values() for q in qs)
    assert c["cpu_s_95"][0] <= c["cpu_s_mean"] <= c["cpu_s_95"][1] < c["requested"]["cpu_s"]
    assert abs(c["x_cpu_s_mean"] + c["y_cpu_s_mean"] - c["cpu_s_mean"]) / c["cpu_s_mean"] < 0.05
    assert c["requested"]["root_cpu_s"] >= c["max_root_cpu_s_stress"]
    est = c["est_root_cpu_s"]
    ks = list(est)[:20]
    assert PM.checkpoint({k: est[k] for k in ks}, est, c["requested"]["cpu_s"])["ok"]
    assert not PM.checkpoint({k: 3 * est[k] for k in ks}, est, c["requested"]["cpu_s"])["ok"]
    assert PM.checkpoint({k: 9e9 for k in ks[:5]}, est, 1)["ok"]                          # no projection before 20 roots


def test_historical_artifacts_and_checkpoints_preserved():
    import hashlib
    import subprocess as sp
    assert hashlib.sha256(V.PILOT.read_bytes()).hexdigest() == "adea6983f1303236b05c41b5755652d0b05dab808dff2951df07a8c26ca2f840"
    assert T.teacher_hash() == json.loads(V.PILOT.read_text())["manifest"]["teacher_hash"][0]          # P9 teacher unchanged: reuse valid
    for d in ("runs/approach_b/bxy", "runs/approach_b/bd2d_lb_v1", "runs/approach_b/bxy_teacher_pilot_v1"):
        assert sp.run(["git", "diff", "--quiet", "HEAD", "--", d]).returncode == 0, d                   # sidecars, FROZEN, checkpoints
        assert sp.run(["git", "ls-files", "--others", "--exclude-standard", d], capture_output=True, text=True).stdout == "", d
