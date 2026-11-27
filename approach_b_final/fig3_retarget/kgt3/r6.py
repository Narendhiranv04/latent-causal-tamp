#!/usr/bin/env python3
"""R6 development evaluation of both compositional planners (R5_PREREG R6; config frozen by R5.3 before any R6 outcome).
Populations   3d     : 20 exposed DEV witness roots (L_ref 4 / 5)
              2d     : coh2d DEV roots with L_ref <= 5 (dense, N 14-20; K6 excluded by evaluator-only filtering); 10-job pilot stop
              2d_demo: held-out moderate-density demonstration roots (R6-2D-DEMO, R6-2D-DEMO-G; N 12-13), never pooled with 2d
Arms          B0 (historical production K <= 3, production F0) | H3 (rank.b0 rule with the selected X) | FLAT-INSERT | REC-ORDERED | GA (H = 5)
Every plan is produced from the public row only under one deadline (floor, proposal, search, selection inside) and sealed before any job.
    $PYG r6.py plan POP CONFIG.json        -> r5/r6/plans_POP.jsonl (+ SEAL)
    python r6.py jobs POP CAP              -> jobs_POP.json (+ SEAL), selection_POP.json
    python r6.py analyze POP               -> R6_POP.json"""
from __future__ import annotations

import collections, hashlib, json, math, statistics, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "r3"), str(HERE.parent / "r24"), str(HERE.parent.parent)]
import common3 as K  # noqa: E402
import guard as GD  # noqa: E402
O = K.C.FIG3 / "kgt3"
R6 = O / "r5" / "r6"
ARMS = ("B0", "H3", "FLAT-INSERT", "REC-ORDERED", "GA")


def jl(p):
    return [json.loads(l) for l in open(p)] if Path(p).exists() else []


def roots(pop):
    """-> [(rid, row, meta)]; meta (evaluator only): L_ref, N, K if certified, witness, path, goal."""
    if pop in ("3d", "2d"):
        import r53
        out = []
        for rid, row, A, W, meta in r53.panel(pop):
            out.append((rid, {"root_id": row["root_id"], "domain": pop, "inputs": row["inputs"]},
                        {"L_ref": len(W), "N": meta["N"], "K_cert": None, "witness": W, "path": meta["path"], "goal": meta.get("goal")}))
        return out
    import contracts as CT
    out = []
    for d in ("demo2d", "demo2d_b"):
        for f in jl(O / "r5" / d / "families.jsonl"):
            st = f["family"]
            if not st.get("ok"):
                continue
            rec = json.loads(Path(st["root"]).read_text())
            inp = CT.view2d(rec)
            ix = {n: i for i, n in enumerate(inp["ids"])}
            out.append((rec["ids"]["root_id"], {"root_id": rec["ids"]["root_id"], "domain": "2d", "inputs": inp},
                        {"L_ref": st["L_ref"], "N": st["N"], "K_cert": None, "witness": [[ix[o], int(c)] for o, c in st["witness"]], "path": st["root"], "goal": st["goal"]}))
    return out


