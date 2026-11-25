#!/usr/bin/env python3
"""Evaluator only (never imported by the planner).  Physical adapter on the UNCHANGED SHELF66V3 3D teacher (fin3d / bd_3dt / bwlphys), seal /
job building and outcome summaries.

Physical X of an ordered sequence with boundary set B (indices after which the arm must return to q_ref = q_ready):
  settle(S0) at q_ready -> for each move: bd_3dt.query from the CURRENT arm state (first feasible side grasp, RRT 5000, seed 0) -> run_plan in
  MuJoCo -> bd_3dt.seq's checks (mover in its cell, |z_err| <= 1 cm, no other object changed cell) -> at every boundary
  bwlphys.connector (CONNECTOR_TO_QREADY_V1: plan_free_move to q_ready, execute, |dq| <= 0.02, nothing pushed > 4 mm, cells kept, nothing
  held, no robot-object contact).  Continuous = B {m} (= fin3d.run_x exactly); chunked = B {group ends}.  Robot state is carried between
  moves and through connectors (no reset, no teleport).  Y = fin3d.run_y (endpoint settled at q_ready, target query + execution).
Replay (fresh process): re-execute every stored move witness (bwlphys.move) and stored connector path in order, refusing a witness whose
first configuration does not match the current arm state (|dq| > 0.02: DISCONNECTED, never teleported), then the stored target witness
from the achieved final state.  Statuses: X/Y in {1, 0, None}; resolution EVALUATED / UNRESOLVED_ADMIN / UNRESOLVED_ERROR (missing).
    worker:  $PY3D evaluate_k45.py work JOBS.json OUT.jsonl WORKERS CPU_LO    (gvlab2, caps enforced at dispatch)"""
from __future__ import annotations

import collections, hashlib, json, os, sys, time, traceback
from pathlib import Path

EVAL_CAPS = {"jobs": 200, "cpu_h": 12.0, "workers": 16, "primary": 100}
TOL_Q = 0.02
W = {}


# ------------------------------------------------------------------------------------------------------------- physical worker (gvlab2)
def boot(store):
    os.environ["FIN3D_STORE"] = store
    sys.path.insert(0, os.environ["FIN3D_CODE"])
    import fin3d as F
    F.boot()
    A = F.Q._M["A"]
    TS = A.env()["TS"]
    cnt = {"plan_pick_place": 0, "plan_free_move": 0}
    for name in cnt:
        orig = getattr(TS.XArm7TableEnv, name)

        def wrap(self, *a, _o=orig, _n=name, **k):
            cnt[_n] += 1
            return _o(self, *a, **k)
        setattr(TS.XArm7TableEnv, name, wrap)
    W.update(F=F, A=A, S=TS, BP=F.M["BP"], store=F.Q._M["store"], cnt=cnt, base=Path(store))


def run_xb(rec, order, bounds):
    """Teacher X with explicit q_ref boundaries (bounds: sorted move counts after which the connector runs; last = len(order))."""
    A, S, BP, store = W["A"], W["S"], W["BP"], W["store"]
    objs, cells0 = rec["objects"], rec["initial_cells"]
    steps = [(o, tuple(d)) for o, d in order]
    e = A.build(objs, cells0)
    W["F"].Q._M["bc"].check_sequence(steps)
    A.settle(e, cells0)
    expected, trace = {k: tuple(v) for k, v in cells0.items()}, []
    for j, (o, d) in enumerate(steps):
        before = {n: e.cell_of(n) for n in e.obj_index if n != o}
        p, qi = A.query(e, o, d)
        if p is None:
            lab = A.label(None, qi)
            return {"x": 0, "phase": f"relocation:{j}", "status": lab.get("reason"), "negative_kind": lab.get("negative_kind"), "trace": trace}
        wid = A.witness(store, p)
        st = {"kind": "move", "object": o, "dest": list(d), "witness": wid, "grasp_id": qi["grasp_id"], "q_start": e.q_now().tolist()}
        try:
            e.run_plan(p)
        except S.GraspFailed as err:
            trace.append(st)
            return {"x": 0, "phase": f"relocation:{j}", "status": f"GRASP_FAILED:{str(err)[:60]}", "negative_kind": "OTHER_FAILURE", "trace": trace}
        h = next(x["height"] for x in objs if x["id"] == o)
        z = e.obj_pos(o)[2] - e.table_z - h / 2
        trace.append(st)
        if e.cell_of(o) != tuple(d) or abs(z) > 0.01 or any(e.cell_of(n) != before[n] for n in before):
            return {"x": 0, "phase": f"relocation:{j}", "status": "EXECUTION_NOT_VERIFIED", "negative_kind": "OTHER_FAILURE", "trace": trace}
        expected[o] = tuple(d)
        if j + 1 in bounds:
            c, path = BP.connector(e, S, expected)
            cw = None
            if path is not None:
                cw = store.witness({"connector_q": path})
            trace.append({"kind": "connector", "after_move": j + 1, "ok": c["ok"], "failure": c.get("failure"), "witness": cw, "dq_ready": c.get("dq_ready")})
            if not c["ok"]:
                return {"x": 0, "phase": f"boundary:{j + 1}", "status": c.get("failure"), "negative_kind": "NO_PLAN_FOUND" if not c.get("planned") else "OTHER_FAILURE", "trace": trace}
    return {"x": 1, "phase": None, "status": "VERIFIED", "trace": trace}


