"""Approach D G2a (approachD_G2_offline_only_instructions_v1_1): offline compiler, compiled-template catalog and the zero-solver runtime.
Every runtime call below runs under ad_runtime.forbid('raise'): any IK / planner / connector / grasp-synthesis entry point raises."""
import ast
import collections
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

import ad_compile as ac
import ad_runtime as ar
import geometry as ge
import motion as mo
import p14_sweep_index as sx
from scene import place_scene

SRC, DST = 45, 47


@pytest.fixture(scope="module")
def built():
    """Two templates for 45 -> 47 from different (pick, place) branch classes, compiled OFFLINE (outside any guard)."""
    cfg, robot, p = ac.setup()
    s, good, goodp, _ = ac.screens(cfg, robot, p, SRC, DST)
    pairs = ac.direct_pairs(good, goodp, np.array(robot.q_home), 3, "spread")
    ts = []
    for pr in pairs[:2]:
        a, term, neg, _ = ac.realize(cfg, robot, p, s, DST, *pr, f"test/{ac.gkey(*pr)}")
        assert a is not None and ac.validate(cfg, robot, p, s, "t0", a, s.lattice.center(DST))["ok"], term
        row = ac.record(cfg, robot, "DIRECT_OFFLINE:spread", "RELOCATION", SRC, DST, a, {}, 0.0)
        ts.append({**row, "arrays": a, "q_start": np.asarray(row["q_start"]), "q_end": np.asarray(row["q_end"])})
    return cfg, robot, p, ts


def _scene(cfg, obstacles=()):
    return place_scene(cfg, "test", "g2a", [SRC], list(obstacles))


