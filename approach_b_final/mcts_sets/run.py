#!/usr/bin/env python3
"""Frozen-model driver for the K<=2 set-search study (plan.md P0-P2).  PUBLIC inputs only (contracts view rows: root_id, domain, inputs).
  p0     bundle hash check; K<=3 benchmark parity on a hash subset vs the frozen V3.4 VAL predictions; scorer batch-composition invariance
  pilot  DEV roots, hyper-parameter grid, replay over each root's K<=2 score table (predicted-score agreement / regret only, no labels)
  eval   frozen protocol (P2_PREREG) over every VAL root: EXACT_K2 + all arms x budgets x seeds by budget-charged replay -> predictions
  live   predeclared timing subset: the same arms with LIVE scorer calls (real batches, wall time) + decision parity vs replay
Replay = every K<=2 ordered sequence of the root scored ONCE (exhaustive cost, chunk 8192); each arm then reads that table through the
budgeted Oracle, so unique-sequence charges are identical to live scoring; validity rests on the P0 batch-invariance result.
    python run.py p0|pilot|eval|live  [--n N]      (env MCTS_PUB, MCTS_BUNDLE, MCTS_FROZEN, MCTS_OUT)"""
from __future__ import annotations

import hashlib, itertools, json, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import search_sets as SS  # noqa: E402

PUB = Path(os.environ.get("MCTS_PUB", str(Path.home() / "abf_v34/parity/public_val_2d.jsonl")))
BUNDLE = Path(os.environ.get("MCTS_BUNDLE", str(Path.home() / "abf_v34/approach_b_bundle")))
FROZEN = Path(os.environ.get("MCTS_FROZEN", str(Path.home() / "abf_v34/parity/pred_val_2d_gpu.jsonl")))
OUT = Path(os.environ.get("MCTS_OUT", str(Path.home() / "mcts_sets_runs")))
BUDGETS = (16, 64, 256, 1024)
SEEDS = (0, 1, 2)
GRID = {"UCT_SET": [{"c": c} for c in (0.1, 0.3, 1.0)], "PW_UCT_SET": [{"c": 0.3, "pw": p} for p in ((1.0, 0.5), (2.0, 0.5), (1.0, 0.7))],
        "BEAM_SET": [{"w": w} for w in (4, 8, 16, 32)], "RAND_SET": [{}]}


def jl(p):
    return [json.loads(l) for l in open(p)]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def split_of(rid):
    """Predeclared K-blind DEV/EVAL split: DEV = sha256('MCTS_DEV|'+root_id) in the lowest 20 % of the hash space."""
    return "DEV" if int(hashlib.sha256(("MCTS_DEV|" + rid).encode()).hexdigest(), 16) < (2 ** 256) // 5 else "EVAL"


def models(device="cuda"):
    import benchmark as BM
    samp, scor, man = BM.load_bundle(BUNDLE, "2d", device, 0)       # asserts every 2d bundle hash against MANIFEST.json
    return samp, scor, man


def proposals(root, samp, man):
    import exhaustive as EX
    D6 = EX.proposals(root, samp, man["config"]["proposal_seed"])  # one batched S0 pass, per-root CUDA generator seed 0, top-6
    return {o: v[: man["config"]["M"]] for o, v in D6.items()}, D6


def table(root, scor, D, chunk=8192):
    """Every K<=2 ordered sequence of the frozen pool scored once from the original root -> {seq tuple: {p11, py, px}}, noop separately."""
    seqs = [o for A in SS.Pool(D).sets() for o in itertools.permutations(A)]
    T = {}
    for i in range(0, len(seqs), chunk):
        part = seqs[i:i + chunk]
        for s, r in zip(part, scor.score(root, [list(map(list, s)) for s in part])):
            T[s] = r
    T[()] = scor.score(root, [[]])[0]
    return T


def replay_fn(T):
    return lambda seqs: [T[tuple(tuple(x) for x in s)] for s in seqs]


def live_fn(root, scor):
    return lambda seqs: scor.score(root, seqs)