def plan(pop, cfg_path):
    import learn as LN
    import planners as PL
    import rank as RK
    import r53
    dom = "3d" if pop == "3d" else "2d"
    cfg = json.loads(Path(cfg_path).read_text())[dom]
    fz, net = LN.load(dom, cfg["spec"]); fz.net = net
    fz0, base = LN.load(dom, "F0"); fz0.net = base
    pcfg = {"rule": {**PL.CFG["rule"], **({"S2_tau": cfg["S2_tau"], "S2_stat": cfg.get("S2_stat")} if cfg.get("S2_tau") is not None else {})},
            "rec": {**PL.CFG["rec"], "admit_m": cfg.get("admit_m", 0.0), "admit_eta": cfg.get("admit_eta")}}
    R6.mkdir(parents=True, exist_ok=True)
    import os
    sh = os.environ.get("R6_SHARD")                                     # "i/n": deterministic root shard (merged + sealed by `merge`)
    i_, n_ = (int(x) for x in sh.split("/")) if sh else (0, 1)
    pf = R6 / (f"plans_{pop}.part{i_}of{n_}.jsonl" if sh else f"plans_{pop}.jsonl")
    with open(pf, "w") as f:
        for k_, (rid, row, meta) in enumerate(roots(pop)):
            if k_ % n_ != i_:
                continue
            rec = {"root_id": rid, "pop": pop, "config": cfg, "arms": {}}
            for arm in ARMS:
                if arm in ("B0", "H3"):
                    m = fz0 if arm == "B0" else fz
                    m.prop_mode = "S1"; m.reset(); m.caps = {}
                    t0 = time.perf_counter()
                    b = RK.b0(m, row, PL.CFG["rule"])
                    if str(m.dev).startswith("cuda"):
                        m.torch.cuda.synchronize()
                    rec["arms"][arm] = {"decision": b["decision"], "seq": b["seq"], "partition": [len(b["seq"])] if b["seq"] else None, "wall_s": round(time.perf_counter() - t0, 3),
                                        "counters": dict(m.c), "kind": "k3_exact4"}
                    continue
                fz.prop_mode = cfg["prop_GA"] if arm == "GA" else cfg["prop_REC"]
                p = PL.plan(fz, row, arm, r53.floor_fn(fz0, row), pcfg)
                rec["arms"][arm] = {k: p[k] for k in ("arm", "decision", "seq", "partition", "E", "kind", "long", "multi_chunk", "stop", "budget_stop", "wall_s", "floor_wall_s",
                                                      "search_wall_s", "select_wall_s", "deadline_overrun_s", "cap_overrun", "counters", "floor_counters", "selection_readouts",
                                                      "n_candidates", "incumbent_from_stop")}
                rec["arms"][arm]["mode"] = (p["info"] or {}).get("mode"); rec["arms"][arm]["exhausted"] = (p["info"] or {}).get("exhausted")
                rec["arms"][arm]["scores"] = (p["info"] or {}).get("scores"); rec["arms"][arm]["tree"] = p.get("tree") if arm == "REC-ORDERED" else None
                rec["arms"][arm]["prop_mode"] = fz.prop_mode
            fz.prop_mode = "S1"
            f.write(json.dumps(rec, default=str) + "\n"); f.flush()
            print(rid, {a: (v["decision"], len(v["seq"] or []), v["wall_s"]) for a, v in rec["arms"].items()}, flush=True)
    if not sh:
        (R6 / f"plans_{pop}.jsonl.SEAL").write_text(GD.sha(pf))


def merge(pop, n):
    """Merge every shard (each root exactly once, in roots() order) -> plans_POP.jsonl + SEAL."""
    parts = [R6 / f"plans_{pop}.part{i}of{n}.jsonl" for i in range(int(n))]
    recs = {r["root_id"]: r for p in parts for r in jl(p)}
    order = [rid for rid, _, _ in roots(pop)]
    assert set(recs) == set(order), f"missing {set(order) - set(recs)}"
    pf = R6 / f"plans_{pop}.jsonl"
    with open(pf, "w") as f:
        for rid in order:
            f.write(json.dumps(recs[rid], default=str) + "\n")
    (R6 / f"plans_{pop}.jsonl.SEAL").write_text(GD.sha(pf)); print("merged", len(order))


def archive3d():
    """Exact (root, ordered names, bounds) -> archived X_CHUNKED + endpoint-Y + replay record (same teacher contract): R2.4, quarantined R3.4
    (labelled), R4.2 and R4.5 runs.  Reuse is predeclared (R5_PREREG) and labelled per record."""
    import jobs24 as J24
    import p3 as P3
    import smoke as SM
    A = dict(SM.archive("3d"))
    pan = {rid: row for rid, row, *_ in P3.panel("3d")}
    sm = O / "r4" / "smoke"
    R = {r["key"]: r for r in jl(sm / "phys_3d.jsonl")}
    for s in json.loads((sm / "selection_3d.json").read_text()):
        if s["status"] == "QUEUED" and s["job"] in R:
            ids = pan[s["root_id"]]["inputs"]["ids"]
            A.setdefault((s["root_id"], J24.nk(J24.names("3d", ids, s["seq"])), J24.nk(bounds(s["partition"]))), {"rec": R[s["job"]], "src": "R4.5:" + s["job"]})
    return A


def bounds(part):
    s, out = 0, []
    for g in part:
        s += g; out.append(s)
    return out


