"""GA-MCTS unit tests (fake deterministic model; no GPU, no physics).  Spec section 5 items covered here: constraint validity, GA == GA-MCTS
energy / partition for the same assignment and for the exhausted domain, no evaluator-only access, no physical calls, deadline respected, no
redundant equivalent-assignment exploration, original planners unaffected, monotone incumbent energy along a trajectory."""
from __future__ import annotations

import hashlib, itertools, json, math, subprocess, sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
KG = HERE.parent
sys.path[:0] = [str(HERE), str(KG), str(KG.parent), str(KG.parent.parent)]
import compose as CP  # noqa: E402
import construct as CO  # noqa: E402
import planners as PL  # noqa: E402
import mcts_ga as MG  # noqa: E402
import anytime as AT  # noqa: E402

TID = 99


class FakeFz:
    dev = "cpu"

    def __init__(self, D, dt=0.0, clock=None):
        self.D, self.dt, self.clock = D, dt, clock
        self.c, self.caps, self.nscore = {"x_unique": 0, "y_unique": 0}, {}, 0

    def reset(self):
        self.c = {"x_unique": 0, "y_unique": 0}

    def proposals(self, row, el):
        return {o: list(self.D.get(o, [])) for o in el}

    def _h(self, *a):
        return int.from_bytes(hashlib.sha256(json.dumps(a, default=str).encode()).digest()[:4], "big") / 2 ** 32

    def score(self, S, seqs):
        if self.clock is not None:
            self.clock[0] += self.dt
        self.nscore += 1
        self.c["x_unique"] += len(seqs)
        return [{"px": 0.2 + 0.79 * self._h("x", S, s), "p11": 0.05 + 0.9 * self._h("p", S, s), "py": 0.5} for s in seqs]

    def y_global(self, row0, E):
        self.c["y_unique"] += len(E)
        return [0.1 + 0.89 * self._h("y", sorted(map(tuple, e))) for e in E]

    def p_noop(self, row):
        return 0.01


@pytest.fixture
def patched(monkeypatch):
    monkeypatch.setattr(PL.V, "eligible", lambda row0, *a, **k: sorted(o for o in row0["D"] if o != TID))
    monkeypatch.setattr(PL.V, "legal_seq", lambda row0, seq, H: all(o != TID for o, _ in seq))
    monkeypatch.setattr(PL.V, "rebase", lambda row0, U, **k: json.dumps(sorted(map(list, U))))
    return PL


@pytest.fixture
def clock(monkeypatch):
    t = [1000.0]
    monkeypatch.setattr(PL.time, "perf_counter", lambda: t[0])
    return t


def row(D):
    return {"domain": "3d", "root_id": "r", "D": D}


D_SMALL = {0: [10, 11], 1: [11, 12], 2: [13], 3: [10, 14], 4: [15, 16], TID: [17]}     # overlapping destinations (distinctness matters)
INF = {"wall_s": 1e9}


def total_sets(D, H=5):
    D = {o: v for o, v in D.items() if o != TID}
    return sum(1 for k in range(1, H + 1) for _ in CO.assignments(D, k))


def run_search(D, mcfg=None, cfg=None):
    fz = FakeFz(D)
    sink = {"cands": [], "info": {}}
    c = {**PL.CFG, **INF, **(cfg or {}), "mcts": {**MG.MCFG, **(mcfg or {})}}
    S = MG.Search(fz, row(D), c, sink)
    cands, info = S.run()
    return S, cands, info, fz


# 1 constraint validity -----------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("expand", ["FULL", "PW"])
def test_constraints_on_every_evaluated_set(patched, expand):
    S, cands, info, _ = run_search(D_SMALL, {"expand": expand, "batch": 7})
    for A in S.evals:
        objs, ds = [o for o, _ in A], [d for _, d in A]
        assert 1 <= len(A) <= 5 and len(set(objs)) == len(objs) and len(set(ds)) == len(ds) and TID not in objs
        assert all(d in D_SMALL[o] for o, d in A) and list(A) == sorted(A)
    for c in cands:
        assert max(c["partition"]) <= 3 and sum(c["partition"]) == len(c["seq"])
        if len(c["seq"]) > 3:
            assert max(c["partition"]) >= 2                                   # has_multi
        assert sorted(map(tuple, c["seq"])) == sorted(map(tuple, c["set"]))


# 2 identical terminal energy / partition ------------------------------------------------------------------------------------------------
def ga_terminal(fz, r0, A):
    """Reference: exactly planners.ga's per-assignment evaluation (fresh Scores cache)."""
    yg = fz.y_global(r0, [list(map(list, A))])[0]
    if len(A) <= 3:
        best = None
        for c in PL.short_options(fz, r0, [list(map(list, o)) for o in itertools.permutations(A)]):
            if best is None or PL.ckey(c) < PL.ckey(best):
                best = c
        return best["E"], best["seq"], best["partition"]
    T = CP.Scores(fz, r0, PL.V.rebase)
    T.need(set(CP.requests(A)))
    F, o, p = CP.grouped_dp(T, A)
    return F - math.log(max(CP.EPS, yg)), o, p


