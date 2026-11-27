#!/usr/bin/env python3
"""R5.3 model-only diagnostics for the R5.2-selected X (rules: reports/R5_3_RULES.md, committed before any of these numbers).
    $PYG r53.py calib DOM NAME            -> r5/r53/calib_DOM.json   (temperature on local VAL; S2 tau from VAL positives g >= 2)
    $PYG r53.py length DOM SPEC [TAU]     -> r5/r53/length_DOM_<tag>.jsonl (GA + REC candidates on DEV roots: energy by size / partition,
                                             has_multi constrained vs all-singleton-inclusive, terminal Y by #edits, S0 vs S2 picks)
    $PYG r53.py admission DOM SPEC        -> r5/r53/admission_DOM.json (paired physical temporary-target evidence vs A0 / A1(m) / A2)
    $PYG r53.py proposals DOM SPEC        -> r5/r53/proposals_DOM.json (S1 / TOP8 / ANC64 / UNIF: GA pool + REC union witness recall, cost)
Evaluator joins only (witness / L_ref / physical labels); the planners never read them."""
from __future__ import annotations

import collections, json, math, statistics, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "r3"), str(HERE.parent / "r24"), str(HERE.parent.parent)]
import common3 as K  # noqa: E402
O = K.C.FIG3 / "kgt3"
R53 = O / "r5" / "r53"


def jl(p):
    return [json.loads(l) for l in open(p)] if Path(p).exists() else []


def panel(dom):
    """DEV roots in scope: 3D all 20 (L_ref 4/5); 2D coh2d with K <= 5 (K6 excluded by evaluator-only filtering)."""
    import p3 as P3
    return [(rid, row, A, W, meta) for rid, row, A, W, meta in P3.panel(dom) if meta["K"] <= 5]


