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
    host=execution_host()
    if r["hostname"] != host['hostname']:
        raise RuntimeError("BLOCKED_PERMISSION: actual host differs from explicit execution authorization")
    record_path=os.environ.get('DISCO_EXECUTION_AUTHORIZATION')
    record=json.loads(Path(record_path).read_text()) if record_path else {}
    reserve=2 if record.get('scope')=='DISCO_RELEASE_RESERVED_CORES_AMENDMENT' else 3
    if record.get('scope')==FINAL_SCALE_SCOPE:
        reserve=int(record['hosts'][r["hostname"]]['reserve'])
    if r["load1"] > r["logical_cpus"]-reserve or r["ram_available"] < 8*2**30 or r["disk_free"] < 20*2**30:
        raise RuntimeError("BLOCKED_RESOURCE: " + json.dumps(r))
    return r


def execution_host(requested=None):
    """An explicit host amendment changes placement, never resource limits.

    The historical gvlab default supports preserved releases. A continuation
    supplies the recorded user amendment, whose single host supersedes it.
    """
    path=os.environ.get('DISCO_EXECUTION_AUTHORIZATION')
    if path and json.loads(Path(path).read_text()).get('scope')==FINAL_SCALE_SCOPE:
        record=json.loads(Path(path).read_text())
        if (record.get('status')!='APPROVED' or not record.get('authorization_text') or record.get('gpu') is not False
                or record.get('cpu_threads')!=1 or socket.gethostname() not in record.get('hosts',{})):
            raise RuntimeError('BLOCKED_PERMISSION: invalid final-scale authorization or host')
        host=dict(alias=record['hosts'][socket.gethostname()]['alias'],hostname=socket.gethostname())
        if requested is not None and requested!=host['alias']:
            raise RuntimeError('BLOCKED_PERMISSION: requested host differs from recorded authorization')
        return host
    if path:
        record=json.loads(Path(path).read_text())
        parallel=record.get('scope')=='DISCO_RELEASE_PARALLEL_HOST_AMENDMENT'
        reserved=record.get('scope')=='DISCO_RELEASE_RESERVED_CORES_AMENDMENT'
        valid_workers=(type(record.get('workers')) is int and 3<=record['workers']<=4) if reserved else record.get('workers')==(3 if parallel else 1)
        if (record.get('status')!='APPROVED' or record.get('scope') not in ('DISCO_RELEASE_HOST_AMENDMENT','DISCO_RELEASE_PARALLEL_HOST_AMENDMENT','DISCO_RELEASE_RESERVED_CORES_AMENDMENT')
                or not record.get('authorization_text') or not valid_workers
                or record.get('gpu') is not False or record.get('cpu_threads')!=1):
            raise RuntimeError('BLOCKED_PERMISSION: invalid execution host amendment')
        if reserved:
            excluded=record.get('reserved_logical_cpus',[])
            if record.get('reserved_physical_cores')!=2 or len(excluded)<2 or len(set(excluded))!=len(excluded):
                raise RuntimeError('BLOCKED_PERMISSION: two complete physical cores must be reserved')
            if set(os.sched_getaffinity(0)) & set(excluded):
                raise RuntimeError('BLOCKED_PERMISSION: reserved CPUs present in DISCO affinity')
            cores=set()
            for cpu in excluded:
                topology=Path(f'/sys/devices/system/cpu/cpu{cpu}/topology')
                siblings=(topology/'thread_siblings_list').read_text().strip()
                ids=set()
                for span in siblings.split(','):
                    ends=list(map(int,span.split('-')));ids.update(range(ends[0],ends[-1]+1))
                if not ids<=set(excluded):raise RuntimeError('BLOCKED_PERMISSION: partial physical core reservation')
                cores.add(((topology/'physical_package_id').read_text(),(topology/'core_id').read_text()))
            if len(cores)!=2:raise RuntimeError('BLOCKED_PERMISSION: reserve exactly two physical cores')
        host=dict(alias=record.get('host'),hostname=record.get('hostname'))
        supported=[{'alias':'girish-laptop','hostname':'gvcstar'}]
        if parallel:supported.append({'alias':'user-laptop','hostname':'pop-os'})
        if host not in supported:
            raise RuntimeError('BLOCKED_PERMISSION: unsupported amended execution host')
    else:
        host=dict(alias='gvlab',hostname='gvlab')
    if requested is not None and requested!=host['alias']:
        raise RuntimeError('BLOCKED_PERMISSION: requested host differs from recorded authorization')
    return host


FINAL_SCALE_SCOPE='DISCO_FINAL_SCALE_AMENDMENT'


def _final_scale():
    path=os.environ.get('DISCO_EXECUTION_AUTHORIZATION')
    return bool(path) and json.loads(Path(path).read_text()).get('scope')==FINAL_SCALE_SCOPE


def _final_scale_runtime_check(manifest):
    """In-flight check for the parallel final-scale campaign: per-host reserve is enforced at ADMISSION (scale.py); while a tree runs
    only real exhaustion aborts it (RAM < 4 GiB, disk < 20 GiB, load beyond 1.5x logical CPUs).  Parallel sibling trees raising load1
    must not kill each other (measured failure mode of the single-worker check under parallel execution)."""
    r=resources()
    if r["ram_available"]<4*2**30 or r["disk_free"]<20*2**30 or r["load1"]>1.5*r["logical_cpus"]:
        raise RuntimeError("BLOCKED_RESOURCE: "+json.dumps(r))
    return r


