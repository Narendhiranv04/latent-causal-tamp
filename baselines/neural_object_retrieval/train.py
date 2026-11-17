#!/usr/bin/env python3
"""NOR-Grid training (laptop GPU, one process).  OSNet: MSE between masked-softmax p_hat and the homotopy blocking distribution (eligible
objects only); RPNet: MSE between predicted and label region costs (all cells); STOP adapter: BCE on decided endpoint Y.  AdamW 3e-4,
wd 1e-4, grad clip 1, early stop on the TRAIN group holdout (patience 8, max 50 epochs).  Random init; nothing from Approach B.

    train.py DOM TENSORS.npz OUTDIR SEED [MODELS=os,rp,st] [MAX_TRAIN_SAMPLES]"""
import hashlib, json, sys, time
from pathlib import Path

import numpy as np
import torch

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import networks as NW  # noqa: E402

CFG = {"d": 128, "os_layers": 3, "rp_layers": 2, "st_layers": 2, "lr": 3e-4, "wd": 1e-4, "batch": 64, "epochs": 50, "patience": 8, "clip": 1.0}


def sha_state(m):
    h = hashlib.sha256()
    for k, v in sorted(m.state_dict().items()):
        h.update(k.encode()); h.update(v.detach().cpu().numpy().tobytes())
    return h.hexdigest()


def batches(idx, bs, rng):
    idx = idx.copy()
    rng.shuffle(idx)
    return [idx[i:i + bs] for i in range(0, len(idx), bs)]


def run(dom, npz, outdir, seed, models=("os", "rp", "st"), max_n=None, cfg=CFG, dev=None):
    dev = dev or ("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(seed)
    D = np.load(npz)
    T = lambda a, dt=torch.float32: torch.as_tensor(np.asarray(a), dtype=dt, device=dev)  # noqa: E731
    X, M, C, E, TM = T(D["X"]), T(D["M"], torch.bool), T(D["C"]), T(D["E"], torch.bool), T(D["T"], torch.bool)
    hold = D["hold"]
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    rep = {"dom": dom, "seed": seed, "cfg": cfg, "device": dev, "tensors_sha256": hashlib.sha256(Path(npz).read_bytes()).hexdigest(), "models": {}}
    specs = {"os": ("os_i", NW.OSNet(cfg["d"], cfg["os_layers"])), "rp": ("rp_i", NW.RPNet(cfg["d"], cfg["rp_layers"])),
             "st": ("st_i", NW.StopAdapter(cfg["d"], cfg["st_layers"]))}
    for name in models:
        key, net = specs[name]
        torch.manual_seed(seed)
        net = type(net)(cfg["d"], cfg[f"{name}_layers"]).to(dev)
        si = D[key]
        tr = np.flatnonzero(~hold[si])
        va = np.flatnonzero(hold[si])
        if max_n:
            tr = tr[:max_n]
        opt = torch.optim.AdamW(net.parameters(), lr=cfg["lr"], weight_decay=cfg["wd"])
        rng = np.random.default_rng(seed)

        def loss_of(j):
            s = T(si[j], torch.long)
            if name == "os":
                p, _ = net(X[s], M[s], E[s], TM[s])
                tgt = T(D["os_p"][j])
                msk = E[s].float()
                return (((p - tgt) ** 2) * msk).sum() / msk.sum()
            if name == "rp":
                c = net(X[s], M[s], C[s], T(D["rp_o"][j], torch.long), TM[s])
                return ((c - T(D["rp_c"][j])) ** 2).mean()
            lg = net(X[s], M[s], TM[s])
            return torch.nn.functional.binary_cross_entropy_with_logits(lg, T(D["st_y"][j]))

        best, bad, curve, t0 = (float("inf"), -1), 0, [], time.time()
        if dev == "cuda":
            torch.cuda.reset_peak_memory_stats()
        for ep in range(cfg["epochs"]):
            net.train()
            tl = []
            for b in batches(tr, cfg["batch"], rng):
                l = loss_of(b)
                opt.zero_grad(); l.backward()
                torch.nn.utils.clip_grad_norm_(net.parameters(), cfg["clip"]); opt.step()
                tl.append(float(l))
            net.eval()
            with torch.no_grad():
                vl = float(np.mean([float(loss_of(b)) for b in batches(va, 256, np.random.default_rng(0))])) if len(va) else float(np.mean(tl))
            curve.append({"epoch": ep, "train": float(np.mean(tl)), "holdout": vl})
            if vl < best[0] - 1e-6:
                best, bad = (vl, ep), 0
                torch.save({"state": net.state_dict(), "cfg": cfg, "kind": name, "dom": dom, "seed": seed, "epoch": ep}, out / f"{name}.pt")
            else:
                bad += 1
                if bad >= cfg["patience"]:
                    break
        net.load_state_dict(torch.load(out / f"{name}.pt", map_location=dev)["state"])
        rep["models"][name] = {"n_train": int(len(tr)), "n_holdout": int(len(va)), "best_holdout": best[0], "best_epoch": best[1],
                               "epochs_run": len(curve), "wall_s": round(time.time() - t0, 1), "state_sha256": sha_state(net),
                               "file_sha256": hashlib.sha256((out / f"{name}.pt").read_bytes()).hexdigest(),
                               "params": sum(p.numel() for p in net.parameters()),
                               "gpu_peak_mib": round(torch.cuda.max_memory_allocated() / 2 ** 20, 1) if dev == "cuda" else None, "curve": curve}
        print(json.dumps({k: v for k, v in rep["models"][name].items() if k != "curve"} | {"model": name}), flush=True)
    (out / "train_report.json").write_text(json.dumps(rep, indent=1))
    return rep


if __name__ == "__main__":
    a = sys.argv
    run(a[1], a[2], a[3], int(a[4]), tuple(a[5].split(",")) if len(a) > 5 else ("os", "rp", "st"), int(a[6]) if len(a) > 6 else None)
