"""P15: search algorithm invariants on synthetic providers (algorithm tests, NOT physical evidence), D-input builder contract, lookup
clustering determinism, and admission / metric errata guards."""
import json
import os
from pathlib import Path

import numpy as np
import pytest

os.environ.setdefault("P10C_OUT", "runs/p10c")

import p15_search as ps  # noqa: E402


class Toy:
    """goal: {(frozenset cells items, q): (status, travel)}; edge: {(o, d, q): [(status, q2, travel)]}; missing -> UNKNOWN_PLANNER."""

    def __init__(self, goal, edge):
        self.g, self.e, self.calls = goal, edge, []

    def truncated(self):
        return False

    def goal(self, cells, q):
        self.calls.append(("g", tuple(sorted(cells.items())), float(q[0])))
        st, t = self.g.get((tuple(sorted(cells.items())), float(q[0])), (ps.U_PLAN, 0.0))
        return st, {"goal": True}, t

    def edges(self, cells, q, o, d):
        out = self.e.get((o, d, float(q[0])), [(ps.U_PLAN, None, 0.0)])
        return [(st, [{"edge": (o, d)}], None if q2 is None else np.array([q2]), t, {"via": "toy"}) for st, q2, t in out]


def run(toy, movers=("A", "B"), slots=(5, 6), cells=None, order=None):
    cells = cells or {"A": 1, "B": 2, "t0": 9}
    sl = lambda c, o: [s for s in slots if s not in c.values()]  # noqa: E731
    return ps.search(toy, order or (lambda c, q, m, cand: cand), list(movers), sl, cells, np.array([0.0]))


C0 = (("A", 1), ("B", 2), ("t0", 9))


def test_01_zero_move_first_and_proven():
    r = run(Toy({(C0, 0.0): (ps.V, 1.0)}, {}))
    assert r["plan"]["moves"] == 0 and r["min_moves_proven"] and r["min_travel_proven"] and not r["log"]["edges"]


def test_02_cheaper_of_two_certified_modes_wins():
    g = {(C0, 0.0): (ps.CI, 0)}
    e = {("A", 5, 0.0): [(ps.V, 1.0, 2.0), (ps.V, 2.0, 1.0)]}
    for o, d in (("A", 6), ("B", 5), ("B", 6)):
        e[(o, d, 0.0)] = [(ps.CI, None, 0.0)]
    g[((("A", 5), ("B", 2), ("t0", 9)), 1.0)] = (ps.V, 0.5)
    g[((("A", 5), ("B", 2), ("t0", 9)), 2.0)] = (ps.V, 0.5)
    r = run(Toy(g, e))
    assert r["plan"]["moves"] == 1 and abs(r["plan"]["travel"] - 1.5) < 1e-12


def test_03_terminal_q_changes_whole_plan_optimum():
    g = {(C0, 0.0): (ps.CI, 0), ((("A", 5), ("B", 2), ("t0", 9)), 1.0): (ps.V, 3.0), ((("A", 5), ("B", 2), ("t0", 9)), 2.0): (ps.V, 0.5)}
    e = {("A", 5, 0.0): [(ps.V, 1.0, 1.0), (ps.V, 2.0, 1.5)], ("A", 6, 0.0): [(ps.CI, None, 0)], ("B", 5, 0.0): [(ps.CI, None, 0)], ("B", 6, 0.0): [(ps.CI, None, 0)]}
    r = run(Toy(g, e))
    assert abs(r["plan"]["travel"] - 2.0) < 1e-12 and r["min_travel_proven"]


def test_05_unknown_shorter_edge_blocks_min_moves_claim():
    g = {(C0, 0.0): (ps.CI, 0), ((("A", 5), ("B", 6), ("t0", 9)), 2.0): (ps.V, 1.0)}
    e = {("A", 5, 0.0): [(ps.V, 1.0, 1.0)], ("B", 6, 1.0): [(ps.V, 2.0, 1.0)]}            # every other edge UNKNOWN_PLANNER (missing)
    r = run(Toy(g, e))
    assert r["plan"]["moves"] == 2 and not r["min_moves_proven"] and r["claim"] == "BEST_VERIFIED_WITHIN_BUDGET"


