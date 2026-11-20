#!/usr/bin/env python3
"""K<=3 ablation prediction harness: one decision per root per arm, through the UNCHANGED approach_b_final pipeline (search.Root ->
proposals -> exhaustive.stream / score_root (every legal K1-K3 ordered sequence, no cap, chunked) -> exhaustive.Selectors = xy.choose with the
frozen rule noop 0.5 / eta 0.3 / alpha = beta = gamma = 0).  Only the component named by the arm changes.  No teacher is called here.

    python run.py predict ARM DOM SPLIT [PART i/k]     -> $K3/runs/predictions/<ARM>/<split>_<dom>.jsonl (resumable, append-only)
    python run.py parity PRED REF                      FULL parity vs the frozen bundle's recorded predictions
    python run.py arms                                 list registered arms
ARM grammar: FULL_s{0,1,2} | DREFIT_s* | E_s* | G_s* | DIRECT_s* | UNIFORM4_r* | TASKFM_s* | NOTASK_s* | SAMPREF_s{1,2} | M1 | C1_r*"""
import hashlib, json, os, sys, time
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE))
import benchmark as BM  # noqa: E402
import exhaustive as EX  # noqa: E402
import search as S  # noqa: E402
import arms as A  # noqa: E402

K3 = Path(os.environ["K3"])
BUNDLE = Path(os.environ["K3_BUNDLE"])
RULE = {"noop_gate": 0.5, "eta": 0.3, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}
TR = K3 / "runs/training"


def spec(arm, dom):
    """-> dict(sampler=('frozen'|'cvae'|'taskfm'|'uniform4', arg), scorer=path, M=4|1, c1=None|seed)."""
    name, _, s = arm.rpartition("_")
    k = int(s[1:]) if s[:1] in "sr" and s[1:].isdigit() else 0
    D0 = BUNDLE / dom / "scorer_s0.pt"
    if arm.startswith("FULL_"):
        return dict(sampler=("frozen", None), scorer=BUNDLE / dom / f"scorer_s{k}.pt", M=4, c1=None)
    if name == "DREFIT":                                    # diagnostic: D re-fitted here with the identical procedure (environment control)
        return dict(sampler=("frozen", None), scorer=TR / "xy" / dom / f"p2_{dom}" / f"D_s{k}" / "model.pt", M=4, c1=None)
    if name in ("E", "G", "DIRECT"):
        return dict(sampler=("frozen", None), scorer=TR / "xy" / dom / f"p2_{dom}" / f"{name}_s{k}" / "model.pt", M=4, c1=None)
    if name == "UNIFORM4":
        return dict(sampler=("uniform4", k), scorer=D0, M=4, c1=None)
    if name == "TASKFM":
        return dict(sampler=("taskfm", TR / "taskfm" / dom / f"taskfm_s{k}" / "model.pt"), scorer=D0, M=4, c1=None)
    if name == "NOTASK":
        return dict(sampler=("cvae", TR / "notask_cvae" / dom / f"scratch_all_notask_s{k}" / "model.pt"), scorer=D0, M=4, c1=None)
    if name == "SAMPREF":                                   # existing frozen-pipeline scratch_all s1/s2 (sampler-seed reference, never the FULL arm)
        return dict(sampler=("cvae", K3 / "stage/samplers" / dom / f"scratch_all_s{k}" / "model.pt"), scorer=D0, M=4, c1=None)
    if arm == "M1":
        return dict(sampler=("frozen", None), scorer=D0, M=1, c1=None)
    if name == "C1":
        return dict(sampler=("frozen", None), scorer=D0, M=4, c1=k)
    raise SystemExit(f"unknown arm {arm}")


class SafeScorer(S.Scorer):
    """DIRECT has no Y / X marginals: report NaN instead of None so exhaustive.flush can build arrays (selection uses p11 only)."""

    def score(self, root, seqs):
        return [{**c, "py": float("nan") if c.get("py") is None else c["py"], "px": float("nan") if c.get("px") is None else c["px"]} for c in super().score(root, seqs)]


