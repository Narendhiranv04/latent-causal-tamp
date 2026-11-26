#!/usr/bin/env python3
"""R3.0 offline audit (no teacher calls): lineage / exposure and eligible pools, frozen readout decomposition (marginal pX vs conditional
pX1 / pX0 vs pY vs p11) on the natural original-VAL m <= 3 labels and on the R2.4 hard local panel, XYNet parameter dependency map, and the
GA top-Y shortlist truncation (independent of X).
    python audit.py lineage DOM        -> O/lineage_DOM.json
    python audit.py readouts DOM       -> O/readouts_DOM.json   (GPU; frozen bundle)
    python audit.py params DOM         -> O/params_DOM.json
    python audit.py shortlist          -> O/shortlist_3d.json   (GPU; 3D exposed roots, evaluator-only witness sets)"""
from __future__ import annotations

import collections, json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common3 as K  # noqa: E402
C = K.C

NB = {"3d": [(1, 4), (5, 6), (7, 9), (10, 13)], "2d": [(1, 8), (9, 12), (13, 15), (16, 30)]}


def nb(dom, n):
    return next(f"{a}-{b}" for a, b in NB[dom] if a <= n <= b)


def lineage(dom):
    rows = C.snapshot_rows(dom)
    ex = K.exposure(dom, rows)
    dev, diag = set(ex["dev_fams"]), set(ex["diag_fams"])
    pool = collections.defaultdict(lambda: collections.Counter())
    elig = {"train": [], "val": []}
    for rid, r in rows.items():
        f = r["parent_family_id"]
        st = "dev" if f in dev else "diag" if f in diag else "clean"
        pool[r["split"]][st] += 1
        if st == "clean":
            elig[r["split"]].append({"root_id": rid, "fam": f, "N": len(r["inputs"]["ids"]), "K": r["K_legacy"]})
    fams = {s: len({e["fam"] for e in v}) for s, v in elig.items()}
    byN = {s: dict(sorted(collections.Counter(nb(dom, e["N"]) for e in v).items())) for s, v in elig.items()}
    replay_drop = sum(1 for r in rows.values() if r["split"] == "train" and r["parent_family_id"] in dev)
    out = {"dom": dom, "n_rows": len(rows), "exposed_job_roots": len(ex["job_roots"]), "dev_roots": ex["dev_roots"], "dev_fams": ex["dev_fams"],
           "n_diag_fams": len(ex["diag_fams"]), "split_status": {s: dict(c) for s, c in pool.items()}, "eligible_roots": {s: len(v) for s, v in elig.items()},
           "eligible_fams": fams, "eligible_by_N": byN, "replay_train_rows_dropped_dev_lineage": replay_drop,
           "dev_in_snapshot": sorted(r for r in ex["dev_roots"] if r in rows), "eligible": elig, "diag_fams": ex["diag_fams"]}
    K.O.mkdir(parents=True, exist_ok=True)
    (K.O / f"lineage_{dom}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k not in ("eligible", "diag_fams", "dev_roots", "dev_fams")}, indent=1))


def _strata(rows, key, pk, extra=None):
    out = {}
    for name, f in [("all", lambda r: True)] + list((extra or {}).items()):
        out[name] = C.summary([r for r in rows if f(r)], key, pk, "fam")
    return out


def readouts(dom):
    """Natural VAL (non-exposed families, original X/Y labels, continuous S0 runs + terminal connector) and the R2.4 hard panel."""
    import torch
    import xy as XY
    from models import Frozen
    fz = Frozen(dom)
    rows = C.snapshot_rows(dom, splits=("val",), snap=C.SNAP_TRAIN)
    lin = json.loads((K.O / f"lineage_{dom}.json").read_text())
    diag = set(lin["diag_fams"])
    R = []
    for rid, r in rows.items():
        if r["parent_family_id"] in diag or not r["labels"]["X"]:
            continue
        v, lab, qm = XY.root_view(r)
        b, _ = XY.collate([v], device=fz.dev, dtype=torch.float32)
        with torch.inference_mode():
            Cf = fz.net.coeffs(b)
        bb, a, w = Cf["b"].double().cpu(), Cf["a"].double().cpu(), Cf["w"].double().cpu()
        for q in range(len(v["x_seqs"])):
            s = v["parent"][q]
            py, p1, p0 = torch.sigmoid(bb[s]).item(), torch.sigmoid(a[q] + w[q]).item(), torch.sigmoid(a[q]).item()
            R.append({"fam": r["parent_family_id"], "root": rid, "N": len(r["inputs"]["ids"]), "m": len(v["x_seqs"][q]), "x": lab["obs_x"].get(q),
                      "y": lab["obs_y"].get(s), "px": py * p1 + (1 - py) * p0, "px1": p1, "px0": p0, "py": py, "p11": py * p1,
                      "a": float(a[q]), "w": float(w[q])})
    for r in R:
        r["z"] = None if r["x"] is None or r["y"] is None else int(r["x"] == 1 and r["y"] == 1)
    ms = {f"m{m}": (lambda r, m=m: r["m"] == m) for m in (1, 2, 3)}
    ns = {f"N{b}": (lambda r, b=b: nb(dom, r["N"]) == b) for b in sorted({nb(dom, r["N"]) for r in R})}
    nat = {"marginal_px_vs_x": _strata(R, "x", "px", {**ms, **ns}),
           "px1_vs_x_given_y1": _strata([r for r in R if r["y"] == 1], "x", "px1", ms),
           "px0_vs_x_given_y0": _strata([r for r in R if r["y"] == 0], "x", "px0", ms),
           "px1_vs_x_all": _strata(R, "x", "px1"), "px0_vs_x_all": _strata(R, "x", "px0"),
           "p11_vs_z": _strata(R, "z", "p11", ms), "py_vs_y": _strata([r for r in R if r["y"] is not None], "y", "py")}
    nat["mean_py_x_labels"] = sum(r["py"] for r in R if r["x"] is not None) / max(1, sum(r["x"] is not None for r in R))
    # hard panel: R2.4 local chunk labels (exposed development roots; diagnostics only)
    H = []
    for l in open(C.FIG3 / "r24" / f"labels_{dom}.jsonl"):
        e = json.loads(l)
        if e["t"] == "chunk" and e["label"] in (0, 1) and e.get("px") is not None:
            e["fam"] = e["root_id"]; H.append(e)
    hs = {"h0": lambda r: r["h"] == 0, "h>=1": lambda r: r["h"] >= 1, "h0_m1": lambda r: r["h"] == 0 and r["m"] == 1,
          "h>=1_m1": lambda r: r["h"] >= 1 and r["m"] == 1, "h>=1_m23": lambda r: r["h"] >= 1 and r["m"] >= 2}
    hard = {k: _strata(H, "label", k, hs) for k in ("px", "px1", "px0", "py", "p11")}
    conf = [r for r in H if r["label"] == 0 and r["px"] >= 0.8]
    hard["confident_negatives"] = {"n": len(conf), "n_neg": sum(r["label"] == 0 for r in H),
                                   "median_px1": _med([r["px1"] for r in conf]), "median_px0": _med([r["px0"] for r in conf]),
                                   "median_py": _med([r["py"] for r in conf]), "both_logits_high": sum(r["px1"] >= 0.8 and r["px0"] >= 0.8 for r in conf),
                                   "mixture_only": sum((r["px1"] >= 0.8) != (r["px0"] >= 0.8) for r in conf)}
    out = {"dom": dom, "natural_val": {"n": len(R), "roots": len({r["root"] for r in R}), "fams": len({r["fam"] for r in R}), **nat}, "hard_r24": hard}
    (K.O / f"readouts_{dom}.json").write_text(json.dumps(out, indent=1))
    with open(K.O / f"readouts_natural_{dom}.jsonl", "w") as f:
        for r in R:
            f.write(json.dumps(r) + "\n")
    s = lambda d: {k: (round(v["auroc"], 3) if v.get("auroc") is not None else None, v.get("n"), v.get("mixed_families")) for k, v in d.items()}  # noqa: E731
    print(json.dumps({"nat_px": s(nat["marginal_px_vs_x"]), "nat_px1|y1": s(nat["px1_vs_x_given_y1"]), "nat_px0|y0": s(nat["px0_vs_x_given_y0"]),
                      "hard_px": s(hard["px"]), "hard_px1": s(hard["px1"]), "hard_px0": s(hard["px0"]), "conf": hard["confident_negatives"]}, indent=0))


def _med(v):
    v = sorted(v)
    return v[len(v) // 2] if v else None


def params(dom):
    """Autograd map: which XYNet modules carry gradient to Y logits b and to X coefficients a, w (on one real 3D / 2D root)."""
    import torch
    import xy as XY
    from models import Frozen
    fz = Frozen(dom)
    net = fz.net.float()
    rows = C.snapshot_rows(dom, splits=("val",), snap=C.SNAP_TRAIN)
    r = next(r for r in rows.values() if len(r["labels"]["X"]) >= 3 and max(len(q["seq"]) for q in r["labels"]["X"]) >= 2)
    v, lab, _ = XY.root_view(r)
    b, _ = XY.collate([v], device=fz.dev, dtype=torch.float32)
    mods = sorted({n.split(".")[0] for n, _ in net.named_parameters()})
    dep = {}
    for out in ("b", "a", "w", "J"):
        net.zero_grad(set_to_none=True)
        with torch.enable_grad():
            Cf = net.coeffs(b)
            Cf[out].sum().backward()
        dep[out] = sorted({n.split(".")[0] for n, p in net.named_parameters() if p.grad is not None and float(p.grad.abs().sum()) > 0})
    x_only = sorted((set(dep["a"]) | set(dep["w"])) - set(dep["b"]))
    shared = sorted((set(dep["a"]) | set(dep["w"])) & set(dep["b"]))
    n = lambda ms: sum(p.numel() for k, p in net.named_parameters() if k.split(".")[0] in ms)  # noqa: E731
    out = {"dom": dom, "arm": net.arm, "modules": mods, "grad_to": dep, "x_only_modules": x_only, "shared_x_y_modules": shared,
           "y_only_modules": sorted(set(dep["b"]) - set(dep["a"]) - set(dep["w"])), "inactive": sorted(set(mods) - set().union(*dep.values())),
           "params": {"total": n(mods), "x_only": n(x_only), "shared": n(shared)}, "probe_root": r["root_id"]}
    (K.O / f"params_{dom}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


def shortlist():
    """GA truncation independent of X: rank of the (evaluator-only) verified witness SET by Y_global among same-size enumerated sets of the
    R2.4 GA-UNION union pool; is it inside the top PER_SIZE shortlist?"""
    import arms as AR
    from models import Frozen
    fz = Frozen("3d"); fz.caps = {}
    oracle = json.loads((C.FIG3 / "r24" / "oracle_3d.json").read_text())
    dep = {json.loads(l)["root_id"]: json.loads(l) for l in open(C.FIG3 / "r24" / "deploy_3d.jsonl")}
    rows = {json.loads(l)["root_id"]: json.loads(l) for l in open(C.R2 / "r23" / "roster_3d.jsonl")}
    out = {}
    for rid, o in oracle.items():
        A = tuple(sorted(tuple(map(int, a)) for a in o["A-DP"]["order"]))
        D = {}
        for ob, d in dep[rid]["GA-UNION"]["union_actions"]:
            D.setdefault(int(ob), []).append(int(d))
        inpool = all(d in D.get(ob, []) for ob, d in A)
        yA = fz.y_global(rows[rid], [list(map(list, A))])[0]
        log = {"assign": []}
        sc = AR.enum_sets(fz, rows[rid], D, len(A), log) if inpool else {}
        same = sorted((y for S, y in sc.items() if len(S) == len(A)), reverse=True)
        rank = 1 + sum(y > yA for y in same) if inpool else None
        out[rid] = {"m": len(A), "in_union_pool": inpool, "y_global_witness_set": yA, "rank_by_y": rank, "n_same_size": len(same),
                    "in_top_per_size": bool(rank and rank <= AR.PER_SIZE), "enum": log["assign"]}
    (K.O / "shortlist_3d.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: {a: v.get(a) for a in ("m", "in_union_pool", "rank_by_y", "n_same_size", "y_global_witness_set")} for k, v in out.items()}, indent=0))


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"lineage": lambda: lineage(sys.argv[2]), "readouts": lambda: readouts(sys.argv[2]), "params": lambda: params(sys.argv[2]),
     "shortlist": shortlist}[cmd]()
