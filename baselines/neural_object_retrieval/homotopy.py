#!/usr/bin/env python3
"""NOR-Grid TRAIN-only path-homotopy supervision (Ren & Qureshi ICRA'24 §III-C/D, adapted to the full target-to-goal task).

2D protocol NOR_HOMOTOPY_2D_V1 (frozen before any label is used):
  * reference paths = the UNCHANGED benchmark target planner (bd_2d.t_goal: pregrasp, approach, side grasp, attached carry, place,
    release, retreat; same FAST budget, same q_ref start as the Y teacher) in a scene that keeps the target and the FIXED structure only
    -> collision-ignorant with respect to every movable non-target object (the paper's "without considering collisions with other
    objects"), but robot kinematics, fixed obstacles and the declared side-grasp family remain enforced;
  * multiple homotopies = one path per (pick grasp, place grasp) pair, the pair restricted with bd_2d_exact._Restricted, pairs drawn from
    the live screened grasps in a seeded order (sha256(root_id|NOR_HOMOTOPY_2D_V1)), up to N_OK verified paths from at most N_TRY pairs;
  * sweep of a path = p14_sweep_index.swept_cells (cells whose obstacle disc would come within the planner margin of any robot body or
    the carried target along the recorded path, all phases) -> full articulated 3R + gripper + held-disc geometry, not a point robot;
  * OSNet label of a (hypothetical) scene: count_o = number of reference paths whose sweep contains object o's current cell, p = count /
    sum(count) over eligible movable objects; sum 0 -> masked (no blocker under the reference paths);
  * RPNet label for object o: cost(c) = 1 for cells that are statically illegal (occupied now, occupied at S0, goal, undeclared) or lie
    in the union sweep of the reference paths (homotopy-blocking); otherwise 0.9 * dist(c, source(o)) / max legal distance (in [0, 0.9]).
The reference paths never depend on movable objects, so labels for any hypothetical prefix are exact lookups (no new planner call).

    homotopy.py 2d ROWS_SPLIT OUT N_ROOTS WORKERS     (run with the 2D teacher env; ABF_ROOT = laptop mirror root)"""
import hashlib, json, os, sys, time
from pathlib import Path

PROTO = "NOR_HOMOTOPY_2D_V1"
N_OK, N_TRY = 6, 12
H = Path(__file__).resolve().parent
AB = H.parents[1] / "approach_b_final"
_M = {}


def boot(geom):
    sys.path.insert(0, str(AB))
    import teacher2d as T2
    T2.boot(geom)
    import bd_2d as A
    import bd_2d_exact as E
    import p14_sweep_index as SX
    _M.update(T2=T2, A=A, E=E, SX=SX, G=A.env())


def root_paths(rec):
    """-> {"paths": [{"pair": [ap, aq], "status", "sweep": [cells]}], "n_tried", "cpu_s"} for one 2D root record (geometry-only labels)."""
    A, E, SX, G = _M["A"], _M["E"], _M["SX"], _M["G"]
    rid = rec["ids"]["root_id"]
    import bxy_teacher as BX
    cells0 = BX.bd.cells0(rec)
    fixed = {o: cells0[o] for o in rec.get("fixed_ids", [])}
    src, goal = int(cells0["t0"]), int(rec["goal_cell"])
    t0 = time.process_time()
    Fp = sorted(E._screen(src, goal, list(fixed.values())))
    Fq = sorted(E._screen(src, goal, list(fixed.values()), side="q"))
    pairs = [(p, q) for p in Fp for q in Fq]
    pairs.sort(key=lambda pq: hashlib.sha256(f"{rid}|{PROTO}|{pq}".encode()).hexdigest())
    out, tried = [], 0
    task, q = BX.task_of(rid, rec), BX.qref(rec)
    keep = {"t0", *fixed}                                          # collision-ignorant: movable non-target objects are absent
    task = {**task, "scene": {**task["scene"], "objects": [o for o in task["scene"]["objects"] if o["id"] in keep]},
            "key": f"{rid}|{PROTO}"}
    for ap, aq in pairs[:N_TRY]:
        if sum(p["status"] == "VERIFIED" for p in out) >= N_OK:
            break
        tried += 1
        with E._Restricted(tuple(ap), tuple(aq)):
            st, a, _ = A.t_goal(task, {}, {"t0": src, **fixed}, q)
        e = {"pair": [list(ap), list(aq)], "status": st}
        if st == "VERIFIED":
            sw = SX.swept_cells(G["robot"], G["cfg"], a)
            e["sweep"] = sorted(set().union(*map(set, sw.values())))
        out.append(e)
    return {"root_id": rid, "protocol": PROTO, "n_live_pick": len(Fp), "n_live_place": len(Fq), "n_pairs": len(pairs), "n_tried": tried,
            "paths": out, "n_verified": sum(p["status"] == "VERIFIED" for p in out), "cpu_s": round(time.process_time() - t0, 2)}


