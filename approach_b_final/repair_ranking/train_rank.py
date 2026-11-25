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


def pick_epoch(curve, a0):
    """Prereg: eligible epochs (D4 top-1, K0 NOOP, NONE ABSTAIN, K3 top-1 >= A0 - 0.03), highest top-1, tie NLL (1e-3), earlier epoch."""
    el = [c for c in curve if c["epoch"] >= 0 and all((c[k] if c[k] is not None else 1) >= (a0[k] if a0[k] is not None else 0) - 0.03
                                                      for k in ("top1_d4", "k0_noop", "none_abstain", "k3_top1"))]
    if not el:
        return None
    top = max(c["top1"] for c in el)
    near = [c for c in el if c["top1"] >= top - 1e-3]
    lo = min(c["nll"] for c in near)
    return min((c for c in near if c["nll"] <= lo + 1e-3), key=lambda c: c["epoch"])


def select():
    import diagnostics as D
    pub = {r["root_id"]: r for r in rr.public_val()}
    cal, aud = dev_light("DEV_CAL"), dev_light("DEV_AUDIT")
    a0net = rr.load_net(rr.scorer_path(0))
    A0 = {"DEV_CAL": dev_eval(a0net, cal, pub), "DEV_AUDIT": dev_eval(a0net, aud, pub)}
    a0c = {k: v for k, v in A0["DEV_CAL"].items() if k != "per_root"}
    runs, ev = {}, {}
    for arm in ARMS:
        for seed in (0, 1, 2):
            f = P4 / f"{arm}_s{seed}" / "curve.json"
            if not f.exists():
                continue
            d = json.loads(f.read_text()); c = pick_epoch(d["curve"], a0c)
            runs[f"{arm}_s{seed}"] = {"selected_epoch": None if c is None else c["epoch"], "dev_cal_at_selected": c, "epochs_run": len(d["curve"]) - 1,
                                      "wall_s": d.get("wall_s"), "gpu_peak_mib": d.get("gpu_peak_mib"), "pair_roots": d.get("pair_roots"),
                                      "ckpt": None if c is None else str(P4 / f"{arm}_s{seed}" / f"ep{c['epoch']:02d}.pt"),
                                      "ckpt_sha256": None if c is None else rr.sha(P4 / f"{arm}_s{seed}" / f"ep{c['epoch']:02d}.pt")}
            if c is not None:
                net = rr.load_net(runs[f"{arm}_s{seed}"]["ckpt"])
                ev[f"{arm}_s{seed}"] = {"DEV_CAL": dev_eval(net, cal, pub), "DEV_AUDIT": dev_eval(net, aud, pub)}
    arm_mean = {}
    for arm in ARMS:
        ks = [k for k in ev if k.startswith(arm + "_")]
        if ks:
            arm_mean[arm] = {m: float(np.mean([ev[k]["DEV_CAL"][m] for k in ks if ev[k]["DEV_CAL"][m] is not None])) for m in ("top1", "conc", "nll", "top1_d4", "k3_top1", "k0_noop", "none_abstain")}
            arm_mean[arm]["seeds"] = len(ks)
            arm_mean[arm]["DEV_AUDIT"] = {m: float(np.mean([ev[k]["DEV_AUDIT"][m] for k in ks if ev[k]["DEV_AUDIT"][m] is not None])) for m in ("top1", "conc", "nll", "top1_d4", "k3_top1", "k0_noop", "none_abstain")}
            arm_mean[arm]["top1_sd"] = float(np.std([ev[k]["DEV_CAL"]["top1"] for k in ks]))

    def paired(a, b, part):
        pa, pb = a[part]["per_root"], b[part]["per_root"]
        com = sorted(set(pa) & set(pb)); fam = [pa[r]["family"] for r in com]
        return {"conc": D.cboot([pa[r]["conc"] - pb[r]["conc"] for r in com], fam), "top1": D.cboot([pa[r]["top1"] - pb[r]["top1"] for r in com], fam), "roots": len(com)}
    con = {}
    for part in ("DEV_CAL", "DEV_AUDIT"):
        for s in (0, 1, 2):
            g = lambda a: ev.get(f"{a}_s{s}")  # noqa: E731
            for name, a, b in (("A1-A0", "A1", None), ("A2-A1", "A2", "A1"), ("A3-A1", "A3", "A1"), ("A4-A2", "A4", "A2"), ("A4-A3", "A4", "A3"), ("A4-A0", "A4", None), ("A3-A0", "A3", None), ("A2-A0", "A2", None)):
                x, y = g(a), (A0 if b is None else g(b))
                if x and y:
                    con[f"{part}|s{s}|{name}"] = paired(x, y, part)
    best = max(arm_mean, key=lambda a: (arm_mean[a]["top1"], -arm_mean[a]["nll"])) if arm_mean else None
    fin = f"{best}_s0" if best and f"{best}_s0" in ev else None
    q = {}
    if fin:
        pc = paired(ev[fin], A0, "DEV_CAL"); pa = paired(ev[fin], A0, "DEV_AUDIT")
        q = {"DEV_CAL_conc_delta": pc["conc"], "DEV_CAL_top1": ev[fin]["DEV_CAL"]["top1"], "A0_DEV_CAL_top1": A0["DEV_CAL"]["top1"],
             "qualifies": pc["conc"][1] > 0 and ev[fin]["DEV_CAL"]["top1"] >= A0["DEV_CAL"]["top1"], "DEV_AUDIT_conc_delta": pa["conc"]}
        au, a0a = ev[fin]["DEV_AUDIT"], A0["DEV_AUDIT"]
        q["DEV_AUDIT_veto"] = pa["conc"][0] < 0 or au["top1"] < a0a["top1"] - 0.03 or any((au[k] or 0) < (a0a[k] or 0) - 0.03 for k in ("top1_d4", "k0_noop", "none_abstain", "k3_top1"))
        q["A_star"] = fin if q["qualifies"] and not q["DEV_AUDIT_veto"] else None
    strip = lambda e: {p: {k: v for k, v in e[p].items() if k != "per_root"} for p in e}  # noqa: E731
    res = {"A0": strip(A0), "runs": runs, "evals": {k: strip(v) for k, v in ev.items()}, "arm_mean_over_seeds": arm_mean, "contrasts": con,
           "best_arm_by_DEV_CAL": best, "finalist_checkpoint": fin, "finalist": q, "cfg": CFG}
    rr.wjson(rr.REP / "P4_ABLATION.json", res)
    print(json.dumps({"arm_mean": {a: {k: round(v, 4) if isinstance(v, float) else v for k, v in m.items() if k != "DEV_AUDIT"} for a, m in arm_mean.items()}, "finalist": q}, indent=1, default=str))


if __name__ == "__main__":
    if sys.argv[1] in ARMS:
        train(sys.argv[1], int(sys.argv[2]))
    elif sys.argv[1] == "select":
        select()
