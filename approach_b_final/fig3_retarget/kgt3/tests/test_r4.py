"""R4.0 regressions: complexity accounting (N_X), K <= 3 energy consistency (exact joint p11 only), EXACT only when exhausted, no displacement
tie-break in the scaling recursion, fail-closed guard hardening, evidence taxonomy (certified / budget-relative / operational / unresolved)."""
from __future__ import annotations

import hashlib, itertools, json, math, sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent)]
import compose as CP  # noqa: E402
import guard as GD  # noqa: E402


def acts(m):
    return [(i, 10 + i) for i in range(m)]


def test_nx_formula_and_requests():
    assert CP.nx(8) == 15360
    for m in range(1, 9):
        assert CP.nx(m) == sum(math.factorial(g) * math.comb(m, g) * 2 ** (m - g) for g in range(1, min(3, m) + 1))
        assert len(CP.requests(acts(m))) == CP.nx(m) == CP.counts(m)["ordered_evaluations"]
    assert CP.counts(8)["unordered_transitions"] == 4608 and CP.counts(8)["states"] == 256


def test_distinct_requests_equals_union_over_pool():
    D = {0: [10, 11], 1: [12], 2: [13, 14], 3: [15], 4: [16, 17]}
    import construct as CO
    H = 5
    union = set()
    for k in range(1, H + 1):
        for A in CO.assignments(D, k):
            union |= set(CP.requests(A))
    e = {s: sum(1 for _ in CO.assignments(D, s)) for s in range(1, H + 1)}
    assert CP.distinct_requests(e) == len(union)
    assert sum(e[k] * CP.nx(k) for k in e) > len(union)                     # unshared theoretical count exceeds the cached unique count


class FakeFz:
    """Deterministic fake learned model: px / p11 depend on scene key + ordered chunk; y_global on the endpoint set."""
    dev = "cpu"

    def __init__(self, D):
        self.D, self.c, self.calls = D, {}, []

    def reset(self):
        self.c = {}

    def proposals(self, row, el):
        return {o: self.D.get(o, []) for o in el}

    def _h(self, *a):
        return int.from_bytes(hashlib.sha256(json.dumps(a, default=str).encode()).digest()[:4], "big") / 2 ** 32

    def score(self, S, seqs):
        self.calls.append(len(seqs))
        return [{"px": 0.2 + 0.7 * self._h("x", S, s), "p11": 0.1 + 0.8 * self._h("p", S, s), "py": 0.5} for s in seqs]

    def y_global(self, row0, E):
        return [0.2 + 0.7 * self._h("y", sorted(map(tuple, e))) for e in E]

    def p_noop(self, row):
        return 0.0


@pytest.fixture
def patched(monkeypatch):
    import planners as PL
    monkeypatch.setattr(PL.V, "eligible", lambda row0, *a, **k: sorted(row0["D"]))
    monkeypatch.setattr(PL.V, "legal_seq", lambda row0, seq, H: True)
    monkeypatch.setattr(PL.V, "rebase", lambda row0, U, **k: json.dumps(sorted(map(list, U))))
    return PL


def test_short_assignments_use_exact_joint_p11_only(patched):
    PL = patched
    D = {0: [10, 11], 1: [12, 13], 2: [14]}
    row = {"domain": "2d", "root_id": "r", "D": D}
    cands, info = PL.ga(FakeFz(D), row, "AUTO")
    assert cands and all(c["kind"] == "p11_single" and c["partition"] == [len(c["seq"])] for c in cands)
    assert info["exhausted"] and info["mode"] == "EXACT"
    out = PL.assignment_given(FakeFz(D), row, [(0, 10), (1, 12)], witness=[[1, 12], [0, 10]])
    assert all(out[a]["partition"] == [2] and out[a]["kind"] == "p11_single" for a in ("SEL-DP", "RANDOM", "WITNESS"))


def test_long_assignments_use_marginal_composition_and_accounting(patched):
    PL = patched
    D = {0: [10], 1: [11], 2: [12], 3: [13], 4: [14]}
    row = {"domain": "3d", "root_id": "r", "D": D}
    cands, info = PL.ga(FakeFz(D), row, "AUTO")
    long = [c for c in cands if len(c["seq"]) > 3]
    assert long and all(c["kind"] == "ga_dp" and max(c["partition"]) >= 2 for c in long)
    s = info["scores"]
    assert s["requested"] == s["x_unique"] + s["cache_hits"] and s["dp_lookups"] == CP.nx(4) * 5 + CP.nx(5)
    assert info["est_distinct_x"] >= s["x_unique"] and set(info["by_size"]) == {1, 2, 3, 4, 5}


def test_rec_passes_no_displacement_tiebreak(patched, monkeypatch):
    PL = patched
    seen = {}

    def fake_discover(fz, row0, arm, rc):
        seen.update(rc)
        raise TimeoutError("stop")
    monkeypatch.setattr(PL.RC, "discover", fake_discover)
    with pytest.raises(TimeoutError):
        PL.rec(FakeFz({}), {"domain": "2d", "root_id": "r"}, "REC-ORDERED")
    assert seen["disp_tiebreak"] is False


