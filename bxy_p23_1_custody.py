"""BXY-P23.1 remote checkpoint custody (BXY_REMOTE_CUSTODY_P23_1_V1): an independent copy of the 60 frozen D / E / DIRECT-GEO / G P21
checkpoints (+ RESULT.json + reproducibility manifests) in the user's Google Drive, verified by READ-BACK, never by listing alone.

  stage     manifest BEFORE upload: relative path, bytes, sha256, arm, run id, provenance commit; staging tree outside the repository
  upload    rclone copy --checksum --immutable to <remote>:<snapshot> (remote must be an rclone `drive` remote, authorized by the user's own
            browser OAuth; the token lives only in ~/.config/rclone, never in the repository, logs or reports)
  readback  rclone copy <remote>:<snapshot> into a clean directory, sha256 of every file against the manifest, all 60 members re-loaded
            from the restored copy (RESULT.json sha + run id + checkpoint sha), representative held-out predictions recomputed against the
            stored P21 predictions (tolerance 1e-9); only then status REMOTE_CUSTODY_VERIFIED
  evidence  runs/approach_b/bxy_p23_1_v1/REMOTE_CUSTODY_P23_1.json (remote file ids stored only as sha256; the raw listing stays local)
P24 calls verify_evidence(): missing, unverified, corrupted or different-checkpoint evidence -> PermissionError.
    python3 bxy_p23_1_custody.py preflight | stage | upload | readback [remote] | lock"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess as sp
import sys
import time
from pathlib import Path

OUT = Path("runs/approach_b/bxy_p23_1_v1")
P23 = Path("runs/approach_b/bxy_p23_v1")
REMOTE = os.environ.get("BXY_DRIVE_REMOTE", "bxydrive")
SCRATCH = Path(os.environ.get("BXY_CUSTODY_SCRATCH", str(Path.home() / "bxy_checkpoint_backup" / "p23_1_work")))
LOCAL_LISTING = Path.home() / "bxy_checkpoint_backup" / "remote_listing_p23_1.json"      # raw Drive ids: local only, never committed
MANIFESTS = ("FROZEN_MODELS_P23_APPEND.json", "CONFIRM_PLAN_P23_LOCK.json", "CONFIRM_ANALYSIS_P23_LOCK.json", "AUTHORIZATION_P24_PROPOSED.json")
TOL = 1e-9
P23_SHA = "a863c17499d3ba49304962ccb89d436af0076533"                     # commit that froze the 60-member ensembles (snapshot provenance)
ARMS = ("D:XYQ-GEO-SYM", "E:XY-UNC-SA-GEO-SYM", "A:DIRECT-GEO", "G:XYQ-GEO-SYM-ORDINV")


def sha_file(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git(*a) -> str:
    return sp.run(["git", *a], capture_output=True, text=True, check=True).stdout.strip()


def rclone(*a, check=True) -> str:
    exe = shutil.which("rclone") or next((x for x in (str(Path.home() / ".local/bin/rclone"), "/run/host/usr/bin/rclone") if Path(x).exists()), "rclone")   # host install seen from the flatpak sandbox
    if not Path(exe).exists():
        raise RuntimeError("RCLONE_NOT_INSTALLED")
    r = sp.run([exe, *a], capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"rclone {a[0]} failed: {r.stderr.strip()[-400:]}")
    return r.stdout


def frozen() -> dict:
    return json.loads((P23 / "FROZEN_MODELS_P23_APPEND.json").read_text())


def snapshot_name(commit=None) -> str:
    return f"Approach_B_P23_Frozen_P21_Checkpoints_{(commit or P23_SHA)[:7]}"


def remote_type(remote=REMOTE, run=rclone) -> str | None:
    """'drive' for an rclone Google Drive remote (listremotes --long prints names and types only, never tokens)."""
    for ln in run("listremotes", "--long").splitlines():
        name, _, typ = ln.partition(":")
        if name.strip() == remote:
            return typ.strip()
    return None


def preflight(remote=REMOTE, run=rclone) -> dict:
    typ = remote_type(remote, run)
    if typ != "drive":
        return {"status": "BLOCKED_REMOTE_NOT_CONFIGURED", "remote": remote, "type": typ}
    about = json.loads(run("about", f"{remote}:", "--json"))
    return {"status": "REMOTE_READY", "remote": remote, "type": typ, "free_bytes": about.get("free"), "total_bytes": about.get("total")}


def stage(commit) -> dict:
    """Staging tree + manifest (written before any upload)."""
    import torch
    fz = frozen()
    st = SCRATCH / "stage"
    if st.exists():
        shutil.rmtree(st)
    rows = []
    for arm in ARMS:
        for m in fz["arms"][arm]["members"]:
            src = Path(m["dir"])
            for n, h in (("best.pt", m["checkpoint_sha256"]), ("RESULT.json", m["result_sha256"])):
                rel = f"p21_runs/{src.name}/{n}"
                (st / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src / n, st / rel)
                if sha_file(st / rel) != h:
                    raise RuntimeError(f"{rel}: local source does not match the frozen hash")
                rows.append({"path": rel, "bytes": (st / rel).stat().st_size, "sha256": h, "arm": arm, "rid": m["rid"], "kind": n})
    (st / "manifests").mkdir(parents=True, exist_ok=True)
    for n in MANIFESTS:
        shutil.copy2(P23 / n, st / "manifests" / n)
        rows.append({"path": f"manifests/{n}", "bytes": (P23 / n).stat().st_size, "sha256": sha_file(P23 / n), "kind": "manifest"})
    env = {"python": sys.version.split()[0], "torch": torch.__version__, "commit": commit, "load": "bxy_p24_confirm.load_member(arm, member) with dir = restored "
           "p21_runs/<run dir>; bxy_p17.build_model(arm, 0).load_state_dict(torch.load(best.pt))"}
    (st / "manifests" / "ENVIRONMENT.json").write_text(json.dumps(env, indent=1, sort_keys=True))
    (st / "README.md").write_text(f"# Approach B frozen P21 checkpoints (P23.1 custody snapshot)\n\nRepository Narendhiranv04/latent-causal-tamp, branch "
                                  f"approach-b-xy-v1, provenance commit {commit}.\n60 checkpoints of the frozen D / E / DIRECT-GEO / G 15-member ensembles "
                                  f"(FROZEN_MODELS_P23_APPEND.json); every file's sha256 is in MANIFEST_P23_1.json. Immutable: do not edit.\n")
    for n in ("manifests/ENVIRONMENT.json", "README.md"):
        rows.append({"path": n, "bytes": (st / n).stat().st_size, "sha256": sha_file(st / n), "kind": "manifest"})
    man = {"version": "BXY_P23_1_CUSTODY_MANIFEST_V1", "provenance_commit": commit, "snapshot": snapshot_name(commit), "files": rows,
           "checkpoints": sum(r["kind"] == "best.pt" for r in rows), "total_bytes": sum(r["bytes"] for r in rows),
           "frozen_models_sha256": sha_file(P23 / "FROZEN_MODELS_P23_APPEND.json")}
    (st / "MANIFEST_P23_1.json").write_text(json.dumps(man, indent=1, sort_keys=True))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "MANIFEST_P23_1.json").write_text(json.dumps(man, indent=1, sort_keys=True))
    return man


def upload(remote=REMOTE, run=rclone) -> dict:
    man = json.loads((OUT / "MANIFEST_P23_1.json").read_text())
    t0 = time.time()
    run("copy", str(SCRATCH / "stage"), f"{remote}:{man['snapshot']}", "--checksum", "--immutable", "--retries", "5", "--low-level-retries", "10", "--transfers", "4")
    return {"uploaded_files": len(man["files"]) + 1, "wall_s": round(time.time() - t0, 1)}


def readback(remote=REMOTE, run=rclone, members=None) -> dict:
    """Download into a clean directory and verify bytes, loads and predictions; REMOTE_CUSTODY_VERIFIED only if everything holds."""
    import numpy as np
    import bxy_p11 as P
    import bxy_p21_k34 as H
    import bxy_p24_confirm as C24
    man = json.loads((OUT / "MANIFEST_P23_1.json").read_text())
    rb = SCRATCH / "readback"
    if rb.exists():
        shutil.rmtree(rb)
    t0 = time.time()
    run("copy", f"{remote}:{man['snapshot']}", str(rb), "--retries", "5")
    listing = json.loads(run("lsjson", "-R", "--hash", "--files-only", f"{remote}:{man['snapshot']}"))
    LOCAL_LISTING.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_LISTING.write_text(json.dumps(listing, indent=1))
    ok = {r["path"]: (rb / r["path"]).exists() and sha_file(rb / r["path"]) == r["sha256"] for r in man["files"]}
    fz = frozen()
    by = None
    loaded, dmax = {}, 0.0
    for arm in ARMS:
        for m in fz["arms"][arm]["members"]:
            if members is not None and m["rid"] not in members:
                continue
            net = C24.load_member(arm, dict(m, dir=str(rb / "p21_runs" / Path(m["dir"]).name)))
            stored = json.loads((Path(m["dir"]) / "predictions.json").read_text())
            if by is None:
                by = {ev["key"]: sv for sv, _, ev in H.build_all()}
            for k in sorted(stored)[:3]:
                new = P.predict_all(net, by[k])
                for a, b in zip(stored[k]["cands"], new["cands"]):
                    for f in ("p", "J_hat", "px", "py"):
                        if a.get(f) is not None:
                            dmax = max(dmax, abs(a[f] - b[f]))
            loaded[m["rid"]] = {"arm": arm, "checkpoint_sha256": m["checkpoint_sha256"], "result_sha256": m["result_sha256"],
                                "readback_sha_ok": ok[f"p21_runs/{Path(m['dir']).name}/best.pt"] and ok[f"p21_runs/{Path(m['dir']).name}/RESULT.json"]}
    rows = {r["Path"]: {"id_sha256": hashlib.sha256(r.get("ID", "").encode()).hexdigest(), "size": r["Size"], "md5": (r.get("Hashes") or {}).get("md5")} for r in listing}
    full = members is None
    verified = bool(full and remote_type(remote, run) == "drive" and all(ok.values()) and len(loaded) == 60 and all(v["readback_sha_ok"] for v in loaded.values())
                    and dmax <= TOL and set(rows) >= {r["path"] for r in man["files"]})
    ev = {"version": "BXY_REMOTE_CUSTODY_P23_1_V1", "status": "REMOTE_CUSTODY_VERIFIED" if verified else "REMOTE_CUSTODY_FAILED",
          "remote_type": remote_type(remote, run), "snapshot": man["snapshot"], "manifest_sha256": sha_file(OUT / "MANIFEST_P23_1.json"),
          "frozen_models_sha256": man["frozen_models_sha256"], "files_verified": sum(ok.values()), "files_expected": len(man["files"]),
          "members": loaded, "members_loaded": len(loaded), "prediction_max_abs_diff": dmax, "tolerance": TOL, "remote_listing": rows,
          "remote_ids": "stored as sha256 only (the folder is link-accessible); raw listing kept locally outside the repository",
          "readback_wall_s": round(time.time() - t0, 1), "verified_at": time.time()}
    if full:
        (OUT / "REMOTE_CUSTODY_P23_1.json").write_text(json.dumps(ev, indent=1, sort_keys=True))
    shutil.rmtree(rb)
    return ev


def verify_evidence(path=OUT / "REMOTE_CUSTODY_P23_1.json", fz=None) -> dict:
    """P24 gate: verified read-back custody of EXACTLY the frozen 60 checkpoints, else PermissionError."""
    path = Path(path)
    if not path.exists():
        raise PermissionError("remote custody evidence missing: P24 refuses to generate")
    try:
        ev = json.loads(path.read_text())
    except ValueError:
        raise PermissionError("remote custody evidence corrupted")
    fz = fz or frozen()
    if ev.get("status") != "REMOTE_CUSTODY_VERIFIED" or ev.get("remote_type") != "drive" or ev.get("members_loaded") != 60 or ev.get("prediction_max_abs_diff", 1) > TOL:
        raise PermissionError("remote custody not verified")
    want = {m["rid"]: (m["checkpoint_sha256"], m["result_sha256"]) for a in ARMS for m in fz["arms"][a]["members"]}
    got = {rid: (v["checkpoint_sha256"], v["result_sha256"]) for rid, v in ev["members"].items() if v.get("readback_sha_ok")}
    if got != want:
        raise PermissionError("remote custody evidence references different or unverified checkpoints")
    return ev


def lock() -> dict:
    """Versioned successors after verified custody: the analysis lock with post-P23.1 implementation hashes (endpoints, thresholds and
    families copied unchanged from the P23 lock) and the P24 authorization proposal bound to the custody evidence and the new code tree."""
    import bd_2d
    import bxy_p24_confirm as C24
    import bxy_teacher as T
    verify_evidence()
    a = json.loads((P23 / "CONFIRM_ANALYSIS_P23_LOCK.json").read_text())
    a = dict(a, version="BXY_P23_1_CONFIRM_ANALYSIS_LOCK_V1",
             parent={"file": str(P23 / "CONFIRM_ANALYSIS_P23_LOCK.json"), "sha256": sha_file(P23 / "CONFIRM_ANALYSIS_P23_LOCK.json")},
             implementation={"analysis": "bxy_p24_analysis.py", "analysis_sha256": sha_file("bxy_p24_analysis.py"), "runner_sha256": sha_file("bxy_p24_confirm.py"),
                             "engine_sha256": sha_file("bxy_p23_engine.py"), "custody_sha256": sha_file("bxy_p23_1_custody.py")},
             amendment_p23_1="gate-only: bxy_p24_confirm.require_authorization additionally requires verified remote custody (bxy_p23_1_custody.verify_evidence); "
                             "no endpoint, population, threshold, family, statistic, model, teacher or generator change")
    f = OUT / "CONFIRM_ANALYSIS_P23_1_LOCK.json"
    txt = json.dumps(a, indent=1, sort_keys=True)
    if f.exists() and f.read_text() != txt:
        raise FileExistsError("P23.1 analysis lock already frozen with different content")
    f.write_text(txt)
    prop = json.loads((P23 / "AUTHORIZATION_P24_PROPOSED.json").read_text())
    prop.update(version="BXY_P24_AUTHORIZATION_PROPOSED_P23_1_V1", parent={"file": str(P23 / "AUTHORIZATION_P24_PROPOSED.json"),
                "sha256": sha_file(P23 / "AUTHORIZATION_P24_PROPOSED.json")}, locks_sha256=C24.locks_now(), code_tree=C24.code_tree(),
                teacher_hash=T.teacher_hash(), per_query_teacher_budget=bd_2d.QB, approved=False, approved_by=None, approval_text=None)
    (OUT / "AUTHORIZATION_P24_PROPOSED_P23_1.json").write_text(json.dumps(prop, indent=1, sort_keys=True))
    return {"analysis_lock": sha_file(f), "authorization_proposed": sha_file(OUT / "AUTHORIZATION_P24_PROPOSED_P23_1.json")}


if __name__ == "__main__":
    cmd = sys.argv[1]
    if len(sys.argv) > 2:
        REMOTE = sys.argv[2]
    r = {"preflight": lambda: preflight(REMOTE), "stage": lambda: stage(P23_SHA), "upload": lambda: upload(REMOTE), "readback": lambda: readback(REMOTE),
         "lock": lock}[cmd]()
    print(json.dumps({k: v for k, v in r.items() if k not in ("files", "members", "remote_listing")}, indent=1, default=str))
