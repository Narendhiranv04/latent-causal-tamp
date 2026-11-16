#!/usr/bin/env python3
"""Small versioned MCTS pilot driver. Reuses RepairEnv and DISCOMCTS exclusively.

No implicit broad campaigns: immutable TRAIN family manifest, aggregate query and
wall envelopes, CPU only, one worker, gvlab allowlist. --execute runs the manifest;
without it only freezes the cohort/config. Expensive scaling is a separate gate.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as D
import env as E
import mcts as M
import policy as P


def input_hash(row):
    return hashlib.sha256(json.dumps(row["inputs"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def resources():
    mem = {x.split(":")[0]:int(x.split()[1])*1024 for x in Path("/proc/meminfo").read_text().splitlines() if x.split(":")[0] in ("MemAvailable",)}
    return {"hostname":socket.gethostname(), "load1":os.getloadavg()[0], "logical_cpus":os.cpu_count(),
            "ram_available":mem["MemAvailable"], "disk_free":shutil.disk_usage(D.DISCO_ROOT).free}


def require_headroom():
    r = resources()
    if r["hostname"] != "gvlab":
        raise RuntimeError("BLOCKED_PERMISSION: DISCO execution host allowlist is gvlab only")
    if r["load1"] > r["logical_cpus"]-3 or r["ram_available"] < 8*2**30 or r["disk_free"] < 20*2**30:
        raise RuntimeError("BLOCKED_RESOURCE: " + json.dumps(r))
    return r


def teacher_sources(dom):
    if dom == "2d":
        base=D.ABF_ROOT/"teacher2d_wt"
        mounted=D.ABF_ROOT/"mirror/rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_bd_classquota/code"
        directories=[mounted/"dataset-bd",mounted,mounted/"latent-causal-tamp",base]
        paths=[]
        for name in ("config.toml","bxy_teacher.py","bd_2d.py","p16_motion.py","p16_common.py","geometry.py","motion.py","skill.py"):
            found=[folder/name for folder in directories if (folder/name).is_file()]
            if not found: raise FileNotFoundError(f"Missing teacher source {name}")
            paths.extend(found)
    else:
        code=Path(os.environ.get("FIN3D_CODE","/home/nav/approachb_final_gen/final3d_v4/code"))
        src=Path(os.environ.get("FIN3D_SRC","/home/nav/approachb_final_gen/final3d_v4/src/dataset_bd_classquota_without_home_position_no_overpass"))
        shelf=src/"code/shelf66_v3"
        scene=(shelf/"shelf_scene_6x6").resolve()
        paths=[code/"fin3d.py",code/"bwlphys.py",shelf/"bd_shelf.py",shelf/"bd_3dt.py",
               scene/"shelf_scene.py",scene/"rrt_connect.py",scene/"rrt_star.py"]
    return {str(p):D.sha256_file(p) for p in paths}


def freeze_manifest(dom, counts, seed, calls, iterations, wall_s, out):
    if any(not isinstance(n,int) or n<=0 for n in counts.values()):
        raise ValueError("Every requested stratum must have a positive integer count")
    rows = D.load_snapshot_rows(dom)
    hygiene = D.check_split_hygiene(rows)
    if any(v for k,v in hygiene.items() if k.endswith("conflicts")):
        raise ValueError("Split overlap: " + json.dumps(hygiene))
    families_by_split = {}
    for row in rows:
        families_by_split.setdefault(D.root_family_key(row), set()).add(row["split"])
    if any(len(s)>1 for s in families_by_split.values()):
        raise ValueError("Cross-split source families")
    historic_ids = {p.name for p in (D.DISCO_ROOT/"trees"/dom).glob("*/*") if p.is_dir()}
    excluded_families = {D.root_family_key(r) for r in rows if r["root_id"] in historic_ids}
    selected, seen = [], set(excluded_families)
    for k, count in counts.items():
        candidates = [r for r in rows if r["split"] == "train" and str(r["K_legacy"]) == k]
        candidates.sort(key=lambda r: hashlib.sha256(f"validation_v2|{seed}|{r['root_id']}".encode()).hexdigest())
        stratum = []
        for row in candidates:
            family = D.root_family_key(row)
            if family not in seen:
                stratum.append({"root_id":row["root_id"], "family_id":family, "root_sha256":row["root_sha256"],
                                "input_sha256":input_hash(row), "K_legacy":k, "split":"train"})
                seen.add(family)
                if len(stratum)==count: break
        if len(stratum)!=count:
            raise ValueError(f"Insufficient independent TRAIN families for K={k}: {len(stratum)}/{count}")
        selected.extend(stratum)
    ceilings = {"2d":(8,40), "3d":(4,24)}
    max_roots,max_calls=ceilings[dom]
    if not selected or len(selected)>max_roots or not 1<=calls<=max_calls or not 1<=wall_s<=1800:
        raise ValueError("Outside authorized pilot ceilings")
    ck = D.DISCO_ROOT/f"runs/p0/{dom}/s0/model.pt"
    scalers = D.ABF_ROOT/f"data/q2_{dom}/scalers.json"
    m = {"version":2, "domain":dom, "roots":selected, "split_hygiene":hygiene,
         "excluded_historical_train_families":sorted(excluded_families), "search_seed":seed,
         "network_initialization_seed":0, "proposal_mode":"p0", "observation_schema":P.O0,
         "policy_checkpoint":str(ck), "policy_sha256":D.sha256_file(ck), "scalers":str(scalers),
         "scalers_sha256":D.sha256_file(scalers), "snapshot_lock_sha256":D.sha256_file(D.BASE_SNAP/"data_snapshot.lock.json"),
         "source_sha256":{p.name:D.sha256_file(p) for p in HERE.glob("*.py")},
         "teacher_source_sha256":teacher_sources(dom),
         "host_allowlist":["gvlab"], "workers":1, "threads":1, "gpu":False,
         "wall_envelope_s":wall_s, "aggregate_adapter_call_ceiling":len(selected)*calls,
         "per_tree":{"iterations":iterations, "max_sim_calls":calls, "expansion_budget_B":2,
                     "C":1.5,"k":2.,"alpha":.3,"max_depth":3,"reward_mode":"geometric"},
         "cancel_command":f"kill -TERM <pid recorded in {out}/pid> (cooperative iteration-boundary save)",
         "scaling_status":"NOT_AUTHORIZED beyond pilot ceilings"}
    out.mkdir(parents=True, exist_ok=True)
    path = out/"manifest.json"
    with path.open("x") as f: json.dump(m,f,indent=2)
    return m


def _execute_worker(out):
    m=json.loads((out/"manifest.json").read_text())
    for name,expected in m["source_sha256"].items():
        if D.sha256_file(HERE/name)!=expected: raise ValueError("Code changed since manifest freeze: "+name)
    for path,expected in ((Path(m["policy_checkpoint"]),m["policy_sha256"]), (Path(m["scalers"]),m["scalers_sha256"]),
                          (D.BASE_SNAP/"data_snapshot.lock.json",m["snapshot_lock_sha256"])):
        if D.sha256_file(path)!=expected: raise ValueError("Frozen input hash mismatch")
    for path,expected in m.get("teacher_source_sha256",{}).items():
        if D.sha256_file(path)!=expected: raise ValueError("Teacher source changed since freeze")
    # Resource check before loading torch/checkpoint, then again before every tree.
    require_headroom()
    os.nice(10)
    import torch
    torch.set_num_threads(1)
    model,ck=P.load_policy_checkpoint(m["policy_checkpoint"],"cpu")
    proposal=P.PolicyProposalWrapper(m["domain"],model,ck["scalers"],"cpu","p0")
    (out/"pid").write_text(str(os.getpid()))
    prior_wall = 0.0
    for checkpoint in out.glob("*/checkpoint.pkl"):
        import pickle
        with checkpoint.open("rb") as f: prior_wall += pickle.load(f).get("cumulative_wall_s",0.)
    started=time.time();remaining=m["wall_envelope_s"]-prior_wall
    results=[];cancelled=False;active=None
    def cancel(signum,frame):
        nonlocal cancelled
        cancelled=True
        if active is not None: active.cancel_requested=True
    old=signal.signal(signal.SIGTERM,cancel)
    oldint=signal.signal(signal.SIGINT,cancel)
    try:
        for root in m["roots"]:
            if cancelled: break
            r=require_headroom()
            for path,expected in m.get("teacher_source_sha256",{}).items():
                if D.sha256_file(path)!=expected: raise ValueError("Teacher source changed during cohort")
            row=next(r for r in D.load_snapshot_rows(m["domain"],"train") if r["root_id"]==root["root_id"])
            if input_hash(row)!=root["input_sha256"] or D.sha256_file(D.raw_root_path(m["domain"],root["root_id"]))!=root["root_sha256"]:
                raise ValueError("Physical root changed since manifest freeze")
            td=out/root["root_id"]
            env=E.RepairEnv(m["domain"],witness_dir=out/"witnesses")
            cfg=m["per_tree"]
            active=M.DISCOMCTS(env,proposal,seed=m["search_seed"], **{k:v for k,v in cfg.items() if k not in ("iterations","max_sim_calls")})
            if (td/"checkpoint.pkl").exists(): active.resume(td)
            remaining=m["wall_envelope_s"]-prior_wall-(time.time()-started)
            if remaining<=0: break
            import evaluate as EV
            try:
                with EV.time_limit(remaining):
                    result=active.run_search(root["root_id"],iterations=cfg["iterations"],max_sim_calls=cfg["max_sim_calls"],save_dir=td)
            except EV.QueryTimeout:
                (out/"BLOCKED_WALL_LIMIT.json").write_text(json.dumps({"root_id":root["root_id"],"in_flight":"Reconciliation required; no automatic rerun"}))
                break
            results.append({**result,"resources_before":r,"K_legacy":root["K_legacy"]})
            (out/"results.json").write_text(json.dumps(results,indent=2))
    finally:
        signal.signal(signal.SIGTERM,old);signal.signal(signal.SIGINT,oldint)
    return results


def wait_for_child(proc, seconds, grace_s=5.):
    """True if the independently bounded worker required cancellation."""
    proc.join(timeout=seconds)
    if not proc.is_alive(): return False
    proc.terminate()
    proc.join(timeout=grace_s)
    if proc.is_alive():
        proc.kill()
        proc.join()
    return True


def execute(out):
    """Independent parent watchdog; teacher SIGALRM handlers cannot extend wall cap."""
    import multiprocessing as mp
    manifest=json.loads((out/"manifest.json").read_text())
    require_headroom()
    prior_wall=0.
    for ck in out.glob("*/checkpoint.pkl"):
        import pickle
        with ck.open("rb") as f: prior_wall += pickle.load(f).get("cumulative_wall_s",0.)
    remaining=max(0.,manifest["wall_envelope_s"]-prior_wall)
    if remaining <= 0:
        raise RuntimeError("BLOCKED_WALL_LIMIT: aggregate envelope exhausted")
    proc=mp.get_context("spawn").Process(target=_execute_worker,args=(out,))
    proc.start()
    (out/"controller_pid").write_text(str(os.getpid()))
    if wait_for_child(proc, remaining):
        (out/"BLOCKED_WALL_LIMIT.json").write_text(json.dumps({
            "status":"UNRESOLVED_IN_FLIGHT", "limit_s":remaining,"grace_s":5,
            "automatic_resume":"REFUSED if IN_FLIGHT exists; reconcile uncertain calls",
            "reason":"parent watchdog independent of teacher SIGALRM"}))
    elif proc.exitcode:
        raise RuntimeError(f"Collection worker failed with exit code {proc.exitcode}; preserve artifacts")
    return json.loads((out/"results.json").read_text()) if (out/"results.json").exists() else []


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--domain",choices=["2d","3d"],required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--counts",default='{"0":1,"2":1}')
    p.add_argument("--seed",type=int,default=20261116)
    p.add_argument("--calls",type=int,default=16)
    p.add_argument("--iterations",type=int,default=12)
    p.add_argument("--wall-s",type=int,default=600)
    p.add_argument("--execute",action="store_true")
    a=p.parse_args()
    if a.out.resolve().is_relative_to(D.DISCO_ROOT.resolve()) is False:
        p.error("Output must be inside the isolated DISCO root")
    if not (a.out/"manifest.json").exists():
        freeze_manifest(a.domain,json.loads(a.counts),a.seed,a.calls,a.iterations,a.wall_s,a.out)
    if a.execute: print(json.dumps(execute(a.out),indent=2))
