#!/usr/bin/env python3
"""Finalized Approach-B X/Y check on accepted 2D hard-order roots (diagnostic sidecar; nothing promoted into any dataset).
X  = BXY_X_TEACHER_V1 (bxy_teacher.x_query): ordered relocations with carried robot state + connector to q_ref (= rec q0) + independent replay.
Y  = BXY_Y_TEACHER_V1 (bxy_teacher.y_query): target from q_ref in the endpoint scene + independent replay.  All 6 orders of one assignment
     reach the same endpoint, so they share ONE Y.  Same pinned bd_2d / p16 code as perm2d (byte-identical; fastgeom1 to rounding).
  xy2d.py ROOT_JSON_LIST.json OUT.jsonl WORKERS"""
import itertools, json, os, sys, time, traceback
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H.parent.parent / "order_classification_2d"))
import perm2d as P  # noqa: E402

WT = H.parent.parent / ".claude/worktrees/approach-b-xy-v1"
WOUT = H / "xy2d_witnesses"
M = {}


def boot():
    P.boot("fastgeom1")
    sys.path.insert(0, str(WT))
    import bxy_teacher as T
    M.update(T=T, E=T.env())


def job(path):
    t0 = time.process_time()
    rec = json.loads(Path(path).read_text())
    rid = rec["ids"]["root_id"]
    out = {"root_id": rid, "legacy_n_success": rec["n_success"], "legacy": {}}
    try:
        T, E = M["T"], M["E"]
        cache = {}
        mini = next(b for b in rec["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1)
        assign = [(o, int(d)) for o, d in mini["sequence"]]
        leg = {tuple(o for o, _ in p["order"]): p["y"] for p in rec["permutations"]}
        xs = {}
        for q in itertools.permutations(assign):
            r = T.x_query(E, rid, rec, list(q), cache, out=str(WOUT))
            key = "".join(o[-1] for o, _ in q)
            xs[key] = {"x": r.get("y"), "status": r.get("teacher_status"), "phase": r.get("failed_phase"), "replay": r.get("independent_replay")}
            out["legacy"][key] = leg[tuple(o for o, _ in q)]
        y = T.y_query(E, rid, rec, assign, cache, out=str(WOUT))
        out.update(x=xs, y={"y": y.get("y"), "status": y.get("teacher_status"), "replay": y.get("independent_replay")},
                   x_n_success=sum(v["x"] == 1 for v in xs.values()), x_unresolved=sum(v["x"] not in (0, 1) for v in xs.values()))
    except Exception as e:  # noqa: BLE001
        out.update(error=f"{type(e).__name__}: {str(e)[:200]}", trace=traceback.format_exc()[-800:])
    out["cpu_s"] = round(time.process_time() - t0, 1)
    return out


if __name__ == "__main__":
    import multiprocessing as mp
    assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
    roots, outp, workers = json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2]), int(sys.argv[3])
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[-workers:])
    done = {json.loads(l)["root_id"] for l in outp.read_text().splitlines()} if outp.exists() else set()
    todo = [r for r in roots if Path(r).stem not in done]
    with open(outp, "a", buffering=1) as f, mp.get_context("spawn").Pool(workers, initializer=boot) as pool:
        for r in pool.imap_unordered(job, todo):
            f.write(json.dumps(r) + "\n"); f.flush()
