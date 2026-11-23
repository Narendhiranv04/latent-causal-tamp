"""Set-MCTS contract tests on hand-verifiable fixtures (illustrative mock scores, NOT model predictions) + parity with the frozen selectors.
    python -m pytest approach_b_final/mcts_sets/tests -q"""
import ast, itertools, json, math, random, sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import search_sets as S  # noqa: E402

RULE = {"noop_gate": 0.5, "eta": 0.3, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}
D4 = {1: [10, 11, 12, 13], 2: [10, 14, 15, 16], 3: [17, 18, 19, 20], 4: [21, 22, 23, 24]}


def table_fn(tab, default=0.05, noop=0.1, log=None):
    """Mock scorer: p11 from an ordered-sequence table; records every request so tests can audit calls."""
    def f(seqs):
        out = []
        for s in seqs:
            k = tuple(tuple(x) for x in s)
            if log is not None:
                log.append(k)
            p = noop if not k else tab.get(k, default)
            out.append({"p11": p, "py": p, "px": 1.0})
        return out
    return f


def test_pool_enumerates_every_legal_set_once():
    P = S.Pool(D4); sets = list(P.sets())
    assert len(sets) == len(set(sets))
    brute = {S.Pool.canon(c) for k in (1, 2) for c in itertools.combinations(P.actions(), k)
             if len({o for o, _ in c}) == k and len({d for _, d in c}) == k}
    assert set(sets) == brute                                      # duplicate objects / destinations rejected (obj 1 and 2 share cell 10)
    assert ((1, 10), (2, 10)) not in set(sets) and all(len({o for o, _ in A}) == len(A) for A in sets)


def test_single_relocation_solves():
    r = S.run_arm("EXACT_K2", D4, table_fn({((3, 18),): 0.9}), None, RULE, "r")
    assert r["decision"] == "REPAIR" and r["seq"] == [[3, 18]]


def test_pair_required_and_every_singleton_poor():
    tab = {((1, 11), (4, 22)): 0.85, ((4, 22), (1, 11)): 0.40}     # every singleton keeps the default 0.05 (< eta)
    for arm in ("EXACT_K2", "UCT_SET"):
        r = S.run_arm(arm, D4, table_fn(tab), None, RULE, "r")
        assert r["decision"] == "REPAIR" and r["seq"] == [[1, 11], [4, 22]], arm
    hits = sum(S.run_arm("UCT_SET", D4, table_fn(tab), 64, RULE, "r", seed=s)["seq"] == [[1, 11], [4, 22]] for s in range(5))
    assert hits >= 1                                               # G2: a low-scoring singleton develops into the high-scoring pair


def test_order_chosen_by_energy_not_insertion():
    tab = {((2, 14), (3, 19)): 0.35, ((3, 19), (2, 14)): 0.8}
    picks = {json.dumps(S.run_arm("UCT_SET", D4, table_fn(tab), None, RULE, "r", seed=s)["seq"]) for s in range(6)}
    assert picks == {json.dumps([[3, 19], [2, 14]])}               # different seeded insertion orders, one energy-chosen order


def test_budget_never_exceeded_and_no_partial_set():
    log = []
    for arm in ("RAND_SET", "BEAM_SET", "UCT_SET", "PW_UCT_SET"):
        for B in (1, 2, 3, 16, 64):
            log.clear()
            r = S.run_arm(arm, D4, table_fn({}, log=log), B, RULE, "r", params={"pw": (1.0, 0.5)} if arm == "PW_UCT_SET" else None)
            assert r["scored"] == len(log) == len(set(log)) <= B, (arm, B)
            sc = [k for k in log if len(k) == 2]
            assert all(tuple(reversed(k)) in log for k in sc), (arm, B)          # both orders of every scored pair, never one


def test_noop_charged_identically_and_gate():
    assert S.run_arm("UCT_SET", D4, table_fn({}, noop=0.7), 16, RULE, "r")["decision"] == "NOOP"
    r = S.run_arm("EXACT_K2", D4, table_fn({}, noop=0.1), None, RULE, "r")
    assert r["decision"] == "ABSTAIN" and r["scored"] == r["pool_ordered"]     # every ordered K<=2 sequence + the no-op


def test_terminates_without_looping():
    for D in ({}, {1: [10]}, D4):
        for arm in ("EXACT_K2", "RAND_SET", "BEAM_SET", "UCT_SET", "PW_UCT_SET"):
            prm = {"pw": (1.0, 0.5)} if arm == "PW_UCT_SET" else {"w": 10 ** 3} if arm == "BEAM_SET" else None   # BEAM w=8 covers only its beam
            r = S.run_arm(arm, D, table_fn({}), 10 ** 6, RULE, "r", params=prm)
            assert r["stop"] == "EXHAUSTED" and r["scored"] == r["pool_ordered"], (arm, D)
    r = S.run_arm("UCT_SET", D4, table_fn({}), 7, RULE, "r")
    assert r["stop"] == "BUDGET" and r["iterations"] < 1000


