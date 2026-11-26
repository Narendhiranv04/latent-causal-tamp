#!/usr/bin/env python3
"""KGT3 P2 evaluation, bounded scaling-only X training (O1 / O2) and the fresh local gate (FIG3_KGT3_PREREG P2).
Metrics (per split panel):  support (mixed h>=1 g2-3 families, discordant permutation families, mixed h0 families), marginal pX AUROC by
h / g with family-cluster CI, family-weighted discordant permutation concordance (ties 0.5) with family bootstrap, first-relocation FPR at
TPR 0.8, NLL / Brier / ECE / AUPRC, natural K<=3 p11 AUROC + max |db| vs F0.
    $PYG learn.py eval DOM SPLIT SPEC [SPEC ...]       -> O/kgt3/eval_DOM_SPLIT.json     (SPLIT in SELECT, TRAIN; GATE only via `gate`)
    $PYG learn.py fit DOM ARCH LOSS SEED                -> O/kgt3/ckpt/DOM_ARCH_LOSS_sSEED
    $PYG learn.py gate DOM SPEC                         -> O/kgt3/gate_DOM.json (guard-bound decision; opens VAL_GATE once)"""
from __future__ import annotations

import collections, copy, json, math, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "r3"), str(HERE.parent / "r24"), str(HERE.parent.parent)]
import common3 as K  # noqa: E402
import data2 as D2  # noqa: E402
import train as TR  # noqa: E402
C = K.C
O = C.FIG3 / "kgt3"
W_RANK = 0.25
ARCH = {"F1": {"init": "F0", "lr": 1e-4, "epochs": 40, "patience": 8}, "M1ft": {"init": "M1s_s0", "lr": 1e-4, "epochs": 40, "patience": 8},
        "G1ft": {"init": "G1s_s0", "lr": 1e-4, "epochs": 40, "patience": 8}, "M1scr": {"init": "scratch_M1", "lr": 1e-3, "epochs": 60, "patience": 10},
        "F0Xscr": {"init": "scratch_F0X", "lr": 1e-3, "epochs": 60, "patience": 10}}


def labels(dom, split):
    return [e for e in (json.loads(l) for l in open(O / f"labels_p2_{dom}.jsonl")) if e["split"] == split and e["label"] in (0, 1)]


def canon(p):
    return json.dumps(sorted(tuple(map(int, a)) for a in p))


def groups(P):
    """Exact matched permutation groups: same root, same placed set (scene), same unordered chunk set (endpoint), same protocol."""
    g = collections.defaultdict(list)
    for e in P:
        if e["m"] >= 2:
            g[(e["root_id"], canon(e["base"] + e["prefix"]), canon(e["chunk"]))].append(e)
    return {k: v for k, v in g.items() if len({json.dumps(x["chunk"]) for x in v}) >= 2}


