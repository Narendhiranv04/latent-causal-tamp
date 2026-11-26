#!/usr/bin/env python3
"""R3.2 / R3.3 local validation gate + K<=3 regression (preregistered in R3_PREREG.json R3_2.local_gate / k3_regression).
    python evaluate.py gate DOM ARM SEED [ARM SEED ...]   -> O/eval/DOM_ARM_sSEED.json (+ per-label predictions)"""
from __future__ import annotations

import collections, json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common3 as K  # noqa: E402
import train as TR  # noqa: E402
C = K.C

STRATA = {"all": lambda e: True, "h0": lambda e: e["h"] == 0, "h>=1": lambda e: e["h"] >= 1, "h0_m1": lambda e: e["h"] == 0 and e["m"] == 1,
          "h0_m23": lambda e: e["h"] == 0 and e["m"] >= 2, "h>=1_m1": lambda e: e["h"] >= 1 and e["m"] == 1, "h>=1_m23": lambda e: e["h"] >= 1 and e["m"] >= 2,
          "m1": lambda e: e["m"] == 1, "m2": lambda e: e["m"] == 2, "m3": lambda e: e["m"] == 3, "S0": lambda e: e.get("scene_type") == "S0",
          "HYPSTART": lambda e: e.get("scene_type") == "HYPSTART", "N5-6": lambda e: e["N"] <= 6, "N7-9": lambda e: e["N"] >= 7}


def fpr_at_tpr(P, key, tpr=0.8):
    pos = sorted((e[key] for e in P if e["label"] == 1), reverse=True)
    neg = [e[key] for e in P if e["label"] == 0]
    if not pos or not neg:
        return None
    thr = pos[max(0, math.ceil(tpr * len(pos)) - 1)]
    return {"threshold": thr, "tpr": sum(p >= thr for p in pos) / len(pos), "fpr": sum(n >= thr for n in neg) / len(neg),
            "fpr_at_0.5": sum(n >= 0.5 for n in neg) / len(neg), "tpr_at_0.5": sum(p >= 0.5 for p in pos) / len(pos), "n_pos": len(pos), "n_neg": len(neg)}


def paired(P0, P1, f, B=2000, seed=0):
    """AUROC(model) - AUROC(F0) on the same labels with family-cluster bootstrap."""
    import numpy as np
    S = [(a, b) for a, b in zip(P0, P1) if f(a)]
    by = collections.defaultdict(list)
    for a, b in S:
        by[a["fam"]].append((a, b))
    fams = sorted(by)
    def d(items):
        y = [a["label"] for a, _ in items]
        u, v = C.auroc(y, [b["px"] for _, b in items]), C.auroc(y, [a["px"] for a, _ in items])
        return None if u is None or v is None else u - v
    pt = d(S)
    rng = np.random.default_rng(seed); vals = []
    for _ in range(B):
        it = [x for k in rng.choice(fams, len(fams)) for x in by[k]]
        x = d(it)
        if x is not None:
            vals.append(x)
    ci = [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))] if len(vals) > B / 2 else None
    return {"delta": pt, "ci95": ci, "n": len(S), "fams": len(fams)}


def concord(P):
    """Within (scene, unordered set) groups: executable vs non-executable permutations (T4/T5 matched endpoints)."""
    g = collections.defaultdict(list)
    for e in P:
        g[(e["root_id"], json.dumps(TR.canon(e["base"] + e["prefix"])), json.dumps(TR.canon(e["chunk"])))].append((e["label"], e["px"]))
    return C.concordance([v for v in g.values() if len(v) > 1])