def labels(inp, dom, cells, sweeps, legal, src_obj=None):
    """OSNet target over eligible objects and (optionally) the RPNet cost map for src_obj, from cached sweeps -> dict (lookups only)."""
    import numpy as np
    n = len(inp["ids"])
    fixed = [bool(a[3]) for a in inp["attrs"]] if dom == "2d" else [False] * n
    elig = [i for i in range(n) if i != inp["tid"] and not fixed[i]]
    cnt = {i: sum(int(cells[i]) in s for s in sweeps) for i in elig}
    tot = sum(cnt.values())
    res = {"count": cnt, "p": {i: c / tot for i, c in cnt.items()} if tot else None}
    if src_obj is not None:
        U = set().union(*sweeps) if sweeps else set()
        xy = {int(k): np.array(v) for k, v in inp["cell_xy"].items()}
        s = xy[int(cells[src_obj])]
        ok = [c for c in legal if c not in U]
        dmax = max([np.linalg.norm(xy[c] - s) for c in ok] or [1.0]) + 1e-9
        res["cost"] = {c: (0.9 * float(np.linalg.norm(xy[c] - s)) / dmax if c in ok else 1.0) for c in xy}
        res["n_nonblocking_legal"] = len(ok)
    return res


def _job(path):
    rec = json.loads(Path(path).read_text())
    try:
        return root_paths(rec)
    except Exception as e:  # noqa: BLE001  (recorded, never a label)
        return {"root_id": rec["ids"]["root_id"], "protocol": PROTO, "error": f"{type(e).__name__}:{str(e)[:200]}", "paths": [], "n_verified": 0}


def _init(geom):
    if geom == "3d":
        boot3d()
    else:
        boot(geom)


# ------------------------------------------------------------------------------------------------ 3D (NOR_HOMOTOPY_3D_V1)
PROTO3 = "NOR_HOMOTOPY_3D_V1"
CODE3D = os.environ.get("NOR_CODE3D", str(Path.home() / "Desktop/rss3d_final_src/gh-yadu-iiith/shelf_6x6_open_sides/"
                                          "dataset_bd_classquota_without_home_position_no_overpass/code"))
QSTEP = 0.02                                                       # rad between replayed configurations (planner free-move resolution)


def boot3d():
    """Unchanged SHELF66V3 scene / planner (bd_shelf + bd_3dt, as the 3D Y teacher builds it)."""
    os.environ.setdefault("MUJOCO_GL", "disable")
    sys.path[:0] = [CODE3D, CODE3D + "/shelf66_v3"]
    os.chdir(CODE3D)
    import run_shelf66_full as F
    D, A, P = F._modules()
    _M.update(A=A, TS=A.env()["TS"])


