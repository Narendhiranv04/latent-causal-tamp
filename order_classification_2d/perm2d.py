#!/usr/bin/env python3
"""Order classification of the 2D class-quota target-task dataset (rss-ebm-infeasibility @ yadu/dataset-3d,
gh-yadu-iiith/planar_2d/dataset_bd_classquota).  Evaluates ordered relocation sequences with the ORIGINAL pinned teacher, exactly as
bd_2d.teach.seq() does: bc.check_sequence -> p16_common.verify_sequence(bd_2d._phys(task, cache), steps) -> bd_2d.label, one fresh QB
budget per sequence, per-root exact shared cache, task key = root_id (per-query planner seeds derive from it), the scene's own geometry
implementation (fastgeom1 iff the record says so).  Carried robot state between moves; T from the achieved state (legacy convention).

Never writes the dataset.  Sidecar: out/store/witnesses (content-addressed), out/<mode>/*.jsonl (append-only, resumable).

  perm2d.py repro  SAMPLE.json  [--workers N]     re-evaluate recorded B entries; compare status / failed_step / witness ids
  perm2d.py run    ROOTS.json   [--workers N]     evaluate the missing permutations of each root's minimal assignment
"""
import argparse, itertools, json, os, signal, sys, time, traceback
from pathlib import Path

DS = Path("/home/naren/Desktop/rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_bd_classquota")
CODE = DS / "code"
OUT = Path(__file__).resolve().parent / "out"
SEQ_WALL_S = 1800          # administrative wall cap per sequence: a hit is UNRESOLVED_ADMIN, never a label
_M = {}


class AdminWall(Exception):
    pass


def _alarm(sig, frm):
    raise AdminWall("sequence wall cap")


def boot(geom):
    try:
        _boot(geom)
    except Exception as e:  # noqa: BLE001  (reported per job; never a respawn loop)
        _M["boot_error"] = f"{type(e).__name__}: {e}"


def _boot(geom):
    shim = [str(CODE / "py310_shim")] if sys.version_info < (3, 11) else []   # tomllib shim only where stdlib lacks it (runner env)
    sys.path[:0] = shim + [str(CODE / "dataset-bd"), str(CODE), str(CODE / "latent-causal-tamp")]
    os.chdir(CODE / "latent-causal-tamp")                       # config.toml, as the original runner
    import warnings
    warnings.filterwarnings("ignore")
    if geom == "fastgeom1":
        import fastgeom
        fastgeom.install()
    import numpy as np
    import bd_2d as A
    import bd_core as bc
    import p16_common as pc
    _M.update(A=A, bc=bc, pc=pc, np=np, geom=geom, store=bc.Store(OUT / "store"))
    signal.signal(signal.SIGALRM, _alarm)


def record(rid):
    return json.loads((DS / "raw/roots" / f"{rid}.json").read_text())


def task_of(rec):
    return {"scene": rec["scene"], "goal_cell": rec["goal_cell"], "fixed_ids": rec["fixed_ids"], "target": "t0", "key": rec["ids"]["root_id"]}


def evaluate(task, cache, steps):
    """One ordered sequence, exactly bd_2d.teach.seq() minus its root-level admin cap; infra problems are UNRESOLVED, never labels."""
    A, bc, pc, np, store = _M["A"], _M["bc"], _M["pc"], _M["np"], _M["store"]
    t0, w0 = time.process_time(), time.time()
    try:
        bc.check_sequence(steps)
        signal.alarm(SEQ_WALL_S)
        r = pc.verify_sequence(A._phys(task, cache), [(o, d) for o, d in steps])
        signal.alarm(0)
        wids = [store.witness({k: np.asarray(v) for k, v in rec.items()}) for rec in r["plan"]["records"]] if r["plan"] else []
        lab = A.label(r["status"], failed_step=r["failed_step"], sequence=[[o, int(d)] for o, d in steps], n_actions=len(steps) + 1,
                      travel=r["plan"]["travel"] if r["plan"] else None, witnesses=wids)
        lab["resolution"] = "EVALUATED"
    except AdminWall as e:
        lab = {"y": None, "resolution": "UNRESOLVED_ADMIN", "error": str(e), "sequence": [[o, int(d)] for o, d in steps]}
    except Exception as e:  # noqa: BLE001
        signal.alarm(0)
        lab = {"y": None, "resolution": "UNRESOLVED_ERROR", "error": f"{type(e).__name__}: {str(e)[:300]}", "trace": traceback.format_exc()[-800:],
               "sequence": [[o, int(d)] for o, d in steps]}
    lab["cpu_s"], lab["wall_s"] = round(time.process_time() - t0, 3), round(time.time() - w0, 3)
    return lab


