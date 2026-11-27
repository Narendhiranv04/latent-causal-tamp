#!/usr/bin/env python3
"""R7 clean training (LEGOLAS final).  No development checkpoint is inherited: every stage starts from fresh initialisation.
  Stage A  placement.fit(DOM, q2_DOM, 'cvae', s)  ->  placement.fit_task(DOM, 'q2init_all', s) on the expanded TRAIN snapshot, VAL = base
           snapshot VAL ELBO, fixed-step budget of the frozen production sampler (arms.STEPS)          (isolated ABF_ROOT / V3OUT)
  Stage B  xy.fit(EXP, DOM, 'D', s)  (original observed-data likelihood, original data, frozen D defaults)
  Stage C  frozen fresh Y (stage B, same seed) + fresh X head (A ordered / M MLP / G GNN) x data (0 original replay / 1 + strict local)
           via xlearn.fit (recipe 'hi' = lr 1e-3, <= 60 epochs, patience 10; family-balanced local + replay; no O2 loss); Y sha asserted
    $PYG r7.py dump DOM OUT.pt                         (gvlab2: physical records live there) local views + replay + K<=3 VAL roots
    $PY  r7.py stageA DOM SEED | stageB DOM SEED       (ABF_ROOT, V3OUT, XY_RUNS set by the caller)
    $PY  r7.py xfit DOM REP DAT SEED [CTRL]            (R7_PACK_DIR, R7_OUT, XY_RUNS)"""
from __future__ import annotations

import hashlib, json, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "r3"), str(HERE.parent / "r24"), str(HERE.parent.parent)]
STEPS = {"2d": (2400, 30), "3d": (1520, 19)}            # frozen scratch_all fixed-step budget (ablations_k3/arms.py)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def dump(dom, out):
    import torch
    import xlearn as XLN
    import train as TR
    import xy as XY
    import common3 as K
    E, rows, info = XLN.data(dom)
    tr, c1 = TR.local_views(dom, [e for e in E if e["split"] == "TRAIN"], rows)
    va, c2 = TR.local_views(dom, [e for e in E if e["split"] == "VAL"], rows)
    rp = TR.replay(dom)
    k3val = [{"v": v, "lab": lab, "fam": r["parent_family_id"]} for rid, r in sorted(K.C.snapshot_rows(dom, splits=("val",), snap=K.C.SNAP_TRAIN).items())
             for v, lab, _ in [XY.root_view(r)]]
    info = {**info, "conflicts_dropped": [c1, c2], "n_train_views": len(tr), "n_val_views": len(va), "n_replay": len(rp), "n_k3val_roots": len(k3val),
            "train_fams": sorted({e["fam"] for e in E if e["split"] == "TRAIN"}), "val_fams": sorted({e["fam"] for e in E if e["split"] == "VAL"})}
    assert not set(info["train_fams"]) & set(info["val_fams"])
    torch.save({"tr": tr, "va": va, "rp": rp, "k3val": k3val, "info": info}, out + ".tmp"); os.replace(out + ".tmp", out)
    print(json.dumps({k: info[k] for k in ("n", "n_train_views", "n_val_views", "n_replay", "n_k3val_roots")}), sha(out))


def stage_a(dom, seed):
    import placement as PL
    seed = int(seed)
    PL.fit(dom, PL.ROOT / "data" / f"q2_{dom}", "cvae", seed)
    s, e = STEPS[dom]
    os.environ["V3_TASK_STAGE"] = "r7_task"
    PL.fit_task(dom, "q2init_all", seed, {"steps": s, "eval_every": e}, PL.ROOT / "snapshot/abf_v32_fb0eef4f5ff433ee", PL.ROOT / "snapshot/abf_9de85710c2a7103f", "cuda")


def abl_a(dom, seed, variant):
    """Placement ablation matched to stage A: same Q2 initialisation (stage-A p1 checkpoint of this seed), data, steps; only `variant` differs."""
    import placement as PL
    s, e = STEPS[dom]
    os.environ["V3_TASK_STAGE"] = "r7_task"
    PL.fit_task(dom, variant, int(seed), {"steps": s, "eval_every": e}, PL.ROOT / "snapshot/abf_v32_fb0eef4f5ff433ee", PL.ROOT / "snapshot/abf_9de85710c2a7103f", "cuda")


def stage_b(dom, seed):
    import placement as PL
    import xy as XY
    XY.fit(PL.ROOT / "snapshot/abf_v32_fb0eef4f5ff433ee", dom.upper(), "D", int(seed))


def base_path(dom, seed):
    return Path(os.environ["XY_RUNS"]) / f"p2_{dom}" / f"D_s{seed}" / "model.pt"


