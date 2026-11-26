#!/usr/bin/env python3
"""R3.2 / R3.3 scaling-checkpoint training (gvlab2 GPU; the production bundle is only READ).

Data
  REPLAY      original v32 TRAIN roots minus DEV-lineage families (xy.root_view: exact X/Y labels, unchanged likelihood)
  LOCAL       one view per (root, start scene = canonical base + prefix): x_seqs = the labelled chunks at that scene (index pairs -> cell xy),
              no Y observed -> exact marginal (Y summed out; permutations of one set share the endpoint Y node).  Conflicting duplicate
              labels of one (scene, chunk) are dropped and counted.
Arms
  F1   XYNet init F0 (bundle scorer_s0); trainable = X-only modules (act, pairo, mix, order_s, xy); everything else frozen (Y bitwise)
  F2   XYNet init F0; all parameters trainable (lr 3e-5)
  G1 / M1  see xrel.py (R3.3 only)
Step = 32 REPLAY roots + 32 LOCAL TRAIN_SCALE views (family-balanced sampling); epoch = ceil(|REPLAY| / 32) steps; AdamW wd 1e-4, clip 10;
early stop (patience 8, <= 40 epochs) on VAL_SCALE family-mean marginal-X NLL.
    python train.py fit DOM ARM SEED      -> O/ckpt/DOM_ARM_sSEED/{model.pt, curve.json}"""
from __future__ import annotations

import collections, copy, json, math, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common3 as K  # noqa: E402
C = K.C
import views as V  # noqa: E402

X_ONLY = ("act", "pairo", "mix", "order_s", "xy")
CFG = {"F1": {"lr": 1e-4, "trainable": X_ONLY}, "F2": {"lr": 3e-5, "trainable": None},
       "G1": {"lr": 1e-4, "trainable": "xrel"}, "M1": {"lr": 1e-4, "trainable": "xrel"},
       # ADDENDUM A1 (R3_PREREG_ADDENDUM_A1.json): randomly initialised X modules with the optimizer that trained F0's X from scratch
       "G1s": {"lr": 1e-3, "trainable": "xrel", "epochs": 60, "patience": 10, "kind": "G1"}, "M1s": {"lr": 1e-3, "trainable": "xrel", "epochs": 60, "patience": 10, "kind": "M1"}}
EPOCHS, PATIENCE, BR, BL = 40, 8, 32, 32


def canon(p):
    return [list(map(int, a)) for a in sorted(tuple(map(int, a)) for a in p)]


def load_labels(dom):
    return [json.loads(l) for l in open(K.O / f"labels_31_{dom}.jsonl")]


def local_views(dom, labs, rows):
    """-> list of {v, lab, fam, rows (label dict per X node)} grouped by start scene; plus conflict count."""
    import xy as XY
    by = collections.defaultdict(list)
    for e in labs:
        if e["label"] in (0, 1):
            by[(e["root_id"], json.dumps(canon(e["base"] + e["prefix"])))].append(e)
    out, conflicts = [], 0
    for (rid, sc), es in sorted(by.items()):
        row = V.rebase(rows[rid], json.loads(sc))
        inp = row["inputs"]; P = lambda c: tuple(inp["cell_xy"][str(int(c))])  # noqa: E731
        uq = {}
        for e in es:
            uq.setdefault(json.dumps(e["chunk"]), []).append(e)
        keep = []
        for k, g in uq.items():
            if len({e["label"] for e in g}) > 1:
                conflicts += 1; continue
            keep.append(g[0])
        if not keep:
            continue
        xs = [[(int(o), P(d)) for o, d in e["chunk"]] for e in keep]
        v, ym, xm = XY.make_view(row["root_id"], inp["xy0"], inp["attrs"], inp["tid"], inp["goal"], inp["base"], inp["ctx"], [], xs, XY._NoGeo)
        lab = XY.labels_for(v, ym, xm, {}, {i: e["label"] for i, e in enumerate(keep)})
        node = [None] * len(v["x_seqs"])
        for i, e in enumerate(keep):
            node[xm[i]] = e
        out.append({"v": v, "lab": lab, "fam": keep[0]["fam"], "rows": node})
    return out, conflicts


def replay(dom):
    import xy as XY
    lin = json.loads((K.O / f"lineage_{dom}.json").read_text())
    dev = set(lin["dev_fams"])
    rows = C.snapshot_rows(dom, splits=("train",), snap=C.SNAP_TRAIN)
    out = []
    for rid, r in sorted(rows.items()):
        if r["parent_family_id"] in dev:
            continue
        v, lab, _ = XY.root_view(r)
        out.append({"v": v, "lab": lab, "fam": r["parent_family_id"]})
    return out


def f0(dom):
    from models import Frozen
    fz = Frozen(dom)
    return fz, copy.deepcopy(fz.net).float()


def make_net(dom, arm, base):
    if arm in ("F1", "F2"):
        net = copy.deepcopy(base)
        tr = CFG[arm]["trainable"]
        for n, p in net.named_parameters():
            p.requires_grad_(tr is None or n.split(".")[0] in tr)
        return net
    import xrel
    return xrel.build(CFG[arm].get("kind", arm), base)


