#!/usr/bin/env python3
"""P4: controlled warm-start training of the frozen coupled X/Y arm D (P4_TRAIN_PREREG.md).
  A1 original TRAIN, NLL      A2 augmented TRAIN, NLL      A3 original TRAIN, NLL + rank      A4 augmented TRAIN, NLL + rank
Loss per root = exact observed-data NLL (xy.batched_log_evidence, root SUM, unchanged) + lambda * C * mean hinge(m - s(z+) + s(z-)) over
same-root verified pairs, s = logsigmoid(b[parent]) + logsigmoid(a + w) from the logits (never predict()).  Mean over roots.
Checkpoint per epoch; selection on DEV_CAL (known-candidate top-1, tie NLL, then earlier epoch) among eligible epochs.
    python train_rank.py ARM SEED          # -> ~/xyrr_runs/p4/ARM_sSEED/{epNN.pt, curve.json}
    python train_rank.py select            # -> reports/P4_ABLATION.json"""
from __future__ import annotations

import collections, json, math, os, pickle, sys, time

import numpy as np
import torch
import torch.nn.functional as F

import rr

ARMS = {"A1": ("orig", 0.0), "A2": ("aug", 0.0), "A3": ("orig", 0.1), "A4": ("aug", 0.1)}
CFG = {"lr": 1e-4, "wd": 1e-4, "clip": 10.0, "batch": 64, "epochs": 15, "patience": 4, "margin": 0.2, "C": 6, "pairs_per_root": 16}
P4 = rr.OUT / "p4"


# ------------------------------------------------------------------------------------------------------------- data
def train_items(which):
    import xy as XY
    snap = rr.SNAP if which == "orig" else rr.PRIV / "snap_aug"
    out = []
    for l in open(Path(snap) / "data2d.jsonl"):
        r = json.loads(l)
        if r["split"] != "train":
            continue
        v, lab, qm = XY.root_view(r)
        out.append({"v": v, "lab": lab, "root_id": r["root_id"]})
    return out


from pathlib import Path  # noqa: E402


def zq(v, lab):
    """Per X node logical Z from its own X label and its endpoint's Y label (missing stays missing)."""
    return [rr.z_logic(lab["obs_x"].get(q), lab["obs_y"].get(v["parent"][q])) for q in range(len(v["x_seqs"]))]


def rank_loss(C, b, chunk, rng, cfg, gen_hard=True):
    """Mean over roots (in the chunk) of the per-root mean hinge over <= pairs_per_root same-root (z+, z-) pairs; roots without pairs give 0."""
    s = F.logsigmoid(C["b"][b["parent"]]) + F.logsigmoid(C["a"] + C["w"])
    per, qo = [], 0
    sd = s.detach()
    for c in chunk:
        nq = len(c["v"]["x_seqs"]); z = c["z"]
        P = [qo + q for q in range(nq) if z[q] == 1]; N = [qo + q for q in range(nq) if z[q] == 0]
        qo += nq
        if not P or not N:
            per.append(s.new_zeros(())); continue
        allp = [(p, n) for p in P for n in N]
        if len(allp) > cfg["pairs_per_root"]:
            k = cfg["pairs_per_root"] // 2
            uni = [allp[i] for i in rng.choice(len(allp), k, replace=False)]
            viol = sorted(allp, key=lambda pn: -(float(sd[pn[1]]) - float(sd[pn[0]])))[:k]          # hardest by current scores (detached)
            allp = list({pn: None for pn in uni + viol})
        pi = torch.tensor([p for p, _ in allp], device=s.device); ni = torch.tensor([n for _, n in allp], device=s.device)
        per.append(F.relu(cfg["margin"] - s[pi] + s[ni]).mean())
    return torch.stack(per)


