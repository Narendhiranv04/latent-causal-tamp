#!/usr/bin/env python3
"""R10.9 / R10.3 unified short-horizon prediction driver (gvlab2, public rows only; no teacher, no label, no reference is read here).

Every learned component comes from the R10 clean lineage (R7_ROOT = R10 runs, R10_MODEL_FREEZE.json hashes asserted); the sampler uses the
canonical-TRAIN Q2 scalers.  One component changes per arm (r8a.py semantics, unchanged production rule noop 0.5 / eta 0.3, S1 top-4, exhaustive
ordered K <= 3):
  FAM   one cached scoring pass of the FINAL pool -> FINAL | FINAL_RANK (top nonempty by p11) | YONLY (p11 := pY of the endpoint, same rule,
        deterministic X-independent tie-break key(cost, m, D, seq)) | YONLY_RANK (top nonempty by pY) | M1 (top-1 destination subset)
  B0    historical production bundle (sampler + scorer_s0 as stored), qualified reference
  UNCOUPLED | ORDINV | DIRECT          R10 G1 controls of the selected X seed
  REP_A1 | REP_M1 | REP_G0             representation x supervision controls (selected X seed, own stage-B base)
  FINAL_X<s>                           alternate feasibility bundle: G1 X seed s on its own stage-B Y, FINAL cVAE
  SEED<s>                              full seed-matched bundle: cVAE s + stage-B s + G1 X s
  UNIFORM4 | TASKFM | NOTASK | C1 | CR | CRXY | FC4   as r8a.py with R10 checkpoints
    python r10eval.py predict ARM DOM PUBLIC.jsonl OUT_DIR      -> OUT_DIR/<arm>/<roster>_<dom>.jsonl (+ files_<dom>.json, resumable)"""
from __future__ import annotations

import hashlib, json, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent)]
import r8a as R8  # noqa: E402  (paths, Pred, cvae, x_net, _run)

RULE = R8.RULE


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def freeze(dom):
    return json.loads((Path(os.environ["R7_ROOT"]) / f"freeze_{dom}.json").read_text())


def scalers(samp, dom):
    import numpy as np
    sc = json.loads((Path(os.environ["R10_Q2"]) / f"q2_{dom}" / "scalers.json").read_text())
    samp.mu, samp.sd = np.array(sc["mean"], np.float32), np.array(sc["std"], np.float32)
    return sha(Path(os.environ["R10_Q2"]) / f"q2_{dom}" / "scalers.json")


class Cached:
    """Scorer wrapper: one network evaluation per (root, sequence); optional p11 := pY (Y-only score replacement)."""

    def __init__(self, base):
        self.base, self.mem, self.yonly, self.evals, self.dev, self.net, self.cost = base, {}, False, 0, base.dev, base.net, None

    def score(self, root, seqs):
        miss = [s for s in seqs if (root.id, json.dumps(s)) not in self.mem]
        if miss:
            for s, c in zip(miss, self.base.score(root, miss)):
                self.mem[(root.id, json.dumps(s))] = c
            self.evals += len(miss)
        out = [self.mem[(root.id, json.dumps(s))] for s in seqs]
        # Y-only: endpoint pY replaces p11 for nonempty sequences; the empty sequence keeps p11 = pY(initial scene) (the production NOOP input)
        return [{**c, "p11": c["py"]} if (self.yonly and s) else c for s, c in zip(seqs, out)]


