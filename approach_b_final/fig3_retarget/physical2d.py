#!/usr/bin/env python3
"""2D physical adapter (evaluator only; gvlab2 env2d) EXTENDING the unchanged BXY 2D teacher (bxy_teacher BXY_X_TEACHER_V1 / BXY_Y_TEACHER_V1
via teacher2d.boot).  No production function is modified; every new query is assembled from the teacher's own primitives.

x_chunked(rec, seq, bounds)   relocations exactly as bxy_teacher.x_query (DetPhysics.edges + p16_common.best_edge, carried q) and, at EVERY
                              declared boundary j (move count), the teacher's terminal connector (pre-checks: current q and q_ref clear in the
                              ('start', False) world; DetPhysics._transit to q_ref with the reference gap, key ('bxy_connector', state_key)),
                              after which the next relocation starts from q_ref.  bounds = {m} reproduces x_query exactly (parity fixture).
replay_xb                     independent re-certification: every relocation (motion.certify_trajectory in the scene it faces, exact
                              continuity, placement, released after retreat) and every connector (continuity, free / open gap, joint limits,
                              geometry.certify per segment, clear endpoint, ends at q_ref); connectors must sit exactly at the declared bounds.
y_temp(rec, cells, A, d)      temporary-target query from q_ref in the scene `cells`: (A, d) = (t0, goal_cell) -> bd_2d.t_goal (production);
                              otherwise the SAME code path as p15_search.Physics._goal with the target / goal parameterized (checker-accepted
                              certificates for picking A and placing at d -> CERTIFIED_INFEASIBLE; else plan_skill(A, d) from q_ref under the
                              goal_plans budget).  The original target t0 stays an ordinary collision body.  `parity_key=True` reuses the
                              production key so (t0, goal) reproduces t_goal bit-for-bit (parity fixture).
replay_ytemp                  motion.certify_trajectory of A's record in `cells` from q_ref, placement at d, released after retreat.
Rejections (never attempted): fixed / unknown object, the original target as a mover, duplicate objects / destinations, destination not a
legal cell or occupied.  Jobs: {key, path, geom, kind: X_CHUNKED | Y_TEMP | Y_TEMP_PARITY | X_PARITY, ...}.
    python physical2d.py work JOBS.json OUT.jsonl WORKERS CPU_LO MAX_JOBS MAX_CPU_H"""
from __future__ import annotations

import json, os, sys, time, traceback
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
TOL_Q = 1e-6
M = {}


def boot(geom="original"):
    import teacher2d as T2
    T2.boot(geom)
    import bd_2d, bxy_data, geometry, motion, p15_retarget, p15_search, p16_common, skill  # noqa: E401
    M.update(T=T2._M["T"], E=T2._M["E"], out=os.environ.get("FIG3_WOUT", T2._M["wout"]), bd_2d=bd_2d, bd=bxy_data, ge=geometry, mo=motion, pr=p15_retarget, ps=p15_search,
             pc=p16_common, sk=skill)


def reject(rec, seq):
    """None if well formed, else the reason (fixed / target movers are never attempted)."""
    T = M["T"]
    fixed = set(rec.get("fixed_ids") or [])
    if any(o in fixed for o, _ in seq):
        return "moves a fixed object"
    if any(o == "t0" for o, _ in seq):
        return "moves the original target"
    return T.eligible(rec, seq)


