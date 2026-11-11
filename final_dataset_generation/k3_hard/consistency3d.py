#!/usr/bin/env python3
"""Fail-closed teacher-vs-fresh-env gate for 3D roots built BEFORE hard3d.finish_checked existed (the DEPSEEK V1 children that the
V3 selection may use): every order whose label came from bd_3dt.teach ("source": "teacher") is re-executed with perm3d.seq on a FRESH
MuJoCo env; the root passes only if every y agrees (same rule as hard3d.finish_checked).  Read-only on the roots; witnesses of the
re-execution go to a scratch store.
  consistency3d.py DATASET_DIR ROOT_JSON_DIR OUT.jsonl WORKERS CPUS(a-b)"""
import json, os, sys, time, traceback
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import perm3d as Q  # noqa: E402


def boot(ds, scratch):
    Q.DS, Q.CODE, Q.OUT = Path(ds), Path(ds) / "code", Path(scratch)
    Q.boot()
    if "boot_error" not in Q._M:
        Q._M["store"] = Q._M["bc"].Store(Path(scratch) / "store")


def job(path):
    t0 = time.process_time()
    rec = json.loads(Path(path).read_text())
    out = {"root_id": rec["ids"]["root_id"], "checked": []}
    try:
        if "boot_error" in Q._M:
            raise RuntimeError("boot: " + Q._M["boot_error"])
        for p in rec["permutations"]:
            if p.get("source") != "teacher":
                continue
            r = Q.seq(rec, [(o, tuple(d)) for o, d in p["order"]])
            out["checked"].append({"order": [o for o, _ in p["order"]], "teacher_y": p["y"], "fresh_y": r.get("y"), "reason": str(r.get("reason"))[:100]})
        out["consistent"] = all(c["teacher_y"] == c["fresh_y"] for c in out["checked"])
    except Exception as e:  # noqa: BLE001
        out.update(consistent=None, error=f"{type(e).__name__}: {str(e)[:200]}", trace=traceback.format_exc()[-800:])
    out["cpu_s"] = round(time.process_time() - t0, 1)
    return out


if __name__ == "__main__":
    import multiprocessing as mp
    assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
    ds, rdir, outp, workers, cpus = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    a, b = map(int, cpus.split("-"))
    os.sched_setaffinity(0, set(range(a, b + 1)))
    done = {json.loads(l)["root_id"] for l in outp.read_text().splitlines()} if outp.exists() else set()
    todo = [str(f) for f in sorted(rdir.glob("*.json")) if f.stem not in done]
    with open(outp, "a", buffering=1) as f, mp.get_context("spawn").Pool(workers, initializer=boot, initargs=(ds, str(outp.parent / "consistency3d_scratch"))) as pool:
        for r in pool.imap_unordered(job, todo):
            f.write(json.dumps(r) + "\n"); f.flush()
    print("checked", len(todo))
