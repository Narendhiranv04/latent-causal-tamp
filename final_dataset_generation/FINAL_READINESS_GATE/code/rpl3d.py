#!/usr/bin/env python3
"""FINAL_READINESS_GATE: independent fresh-environment REPLAY audit of FINAL_3D_DATASET_V4 X / Y labels (3D shelf, SHELF66V3, mujoco 3.16.0).

Replay path (no planning for positives; the teacher's stored verdicts are never read by the replay):
  scene      the selected root JSON (immutable source; sha256 checked against the selection manifest), A.build + A.settle in a NEW env.
  X          settle(S0) at q_ready -> per relocation: load the stored witness (content id re-derived: bwlphys.witness), check continuity
             (witness q[0] == current q), recover the grasp by forward kinematics of the stored grasp configuration (end of the 'approach'
             segment) against the object's candidate grasp poses (pos <= 5 mm, angle <= 3 deg, unique open width), execute it with the
             pinned bwlphys.move (bd_3dt.seq checks: end cell, |z| <= 1 cm, no other object changed cell), carried state, no reset ->
             stored connector path executed with bwlphys.connector(path=...) (CONNECTOR_TO_QREADY_V1 checks: |q - q_ref| <= 0.02 rad, nothing
             pushed > 4 mm, every object in its endpoint cell, nothing held, gripper opened, no robot-object contact) + path end == q_ref.
  Y          settle(endpoint) at q_ref -> stored target witness, same grasp recovery, bwlphys.move(t0 -> goal) (+ nothing held after).
  negatives  the stored prefix is replayed; a planning failure is RE-CONFIRMED by re-planning (bd_3dt.query / plan_free_move, seed 0) from
             the REPLAYED state; an execution failure is reproduced by replaying its stored witness.
  no stored witness (R1 gvlab V3 rows, R2 legacy-shortcut rows, R1 Y): the X / Y teacher (fin3d.run_x / run_y, unchanged) is re-run in this
             fresh process into a separate store (RERUN), then its witnesses are replayed in another new env as above.
  LEGACY     (diagnostic, omission rows only) perm3d.seq of the shortened order: relocations then T from the achieved pose.
  rpl3d.py run ITEMS.json OUT.jsonl WORKERS CPU_LO"""
import json, os, signal, sys, time, traceback
from pathlib import Path

H = Path(__file__).resolve().parent
G = H.parent.parent
V4 = G / "final3d_v4"
os.environ.setdefault("FIN3D_STORE", str(H.parent / "work/rpl_store"))
sys.path.insert(0, str(V4 / "code"))
STORES = [V4 / "work/store", V4 / "work/store_gvlab", G / "k3_hard/d3/store", Path(os.environ["FIN3D_STORE"])]
M = {}


def boot():
    import fin3d as F
    F.boot()
    if "boot_error" in F.Q._M:
        M["boot_error"] = F.Q._M["boot_error"]
        return
    import numpy as np
    M.update(F=F, A=F.Q._M["A"], BP=F.M["BP"], np=np)


def find_w(w):
    for st in STORES:
        if (st / "witnesses" / w[:2] / f"{w}.npz").exists():
            return M["BP"].witness(w, st)
    raise FileNotFoundError(f"WITNESS_MISSING {w}")


def grasp_of(e, S, name, w):
    """Index (in S.grasp_poses order, as bd_3dt.query / bwlphys.segments use) of the grasp whose pose the stored grasp configuration reaches."""
    np = M["np"]
    i = e.obj_id(name)
    e._focus(i)
    e.objects[i]["pos"] = e.obj_pos(i)
    gs = S.grasp_poses(e.objects[i], e.table_z)
    ph = [str(x) for x in w["phases"]]
    k = ph.index("approach")
    qg = w["q"][w["segment"] == k][-1]
    p, quat = e._fk(qg)
    best = []
    for g in gs:
        dp = float(np.linalg.norm(p - g["position"]))
        da = float(np.degrees(2 * np.arccos(min(1.0, abs(float(np.dot(quat, g["quat"])))))))
        best.append((dp + 0.001 * da, dp, da, g["id"], g["open_width"]))
    best.sort()
    ok = [b for b in best if b[1] <= 0.005 and b[2] <= 3.0]
    if not ok:
        return None, {"grasp_match": "NONE", "best_dp_mm": round(best[0][1] * 1000, 3), "best_da_deg": round(best[0][2], 3)}
    if max(b[4] for b in ok) - min(b[4] for b in ok) > 1e-9:
        return None, {"grasp_match": "AMBIGUOUS_WIDTH", "n": len(ok)}
    return ok[0][3], {"grasp_match": "OK", "dp_mm": round(ok[0][1] * 1000, 3), "da_deg": round(ok[0][2], 3), "n_match": len(ok)}


