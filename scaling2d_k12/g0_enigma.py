#!/usr/bin/env python3
"""G0 host parity on enigma (scaling2d): re-run the 46 G0 K3 parity queries (girish g0parity jobs) with the frozen 2D teacher exactly as the
witness search calls it (mink.boot -> bxy_teacher.x_query / y_query) and compare x / status / y with girish's verified cache.
    python g0_enigma.py WORKERS   -> G0_ENIGMA_PARITY.json"""
import json, os, sys, time
from multiprocessing import get_context
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
ROOT = Path(os.environ["ABF_ROOT"]).parents[1]          # .../scaling2d (holds abf_v314v/root)


def job(j):
    import mink as MK
    MK.boot(j["geom"])
    import bxy_teacher as BT
    rec = json.loads((ROOT / j["rel"]).read_text())
    out, cache = [], {}
    for s in j["seqs"]:
        x = BT.x_query(MK._M["E"], j["root_id"], rec, s, cache)
        y = BT.y_query(MK._M["E"], j["root_id"], rec, s, cache)
        out.append({"seq": [[j["ids"].index(o), c] for o, c in s], "x": x.get("y"), "x_status": x.get("teacher_status"), "y": y.get("y"), "y_status": y.get("teacher_status")})
    return j["root_id"], out


def main(W):
    ref = {}
    for l in open(H / "g0parity/cache/verify_2d.jsonl"):
        v = json.loads(l)
        for x in v["results"]:
            ref[(v["root"], json.dumps(x["seq"]))] = ((x["x"] or {}).get("x"), (x["x"] or {}).get("status"), (x["y"] or {}).get("y"), (x["y"] or {}).get("status"))
    jobs = []
    for l in open(H / "g0parity/jobs_2d.jsonl"):
        j = json.loads(l)
        j["rel"] = "abf_v314v" + j["path"].split("abf_v314v", 1)[1]
        jobs.append(j)
    t0, agree, tot, mism = time.time(), {"x": 0, "x_status": 0, "y": 0, "y_status": 0}, 0, []
    for g in sorted({j["geom"] for j in jobs}):
        with get_context("spawn").Pool(W, maxtasksperchild=1) as pool:
            for rid, out in pool.imap_unordered(job, [j for j in jobs if j["geom"] == g]):
                for o in out:
                    r = ref[(rid, json.dumps(o["seq"]))]
                    tot += 1
                    for k, v in zip(("x", "x_status", "y", "y_status"), r):
                        agree[k] += o[k] == v
                    if (o["x"], o["x_status"], o["y"], o["y_status"]) != r:
                        mism.append({"root": rid, "seq": o["seq"], "enigma": [o["x"], o["x_status"], o["y"], o["y_status"]], "girish": list(r)})
    res = {"host": "enigma (naren-m4m, venv python %s)" % sys.version.split()[0], "n_queries": tot, "agreement": {k: f"{v}/{tot}" for k, v in agree.items()},
           "exact": not mism, "mismatches": mism, "wall_s": round(time.time() - t0, 1), "workers": W}
    (H / "G0_ENIGMA_PARITY.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ("n_queries", "agreement", "exact", "wall_s")}))


if __name__ == "__main__":
    main(int(sys.argv[1]))