def natural(net, dom, dev="cuda"):
    """K<=3 regression on NATURAL_VAL (original v32 VAL labels, non-exposed families): marginal pX vs x, p11 vs z, pY vs y, max |delta b| vs F0."""
    import torch
    import xy as XY
    lin = json.loads((K.O / f"lineage_{dom}.json").read_text())
    diag = set(lin["diag_fams"])
    rows = C.snapshot_rows(dom, splits=("val",), snap=C.SNAP_TRAIN)
    items = []
    for rid, r in sorted(rows.items()):
        if r["parent_family_id"] in diag:
            continue
        v, lab, _ = XY.root_view(r)
        items.append({"v": v, "lab": lab, "fam": r["parent_family_id"]})
    R, B = [], []
    with torch.no_grad():
        for i in range(0, len(items), 256):
            ch = items[i:i + 256]
            b, _ = XY.collate([c["v"] for c in ch], device=dev, dtype=torch.float32)
            Cf = net.coeffs(b)
            bb, a, w = Cf["b"].double().cpu(), Cf["a"].double().cpu(), Cf["w"].double().cpu()
            B.append(bb)
            qo = so = 0
            for c in ch:
                v, l = c["v"], c["lab"]
                for q in range(len(v["x_seqs"])):
                    s = so + v["parent"][q]
                    py, p1, p0 = torch.sigmoid(bb[s]).item(), torch.sigmoid(a[qo + q] + w[qo + q]).item(), torch.sigmoid(a[qo + q]).item()
                    x, y = l["obs_x"].get(q), l["obs_y"].get(v["parent"][q])
                    R.append({"fam": c["fam"], "x": x, "y": y, "z": None if x is None or y is None else int(x == 1 and y == 1), "m": len(v["x_seqs"][q]),
                              "px": py * p1 + (1 - py) * p0, "p11": py * p1, "py": py})
                qo += len(v["x_seqs"]); so += len(v["y_xy"])
    return R, torch.cat(B)


