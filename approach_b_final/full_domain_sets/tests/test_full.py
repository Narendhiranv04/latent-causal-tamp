"""Contract tests for the full-legal-domain K<=2 set search (plan.md v1.1 P2).  Synthetic worlds need no GPU; the real-root tests skip if the
frozen bundle / public VAL file / CUDA are unavailable."""
import gzip, itertools, json, math, os, re, sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import domain as DM  # noqa: E402
import fsearch as FS  # noqa: E402

RULE = {"noop_gate": 0.5, "eta": 0.3, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}
SCHED = (0.25, 0.5)
P = {"sched": SCHED, "w": 4, "c": 0.3, "pw": (1.0, 0.5), "nb": 8, "q_dir": 0.25}
SEARCH = ("RAND_FULL", "BEAM_SEEDED4", "BEAM_FULL", "BEAM_FULL_UNIFORM", "PW_MCTS_SEEDED4", "PW_MCTS_FULL", "PW_MCTS_UNIFORM")


def world(n_obj=4, cells=range(10, 22)):
    """Synthetic domain: prior decreasing in cell id (ties broken by id), archived top-6 = the six highest."""
    raw = {o: {d: (len(cells) - i + 0.5 * (o % 2 == 0)) for i, d in enumerate(cells)} for o in range(n_obj)}
    raw = {o: {d: v / sum(r.values()) for d, v in r.items()} for o, r in raw.items()}
    D6 = {o: sorted(r, key=lambda d: (-r[d], d))[:6] for o, r in raw.items()}
    return DM.Domain(raw, D6, 0.25), DM.Domain(raw, D6, 1.0), raw


def scorer(table, base=0.05, noop=0.1, log=None):
    def f(seqs):
        if log is not None:
            log.append(len(seqs))
        return [{"p11": noop if not s else table.get(tuple(map(tuple, s)), base), "py": None, "px": None} for s in seqs]
    return f


def run(arm, dom, udom, f, B, seed=0, **kw):
    return FS.run_arm(arm, dom, f, B, RULE, "root", seed, None, {**P, **kw}, udom)


def full_sets(dom):
    return sum(1 for _ in FS.Pool({o: [d for (oo, d) in dom.acts if oo == o] for o in dom.objs}).sets())


# ----------------------------------------------------------------------------------------------------------------------- domain / prior
def test_universe_tiers_prior_support():
    dom, udom, raw = world()
    assert set(dom.acts) == {(o, d) for o in raw for d in raw[o]}
    for o in dom.objs:
        by = sorted((a for a in dom.acts if a[0] == o), key=lambda a: dom.rank[a])
        assert [d for _, d in by[:4]] == dom.D6[o][:4] and [d for _, d in by[4:6]] == dom.D6[o][4:6]
        assert [dom.tier[a] for a in by] == [1] * 4 + [2] * 2 + [3] * (len(by) - 6)
    assert all(v > 0 for v in dom.pi.values()) and abs(sum(dom.pi.values()) - 1) < 1e-9
    assert len({round(v, 12) for v in udom.pi.values()}) == 1                       # eps = 1: uniform over legal actions
    assert dom.n_pairs() == full_sets(dom) - len(dom.acts)
    with pytest.raises(AssertionError):
        DM.Domain(raw, {0: [99]}, 0.25)                                              # archived cell outside the public legal domain


def test_zero_mass_cell_stays_reachable():
    dom, udom, raw = world()
    raw2 = {o: dict(r) for o, r in raw.items()}; raw2[0][21] = 0.0                  # unseen-by-MC style zero raw mass
    d2 = DM.Domain(raw2, {o: v for o, v in dom.D6.items()}, 0.25)
    assert d2.tier[(0, 21)] == 3 and d2.pi[(0, 21)] > 0
    f = scorer({((0, 21), (1, 20)): 0.95, ((1, 20), (0, 21)): 0.9})
    x = run("PW_MCTS_SEEDED4", d2, udom, f, 2 * full_sets(d2) + 1)
    assert x["decision"] == "REPAIR" and x["seq"] == [[0, 21], [1, 20]]


