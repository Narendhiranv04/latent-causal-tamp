"""BXY-P24 one-shot independent K0-K4 confirmation runner (namespace bxyg34confirm). Prepared and tested in P23; NOT authorized by P23.

Every confirmation step refuses unless runs/approach_b/bxy_p24_v1/AUTHORIZATION_P24.json exists, carries the user's explicit approval, and
its hashes equal the committed P23 locks (plan, analysis, frozen models), the code tree and the teacher. Order of the one-shot protocol:
  generate   the 440 predetermined slots of CONFIRM_PLAN_P23_LOCK (P20 BXY_GEN_K34C doorway construction = REV34['k3'] for local families,
             P16 V21B for controls; new namespace seeds), every attempt recorded, no replacement of rejected slots
  freeze     outcome-blind catalogue + query design per accepted root (bxy_p20_k34.root_design), label-free DINOv2 inputs, scorer views
             with NO results, and the frozen D / E / DIRECT-GEO / G ensemble predictions + choices SEALED (sha256 in the ledger) before any
             teacher call: predictions cannot depend on labels
  collect    bxy_p23_engine.supervise with the unchanged teacher (bxy_teacher / bxy_pmin, per-query budget bd_2d.QB), labelling order fixed
             by the lock (seeded permutation), one owner, ledger accounting against the authorized ceilings
  evaluate   once: the locked bxy_p24_analysis on every accepted root; EVALUATION_P24.json is written once and never overwritten
The `synthetic` path runs generate + freeze on a separate P23 synthetic namespace (no teacher, no confirmation seed) to validate the input
contract and model loading before authorization.
    python3 bxy_p24_confirm.py preflight | generate | freeze | collect | evaluate | status"""
from __future__ import annotations

import hashlib
import json
import subprocess as sp
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np

import bxy_p23_engine as EN

OUT = Path("runs/approach_b/bxy_p24_v1")
P23 = Path("runs/approach_b/bxy_p23_v1")
NS, WAVE, GEN = "bxyg34confirm", "c34", "BXY_GEN_K34C"
LOCKS = ("CONFIRM_PLAN_P23_LOCK.json", "CONFIRM_ANALYSIS_P23_LOCK.json", "FROZEN_MODELS_P23_APPEND.json")
ARMS = ("D:XYQ-GEO-SYM", "E:XY-UNC-SA-GEO-SYM", "A:DIRECT-GEO", "G:XYQ-GEO-SYM-ORDINV")


