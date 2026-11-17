#!/usr/bin/env python3
"""Approach B V3.4 portable benchmark harness: public scenes in, one sealed decision per root out, private physical evaluation separately.

    bundle  OUT --sampler DOM=PATH --scorer DOM:SEED=PATH --scalers DOM=PATH      self-contained, hashed inference bundle (no Q2 neural weights)
    public  OUT (--snapshot DATA.jsonl --split S | --index PRIVATE_INDEX.jsonl)   learner-visible scene rows only (contracts view, no K / labels)
    predict --bundle B --input PUBLIC --output PRED [--device cuda|cpu] [--scorer-seed 0] [--part i/k]   Approach B (resumable, per-root atomic lines)
    seal    PRED --public PUBLIC                                                   freeze a prediction file (sha256 + time) BEFORE any teacher call
    validate --public PUBLIC --predictions PRED                                    schema + static legality of ANY method's predictions
    queries --predictions PRED --private INDEX --cache DIR --out JOBS             teacher jobs not yet in the shared cache (sealed predictions only)
    teach   DOM JOBS CACHE WORKERS CPU0                                            unchanged X/Y teachers (run under the teacher env), append to cache
    evaluate --public P --predictions PRED --private INDEX --cache DIR --out RES   per-root outcomes (refuses unsealed predictions; UNKNOWN never = fail)
    summarize --private INDEX --out OUT.json RES...                                denominators, by-K rates, stratified group-cluster bootstrap CIs

Prediction line: {"root_id", "domain", "decision": REPAIR|NOOP|ABSTAIN, "moves": [{"object_id", "object_index", "destination_cell"}], ...}.
A REPAIR is an ordered sequence of <= 3 relocations of distinct movable non-target objects to declared legal cells that are free in the
current hypothetical scene, never an initially occupied cell and never the target's goal cell (construct / search static grammar)."""
from __future__ import annotations

import argparse, collections, glob, hashlib, json, os, resource, sys, time
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
VERSION = "APPROACH_B_BENCH_V1"
RULE = {"noop_gate": 0.5, "eta": 0.3, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}      # = evaluate.GRID[24], frozen in V3-5
CFG = {"M": 4, "propose_top": 6, "n_z": 64, "proposal_rule": "S1", "proposal_seed": 0, "K_max": 3, "B_cap": None, "chunk": 8192, "rule": RULE}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()] if Path(p).exists() else []


def wjson(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(p) + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1))
    os.replace(tmp, p)


# ------------------------------------------------------------------------------------------------ bundle / public
def bundle(out, samplers, scorers, scalers):
    import shutil, torch
    out = Path(out)
    if out.exists():
        raise SystemExit(f"REFUSED: {out} exists (bundles are immutable)")
    files, prov = {}, {}
    for spec, kind in [(s, "sampler") for s in samplers] + [(s, "scorer") for s in scorers] + [(s, "scalers") for s in scalers]:
        key, src = spec.split("=", 1)
        dom, seed = (key.split(":") + ["0"])[:2]
        name = f"{dom}/{kind}.json" if kind == "scalers" else f"{dom}/{kind}{'_s' + seed if kind == 'scorer' else ''}.pt"
        (out / dom).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, out / name)
        files[name] = sha(out / name)
        if kind != "scalers":
            ck = torch.load(out / name, map_location="cpu", weights_only=False)
            prov[name] = {"source_path": src, **{k: ck.get(k) for k in ("prov", "arm", "seed", "epoch", "snapshot", "variant") if k in ck}}
    man = {"version": VERSION, "config": CFG, "files": files, "provenance": prov, "created_utc": time.strftime("%FT%TZ", time.gmtime()),
           "note": "sampler = scratch TaskCVAE scratch_all (random init, no Q2 neural weights); scorer = D-expanded XYNet (random init); "
                   "scalers = frozen TRAIN-only Q2 feature-normalisation constants (not neural weights)"}
    wjson(out / "MANIFEST.json", man)
    print(json.dumps({"bundle": str(out), "files": files}, indent=1))