def replay(rec, res_x, y_witness):
    """Independent re-execution of the stored witnesses (no planning, no teleport); then the stored target witness from the achieved state."""
    A, S, BP = W["A"], W["S"], W["BP"]
    e = A.build(rec["objects"], rec["initial_cells"]); A.settle(e, rec["initial_cells"])
    expected = {k: tuple(v) for k, v in rec["initial_cells"].items()}
    out = []
    for st in res_x["trace"]:
        if st["kind"] == "move":
            w = BP.witness(st["witness"], W["base"])
            dq = float(abs(w["q"][0] - e.q_now()).max())
            if dq > TOL_Q:
                return {"replay": 0, "failure": "DISCONNECTED_START", "dq": dq, "steps": out}
            r = BP.move(e, S, rec, st["object"], tuple(st["dest"]), w, st["grasp_id"])
            out.append({"object": st["object"], "ok": r["ok"]})
            if not r["ok"]:
                return {"replay": 0, "failure": r.get("failure"), "steps": out}
            expected[st["object"]] = tuple(st["dest"])
        else:
            z = __import__("numpy").load(Path(W["base"]) / "witnesses" / st["witness"][:2] / f"{st['witness']}.npz")
            c, _ = BP.connector(e, S, expected, path=z["connector_q"])
            out.append({"connector": st["after_move"], "ok": c["ok"]})
            if not c["ok"]:
                return {"replay": 0, "failure": "CONNECTOR_REPLAY_FAILED", "steps": out}
    if y_witness:
        w = BP.witness(y_witness["witness"], W["base"])
        dq = float(abs(w["q"][0] - e.q_now()).max())
        if dq > TOL_Q:
            return {"replay": 0, "failure": "TARGET_DISCONNECTED_START", "dq": dq, "steps": out}
        r = BP.move(e, S, rec, "t0", tuple(rec["goal"]), w, y_witness["grasp_id"])
        return {"replay": int(r["ok"]), "failure": None if r["ok"] else "TARGET_REPLAY_" + str(r.get("failure")), "steps": out}
    return {"replay": None, "failure": "NO_TARGET_WITNESS", "steps": out}


def run_y_g(rec, cells):
    """fin3d.run_y + the target grasp id (needed for replay)."""
    A, S, store = W["A"], W["S"], W["store"]
    e = A.build(rec["objects"], rec["initial_cells"]); A.settle(e, {k: tuple(v) for k, v in cells.items()})
    p, qi = A.query(e, "t0", tuple(rec["goal"]))
    if p is None:
        lab = A.label(None, qi)
        return {"y": 0, "status": lab.get("reason"), "negative_kind": lab.get("negative_kind")}
    wid = A.witness(store, p)
    before = {n: e.cell_of(n) for n in e.obj_index if n != "t0"}
    try:
        e.run_plan(p)
    except S.GraspFailed as err:
        return {"y": 0, "status": f"GRASP_FAILED:{str(err)[:60]}", "negative_kind": "OTHER_FAILURE", "witness": wid, "grasp_id": qi["grasp_id"]}
    h = next(x["height"] for x in rec["objects"] if x["id"] == "t0")
    z = e.obj_pos("t0")[2] - e.table_z - h / 2
    ok = e.cell_of("t0") == tuple(rec["goal"]) and abs(z) <= 0.01 and all(e.cell_of(n) == before[n] for n in before)
    return {"y": int(ok), "status": "VERIFIED" if ok else "EXECUTION_NOT_VERIFIED", "negative_kind": None if ok else "OTHER_FAILURE", "witness": wid, "grasp_id": qi["grasp_id"]}


