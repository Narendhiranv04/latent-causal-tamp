#!/usr/bin/env python3
"""R5.2 controlled local-X learning (R5_PREREG R5_2).  Y pathway + cVAE frozen (bitwise-asserted); fresh X components; original observed-data
likelihood (xy.batched_log_evidence, unknown X / Y marginalised); R3 replay / local-view machinery reused (r3/train.py).

Representations  A = original ordered XYNet X modules (act, pairo, mix, order_s, xy) re-initialised on the frozen F0 encoder / Y path
                 M = query-relative MLP (r3/xrel M1), G = query-relative GNN (r3/xrel G1)      (both fresh)
Data             0 = original v32 TRAIN replay only;  1 = + ADDITIONAL strict local labels (replayed positives, certified negatives, chunks <= 3)
Controls         ORDINV (actions canonically sorted -> orders indistinguishable), UNCOUPLED (w = 0), DIRECT (a trained as a short-sequence
                 success logit by BCE on observed replay success; compared on K <= 3 success only)
VAL              strict local labels of R5.1 VAL families (+ 2D: KGT3 P2 2D GATE families, never read by a model before)
    $PYG xlearn.py data DOM                 -> O/kgt3/r5/xl/data_DOM.json (provenance, support, split audit)
    $PYG xlearn.py run DOM STAGE [args]     STAGE = recipe | matrix | controls   -> results_DOM.jsonl, ckpt/
    $PYG xlearn.py select DOM               -> selection_DOM.json (preregistered rule)"""
from __future__ import annotations

import collections, copy, hashlib, json, math, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "r3"), str(HERE.parent / "r24"), str(HERE.parent.parent)]
import common3 as K  # noqa: E402
import guard as GD  # noqa: E402
import views as V  # noqa: E402
C = K.C
O = C.FIG3 / "kgt3"
XL = O / "r5" / "xl"
RECIPES = {"lo": {"lr": 1e-4, "epochs": 60, "patience": 10}, "hi": {"lr": 1e-3, "epochs": 60, "patience": 10}}
REPS = ("A", "M", "G")


def h01(*a):
    return int(hashlib.sha256("|".join(map(str, a)).encode()).hexdigest()[:8], 16) / 2 ** 32


def new_split(fam):
    return "VAL" if h01("R5.1-split", fam) < 0.40 else "TRAIN"


def jl(p):
    return [json.loads(l) for l in open(p)] if Path(p).exists() else []


# ------------------------------------------------------------------------------------------------------------------ strict labels
def chunk_labels(seq, bounds, oc, phase, replay_ok):
    """-> [(s, e, label, kind)] strict: positives only from SUCCESS runs with independent replay; negatives only the certified failing chunk."""
    b = [0] + list(bounds)
    ch = list(zip(b[:-1], b[1:]))
    if oc == "SUCCESS":
        return [(s, e, 1, "pos_replayed") for s, e in ch] if replay_ok else []
    ph = str(phase or "")
    if oc == "CERTIFIED_INFEASIBLE" and ph.startswith("relocation"):
        j = int(ph.split(":")[1])
        return [(s, e, 0, "neg_certified") for s, e in ch if s <= j < e]
    return []


def _entry(rowkey, fam, split, src, seq, s, e, lab, kind, N, dep):
    return {"root_id": rowkey, "fam": fam, "split": split, "src": src, "base": [], "prefix": seq[:s], "chunk": seq[s:e], "label": lab, "kind": kind,
            "h": s, "m": e - s, "N": N, "dep": dep}