def load_bundle(b, dom, device, scorer_seed=0, check=True):
    import torch
    import construct as CO
    import placement as PL
    import search as S
    b = Path(b)
    man = json.loads((b / "MANIFEST.json").read_text())
    if check:
        bad = [n for n, h in man["files"].items() if (n.startswith(dom + "/")) and sha(b / n) != h]
        assert not bad, f"bundle hash mismatch: {bad}"
    ck = torch.load(b / dom / "sampler.pt", map_location=device, weights_only=False)
    m = PL.TaskCVAE(*ck["grid"], ck["tdim"], ck["cfg"]["hidden"], ck["cfg"]["zdim"]).to(device)
    m.load_state_dict(ck["state"])
    m.task_on = ck["v"]["task"]
    m.eval()
    samp = S.Sampler(dom, "task:scratch_all", 0, b / dom, device=device, rule=CO.RULES[man["config"]["proposal_rule"]], model=m)
    scor = S.Scorer(b / dom / f"scorer_s{scorer_seed}.pt", None, device=device)          # gamma = 0: the travel head never enters a decision
    return samp, scor, man


def public(out, snapshot=None, split=None, index=None):
    import contracts as CT
    rows = []
    if snapshot:
        dom = "2d" if "2d" in Path(snapshot).name else "3d"
        rows = [{"root_id": r["root_id"], "domain": dom, "inputs": r["inputs"]} for r in jl(snapshot) if r["split"] == split]
    else:
        base = Path(index).parent
        for e in jl(index):
            rec = json.loads((base / e["path"]).read_text())
            v = CT.view2d(rec) if e["domain"] == "2d" else CT.view3d(rec)
            rows.append({"root_id": e["root_id"], "domain": e["domain"], "inputs": v})
    rows.sort(key=lambda r: (r["domain"], r["root_id"]))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(str(out) + ".tmp", "w") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    os.replace(str(out) + ".tmp", out)
    print(json.dumps({"public": str(out), "n": len(rows), "sha256": sha(out)}))


# ------------------------------------------------------------------------------------------------ predict
def predict(bundle_dir, inp, outp, device="cuda", scorer_seed=0, part=None, threads=1):
    import torch
    import exhaustive as EX
    import search as S
    torch.set_num_threads(threads)
    rows = jl(inp)
    if part:
        i_, k_ = map(int, part.split("/"))
        rows = [r for r in rows if int(hashlib.sha256(r["root_id"].encode()).hexdigest(), 16) % k_ == i_]
    done = {r["root_id"] for r in jl(outp)}
    models, cuda = {}, device.startswith("cuda")
    with open(outp, "a") as f:
        for r in rows:
            if r["root_id"] in done:
                continue
            dom = r["domain"]
            if dom not in models:
                models[dom] = load_bundle(bundle_dir, dom, device, scorer_seed)
            samp, scor, man = models[dom]
            if cuda:
                torch.cuda.reset_peak_memory_stats()
            t0 = time.time()
            root = S.Root(r, dom)
            D6 = EX.proposals(root, samp, man["config"]["proposal_seed"])
            t1 = time.time()
            rec = EX.score_root(root, D6, scor, [man["config"]["rule"]], man["config"]["M"], set(), man["config"]["chunk"])
            t2 = time.time()
            d = rec["per_M"][str(man["config"]["M"])]["decisions"][0]
            kind = "ABSTAIN" if d is None else "NOOP" if d["seq"] == [] else "REPAIR"
            moves = [{"object_id": root.ids[o], "object_index": o, "destination_cell": c} for o, c in (d["seq"] if kind == "REPAIR" else [])]
            f.write(json.dumps({"root_id": r["root_id"], "domain": dom, "decision": kind, "moves": moves,
                                "score_p11": None if d is None else d["p11"], "p_noop": rec["p_noop"],
                                "proposals": {k: v[:man["config"]["M"]] for k, v in rec["D6"].items()},
                                "n_scored": rec["per_M"][str(man["config"]["M"])]["n_scored"],
                                "timing_s": {"proposal": round(t1 - t0, 4), "construct_score_select": round(t2 - t1, 4), "total": round(t2 - t0, 4)},
                                "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
                                "gpu_peak_mib": round(torch.cuda.max_memory_allocated() / 2 ** 20, 1) if cuda else None,
                                "method": "approach_b", "scorer_seed": scorer_seed, "device": device,
                                "device_name": torch.cuda.get_device_name(0) if cuda else "cpu", "torch": torch.__version__}) + "\n")
            f.flush()
    print(json.dumps({"predictions": str(outp), "n": len(jl(outp))}), flush=True)