def job(j):
    F = W["F"]
    t0, c0, cnt0 = time.time(), time.process_time(), dict(W["cnt"])
    rec = json.loads(Path(j["path"]).read_text())
    out = {"key": j["key"], "root_id": j["root_id"], "mode": j["mode"]}
    try:
        if j["order"]:
            x = F.capped(run_xb, rec, j["order"], set(j["bounds"]))
        else:
            x = {"x": None, "resolution": "NOT_APPLICABLE"}
        out["X"] = x
        if j.get("y_cells") is not None:
            yc = j["y_cells"] if j["y_cells"] != "ENDPOINT" else {**{k: list(v) for k, v in rec["initial_cells"].items()}, **{o: list(d) for o, d in j["order"]}}
            out["Y"] = F.capped(run_y_g, rec, yc)
        if j.get("replay") and x.get("x") == 1 and out.get("Y", {}).get("y") == 1:
            out["REPLAY"] = F.capped(replay, rec, x, out["Y"])
            if j.get("fixture") == "drop_inner_connectors":                     # negative control: skip intermediate q_ref returns
                last = max(i for i, s in enumerate(x["trace"]) if s["kind"] == "connector")
                bad = {**x, "trace": [s for i, s in enumerate(x["trace"]) if s["kind"] == "move" or i == last]}
                out["FIXTURE_DISCONNECTED"] = F.capped(replay, rec, bad, out["Y"])
    except Exception as e:  # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {str(e)[:200]}"; out["trace"] = traceback.format_exc()[-600:]
    out.update(cpu_s=round(time.process_time() - c0, 1), wall_s=round(time.time() - t0, 1), planner_calls={k: W["cnt"][k] - cnt0[k] for k in cnt0},
               utc=time.strftime("%FT%TZ", time.gmtime()))
    return out


def work(jobs_file, outp, workers, cpu_lo):
    """Dispatcher: <= EVAL_CAPS jobs and worker CPU-h over ALL eval stages (ledger shared through OUT's directory), headroom per running job."""
    import multiprocessing as mp
    workers = min(int(workers), EVAL_CAPS["workers"])
    out = Path(outp); allf = sorted(out.parent.glob("eval_*.jsonl"))
    prior = [json.loads(l) for f in allf for l in open(f) if l.strip()]
    used = {"jobs": len(prior), "cpu_s": sum(p.get("cpu_s", 0) for p in prior)}
    done = {p["key"] for p in prior}
    todo = [j for j in json.loads(Path(jobs_file).read_text()) if j["key"] not in done]
    os.sched_setaffinity(0, set(range(int(cpu_lo), int(cpu_lo) + workers)))
    pool = mp.get_context("spawn").Pool(workers, initializer=boot, initargs=(os.environ["K45_STORE"],), maxtasksperchild=10)
    running, f, stop = {}, open(out, "a"), None
    i = 0
    while True:
        for k, (ar, t) in list(running.items()):
            if ar.ready():
                r = ar.get(); running.pop(k)
                f.write(json.dumps(r) + "\n"); f.flush(); os.fsync(f.fileno())
                used["jobs"] += 1; used["cpu_s"] += r.get("cpu_s", 0)
                print(f"{time.strftime('%H:%M:%S')} {k} X={r.get('X', {}).get('x')} Y={r.get('Y', {}).get('y')} R={r.get('REPLAY', {}).get('replay')} "
                      f"cpu={r.get('cpu_s')} used={used['jobs']}J/{used['cpu_s'] / 3600:.2f}h", flush=True)
        cpu_h = (used["cpu_s"] + sum(time.time() - t for _, t in running.values())) / 3600
        if cpu_h >= EVAL_CAPS["cpu_h"] - 0.05:
            stop = "CAP_HARD_STOP"; pool.terminate(); break
        if i < len(todo) and len(running) < workers and used["jobs"] + len(running) < EVAL_CAPS["jobs"] and cpu_h + (len(running) + 1) * 0.25 < EVAL_CAPS["cpu_h"] \
                and not (out.parent / "STOP").exists():
            j = todo[i]; i += 1
            running[j["key"]] = (pool.apply_async(job, (j,)), time.time())
            continue
        if not running:
            stop = "ALL_DISPATCHED" if i >= len(todo) else "CAP_OR_STOP"
            break
        time.sleep(3)
    for k, (_, t) in running.items():
        f.write(json.dumps({"key": k, "censored": True, "reason": "CENSORED_AT_CAP", "wall_s": round(time.time() - t, 1)}) + "\n")
    f.close()
    print("EVAL_DONE", stop, json.dumps(used), "undispatched", len(todo) - i, flush=True)


