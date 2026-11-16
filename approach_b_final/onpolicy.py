#!/usr/bin/env python3
"""V2 on-policy X/Y evidence (user decision 2026-11-12).  TRAIN roots only; the unchanged finalized teachers; V1 files are never touched.

    python onpolicy.py search   DOM N SEED          V1 full-arm search (D + cVAE, frozen V1 checkpoints) on a K-stratified TRAIN subset
                                                     -> runs/v2/<dom>/search_train.jsonl
    python onpolicy.py items    DOM coverage|collect  labelling items: coverage = EVERY candidate of the first 15 roots per K (K1/K2/K3);
                                                     collect = per root a stratified sample: top-3 by p11, 2 from [0.5, 0.9), 2 from [0.1, 0.5),
                                                     1 from < 0.1 (seeded; fewer where a band is empty)
    python onpolicy.py label    DOM KIND WORKERS     teacher queries: Y at every unique endpoint first, then X of the candidate's order
                                                     (coverage: X only where Y = 1, since X = 1 and Y = 1 needs both) -> runs/v2/<dom>/labels_<kind>.jsonl
    python onpolicy.py coverage DOM                  proposal-vs-ranking diagnostic over the coverage roots
Teacher semantics are those of evaluate._verify_job (2D teacher2d with replay; 3D fin3d run_x / run_y).  Administrative failures are MISSING."""
from __future__ import annotations

import collections, hashlib, json, os, random, sys, time
from pathlib import Path

ABF = Path(os.environ.get("ABF_ROOT", "/scratch/nav/approachb_final"))
SNAP = Path(os.environ.get("ABF_SNAPSHOT", str(ABF / "snapshot/abf_9de85710c2a7103f")))
V2 = ABF / "runs/v2"


def jl(p):
    return [json.loads(l) for l in open(p)] if Path(p).exists() else []


