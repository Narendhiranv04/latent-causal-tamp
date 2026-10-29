"""Approach D G2b (approachD_G2b_solver_free_provider_instructions_v1_2): the AD_PRECOMPILED provider over the finite robot-state graph.
Real saved records (runs/approach_d/g2b/catalog/GRAPH*), every runtime path under ad_runtime.forbid('raise')."""
import ast
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

import ad_compile as ac
import ad_g2b as g2
import ad_provider as pv
import ad_runtime as ar

F12_SEQ = [["o00", 45], ["o01", 36]]


@pytest.fixture(scope="module")
def env():
    from scene import scene_from_dict
    cfg, robot, _ = ac.setup()
    g = pv.Graph(g2.OUT / "catalog")
    ri, member = g2._ri()
    P = g2.rd(g2.DEV_PLAN)["roots"]
    return cfg, robot, g, ri, member, P, scene_from_dict


def _prov(env, root, policy="EXACT+REL_6x1+CATALOG", graph=None, prefilter="OFF"):
    cfg, robot, g, ri, member, P, sfd = env
    s = sfd(P[root]["scene"])
    rk = g2.Ranker(ri, member, g2._excl(root), **g2.POLICIES[policy])
    return pv.Precompiled(cfg, robot, s, P[root]["goal_cell"], graph or g, rk, 6, 2, prefilter, policy), s


