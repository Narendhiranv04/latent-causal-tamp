#!/usr/bin/env python3
"""Train the complete-repair cVAE (plan.md 4.4-4.5): one model per domain, seeds {0, 1, 2}, TRAIN only, fixed VAL selection.

    python train.py fit DOM SEED [--tag T]       -> $CR_RUNS/models/<dom>/<tag>_s<seed>/{model.pt, curve.json}
    python train.py overfit DOM [N_ROOTS]        tiny sanity fit on the first N TRAIN roots with a repair (reconstruction, masks, no NaN)

Budget = the released per-object sampler's fixed optimizer-step budget and evaluation cadence, read from the bundle checkpoint cfg
(2D 2,400 steps / eval every 30; 3D 1,520 / 19), batch 256 ordered repairs, AdamW lr 1e-3 wd 1e-4, grad-norm clip 10, beta ramp 0 -> 1 over
the first 10 evaluations, best weighted VAL (-ELBO at beta = 1, fixed latent noise) + VAL decision CE, earliest tie, no early stopping.
Decision loss: a separate root-uniform minibatch of 256 labelled TRAIN roots per step (never multiplied by the number of orders)."""
from __future__ import annotations

import argparse, hashlib, json, math, os, time
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as Fn

import data as D
from model import CRCVAE, param_counts

KEYS = ("tok", "tmask", "movable", "cell", "legal0", "glob")


def to_t(arr, dev):
    return {k: torch.as_tensor(v, device=dev) for k, v in arr.items()}


def load_split(dom, snap, split, dev, limit=None):
    rr, triples, labels = D.supervision(dom, snap, split)
    if limit:                                                    # overfit fixture: the first `limit` roots that carry a verified repair
        keep = sorted({i for i, _, _ in triples})[:limit]
        rr2 = [rr[i] for i in keep]
        remap = {i: j for j, i in enumerate(keep)}
        triples = [(remap[i], s, w) for i, s, w in triples if i in remap]
        labels, rr = [labels[i] for i in keep], rr2
    musd = D.scalers(dom)
    R = to_t(D.stack([D.encode(dom, r, musd) for r in rr]), dev)
    o, d, n = D.seq_arrays([s for _, s, _ in triples])
    w = np.array([x for _, _, x in triples], np.float32)
    return {"roots": R, "root_ids": [r["root_id"] for r in rr], "ridx": torch.as_tensor([i for i, _, _ in triples], device=dev),
            "obj": torch.as_tensor(o, device=dev), "dst": torch.as_tensor(d, device=dev), "n": torch.as_tensor(n, device=dev),
            "w": torch.as_tensor(w, device=dev), "label": torch.as_tensor(labels, device=dev), "n_roots": len(rr)}


def gather(S, idx):
    return {k: S["roots"][k][idx] for k in KEYS}


def evaluate(m, V, seed=12345, chunk=4096):
    """Weighted VAL -ELBO (beta = 1, fixed posterior noise) + parts + decision CE / accuracy over labelled VAL roots."""
    m.eval()
    g = torch.Generator(device=V["n"].device).manual_seed(seed)
    tot = {"nll": 0.0, "kl": 0.0, "obj": 0.0, "cell": 0.0, "stop": 0.0}
    W = float(V["w"].sum())
    mus = []
    with torch.no_grad():
        for s in range(0, len(V["n"]), chunk):
            ix = torch.arange(s, min(s + chunk, len(V["n"])), device=V["n"].device)
            nll, parts, kl, (mu, _) = m.elbo_terms(gather(V, V["ridx"][ix]), V["obj"][ix], V["dst"][ix], V["n"][ix], g)
            w = V["w"][ix]
            tot["nll"] += float((nll * w).sum()); tot["kl"] += float((kl * w).sum())
            for k in ("obj", "cell", "stop"):
                tot[k] += float((-parts[k] * w).sum())
            mus.append(mu)
        lab = V["label"]
        ok = lab >= 0
        c, _, _ = m.encode({k: V["roots"][k][ok] for k in KEYS})
        lg = m.decision_logits(c)
        ce = float(Fn.cross_entropy(lg, lab[ok]))
        acc = float((lg.argmax(-1) == lab[ok]).float().mean())
    mu = torch.cat(mus)
    out = {k: v / W for k, v in tot.items()}
    toks = 2 * V["n"].float() + (V["n"] < 3).float()                 # object + cell per action, + STOP unless forced at k = 3
    out.update({"neg_elbo": out["nll"] + out["kl"], "dec_ce": ce, "dec_acc": acc, "active_dims": int((mu.var(0) > 0.01).sum()),
                "per_token_nll": out["nll"] * W / float((V["w"] * toks).sum())})
    out["select"] = out["neg_elbo"] + out["dec_ce"]
    return out