def test_same_assignment_same_energy_and_partition(patched):
    D = {0: [10, 11], 1: [12, 13], 2: [14], 3: [15, 16], 4: [17], 5: [18]}
    fz = FakeFz(D); r0 = row(D)
    sink = {"cands": [], "info": {}}
    S = MG.Search(fz, r0, {**PL.CFG, **INF}, sink)
    S.root = MG.Node(()); S.prefetch()
    sets = [A for k in (1, 2, 3, 4, 5) for A in itertools.islice(CO.assignments(D, k), 0, 40, 7)]
    res = S.evaluate(sets)
    for A in sets:
        E, o, p = ga_terminal(FakeFz(D), r0, A)
        assert abs(res[A]["E"] - E) < 1e-12 and res[A]["seq"] == [list(a) for a in o] and res[A]["partition"] == p


def test_exhausted_mcts_equals_exact_ga_plan(patched):
    D = dict(D_SMALL)
    for m in ({"expand": "FULL"}, {"expand": "PW", "c": 0.2, "batch": 5}, {"expand": "PW", "c": 2.0, "seed": 3}):
        g = PL.plan(FakeFz(D), row(D), "GA", {"seq": [[0, 10]]}, INF)
        assert g["info"]["mode"] == "EXACT" and g["info"]["exhausted"]
        mm = MG.plan(FakeFz(D), row(D), {"seq": [[0, 10]]}, INF, m)
        assert mm["info"]["exhausted"] and mm["arm"] == "GA-MCTS"
        assert (mm["decision"], mm["seq"], mm["partition"], mm["kind"]) == (g["decision"], g["seq"], g["partition"], g["kind"])
        assert abs(mm["E"] - g["E"]) < 1e-12
        assert {int(k): v["E"] for k, v in mm["info"]["by_size"].items()} == {int(k): v["E"] for k, v in g["info"]["by_size"].items()}


# 3 no evaluator-only access / 4 no physical calls --------------------------------------------------------------------------------------
FORBIDDEN = ("witness", "L_ref", "K_cert", "PRIVATE", "R10_PRIVATE", "physical", "mujoco", "jobs24", "teacher", "labels", "oracle", "r8b")


def test_static_no_evaluator_or_physical_tokens():
    for f in ("mcts_ga.py", "anytime.py"):
        src = (HERE / f).read_text()
        code = "\n".join(l.split("#")[0] for l in src.split('"""', 2)[-1].splitlines())   # docstring stripped, comments stripped
        bad = [t for t in FORBIDDEN if t in code]
        assert not bad, (f, bad)


def test_no_physical_module_loaded_after_planning():
    prog = f"""
import sys, json; sys.path[:0] = {[str(HERE), str(KG), str(KG.parent), str(KG.parent.parent)]!r}
sys.path.insert(0, {str(Path(__file__).parent)!r})
import test_mcts_ga as T, planners as PL, mcts_ga as MG
PL.V.eligible = lambda r, *a, **k: sorted(o for o in r['D'] if o != T.TID)
PL.V.legal_seq = lambda r, s, H: True
PL.V.rebase = lambda r, U, **k: json.dumps(sorted(map(list, U)))
D = T.D_SMALL
MG.plan(T.FakeFz(D), T.row(D), None, T.INF, {{}})
bad = [m for m in sys.modules if any(t in m.lower() for t in ('physical', 'mujoco', 'jobs24', 'teacher', 'pybullet', 'bd_gif', 'ompl'))]
print(json.dumps(bad))
"""
    out = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1]
    assert json.loads(out) == []


def test_roster_public_only_private_absent(tmp_path):
    pub = tmp_path / "pub.jsonl"
    pub.write_text(json.dumps({"root_id": "r1", "domain": "3d", "inputs": {"ids": ["t0", "o00"], "cells0": [0, 1], "tid": 0, "goal_cell": 5}}) + "\n")
    rows = AT.roster(pub)
    assert [r[0] for r in rows] == ["r1"] and set(rows[0][1]) == {"root_id", "domain", "inputs"}
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({"root_id": "r1", "domain": "3d", "witness": [[1, 2]], "inputs": {"ids": []}}) + "\n")
    with pytest.raises(AssertionError):
        AT.roster(bad)


