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


def test_fast_b_scorer_equals_root_eval9_marginals():
    import torch
    import p17_b as pb
    recs = torch.load("runs/p16/b/DEV_records.pt", weights_only=False)
    rs = pb.prepare((recs["roots"] if isinstance(recs, dict) else recs)[:2])
    for arm in ("LB", "LB+G", "FULLB", "A"):
        torch.manual_seed(0)
        m = pb.model(arm).eval()
        f, s = pb.score(m, arm, rs), pb.score_slow(m, arm, rs)
        for k in f:
            assert [x["query"] for x in f[k]] == [x["query"] for x in s[k]]
            assert max(abs(x["p"] - y["p"]) for x, y in zip(f[k], s[k])) < 1e-12


# ------------------------------------------------------------------ P17 search: repeats, cycles and finite-domain claims
def _repeat_toy():
    # only A->5, B->6, A->7 clears the target; no-repeat plans are all decided negative.
    e = {("A", 5, 0.0): [(ps.V, 1.0, 1.0)], ("B", 6, 1.0): [(ps.V, 2.0, 1.0)], ("A", 7, 2.0): [(ps.V, 3.0, 1.0)]}
    g = {((("A", 7), ("B", 6), ("t0", 9)), 3.0): (ps.V, 0.5)}
    t = Toy(g, e)
    t.e = {k: v for k, v in e.items()}
    dflt = [(ps.CI, None, 0.0)]
    t.edges = lambda cells, q, o, d, _t=t: [(st, [{"q": np.zeros((2, 3)), "gap": np.zeros(2)}], None if q2 is None else np.array([q2]), tt, {"via": "toy"})
                                          for st, q2, tt in _t.e.get((o, d, float(q[0])), dflt)]
    t.goal = lambda cells, q, _g=g: ((lambda st, tt: (st, {"certificates": ["TARGET_PICK"]} if st == ps.CI else {"q": np.zeros((2, 3)), "gap": np.zeros(2)}, tt))(
        *_g.get((tuple(sorted(cells.items())), float(q[0])), (ps.CI, 0.0))))
    return t


def test_repeat_needed_no_repeat_class_fully_refuted():
    t = _phys(_repeat_toy())
    r1 = _run(t, s17.search, n=4, per_obj=1)
    assert not r1["found"] and r1["claim"] == "NO_PLAN_IN_FULLY_ADJUDICATED_FINITE_GRAPH"
    r2 = _run(_phys(_repeat_toy()), s17.search, n=4, per_obj=2)
    assert r2["found"] and [(s["object"], s["dest"]) for s in r2["plan"]["steps"]] == [("A", 5), ("B", 6), ("A", 7)]
    assert r2["claim"].startswith("MIN_MOVES")
    ref = s17.exhaustive(_phys(_repeat_toy()), ["A", "B"], lambda c, o: [x for x in (5, 6, 7) if x not in c.values()], {"A": 1, "B": 2, "t0": 9},
                         np.array([0.0]), 4, 2)
    assert ref["best"][0] == 3 and not ref["undecided_depths"]


def test_library_domain_refutation_is_scoped_and_budget_stays_unknown(monkeypatch):
    import p15_search as ps_
    import p16_motion as pm
    import p17_mech as m
    _, task, _, idx = _dev_phys()
    ph = m.lib_domain(task, idx)
    for why, expect in (("LIBRARY_COLLISION", ps_.CI), (ps_.U_TR, ps_.CI), (ps_.U_LIB, ps_.CI),
                        ("motion_checks exhausted before all modes were tried", ps_.U_BUD)):
        monkeypatch.setattr(pm.DetPhysics, "_edges", lambda self, c, q, o, d, k, _w=why: [(ps_.U_BUD, None, None, 0.0, {"lookup": _w})])
        r = type(ph)._edges(ph, {}, None, "o00", 1, ("edge",))
        assert r[0][0] == expect and (expect != ps_.CI or r[0][4]["scope"] == m.LIB_DOMAIN)
    assert ph.transit == "direct" and ph.budget["online_moves"] == 0


# ------------------------------------------------------------------ replay: continuity and mid-sweep collision
def test_replay_rejects_discontinuity_and_moved_obstacle_in_recorded_sweep():
    import copy
    import p16_motion as pm
    _, task, _, idx = _dev_phys()
    ph = pm.DetPhysics(task, idx)
    v = pv.verify_existential(ph, [("o02", 62)], first=True)
    assert v["status"] == pv.V and pm.replay(ph, v["plan"])["ok"]
    bad = copy.deepcopy(v["plan"])
    bad["records"][-1]["q"] = np.asarray(bad["records"][-1]["q"], float) + 0.05
    assert pm.replay(ph, bad) == {"ok": False, "step": "target", "why": "discontinuous record"} or not pm.replay(ph, bad)["ok"]
    moved = copy.deepcopy(v["plan"])
    moved["steps"][0]["dest"] = 36                                   # P17 M5 instance: o02 at 36 lies in the recorded target sweep
    assert not pm.replay(ph, moved)["ok"]


