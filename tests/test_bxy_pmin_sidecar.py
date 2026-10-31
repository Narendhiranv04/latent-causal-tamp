"""BXY-P-MIN sidecar verification / analysis tests on stored P9 witnesses (copied to a scratch store) and synthetic rows: a tampered or
missing witness demotes a positive to unobserved (never 0), a negative needs its failed phase, identity / membership checks, order and
omission contrast bookkeeping. No teacher planning."""
import copy
import json
import shutil

import numpy as np
import pytest

import bxy_data as bd

HAVE = (bd.DATA / "roots").exists()
pytestmark = pytest.mark.skipif(not HAVE, reason="local BD_GEN_V1 snapshot not present")
if HAVE:
    import bxy_pmin_collect as C
    import bxy_pmin_sidecar as S
    import bxy_teacher as T
    R, E, D = bd.roots(), T.env(), C.design()


@pytest.fixture
def store(tmp_path, monkeypatch):
    shutil.copytree(S.P9_OUT / "witnesses", tmp_path / "witnesses")
    monkeypatch.setattr(S, "OUT", tmp_path)
    sc = json.loads(S.PM.PILOT.read_text())
    xs, ys = S.p9_reused(D)
    return tmp_path, xs, ys, sc


def test_p9_reuse_selects_design_members_and_verifies(store):
    out, xs, ys, sc = store
    assert len(xs) == 57 and len(ys) == 59
    v = [S.verify(E, R, D, r) for r in xs + ys]
    assert all(r["verification"]["identity"] and r["verification"]["f1"] and r["verification"]["member"] for r in v)
    assert sum(r["verification"]["witness"] is True for r in v) == 49 + 29 and all(r["observed"] for r in v)


def test_tampered_or_missing_witness_is_demoted_not_relabelled(store):
    out, xs, ys, sc = store
    x = next(r for r in xs if r["y"] == 1)
    w = out / "witnesses" / x["witness_connector"][:2] / f"{x['witness_connector']}.npz"
    z = dict(np.load(w))
    z["q"] = z["q"] + 0.05
    np.savez(w, **z)
    v = S.verify(E, R, D, x)
    assert v["teacher_status"] == "WITNESS_VERIFICATION_FAILED" and v["observed"] is False and v["y"] is None and v["original_y"] == 1
    y = next(r for r in ys if r["y"] == 1)
    (out / "witnesses" / y["target_witness"][:2] / f"{y['target_witness']}.npz").unlink()
    assert S.verify(E, R, D, y)["teacher_status"] == "WITNESS_VERIFICATION_FAILED"


def test_negative_needs_phase_and_identity_is_rechecked(store):
    out, xs, ys, sc = store
    n = copy.deepcopy(next(r for r in xs if r["y"] == 0))
    assert S.verify(E, R, D, n)["observed"] is True
    n["failed_phase"] = None
    assert S.verify(E, R, D, n)["teacher_status"] == "VERIFICATION_FAILED"
    m = copy.deepcopy(next(r for r in ys if r["y"] == 0))
    m["hypothetical_poses"] = {**m["hypothetical_poses"], "o00": 0}
    assert S.verify(E, R, D, m)["verification"]["identity"] is False


def test_order_and_omission_bookkeeping():
    k = next(k for k in D["root_order"] if any(len(c["seq"]) == 2 and S.F1.screen(R[k], [tuple(a) for a in c["seq"]])["x_ok"]
                                               for c in bd.catalogue(R[k])[1:]))
    rec = R[k]
    s = next([tuple(a) for a in c["seq"]] for c in bd.catalogue(rec)[1:] if len(c["seq"]) == 2 and S.F1.screen(rec, [tuple(a) for a in c["seq"]])["x_ok"])
    X = [{"root": k, "design_key": T.xkey(k, rec, s), "ordered_actions": s, "parent_y_key": T.ykey(k, rec, s), "y": 1, "negative_kind": None, "teacher_status": "VERIFIED"},
         {"root": k, "design_key": T.xkey(k, rec, s[::-1]), "ordered_actions": s[::-1], "parent_y_key": T.ykey(k, rec, s), "y": 0,
          "negative_kind": "CERTIFIED", "failed_phase": "relocation:0", "teacher_status": "CERTIFIED_INFEASIBLE", "detail": "x"}]
    o = S.order_contrasts(X, R)
    assert (o["groups"], o["discordant"], o["failing_orders"]["certified"]) == (1, 1, 1)
    Y = [{"design_key": T.ykey(k, rec, q), "y": v} for q, v in ((s, 1), ([s[0]], 0), ([s[1]], 0), ([], 0))]
    om = S.omission_contrasts([], Y, {"root_order": [k]}, R)
    assert om["two_move_interaction"] == {"1": 1} and om["y_full_to_omitted"] == {"1->0": 2}