# ---------------------------------------------------------------------------------------------------------------------- staged access
@pytest.mark.parametrize("arm", ["BEAM_SEEDED4", "PW_MCTS_SEEDED4"])
def test_initial_top4_only_and_exact_unlock_thresholds(arm):
    dom, udom, _ = world(5, range(10, 30))
    B = 401
    x = FS.run_arm(arm, dom, scorer({}), B, RULE, "r", 0, None, dict(P), udom)
    ev = {lvl: c for lvl, c, why in x["tier_events"] if why == "BUDGET_FRACTION"}
    assert set(ev) == {2, 3}
    for lvl, f in ((2, SCHED[0]), (3, SCHED[1])):
        assert (ev[lvl] - 1) / (B - 1) >= f                                         # inclusive threshold on the non-noop budget fraction
        assert (ev[lvl] - 1 - 2 * P["nb"]) / (B - 1) < f                            # fired at the first batch boundary after crossing
    O_log = _log(arm, dom, udom, B)
    for A, start, _ in O_log:
        t = max(dom.tier[a] for a in A)
        assert t == 1 or start >= ev[t], (A, start, ev)                             # no T56 / tail set assembled before its unlock


def _log(arm, dom, udom, B):
    O = FS.Oracle(scorer({}), B); st = FS.Stage(dom, O, SCHED); rng = np.random.default_rng(FS.h64(arm.split("_")[0], "r", 0))
    (FS.beam if arm.startswith("BEAM") else FS.mcts)(dom, O, st, rng, **{k: v for k, v in P.items() if k != "sched" and (k != "w" or arm.startswith("BEAM")) and (k not in ("c", "pw") or arm.startswith("PW"))})
    return O.log


@pytest.mark.parametrize("arm", ["BEAM_SEEDED4", "PW_MCTS_SEEDED4"])
def test_early_tier_exhaustion_unlocks_without_charge(arm):
    dom, udom, _ = world(1, range(10, 20))                                           # one object: T4 = 4 singletons, exhausted at charge 5
    x = run(arm, dom, udom, scorer({}), 1000)
    early = [(l, c) for l, c, why in x["tier_events"] if why == "EARLY_TIER_EXHAUSTION"]
    assert early and early[0] == (2, 5)                                              # unlocked at charge 5: no fake scorer charge
    assert x["scored"] == 1 + len(dom.acts) and x["stop"] == "EXHAUSTED"


def test_reopen_after_unlock_and_full_reachability():
    dom, udom, _ = world(3, range(10, 20))
    n = full_sets(dom)
    for arm in ("PW_MCTS_SEEDED4", "BEAM_SEEDED4", "PW_MCTS_FULL", "BEAM_FULL"):
        O = FS.Oracle(scorer({}), 10 ** 6); st = FS.Stage(dom, O, SCHED if "SEEDED" in arm else None)
        rng = np.random.default_rng(1)
        if arm.startswith("PW"):
            stop, it, root, T, stats = FS.mcts(dom, O, st, rng, c=0.3, pw=(1.0, 0.5), nb=4, q_dir=0.25)
            if "SEEDED" in arm:
                assert stats["reopen_events"] + sum(1 for e in st.events if e[2] == "EARLY_TIER_EXHAUSTION") >= 2
                assert any(dom.tier[k.A[0]] == 1 and any(max(dom.tier[a] for a in kk.A) == 3 for kk in k.kids if not kk.stop)
                           for k in root.kids)                                        # a T4 singleton node later grew tail pairs
        else:
            stop = FS.beam(dom, O, st, rng, w=2, nb=4, q_dir=0.25)
        assert stop == "EXHAUSTED" and len(O.sets) == n                             # every legal unordered K1/K2 set reached exactly once
        assert len(O.log) == n and O.n["scored"] == len(O.cache)


def test_same_domain_and_schedule_for_seeded_arms():
    dom, udom, _ = world(5, range(10, 30))
    a = run("BEAM_SEEDED4", dom, udom, scorer({}), 401); b = run("PW_MCTS_SEEDED4", dom, udom, scorer({}), 401)
    lv = lambda x: [(l, w) for l, _, w in x["tier_events"]]  # noqa: E731
    assert lv(a) == lv(b) == [(1, "START"), (2, "BUDGET_FRACTION"), (3, "BUDGET_FRACTION")]
    for x in (a, b):
        assert all(abs((c - 1) / 400 - f) <= 2 * P["nb"] / 400 for (l, c, w), f in zip(x["tier_events"][1:], SCHED))


