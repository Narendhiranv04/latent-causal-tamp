#!/usr/bin/env python3
"""G5 X/Y labelling + label audit for accepted final scenes (frozen teacher via teacher_long; fresh teacher cache per scene, separate process
from the G2/G4 witness search).  Per scene with witness sequence s (len K):
  Y0        target-Y on the unedited layout (must be 0)
  X(s)      full relocation execution of the witness, independently replayed; per-step witness hashes compared with the search run
  Y(s)      target-Y at the witness endpoint, independently replayed; witness hash compared with the search run
  Y(s[:j])  target-Y after every proper prefix j = 1..K-1 (the minimum-K certificate implies 0 for any < K relocations; a 1 falsifies the
            bound -> AUDIT_FAIL)
Verdict LABEL_OK iff Y0 = 0, X = 1, Y = 1, both replays true, all prefix Y = 0, and the X/Y witness hashes reproduce.  Coverage: every query,
its status and CPU time is recorded (budget-limited / unknown outcomes are kept and counted, never coerced).
    python label_g5.py LAYOUTS.jsonl WITNESS.jsonl OUT.jsonl WORKERS       (LAYOUTS = final candidates; WITNESS = witness_v3 rows)"""
import hashlib, json, sys, time
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mink as MK  # noqa: E402
import witness as W  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def job(args):
    L, w = args
    MK.boot(L["geom"])
    import teacher_long as TL
    E = MK._M["E"]
    rec, ids = W.rec_of(L, L["geom"])
    fin = next(t for t in w["tries"] if t.get("final"))
    s = [tuple(t) for t in fin["seq"]]
    cache, Q, t0 = {}, [], time.process_time()

    def yq(seq, tag):
        r = TL.y_query(E, L["root_id"], rec, list(seq), cache)
        Q.append({"q": tag, "kind": "Y", "len": len(seq), "y": r.get("y"), "status": r.get("teacher_status"), "negative_kind": r.get("negative_kind"),
                  "replay": r.get("independent_replay"), "witness": r.get("target_witness"), "teacher": r.get("teacher")})
        return Q[-1]
    y0 = yq([], "Y0")
    x = TL.x_query(E, L["root_id"], rec, s, cache)
    xs = [st.get("witness") for st in (x.get("steps") or [])]
    Q.append({"q": "X", "kind": "X", "len": len(s), "y": x.get("y"), "status": x.get("teacher_status"), "replay": x.get("independent_replay"),
              "teacher": x.get("teacher"), "steps_witness": xs, "connector_witness": x.get("witness_connector"), "failed_phase": x.get("failed_phase")})
    xr = Q[-1]
    yf = yq(s, "Y_endpoint")
    pre = [yq(s[:j], f"Y_prefix{j}") for j in range(1, len(s))]
    ok = {"y0_zero": y0["y"] == 0, "x_one": xr["y"] == 1, "x_replay": bool(xr["replay"]), "y_one": yf["y"] == 1, "y_replay": bool(yf["replay"]),
          "prefix_all_zero": all(p["y"] == 0 for p in pre), "x_hash_reproduced": xs == fin.get("x_steps_witness"),
          "y_hash_reproduced": yf["witness"] == fin.get("y_witness"), "len_eq_K": len(s) == w["K_lb_v1"] == w["K_lb_v2"]}
    return {"root_id": L["root_id"], "K": w["K_lb"], "geom": L["geom"], "witness": [list(t) for t in s], "checks": ok,
            "verdict": "LABEL_OK" if all(ok.values()) else "AUDIT_FAIL", "queries": Q, "n_queries": len(Q), "cpu_s": round(time.process_time() - t0, 1)}


def main(lay_f, wit_f, out_f, workers):
    Ls = {json.loads(l)["root_id"]: json.loads(l) for l in open(lay_f)}
    Ws = [json.loads(l) for l in open(wit_f)]
    done = {json.loads(l)["root_id"] for l in open(out_f)} if Path(out_f).exists() else set()
    todo = [(Ls[w["root_id"]], w) for w in Ws if w["root_id"] not in done]
    prov = {"code_sha256": {f: sha(HERE / f) for f in ("label_g5.py", "teacher_long.py", "witness.py", "mink.py", "cert.py") if (HERE / f).exists()}}
    print(json.dumps(prov), flush=True)
    with get_context("spawn").Pool(workers, maxtasksperchild=2) as pool, open(out_f, "a") as f:
        for r in pool.imap_unordered(job, todo):
            r["provenance"] = prov
            f.write(json.dumps(r) + "\n"); f.flush()
            print(json.dumps({k: r[k] for k in ("root_id", "K", "verdict", "n_queries", "cpu_s")}), flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2], int(a[3]))