def xfit(dom, rep, dat, seed, ctrl=None):
    import torch
    import xlearn as XLN
    import xy as XY
    XLN.XL = Path(os.environ["R7_OUT"]) / "xl"
    ctrl = None if ctrl in (None, "", "base") else ctrl
    name = f"{dom}_{rep}{dat}_hi_{ctrl or 'base'}_s{seed}"
    res_p = XLN.XL / f"results_{dom}.jsonl"
    if res_p.exists() and any(json.loads(l)["name"] == name for l in open(res_p)):
        print("SKIP", name); return
    P = torch.load(Path(os.environ["R7_PACK_DIR"]) / f"pack_{dom}.pt", weights_only=False)
    bp = base_path(dom, seed)
    base = XY.load_model(bp, "cuda").float().eval()
    yb = XLN.ysha(base)
    r = XLN.fit(dom, rep, int(dat), "hi", int(seed), ctrl, P["tr"], P["va"], P["rp"], P["k3val"], base)
    assert r["y_sha"] == yb, "Y of the X model differs from the fresh stage-B Y"
    r.update(base_ckpt=str(bp), base_sha256=sha(bp), base_y_sha=yb, pack_sha256=sha(Path(os.environ["R7_PACK_DIR"]) / f"pack_{dom}.pt"))
    XLN.XL.mkdir(parents=True, exist_ok=True)
    with open(res_p, "a") as f:
        f.write(json.dumps({k: v for k, v in r.items() if k != "curve"}, default=str) + "\n")
    print(name, round(r["best_val"], 4), r["best_epoch"], r["wall_s"], flush=True)


def select(dom):
    """Stage D (predefined, VAL only): representation = R5.2 rule (simplest A < M < G within max(seed spread of the best, 0.005) of the best
    seed-mean local-family VAL NLL; data 1, recipe hi); seed = lowest VAL NLL of that representation; calibration = R5.3 rule (temperature on
    VAL family NLL, adopted iff it improves by >= 0.005); cVAE seed = lowest base-snapshot VAL ELBO (q2init_all).  -> R7_OUT/freeze_DOM.json"""
    import numpy as np
    import torch
    import xlearn as XLN
    import xrel
    import xy as XY
    R = [json.loads(l) for l in open(Path(os.environ["R7_OUT"]) / "xl" / f"results_{dom}.jsonl")]
    base = [r for r in R if not r["ctrl"] and r["data"] == 1]
    m = {rep: [r["best_val"] for r in base if r["rep"] == rep] for rep in XLN.REPS}
    mean = {k: float(np.mean(v)) for k, v in m.items() if v}
    best = min(mean, key=mean.get)
    tol = max(float(np.ptp(m[best])) if len(m[best]) > 1 else 0.0, 0.005)
    rep = next(k for k in XLN.REPS if k in mean and mean[k] <= mean[best] + tol)
    pick = min((r for r in base if r["rep"] == rep), key=lambda r: r["best_val"])
    s = pick["seed"]
    P = torch.load(Path(os.environ["R7_PACK_DIR"]) / f"pack_{dom}.pt", weights_only=False)
    b = XY.load_model(base_path(dom, s), "cuda").float().eval()
    net = XLN.make(rep, b).to("cuda")
    ck = Path(os.environ["R7_OUT"]) / "xl" / "ckpt" / pick["name"] / "model.pt"
    net.load_state_dict(torch.load(ck, map_location="cuda", weights_only=False)["state"]); net.eval()
    cal = XLN.fit_temperature(net, P["va"], "cuda")
    use_T = cal["val_nll_raw"] - cal["val_nll_cal"] >= 0.005
    V3 = Path(os.environ["V3OUT"]) / "r7_task" / dom
    cv = {}
    for d in sorted(V3.glob("q2init_all_s*")):
        c = json.loads((d / "curve.json").read_text())
        cv[d.name] = {"best_val": c.get("best_val"), "sha256": sha(d / "model.pt")}
    cpick = min(cv, key=lambda k: cv[k]["best_val"])
    out = {"dom": dom, "x": {"rep": rep, "seed_mean_val": mean, "seeds": m, "tolerance": tol, "best": best, "name": pick["name"], "seed": s,
                             "val_fam_nll": pick["best_val"], "ckpt": str(ck), "sha256": sha(ck), "rule": "R5.2 simplest-within-tolerance; lowest-VAL seed"},
           "calibration": {"T": cal["T"], "val_nll_raw": cal["val_nll_raw"], "val_nll_cal": cal["val_nll_cal"], "adopted": bool(use_T),
                           "rule": "R5.3 adopt iff VAL NLL improves >= 0.005"},
           "y_base": {"ckpt": str(base_path(dom, s)), "sha256": sha(base_path(dom, s)), "y_sha": pick["y_sha"]},
           "cvae": {"pick": cpick, "ckpt": str(V3 / cpick / "model.pt"), "sha256": cv[cpick]["sha256"], "all": cv, "rule": "lowest base-snapshot VAL ELBO"},
           "spec": f"R7:{pick['name']}" + (f"@T={cal['T']}" if use_T else "")}
    (Path(os.environ["R7_OUT"]) / f"freeze_{dom}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("x", "calibration", "spec")}, default=str)[:900])


if __name__ == "__main__":
    a = sys.argv[1:]
    {"dump": lambda: dump(*a[1:3]), "stageA": lambda: stage_a(*a[1:3]), "stageB": lambda: stage_b(*a[1:3]), "xfit": lambda: xfit(*a[1:6]),
     "select": lambda: select(a[1]), "ablA": lambda: abl_a(*a[1:4])}[a[0]]()
