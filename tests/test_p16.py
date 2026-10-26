"""P16: scene-only task interface (no teacher dependency), expanded-domain search (repeat moves, dominance, claims), sequence
verification semantics, deterministic-record hashing, lean-B exact factorized likelihood and D label semantics."""
import json
import os
from pathlib import Path

import numpy as np

os.environ.setdefault("P10C_OUT", "runs/p13/models")

import p15_search as ps  # noqa: E402
import p16_common as pc  # noqa: E402


class Toy:
    """goal: {(cells items, q): (status, travel)}; edge: {(o, d, q): [(status, q2, travel)]}; missing -> UNKNOWN_PLANNER."""

    def __init__(self, goal, edge):
        self.g, self.e = goal, edge

    def truncated(self):
        return False

    def goal(self, cells, q):
        st, t = self.g.get((tuple(sorted(cells.items())), float(q[0])), (ps.U_PLAN, 0.0))
        return st, {"q": np.zeros((2, 3)), "gap": np.zeros(2)}, t

    def edges(self, cells, q, o, d):
        out = self.e.get((o, d, float(q[0])), [(ps.U_PLAN, None, 0.0)])
        return [(st, [{"q": np.zeros((2, 3)), "gap": np.zeros(2)}], None if q2 is None else np.array([q2]), t, {"via": "toy"}) for st, q2, t in out]


def _roots():
    return json.loads(Path("runs/p15/prospective/plan.json").read_text())["roots"]


def test_task_is_scene_only_and_ignores_catalogue():
    r = next(iter(_roots().values()))
    a = pc.task_from_root(r, "k")
    b = pc.task_from_root({k: v for k, v in r.items() if k not in ("items", "parking", "dest", "role_cells", "predicates", "ids")}, "k")
    assert a == b and set(a) == {"scene", "goal_cell", "fixed_ids", "target", "key"}


def test_movers_exclude_target_and_fixed_structures():
    for r in list(_roots().values())[:12]:
        t = pc.task_from_root(r, "k")
        cells = {o["id"]: o["cell"] for o in r["scene"]["objects"]}
        kept, omitted = pc.propose_movers(t, cells)
        assert "t0" not in kept + omitted and not set(kept + omitted) & set(t["fixed_ids"])
        assert len(kept) <= pc.MOVER_CAP


def _run(toy, movers=("A", "B"), slots=(5, 6), per_obj=1, n_max=3, order=None):
    sl = lambda c, o: [s for s in slots if s not in c.values()]  # noqa: E731
    return pc.search(toy, order or (lambda c, q, m, cand: cand), list(movers), sl, {"A": 1, "B": 2, "t0": 9}, np.array([0.0]), n_max, per_obj)


def test_repeat_move_found_only_in_expanded_domain():
    # A must leave cell 1 (to 5) so B can go 2 -> 1? no: B -> 6 needs A away; then the target needs A back off 5 to 1.
    g = {((("A", 1), ("B", 6), ("t0", 9)), 3.0): (ps.V, 1.0)}
    e = {("A", 5, 0.0): [(ps.V, 1.0, 1.0)], ("B", 6, 1.0): [(ps.V, 2.0, 1.0)], ("A", 1, 2.0): [(ps.V, 3.0, 1.0)]}
    assert not _run(Toy(g, e), slots=(5, 6, 1), per_obj=1)["found"]
    r = _run(Toy(g, e), slots=(5, 6, 1), per_obj=2)
    assert r["found"] and [s["object"] for s in r["plan"]["steps"]] == ["A", "B", "A"] and abs(r["plan"]["travel"] - 4.0) < 1e-12


def test_no_consecutive_repeat_of_same_object():
    seen = []
    _run(Toy({}, {("A", 5, 0.0): [(ps.V, 1.0, 1.0)]}), per_obj=2, n_max=2, order=lambda c, q, m, cand: seen.append((dict(c), cand)) or cand)
    after_a = [cand for c, cand in seen if c["A"] == 5]
    assert after_a and all(o != "A" for o, _ in after_a[0])


def test_unknown_blocks_min_moves_claim_in_expanded_search():
    g = {((("A", 5), ("B", 6), ("t0", 9)), 2.0): (ps.V, 1.0)}
    e = {("A", 5, 0.0): [(ps.V, 1.0, 1.0)], ("B", 6, 1.0): [(ps.V, 2.0, 1.0)]}
    r = _run(Toy(g, e))
    assert r["found"] and not r["min_moves_proven"] and r["claim"] == "BEST_VERIFIED_WITHIN_BUDGET"


def test_node_cap_marks_incomplete():
    r = pc.search(Toy({}, {}), lambda c, q, m, cand: cand, ["A", "B"], lambda c, o: [5, 6], {"A": 1, "B": 2, "t0": 9}, np.array([0.0]), 3, 1, node_cap=2)
    assert r["log"]["node_cap_hit"] and not r["flags"][max(r["flags"])]["search_enumeration_complete"]