def jobs(pop, cap):
    import jobs24 as J24
    pf = R6 / f"plans_{pop}.jsonl"
    if GD.sha(pf) != (R6 / f"plans_{pop}.jsonl.SEAL").read_text().strip():
        raise SystemExit("plans not sealed")
    P = {r["root_id"]: r for r in jl(pf)}
    RT = {rid: (row, meta) for rid, row, meta in roots(pop)}
    A = archive3d() if pop == "3d" else {}
    seen, jb, sel = {}, [], []
    for rid in sorted(P, key=lambda r: hashlib.sha256(f"R6|{r}".encode()).hexdigest()):
        row, meta = RT[rid]; ids = row["inputs"]["ids"]
        for arm in ARMS:
            p = P[rid]["arms"][arm]
            base = {"root_id": rid, "arm": arm, "seq": p["seq"], "partition": p["partition"], "decision": p["decision"]}
            if p["decision"] != "REPAIR" or not p["seq"]:
                sel.append({**base, "status": "NO_REPAIR"}); continue
            b = bounds(p["partition"])
            k = (rid, J24.nk(J24.names("3d", ids, p["seq"])), J24.nk(b)) if pop == "3d" else (rid, json.dumps(p["seq"]), json.dumps(b))
            key = f"R6|{pop}|{rid}|{json.dumps(p['seq'])}|{json.dumps(b)}"
            if k in seen:
                sel.append({**base, "status": "SAME_AS", "job": seen[k]}); continue
            seen[k] = key
            if k in A:
                sel.append({**base, "status": "REUSED", "job": key, "src": A[k]["src"]}); continue
            if len(jb) + 1 > int(cap):
                sel.append({**base, "status": "NOT_RUN_BUDGET", "job": key}); continue
            if pop == "3d":
                jb.append({"key": key, "root_id": rid, "arm": arm, "path": meta["path"], "kind": "X_CHUNKED", "order": J24.names("3d", ids, p["seq"]), "bounds": b,
                           "y": {"target": "t0", "goal": meta["goal"]}})
            else:
                jb.append({"key": key, "root_id": rid, "arm": arm, "path": meta["path"], "geom": "original", "kind": "X_CHUNKED",
                           "seq": [[ids[o], int(d)] for o, d in p["seq"]], "seq_idx": p["seq"], "bounds": b, "y_endpoint": True})
            sel.append({**base, "status": "QUEUED", "job": key})
    jf = R6 / f"jobs_{pop}.json"; jf.write_text(json.dumps(jb, indent=1))
    sf = R6 / f"selection_{pop}.json"; sf.write_text(json.dumps(sel, indent=1))
    GD.seal(jf); (R6 / f"selection_{pop}.json.SEAL").write_text(GD.sha(sf))
    print(json.dumps({"queued": len(jb), "by": collections.Counter(f"{s['arm']}:{s['status']}" for s in sel)}))


def res(dom, r):
    X, Y = r.get("X") or {}, r.get("Y") or {}
    rep = (r.get("REPLAY") or {}).get("replay") == 1 if dom == "3d" else bool(X.get("independent_replay"))
    return {"x": X.get("x"), "y": Y.get("y"), "replay": rep, "succ": bool(X.get("x") == 1 and Y.get("y") == 1 and rep), "x_outcome": GD.outcome(r, "X"),
            "y_outcome": GD.outcome(r, "Y") if r.get("Y") else None, "phase": X.get("phase") or X.get("failed_phase"), "verify_cpu_s": r.get("cpu_s"), "verify_wall_s": r.get("wall_s")}


def _sign(g, l):
    n = g + l
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(0, min(g, l) + 1)) / 2 ** n) if n else None