def setup(arm, dom):
    import benchmark as BM
    RUN = R8._run()
    F = freeze(dom)
    R7 = Path(os.environ["R7_ROOT"])
    files = {}
    if arm == "B0":
        samp, scor0, man = BM.load_bundle(Path(os.environ["K3_BUNDLE"]), dom, "cuda", 0)
        scor = RUN.SafeScorer.__new__(RUN.SafeScorer)
        scor.net, scor.dev, scor.cost, scor.evals = scor0.net, "cuda", None, 0
        files = {"bundle": os.environ["K3_BUNDLE"], "bundle_manifest_sha256": sha(Path(os.environ["K3_BUNDLE"]) / "MANIFEST.json")}
        return {"M": 4, "c1": None, "prop": "cvae"}, samp, scor, man, None, None, files
    samp, _, man = BM.load_bundle(Path(os.environ["FIG3_BUNDLE"]), dom, "cuda", 0)      # plumbing only: rule / proposal seed / sampler object
    files["q2_scalers_sha256"] = scalers(samp, dom)
    cs = F["cvae"]["pick"].rsplit("_s", 1)[1]
    xs = F["x"]["seed"]; rep = F["x"]["rep"]
    xname = F["x"]["name"]
    if arm in ("UNCOUPLED", "ORDINV", "DIRECT"):
        xname = f"{dom}_{rep}1_hi_{arm}_s{xs}"
    elif arm.startswith("REP_"):
        xname = f"{dom}_{arm[4:]}_hi_base_s{xs}"
    elif arm.startswith("FINAL_X"):
        xname = f"{dom}_{rep}1_hi_base_s{arm[7:]}"
    elif arm.startswith("SEED"):
        cs = xs = arm[4:]; xname = f"{dom}_{rep}1_hi_base_s{xs}"
    cpath = R7 / "r7_task" / dom / (f"q2init_all_notask_s{cs}" if arm == "NOTASK" else f"q2init_all_s{cs}") / "model.pt"
    R8.cvae(samp, cpath)
    net, direct, xpath = R8.x_net(dom, xname)
    if xname == F["x"]["name"]:
        assert sha(xpath) == F["x"]["sha256"], "FINAL X checkpoint differs from the freeze"
        if F["calibration"]["adopted"]:
            import xlearn as XLN
            net = XLN.Cal(net, float(F["calibration"]["T"])); files["temperature"] = F["calibration"]["T"]
    if cpath == Path(F["cvae"]["ckpt"]):
        assert sha(cpath) == F["cvae"]["sha256"], "FINAL cVAE differs from the freeze"
    scor = RUN.SafeScorer.__new__(RUN.SafeScorer)
    scor.net, scor.dev, scor.cost, scor.evals = R8.Pred(net, direct), "cuda", None, 0
    sp = {"M": 1 if arm == "M1" else 4, "c1": 0 if arm == "C1" else None, "prop": "uniform4" if arm == "UNIFORM4" else "taskfm" if arm == "TASKFM" else "cvae"}
    fm = cr = None
    if arm == "TASKFM":
        import arms as A
        fp = Path(os.environ["K3"]) / "runs/training/taskfm" / dom / f"taskfm_s{cs}" / "model.pt"
        fm = A.load_taskfm(fp, "cuda"); sp["fm_path"] = str(fp)
    if arm in ("CR", "CRXY", "FC4"):
        sys.path.insert(0, R8.CRDIR)
        import infer as INF
        crr = Path(os.environ["CR_RUNS"]) / "models" / dom
        best = min(crr.glob("r10_s*"), key=lambda d: json.loads((d / "curve.json").read_text())["best_select"])
        cr = INF.load_cr(str(best / "model.pt"), "cuda")[0]; sp["cr_path"] = str(best / "model.pt")
    files.update({"x_name": xname, "x_ckpt": str(xpath), "x_sha256": sha(xpath), "cvae": str(cpath), "cvae_sha256": sha(cpath),
                  **{k: v for k, v in sp.items() if k.endswith("_path")}, **{k + "_sha256": sha(v) for k, v in sp.items() if k.endswith("_path")}})
    return sp, samp, scor, man, fm, cr, files