# ------------------------------------------------------------------ B: lean / generic / capacity / coupling-off controls
def _b_roots(n=2):
    import torch
    import p17_b as pb
    recs = torch.load("runs/p16/b/DEV_records.pt", weights_only=False)
    return pb.prepare((recs["roots"] if isinstance(recs, dict) else recs)[:n])


def test_b_arms_structure_and_parameter_matched_control():
    import p17_b as pb
    n = {a: sum(p.numel() for p in pb.model(a).parameters()) for a in ("LB", "LB+G", "LB-W", "FULLB")}
    assert n["LB"] < n["LB+G"] and abs(n["LB-W"] - n["LB+G"]) / n["LB+G"] < 0.001 and n["FULLB"] > n["LB+G"]
    g = dict(pb.model("LB+G").named_modules())
    assert "cpl" in g and not any(k.startswith(("pair_scene", "pair_omit", "ho_")) for k in g)
    assert not any(k.startswith("cpl") for k in dict(pb.model("LB").named_modules()))


def test_coupling_off_is_inference_only_and_keeps_original_marginal():
    import torch
    import p17_b as pb
    rs = _b_roots()
    torch.manual_seed(0)
    m = pb.model("LB+G").eval()
    with torch.no_grad():
        for p in m.cpl.parameters():
            p.add_(torch.randn_like(p))                                # make the generic term clearly non-zero
    sd = {k: v.clone() for k, v in m.state_dict().items()}
    on = pb.score(m, "LB+G", rs)
    with pb.coupling_off(m):
        off = pb.score(m, "LB+G", rs)
    assert all(torch.equal(sd[k], v) for k, v in m.state_dict().items())
    diff_rep = 0.0
    for k in on:
        e_on, e_off = [x for x in on[k] if x["m"] == 0], [x for x in off[k] if x["m"] == 0]
        assert abs(e_on[0]["p"] - e_off[0]["p"]) < 1e-12                # P(z0) invariant: no scene-pair term in LB+G
        diff_rep = max(diff_rep, max(abs(a["p"] - b["p"]) for a, b in zip(on[k], off[k]) if a["m"] > 0))
    assert diff_rep > 1e-6                                              # repair marginals do change


def test_layout_long_sequences_repeats_and_order():
    import pytest
    import p17_b as pb
    lay = pb.layout("k", [("a", 1), ("b", 2), ("a", 3), ("c", 4)], [])
    assert lay["query"]["zR"] == "seq:k:a>1.b>2.a>3.c>4" and lay["active_count"] <= pb.MAX_ACTIVE
    with pytest.raises(ValueError):
        pb.layout("k", [("a", 1), ("a", 2)], [])
    rev = pb.layout("k", [("b", 2), ("a", 1)], [])
    assert rev["query"]["zR"] != pb.layout("k", [("a", 1), ("b", 2)], [])["query"]["zR"]
    assert pb.layout("k", [("a", 1)], [])["query"]["zR"] != pb.layout("k", [("a", 2)], [])["query"]["zR"]
    om = pb.layout("k", [("a", 1), ("b", 2), ("a", 3)], [])                # omitting b would make a consecutive repeat: inactive
    assert om["active"][om["slots"].index("zO[1]")] is False


def test_early_stopping_training_finite_gradients():
    import p17_b as pb
    rs = _b_roots(4)
    m, rec = pb.fit("LB", 0, rs[:3], rs[3:], updates=40, patience_evals=1)
    assert not rec["nonfinite"] and rec["best_update"] > 0 and rec["updates_run"] <= 40
    assert all(np.isfinite(h["grad_pre"]) for h in rec["history"] if "grad_pre" in h)


# ------------------------------------------------------------------ D: label protocol versions, per-family calibration
def test_platt_forms_finite_and_identity_when_calibrated():
    import p17_d as pd
    a, b = pd._fit_tb([5.0, 6.0, -5.0, -6.0], [1, 1, 0, 0], "full")              # separable: prior keeps it finite
    assert np.isfinite(a) and np.isfinite(b) and abs(a) < 50
    rng = np.random.default_rng(0)
    z = rng.normal(0, 2, 4000)
    y = (rng.random(4000) < 1 / (1 + np.exp(-z))).astype(int)
    pr = [{"root": f"r{i % 40}", "logit_raw": float(zz), "y": int(yy)} for i, (zz, yy) in enumerate(zip(z, y))]
    c = pd.fit_calibration("X", pr)
    assert abs(c["slope"] - 1) < 0.2 and abs(c["bias"]) < 0.2