def load(arm, dom, dev="cuda"):
    sp = spec(arm, dom)
    samp, _, man = BM.load_bundle(BUNDLE, dom, dev, 0)                          # frozen sampler (hash-checked) + its features / rule
    kind, arg = sp["sampler"]
    fm = None
    if kind == "cvae":
        import placement as PL
        ck = torch.load(arg, map_location=dev, weights_only=False)
        m = PL.TaskCVAE(*ck["grid"], ck["tdim"], ck["cfg"]["hidden"], ck["cfg"]["zdim"]).to(dev)
        m.load_state_dict(ck["state"]); m.task_on = ck["v"]["task"]; m.eval()
        samp.m = m
    elif kind == "taskfm":
        fm = A.load_taskfm(arg, dev)
    scor = SafeScorer(Path(sp["scorer"]), None, device=dev)
    files = {"scorer": str(sp["scorer"]), "scorer_sha256": BM.sha(sp["scorer"]),
             "sampler": str(arg) if kind in ("cvae", "taskfm") else kind, "sampler_sha256": BM.sha(arg) if kind in ("cvae", "taskfm") else None}
    return sp, samp, scor, fm, man, files


def proposals(sp, samp, fm, root, man):
    kind, arg = sp["sampler"]
    if kind == "uniform4":
        return A.propose_uniform4(root, 4, arg), {"sampler_evals": 0}
    if kind == "taskfm":
        D, info = A.propose_taskfm(samp, fm, root, 4, 64, 0)
        return D, {"sampler_evals": info["evals"], "hist_support_lt_M": info["support_lt_M"]}
    D6 = EX.proposals(root, samp, man["config"]["proposal_seed"])            # S1, 64 draws, per-root CUDA generator seed 0 (frozen)
    return D6, {"sampler_evals": 64 * len(root.movable)}


def c1_decision(root, D, scor, seed):
    """C1: one label-blind complete candidate from the M4 pool: K uniform over the lengths that have >= 1 legal sequence, then a uniform legal
    sequence of that length (root-keyed RNG); the D scorer is called once for it and once for the no-op; frozen rule via exhaustive.Selectors."""
    by = {1: [], 2: [], 3: []}
    for s, r in EX.stream(D, 4):
        by[len(s)].append(s)
    ks = [k for k in (1, 2, 3) if by[k]]
    rng = np.random.default_rng(int(hashlib.sha256(f"C1|{seed}|{root.id}".encode()).hexdigest()[:16], 16))
    noop = scor.score(root, [[]])[0]["p11"]
    if not ks:
        return (None if noop < RULE["eta"] else {"seq": [], "p11": noop}) if noop < RULE["noop_gate"] else {"seq": [], "p11": noop}, noop, None, 1
    k = int(rng.choice(ks))
    seq = by[k][int(rng.integers(len(by[k])))]
    c = scor.score(root, [list(map(list, seq))])[0]
    sel = EX.Selectors([RULE])
    sel.update([seq], np.array([c["p11"]]), np.array([len(seq)]), np.array([root.displacement(list(seq))]), np.array([0.0]), np.array([0]),
               {"py": np.array([c["py"]]), "px": np.array([c["px"]]), "J": np.array([0.0])})
    return sel.finish(noop)[4][0], noop, [list(map(int, x)) for x in seq], 2


def pool_hash(D, M):
    return hashlib.sha256(json.dumps({str(o): v[:M] for o, v in sorted(D.items())}, sort_keys=True).encode()).hexdigest()[:20]


