#!/usr/bin/env python3
"""3D order classification of the SHELF66V3 class-quota target-task dataset (rss-ebm-infeasibility @ yadu/dataset-3d 8fe96075,
gh-yadu-iiith/shelf_6x6_open_sides/dataset_bd_classquota_without_home_position_no_overpass), laptop only.

Sequence evaluation = the body of bd_3dt.teach.seq() reproduced line for line with the module's own helpers (query: the scene's grasp poses
in order, first feasible wins, RRT seed 0, max_iters 5000, no wall clock; run_plan in MuJoCo; a step counts only if the mover ends in its
destination cell, |z_err| <= 0.01 and no other object changed cell; then T to its goal the same way).  One fresh env per root, reset ONCE to
the initial cells and ready pose (settle), robot state carried between moves (no return to ready), as the original teacher.
Modules: bd_shelf first (points bd_3dt at the vendored shelf_scene_6x6), then bd_3dt / bd_3dt_plus, unmodified.  Never writes the dataset.

  perm3d.py repro SAMPLE.json WORKERS     re-evaluate recorded B entries [[root_id, role], ...]; compare everything recorded
  perm3d.py run   ROOTS.json  WORKERS     the missing permutations of each root's minimal assignment (K2: 2, K3: 6 orders)
Outputs (append-only, resumable): out/<mode>/results.jsonl ; witnesses: out/store/witnesses (content addressed)."""
import itertools, json, os, signal, sys, time, traceback
from pathlib import Path

H = Path(__file__).resolve().parent
DS = H / "src_8fe96075/gh-yadu-iiith/shelf_6x6_open_sides/dataset_bd_classquota_without_home_position_no_overpass"
CODE = DS / "code"
OUT = H / "out"
SEQ_WALL_S = 3600          # administrative wall cap per sequence -> UNRESOLVED_ADMIN, never a label
_M = {}


class AdminWall(Exception):
    pass


def _alarm(sig, frm):
    raise AdminWall("sequence wall cap")


def boot():
    try:
        sys.path[:0] = [str(CODE / "shelf66_v3"), str(CODE), str(CODE / "dataset-bd")]
        os.environ.setdefault("MUJOCO_GL", "disable")
        import warnings
        warnings.filterwarnings("ignore")
        import bd_shelf as D                     # first: bd_3dt.env() -> the shelf scene
        import bd_3dt as A
        import bd_3dt_plus as P
        import bd_core as bc
        import numpy as np
        assert D.DOMAIN == "3ds66" and "shelf66_v3" in A.__file__ and "shelf66_v3" in P.__file__
        A.env()
        _M.update(A=A, bc=bc, np=np, store=bc.Store(OUT / "store"))
        signal.signal(signal.SIGALRM, _alarm)
    except Exception as e:  # noqa: BLE001
        _M["boot_error"] = f"{type(e).__name__}: {e} | {traceback.format_exc()[-600:]}"


def src_dir(rid, k):
    return DS / ("raw_k4_ordered" if str(k) == "4" else "raw") / "roots" / f"{rid}.json"


def record(rid):
    for sub in ("raw", "raw_k4_ordered", "raw_none"):
        p = DS / sub / "roots" / f"{rid}.json"
        if p.exists():
            return json.loads(p.read_text())
    raise FileNotFoundError(rid)


def seq(rec, steps):
    """bd_3dt.teach.seq(steps), verbatim logic, on a fresh env for this root."""
    A, bc = _M["A"], _M["bc"]
    objs, cells0, goal, store = rec["objects"], rec["initial_cells"], rec["goal"], _M["store"]
    e = A.build(objs, cells0)
    bc.check_sequence(steps)
    A.settle(e, cells0)
    info, wids = [], []
    for j, (o, d) in enumerate(list(steps) + [("t0", goal)]):
        before = {n: e.cell_of(n) for n in e.obj_index if n != o}
        p, qi = A.query(e, o, d)
        step = {"object": o, "dest": list(d), **qi}
        fail = None
        if p is None:
            fail = A.label(None, qi)
        else:
            wids.append(A.witness(store, p))
            try:
                e.run_plan(p)
            except A.env()["TS"].GraspFailed as err:
                fail = bc.binary(False, f"GRASP_FAILED:{str(err)[:80]}", "OTHER_FAILURE")
            if fail is None:
                h = next(x["height"] for x in objs if x["id"] == o)
                z = e.obj_pos(o)[2] - e.table_z - h / 2
                moved = sorted(n for n in before if e.cell_of(n) != before[n])
                step.update(pushed=p.get("pushed", []), end_cell=e.cell_of(o), z_err=float(z))
                if e.cell_of(o) != tuple(d) or abs(z) > 0.01 or moved:
                    fail = bc.binary(False, f"EXECUTION_NOT_VERIFIED:end={e.cell_of(o)} z_err={z:.3f} displaced={moved}", "OTHER_FAILURE")
        info.append({**step, "ok": fail is None})
        if fail is not None:
            return {**fail, "failed_step": j if o != "t0" else "target", "sequence": [[x, list(y)] for x, y in steps], "n_actions": len(steps) + 1,
                    "steps": info, "witnesses": wids}
    final = {n: list(e.cell_of(n)) for n in e.obj_index}
    return bc.binary(True, "executed", failed_step=None, sequence=[[x, list(y)] for x, y in steps], n_actions=len(steps) + 1, steps=info,
                     witnesses=wids, final_cells=final)


