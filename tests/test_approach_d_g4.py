"""Approach D G4 (approachD_G4_local_witness_catalog_and_causal_repair_instructions_v1_0): stored-sweep demotion logic on deterministic
fixtures (reusing the G3 fakes), plus real-record checks on the saved G4 catalogs, diagnostics and evaluation."""
import glob
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

import ad_causal as C
import ad_g4 as G
import ad_runtime as ar
from test_approach_d_g3 import CELLS0, CFG, G as FakeGraph, PAIRS, Dor, Prov, St, slot_f


class SweepGeo:
    """Fake geometry with stored T sweeps: every stored T motion sweeps `blocked` cells (a placement there clashes with all of them)."""

    def __init__(self, rel, blocked, n_t=2):
        self.rel, self.blocked, self.n_t = rel, set(blocked), n_t

    def relevance(self, cells, o):
        return self.rel.get(o, 0.0)

    def conflict(self, cells, d):
        return 1.0 if d in self.blocked else 0.0

    def t_options(self, cells, d, movers):
        return self.n_t, 0 if d in self.blocked else self.n_t


def run(policy, prov, geo, dor, cfg=CFG):
    return C.search(policy, prov, St(), CELLS0, np.zeros(3), ["o1", "o2", "o3", "o4"], slot_f, geo, dor, cfg)


def first(r):
    return next(t for t in r["trace"] if t["event"] == "certify")


def test_original_target_and_exact_q_end_in_every_d_call():
    g = FakeGraph(PAIRS, extra=[(1, 21)])
    dor = Dor({"o1": 0.9, "o2": 0.1})
    run("D_CAUSAL_G4_SWEEP", Prov(g, CELLS0, need=["o1"]), SweepGeo({}, ()), dor, {**CFG, "beam": 1, "max_depth": 1})
    assert all(cells["t0"] == 10 for cells, _ in dor.asked)                       # T never moves, never a temporary target
    qs = {float(q[0]) for cells, q in dor.asked if cells.get("o1") == 21}
    assert {float(g.q[g.actions[a]["to"]][0]) for a in g.by_pair[(1, 21)]} <= qs   # each candidate scored at its own stored q_end


def test_sweep_demotion_changes_the_chosen_placement():
    g = FakeGraph(PAIRS)
    dor = lambda: Dor({"o1": 0.9, "o2": 0.1}, after={("o1", 21): 0.9, ("o1", 22): 0.5})  # noqa: E731   D prefers 21
    cfg = {**CFG, "beam": 1, "max_depth": 1}
    r3 = run("D_CAUSAL_G3", Prov(g, CELLS0, need=["o1"]), SweepGeo({}, {21}), dor(), cfg)
    r4 = run("D_CAUSAL_G4_SWEEP", Prov(g, CELLS0, need=["o1"]), SweepGeo({}, {21}), dor(), cfg)
    assert first(r3)["dest"] == 21 and first(r4)["dest"] == 22                    # 21 lies in every stored T sweep -> demoted
    fr = [t for t in r4["trace"] if t["event"] == "frontier"][0]["candidates"]
    assert any(c["demoted"] for c in fr) and all("t_options" in c for c in fr)


def test_demotion_never_vetoes_a_valid_intermediate():
    g = FakeGraph(PAIRS)
    prov = Prov(g, CELLS0, need=["o1", "o2"], fail={("o1", 22), ("o2", 24)})     # only 21 / 23 realise; both lie in every T sweep
    r = run("D_CAUSAL_G4_SWEEP", prov, SweepGeo({}, {21, 23}), Dor({"o1": 0.9, "o2": 0.8}), {**CFG, "beam": 4})
    assert r["status"] == "SUCCESS" and r["depth"] == 2 and sorted(m[1] for m in r["moves"]) == [21, 23]   # reached via demoted slots


def test_failed_motion_never_becomes_a_successor_under_demotion():
    g = FakeGraph(PAIRS)
    prov = Prov(g, CELLS0, need=["o1"], fail={("o1", 21), ("o1", 22)})
    r = run("D_CAUSAL_G4_SWEEP", prov, SweepGeo({}, {22}), Dor({"o1": 0.9, "o2": 0.8}), {**CFG, "max_depth": 1})
    assert r["status"] == "FAILURE" and not any(t["status"] == "SUCCESS" for t in r["trace"] if t["event"] == "certify" and t["object"] == "o1")


def test_budgets_are_global_across_widening_and_identical_across_policies():
    g = FakeGraph(PAIRS)
    cfg = {**CFG, "widening": [2, 0], "max_reloc_attempts": 3}
    for pol in ("D_CAUSAL_G4_SWEEP", "GEOM_CAUSAL", "UNIFORM"):
        r = run(pol, Prov(g, CELLS0, need=["o4"]), SweepGeo({}, ()), Dor({"o1": 0.9}) if pol.startswith("D") else None, cfg)
        assert r["budget"]["reloc"] <= 3
    ev = json.loads((G.OUT / "eval" / "EVAL_W_ROOT.json").read_text())
    assert ev["policies"] == list(C.G4_POLICIES) and ev["config"] == C.ccfg()     # one config for every policy and root
    assert all(set(r) == set(C.G4_POLICIES) for r in ev["rows"].values()) and len(ev["rows"]) == 12   # no root filtering