# ------------------------------------------------------------------------------------------------------------- synergy / order / budget
@pytest.mark.parametrize("arm", SEARCH)
def test_off4_only_winning_pair_found_with_adequate_budget(arm):
    dom, udom, _ = world(4, range(10, 20))
    tail = [a for a in dom.acts if dom.tier[a] == 3]
    a, b = next((x, y) for x in tail for y in tail if x[0] < y[0] and x[1] != y[1])
    f = scorer({(a, b): 0.4, (b, a): 0.93})
    x = run(arm, dom, udom, f, 2 * full_sets(dom) + 1)
    assert x["decision"] == "REPAIR" and x["seq"] == [list(b), list(a)]              # X/Y-chosen order, not insertion order
    assert x["pick_stratum"] == "TWO_OFF4|BEYOND6"


@pytest.mark.parametrize("arm", ["BEAM_SEEDED4", "BEAM_FULL", "PW_MCTS_SEEDED4", "PW_MCTS_FULL"])
def test_low_singleton_high_pair(arm):
    """Every singleton (including a and b) is poor and only the pair {a, b} is good: no arm may prune it away.  Contract = found with an
    adequate budget for every seed; the fraction found at 600 of ~4,800 ordered sequences is a measured property (reported, not asserted)."""
    dom, udom, _ = world(6, range(10, 22))
    a, b = (0, dom.D6[0][0]), (5, dom.D6[5][1])
    f = scorer({(a, b): 0.9, (b, a): 0.9}, base=0.02)
    good = ([list(a), list(b)], [list(b), list(a)])
    assert all(run(arm, dom, udom, f, 2 * full_sets(dom) + 1, seed=s)["seq"] in good for s in range(3))
    hits = sum(run(arm, dom, udom, f, 600, seed=s)["seq"] in good for s in range(8))
    f = HERE / "reports" / "P2_LOW_SINGLETON_FIXTURE.json"
    R = json.loads(f.read_text()) if f.exists() else {}
    R[arm] = {"budget": 600, "ordered_sequences_in_domain": 2 * full_sets(dom) - len(dom.acts), "found_of_8_seeds": hits}
    f.write_text(json.dumps(R, indent=1, sort_keys=True))


def test_budget_all_orders_or_nothing_and_accounting():
    O = FS.Oracle(scorer({}), 2)
    assert O.eval_many([((0, 10), (1, 11))])[((0, 10), (1, 11))] is None and O.n["scored"] == 1   # a pair never half-scored
    assert O.eval_many([((0, 10),)])[((0, 10),)] is not None and O.left() == 0
    dom, udom, _ = world()
    for arm in SEARCH:
        for B in (16, 64, 257):
            x = run(arm, dom, udom, scorer({}), B)
            assert x["scored"] <= B and x["stop"] in ("BUDGET", "EXHAUSTED")


def test_noop_gate_and_abstain():
    dom, udom, _ = world()
    assert run("PW_MCTS_SEEDED4", dom, udom, scorer({}, noop=0.6), 64)["decision"] == "NOOP"
    assert run("BEAM_FULL", dom, udom, scorer({}, base=0.1, noop=0.1), 64)["decision"] == "ABSTAIN"


def test_limits_and_determinism():
    dom, udom, _ = world(5, range(10, 30))
    for arm in SEARCH:
        x = FS.run_arm(arm, dom, scorer({}), 4096, RULE, "r", 0, None, dict(P), udom, max_batches=3)
        assert x["stop"] == "BATCH_LIMIT" and x["batches"] == 3
        y = FS.run_arm(arm, dom, scorer({}), 4096, RULE, "r", 0, None, dict(P), udom, max_wall=0.0)
        assert y["stop"] == "WALL_LIMIT"
        r1, r2 = run(arm, dom, udom, scorer({((0, 10),): 0.7}), 300), run(arm, dom, udom, scorer({((0, 10),): 0.7}), 300)
        assert {k: v for k, v in r1.items() if k != "wall_s"} == {k: v for k, v in r2.items() if k != "wall_s"}
    O = FS.Oracle(scorer({}), 10 ** 6); st = FS.Stage(dom, O, None)
    assert FS.mcts(dom, O, st, np.random.default_rng(0), max_iter=5)[0] == "ITER_GUARD"