def calib(dom, name):
    import numpy as np
    import learn as LN
    import xlearn as XLN
    import train as TR
    D = XLN.prepare(dom)
    fz, net = LN.load(dom, "XL:" + name)
    res = XLN.fit_temperature(net, D["va"], "cuda")
    out = {"name": name, "T": res["T"], "val_nll_raw": res["val_nll_raw"], "val_nll_cal": res["val_nll_cal"],
           "adopt": res["val_nll_raw"] - res["val_nll_cal"] >= 0.005}
    m = XLN.Cal(net, res["T"]) if out["adopt"] else net
    P = TR.predict(m, D["va"], "cuda")
    pos = [-math.log(max(1e-8, e["px"])) for e in P if e["label"] == 1 and e["m"] >= 2]
    out["S2_tau"] = float(np.percentile(pos, 95)) if pos else None
    out["n_pos_g2"] = len(pos)
    out["raw_metrics"] = XLN.metrics(TR.predict(net, D["va"], "cuda")); out["cal_metrics"] = XLN.metrics(TR.predict(XLN.Cal(net, res["T"]), D["va"], "cuda"))
    out["reliability"] = reliability(TR.predict(m, D["va"], "cuda"))
    out["grid"] = res["grid"]
    R53.mkdir(parents=True, exist_ok=True)
    (R53 / f"calib_{dom}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k not in ("grid", "reliability")}))


def reliability(P, n=10):
    out = []
    for k in range(n):
        s = [e for e in P if k / n <= e["px"] < (k + 1) / n or (k == n - 1 and e["px"] == 1.0)]
        if s:
            out.append({"bin": k, "n": len(s), "mean_p": sum(e["px"] for e in s) / len(s), "freq": sum(e["label"] for e in s) / len(s)})
    return out


def floor_fn(fz0, row):
    import planners as PL
    import rank as RK

    def f(t_end):
        fz0.reset(); fz0.caps = {}
        b = RK.b0(fz0, row, PL.CFG["rule"])
        return {"seq": b["seq"] if b["decision"] == "REPAIR" else None, "counters": dict(fz0.c)}
    return f


def length(dom, spec, tau=None, tag=None):
    import compose as CP
    import learn as LN
    import planners as PL
    import views as V
    fz, net = LN.load(dom, spec); fz.net = net
    fz0, base = LN.load(dom, "F0"); fz0.net = base
    tau = None if tau in (None, "None") else float(tau)
    R53.mkdir(parents=True, exist_ok=True)
    outp = R53 / f"length_{dom}_{tag or spec.replace(':', '_').replace('@', '_')}.jsonl"
    with open(outp, "w") as f:
        for rid, row, A, W, meta in panel(dom):
            r0 = {"root_id": row["root_id"], "domain": row["domain"], "inputs": row["inputs"]}
            fl = floor_fn(fz0, r0)(None)
            rec = {"root_id": rid, "K": meta["K"], "N": meta["N"], "arms": {}}
            for arm in ("GA", "REC-ORDERED"):
                fz.reset(); fz.caps = {}
                t0 = time.perf_counter()
                cfg = {**PL.CFG, "t_end": time.perf_counter() + PL.CFG["wall_s"]}
                cands, info = (PL.ga(fz, r0, "AUTO", cfg) if arm == "GA" else PL.rec(fz, r0, arm, cfg))
                wall = time.perf_counter() - t0
                picks = {}
                for rn, rule in (("S0", PL.CFG["rule"]), ("S2", {**PL.CFG["rule"], "S2_tau": tau}) if tau is not None else (None, None)):
                    if rn:
                        p, why, noop = PL.select(fz, r0, [dict(c) for c in cands], {"seq": fl["seq"]} if fl["seq"] else None, rule)
                        picks[rn] = {"why": why, "seq": p["seq"] if p else None, "partition": p["partition"] if p else None, "E": p["E"] if p else None,
                                     "len": len(p["seq"]) if p else 0, "kind": p["kind"] if p else None}
                sizes = collections.defaultdict(list)
                for c in cands:
                    sizes[len(c["seq"])].append(c)
                by = {k: {"E": min(c["E"] for c in v), "F": min((c.get("F") or 0.0) for c in v), "y": max((c.get("y_global") or 0.0) for c in v),
                          "n_chunks": min(len(c["partition"]) for c in v)} for k, v in sizes.items()}
                hm = []
                if arm == "GA":
                    T = CP.Scores(fz, r0, V.rebase)
                    for c in cands:
                        if len(c["seq"]) > 3:
                            A_ = [tuple(map(int, a)) for a in c["seq"]]
                            T.need(CP.requests(A_))
                            r1, r2 = CP.grouped_dp(T, A_, need_multi=True), CP.grouped_dp(T, A_, need_multi=False)
                            hm.append({"m": len(A_), "F_constrained": r1[0] if r1 else None, "F_free": r2[0] if r2 else None,
                                       "free_all_singletons": bool(r2 and max(r2[2]) == 1), "binds": bool(r1 and r2 and abs(r1[0] - r2[0]) > 1e-12)})
                rec["arms"][arm] = {"wall_s": round(wall, 2), "mode": info.get("mode"), "n_cands": len(cands), "by_size": by, "picks": picks, "has_multi": hm,
                                    "witness_set_in_cands": any(sorted(map(tuple, c["seq"])) == sorted(map(tuple, W)) for c in cands)}
            f.write(json.dumps(rec, default=str) + "\n"); f.flush()
            print(rid, {a: (v["picks"].get("S0", {}).get("len"), v["picks"].get("S2", {}).get("len"), v["wall_s"]) for a, v in rec["arms"].items()}, flush=True)


def admission(dom, spec):
    """Paired evidence: for each family and intervention, model admission (A0 / A1(m) / A2) vs physical usefulness (temporary target verified)."""
    import guard as GD
    import learn as LN
    import views as V
    fz, net = LN.load(dom, spec); fz.net = net
    cell = lambda rc: int(rc[0]) * 6 + int(rc[1])  # noqa: E731
    rows = []
    if dom == "3d":
        import xlearn as XLN
        for src, d in (("R5.1", O / "r5" / "d3d"), ("R4.4", O / "r4" / "d3d")):
            J = {j["key"]: j for j in json.loads((d / "jobs.json").read_text())}
            R = {r["key"]: r for r in jl(d / "phys.jsonl")}
            RW = {r["root_id"]: r for r in jl(d / "rows.jsonl")}
            for k, j in J.items():
                if j["kind"] != "Y_TARGET" or j["template"] == "TEMP_baseline" or k not in R:
                    continue
                rec = json.loads(Path(j["path"]).read_text()); kg = rec.get("r44")
                row = {"root_id": j["root_id"], "domain": "3d", "inputs": RW[j["root_id"]]["inputs"]}
                ids = row["inputs"]["ids"]
                task = (ids.index(kg["B"]), cell(kg["pB"]))
                T = V.rebase(row, [], task=task)
                grp = [[ids.index(o), cell(dd)] for o, dd in j["edit"].items()]
                fz.reset(); fz.caps = {}
                y0 = fz.p_noop(T); x = fz.score(T, [grp])[0]
                oc = GD.outcome(R[k], "Y")
                rows.append({"src": src, "split": XLN.new_split(j["fam"]) if src == "R5.1" else "EXPOSED", "fam": j["fam"], "kind": j["template"][5:],
                             "useful": oc == "SUCCESS", "decided": oc in ("SUCCESS", "CERTIFIED_INFEASIBLE"), "outcome": oc, "y0": y0, "py": x["py"], "p11": x["p11"],
                             "grammar_legal": j["template"] != "TEMP_harmful"})
    else:
        import contracts as CT
        import xlearn as XLN
        for src, d in (("R5.1", O / "r5" / "b2d"), ("R4.3", O / "r4" / "b2d")):
            Q = jl(d / "queries.jsonl")
            fam = collections.defaultdict(dict)
            for q in Q:
                if q["kind"] == "PROBE":
                    fam[q["fid"]].setdefault(q["stage"], q)
            for fid, st in fam.items():
                b, a = st.get("PROBE:B_blocked_by_E"), st.get("PROBE:B_free_after_E")
                if not b or not a or b["outcome"] != "CERTIFIED_INFEASIBLE":
                    continue
                rec = json.loads(Path(b["rec"]).read_text()); inp = CT.view2d(rec)
                row = {"root_id": fid, "domain": "2d", "inputs": inp}
                ix = {n: i for i, n in enumerate(inp["ids"])}
                (B, pB), = b["seq"]; (_, pE) = next(((o, dd) for o, dd in a["seq"]), (None, None))
                pE = a["cells"]["oE"]
                T = V.rebase(row, [], task=(ix[B], int(pB)))
                fz.reset(); fz.caps = {}
                y0 = fz.p_noop(T); x = fz.score(T, [[[ix["oE"], int(pE)]]])[0]
                rows.append({"src": src, "split": XLN.new_split(fid) if src == "R5.1" else "EXPOSED", "fam": fid, "kind": "beneficial",
                             "useful": a["outcome"] == "SUCCESS", "decided": a["outcome"] in ("SUCCESS", "CERTIFIED_INFEASIBLE"), "outcome": a["outcome"],
                             "y0": y0, "py": x["py"], "p11": x["p11"], "grammar_legal": True})
    ms = [0.0, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3]

    def rates(S, m, a2=False):
        dec = [r for r in S if r["decided"]]
        adm = lambda r: r["py"] >= r["y0"] + m and (r["py"] > r["y0"]) and (not a2 or r["p11"] >= 0.3)  # noqa: E731
        u = [r for r in dec if r["useful"]]; nu = [r for r in dec if not r["useful"]]
        return {"n_useful": len(u), "n_not_useful": len(nu), "true_admit": (sum(adm(r) for r in u) / len(u)) if u else None,
                "false_admit": (sum(adm(r) for r in nu) / len(nu)) if nu else None}
    out = {"dom": dom, "spec": spec, "n": len(rows), "by": dict(collections.Counter(f"{r['src']}|{r['split']}|{r['kind']}|{r['outcome']}" for r in rows))}
    for sp in ("VAL", "TRAIN", "EXPOSED"):
        S = [r for r in rows if r["split"] == sp]
        out[sp] = {"A0": rates(S, 0.0), **{f"A1_m{m}": rates(S, m) for m in ms}, **{f"A2_m{m}": rates(S, m, True) for m in ms}}
    V_ = out["VAL"]
    ok = [m for m in ms if (V_[f"A1_m{m}"]["false_admit"] is None or V_[f"A1_m{m}"]["false_admit"] <= 0.2) and (V_[f"A1_m{m}"]["true_admit"] or 0) >= 0.8]
    if ok:
        m = ok[0]
    else:
        m = min(ms, key=lambda m: (V_[f"A1_m{m}"]["false_admit"] or 0) * (V_[f"A1_m{m}"]["n_not_useful"] or 0) + (1 - (V_[f"A1_m{m}"]["true_admit"] or 0)) * V_[f"A1_m{m}"]["n_useful"])
    a1, a2 = V_[f"A1_m{m}"], V_[f"A2_m{m}"]
    use_a2 = (a2["false_admit"] is not None and a1["false_admit"] is not None and a2["false_admit"] < a1["false_admit"]
              and (a1["true_admit"] or 0) - (a2["true_admit"] or 0) <= 0.05)
    out["choice"] = {"rule": ("A2" if use_a2 else "A1") if m > 0 or use_a2 else "A0", "m": m, "met_targets": bool(ok)}
    out["rows"] = rows
    R53.mkdir(parents=True, exist_ok=True)
    (R53 / f"admission_{dom}.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items() if k not in ("rows",)}, default=str)[:3000])


def proposals(dom, spec):
    import learn as LN
    import planners as PL
    import recursive as RC
    import views as V
    fz, net = LN.load(dom, spec); fz.net = net
    res = []
    for rid, row, A, W, meta in panel(dom):
        r0 = {"root_id": row["root_id"], "domain": row["domain"], "inputs": row["inputs"]}
        W = [tuple(map(int, a)) for a in W]
        rec = {"root_id": rid, "K": meta["K"], "N": meta["N"]}
        for mode in ("S1", "TOP8", "ANC64", "UNIF"):
            fz.prop_mode = mode; fz.reset(); fz.caps = {}
            D = fz.proposals(r0, V.eligible(r0))
            ga = {(int(o), int(d)) for o, ds in D.items() for d in ds}
            fz.reset(); fz.caps = {}
            t0 = time.perf_counter()
            rc = {**PL.CFG["rec"], "m_max": 5, "wall_s": PL.CFG["wall_s"] * 0.6, "x_unique": PL.CFG["x_unique"], "y_unique": PL.CFG["y_unique"], "disp_tiebreak": False}
            ctx, pool, tree, stop = RC.discover(fz, r0, "R-FIG3", rc)
            wall = time.perf_counter() - t0
            uni = {(int(o), int(d)) for k, v in fz._p.items() for o, ds in v.items() for d in ds}
            sizes = [len(v) for v in D.values() if v]
            import cover as CV
            pj = CV.proj(sizes, 5)
            rec[mode] = {"ga_recall": sum(a in ga for a in W) / len(W), "ga_set": all(a in ga for a in W), "rec_recall": sum(a in uni for a in W) / len(W),
                         "rec_set": all(a in uni for a in W), "rec_wall_s": round(wall, 2), "rec_pool": len(pool), "rec_stop": stop, "ga_exact_envelope": pj["exact_envelope"],
                         "ga_distinct_x": pj["distinct_x"], "latent_draws": fz.c["latent_draws"], "proposal_calls": fz.c["proposal_calls"]}
        fz.prop_mode = "S1"
        res.append(rec)
        print(rid, {m: (round(rec[m]["ga_recall"], 2), round(rec[m]["rec_recall"], 2), rec[m]["rec_wall_s"]) for m in ("S1", "TOP8", "ANC64", "UNIF")}, flush=True)
    summ = {m: {"ga_recall": statistics.mean(r[m]["ga_recall"] for r in res), "ga_set": sum(r[m]["ga_set"] for r in res),
                "rec_recall": statistics.mean(r[m]["rec_recall"] for r in res), "rec_set": sum(r[m]["rec_set"] for r in res),
                "rec_wall_median": statistics.median(r[m]["rec_wall_s"] for r in res), "ga_exact_envelope_roots": sum(r[m]["ga_exact_envelope"] for r in res),
                "ga_distinct_x_median": statistics.median(r[m]["ga_distinct_x"] for r in res)} for m in ("S1", "TOP8", "ANC64", "UNIF")}
    s1, t8, an = summ["S1"], summ["TOP8"], summ["ANC64"]
    choice = {"GA": "TOP8" if (t8["ga_recall"] - s1["ga_recall"] >= 0.10 and t8["ga_exact_envelope_roots"] >= 0.5 * len(res)) else "S1",
              "REC": "ANC64" if (an["rec_recall"] - s1["rec_recall"] >= 0.05 and an["rec_wall_median"] <= 60) else "S1",
              "cvae_recovery_triggered": max(s["rec_recall"] for s in summ.values() if s is not summ["UNIF"]) < 0.5 if dom == "2d" else False}
    out = {"dom": dom, "spec": spec, "n": len(res), "summary": summ, "choice": choice, "per_root": res}
    R53.mkdir(parents=True, exist_ok=True)
    (R53 / f"proposals_{dom}.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({"summary": summ, "choice": choice}, default=str))


if __name__ == "__main__":
    a = sys.argv[1]
    {"calib": lambda: calib(*sys.argv[2:4]), "length": lambda: length(*sys.argv[2:6]), "admission": lambda: admission(*sys.argv[2:4]),
     "proposals": lambda: proposals(*sys.argv[2:4])}[a]()
