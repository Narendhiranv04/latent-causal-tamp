#!/usr/bin/env python3
"""EVALUATOR ONLY (post-seal): teacher-verify the extra post-hoc candidates (EXTRA_JOBS.jsonl from p4_eval.py extra) with the same job function
as dev_verify.py; appends to the same verify file (dedup by root+seq).  Results are never fed back to any planner.
    ABF_ROOT=... python p4_verify_extra.py SCALING_CODE_DIR EXTRA_JOBS.jsonl DEV_PRIVATE_DIR VERIFY.jsonl WORKERS"""
import json, sys
from multiprocessing import get_context
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dev_verify import job  # noqa: E402


def main(code, extra, priv, out, W):
    done = {(json.loads(l)["root_id"], json.dumps(json.loads(l)["seq"])) for l in open(out)} if Path(out).exists() else set()
    todo = []
    for j in (json.loads(l) for l in open(extra)):
        k = (j["root_id"], json.dumps(j["seq"]))
        if k not in done:
            done.add(k); todo.append((str(code), str(Path(priv) / "dev_records" / f"{j['root_id']}.json"), j["root_id"], j["seq"]))
    print(json.dumps({"extra_todo": len(todo)}), flush=True)
    with get_context("spawn").Pool(int(W), maxtasksperchild=4) as pool, open(out, "a") as f:
        for r in pool.imap_unordered(job, todo):
            f.write(json.dumps(r) + "\n"); f.flush()


if __name__ == "__main__":
    main(*sys.argv[1:6])