def test_batching_is_cache_invariant():
    """Same arm, batched scorer vs one-sequence-at-a-time scorer: identical decisions and charges (scores are pure functions)."""
    dom, udom, _ = world(5, range(10, 30))
    t = {((1, 12),): 0.8, ((2, 11), (3, 14)): 0.9}
    f1 = scorer(t); f2 = lambda seqs: [scorer(t)([s])[0] for s in seqs]  # noqa: E731
    for arm in SEARCH:
        a, b = run(arm, dom, udom, f1, 500), run(arm, dom, udom, f2, 500)
        assert (a["seq"], a["scored"], a["sets_scored"]) == (b["seq"], b["scored"], b["sets_scored"])


def test_exact_full_matches_bruteforce_and_choose_is_frozen():
    sys.path.insert(0, str(HERE.parent))
    import xy as XY
    dom, udom, _ = world(3, range(10, 16))
    rng = np.random.default_rng(3); seqs = {}
    for A in FS.Pool({o: [d for (oo, d) in dom.acts if oo == o] for o in dom.objs}).sets():
        for r in itertools.permutations(A):
            seqs[r] = float(rng.uniform(0, 0.99))
    x = run("EXACT_FULL", dom, udom, scorer(seqs), None)
    best = max(seqs, key=lambda r: (seqs[r], [-v for v in json.dumps(r).encode()]))
    assert x["scored"] == len(seqs) + 1 and tuple(map(tuple, x["seq"])) == best
    O = FS.Oracle(scorer(seqs), None); O.eval_many(list(FS.Pool({o: [d for (oo, d) in dom.acts if oo == o] for o in dom.objs}).sets()))
    rows = O.candidates()
    xr = [{"admissible": True, "m": c["m"], "p": c["p11"], "cd": c["D"], "J_hat": 0.0, "sig": json.dumps(c["seq"])} for c in rows]
    i = XY.choose(xr, RULE)
    assert FS.choose(rows, RULE)["seq"] == json.loads(xr[i]["sig"])


def test_no_teacher_private_or_intermediate_scene_access():
    for f in ("fsearch.py", "domain.py", "run.py"):
        src = (HERE / f).read_text()
        assert not re.search(r"import (teacher2d|evaluate|v32b_phys)|_verify_job|BM\.teach|verify_2d|private_val|mcts_sets_private|fds_private|genlab|labels\.B|\[\"K\"\]", src), f
    assert "cells0" in (HERE / "domain.py").read_text() and "root.cells(" not in (HERE / "domain.py").read_text()


# --------------------------------------------------------------------------------------------------------------------- real roots
def _real():
    if not (Path.home() / "abf_v34/approach_b_bundle/MANIFEST.json").exists():
        pytest.skip("frozen bundle unavailable")
    import torch
    if not torch.cuda.is_available():
        pytest.skip("no CUDA")
    import importlib.util  # load by path: ../mcts_sets/run.py has the same module name
    spec = importlib.util.spec_from_file_location("fds_run", HERE / "run.py")
    RUN = importlib.util.module_from_spec(spec); spec.loader.exec_module(RUN)
    return RUN


def test_real_roots_top6_parity_legal_domain_and_exact4_matches_sealed_old_predictions():
    RUN = _real()
    import exhaustive as EX
    samp, scor, man = RUN.models()
    old = {}
    with gzip.open(HERE.parent / "mcts_sets/reports/P2_EVAL_PREDICTIONS.jsonl.gz", "rt") as fh:
        for l in fh:
            r = json.loads(l); old[r["root_id"]] = next(x for x in r["results"] if x["arm"] == "EXACT_K2")
    rows = [r for r in RUN.root_rows(None, "EVAL")][:6]
    for r in rows:
        root, dom, _ = RUN.build(r, samp, man, 0.25)
        assert dom.D6 == EX.proposals(root, samp, 0)
        assert dom.L == sorted(root.legal_dests(root.cells0)) and root.goal not in dom.L and not set(dom.L) & set(root.cells0)
        assert dom.objs == sorted(root.movable) and root.tid not in dom.objs
        x = FS.run_arm("EXACT4", dom, lambda s: scor.score(root, s), None, man["config"]["rule"], r["root_id"], disp=root.displacement)
        assert (x["decision"], x["seq"]) == (old[r["root_id"]]["decision"], old[r["root_id"]]["seq"])