def sha_file(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def code_tree() -> dict:
    """sha256 of every tracked top-level source file (generator, teacher, features, model, evaluator, engine) + the robot config."""
    fs = sp.run(["git", "ls-files", "*.py", "config.toml"], capture_output=True, text=True, check=True).stdout.split()
    files = {f: sha_file(f) for f in sorted(fs) if "/" not in f}
    return {"files": len(files), "sha256": EN.sha(files)}


def locks_now() -> dict:
    return {n: sha_file(P23 / n) for n in LOCKS}


def require_authorization() -> dict:
    """The user's explicit P24 approval with unchanged locks, code and teacher; anything else -> PermissionError (nothing is generated)."""
    import bxy_teacher as T
    f = OUT / "AUTHORIZATION_P24.json"
    if not f.exists():
        raise PermissionError("P24 is not authorized: AUTHORIZATION_P24.json is absent (P23 prepared only a PROPOSED manifest)")
    a = json.loads(f.read_text())
    if a.get("approved") is not True or not a.get("approved_by") or not a.get("approval_text"):
        raise PermissionError("P24 authorization lacks the user's explicit approval")
    if a["locks_sha256"] != locks_now() or a["code_tree"]["sha256"] != code_tree()["sha256"] or a["teacher_hash"] != T.teacher_hash():
        raise PermissionError("P24 authorization drift: locks, code tree or teacher changed after approval")
    return a


def plan() -> dict:
    return json.loads((P23 / "CONFIRM_PLAN_P23_LOCK.json").read_text())


def ids(slot, spec, ns=NS) -> dict:
    import bd_2d
    import bd_core as bc
    E = bd_2d.env()
    return {"root_id": f"2d-{ns}-{WAVE}-s{slot:03d}", "parent_family_id": "fam34c-" + bc.sha([GEN, ns, WAVE, slot, spec])[:10],
            "construction_seed": int(bc.sha([GEN, ns, WAVE, slot])[:8], 16), "variant_id": "orig", "generator_version": GEN,
            "namespace": "confirm" if ns == NS else "synthetic", "wave": WAVE, "config_hash": E["config_hash"], "teacher_version": bd_2d.TEACHER_VERSION,
            "robot_protocol": E["protocol"], "label_protocol": bc.LABEL_PROTOCOL}


@contextmanager
def k3_revision():
    """Construction exactly as the last development version (P20 wave k3, BXY_GEN_K34C), in memory only: bxy_p20_k34 is not edited."""
    import bxy_p20_k34 as Z
    Z.REV34[WAVE], Z.GEN_WAVE[WAVE] = Z.REV34["k3"], GEN
    try:
        yield Z
    finally:
        Z.REV34.pop(WAVE), Z.GEN_WAVE.pop(WAVE)


def _slot(args):
    import bd_2d
    out, slot, spec, ns = args
    idd = ids(slot, spec, ns)
    row = {"slot": slot, "spec": spec, "root_id": idd["root_id"], "family": idd["parent_family_id"], "seed": idd["construction_seed"]}
    t0 = time.process_time()
    with k3_revision() as Z:
        try:
            rec = Z.construct(spec, idd, Path(out))
            dd = Z.root_design(idd["root_id"], rec)
        except bd_2d.Reject as e:
            return row | {"accepted": False, "reject": str(e)[:400], "cpu_s": round(time.process_time() - t0, 3)}, None
    rec["catalogue_v21"], rec["design_v21"] = dd["catalogue"], {"queries": dd["queries"], "f1_screened": dd["f1_screened"]}
    return row | {"accepted": True, "cpu_s": round(time.process_time() - t0, 3), "candidates": len(dd["catalogue"]), "queries": len(dd["queries"]),
                  "K_cert": rec["construction"].get("K_cert")}, rec


def generate(out=OUT, ns=NS, slots=None, workers=4) -> dict:
    import multiprocessing as mp
    import bxy_p16 as G
    out = Path(out)
    if ns == NS:
        require_authorization()
        slots = plan()["slots"]
    if (out / "GENERATION.json").exists():
        raise FileExistsError("generation already done: no second cohort, no replacement wave")
    (out / "roots").mkdir(parents=True, exist_ok=True)
    w0 = time.time()
    G._load_maps()
    with mp.get_context("fork").Pool(workers) as pool:
        res = pool.map(_slot, [(str(out), s["slot"], s["spec"], ns) for s in slots], chunksize=1)
    att = []
    for row, rec in res:
        att.append(row)
        if rec is not None:
            (out / "roots" / f"{row['root_id']}.json").write_text(json.dumps(rec, indent=1, sort_keys=True))
    man = {"generator": GEN, "namespace": ns, "slots": len(slots), "attempts": att, "accepted": sum(a["accepted"] for a in att), "workers": workers,
           "construction_cpu_s": round(sum(a["cpu_s"] for a in att), 3), "wall_s": round(time.time() - w0, 1)}
    (out / "GENERATION.json").write_text(json.dumps(man, indent=1, sort_keys=True))
    EN.charge(out, "construction", man["construction_cpu_s"], man["wall_s"], f"{man['accepted']}/{len(slots)} accepted")
    return {k: v for k, v in man.items() if k != "attempts"}


def frozen_models() -> dict:
    return json.loads((P23 / "FROZEN_MODELS_P23_APPEND.json").read_text())


def load_member(arm, m):
    """One frozen checkpoint, verified by its RESULT.json sha256, run id and checkpoint sha256 (never by file name alone)."""
    import torch
    import bxy_p17 as M
    d = Path(m["dir"])
    r = json.loads((d / "RESULT.json").read_text())
    if sha_file(d / "RESULT.json") != m["result_sha256"] or r["rid"] != m["rid"] or r["spec"]["arm"] != arm:
        raise RuntimeError(f"{m['rid']}: RESULT.json identity mismatch")
    if sha_file(d / "best.pt") != m["checkpoint_sha256"] or r["files"]["best.pt"] != m["checkpoint_sha256"]:
        raise RuntimeError(f"{m['rid']}: checkpoint hash mismatch")
    net = M.build_model(arm, 0)
    net.load_state_dict(torch.load(d / "best.pt", weights_only=False))
    return net.eval()


def load_all(fz=None) -> dict:
    fz = fz or frozen_models()
    return {arm: [load_member(arm, m) for m in fz["arms"][arm]["members"]] for arm in ARMS}


def ensemble(arm, nets, sv) -> dict:
    """Mean over the arm's 15 members of p (p_succ; no-op P(Y0)), J_hat, px, py per candidate and of px / py per variable; F1 rows carry none."""
    import bxy_p11 as P
    pr = [P.predict_all(n, sv) for n in nets]
    rows = []
    for j, c in enumerate(sv["cands"]):
        r = dict(c)
        if c["admissible"]:
            for f in ("p", "J_hat", "px", "py"):
                v = [p["cands"][j].get(f) for p in pr]
                if all(x is not None for x in v):
                    r[f] = float(np.mean(v))
        rows.append(r)
    var = {f: (np.mean([p["vars"][f] for p in pr], 0).tolist() if pr[0]["vars"].get(f) is not None else None) for f in ("px", "py")}
    return {"cands": rows, "vars": var}


def view(out, k, rec, D, inp, results=None):
    """bxy_p17_data.view of one root; results=None -> the label-free prediction-time view (no result file is read at all)."""
    import bxy_p17_data as DATA
    from bxy_p14_run import _swap
    with _swap(DATA, "_results", lambda _rdir: dict(results or {})):
        return DATA.view("CONFIRM", WAVE, k, rec, D["roots"][k], Path(out) / "results" / k, inp)


def freeze(out=OUT, synthetic=False) -> dict:
    import bd_core as bc
    import bxy_p11 as P
    import bxy_p16_inputs as I
    import torch
    torch.set_num_threads(1)                                              # single-thread CPU work (contract)
    out = Path(out)
    auth = None if synthetic else require_authorization()
    if (out / "DESIGN.json").exists() or (out / "results").exists():
        raise FileExistsError("design already frozen or results exist: the catalogue is frozen exactly once, before any teacher call")
    t0, w0 = time.process_time(), time.time()
    R = {p.stem: json.loads(p.read_text()) for p in sorted((out / "roots").glob("*.json"))}
    order = sorted(R, key=lambda k: hashlib.sha256(f"{NS}|label-order|{k}".encode()).hexdigest())
    D = {"version": "BXY_P24_DESIGN_V1", "namespace": R[order[0]]["ids"]["namespace"] if R else None, "root_order": order,
         "roots": {k: {"record_sha256": bc.sha(r), "catalogue": r["catalogue_v21"], "queries": r["design_v21"]["queries"]} for k, r in R.items()}}
    (out / "DESIGN.json").write_text(json.dumps(D, indent=1, sort_keys=True))
    inp = {k: I.inputs(k, r) for k, r in R.items()}
    torch.save({"version": "BXY_P16_INPUTS_V1", "identity": I.identity(), "roots": inp}, out / "INPUTS_P24.pt")
    fz = frozen_models()
    nets = load_all(fz)
    preds = {}
    for k in order:
        sv, _, _ = view(out, k, R[k], D, inp[k])
        preds[k] = {}
        for arm in ARMS:
            e = ensemble(arm, nets[arm], sv)
            e["chosen"] = P.choose(e["cands"], fz["arms"][arm]["rule"])
            preds[k][arm] = e
    (out / "PREDICTIONS_P24.json").write_text(json.dumps(preds, sort_keys=True))
    seal = {"predictions_sha256": sha_file(out / "PREDICTIONS_P24.json"), "design_sha256": sha_file(out / "DESIGN.json"),
            "inputs_sha256": sha_file(out / "INPUTS_P24.pt"), "frozen_models_sha256": sha_file(P23 / "FROZEN_MODELS_P23_APPEND.json"),
            "authorization_sha256": sha_file(out / "AUTHORIZATION_P24.json") if auth else None, "roots": len(order)}
    EN.jw(out / "SEAL_P24.json", seal)
    EN.append(out, {"event": "seal", **seal})
    EN.charge(out, "freeze_inputs_predictions", time.process_time() - t0, time.time() - w0, f"{len(order)} roots")
    return seal


def collect(out=OUT) -> dict:
    import bd_2d
    import bxy_pmin_collect as PC
    a = require_authorization()
    seal = json.loads((out / "SEAL_P24.json").read_text())
    if seal["predictions_sha256"] != sha_file(out / "PREDICTIONS_P24.json") or seal["design_sha256"] != sha_file(out / "DESIGN.json"):
        raise PermissionError("sealed predictions or design changed")
    if bd_2d.QB != PC.QB:
        raise PermissionError("per-query teacher budget differs from P-min")
    L = a["limits"]
    sp_ = EN.spent(out)["cpu_s"]
    pre_wall = sum(e["wall_s"] for e in EN.ledger(out) if e["event"] == "charge")          # construction + freeze count against the same wall cap
    lim = {"cpu_s": L["aggregate_cpu_s"] - L["evaluation_reserve_cpu_s"], "root_cpu_s": L["per_root_cpu_s"], "workers": L["workers"],
           "wall_s": L["wall_s"] - pre_wall, "min_allow": 30.0}
    if sp_ >= lim["cpu_s"]:
        raise PermissionError("labelling budget already spent")
    return EN.supervise(out, lim, teacher="bxy", manifest_sha=sha_file(out / "AUTHORIZATION_P24.json"))


def evaluate(out=OUT) -> dict:
    import bxy_p24_analysis as AN
    require_authorization()
    out = Path(out)
    if (out / "EVALUATION_P24.json").exists():
        raise FileExistsError("the one-shot evaluation already exists")
    if list((out / "reservations").glob("*.json")) or json.loads((out / "SUPERVISOR.json").read_text())["state"] == "RUNNING":
        raise PermissionError("collection still owned / running")
    t0, w0 = time.process_time(), time.time()
    D = EN.design(out)
    rows = EN.rows(out, D)
    preds = json.loads((out / "PREDICTIONS_P24.json").read_text())
    import torch
    inp = torch.load(out / "INPUTS_P24.pt", weights_only=False)["roots"]
    fz = frozen_models()
    Rs = []
    for k in D["root_order"]:
        rec = json.loads((out / "roots" / f"{k}.json").read_text())
        res = {r["design_key"]: r for (kk, _, _), r in rows.items() if kk == k and r["status"] in ("OBSERVED", "CENSORED")}
        sv, lab, ev = view(out, k, rec, D, inp[k], res)
        Rs.append({"key": k, "family": rec["ids"]["parent_family_id"], "sv": sv, "lab": lab, "ev": ev, "rec": rec, "preds": preds[k]})
    res = AN.evaluate(Rs, {a: fz["arms"][a]["rule"] for a in ARMS})
    res["engine_audit"] = EN.audit(out)
    res["status_counts"] = res["engine_audit"]["status"]
    EN.write_once(out / "EVALUATION_P24.json", res)
    EN.charge(out, "evaluation", time.process_time() - t0, time.time() - w0, "one-shot")
    return {k: res[k] for k in ("populations", "primary")}


if __name__ == "__main__":
    import os
    for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[v] = "1"
    cmd = sys.argv[1]
    if cmd == "preflight":
        print(json.dumps(require_authorization(), indent=1))
    elif cmd in ("generate", "freeze", "collect", "evaluate"):
        print(json.dumps({"generate": generate, "freeze": freeze, "collect": collect, "evaluate": evaluate}[cmd](), indent=1, default=str))
    elif cmd == "status":
        print(json.dumps(EN.audit(OUT), indent=1))