# 5 deadline respected -------------------------------------------------------------------------------------------------------------------
def test_deadline_respected_with_incumbent(patched, clock):
    D = {i: [10 + i, 30 + i] for i in range(8)}
    fz = FakeFz(D, dt=0.05, clock=clock)
    out = MG.plan(fz, row(D), {"seq": [[0, 10]]}, {"wall_s": 6.0, "select_reserve": {"wall_s": 1.0, "x_unique": 64, "y_unique": 8}}, {"batch": 4})
    assert out["stop"] and out["stop"].startswith("TimeoutError") and out["budget_stop"]
    assert out["search_wall_s"] <= 6.0 - 1.0 + 0.05 * 3 + 1e-9                  # bounded overrun: one model batch
    assert out["deadline_overrun_s"] == round(max(0.0, out["wall_s"] - 6.0), 3) and out["deadline_overrun_s"] <= 0.2
    assert out["decision"] == "REPAIR" and out["n_candidates"] >= 1 and out["info"]["exhausted"] is False


def test_floor_consuming_budget_no_search(patched, clock):
    D = {0: [10], 1: [11]}

    def floor(t_end):
        clock[0] += 100.0
        return {"seq": [[0, 10]]}
    out = MG.plan(FakeFz(D), row(D), floor, {"wall_s": 50.0})
    assert out["stop"].startswith("TimeoutError") and out["kind"] == "production_floor" and out["arm"] == "GA-MCTS"


# 6 no redundant exploration -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("m", [{"expand": "FULL"}, {"expand": "PW", "batch": 3}, {"expand": "PW", "c": 0.05, "seed": 7}])
def test_each_legal_set_evaluated_exactly_once(patched, m):
    S, _, info, _ = run_search(D_SMALL, m)
    assert info["exhausted"] and info["n_evals"] == len(S.evals) == total_sets(D_SMALL)
    assert set(S.evals) == {A for k in range(1, 6) for A in CO.assignments({o: v for o, v in D_SMALL.items() if o != TID}, k)}


def test_canonical_paths_unique(patched):
    S, *_ = run_search(D_SMALL)
    seen = {}

    def walk(n, path):
        for k in n.kids:
            assert k.A not in seen, ("transposition", k.A)
            seen[k.A] = path
            walk(k, path + (k.A,))
    walk(S.root, ())
    assert len(seen) == total_sets(D_SMALL)


# 7 original planners unaffected ---------------------------------------------------------------------------------------------------------
def test_planners_ga_restored_and_ga_plan_unchanged(patched):
    D = dict(D_SMALL)
    orig = PL.ga
    a = PL.plan(FakeFz(D), row(D), "GA", {"seq": [[0, 10]]}, INF)
    MG.plan(FakeFz(D), row(D), {"seq": [[0, 10]]}, INF)
    with pytest.raises(RuntimeError):
        with MG.search_as_ga(lambda *a_, **k: (_ for _ in ()).throw(RuntimeError("x"))):
            PL.plan(FakeFz(D), row(D), "GA", None, INF)
    assert PL.ga is orig
    b = PL.plan(FakeFz(D), row(D), "GA", {"seq": [[0, 10]]}, INF)
    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items() if "wall" not in str(k) and k != "deadline_overrun_s"}
        return [strip(v) for v in o] if isinstance(o, list) else o
    assert json.dumps(strip(a), sort_keys=True, default=str) == json.dumps(strip(b), sort_keys=True, default=str)


def test_timed_wrapper_preserves_ga_plan(patched):
    D = dict(D_SMALL)
    a = PL.plan(FakeFz(D), row(D), "GA", {"seq": [[0, 10]]}, INF)
    r = AT.trajectory(FakeFz(D), row(D), "GA", lambda t: {"seq": [[0, 10]]}, {}, 1e6, (5, 1e6))
    f = r["final"]
    assert (f["decision"], f["seq"], f["partition"], f["E"], f["kind"]) == (a["decision"], a["seq"], a["partition"], a["E"], a["kind"])
    assert r["recon_final_ok"]


# 8 monotone incumbent energy ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("arm", ["GA", "GA-MCTS"])
def test_monotone_incumbent_along_trajectory(patched, clock, arm):
    D = {i: [10 + i, 30 + i, 50 + i] for i in range(7)}
    fz = FakeFz(D, dt=0.01, clock=clock)
    r = AT.trajectory(fz, row(D), arm, lambda t: {"seq": [[0, 10]]}, {}, 30.0, (5, 10, 20, 30), {"batch": 8, "expand": "PW"})
    es = [e for _, e in r["trace"] if e is not None]
    assert es and all(b <= a + 1e-12 for a, b in zip(es, es[1:]))
    sel = [r["budgets"][str(b)]["E"] for b in (5, 10, 20, 30) if r["budgets"][str(b)]["E"] is not None]
    assert all(b <= a + 1e-12 for a, b in zip(sel, sel[1:]))
    assert r["recon_final_ok"]
    assert all(v["overrun_s"] <= 0.5 for v in r["budgets"].values())