# ------------------------------------------------------------------------------------------------ seal / validate
def seal(pred, pub):
    p = Path(str(pred) + ".SEAL.json")
    if p.exists():
        raise SystemExit(f"REFUSED: {p} exists")
    rows = jl(pred)
    ids = [r["root_id"] for r in rows]
    assert len(ids) == len(set(ids)), "duplicate root ids in predictions"
    wjson(p, {"predictions": Path(pred).name, "sha256": sha(pred), "n": len(rows), "public_sha256": sha(pub), "sealed_utc": time.strftime("%FT%TZ", time.gmtime()),
              "statement": "sealed before any physical teacher call on these predictions"})
    os.chmod(pred, 0o444)
    print(p.read_text())


def legality(row, moves):
    """-> None if the ordered move list is a legal REPAIR for this public root, else the first violated rule."""
    inp = row["inputs"]
    ids, tid = inp["ids"], inp["tid"]
    fixed = [bool(a[3]) for a in inp["attrs"]] if row["domain"] == "2d" else [False] * len(ids)
    cells0, legal, goal = [int(c) for c in inp["cells0"]], set(int(c) for c in inp["legal_cells"]), int(inp["goal_cell"])
    if not 1 <= len(moves) <= 3:
        return "LENGTH"
    cells, seen = list(cells0), set()
    for m in moves:
        o = m.get("object_index", ids.index(m["object_id"]) if m.get("object_id") in ids else None)
        if o is None or not 0 <= o < len(ids) or (m.get("object_id") not in (None, ids[o])):
            return "UNKNOWN_OBJECT"
        d = int(m["destination_cell"])
        if o == tid or fixed[o]:
            return "IMMOVABLE_OBJECT"
        if o in seen:
            return "OBJECT_MOVED_TWICE"
        if d not in legal or d in cells or d in cells0 or d == goal:
            return "ILLEGAL_DESTINATION"
        seen.add(o)
        cells[o] = d
    return None


def validate(pub, pred, quiet=False):
    P = {r["root_id"]: r for r in jl(pub)}
    out, c = {}, collections.Counter()
    for r in jl(pred):
        if r["root_id"] not in P:
            c["UNKNOWN_ROOT"] += 1
            continue
        if r["root_id"] in out:
            c["DUPLICATE"] += 1
            continue
        dec = r.get("decision")
        err = None if dec in ("NOOP", "ABSTAIN") and not r.get("moves") else legality(P[r["root_id"]], r.get("moves") or []) if dec == "REPAIR" else "BAD_DECISION"
        out[r["root_id"]] = err
        c[err or "VALID_" + dec] += 1
    c["MISSING"] = len(set(P) - set(out))
    if not quiet:
        print(json.dumps(dict(c)))
    return out, c


# ------------------------------------------------------------------------------------------------ physical evaluation
def seq_of(r):
    return [[m["object_index"], int(m["destination_cell"])] for m in r["moves"]]


def cache_labels(cache_dir, dom):
    import importlib.util
    sp = importlib.util.spec_from_file_location("v32b_phys", H / "scripts/v32b_phys.py")
    V = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(V)
    return V.labels(dom, str(Path(cache_dir) / f"verify_{dom}*.jsonl")), V.outcome


