"""BXY-P23 final-confirmation preflight (no teacher query, no training, no confirmation scene, no test prediction).

  start        P22 HEAD, clean tracked tree, frozen-artifact hash guard
  reproduce    EVALUATION_P21.json recomputed from the committed P21 runs (only accounting.eval_cpu_s may differ)
  checkpoints  all 90 P21 runs: RESULT.json sha256 + run id + best.pt sha256 (repository and the P22 same-disk copy); every D / E / A / G
               member test-loaded and its stored held-out predictions recomputed (max abs difference)
  freeze       FROZEN_MODELS_P23_APPEND.json: the immutable P22 D / E / A ensembles referenced by hash, the P21 G ensemble added with the
               SAME 15-member averaging, and each arm's single pooled rule (bxy_p18.pooled_rule = bxy_p17.choose_rule on the arm's P21
               early-stop predictions pooled over folds and seeds; frozen GRID / U_MAX; no new search, no test data)
  contract     q_ref = q0 = scene robot state for every record and frozen input cache; scorer views carry no forbidden key
  synthetic    the P24 generate + freeze path on a separate synthetic namespace (bxyp23synth; no teacher): construction, label-free
               inputs, all 60 frozen members loaded and scored with the frozen rules
  lock         CONFIRM_PLAN_P23_LOCK.json, CONFIRM_ANALYSIS_P23_LOCK.json (successors; the P22 originals are referenced by sha256) and
               the PROPOSED P24 authorization manifest (approved = false)
  custody      a hash-verified copy of the frozen checkpoints on a PHYSICALLY different disk or an approved off-machine path, plus a
               restore test; a copy on the repository's own disk is refused (BLOCKED_CHECKPOINT_CUSTODY)
    python3 bxy_p23_preflight.py start | reproduce | checkpoints | freeze | contract | synthetic | lock | figure | custody [dest]"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess as sp
import sys
import time
from pathlib import Path

import numpy as np

import bxy_p23_engine as EN
import bxy_p24_confirm as C24
from bxy_p24_confirm import ARMS, sha_file

OUT = Path("runs/approach_b/bxy_p23_v1")
P21, P22 = Path("runs/approach_b/bxy_p21_v1"), Path("runs/approach_b/bxy_p22_v1")
P22_SHA = "bcad58e68c09f5d7ec3cc5942f5fc7a40c9315a4"
SYNTH_NS = "bxyp23synth"


def git(*a) -> str:
    return sp.run(["git", *a], capture_output=True, text=True, check=True).stdout.strip()


def save(name, obj, once=False):
    f = OUT / name
    txt = json.dumps(obj, indent=1, sort_keys=True, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    if once and f.exists() and f.read_text() != txt:
        raise FileExistsError(f"{f} already frozen with different content")
    f.write_text(txt)
    return sha_file(f)


def start() -> dict:
    import bxy_p16_audit as AU
    return {"head": git("rev-parse", "HEAD"), "head_is_p22": git("rev-parse", "HEAD") == P22_SHA, "tracked_clean": git("status", "--porcelain", "-uno") == "",
            "guard": AU.guard(), "confirm_namespace_absent": not any(Path("runs").glob("**/*bxyg34confirm*")) and not C24.OUT.exists()}


def _strip(d):
    return {k: _strip(v) for k, v in d.items() if k != "accounting"} if isinstance(d, dict) else d


def reproduce() -> dict:
    import bxy_p21_eval as E2
    new = json.loads(json.dumps(E2.evaluate(), sort_keys=True, default=str))
    old = json.loads((P21 / "EVALUATION_P21.json").read_text())
    return {"identical_except_accounting": _strip(new) == _strip(old), "stored_sha256": sha_file(P21 / "EVALUATION_P21.json"),
            "recomputed_sha256_except_accounting": EN.sha(_strip(new))}


def runs() -> dict:
    out = {}
    for f in sorted((P21 / "runs").glob("*/RESULT.json")):
        r = json.loads(f.read_text())
        out[r["rid"]] = {"dir": str(f.parent), "arm": r["spec"]["arm"], "seed": r["spec"]["seed"], "result_sha256": sha_file(f),
                         "checkpoint_sha256": r["files"]["best.pt"], "files": r["files"]}
    return out


def checkpoints() -> dict:
    import bxy_p17_data as DATA
    import bxy_p21_k34 as H
    import bxy_p11 as P
    F = runs()
    p22 = json.loads((P22 / "FROZEN_MODELS_P22.json").read_text())
    rows = {}
    for rid, r in F.items():
        d = Path(r["dir"])
        b = Path(p22["backup"]) / d.name / "best.pt"
        rows[rid] = {"arm": r["arm"], "repo_ok": sha_file(d / "best.pt") == r["checkpoint_sha256"],
                     "files_ok": all(sha_file(d / n) == h for n, h in r["files"].items() if (d / n).exists()),
                     "p22_record_ok": p22["arms"].get(r["arm"], {}).get("checkpoints", {}).get(rid, {}).get("sha256", r["checkpoint_sha256"]) == r["checkpoint_sha256"],
                     "same_disk_copy_ok": b.exists() and sha_file(b) == r["checkpoint_sha256"]}
    with_p22 = {rid for a in p22["arms"].values() for rid in a["runs"]}
    by = {ev["key"]: sv for sv, _, ev in H.build_all()}
    load = {}
    for rid, r in sorted(F.items()):
        if r["arm"] not in ARMS:
            continue
        net = C24.load_member(r["arm"], {"rid": rid, **r})
        stored = json.loads((Path(r["dir"]) / "predictions.json").read_text())
        dmax, n = 0.0, 0
        for k, pr in stored.items():
            new = P.predict_all(net, by[k])
            for a, b in zip(pr["cands"], new["cands"]):
                for f in ("p", "J_hat", "px", "py", "w"):
                    if a.get(f) is not None:
                        dmax = max(dmax, abs(a[f] - b[f]))
            for f in ("px", "py", "psucc"):
                if pr["vars"].get(f) is not None:
                    dmax = max(dmax, float(np.max(np.abs(np.asarray(pr["vars"][f]) - np.asarray(new["vars"][f])))) if pr["vars"][f] else 0.0)
            n += 1
        load[rid] = {"arm": r["arm"], "heldout_roots": n, "max_abs_diff": dmax}
    del DATA
    return {"runs": len(F), "all_repo_ok": all(v["repo_ok"] and v["files_ok"] for v in rows.values()),
            "p22_recorded_runs_ok": all(rows[r]["p22_record_ok"] and rows[r]["same_disk_copy_ok"] for r in with_p22),
            "rows": rows, "test_load": load, "test_load_max_abs_diff": max(v["max_abs_diff"] for v in load.values()),
            "test_load_members": {a: sum(v["arm"] == a for v in load.values()) for a in ARMS}}


def env_identity() -> dict:
    import torch
    return {"python": sys.version.split()[0], "torch": torch.__version__, "numpy": np.__version__, "platform": platform.platform(), "cpu_only": True}


def freeze() -> dict:
    import bxy_p18 as Z18
    import bxy_p21_eval as E2
    import bxy_p11 as P
    import bxy_p17 as M
    F, Cx = runs(), E2.context()
    p22 = json.loads((P22 / "FROZEN_MODELS_P22.json").read_text())
    arms = {}
    for arm in ARMS:
        mem = sorted((rid for rid, r in F.items() if r["arm"] == arm), key=lambda rid: (F[rid]["seed"], rid))
        rule = Z18.pooled_rule(arm, Cx)
        if arm in p22["arms"] and sorted(p22["arms"][arm]["runs"]) != sorted(mem):
            raise RuntimeError(f"{arm}: P22 frozen members differ from the P21 run tree")
        arms[arm] = {"members": [{"rid": rid, "dir": F[rid]["dir"], "result_sha256": F[rid]["result_sha256"], "checkpoint_sha256": F[rid]["checkpoint_sha256"]} for rid in mem],
                     "rule": rule["rule"], "rule_inner_pooled_early_stop": rule["inner"], "rule_guardrail_met": rule["guardrail_met"],
                     "source": "P22 frozen (unchanged; referenced)" if arm in p22["arms"] else "ADDED IN P23 (P21 checkpoints; no retraining)",
                     "role": {"D:XYQ-GEO-SYM": "candidate", "E:XY-UNC-SA-GEO-SYM": "uncoupled challenger / deployment preference", "A:DIRECT-GEO": "matched DIRECT",
                              "G:XYQ-GEO-SYM-ORDINV": "secondary mechanistic order-invariant control"}[arm]}
    return {"version": "BXY_P23_FROZEN_MODELS_APPEND_V1", "parent": {"file": str(P22 / "FROZEN_MODELS_P22.json"), "sha256": sha_file(P22 / "FROZEN_MODELS_P22.json"),
                                                                     "commit": P22_SHA},
            "amendment": ["adds G:XYQ-GEO-SYM-ORDINV (15 P21 checkpoints) as the matched order-invariant control required by the P23 contract",
                          "records each arm's pooled rule: P22 declared the procedure (bxy_p18.pooled_rule) but did not record the chosen rules; they are "
                          "computed here deterministically from the P21 early-stop predictions with the frozen GRID and U_MAX, no new search, no test data"],
            "arms": arms, "grid": M.GRID, "u_max": M.U_MAX,
            "ensemble": "mean over the arm's 15 cross-fit checkpoints of p (p_succ; no-op P(Y0)), J_hat, px, py per candidate; F1 first; P.choose with the arm's rule",
            "input_contract": "bxy_p16_inputs.view: scene, goal_cell, q0 = q_ref only (DINOv2-small rev ed25f3a3, 224 px, 16 x 16); catalogue structure (sig, m, C_d, "
                              "F1 admissibility, X / Y query identities) from bxy_p20_k34.root_design; no label, kind, role, K, certificate or witness",
            "p21_numbers_are_not_ensemble_estimates": "P21 OOF numbers are 3-seed fold-rule estimates of the cross-fit procedure, not of these 15-member pooled-rule ensembles",
            "model_code_sha256": {f: sha_file(f) for f in ("bxy_p17.py", "bxy_p11.py", "bxy_p17_data.py", "bxy_p16_inputs.py", "bxy_p18.py", "abc_models.py", "bxy_core.py", "bxy_p14.py")},
            "design_sha256": sha_file(P21 / "TRAINING_DESIGN_P21.json"), "inputs_k34_sha256": sha_file(P21 / "INPUTS_K34.pt"), "environment": env_identity(),
            "choose_sha256": EN.sha(P.choose.__code__.co_code.hex())}


def contract() -> dict:
    import torch
    import bxy_data as bd
    import bxy_p15 as P15
    import bxy_p16 as G
    import bxy_p20_k34 as Z
    recs = {k: r for k, r in bd.roots().items() if bd.split_of(r) in ("train", "val")}          # the 34 exposed test roots are never read
    recs.update(P15.pilot_roots())
    for w in G.WAVES:
        if (G.wdir(w) / "roots").exists():
            recs.update(G.roots_of(w))
    for w in Z.WAVES:
        recs.update(Z.roots_of(w))
    bad = [k for k, r in recs.items() if not (list(r.get("q_ref", r["q0"])) == list(r["q0"]) == list(r["scene"]["robot"]["q_rad"]))]
    caches = {}
    for f in ("runs/approach_b/bxy_p16_v1/inputs/INPUTS_P15_PILOT.pt", "runs/approach_b/bxy_p16_v1/inputs/INPUTS_V21.pt", str(P21 / "INPUTS_K34.pt")):
        d = torch.load(f, weights_only=False)["roots"]
        caches[f] = {"roots": len(d), "q_ref_eq_q0": all(list(v["q_ref"]) == list(recs[k]["q0"]) for k, v in d.items())}
    return {"records": len(recs), "q_ref_ne_q0": bad, "caches": caches, "forbidden_scorer_keys": list(__import__("bxy_p11").FORBIDDEN)}


def synthetic() -> dict:
    """P24 machinery on two synthetic slots (the first local_pick doorway slot, the first V21B control slot) under a separate namespace: no
    teacher, no confirmation seed (seeds hash the namespace)."""
    d = OUT / "synthetic"
    if d.exists():
        shutil.rmtree(d)
    slots = [s for s in json.loads((OUT / "CONFIRM_PLAN_P23_LOCK.json").read_text())["slots"] if s["spec"]["family"] in ("local_pick", "v21b_near_closed")]
    pick = [next(s for s in slots if s["spec"]["family"] == "local_pick"), next(s for s in slots if s["spec"]["family"] == "v21b_near_closed")]
    g = C24.generate(d, ns=SYNTH_NS, slots=pick, workers=2)
    seal = C24.freeze(d, synthetic=True) if g["accepted"] else None
    pr = json.loads((d / "PREDICTIONS_P24.json").read_text()) if seal else {}
    return {"namespace": SYNTH_NS, "generation": g, "seal": seal, "roots": {k: {a: {"n_cands": len(v["cands"]), "chosen": v["chosen"],
                                                                                  "p_noop": next(c["p"] for c in v["cands"] if c["m"] == 0)} for a, v in p.items()} for k, p in pr.items()},
            "confirm_namespace_absent": not C24.OUT.exists() and not any(Path("runs").glob("**/*bxyg34confirm*"))}


def custody(dest=None) -> dict:
    """Second checkpoint copy on a different PHYSICAL disk (sysfs parent of the partition) with sha256 verification and a restore test."""
    def disk(p):
        st = os.stat(p)
        real = os.path.realpath(f"/sys/dev/block/{os.major(st.st_dev)}:{os.minor(st.st_dev)}")
        return Path(real).parent.name if Path(real, "partition").exists() else Path(real).name
    repo = disk(".")
    cand = {}
    mounts = sorted({ln.split()[1] for ln in open("/proc/mounts") if ln.startswith("/dev/") and ln.split()[1].startswith(("/media", "/mnt", "/run/media"))})
    for p in [*mounts, *sorted(str(d) for d in Path("/mnt").glob("*")), *([dest] if dest else [])]:
        if os.path.exists(p):
            cand[p] = {"disk": disk(p), "independent": disk(p) != repo}
    res = {"repository_disk": repo, "candidates": cand, "lsblk_disks": sp.run(["lsblk", "-dno", "NAME,TYPE"], capture_output=True, text=True).stdout.split("\n")}
    if not dest or not cand.get(dest, {}).get("independent"):
        return res | {"status": "BLOCKED_CHECKPOINT_CUSTODY", "reason": "no physically independent volume or approved off-machine location; the P22 copy and every "
                      "mounted volume are on the repository's own disk",
                      "user_steps": ["attach an external drive (or approve an off-machine path / private storage)",
                                     "run: python3 bxy_p23_preflight.py custody <mount point of that drive>",
                                     "the step copies the 60 frozen D / E / A / G checkpoints + RESULT.json, verifies sha256, restores into a scratch "
                                     "directory and re-loads every member from the restored copy; P23 becomes READY only then"]}
    fz = json.loads((OUT / "FROZEN_MODELS_P23_APPEND.json").read_text())
    root = Path(dest) / "bxy_checkpoint_custody_p23"
    ok = {}
    for arm in ARMS:
        for m in fz["arms"][arm]["members"]:
            src = Path(m["dir"])
            dst = root / src.name
            dst.mkdir(parents=True, exist_ok=True)
            for n in ("best.pt", "RESULT.json"):
                shutil.copy2(src / n, dst / n)
                os.sync()
            ok[m["rid"]] = sha_file(dst / "best.pt") == m["checkpoint_sha256"] and sha_file(dst / "RESULT.json") == m["result_sha256"]
    restore = root.parent / "restore_test_p23"
    shutil.copytree(root, restore, dirs_exist_ok=True)
    nets = {arm: [C24.load_member(arm, dict(m, dir=str(restore / Path(m["dir"]).name))) for m in fz["arms"][arm]["members"]] for arm in ARMS}
    shutil.rmtree(restore)
    return res | {"status": "CUSTODY_OK" if all(ok.values()) else "CUSTODY_HASH_FAILURE", "copied": len(ok), "all_hashes_ok": all(ok.values()),
                  "restore_test_members_loaded": {a: len(v) for a, v in nets.items()}, "location_disk": cand[dest]["disk"]}


if __name__ == "__main__":
    for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[v] = "1"
    import torch
    torch.set_num_threads(1)                                                # contract: single-thread CPU workers
    import bxy_p23_lock as LK
    cmd = sys.argv[1]
    OUT.mkdir(parents=True, exist_ok=True)
    t0, c0, w0 = time.process_time(), os.times(), time.time()
    fn = {"start": start, "reproduce": reproduce, "checkpoints": checkpoints, "contract": contract, "synthetic": synthetic}
    if cmd in fn:
        r = fn[cmd]()
        save({"start": "START_P23.json", "reproduce": "REPRODUCTION_P21.json", "checkpoints": "CHECKPOINTS_P23.json", "contract": "INPUT_CONTRACT_P23.json",
              "synthetic": "SYNTHETIC_PIPELINE_P23.json"}[cmd], r)
    elif cmd == "freeze":
        r = {"sha256": save("FROZEN_MODELS_P23_APPEND.json", freeze(), once=True)}
    elif cmd == "lock":
        r = LK.write_all(save)
    elif cmd == "figure":
        r = {"figure": LK.figure()}
    elif cmd == "custody":
        r = custody(sys.argv[2] if len(sys.argv) > 2 else None)
        n = len(list(OUT.glob("CUSTODY_P23_attempt*.json")))
        save(f"CUSTODY_P23_attempt{n + 1}.json", r)
    c1 = os.times()
    EN.charge(OUT, f"p23_{cmd}", (c1.user - c0.user) + (c1.system - c0.system) + (c1.children_user - c0.children_user) + (c1.children_system - c0.children_system),
              time.time() - w0)
    print(json.dumps({k: v for k, v in r.items() if k not in ("rows", "test_load", "roots")} if isinstance(r, dict) else r, indent=1, default=str)[:3000])
