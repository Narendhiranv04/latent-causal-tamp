#!/usr/bin/env python3
"""P5 end-to-end runner: search (GPU) -> stopping rule -> independent physical verification (CPU) -> metrics.  Shared by 2D and 3D.

    python evaluate.py select DOM ARM SEED SPLIT [N]   searches of every root of SPLIT (resumable)  -> runs/p5_<dom>/search/<arm>_s<seed>_<split>.jsonl
    python evaluate.py verify DOM SPLIT RULES.json W   physical X / Y of every unique selected repair -> runs/p5_<dom>/verify.jsonl (cache)
    python evaluate.py tune DOM SPLIT                  stopping-rule grid on VALIDATION -> runs/p5_<dom>/rule.json (frozen)
    python evaluate.py table DOM SPLIT                 Table I(b)-style metrics -> runs/p5_<dom>/table_<split>.json

Verification = the unchanged finalized teachers from the ORIGINAL root: 2D teacher2d (bxy_teacher X with connector + replay, Y from q_ref + replay),
3D fin3d run_x / run_y.  Task success = X = 1 and Y = 1 (no-op: Y of the unedited scene).  Repair success = Task success with exactly the
certified K relocations, on eval_repair roots only.  Planner calls inside the learned search = 0 (reported); verifier calls are reported apart.
Travel = witnessed J_complete of successful repairs only (cost.jrec); never imputed."""
from __future__ import annotations

import collections, itertools, json, math, os, sys, time
from pathlib import Path

import numpy as np

ABF = Path(os.environ.get("ABF_ROOT", "/scratch/nav/approachb_final"))
SNAP = Path(os.environ.get("ABF_SNAPSHOT", ""))
ARMS = {"full": {"sampler": "cvae", "xy": "D", "mode": "iterative"},
        "uncoupled": {"sampler": "cvae", "xy": "E", "mode": "iterative"},
        "orderinv": {"sampler": "cvae", "xy": "G", "mode": "iterative"},
        "direct": {"sampler": "cvae", "xy": "DIRECT", "mode": "iterative"},
        "analytic": {"sampler": "ANALYTIC", "xy": "D", "mode": "iterative"},
        "flow": {"sampler": "fm", "xy": "D", "mode": "iterative"},
        "oneshot": {"sampler": "cvae", "xy": "D", "mode": "oneshot"}}
# "notravel" = the full arm's own searches with gamma = 0 in the frozen stopping rule (plan 5.3)
SEARCH = {"M": 4, "max_expansions": 12, "fair": 4, "alpha_exp": 0.0}


def rows_of(dom, split):
    return [json.loads(l) for l in open(SNAP / f"data{dom.lower()}.jsonl") if json.loads(l)["split"] == split]


def jl(p):
    return [json.loads(l) for l in open(p)] if Path(p).exists() else []


def select_runs(dom, arm, seed, split, limit=None):
    import torch
    import search as S
    a = ARMS[arm]
    out = ABF / "runs" / f"p5_{dom.lower()}" / "search" / f"{arm}_s{seed}_{split}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {r["root"] for r in jl(out)}
    kind = json.loads((ABF / "runs" / f"p1_{dom.lower()}" / "analytic_choice.json").read_text())["kind"] if a["sampler"] == "ANALYTIC" else a["sampler"]
    samp = S.Sampler(dom.lower(), kind, seed, ABF / "data" / f"q2_{dom.lower()}")
    cost = ABF / "runs" / f"p3_{dom.lower()}" / f"cost_s{seed}" / "model.pt"
    scor = S.Scorer(ABF / "runs" / f"p2_{dom.lower()}" / f"{a['xy']}_s{seed}" / "model.pt", cost if cost.exists() else None)
    rows = [r for r in rows_of(dom, split) if r["root_id"] not in done][:limit]
    with open(out, "a") as f:
        for r in rows:
            res = S.search(S.Root(r, dom.lower()), samp, scor, {**SEARCH, "seed": seed}, mode=a["mode"])
            res.update(arm=arm, seed=seed, sampler=kind, K=r["K_legacy"])
            f.write(json.dumps(res) + "\n"); f.flush()
    print(json.dumps({"arm": arm, "seed": seed, "split": split, "searched": len(rows), "gpu_peak_mib": round(torch.cuda.max_memory_allocated() / 2 ** 20, 1)}))