def replay_move(e, S, rec, name, dest, w):
    np = M["np"]
    cont = float(np.max(np.abs(w["q"][0] - e.q_now())))
    gid, gm = grasp_of(e, S, name, w)
    if gid is None:
        return {"ok": False, "failure": "GRASP_RECOVERY_FAILED", "continuity": cont, **gm}
    r = M["BP"].move(e, S, rec, name, dest, w, gid)
    r.update(continuity=cont, grasp_id=gid, **gm)
    if cont > 1e-6:
        r.update(ok=False, failure="DISCONTINUOUS_ROBOT_STATE")
    if r["ok"] and r.get("held_after") is not None:
        r.update(ok=False, failure="OBJECT_STILL_HELD")
    r["pushed"] = [list(x) for x in (r.get("pushed") or [])]
    return r


def jd(x):
    return json.loads(json.dumps(x, default=lambda v: v.tolist() if hasattr(v, "tolist") else str(v)))


def replay_x(rec, order, wids):
    """-> {"x": 0/1, "phase": ..., ...} from the stored witnesses (+ re-confirmation of a planning failure)."""
    A, BP, np = M["A"], M["BP"], M["np"]
    S = A.env()["TS"]
    cells0 = {k: tuple(v) for k, v in rec["initial_cells"].items()}
    e = A.build(rec["objects"], rec["initial_cells"])
    A.settle(e, cells0)
    out = {"start_dq_ready": float(np.max(np.abs(e.q_now() - e.q_ready))), "steps": []}
    ws = [find_w(w) for w in wids]
    rel = [w for w in ws if "connector_q" not in w]
    con = [w for w in ws if "connector_q" in w]
    expected = dict(cells0)
    for j, (o, d) in enumerate(order):
        d = tuple(d)
        if j < len(rel):
            r = replay_move(e, S, rec, o, d, rel[j])
            out["steps"].append({k: r.get(k) for k in ("ok", "failure", "end_cell", "z_err", "displaced", "continuity", "grasp_id", "grasp_match", "dp_mm", "da_deg", "pushed")})
            if not r["ok"]:
                return {**out, "x": 0, "phase": f"relocation:{j}", "how": "REPLAYED_EXECUTION_FAILURE", "failure": r.get("failure")}
        else:
            p, qi = A.query(e, o, d)
            if p is None:
                return {**out, "x": 0, "phase": f"relocation:{j}", "how": "PLANNING_FAILURE_RECONFIRMED", "kind": A.kind(qi["grasp_reasons"])}
            return {**out, "x": None, "phase": f"relocation:{j}", "how": "PLAN_FOUND_WHERE_NO_WITNESS", "grasp_id": qi.get("grasp_id")}
        expected[o] = d
    if con:
        path = np.asarray(con[0]["connector_q"])
        start_dq = float(np.max(np.abs(path[0] - e.q_now())))
        c, _ = BP.connector(e, S, expected, path)
        end_dq = float(np.max(np.abs(path[-1] - e.q_ready)))
        ok = bool(c["ok"]) and end_dq <= 1e-9 and start_dq <= 1e-6
        out["connector"] = {**c, "path_end_vs_qref": end_dq, "path_start_vs_q": start_dq}
        return {**out, "x": int(ok), "phase": None if ok else "connector", "how": "REPLAYED_CONNECTOR"}
    c, _ = BP.connector(e, S, expected, None)                       # no stored connector: the teacher had no plan -> re-confirm
    out["connector"] = c
    if not c.get("planned", True):
        return {**out, "x": 0, "phase": "connector", "how": "CONNECTOR_NO_PLAN_RECONFIRMED"}
    return {**out, "x": None, "phase": "connector", "how": "CONNECTOR_PLAN_FOUND_WHERE_NO_WITNESS", "connector_ok": c["ok"]}


def replay_y(rec, cells, wids):
    A, np = M["A"], M["np"]
    S = A.env()["TS"]
    e = A.build(rec["objects"], rec["initial_cells"])
    A.settle(e, {k: tuple(v) for k, v in cells.items()})
    out = {"start_dq_ready": float(np.max(np.abs(e.q_now() - e.q_ready)))}
    if wids:
        r = replay_move(e, S, rec, "t0", tuple(rec["goal"]), find_w(wids[0]))
        out["step"] = {k: r.get(k) for k in ("ok", "failure", "end_cell", "z_err", "displaced", "continuity", "grasp_id", "grasp_match", "dp_mm", "da_deg", "pushed")}
        return {**out, "y": int(bool(r["ok"])), "how": "REPLAYED_TARGET" if r["ok"] else "REPLAYED_EXECUTION_FAILURE"}
    p, qi = A.query(e, "t0", tuple(rec["goal"]))
    if p is None:
        return {**out, "y": 0, "how": "PLANNING_FAILURE_RECONFIRMED", "kind": A.kind(qi["grasp_reasons"])}
    return {**out, "y": None, "how": "PLAN_FOUND_WHERE_NO_WITNESS"}