def test_guide_uses_only_its_own_family_calibration(tmp_path, monkeypatch):
    import json
    import pytest
    import p17_d as pd
    _, task, ph, _ = _dev_phys()
    monkeypatch.setattr(pd, "OUT", tmp_path)
    (tmp_path / "calibration").mkdir()
    with pytest.raises(SystemExit):
        pd.Guide("Dp16", task, ph, ["o00"])
    (tmp_path / "calibration" / "Dp.json").write_text(json.dumps({"slope": 9.0, "bias": 9.0}))
    with pytest.raises(SystemExit):
        pd.Guide("Dp16", task, ph, ["o00"])                                     # another family's file is never used
    (tmp_path / "calibration" / "Dp16.json").write_text(json.dumps({"slope": 2.0, "bias": -1.0}))
    assert pd.Guide("Dp16", task, ph, ["o00"]).cal == {"slope": 2.0, "bias": -1.0}
    assert pd.Guide("Dp16-norec", task, ph, ["o00"]).recursion is False


def test_multi_destination_semantics_existential_and_unknown():
    import d_blockers as db
    import p15_search as ps_
    import p17_d as pd

    class P:
        s0 = type("S", (), {"objects": [type("O", (), {"id": i, "cell": c})() for i, c in (("a", 1), ("b", 2), ("t0", 9))],
                            "robot": type("R", (), {"q_rad": (0.0,)})()})()

        def goal(self, cells, q):
            return ({(1, 2): ps_.CI, (5, 2): ps_.CI, (6, 2): ps_.V, (1, 7): ps_.U_PLAN, (1, 8): ps_.CI}.get((cells["a"], cells["b"]), ps_.CI), None, 0)
    r = pd.multi_dest_lattice(P(), ["a", "b"], lambda c, o: {"a": [5, 6], "b": [7, 8]}[o], k=2)
    assert r["statuses"][("a",)] == db.V                                        # one admissible assignment verifies -> sufficient
    assert r["statuses"][()] == db.C
    assert r["statuses"][("b",)] is None                                        # one assignment UNKNOWN -> not negative


# ------------------------------------------------------------------ custody / leakage / resumption
def test_split_custody_calibration_disjoint_and_prereg_required(tmp_path, monkeypatch):
    import pytest
    import p17_data as pe
    import p17_prosp as pp
    assert not set(pe.CAL_FIT + pe.CAL_EVAL) & set(pe.D_TRAIN_SPLITS)
    assert "p17calib" not in pe.TRAIN_SPLITS and not any(s.startswith("p17test") for s in pe.TRAIN_SPLITS + pe.VAL_SPLITS + pe.CAL_FIT + pe.CAL_EVAL)
    monkeypatch.setattr(pp, "OUT", tmp_path)
    with pytest.raises(SystemExit):
        pp.p_queue("w0", "b")
    lk, ex = pe.rd(pe.DATA / "LEAKAGE.json"), pe.rd(pe.DATA / "EXCLUDED.json")
    excl = {k for kk, v in ex.items() if kk != "reason" for k in v}
    assert not lk["index_overlap"]
    for pair in lk["duplicates"].values():                                     # every fingerprint duplicate has an excluded member
        assert any(k in excl for _, k in pair) and not any("p17test" in d for d, _ in pair)


def test_labelling_resumes_from_checkpoint(tmp_path, monkeypatch):
    import config as cf
    import p17_b as pb
    import p17_data as pe
    monkeypatch.setattr(pe, "DATA", tmp_path)
    (tmp_path / "dev").mkdir()
    cf.write_json(tmp_path / "dev" / "labels_w9.json", {"p13_2026210000": {"done": True}})
    monkeypatch.setattr(pe, "_plan", lambda s: {"roots": {"p13_2026210000": {}}})
    monkeypatch.setattr(pb, "catalogue", lambda *a, **k: (_ for _ in ()).throw(AssertionError("recomputed")))
    pe.label_roots("dev", ["p13_2026210000"], "w0")


def test_empty_sequence_q_dependent_certificate_is_sound_at_q0():
    t = _phys(Toy({((("A", 1), ("B", 2), ("t0", 9)), 0.0): (ps.CI, 0.0)}, {}, cert=("LINK0_SECTOR_PICK",)))
    assert pv.verify_existential(t, [])["status"] == pv.CI                     # q0 is the only realization of the empty sequence
    t2 = _phys(Toy({((("A", 5), ("B", 2), ("t0", 9)), 1.0): (ps.CI, 0.0)}, {("A", 5, 0.0): [(ps.V, 1.0, 1.0)]}, cert=("LINK0_SECTOR_PICK",)))
    assert pv.verify_existential(t2, [("A", 5)])["status"].startswith("UNKNOWN")  # after a move: only that branch is refuted
