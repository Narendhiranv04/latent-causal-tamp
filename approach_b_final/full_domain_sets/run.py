#!/usr/bin/env python3
"""Frozen-model driver for the full-legal-domain K<=2 set-search study (plan.md v1.1).  PUBLIC inputs only (root_id, domain, inputs).
  p0     bundle hashes, archived top-6 parity of the reconstructed S1 marginal (every VAL root), marginal support / normalization
  pilot  DEV roots: every arm x budget x seed x grid point, model-only (shared per-root memo of ACTUAL scorer outputs; budgets charged per arm)
  eval   frozen protocol (P3_FROZEN_PARAMS) over every EVAL root -> sealed predictions
  live   predeclared timing subset: frozen arms with LIVE scorer calls, no memo, CUDA-synchronized, warm-up + repeats
Memo = every sequence any arm asks for is scored once per root by the frozen scorer and shared; each arm is still charged for every unique
ordered sequence it requests (search.Oracle).  Validity rests on the scorer's batch-composition invariance (P0, max |dp11| <= 1e-6).
    python run.py p0|pilot|eval|live [--n N]     (env FDS_PUB, FDS_BUNDLE, FDS_OUT)"""
from __future__ import annotations

import hashlib, itertools, json, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import domain as DM  # noqa: E402
import fsearch as FS  # noqa: E402  (named fsearch, NOT search: a local search.py would shadow the frozen approach_b_final/search.py)

PUB = Path(os.environ.get("FDS_PUB", str(Path.home() / "abf_v34/parity/public_val_2d.jsonl")))
BUNDLE = Path(os.environ.get("FDS_BUNDLE", str(Path.home() / "abf_v34/approach_b_bundle")))
OUT = Path(os.environ.get("FDS_OUT", str(Path.home() / "fds_runs")))


def jl(p):
    return [json.loads(l) for l in open(p)]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def hx(tag, rid):
    return int(hashlib.sha256((tag + rid).encode()).hexdigest(), 16)


def split_of(rid):
    """Same K-blind DEV/EVAL split as the completed fixed-pool study: DEV = lowest 20 % of sha256('MCTS_DEV|'+root_id)."""
    return "DEV" if hx("MCTS_DEV|", rid) < (2 ** 256) // 5 else "EVAL"


def models(device="cuda"):
    import benchmark as BM
    return BM.load_bundle(BUNDLE, "2d", device, 0)                # asserts every 2d bundle file hash against MANIFEST.json


def root_rows(n=None, split=None):
    rows = [r for r in jl(PUB) if r["domain"] == "2d"]
    if split:
        rows = [r for r in rows if split_of(r["root_id"]) == split]
    rows.sort(key=lambda r: hashlib.sha256(("MCTS_ORDER|" + r["root_id"]).encode()).hexdigest())
    return rows[:n] if n else rows


def build(r, samp, man, eps):
    """Original public root -> (Root, Domain, seconds spent on the cVAE marginal)."""
    import search as S
    root = S.Root(r, "2d")
    t0 = time.perf_counter(); raw, D6, _ = DM.cvae_raw(root, samp, man["config"]["proposal_seed"], man["config"]["n_z"])
    return root, DM.Domain(raw, D6, eps), time.perf_counter() - t0