def test_seed_tiebreak_ignores_displacement_when_disabled(monkeypatch):
    import recursive as RC
    calls = []
    monkeypatch.setattr(RC.V, "displacement", lambda row0, s: calls.append(1) or 0.0)
    monkeypatch.setattr(RC, "local_groups", lambda ctx, *a, **k: [[[0, 10]], [[1, 11]]])

    class F(FakeFz):
        def score(self, S, seqs):
            return [{"p11": 0.5, "px": 0.5} for _ in seqs]
    for dsp, expect in ((False, 0), (True, 1)):
        calls.clear()
        ctx = RC.Ctx(F({}), {"domain": "2d", "root_id": "r"}, "R-FIG3", {"disp_tiebreak": dsp, "n_seeds": 1})
        RC.seeds(ctx)
        assert (len(calls) > 0) == bool(expect)


def _mk(tmp, n=2):
    m = tmp / "jobs_a.json"
    m.write_text(json.dumps([{"key": f"k{i}"} for i in range(n)]))
    GD.seal(m)
    return m


def test_guard_no_outcome_record_is_incomplete(tmp_path):
    m = _mk(tmp_path)
    o = tmp_path / "out.jsonl"
    o.write_text(json.dumps({"key": "k0", "X": {"x": 1}}) + "\n" + json.dumps({"key": "k1", "X": {}}) + "\n")
    c = GD.complete(m, o)
    assert c["status"] == "INCOMPLETE" and any("terminal outcome" in w for w in c["why"])


def test_guard_unbound_manifest_once_and_required(tmp_path):
    m = _mk(tmp_path)
    o = tmp_path / "out.jsonl"
    o.write_text("".join(json.dumps({"key": f"k{i}", "X": {"x": 0, "negative_kind": "CERTIFIED"}}) + "\n" for i in range(2)))
    m2 = tmp_path / "jobs_expansion.json"
    m2.write_text(json.dumps([{"key": "z"}])); GD.seal(m2)
    with pytest.raises(GD.NotAuthorized, match="unbound"):
        GD.decide(tmp_path / "d.json", {"G": "PASS", "auroc": 0.8}, [m], manifests=[(m, o)], stage_dir=tmp_path)
    with pytest.raises(GD.NotAuthorized, match="missing required"):
        GD.decide(tmp_path / "d.json", {"G": "PASS", "auroc": None}, [m], manifests=[(m, o)], required=("auroc",))
    GD.decide(tmp_path / "d.json", {"G": "PASS", "auroc": 0.8}, [m], manifests=[(m, o)], required=("auroc",), once=True)
    with pytest.raises(GD.NotAuthorized, match="already opened"):
        GD.decide(tmp_path / "d.json", {"G": "PASS", "auroc": 0.8}, [m], manifests=[(m, o)], once=True)


@pytest.mark.parametrize("rec,exp", [
    ({"X": {"x": 1, "status": "VERIFIED"}}, "SUCCESS"),
    ({"X": {"x": 0, "status": "no feasible side grasp", "negative_kind": "CERTIFIED"}}, "CERTIFIED_INFEASIBLE"),
    ({"X": {"x": 0, "status": "no feasible side grasp", "negative_kind": "NO_PLAN_FOUND"}}, "BUDGET_NO_PLAN"),
    ({"X": {"x": 0, "status": "CONNECTOR_NO_PLAN", "negative_kind": "NO_PLAN_FOUND"}}, "BUDGET_NO_PLAN"),
    ({"X": {"x": 0, "status": "EXECUTION_NOT_VERIFIED", "negative_kind": "OTHER_FAILURE"}}, "OPERATIONAL_FAILURE"),
    ({"X": {"x": 0, "teacher_status": "UNKNOWN_PLANNER", "negative_kind": "NO_PLAN_FOUND"}}, "UNRESOLVED"),
    ({"X": {"x": 0, "teacher_status": "CERTIFIED_INFEASIBLE", "negative_kind": "CERTIFIED"}}, "CERTIFIED_INFEASIBLE"),
    ({"censored": True}, "CENSORED"), ({"error": "x"}, "ERROR"), ({"X": {}}, "NO_OUTCOME")])
def test_outcome_taxonomy(rec, exp):
    assert GD.outcome(rec) == exp


def test_assignment_given_long_reports_chunk_px(patched):
    PL = patched
    D = {0: [10], 1: [11], 2: [12], 3: [13]}
    row = {"domain": "3d", "root_id": "r", "D": D}
    A = [(0, 10), (1, 11), (2, 12), (3, 13)]
    out = PL.assignment_given(FakeFz(D), row, A, witness=[[3, 13], [2, 12], [1, 11], [0, 10]])
    for a in ("SEL-DP", "RANDOM", "WITNESS"):
        assert max(out[a]["partition"]) >= 2 and len(out[a]["chunk_px"]) == len(out[a]["partition"])
    assert out["WITNESS"]["order"] == [[3, 13], [2, 12], [1, 11], [0, 10]]