def test_runtime_module_static_deny_by_default():
    """ad_runtime's inference functions import and reference only an allowlist (FK / occupancy / frozen-trajectory certification)."""
    tree = ast.parse(Path("ad_runtime.py").read_text())
    imports = {a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names} | \
              {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert imports <= {"annotations", "__future__", "collections", "contextlib", "importlib", "sys", "numpy", "geometry", "motion"}
    allow = {("ge", "Checker"), ("ge", "make_world"), ("ge", "certify"), ("ge", "CLEAR"), ("ge", "COLLISION"), ("mo", "certify_trajectory")}
    for f in (n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ("check", "check_entry", "_params")):
        used = {(a.value.id, a.attr) for a in ast.walk(f) if isinstance(a, ast.Attribute) and isinstance(a.value, ast.Name)
                and a.value.id in ("ge", "mo")}
        assert used <= allow, (f.name, used - allow)
        names = {n.id for n in ast.walk(f) if isinstance(n, ast.Name)} | {a.attr for a in ast.walk(f) if isinstance(a, ast.Attribute)}
        assert not names & {"ik", "ik_track", "ik_line", "carry_line", "plan", "plan_skill", "screen_pick", "screen_place", "_rrt_connect"}


def test_forbid_blocks_every_entry_point_and_restores_them():
    import importlib
    import p15_search as ps
    import p16_motion as pm
    before = {(m, n): getattr(importlib.import_module(m), n) for m, ns in ar.FORBIDDEN.items() for n in ns if "." not in n}
    with ar.forbid() as calls:
        for leaf in ar.LEAVES:
            m, n = leaf.split(".")
            with pytest.raises(ar.ForbiddenCall):
                getattr(importlib.import_module(m), n)()
        with pytest.raises(ar.ForbiddenCall):
            pm.DetPhysics._goal(None, None, None)                  # inherited from p15_search.Physics: patched on DetPhysics too
    assert all(calls[x] == 1 for x in ar.LEAVES)
    assert before == {(m, n): getattr(importlib.import_module(m), n) for m, ns in ar.FORBIDDEN.items() for n in ns if "." not in n}
    assert "_goal" not in pm.DetPhysics.__dict__ and "_goal" in ps.Physics.__dict__


def test_first_valid_alternative_and_failure_paths_make_zero_solver_calls(built):
    cfg, robot, p, (t1, t2) = built
    home = np.array(robot.q_home)
    only1 = sorted(set(t1["swept"]) - set(t2["swept"]) - {SRC, DST})
    both = sorted(set(t1["swept"]) & set(t2["swept"]) - {SRC, DST})
    with ar.forbid() as calls:
        r = ar.check(robot, cfg, _scene(cfg), "t0", DST, home, [t1, t2], 6)
        assert (r["status"], r["template_id"], r["checks"]) == (ar.SUCCESS, t1["id"], 1)          # stops at the first accepted template
        r = ar.check(robot, cfg, _scene(cfg, only1[:1]), "t0", DST, home, [t1, t2], 6)
        assert r["status"] == ar.SUCCESS and r["template_id"] == t2["id"] and r["rejected"][0]["by"] == "SWEPT_PREFILTER"
        hit = next(c for c in both if ar.check(robot, cfg, _scene(cfg, [c]), "t0", DST, home, [t1, t2], 6, prefilter=False)["reason"]
                   == "COLLISION_ALL_CHECKED")                       # the sweep is conservative: take a cell the certifier rejects for both
        r = ar.check(robot, cfg, _scene(cfg, [hit]), "t0", DST, home, [t1, t2], 6, prefilter=False)
        assert (r["status"], r["checks"]) == (ar.FAILURE, 2) and all(x["verdict"] == ge.COLLISION for x in r["rejected"])
        assert ar.check(robot, cfg, _scene(cfg, [hit]), "t0", DST, home, [t1, t2], 1, prefilter=False)["reason"] == "CHECK_BUDGET_EXHAUSTED"
        assert ar.check(robot, cfg, _scene(cfg, [DST]), "t0", DST, home, [t1], 6)["reason"] == "DEST_OCCUPIED"
        assert ar.check(robot, cfg, _scene(cfg), "t0", DST, home, [], 6)["reason"] == "NO_TEMPLATE"
        assert ar.check(robot, cfg, _scene(cfg), "t0", DST, home + 1e-6, [t1], 6)["reason"] == "NO_COMPATIBLE_START"
        assert ar.check(robot, cfg, _scene(cfg), "t0", DST, home, [{**t1, "radius": 0.03}], 6)["reason"] == "FOOTPRINT_MISMATCH"
    assert not calls


def test_same_relative_motion_elsewhere_is_a_pattern_never_an_executable_template(built):
    """A template compiled for 45 -> 47 is never accepted for the same displacement at another absolute pair (37 -> 39): there is no
    runtime translation, retargeting or IK; the move fails closed with NO_TEMPLATE."""
    cfg, robot, p, (t1, _) = built
    assert sx.rel_key(SRC, DST, 0.024) == sx.rel_key(37, 39, 0.024)
    s = place_scene(cfg, "test", "shift", [37], [])
    with ar.forbid() as calls:
        r = ar.check(robot, cfg, s, "t0", 39, np.array(robot.q_home), [t1], 6)
    assert (r["status"], r["reason"]) == (ar.FAILURE, "NO_TEMPLATE") and not calls


def test_whole_arm_collision_outside_the_local_patches_is_caught(built):
    """An obstacle the 3x3 / 4x4 source and destination patches cannot see (outside both windows) but on the stored whole-arm sweep:
    the frozen-trajectory certifier rejects it and names the phase and body pair."""
    cfg, robot, p, (t1, _) = built
    near = lambda c, x: max(abs(c // 8 - x // 8), abs(c % 8 - x % 8)) <= 2  # noqa: E731   (covers both window shapes)
    far = [c for c in t1["swept"] if not near(c, SRC) and not near(c, DST)]
    assert far, "the stored sweep reaches beyond the object-local windows (whole arm)"
    with ar.forbid() as calls:
        for c in far:
            s = _scene(cfg, [c])
            r = ar.check(robot, cfg, s, "t0", DST, np.array(robot.q_home), [t1], 6, prefilter=False)
            if r["status"] == ar.FAILURE:
                break
    occ = sx._occ(s, 63, "t0")
    assert sx.windows(occ, SRC) == sx.windows(sx._occ(_scene(cfg), 63, "t0"), SRC)
    assert sx.windows(occ, DST) == sx.windows(sx._occ(_scene(cfg), 63, "t0"), DST)
    rej = r["rejected"][0]
    assert r["reason"] == "COLLISION_ALL_CHECKED" and rej["verdict"] == ge.COLLISION and rej["phase"] in mo.PHASES and "o00" in rej["pair"]
    assert not calls


def test_entry_template_is_precompiled_and_checked_not_planned():
    import p6_scenes as p6
    out = ac.compile_entries({"S2": p6.STRATA["S2"]})
    (row, a), = out["templates"]
    cfg, robot, _ = ac.setup()
    tpl = {**row, "arrays": a, "q_start": np.asarray(row["q_start"]), "q_end": np.asarray(row["q_end"])}
    assert np.array_equal(tpl["q_end"], np.array(robot.q_home)) and out["attempts"][0]["compiled"] == 1
    with ar.forbid() as calls:
        assert ar.check_entry(robot, cfg, _scene(cfg), p6.STRATA["S2"], tpl)["status"] == ar.SUCCESS
        assert ar.check_entry(robot, cfg, _scene(cfg), p6.STRATA["S1"], tpl)["reason"] == "NO_COMPATIBLE_START"
    assert not calls


def test_exact_base_rotation_needs_both_endpoints_and_has_no_valid_lattice_pair(built):
    """Controlled off-lattice fixture: q1 + psi carries the whole compiled record rigidly about the base and re-certifies at the rotated
    poses; the same rotation does not serve a lattice pair whose destination it misses. On the lattice no valid-cell ordered pair has an
    exact rotation partner (only radially collinear pairs touching the link-0 annulus do)."""
    import p6_scenes as p6
    cfg, robot, p, (t1, _) = built
    psi = 0.10
    a = ac.rotate(robot, t1["arrays"], psi)
    b, R = np.asarray(robot.base), np.array([[math.cos(psi), -math.sin(psi)], [math.sin(psi), math.cos(psi)]])
    s0 = _scene(cfg)
    o = s0.get("t0")
    rs = replace(s0, objects=(replace(o, xy_m=tuple(R @ (np.asarray(o.xy_m) - b) + b), cell=None),))
    assert all(v.status == ge.CLEAR for v in mo.certify_trajectory(robot, rs, "t0", a, p["delta"], p["eps"], p["evals"]))
    assert np.allclose(a["place_xy"], R @ (np.asarray(t1["arrays"]["place_xy"]) - b) + b)
    assert not np.array_equal(a["q"][0], np.array(robot.q_home))       # rotated start is off home: needs offline connectors (complete)
    res, best = sx.base_residual(robot.base, SRC, DST, SRC + 8, DST + 8)
    assert res > 0.01                                                  # a grid translation is not a base rotation
    a2 = ac.rotate(robot, t1["arrays"], best)
    assert np.linalg.norm(a2["place_xy"] - sx.center(DST + 8)) > p["release_tol"]
    scr = p6.Screens(cfg, robot)
    valid = sorted(scr.valid)
    sig = collections.defaultdict(list)
    for s in valid:
        for d in valid:
            if s != d:
                (rs_, a_), (rd_, b_) = [(round(float(np.hypot(*(sx.center(c) - b))), 9),
                                         math.atan2(*(sx.center(c) - b)[::-1])) for c in (s, d)]
                sig[(rs_, rd_, round((b_ - a_ + math.pi) % (2 * math.pi) - math.pi, 9))].append((s, d))
    assert all(len(v) == 1 for v in sig.values())


def test_complete_keeps_a_stored_witness_core_verbatim():
    import json
    import g4d_run as gr
    e = next(e for e in json.loads(Path("runs/p14/lookup/INDEX.json").read_text())["entries"] if (e["src"], e["dst"]) == (SRC, DST))
    a = gr._arrays(Path(e["file"]))[e["index"]]
    cfg, robot, p = ac.setup()
    s = ac.fixture(cfg, SRC)
    out, term, neg = ac.complete(cfg, robot, p, s, "t0", a, "test/complete")
    assert out is not None and ac.validate(cfg, robot, p, s, "t0", out, s.lattice.center(DST))["ok"], term
    q, n = np.asarray(out["q"]), len(a["q"])
    k = next(i for i in range(len(q) - n + 1) if np.array_equal(q[i:i + n], a["q"]))
    assert list(map(str, out["phase"][k:k + n - 1])) == list(map(str, a["phase"]))
    assert np.array_equal(q[0], robot.q_home) and np.array_equal(q[-1], robot.q_home)


def test_compile_outcomes_are_binary_with_metadata_only():
    class P:
        def __init__(self, status, reason):
            self.status, self.reason = status, reason
    assert ac._neg(P(ge.COLLISION, "LINK0_SWEEP:x")) == "CERTIFIED"
    assert ac._neg(P(ge.UNRESOLVED, "BUDGET_EXHAUSTED:nodes")) == "TIMEOUT"
    assert ac._neg(P(ge.UNRESOLVED, "DIRECT_ONLY")) == "NO_PLAN_FOUND"
    r = ac.attempt("DIRECT_OFFLINE:order", 0, 4, {}, False, "BUDGET_EXHAUSTED", "TIMEOUT", 1.0)
    assert r["compiled"] == 0 and r["negative_kind"] == "TIMEOUT" and r["label_protocol"] == "AD_BINARY_BUDGET_V1"
    assert ac.attempt("x", 0, 4, {}, True, "WITNESS_RECHECKED", None, 1.0)["negative_kind"] is None
    with pytest.raises(AssertionError):
        ac.attempt("x", 0, 4, {}, False, "?", "UNKNOWN", 1.0)       # no third label
    out = ac.compile_job({"src": 0, "dst": 4, "kind": "PROBE", "direct_k": 2, "seeds": [], "exact": []})   # inside the link-0 annulus
    assert not out["templates"] and {a["compiled"] for a in out["attempts"]} == {0}
    assert all(a["negative_kind"] in ac.NEG for a in out["attempts"])


def test_seeded_snap_keeps_the_seed_branches_and_bounds_the_shift():
    C = lambda phi, b: sk_cand(phi, b)  # noqa: E731
    good, goodp = [C(0.0, 1), C(0.5, 1), C(0.5, -1)], [C(1.0, -1), C(2.0, 1)]
    pair, why, shift = ac.seeded_pair(good, goodp, ((0.45, 1), (2.1, 1)), 0.0, math.radians(30))
    assert why is None and (pair[0].phi, pair[0].branch, pair[1].phi, pair[1].branch) == (0.5, 1, 2.0, 1)
    assert ac.seeded_pair(good, goodp, ((0.45, 1), (2.1, 1)), 1.0, math.radians(30))[1] == "SEED_GRASP_UNAVAILABLE"
    assert ac.seeded_pair(good, [C(1.0, -1)], ((0.45, 1), (2.1, 1)), 0.0, math.radians(30))[1] == "SEED_BRANCH_UNAVAILABLE"


def sk_cand(phi, b):
    import skill as sk
    return sk.Candidate(phi, b, "OK")


def test_catalog_roundtrip_identity_and_versioned_ids(built, tmp_path, monkeypatch):
    cfg, robot, p, (t1, t2) = built
    monkeypatch.setattr(ac, "OUT", tmp_path)
    strip = lambda t: {k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in t.items() if k != "arrays"}  # noqa: E731
    cat = ac.save_catalog([(strip(t), t["arrays"]) for t in (t1, t2)], [], "T")
    T = ac.load_catalog("T")
    assert set(T) == {t1["id"], t2["id"]} and cat["execution_index"] == {f"{SRC}>{DST}|0.024|home": [t1["id"], t2["id"]]}
    assert all(np.array_equal(T[t1["id"]]["arrays"][k], t1["arrays"][k]) for k in t1["arrays"])
    a = {**t1["arrays"], "q": t1["arrays"]["q"].copy()}
    a["q"][3, 0] += 1e-6
    assert ac.tid(a, SRC, DST) != t1["id"] and ac.tid(t1["arrays"], SRC, DST + 1) != t1["id"]


def test_config_sections_validated_and_config_toml_untouched(tmp_path):
    src = Path("approach_d.toml").read_text()
    (tmp_path / "bad.toml").write_text(src.replace('contract = "Q_HOME"', 'contract = "ANY_Q"'))
    with pytest.raises(ValueError):
        ac.ccfg(tmp_path / "bad.toml")
    (tmp_path / "bad2.toml").write_text(src.replace("direct_k = 6", "direct_k = 6\nonline_fallback = true"))
    with pytest.raises(ValueError):
        ac.ccfg(tmp_path / "bad2.toml")
    import config as cf
    c = cf.load_config("config.toml")
    assert "compiler" not in c and "runtime" not in c
