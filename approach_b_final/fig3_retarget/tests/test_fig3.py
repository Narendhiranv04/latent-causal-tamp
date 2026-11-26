"""R1 synthetic contract tests (no model, no teacher: a declared fake scorer with an explicit blocker graph; SYNTHETIC, never a success claim).
Fig. 3(a) literal example: seed [B, C, A]; retarget B -> [E, D]; C -> [G]; A -> [F]; compose [E, D, B, G, C, F, A] with edges
E->D->B, G->C, F->A, B->C->A (plan §3.4).  The nested variant makes D a prerequisite of B and E a prerequisite of D (enabler of enabler)."""
from __future__ import annotations

import ast, itertools, json, math, random, sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE.parent.parent))
import rank as RK  # noqa: E402
import recursive as RC  # noqa: E402
import views as V  # noqa: E402
from models import CapReached  # noqa: E402

NAMES = ["A", "B", "C", "D", "E", "F", "G", "T"]
I = {n: i for i, n in enumerate(NAMES)}
RULE = {"noop_gate": 0.5, "eta": 0.3}
LITERAL = {"T": [["B", "C", "A"]], "B": [["E", "D"]], "C": [["G"]], "A": [["F"]]}
NESTED = {"T": [["B", "C", "A"]], "B": [["D"]], "D": [["E"]], "C": [["G"]], "A": [["F"]]}
WANT = ["E", "D", "B", "G", "C", "F", "A"]


