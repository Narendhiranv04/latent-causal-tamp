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
        per = collections.Counter()
        for s in srch:
            if per[s["K"]] >= 15:
                continue
            per[s["K"]] += 1
            out.append({"root": s["root"], "cands": [c["seq"] for c in s["cands"] if c["seq"]], "mode": "coverage"})
    else:
        for s in srch:
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
                if lo == 10 and v1():
                    (V2 / "YIELD_10").touch()
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
    else:
        raise SystemExit(__doc__)
