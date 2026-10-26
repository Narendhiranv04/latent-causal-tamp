"""P17: corrected search state / dominance vs an exhaustive reference, existential fixed-sequence verification, certificate scope."""
import numpy as np

import p15_search as ps
import p17_search as s17
import p17_verify as pv


class Toy:
    def __init__(self, goal, edge, cert=("TARGET_PICK",)):
        self.g, self.e, self.cert = goal, edge, list(cert)

    def truncated(self):
        return False

    def goal(self, cells, q):
        st, t = self.g.get((tuple(sorted(cells.items())), float(q[0])), (ps.U_PLAN, 0.0))
        return st, ({"certificates": self.cert} if st == ps.CI else {"q": np.zeros((2, 3)), "gap": np.zeros(2)}), t

    def edges(self, cells, q, o, d):
        out = self.e.get((o, d, float(q[0])), [(ps.U_PLAN, None, 0.0)])
        return [(st, [{"q": np.zeros((2, 3)), "gap": np.zeros(2)}], None if q2 is None else np.array([q2]), t, {"via": "toy"}) for st, q2, t in out]


def _phys(toy, cells=(("A", 1), ("B", 2), ("t0", 9))):
    toy.s0 = type("S", (), {"objects": [type("O", (), {"id": i, "cell": c})() for i, c in cells], "robot": type("R", (), {"q_rad": (0.0,)})()})()
    return toy


def _run(toy, search, slots=(5, 6, 7), n=3, per_obj=2):
    sl = lambda c, o: [x for x in slots if x not in c.values()]  # noqa: E731
    return search(toy, lambda c, q, m, cand: cand, ["A", "B"], sl, {"A": 1, "B": 2, "t0": 9}, np.array([0.0]), n, per_obj, node_cap=10 ** 6)


def _last_mover_toy():
    # path 1: A->5 (q1, 1.0), B->6 (q3, 1.0)  [J 2.0, last B];  path 2: B->6 (q2, 1.0), A->5 (q3, 1.5)  [J 2.5, last A]
    # same (occupancy, q); only path 2 may move B again: B->7 at q3 makes the target feasible.
    e = {("A", 5, 0.0): [(ps.V, 1.0, 1.0)], ("B", 6, 1.0): [(ps.V, 3.0, 1.0)], ("B", 6, 0.0): [(ps.V, 2.0, 1.0)],
         ("A", 5, 2.0): [(ps.V, 3.0, 1.5)], ("B", 7, 3.0): [(ps.V, 4.0, 1.0)]}
    g = {((("A", 5), ("B", 7), ("t0", 9)), 4.0): (ps.V, 0.5)}
    return Toy(g, e)


def test_last_mover_dominance_counterexample():
    import p16_common as pc
    assert not _run(_last_mover_toy(), pc.search)["found"]                     # P16 key (occupancy, q) prunes the only path
    r = _run(_last_mover_toy(), s17.search)
    assert r["found"] and [x["object"] for x in r["plan"]["steps"]] == ["B", "A", "B"] and abs(r["plan"]["travel"] - 4.0) < 1e-12


def test_corrected_search_matches_exhaustive_reference():
    for kw in ({}, {"n_obj": 2, "n_slots": 2, "nq": 1, "p_goal": 0.08}):
        for seed in list(range(120)) + [115, 1563]:
            T, objs, sl, c0, q0 = s17.random_toy(seed, **kw)
            ref = s17.exhaustive(T, objs, sl, c0, q0, 3, 2)
            r = s17.search(T, lambda c, q, m, cand: cand, objs, sl, c0, q0, 3, 2, node_cap=10 ** 7)
            got = (r["plan"]["moves"], round(r["plan"]["travel"], 9)) if r["found"] else None
            assert got == ((ref["best"][0], round(ref["best"][1], 9)) if ref["best"] else None), (kw, seed)


def test_p16_search_fails_on_documented_seeds():
    import p16_common as pc
    for seed in (115, 1563):
        T, objs, sl, c0, q0 = s17.random_toy(seed, n_obj=2, n_slots=2, nq=1, p_goal=0.08)
        assert not pc.search(T, lambda c, q, m, cand: cand, objs, sl, c0, q0, 3, 2, node_cap=10 ** 7)["found"]
        assert s17.exhaustive(T, objs, sl, c0, q0, 3, 2)["best"] is not None


def test_dominance_requires_counts_and_key_includes_last_and_exact_q():
    assert s17.dominated([(1.0, {"A": 1})], 2.0, {"A": 1, "B": 1})
    assert not s17.dominated([(1.0, {"A": 2})], 2.0, {"A": 1})              # more moves used -> fewer remaining -> no dominance
    assert not s17.dominated([(3.0, {})], 2.0, {})
    assert s17.key({"A": 1}, [0.1], "A") != s17.key({"A": 1}, [0.1], "B")
    assert s17.key({"A": 1}, [0.1], "A") != s17.key({"A": 1}, [0.1 + 1e-13], "A")
    assert s17.key({"A": 1}, [0.1], "A", rule=False) == s17.key({"A": 1}, [0.1], "B", rule=False)


def test_unknown_blocks_no_plan_proof():
    e = {("A", 5, 0.0): [(ps.U_PLAN, None, 0.0)]}
    r = _run(Toy({}, e), s17.search, n=1, per_obj=1)
    assert not r["found"] and r["claim"] == "NO_PLAN_FOUND"


def _greedy_case():
    g = {((("A", 5), ("B", 6), ("t0", 9)), 3.0): (ps.V, 0.5)}
    e = {("A", 5, 0.0): [(ps.V, 1.0, 1.0), (ps.V, 2.0, 3.0)], ("B", 6, 2.0): [(ps.V, 3.0, 1.0)]}
    return g, e