def test_06_unknown_goal_at_depth0_no_zero_move_optimality():
    g = {((("A", 5), ("B", 2), ("t0", 9)), 1.0): (ps.V, 1.0)}                            # depth-0 goal UNKNOWN
    e = {("A", 5, 0.0): [(ps.V, 1.0, 1.0)], ("A", 6, 0.0): [(ps.CI, None, 0)], ("B", 5, 0.0): [(ps.CI, None, 0)], ("B", 6, 0.0): [(ps.CI, None, 0)]}
    r = run(Toy(g, e))
    assert r["plan"]["moves"] == 1 and not r["min_moves_proven"]


def test_07_occupied_slot_not_offered_and_freed_source_reusable():
    seen = []
    def order(c, q, m, cand):
        seen.append((dict(c), list(cand)))
        return cand
    g = {(C0, 0.0): (ps.CI, 0)}
    e = {("A", 5, 0.0): [(ps.V, 1.0, 1.0)]}
    run(Toy(g, e), slots=(5, 1), order=order)
    after = [cand for c, cand in seen if c["A"] == 5]
    assert after and ("B", 5) not in after[0] and ("B", 1) in after[0]                  # A sits on 5; A's old cell 1 is free


def test_08_memo_key_includes_object_identity():
    assert ps.state_key({"A": 1, "B": 2}, [0.0], ()) != ps.state_key({"A": 2, "B": 1}, [0.0], ())


def test_09_two_moves_of_one_object_excluded_by_move_once():
    g = {(C0, 0.0): (ps.CI, 0), ((("A", 1), ("B", 2), ("t0", 9)), 2.0): (ps.V, 1.0)}     # only "A away and back" would work
    e = {("A", 5, 0.0): [(ps.V, 1.0, 1.0)]}
    r = run(Toy(g, e), movers=("A",))
    assert not r["found"] and r["claim"] == "NO_PLAN_FOUND"


def test_10_dominance_keeps_cheaper_equal_state():
    tgt = (("A", 5), ("B", 6), ("t0", 9))
    g = {(C0, 0.0): (ps.CI, 0), (tgt, 3.0): (ps.V, 1.0)}
    e = {("A", 5, 0.0): [(ps.V, 1.0, 1.0)], ("B", 6, 1.0): [(ps.V, 3.0, 1.0)], ("B", 6, 0.0): [(ps.V, 2.0, 5.0)], ("A", 5, 2.0): [(ps.V, 3.0, 5.0)]}
    r = run(Toy(g, e))
    assert r["plan"]["moves"] == 2 and abs(r["plan"]["travel"] - 3.0) < 1e-12 and r["log"]["pruned_dominated"] + r["log"]["pruned_bnb"] >= 1


def test_11_guidance_changes_order_not_exhaustive_result():
    g = {(C0, 0.0): (ps.CI, 0), ((("A", 5), ("B", 2), ("t0", 9)), 1.0): (ps.V, 2.0), ((("A", 1), ("B", 6), ("t0", 9)), 2.0): (ps.V, 0.2)}
    e = {("A", 5, 0.0): [(ps.V, 1.0, 1.0)], ("B", 6, 0.0): [(ps.V, 2.0, 1.0)], ("A", 6, 0.0): [(ps.CI, None, 0)], ("B", 5, 0.0): [(ps.CI, None, 0)]}
    r1 = run(Toy(g, e))
    r2 = run(Toy(g, e), order=lambda c, q, m, cand: list(reversed(cand)))
    assert r1["plan"]["travel"] == r2["plan"]["travel"] == 1.2 and r1["plan"]["steps"] == r2["plan"]["steps"]


def test_12_deterministic_rerun():
    g = {(C0, 0.0): (ps.CI, 0), ((("A", 5), ("B", 2), ("t0", 9)), 1.0): (ps.V, 1.0)}
    e = {("A", 5, 0.0): [(ps.V, 1.0, 1.0)]}
    a, b = run(Toy(g, e)), run(Toy(g, e))
    for r in (a, b):                                                                      # anytime CPU stamps are timing, not outputs
        r["log"]["anytime"] = [{k: v for k, v in x.items() if k != "cpu_s"} for x in r["log"].get("anytime", [])]
    assert json.dumps(a, default=str, sort_keys=True) == json.dumps(b, default=str, sort_keys=True)