def one(q, rec):
    F = M["F"]
    res = {}
    if q["q"] == "X":
        wids = q.get("witnesses")
        if wids is None:                                            # RERUN: teacher in this fresh process, then replay its witnesses
            t = F.capped(F.run_x, rec, q["order"])
            res["rerun"] = {k: t.get(k) for k in ("x", "phase", "status", "resolution", "witnesses", "cpu_s")}
            if t.get("resolution") != "EVALUATED":
                return {**res, "replay": None, "verdict": "ADMIN_" + str(t.get("resolution"))}
            wids = t.get("witnesses") or []
        r = F.capped(replay_x, rec, q["order"], wids)
        res["replay"] = r
        lab = (q["label_x"], q.get("label_phase"))
        got = (r.get("x"), r.get("phase"))
        res["verdict"] = "AGREE" if r.get("resolution") == "EVALUATED" and got[0] == lab[0] and (lab[0] == 1 or (lab[1] or "") == (got[1] or "")) else \
            ("AGREE_VALUE_PHASE_DIFFERS" if got[0] == lab[0] else ("ADMIN_" + str(r.get("resolution")) if r.get("resolution") != "EVALUATED" else "MISMATCH"))
        if "rerun" in res:
            res["rerun_agrees_with_label"] = res["rerun"].get("x") == q["label_x"]
    elif q["q"] == "Y":
        wids = q.get("witnesses")
        if wids is None:
            t = F.capped(F.run_y, rec, q["cells"])
            res["rerun"] = {k: t.get(k) for k in ("y", "status", "resolution", "witnesses", "cpu_s")}
            if t.get("resolution") != "EVALUATED":
                return {**res, "replay": None, "verdict": "ADMIN_" + str(t.get("resolution"))}
            wids = t.get("witnesses") or []                         # [] = planning failure (re-confirmed by re-planning)
        r = F.capped(replay_y, rec, q["cells"], wids)
        res["replay"] = r
        res["verdict"] = "AGREE" if r.get("resolution") == "EVALUATED" and r.get("y") == q["label_y"] else \
            ("ADMIN_" + str(r.get("resolution")) if r.get("resolution") != "EVALUATED" else "MISMATCH")
        if "rerun" in res:
            res["rerun_agrees_with_label"] = res["rerun"].get("y") == q["label_y"]
    elif q["q"] == "LEGACY":
        res["legacy"] = F.capped(F.legacy_one, rec, q["order"])
        res["verdict"] = "DIAGNOSTIC"
    return res


def job(it):
    out = {"key": it["key"], "root_id": it["root_id"], "results": []}
    if "boot_error" in M:
        return {**out, "error": "boot: " + M["boot_error"]}
    M["F"].guard()
    import hashlib
    raw = Path(it["path"]).read_bytes()
    out["root_sha256_ok"] = it.get("root_sha256") is None or hashlib.sha256(raw).hexdigest() == it["root_sha256"]
    rec = json.loads(raw)
    c0 = time.process_time()
    for q in it["queries"]:
        try:
            r = one(q, rec)
        except Exception as e:  # noqa: BLE001
            r = {"verdict": "ERROR", "error": f"{type(e).__name__}: {str(e)[:200]}", "trace": traceback.format_exc()[-600:]}
        out["results"].append(jd({**q, **r}))
    out["cpu_s"] = round(time.process_time() - c0, 1)
    return out


if __name__ == "__main__":
    import multiprocessing as mp
    assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
    items, outp, workers, lo = json.loads(Path(sys.argv[2]).read_text()), Path(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    os.sched_setaffinity(0, set(range(lo, lo + workers)))
    done = {json.loads(l)["key"] for l in outp.read_text().splitlines() if l.strip()} if outp.exists() else set()
    todo = [it for it in items if it["key"] not in done]
    print(f"{time.strftime('%FT%TZ', time.gmtime())} rpl3d items={len(todo)} workers={workers}", flush=True)
    with open(outp, "a", buffering=1) as f, mp.get_context("spawn").Pool(workers, initializer=boot, maxtasksperchild=20) as pool:
        for i, r in enumerate(pool.imap_unordered(job, todo), 1):
            f.write(json.dumps(r) + "\n"); f.flush(); os.fsync(f.fileno())
            if i % 10 == 0 or i == len(todo):
                print(f"{time.strftime('%FT%TZ', time.gmtime())} {i}/{len(todo)}", flush=True)
            if (outp.parent / "STOP3D").exists():
                print("STOP3D file: exiting", flush=True); pool.terminate(); break