def _connector(phys, rec, cells, q):
    T, mo, ge, ps, E = M["T"], M["mo"], M["ge"], M["ps"], M["E"]
    s = phys.scene(cells, q)
    ck = mo.checkers(E["robot"], s, "t0", None, None, E["p"]["delta"], E["p"]["eps"])[("start", False)]
    gap = T.ref_gap(rec)
    if ck.status_at(q, gap).status != ge.CLEAR:
        return None, {"teacher_status": "TERMINAL_STATE_NOT_CLEAR", "negative_kind": "CERTIFIED"}
    if ck.status_at(T.qref(rec), gap).status != ge.CLEAR:
        return None, {"teacher_status": "Q_REF_NOT_CLEAR_IN_EDITED_SCENE", "negative_kind": "CERTIFIED"}
    conn, how = phys._transit(s, "t0", q, {"q": [T.qref(rec)], "gap": [gap]}, ("bxy_connector", ps.state_key(cells, q, ())))
    if conn is None:
        st = ps.U_BUD if phys.used["transit_plans"] >= phys.budget["transit_plans"] else ps.U_TR
        return None, {"teacher_status": st, "negative_kind": T._neg(st), "how": how}
    return conn, {"how": how}


def x_chunked(rec, seq, bounds, cache):
    T, pc, ps, bd = M["T"], M["pc"], M["ps"], M["bd"]
    k = rec["ids"]["root_id"]
    seq = [(o, int(d)) for o, d in seq]
    bounds = sorted({int(b) for b in bounds})
    row = {"ordered_actions": [list(a) for a in seq], "bounds": bounds, "teacher": "FIG3_X_CHUNKED_V1(" + T.X_VERSION + " primitives)"}
    bad = reject(rec, seq) or (None if seq and bounds and bounds[-1] == len(seq) and bounds[0] >= 1 else "bounds must end at m")
    if bad:
        return row | {"attempted": False, "x": None, "teacher_status": "INELIGIBLE", "why": bad}
    c0 = time.process_time()
    phys = T._phys(k, rec, cache)
    cells, q, items, fail = bd.cells0(rec), T.qref(rec), [], None
    for j, (o, d) in enumerate(seq):
        outs = phys.edges(cells, q, o, d)
        e = pc.best_edge(outs)
        if e is None:
            st = outs[0][0] if outs else ps.U_PLAN
            fail = {"teacher_status": st, "negative_kind": T._neg(st), "failed_phase": f"relocation:{j}"}
            break
        _, rs, q2, J, meta = e
        assert len(rs) == 1, "library-free teacher returns one record per relocation"
        items.append({"kind": "move", "object": o, "dest": d, "rec": rs[0], "via": meta.get("via")})
        cells, q = {**cells, o: d}, np.asarray(q2, float)
        if j + 1 in bounds:
            conn, info = _connector(phys, rec, cells, q)
            if conn is None:
                fail = {**info, "failed_phase": f"boundary:{j + 1}"}
                break
            items.append({"kind": "connector", "after_move": j + 1, "rec": conn, "how": info["how"]})
            q = np.asarray(conn["q"][-1], float)
    row |= {"budget_spent": dict(phys.used), "process_cpu_s": round(time.process_time() - c0, 3)}
    wit = [{"kind": it["kind"], **({"object": it["object"], "dest": it["dest"]} if it["kind"] == "move" else {"after_move": it["after_move"], "how": it["how"]}),
            "witness": T.wid(it["rec"], M["out"])} for it in items]
    row["trace"] = wit
    if fail is not None:
        return row | {"attempted": True, "x": 0, **fail, "independent_replay": None}
    rep = replay_xb(rec, seq, bounds, items)
    row |= {"independent_replay": rep["ok"], "replay_why": rep["why"]}
    return row | ({"x": 1, "teacher_status": "VERIFIED"} if rep["ok"] else {"x": 0, "teacher_status": "REPLAY_FAILED", "negative_kind": "OTHER_FAILURE"})


