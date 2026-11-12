#!/usr/bin/env python3
"""FINAL 3D V4 worker (laptop only).  Published source: rss-ebm-infeasibility @ yadu/dataset-3d fb1120a30 (extracted read-only).

  fin3d.py MODE ITEMS.json OUT.jsonl WORKERS

MODE legacy : item {"key", "path", "orders": [[[obj, [r, c]], ...], ...]}
              each order = perm3d.seq (bd_3dt.teach.seq verbatim) in a FRESH env: relocations with carried arm state, then T to its goal
              from the achieved pose (the legacy full-task label).
MODE fixed  : item {"key", "path"}  -> none_dense.pickable_alone (the published no-fixed-object rule) for every non-target object,
              alone on the empty shelf under the scene's own arm ceiling.
MODE xy     : item {"key", "path", "x_orders": [...], "y": {"cells": {obj: [r, c]}} | null}
              X = the order's relocations exactly as perm3d.seq executes them (fresh env, same checks) WITHOUT the target step, then
                  bwlphys.connector (CONNECTOR_TO_QREADY_V1) back to q_ref = q_ready.
              Y = BD3DS66_Y_PLAN_V1: settle the endpoint scene (cells) at q_ref, bd_3dt.query(t0 -> goal), execute with seq's target checks.
              Plans of X relocations, connector paths and Y target plans are stored as content-addressed witnesses.
Every sequence has an administrative wall cap (3600 s) -> UNRESOLVED_ADMIN (MISSING, never a label).  Planner-budget failure = 0.
Outputs append-only (fsync), resumable by key; STOP file next to OUT stops cleanly; thermal pause on k10temp (never a label)."""
import json, os, signal, sys, time, traceback
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import perm3d as Q  # noqa: E402

SRC = Path(os.environ.get("FIN3D_SRC", "/home/naren/Desktop/rss3d_final_src/gh-yadu-iiith/shelf_6x6_open_sides/"
                          "dataset_bd_classquota_without_home_position_no_overpass"))
STORE = Path(os.environ.get("FIN3D_STORE", str(H.parent / "work/store")))
WALL = 3600
PAUSE_C, RESUME_C = (float(x) for x in os.environ.get("FIN3D_TEMPS", "96,92").split(","))
M = {}


class AdminWall(Exception):
    pass


def _alarm(sig, frm):
    raise AdminWall("sequence wall cap")


def temp():
    for d in Path("/sys/class/hwmon").glob("hwmon*"):
        try:
            if (d / "name").read_text().strip() == "k10temp":
                return int((d / "temp1_input").read_text()) / 1000
        except OSError:
            pass
    return None


def guard():
    t = temp()
    if t is not None and t >= PAUSE_C:
        while (t := temp()) is not None and t > RESUME_C:
            time.sleep(20)


def boot():
    Q.DS, Q.CODE, Q.OUT = SRC, SRC / "code", STORE.parent
    Q.boot()
    if "boot_error" in Q._M:
        return
    Q._M["store"] = Q._M["bc"].Store(STORE)
    sys.path.insert(0, str(SRC / "code" / "shelf66_v3"))
    import none_dense as ND
    import bwlphys as BP
    M.update(ND=ND, BP=BP)
    signal.signal(signal.SIGALRM, _alarm)


def jd(x):
    return json.loads(json.dumps(x, default=lambda v: v.tolist() if hasattr(v, "tolist") else list(v) if isinstance(v, tuple) else str(v)))


def capped(fn, *a):
    t0, w0 = time.process_time(), time.time()
    try:
        signal.alarm(WALL)
        r = fn(*a)
        signal.alarm(0)
        r["resolution"] = "EVALUATED"
    except AdminWall as e:
        r = {"resolution": "UNRESOLVED_ADMIN", "error": str(e)}
    except Exception as e:  # noqa: BLE001
        signal.alarm(0)
        r = {"resolution": "UNRESOLVED_ERROR", "error": f"{type(e).__name__}: {str(e)[:300]}", "trace": traceback.format_exc()[-800:]}
    r["cpu_s"], r["wall_s"] = round(time.process_time() - t0, 2), round(time.time() - w0, 2)
    return jd(r)


def legacy_one(rec, order):
    r = Q.seq(rec, [(o, tuple(d)) for o, d in order])
    keep = ("y", "reason", "failed_step", "negative_kind", "witnesses", "final_cells")
    return {**{k: r.get(k) for k in keep}, "steps": [{k: s.get(k) for k in ("object", "dest", "ok", "end_cell", "grasp_id", "tried")}
                                                    for s in (r.get("steps") or [])]}