# ------------------------------------------------------------------------------------------------------------- DEV evaluation (light tables)
def dev_light(part):
    """DEV root table restricted to [no-op] + known labelled candidates (+ the D4 pool for K0 / NONE roots, safeguard decisions)."""
    f = rr.PRIV / f"p4_dev_{part}.pkl"
    if f.exists():
        return pickle.loads(f.read_bytes())
    import diagnostics as D
    import search as S
    full = D.load()
    lab = rr.strict_labels(); pubm = {r["root_id"]: r for r in rr.public_val()}
    k3 = collections.defaultdict(dict)
    for (rid, sq), e in lab.items():
        if len(json.loads(sq)) == 3:
            k3[rid][sq] = e
    out = []
    for r in full:
        if r["part"] != part:
            continue
        keep = [0] + sorted(r["known"]) + (r["d4"] if r["K"] in ("0", "NONE") else [])
        keep = list(dict.fromkeys(keep))
        m = {i: j for j, i in enumerate(keep)}
        out.append({"root_id": r["root_id"], "K": r["K"], "family": r["family"], "part": part, "seqs": [r["seqs"][i] for i in keep],
                    "known": {m[i]: v for i, v in r["known"].items()}, "d4": [m[i] for i in r["d4"] if i in m],
                    "in_d4": {m[i] for i in r["d4"] if i in m}, "info": [r["info"][i] for i in keep]})
        if r["K"] == "3":                                                      # historical K3 regression: cached legal len-3 sequences
            e = out[-1]; R = S.Root(pubm[r["root_id"]], "2d"); L, mv = set(R.legal_dests(R.cells0)), set(R.movable)
            for sq, v in sorted(k3[r["root_id"]].items()):
                q = json.loads(sq)
                if len({o for o, _ in q}) == 3 and len({d for _, d in q}) == 3 and all(o in mv and d in L for o, d in q):
                    e["known"][len(e["seqs"])] = {"x": v["x"], "y": v["y"], "z": rr.z_logic(v["x"], v["y"])}; e["seqs"].append(q)
                    e["info"].append({"max_tier": "TAIL", "off": 1.0, "prior": 0.0, "n_off4": 3, "ranks": []})
    f.write_bytes(pickle.dumps(out))
    return out


def dev_nll(net, roots, pub, dev="cuda"):
    """Mean over roots of the exact observed-data NLL of the exact-contract labels (decided X / Y only) on known candidates."""
    import xy as XY
    views, labs = [], []
    for r in roots:
        inp = pub[r["root_id"]]["inputs"]; P = lambda c: tuple(inp["cell_xy"][str(c)])  # noqa: E731
        ks = [i for i in sorted(r["known"]) if r["seqs"][i]]
        if not ks:
            continue
        v, ym, xm = XY.make_view(r["root_id"], inp["xy0"], inp["attrs"], inp["tid"], inp["goal"], inp["base"], inp["ctx"],
                                 [{int(o): P(d) for o, d in r["seqs"][i]} for i in ks], [[(int(o), P(d)) for o, d in r["seqs"][i]] for i in ks], XY._NoGeo)
        oy = {j: r["known"][i]["y"] for j, i in enumerate(ks) if r["known"][i]["y"] is not None}
        ox = {j: r["known"][i]["x"] for j, i in enumerate(ks) if r["known"][i]["x"] is not None}
        try:
            lab = XY.labels_for(v, ym, xm, oy, ox)
        except ValueError:
            continue
        views.append(v); labs.append(lab)
    tot, n = 0.0, 0
    with torch.no_grad():
        for i in range(0, len(views), 128):
            b, lab = XY.collate(views[i:i + 128], labs[i:i + 128], device=dev, dtype=torch.float32)
            C = net.coeffs(b)
            ll = XY.batched_log_evidence(C["b"], C["a"], C["w"], b["parent"], lab["y_obs"], lab["x_obs"], b["s_root"], b["n_roots"])
            tot += float(-ll.sum()); n += len(views[i:i + 128])
    return tot / max(n, 1)


def dev_eval(net, roots, pub):
    """Known-candidate top-1 / concordance (K1K2, all known and D4-only), K3 known top-1 (historical regression), K0/NONE EXACT4 decisions, NLL."""
    import search as S
    import diagnostics as D
    res = rr.readout(net, [(pub[r["root_id"]], r["seqs"]) for r in roots])
    for r, o in zip(roots, res):
        r["sc"] = {"cur": {"p11": np.array([x["p11"] for x in o["rows"]])}}
    sc = lambda r: r["sc"]["cur"]["p11"]  # noqa: E731
    k12 = D.ranking(roots, sc)
    d4roots = []
    for r in roots:
        d4roots.append({**r, "known": {i: v for i, v in r["known"].items() if i in r["in_d4"]}})
    d4 = D.ranking(d4roots, sc)
    k3 = D.ranking(roots, sc, Ks=("3",))
    safe = collections.Counter()
    for r in roots:
        if r["K"] not in ("0", "NONE"):
            continue
        R = S.Root(pub[r["root_id"]], "2d"); p = r["sc"]["cur"]["p11"]
        cand = [{"seq": [], "p11": float(p[0])}] + [{"seq": r["seqs"][i], "p11": float(p[i])} for i in r["d4"]]
        dec = D.decision(D.choose(R, cand))
        safe[f"K{r['K']}_n"] += 1
        safe[f"K{r['K']}_correct"] += (dec == "NOOP") if r["K"] == "0" else (dec == "ABSTAIN")
    return {"top1": k12["top1_known"][0], "conc": k12["concordance"][0], "top1_d4": d4["top1_known"][0], "k3_top1": k3["top1_known"][0],
            "k0_noop": safe["K0_correct"] / max(1, safe["K0_n"]), "none_abstain": safe["KNONE_correct"] / max(1, safe["KNONE_n"]),
            "nll": dev_nll(net, roots, pub), "per_root": {p["root_id"]: p for p in k12["per_root"]}}