def fam(dom, samp, scor, man, r):
    """FINAL / FINAL_RANK / YONLY / YONLY_RANK / M1 from one cached scoring pass."""
    import exhaustive as EX
    import search as S
    root = S.Root(r, dom)
    t0 = time.time()
    D = EX.proposals(root, samp, man["config"]["proposal_seed"])
    t_prop = time.time() - t0
    C = Cached(scor)
    out = {}

    def rec_of(Dm, yonly):
        C.yonly = yonly
        t = time.time()
        rec = EX.score_root(root, Dm, C, [RULE], 4, set(), 8192)
        return rec, time.time() - t
    D4 = {int(o): [int(x) for x in v[:4]] for o, v in D.items()}
    D1 = {int(o): [int(x) for x in v[:1]] for o, v in D.items()}
    for arm, Dm, yo in (("FINAL", D4, False), ("YONLY", D4, True), ("M1", D1, False)):
        e0 = C.evals
        rec, dt = rec_of(Dm, yo)
        dd = rec["per_M"]["4"]["decisions"][0]
        kind = "ABSTAIN" if dd is None else "NOOP" if dd["seq"] == [] else "REPAIR"
        top = rec["per_M"]["4"]["top"]
        base = {"root_id": r["root_id"], "domain": dom, "proposals": {str(o): v for o, v in Dm.items()}, "n_scored": rec["per_M"]["4"]["n_scored"],
                "p_noop": rec["p_noop"], "new_evals": C.evals - e0, "wall_s": round(dt + (t_prop if arm == "FINAL" else 0.0), 4)}
        out[arm] = {**base, "arm": arm, "decision": kind, "seq": dd["seq"] if kind == "REPAIR" else [], "score": None if dd is None else dd.get("p11"),
                    "top_score": top[0][0] if top else None}
        if arm in ("FINAL", "YONLY"):
            ts = json.loads(top[0][1]) if top else []
            out[arm + "_RANK"] = {**base, "arm": arm + "_RANK", "decision": "REPAIR" if ts else "ABSTAIN", "seq": ts, "score": top[0][0] if top else None,
                                  "top5": [[t[0], t[1], t[2], t[3]] for t in top[:5]]}
    return out, root


def moves(root, seq):
    return [{"object_id": root.ids[o], "object_index": int(o), "destination_cell": int(c)} for o, c in seq]


def predict(arm, dom, public, out_dir):
    import torch
    torch.set_num_threads(1)
    arms = ["FINAL", "FINAL_RANK", "YONLY", "YONLY_RANK", "M1"] if arm == "FAM" else [arm]
    roster = Path(public).stem.split("_")[1]
    fo = {a: Path(out_dir) / a / f"{roster}_{dom}.jsonl" for a in arms}
    for f in fo.values():
        f.parent.mkdir(parents=True, exist_ok=True)
    done = set.intersection(*[{json.loads(l)["root_id"] for l in open(f)} if f.exists() else set() for f in fo.values()])
    rows = [r for r in map(json.loads, open(public)) if r["domain"] == dom and r["root_id"] not in done]
    sp, samp, scor, man, fm, cr, files = setup("FINAL" if arm == "FAM" else arm, dom)
    for a in arms:
        (fo[a].parent / f"files_{dom}.json").write_text(json.dumps({**files, "torch": torch.__version__, "gpu": torch.cuda.get_device_name(0),
                                                                     "host": os.uname().nodename}, indent=1))
    hs = {a: open(fo[a], "a") for a in arms}
    for r in rows:
        if arm == "FAM":
            res, root = fam(dom, samp, scor, man, r)
            for a in arms:
                d = res[a]
                hs[a].write(json.dumps({**{k: v for k, v in d.items() if k != "seq"}, "moves": moves(root, d["seq"])}, default=float) + "\n"); hs[a].flush()
        else:
            scor.evals = 0
            d = R8.decide(arm if arm not in ("B0",) and not arm.startswith(("REP_", "FINAL_X", "SEED")) else "FINAL", dom, sp, samp, scor, man, fm, cr, r)
            d["arm"] = arm
            hs[arm].write(json.dumps(d, default=float) + "\n"); hs[arm].flush()
    for h in hs.values():
        h.close()
    print(json.dumps({"arm": arm, "dom": dom, "n": {a: sum(1 for _ in open(f)) for a, f in fo.items()}}), flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    {"predict": lambda: predict(*a[1:5])}[a[0]]()