# ------------------------------------------------------------------------------------------------------------- local side (laptop)
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def outcome(r):
    """Per-job strict outcome: SUCCESS (X = Y = 1 decided), FAIL_X / FAIL_Y (certified-by-teacher-contract 0), UNKNOWN (unresolved / missing)."""
    if r is None or r.get("censored") or r.get("error"):
        return "UNKNOWN"
    x, y = r.get("X") or {}, r.get("Y") or {}
    xv = x.get("x") if x.get("resolution") == "EVALUATED" else None
    yv = y.get("y") if y.get("resolution") == "EVALUATED" else None
    if yv == 0:
        return "FAIL_Y"
    if xv == 1 and yv == 1:
        return "SUCCESS"
    if xv == 0:
        return "FAIL_X"
    return "UNKNOWN"


PRIV = Path.home() / "k45_private"
GV = "/home/projects/long-horizon/naren_workspace/k45"
ARMS = ["B0", "B1", "B2", "B3", "B4"]


def seal(pred, public, out):
    """Seal the public-only predictions (before ANY physical evaluation of them)."""
    recs = [json.loads(l) for l in open(pred)]
    for r in recs:
        assert sorted(p["arm"] for p in r["plans"]) == ARMS, "one committed plan per root and arm"
    s = {"predictions": Path(pred).name, "sha256": sha(pred), "n_roots": len(recs), "public_sha256": sha(public),
         "decisions": dict(collections.Counter(f"{p['arm']}:{p['decision']}:{len(p['seq'] or [])}" for r in recs for p in r["plans"])),
         "sealed_utc": time.strftime("%FT%TZ", time.gmtime())}
    Path(out).write_text(json.dumps(s, indent=1))
    return s


def ids_of(public):
    return {r["root_id"]: r["inputs"]["ids"] for r in map(json.loads, open(public))}


def cell_rc(c):
    return [int(c) // 6, int(c) % 6]


def primary_jobs(pred, public, index):
    """Unique (root, ordered seq, boundary set) physical jobs of the sealed REPAIR plans; Y once per endpoint; fixed order (root, arm)."""
    ids = ids_of(public); idx = {e["root_id"]: e for e in map(json.loads, open(index))}
    jobs, seen, yseen, plan_job = [], {}, set(), {}
    for r in sorted((json.loads(l) for l in open(pred)), key=lambda r: r["root_id"]):
        rid = r["root_id"]
        for p in sorted(r["plans"], key=lambda p: p["arm"]):
            if p["decision"] != "REPAIR":
                continue
            seq = p["seq"]; m = len(seq)
            bounds = [m] if p["arm"] in ("B0", "B1") else [int(x) for x in itertools.accumulate(p["partition"] or [m])]
            order = [[ids[rid][int(o)], cell_rc(d)] for o, d in seq]
            key = f"primary|{rid}|{json.dumps(order)}|{json.dumps(bounds)}"
            ep = json.dumps(sorted(order))
            if key not in seen:
                seen[key] = True
                jobs.append({"key": key, "root_id": rid, "mode": "continuous" if bounds == [m] else "chunked", "path": f"{GV}/gen/roots/{rid}.json",
                             "order": order, "bounds": bounds, "replay": True, "y_cells": "ENDPOINT" if (rid, ep) not in yseen else None, "y_endpoint": ep})
                yseen.add((rid, ep))
            plan_job[(rid, p["arm"])] = key
    return jobs, plan_job


def merged(results):
    """Per job outcome with the endpoint Y shared across jobs of the same (root, endpoint)."""
    by = {r["key"]: r for r in results if "key" in r}
    ys = {}
    for k, r in by.items():
        if r.get("Y") is not None:
            ys[(r["root_id"], json.dumps(sorted(json.loads(k.split("|")[2]))))] = r["Y"]
    out = {}
    for k, r in by.items():
        if r.get("censored"):
            out[k] = {**r, "X": {}, "Y": {}}; continue
        y = r.get("Y") or ys.get((r["root_id"], json.dumps(sorted(json.loads(k.split("|")[2])))))
        out[k] = {**r, "Y": y or {}}
    return out


import itertools  # noqa: E402


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(*sys.argv[2:6])
