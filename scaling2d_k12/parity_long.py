#!/usr/bin/env python3
"""G1 parity gate for teacher_long (BXY_*_TEACHER_V2_LONG).  Runs on a host with the frozen 2D environment (ABF_ROOT) where G0 passed.
  P1  K <= 6 dispatch: the 46 G0 parity queries (cached girish verify results incl. witness ids) and every recorded prefix / final query of
      the certified engineering roots (K4-6) -> identical x / status / phase (+ witness ids where cached) and y / status.
  P2  7-8 relocations: long teacher == frozen x_query with ONLY the eligibility cap lifted (frozen shared budget) -> identical rows
      (x, status, phase, every relocation witness id, connector id, replay).
  P3  9-12 relocations on easy synthetic layouts: the frozen path is budget-censored at relocation 8 (UNKNOWN_BUDGET); the long teacher
      returns complete rows; relocation witness ids of steps 0..5 equal the frozen 6-prefix query; X = 1 rows replay independently and the
      connector ends at q_ref; Y (long) evaluated on the endpoint.
  P4  explicit exhaustion: total_cap = 3 on a >= 7 sequence -> x = 0, status UNKNOWN_BUDGET at relocation:3 (never a success).
    python parity_long.py OUT.json WORKERS"""
import hashlib, json, os, random, sys, time
from multiprocessing import get_context
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import mink as MK  # noqa: E402
import witness as W  # noqa: E402
import teacher_long as TL  # noqa: E402

PARK = [0, 2, 8, 10, 16, 24, 32, 34, 40, 42, 9, 26, 18, 19, 27, 35, 41, 43, 48, 49, 56, 57]   # TRAIN-prior reliable parking (cols 0-2, F = 0)


def xrow(r):
    return {"x": r.get("y"), "status": r.get("teacher_status"), "phase": r.get("failed_phase"), "replay": r.get("independent_replay"),
            "reloc_w": [st.get("witness") for st in (r.get("steps") or [])], "conn": r.get("witness_connector"), "fq": r.get("final_q_after_connector")}


def job(j):
    MK.boot(j["geom"])
    E = MK._M["E"]
    import bxy_teacher as BT
    out = {"name": j["name"], "kind": j["kind"], "res": []}
    rec = j["rec"]
    k = rec["ids"]["root_id"]
    if j["kind"] == "P1":
        cache = {}
        for s, ref in zip(j["seqs"], j["refs"]):
            x = TL.x_query(E, k, rec, s, cache) if s else None
            y = TL.y_query(E, k, rec, s, cache)
            got = {"x": x and x.get("y"), "x_status": x and x.get("teacher_status"), "x_phase": x and x.get("failed_phase"), "y": y.get("y"),
                   "y_status": y.get("teacher_status"), "x_w": (x.get("witness_relocations") or []) + ([x["witness_connector"]] if x and x.get("witness_connector") else []) if x else None}
            out["res"].append({"seq": s, "ref": ref, "got": got,
                               "match": all(ref.get(f) is None or ref[f] == got[f] for f in ("x", "x_status", "x_phase", "y", "y_status", "x_w"))})
    elif j["kind"] == "P2":
        for s in j["seqs"]:
            a, b = xrow(TL.frozen_bypass_x(E, k, rec, s, {})), xrow(TL.x_query(E, k, rec, s, {}))
            out["res"].append({"len": len(s), "frozen_bypass": a, "long": b, "match": a == b})
    elif j["kind"] == "P3":
        for s in j["seqs"]:
            fz = xrow(TL.frozen_bypass_x(E, k, rec, s, {}))
            lg_full = TL.x_query(E, k, rec, s, {})
            lg = xrow(lg_full)
            p6 = xrow(TL.x_query(E, k, rec, s[:6], {}))
            yl = TL.y_query(E, k, rec, s, {})
            fq_ok = lg["fq"] is not None and max(abs(a - b) for a, b in zip(lg["fq"], rec["q0"])) < 1e-6
            out["res"].append({"len": len(s), "frozen_bypass": {kk: fz[kk] for kk in ("x", "status", "phase")}, "long": lg, "y_long": yl.get("y"),
                               "y_status": yl.get("teacher_status"), "y_teacher": yl.get("teacher"),
                               "prefix6_witness_equal": lg["reloc_w"][:6] == p6["reloc_w"][:6] if len(lg["reloc_w"]) >= 6 else None,
                               "frozen_censored_at_8": fz["status"] == "UNKNOWN_BUDGET" and fz["phase"] == "relocation:8",
                               "long_x1_replay_and_qref": (lg["x"] != 1) or (lg["replay"] is True and fq_ok)})
    elif j["kind"] == "P4":
        for s in j["seqs"]:
            r = xrow(TL.x_query(E, k, rec, s, {}, total_cap=3))
            out["res"].append({"len": len(s), "row": {kk: r[kk] for kk in ("x", "status", "phase")}, "match": r["x"] == 0 and r["status"] == "UNKNOWN_BUDGET" and r["phase"] == "relocation:3"})
    return out