def gate(dom, specs):
    import torch
    rows = C.snapshot_rows(dom, snap=C.SNAP_TRAIN)
    L = TR.load_labels(dom)
    va, conf = TR.local_views(dom, [e for e in L if e["split"] == "VAL_SCALE"], rows)
    fz, base = TR.f0(dom)
    base = base.to("cuda").eval()
    P0 = TR.predict(base, va, "cuda")
    N0, b0 = natural(base, dom)
    od = K.O / "eval"; od.mkdir(parents=True, exist_ok=True)
    res = {}
    models = [("F0", None, base)] + [(a, s, TR.load(dom, a, s)[1]) for a, s in zip(specs[::2], specs[1::2])]
    for arm, seed, net in models:
        P = P0 if arm == "F0" else TR.predict(net, va, "cuda")
        key = lambda e: (e["key"], json.dumps(e["prefix"]), json.dumps(e["chunk"]))  # noqa: E731
        m1 = {key(e): e for e in P}
        P1 = [m1[key(e)] for e in P0]
        st = {k: C.summary([e for e in P1 if f(e)], "label", "px", "fam") for k, f in STRATA.items()}
        out = {"arm": arm, "seed": seed, "n_labels": len(P1), "val_conflicts_dropped": conf, "strata": st,
               "strata_px1": {k: C.summary([e for e in P1 if STRATA[k](e)], "label", "px1", "fam") for k in ("h0", "h>=1")},
               "fpr_first_relocation": fpr_at_tpr([e for e in P1 if STRATA["h0_m1"](e)], "px"),
               "concordance_matched_permutations": concord(P1), "val_fam_nll": TR.fam_nll(P1)}
        if arm != "F0":
            out["paired_vs_F0"] = {k: paired(P0, P1, STRATA[k]) for k in ("all", "h0", "h>=1", "h0_m1", "h>=1_m23")}
        N, bm = natural(net, dom) if arm != "F0" else (N0, b0)
        out["natural_val"] = {"px_vs_x": C.summary(N, "x", "px", "fam"), "p11_vs_z": C.summary(N, "z", "p11", "fam"), "py_vs_y": C.summary(N, "y", "py", "fam"),
                              "p11_vs_z_m3": C.summary([e for e in N if e["m"] == 3], "z", "p11", "fam"), "max_abs_delta_b_vs_F0": float((bm - b0).abs().max())}
        if arm != "F0":
            out["natural_val"]["paired_p11_auroc_vs_F0"] = paired([{**a, "label": a["z"], "px": a["p11"]} for a in N0 if a["z"] is not None],
                                                                    [{**a, "label": a["z"], "px": a["p11"]} for a in N if a["z"] is not None], lambda e: True)
        ok = lambda s: s.get("auroc") is not None  # noqa: E731
        h1, h0 = st["h>=1"], st["h0"]
        f0r, fmr = res.get("F0", {}).get("fpr_first_relocation"), out["fpr_first_relocation"]
        out["gate"] = {"support_h0_mixed": h0.get("mixed_families", 0), "support_h1_mixed": h1.get("mixed_families", 0),
                       "support_ok": h0.get("mixed_families", 0) >= 10 and h1.get("mixed_families", 0) >= 10,
                       "h1_auroc": h1.get("auroc"), "h1_ci": h1.get("auroc_ci"),
                       "h1_pass": ok(h1) and h1["auroc"] >= 0.75 and bool(h1.get("auroc_ci")) and h1["auroc_ci"][0] >= 0.60,
                       "paired_pass": arm != "F0" and bool(out["paired_vs_F0"]["h>=1"]["ci95"]) and out["paired_vs_F0"]["h>=1"]["ci95"][0] > 0,
                       "fpr_drop": (f0r["fpr"] - fmr["fpr"]) if f0r and fmr else None}
        g = out["gate"]
        g["fpr_pass"] = g["fpr_drop"] is not None and g["fpr_drop"] >= 0.15
        g["PASS"] = bool(g["support_ok"] and g["h1_pass"] and g["paired_pass"] and g["fpr_pass"])
        res[arm if arm == "F0" else f"{arm}_s{seed}"] = out
        with open(od / f"pred_{dom}_{arm}_s{seed}.jsonl", "w") as f:
            for e in P1:
                f.write(json.dumps({k: e[k] for k in ("root_id", "fam", "h", "m", "N", "scene_type", "template", "label", "px", "px1", "px0", "py", "chunk", "prefix", "base", "kind")}) + "\n")
    (od / f"gate_{dom}.json").write_text(json.dumps(res, indent=1))
    for k, o in res.items():
        g = o["gate"]; s = o["strata"]
        print(k, json.dumps({"h0": [round(s["h0"].get("auroc") or 0, 3), s["h0"].get("auroc_ci")], "h>=1": [round(g["h1_auroc"] or 0, 3), g["h1_ci"]],
                             "h>=1_m23": round(s["h>=1_m23"].get("auroc") or 0, 3), "mixed": [g["support_h0_mixed"], g["support_h1_mixed"]],
                             "paired_h1": o.get("paired_vs_F0", {}).get("h>=1"), "fpr": o["fpr_first_relocation"], "fpr_drop": g["fpr_drop"],
                             "conc": o["concordance_matched_permutations"], "nat_p11": round(o["natural_val"]["p11_vs_z"]["auroc"], 3),
                             "nat_px": round(o["natural_val"]["px_vs_x"]["auroc"], 3), "dB": o["natural_val"]["max_abs_delta_b_vs_F0"], "PASS": g["PASS"]}, default=str))