def run_x(rec, order):
    A, BP, store = Q._M["A"], M["BP"], Q._M["store"]
    S = A.env()["TS"]
    objs, cells0 = rec["objects"], rec["initial_cells"]
    steps = [(o, tuple(d)) for o, d in order]
    e = A.build(objs, cells0)
    Q._M["bc"].check_sequence(steps)
    A.settle(e, cells0)
    wids = []
    for j, (o, d) in enumerate(steps):
        before = {n: e.cell_of(n) for n in e.obj_index if n != o}
        p, qi = A.query(e, o, d)
        if p is None:
            return {"x": 0, "phase": f"relocation:{j}", "status": A.label(None, qi).get("reason"), "witnesses": wids}
        wids.append(A.witness(store, p))
        try:
            e.run_plan(p)
        except S.GraspFailed as err:
            return {"x": 0, "phase": f"relocation:{j}", "status": f"GRASP_FAILED:{str(err)[:60]}", "witnesses": wids}
        h = next(x["height"] for x in objs if x["id"] == o)
        z = e.obj_pos(o)[2] - e.table_z - h / 2
        if e.cell_of(o) != tuple(d) or abs(z) > 0.01 or any(e.cell_of(n) != before[n] for n in before):
            return {"x": 0, "phase": f"relocation:{j}", "status": "EXECUTION_NOT_VERIFIED", "witnesses": wids}
    expected = {**{k: tuple(v) for k, v in cells0.items()}, **dict(steps)}
    c, path = BP.connector(e, S, expected)
    if path is not None:
        wids.append(store.witness({"connector_q": path}))
    return {"x": int(bool(c["ok"])), "phase": None if c["ok"] else "connector", "status": c.get("failure") or "VERIFIED",
            "dq_ready": c.get("dq_ready"), "witnesses": wids}


def run_y(rec, cells):
    A, store = Q._M["A"], Q._M["store"]
    S = A.env()["TS"]
    objs = rec["objects"]
    cells = {k: tuple(v) for k, v in cells.items()}
    e = A.build(objs, rec["initial_cells"])
    A.settle(e, cells)
    p, qi = A.query(e, "t0", tuple(rec["goal"]))
    if p is None:
        return {"y": 0, "status": A.label(None, qi).get("reason"), "witnesses": []}
    w = A.witness(store, p)
    before = {n: e.cell_of(n) for n in e.obj_index if n != "t0"}
    try:
        e.run_plan(p)
    except S.GraspFailed as err:
        return {"y": 0, "status": f"GRASP_FAILED:{str(err)[:60]}", "witnesses": [w]}
    h = next(x["height"] for x in objs if x["id"] == "t0")
    z = e.obj_pos("t0")[2] - e.table_z - h / 2
    ok = e.cell_of("t0") == tuple(rec["goal"]) and abs(z) <= 0.01 and all(e.cell_of(n) == before[n] for n in before)
    return {"y": int(ok), "status": "VERIFIED" if ok else "EXECUTION_NOT_VERIFIED", "witnesses": [w]}


def fixed_one(rec):
    A, ND = Q._M["A"], M["ND"]
    ceil_h = max(o["height"] for o in rec["objects"])
    res = {}
    for o in rec["objects"]:
        if o["id"] != "t0":
            res[o["id"]] = bool(ND.pickable_alone(A, o, tuple(rec["initial_cells"][o["id"]]), ceil_h))
    return {"pickable": res, "fixed_objects": sorted(k for k, v in res.items() if not v)}


def job(item):
    mode = item["mode"]
    out = {"key": item["key"], "mode": mode}
    if "boot_error" in Q._M:
        return {**out, "error": "boot: " + Q._M["boot_error"]}
    guard()
    rec = json.loads(Path(item["path"]).read_text())
    out["root_id"] = rec["ids"]["root_id"]
    if mode == "legacy":
        out["orders"] = [{"order": o, **capped(legacy_one, rec, o)} for o in item["orders"]]
    elif mode == "fixed":
        out.update(capped(fixed_one, rec))
    elif mode == "xy":
        out["x"] = [{"order": o, **capped(run_x, rec, o)} for o in item.get("x_orders", [])]
        if item.get("y"):
            out["y"] = {"cells": item["y"]["cells"], **capped(run_y, rec, item["y"]["cells"])}
    return out


if __name__ == "__main__":
    import multiprocessing as mp
    assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
    mode, items, outp, workers = sys.argv[1], json.loads(Path(sys.argv[2]).read_text()), Path(sys.argv[3]), int(sys.argv[4])
    a, b = map(int, os.environ.get("FIN3D_CPUS", f"0-{workers - 1}").split("-"))
    os.sched_setaffinity(0, set(range(a, b + 1)))
    done = {json.loads(l)["key"] for l in outp.read_text().splitlines() if l.strip()} if outp.exists() else set()
    todo = [{**it, "mode": mode} for it in items if it["key"] not in done]
    print(f"{time.strftime('%FT%TZ', time.gmtime())} fin3d {mode} items={len(todo)} workers={workers}", flush=True)
    with open(outp, "a", buffering=1) as f, mp.get_context("spawn").Pool(workers, initializer=boot, maxtasksperchild=50) as pool:
        for i, r in enumerate(pool.imap_unordered(job, todo), 1):
            f.write(json.dumps(r) + "\n"); f.flush(); os.fsync(f.fileno())
            if i % 10 == 0 or i == len(todo):
                print(f"{time.strftime('%FT%TZ', time.gmtime())} {i}/{len(todo)} temp={temp()}", flush=True)
            if (outp.parent / "STOP").exists():
                print("STOP file: exiting", flush=True)
                pool.terminate()
                break