def replay_xb(rec, seq, bounds, items):
    T, mo, ge, bd = M["T"], M["mo"], M["ge"], M["bd"]
    import p16_motion as pm
    E = M["E"]; robot, p = E["robot"], E["p"]
    phys = pm.DetPhysics(T.task_of("replay", rec), None, budget=dict(M["bd_2d"].QB))
    cells, q, gap, j, nb = bd.cells0(rec), T.qref(rec), T.ref_gap(rec), 0, []
    for it in items:
        a = it["rec"]
        if np.max(np.abs(np.asarray(a["q"][0], float) - q)) > TOL_Q:
            return {"ok": False, "why": f"{it['kind']} {j}: discontinuous robot state"}
        if it["kind"] == "move":
            o, d = seq[j]
            if (it["object"], it["dest"]) != (o, d):
                return {"ok": False, "why": f"move {j}: record does not match the sequence"}
            if abs(float(a["gap"][0]) - gap) > 1e-12:
                return {"ok": False, "why": f"move {j}: gap discontinuity"}
            s = phys.scene(cells, q)
            try:
                v = mo.certify_trajectory(robot, s, o, a, p["delta"], p["eps"], p["evals"])
            except ValueError as e:
                return {"ok": False, "why": f"move {j}: invalid record ({e})"}
            if not all(x.status == ge.CLEAR for x in v):
                return {"ok": False, "why": f"move {j}: segment not certified clear"}
            if np.linalg.norm(np.asarray(a["place_xy"], float) - np.asarray(s.lattice.center(int(d)))) > 1e-9:
                return {"ok": False, "why": f"move {j}: not placed at the requested cell"}
            if bool(a["attached"][-1]) or str(a["phase"][-1]) != "retreat":
                return {"ok": False, "why": f"move {j}: does not end released after a safe retreat"}
            cells, q, gap, j = {**cells, o: int(d)}, np.asarray(a["q"][-1], float), float(a["gap"][-1]), j + 1
        else:
            cq = np.asarray(a["q"], float)
            if it["after_move"] != j:
                return {"ok": False, "why": "connector out of place"}
            if any(a["attached"]) or np.asarray(a["held_local"]).size or np.any(np.abs(np.asarray(a["gap"], float) - T.ref_gap(rec)) > 1e-12) or abs(gap - T.ref_gap(rec)) > 1e-12:
                return {"ok": False, "why": f"connector {j}: gripper not free / open at the reference gap"}
            if not all(ge.within_limits(robot, w) for w in cq):
                return {"ok": False, "why": f"connector {j}: waypoint outside joint limits"}
            ck = mo.checkers(robot, phys.scene(cells, q), "t0", None, None, p["delta"], p["eps"])[("start", False)]
            for qa, qb in zip(cq[:-1], cq[1:]):
                if ge.certify(ck, qa, qb, gap, gap, p["evals"]).status != ge.CLEAR:
                    return {"ok": False, "why": f"connector {j}: segment not certified clear"}
            if ck.status_at(cq[-1], gap).status != ge.CLEAR or np.max(np.abs(cq[-1] - T.qref(rec))) > TOL_Q:
                return {"ok": False, "why": f"connector {j}: endpoint not clear / not q_ref"}
            q = cq[-1]; nb.append(j)
    if j != len(seq) or nb != list(bounds):
        return {"ok": False, "why": f"boundary structure {nb} != declared {list(bounds)}"}
    return {"ok": True, "why": None, "final_cells": cells}


