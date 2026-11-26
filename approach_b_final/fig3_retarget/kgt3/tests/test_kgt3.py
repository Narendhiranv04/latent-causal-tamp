"""KGT3 tests: grouped / fixed-order DP vs brute force (variable chunks, has_multi, precedence, historical lambda), equivalence with the
historical r24 order.dp, request coverage, assignment counts, fail-closed guard.  Model / planner tests live in test_planners.py (gvlab2)."""
from __future__ import annotations

import hashlib, itertools, json, random, sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "r24"), str(HERE.parent.parent)]
import compose as CP  # noqa: E402
import guard as GD  # noqa: E402


class FakeT:
    """Deterministic pseudo-random chunk costs that depend on the placed SET and the ORDERED chunk (AB != BA)."""
    def __init__(self, seed, strict=None):
        self.seed, self.strict, self.A = seed, strict, None

    def cost(self, U, C):
        U = frozenset(CP._t(U)); C = CP._t(C)
        if self.strict is not None and (U, C) not in self.strict:
            raise KeyError("unrequested read")
        h = hashlib.sha256(f"{self.seed}|{sorted(U)}|{C}".encode()).digest()
        return 0.05 + 3.0 * int.from_bytes(h[:4], "big") / 2 ** 32 + 0.4 * (len(C) - 1)


def same(a, b):
    return (a is None and b is None) or (abs(a[0] - b[0]) < 1e-9 and a[1:] == b[1:])


def acts(m):
    return [(i, 10 + i) for i in range(m)]


@pytest.mark.parametrize("m", [1, 2, 3, 4, 5, 6])
@pytest.mark.parametrize("lam", [0.0, CP.LAM_HIST])
def test_grouped_dp_equals_brute(m, lam):
    for seed in range(4):
        T = FakeT(seed)
        for nm in (False, True):
            assert same(CP.grouped_dp(T, acts(m), need_multi=nm, lam=lam), CP.brute(T, acts(m), need_multi=nm, lam=lam))


@pytest.mark.parametrize("m", [3, 4, 5, 6])
def test_precedence_and_fixed_order(m):
    rng = random.Random(m)
    for seed in range(4):
        T = FakeT(seed)
        A = acts(m)
        before = [(A[i], A[j]) for i, j in itertools.combinations(range(m), 2) if rng.random() < 0.3]
        assert same(CP.grouped_dp(T, A, before=before), CP.brute(T, A, before=before))
        o = list(A); rng.shuffle(o)
        assert same(CP.fixed_order_dp(T, o), CP.brute(T, A, fixed=o))
        assert same(CP.fixed_order_dp(T, o, need_multi=False, lam=CP.LAM_HIST), CP.brute(T, A, fixed=o, need_multi=False, lam=CP.LAM_HIST))


def test_has_multi_forces_multi_action_chunk():
    class Single(FakeT):
        def cost(self, U, C):
            return 0.01 if len(C) == 1 else 5.0
    r = CP.grouped_dp(Single(0), acts(4))
    assert max(r[2]) >= 2 and CP.grouped_dp(Single(0), acts(4), need_multi=False)[2] == [1, 1, 1, 1]


def test_equivalent_to_historical_order_dp():
    import order as OD
    for m in (2, 3, 4, 5):
        for seed in range(3):
            T = FakeT(seed); T.A = sorted(acts(m))
            for lam in (0.0, CP.LAM_HIST):
                h = OD.dp(T, lam=lam)
                g = CP.grouped_dp(T, acts(m), need_multi=False, lam=lam)
                assert abs(h[0] - g[0]) < 1e-12 and h[1] == g[1] and h[2] == g[2]


def test_dp_reads_only_requested_scores():
    for m in (3, 5):
        A = acts(m)
        req = set(CP.requests(A))
        T = FakeT(1, strict=req)
        CP.grouped_dp(T, A)
        o = list(reversed(A))
        T2 = FakeT(1, strict=set(CP.fixed_requests(o)))
        CP.fixed_order_dp(T2, o)


def test_no_factorial_materialization():
    c = CP.counts(8)
    assert len(CP.requests(acts(8))) == c["ordered_evaluations"] and c["ordered_evaluations"] < c["full_orders"]


def test_assignment_counts_and_bound():
    import construct as CO
    sys.path.insert(0, str(HERE))
    import planners as PL
    rng = random.Random(0)
    for _ in range(20):
        D = {o: sorted(rng.sample(range(20), rng.randint(1, 4))) for o in range(rng.randint(2, 6))}
        for k in range(1, len(D) + 1):
            brute = sum(1 for objs in itertools.combinations(sorted(D), k) for ds in itertools.product(*(D[o] for o in objs)) if len(set(ds)) == k)
            assert brute == sum(1 for _ in CO.assignments(D, k)) <= PL.elem([len(v) for v in D.values()], k)


def _write(p, obj):
    p.write_text(json.dumps(obj))


def test_guard_fail_closed(tmp_path):
    jobs = [{"key": f"k{i}"} for i in range(4)]
    m = tmp_path / "jobs.json"; _write(m, jobs)
    GD.seal(m)
    out = tmp_path / "out.jsonl"
    out.write_text("".join(json.dumps({"key": f"k{i}", "X": {"x": 1}}) + "\n" for i in range(3)))
    c = GD.complete(m, out)
    assert c["status"] == "INCOMPLETE" and any("missing" in w for w in c["why"])               # premature completion
    with pytest.raises(GD.NotAuthorized):
        GD.decide(tmp_path / "d.json", {"PASS": True}, [m, out], manifests=[(m, out)])
    with open(out, "a") as f:
        f.write(json.dumps({"key": "k3", "X": {"teacher_status": "UNKNOWN_PLANNER"}}) + "\n")
    c = GD.complete(m, out)
    assert c["status"] == "COMPLETE" and c["kinds"] == {"DONE": 3, "UNKNOWN": 1}
    d = tmp_path / "d.json"
    GD.decide(d, {"PASS": False}, [m, out], manifests=[(m, out)])
    with pytest.raises(GD.NotAuthorized):
        GD.authorize(d, "PASS", True)                                                              # dispatch with a failed gate
    GD.decide(d, {"PASS": True}, [m, out], manifests=[(m, out)])
    assert GD.authorize(d, "PASS", True)
    with open(out, "a") as f:
        f.write(json.dumps({"key": "k0", "X": {"x": 0}}) + "\n")                                    # duplicate record after the decision
    assert GD.complete(m, out)["status"] == "INCOMPLETE"
    with pytest.raises(GD.NotAuthorized):
        GD.authorize(d, "PASS", True)
    _write(m, jobs + [{"key": "k9"}])                                                               # manifest changed after sealing
    assert "seal sha mismatch" in GD.complete(m, out)["why"]
    with pytest.raises(ValueError):
        _write(m, jobs + [{"key": "k0"}]); GD.seal(m)                                              # duplicate keys cannot be sealed