def test_provider_static_deny_by_default():
    for f, allow_mods in (("ad_provider.py", {"__future__", "annotations", "collections", "hashlib", "json", "time", "dataclasses", "replace",
                                              "pathlib", "Path", "numpy", "ad_runtime", "tomllib"}),):
        tree = ast.parse(Path(f).read_text())
        mods = {a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names} | \
               {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        assert mods <= allow_mods, mods - allow_mods
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {a.attr for a in ast.walk(tree) if isinstance(a, ast.Attribute)}
        assert not names & {"ik", "ik_track", "ik_line", "carry_line", "plan", "plan_skill", "screen_pick", "screen_place", "_rrt_connect",
                            "certified", "certificates_for", "DetPhysics", "Physics"}
    tree = ast.parse(Path("ad_runtime.py").read_text())
    allow = {("ge", "Checker"), ("ge", "make_world"), ("ge", "certify"), ("ge", "CLEAR"), ("ge", "COLLISION"), ("ge", "within_limits"),
             ("mo", "certify_trajectory")}
    for fn in (n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ("certify_free", "certify_action")):
        used = {(a.value.id, a.attr) for a in ast.walk(fn) if isinstance(a, ast.Attribute) and isinstance(a.value, ast.Name) and a.value.id in ("ge", "mo")}
        assert used <= allow, used - allow


def test_two_relocation_chain_then_original_target_end_to_end(env):
    """A -> B -> T from the root's actual start stratum: only stored records, exact q continuity, independent replay, zero solver calls."""
    prov, s = _prov(env, "p13_2026216000")
    cells0, q0 = {o.id: o.cell for o in s.objects}, np.asarray(s.robot.q_rad, float)
    with ar.forbid() as calls:
        r = pv.run_sequence(prov, cells0, q0, F12_SEQ)
    assert not calls and r["status"] == ar.SUCCESS and r["replay"]["status"] == ar.SUCCESS
    assert [x["kind"] for x in r["log"]] == ["RELOCATION", "RELOCATION", "TARGET"] and r["replay"]["cells"]["t0"] == prov.goal_cell
    g, q = prov.g, prov.g.node_of(q0)
    for kind, rid, _ in r["steps"]:                                 # every record starts bitwise at the state the previous one left
        rec = g.connectors.get(rid) or g.actions[rid]
        assert rec["from"] == q and np.array_equal(g.arrays[rid]["q"][0], g.q[q])
        q = rec["to"]
    assert {g.connectors[i]["origin"] for k, i, _ in r["steps"] if k == "connector"} >= {"ROOT_ENTRY", "ENTRY_LEG", "EXIT_LEG"}
    saved = g2.rd(g2.OUT / "CHAINS.json")["rows"]["F12|EXACT+REL_6x1+CATALOG"]
    assert r["replay"]["trajectory_hash"] == saved["replay"]["trajectory_hash"]


def test_injected_forbidden_call_trips_inside_the_provider(env, monkeypatch):
    prov, s = _prov(env, "p13_2026216000")
    import geometry as ge
    monkeypatch.setattr(pv.ar, "certify_free", lambda *a, **k: ge.ik(None, None, None))   # a checker that secretly calls IK
    with ar.forbid() as calls, pytest.raises(ar.ForbiddenCall):
        pv.run_sequence(prov, {o.id: o.cell for o in s.objects}, np.asarray(s.robot.q_rad, float), F12_SEQ)
    assert calls["geometry.ik"] == 1


def test_failed_candidates_then_alternative_and_isolated_failure_causes(env):
    prov, s = _prov(env, "p13_2026216000")
    with ar.forbid() as calls:
        r = pv.repair(prov, {o.id: o.cell for o in s.objects}, np.asarray(s.robot.q_rad, float), g2.F12_CANDIDATES)
        single = pv.run_sequence(prov, {o.id: o.cell for o in s.objects}, np.asarray(s.robot.q_rad, float), [["o00", 45]])
    assert not calls and r["status"] == ar.SUCCESS and r["sequence"] == F12_SEQ
    assert [t["status"] for t in r["tried"]][:-1] == [ar.FAILURE] * (len(r["tried"]) - 1) and all(t["reason"] for t in r["tried"][:-1])
    assert single["status"] == ar.FAILURE and single["failed_step"] == 1 and single["log"][-1]["kind"] == "TARGET"   # B is needed


def test_no_snapping_no_compatible_q_and_connector_ablation(env):
    _, robot, g, *_ = env
    prov, s = _prov(env, g2.ANOMALY_ROOT)
    cells = {o.id: o.cell for o in s.objects}
    q0 = np.asarray(s.robot.q_rad, float)
    with ar.forbid() as calls:
        assert prov.goal(cells, q0 + 1e-7)["reason"] == "NO_COMPATIBLE_Q"                     # off-graph by 1e-7 rad: no snapping
        cut, _ = _prov(env, g2.ANOMALY_ROOT, graph=g2._graph_without(g, "ROOT_ENTRY"))
        assert cut.goal(cells, q0)["reason"] == "NO_COMPATIBLE_CONNECTOR"
        ok = prov.goal(cells, q0)
        assert ok["status"] == ar.SUCCESS and [k for k, _ in ok["steps"]] == ["connector", "connector", "action"]
        assert prov.goal(cells, np.array(robot.q_home))["status"] == ar.SUCCESS
    assert not calls


def test_anomaly_root_regression_fixture():
    a = g2.rd(g2.OUT / "ANOMALY_TRACE.json")
    lab = g2.rd(a["p16_label_file"])[g2.ANOMALY_ROOT]["original"]
    assert lab == {"status": "VERIFIED", "y": 1} == a["p16_label_original"]                  # never labelled obstructed; nothing relabelled
    c = {k: (v["status"], v["reason"]) for k, v in a["conditions"].items()}
    assert c == {"a_q_initial_no_root_entry": ("FAILURE", "NO_COMPATIBLE_CONNECTOR"), "b_q_initial_via_stored_root_entry": ("SUCCESS", None),
                 "c_q_home": ("SUCCESS", None)}
    assert a["offline_planner_from_q_initial"]["status"] == "VERIFIED_FEASIBLE"


def test_replay_detects_discontinuity_and_records_are_not_mutated(env):
    prov, s = _prov(env, "p13_2026216000")
    steps = [tuple(x) for x in g2.rd(g2.OUT / "CHAINS.json")["rows"]["F12|EXACT+REL_6x1+CATALOG"]["steps"]]
    cells0, q0 = {o.id: o.cell for o in s.objects}, np.asarray(s.robot.q_rad, float)
    h = lambda: hashlib.sha256(b"".join(np.asarray(prov.g.arrays[i]["q"]).tobytes() for _, i, _ in steps)).hexdigest()  # noqa: E731
    h0 = h()
    with ar.forbid() as calls:
        assert prov.verify_plan(cells0, q0, steps)["status"] == ar.SUCCESS
        bad = prov.verify_plan(cells0, q0, [steps[0]] + steps[2:])                              # a connector dropped
        assert (bad["status"], bad["reason"]) == (ar.FAILURE, "SEQUENCE_DISCONTINUITY")
        wrong = prov.verify_plan({**cells0, "o00": 44}, q0, steps)                              # the object is not where the action picks
        assert wrong["status"] == ar.FAILURE
    assert not calls and h() == h0 and not prov.counts                                         # replay is independent of the cache


def test_cache_is_keyed_on_occupancy_versions_and_policy(env):
    prov, s = _prov(env, "p13_2026216000")
    cells = {o.id: o.cell for o in s.objects}
    i = next(iter(prov.g.by_pair[(cells["o00"], 45)]))
    with ar.forbid():
        prov._cert(i, cells, "o00")
        prov._cert(i, cells, "o00")
        prov._cert(i, {**cells, "o01": 37}, "o00")
    assert prov.counts["cache_hits"] == 1 and prov.counts["certify_action"] == 2
    other, _ = _prov(env, "p13_2026216000", policy="EXACT+REL_3x2")
    assert other.cache is not prov.cache and other.cache_key != prov.cache_key
    assert {prov.g.hash, pv.CHECKER, "EXACT+REL_6x1+CATALOG"} <= set(prov.cache_key)


def test_prefilter_modes_and_a_reproduced_false_rejection():
    per = {"a": {"hit_full": [3], "full": True, "entry": True, "core": True, "hit_entry": [], "hit_core": [3], "cpu_s": 1.0},
           "b": {"hit_full": [], "full": False, "entry": True, "core": False, "hit_entry": [], "hit_core": [], "cpu_s": 1.0}}
    off, adv, hard = (g2._first_valid(["a", "b"], per, 6, m, False) for m in ("OFF", "ADVISORY", "HARD"))
    assert off["ok"] and off == adv and not hard["ok"] and hard["checks"] == 1                # HARD skipped a valid path at no cost
    fr = {(f["qid"], f["template"]): f for f in g2.rd(g2.OUT / "ANALYSIS.json")["prefilter_false_rejections"]}
    assert len(fr) == 4
    for f in fr.values():                                                                    # every one lies between delta and delta+STEP_M
        (c,) = f["clearance"].values()
        assert c["certifier"] == "VALID" and f["delta_m"] <= c["dense_min_m"] < f["prefilter_margin_m"]


def test_outcomes_are_binary_and_new_artifacts_carry_no_unknown_label():
    allowed = {"NO_TEMPLATE", "NO_COMPATIBLE_Q", "NO_COMPATIBLE_CONNECTOR", "CONNECTOR_COLLISION", "DESTINATION_OCCUPIED", "PHASE_INCONSISTENT",
               "SWEEP_PREFILTER_REJECT", "COLLISION_CURRENT_SCENE", "CHECK_BUDGET_EXHAUSTED", "TARGET_TEMPLATE_UNAVAILABLE",
               "TARGET_ACTION_COLLISION", "SEQUENCE_DISCONTINUITY", "REPLAY_REJECTED", "TARGET_NOT_AT_GOAL", "NO_CANDIDATE_SEQUENCE_ACCEPTED", None}
    for f in ("CHAINS.json", "PILOT_PROVIDER.json"):
        for r in g2.rd(g2.OUT / f)["rows"].values():
            assert r["status"] in (ar.SUCCESS, ar.FAILURE) and r["reason"] in allowed
    for f in g2.OUT.glob("*.json"):
        assert '"UNKNOWN' not in f.read_text(), f


def test_segments_are_exact_and_graph_is_validated():
    meta = g2.rd(g2.OUT / "catalog" / "GRAPH.json")
    assert meta["rejected"] == [] and len(meta["hubs"]) == 4
    T = ac.load_catalog()
    t = next(t for t in T.values() if t["kind"] != "ENTRY")
    sg = ac.segment(t["arrays"])
    q = np.concatenate([sg["entry"]["q"], sg["core"]["q"][1:], sg["exit"]["q"][1:]])
    assert np.array_equal(q, t["arrays"]["q"]) and str(sg["core"]["phase"][-1]) == "retreat" and not sg["exit"]["attached"].any()
    a = meta["actions"][f"A:{t['id']}"]
    assert a["from"] == ac.qid(sg["core"]["q"][0]) and a["to"] == ac.qid(sg["core"]["q"][-1])


def test_compile_budget_ledger_and_config_isolation(tmp_path):
    led = g2.rd(g2.OUT / "COMPILE_LEDGER.json")
    assert sum(e["attempts"] for e in led["entries"]) <= 120 and sum(e["cpu_s"] for e in led["entries"]) <= 25 * 60
    src = Path("approach_d.toml").read_text()
    (tmp_path / "bad.toml").write_text(src.replace('prefilter = "OFF"', 'prefilter = "OFF"\nonline_fallback = true'))
    with pytest.raises(ValueError):
        pv.pcfg(tmp_path / "bad.toml")
    assert pv.pcfg()["tiers"] == ["exact", "relative"]
    import subprocess
    assert subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "config.toml"]).returncode == 0
