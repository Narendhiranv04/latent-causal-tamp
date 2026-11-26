#!/usr/bin/env python3
"""3D physical adapter (evaluator only; gvlab2 env3d) on the UNCHANGED SHELF66V3 teacher (fin3d / bd_3dt / bwlphys) via compose3d_k45's
audited `run_xb` (relocations from the carried arm state; planned + executed CONNECTOR_TO_QREADY_V1 at every declared boundary).

New here (amendment R1b): every target-dependent step is parameterized by (target_id, goal_rc) instead of the hard-coded "t0":
  y_target(rec, cells, target, goal)  = bd_3dt.query(e, target, goal) from q_ready in the settled scene `cells` + run_plan + seq()'s checks
                                        (identical to fin3d.run_y when target = "t0", goal = rec["goal"]).  All other bodies, including the
                                        ORIGINAL target, stay present as ordinary collision bodies.
  replay(..., target, goal)           = stored move witnesses + stored connector paths + stored target witness of `target` from the achieved
                                        state; refuses any discontinuous start (no teleport).
Job kinds: Y_TARGET {cells, target, goal}; X_CHUNKED {order, bounds, cells0 (optional hypothetical start), y: {target, goal} | null}.
    python physical3d.py work JOBS.json OUT.jsonl WORKERS CPU_LO MAX_JOBS MAX_CPU_H"""
from __future__ import annotations

import json, os, sys, time, traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "compose3d_k45"))
import evaluate_k45 as EV  # noqa: E402  (importable by name: spawn workers pickle EV.boot)
TOL_Q = 0.02


def y_target(rec, cells, target, goal):
    W = EV.W; A, S, store = W["A"], W["S"], W["store"]
    e = A.build(rec["objects"], rec["initial_cells"]); A.settle(e, {k: tuple(v) for k, v in cells.items()})
    p, qi = A.query(e, target, tuple(goal))
    if p is None:
        lab = A.label(None, qi)
        return {"y": 0, "status": lab.get("reason"), "negative_kind": lab.get("negative_kind"), "target": target, "goal": list(goal)}
    wid = A.witness(store, p)
    before = {n: e.cell_of(n) for n in e.obj_index if n != target}
    try:
        e.run_plan(p)
    except S.GraspFailed as err:
        return {"y": 0, "status": f"GRASP_FAILED:{str(err)[:60]}", "negative_kind": "OTHER_FAILURE", "witness": wid, "grasp_id": qi["grasp_id"], "target": target}
    h = next(x["height"] for x in rec["objects"] if x["id"] == target)
    z = e.obj_pos(target)[2] - e.table_z - h / 2
    ok = e.cell_of(target) == tuple(goal) and abs(z) <= 0.01 and all(e.cell_of(n) == before[n] for n in before)
    return {"y": int(ok), "status": "VERIFIED" if ok else "EXECUTION_NOT_VERIFIED", "negative_kind": None if ok else "OTHER_FAILURE",
            "witness": wid, "grasp_id": qi["grasp_id"], "target": target, "goal": list(goal)}


def replay(rec, res_x, yw, target, goal):
    """Independent re-execution of stored witnesses (moves, connectors, then the target witness of `target` from the achieved state)."""
    import numpy as np
    W = EV.W; A, S, BP = W["A"], W["S"], W["BP"]
    e = A.build(rec["objects"], rec["initial_cells"]); A.settle(e, rec["initial_cells"])
    expected = {k: tuple(v) for k, v in rec["initial_cells"].items()}
    steps = []
    for st in res_x["trace"]:
        if st["kind"] == "move":
            w = BP.witness(st["witness"], W["base"])
            dq = float(abs(w["q"][0] - e.q_now()).max())
            if dq > TOL_Q:
                return {"replay": 0, "failure": "DISCONNECTED_START", "dq": dq, "steps": steps}
            r = BP.move(e, S, rec, st["object"], tuple(st["dest"]), w, st["grasp_id"])
            steps.append({"object": st["object"], "ok": r["ok"], "q_end": e.q_now().tolist()})
            if not r["ok"]:
                return {"replay": 0, "failure": r.get("failure"), "steps": steps}
            expected[st["object"]] = tuple(st["dest"])
        else:
            z = np.load(Path(W["base"]) / "witnesses" / st["witness"][:2] / f"{st['witness']}.npz")
            c, _ = BP.connector(e, S, expected, path=z["connector_q"])
            steps.append({"connector": st["after_move"], "ok": c["ok"], "dq_ready": c.get("dq_ready"), "path": z["connector_q"].tolist()})
            if not c["ok"]:
                return {"replay": 0, "failure": "CONNECTOR_REPLAY_FAILED", "steps": steps}
    if not yw:
        return {"replay": 1, "failure": None, "steps": steps, "note": "no target witness requested"}
    w = BP.witness(yw["witness"], W["base"])
    dq = float(abs(w["q"][0] - e.q_now()).max())
    if dq > TOL_Q:
        return {"replay": 0, "failure": "TARGET_DISCONNECTED_START", "dq": dq, "steps": steps}
    r = BP.move(e, S, rec, target, tuple(goal), w, yw["grasp_id"])
    return {"replay": int(r["ok"]), "failure": None if r["ok"] else "TARGET_REPLAY_" + str(r.get("failure")), "steps": steps}