def row(dom="3d", fixed=()):
    n = len(NAMES)
    cells0 = list(range(n))
    xy = {str(c): [0.075 * (c % 8), 0.075 * (c // 8)] for c in range(40)}
    if dom == "3d":
        attrs = [[1.0, 0.0, 0.05, 0.1, float(i == I["T"])] for i in range(n)]
        ctx = [0.0] * 14 + xy["30"] + [0.05, 0.1, 1.0]
        qref = [0.0] * 7
    else:
        attrs = [[0.024, float(i == I["T"]), float(i != I["T"]), float(NAMES[i] in fixed)] for i in range(n)]
        ctx = [0.0] * 6 + xy["30"] + [0.07]
        qref = [0.0] * 3
    inp = {"ids": NAMES, "tid": I["T"], "cells0": cells0, "xy0": [xy[str(c)] for c in cells0], "attrs": attrs, "ctx": ctx, "goal": xy["30"],
           "goal_cell": 30, "legal_cells": list(range(36)), "cell_xy": xy, "q_ref": qref, "base": [0.0, 0.0], "grid": [8, 5]}
    return {"root_id": f"synthetic-{dom}", "domain": dom, "inputs": inp}


class Fake:
    """Declared synthetic scorer.  Object o has one proposal (cell 10 + o).  For task X (tid of the view) the required ordered enabler group is
    G[X]; temporary no-op Y is high iff all of X's prerequisites are already moved; local p11 high iff the group is exactly a required group
    in order.  pX of an action is high iff its prerequisites are moved before it; Y_global high iff every dependency is respected."""

    def __init__(self, graph, caps=None):
        self.G, self.caps, self.man = graph, caps or {}, {"config": {"rule": RULE}}
        self.reset()

    def reset(self):
        self.c = {"proposal_calls": 0, "latent_draws": 0, "x_unique": 0, "y_unique": 0, "batches": 0, "cache_hits": 0}
        self._seen = set()

    def _moved(self, r):
        return {NAMES[i] for i, c in enumerate(r["inputs"]["cells0"]) if c != i}

    def _need(self, X):
        return {o for g in self.G.get(X, []) for o in g}

    def proposals(self, r, objs, m=4):
        self.c["proposal_calls"] += 1
        return {int(o): [10 + int(o)] for o in objs}

    def p_noop(self, r):
        X = NAMES[r["inputs"]["tid"]]
        return 0.95 if self._need(X) <= self._moved(r) else 0.2

    def _px(self, moved, seq):
        ok, mv = True, set(moved)
        for o, _ in seq:
            n = NAMES[int(o)]
            ok &= self._need(n) <= mv
            mv.add(n)
        return 0.9 if ok else 0.05

    def score(self, r, seqs):
        out = []
        X = NAMES[r["inputs"]["tid"]]
        moved = self._moved(r)
        for s in seqs:
            k = (V.skey(r), json.dumps(s))
            if k not in self._seen and s:
                if self.caps.get("x_unique") is not None and self.c["x_unique"] >= self.caps["x_unique"]:
                    raise CapReached("x_unique")
                self._seen.add(k); self.c["x_unique"] += 1
            names = [NAMES[int(o)] for o, _ in s]
            exact = any(names == g for g in self.G.get(X, [])) or (not self._need(X) - moved and not s)
            px = self._px(moved, s)
            py = 0.9 if exact else 0.01                                          # declared: the seed itself looks right to Y but not to X
            out.append({"p11": py * px, "py": py, "px": px, "px1": px, "px0": px})
        return out

    def y_global(self, r0, endpoints):
        return [0.9 if self._need("T") <= {NAMES[int(o)] for o, _ in e} else 0.05 for e in endpoints]


def names(seq):
    return [NAMES[int(o)] for o, _ in seq]


def act(n):
    return [I[n], 10 + I[n]]


@pytest.mark.parametrize("graph", [LITERAL, NESTED], ids=["literal", "nested"])
def test_fig3_seven_action_composition(graph):
    fz = Fake(graph)
    p = RC.plan(fz, row(), RULE, "R-FIG3", {"m_max": 7})
    assert p["decision"] == "REPAIR" and names(p["seq"]) == WANT
    E = {(x[0], y[0], k) for x, y, k in p["edges"]}
    for a, b in [("B", "C"), ("C", "A")]:
        assert (a, b, "SEED") in E
    for a, b in [("G", "C"), ("F", "A")]:
        assert (a, b, "PREREQ") in E
    if graph is LITERAL:
        assert {("E", "B", "PREREQ"), ("D", "B", "PREREQ"), ("E", "D", "LOCAL")} <= E
    else:
        assert {("D", "B", "PREREQ"), ("E", "D", "PREREQ")} <= E and p["counters"]["max_depth"] >= 2
    assert RC.valid_dag(row(), p["seq"], [(tuple(x), tuple(y), k) for x, y, k in p["edges"]])
    assert len({o for o, _ in p["seq"]}) == len(p["seq"]) and len({d for _, d in p["seq"]}) == len(p["seq"])


def _tree_actions(node, acc):
    for ch in node.get("children", []):
        if "action" in ch:
            acc.append((ch["action"][0], ch.get("y_temp")))
        _tree_actions(ch, acc)
        for r in ch.get("repairs", []):
            _tree_actions(r, acc)
    return acc


def test_every_action_retargeted_including_high_py():
    fz = Fake(LITERAL)
    p = RC.plan(fz, row(), RULE, "R-FIG3", {"m_max": 7})
    seen = _tree_actions(p["tree"], [])
    got = {a for a, _ in seen}
    assert set(WANT) <= got                                                         # every seed action AND every new enabler retargeted
    assert any(a in ("E", "G", "F") and y is not None and y > 0.9 for a, y in seen)  # high temporary feasibility still retargeted


def _nodes(node, acc):
    for ch in node.get("children", []):
        if "action" in ch:
            acc.append(ch)
        _nodes(ch, acc)
        for r in ch.get("repairs", []):
            _nodes(r, acc)
    return acc


def test_gated_arm_only_expands_low_py():
    fz = Fake(LITERAL)
    p = RC.plan(fz, row(), RULE, "R-GATED", {"m_max": 7})
    ns = _nodes(p["tree"], [])
    assert any(n.get("why") == "gated" for n in ns)
    assert all(n["y_temp"] >= 0.5 for n in ns if n.get("why") == "gated")                  # legacy gate: only pY >= 0.5 (or 0.9) is skipped
    assert all(n.get("why") != "gated" for n in ns if n["y_temp"] is not None and n["y_temp"] < 0.5)
    assert names(p["seq"]) == WANT                                                  # low-py seed actions still repaired


def test_recursion_admits_by_temporary_y_not_enabler_x():
    fz = Fake(NESTED)
    ctx = RC.Ctx(fz, row(), "R-FIG3", {"m_max": 7})
    vs = RC.place(ctx, [], set(), act("B"), [], 1, [], {"children": []})
    assert any(names(v[0]) == ["E", "D", "B"] for v in vs)                          # D is X-blocked by E, admitted for B, then repaired


def test_cap_infeasible_never_drops_seed_actions():
    fz = Fake(LITERAL)
    p = RC.plan(fz, row(), RULE, "R-FIG3", {"m_max": 5})
    assert p["m_max"] == 5
    if p["seq"] is not None:
        s = names(p["seq"])
        assert len(s) <= 5
        seeds = [x for x in s if x in ("B", "C", "A")]
        assert seeds == [x for x in ["B", "C", "A"] if x in s]                    # seed order kept
        assert WANT != s


def test_empty_sibling_kept_and_cycle_guard():
    fz = Fake(LITERAL)
    ctx = RC.Ctx(fz, row(), "R-FIG3", {"m_max": 7})
    node = {"children": []}
    vs = RC.place(ctx, [], set(), act("B"), [act("C"), act("A")], 1, [], node)
    assert names(vs[0][0]) == ["B"]                                                 # empty (no-insertion) sibling first
    assert any(names(v[0]) == ["E", "D", "B"] for v in vs)
    assert RC.place(ctx, [], set(), act("B"), [], 2, [act("B")], {"children": []}) == [] and ctx.n["cycle_rejects"] == 1


def test_protected_and_pending_never_in_repairs():
    fz = Fake({"T": [["B"]], "B": [["C"]]})
    ctx = RC.Ctx(fz, row(), "R-FIG3", {"m_max": 6})
    T = V.rebase(row(), [], task=act("B"), reserved=[10 + I["C"]])
    gs = RC.local_groups(ctx, T, [], [I["B"]], [act("C")], 3, task_dest=10 + I["B"])
    assert gs and all(I["B"] not in [o for o, _ in g] and I["C"] not in [o for o, _ in g] and I["T"] not in [o for o, _ in g] for g in gs)


def test_masks_and_grammar():
    r = row("2d", fixed=("G",))
    S = V.rebase(r, [act("A")], reserved=[17])
    L = set(S["inputs"]["legal_cells"])
    assert not L & set(range(8)) and 30 not in L and 17 not in L and L <= set(r["inputs"]["legal_cells"])
    assert I["G"] not in V.eligible(r) and I["T"] not in V.eligible(r)
    assert V.eligible(r, used=[I["A"]], pending=[I["B"]], protect=[I["C"]]) == [I["D"], I["E"], I["F"]]
    assert V.legal_seq(r, [act("A"), act("B")], 6)
    assert not V.legal_seq(r, [act("A"), [I["A"], 20]], 6)                         # no double move
    assert not V.legal_seq(r, [act("A"), [I["B"], 10 + I["A"]]], 6)                 # no destination reuse
    assert not V.legal_seq(r, [[I["A"], 30]], 6) and not V.legal_seq(r, [[I["A"], 3]], 6)   # goal / originally occupied
    assert not V.legal_seq(r, [[I["T"], 20]], 6) and not V.legal_seq(r, [[I["G"], 20]], 6)  # target / fixed
    assert not V.legal_seq(r, [act(n) for n in "ABCDEF"], 5)                       # cap


@pytest.mark.parametrize("dom", ["2d", "3d"])
def test_retarget_fields(dom):
    r = row(dom)
    orig = json.dumps(r, sort_keys=True)
    T = V.rebase(r, [act("E")], task=act("B"))
    inp = T["inputs"]
    assert json.dumps(r, sort_keys=True) == orig                                    # deep copy
    assert inp["tid"] == I["B"] and inp["goal_cell"] == 10 + I["B"] and inp["goal"] == r["inputs"]["cell_xy"][str(10 + I["B"])]
    assert inp["cells0"][I["E"]] == 10 + I["E"] and inp["xy0"][I["E"]] == r["inputs"]["cell_xy"][str(10 + I["E"])]
    n = 2 * len(inp["q_ref"])
    assert inp["ctx"][n:n + 2] == inp["goal"]
    if dom == "2d":
        assert inp["attrs"][I["B"]][1:3] == [1.0, 0.0] and inp["attrs"][I["T"]][1:3] == [0.0, 1.0]
        assert sum(a[1] for a in inp["attrs"]) == 1.0 and all(a[0] == 0.024 for a in inp["attrs"])
    else:
        assert [a[4] for a in inp["attrs"]] == [float(i == I["B"]) for i in range(len(NAMES))]
        a = inp["attrs"][I["B"]]
        assert inp["ctx"][n + 2:n + 5] == [a[2], a[3], a[0]]


def test_cache_identity_and_counted_temp_readouts():
    r = row()
    k = {V.skey(V.rebase(r, [], task=act("B"))), V.skey(V.rebase(r, [], task=act("C"))), V.skey(V.rebase(r, [], task=act("B"), reserved=[20])),
         V.skey(V.rebase(r, [act("E")], task=act("B"))), V.skey(r)}
    assert len(k) == 5
    fz = Fake(LITERAL)
    ctx = RC.Ctx(fz, r, "R-FIG3", {"m_max": 7})
    T = V.rebase(r, [], task=act("B"))
    ctx.ytemp(T); ctx.ytemp(V.rebase(r, [], task=act("B")))
    assert ctx.n["temp_readouts"] == 1


def test_hard_caps_and_deadline():
    fz = Fake(LITERAL)
    p = RC.plan(fz, row(), RULE, "R-FIG3", {"m_max": 7, "temp_readouts": 2})
    assert p["counters"]["cap_hits"].get("temp_readouts", 0) >= 1 and p["counters"]["temp_readouts"] == 2
    p = RC.plan(Fake(LITERAL), row(), RULE, "R-FIG3", {"m_max": 7, "wall_s": 0.0})
    assert p["cap_stop"] and "TimeoutError" in p["cap_stop"] and p["decision"] in ("ABSTAIN", "REPAIR", "NOOP")
    p = RC.plan(Fake(LITERAL), row(), RULE, "R-FIG3", {"m_max": 7, "x_unique": 3})
    assert p["cap_stop"] and "CapReached" in p["cap_stop"]


def test_flat_arm_has_no_retargeting():
    p = RC.plan(Fake(LITERAL), row(), RULE, "F-FLAT", {"m_max": 7})
    assert p["counters"]["retargeted_actions"] == 0 and p["counters"]["temp_readouts"] == 0
    assert all(k == "FLAT_BEFORE" for _, _, k in (p["edges"] or []))


def test_topo_arm_keeps_prereq_and_local():
    r = row()
    E = {(V.key(r, act("E")), V.key(r, act("D")), "LOCAL"), (V.key(r, act("D")), V.key(r, act("B")), "PREREQ"),
         (V.key(r, act("B")), V.key(r, act("C")), "SEED"), (V.key(r, act("G")), V.key(r, act("C")), "PREREQ")}
    seq = [act(n) for n in ["E", "D", "B", "G", "C"]]
    orders = RC.topo_orders(r, seq, E, limit=200)
    assert orders[0] == seq
    for o in orders:
        pos = {names([a])[0]: i for i, a in enumerate(o)}
        assert pos["E"] < pos["D"] < pos["B"] and pos["G"] < pos["C"]
    assert any(names(o).index("C") < names(o).index("B") for o in orders)          # SEED edge relaxed


@pytest.mark.parametrize("m", [1, 2, 3, 4, 5, 6])
def test_partitions_count(m):
    assert len(V.partitions(m)) == [1, 2, 4, 7, 13, 24][m - 1]
    assert all(sum(p) == m and max(p) <= 3 for p in V.partitions(m))


class RandScore(Fake):
    def __init__(self, seed):
        super().__init__({})
        self.rng = random.Random(seed); self.t = {}

    def _r(self, k):
        if k not in self.t:
            self.t[k] = self.rng.uniform(0.05, 0.99)
        return self.t[k]

    def score(self, r, seqs):
        out = []
        for s in seqs:
            py, p1, p0 = self._r(("py", V.skey(r), json.dumps(s))), self._r(("p1", V.skey(r), json.dumps(s))), self._r(("p0", V.skey(r), json.dumps(s)))
            out.append({"p11": py * p1, "py": py, "px": py * p1 + (1 - py) * p0, "px1": p1, "px0": p0})
        return out

    def y_global(self, r0, endpoints):
        return [self._r(("yg", json.dumps(sorted(map(list, e))))) for e in endpoints]


@pytest.mark.parametrize("m", [1, 2, 3, 4, 5, 6])
@pytest.mark.parametrize("seed", range(5))
def test_dp_equals_bruteforce_and_mode_consistency(m, seed):
    fz = RandScore(seed)
    r = row()
    seq = [act(n) for n in "ABCDEF"[:m]]
    E, part, px, yf = RK.best_partition(fz, r, seq)
    Eb, _, pb = RK.brute_partition(fz, r, seq)
    assert part == pb and abs(E - Eb) < 1e-12
    if part == (m,) and m <= 3:                                                    # single chunk: exact p11, nothing else multiplied
        assert px == [] and abs(E - (-math.log(fz.score(r, [seq])[0]["p11"]))) < 1e-12
    else:                                                                          # executed partition == scored partition
        assert len(px) == len(part) and abs(E - (-sum(math.log(x) for x in px) - math.log(yf))) < 1e-9
    for x in fz.score(r, [seq]):
        assert abs(x["p11"] - x["py"] * x["px1"]) < 1e-12 and abs(x["px"] - (x["py"] * x["px1"] + (1 - x["py"]) * x["px0"])) < 1e-12


def test_no_privileged_imports_in_inference():
    banned = {"evaluate_k45", "physical2d", "physical3d", "bxy_teacher", "teacher2d", "fin3d", "bd_2d", "bd_3dt", "bwlphys", "evaluate", "oracle", "jobs"}
    for f in ("views.py", "models.py", "rank.py", "recursive.py", "run.py"):
        tree = ast.parse((HERE.parent / f).read_text())
        mods = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        mods |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        assert not mods & banned, (f, mods & banned)
        src = (HERE.parent / f).read_text()
        assert not [b for b in ("_private", "PRIVATE_INDEX", '["labels"]', "witnesses/", "k45/cohort/roots") if b in src], f


def test_staged_group_generation_is_bounded_and_declared():
    fz = RandScore(1)
    fz.proposals = lambda r, objs, m=4: {int(o): [40 + 4 * int(o) + k for k in range(4)] for o in objs}
    r = row()
    r["inputs"]["cell_xy"].update({str(c): [0.075 * (c % 8), 0.075 * (c // 8)] for c in range(40, 80)})
    r["inputs"]["legal_cells"] = list(range(80))
    ctx = RC.Ctx(fz, r, "R-FIG3", {"m_max": 6, "exhaustive_max_groups": 50, "beam": 4})
    gs = RC.local_groups(ctx, r, [], [], [], 3)
    assert ctx.n["staged_calls"] == 1 and 0 < len(gs) <= 7 * 4 + 4 * 4 + 4 * 4 * 3
    assert all(V.legal_seq(r, g, 6) for g in gs) and {len(g) for g in gs} == {1, 2, 3}
    ctx2 = RC.Ctx(fz, r, "R-FIG3", {"m_max": 6})
    assert len(RC.local_groups(ctx2, r, [], [], [], 1)) == 7 * 4 and ctx2.n["staged_calls"] == 0


def test_b0_argmax_always_seeded():
    fz = RandScore(3)
    r = row()
    ctx = RC.Ctx(fz, r, "R-FIG3", {"m_max": 6, "n_seeds": 2})
    gs = RC.local_groups(ctx, r, [], [], [], 3, exhaustive=True)
    sc = fz.score(r, gs)
    best = max(zip(gs, sc), key=lambda t: t[1]["p11"])[0]
    assert any(g == best for g, _ in RC.seeds(ctx))