def easy_layout(T, qc, seed, n_obs=12):
    """synthetic layout: target + n_obs discs on q_ref-clear cells with every disc individually pickable; a greedy relaxation-feasible move
    order to PARK / free cells (occupancy simulated on the kill tables).  Engineering test input only."""
    rng = random.Random(f"PARITYLONG|{seed}")
    import functools
    pk, pl, p0, pl0 = T["pickkill"], T["placekill"], T["pick0"], T["place0"]
    kill = lambda tab, x, occ: functools.reduce(lambda a, q: a | int(tab[str(x)].get(str(q), 0)), occ, 0)  # noqa: E731
    cells = [c for c in qc if int(p0[str(c)]) and int(pl0[str(c)]) and c % 8 >= 3]          # objects in the TRAIN support (columns 3-7)
    for _ in range(500):
        lay = rng.sample([c for c in cells if c not in PARK], n_obs + 2)
        tgt, goal, obs = lay[0], lay[1], lay[2:]
        cur, seq = {i: c for i, c in enumerate(obs)}, []
        free = [c for c in PARK + [c for c in cells if c not in lay] if c in qc]
        ok = True
        for i in range(n_obs):
            others = [c for j, c in cur.items() if j != i] + [tgt]
            if int(p0[str(cur[i])]) & ~kill(pk, cur[i], others) == 0:
                ok = False; break
            dd = next((d for d in free if d not in cur.values() and d != goal and int(pl0[str(d)]) & ~kill(pl, d, others) != 0), None)
            if dd is None:
                ok = False; break
            seq.append((i, dd)); cur[i] = dd
        if ok:
            return tgt, goal, obs, seq
    return None