def execution_workers():
    execution_host()
    path=os.environ.get('DISCO_EXECUTION_AUTHORIZATION')
    return json.loads(Path(path).read_text())['workers'] if path else 1


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
    groups=D.independence_groups(rows)
    hygiene = D.check_split_hygiene(rows)
    if any(v for k,v in hygiene.items() if k.endswith("conflicts")):
        raise ValueError("Split overlap: " + json.dumps(hygiene))
    families_by_split = {}
    for row in rows:
        families_by_split.setdefault(D.root_family_key(row), set()).add(row["split"])
    if any(len(s)>1 for s in families_by_split.values()):
        raise ValueError("Cross-split source families")
    historic_ids = {p.name for p in (D.DISCO_ROOT/"trees"/dom).glob("*/*") if p.is_dir()}
    for path in (D.DISCO_ROOT/"stage2/trees").glob("*/manifest.json"):
        historic_ids.update(r["root_id"] for r in json.loads(path.read_text()).get("roots",[]))
    excluded_families = {groups[r["root_id"]] for r in rows if r["root_id"] in historic_ids}
    # Prior pilots are exposure, not fresh independent coverage.
    for path in (D.DISCO_ROOT/"validation_v2").glob("pilot_*/manifest.json"):
        for root in json.loads(path.read_text()).get("roots",[]):
            if root["root_id"] in groups:excluded_families.add(groups[root["root_id"]])
    selected, seen = [], set(excluded_families)
    for k, count in counts.items():
        candidates = [r for r in rows if r["split"] == "train" and str(r["K_legacy"]) == k]
        candidates.sort(key=lambda r: hashlib.sha256(f"validation_v2|{seed}|{r['root_id']}".encode()).hexdigest())
        stratum = []
        for row in candidates:
            family = groups[row["root_id"]]
            if family not in seen:
                stratum.append({"root_id":row["root_id"], "family_id":family, "legacy_family_id":D.root_family_key(row), "root_sha256":row["root_sha256"],
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
         "runtime_versions":{n:__import__("importlib.metadata",fromlist=["version"]).version(n) for n in ("torch","numpy","mujoco")},
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


def _execute_worker(out, controller_pid=None):
    if controller_pid is not None:J.die_with_parent(controller_pid)
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
    model,ck=P.load_policy_checkpoint(m["policy_checkpoint"],"cpu",observation_schema=m["observation_schema"])
    value=None
    if m.get("value_checkpoint"):
        import distill as DS
        if D.sha256_file(m["value_checkpoint"])!=m["value_sha256"]:raise ValueError("Frozen value checkpoint changed")
        value,vck=DS.load_value_checkpoint(m["value_checkpoint"],"cpu")
    proposal=P.PolicyProposalWrapper(m["domain"],model,ck["scalers"],"cpu",m.get("proposal_mode","p0"),value)
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


def manifest_headroom(manifest):
    r=require_headroom()
    if manifest.get("disk_budget_root"):
        size=sum(p.stat().st_size for p in Path(manifest["disk_budget_root"]).rglob("*") if p.is_file())
        if size>manifest["disk_budget_bytes"]:raise RuntimeError("CAMPAIGN_DISK_LIMIT")
    return r


def execute(out):
    """One externally bounded CPU worker, with aggregate attempt accounting."""
    import fcntl
    import multiprocessing as mp
    out=Path(out).resolve()
    manifest=json.loads((out/"manifest.json").read_text())
    require_headroom()
    max_roots,max_calls={"2d":(8,40),"3d":(4,24)}[manifest["domain"]]
    final_scale=_final_scale()
    if final_scale:                  # explicitly authorized scaled TRAIN campaign: one root per tree job, larger per-tree caps
        max_roots,max_calls={"2d":(1,64),"3d":(1,32)}[manifest["domain"]]
    if (len(manifest["roots"])>max_roots or not 0<manifest["per_tree"]["max_sim_calls"]<=max_calls
        or not 0<manifest["wall_envelope_s"]<=(3600 if final_scale else 1800) or manifest.get("workers")!=1
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
    slot=os.environ.get("DISCO_WORKER_SLOT") if final_scale else None   # one physical child per worker slot (final-scale scope only)
    with (D.DISCO_ROOT/(f"active_physical.{slot}.lock" if slot else "active_physical.lock")).open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        attempt=attempts/f"attempt_{len(list(attempts.iterdir())):03d}"
        attempt.mkdir()
        J.atomic_json(attempt/"START.json",{"controller":J.process_identity(),"utc_s":time.time(),"monotonic_start":time.monotonic(),"remaining_wall_s":remaining})
        proc=mp.get_context("spawn").Process(target=_execute_worker,args=(out,os.getpid()))
        proc.start()
        # Query journals are below out, watchdog accounting belongs to this parent attempt.
        check=(lambda:_final_scale_runtime_check(manifest)) if final_scale else (lambda:manifest_headroom(manifest))
        cancelled=J.wait_for_child(proc,remaining,directory=out,query_wall_s=manifest["query_wall_s"],resource_check=check,cpu_seconds=manifest.get("cpu_envelope_s"),rss_limit_kib=manifest.get("rss_limit_kib"))
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