def test_existential_succeeds_where_greedy_fails():
    import p16_common as pc
    g, e = _greedy_case()
    assert pc.verify_sequence(_phys(Toy(g, e)), [("A", 5), ("B", 6)])["status"] != ps.V
    r = pv.verify_existential(_phys(Toy(g, e)), [("A", 5), ("B", 6)])
    assert r["status"] == ps.V and abs(r["plan"]["travel"] - 4.5) < 1e-12 and r["plan"]["steps"][0]["object"] == "A"


def test_no_motion_works_is_unknown_not_negative():
    e = {("A", 5, 0.0): [(ps.U_PLAN, None, 0.0)]}
    assert pv.verify_existential(_phys(Toy({}, e)), [("A", 5)])["status"].startswith("UNKNOWN")


def test_certificate_scope_q_dependent_vs_q_independent():
    e = {("A", 5, 0.0): [(ps.V, 1.0, 1.0)]}
    g = {((("A", 5), ("B", 2), ("t0", 9)), 1.0): (ps.CI, 0.0)}
    assert pv.verify_existential(_phys(Toy(g, e, cert=["LINK0_SECTOR_PICK"])), [("A", 5)])["status"].startswith("UNKNOWN")
    assert pv.verify_existential(_phys(Toy(g, e, cert=["TARGET_PICK"])), [("A", 5)])["status"] == ps.CI
    assert pv.verify_existential(_phys(Toy({}, {})), [("A", 2)])["status"] == ps.CI          # destination occupied by B


def test_existential_minimum_travel_over_modes():
    g = {((("A", 5), ("B", 2), ("t0", 9)), 1.0): (ps.V, 5.0), ((("A", 5), ("B", 2), ("t0", 9)), 2.0): (ps.V, 0.1)}
    e = {("A", 5, 0.0): [(ps.V, 1.0, 1.0), (ps.V, 2.0, 2.0)]}
    r = pv.verify_existential(_phys(Toy(g, e)), [("A", 5)])
    assert r["status"] == ps.V and abs(r["plan"]["travel"] - 2.1) < 1e-12 and r["travel_minimal_over_alternatives"]


# ------------------------------------------------------------------ P17-2 shared scene-only domain
def _dev_phys(key="p13_2026210000"):
    import json
    from pathlib import Path
    import p15_lookup as pl
    import p16_common as pc
    import p16_motion as pm
    plan = json.loads(Path("runs/p16/data/dev/plan.json").read_text())["roots"]
    task = pc.task_from_root(plan[key], key)
    idx = pl.index_v2()[0]
    return plan[key], task, pm.DetPhysics(task, idx), idx


def test_domain_scene_only_and_all_movers():
    import p16_common as pc
    import p17_domain as dm
    root, task, phys, idx = _dev_phys()
    stripped = {k: v for k, v in root.items() if k not in ("items", "parking", "dest", "role_cells", "predicates", "ids", "mechanism")}
    assert pc.task_from_root(stripped, "p13_2026210000") == task
    cells = {o.id: o.cell for o in phys.s0.objects}
    mv, om = dm.movers(task, cells)
    assert len(mv) == 4 and not om and "t0" not in mv                                        # DENSE: all four movers, no cap
    a = dm.repairs(task, phys, idx)
    b = dm.repairs(task, phys, idx)
    assert a["sequences"] == b["sequences"] and a["kept"][4] > 0 and a["kept"][3] > 0         # deterministic, 0..4 moves
    assert any(len({o for o, _ in s}) < len(s) for s in a["sequences"])                       # repeated objects present
    assert all(s[i][0] != s[i + 1][0] for s in a["sequences"] for i in range(len(s) - 1))    # never consecutively


def test_slots_recomputed_after_moves_and_freed_source():
    import json
    from pathlib import Path
    import p17_domain as dm
    hits = 0
    for key in json.loads(Path("runs/p16/data/dev/pilot_keys.json").read_text()):
        root, task, phys, idx = _dev_phys(key)
        cells = {o.id: o.cell for o in phys.s0.objects}
        sl = dm.slot_fn(phys, idx, width=4, origin=cells)
        movable = [x for x in cells if x != "t0" and x not in task["fixed_ids"]]
        for o1 in movable:
            if cells[o1] not in phys.scr.valid:
                continue
            after = {**cells, o1: sl(cells, o1)[0]}
            for o2 in movable:
                if o2 != o1:
                    s2 = sl(after, o2)
                    assert all(x not in set(after.values()) for x in s2)                       # never an occupied cell
                    assert cells[o1] in s2                                                     # freed source offered
                    hits += 1
    assert hits > 0
    assert dm.query_id("k", [("a", 1), ("b", 2)]) != dm.query_id("k", [("b", 2), ("a", 1)])


def test_b_and_d_share_one_action_domain():
    import p17_domain as dm
    root, task, phys, idx = _dev_phys("p13_2026213000")
    cells = {o.id: o.cell for o in phys.s0.objects}
    sl = dm.slot_fn(phys, idx, width=4, origin=cells)
    rep = dm.repairs(task, phys, idx, width=4, caps={0: 1, 1: 100, 2: 1000, 3: 0, 4: 0})
    first = {tuple(s[0]) for s in rep["sequences"] if s}
    mv, _ = dm.movers(task, cells)
    assert first == {(o, d) for o in mv for d in sl(cells, o)[:6]}                          # B's 1-move set == D's root expansions