def hard(dom, specs):
    """DIAGNOSTIC ONLY (exposed DEV roots; never used for selection): marginal pX AUROC on the R2.4 exact local panel per model."""
    rows = dict(C.snapshot_rows(dom, snap=C.SNAP_TRAIN))
    rows.update({json.loads(l)["root_id"]: json.loads(l) for l in open(C.R2 / "r23" / f"roster_{dom}.jsonl")})
    H = [json.loads(l) for l in open(C.FIG3 / "r24" / f"labels_{dom}.jsonl")]
    H = [{**e, "fam": e["root_id"], "base": [], "N": len(rows[e["root_id"]]["inputs"]["ids"]), "scene_type": "DEV"} for e in H if e["t"] == "chunk" and e["label"] in (0, 1)]
    va, _ = TR.local_views(dom, H, rows)
    fz, base = TR.f0(dom)
    models = [("F0", None, base.to("cuda").eval())] + [(a, s, TR.load(dom, a, s)[1]) for a, s in zip(specs[::2], specs[1::2])]
    out = {}
    for arm, seed, net in models:
        P = TR.predict(net, va, "cuda")
        out[f"{arm}_s{seed}"] = {k: C.summary([e for e in P if STRATA[k](e)], "label", "px", "fam") for k in ("all", "h0", "h>=1", "h0_m1", "h>=1_m23")}
        out[f"{arm}_s{seed}"]["fpr_first_relocation"] = fpr_at_tpr([e for e in P if STRATA["h0_m1"](e)], "px")
    (K.O / "eval" / f"hard_{dom}.json").write_text(json.dumps(out, indent=1))
    for k, v in out.items():
        print(k, {s: (round(v[s]["auroc"], 3) if v[s].get("auroc") is not None else None, [round(x, 2) for x in (v[s].get("auroc_ci") or [])]) for s in ("all", "h0", "h>=1", "h0_m1", "h>=1_m23")},
              "fpr", round(v["fpr_first_relocation"]["fpr"], 3))


def diag2d():
    """Preregistered 2D frozen-X decision (R3_1_2d.decision) on the union of the R2.4 2D panel and the R3.1 diagnostic panel, h >= 1."""
    A = [json.loads(l) for l in open(K.O / "labels_31_2d.jsonl")]
    A = [{**e, "px": e["f0_px"], "panel": "R3.1"} for e in A if e["label"] in (0, 1)]
    B = [json.loads(l) for l in open(C.FIG3 / "r24" / "labels_2d.jsonl")]
    B = [{**e, "fam": e["root_id"], "panel": "R2.4"} for e in B if e["t"] == "chunk" and e["label"] in (0, 1) and e.get("px") is not None]
    U = A + B
    res = {k: {p: C.summary([e for e in S if f(e)], "label", "px", "fam") for p, S in (("union", U), ("R3.1", A), ("R2.4", B))}
           for k, f in (("h>=1", STRATA["h>=1"]), ("h0", STRATA["h0"]), ("h0_m1", STRATA["h0_m1"]), ("h>=1_m23", STRATA["h>=1_m23"]))}
    u = res["h>=1"]["union"]
    ci = u.get("auroc_ci")
    if u.get("mixed_families", 0) < 10 or u.get("auroc") is None:
        dec = "INCONCLUSIVE_SUPPORT"
    elif u["auroc"] >= 0.75 and ci and ci[0] >= 0.60:
        dec = "PASS"
    elif ci and ci[1] < 0.70:
        dec = "DEFICIT"
    else:
        dec = "INCONCLUSIVE"
    jobs = json.loads((K.O / "jobs_31_2d.json").read_text())
    R = [json.loads(l) for l in open(K.O / "phys_31_2d.jsonl")]
    st = collections.Counter(str((r.get("X") or {}).get("teacher_status")) + "@" + str((r.get("X") or {}).get("failed_phase")) for r in R)
    out = {"decision": dec, "strata": res, "n_jobs": len(R), "n_sealed": len(jobs), "cpu_h": sum(r.get("cpu_s", 0) for r in R) / 3600, "statuses": dict(st),
           "labels_r31": collections.Counter(f"h{min(e['h'], 1)}_y{e['label']}" for e in A)}
    (K.O / "diag2d.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"decision": dec, "h>=1": {p: (v.get("auroc"), v.get("auroc_ci"), v.get("n"), v.get("pos"), v.get("mixed_families")) for p, v in res["h>=1"].items()},
                      "h0": {p: (v.get("auroc"), v.get("n"), v.get("mixed_families")) for p, v in res["h0"].items()}, "labels": out["labels_r31"], "statuses": dict(st), "cpu_h": out["cpu_h"]}, default=str))