def choose_all(dom, split, rule, arms=None):
    """-> {(arm, seed, root): selected seq | None}; 'notravel' derived from 'full' with gamma = 0."""
    import search as S
    sel = {}
    for f in sorted((ABF / "runs" / f"p5_{dom.lower()}" / "search").glob(f"*_{split}.jsonl")):
        for r in jl(f):
            if arms and r["arm"] not in arms:
                continue
            sel[(r["arm"], r["seed"], r["root"])] = S.select(r["cands"], rule)
            if r["arm"] == "full":
                sel[("notravel", r["seed"], r["root"])] = S.select(r["cands"], {**rule, "gamma": 0.0})
    return sel


# --------------------------------------------------------------------------------------------- physical verification (CPU pool)
_W = {}


def _boot(dom, geom):
    if dom == "2D":
        sys.path.insert(0, str(ABF / "code"))
        import teacher2d as T
        T.boot(geom)
        _W["T"] = T
    else:
        os.environ.setdefault("FIN3D_STORE", str(ABF / "runs/p5_3d/verify_store"))
        sys.path.insert(0, str(Path.home() / "approachb_final_gen/final3d_v4/code"))
        import fin3d as F
        F.boot()
        _W["F"] = F


def _verify_job(job):
    """job: root path, list of sequences [(obj id, cell)] -> per sequence X and Y results (one cache per root)."""
    dom, path, seqs = job["dom"], job["path"], job["seqs"]
    rec = json.loads(Path(path).read_text())
    out = []
    t0 = time.process_time()
    if dom == "2D":
        T, cache = _W["T"], {}
        for s in seqs:
            x = T.query(rec, s, cache, "X") if s else {"x": 1, "status": "EMPTY", "witnesses": []}
            y = T.query(rec, s, cache, "Y")
            out.append({"seq": s, "x": x, "y": y})
    else:
        F = _W["F"]
        for s in seqs:
            order = [[o, [c // 6, c % 6]] for o, c in s]
            x = F.capped(F.run_x, rec, order) if s else {"x": 1, "resolution": "EVALUATED", "witnesses": []}
            cells = {**{k: list(v) for k, v in rec["initial_cells"].items()}, **{o: d for o, d in order}}
            y = F.capped(F.run_y, rec, cells)
            out.append({"seq": s, "x": x, "y": y})
    return {"root": rec["ids"]["root_id"], "results": out, "cpu_s": round(time.process_time() - t0, 1)}


def verify(dom, split, rule_file, workers):
    import multiprocessing as mp
    rule = json.loads(Path(rule_file).read_text())
    rules = rule if isinstance(rule, list) else [rule]
    want = collections.defaultdict(set)
    for r in rules:
        for (arm, seed, root), seq in choose_all(dom, split, r).items():
            if seq is not None:
                want[root].add(json.dumps(seq))
    cache_f = ABF / "runs" / f"p5_{dom.lower()}" / "verify.jsonl"
    have = collections.defaultdict(set)
    for v in jl(cache_f):
        for r in v["results"]:
            have[v["root"]].add(json.dumps(r["seq"]))
    rows = {r["root_id"]: r for r in rows_of(dom, split)}
    jobs = []
    for root, seqs in want.items():
        todo = sorted(seqs - have[root])
        if not todo:
            continue
        ids = rows[root]["inputs"]["ids"]
        geom = "fastgeom1" if dom == "2D" and json.loads(Path(path_of(dom, rows[root])).read_text()).get("geometry_impl") == "fastgeom1" else "original"
        jobs.append({"dom": dom, "path": str(path_of(dom, rows[root])), "geom": geom,
                     "seqs": [[(ids[i], c) for i, c in json.loads(s)] for s in todo]})
    print(json.dumps({"roots": len(want), "jobs": len(jobs), "queries": sum(len(j["seqs"]) for j in jobs)}), flush=True)
    os.sched_setaffinity(0, set(range(24 - workers, 24)))
    with open(cache_f, "a") as f:
        for geom in sorted({j["geom"] for j in jobs}):
            js = [j for j in jobs if j["geom"] == geom]
            with mp.get_context("spawn").Pool(workers, initializer=_boot, initargs=(dom, geom), maxtasksperchild=50) as pool:
                for i, r in enumerate(pool.imap_unordered(_verify_job, js), 1):
                    # store sequences in snapshot index form for joins
                    ids = rows[r["root"]]["inputs"]["ids"]
                    for x in r["results"]:
                        x["seq"] = [[ids.index(o), c] for o, c in x["seq"]]
                    f.write(json.dumps(r) + "\n"); f.flush()
                    if i % 25 == 0:
                        print(f"{time.strftime('%H:%M:%S')} {geom} {i}/{len(js)}", flush=True)


def path_of(dom, row):
    """Verified mirror path of the selected root record (the same file whose sha256 the snapshot recorded)."""
    import contracts as C
    if dom == "2D":
        sel = {r["root_id"]: r for r in json.loads(C.SEL2.read_text())["rows"]}[row["root_id"]]
        return C.DS2 / "raw/roots" / f"{row['root_id']}.json" if sel["source"] == "ORIGINAL_SELECTED" else C.mp(sel["host_store"]) / "roots" / f"{row['root_id']}.json"
    sel = {r["root_id"]: r for r in json.loads((C.V4 / "FINAL_3D_SELECTION_MANIFEST.json").read_text())["rows"]}[row["root_id"]]
    return C.mp(sel["path"]) if sel["path"].startswith("/") else C.SRC3 / sel["path"]


# --------------------------------------------------------------------------------------------- metrics
def outcomes(dom, split, rule):
    """-> {(arm, seed, root): outcome dict} joining selections, physical verification and snapshot masks."""
    import cost as CO
    rows = {r["root_id"]: r for r in rows_of(dom, split)}
    ver = {}
    for v in jl(ABF / "runs" / f"p5_{dom.lower()}" / "verify.jsonl"):
        for r in v["results"]:
            ver[(v["root"], json.dumps(r["seq"]))] = r
    rng = np.full(3, 2 * math.pi) if dom == "2D" else np.array(json.loads((ABF / "runs/p3/ranges3d.json").read_text())["arm_joint_ranges"])
    stores = CO.STORES2 if dom == "2D" else CO.STORES3 + [ABF / "runs/p5_3d/verify_store"]
    out = {}
    for (arm, seed, root), seq in choose_all(dom, split, rule).items():
        r = rows[root]
        K, m = r["K_legacy"], (None if seq is None else len(seq))
        o = {"arm": arm, "seed": seed, "root": root, "K": K, "masks": r["masks"], "status": "ABSTAIN" if seq is None else ("NOOP" if not seq else "REPAIR"), "m": m}
        if seq is not None:
            v = ver.get((root, json.dumps(seq)))
            if v is None:
                o["verified"] = None
            else:
                x = v["x"].get("x") if dom == "2D" else v["x"].get("x")
                y = v["y"].get("y")
                o["verified"] = int(x == 1 and y == 1) if x in (0, 1) and y in (0, 1) else None
                if o["verified"] == 1:
                    xw = v["x"].get("witnesses") or []
                    yw = [v["y"].get("witness")] if dom == "2D" else (v["y"].get("witnesses") or [])
                    ws = [CO.wload(w, stores) for w in xw + [w for w in yw if w]]
                    o["travel"] = None if any(w is None for w in ws) else sum(CO.jrec(w["connector_q"] if "connector_q" in w else w["q"], rng) for w in ws)
        out[(arm, seed, root)] = o
    return out


def summarize(outs, arms):
    res = {}
    for arm in arms:
        os_ = [o for o in outs.values() if o["arm"] == arm]
        if not os_:
            continue
        task = [o for o in os_ if o["masks"]["eval_task"]]
        rep = [o for o in os_ if o["masks"]["eval_repair"]]
        k0 = [o for o in os_ if o["masks"]["eval_noop"]]
        none = [o for o in os_ if o["masks"]["eval_abstain"]]
        succ = lambda o: o.get("verified") == 1 and o["status"] == "REPAIR"  # noqa: E731
        res[arm] = {"task_success": np.mean([succ(o) for o in task]) if task else None, "n_task": len(task),
                    "repair_success": np.mean([succ(o) and o["m"] == int(o["K"]) for o in rep]) if rep else None, "n_repair": len(rep),
                    "shorter_than_K": int(sum(succ(o) and o["m"] < int(o["K"]) for o in rep)),
                    "noop_correct": np.mean([o["status"] == "NOOP" for o in k0]) if k0 else None, "n_k0": len(k0),
                    "abstain_correct": np.mean([o["status"] == "ABSTAIN" for o in none]) if none else None, "n_none": len(none),
                    "unverified": sum(o["status"] == "REPAIR" and o.get("verified") is None for o in os_),
                    "travel_success_mean": float(np.mean([o["travel"] for o in task if succ(o) and o.get("travel") is not None]))
                    if any(succ(o) and o.get("travel") is not None for o in task) else None}
    return {a: {k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in d.items()} for a, d in res.items()}


def tune(dom, split="val"):
    """Stopping-rule grid on VALIDATION roots with the full arm (D + cVAE + iterative); objective (declared before any test run): mean of
    Task success (K1-K3), correct no-op (K0) and correct abstention (NONE); ties -> lower mean executed travel."""
    grid = [{"noop_gate": ng, "eta": e, "alpha": a, "beta": b, "gamma": g} for ng in (0.5, 0.8) for e in (0.0, 0.1, 0.3) for a in (0.0, 0.5)
            for b in (0.0, 0.1) for g in (0.0, 0.5, 2.0)]
    scored = []
    for rule in grid:
        s = summarize(outcomes(dom, split, rule), ["full"]).get("full")
        if not s:
            continue
        parts = [v for v in (s["task_success"], s["noop_correct"], s["abstain_correct"]) if v is not None]
        scored.append((float(np.mean(parts)), -(s["travel_success_mean"] or 0.0), rule, s))
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    best = scored[0]
    out = ABF / "runs" / f"p5_{dom.lower()}" / "rule.json"
    out.write_text(json.dumps(best[2], indent=1))
    (out.parent / "tune_val.json").write_text(json.dumps([{"objective": s[0], "rule": s[2], "summary": s[3]} for s in scored], indent=1))
    print(json.dumps({"best_rule": best[2], "objective": best[0], "summary": best[3]}))


def bootstrap(outs, arm, ref="full", key="task", B=2000, seed=0):
    """Paired root-cluster bootstrap of (arm - ref) over seeds-averaged per-root success."""
    def per_root(a):
        d = collections.defaultdict(list)
        for o in outs.values():
            if o["arm"] == a and o["masks"]["eval_" + key]:
                ok = o.get("verified") == 1 and o["status"] == "REPAIR" and (key != "repair" or o["m"] == int(o["K"]))
                d[o["root"]].append(float(ok))
        return {r: np.mean(v) for r, v in d.items()}
    pa, pr = per_root(arm), per_root(ref)
    roots = sorted(set(pa) & set(pr))
    if not roots:
        return None
    diff = np.array([pa[r] - pr[r] for r in roots])
    rng = np.random.default_rng(seed)
    bs = [diff[rng.integers(0, len(diff), len(diff))].mean() for _ in range(B)]
    return {"delta": float(diff.mean()), "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))], "roots": len(roots)}


def table(dom, split):
    rule = json.loads((ABF / "runs" / f"p5_{dom.lower()}" / "rule.json").read_text())
    outs = outcomes(dom, split, rule)
    arms = list(ARMS) + ["notravel"]
    res = {"rule": rule, "split": split, "summary": summarize(outs, arms),
           "paired_vs_full": {a: {"task": bootstrap(outs, a, key="task"), "repair": bootstrap(outs, a, key="repair")} for a in arms if a != "full"}}
    (ABF / "runs" / f"p5_{dom.lower()}" / f"table_{split}.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res["summary"], indent=1))


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "select":
        select_runs(sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5], int(sys.argv[6]) if len(sys.argv) > 6 else None)
    elif c == "verify":
        verify(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]))
    elif c == "tune":
        tune(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "val")
    elif c == "table":
        table(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(__doc__)