def job_repro(item):
    rid, role = item
    if "boot_error" in _M:
        return {"root_id": rid, "role": role, "resolution": "UNRESOLVED_ERROR", "error": "boot: " + _M["boot_error"]}
    rec = record(rid)
    b = next(x for x in rec["labels"]["B"] if x["role"] == role)
    new = evaluate(task_of(rec), {}, [tuple(s) for s in b["sequence"]])
    keys = ("y", "reason", "failed_step", "negative_kind", "witnesses")
    return {"root_id": rid, "role": role, "geom": _M["geom"], "stored": {k: b.get(k) for k in keys}, "new": {k: new.get(k) for k in keys},
            "resolution": new["resolution"], "match": {k: b.get(k) == new.get(k) for k in keys}, "cpu_s": new["cpu_s"], "error": new.get("error")}


def job_run(rid):
    if "boot_error" in _M:
        return {"root_id": rid, "resolution": "UNRESOLVED_ERROR", "error": "boot: " + _M["boot_error"], "perms": []}
    rec = record(rid)
    B = rec["labels"]["B"]
    mini = next(b for b in B if b["role"] == "minimal" and b["y"] == 1)
    assign = [tuple(s) for s in mini["sequence"]]
    recorded = {tuple(tuple(s) for s in b["sequence"]): b for b in B}
    task, cache, perms = task_of(rec), {}, []
    for p in itertools.permutations(assign):
        if p in recorded:
            b = recorded[p]
            perms.append({"order": [list(s) for s in p], "source": "historical", "role": b["role"], "y": b["y"], "reason": b["reason"],
                          "failed_step": b["failed_step"], "negative_kind": b["negative_kind"], "witnesses": b["witnesses"]})
        else:
            r = evaluate(task, cache, list(p))
            perms.append({"order": [list(s) for s in p], "source": "new", **{k: r.get(k) for k in
                          ("y", "reason", "failed_step", "negative_kind", "witnesses", "resolution", "error", "cpu_s", "wall_s")}})
    return {"root_id": rid, "geom": _M["geom"], "minimal": mini["sequence"], "assignment": sorted([list(s) for s in assign]), "perms": perms,
            "utc": time.strftime("%FT%TZ", time.gmtime())}


def drive(mode, items, workers):
    import multiprocessing as mp
    d = OUT / mode
    d.mkdir(parents=True, exist_ok=True)
    res = d / "results.jsonl"
    done = set()
    if res.exists():
        for l in res.read_text().splitlines():
            x = json.loads(l)
            done.add(json.dumps([x["root_id"], x.get("role")]) if mode == "repro" else x["root_id"])
    by_geom = {}
    for it in items:
        rid = it[0] if mode == "repro" else it
        key = json.dumps([rid, it[1]]) if mode == "repro" else rid
        if key in done:
            continue
        by_geom.setdefault(record(rid).get("geometry_impl") or "original", []).append(tuple(it) if mode == "repro" else it)
    fn = job_repro if mode == "repro" else job_run
    with open(res, "a", buffering=1) as f:
        for geom, its in sorted(by_geom.items()):
            print(f"{time.strftime('%FT%TZ', time.gmtime())} {mode} geom={geom} items={len(its)} workers={workers}", flush=True)
            with mp.get_context("spawn").Pool(workers, initializer=boot, initargs=(geom,)) as pool:
                for i, r in enumerate(pool.imap_unordered(fn, its), 1):
                    f.write(json.dumps(r) + "\n")
                    f.flush()
                    os.fsync(f.fileno())
                    if i % 10 == 0 or i == len(its):
                        print(f"{time.strftime('%FT%TZ', time.gmtime())} {geom} {i}/{len(its)}", flush=True)
                    if (OUT / "STOP").exists():
                        break                                   # pool terminated on exit; finished roots are kept, in-flight ones re-run
            if (OUT / "STOP").exists():
                print("STOP file: exiting after this geometry group", flush=True)
                break


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["repro", "run"])
    ap.add_argument("items")
    ap.add_argument("--workers", type=int, default=1)
    a = ap.parse_args()
    drive(a.mode, json.loads(Path(a.items).read_text()), a.workers)