class SeqPhys:
    def __init__(self, toy):
        self.t = toy
        self.s0 = type("S", (), {"objects": [type("O", (), {"id": i, "cell": c})() for i, c in (("A", 1), ("B", 2), ("t0", 9))],
                                 "robot": type("R", (), {"q_rad": (0.0,)})()})()

    def edges(self, cells, q, o, d):
        return self.t.edges(cells, q, o, d)

    def goal(self, cells, q):
        return self.t.goal(cells, q)


def test_verify_sequence_uses_cheapest_mode_and_reports_first_failure():
    g = {((("A", 5), ("B", 2), ("t0", 9)), 2.0): (ps.V, 0.5)}
    e = {("A", 5, 0.0): [(ps.V, 1.0, 3.0), (ps.V, 2.0, 1.0)]}
    r = pc.verify_sequence(SeqPhys(Toy(g, e)), [("A", 5)])
    assert r["status"] == ps.V and abs(r["plan"]["travel"] - 1.5) < 1e-12
    r = pc.verify_sequence(SeqPhys(Toy(g, e)), [("B", 6)])
    assert r["status"] == ps.U_PLAN and r["failed_step"] == 0 and r["plan"] is None


def test_traj_hash_deterministic_and_sensitive():
    import p16_motion as pm
    a = {"q": np.array([[0.0, 1.0, 2.0], [0.1, 1.0, 2.0]]), "gap": np.array([0.02, 0.02])}
    b = {"q": a["q"] + 1e-6, "gap": a["gap"]}
    assert pm.traj_hash([a]) == pm.traj_hash([dict(a)]) and pm.traj_hash([a]) != pm.traj_hash([b])
    t = pm.transit_record([[0, 0, 0], [0.1, 0, 0], [0.2, 0, 0]], 0.02)
    assert len(t["phase"]) == 2 and not t["held_local"].size and not any(t["attached"])


def test_historical_manifest_unchanged():
    import p16_eval as pe
    if (pe.OUT / "audit" / "HISTORICAL_MANIFEST.json").exists():
        assert pe.verify_historical() == []


class _Fake:
    def __init__(self, cache, budget):
        self.memo, self.cache, self.tag, self.budget = {}, cache, ("t",), dict(budget)
        self.used, self.stats, self.vcpu, self.pcpu, self.edge_log = {k: 0 for k in budget}, {"cache_hits": 0, "x": 0}, 0.0, 0.0, []

    def truncated(self):
        return False


def test_shared_cache_exact_virtual_accounting():
    import p16_motion as pm
    calls = []

    def fn(phys):
        def run():
            calls.append(1)
            phys.used["motion_checks"] += 3
            phys.stats["x"] += 2
            return [(pm.V, None, None, 1.0, {})]
        return run
    cache = {}
    a = _Fake(cache, {"motion_checks": 10})
    pm.DetPhysics._cached(a, ("edge", 1, "o", 5), fn(a))
    b = _Fake(cache, {"motion_checks": 10})
    r = pm.DetPhysics._cached(b, ("edge", 1, "o", 5), fn(b))
    assert len(calls) == 1 and b.used["motion_checks"] == 3 and b.stats["x"] == 2 and b.stats["cache_hits"] == 1 and r[0][0] == pm.V
    c = _Fake(cache, {"motion_checks": 2})                       # cannot afford the recorded consumption -> recompute with own budget
    pm.DetPhysics._cached(c, ("edge", 1, "o", 5), fn(c))
    assert len(calls) == 2 and c.stats["cache_hits"] == 0


def _lean_root():
    import torch
    import p16_b as pb
    import p16_eval as pe
    labs = pe.merged("dev", "labels")
    if not labs:
        return None, None
    k = sorted(labs)[0]
    plan = json.loads((pe.DATA / "dev" / "plan.json").read_text())
    r = pb.prepare(pb.records(plan, {k: labs[k]}, "train"))[0]
    torch.manual_seed(0)
    return pb.model("LB"), r


def test_lean_b_is_exactly_factorized_and_matches_brute_force():
    import unique_factor as uf
    import unique_factor_keyed as ufk
    import joint_likelihood as jl
    m, r = _lean_root()
    if m is None:
        return
    with ufk.installed():
        inst = uf.instances(m, r)
        lab = jl.labels(r)
        ll, n = uf.log_evidence(inst, lab)
        pm = uf.prior_marginals(inst)
        closed = sum(np.log(pm[q] if y else 1 - pm[q]) for q, y in lab.items() if y is not None)
        assert all(float(b["energy"].abs().max()) == 0.0 for b in inst["blocks"].values())
        assert abs(float(ll) - uf.brute_force(inst, lab)) < 1e-9 and abs(float(ll) - closed) < 1e-9 and n == sum(y is not None for y in lab.values())


