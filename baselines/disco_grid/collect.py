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
import journal as J


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


def freeze_manifest(dom, counts, seed, calls, iterations, wall_s, out, query_wall_s=120):
    if iterations<=0 or not 0<query_wall_s<=wall_s: raise ValueError("Invalid iteration/query wall cap")
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
    # Prior pilots are exposure, not fresh independent coverage.
    for path in (D.DISCO_ROOT/"validation_v2").glob("pilot_*/manifest.json"):
        for root in json.loads(path.read_text()).get("roots",[]):
            excluded_families.add(root["family_id"])
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
    m = {"version":3, "domain":dom, "roots":selected, "split_hygiene":hygiene,
         "excluded_historical_train_families":sorted(excluded_families), "search_seed":seed,
         "network_initialization_seed":0, "proposal_mode":"p0", "observation_schema":P.O0,
         "policy_checkpoint":str(ck), "policy_sha256":D.sha256_file(ck), "scalers":str(scalers),
         "scalers_sha256":D.sha256_file(scalers), "snapshot_lock_sha256":D.sha256_file(D.BASE_SNAP/"data_snapshot.lock.json"),
         "source_sha256":{p.name:D.sha256_file(p) for p in HERE.glob("*.py")},
         "teacher_source_sha256":teacher_sources(dom),
         "host_allowlist":["gvlab"], "workers":1, "threads":1, "gpu":False,
         "source_commit":os.environ.get("DISCO_SOURCE_COMMIT","UNRECORDED"),
         "query_wall_s":query_wall_s,
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
    os.setsid()
    J.atomic_json(out/"WORKER_IDENTITY.json",J.process_identity())
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
    prior_wall = sum(json.loads(p.read_text())["wall_s"] for p in (out/"attempts").glob("*/WATCHDOG_ACCOUNTING.json"))
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


# Kept public for existing deterministic watchdog tests.
wait_for_child=J.wait_for_child


def execute(out):
    """One externally bounded CPU worker, with aggregate attempt accounting."""
    import fcntl
    import multiprocessing as mp
    out=Path(out).resolve()
    manifest=json.loads((out/"manifest.json").read_text())
    require_headroom()
    max_roots,max_calls={"2d":(8,40),"3d":(4,24)}[manifest["domain"]]
    if (len(manifest["roots"])>max_roots or not 0<manifest["per_tree"]["max_sim_calls"]<=max_calls
        or not 0<manifest["wall_envelope_s"]<=1800 or manifest.get("workers")!=1
        or manifest.get("gpu") is not False or not 0<manifest.get("query_wall_s",0)<=manifest["wall_envelope_s"]):
        raise ValueError("Manifest violates authorized pilot envelope")
    if os.environ.get("CUDA_VISIBLE_DEVICES")!="":
        raise ValueError("CPU-only execution requires CUDA_VISIBLE_DEVICES=''")
    if list(out.rglob("IN_FLIGHT")) or list(out.rglob("ACTIVE_QUERY.json")):
        raise ValueError("Unreconciled in-flight physical work; automatic resume refused")
    attempts=out/"attempts"; attempts.mkdir(exist_ok=True)
    prior=0.
    for old in attempts.iterdir():
        if not (old/"WATCHDOG_ACCOUNTING.json").exists():
            raise ValueError("Interrupted parent has unknown wall accounting; reconcile before restart")
        prior+=json.loads((old/"WATCHDOG_ACCOUNTING.json").read_text())["wall_s"]
    remaining=manifest["wall_envelope_s"]-prior
    if remaining<=0: raise RuntimeError("BLOCKED_WALL_LIMIT: aggregate envelope exhausted")
    with (D.DISCO_ROOT/"active_physical.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        attempt=attempts/f"attempt_{len(list(attempts.iterdir())):03d}"
        attempt.mkdir()
        J.atomic_json(attempt/"START.json",{"controller":J.process_identity(),"utc_s":time.time(),"remaining_wall_s":remaining})
        proc=mp.get_context("spawn").Process(target=_execute_worker,args=(out,))
        proc.start()
        # Query journals are below out, watchdog accounting belongs to this parent attempt.
        cancelled=J.wait_for_child(proc,remaining,directory=out,query_wall_s=manifest["query_wall_s"],resource_check=require_headroom)
        os.replace(out/"WATCHDOG_ACCOUNTING.json",attempt/"WATCHDOG_ACCOUNTING.json")
        if cancelled:
            J.atomic_json(out/"BLOCKED_WALL_LIMIT.json",{
                "status":"UNRESOLVED_IN_FLIGHT" if list(out.rglob("IN_FLIGHT")) else "CANCELLED_CLEAN",
                "accounting":str(attempt/"WATCHDOG_ACCOUNTING.json"),"automatic_resume":"REFUSED if IN_FLIGHT exists"})
        elif proc.exitcode:
            raise RuntimeError(f"Collection worker exit {proc.exitcode}; preserve artifacts")
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
    p.add_argument("--query-wall-s",type=int,default=120)
    p.add_argument("--execute",action="store_true")
    a=p.parse_args()
    if a.out.resolve().is_relative_to(D.DISCO_ROOT.resolve()) is False:
        p.error("Output must be inside the isolated DISCO root")
    if not (a.out/"manifest.json").exists():
        freeze_manifest(a.domain,json.loads(a.counts),a.seed,a.calls,a.iterations,a.wall_s,a.out,a.query_wall_s)
    if a.execute: print(json.dumps(execute(a.out),indent=2))