def concordance(P, key="px", B=2000, seed=0):
    import numpy as np
    fam = collections.defaultdict(list)
    for k, v in groups(P).items():
        pos = [e for e in v if e["label"] == 1]; neg = [e for e in v if e["label"] == 0]
        if pos and neg:
            s = [1.0 if a[key] > b[key] else 0.5 if a[key] == b[key] else 0.0 for a in pos for b in neg]
            fam[v[0]["fam"]].append((sum(s) / len(s), len(s)))
    if not fam:
        return {"families": 0, "pairs": 0, "concordance": None, "ci95": None}
    fs = sorted(fam); val = {f: sum(x for x, _ in fam[f]) / len(fam[f]) for f in fs}
    rng = np.random.default_rng(seed)
    bs = [float(np.mean([val[f] for f in rng.choice(fs, len(fs))])) for _ in range(B)]
    return {"families": len(fs), "groups": sum(len(v) for v in fam.values()), "pairs": sum(n for v in fam.values() for _, n in v),
            "concordance": float(np.mean(list(val.values()))), "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]}


def support(P):
    mix = lambda S: sum(1 for v in _byfam(S).values() if len({e["label"] for e in v}) == 2)  # noqa: E731
    disc = {v[0]["fam"] for v in groups(P).values() if len({e["label"] for e in v}) == 2}
    return {"mixed_h1_g23": mix([e for e in P if e["h"] >= 1 and e["m"] >= 2]), "discordant_perm_families": len(disc),
            "mixed_h0": mix([e for e in P if e["h"] == 0]), "mixed_h1_g2": mix([e for e in P if e["h"] >= 1 and e["m"] == 2]),
            "mixed_h1_g3": mix([e for e in P if e["h"] >= 1 and e["m"] == 3])}


def _byfam(S):
    d = collections.defaultdict(list)
    for e in S:
        d[e["fam"]].append(e)
    return d


STR = {"all": lambda e: True, "h0": lambda e: e["h"] == 0, "h>=1_g23": lambda e: e["h"] >= 1 and e["m"] >= 2, "h>=1_g2": lambda e: e["h"] >= 1 and e["m"] == 2,
       "h>=1_g3": lambda e: e["h"] >= 1 and e["m"] == 3, "h0_g23": lambda e: e["h"] == 0 and e["m"] >= 2, "h>=1": lambda e: e["h"] >= 1,
       "h0_g1": lambda e: e["h"] == 0 and e["m"] == 1, "h>=2": lambda e: e["h"] >= 2, "CHAIN": lambda e: e["stratum"] == "CHAIN", "ORD": lambda e: e["stratum"] == "ORD"}


def load(dom, spec):
    """F0 | G1s_s0 | M1s_s0 (R3 checkpoints) | ARCH_LOSS_sSEED (KGT3 checkpoints)."""
    import torch
    if spec == "F0":
        fz, base = TR.f0(dom)
        return fz, base.to("cuda").eval()
    if spec in ("G1s_s0", "M1s_s0"):
        a, s = spec.split("_s")
        return TR.load(dom, a, s)
    arch = spec.split("_")[0]
    fz, base = TR.f0(dom)
    net = make(dom, arch, base)
    ck = torch.load(O / "ckpt" / f"{dom}_{spec}" / "model.pt", map_location="cuda", weights_only=False)
    net.load_state_dict(ck["state"])
    return fz, net.eval()


def make(dom, arch, base):
    import torch
    import xrel
    cfg = ARCH[arch]
    if arch == "F1":
        return TR.make_net(dom, "F1", base).to("cuda")
    if arch in ("M1ft", "G1ft"):
        net = xrel.build("M1" if arch == "M1ft" else "G1", base).to("cuda")
        if Path(K.O / "ckpt" / f"{dom}_{cfg['init'].replace('_s0', '')}_s0").exists():
            ck = torch.load(K.O / "ckpt" / f"{dom}_{cfg['init'].replace('_s0', '')}_s0" / "model.pt", map_location="cuda", weights_only=False)
            net.load_state_dict(ck["state"])
        return net
    if arch == "M1scr":
        return xrel.build("M1", base).to("cuda")
    if arch == "F0Xscr":
        net = TR.make_net(dom, "F1", base).to("cuda")
        for n, m in net.named_modules():
            if n.split(".")[0] in TR.X_ONLY and hasattr(m, "reset_parameters"):
                m.reset_parameters()
        return net
    raise KeyError(arch)


def predict(dom, net, labs):
    rows = D2.all_rows(dom)
    va, conf = TR.local_views(dom, labs, rows)
    P = TR.predict(net, va, "cuda")
    by = {(e["root_id"], json.dumps(e["prefix"]), json.dumps(e["chunk"])): e for e in labs}
    out = []
    for p in P:
        src = by[(p["root_id"], json.dumps(p["prefix"]), json.dumps(p["chunk"]))]
        out.append({**src, **{k: p[k] for k in ("px", "px1", "px0", "py", "p11")}})
    return out, conf


def metrics(P):
    from evaluate import fpr_at_tpr
    st = {k: C.summary([e for e in P if f(e)], "label", "px", "fam", B=2000) for k, f in STR.items()}
    return {"support": support(P), "strata": st, "concordance": concordance(P), "fpr_first": fpr_at_tpr([e for e in P if e["h"] == 0 and e["m"] == 1], "px"),
            "fam_nll": TR.fam_nll(P) if P else None, "n": len(P)}


def eval_(dom, split, specs):
    import evaluate as EVL
    assert split in ("SELECT", "TRAIN"), "VAL_GATE is opened only by `gate`"
    labs = labels(dom, split)
    out = {}
    _, base = TR.f0(dom); base = base.to("cuda").eval()
    N0, b0 = EVL.natural(base, dom)
    for s in specs:
        _, net = load(dom, s)
        P, conf = predict(dom, net, labs)
        m = metrics(P)
        N, b = (N0, b0) if s == "F0" else EVL.natural(net, dom)
        m["natural"] = {"p11_auroc": C.summary(N, "z", "p11", "fam")["auroc"], "px_auroc": C.summary(N, "x", "px", "fam")["auroc"], "max_abs_db": float((b - b0).abs().max())}
        m["qualifies"] = bool((m["strata"]["h>=1_g23"].get("auroc") or 0) >= 0.75 and (m["concordance"]["concordance"] or 0) >= 0.70)
        m["conflicts_dropped"] = conf
        out[s] = m
        print(s, json.dumps({"support": m["support"], "h1g23": [m["strata"]["h>=1_g23"].get("auroc"), m["strata"]["h>=1_g23"].get("auroc_ci")],
                             "conc": [m["concordance"]["concordance"], m["concordance"]["ci95"], m["concordance"]["families"]], "h0": m["strata"]["h0"].get("auroc"),
                             "nll": m["fam_nll"], "nat_p11": m["natural"]["p11_auroc"], "db": m["natural"]["max_abs_db"], "qualifies": m["qualifies"]}, default=str), flush=True)
    (O / f"eval_{dom}_{split}.json").write_text(json.dumps(out, indent=1, default=str))
    return out


# ------------------------------------------------------------------------------------------------ training (O1 / O2)
def rank_loss(Cf, b, items):
    """Within-family mean over exact discordant permutation pairs (same view = same start scene, same endpoint node) of
    softplus(-(logit pX(C+) - logit pX(C-))), then mean over families present."""
    import torch
    bb, a, w = Cf["b"], Cf["a"], Cf["w"]
    py = torch.sigmoid(bb[b["parent"]])
    px = py * torch.sigmoid(a + w) + (1 - py) * torch.sigmoid(a)
    lg = torch.logit(px.clamp(1e-6, 1 - 1e-6)).clamp(-20, 20)
    fam, qo = collections.defaultdict(list), 0
    for it in items:
        v = it["v"]
        if it.get("rows"):
            byp = collections.defaultdict(list)
            for q, e in enumerate(it["rows"]):
                if e is not None and e["label"] in (0, 1):
                    byp[v["parent"][q]].append((q, e["label"]))
            for lst in byp.values():
                for qp, yp in lst:
                    for qn, yn in lst:
                        if yp == 1 and yn == 0:
                            fam[it["fam"]].append(torch.nn.functional.softplus(-(lg[qo + qp] - lg[qo + qn])))
        qo += len(v["x_seqs"])
    if not fam:
        return None
    return torch.stack([torch.stack(v).mean() for v in fam.values()]).mean()


def fit(dom, arch, loss, seed):
    import numpy as np
    import torch
    import xy as XY
    torch.manual_seed(int(seed)); rng = np.random.default_rng(int(seed))
    rows = D2.all_rows(dom)
    trl = labels(dom, "TRAIN")
    if dom == "3d":
        trl += [e for e in TR.load_labels("3d") if e["split"] == "TRAIN_SCALE"]
    tr, c1 = TR.local_views(dom, trl, rows)
    va, c2 = TR.local_views(dom, labels(dom, "SELECT"), rows)
    rp = TR.replay(dom)
    fz, base = TR.f0(dom)
    net = make(dom, arch, base).to("cuda")
    params = [p for p in net.parameters() if p.requires_grad]
    cfg = ARCH[arch]
    opt = torch.optim.AdamW(params, lr=cfg["lr"], weight_decay=1e-4)
    fam_n = collections.Counter(x["fam"] for x in tr)
    wts = np.array([1.0 / fam_n[x["fam"]] for x in tr]); wts /= wts.sum()
    rb = [list(range(i, min(i + 32, len(rp)))) for i in range(0, len(rp), 32)]
    tag = f"{arch}_{loss}_s{seed}"
    out = O / "ckpt" / f"{dom}_{tag}"; out.mkdir(parents=True, exist_ok=True)

    def vnll():
        net.eval()
        return TR.fam_nll(TR.predict(net, va, "cuda"))
    v0 = vnll()
    curve, best, bad, t0 = [{"epoch": -1, "val_fam_nll": v0}], (v0, -1), 0, time.time()
    torch.save({"state": net.state_dict(), "epoch": -1}, out / "model.pt")
    with torch.no_grad():
        b0 = net.coeffs(XY.collate([rp[0]["v"]], device="cuda", dtype=torch.float32)[0])["b"].clone()
    for ep in range(cfg["epochs"]):
        net.train(); tl, tr_rank = [], []
        for k in rng.permutation(len(rb)):
            li = rng.choice(len(tr), size=32, replace=True, p=wts)
            items = [rp[j] for j in rb[k]] + [tr[j] for j in li]
            b, lab = XY.collate([x["v"] for x in items], [x["lab"] for x in items], device="cuda", dtype=torch.float32)
            Cf = net.coeffs(b)
            nll = -XY.batched_log_evidence(Cf["b"], Cf["a"], Cf["w"], b["parent"], lab["y_obs"], lab["x_obs"], b["s_root"], b["n_roots"]).mean()
            L = nll
            if loss == "O2":
                r = rank_loss(Cf, b, items)
                if r is not None:
                    L = nll + W_RANK * r; tr_rank.append(float(r.detach()))
            opt.zero_grad(); L.backward(); torch.nn.utils.clip_grad_norm_(params, 10.0); opt.step()
            tl.append(float(nll.detach()))
        vl = vnll()
        curve.append({"epoch": ep, "train_nll": float(np.mean(tl)), "train_rank": float(np.mean(tr_rank)) if tr_rank else None, "val_fam_nll": vl, "s": round(time.time() - t0, 1)})
        print(json.dumps(curve[-1]), flush=True)
        if vl < best[0] - 1e-5:
            best, bad = (vl, ep), 0
            torch.save({"state": net.state_dict(), "epoch": ep}, out / "model.pt")
        else:
            bad += 1
            if bad >= cfg["patience"]:
                break
    with torch.no_grad():
        net.load_state_dict(torch.load(out / "model.pt", map_location="cuda", weights_only=False)["state"])
        b1 = net.coeffs(XY.collate([rp[0]["v"]], device="cuda", dtype=torch.float32)[0])["b"]
    assert float((b1 - b0).abs().max()) == 0.0, "Y changed"
    info = {"dom": dom, "arch": arch, "loss": loss, "seed": int(seed), "curve": curve, "best_val_fam_nll": best[0], "best_epoch": best[1], "wall_s": round(time.time() - t0, 1),
            "n_train_views": len(tr), "n_select_views": len(va), "conflicts": [c1, c2], "trainable_params": sum(p.numel() for p in params),
            "model_sha256": K.sha(out / "model.pt"), "y_bitwise": True}
    (out / "curve.json").write_text(json.dumps(info, indent=1))
    print(json.dumps({k: v for k, v in info.items() if k != "curve"}))


# ------------------------------------------------------------------------------------------------ fresh gate (opened once)
def gate(dom, spec):
    import evaluate as EVL
    import guard as GD
    jf, rf = O / f"jobs_p2_{dom}.json", O / f"phys_p2_{dom}.jsonl"
    labs = labels(dom, "GATE")
    _, base = TR.f0(dom); base = base.to("cuda").eval()
    P0, _ = predict(dom, base, labs)
    _, net = load(dom, spec)
    P1, _ = predict(dom, net, labs) if spec != "F0" else (P0, 0)
    m0, m1 = metrics(P0), metrics(P1)
    N0, b0 = EVL.natural(base, dom)
    N1, b1 = (N0, b0) if spec == "F0" else EVL.natural(net, dom)
    from evaluate import paired
    pr = paired(P0, P1, STR["h>=1_g23"]) if spec != "F0" else None
    s, st, cc = m1["support"], m1["strata"]["h>=1_g23"], m1["concordance"]
    f0f, f1f = m0["fpr_first"], m1["fpr_first"]
    nat0, nat1 = C.summary(N0, "z", "p11", "fam")["auroc"], C.summary(N1, "z", "p11", "fam")["auroc"]
    g = {"spec": spec, "support": s,
         "support_ok": s["mixed_h1_g23"] >= 10 and s["discordant_perm_families"] >= 10 and s["mixed_h0"] >= 10,
         "auroc_h1_g23": st.get("auroc"), "auroc_ci": st.get("auroc_ci"),
         "auroc_pass": st.get("auroc") is not None and st["auroc"] >= 0.75 and bool(st.get("auroc_ci")) and st["auroc_ci"][0] >= 0.60,
         "concordance": cc, "concordance_pass": cc["concordance"] is not None and cc["concordance"] >= 0.70 and cc["ci95"][0] > 0.50,
         "paired_vs_F0": pr, "paired_pass": spec == "F0" or bool(pr and pr["ci95"] and pr["ci95"][0] > 0),
         "natural_p11": [nat0, nat1], "natural_pass": nat0 - nat1 <= 0.05, "max_abs_db": float((b1 - b0).abs().max()), "y_pass": float((b1 - b0).abs().max()) == 0.0,
         "fpr_first": [f0f and f0f["fpr"], f1f and f1f["fpr"]], "fpr_block": bool(f0f and f1f and f1f["fpr"] - f0f["fpr"] > 0.05)}
    g["PASS"] = bool(g["support_ok"] and g["auroc_pass"] and g["concordance_pass"] and g["paired_pass"] and g["natural_pass"] and g["y_pass"] and not g["fpr_block"])
    g["DECISION"] = "PASS" if g["PASS"] else ("DATA_LIMITED" if not g["support_ok"] else ("BLOCKED" if g["fpr_block"] else "FAIL"))
    res = {"decision": g, "selected": m1, "F0": m0}
    (O / f"gate_{dom}_metrics.json").write_text(json.dumps(res, indent=1, default=str))
    inputs = [jf, rf, O / f"labels_p2_{dom}.jsonl", O / f"gate_{dom}_metrics.json", Path(__file__), HERE / "data2.py"]
    if spec not in ("F0", "G1s_s0", "M1s_s0"):
        inputs.append(O / "ckpt" / f"{dom}_{spec}" / "model.pt")
    GD.decide(O / f"gate_{dom}.json", {"P2_GATE": g["DECISION"], "spec": spec}, inputs, manifests=[(jf, rf)])
    print(json.dumps(g, default=str))


if __name__ == "__main__":
    a = sys.argv[1]
    if a == "eval":
        eval_(sys.argv[2], sys.argv[3], sys.argv[4:])
    elif a == "fit":
        fit(*sys.argv[2:6])
    elif a == "gate":
        gate(sys.argv[2], sys.argv[3])