def main(outp, workers):
    jobs = []
    cachef = H / "g0parity/cache/verify_2d.jsonl"
    ref = {}
    for l in open(cachef):
        v = json.loads(l)
        for x in v["results"]:
            ref[(v["root"], json.dumps(x["seq"]))] = x
    for l in open(H / "g0parity/jobs_2d.jsonl"):                              # P1a: 46 G0 queries
        j = json.loads(l)
        rel = "abf_v314v" + j["path"].split("abf_v314v", 1)[1]
        rec = json.loads((Path(os.environ["ABF_ROOT"]).parents[1] / rel).read_text())
        refs = []
        for s in j["seqs"]:
            x = ref[(j["root_id"], json.dumps([[j["ids"].index(o), c] for o, c in s]))]
            refs.append({"x": x["x"]["x"], "x_status": x["x"]["status"], "x_phase": x["x"].get("phase"), "y": x["y"]["y"], "y_status": x["y"]["status"], "x_w": x["x"].get("witnesses")})
        jobs.append({"name": j["root_id"], "kind": "P1", "geom": j["geom"], "rec": rec, "seqs": j["seqs"], "refs": refs})
    lay = {}
    for f in sorted(H.glob("*layouts*.jsonl")):
        for l in open(f):
            r = json.loads(l)
            if "root_id" in r:
                lay[r["root_id"]] = r
    certs = [json.loads(l) for l in open(H / "eng_certs16.jsonl")]
    T = {g: json.loads((H / f"tables/MINK_TABLE_{g}.json").read_text()) for g in ("original", "fastgeom1")}
    for c in certs:                                                           # P1b + P2 on the engineering roots
        L = lay[c["root_id"]]
        MKboot = None
        rec, ids = W.rec_of(L, L["geom"])
        seqs, refs = [], []
        for t in c["tries"]:
            seqs.append(t["seq"]); refs.append({"x": t.get("x"), "x_status": t.get("x_status"), "x_phase": t.get("x_phase"), "y": t.get("y"), "y_status": t.get("y_status"), "x_w": None})
        jobs.append({"name": c["root_id"], "kind": "P1", "geom": L["geom"], "rec": rec, "seqs": seqs, "refs": refs})
        wit = next(t["seq"] for t in c["tries"] if t.get("x") == 1 and t.get("y") == 1)
        if len(wit) >= 5:
            used = {d for _, d in wit} | set(L["cells0"]) | {L["goal_cell"]}
            extra = [o for o in ids[1:] if o not in {x for x, _ in wit}]
            park = [d for d in PARK if d not in used]
            ext = [[o, d] for o, d in zip(extra, park)]
            p2 = [wit + ext[:m] for m in (1, 2) if len(wit) + m in (7, 8) and len(ext) >= m]
            if p2:
                jobs.append({"name": c["root_id"] + "|P2", "kind": "P2", "geom": L["geom"], "rec": rec, "seqs": p2})
    qc = set(json.loads((H / "G1/QCLEAR_original.json").read_text())["cells"]) if (H / "G1/QCLEAR_original.json").exists() else set(range(64))
    for seed in range(6):                                                     # P3 / P4 synthetic long sequences
        e = easy_layout(T["original"], qc, seed, 12)
        if not e:
            continue
        tgt, goal, obs, seq = e
        L = {"root_id": f"PARITYLONG_{seed}", "cells0": [tgt] + obs, "goal_cell": goal, "geom": "original"}
        rec, ids = W.rec_of(L, "original")
        s = [[ids[1 + i], d] for i, d in seq]
        jobs.append({"name": L["root_id"], "kind": "P3", "geom": "original", "rec": rec, "seqs": [s[:9], s[:12]]})
        if seed < 2:
            jobs.append({"name": L["root_id"] + "|P4", "kind": "P4", "geom": "original", "rec": rec, "seqs": [s[:8]]})
    if os.environ.get("ONLY_LONG"):
        jobs = [j for j in jobs if j["kind"] in ("P3", "P4")]
    t0, res = time.time(), []
    for g in sorted({j["geom"] for j in jobs}):
        with get_context("spawn").Pool(workers, maxtasksperchild=1) as pool:
            res += list(pool.imap_unordered(job, [j for j in jobs if j["geom"] == g]))
    summ = {}
    for kind in ("P1", "P2", "P3", "P4"):
        R = [r for o in res if o["kind"] == kind for r in o["res"]]
        if kind == "P3":
            summ[kind] = {"queries": len(R), "frozen_censored_at_8": sum(r["frozen_censored_at_8"] for r in R),
                          "prefix6_witness_equal": sum(bool(r["prefix6_witness_equal"]) for r in R), "long_x1": sum(r["long"]["x"] == 1 for r in R),
                          "long_x1_replay_and_qref_ok": sum(r["long_x1_replay_and_qref"] for r in R), "long_status": sorted({r["long"]["status"] for r in R})}
        else:
            summ[kind] = {"queries": len(R), "match": sum(r["match"] for r in R)}
    out = {"teacher": TL.X_LONG, "summary": summ, "wall_s": round(time.time() - t0, 1), "jobs": res}
    Path(outp).write_text(json.dumps(out, indent=1, default=str))     # outp must be absolute (mink.boot changes the working directory)
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]), int(sys.argv[2]))