def y_temp(rec, cells, A, d, cache, parity_key=False):
    T, bd_2d, ps, pr, sk, bd = M["T"], M["bd_2d"], M["ps"], M["pr"], M["sk"], M["bd"]
    import ordered as od
    k = rec["ids"]["root_id"]
    cells = {o: int(c) for o, c in cells.items()}
    q = T.qref(rec)
    row = {"target": A, "goal": int(d), "cells": cells, "teacher": "FIG3_Y_TEMP_V1"}
    fixed = set(rec.get("fixed_ids") or [])
    legal = set(int(c) for c in rec["scene"]["legal_cells"])
    if A in fixed or A not in cells:
        return row | {"attempted": False, "y": None, "teacher_status": "INELIGIBLE", "why": "fixed or unknown temporary target"}
    if int(d) not in legal or any(c == int(d) for o, c in cells.items() if o != A):
        return row | {"attempted": False, "y": None, "teacher_status": "INELIGIBLE", "why": "goal not legal or occupied"}
    c0 = time.process_time()
    if (A, int(d)) == ("t0", int(rec["goal_cell"])) and not parity_key:
        st, a, _ = bd_2d.t_goal(T.task_of(k, rec), cache, cells, q)
        path = "bd_2d.t_goal"
    else:
        phys = T._phys(k, rec, cache)
        s = phys.scene(cells, q)
        kk = ("goal", ps.state_key(cells, q, ())) if parity_key else ("tgoal", ps.state_key(cells, q, ()), A, int(d))
        cert = pr.certified(phys.cfg, phys.robot, s, A, int(d))
        if cert:
            st, a = ps.CI, {"certificates": cert}
        elif not phys._take("goal_plans"):
            st, a = ps.U_BUD, None
        else:
            r = sk.plan_skill(phys.robot, s, A, int(d), phys.cfg, phys._key(*kk), q_start=np.asarray(q, float), q_goal=None)
            st, a = (ps.V, r.traj.arrays()) if r.status == sk.VERIFIED and r.traj is not None else (ps.U_PLAN, {"planner": r.status, "reason": r.reason})
        path = "generic_goal(parity_key)" if parity_key else "generic_goal"
    row |= {"process_cpu_s": round(time.process_time() - c0, 3), "attempted": True, "path": path}
    if st != "VERIFIED":
        return row | {"y": 0, "teacher_status": st, "negative_kind": T._neg(st), "witness": None, "independent_replay": None,
                      "certificates": a.get("certificates") if isinstance(a, dict) else None}
    rep = replay_ytemp(rec, cells, A, int(d), a)
    row |= {"witness": T.wid(a, M["out"]), "independent_replay": rep["ok"], "replay_why": rep["why"],
            "q_start": np.asarray(a["q"][0]).tolist(), "J": od.joint_travel(M["E"]["robot"], [a])["J"]}
    return row | ({"y": 1, "teacher_status": "VERIFIED"} if rep["ok"] else {"y": 0, "teacher_status": "REPLAY_FAILED"})


def replay_ytemp(rec, cells, A, d, a):
    T, mo, ge = M["T"], M["mo"], M["ge"]
    import p16_motion as pm
    E = M["E"]
    phys = pm.DetPhysics(T.task_of("replay", rec), None, budget=dict(M["bd_2d"].QB))
    if np.max(np.abs(np.asarray(a["q"][0], float) - T.qref(rec))) > TOL_Q or abs(float(a["gap"][0]) - T.ref_gap(rec)) > 1e-12:
        return {"ok": False, "why": "temporary-target record does not start at q_ref with the reference gap"}
    s = phys.scene(cells, T.qref(rec))
    try:
        v = mo.certify_trajectory(E["robot"], s, A, a, E["p"]["delta"], E["p"]["eps"], E["p"]["evals"])
    except ValueError as e:
        return {"ok": False, "why": f"invalid record ({e})"}
    if not all(x.status == ge.CLEAR for x in v):
        return {"ok": False, "why": "segment not certified clear"}
    if np.linalg.norm(np.asarray(a["place_xy"], float) - np.asarray(s.lattice.center(int(d)))) > 1e-9:
        return {"ok": False, "why": "not placed at the temporary goal"}
    if bool(a["attached"][-1]) or str(a["phase"][-1]) != "retreat":
        return {"ok": False, "why": "does not end released after a safe retreat"}
    return {"ok": True, "why": None}