def test_lean_b_unknown_labels_are_marginalized_not_negative():
    import unique_factor as uf
    import unique_factor_keyed as ufk
    import joint_likelihood as jl
    m, r = _lean_root()
    if m is None:
        return
    with ufk.installed():
        inst = uf.instances(m, r)
        lab = jl.labels(r)
        unk = [q for q, y in lab.items() if y is None]
        if not unk:
            return
        assert abs(float(uf.log_evidence(inst, lab)[0]) - float(uf.log_evidence(inst, {q: y for q, y in lab.items() if y is not None})[0])) < 1e-12
        assert abs(float(uf.log_evidence(inst, {**lab, unk[0]: 0})[0]) - float(uf.log_evidence(inst, lab)[0])) > 1e-9


def test_lean_b_order_sensitive_and_no_op_distinct_from_abstain():
    import torch
    import p16_b as pb
    m, r = _lean_root()
    if m is None:
        return
    two = next(c for c in r["cands"] if len(c["seq"]) == 2)
    m._memo = {}
    with torch.no_grad():
        a = float(m.order(r["R"], two["seq"])[0])
        m._memo = {}
        b = float(m.order(r["R"], list(reversed(two["seq"])))[0])
    m._memo = None
    assert abs(a - b) > 1e-9                                         # F2 order-sensitive repair unary
    rows = [{"query": "e", "m": 0, "u": 3.0}, {"query": "r", "m": 1, "u": 3.0}]
    assert pb.choose(rows, 0.5, 0.5) == "e" and pb.choose([dict(rows[0], u=-3.0), dict(rows[1], u=-3.0)], 0.5, 0.5) == "ABSTAIN"
    assert pb.choose([dict(rows[0], u=-3.0), rows[1]], 0.5, 0.5) == "r"


def test_keyed_identity_rejects_one_query_two_sequences():
    import pytest
    import joint_likelihood as jl
    import unique_factor_keyed as ufk
    m, r = _lean_root()
    if m is None:
        return
    r = dict(r, cands=[dict(c) for c in r["cands"]])
    one = next(i for i, c in enumerate(r["cands"]) if len(c["seq"]) == 1)
    two = next(i for i, c in enumerate(r["cands"]) if len(c["seq"]) == 1 and i != one)
    r["cands"][two] = dict(r["cands"][two], z_q=[r["cands"][one]["query"] if s == "zR" else q for s, q in zip(r["cands"][two]["slots"], r["cands"][two]["z_q"])])
    with pytest.raises(jl.IdentityError):
        ufk.instances(m, r)


def _lab(y0, edits):
    return {"original": {"y": y0}, "edits": {k: {"y": v} for k, v in edits.items()}}


def test_d_union_vs_necessary_alternative_clearing_sets():
    import p16_d as pd
    d = pd.lattice(_lab(0, {"a": 1, "b": 1, "a+b": 1}), ["a", "b"])           # A or B suffices
    assert d["type"] == "MINIMAL_SETS" and d["mask"] == [1, 1] and d["necessary"] == [0, 0]
    d = pd.lattice(_lab(0, {"a": 0, "b": 0, "a+b": 1}), ["a", "b"])           # complementary: both needed
    assert d["mask"] == [1, 1] and d["necessary"] == [1, 1]


def test_d_no_clearing_set_and_incomplete_lattice_get_no_blocker_term():
    import p16_d as pd
    d = pd.lattice(_lab(0, {"a": 0, "b": 0, "a+b": 0}), ["a", "b"])
    assert d["type"] == "NO_CLEARING_SET_WITHIN_POOL" and pd.item("R", {**d, "pool": [0, 1]}) == ("R", [], 0, None)
    d = pd.lattice(_lab(0, {"a": None, "b": 0, "a+b": 1}), ["a", "b"])
    assert d["type"] == "INCOMPLETE" and pd.item("R", {**d, "pool": [0, 1]})[3] is None
    d = pd.lattice(_lab(1, {"a": 1, "b": 1, "a+b": 1}), ["a", "b"])
    assert d["type"] == "FEASIBLE_ORIGINAL" and pd.item("R", {**d, "pool": [0, 1]}) == ("R", [], 1, None)
    assert pd.lattice(_lab(None, {}), ["a"])["y0"] is None and pd.item("R", {"y0": None}) is None


def test_d_pairless_conditional_vs_gated_marginals():
    import torch
    import d_blockers as db
    a, w = torch.tensor([0.3, -1.2], dtype=torch.float64), torch.zeros(2, 2, dtype=torch.float64)
    lp = db.blocker_logp(a, w)
    m = (lp.exp()[:, None] * db.states(2)).sum(0)
    assert torch.allclose(m, torch.sigmoid(a)) and abs(float(lp.exp().sum()) - 1) < 1e-12   # pairless = independent Bernoullis
    w2 = torch.tensor([[0.0, 2.0], [2.0, 0.0]], dtype=torch.float64)
    m2 = (db.blocker_logp(a, w2).exp()[:, None] * db.states(2)).sum(0)
    assert not torch.allclose(m2, torch.sigmoid(a))                                           # paired term couples them