def predict(arm, dom, split, part=None, dev="cuda"):
    torch.set_num_threads(1)
    rows = BM.jl(K3 / "runs/public" / f"public_{split}_{dom}.jsonl")
    if part:
        i_, k_ = map(int, part.split("/"))
        rows = [r for r in rows if int(hashlib.sha256(r["root_id"].encode()).hexdigest(), 16) % k_ == i_]
    out = K3 / "runs/predictions" / arm
    out.mkdir(parents=True, exist_ok=True)
    fo = out / (f"{split}_{dom}.jsonl" if not part else f"{split}_{dom}.part{part.replace('/', 'of')}.jsonl")
    import fcntl
    lk = open(str(fo) + ".lock", "w")
    try:                                                     # one writer per prediction file (parallel queues never double-write)
        fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(json.dumps({"arm": arm, "dom": dom, "split": split, "busy": True})); return
    done = {r["root_id"] for r in BM.jl(fo)} if fo.exists() else set()
    sp, samp, scor, fm, man, files = load(arm, dom, dev)
    with open(fo, "a") as f:
        for r in rows:
            if r["root_id"] in done:
                continue
            torch.cuda.reset_peak_memory_stats()
            t0, e0 = time.time(), scor.evals
            root = S.Root(r, dom)
            D, pinfo = proposals(sp, samp, fm, root, man)
            Dm = {int(o): [int(d) for d in v[:sp["M"]]] for o, v in D.items()}
            t1 = time.time()
            c1seq = None
            if sp["c1"] is not None:
                d, p_noop, c1seq, n_sc = c1_decision(root, Dm, scor, sp["c1"])
                n_scored = n_sc - 1
            else:
                rec = EX.score_root(root, Dm, scor, [RULE], 4, set(), 8192)
                d, p_noop, n_scored = rec["per_M"]["4"]["decisions"][0], rec["p_noop"], rec["per_M"]["4"]["n_scored"]
            t2 = time.time()
            kind = "ABSTAIN" if d is None else "NOOP" if d["seq"] == [] else "REPAIR"
            moves = [{"object_id": root.ids[o], "object_index": o, "destination_cell": c} for o, c in (d["seq"] if kind == "REPAIR" else [])]
            f.write(json.dumps({"root_id": r["root_id"], "domain": dom, "decision": kind, "moves": moves, "score_p11": None if d is None else d["p11"],
                                "score_py": None if d is None or d.get("py") is None or d.get("py") != d.get("py") else d.get("py"),
                                "p_noop": p_noop, "proposals": {str(o): v for o, v in Dm.items()}, "pool_hash": pool_hash(Dm, sp["M"]),
                                "n_scored": n_scored, "scorer_evals": scor.evals - e0, "c1_candidate": c1seq, **pinfo,
                                "timing_s": {"proposal": round(t1 - t0, 4), "construct_score_select": round(t2 - t1, 4), "total": round(t2 - t0, 4)},
                                "gpu_peak_mib": round(torch.cuda.max_memory_allocated() / 2 ** 20, 1), "arm": arm, "M": sp["M"], **files,
                                "method": "approach_b_ablation", "device_name": torch.cuda.get_device_name(0), "torch": torch.__version__}) + "\n")
            f.flush()
    print(json.dumps({"arm": arm, "dom": dom, "split": split, "out": str(fo), "n": len(BM.jl(fo))}), flush=True)


def parity(pred, ref):
    a, b = {r["root_id"]: r for r in BM.jl(pred)}, {r["root_id"]: r for r in BM.jl(ref)}
    com = sorted(set(a) & set(b))
    mis = [k for k in com if (a[k]["decision"], a[k]["moves"]) != (b[k]["decision"], b[k]["moves"])]
    prop = sum(a[k]["proposals"] == b[k]["proposals"] for k in com)
    dp = max([abs((a[k]["score_p11"] or 0) - (b[k]["score_p11"] or 0)) for k in com] or [0])
    dn = max([abs(a[k]["p_noop"] - b[k]["p_noop"]) for k in com] or [0])
    ns = sum(a[k]["n_scored"] == b[k]["n_scored"] for k in com)
    res = {"n_pred": len(a), "n_ref": len(b), "n_common": len(com), "proposals_equal": prop, "n_scored_equal": ns, "decision_equal": len(com) - len(mis),
           "max_abs_dp11": dp, "max_abs_dpnoop": dn, "mismatch": mis[:20]}
    print(json.dumps(res))
    return res


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["predict"]:
        predict(a[1], a[2], a[3], a[4] if len(a) > 4 else None)
    elif a[:1] == ["parity"]:
        r = parity(a[1], a[2]); sys.exit(0 if r["decision_equal"] == r["n_common"] == r["n_ref"] and r["proposals_equal"] == r["n_common"] else 1)
    else:
        raise SystemExit(__doc__)
