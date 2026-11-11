#!/usr/bin/env python3
"""Finalized Approach-B X/Y check on accepted 3D hard-order roots (gvlab; diagnostic sidecar, nothing promoted).
X = the relocations of one order exactly as bd_3dt.teach.seq executes them (perm3d.seq loop, carried state, same checks) WITHOUT the
    target step, then bwlphys.connector (CONNECTOR_TO_QREADY_V1: plan_free_move(q_now, q_ready, seed 0, RRT 5000), execute, open gripper,
    |q - q_ready| <= 0.02, nothing pushed > 4 mm, every object in its endpoint cell, nothing held, no contact).
Y = BD3DS66_Y_PLAN_V1 teacher step: settle the endpoint scene at q_ready, bd_3dt.query(t0 -> goal), execute with seq's target checks.
    All 6 orders of one assignment share the endpoint, hence one Y.
Teacher pass only: the fresh-process independent replay of the full protocol is NOT run here (reported as such).
  xy3d.py DATASET_DIR STORE_DIR ROOT_IDS.json OUT.jsonl WORKERS CPUS(a-b)"""
import itertools, json, os, sys, time, traceback
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import dep3d as D  # noqa: E402
import perm3d as Q  # noqa: E402

M = {}


def boot(ds, out):
    D.boot("XY", ds, out, {})
    sys.path.insert(0, str(Path.home() / "approachb3d_v3/bwl_physics_pilot"))
    import bwlphys as BP
    M.update(BP=BP)


def run_x(rec, steps):
    A, BP = Q._M["A"], M["BP"]
    S = A.env()["TS"]
    objs, cells0 = rec["objects"], rec["initial_cells"]
    e = A.build(objs, cells0)
    A.settle(e, cells0)
    for j, (o, d) in enumerate(steps):
        before = {n: e.cell_of(n) for n in e.obj_index if n != o}
        p, qi = A.query(e, o, d)
        if p is None:
            return {"x": 0, "phase": f"relocation:{j}", "status": A.label(None, qi).get("reason")}
        try:
            e.run_plan(p)
        except S.GraspFailed as err:
            return {"x": 0, "phase": f"relocation:{j}", "status": f"GRASP_FAILED:{str(err)[:60]}"}
        h = next(x["height"] for x in objs if x["id"] == o)
        z = e.obj_pos(o)[2] - e.table_z - h / 2
        if e.cell_of(o) != tuple(d) or abs(z) > 0.01 or any(e.cell_of(n) != before[n] for n in before):
            return {"x": 0, "phase": f"relocation:{j}", "status": "EXECUTION_NOT_VERIFIED"}
    expected = {**{k: tuple(v) for k, v in cells0.items()}, **{o: tuple(d) for o, d in steps}}
    c, _ = BP.connector(e, S, expected)
    return {"x": int(bool(c["ok"])), "phase": None if c["ok"] else "connector", "status": c.get("failure") or "VERIFIED",
            "dq_ready": c.get("dq_ready")}


def run_y(rec, steps):
    A = Q._M["A"]
    S = A.env()["TS"]
    objs = rec["objects"]
    cells = {**{k: tuple(v) for k, v in rec["initial_cells"].items()}, **{o: tuple(d) for o, d in steps}}
    e = A.build(objs, rec["initial_cells"])
    A.settle(e, cells)
    p, qi = A.query(e, "t0", tuple(rec["goal"]))
    if p is None:
        return {"y": 0, "status": A.label(None, qi).get("reason")}
    before = {n: e.cell_of(n) for n in e.obj_index if n != "t0"}
    try:
        e.run_plan(p)
    except S.GraspFailed as err:
        return {"y": 0, "status": f"GRASP_FAILED:{str(err)[:60]}"}
    h = next(x["height"] for x in objs if x["id"] == "t0")
    z = e.obj_pos("t0")[2] - e.table_z - h / 2
    ok = e.cell_of("t0") == tuple(rec["goal"]) and abs(z) <= 0.01 and all(e.cell_of(n) == before[n] for n in before)
    return {"y": int(ok), "status": "VERIFIED" if ok else "EXECUTION_NOT_VERIFIED"}


def job(path):
    t0 = time.process_time()
    rec = json.loads(Path(path).read_text())
    rid = rec["ids"]["root_id"]
    out = {"root_id": rid, "legacy_n_success": rec["n_success"], "legacy": {}, "replay": "NOT_RUN(teacher pass only)"}
    try:
        mini = next(b for b in rec["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1)
        assign = [(o, tuple(d)) for o, d in mini["sequence"]]
        leg = {tuple(o for o, _ in p["order"]): p["y"] for p in rec["permutations"]}
        xs = {}
        for q in itertools.permutations(assign):
            key = "".join(o[-1] for o, _ in q)
            xs[key] = run_x(rec, list(q))
            out["legacy"][key] = leg[tuple(o for o, _ in q)]
        out.update(x=xs, y=run_y(rec, assign), x_n_success=sum(v["x"] == 1 for v in xs.values()))
    except Exception as e:  # noqa: BLE001
        out.update(error=f"{type(e).__name__}: {str(e)[:200]}", trace=traceback.format_exc()[-800:])
    out["cpu_s"] = round(time.process_time() - t0, 1)
    return out


if __name__ == "__main__":
    import multiprocessing as mp
    assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
    ds, store, ids, outp, workers, cpus = sys.argv[1], Path(sys.argv[2]), json.loads(Path(sys.argv[3]).read_text()), Path(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
    a, b = map(int, cpus.split("-"))
    os.sched_setaffinity(0, set(range(a, b + 1)))
    done = {json.loads(l)["root_id"] for l in outp.read_text().splitlines()} if outp.exists() else set()
    todo = [str(store / "roots" / f"{r}.json") for r in ids if r not in done]
    with open(outp, "a", buffering=1) as f, mp.get_context("spawn").Pool(workers, initializer=boot, initargs=(ds, str(outp.parent / "xy3d_scratch"))) as pool:
        for r in pool.imap_unordered(job, todo):
            f.write(json.dumps(r) + "\n"); f.flush()