# ======================================================================================================== R3.3A (addendum A2)
S33 = {**STRATA, "h>=1_m1": STRATA["h>=1_m1"], "S0_h0": lambda e: e["h"] == 0 and e["scene_type"] == "S0",
       "static_h0": lambda e: e["h"] == 0 and e["scene_type"] in ("HYPSTART", "DENSE"), "HYPSTART_h0": lambda e: e["h"] == 0 and e["scene_type"] == "HYPSTART",
       "DENSE_h0": lambda e: e["h"] == 0 and e["scene_type"] == "DENSE", "reached_h1_from_S0": lambda e: e["h"] >= 1 and e["scene_type"] == "S0",
       "reached_h1_from_static": lambda e: e["h"] >= 1 and e["scene_type"] != "S0"}
PANELS = {"ORIG_VAL_SCALE": lambda e: e["panel"] == "ORIG", "NEW_ORD": lambda e: e["panel"] == "ORD", "NEW_DENSE": lambda e: e["panel"] == "DENSE",
          "NEW": lambda e: e["panel"] in ("ORD", "DENSE"), "POOLED": lambda e: True}


def components(st, pr, f0r, fmr):
    """The ORIGINAL R3_2.local_gate (unchanged thresholds) on one panel."""
    h1, h0 = st["h>=1"], st["h0"]
    g = {"support_h0_mixed": h0.get("mixed_families", 0), "support_h1_mixed": h1.get("mixed_families", 0),
         "support_ok": h0.get("mixed_families", 0) >= 10 and h1.get("mixed_families", 0) >= 10, "h1_auroc": h1.get("auroc"), "h1_ci": h1.get("auroc_ci"),
         "h1_pass": h1.get("auroc") is not None and h1["auroc"] >= 0.75 and bool(h1.get("auroc_ci")) and h1["auroc_ci"][0] >= 0.60,
         "paired_h1": pr, "paired_pass": bool(pr and pr["ci95"]) and pr["ci95"][0] > 0,
         "fpr_drop": (f0r["fpr"] - fmr["fpr"]) if f0r and fmr else None}
    g["fpr_pass"] = g["fpr_drop"] is not None and g["fpr_drop"] >= 0.15
    g["PASS"] = bool(g["support_ok"] and g["h1_pass"] and g["paired_pass"] and g["fpr_pass"])
    return g