def evaluate(rec, steps):
    t0, w0 = time.process_time(), time.time()
    try:
        signal.alarm(SEQ_WALL_S)
        r = seq(rec, [(o, tuple(d)) for o, d in steps])
        signal.alarm(0)
        r["resolution"] = "EVALUATED"
    except AdminWall as e:
        r = {"y": None, "resolution": "UNRESOLVED_ADMIN", "error": str(e)}
    except Exception as e:  # noqa: BLE001
        signal.alarm(0)
        r = {"y": None, "resolution": "UNRESOLVED_ERROR", "error": f"{type(e).__name__}: {str(e)[:300]}", "trace": traceback.format_exc()[-800:]}
    r["sequence"] = [[o, list(d)] for o, d in steps]
    r["cpu_s"], r["wall_s"] = round(time.process_time() - t0, 3), round(time.time() - w0, 3)
    return json.loads(json.dumps(r, default=lambda x: x.tolist() if hasattr(x, "tolist") else list(x) if isinstance(x, tuple) else str(x)))


def norm(x):
    return json.loads(json.dumps(x, default=lambda v: v.tolist() if hasattr(v, "tolist") else str(v)))


def job_repro(item):
    rid, role = item
    if "boot_error" in _M:
        return {"root_id": rid, "role": role, "resolution": "UNRESOLVED_ERROR", "error": "boot: " + _M["boot_error"]}
    rec = record(rid)
    b = next(x for x in rec["labels"]["B"] if x["role"] == role)
    new = evaluate(rec, b["sequence"])
    keys = ("y", "reason", "failed_step", "negative_kind", "witnesses", "final_cells")
    sk = lambda s: [{k: s.get(k) for k in ("object", "dest", "ok", "end_cell", "grasp_id", "tried")} | {"z_err": round(s["z_err"], 4) if s.get("z_err") is not None else None}
                    for s in (s or [])]
    stored, fresh = norm({k: b.get(k) for k in keys}), {k: new.get(k) for k in keys}
    return {"root_id": rid, "role": role, "resolution": new["resolution"], "stored": stored, "new": fresh,
            "match": {k: stored.get(k) == fresh.get(k) for k in keys}, "steps_stored": sk(norm(b.get("steps"))), "steps_new": sk(new.get("steps")),
            "cpu_s": new["cpu_s"], "error": new.get("error")}


def job_run(rid):
    if "boot_error" in _M:
        return {"root_id": rid, "resolution": "UNRESOLVED_ERROR", "error": "boot: " + _M["boot_error"], "perms": []}
    rec = record(rid)
    B = rec["labels"]["B"]
    mini = next(b for b in B if b["role"] == "minimal" and b["y"] == 1)
    assign = [(o, tuple(d)) for o, d in mini["sequence"]]
    recd = {tuple((o, tuple(d)) for o, d in b["sequence"]): b for b in B}
    perms = []
    for p in itertools.permutations(assign):
        if p in recd:
            b = recd[p]
            perms.append({"order": [[o, list(d)] for o, d in p], "source": "historical", "role": b["role"], "y": b["y"], "reason": b["reason"],
                          "failed_step": b["failed_step"], "negative_kind": b["negative_kind"], "witnesses": b.get("witnesses"),
                          "final_cells": b.get("final_cells")})
        else:
            r = evaluate(rec, [[o, list(d)] for o, d in p])
            perms.append({"order": [[o, list(d)] for o, d in p], "source": "new", **{k: r.get(k) for k in
                          ("y", "reason", "failed_step", "negative_kind", "witnesses", "final_cells", "steps", "resolution", "error", "cpu_s", "wall_s")}})
    return {"root_id": rid, "K": rec["verified_K"], "minimal": mini["sequence"], "perms": perms, "utc": time.strftime("%FT%TZ", time.gmtime())}


def drive(mode, items, workers):
    import multiprocessing as mp
    d = OUT / mode
    d.mkdir(parents=True, exist_ok=True)
    res = d / "results.jsonl"
    key = (lambda it: json.dumps(list(it))) if mode.startswith("repro") else (lambda it: it)
    done = set()
    if res.exists():
        for l in res.read_text().splitlines():
            x = json.loads(l)
            done.add(json.dumps([x["root_id"], x["role"]]) if mode.startswith("repro") else x["root_id"])
    todo = [tuple(it) if mode.startswith("repro") else it for it in items if key(it) not in done]
    fn = job_repro if mode.startswith("repro") else job_run
    print(f"{time.strftime('%FT%TZ', time.gmtime())} {mode} items={len(todo)} workers={workers}", flush=True)
    with open(res, "a", buffering=1) as f, mp.get_context("spawn").Pool(workers, initializer=boot) as pool:
        for i, r in enumerate(pool.imap_unordered(fn, todo), 1):
            f.write(json.dumps(r) + "\n")
            f.flush()
            os.fsync(f.fileno())
            print(f"{time.strftime('%FT%TZ', time.gmtime())} {i}/{len(todo)}", flush=True)
            if (OUT / "STOP").exists():
                print("STOP file: exiting", flush=True)
                break


if __name__ == "__main__":
    assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1", "set PYTHONDONTWRITEBYTECODE=1"
    drive(sys.argv[1], json.loads(Path(sys.argv[2]).read_text()), int(sys.argv[3]))
