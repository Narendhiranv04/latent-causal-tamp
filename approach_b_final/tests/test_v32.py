"""V3.2-A exhaustive streaming: exact enumeration and exact equivalence of the online selectors with xy.choose (CPU, synthetic)."""
import itertools, json, math, random, sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import construct as CO  # noqa: E402
import contracts as CT  # noqa: E402
import evaluate as EV  # noqa: E402
import exhaustive as EX  # noqa: E402


def _D6(rng, n_obj, cells=30):
    return {o: rng.sample(range(cells), rng.randint(0, 6)) for o in range(n_obj)}


def test_stream_counts_membership_uniqueness_and_all_orders():
    rng = random.Random(1)
    for _ in range(25):
        D6 = _D6(rng, rng.randint(1, 6))
        seqs = list(EX.stream(D6, 6))
        assert len(seqs) == len({s for s, _ in seqs})                                   # every legal candidate exactly once
        for M in (4, 5, 6):
            DM = {o: v[:M] for o, v in D6.items()}
            got = Counter(len(s) for s, r in seqs if r < M)
            assert [got[1], got[2], got[3]] == CO.counts(DM)                             # prefix membership = exact M counts
            ref = {tuple(p) for k in (1, 2, 3) for a in CO.assignments(DM, k) for p in itertools.permutations(a)}
            assert {s for s, r in seqs if r < M} == ref                                  # same set as the complete constructor
        by = Counter(CT.ekey([list(x) for x in s]) for s, _ in seqs)
        for k, v in by.items():
            assert v == math.factorial(len(json.loads(k)))                               # every K2 / K3 order retained


def test_selectors_equal_xy_choose_all_rules_all_M_with_ties_and_chunks():
    rng = random.Random(7)
    rules = EV.GRID
    for trial in range(40):
        n = rng.randint(1, 60)
        seqs = [tuple((rng.randint(0, 5), rng.randint(0, 40)) for _ in range(rng.randint(1, 3))) for _ in range(n)]
        seqs = list(dict.fromkeys(seqs))
        n = len(seqs)
        p = np.array([rng.choice([0.05, 0.2, 0.31, 0.5, 0.5, 0.9, rng.random()]) for _ in range(n)])   # forced exact ties
        m = np.array([len(s) for s in seqs]); D = np.array([rng.choice([0.0, 1.0, 1.5, rng.random() * 3]) for _ in range(n)])
        J = np.array([rng.choice([0.0, 0.5, rng.random()]) for _ in range(n)]); r = np.array([rng.randint(0, 5) for _ in range(n)])
        p_noop = rng.choice([0.05, 0.31, 0.6, 0.85, 0.5])
        sel = EX.Selectors(rules)
        cut = sorted(rng.sample(range(n + 1), min(2, n + 1)))
        for a, b in zip([0] + cut, cut + [n]):
            if b > a:
                sel.update(seqs[a:b], p[a:b], m[a:b], D[a:b], J[a:b], r[a:b], {"py": p[a:b], "px": p[a:b], "J": J[a:b]})
        dec = sel.finish(p_noop)
        for M in (4, 5, 6):
            cands = [{"seq": [], "p11": p_noop, "J": 0.0, "m": 0, "D": 0.0}] + [
                {"seq": [list(x) for x in seqs[i]], "p11": float(p[i]), "J": float(J[i]), "m": int(m[i]), "D": float(D[i])} for i in range(n) if r[i] < M]
            for k, rule in enumerate(rules):
                want = EV.select(cands, rule)
                got = dec[M][k]
                assert (None if got is None else got["seq"]) == want, (trial, M, rule)
