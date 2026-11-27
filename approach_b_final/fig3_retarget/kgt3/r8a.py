#!/usr/bin/env python3
"""R8A K <= 3 component ablations of the FINAL clean model on the V3.4 cohort (1,114 public rows; predictions only, no teacher here).
FINAL = clean stage-A cVAE (R7 freeze) -> S1 top-4 proposals (production sampler rule) -> every legal ordered K <= 3 sequence (exhaustive M4)
        -> clean X/Y (frozen stage-B Y + selected GNN X, R7 freeze) -> production rule (noop 0.5 / eta 0.3).  One component changes per arm:
  scoring    UNCOUPLED (w = 0) | ORDINV (order-invariant X) | DIRECT (Z = short-sequence success logit)   [R7 controls, selected seed]
  placement  UNIFORM4 (4 distinct legal cells) | TASKFM (clean task-conditioned flow matching) | NOTASK (clean q2init_all_notask cVAE)
  selection  M1 (top-1 destination per object) | C1 (one label-blind complete candidate)
  generative CR (complete-repair cVAE alone) | CRXY (same CR pool scored by the final X/Y) | FC4 (factorized pool, count-matched to the CR
             pool size, scored by the final X/Y)   [complete_repair_cvae.infer c1 / c2 / c4, main budget 256]
  seeds      FINAL_X{s} = the other X seeds (each on its own stage-B base) with the same cVAE
    python r8a.py predict ARM DOM PUBLIC.jsonl OUT_DIR       (env R7_ROOT, R7_FREEZE_DIR, FIG3_BUNDLE, K3, K3_BUNDLE, CR_BUNDLE, CR_RUNS)"""
from __future__ import annotations

import hashlib, json, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ABF = HERE.parents[1]
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "r3"), str(ABF), str(ABF / "ablations_k3")]
CRDIR = str(ABF / "complete_repair_cvae")                              # own data.py / train.py: put first only when the CR arms import it
def _run():
    """ablations_k3/run.py by path (fig3_retarget/run.py shadows the name)."""
    import importlib.util
    if "k3run" not in sys.modules:
        sp = importlib.util.spec_from_file_location("k3run", ABF / "ablations_k3" / "run.py")
        m = importlib.util.module_from_spec(sp); sys.modules["k3run"] = m; sp.loader.exec_module(m)
    return sys.modules["k3run"]


RULE = {"noop_gate": 0.5, "eta": 0.3, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}


class Pred:
    """XYNet.predict interface for an R7 X model (Ctl / ScalingNet): marginals from coeffs; DIRECT reads sigmoid(a) as the success prob."""

    def __init__(self, net, direct=False):
        self.net, self.direct = net, direct

    def predict(self, b):
        import torch
        import xy as XY
        C = self.net.coeffs(b)
        if self.direct:
            return {"psucc": torch.sigmoid(C["a"]), "p_noop": torch.sigmoid(C["b"][b["y0"]])}
        mg = XY.marginals(C["b"], C["a"], C["w"], b["parent"])
        return {**mg, "p_noop": mg["py"][b["y0"]]}


def freeze(dom):
    return json.loads((Path(os.environ["R7_FREEZE_DIR"]) / f"freeze_{dom}.json").read_text())


def x_net(dom, name):
    import torch
    import xlearn as XLN
    import xy as XY
    R7 = Path(os.environ["R7_ROOT"])
    _, repdat, _, ctrl, s = name.split("_")
    base = XY.load_model(R7 / "xy" / f"p2_{dom}" / f"D_{s}" / "model.pt", "cuda").float().eval()
    net = XLN.make(repdat[0], base, None if ctrl == "base" else ctrl).to("cuda")
    net.load_state_dict(torch.load(R7 / "xl" / "ckpt" / name / "model.pt", map_location="cuda", weights_only=False)["state"])
    return net.eval(), ctrl == "DIRECT", R7 / "xl" / "ckpt" / name / "model.pt"


