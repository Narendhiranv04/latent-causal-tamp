"""BXY-P23.1: the remote-custody proof is produced only by a real read-back (bytes, loads, predictions), and P24 refuses to run without verified
evidence for exactly the frozen 60 checkpoints. A fake rclone over a local directory stands in for Drive; it can never yield VERIFIED."""
import json
import shutil
from pathlib import Path

import pytest

import bxy_p23_1_custody as RC

pytestmark = pytest.mark.skipif(not (RC.P23 / "FROZEN_MODELS_P23_APPEND.json").exists(), reason="P23 artifacts missing")


def good_evidence():
    fz = RC.frozen()
    mem = {m["rid"]: {"arm": a, "checkpoint_sha256": m["checkpoint_sha256"], "result_sha256": m["result_sha256"], "readback_sha_ok": True}
           for a in RC.ARMS for m in fz["arms"][a]["members"]}
    return {"status": "REMOTE_CUSTODY_VERIFIED", "remote_type": "drive", "members_loaded": 60, "members": mem, "prediction_max_abs_diff": 0.0}


def test_verify_evidence_refusals_and_positive_case(tmp_path):
    f = tmp_path / "ev.json"
    with pytest.raises(PermissionError, match="missing"):
        RC.verify_evidence(f)
    f.write_text("{not json")
    with pytest.raises(PermissionError, match="corrupted"):
        RC.verify_evidence(f)
    ev = good_evidence()
    f.write_text(json.dumps(ev))
    assert RC.verify_evidence(f)["status"] == "REMOTE_CUSTODY_VERIFIED"
    for bad in (dict(ev, status="REMOTE_CUSTODY_FAILED"), dict(ev, remote_type="local"), dict(ev, members_loaded=59), dict(ev, prediction_max_abs_diff=1e-3)):
        f.write_text(json.dumps(bad))
        with pytest.raises(PermissionError, match="not verified"):
            RC.verify_evidence(f)
    swap = json.loads(json.dumps(ev))
    rid = next(iter(swap["members"]))
    swap["members"][rid]["checkpoint_sha256"] = "0" * 64
    f.write_text(json.dumps(swap))
    with pytest.raises(PermissionError, match="different"):
        RC.verify_evidence(f)
    gone = json.loads(json.dumps(ev))
    gone["members"].pop(rid)
    f.write_text(json.dumps(gone))
    with pytest.raises(PermissionError, match="different"):
        RC.verify_evidence(f)


def fake_rclone(root, typ="local", corrupt=None):
    def run(*a, check=True):
        if a[0] == "listremotes":
            return f"bxydrive: {typ}\n"
        if a[0] == "copy":
            src, dst = (Path(x.split(":", 1)[1]) if x.startswith("bxydrive:") else Path(x) for x in a[1:3])
            src = root / src if a[1].startswith("bxydrive:") else src
            dst = root / dst if a[2].startswith("bxydrive:") else dst
            shutil.copytree(src, dst, dirs_exist_ok=True)
            if corrupt and a[1].startswith("bxydrive:"):
                p = dst / corrupt
                p.write_bytes(p.read_bytes() + b" ")
            return ""
        if a[0] == "lsjson":
            base = root / a[-1].split(":", 1)[1]
            return json.dumps([{"Path": str(p.relative_to(base)), "ID": "id-" + p.name, "Size": p.stat().st_size, "Hashes": {}} for p in sorted(base.rglob("*")) if p.is_file()])
        raise AssertionError(a)
    return run


def test_readback_round_trip_and_corruption_never_verify(tmp_path, monkeypatch):
    monkeypatch.setattr(RC, "SCRATCH", tmp_path / "scratch")
    monkeypatch.setattr(RC, "OUT", tmp_path / "out")
    monkeypatch.setattr(RC, "LOCAL_LISTING", tmp_path / "listing.json")
    man = RC.stage("a863c17499d3ba49304962ccb89d436af0076533")
    assert man["checkpoints"] == 60 and len(man["files"]) == 120 + len(RC.MANIFESTS) + 2
    remote = tmp_path / "remote"
    run = fake_rclone(remote)
    RC.upload(run=run)
    fz = RC.frozen()
    one = {fz["arms"][a]["members"][0]["rid"] for a in RC.ARMS}
    ev = RC.readback(run=run, members=one)
    assert ev["files_verified"] == ev["files_expected"] and ev["members_loaded"] == 4 and ev["prediction_max_abs_diff"] <= RC.TOL
    assert ev["status"] == "REMOTE_CUSTODY_FAILED"                          # partial check and a non-drive remote can never verify
    assert all(len(v["id_sha256"]) == 64 for v in ev["remote_listing"].values()) and "id-" not in json.dumps(ev["remote_listing"])
    m = next(m for m in fz["arms"]["G:XYQ-GEO-SYM-ORDINV"]["members"] if m["rid"] not in one)
    ev2 = RC.readback(run=fake_rclone(remote, "drive", corrupt=f"p21_runs/{Path(m['dir']).name}/RESULT.json"), members=one)
    assert ev2["files_verified"] == ev2["files_expected"] - 1 and ev2["status"] == "REMOTE_CUSTODY_FAILED"


def test_p24_refuses_without_verified_custody(tmp_path, monkeypatch):
    import bxy_p24_confirm as C24
    import bxy_teacher as T
    monkeypatch.setattr(C24, "OUT", tmp_path)
    monkeypatch.setitem(C24.LOCKS, "remote_custody", tmp_path / "REMOTE_CUSTODY_P23_1.json")
    auth = {"approved": True, "approved_by": "test", "approval_text": "x", "locks_sha256": C24.locks_now(), "code_tree": C24.code_tree(), "teacher_hash": T.teacher_hash()}
    (tmp_path / "AUTHORIZATION_P24.json").write_text(json.dumps(auth))
    with pytest.raises(PermissionError, match="remote custody evidence missing"):
        C24.require_authorization()
    (tmp_path / "REMOTE_CUSTODY_P23_1.json").write_text(json.dumps(dict(good_evidence(), status="REMOTE_CUSTODY_FAILED")))
    auth["locks_sha256"] = C24.locks_now()
    (tmp_path / "AUTHORIZATION_P24.json").write_text(json.dumps(auth))
    with pytest.raises(PermissionError, match="not verified"):
        C24.require_authorization()
    (tmp_path / "REMOTE_CUSTODY_P23_1.json").write_text(json.dumps(good_evidence()))
    auth["locks_sha256"] = C24.locks_now()
    (tmp_path / "AUTHORIZATION_P24.json").write_text(json.dumps(auth))
    assert C24.require_authorization()["approved"] is True                 # positive proof: the gate opens only with verified evidence
    (tmp_path / "REMOTE_CUSTODY_P23_1.json").write_text(json.dumps(dict(good_evidence(), prediction_max_abs_diff=0.0, members_loaded=60) | {"extra": 1}))
    with pytest.raises(PermissionError, match="drift"):
        C24.require_authorization()                                         # evidence changed after approval -> lock drift