def root_rows(n=None, split=None):
    rows = [r for r in jl(PUB) if r["domain"] == "2d"]
    if split:
        rows = [r for r in rows if split_of(r["root_id"]) == split]
    rows.sort(key=lambda r: hashlib.sha256(("MCTS_ORDER|" + r["root_id"]).encode()).hexdigest())
    return rows[:n] if n else rows


def p0(n=40):
    import torch
    import exhaustive as EX
    import search as S
    samp, scor, man = models()
    rep = {"bundle_manifest_sha256": sha(BUNDLE / "MANIFEST.json"), "bundle_files_checked": sorted(k for k in man["files"] if k.startswith("2d/")),
           "config": man["config"], "public_sha256": sha(PUB), "frozen_pred_sha256": sha(FROZEN), "torch": torch.__version__,
           "device": torch.cuda.get_device_name(0)}
    pub_keys = set().union(*(set(r) for r in jl(PUB))); inp_keys = set().union(*(set(r["inputs"]) for r in jl(PUB)))
    rep["public_row_keys"], rep["public_input_keys"] = sorted(pub_keys), sorted(inp_keys)
    rep["public_has_private_fields"] = bool((pub_keys | inp_keys) & {"K", "K_legacy", "labels", "masks", "witness", "split", "certificate"})
    fz = {r["root_id"]: r for r in jl(FROZEN)}
    par = {"n": 0, "proposals_equal": 0, "decision_equal": 0, "max_abs_dp11": 0.0, "max_abs_dpnoop": 0.0, "mismatch": []}
    inv = {"roots": 0, "sequences": 0, "max_abs_dp11_batch_vs_single": 0.0, "max_abs_dp11_batch_vs_shuffled": 0.0}
    for r in root_rows(n):
        root = S.Root(r, "2d"); D, D6 = proposals(root, samp, man)
        rec = EX.score_root(root, D6, scor, [man["config"]["rule"]], man["config"]["M"], set(), man["config"]["chunk"])
        d = rec["per_M"]["4"]["decisions"][0]; f = fz[r["root_id"]]
        kind = "ABSTAIN" if d is None else "NOOP" if d["seq"] == [] else "REPAIR"
        moves = [[m["object_index"], m["destination_cell"]] for m in f["moves"]]
        par["n"] += 1; par["proposals_equal"] += {str(k): v[:4] for k, v in rec["D6"].items()} == f["proposals"]
        same = kind == f["decision"] and (kind != "REPAIR" or d["seq"] == moves); par["decision_equal"] += same
        if not same:
            par["mismatch"].append(r["root_id"])
        if d is not None and f["score_p11"] is not None:
            par["max_abs_dp11"] = max(par["max_abs_dp11"], abs(d["p11"] - f["score_p11"]))
        par["max_abs_dpnoop"] = max(par["max_abs_dpnoop"], abs(rec["p_noop"] - f["p_noop"]))
        if inv["roots"] < 12:                                             # batch-composition invariance of the frozen scorer
            T = table(root, scor, D)
            seqs = [s for s in T if s][:600]
            single = {s: scor.score(root, [list(map(list, s))])[0]["p11"] for s in seqs[:120]}
            shuf = sorted(seqs, key=lambda s: hashlib.sha256(repr(s).encode()).hexdigest())
            sh = dict(zip(shuf, (x["p11"] for x in scor.score(root, [list(map(list, s)) for s in shuf]))))
            inv["roots"] += 1; inv["sequences"] += len(seqs)
            inv["max_abs_dp11_batch_vs_single"] = max([inv["max_abs_dp11_batch_vs_single"]] + [abs(T[s]["p11"] - v) for s, v in single.items()])
            inv["max_abs_dp11_batch_vs_shuffled"] = max([inv["max_abs_dp11_batch_vs_shuffled"]] + [abs(T[s]["p11"] - v) for s, v in sh.items()])
    rep["k_le_3_parity_vs_frozen_v34"], rep["scorer_batch_invariance"] = par, inv
    (OUT / "P0_EMPIRICAL.json").write_text(json.dumps(rep, indent=1)); print(json.dumps({"parity": par, "invariance": inv}))