def p0():
    import torch
    import exhaustive as EX
    import search as S
    samp, scor, man = models()
    rep = {"bundle_manifest_sha256": sha(BUNDLE / "MANIFEST.json"), "config": man["config"], "public_sha256": sha(PUB), "torch": torch.__version__,
           "device": torch.cuda.get_device_name(0), "roots": 0, "D6_parity": 0, "mismatch": [], "marginal_sum": [9, -9], "zero_mass_legal_actions": 0,
           "legal_actions": 0, "objects": [], "legal_cells": [], "full_unordered_pairs": []}
    keys = set().union(*(set(r) for r in jl(PUB))) | set().union(*(set(r["inputs"]) for r in jl(PUB)))
    rep["public_keys"] = sorted(keys)
    rep["public_has_private_fields"] = bool(keys & {"K", "K_legacy", "labels", "masks", "witness", "split", "certificate", "B", "verified_K"})
    for r in root_rows():
        root = S.Root(r, "2d"); raw, D6, _ = DM.cvae_raw(root, samp, 0, 64); ref = EX.proposals(root, samp, 0)
        rep["roots"] += 1; rep["D6_parity"] += ref == D6
        if ref != D6:
            rep["mismatch"].append(r["root_id"])
        for v in raw.values():
            s = sum(v.values()); rep["marginal_sum"] = [min(rep["marginal_sum"][0], s), max(rep["marginal_sum"][1], s)]
            rep["zero_mass_legal_actions"] += sum(x <= 0 for x in v.values()); rep["legal_actions"] += len(v)
        d = DM.Domain(raw, D6, 0.25)
        rep["objects"].append(len(d.objs)); rep["legal_cells"].append(len(d.L)); rep["full_unordered_pairs"].append(d.n_pairs())
    q = lambda x: {"min": min(x), "median": sorted(x)[len(x) // 2], "max": max(x)}  # noqa: E731
    for k in ("objects", "legal_cells", "full_unordered_pairs"):
        rep[k] = q(rep[k])
    (OUT / "P0_PARITY.json").write_text(json.dumps(rep, indent=1)); print(json.dumps(rep))


EPS, SCH, QD, CS, PWS, WS = (0.1, 0.25, 0.5), ((0.2, 0.4), (0.25, 0.5), (0.4, 0.7)), (0.125, 0.25), (0.1, 0.3), ((1.0, 0.5), (2.0, 0.5)), (4, 16)
KEEP = ("arm", "budget", "seed", "decision", "seq", "p11", "scored", "batches", "sets_scored", "actions_scored", "actions_scored_off4",
        "objects_scored", "pick_stratum", "pick_max_rank", "sets_by_max_tier", "first_off4_at", "tier_events", "stop", "wall_s", "nodes", "batch_sizes",
        "final_level")


def grid():
    """P2_TUNING_PREREG grid, in registered order -> [(arm, params)]."""
    G = []
    for e in EPS:
        for q in QD:
            for c in CS:
                for pw in PWS:
                    G.append(("PW_MCTS_FULL", {"eps": e, "q_dir": q, "c": c, "pw": pw, "nb": 16}))
                    G += [("PW_MCTS_SEEDED4", {"eps": e, "q_dir": q, "c": c, "pw": pw, "nb": 16, "sched": sc}) for sc in SCH]
            for w in WS:
                G.append(("BEAM_FULL", {"eps": e, "q_dir": q, "w": w, "nb": 16, "q_single": 0.5}))
                G += [("BEAM_SEEDED4", {"eps": e, "q_dir": q, "w": w, "nb": 16, "q_single": 0.5, "sched": sc}) for sc in SCH]
    return G


def table(root, dom, scor, chunk=8192):
    """OFFLINE diagnostic: every legal K<=2 ordered sequence of the FULL domain scored once (+ no-op) -> {seq tuple: scorer row}."""
    acts = dom.acts
    seqs = [(a,) for a in acts] + [p for a, b in itertools.combinations(sorted(acts), 2) if a[0] != b[0] and a[1] != b[1] for p in ((a, b), (b, a))]
    T = {(): scor.score(root, [[]])[0]}
    for i in range(0, len(seqs), chunk):
        part = seqs[i:i + chunk]
        for q, r in zip(part, scor.score(root, [list(map(list, x)) for x in part])):
            T[q] = {"p11": r["p11"], "py": r["py"], "px": r["px"]}
    return T


def replay(T):
    return lambda seqs: [T[tuple(tuple(x) for x in q)] for q in seqs]


def compact(x, cfg=None):
    y = {k: x.get(k) for k in KEEP}
    y["cfg"] = cfg
    return y


def run_root(r, samp, scor, man, jobs, fn=None, keep_sets=False):
    """jobs = [(arm, params or None, budget, seed, cfg id)].  fn None -> offline full-table replay (EXACT_FULL included)."""
    t0 = time.perf_counter(); root, dom, t_prior = build(r, samp, man, 0.25)
    doms = {e: DM.Domain({o: {d: dom.raw[(o, d)] for (oo, d) in dom.acts if oo == o} for o in dom.objs}, dom.D6, e) for e in EPS + (1.0,)}
    doms[0.25] = dom
    out = {"root_id": r["root_id"], "split": split_of(r["root_id"]), "objects": len(dom.objs), "legal_cells": len(dom.L), "t_prior_s": round(t_prior, 4)}
    if fn is None:
        t1 = time.perf_counter(); T = table(root, dom, scor); out["t_table_s"] = round(time.perf_counter() - t1, 3); out["table_rows"] = len(T)
        fn = replay(T)
    rule = man["config"]["rule"]; res = []
    for arm, p, B, sd, cfg in jobs:
        p = dict(p or {}); e = p.pop("eps", 0.25)
        x = FS.run_arm(arm, doms[e], fn, B, rule, r["root_id"], sd, root.displacement, p, doms[1.0])
        y = compact(x, cfg)
        if keep_sets and B == 1024 and sd == 0:
            y["scored_sets"] = x["scored_sets"]                       # for P4 attribution (eligible / scored / committed), primary budget only
        res.append(y)
    out["results"] = res; out["t_root_s"] = round(time.perf_counter() - t0, 3)
    return out


def exact_jobs():
    return [("EXACT_FULL", None, None, 0, None), ("EXACT4", None, None, 0, None), ("EXACT6", None, None, 0, None)]


def _done(i, pre):
    d = set()
    for f in (OUT / f"{pre}.{i}.jsonl", OUT / f"{pre}.{i}r.jsonl"):
        if f.exists():
            d |= {json.loads(l)["root_id"] for l in open(f) if l.strip()}
    return d


def pilot(part="0/1", rev=False):
    """rev = helper worker: the same partition in reverse order, its own file, re-checking every file of the partition before each root."""
    i, k = map(int, part.split("/"))
    samp, scor, man = models(); fo = OUT / f"pilot_dev.{i}{'r' if rev else ''}.jsonl"
    done = _done(i, "pilot_dev")
    G = grid()
    jobs = exact_jobs() + [("RAND_FULL", None, B, sd, None) for B in (256, 1024) for sd in (0, 1)]
    jobs += [(a, p, B, sd, j) for j, (a, p) in enumerate(G) for B in (256, 1024) for sd in (0, 1)]
    with open(fo, "a") as f:
        for r in (root_rows(None, "DEV")[::-1] if rev else root_rows(None, "DEV")):
            if hx("PART|", r["root_id"]) % k == i and r["root_id"] not in done and (not rev or r["root_id"] not in _done(i, "pilot_dev")):
                f.write(json.dumps(run_root(r, samp, scor, man, jobs)) + "\n"); f.flush()


def frozen_jobs(budgets=(64, 256, 1024, 4096), seeds=(0, 1, 2)):
    fp = json.loads((HERE / "reports" / "P2_FROZEN_PARAMS.json").read_text())
    jobs = exact_jobs()
    for arm in ("RAND_FULL", "BEAM_SEEDED4", "BEAM_FULL", "BEAM_FULL_UNIFORM", "PW_MCTS_SEEDED4", "PW_MCTS_FULL", "PW_MCTS_UNIFORM"):
        jobs += [(arm, fp.get(arm), B, sd, arm) for B in budgets for sd in seeds]
    return jobs


def frozen(split, part="0/1", rev=False):
    i, k = map(int, part.split("/")); pre = f"frozen_{split.lower()}"
    samp, scor, man = models(); fo = OUT / f"{pre}.{i}{'r' if rev else ''}.jsonl"
    done = _done(i, pre)
    jobs = frozen_jobs()
    with open(fo, "a") as f:
        for r in (root_rows(None, split)[::-1] if rev else root_rows(None, split)):
            if hx("PART|", r["root_id"]) % k == i and r["root_id"] not in done and (not rev or r["root_id"] not in _done(i, pre)):
                f.write(json.dumps(run_root(r, samp, scor, man, jobs, keep_sets=True)) + "\n"); f.flush()


def live(split="DEV", n=30, repeats=3):
    """LIVE timing (no table, no memo): predeclared subset sha256('FDS_LIVE|'+root) % 10 == 0, first n in MCTS_ORDER.  Per root: the
    uncached cVAE marginal (CUDA-synchronized), then every frozen arm at B in {64, 256, 1024, 4096} (seed 0; median of `repeats` after one
    warm-up), EXACT4 / EXACT6 / EXACT_FULL (EXACT_FULL once), and wall-capped runs (B = 4096 cap, W in {0.06, 0.25, 1.0} s).
    End-to-end = marginal + search + selection.  Peak GPU memory per arm.  Decisions are checked against the offline replay."""
    import statistics
    import torch
    samp, scor, man = models(); fp = json.loads((HERE / "reports" / "P2_FROZEN_PARAMS.json").read_text()); rule = man["config"]["rule"]
    rows = [r for r in root_rows(None, split) if hx("FDS_LIVE|", r["root_id"]) % 10 == 0][:n]
    fo = OUT / f"live_{split.lower()}.jsonl"; done = {json.loads(l)["root_id"] for l in open(fo)} if fo.exists() else set()
    sync = torch.cuda.synchronize
    for r in rows:
        if r["root_id"] in done:
            continue
        import search as S
        root = S.Root(r, "2d"); fn = lambda q: scor.score(root, q)  # noqa: E731
        ts = []
        for _ in range(repeats):
            sync(); t0 = time.perf_counter(); raw, D6, _ = DM.cvae_raw(root, samp, 0, 64); sync(); ts.append(time.perf_counter() - t0)
        doms = {e: DM.Domain(raw, D6, e) for e in set(EPS) | {0.25, 1.0}}
        rec = {"root_id": r["root_id"], "t_prior_s": statistics.median(ts), "runs": []}

        def one(arm, B, wall=None, reps=repeats):
            p = dict(fp.get(arm) or {}); e = p.pop("eps", 0.25); w = []
            FS.run_arm(arm, doms[e], fn, min(B or 64, 64), rule, r["root_id"], 0, root.displacement, p, doms[1.0])     # warm-up
            for _ in range(reps):
                torch.cuda.reset_peak_memory_stats(); sync(); t0 = time.perf_counter()
                x = FS.run_arm(arm, doms[e], fn, B, rule, r["root_id"], 0, root.displacement, p, doms[1.0], max_wall=wall); sync()
                w.append(time.perf_counter() - t0)
            y = compact(x, arm); y.update({"live_wall_s": statistics.median(w), "end_to_end_s": statistics.median(w) + rec["t_prior_s"],
                                           "peak_gpu_mb": torch.cuda.max_memory_allocated() / 2 ** 20, "wall_cap_s": wall,
                                           "batch_sizes_all": None})
            rec["runs"].append(y)
        for arm in ("EXACT4", "EXACT6"):
            one(arm, None)
        one("EXACT_FULL", None, reps=1)
        for arm in ("RAND_FULL", "BEAM_SEEDED4", "BEAM_FULL", "BEAM_FULL_UNIFORM", "PW_MCTS_SEEDED4", "PW_MCTS_FULL", "PW_MCTS_UNIFORM"):
            for B in (64, 256, 1024, 4096):
                one(arm, B)
            for W in (0.06, 0.25, 1.0):
                one(arm, 4096, wall=W, reps=1)
        with open(fo, "a") as f:
            f.write(json.dumps(rec) + "\n")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    a = sys.argv[1:]; part = a[a.index("--part") + 1] if "--part" in a else "0/1"
    {"p0": p0, "pilot": lambda: pilot(part, "--rev" in a), "dev": lambda: frozen("DEV", part, "--rev" in a), "eval": lambda: frozen("EVAL", part, "--rev" in a),
     "live": lambda: live(a[a.index("--split") + 1] if "--split" in a else "DEV")}[a[0]]()
