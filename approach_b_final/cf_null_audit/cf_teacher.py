#!/usr/bin/env python3
"""CF/NULL physical target-Y oracle (laptop only).  Thin versioned wrappers around the UNCHANGED finalized teachers; no teacher file edited.

3D  CF_Y3D_V1 = the exact steps of fin3d.run_y (BD3DS66_Y_PLAN_V1): build the scene at the record's initial cells, settle the queried layout
    at q_ref, bd_3dt.query(t0 -> goal) over the scene's 32 side grasps (RRT-Connect max_iters 5000, seed), execute the plan in MuJoCo with
    the seq target checks (goal cell, upright, nobody else moved).  Additionally returned (dropped by run_y): bd_3dt.label's negative kind
    CERTIFIED (every grasp fails a deterministic geometric check: overlap / would hit / occupied -- no search) vs NO_PLAN_FOUND (some grasp
    failed only in RRT search = budget-limited), and the per-grasp reasons.
2D  CF_Y2D_V1 = bxy_teacher.y_query (BXY_Y_TEACHER_V1) on an edited raw record (objects' cells changed, ids / roles / goal / q0 unchanged):
    statuses VERIFIED / CERTIFIED_INFEASIBLE / UNKNOWN_PLANNER / ... exactly as the teacher reports them.
    python cf_teacher.py run3d JOBS.jsonl OUT.jsonl WORKERS     (job: {qid, root_id, path, cells: {id: [r, c]}, seed})
    python cf_teacher.py run2d JOBS.jsonl OUT.jsonl WORKERS     (job: {qid, root_id, path, geom, cells: {id: cell}})"""
import json, os, sys, time
from multiprocessing import get_context
from pathlib import Path

F3 = Path(os.environ.get("FIN3D_CODE", str(Path.home() / "abf_v3_laptop/gen/final3d_v4/code")))
_W = {}


def boot3d():
    if "F" in _W:
        return
    os.environ.setdefault("MUJOCO_GL", "disable")
    sys.path.insert(0, str(F3))
    import fin3d as F
    F.boot()
    _W["F"] = F


def y3d(job):
    boot3d()
    F = _W["F"]
    import perm3d as Q
    A = Q._M["A"]
    rec = json.loads(Path(job["path"]).read_text())
    t0 = time.process_time()
    S = A.env()["TS"]
    cells = {k: tuple(v) for k, v in job["cells"].items()}
    mode = "run_y"                                  # fin3d.run_y path: build at the record's initial cells, settle the queried layout
    try:
        if job.get("force_direct"):                 # parity audit only: take the direct path on a conflict-free layout
            raise ValueError("forced: occupied")
        e = A.build(rec["objects"], rec["initial_cells"])
        A.settle(e, cells)
    except ValueError as err:                       # the queried layout needs a cell still held mid-settle (edits on a repair endpoint):
        if "occupied" not in str(err):              # build directly at the queried cells, then settle (flagged; parity-checked separately)
            raise
        mode = "direct"
        e = A.build(rec["objects"], {k: list(v) for k, v in cells.items()})
        A.settle(e, cells)
    settled_ok = all(e.cell_of(n) == cells[n] for n in cells)
    p, qi = A.query(e, "t0", tuple(rec["goal"]), seed=int(job.get("seed", 0)))
    out = {"qid": job["qid"], "root_id": job["root_id"], "teacher": "CF_Y3D_V1(fin3d.run_y steps; bd_3dt.query/label)", "settled_ok": settled_ok,
           "seed": int(job.get("seed", 0)), "build_mode": mode}
    if p is None:
        lab = A.label(None, qi)
        out.update(y=0, status="NO_FEASIBLE_SIDE_GRASP", negative_kind=lab.get("negative_kind"), grasp_reasons=qi.get("grasp_reasons"),
                   hit_objects=lab.get("hit_objects"))
    else:
        before = {n: e.cell_of(n) for n in e.obj_index if n != "t0"}
        try:
            e.run_plan(p)
            h = next(x["height"] for x in rec["objects"] if x["id"] == "t0")
            z = e.obj_pos("t0")[2] - e.table_z - h / 2
            ok = e.cell_of("t0") == tuple(rec["goal"]) and abs(z) <= 0.01 and all(e.cell_of(n) == before[n] for n in before)
            out.update(y=int(ok), status="VERIFIED" if ok else "EXECUTION_NOT_VERIFIED", negative_kind=None if ok else "EXECUTION",
                       grasp_id=qi.get("grasp_id"))
        except S.GraspFailed as err:
            out.update(y=0, status=f"GRASP_FAILED:{str(err)[:60]}", negative_kind="EXECUTION")
    out["cpu_s"] = round(time.process_time() - t0, 2)
    return out


def y2d(job):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import teacher2d as T2
    T2.boot(job["geom"])
    T, E = T2._M["T"], T2._M["E"]
    rec = json.loads(Path(job["path"]).read_text())
    lat = rec["scene"]["lattice"]
    for o in rec["scene"]["objects"]:                                   # edited layout: only the cell / centre of listed objects change
        if o["id"] in job["cells"]:
            c = int(job["cells"][o["id"]])
            o["cell"], o["xy_m"] = c, [lat["pitch_m"] * (c % lat["cols"] + 0.5), lat["pitch_m"] * (c // lat["cols"] + 0.5)]
    rec["ids"] = {**rec["ids"], "root_id": job["qid"]}
    rec["scene"]["root_id"] = job["qid"]
    t0 = time.process_time()
    r = T.y_query(E, job["qid"], rec, [], {})
    return {"qid": job["qid"], "root_id": job["root_id"], "teacher": "CF_Y2D_V1(bxy_teacher.y_query)", "y": r.get("y"), "status": r.get("teacher_status"),
            "negative_kind": r.get("negative_kind"), "replay": r.get("independent_replay"), "cpu_s": round(time.process_time() - t0, 2)}


def safe(job):
    try:
        return (y3d if job.get("_dom") == "3d" else y2d)(job)
    except Exception as err:  # noqa: BLE001 -- explicit ERROR row: excluded from every metric and counted, never coerced to 0
        return {"qid": job["qid"], "root_id": job["root_id"], "y": None, "status": "ERROR", "error": f"{type(err).__name__}: {str(err)[:200]}"}


def run(kind, jobs_f, out_f, W):
    jobs = [json.loads(l) for l in open(jobs_f)]
    done = {json.loads(l)["qid"] for l in open(out_f)} if Path(out_f).exists() else set()
    todo = [j for j in jobs if j["qid"] not in done]
    for j in todo:
        j["_dom"] = "3d" if kind == "run3d" else "2d"
    with get_context("spawn").Pool(W, maxtasksperchild=20) as pool, open(out_f, "a") as f:
        for r in pool.imap_unordered(safe, todo):
            f.write(json.dumps(r, default=str) + "\n"); f.flush()


if __name__ == "__main__":
    a = sys.argv[1:]
    run(a[0], a[1], a[2], int(a[3]))