def production_cfg(dom):
    ck = torch.load(D.BUNDLE / dom / "sampler.pt", map_location="cpu", weights_only=False)
    return {k: ck["cfg"][k] for k in ("steps", "eval_every", "batch", "lr", "warm", "hidden", "zdim")}


def fit(dom, seed, tag="cr", cfg=None, train=None, val=None, out=None, dev=None):
    dev = dev or os.environ.get("CR_DEVICE", "cuda")
    cfg = {**production_cfg(dom), "wd": 1e-4, "clip": 10.0, "lambda_gate": 1.0, "gate_batch": 256, "beta_max": 1.0, **(cfg or {})}
    torch.manual_seed(seed)
    t_load = time.time()
    Tr = train or load_split(dom, D.TRAIN_SNAP, "train", dev)
    Va = val or load_split(dom, D.VAL_SNAP, "val", dev)
    t_load = time.time() - t_load
    m = CRCVAE(dom, cfg["hidden"], cfg["zdim"]).to(dev)
    opt = torch.optim.AdamW(m.parameters(), lr=cfg["lr"], weight_decay=cfg["wd"])
    out = Path(out or D.RUNS / "models" / dom / f"{tag}_s{seed}")
    out.mkdir(parents=True, exist_ok=True)
    g = torch.Generator(device=dev).manual_seed(seed)
    n, S_, E, B = len(Tr["n"]), int(cfg["steps"]), int(cfg["eval_every"]), int(cfg["batch"])
    lab_idx = torch.nonzero(Tr["label"] >= 0).squeeze(1)
    if dev.startswith("cuda"):
        torch.cuda.reset_peak_memory_stats()
    curve, best, t0, step, ev, perm, pi, acc = [], (math.inf, None), time.time(), 0, 0, None, n, []
    while step < S_:
        if pi >= n:
            perm, pi = torch.randperm(n, device=dev, generator=g), 0
        ix = perm[pi:pi + B]
        pi += B
        m.train()
        beta = cfg["beta_max"] * min(1.0, ev / cfg["warm"])          # linear 0 -> 1 over the first `warm` evaluations
        nll, parts, kl, _ = m.elbo_terms(gather(Tr, Tr["ridx"][ix]), Tr["obj"][ix], Tr["dst"][ix], Tr["n"][ix], g)
        w = Tr["w"][ix]
        rec = ((nll + beta * kl) * w).sum() / w.sum()
        jx = lab_idx[torch.randint(len(lab_idx), (cfg["gate_batch"],), device=dev, generator=g)]
        c, _, _ = m.encode(gather(Tr, jx))
        ce = Fn.cross_entropy(m.decision_logits(c), Tr["label"][jx])
        loss = rec + cfg["lambda_gate"] * ce
        assert torch.isfinite(loss), ("non-finite loss", step)
        opt.zero_grad(); loss.backward()
        gn = torch.nn.utils.clip_grad_norm_(m.parameters(), cfg["clip"])
        opt.step()
        step += 1
        acc.append([float(rec), float((nll * w).sum() / w.sum()), float((kl * w).sum() / w.sum()), float(ce), float(gn)])
        if step % E == 0 or step == S_:
            v = evaluate(m, Va)
            a = np.mean(acc, 0)
            curve.append({"eval": ev, "step": step, "epochs": round(step * B / n, 3), "beta": beta, "train_loss": a[0], "train_nll": a[1],
                          "train_kl": a[2], "train_dec_ce": a[3], "grad_norm": a[4], **{f"val_{k}": x for k, x in v.items()}})
            acc = []
            if v["select"] < best[0]:
                best = (v["select"], step)
                torch.save({"state": m.state_dict(), "cfg": cfg, "dom": dom, "seed": seed, "step": step, "eval": ev, "val": v}, out / "model.pt.tmp")
                os.replace(out / "model.pt.tmp", out / "model.pt")
            ev += 1
    peak = round(torch.cuda.max_memory_allocated() / 2 ** 20, 1) if dev.startswith("cuda") else None
    wall = time.time() - t0
    res = {"dom": dom, "seed": seed, "tag": tag, "cfg": cfg, "best_select": best[0], "best_step": best[1], "curve": curve, "params": param_counts(m),
           "train_triples": n, "train_roots": int(Tr["ridx"].unique().numel()), "train_label_roots": int(len(lab_idx)),
           "train_label_counts": {D.CLASSES[k]: int((Tr["label"] == k).sum()) for k in range(3)}, "train_masked_roots": int((Tr["label"] < 0).sum()),
           "val_triples": len(Va["n"]), "val_roots": int(Va["ridx"].unique().numel()), "load_s": round(t_load, 1), "wall_s": round(wall, 1),
           "gpu_peak_mib": peak, "gpu_hours": round(wall / 3600, 5) if dev.startswith("cuda") else 0.0, "device": dev,
           "device_name": torch.cuda.get_device_name(0) if dev.startswith("cuda") else "cpu", "torch": torch.__version__,
           "model_sha256": hashlib.sha256((out / "model.pt").read_bytes()).hexdigest(),
           "train_snapshot": str(D.TRAIN_SNAP), "train_data_sha256": D.sha(D.TRAIN_SNAP / f"data{dom}.jsonl"),
           "val_snapshot": str(D.VAL_SNAP), "val_data_sha256": D.sha(D.VAL_SNAP / f"data{dom}.jsonl")}
    (out / "curve.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ("dom", "seed", "tag", "best_select", "best_step", "wall_s", "gpu_peak_mib")}), flush=True)
    return res


def load(path, dev=None):
    dev = dev or os.environ.get("CR_DEVICE", "cuda")
    ck = torch.load(path, map_location=dev, weights_only=False)
    m = CRCVAE(ck["dom"], ck["cfg"]["hidden"], ck["cfg"]["zdim"]).to(dev)
    m.load_state_dict(ck["state"])
    return m.eval(), ck


def overfit(dom, n_roots=16, steps=600, dev=None):
    """Sanity: fit the verified orders of a few TRAIN roots; report teacher-forced NLL, greedy-free posterior reconstruction and STOP lengths."""
    dev = dev or os.environ.get("CR_DEVICE", "cuda")
    Tr = load_split(dom, D.TRAIN_SNAP, "train", dev, limit=n_roots)
    out = D.RUNS / "overfit" / dom
    res = fit(dom, 0, "overfit", {"steps": steps, "eval_every": 50, "warm": 2, "batch": 64, "gate_batch": 16}, train=Tr, val=Tr, out=out, dev=dev)
    m, _ = load(out / "model.pt", dev)
    with torch.no_grad():
        c, T, Ce = m.encode(gather(Tr, Tr["ridx"]))
        mu, _ = m.posterior(c, T, Ce, Tr["obj"], Tr["dst"], Tr["n"])
        lp, _ = m.logp(c, T, Ce, Tr["roots"]["movable"][Tr["ridx"]], Tr["roots"]["legal0"][Tr["ridx"]], mu, Tr["obj"], Tr["dst"], Tr["n"])
    rep = {"roots": Tr["n_roots"], "triples": len(Tr["n"]), "final_val": res["curve"][-1], "posterior_mean_logp_mean": float(lp.mean()),
           "posterior_mean_prob_mean": float(lp.exp().mean()), "lengths": {int(k): int(v) for k, v in zip(*np.unique(Tr["n"].cpu().numpy(), return_counts=True))}}
    (out / "overfit_report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep), flush=True)
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["fit", "overfit"]); ap.add_argument("dom", choices=["2d", "3d"]); ap.add_argument("arg", nargs="?", type=int)
    ap.add_argument("--tag", default="cr")
    A = ap.parse_args()
    if A.cmd == "fit":
        fit(A.dom, A.arg or 0, A.tag)
    else:
        overfit(A.dom, A.arg or 16)