def test_metric_renamed_and_builder_reproduces_training_record():
    p = json.loads(Path("runs/p15/retarget/PROBES.json").read_text())
    assert p["summary"]["decided"] >= 40
    assert "moves_outside_original_blocker_union" in Path("p15_bench.py").read_text()


def test_13_partial_budget_edge_expands_verified_but_blocks_proofs():
    """An edge with one certified mode plus UNKNOWN_BUDGET (lookup budget exhausted before all modes) is expanded; no min-travel proof."""
    g = {(C0, 0.0): (ps.CI, 0), ((("A", 5), ("B", 2), ("t0", 9)), 1.0): (ps.V, 1.0)}
    e = {("A", 5, 0.0): [(ps.V, 1.0, 1.0), (ps.U_BUD, None, 0.0)], ("A", 6, 0.0): [(ps.CI, None, 0)], ("B", 5, 0.0): [(ps.CI, None, 0)],
         ("B", 6, 0.0): [(ps.CI, None, 0)]}
    r = run(Toy(g, e))
    assert r["found"] and r["plan"]["moves"] == 1 and r["min_moves_proven"] and not r["min_travel_proven"]


def test_14_exhausted_edge_budget_does_not_stop_search():
    import inspect
    src = inspect.getsource(ps.Physics.truncated) + inspect.getsource(ps.Physics._take)
    assert "self._trunc = True\n            return False" not in src and '"goal_plans" in self.exhausted' in src


def _root0():
    plan = json.loads(Path("runs/p15/prospective/plan.json").read_text())
    k = sorted(plan["roots"])[0]
    return k, plan["roots"][k]


def test_retarget_scene_moves_target_role_and_keeps_geometry():
    import p15_retarget as pr
    from scene import scene_from_dict
    _, r = _root0()
    s = scene_from_dict(r["scene"])
    o = next(x.id for x in s.objects if x.kind == "obstacle")
    s2 = pr.retarget_scene(s, {}, o, s.robot.q_rad)
    assert s2.get(o).kind == "target" and s2.get("t0").kind == "obstacle"
    assert [(x.id, x.cell, x.radius_m) for x in s.objects] == [(x.id, x.cell, x.radius_m) for x in s2.objects]


def test_index_v2_excludes_evaluation_roots_and_fingerprints():
    import p15_lookup as pl
    import p14_sweep_index as sx
    idx, dropped = pl.index_v2()
    P, excl = sx._plans(), set(json.loads(Path("runs/p14/eval_roster.json").read_text())["excluded_roots"])
    bad = {pl.json_fp(P[k]) for k in excl if k in P}
    roots = {e["root"] for es in idx.by_key.values() for e in es}
    assert dropped == 17 and not roots & excl and not {pl.json_fp(P[k]) for k in roots} & bad


def test_prospective_roster_disjoint_from_index_and_sealed_before_unseal():
    leak = json.loads(Path("runs/p15/prospective/LEAKAGE_CHECK.json").read_text())
    pre = json.loads(Path("runs/p15/P15_PREREG.json").read_text())
    assert leak["roots"] == 32 and not leak["index_overlap_by_root_or_fingerprint"] and len(pre["prospective"]["roster"]) == 32


def test_lookup_variants_only_filter_candidates():
    src = Path("p15_search.py").read_text()
    assert 'c["similarity"] >= SIM_THR' in src and 'c["rank_in_mode"] == 0' in src and abs(ps.SIM_THR - 1.0499131944444444) < 1e-12


def test_sign_test_exact_values():
    import p15_bench as pb
    assert abs(pb.sign_test([True] * 6, [False] * 6)["p_two_sided"] - 0.03125) < 1e-12
    assert pb.sign_test([True] * 5, [False] * 5)["status"] == "UNDERPOWERED"
