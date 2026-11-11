#!/usr/bin/env python3
"""Stage 2 (2026-11-10, laptop only): the 4 remaining permutations of the 228 selected K3 scenes that were already order-dependent.
Thin wrapper over perm2d.py (unchanged, same pinned teacher path); writes ONLY to new directories:
  out/repro2/results.jsonl   reproduction of recorded outcomes (sample from the 228 scenes)
  out/run228/results.jsonl   six-permutation records of the 228 scenes (2 historical + 4 new each)
Run with PYTHONDONTWRITEBYTECODE=1 (no bytecode caches in the dataset's code dir)."""
import json, multiprocessing as mp, os, sys, time
from pathlib import Path

import perm2d as P


def drive_repro(items, workers, name="repro2"):
    d = P.OUT / name
    d.mkdir(parents=True, exist_ok=True)
    res = d / "results.jsonl"
    done = {json.dumps([x["root_id"], x["role"]]) for x in map(json.loads, res.read_text().splitlines())} if res.exists() else set()
    by = {}
    for rid, role in items:
        if json.dumps([rid, role]) not in done:
            by.setdefault(P.record(rid).get("geometry_impl") or "original", []).append((rid, role))
    with open(res, "a", buffering=1) as f:
        for geom, its in sorted(by.items()):
            print(f"{time.strftime('%FT%TZ', time.gmtime())} {name} geom={geom} items={len(its)}", flush=True)
            with mp.get_context("spawn").Pool(workers, initializer=P.boot, initargs=(geom,)) as pool:
                for r in pool.imap_unordered(P.job_repro, its):
                    f.write(json.dumps(r) + "\n")
                    f.flush()
                    os.fsync(f.fileno())


if __name__ == "__main__":
    assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1", "set PYTHONDONTWRITEBYTECODE=1"
    mode, items, workers = sys.argv[1], json.loads(Path(sys.argv[2]).read_text()), int(sys.argv[3])
    if mode == "repro2":
        drive_repro(items, workers)
    else:
        P.drive(mode, items, workers)          # any non-"repro" mode name -> perm2d.job_run into out/<mode>/