def gate33a(specs):
    rows = C.snapshot_rows("3d", snap=C.SNAP_TRAIN)
    L = [{**e, "panel": "ORIG"} for e in TR.load_labels("3d") if e["split"] == "VAL_SCALE"]
    L += [{**e, "panel": e["stratum"]} for e in (json.loads(l) for l in open(K.O / "labels_33a_3d.jsonl"))]
    va, conf = TR.local_views("3d", L, rows)
    fz, base = TR.f0("3d")
    nets = [("F0", None, base.to("cuda").eval())] + [(a, s, TR.load("3d", a, s)[1]) for a, s in zip(specs[::2], specs[1::2])]
    key = lambda e: (e["key"], json.dumps(e["prefix"]), json.dumps(e["chunk"]))  # noqa: E731
    P = {}
    for arm, seed, net in nets:
        m = {key(e): e for e in TR.predict(net, va, "cuda")}
        P[arm if arm == "F0" else f"{arm}_s{seed}"] = m
    ks = sorted(P["F0"])
    od = K.O / "eval"; od.mkdir(parents=True, exist_ok=True)
    thr0 = {}
    res = {"labels": len(ks), "val_conflicts_dropped": conf, "panels": {}}
    for pn, pf in PANELS.items():
        R = {}
        for tag in P:
            X = [P[tag][k] for k in ks if pf(P[tag][k])]
            X0 = [P["F0"][k] for k in ks if pf(P["F0"][k])]
            st = {k: C.summary([e for e in X if f(e)], "label", "px", "fam") for k, f in S33.items()}
            fr = fpr_at_tpr([e for e in X if STRATA["h0_m1"](e)], "px")
            if pn == "ORIG_VAL_SCALE" and fr:
                thr0[tag] = fr["threshold"]
            neg = [e["px"] for e in X if STRATA["h0_m1"](e) and e["label"] == 0]; pos = [e["px"] for e in X if STRATA["h0_m1"](e) and e["label"] == 1]
            frz = {"threshold_from_ORIG": thr0.get(tag), "fpr": sum(v >= thr0[tag] for v in neg) / len(neg) if neg and tag in thr0 else None,
                   "tpr": sum(v >= thr0[tag] for v in pos) / len(pos) if pos and tag in thr0 else None}
            o = {"strata": st, "fpr_first_relocation": fr, "fpr_first_relocation_frozen_ORIG_threshold": frz, "concordance_matched_permutations": concord(X),
                 "fam_nll": TR.fam_nll(X) if X else None}
            if tag != "F0":
                o["paired_vs_F0"] = {k: paired(X0, X, S33[k]) for k in ("all", "h0", "h>=1", "h0_m1", "h>=1_m1", "h>=1_m23", "static_h0", "DENSE_h0")}
                o["gate"] = components(st, o["paired_vs_F0"]["h>=1"], R["F0"]["fpr_first_relocation"], fr)
            R[tag] = o
        res["panels"][pn] = R
    sel = next(t for t in P if t.startswith("G1s"))
    Pp, Pn, Pd = (res["panels"][k][sel] for k in ("POOLED", "NEW", "NEW_DENSE"))
    g = dict(Pp["gate"])
    g["guard_new_paired_point_gt0"] = (Pn["paired_vs_F0"]["h>=1"]["delta"] or 0) > 0
    g["guard_new_fpr_drop_gt0"] = (Pn["gate"]["fpr_drop"] or 0) > 0
    g["R3_3A_PASS"] = bool(g["PASS"] and g["guard_new_paired_point_gt0"] and g["guard_new_fpr_drop_gt0"])
    failed = [c for c in ("paired_pass", "fpr_pass", "guard_new_paired_point_gt0", "guard_new_fpr_drop_gt0") if not g[c]]
    g["narrow"] = bool(g["support_ok"] and g["h1_pass"] and len(failed) == 1)
    dp = Pd["paired_vs_F0"]["h>=1"]
    g["dense_support_h1_mixed"] = Pd["strata"]["h>=1"].get("mixed_families", 0)
    g["dense_paired_h1"] = dp
    g["dense_supports"] = bool(g["dense_support_h1_mixed"] >= 10 and dp["ci95"] and dp["ci95"][0] > 0)
    g["R3_4_MODE"] = "FORMAL" if g["R3_3A_PASS"] else "DIAGNOSTIC_ONLY" if (g["narrow"] and g["dense_supports"]) else "NOT_AUTHORIZED"
    g["failed_components"] = failed
    res["decision"] = {"selected": sel, **g}
    (od / "gate33a_3d.json").write_text(json.dumps(res, indent=1, default=str))
    with open(od / "pred33a_3d.jsonl", "w") as f:
        for k in ks:
            e = P["F0"][k]
            f.write(json.dumps({**{c: e[c] for c in ("root_id", "fam", "panel", "h", "m", "N", "scene_type", "template", "label", "chunk", "prefix", "base", "kind", "key")},
                                **{f"px_{t}": P[t][k]["px"] for t in P}}) + "\n")
    for pn in PANELS:
        for t, o in res["panels"][pn].items():
            st = o["strata"]
            print(pn, t, json.dumps({"h0": [st["h0"].get("auroc"), st["h0"].get("mixed_families")], "h>=1": [st["h>=1"].get("auroc"), st["h>=1"].get("auroc_ci"), st["h>=1"].get("mixed_families")],
                                     "fpr": (o["fpr_first_relocation"] or {}).get("fpr"), "paired_h1": (o.get("paired_vs_F0") or {}).get("h>=1"),
                                     "PASS": (o.get("gate") or {}).get("PASS")}, default=str))
    print("DECISION", json.dumps(res["decision"], default=str))