def test_full_budget_mcts_scores_every_set_exactly_once_and_matches_exact():
    rng = random.Random(3)
    tab = {}
    for A in S.Pool(D4).sets():
        for o in itertools.permutations(A):
            tab[o] = rng.random() * 0.6
    ex = S.run_arm("EXACT_K2", D4, table_fn(tab), None, RULE, "r")
    for arm, p in (("UCT_SET", None), ("PW_UCT_SET", {"pw": (1.0, 0.5)}), ("RAND_SET", None), ("BEAM_SET", {"w": 100})):
        r = S.run_arm(arm, D4, table_fn(tab), None, RULE, "r", params=p)
        assert r["sets_scored"] == r["pool_sets"] and r["seq"] == ex["seq"] and r["p11"] == ex["p11"], arm


def test_reentrance_uses_cache():
    log = []; O = S.Oracle(table_fn({}, log=log), 100)
    O.eval_set(((1, 11), (3, 18))); n = len(log)
    assert O.eval_set(((3, 18), (1, 11))) is not None and len(log) == n and O.n["cache_hits"] == 1


def test_deterministic_per_seed():
    tab = {((1, 11),): 0.6, ((2, 15), (4, 23)): 0.7, ((4, 23), (2, 15)): 0.2}
    for arm in ("RAND_SET", "UCT_SET", "PW_UCT_SET", "BEAM_SET"):
        a = S.run_arm(arm, D4, table_fn(tab), 20, RULE, "root-x", seed=1); b = S.run_arm(arm, D4, table_fn(tab), 20, RULE, "root-x", seed=1)
        a.pop("wall_s"); b.pop("wall_s")
        assert a == b, arm


def test_choose_matches_frozen_xy_choose():
    import xy as XY
    rng = random.Random(0)
    for t in range(300):
        rows = [{"seq": [], "p11": rng.random(), "m": 0, "D": 0.0}]
        for i in range(rng.randint(0, 8)):
            m = rng.randint(1, 2); rows.append({"seq": [[i, 30 + i]] * m, "p11": round(rng.random(), rng.choice([2, 6])), "m": m, "D": rng.random()})
        rule = {**RULE, "noop_gate": rng.choice([0.5, None]), "beta": rng.choice([0.0, 0.1])}
        mine = S.choose(rows, rule)
        xr = [{"admissible": True, "m": r["m"], "p": r["p11"], "cd": r["D"], "J_hat": 0.0, "sig": json.dumps(r["seq"])} for r in rows]
        k = XY.choose(xr, rule)
        assert (mine is None and k is None) or (k is not None and mine is rows[k]), t


def test_exact_matches_exhaustive_selectors_k_le_2():
    import numpy as np
    import exhaustive as EX
    rng = random.Random(1)
    for t in range(25):
        D = {o: rng.sample(range(10, 30), 4) for o in rng.sample(range(1, 9), rng.randint(1, 5))}
        tab = {}
        for A in S.Pool(D).sets():
            for o in itertools.permutations(A):
                tab[o] = round(rng.random() * 0.7, rng.choice([2, 5]))
        noop = rng.choice([0.05, 0.35, 0.6])
        ex = S.run_arm("EXACT_K2", D, table_fn(tab, noop=noop), None, RULE, "r")
        sel = EX.Selectors([RULE]); seqs = [o for A in S.Pool(D).sets() for o in itertools.permutations(A)]
        if seqs:
            p = np.array([tab[s] for s in seqs]); m = np.array([len(s) for s in seqs])
            sel.update(seqs, p, m, np.zeros(len(seqs)), np.zeros(len(seqs)), np.zeros(len(seqs), int), {})
        d = sel.finish(noop)[4][0]
        want = None if d is None else d["seq"]
        assert ex["seq"] == want, (t, ex["seq"], want)


def test_planner_modules_import_no_teacher_or_private_data():
    for f in ("search_sets.py", "run.py"):
        p = HERE / f
        if not p.exists():
            continue
        t = ast.parse(p.read_text())
        names = {a.name for n in ast.walk(t) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names} | \
                {n.module for n in ast.walk(t) if isinstance(n, ast.ImportFrom) and n.module}
        assert not names & {"evaluate", "teacher2d", "bxy_teacher", "teacher_long", "mink"}, f
    src = (HERE / "search_sets.py").read_text()
    for bad in ("K_legacy", "labels", "masks", "witness", "private"):
        assert bad not in src.split('"""', 2)[2], bad
