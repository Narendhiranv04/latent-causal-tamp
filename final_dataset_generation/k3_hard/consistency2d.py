#!/usr/bin/env python3
"""Fail-closed consistency gate for accepted 2D hard-order roots (same rule as hard3d.finish_checked): every order whose label came from
bd_2d.teach ("source": "teacher") is re-executed with perm2d.evaluate on a FRESH cache; the root passes only if every y agrees.
  consistency2d.py OUT.jsonl WORKERS STORE_DIR [STORE_DIR ...]"""
import json, os, sys, time
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H.parent.parent / "order_classification_2d"))
import perm2d as P  # noqa: E402

SCRATCH = H / "consistency2d_scratch"


def boot():
    P.boot("fastgeom1")
    if "boot_error" not in P._M:
        P._M["store"] = P._M["bc"].Store(SCRATCH)


def job(path):
    rec = json.loads(Path(path).read_text())
    task = {"scene": rec["scene"], "goal_cell": rec["goal_cell"], "fixed_ids": [], "target": "t0", "key": rec["ids"]["root_id"]}
    out, t0 = {"root_id": rec["ids"]["root_id"], "checked": []}, time.process_time()
    for p in rec["permutations"]:
        if p["source"] != "teacher":
            continue
        e = P.evaluate(task, {}, [(o, int(d)) for o, d in p["order"]])
        out["checked"].append({"order": [o for o, _ in p["order"]], "teacher_y": p["y"], "fresh_y": e.get("y")})
    out["consistent"] = all(c["teacher_y"] == c["fresh_y"] for c in out["checked"])
    out["cpu_s"] = round(time.process_time() - t0, 1)
    return out


if __name__ == "__main__":
    import multiprocessing as mp
    assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
    outp, workers = Path(sys.argv[1]), int(sys.argv[2])
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:workers])
    done = {json.loads(l)["root_id"] for l in outp.read_text().splitlines()} if outp.exists() else set()
    todo = [str(f) for d in sys.argv[3:] for f in sorted(Path(d, "roots").glob("D2H_*.json")) if f.stem not in done]
    with open(outp, "a", buffering=1) as f, mp.get_context("spawn").Pool(workers, initializer=boot) as pool:
        for r in pool.imap_unordered(job, todo):
            f.write(json.dumps(r) + "\n"); f.flush()
    print("checked", len(todo))