def train_subset(dom, n):
    rows = [r for r in map(json.loads, open(SNAP / f"data{dom.lower()}.jsonl")) if r["split"] == "train" and r["K_legacy"] in ("1", "2", "3")]
    by = collections.defaultdict(list)
    for r in rows:
        by[r["K_legacy"]].append(r)
    out = []
    for K in ("1", "2", "3"):
        out += sorted(by[K], key=lambda r: hashlib.sha256(("v2|" + r["root_id"]).encode()).hexdigest())[:n // 3]
    return out


def search_train(dom, n, seed):
    import search as S
    out = V2 / dom.lower() / "search_train.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {r["root"] for r in jl(out)}
    samp = S.Sampler(dom.lower(), "cvae", seed, ABF / "data" / f"q2_{dom.lower()}")
    cost = ABF / "runs" / f"p3_{dom.lower()}" / f"cost_s{seed}" / "model.pt"
    scor = S.Scorer(ABF / "runs" / f"p2_{dom.lower()}" / f"D_s{seed}" / "model.pt", cost)
    cfg = {"M": 4, "max_expansions": 12, "fair": 4, "alpha_exp": 0.0, "seed": seed}       # = evaluate.SEARCH (V1 frozen)
    with open(out, "a") as f:
        for r in train_subset(dom, n):
            if r["root_id"] in done:
                continue
            res = S.search(S.Root(r, dom.lower()), samp, scor, cfg, mode="iterative")
            res.update(K=r["K_legacy"], order=len(done))
            f.write(json.dumps(res) + "\n"); f.flush()
    print(json.dumps({"dom": dom, "searched": len(jl(out))}))


def items(dom, kind):
    srch = jl(V2 / dom.lower() / "search_train.jsonl")
    rows = {r["root_id"]: r for r in map(json.loads, open(SNAP / f"data{dom.lower()}.jsonl"))}
    out = []
    if kind == "coverage":
        # 10 roots per K; per root the top-T candidates by predicted p11 + R random others (2D T=100 R=50, 3D T=50 R=30)
        T, R = (100, 50) if dom == "2D" else (30, 15)
        nper = 10 if dom == "2D" else 5
        per = collections.Counter()
        for s in srch:
            if per[s["K"]] >= nper:
                continue
            per[s["K"]] += 1
            cs = sorted((c for c in s["cands"] if c["seq"]), key=lambda c: -c["p11"])
            rest = cs[T:]
            pick = cs[:T] + random.Random("v2cov|" + s["root"]).sample(rest, min(R, len(rest)))
            out.append({"root": s["root"], "cands": [c["seq"] for c in pick], "mode": "coverage", "n_all": len(cs)})
    else:
        nper, per = (300 if dom == "2D" else 90), collections.Counter()           # speed-up (user, 2026-11-13): 900 2D / 270 3D roots
        for s in srch:
            if per[s["K"]] >= nper:
                continue
            per[s["K"]] += 1
            rng = random.Random("v2collect|" + s["root"])
            cs = sorted((c for c in s["cands"] if c["seq"]), key=lambda c: -c["p11"])
            pick = cs[:3]
            for lo, hi, k in ((0.5, 0.9, 2), (0.1, 0.5, 2), (0.0, 0.1, 1)):
                band = [c for c in cs[3:] if lo <= c["p11"] < hi and c not in pick]
                pick += rng.sample(band, min(k, len(band)))
            out.append({"root": s["root"], "cands": [c["seq"] for c in pick], "p11": [c["p11"] for c in pick], "mode": "collect"})
    for it in out:
        ids = rows[it["root"]]["inputs"]["ids"]
        it["seqs"] = [[(ids[i], c) for i, c in q] for q in it["cands"]]
    p = V2 / dom.lower() / f"items_{kind}.json"
    p.write_text(json.dumps(out))
    print(json.dumps({"dom": dom, "kind": kind, "roots": len(out), "candidates": sum(len(i["cands"]) for i in out)}))


# --------------------------------------------------------------------------------------------- teacher labelling (CPU pool; unchanged teachers)
_W = {}


def _boot(dom, geom):
    """V2 witness stores are separate from every V1 store."""
    sys.path.insert(0, str(ABF / "code"))
    os.environ["FIN3D_STORE"] = str(V2 / "3d/store")
    import evaluate as EV
    EV._boot(dom, geom)
    _W.update(EV._W)
    if dom == "2D":
        _W["T"]._M["wout"] = str(V2 / "2d/witnesses")


def _job(job):
    import evaluate as EV
    dom, rec = job["dom"], json.loads(Path(job["path"]).read_text())
    t0 = time.process_time()
    out, ycache = [], {}
    if dom == "2D":
        T, cache = _W["T"], {}
        for s in job["seqs"]:
            ek = json.dumps(sorted(s))
            if ek not in ycache:
                ycache[ek] = T.query(rec, s, cache, "Y")
            y = ycache[ek]
            x = T.query(rec, s, cache, "X") if (job["mode"] == "collect" or y.get("y") == 1) else None
            out.append({"seq": s, "x": x, "y": y})
    else:
        F = _W["F"]
        for s in job["seqs"]:
            order = [[o, [c // 6, c % 6]] for o, c in s]
            cells = {**{k: list(v) for k, v in rec["initial_cells"].items()}, **{o: d for o, d in order}}
            ek = json.dumps(sorted(cells.items()))
            if ek not in ycache:
                ycache[ek] = F.capped(F.run_y, rec, cells)
            y = ycache[ek]
            x = F.capped(F.run_x, rec, order) if (job["mode"] == "collect" or y.get("y") == 1) else None
            out.append({"seq": s, "x": x, "y": y})
    return {"root": rec["ids"]["root_id"], "mode": job["mode"], "results": out, "cpu_s": round(time.process_time() - t0, 1)}


def label(dom, kind, workers, lo):
    import multiprocessing as mp
    import evaluate as EV
    its = json.loads((V2 / dom.lower() / f"items_{kind}.json").read_text())
    outp = V2 / dom.lower() / f"labels_{kind}.jsonl"
    done = {r["root"] for r in jl(outp)}
    rows = {r["root_id"]: r for r in map(json.loads, open(SNAP / f"data{dom.lower()}.jsonl"))}
    EV.SNAP = SNAP
    jobs = []
    for it in its:
        if it["root"] in done:
            continue
        p = EV.path_of(dom, rows[it["root"]])
        geom = "fastgeom1" if dom == "2D" and json.loads(Path(p).read_text()).get("geometry_impl") == "fastgeom1" else "original"
        jobs.append({"dom": dom, "path": str(p), "geom": geom, "seqs": it["seqs"], "mode": it["mode"]})
    os.sched_setaffinity(0, set(range(lo, lo + workers)))
    print(json.dumps({"dom": dom, "kind": kind, "jobs": len(jobs), "queries": sum(len(j["seqs"]) for j in jobs)}), flush=True)
    with open(outp, "a") as f:
        for geom in sorted({j["geom"] for j in jobs}):
            js = sorted((j for j in jobs if j["geom"] == geom), key=lambda j: -len(j["seqs"]))
            with mp.get_context("spawn").Pool(workers, initializer=_boot, initargs=(dom, geom), maxtasksperchild=20) as pool:
                for i, r in enumerate(pool.imap_unordered(_job, js), 1):
                    ids = rows[r["root"]]["inputs"]["ids"]
                    for x in r["results"]:
                        x["seq"] = [[ids.index(o), c] for o, c in x["seq"]]
                    f.write(json.dumps(r) + "\n"); f.flush()
                    if i % 10 == 0:
                        print(f"{time.strftime('%H:%M:%S')} {geom} {i}/{len(js)}", flush=True)
                    if (V2 / f"YIELD_{lo}").exists():                    # yield the CPUs to V1 verification (resumable by root)
                        print("YIELD", flush=True)
                        pool.terminate()
                        return


def supervise(kinds):
    """Fixed allocation read from runs/v2/ALLOC ({"workers": N, "lo": L}); a change restarts the pool (finished roots stay on disk)."""
    import subprocess
    py = str(ABF / "venv/bin/python")
    teach = {"2D": str(Path.home() / "approachb3d_v3/2d_q2_spillover/venv313/bin/python"), "3D": str(Path.home() / "approachb3d_mock/env/bin/python")}
    alloc = lambda: json.loads((V2 / "ALLOC").read_text())  # noqa: E731
    for dk in kinds:
        dom, kind = dk.split(":")
        while True:
            its = {i["root"] for i in json.loads((V2 / dom.lower() / f"items_{kind}.json").read_text())}
            if its <= {r["root"] for r in jl(V2 / dom.lower() / f"labels_{kind}.jsonl")}:
                break
            a = alloc()
            p = subprocess.Popen([teach[dom], str(ABF / "code/onpolicy.py"), "label", dom, kind, str(a["workers"]), str(a["lo"])],
                                 stdout=open(ABF / "logs/v2_label.log", "a"), stderr=subprocess.STDOUT, cwd=str(ABF / "code"))
            while p.poll() is None:
                time.sleep(30)
                if alloc() != a:
                    kids = subprocess.run(["pgrep", "-P", str(p.pid)], capture_output=True, text=True).stdout.split()
                    p.terminate()
                    for k in kids:
                        subprocess.run(["kill", k], capture_output=True)
                    break
            p.wait()
        print(f"{time.strftime('%H:%M:%S')} labelled {dom} {kind}", flush=True)


def supervise_old(kinds):
    """Run every (dom, kind) labelling to completion; 14 workers on CPUs 10-23 while no V1 verification runs, else 4 workers on CPUs 6-9.
    Switches by an in-band YIELD flag (the label pool exits after the current root and resumes from its file)."""
    import subprocess
    py = str(ABF / "venv/bin/python")
    teach = {"2D": str(Path.home() / "approachb3d_v3/2d_q2_spillover/venv313/bin/python"), "3D": str(Path.home() / "approachb3d_mock/env/bin/python")}
    v1 = lambda: subprocess.run(["pgrep", "-f", "evaluate.py verify"], capture_output=True).returncode == 0  # noqa: E731
    for dk in kinds:
        dom, kind = dk.split(":")
        while True:
            its = {i["root"] for i in json.loads((V2 / dom.lower() / f"items_{kind}.json").read_text())}
            if its <= {r["root"] for r in jl(V2 / dom.lower() / f"labels_{kind}.jsonl")}:
                break
            workers, lo = (4, 6) if v1() else (14, 10)
            (V2 / f"YIELD_{lo}").unlink(missing_ok=True)
            p = subprocess.Popen([teach[dom], str(ABF / "code/onpolicy.py"), "label", dom, kind, str(workers), str(lo)],
                                 stdout=open(ABF / "logs/v2_label.log", "a"), stderr=subprocess.STDOUT, cwd=str(ABF / "code"))
            while p.poll() is None:
                time.sleep(30)
                if lo == 10 and v1():                               # yield NOW: stop the pool (finished roots are on disk; resumable)
                    kids = subprocess.run(["pgrep", "-P", str(p.pid)], capture_output=True, text=True).stdout.split()
                    p.terminate()
                    for k in kids:
                        subprocess.run(["kill", k], capture_output=True)
                    break
            p.wait()
            (V2 / f"YIELD_{lo}").unlink(missing_ok=True)
        print(f"{time.strftime('%H:%M:%S')} labelled {dom} {kind}", flush=True)


def snapshot():
    """V2 snapshot = V1 snapshot + on-policy labels on TRAIN roots only (coverage + collect).  X per labelled order, Y per endpoint;
    administrative failures absent (MISSING).  Validation / test roots are byte-identical to V1."""
    import stat
    base = SNAP
    extra = {"2D": collections.defaultdict(list), "3D": collections.defaultdict(list)}
    st = collections.Counter()
    for dom in ("2D", "3D"):
        for kind in ("coverage", "collect"):
            for r in jl(V2 / dom.lower() / f"labels_{kind}.jsonl"):
                for x in r["results"]:
                    xr, yr = x["x"] or {}, x["y"] or {}
                    xv = xr.get("x") if dom == "2D" else (xr.get("x") if xr.get("resolution") == "EVALUATED" else None)
                    yv = yr.get("y") if dom == "2D" else (yr.get("y") if yr.get("resolution") == "EVALUATED" else None)
                    extra[dom][r["root"]].append({"seq": x["seq"], "x": xv if xv in (0, 1) else None, "y": yv if yv in (0, 1) else None,
                                                  "x_witnesses": xr.get("witnesses"), "kind": "ONPOLICY_" + kind.upper()})
                    st[(dom, kind, "x" if xv in (0, 1) else "x_missing", "y" if yv in (0, 1) else "y_missing")] += 1
    h = hashlib.sha256(json.dumps({d: {k: v for k, v in sorted(e.items())} for d, e in extra.items()}, sort_keys=True).encode()).hexdigest()[:16]
    out = ABF / "snapshot" / f"abf_v2_{h}"
    if out.exists():
        raise SystemExit(f"REFUSED: {out} exists")
    out.mkdir(parents=True)
    added = collections.Counter()
    for dom in ("2D", "3D"):
        with open(out / f"data{dom.lower()}.jsonl", "w") as f:
            for line in open(base / f"data{dom.lower()}.jsonl"):
                r = json.loads(line)
                if r["root_id"] in extra[dom]:
                    assert r["split"] == "train", r["root_id"]
                    X = {json.dumps(q["seq"]): q for q in r["labels"]["X"]}
                    Y = {json.dumps(sorted(map(tuple, y["edit"]))): y for y in r["labels"]["Y"]}
                    for e in extra[dom][r["root_id"]]:
                        ek = json.dumps(sorted(map(tuple, e["seq"])))
                        if e["y"] is not None and ek not in Y:
                            Y[ek] = {"edit": sorted(map(list, e["seq"])), "y": e["y"], "kinds": [e["kind"]]}; added[(dom, "Y")] += 1
                        xk = json.dumps(e["seq"])
                        if e["x"] is not None and xk not in X:
                            X[xk] = {"seq": e["seq"], "x": e["x"], "kind": e["kind"], "x_witnesses": e["x_witnesses"]}; added[(dom, "X")] += 1
                    r["labels"] = {"X": list(X.values()), "Y": list(Y.values())}
                f.write(json.dumps(r) + "\n")
    for n in ("QUALIFIED_TRAINING_EXCEPTION.json", "EVALUATION_MASKS.json"):
        (out / n).write_bytes((base / n).read_bytes())
    lock = {"snapshot_id": out.name, "base_snapshot": base.name, "variant": "V2_ONPOLICY (user decision 2026-11-12)", "onpolicy_label_counts":
            {"|".join(k): v for k, v in st.items()}, "added": {"|".join(k): v for k, v in added.items()},
            "label_files_sha256": {f"{d}_{k}": hashlib.sha256((V2 / d.lower() / f"labels_{k}.jsonl").read_bytes()).hexdigest()
                                   for d in ("2D", "3D") for k in ("coverage", "collect") if (V2 / d.lower() / f"labels_{k}.jsonl").exists()},
            "files": {n: hashlib.sha256((out / n).read_bytes()).hexdigest() for n in ("data2d.jsonl", "data3d.jsonl")},
            "rule": "TRAIN roots only; validation / test rows identical to the base snapshot"}
    (out / "data_snapshot.lock.json").write_text(json.dumps(lock, indent=1))
    for p_ in sorted(out.rglob("*"), reverse=True) + [out]:
        p_.chmod(p_.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    print(json.dumps({"snapshot": str(out), "added": lock["added"]}))


def coverage(dom):
    """Per coverage root: does ANY search candidate succeed physically (Y = 1 and X = 1)?  -> proposal failure vs ranking failure."""
    lab = {r["root"]: r for r in jl(V2 / dom.lower() / "labels_coverage.jsonl")}
    srch = {r["root"]: r for r in jl(V2 / dom.lower() / "search_train.jsonl")}
    import evaluate as EV
    rule = json.loads((ABF / "runs" / f"p5_{dom.lower()}" / "rule.json").read_text())
    res, per = collections.Counter(), []
    for root, l in lab.items():
        ok = {json.dumps(x["seq"]): int((x["x"] or {}).get("x") == 1 and (x["y"] or {}).get("y") == 1) for x in l["results"]}
        yk = sum((x["y"] or {}).get("y") == 1 for x in l["results"])
        sel = EV.select(srch[root]["cands"], rule)
        sel_ok = ok.get(json.dumps(sel)) if sel else None
        any_ok = any(ok.values())
        cs = sorted((c for c in srch[root]["cands"] if c["seq"]), key=lambda c: -c["p11"])
        best_rank = next((i for i, c in enumerate(cs) if ok.get(json.dumps(c["seq"]))), None)
        per.append({"root": root, "K": srch[root]["K"], "n_cands": len(ok), "n_y1": yk, "n_success": sum(ok.values()), "any_success": any_ok,
                    "selected_success": sel_ok, "best_success_rank": best_rank})
        res["roots"] += 1
        res["proposal_failure(no successful candidate)" if not any_ok else ("ranking_ok(selected succeeds)" if sel_ok else "ranking_failure(success exists, not selected)")] += 1
    out = {"dom": dom, "summary": dict(res), "per_root": per,
           "by_K": {K: dict(collections.Counter("none" if not p["any_success"] else "selected" if p["selected_success"] else "missed" for p in per if p["K"] == K))
                    for K in ("1", "2", "3")}}
    (V2 / dom.lower() / "COVERAGE_DIAGNOSTIC.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("summary", "by_K")}, indent=1))


# --------------------------------------------------------------------------------------------- V3-4: candidate-matched X/Y evidence (plan V3 5.5)
V3OUT = Path(os.environ.get("V3OUT", str(ABF.parent / "runs")))
V34 = V3OUT / "v3_4"
V3_ROOTS = {"2D": {"1": 120, "2": 120, "3": 120, "0": 40, "NONE": 60}, "3D": {"1": 70, "2": 70, "3": 70, "0": 25, "NONE": 40}}


def v3_roots(dom):
    """TRAIN roots stratified by legacy class (K0 and NONE included: their false positives drive no-op / abstention errors), sha256 order."""
    rows = [r for r in map(json.loads, open(ABF / "snapshot/abf_9de85710c2a7103f" / f"data{dom.lower()}.jsonl")) if r["split"] == "train"]
    out = []
    for K, n in V3_ROOTS[dom].items():
        out += sorted((r for r in rows if r["K_legacy"] == K), key=lambda r: hashlib.sha256(("v3|" + r["root_id"]).encode()).hexdigest())[:n]
    return out


def v3_candidates(dom, kind, rule_name, M, B, seed=0):
    """Direct-construction candidates (the deployment distribution) of the chosen sampler on the V3 TRAIN roots, scored by the frozen V2 D."""
    import torch
    import construct as CO
    import search as S
    tag = f"{CO.rule_tag(rule_name, kind)}_M{M}_B{B}_s{seed}"
    out = V34 / dom.lower() / f"cands_{tag}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(l)["root_id"] for l in open(out)} if out.exists() else set()
    samp = CO.make_sampler(dom.lower(), kind, seed, CO.RULES[rule_name])
    scor = S.Scorer(ABF / "runs/v2" / f"p2_{dom.lower()}" / f"D_s{seed}" / "model.pt", ABF / "runs" / f"p3_{dom.lower()}" / f"cost_s{seed}" / "model.pt")
    rule = json.loads((ABF / "runs/v2" / f"p5_{dom.lower()}" / "rule.json").read_text())
    with open(out, "a") as f:
        for r in v3_roots(dom):
            if r["root_id"] not in done:
                rec = CO.run_root(S.Root(r, dom.lower()), samp, scor, M, B, rule, seed)
                rec.update(sampler=tag, scorer="v2:D_s%d" % seed, rule=rule)
                f.write(json.dumps(rec) + "\n"); f.flush()
    print(json.dumps({"out": str(out), "roots": sum(1 for _ in open(out))}))


def v3_items(dom, tag):
    """Per root (seeded, label-blind): top-2 by p11, 1 from [0.3, 0.9), 1 from [0.1, 0.3), 1 below 0.1, 1 uniform random, and every
    constructed order of the selected repair's assignment (same-endpoint order contrasts).  X is queried where Y = 1, and where Y = 0 only for
    items flagged x_on_y0 (a seeded third), so the X | Y = 0 factor keeps observations; unqueried X stays MISSING (marginalized)."""
    import contracts as CT
    rows = {r["root_id"]: r for r in map(json.loads, open(ABF / "snapshot/abf_9de85710c2a7103f" / f"data{dom.lower()}.jsonl"))}
    out = []
    for c in jl(V34 / dom.lower() / f"cands_{tag}.jsonl"):
        rng = random.Random("v3items|" + c["root_id"])
        cs = sorted((x for x in c["cands"] if x["seq"]), key=lambda x: -x["p11"])
        pick, why = [], []
        def add(x, w):
            if x is not None and x["seq"] not in pick:
                pick.append(x["seq"]); why.append(w)
        for x in cs[:2]:
            add(x, "top")
        for lo, hi, w in ((0.3, 0.9, "band_0.3_0.9"), (0.1, 0.3, "band_0.1_0.3"), (0.0, 0.1, "band_lt_0.1")):
            band = [x for x in cs if lo <= x["p11"] < hi and x["seq"] not in pick]
            add(rng.choice(band) if band else None, w)
        rest = [x for x in cs if x["seq"] not in pick]
        add(rng.choice(rest) if rest else None, "random")
        sel = c["selected_ordered_seq"]
        if sel:
            k = CT.ekey(sel)
            for x in cs:
                if CT.ekey(x["seq"]) == k:
                    add(x, "selected_assignment_order")
        ids = rows[c["root_id"]]["inputs"]["ids"]
        out.append({"root": c["root_id"], "K": c["K"], "cands": pick, "why": why, "p11": [next(x["p11"] for x in cs if x["seq"] == q) for q in pick],
                    "x_on_y0": [rng.random() < 1 / 3 for _ in pick], "seqs": [[(ids[i], d) for i, d in q] for q in pick], "mode": "v3"})
    p = V34 / dom.lower() / f"items_{tag}.json"
    p.write_text(json.dumps(out))
    print(json.dumps({"dom": dom, "roots": len(out), "candidates": sum(len(i["cands"]) for i in out)}))


def _v3_boot(dom, geom):
    import construct as CO
    import evaluate as EV
    os.environ["FIN3D_STORE"] = str(V34 / "store_3d")
    CO._boot(dom, geom)
    _W.update(EV._W)
    if dom == "2D":
        (V34 / "witnesses_2d").mkdir(parents=True, exist_ok=True)
        _W["T"]._M["wout"] = str(V34 / "witnesses_2d")


def _v3_job(job):
    """Unchanged teachers (same calls as evaluate._verify_job / V2 _job): Y once per endpoint, X per order (where Y = 1 or flagged)."""
    rec = json.loads(Path(job["path"]).read_text())
    t0 = time.process_time()
    out, ycache = [], {}
    if job["dom"] == "2D":
        T, cache = _W["T"], {}
        for s, xf in zip(job["seqs"], job["x_on_y0"]):
            ek = json.dumps(sorted(s))
            if ek not in ycache:
                ycache[ek] = T.query(rec, s, cache, "Y")
            y = ycache[ek]
            x = T.query(rec, s, cache, "X") if (y.get("y") == 1 or xf) else None
            out.append({"seq": s, "x": x, "y": y})
    else:
        F = _W["F"]
        for s, xf in zip(job["seqs"], job["x_on_y0"]):
            order = [[o, [c // 6, c % 6]] for o, c in s]
            cells = {**{k: list(v) for k, v in rec["initial_cells"].items()}, **{o: d for o, d in order}}
            ek = json.dumps(sorted(cells.items()))
            if ek not in ycache:
                ycache[ek] = F.capped(F.run_y, rec, cells)
            y = ycache[ek]
            x = F.capped(F.run_x, rec, order) if (y.get("y") == 1 or xf) else None
            out.append({"seq": s, "x": x, "y": y})
    return {"root": rec["ids"]["root_id"], "mode": "v3", "results": out, "cpu_s": round(time.process_time() - t0, 1)}


def v3_label(dom, tag, workers, cpu0, host="g2"):
    """Teacher labelling of the V3 items; V3_PART='a,b/n' shards roots across hosts (disjoint), output labels_<tag>_<host>.jsonl (resumable)."""
    import multiprocessing as mp
    import queue, threading
    import evaluate as EV
    EV.SNAP = ABF / "snapshot/abf_9de85710c2a7103f"
    its = json.loads((V34 / dom.lower() / f"items_{tag}.json").read_text())
    part = os.environ.get("V3_PART")
    if part:
        keep, n = part.split("/")
        keep = {int(x) for x in keep.split(",")}
        its = [i for i in its if int(hashlib.sha256(i["root"].encode()).hexdigest(), 16) % int(n) in keep]
    outp = V34 / dom.lower() / f"labels_{tag}_{host}.jsonl"
    done = {r["root"] for r in jl(outp)}
    rows = {r["root_id"]: r for r in map(json.loads, open(EV.SNAP / f"data{dom.lower()}.jsonl"))}
    jobs = []
    for it in its:
        if it["root"] in done:
            continue
        p = EV.path_of(dom, rows[it["root"]])
        geom = "fastgeom1" if dom == "2D" and json.loads(Path(p).read_text()).get("geometry_impl") == "fastgeom1" else "original"
        jobs.append({"dom": dom, "path": str(p), "geom": geom, "seqs": it["seqs"], "x_on_y0": it["x_on_y0"]})
    os.sched_setaffinity(0, set(range(cpu0, cpu0 + workers)))
    print(json.dumps({"dom": dom, "tag": tag, "host": host, "jobs": len(jobs), "queries_max": sum(len(j["seqs"]) for j in jobs)}), flush=True)
    geoms = sorted({j["geom"] for j in jobs})
    if not geoms:
        return
    ctx = mp.get_context("spawn")
    share = {g: max(1, round(workers * sum(j["geom"] == g for j in jobs) / len(jobs))) for g in geoms}
    pools = {g: ctx.Pool(share[g], initializer=_v3_boot, initargs=(dom, g), maxtasksperchild=20) for g in geoms}
    q = queue.Queue()
    for g in geoms:
        it = pools[g].imap_unordered(_v3_job, sorted((j for j in jobs if j["geom"] == g), key=lambda j: -len(j["seqs"])))
        threading.Thread(target=lambda it=it: ([q.put(r) for r in it], q.put(None)), daemon=True).start()
    ended = n = 0
    with open(outp, "a") as f:
        while ended < len(geoms):
            r = q.get()
            if r is None:
                ended += 1
                continue
            ids = rows[r["root"]]["inputs"]["ids"]
            for x in r["results"]:
                x["seq"] = [[ids.index(o), c] for o, c in x["seq"]]
            f.write(json.dumps(r) + "\n"); f.flush()
            n += 1
            if n % 20 == 0:
                print(f"{time.strftime('%H:%M:%S')} {n}/{len(jobs)}", flush=True)
    for p_ in pools.values():
        p_.close(); p_.join()


def v3_snapshot(tag):
    """V3 snapshot = V2 snapshot + V3-4 labels on TRAIN roots only (all hosts' label files); new immutable dir under $V3OUT/snapshot."""
    import stat
    base = ABF / "snapshot/abf_v2_7d146b53e4b92fe4"
    extra = {"2D": collections.defaultdict(list), "3D": collections.defaultdict(list)}
    st, files = collections.Counter(), []
    for dom in ("2D", "3D"):
        for fp in sorted((V34 / dom.lower()).glob(f"labels_{tag[dom]}_*.jsonl")):
            files.append(fp)
            for r in jl(fp):
                for x in r["results"]:
                    xr, yr = x["x"] or {}, x["y"] or {}
                    xv = xr.get("x") if dom == "2D" else (xr.get("x") if xr.get("resolution") == "EVALUATED" else None)
                    yv = yr.get("y") if dom == "2D" else (yr.get("y") if yr.get("resolution") == "EVALUATED" else None)
                    extra[dom][r["root"]].append({"seq": x["seq"], "x": xv if xv in (0, 1) else None, "y": yv if yv in (0, 1) else None,
                                                  "x_witnesses": xr.get("witnesses"), "kind": "V3_DIRECT_CANDIDATE"})
                    st[(dom, "x" if xv in (0, 1) else ("x_not_queried" if not x["x"] else "x_missing"), "y" if yv in (0, 1) else "y_missing")] += 1
    h = hashlib.sha256(json.dumps({d: {k: v for k, v in sorted(e.items())} for d, e in extra.items()}, sort_keys=True).encode()).hexdigest()[:16]
    out = V3OUT / "snapshot" / f"abf_v3_{h}"
    if out.exists():
        raise SystemExit(f"REFUSED: {out} exists")
    out.mkdir(parents=True)
    added = collections.Counter()
    for dom in ("2D", "3D"):
        with open(out / f"data{dom.lower()}.jsonl", "w") as f:
            for line in open(base / f"data{dom.lower()}.jsonl"):
                r = json.loads(line)
                if r["root_id"] in extra[dom]:
                    assert r["split"] == "train", r["root_id"]
                    X = {json.dumps(q["seq"]): q for q in r["labels"]["X"]}
                    Y = {json.dumps(sorted(map(tuple, y["edit"]))): y for y in r["labels"]["Y"]}
                    for e in extra[dom][r["root_id"]]:
                        ek = json.dumps(sorted(map(tuple, e["seq"])))
                        if e["y"] is not None:
                            if ek in Y:
                                assert Y[ek]["y"] == e["y"], (r["root_id"], ek)          # same teacher, same endpoint -> same label
                            else:
                                Y[ek] = {"edit": sorted(map(list, e["seq"])), "y": e["y"], "kinds": [e["kind"]]}; added[(dom, "Y")] += 1
                        xk = json.dumps(e["seq"])
                        if e["x"] is not None:
                            if xk in X:
                                assert X[xk]["x"] == e["x"], (r["root_id"], xk)
                            else:
                                X[xk] = {"seq": e["seq"], "x": e["x"], "kind": e["kind"], "x_witnesses": e["x_witnesses"]}; added[(dom, "X")] += 1
                    r["labels"] = {"X": list(X.values()), "Y": list(Y.values())}
                f.write(json.dumps(r) + "\n")
    for n_ in ("QUALIFIED_TRAINING_EXCEPTION.json", "EVALUATION_MASKS.json"):
        src = base / n_
        if not src.exists():
            src = ABF / "snapshot/abf_9de85710c2a7103f" / n_
        (out / n_).write_bytes(src.read_bytes())
    lock = {"snapshot_id": out.name, "base_snapshot": base.name, "variant": "V3_DIRECT_CANDIDATES (plan V3 5.5)", "tags": tag,
            "label_counts": {"|".join(k): v for k, v in st.items()}, "added": {"|".join(k): v for k, v in added.items()},
            "label_files_sha256": {str(p.name): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
            "files": {n_: hashlib.sha256((out / n_).read_bytes()).hexdigest() for n_ in ("data2d.jsonl", "data3d.jsonl")},
            "rule": "TRAIN roots only; validation / test rows identical to the base snapshot; same-teacher duplicates must agree"}
    (out / "data_snapshot.lock.json").write_text(json.dumps(lock, indent=1))
    for p_ in sorted(out.rglob("*"), reverse=True) + [out]:
        p_.chmod(p_.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    print(json.dumps({"snapshot": str(out), "added": lock["added"], "counts": lock["label_counts"]}))


if __name__ == "__main__":
    c, dom = sys.argv[1], sys.argv[2]
    if c == "search":
        search_train(dom, int(sys.argv[3]), int(sys.argv[4]))
    elif c == "items":
        items(dom, sys.argv[3])
    elif c == "label":
        label(dom, sys.argv[3], int(sys.argv[4]), int(sys.argv[5]))
    elif c == "coverage":
        coverage(dom)
    elif c == "snapshot":
        snapshot()
    elif c == "supervise":
        supervise(sys.argv[2:])
    elif c == "v3cands":
        v3_candidates(dom, sys.argv[3], sys.argv[4], int(sys.argv[5]), int(sys.argv[6]))
    elif c == "v3items":
        v3_items(dom, sys.argv[3])
    elif c == "v3label":
        v3_label(dom, sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), sys.argv[6] if len(sys.argv) > 6 else "g2")
    elif c == "v3snapshot":
        v3_snapshot(json.loads(sys.argv[2]))
    else:
        raise SystemExit(__doc__)