@__import__("torch").no_grad()
def predict(net, items, dev):
    """Per-label marginal px, px1, px0, py, p11 for local views (rows aligned to X nodes)."""
    import torch
    import xy as XY
    out = []
    for i in range(0, len(items), 128):
        ch = items[i:i + 128]
        b, _ = XY.collate([c["v"] for c in ch], device=dev, dtype=torch.float32)
        Cf = net.coeffs(b)
        bb, a, w = Cf["b"].double().cpu(), Cf["a"].double().cpu(), Cf["w"].double().cpu()
        qo = so = 0
        for c in ch:
            for q, e in enumerate(c["rows"]):
                s = so + c["v"]["parent"][q]
                py, p1, p0 = torch.sigmoid(bb[s]).item(), torch.sigmoid(a[qo + q] + w[qo + q]).item(), torch.sigmoid(a[qo + q]).item()
                if e is not None:
                    out.append({**e, "px": py * p1 + (1 - py) * p0, "px1": p1, "px0": p0, "py": py, "p11": py * p1})
            qo += len(c["v"]["x_seqs"]); so += len(c["v"]["y_xy"])
    return out


def fam_nll(P):
    by = collections.defaultdict(list)
    for e in P:
        p = min(max(e["px"], 1e-6), 1 - 1e-6)
        by[e["fam"]].append(-(e["label"] * math.log(p) + (1 - e["label"]) * math.log(1 - p)))
    return sum(sum(v) / len(v) for v in by.values()) / max(1, len(by))


def fit(dom, arm, seed):
    import numpy as np
    import torch
    import xy as XY
    dev = "cuda"
    torch.manual_seed(int(seed)); rng = np.random.default_rng(int(seed))
    rows = C.snapshot_rows(dom, snap=C.SNAP_TRAIN)
    L = load_labels(dom)
    tr, c1 = local_views(dom, [e for e in L if e["split"] == "TRAIN_SCALE"], rows)
    va, c2 = local_views(dom, [e for e in L if e["split"] == "VAL_SCALE"], rows)
    rp = replay(dom)
    fz, base = f0(dom)
    net = make_net(dom, arm, base).to(dev)
    params = [p for p in net.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=CFG[arm]["lr"], weight_decay=1e-4)
    fam_n = collections.Counter(x["fam"] for x in tr)
    wts = np.array([1.0 / fam_n[x["fam"]] for x in tr]); wts /= wts.sum()
    rb = [list(range(i, min(i + BR, len(rp)))) for i in range(0, len(rp), BR)]
    rcol = [XY.collate([rp[j]["v"] for j in idx], [rp[j]["lab"] for j in idx], device=dev, dtype=torch.float32) for idx in rb]
    out = K.O / "ckpt" / f"{dom}_{arm}_s{seed}"; out.mkdir(parents=True, exist_ok=True)
    net.eval()
    v0 = fam_nll(predict(net, va, dev))
    curve, best, bad, t0 = [{"epoch": -1, "val_fam_nll": v0}], (v0, -1), 0, time.time()
    torch.save({"state": net.state_dict(), "arm": arm, "dom": dom, "seed": int(seed), "epoch": -1}, out / "model.pt")
    for ep in range(CFG[arm].get("epochs", EPOCHS)):
        net.train(); tl = []
        for k in rng.permutation(len(rb)):
            li = rng.choice(len(tr), size=BL, replace=True, p=wts)
            items = [rp[j] for j in rb[k]] + [tr[j] for j in li]
            b, lab = XY.collate([x["v"] for x in items], [x["lab"] for x in items], device=dev, dtype=torch.float32)
            nll = -XY.batched_log_evidence(*(lambda Cf: (Cf["b"], Cf["a"], Cf["w"]))(net.coeffs(b)), b["parent"], lab["y_obs"], lab["x_obs"], b["s_root"], b["n_roots"]).mean()
            opt.zero_grad(); nll.backward(); torch.nn.utils.clip_grad_norm_(params, 10.0); opt.step()
            tl.append(float(nll.detach()))
        net.eval()
        vl = fam_nll(predict(net, va, dev))
        curve.append({"epoch": ep, "train_nll": float(np.mean(tl)), "val_fam_nll": vl, "s": round(time.time() - t0, 1)})
        print(json.dumps(curve[-1]), flush=True)
        if vl < best[0] - 1e-5:
            best, bad = (vl, ep), 0
            torch.save({"state": net.state_dict(), "arm": arm, "dom": dom, "seed": int(seed), "epoch": ep}, out / "model.pt")
        else:
            bad += 1
            if bad >= CFG[arm].get("patience", PATIENCE):
                break
    info = {"dom": dom, "arm": arm, "seed": int(seed), "curve": curve, "best_val_fam_nll": best[0], "best_epoch": best[1], "wall_s": round(time.time() - t0, 1),
            "gpu_peak_mib": round(torch.cuda.max_memory_allocated() / 2 ** 20, 1), "n_replay": len(rp), "n_local_train_views": len(tr),
            "n_local_val_views": len(va), "conflicts_dropped": [c1, c2], "trainable_params": sum(p.numel() for p in params),
            "total_params": sum(p.numel() for p in net.parameters()), "model_sha256": K.sha(out / "model.pt")}
    (out / "curve.json").write_text(json.dumps(info, indent=1))
    print(json.dumps({k: v for k, v in info.items() if k != "curve"}))


def load(dom, arm, seed, dev="cuda"):
    import torch
    fz, base = f0(dom)
    net = make_net(dom, arm, base).to(dev)
    ck = torch.load(K.O / "ckpt" / f"{dom}_{arm}_s{seed}" / "model.pt", map_location=dev, weights_only=False)
    net.load_state_dict(ck["state"])
    return fz, net.eval()


if __name__ == "__main__":
    if sys.argv[1] == "fit":
        fit(*sys.argv[2:5])