def need(pred, index, cache_dir, out):
    seal_ = Path(str(pred) + ".SEAL.json")
    assert seal_.exists() and json.loads(seal_.read_text())["sha256"] == sha(pred), "predictions are not sealed (run seal first)"
    priv = {e["root_id"]: e for e in jl(index)}
    base = Path(index).parent
    jobs = collections.defaultdict(lambda: collections.defaultdict(set))
    have = {d: cache_labels(cache_dir, d)[0] for d in ("2d", "3d")}
    for r in jl(pred):
        if r["decision"] != "REPAIR":
            continue
        e = priv[r["root_id"]]
        k = (r["root_id"], json.dumps(seq_of(r)))
        if None in have[e["domain"]].get(k, (None, None)):
            jobs[e["domain"]][r["root_id"]].add(json.dumps([[r_["object_id"], int(r_["destination_cell"])] for r_ in r["moves"]]))
    n = {}
    for d, roots in jobs.items():
        rows = [{"root_id": rid, "dom": d.upper(), "path": str((base / priv[rid]["path"]).resolve()), "geom": priv[rid].get("geom", "original"),
                 "seqs": [json.loads(s) for s in sorted(ss)], "ids": priv[rid]["ids"]} for rid, ss in sorted(roots.items())]
        with open(f"{out}_{d}.jsonl", "w") as f:
            for j in rows:
                f.write(json.dumps(j) + "\n")
        n[d] = {"roots": len(rows), "queries": sum(len(j["seqs"]) for j in rows)}
    print(json.dumps(n))


def teach(dom, jobs_file, cache_dir, workers, cpu0):
    """Unchanged teachers (evaluate._verify_job behind construct._boot); results keyed by (root, [[object index, cell]]) like construct.verify."""
    import multiprocessing as mp
    import construct as CO
    import evaluate as EV
    cache = Path(cache_dir) / f"verify_{dom}.jsonl"
    have = {(v["root"], json.dumps(x["seq"])) for v in jl(cache) for x in v["results"]}
    jobs = []
    for j in jl(jobs_file):
        seqs = [s for s in j["seqs"] if (j["root_id"], json.dumps([[j["ids"].index(o), c] for o, c in s])) not in have]
        if seqs:
            jobs.append({**j, "seqs": seqs})
    os.sched_setaffinity(0, set(range(cpu0, cpu0 + workers)))
    geoms = sorted({j["geom"] for j in jobs})
    print(json.dumps({"dom": dom, "roots": len(jobs), "queries": sum(len(j["seqs"]) for j in jobs)}), flush=True)
    with open(cache, "a") as f:
        for g in geoms:
            sub = [j for j in jobs if j["geom"] == g]
            with mp.get_context("spawn").Pool(workers, initializer=CO._boot, initargs=(dom.upper(), g), maxtasksperchild=50) as pool:
                for i, r in enumerate(pool.imap_unordered(EV._verify_job, sub), 1):
                    ids = next(j["ids"] for j in sub if j["root_id"] == r["root"])
                    for x in r["results"]:
                        x["seq"] = [[ids.index(o), c] for o, c in x["seq"]]
                    r["teacher_provenance"] = "unchanged finalized teacher (evaluate._verify_job), V3.4 benchmark"
                    f.write(json.dumps(r) + "\n"); f.flush()
                    if i % 25 == 0:
                        print(f"{time.strftime('%H:%M:%S')} {g} {i}/{len(sub)}", flush=True)


def evaluate(pub, pred, index, cache_dir, out):
    seal_ = Path(str(pred) + ".SEAL.json")
    assert seal_.exists() and json.loads(seal_.read_text())["sha256"] == sha(pred), "predictions are not sealed"
    valid, _ = validate(pub, pred, quiet=True)
    priv = {e["root_id"]: e for e in jl(index)}
    preds = {r["root_id"]: r for r in jl(pred)}
    lab = {d: cache_labels(cache_dir, d) for d in ("2d", "3d")}
    rows = []
    for rid, e in sorted(priv.items()):
        r = preds.get(rid)
        if r is None:
            o, sel = "MISSING_PREDICTION", None
        elif valid.get(rid):
            o, sel = "INVALID_" + valid[rid], None
        else:
            sel = None if r["decision"] == "ABSTAIN" else [] if r["decision"] == "NOOP" else seq_of(r)
            L, outcome = lab[e["domain"]]
            o = outcome(sel, L, rid)
        rows.append({"root_id": rid, "domain": e["domain"], "K": e["K"], "masks": e["masks"], "group": e.get("evaluation_group_id", rid),
                     "outcome": o, "decision": r and r["decision"], "seq": sel, "score_p11": r and r.get("score_p11"),
                     "latency_s": r and (r.get("timing_s") or {}).get("total")})
    with open(out, "w") as f:
        for x in rows:
            f.write(json.dumps(x) + "\n")
    print(json.dumps({"results": str(out), **collections.Counter(x["outcome"] for x in rows)}))


