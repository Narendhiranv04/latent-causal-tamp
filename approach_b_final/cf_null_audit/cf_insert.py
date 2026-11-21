#!/usr/bin/env python3
"""PROP_INS_3D: paper-faithful corridor-INSERTION counterfactuals (arXiv:2611.09130 Sec. 3 / App. F,H adapted to the shelf; amendment 4).
Paper: hold the grasp pose fixed, drop a solid box (edge 1.5-5 cm) into the approach corridor at a 5-15 cm standoff, re-run the planner for the
new label; NULL = the matched box placed ~30 cm off-corridor (should stay feasible); the reported 'Null' is the oracle false-flip rate.
Shelf adaptation (objects stand on the lattice, as the paper's 'resting pillar' family):
  fixed grasp  g* = the BASE's winning grasp (teacher query, first feasible in the scene's grasp order; ids are geometry-only, unchanged by edits)
  CF box       NEW object o_ins (shape box, half-size s in {0.0125, 0.02} -> edge 2.5 / 4 cm, height = target height so it reaches the pads),
               on a free legal cell whose centre lies in g*'s approach corridor: axial standoff 0.05-0.15 m behind the pad centre along -approach,
               lateral distance <= pitch/2; order: standoff asc, edge desc
  NULL box     the same box, Chebyshev >= 2 from target and goal, first on the far side of the target ("30 cm back", paper App. F distal
               control: axial <= -0.10 m, lateral <= pitch), then off-corridor (lateral >= 1.5 pitch); each ordered by |distance from CF cell - 0.30 m|
  labels       y_grasp = plan_pick_place(t0 -> goal, g*) on the edited scene (the paper's unit: same grasp, identical pose; planner dry run)
               y_task  = CF_Y3D_V1 target-Y (all 32 grasps + MuJoCo execution) -- the semantics of every compared model's score
    python cf_insert.py gen   BASES.jsonl BASE_LABELS.jsonl OUT_JOBS.jsonl        (env3d)
    python cf_insert.py label JOBS.jsonl OUT.jsonl WORKERS                        (env3d)"""
import hashlib, json, os, sys, time
from multiprocessing import get_context
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SIZES, PITCH = (0.02, 0.0125), 0.075


def h(*a):
    return hashlib.sha256("|".join(map(str, ("CFINS",) + a)).encode()).hexdigest()


def gen(bases_f, lab_f, out_f):
    sys.path.insert(0, os.environ["CF_SCN"])
    import scn_geometry as G
    L = {json.loads(l)["qid"]: json.loads(l) for l in open(lab_f)}
    n = 0
    with open(out_f, "w") as f:
        for b in (json.loads(l) for l in open(bases_f)):
            rid = b["root_id"]
            bl = L.get(f"{rid}|BASE")
            if not bl or bl.get("y") != 1 or bl.get("grasp_id") is None:
                continue
            rec = json.loads(Path(b["path"]).read_text())
            t = next(o for o in rec["objects"] if o["id"] == "t0")
            cells = {k: tuple(v) for k, v in b["cells"].items()}
            goal = tuple(rec["goal"])
            pos, R, _ = G.grasps_of(dict(height=float(t["height"]), size=float(t["size"]), shape=t["shape"]), cells["t0"])
            gid = int(bl["grasp_id"])
            pg, a = pos[gid][:2].astype(float), R[gid][:2, 2].astype(float)
            d = -a / max(np.linalg.norm(a), 1e-9)                         # from the pad centre back towards the pre-grasp / hand
            occ = set(cells.values())
            free = [(r, c) for r in range(6) for c in range(6) if (r, c) not in occ and (r, c) != goal]
            geo = {}
            for q in free:
                v = np.array(G.cell_xy(q)) - pg
                s = float(v @ d)
                geo[q] = (s, float(np.linalg.norm(v - s * d)))
            cf = sorted((q for q in free if 0.05 <= geo[q][0] <= 0.15 and geo[q][1] <= PITCH / 2), key=lambda q: (geo[q][0], h(rid, q)))
            nid = f"o{sum(1 for k in cells if k != 't0'):02d}"
            while nid in cells:
                nid = f"o{int(nid[1:]) + 1:02d}"
            base = {"qid": f"{rid}|BASE", "root_id": rid, "kind": "BASE", "cells": b["cells"], "extra_objects": [], "grasp_id": gid, "path": b["path"],
                    "base_kind": b.get("base_kind"), "seed": 0, "family": "PROP_INS_3D"}
            f.write(json.dumps(base) + "\n"); n += 1
            for si, sz in enumerate(SIZES):
                box = {"id": nid, "shape": "box", "size": sz, "height": float(t["height"]), "color": "yellow"}
                for k, q in enumerate(cf):
                    f.write(json.dumps({**base, "qid": f"{rid}|CF|{nid}|{q[0]}_{q[1]}|s{si}", "kind": "CF", "obj": nid, "rank": si * 10 + k,
                                        "cells": {**b["cells"], nid: list(q)}, "extra_objects": [box], "standoff_m": round(geo[q][0], 4),
                                        "lateral_m": round(geo[q][1], 4), "box_edge_m": 2 * sz}) + "\n"); n += 1
                if not cf:
                    continue
                q0 = cf[0]
                far = lambda q: max(abs(q[0] - cells["t0"][0]), abs(q[1] - cells["t0"][1])) >= 2 and max(abs(q[0] - goal[0]), abs(q[1] - goal[1])) >= 2  # noqa: E731
                dcf = lambda q: abs(float(np.linalg.norm(np.subtract(G.cell_xy(q), G.cell_xy(q0)))) - 0.30)  # noqa: E731
                back = sorted((q for q in free if q not in cf and far(q) and geo[q][0] <= -0.10 and geo[q][1] <= PITCH), key=lambda q: (dcf(q), h(rid, "B", q)))
                lat = sorted((q for q in free if q not in cf and q not in back and far(q) and geo[q][1] >= 1.5 * PITCH), key=lambda q: (dcf(q), h(rid, "N", q)))
                nl = back + lat                                   # paper App. F: distal control "30 cm back" first, then the lateral off-corridor box
                for k, q in enumerate(nl[:2]):
                    f.write(json.dumps({**base, "qid": f"{rid}|NULL|{nid}|{q[0]}_{q[1]}|s{si}", "kind": "NULL", "obj": nid, "rank": si * 10 + k,
                                        "cells": {**b["cells"], nid: list(q)}, "extra_objects": [box], "lateral_m": round(geo[q][1], 4),
                                        "null_mode": "back" if q in back else "lateral", "dist_from_cf_m": round(float(np.linalg.norm(np.subtract(G.cell_xy(q), G.cell_xy(q0)))), 4),
                                        "box_edge_m": 2 * sz}) + "\n"); n += 1
    print("jobs", n)