# ------------------------------------------------------------------------------------------------------------- training
def train(arm, seed):
    import xy as XY
    which, lam = ARMS[arm]
    dev = "cuda"
    torch.manual_seed(seed); rng = np.random.default_rng(seed)
    items = train_items(which)
    for c in items:
        c["z"] = zq(c["v"], c["lab"])
    net = rr.load_net(rr.scorer_path(0), dev).train()                          # same warm start for every arm
    ck0 = torch.load(rr.scorer_path(0), map_location="cpu", weights_only=False)
    opt = torch.optim.AdamW(net.parameters(), lr=CFG["lr"], weight_decay=CFG["wd"])
    part = np.random.default_rng(seed).permutation(len(items))                   # fixed seeded partition (same roots => same batches across data arms)
    chunks = [[items[j] for j in part[i:i + CFG["batch"]]] for i in range(0, len(items), CFG["batch"])]
    pre = [XY.collate([c["v"] for c in ch], [c["lab"] for c in ch], device=dev, dtype=torch.float32) for ch in chunks]
    pub = {r["root_id"]: r for r in rr.public_val()}
    devr = dev_light("DEV_CAL")
    out = P4 / f"{arm}_s{seed}"; out.mkdir(parents=True, exist_ok=True)
    net.eval(); e0 = dev_eval(net, devr, pub); e0.pop("per_root")
    curve = [{"epoch": -1, **e0}]
    best, bad, t0 = None, 0, time.time()
    torch.cuda.reset_peak_memory_stats()
    for ep in range(CFG["epochs"]):
        net.train(); tl, tr_, npair = [], [], 0
        for k in rng.permutation(len(pre)):
            b, lab = pre[k]
            C = net.coeffs(b)
            nll_r = -XY.batched_log_evidence(C["b"], C["a"], C["w"], b["parent"], lab["y_obs"], lab["x_obs"], b["s_root"], b["n_roots"])
            loss_r = nll_r
            if lam:
                rk = rank_loss(C, b, chunks[k], rng, CFG)
                loss_r = nll_r + lam * CFG["C"] * rk; tr_.append(float(rk.detach().mean()))
            loss = loss_r.mean()
            opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(net.parameters(), CFG["clip"]); opt.step()
            tl.append(float(nll_r.detach().mean()))
        net.eval(); e = dev_eval(net, devr, pub); e.pop("per_root")
        torch.save({"state": net.state_dict(), "arm": ck0["arm"], "attr_dim": ck0["attr_dim"], "ctx_dim": ck0["ctx_dim"],
                    "xyrr_arm": arm, "seed": seed, "epoch": ep, "warm_start": rr.sha(rr.scorer_path(0)), "data": which, "lam": lam, "cfg": CFG}, out / f"ep{ep:02d}.pt")
        curve.append({"epoch": ep, "train_nll": float(np.mean(tl)), "train_rank": float(np.mean(tr_)) if tr_ else None, "s": round(time.time() - t0, 1), **e})
        key = (e["top1"], -e["nll"])
        if best is None or key > best[0]:
            best, bad = (key, ep), 0
        else:
            bad += 1
            if bad >= CFG["patience"]:
                break
        (out / "curve.json").write_text(json.dumps({"curve": curve, "cfg": CFG, "arm": arm, "seed": seed}, indent=1))
    (out / "curve.json").write_text(json.dumps({"curve": curve, "cfg": CFG, "arm": arm, "seed": seed, "wall_s": round(time.time() - t0, 1),
                                                 "gpu_peak_mib": round(torch.cuda.max_memory_allocated() / 2 ** 20, 1), "n_train_roots": len(items),
                                                 "pair_roots": sum(1 for c in items if 1 in c["z"] and 0 in c["z"])}, indent=1))
    print(json.dumps({"arm": arm, "seed": seed, "best": best, "s": round(time.time() - t0, 1)}))


if __name__ == "__main__":
    if sys.argv[1] in ARMS:
        train(sys.argv[1], int(sys.argv[2]))