# ------------------------------------------------------------------------------------------------ summary statistics
def correct(x):
    """-> (task, noop, abstain) indicators or None when the root is outside that denominator (UNKNOWN -> None, never a failure)."""
    m, o = x["masks"], x["outcome"]
    t = None if not m.get("eval_task") or o == "UNKNOWN" else float(o == "SUCCESS")
    n = None if not m.get("eval_noop") else float(o == "NOOP")
    a = None if not m.get("eval_abstain") else float(o == "ABSTAIN")
    return t, n, a


def boot_ci(groups, weights=None, n=2000, seed=0):
    """groups: {stratum: [(group id, [values])]} -> (point, lo, hi).  Stratified cluster bootstrap: resample evaluation groups within each
    stratum; the estimate is the stratum-weighted mean of per-stratum root means (weights None -> pooled root mean)."""
    import numpy as np
    g = np.random.default_rng(seed)

    def est(sample):
        means = {s: (sum(sum(v) for _, v in gs) / max(1, sum(len(v) for _, v in gs))) for s, gs in sample.items() if sum(len(v) for _, v in gs)}
        if weights:
            w = {s: weights[s] for s in means}
            return sum(means[s] * w[s] for s in means) / sum(w.values())
        tot = sum(sum(len(v) for _, v in gs) for gs in sample.values())
        return sum(sum(sum(v) for _, v in gs) for gs in sample.values()) / max(1, tot)

    pt = est(groups)
    bs = [est({s: [gs[i] for i in g.integers(0, len(gs), len(gs))] for s, gs in groups.items() if gs}) for _ in range(n)]
    return [round(100 * pt, 2), round(100 * float(np.percentile(bs, 2.5)), 2), round(100 * float(np.percentile(bs, 97.5)), 2)]