def test_provenance_never_mixes_and_transfer_never_reads_dev():
    m = json.loads((G.OUT / "manifest" / "WITNESS_MANIFEST.json").read_text())
    dev = set(G.dev_roots())
    assert not {x["root"] for x in m["transfer_pool"]} & dev
    tr = json.loads((G.OUT / "catalogs" / "W_TRANSFER_PIECES.json").read_text())["rows"]
    assert tr and all(r["split"] == "train" and r["root"] not in dev for r in tr)
    for name, own, other in (("W_ROOT", "W_ROOT_WITNESS", "W_TRANSFER_WITNESS"), ("W_TRANSFER", "W_TRANSFER_WITNESS", "W_ROOT_WITNESS")):
        gm = json.loads((G.OUT / "catalogs" / f"GRAPH_{name}.json").read_text())
        w = [a for a in gm["actions"].values() if any(o.startswith("W_") for o in a["origins"])]
        assert w and all(a["origins"] == [own] for a in w) and not any(other in a["origins"] for a in gm["actions"].values())
        assert all(a["root"] not in dev for a in w) if name == "W_TRANSFER" else all(a["root"] in dev for a in w)


def test_witness_pieces_are_bitwise_continuous_and_validated():
    meta, arr = G.load_pieces("W_ROOT")
    assert len(meta) == 30 and all(r["status"] == "VERIFIED" and r["replay"]["ok"] for r in meta)
    for r in meta:
        qs = [arr[p["key"]]["q"] for p in r["pieces"]]
        assert np.array_equal(qs[0][0], np.asarray(r["q0"])) and all(np.array_equal(a[-1], b[0]) for a, b in zip(qs, qs[1:]))
        assert all(p["check"]["ok"] for p in r["pieces"]) and r["pieces"][-1]["object"] == "t0"


def test_unconnected_pose_fails_closed_and_discontinuity_is_rejected():
    import ad_local as L
    st = L.Stub("p13_2026216000")
    cells0 = {o.id: o.cell for o in st.s0.objects}
    g = G._graph("W_ROOT")
    prov = G._prov(st, g, "p13_2026216000", "test")
    with ar.forbid("raise") as calls:
        r = prov.edges(cells0, np.asarray(st.s0.robot.q_rad) + 1e-3, "o00", 59)
        assert r["status"] == "FAILURE" and r["reason"] == "NO_COMPATIBLE_Q"          # no snapping onto a stored node
        rid = next(i for i, a in g.actions.items() if a["origins"] == ["W_ROOT_WITNESS"] and a["root"] == "p13_2026216000" and a["object"] == "o00")
        v = prov.verify_plan(cells0, st.s0.robot.q_rad, [("action", rid, "o00")])     # skips the stored entry connector
        assert v["status"] == "FAILURE" and v["reason"] == "SEQUENCE_DISCONTINUITY"
    assert sum(calls.values()) == 0


def test_forbidden_guard_trips_and_g4_runtime_records_zero_calls():
    import planner as pn
    with ar.forbid("raise"), pytest.raises(ar.ForbiddenCall):
        pn.plan(None, np.zeros(3), np.zeros(3), 0.0, {}, 1, "x", True)
    av = json.loads((G.OUT / "diagnostics" / "AVAILABILITY.json").read_text())
    assert av["forbidden_calls"] == 0
    for f in glob.glob(str(G.OUT / "eval" / "EVAL_*.json")):
        assert json.loads(Path(f).read_text())["forbidden_calls"] == 0


def test_f12_stays_a_one_relocation_verified_repair():
    lab = {}
    for f in sorted(glob.glob("runs/p16/data/dev/labels_v2w*.json")):
        lab.update(json.loads(Path(f).read_text()))
    s = lab["p13_2026216000"]["sequences"]
    assert s["o00>59"]["status"] == "VERIFIED"                                   # one relocation suffices historically
    w = json.loads((G.OUT / "manifest" / "WITNESS_MANIFEST.json").read_text())["cohort_A"]["p13_2026216000"]
    assert min(len(x) for x in w["witnesses"]) == 1


def test_g3_c3_and_history_untouched():
    b = json.loads((G.OUT / "baseline" / "BASELINE.json").read_text())
    for f, h in b["files_sha256"].items():
        if f != "approach_d.toml":                                                    # the overlay only gains the additive [g4] section
            assert hashlib.sha256(Path(f).read_bytes()).hexdigest() == h, f
    vb = json.loads((C.OUT / "VIEW_B_C3.json").read_text())
    assert vb["summary"]["D_CAUSAL_G3"]["success"] == 1 and set(vb["rows"]["p13_2026210004"]) == set(C.POLICIES)
    ev = json.loads((G.OUT / "eval" / "EVAL_C3.json").read_text())["rows"]          # G3 policies re-run under G4 code on C3: identical traces
    sig = lambda r: [(t["event"], t.get("object"), t.get("dest"), t.get("action"), t.get("status")) for t in r["trace"]]  # noqa: E731
    for k in vb["rows"]:
        for p in ("D_CAUSAL_G3", "GEOM_CAUSAL", "D_BLOCKER_ONLY", "UNIFORM"):
            assert sig(ev[k][p]) == sig(vb["rows"][k][p]) and ev[k][p]["budget"] == vb["rows"][k][p]["budget"], (k, p)
    for p in ("config.toml", "runs/p17/eval/P17_PROSPECTIVE.json", "runs/p16/data/calib/plan.json", "p17_d.py", "p16_motion.py", "p16_common.py"):
        assert subprocess.run(["git", "diff", "--quiet", "HEAD", "--", p]).returncode == 0, p