def analyze(pop):
    dom = "3d" if pop == "3d" else "2d"
    jf, rf = R6 / f"jobs_{pop}.json", R6 / f"phys_{pop}.jsonl"
    comp = GD.complete(jf, rf)
    R = {r["key"]: r for r in jl(rf)}
    P = {r["root_id"]: r for r in jl(R6 / f"plans_{pop}.jsonl")}
    RT = {rid: meta for rid, _, meta in roots(pop)}
    A = {v["src"]: v["rec"] for v in archive3d().values()} if pop == "3d" else {}
    sel = json.loads((R6 / f"selection_{pop}.json").read_text())
    by_job = {}
    for s in sel:
        if s["status"] == "QUEUED" and s["job"] in R:
            by_job[s["job"]] = {**res(dom, R[s["job"]]), "src": "NEW"}
        elif s["status"] == "REUSED":
            by_job[s["job"]] = {**res(dom, A[s["src"]]), "src": s["src"]}
    per = collections.defaultdict(dict)
    for s in sel:
        p = P[s["root_id"]]["arms"][s["arm"]]
        if s["status"] == "NO_REPAIR":
            v = {"succ": False, "x_outcome": "NO_REPAIR:" + str(s["decision"])}
        elif s["status"] == "NOT_RUN_BUDGET" or s.get("job") not in by_job:
            v = {"succ": False, "x_outcome": "UNRUN"}
        else:
            v = dict(by_job[s["job"]])
        L = len(s["seq"] or [])
        v.update(L_pred=L, L_exec=L if v.get("succ") else (int(str(v.get("phase") or "relocation:0").split(":")[1]) if str(v.get("phase") or "").startswith("relocation") else None),
                 plan_wall_s=p.get("wall_s"), floor_wall_s=p.get("floor_wall_s"), decision=p["decision"], mode=p.get("mode"), budget_stop=p.get("budget_stop"),
                 x_unique=(p.get("counters") or {}).get("x_unique"), latent_draws=(p.get("counters") or {}).get("latent_draws"), n_candidates=p.get("n_candidates"),
                 witness_action_recall=len({tuple(a) for a in (s["seq"] or [])} & {tuple(a) for a in RT[s["root_id"]]["witness"]}) / RT[s["root_id"]]["L_ref"],
                 L_ref=RT[s["root_id"]]["L_ref"], N=RT[s["root_id"]]["N"])
        per[s["root_id"]][s["arm"]] = v
    roots_ = sorted(per)
    n = len(roots_)
    q = lambda xs, p: sorted(xs)[min(len(xs) - 1, int(math.ceil(p * len(xs)) - 1))] if xs else None  # noqa: E731
    summ = {}
    for arm in ARMS:
        rr = [per[r][arm] for r in roots_]
        pw = [x["plan_wall_s"] for x in rr if x.get("plan_wall_s") is not None]
        vw = [x["verify_wall_s"] for x in rr if x.get("verify_wall_s")]
        summ[arm] = {"n": n, "succ": sum(x["succ"] for x in rr), "succ_L4": sum(x["succ"] and x["L_pred"] == 4 for x in rr), "succ_L5": sum(x["succ"] and x["L_pred"] == 5 for x in rr),
                     "succ_long": sum(x["succ"] and x["L_pred"] > 3 for x in rr), "x1": sum(x.get("x") == 1 for x in rr), "y1": sum(x.get("y") == 1 for x in rr),
                     "replay1": sum(bool(x.get("replay")) for x in rr), "outcomes": dict(collections.Counter(x["x_outcome"] for x in rr)),
                     "decisions": dict(collections.Counter(x["decision"] for x in rr)), "L_pred": dict(collections.Counter(x["L_pred"] for x in rr)),
                     "plan_wall": {"mean": statistics.mean(pw) if pw else None, "median": statistics.median(pw) if pw else None, "p90": q(pw, 0.9), "max": max(pw) if pw else None},
                     "verify_wall": {"mean": statistics.mean(vw) if vw else None, "median": statistics.median(vw) if vw else None, "p90": q(vw, 0.9)},
                     "x_unique_median": statistics.median([x["x_unique"] for x in rr if x.get("x_unique") is not None] or [0]),
                     "budget_stops": sum(bool(x.get("budget_stop")) for x in rr), "witness_action_recall_mean": statistics.mean(x["witness_action_recall"] for x in rr),
                     "by_L_ref": {L: [sum(x["succ"] for x in rr if x["L_ref"] == L), sum(1 for x in rr if x["L_ref"] == L)] for L in sorted({x["L_ref"] for x in rr})},
                     "by_N": {N: [sum(x["succ"] for x in rr if x["N"] == N), sum(1 for x in rr if x["N"] == N)] for N in sorted({x["N"] for x in rr})},
                     "new": sum(x.get("src") == "NEW" for x in rr), "reused": sum(str(x.get("src", "")).startswith("R") for x in rr)}
        k = summ[arm]["succ"]
        z = 1.96; ph = k / n if n else 0
        summ[arm]["wilson95"] = [(ph + z * z / (2 * n) - z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))) / (1 + z * z / n),
                                 (ph + z * z / (2 * n) + z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))) / (1 + z * z / n)] if n else None
    paired = {}
    for a, b in (("REC-ORDERED", "FLAT-INSERT"), ("GA", "FLAT-INSERT"), ("REC-ORDERED", "GA"), ("REC-ORDERED", "H3"), ("GA", "H3"), ("H3", "B0"), ("FLAT-INSERT", "H3")):
        g = sum(per[r][a]["succ"] and not per[r][b]["succ"] for r in roots_); l = sum(per[r][b]["succ"] and not per[r][a]["succ"] for r in roots_)
        paired[f"{a}_vs_{b}"] = {"gain": g, "loss": l, "p_sign_two_sided": _sign(g, l)}
    out = {"pop": pop, "n_roots": n, "summary": summ, "paired": paired, "either_fig3": sum(per[r]["REC-ORDERED"]["succ"] or per[r]["GA"]["succ"] for r in roots_),
           "per_root": per, "completion": comp, "cpu_h_new": sum(r.get("cpu_s", 0) for r in R.values()) / 3600,
           "label": "R6 DEVELOPMENT evaluation (exposed or development roots; planners never see assignment / order / K)"}
    (R6 / f"R6_{pop}.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items() if k != "per_root"}, default=str)[:4000])


if __name__ == "__main__":
    a = sys.argv[1]
    {"merge": lambda: merge(*sys.argv[2:4]), "plan": lambda: plan(*sys.argv[2:4]), "jobs": lambda: jobs(*sys.argv[2:4]), "analyze": lambda: analyze(sys.argv[2])}[a]()