def root_paths3d(rec):
    """3D protocol: the target-only scene (every movable non-target object absent) with the arm ceiling held at the FULL scene's value
    (CEILING_MARGIN raised by tallest - target height: the only place other objects enter the planner), one plan_pick_place path per
    side-grasp pose (TS.grasp_poses, seeded order), replayed in the FULL scene: blockers = objects the arm / open hand comes within
    OBJECT_MARGIN of (the teacher's own _object_hits) or whose footprint the carried target's footprint overlaps (CARRY_GAP);
    sweep = cells whose generic column (median footprint radius) any robot geom's bounding sphere reaches in the table plane."""
    import numpy as np
    A, TS = _M["A"], _M["TS"]
    rid = rec["ids"]["root_id"]
    objs, cells = rec["objects"], {k: tuple(v) for k, v in rec["initial_cells"].items()}
    tgt = [o for o in objs if o["id"] == "t0"]
    t0 = time.process_time()
    old = TS.CEILING_MARGIN
    TS.CEILING_MARGIN = old + max(o["height"] for o in objs) - tgt[0]["height"]
    try:
        e = A.build(tgt, {"t0": cells["t0"]})
    finally:
        TS.CEILING_MARGIN = old
    full = A.build(objs, cells)
    i = e.obj_id("t0")
    e.objects[i]["pos"] = e.obj_pos(i)
    q0 = e.q_now()
    gs = list(TS.grasp_poses(e.objects[i], e.table_z))
    gs.sort(key=lambda g: hashlib.sha256(f"{rid}|{PROTO3}|{g['id']}".encode()).hexdigest())
    it = full.obj_id("t0")
    full._focus_i = it
    m, d = full.model, full.ik_data
    rg = full._robot_geoms
    fr = {o["id"]: TS.footprint_radius(o) for o in objs}
    rgen = float(np.median(list(fr.values())))
    cxy = {r * 6 + c: np.array(full.cell_xy((r, c)) if hasattr(full, "cell_xy") else
                                [full.x0 + (r - 2.5) * full.pitch, (c - 2.5) * full.pitch]) for r in range(6) for c in range(6)}
    pos = {o["id"]: np.array(full.obj_pos(full.obj_id(o["id"]))[:2]) for o in objs}
    import mujoco as mj
    others = [j for j, o in enumerate(full.objects) if o["name"] != "t0"]
    col = full._col_ids[others[0]] if others and full._col_ids else None          # one no-overpass column re-used as the probe
    if col is not None:
        col_xy0 = m.geom_pos[col, :2].copy()
        m.geom_size[col, 0] = rgen                                                # probe radius = median footprint radius
    out, tried = [], 0
    for g in gs[:N_TRY]:
        if sum(p["status"] == "VERIFIED" for p in out) >= N_OK:
            break
        tried += 1
        p = e.plan_pick_place("t0", tuple(rec["goal"]), g, q_start=q0)
        ent = {"grasp": g["id"], "status": "VERIFIED" if p["feasible"] else "NO_PLAN"}
        if p["feasible"]:
            hits, sweep = set(), set()
            for s in p["segments"]:
                if s["kind"] == "grip":
                    continue
                Q = np.asarray(s["q"], float)
                for a_, b_ in zip(Q[:-1], Q[1:]) if len(Q) > 1 else [(Q[0], Q[0])]:
                    n = max(2, int(np.ceil(np.max(np.abs(b_ - a_)) / QSTEP)) + 1)
                    for t in np.linspace(0, 1, n):
                        q = a_ + t * (b_ - a_)
                        hits |= set(full._object_hits(q, every=False))        # also leaves d at q (mj_kinematics)
                        if col is None:
                            continue
                        xy, rb = d.geom_xpos[rg, :2], m.geom_rbound[rg]
                        for c, cc in cxy.items():                             # generic column at c: exact MuJoCo distance
                            if c in sweep:
                                continue
                            near = np.linalg.norm(xy - cc, axis=1) < rb + rgen + TS.OBJECT_MARGIN
                            if not near.any():
                                continue
                            m.geom_pos[col, :2] = cc
                            if any(mj.mj_geomDistance(m, d, int(gg), int(col), TS.OBJECT_MARGIN, None) < TS.OBJECT_MARGIN
                                   for gg in rg[near]):
                                sweep.add(c)
                        if col is not None:
                            m.geom_pos[col, :2] = col_xy0
            for xy in np.asarray(p.get("carry_xy", []), float).reshape(-1, 2):
                for o in objs:
                    if o["id"] != "t0" and np.linalg.norm(xy - pos[o["id"]]) < fr["t0"] + fr[o["id"]] + TS.CARRY_GAP:
                        hits.add(o["id"])
                for c, cc in cxy.items():
                    if np.linalg.norm(xy - cc) < fr["t0"] + rgen + TS.CARRY_GAP:
                        sweep.add(c)
            hits.discard("t0")
            ent.update(blockers=sorted(hits), sweep=sorted(sweep))
        out.append(ent)
    return {"root_id": rid, "protocol": PROTO3, "n_grasps": len(gs), "n_tried": tried, "paths": out,
            "n_verified": sum(p["status"] == "VERIFIED" for p in out), "cpu_s": round(time.process_time() - t0, 2)}


def _job3(path):
    rec = json.loads(Path(path).read_text())
    try:
        return root_paths3d(rec)
    except Exception as e:  # noqa: BLE001
        import traceback
        return {"root_id": rec["ids"]["root_id"], "protocol": PROTO3, "error": f"{type(e).__name__}:{str(e)[:200]}",
                "trace": traceback.format_exc()[-800:], "paths": [], "n_verified": 0}


def main():
    dom, split, out, n, w = sys.argv[1], sys.argv[2], Path(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    import multiprocessing as mp
    sys.path.insert(0, str(H)); sys.path.insert(0, str(AB))
    import nor_data as DA
    import evaluate as EV
    assert split == "train", "homotopy labels are TRAIN-only"
    rows = sorted(DA.rows(dom, DA.BASE, split), key=lambda r: hashlib.sha256(("NOR_PILOT|" + r["root_id"]).encode()).hexdigest())[:n]
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(l)["root_id"] for l in open(out)} if out.exists() else set()
    jobs = []
    for r in rows:
        if r["root_id"] in done:
            continue
        p = EV.path_of(dom.upper(), r)
        if dom == "3d":
            geom = "3d"
        else:
            geom = "fastgeom1" if json.loads(Path(p).read_text()).get("geometry_impl") == "fastgeom1" else "original"
        jobs.append((str(p), geom))
    t0 = time.time()
    with open(out, "a") as f:
        for geom in sorted({g for _, g in jobs}):
            sub = [p for p, g in jobs if g == geom]
            with mp.get_context("spawn").Pool(w, initializer=_init, initargs=(geom,), maxtasksperchild=50) as pool:
                for i, r in enumerate(pool.imap_unordered(_job3 if geom == "3d" else _job, sub), 1):
                    r["geom"] = geom
                    f.write(json.dumps(r) + "\n"); f.flush()
                    if i % 10 == 0:
                        print(f"{time.strftime('%H:%M:%S')} {geom} {i}/{len(sub)}", flush=True)
    print(json.dumps({"out": str(out), "n": len(jobs), "wall_s": round(time.time() - t0, 1)}))


if __name__ == "__main__":
    main()