def job(j):
    if not M:
        boot(j.get("geom", "original"))
    T, bd = M["T"], M["bd"]
    t0, c0 = time.time(), time.process_time()
    rec = json.loads(Path(j["path"]).read_text())
    out = {"key": j["key"], "kind": j["kind"], "root_id": rec["ids"]["root_id"]}
    try:
        if j["kind"] == "X_PARITY":                                  # production x_query vs x_chunked(bounds={m}), fresh caches each
            ref = T.x_query(M["E"], rec["ids"]["root_id"], rec, j["seq"], {}, out=M["out"])
            got = x_chunked(rec, j["seq"], [len(j["seq"])], {})
            wref = (ref.get("witness_relocations") or []) + ([ref["witness_connector"]] if ref.get("witness_connector") else [])
            out |= {"ref": {"x": ref.get("y"), "status": ref.get("teacher_status"), "witnesses": wref},
                    "got": {"x": got.get("x"), "status": got.get("teacher_status"), "witnesses": [w["witness"] for w in got.get("trace", [])]}}
            out["parity"] = out["ref"] == out["got"]
        elif j["kind"] == "Y_TEMP_PARITY":                           # bd_2d.t_goal vs generic_goal(t0, goal) with the production key
            cells = {**bd.cells0(rec), **{o: int(d) for o, d in j.get("edit", [])}}
            ref = y_temp(rec, cells, "t0", rec["goal_cell"], {})
            got = y_temp(rec, cells, "t0", rec["goal_cell"], {}, parity_key=True)
            out |= {"ref": {k: ref.get(k) for k in ("y", "teacher_status", "witness")}, "got": {k: got.get(k) for k in ("y", "teacher_status", "witness")}}
            out["parity"] = out["ref"] == out["got"]
        elif j["kind"] == "REJECT":                                  # malformed / forbidden queries: never attempted, 0 planner calls
            fx = sorted(rec.get("fixed_ids") or [])
            mv = sorted(rec["roles"])
            cases = {"target_mover": [["t0", j["free"]]], "duplicate_object": [[mv[0], j["free"]], [mv[0], j["free2"]]],
                     "illegal_dest": [[mv[0], 10_000]], "fixed_mover": [[fx[0], j["free"]]] if fx else None}
            out["REJECT"] = {k: (reject(rec, [(o, int(d)) for o, d in v]) if v else "NO_FIXED_OBJECT_IN_ROOT") for k, v in cases.items()}
            cells = bd.cells0(rec)
            out["REJECT"]["temp_fixed"] = y_temp(rec, cells, fx[0], j["free"], {})["why"] if fx else "NO_FIXED_OBJECT_IN_ROOT"
            out["REJECT"]["temp_occupied"] = y_temp(rec, cells, mv[0], cells[mv[1]], {})["why"]
        elif j["kind"] == "Y_TT":                                    # reference: TT_ADAPTER_V1 record + unchanged bxy_teacher.y_query
            import tt_adapter as TT
            edit = [(o, int(d)) for o, d in j.get("edit", [])]
            assert all(o not in (j["target"], "t0") for o, _ in edit), "edits never move the temporary or the original target"
            rawT = TT.adapt(rec, "2d", j["target"], j["goal"])
            r = T.y_query(M["E"], rawT["ids"]["root_id"], rawT, edit, {}, out=M["out"])
            out["Y"] = {"y": r.get("y"), "teacher_status": r.get("teacher_status"), "witness": r.get("target_witness"), "why": r.get("why"),
                        "independent_replay": r.get("independent_replay"), "path": "TT_ADAPTER_V1 + bxy_teacher.y_query", "tt_root": rawT["ids"]["root_id"]}
        elif j["kind"] == "Y_TEMP":
            cells = {**bd.cells0(rec), **{o: int(d) for o, d in j.get("edit", [])}}
            out["Y"] = y_temp(rec, cells, j["target"], j["goal"], {})
        else:
            cache = {}
            x = x_chunked(rec, j["seq"], j["bounds"], cache)
            out["X"] = x
            if j.get("y_endpoint"):
                cells = {**bd.cells0(rec), **{o: int(d) for o, d in j["seq"]}}
                out["Y"] = y_temp(rec, cells, "t0", rec["goal_cell"], cache)
            if j.get("fixture") == "drop_inner_connectors" and x.get("x") == 1:
                out["FIXTURE"] = {"declared": "inner connectors removed; replay must refuse (discontinuous state)"}
                out["FIXTURE"]["replay"] = _drop_fixture(rec, j["seq"], j["bounds"], cache)
    except Exception as e:  # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {str(e)[:200]}"; out["trace"] = traceback.format_exc()[-800:]
    out.update(cpu_s=round(time.process_time() - c0, 1), wall_s=round(time.time() - t0, 1), utc=time.strftime("%FT%TZ", time.gmtime()))
    return out