def build(dom):
    """-> entries (strict additional local labels), rows {rowkey: row}, audit."""
    import contracts as CT
    import data2 as D2
    rows, E, audit = {}, [], collections.Counter()
    # (1) KGT3 P2 (historical X_CHUNKED runs; strict filter applied, drops counted)
    allr = D2.all_rows(dom)
    for tag in ("p2", "p2x"):
        jf = O / f"jobs_{tag}_{dom}.json"
        if not jf.exists():
            continue
        R = {r["key"]: r for r in jl(O / f"phys_{tag}_{dom}.jsonl")}
        for j in json.loads(jf.read_text()):
            r = R.get(j["key"])
            if not r:
                continue
            X = r.get("X") or {}
            oc = GD.outcome(r, "X")
            rep = (r.get("REPLAY") or {}).get("replay") == 1 if dom == "3d" else bool(X.get("independent_replay"))
            seq = [list(map(int, a)) for a in (j.get("seq_idx") or j["seq"])]
            split = "VAL" if (dom == "2d" and j["split"] == "GATE") else "TRAIN"
            rows[j["root_id"]] = {"root_id": j["root_id"], "domain": dom, "inputs": allr[j["root_id"]]["inputs"]}
            out = chunk_labels(seq, j["bounds"], oc, X.get("phase") or X.get("failed_phase"), rep)
            audit[f"KGT3|{oc}|{'kept' if out else 'dropped'}"] += 1
            E += [_entry(j["root_id"], "KGT3|" + str(j["fam"]), split, "KGT3_P2" + ("_GATE2D" if split == "VAL" else ""), seq, s, e, l, k,
                         len(allr[j["root_id"]]["inputs"]["ids"]), j.get("stratum")) for s, e, l, k in out]
    # (2) R3.1 3D local labels (historical contract audited; strict additionally requires replay / certificate from the raw run)
    if dom == "3d":
        R = {r["key"]: r for r in jl(K.O / "phys_31_3d.jsonl")}
        snap = C.snapshot_rows(dom, snap=C.SNAP_TRAIN)
        for e in jl(K.O / "labels_31_3d.jsonl"):
            r = R.get(e["key"])
            if not r or e["label"] not in (0, 1):
                audit["R3.1|missing"] += 1; continue
            oc = GD.outcome(r, "X"); rep = (r.get("REPLAY") or {}).get("replay") == 1
            ok = (e["label"] == 1 and oc == "SUCCESS" and rep) or (e["label"] == 0 and oc == "CERTIFIED_INFEASIBLE" and e["kind"] == "chunk_neg")
            audit[f"R3.1|hist_label{e['label']}|{oc}|{'kept' if ok else 'dropped'}"] += 1
            if ok:
                rows[e["root_id"]] = {"root_id": e["root_id"], "domain": dom, "inputs": snap[e["root_id"]]["inputs"]}
                E.append({**_entry(e["root_id"], "R3.1|" + str(e["fam"]), "TRAIN", "R3.1", e["base"] + e["prefix"], len(e["base"] + e["prefix"]),
                                   len(e["base"] + e["prefix"]) + e["m"], e["label"], "pos_replayed" if e["label"] else "neg_certified", e["N"], e.get("template")),
                          "base": e["base"], "prefix": e["prefix"], "chunk": e["chunk"]})
    # (3) constructed families: R4.3 / R5.1 2D (queries) or R4.4 / R5.1 3D (jobs + phys)
    if dom == "2d":
        for src, d, split_fn in (("R4.3", O / "r4" / "b2d", lambda f: "TRAIN"), ("R5.1", O / "r5" / "b2d", new_split)):
            for q in jl(d / "queries.jsonl"):
                if q["kind"] not in ("X", "PROBE"):
                    continue
                rec = json.loads(Path(q["rec"]).read_text())
                inp = CT.view2d(rec)
                key = f"{q['fid']}|{hashlib.sha256(json.dumps(sorted(q['cells'].items())).encode()).hexdigest()[:12]}"
                rows[key] = {"root_id": key, "domain": "2d", "inputs": inp}
                ix = {n: i for i, n in enumerate(inp["ids"])}
                seq = [[ix[o], int(dd)] for o, dd in q["seq"]]
                out = chunk_labels(seq, q["bounds"], q["outcome"], q.get("phase"), q["outcome"] == "SUCCESS")
                audit[f"{src}|{q['outcome']}|{'kept' if out else 'dropped'}"] += 1
                E += [_entry(key, f"{src}|{q['fid']}", split_fn(q["fid"]), src, seq, s, e, l, k, len(inp["ids"]), q["stage"]) for s, e, l, k in out]
    else:
        for src, d, split_fn in (("R4.4", O / "r4" / "d3d", lambda f: "TRAIN"), ("R5.1", O / "r5" / "d3d", new_split)):
            if not (d / "jobs.json").exists():
                continue
            rw = {r["root_id"]: r for r in jl(d / "rows.jsonl")}
            R = {r["key"]: r for r in jl(d / "phys.jsonl")}
            for j in json.loads((d / "jobs.json").read_text()):
                r = R.get(j["key"])
                if j["kind"] != "X_CHUNKED" or not r:
                    continue
                oc = GD.outcome(r, "X"); rep = (r.get("REPLAY") or {}).get("replay") == 1
                rows[j["root_id"]] = {"root_id": j["root_id"], "domain": "3d", "inputs": rw[j["root_id"]]["inputs"]}
                out = chunk_labels(j["seq"], j["bounds"], oc, (r.get("X") or {}).get("phase"), rep)
                audit[f"{src}|{oc}|{'kept' if out else 'dropped'}"] += 1
                E += [_entry(j["root_id"], f"{src}|{j['fam']}", split_fn(j["fam"]), src, j["seq"], s, e, l, k, len(rw[j["root_id"]]["inputs"]["ids"]), j["template"])
                      for s, e, l, k in out]
    assert all(e["m"] <= 3 for e in E), "supervised local sequences must have length <= 3"
    return E, rows, audit


