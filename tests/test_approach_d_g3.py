"""Approach D G3 (approachD_G3_causal_repair_instructions_v1_4): D_CAUSAL_G3 logic on small deterministic fixtures (fake provider / fake D /
fake geometry, so each test isolates one claim), plus real-data checks (zero forbidden calls, original-target-only D, saved results)."""
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

import ad_causal as C
import ad_runtime as ar

CFG = {"top_movers": 2, "widening": [2], "dests_per_mover": 3, "templates_per_pair": 2, "universe_slots": 4, "beam": 3, "max_depth": 2,
       "max_reloc_attempts": 60, "max_expansions": 30, "max_d_calls": 200}


class Lat:
    def center(self, c):
        return np.array([c % 8, c // 8], float)


class St:
    goal_cell = 63

    def __init__(self):
        self.s0 = type("S", (), {"lattice": Lat()})()


class G:
    """Fake graph: one stored action per (src, dst), q_end node named after the action; optional extra template with another q_end."""

    def __init__(self, pairs, extra=()):
        self.actions, self.by_pair, self.q = {}, {}, {"home": np.zeros(3)}
        for i, (s, d) in enumerate(list(pairs) + list(extra)):
            aid = f"A{i}:{s}>{d}"
            self.actions[aid] = {"to": f"q_{aid}", "travel_J": float(i), "radius": 0.024}
            self.by_pair.setdefault((s, d), []).append(aid)
            self.q[f"q_{aid}"] = np.array([float(i + 1), 0.0, 0.0])


class Prov:
    """Fake provider: relocations succeed unless listed in `fail`; T succeeds iff every object in `need` has left its original cell."""

    def __init__(self, g, cells0, need, fail=()):
        self.g, self.cells0, self.need, self.fail, self.edge_calls = g, cells0, set(need), set(fail), []

    def order(self, prov, cells, o, d, cand):
        return cand

    def goal(self, cells, q):
        ok = all(cells[o] != self.cells0[o] for o in self.need)
        return {"status": "SUCCESS" if ok else "FAILURE", "reason": None if ok else "TARGET_ACTION_COLLISION", "steps": [("action", "T")],
                "object": "t0", "dest": St.goal_cell}

    def edges(self, cells, q, o, d, only=None):
        self.edge_calls.append((o, d, only))
        if (o, d) in self.fail:
            return {"status": "FAILURE", "reason": "COLLISION_CURRENT_SCENE", "steps": []}
        return {"status": "SUCCESS", "reason": None, "cells": {**cells, o: d}, "q_end": self.g.actions[only]["to"], "steps": [("action", only)],
                "object": o, "dest": d}

    def verify_plan(self, cells0, q0, steps):
        return {"status": "SUCCESS", "reason": None, "steps": len(steps)}

    def stats(self):
        return {"counts": {}}


class Geo:
    def __init__(self, rel, conf=None):
        self.rel, self.conf = rel, conf or {}

    def relevance(self, cells, o):
        return self.rel.get(o, 0.0)

    def conflict(self, cells, d):
        return self.conf.get(d, 0.0)


class Dor:
    """Fake D: marginals fixed; p_T after an edit from `after[(obj, dest)]`; records every (cells, q) it is asked about."""

    def __init__(self, marg, after=None, by_q=None):
        self.marg, self.after, self.by_q, self.calls, self.cpu, self.asked = marg, after or {}, by_q or {}, 0, 0.0, []

    def predict(self, cells, q, target="t0"):
        assert target == "t0"
        self.calls += 1
        self.asked.append((dict(cells), np.asarray(q, float).copy()))
        moved = [(o, d) for o, d in cells.items() if CELLS0.get(o) != d]
        p = max([self.after.get(m, 0.05) for m in moved] + [self.by_q.get(float(np.asarray(q)[0]), 0.0)] + [0.05])
        return {"p": p, "marg": dict(self.marg)}


CELLS0 = {"t0": 10, "o1": 1, "o2": 2, "o3": 3, "o4": 4}
SLOTS = {"o1": [21, 22], "o2": [23, 24], "o3": [25, 26], "o4": [27, 28]}
slot_f = lambda cells, o: SLOTS[o]  # noqa: E731
PAIRS = [(CELLS0[o], d) for o in SLOTS for d in SLOTS[o]]


def run(policy, prov, geo, dor, cfg=CFG):
    return C.search(policy, prov, St(), CELLS0, np.zeros(3), ["o1", "o2", "o3", "o4"], slot_f, geo, dor, cfg)


def frontier(r):
    return [t["frontier"] for t in r["trace"] if t["event"] == "frontier"][0]


def test_d_marginals_change_the_candidate_set_not_just_its_order():
    g = G(PAIRS)
    geo, dor = Geo({"o1": 0.9, "o2": 0.8}), Dor({"o3": 0.9, "o4": 0.8, "o1": 0.1, "o2": 0.1})
    one = {**CFG, "max_depth": 1}                                            # one relocation: the root frontier alone decides
    rd = run("D_CAUSAL_G3", Prov(g, CELLS0, need=["o3"]), geo, dor, one)
    rg = run("GEOM_CAUSAL", Prov(g, CELLS0, need=["o3"]), geo, None, one)
    assert set(frontier(rd)) == {"o3", "o4"} and set(frontier(rg)) == {"o1", "o2"}
    cd = {(t["object"]) for t in rd["trace"] if t["event"] == "certify"}
    cg = {(t["object"]) for t in rg["trace"] if t["event"] == "certify"}
    assert cd <= {"o3", "o4"} and cg <= {"o1", "o2"}                       # disjoint explored sets, same budget caps
    assert rd["status"] == "SUCCESS" and rg["status"] == "FAILURE"          # without widening, a wrong geometric frontier stays wrong


def test_counterfactual_p_T_changes_the_chosen_placement():
    g = G(PAIRS)
    geo, dor = Geo({"o1": 1.0}, conf={21: 0.0, 22: 0.5}), Dor({"o1": 0.9, "o2": 0.1}, after={("o1", 22): 0.9, ("o1", 21): 0.1})
    cfg = {**CFG, "beam": 1, "max_depth": 1}
    rd = run("D_CAUSAL_G3", Prov(g, CELLS0, need=["o1"]), geo, dor, cfg)
    rb = run("D_BLOCKER_ONLY", Prov(g, CELLS0, need=["o1"]), geo, Dor({"o1": 0.9, "o2": 0.1}), cfg)
    first = lambda r: next(t for t in r["trace"] if t["event"] == "certify")  # noqa: E731
    assert (first(rd)["object"], first(rd)["dest"]) == ("o1", 22)           # D's predicted post-edit feasibility decides
    assert (first(rb)["object"], first(rb)["dest"]) == ("o1", 21)           # geometric placement (lower sweep conflict) without the re-query


def test_counterfactual_query_uses_the_stored_motions_own_q_end():
    g = G(PAIRS, extra=[(1, 21)])                                           # two stored motions for o1 -> 21 with different q_end
    dor = Dor({"o1": 0.9, "o2": 0.1}, by_q={2.0: 0.2, 9.0: 0.8})
    run("D_CAUSAL_G3", Prov(g, CELLS0, need=["o1"]), Geo({}), dor, {**CFG, "beam": 1, "max_depth": 1})
    qs = {float(q[0]) for cells, q in dor.asked if cells.get("o1") == 21}
    want = {float(g.q[g.actions[a]["to"]][0]) for a in g.by_pair[(1, 21)]}
    assert want <= qs and len(want) == 2                                    # each candidate is scored at the q it actually reaches
    assert all(cells["t0"] == 10 for cells, _ in dor.asked)                 # T never moves; only the original target is queried


def test_two_step_repair_found_although_the_first_move_does_not_raise_p_T():
    g = G(PAIRS)
    dor = Dor({"o1": 0.6, "o2": 0.6, "o3": 0.1, "o4": 0.1})                 # no single edit raises p_T (all 0.05)
    r = run("D_CAUSAL_G3", Prov(g, CELLS0, need=["o1", "o2"]), Geo({}), dor)
    assert r["status"] == "SUCCESS" and r["depth"] == 2 and sorted(o for o, _ in r["moves"]) == ["o1", "o2"]


def test_widening_recovers_a_wrong_d_shortlist_within_the_same_budget():
    g = G(PAIRS)
    wrong = {"o1": 0.9, "o2": 0.8, "o3": 0.05, "o4": 0.01}
    narrow = run("D_CAUSAL_G3", Prov(g, CELLS0, need=["o3"]), Geo({}), Dor(wrong), {**CFG, "widening": [2], "max_depth": 1})
    wide = run("D_CAUSAL_G3", Prov(g, CELLS0, need=["o3"]), Geo({}), Dor(wrong), {**CFG, "widening": [2, 0], "max_depth": 1})
    assert narrow["status"] == "FAILURE" and wide["status"] == "SUCCESS" and wide["stage"] == 1
    assert wide["budget"]["reloc"] <= CFG["max_reloc_attempts"] and wide["budget"]["expand"] <= CFG["max_expansions"]


def test_budget_is_shared_and_enforced():
    g = G(PAIRS)
    r = run("UNIFORM", Prov(g, CELLS0, need=["o4"]), Geo({}), None, {**CFG, "widening": [2, 0], "max_reloc_attempts": 3})
    assert r["budget"]["reloc"] <= 3 and (r["status"] == "SUCCESS" or r["reason"] == "MOTION_CHECK_BUDGET")


def test_sweep_conflict_ranks_but_never_vetoes():
    g = G(PAIRS)
    geo = Geo({"o1": 1.0, "o2": 0.0}, conf={21: 1.0, 22: 1.0})              # every o1 slot lies in stored target sweeps
    r = run("GEOM_CAUSAL", Prov(g, CELLS0, need=["o1"]), geo, None, {**CFG, "max_depth": 1})
    assert r["status"] == "SUCCESS" and r["moves"][0][0] == "o1"


def test_failed_motion_never_becomes_a_successor():
    g = G(PAIRS)
    prov = Prov(g, CELLS0, need=["o1"], fail={("o1", 21), ("o1", 22)})
    r = run("D_CAUSAL_G3", prov, Geo({}), Dor({"o1": 0.9, "o2": 0.8}), {**CFG, "max_depth": 1})
    assert r["status"] == "FAILURE"
    assert all(t["status"] == "FAILURE" for t in r["trace"] if t["event"] == "certify" and t["object"] == "o1")


def test_doracle_refuses_temporary_targets():
    d = C.DOracle.__new__(C.DOracle)
    with pytest.raises(ValueError):
        d.predict({}, np.zeros(3), target="o1")


def test_real_root_zero_solver_calls_original_target_only_and_verified():
    root, cat, out, calls = C._root_job(("p13_2026210004", "C3", ("D_CAUSAL_G3", "GEOM_CAUSAL")))
    assert calls == 0 and all(v["status"] == "SUCCESS" and v["depth"] == 0 and v["replay"]["status"] == "SUCCESS" for v in out.values())


def test_saved_view_results_are_consistent_and_historical_artifacts_untouched():
    B = json.loads((C.OUT / "VIEW_B_C3.json").read_text())
    assert B["forbidden_calls"] == 0 and len({json.dumps(B["config"])}) == 1
    assert all(set(r) == set(C.POLICIES) for r in B["rows"].values())
    A = json.loads((C.OUT / "VIEW_A_calib.json").read_text())
    assert A["in_D_training"] is False and A["edit_auroc"]["D"] > A["edit_auroc"]["uniform"]
    for p in ("config.toml", "runs/p17/eval/P17_PROSPECTIVE.json", "runs/p16/data/calib/plan.json", "p17_d.py", "p16_motion.py"):
        assert subprocess.run(["git", "diff", "--quiet", "HEAD", "--", p]).returncode == 0, p