def diag2dd():
    """Preregistered 2D frozen-X decision (A2): R3_1_2d.decision rule on the union of R2.4 + R3.1 + R3.1D panels at h >= 1; R3.1D alone reported."""
    D = [json.loads(l) for l in open(K.O / "labels_31d_2d.jsonl")]
    D = [{**e, "px": e["f0_px"], "panel": "R3.1D"} for e in D if e["label"] in (0, 1)]
    A = [json.loads(l) for l in open(K.O / "labels_31_2d.jsonl")]
    A = [{**e, "px": e["f0_px"], "panel": "R3.1"} for e in A if e["label"] in (0, 1)]
    B = [json.loads(l) for l in open(C.FIG3 / "r24" / "labels_2d.jsonl")]
    B = [{**e, "fam": e["root_id"], "panel": "R2.4"} for e in B if e["t"] == "chunk" and e["label"] in (0, 1) and e.get("px") is not None]
    U = D + A + B
    res = {k: {p: C.summary([e for e in S if f(e)], "label", "px", "fam") for p, S in (("union", U), ("R3.1D", D), ("R3.1", A), ("R2.4", B))}
           for k, f in (("h>=1", STRATA["h>=1"]), ("h0", STRATA["h0"]), ("h>=1_m1", STRATA["h>=1_m1"]), ("h>=1_m23", STRATA["h>=1_m23"]))}
    def dec(u):
        ci = u.get("auroc_ci")
        if u.get("mixed_families", 0) < 10 or u.get("auroc") is None:
            return "INCONCLUSIVE_SUPPORT"
        if u["auroc"] >= 0.75 and ci and ci[0] >= 0.60:
            return "PASS"
        return "DEFICIT" if ci and ci[1] < 0.70 else "INCONCLUSIVE"
    jobs = json.loads((K.O / "jobs_31d_2d.json").read_text())
    R = {json.loads(l)["key"]: json.loads(l) for l in open(K.O / "phys_31d_2d.jsonl")}
    st = collections.Counter(str((r.get("X") or {}).get("teacher_status")) + "@" + str((r.get("X") or {}).get("failed_phase")) for r in R.values())
    pre = collections.Counter(f"label={e['label']}" for e in (json.loads(l) for l in open(K.O / "labels_31d_2d.jsonl"))
                              if e["template"] in ("Q1", "Q2", "Q3") and e["h"] == 0)   # established prefix p re-run as chunk 0 (x = 1 expected)
    out = {"decision_union": dec(res["h>=1"]["union"]), "decision_R3.1D_alone": dec(res["h>=1"]["R3.1D"]), "strata": res, "n_jobs": len(R),
           "n_sealed": len(jobs), "cpu_h": sum(r.get("cpu_s", 0) for r in R.values()) / 3600, "statuses": dict(st), "prefix_reproduction": dict(pre),
           "labels_R3.1D": collections.Counter(f"h{min(e['h'], 1)}_y{e['label']}" for e in D)}
    (K.O / "diag2dd.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("decision_union", "decision_R3.1D_alone", "statuses", "prefix_reproduction", "labels_R3.1D", "cpu_h")}, default=str))
    print(json.dumps({p: (v.get("auroc"), v.get("auroc_ci"), v.get("n"), v.get("pos"), v.get("mixed_families")) for p, v in res["h>=1"].items()}, default=str))


if __name__ == "__main__":
    if sys.argv[1] == "gate33a":
        gate33a(sys.argv[2:])
    elif sys.argv[1] == "diag2dd":
        diag2dd()
    elif sys.argv[1] == "gate":
        gate(sys.argv[2], sys.argv[3:])
    elif sys.argv[1] == "hard":
        hard(sys.argv[2], sys.argv[3:])
    elif sys.argv[1] == "diag2d":
        diag2d()