def groups(E):
    g = collections.defaultdict(list)
    for e in E:
        if e["m"] >= 2:
            g[(e["root_id"], json.dumps(sorted(map(tuple, e["base"] + e["prefix"]))), json.dumps(sorted(map(tuple, e["chunk"]))))].append(e)
    return {k: v for k, v in g.items() if len({json.dumps(x["chunk"]) for x in v}) >= 2 and len({x["label"] for x in v}) == 2}


def data(dom):
    E, rows, audit = build(dom)
    fams = collections.defaultdict(set)
    for e in E:
        fams[e["split"]].add(e["fam"])
    assert not (fams["TRAIN"] & fams["VAL"]), "family leak between TRAIN and VAL"
    val = [e for e in E if e["split"] == "VAL"]
    G = groups(val)
    sup = {"val_families": len(fams["VAL"]), "val_matched_discordant_groups": len(G),
           "val_families_with_h_ge_1_multi": len({e["fam"] for e in val if e["h"] >= 1 and e["m"] >= 2}),
           "train_families": len(fams["TRAIN"])}
    mins = {"val_families": 20, "val_matched_discordant_groups": 30, "val_families_with_h_ge_1_multi": 10}
    cnt = collections.Counter(f"{e['split']}|{e['src']}|h{min(e['h'], 3)}|g{e['m']}|y{e['label']}" for e in E)
    out = {"dom": dom, "n": len(E), "support": sup, "minima": mins, "minima_met": all(sup[k] >= v for k, v in mins.items()), "audit": dict(sorted(audit.items())),
           "counts": dict(sorted(cnt.items())), "density": dict(collections.Counter(f"{e['split']}|N{e['N']}" for e in E)),
           "dependency_type": dict(collections.Counter(f"{e['split']}|{e['dep']}" for e in E))}
    XL.mkdir(parents=True, exist_ok=True)
    (XL / f"data_{dom}.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: out[k] for k in ("n", "support", "minima_met")}))
    return E, rows, out


# ------------------------------------------------------------------------------------------------------------------ models
X_ONLY = ("act", "pairo", "mix", "order_s", "xy")


class Ctl(__import__("torch").nn.Module):
    """Control wrapper with identical semantics for every representation: ORDINV sorts each query's actions by the stable object key before the
    X module sees them; UNCOUPLED / DIRECT zero w (X independent of Y; DIRECT reads sigmoid(a) as a short-sequence success probability)."""
    def __init__(self, net, ctrl):
        super().__init__()
        self.net, self.ctrl = net, ctrl

    def coeffs(self, b):
        import torch
        if self.ctrl == "ORDINV" and len(b["q_root"]):
            obj = b["q_obj"]
            key = b["okey"][b["q_root"]].gather(1, obj.clamp(min=0))
            o = torch.sort(torch.where(obj < 0, torch.full_like(obj, 1 << 31), key), dim=1, stable=True).indices
            b = {**b, "q_obj": obj.gather(1, o), "q_dest": b["q_dest"].gather(1, o[..., None].expand(-1, -1, 2))}
        Cf = self.net.coeffs(b)
        if self.ctrl in ("UNCOUPLED", "DIRECT"):
            Cf = {**Cf, "w": Cf["w"] * 0.0}
        return Cf


class Cal(__import__("torch").nn.Module):
    """R5.3 temperature calibration of the X conditional logits: a' = a / T, (a + w)' = (a + w) / T  (so w' = w / T); Y untouched; marginal pX
    and p11 are recomputed from the scaled logits by every consumer (the probabilistic contract is preserved)."""
    def __init__(self, net, T):
        super().__init__()
        self.net, self.T = net, float(T)

    def coeffs(self, b):
        Cf = self.net.coeffs(b)
        return {**Cf, "a": Cf["a"] / self.T, "w": Cf["w"] / self.T}


def fit_temperature(net, va, dev, grid=None):
    """T minimising VAL family NLL of marginal pX (grid, local VAL labels only)."""
    import numpy as np
    import train as TR
    grid = grid or [float(x) for x in np.round(np.exp(np.linspace(np.log(0.4), np.log(4.0), 41)), 4)]
    sc = [(TR.fam_nll(TR.predict(Cal(net, T), va, dev)), T) for T in grid]
    best = min(sc)
    return {"T": best[1], "val_nll_cal": best[0], "val_nll_raw": TR.fam_nll(TR.predict(net, va, dev)), "grid": sc}


def make(rep, base, ctrl=None):
    import torch
    if rep == "A":
        net = copy.deepcopy(base)
        net.cfg = dict(net.cfg)
        for n in X_ONLY:
            for m in getattr(net, n).modules():
                if hasattr(m, "reset_parameters"):
                    m.reset_parameters()
        for n, p in net.named_parameters():
            p.requires_grad_(n.split(".")[0] in X_ONLY)
    else:
        import xrel
        net = xrel.build({"M": "M1", "G": "G1"}[rep], base)
    return Ctl(net, ctrl) if ctrl else net


def ysha(net):
    import torch
    base = net.net if isinstance(net, Ctl) else net
    base = getattr(base, "base", base)
    hs = hashlib.sha256()
    for n, p in sorted(base.named_parameters()):
        if n.split(".")[0] not in X_ONLY:
            hs.update(n.encode()); hs.update(p.detach().cpu().numpy().tobytes())
    return hs.hexdigest()


# ------------------------------------------------------------------------------------------------------------------ evaluation
def metrics(P, key="px"):
    import numpy as np
    import xy as XY
    if not P:
        return {}
    y = np.array([e["label"] for e in P]); p = np.clip(np.array([e[key] for e in P]), 1e-6, 1 - 1e-6)
    by = collections.defaultdict(list)
    for e, pp in zip(P, p):
        by[e["fam"]].append(-(e["label"] * math.log(pp) + (1 - e["label"]) * math.log(1 - pp)))
    out = {"n": len(P), "fam_nll": float(np.mean([np.mean(v) for v in by.values()])), "brier": float(np.mean((p - y) ** 2)), "ece": XY.ece(y, p),
           "auroc": XY.auroc(y, p), "auprc": XY.auprc(y, p), "pos_rate": float(y.mean())}
    return out


def concordance(P, key="px", B=1000, seed=0):
    import numpy as np
    fam = collections.defaultdict(list)
    for k, v in groups(P).items():
        pos = [e for e in v if e["label"] == 1]; neg = [e for e in v if e["label"] == 0]
        s = [1.0 if a[key] > b[key] else 0.5 if a[key] == b[key] else 0.0 for a in pos for b in neg]
        fam[v[0]["fam"]].append(sum(s) / len(s))
    if not fam:
        return {"families": 0, "concordance": None}
    fv = {f: float(np.mean(v)) for f, v in fam.items()}; fs = sorted(fv)
    rng = np.random.default_rng(seed)
    bs = [float(np.mean([fv[f] for f in rng.choice(fs, len(fs))])) for _ in range(B)]
    return {"families": len(fs), "groups": sum(len(v) for v in fam.values()), "concordance": float(np.mean(list(fv.values()))),
            "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]}


def evaluate(net, va, dev):
    import train as TR
    P = TR.predict(net, va, dev)
    sub = {"all": P, "h0": [e for e in P if e["h"] == 0], "h_ge1": [e for e in P if e["h"] >= 1], "g1": [e for e in P if e["m"] == 1],
           "g_ge2": [e for e in P if e["m"] >= 2], "h_ge1_g_ge2": [e for e in P if e["h"] >= 1 and e["m"] >= 2]}
    return {"metrics": {k: metrics(v) for k, v in sub.items()}, "concordance": concordance(P), "concordance_h_ge1": concordance([e for e in P if e["h"] >= 1])}


def k3_regression(net, items, dev):
    """Original K <= 3 VAL roots: exact observed-data NLL (original objective) and success AUROC of p11 / direct sigmoid(a)."""
    import numpy as np
    import torch
    import xy as XY
    nll, ys, ps = [], [], []
    with torch.no_grad():
        for i in range(0, len(items), 64):
            ch = items[i:i + 64]
            b, lab = XY.collate([c["v"] for c in ch], [c["lab"] for c in ch], device=dev, dtype=torch.float32)
            Cf = net.coeffs(b)
            nll.append(float(-XY.batched_log_evidence(Cf["b"], Cf["a"], Cf["w"], b["parent"], lab["y_obs"], lab["x_obs"], b["s_root"], b["n_roots"]).mean()) * len(ch))
            py = torch.sigmoid(Cf["b"])[b["parent"]]
            direct = isinstance(net, Ctl) and net.ctrl == "DIRECT"
            p11 = torch.sigmoid(Cf["a"]) if direct else py * torch.sigmoid(Cf["a"] + Cf["w"])
            m = lab["succ_q"] >= 0
            ys += lab["succ_q"][m].cpu().tolist(); ps += p11[m].cpu().tolist()
    yv, pv = np.array(ys, float), np.clip(np.array(ps, float), 1e-6, 1 - 1e-6)
    bce = float(-np.mean(yv * np.log(pv) + (1 - yv) * np.log(1 - pv))) if len(yv) else None
    return {"root_nll": sum(nll) / max(1, len(items)), "succ_auroc": XY.auroc(yv, pv), "succ_bce": bce, "succ_ece": XY.ece(yv, pv) if len(yv) else None,
            "n_roots": len(items), "n_succ_labels": len(ys)}


# ------------------------------------------------------------------------------------------------------------------ training
def fit(dom, rep, dat, recipe, seed, ctrl, tr, va, rp, k3val, base, dev="cuda"):
    import numpy as np
    import torch
    import xy as XY
    import train as TR
    rc = RECIPES[recipe]
    torch.manual_seed(int(seed)); rng = np.random.default_rng(int(seed))
    net = make(rep, base, ctrl).to(dev)
    y0 = ysha(net)
    params = [p for p in net.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=rc["lr"], weight_decay=1e-4)
    loc = tr if dat == 1 else []
    fam_n = collections.Counter(x["fam"] for x in loc)
    wts = np.array([1.0 / fam_n[x["fam"]] for x in loc]) if loc else None
    if loc:
        wts /= wts.sum()
    rb = [list(range(i, min(i + 32, len(rp)))) for i in range(0, len(rp), 32)]
    name = f"{dom}_{rep}{dat}_{recipe}_{ctrl or 'base'}_s{seed}"
    out = XL / "ckpt" / name; out.mkdir(parents=True, exist_ok=True)

    def val_score():
        net.eval()
        if ctrl == "DIRECT":
            return k3_regression(net, k3val, dev)["succ_bce"]           # direct success head: short-sequence success BCE (K <= 3 VAL roots)
        return TR.fam_nll(TR.predict(net, va, dev))
    v0 = val_score(); best, bad, t0 = (v0, -1), 0, time.time()
    curve = [{"epoch": -1, "val": v0}]
    torch.save({"state": net.state_dict(), "epoch": -1}, out / "model.pt")
    for ep in range(rc["epochs"]):
        net.train(); tl = []
        for k in rng.permutation(len(rb)):
            items = [rp[j] for j in rb[k]] + ([loc[j] for j in rng.choice(len(loc), size=32, replace=True, p=wts)] if loc else [])
            b, lab = XY.collate([x["v"] for x in items], [x["lab"] for x in items], device=dev, dtype=torch.float32)
            Cf = net.coeffs(b)
            if ctrl == "DIRECT":
                m = lab["succ_q"] >= 0
                loss = torch.nn.functional.binary_cross_entropy_with_logits(Cf["a"][m], lab["succ_q"][m].float()) if m.any() else Cf["a"].sum() * 0
            else:
                loss = -XY.batched_log_evidence(Cf["b"], Cf["a"], Cf["w"], b["parent"], lab["y_obs"], lab["x_obs"], b["s_root"], b["n_roots"]).mean()
            if not loss.requires_grad:                                    # replay-only batch without any X query (K0 roots): no X gradient
                continue
            opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(params, 10.0); opt.step()
            tl.append(float(loss.detach()))
        vl = val_score()
        curve.append({"epoch": ep, "train": float(np.mean(tl)) if tl else None, "val": vl, "s": round(time.time() - t0, 1)})
        if vl < best[0] - 1e-5:
            best, bad = (vl, ep), 0
            torch.save({"state": net.state_dict(), "epoch": ep}, out / "model.pt")
        else:
            bad += 1
            if bad >= rc["patience"]:
                break
    net.load_state_dict(torch.load(out / "model.pt", map_location=dev, weights_only=False)["state"]); net.eval()
    assert ysha(net) == y0, "Y pathway changed"
    res = {"name": name, "dom": dom, "rep": rep, "data": dat, "recipe": recipe, "seed": int(seed), "ctrl": ctrl, "best_val": best[0], "best_epoch": best[1],
           "max_epochs": rc["epochs"], "converged_before_max": best[1] < rc["epochs"] - 1, "epochs_run": len(curve) - 1, "wall_s": round(time.time() - t0, 1),
           "trainable_params": sum(p.numel() for p in params), "y_sha": y0, "curve": curve, "k3": k3_regression(net, k3val, dev)}
    if ctrl != "DIRECT":
        res["val"] = evaluate(net, va, dev)
    res["model_sha256"] = hashlib.sha256((out / "model.pt").read_bytes()).hexdigest()
    (out / "curve.json").write_text(json.dumps(res, indent=1, default=str))
    return res


def prepare(dom):
    import train as TR
    import xy as XY
    E, rows, info = data(dom)
    tr, c1 = TR.local_views(dom, [e for e in E if e["split"] == "TRAIN"], rows)
    va, c2 = TR.local_views(dom, [e for e in E if e["split"] == "VAL"], rows)
    for v in va:                                                         # h / m on predicted rows (local_views keeps the entries)
        pass
    rp = TR.replay(dom)
    vrows = C.snapshot_rows(dom, splits=("val",), snap=C.SNAP_TRAIN)
    k3val = []
    for rid, r in sorted(vrows.items()):
        v, lab, _ = XY.root_view(r)
        k3val.append({"v": v, "lab": lab, "fam": r["parent_family_id"]})
    fz, base = TR.f0(dom)
    base = base.to("cuda").eval()
    return {"tr": tr, "va": va, "rp": rp, "k3val": k3val, "base": base, "info": {**info, "conflicts_dropped": [c1, c2], "n_train_views": len(tr), "n_val_views": len(va),
                                                                                "n_replay": len(rp), "n_k3val_roots": len(k3val)}}


def run(dom, stage, *args):
    t0 = time.time()
    D = prepare(dom)
    outp = XL / f"results_{dom}.jsonl"
    done = {r["name"] for r in jl(outp)}
    cfgs = []
    if stage == "recipe":
        cfgs = [(rep, 1, rc, 0, None) for rep in REPS for rc in ("lo", "hi")]
    elif stage == "matrix":
        sel = json.loads((XL / f"recipe_{dom}.json").read_text())
        cfgs = [(rep, dat, sel[rep], s, None) for rep in REPS for dat in (0, 1) for s in (0, 1)]
    elif stage == "controls":
        sel = json.loads((XL / f"selection_{dom}.json").read_text())
        cfgs = [(sel["rep"], 1, sel["recipe"], s, c) for c in ("ORDINV", "UNCOUPLED", "DIRECT") for s in (0, 1)]
    with open(outp, "a") as f:
        for rep, dat, rc, s, ctrl in cfgs:
            name = f"{dom}_{rep}{dat}_{rc}_{ctrl or 'base'}_s{s}"
            if name in done:
                continue
            r = fit(dom, rep, dat, rc, s, ctrl, D["tr"], D["va"], D["rp"], D["k3val"], D["base"])
            f.write(json.dumps({k: v for k, v in r.items() if k != "curve"}, default=str) + "\n"); f.flush()
            print(name, round(r["best_val"], 4), r["best_epoch"], r["wall_s"], (r.get("val") or {}).get("concordance", {}).get("concordance"), flush=True)
    (XL / f"info_{dom}.json").write_text(json.dumps(D["info"], indent=1, default=str))
    print("XL_DONE", stage, round(time.time() - t0, 1), flush=True)


def choose_recipe(dom):
    R = [r for r in jl(XL / f"results_{dom}.jsonl") if r["data"] == 1 and r["seed"] == 0 and not r["ctrl"]]
    out = {rep: min((r for r in R if r["rep"] == rep), key=lambda r: r["best_val"])["recipe"] for rep in REPS}
    (XL / f"recipe_{dom}.json").write_text(json.dumps(out)); print(out)


def select(dom):
    """Preregistered: simplest representation (A < M < G) whose seed-mean VAL NLL (data 1, chosen recipe) is within max(seed spread of the best,
    0.005) of the best seed-mean."""
    import numpy as np
    rc = json.loads((XL / f"recipe_{dom}.json").read_text())
    R = [r for r in jl(XL / f"results_{dom}.jsonl") if not r["ctrl"] and r["data"] == 1 and r["recipe"] == rc[r["rep"]]]
    m = {rep: [r["best_val"] for r in R if r["rep"] == rep] for rep in REPS}
    mean = {k: float(np.mean(v)) for k, v in m.items() if v}
    best = min(mean, key=mean.get)
    tol = max(float(np.ptp(m[best])) if len(m[best]) > 1 else 0.0, 0.005)
    pick = next(rep for rep in REPS if rep in mean and mean[rep] <= mean[best] + tol)
    out = {"rep": pick, "recipe": rc[pick], "seed_mean_val": mean, "seeds": m, "best": best, "tolerance": tol,
           "rule": "simplest within max(seed spread of best, 0.005) of best seed-mean VAL NLL"}
    (XL / f"selection_{dom}.json").write_text(json.dumps(out, indent=1)); print(out)


if __name__ == "__main__":
    a = sys.argv[1]
    {"data": lambda: data(sys.argv[2]), "run": lambda: run(*sys.argv[2:]), "recipe": lambda: choose_recipe(sys.argv[2]),
     "select": lambda: select(sys.argv[2])}[a]()