_W = {}


def lab(job):
    try:
        if "F" not in _W:
            os.environ.setdefault("MUJOCO_GL", "disable")
            sys.path.insert(0, str(Path(os.environ.get("FIN3D_CODE", str(Path.home() / "abf_v3_laptop/gen/final3d_v4/code")))))
            import fin3d as F
            F.boot(); _W["F"] = F
        import perm3d as Q
        A = Q._M["A"]; TS = A.env()["TS"]
        rec = json.loads(Path(job["path"]).read_text())
        objs = rec["objects"] + job["extra_objects"]
        cells = {k: tuple(v) for k, v in job["cells"].items()}
        t0 = time.process_time()
        e = A.build(objs, {k: list(v) for k, v in cells.items()})
        A.settle(e, cells)
        settled = all(e.cell_of(o) == cells[o] for o in cells)
        i = e.obj_id("t0"); e.objects[i]["pos"] = e.obj_pos(i)
        g = TS.grasp_poses(e.objects[i], e.table_z)[job["grasp_id"]]
        assert g["id"] == job["grasp_id"]
        pg = e.plan_pick_place("t0", tuple(rec["goal"]), g, q_start=e.q_now(), seed=int(job.get("seed", 0)))
        r = pg.get("reason", "")
        yg = int(bool(pg["feasible"]))
        gk = None if yg else ("CERTIFIED" if ("overlap a neighbour" in r or "would hit" in r or "occupied" in r) else "NO_PLAN_FOUND")
        p, qi = A.query(e, "t0", tuple(rec["goal"]), seed=int(job.get("seed", 0)))
        out = {"qid": job["qid"], "root_id": job["root_id"], "teacher": "CF_INS_3D_V1", "settled_ok": settled, "y_grasp": yg, "grasp_negative_kind": gk,
               "grasp_reason": r[:120]}
        if p is None:
            out.update(y=0, status="NO_FEASIBLE_SIDE_GRASP", negative_kind=A.label(None, qi).get("negative_kind"))
        else:
            before = {n: e.cell_of(n) for n in e.obj_index if n != "t0"}
            try:
                e.run_plan(p)
                ht = next(x["height"] for x in rec["objects"] if x["id"] == "t0")
                z = e.obj_pos("t0")[2] - e.table_z - ht / 2
                ok = e.cell_of("t0") == tuple(rec["goal"]) and abs(z) <= 0.01 and all(e.cell_of(n) == before[n] for n in before)
                out.update(y=int(ok), status="VERIFIED" if ok else "EXECUTION_NOT_VERIFIED", negative_kind=None if ok else "EXECUTION", task_grasp_id=qi.get("grasp_id"))
            except TS.GraspFailed as err:
                out.update(y=0, status=f"GRASP_FAILED:{str(err)[:60]}", negative_kind="EXECUTION")
        out["cpu_s"] = round(time.process_time() - t0, 2)
        return out
    except Exception as err:  # noqa: BLE001 -- explicit ERROR row, excluded and counted
        return {"qid": job["qid"], "root_id": job["root_id"], "y": None, "y_grasp": None, "status": "ERROR", "error": f"{type(err).__name__}: {str(err)[:200]}"}


def label(jobs_f, out_f, W):
    jobs = [json.loads(l) for l in open(jobs_f)]
    done = {json.loads(l)["qid"] for l in open(out_f)} if Path(out_f).exists() else set()
    with get_context("spawn").Pool(W, maxtasksperchild=20) as pool, open(out_f, "a") as f:
        for r in pool.imap_unordered(lab, [j for j in jobs if j["qid"] not in done]):
            f.write(json.dumps(r, default=str) + "\n"); f.flush()


if __name__ == "__main__":
    a = sys.argv[1:]
    gen(*a[1:4]) if a[0] == "gen" else label(a[1], a[2], int(a[3]))