def _drop_fixture(rec, seq, bounds, cache):
    """Rebuild the same plan from the shared exact cache (no new planning) and replay with every inner connector removed: must fail."""
    T, pc, bd = M["T"], M["pc"], M["bd"]
    phys = T._phys(rec["ids"]["root_id"], rec, cache)
    cells, q, items = bd.cells0(rec), T.qref(rec), []
    for j, (o, d) in enumerate([(o, int(d)) for o, d in seq]):
        e = pc.best_edge(phys.edges(cells, q, o, d))
        items.append({"kind": "move", "object": o, "dest": d, "rec": e[1][0]})
        cells, q = {**cells, o: d}, np.asarray(e[2], float)
        if j + 1 in set(bounds):
            conn, _ = _connector(phys, rec, cells, q)
            items.append({"kind": "connector", "after_move": j + 1, "rec": conn})
            q = np.asarray(conn["q"][-1], float)
    inner = [i for i, it in enumerate(items) if it["kind"] == "connector"][:-1]
    bad = [it for i, it in enumerate(items) if i not in inner]
    r = replay_xb(rec, [(o, int(d)) for o, d in seq], bounds, bad)
    return {"ok": r["ok"], "why": r["why"], "removed": len(inner)}


def work(jobs_file, outp, workers, cpu_lo, max_jobs, max_cpu_h):
    import multiprocessing as mp
    out = Path(outp)
    prior = [json.loads(l) for l in open(out)] if out.exists() else []
    used = {"jobs": len(prior), "cpu_s": sum(p.get("cpu_s", 0) for p in prior)}
    todo = [j for j in json.loads(Path(jobs_file).read_text()) if j["key"] not in {p["key"] for p in prior}]
    os.sched_setaffinity(0, set(range(int(cpu_lo), int(cpu_lo) + int(workers))))
    pool = mp.get_context("spawn").Pool(int(workers), maxtasksperchild=1)
    running, f, i = {}, open(out, "a"), 0
    while True:
        for k, (ar, t) in list(running.items()):
            if ar.ready():
                r = ar.get(); running.pop(k); f.write(json.dumps(r) + "\n"); f.flush()
                used["jobs"] += 1; used["cpu_s"] += r.get("cpu_s", 0)
                print(time.strftime("%H:%M:%S"), k, r.get("parity"), (r.get("X") or {}).get("x"), (r.get("Y") or {}).get("y"), r.get("error"), r.get("cpu_s"), flush=True)
        cpu_h = (used["cpu_s"] + sum(time.time() - t for _, t in running.values())) / 3600
        if cpu_h >= float(max_cpu_h) - 0.02:
            pool.terminate(); break
        if i < len(todo) and len(running) < int(workers) and used["jobs"] + len(running) < int(max_jobs) and cpu_h + (len(running) + 1) * 0.05 < float(max_cpu_h):
            j = todo[i]; i += 1; running[j["key"]] = (pool.apply_async(job, (j,)), time.time()); continue
        if not running:
            break
        time.sleep(2)
    for k, (_, t) in running.items():
        f.write(json.dumps({"key": k, "censored": True, "cpu_s": round(time.time() - t, 1)}) + "\n")
    print("P2D_DONE", json.dumps(used), "undispatched", len(todo) - i, flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(*sys.argv[2:8])
