"""Contract tests for the repair-ranking study (plan.md 12).  Real-bundle tests skip when the frozen bundle / CUDA is unavailable."""
import json, math, sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import rr  # noqa: E402


def _real():
    if not (rr.BUNDLE / "MANIFEST.json").exists() or not rr.PUB_VAL.exists():
        pytest.skip("frozen bundle unavailable")
    import torch
    if not torch.cuda.is_available():
        pytest.skip("no CUDA")
    return rr.bundle()


# ------------------------------------------------------------------------------------------------ labels and semantics
def test_z_logic_and_historical_strict():
    assert rr.z_logic(1, 1) == 1 and rr.z_logic(0, None) == 0 and rr.z_logic(None, 0) == 0 and rr.z_logic(1, None) is None
    assert rr.z_hist(0, None) == "UNKNOWN" and rr.z_hist(None, 0) == "FAIL_Y" and rr.z_hist(0, 1) == "FAIL_X" and rr.z_hist(1, 1) == "SUCCESS"


def _cache(tmp, name, recs):
    d = tmp / name; d.mkdir()
    (d / "verify_2d.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
    return d / "verify_2d.jsonl"


def test_strict_labels_unknown_missing_fill_and_conflict_quarantine(tmp_path):
    R = lambda seq, x, xs, y, ys: {"seq": seq, "x": {"x": x, "status": xs}, "y": {"y": y, "status": ys}}  # noqa: E731
    a = _cache(tmp_path, "a", [{"root": "r", "results": [R([[0, 5]], 0, "UNKNOWN_PLANNER", 1, "VERIFIED"), R([[1, 6]], 1, "VERIFIED", 1, "VERIFIED")]}])
    b = _cache(tmp_path, "b", [{"root": "r", "results": [R([[0, 5]], 1, "VERIFIED", 1, "VERIFIED"), R([[1, 6]], 0, "CERTIFIED_INFEASIBLE", 1, "VERIFIED")]}])
    lab = rr.strict_labels([a, b])
    e1, e2 = lab[("r", "[[0, 5]]")], lab[("r", "[[1, 6]]")]
    assert (e1["x"], e1["y"], e1["conflict"]) == (1, 1, False)          # UNKNOWN value 0 never counts; later decided value fills it
    assert e2["conflict"] and e2["x"] is None and e2["y"] is None       # disagreeing decided values -> quarantined, not picked


def test_family_partition_deterministic_and_family_level():
    assert rr.dev_part("fam-abc") == rr.dev_part("fam-abc")
    if rr.SNAP.exists() and rr.PRIV_VAL.exists():
        vm = rr.val_meta()
        fam_parts = {}
        for m in vm.values():
            fam_parts.setdefault(m["family"], set()).add(m["part"])
        assert all(len(s) == 1 for s in fam_parts.values())
        tr = {r["parent_family_id"] for r in rr.snapshot_rows("train")}
        assert not tr & {m["family"] for m in vm.values()}


# ------------------------------------------------------------------------------------------------ frozen readout
def test_readout_identities_and_batch_invariance_real():
    samp, scor, man = _real()
    import search as S
    pub = rr.public_val()[:6]
    jobs = []
    for r in pub:
        R = S.Root(r, "2d"); L = R.legal_dests(R.cells0); mv = R.movable
        seqs = [[]] + [[[o, d]] for o in mv[:2] for d in L[:3]] + [[[mv[0], L[0]], [mv[1], L[1]]], [[mv[1], L[1]], [mv[0], L[0]]]]
        jobs.append((r, seqs))
    many = rr.readout(scor.net, jobs)
    for (r, seqs), o in zip(jobs, many):
        ref = scor.score(S.Root(r, "2d"), seqs)
        one = rr.readout(scor.net, [(r, seqs)])[0]
        for a, b, c in zip(ref, o["rows"], one["rows"]):
            assert abs(a["p11"] - b["p11"]) < 1e-5 and abs(b["p11"] - c["p11"]) < 1e-6
            if "px1" in b:
                assert abs(b["p11"] - b["py"] * b["px1"]) < 1e-12
                assert abs(b["px"] - (b["py"] * b["px1"] + (1 - b["py"]) * b["px0"])) < 1e-12
                assert abs(a["px"] - b["px"]) < 1e-5                    # Scorer.score px is the MARGINAL, not pX1
                assert math.isfinite(b["lp11"])
        assert abs(o["rows"][-1]["py"] - o["rows"][-2]["py"]) < 1e-12  # same endpoint, both orders: one Y node


def test_legal_grammar():
    if not rr.PUB_VAL.exists():
        pytest.skip("public VAL unavailable")
    import search as S
    r = rr.public_val()[0]; R = S.Root(r, "2d"); L = R.legal_dests(R.cells0); mv = R.movable
    assert rr.legal_k2(r, [[mv[0], L[0]]]) and rr.legal_k2(r, [[mv[0], L[0]], [mv[1], L[1]]])
    assert not rr.legal_k2(r, [[mv[0], L[0]], [mv[0], L[1]]])            # object twice
    assert not rr.legal_k2(r, [[mv[0], L[0]], [mv[1], L[0]]])            # destination twice
    assert not rr.legal_k2(r, [[mv[0], R.cells0[mv[1]]]])                # vacated / originally occupied cell
    assert not rr.legal_k2(r, [[mv[0], R.goal]]) and not rr.legal_k2(r, [[R.tid, L[0]]])
    assert not rr.legal_k2(r, [[mv[0], L[0]], [mv[1], L[1]], [mv[2] if len(mv) > 2 else mv[1], L[2]]])