def summarize(index, out, results, ref_weights=None):
    W = json.loads(Path(ref_weights).read_text()) if ref_weights else None
    S = {}
    for rp in results:
        R = jl(rp)
        for dom in sorted({x["domain"] for x in R}):
            X = [x for x in R if x["domain"] == dom]
            res = {"n_roots": len(X), "outcomes": dict(collections.Counter(x["outcome"] for x in X))}
            for name, idx, strata in (("task", 0, ("1", "2", "3")), ("noop", 1, ("0",)), ("abstain", 2, ("NONE",))):
                G = {s: collections.defaultdict(list) for s in strata}
                unk = 0
                for x in X:
                    if x["K"] in strata:
                        v = correct(x)[idx]
                        if v is None and name == "task" and x["masks"].get("eval_task"):
                            unk += 1
                        if v is not None:
                            G[x["K"]][x["group"]].append(v)
                Gl = {s: list(d.items()) for s, d in G.items()}
                res[name] = {"n": sum(len(v) for d in G.values() for v in d.values()), "unknown": unk, "rate_ci": boot_ci(Gl)}
                if name == "task":
                    res["task_by_K"] = {s: {"n": sum(len(v) for v in G[s].values()), "rate_ci": boot_ci({s: Gl[s]})} for s in strata}
                    if W and dom in W:
                        res["task_standardized"] = {"weights": W[dom], "rate_ci": boot_ci(Gl, W[dom])}
            att = [x for x in X if x["decision"] == "REPAIR" and x["masks"].get("eval_task")]
            res["attempted_repair"] = {"n": len(att), "success": sum(x["outcome"] == "SUCCESS" for x in att),
                                       "fail_x": sum(x["outcome"] == "FAIL_X" for x in att), "fail_y": sum(x["outcome"] == "FAIL_Y" for x in att),
                                       "unknown": sum(x["outcome"] == "UNKNOWN" for x in att)}
            nn = [x for x in X if x["masks"].get("eval_abstain")]
            res["none_false_repair"] = {"n": len(nn), "repair_attempts": sum(x["decision"] == "REPAIR" for x in nn)}
            sel = [(x["score_p11"], x["outcome"] == "SUCCESS") for x in X if x["decision"] == "REPAIR" and x.get("score_p11") is not None and x["outcome"] in ("SUCCESS", "FAIL_X", "FAIL_Y")]
            if sel:
                res["calibration"] = {"n": len(sel), "mean_p11": round(sum(p for p, _ in sel) / len(sel), 4), "success_rate": round(sum(s for _, s in sel) / len(sel), 4)}
            lat = sorted(x["latency_s"] for x in X if x.get("latency_s") is not None)
            if lat:
                q = lambda f: lat[min(len(lat) - 1, int(f * len(lat)))]  # noqa: E731
                res["latency_s"] = {"p50": q(0.5), "p90": q(0.9), "p99": q(0.99), "max": lat[-1]}
            S[f"{Path(rp).stem}:{dom}"] = res
    wjson(out, S)
    print(json.dumps(S, indent=1)[:4000])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("bundle"); a.add_argument("out"); a.add_argument("--sampler", action="append", default=[]); a.add_argument("--scorer", action="append", default=[]); a.add_argument("--scalers", action="append", default=[])
    a = sp.add_parser("public"); a.add_argument("out"); a.add_argument("--snapshot"); a.add_argument("--split"); a.add_argument("--index")
    a = sp.add_parser("predict"); a.add_argument("--bundle", required=True); a.add_argument("--input", required=True); a.add_argument("--output", required=True)
    a.add_argument("--device", default="cuda"); a.add_argument("--scorer-seed", type=int, default=0); a.add_argument("--part"); a.add_argument("--threads", type=int, default=1)
    a = sp.add_parser("seal"); a.add_argument("predictions"); a.add_argument("--public", required=True)
    a = sp.add_parser("validate"); a.add_argument("--public", required=True); a.add_argument("--predictions", required=True)
    a = sp.add_parser("queries"); a.add_argument("--predictions", required=True); a.add_argument("--private", required=True); a.add_argument("--cache", required=True); a.add_argument("--out", required=True)
    a = sp.add_parser("teach"); a.add_argument("dom"); a.add_argument("jobs"); a.add_argument("cache"); a.add_argument("workers", type=int); a.add_argument("cpu0", type=int)
    a = sp.add_parser("evaluate"); a.add_argument("--public", required=True); a.add_argument("--predictions", required=True); a.add_argument("--private", required=True)
    a.add_argument("--cache", required=True); a.add_argument("--out", required=True)
    a = sp.add_parser("summarize"); a.add_argument("results", nargs="+"); a.add_argument("--private"); a.add_argument("--out", required=True); a.add_argument("--weights")
    A = ap.parse_args()
    if A.cmd == "bundle":
        bundle(A.out, A.sampler, A.scorer, A.scalers)
    elif A.cmd == "public":
        public(A.out, A.snapshot, A.split, A.index)
    elif A.cmd == "predict":
        predict(A.bundle, A.input, A.output, A.device, A.scorer_seed, A.part, A.threads)
    elif A.cmd == "seal":
        seal(A.predictions, A.public)
    elif A.cmd == "validate":
        validate(A.public, A.predictions)
    elif A.cmd == "queries":
        need(A.predictions, A.private, A.cache, A.out)
    elif A.cmd == "teach":
        teach(A.dom, A.jobs, A.cache, A.workers, A.cpu0)
    elif A.cmd == "evaluate":
        evaluate(A.public, A.predictions, A.private, A.cache, A.out)
    elif A.cmd == "summarize":
        summarize(A.private, A.out, A.results, A.weights)