def cvae(samp, path):
    import torch
    import placement as PLC
    c = torch.load(path, map_location=samp.dev, weights_only=False)
    m = PLC.TaskCVAE(*c["grid"], c["tdim"], c["cfg"]["hidden"], c["cfg"]["zdim"]).to(samp.dev)
    m.load_state_dict(c["state"]); m.task_on = c["v"]["task"]
    samp.m = m.eval()


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def setup(arm, dom):
    import benchmark as BM
    RUN = _run()
    F = freeze(dom)
    R7 = Path(os.environ["R7_ROOT"])
    samp, scor0, man = BM.load_bundle(Path(os.environ["FIG3_BUNDLE"]), dom, "cuda", 0)
    cs = F["cvae"]["pick"].rsplit("_s", 1)[1]
    cpath = R7 / "r7_task" / dom / f"q2init_all_s{cs}" / "model.pt"
    xname = F["x"]["name"]; xs = F["x"]["seed"]
    if arm in ("UNCOUPLED", "ORDINV", "DIRECT"):
        xname = f"{dom}_G1_hi_{arm}_s{xs}"
    elif arm.startswith("FINAL_X"):
        xname = f"{dom}_{F['x']['rep']}1_hi_base_s{arm[7:]}"
    if arm == "NOTASK":
        cpath = R7 / "r7_task" / dom / f"q2init_all_notask_s{cs}" / "model.pt"
    cvae(samp, cpath)
    net, direct, xpath = x_net(dom, xname)
    scor = RUN.SafeScorer.__new__(RUN.SafeScorer)
    scor.net, scor.dev, scor.cost, scor.evals = Pred(net, direct), "cuda", None, 0
    sp = {"M": 1 if arm == "M1" else 4, "c1": 0 if arm == "C1" else None, "prop": "uniform4" if arm == "UNIFORM4" else "taskfm" if arm == "TASKFM" else "cvae"}
    fm = None
    if arm == "TASKFM":
        import arms as A
        fp = Path(os.environ["K3"]) / "runs/training/taskfm" / dom / f"taskfm_s{cs}" / "model.pt"
        fm = A.load_taskfm(fp, "cuda"); sp["fm_path"] = str(fp)
    cr = None
    if arm in ("CR", "CRXY", "FC4"):
        sys.path.insert(0, CRDIR)
        import infer as INF
        crr = Path(os.environ["CR_RUNS"]) / "models" / dom
        best = min(crr.glob("r7_s*"), key=lambda d: json.loads((d / "curve.json").read_text())["best_select"])
        cr = INF.load_cr(str(best / "model.pt"), "cuda")[0]; sp["cr_path"] = str(best / "model.pt")
    files = {"x_ckpt": str(xpath), "x_sha256": sha(xpath), "cvae": str(cpath), "cvae_sha256": sha(cpath), **{k: v for k, v in sp.items() if k.endswith("_path")}}
    return sp, samp, scor, man, fm, cr, files


def decide(arm, dom, sp, samp, scor, man, fm, cr, r):
    import exhaustive as EX
    import search as S
    import arms as A
    RUN = _run()
    root = S.Root(r, dom)
    t0 = time.time()
    if arm in ("CR", "CRXY", "FC4"):
        import infer as INF
        import data as CRD
        b1 = INF.enc_t(dom, r, "cuda", CRD.scalers(dom))
        P = INF.make_pool(cr, dom, r, b1, 256, 0)
        seqs, acct = INF.prefix(P, 256)
        if arm == "CR":
            d = INF.c1(cr, root, b1, seqs, 64, 0)
        elif arm == "CRXY":
            d = INF.c2(scor, root, seqs)
        else:
            d = INF.c4(root, samp, scor, man, len(seqs))
        kind = d["decision"]; seq = d["seq"] if kind == "REPAIR" else []
        extra = {"pool_unique": len(seqs), "pool_hash": INF.pool_hash(seqs), "n_scored": d.get("n_scored"), "p_noop": d.get("p_noop"), "score": d.get("score")}
    else:
        if sp["prop"] == "uniform4":
            D = A.propose_uniform4(root, 4, 0)
        elif sp["prop"] == "taskfm":
            D, _ = A.propose_taskfm(samp, fm, root, 4, 64, 0)
        else:
            D = EX.proposals(root, samp, man["config"]["proposal_seed"])
        Dm = {int(o): [int(x) for x in v[:sp["M"]]] for o, v in D.items()}
        if sp["c1"] is not None:
            dd, p_noop, _, n = RUN.c1_decision(root, Dm, scor, sp["c1"])
        else:
            rec = EX.score_root(root, Dm, scor, [RULE], 4, set(), 8192)
            dd, p_noop, n = rec["per_M"]["4"]["decisions"][0], rec["p_noop"], rec["per_M"]["4"]["n_scored"]
        kind = "ABSTAIN" if dd is None else "NOOP" if dd["seq"] == [] else "REPAIR"
        seq = dd["seq"] if kind == "REPAIR" else []
        extra = {"proposals": {str(o): v for o, v in Dm.items()}, "n_scored": n, "p_noop": p_noop, "score": None if dd is None else dd.get("p11")}
    moves = [{"object_id": root.ids[o], "object_index": int(o), "destination_cell": int(c)} for o, c in seq]
    return {"root_id": r["root_id"], "domain": dom, "decision": kind, "moves": moves, "arm": arm, "wall_s": round(time.time() - t0, 4),
            "scorer_evals": scor.evals, **extra}


def predict(arm, dom, public, out_dir):
    import torch
    torch.set_num_threads(1)
    out = Path(out_dir) / arm; out.mkdir(parents=True, exist_ok=True)
    fo = out / f"pred_{dom}.jsonl"
    done = {json.loads(l)["root_id"] for l in open(fo)} if fo.exists() else set()
    rows = [r for r in map(json.loads, open(public)) if r["domain"] == dom and r["root_id"] not in done]
    sp, samp, scor, man, fm, cr, files = setup(arm, dom)
    (out / f"files_{dom}.json").write_text(json.dumps(files, indent=1))
    with open(fo, "a") as f:
        for r in rows:
            scor.evals = 0
            f.write(json.dumps(decide(arm, dom, sp, samp, scor, man, fm, cr, r), default=float) + "\n"); f.flush()
    print(json.dumps({"arm": arm, "dom": dom, "n": sum(1 for _ in open(fo))}), flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    {"predict": lambda: predict(*a[1:5])}[a[0]]()