def job(j):
    F = EV.W["F"]
    t0, c0, cnt0 = time.time(), time.process_time(), dict(EV.W["cnt"])
    rec = json.loads(Path(j["path"]).read_text())
    if j.get("cells0"):                                                          # hypothetical pre-action start scene (local diagnostic)
        rec = {**rec, "initial_cells": {k: list(v) for k, v in j["cells0"].items()}}
    out = {"key": j["key"], "kind": j["kind"]}
    try:
        if j["kind"] == "Y_TT":                                                     # reference: TT_ADAPTER_V1 record + unchanged run_y
            sys.path.insert(0, str(HERE))
            import tt_adapter as TT
            A = j["target"]
            rawT = TT.adapt(rec, "3d", A, j["goal"][0] * 6 + j["goal"][1])
            cells = {k: list(v) for k, v in j["cells"].items()}
            cells["t0"], cells[A] = cells[A], cells["t0"]
            out["Y"] = {**F.capped(EV.run_y_g, rawT, cells), "path": "TT_ADAPTER_V1 + evaluate_k45.run_y_g", "tt_root": rawT["ids"]["root_id"]}
        elif j["kind"] == "Y_TARGET":
            out["Y"] = F.capped(y_target, rec, j["cells"], j["target"], j["goal"])
        else:
            x = F.capped(EV.run_xb, rec, j["order"], set(j["bounds"]))
            out["X"] = x
            if j.get("y"):
                cells = {**{k: list(v) for k, v in rec["initial_cells"].items()}, **{o: list(d) for o, d in j["order"]}}
                out["Y"] = F.capped(y_target, rec, cells, j["y"]["target"], j["y"]["goal"])
            if x.get("x") == 1 and (not j.get("y") or out["Y"].get("y") == 1):
                yt = j.get("y") or {}
                out["REPLAY"] = F.capped(replay, rec, x, out.get("Y"), yt.get("target"), yt.get("goal"))
                if j.get("fixture") == "drop_inner_connectors":                # negative control: skip intermediate q_ref returns
                    last = max(i for i, s in enumerate(x["trace"]) if s["kind"] == "connector")
                    bad = {**x, "trace": [s for i, s in enumerate(x["trace"]) if s["kind"] == "move" or i == last]}
                    out["FIXTURE_DISCONNECTED"] = F.capped(replay, rec, bad, out.get("Y"), yt.get("target"), yt.get("goal"))
    except Exception as e:  # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {str(e)[:200]}"; out["trace"] = traceback.format_exc()[-600:]
    out.update(cpu_s=round(time.process_time() - c0, 1), wall_s=round(time.time() - t0, 1),
               planner_calls={k: EV.W["cnt"][k] - cnt0[k] for k in cnt0}, utc=time.strftime("%FT%TZ", time.gmtime()))
    return out


def work(jobs_file, outp, workers, cpu_lo, max_jobs, max_cpu_h):
    import multiprocessing as mp
    out = Path(outp)
    prior = [json.loads(l) for l in open(out)] if out.exists() else []
    used = {"jobs": len(prior), "cpu_s": sum(p.get("cpu_s", 0) for p in prior)}
    todo = [j for j in json.loads(Path(jobs_file).read_text()) if j["key"] not in {p["key"] for p in prior}]
    os.sched_setaffinity(0, set(range(int(cpu_lo), int(cpu_lo) + int(workers))))
    pool = mp.get_context("spawn").Pool(int(workers), initializer=EV.boot, initargs=(os.environ["FIG3_STORE"],), maxtasksperchild=10)
    running, f, i = {}, open(out, "a"), 0
    while True:
        for k, (ar, t) in list(running.items()):
            if ar.ready():
                r = ar.get(); running.pop(k); f.write(json.dumps(r) + "\n"); f.flush()
                used["jobs"] += 1; used["cpu_s"] += r.get("cpu_s", 0)
                print(time.strftime("%H:%M:%S"), k, (r.get("X") or {}).get("x"), (r.get("Y") or {}).get("y"), (r.get("REPLAY") or {}).get("replay"), r.get("cpu_s"), flush=True)
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
    print("P3D_DONE", json.dumps(used), "undispatched", len(todo) - i, flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(*sys.argv[2:8])