def run_root(r, samp, scor, man, arms_params, budgets, seeds, live=False):
    import search as S
    root = S.Root(r, "2d"); t0 = time.perf_counter(); D, _ = proposals(root, samp, man); t_prop = time.perf_counter() - t0
    out = {"root_id": r["root_id"], "split": split_of(r["root_id"]), "pool": {str(k): v for k, v in D.items()},
           "pool_sha256": hashlib.sha256(json.dumps(sorted((int(k), v) for k, v in D.items())).encode()).hexdigest(), "t_proposal_s": round(t_prop, 4)}
    t1 = time.perf_counter(); T = table(root, scor, D); t_tab = time.perf_counter() - t1
    out["t_table_s"] = round(t_tab, 4); out["table_sha256"] = hashlib.sha256(json.dumps(sorted((list(map(list, s)), round(v["p11"], 7)) for s, v in T.items())).encode()).hexdigest()
    fn = live_fn(root, scor) if live else replay_fn(T)
    ex = SS.run_arm("EXACT_K2", D, replay_fn(T), None, man["config"]["rule"], r["root_id"], disp=root.displacement)
    ex["wall_s"] = round(t_tab + ex["wall_s"], 4)                         # exact cost = full table scoring + selection
    res = [ex]
    for arm, params in arms_params:
        for B in budgets:
            for sd in (seeds if arm != "BEAM_SET" else (0,)):
                x = SS.run_arm(arm, D, fn, B, man["config"]["rule"], r["root_id"], seed=sd, disp=root.displacement, params=params)
                x["params"] = params; res.append(x)
    out["results"] = res
    return out


def pilot(n=None):
    samp, scor, man = models(); fo = OUT / "pilot_dev.jsonl"
    done = {json.loads(l)["root_id"] for l in open(fo)} if fo.exists() else set()
    ap = [(a, p) for a, ps in GRID.items() for p in ps]
    with open(fo, "a") as f:
        for r in root_rows(n, "DEV"):
            if r["root_id"] not in done:
                f.write(json.dumps(run_root(r, samp, scor, man, ap, BUDGETS, SEEDS)) + "\n"); f.flush()
    print(json.dumps({"pilot": str(fo), "roots": sum(1 for _ in open(fo))}))


def eval_(n=None, frozen_params=None):
    samp, scor, man = models(); fp = json.loads((HERE / "reports" / "P2_FROZEN_PARAMS.json").read_text())
    ap = [(a, fp[a]) for a in ("RAND_SET", "BEAM_SET", "UCT_SET", "PW_UCT_SET")]
    fo = OUT / "eval_val.jsonl"; done = {json.loads(l)["root_id"] for l in open(fo)} if fo.exists() else set()
    with open(fo, "a") as f:
        for r in root_rows(n):
            if r["root_id"] not in done:
                f.write(json.dumps(run_root(r, samp, scor, man, ap, BUDGETS, SEEDS)) + "\n"); f.flush()
    print(json.dumps({"eval": str(fo), "roots": sum(1 for _ in open(fo))}))


def live(n=30):
    samp, scor, man = models(); fp = json.loads((HERE / "reports" / "P2_FROZEN_PARAMS.json").read_text())
    ap = [(a, fp[a]) for a in ("RAND_SET", "BEAM_SET", "UCT_SET", "PW_UCT_SET")]
    rows = [r for r in root_rows(None, "EVAL") if int(hashlib.sha256(("MCTS_LIVE|" + r["root_id"]).encode()).hexdigest(), 16) % 20 == 0][:n]
    fo = OUT / "live_timing.jsonl"
    with open(fo, "w") as f:
        for r in rows:
            import torch
            torch.cuda.synchronize(); f.write(json.dumps(run_root(r, samp, scor, man, ap, BUDGETS, (0,), live=True)) + "\n"); f.flush()
    print(json.dumps({"live": str(fo), "roots": len(rows)}))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    a = sys.argv[1:]; n = int(a[a.index("--n") + 1]) if "--n" in a else None
    {"p0": lambda: p0(n or 40), "pilot": lambda: pilot(n), "eval": lambda: eval_(n), "live": lambda: live(n or 30)}[a[0]]()
