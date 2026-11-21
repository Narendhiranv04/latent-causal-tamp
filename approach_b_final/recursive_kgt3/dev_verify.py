#!/usr/bin/env python3
"""EVALUATOR ONLY (post-seal): physical verification of every sealed DEV decision with the unchanged long teacher (scaling2d_k12.teacher_long:
<=6 relocations -> frozen BXY teacher, 7-12 -> LongPhysics; chained relocations + one terminal connector to q_ref; Y of the ORIGINAL target from
q_ref).  Verifies the primary pick of every arm plus the B2/B3 re-rankings of REC/REC2.  Refuses to run unless every SEAL.json matches.
Run with the teacher env from the scaling2d_k12 code dir:
    ABF_ROOT=... python dev_verify.py SCALING_CODE_DIR RUNS_DIR DEV_PRIVATE_DIR OUT.jsonl WORKERS"""
import hashlib, json, sys
from multiprocessing import get_context
from pathlib import Path


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def job(a):
    code, rec_f, rid, seq = a
    sys.path.insert(0, code)
    import mink as MK
    MK.boot("original")
    import teacher_long as TL
    E = MK._M["E"]
    rec = json.loads(Path(rec_f).read_text())
    names = [o["id"] for o in rec["scene"]["objects"]]
    s = [(names[i], int(d)) for i, d in seq]
    x = TL.x_query(E, rid, rec, s, {})
    y = TL.y_query(E, rid, rec, s, {})
    return {"root_id": rid, "seq": seq, "x": x.get("y"), "x_status": x.get("teacher_status"), "x_phase": x.get("failed_phase"),
            "x_negative_kind": x.get("negative_kind"), "x_replay": x.get("independent_replay"), "y": y.get("y"), "y_status": y.get("teacher_status"),
            "y_negative_kind": y.get("negative_kind"), "x_teacher": x.get("teacher"), "y_teacher": y.get("teacher")}


def main(code, runs, priv, out, W):
    runs = Path(runs); jobs, seen = [], set()
    for sealf in sorted(runs.glob("*/SEAL.json")):
        seal = json.loads(sealf.read_text())
        assert sha(sealf.parent / "predictions.jsonl") == seal["predictions_sha256"], f"seal mismatch {sealf}"
        for p in (json.loads(l) for l in open(sealf.parent / "predictions.jsonl")):
            for s in (p["seq"], p.get("alt_Yonly"), p.get("alt_Xonly")):
                if s and (p["root_id"], json.dumps(s)) not in seen:
                    seen.add((p["root_id"], json.dumps(s)))
                    jobs.append((str(code), str(Path(priv) / "dev_records" / f"{p['root_id']}.json"), p["root_id"], s))
    done = {(json.loads(l)["root_id"], json.dumps(json.loads(l)["seq"])) for l in open(out)} if Path(out).exists() else set()
    todo = [j for j in jobs if (j[2], json.dumps(j[3])) not in done]
    print(json.dumps({"verify_jobs": len(jobs), "todo": len(todo)}), flush=True)
    with get_context("spawn").Pool(int(W), maxtasksperchild=4) as pool, open(out, "a") as f:
        for r in pool.imap_unordered(job, todo):
            f.write(json.dumps(r) + "\n"); f.flush()


if __name__ == "__main__":
    main(*sys.argv[1:6])
