#!/usr/bin/env python3
"""Shared core of the repair-ranking study (plan.md v1.0): paths, family partition, read-only X/Y readout, frozen cVAE ranks, strict labels.

Planner-side helpers (readout, cvae, root objects) take PUBLIC inputs only; label helpers (strict_labels, train_items) are evaluator / training
side and are never imported by run_eval.py.  Nothing here edits xy.py, search.py, the bundle, the snapshot or a completed study."""
from __future__ import annotations

import collections, gzip, hashlib, json, math, os, pickle, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ABF = HERE.parent
for p in (str(ABF), str(ABF / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)
H = Path.home()
SNAP = Path(os.environ.get("RR_SNAP", H / "abf_v32/snap_out/snapshot/abf_v32_fb0eef4f5ff433ee"))
PUB_VAL = Path(os.environ.get("RR_PUB", H / "abf_v34/parity/public_val_2d.jsonl"))
BUNDLE = Path(os.environ.get("RR_BUNDLE", H / "abf_v34/approach_b_bundle"))
PRIV = Path(os.environ.get("RR_PRIV", H / "xyrr_private"))           # private (labels, manifests, caches): never committed
OUT = Path(os.environ.get("RR_OUT", H / "xyrr_runs"))                # large derived artifacts (readouts, checkpoints)
PRIV_VAL = H / "mcts_sets_private/k3abl/private_val_2d.jsonl"
CACHES = [H / "mcts_sets_private/k3abl/verify_2d.jsonl", H / "mcts_sets_private/k3val/verify_2d.jsonl",
          H / "mcts_sets_private/mcts/verify_2d.jsonl", H / "fds_private/fds/verify_2d.jsonl"]
GENLAB = H / "fds_private/genlab_val_2d.jsonl"
FDS_REP = ABF / "full_domain_sets/reports"
REP = HERE / "reports"
RULE = {"noop_gate": 0.5, "eta": 0.3, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}


def jl(p):
    op = gzip.open if str(p).endswith(".gz") else open
    with op(p, "rt") as f:
        return [json.loads(l) for l in f if l.strip()]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def wjson(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, indent=1, sort_keys=False, default=str) + "\n")


def hx(tag, s):
    return int(hashlib.sha256((tag + s).encode()).hexdigest(), 16)


# ------------------------------------------------------------------------------------------------------------- data partition (family level)
def snapshot_rows(split=None):
    rows = jl(SNAP / "data2d.jsonl")
    return [r for r in rows if split is None or r["split"] == split]


def dev_part(family):
    """DEV_CAL / DEV_AUDIT by parent family (50 / 50 on sha256('XYRR_DEV|'+family)); every sibling of a family stays on one side."""
    return "DEV_CAL" if hx("XYRR_DEV|", family) % 2 == 0 else "DEV_AUDIT"


def val_meta():
    """root_id -> {K, family, part} for the 751 old VAL roots (K evaluator-side only)."""
    fam = {r["root_id"]: r["parent_family_id"] for r in snapshot_rows("val")}
    K = {e["root_id"]: str(e["K"]) for e in jl(PRIV_VAL)}
    return {rid: {"K": K[rid], "family": f, "part": dev_part(f)} for rid, f in fam.items()}


def public_val():
    return [r for r in jl(PUB_VAL) if r["domain"] == "2d"]


# ------------------------------------------------------------------------------------------------------------- models
def bundle(device="cuda", seed=0):
    import benchmark as BM
    return BM.load_bundle(BUNDLE, "2d", device, seed)                # asserts every 2d bundle file hash against MANIFEST.json


def load_net(path, device="cuda"):
    import xy as XY
    return XY.load_model(str(path), device)


def scorer_path(seed=0):
    return BUNDLE / "2d" / f"scorer_s{seed}.pt"


# ------------------------------------------------------------------------------------------------------------- read-only X/Y readout
def _views(jobs):
    import xy as XY
    out = []
    for row, seqs in jobs:
        inp = row["inputs"]
        P = lambda c: tuple(inp["cell_xy"][str(c)])  # noqa: E731
        xs = [[(int(i), P(d)) for i, d in s] for s in seqs if s]
        v, _, xm = XY.make_view(row["root_id"], inp["xy0"], inp["attrs"], inp["tid"], inp["goal"], inp["base"], inp["ctx"], [], xs, XY._NoGeo)
        out.append((v, xm))
    return out


def readout(net, jobs, device="cuda", max_q=6000):
    """jobs = [(public row, [ordered seq [[obj, cell], ...]])] -> per job {'p_noop', 'b0', 'rows': [per seq dict b, a, w, py, px1, px0, px, p11, lp11]}.
    Coefficients come from net.coeffs (the same forward pass as predict); probabilities are recomputed in float64 from the logits with
    log-sigmoid (no division by small pY).  Empty seq -> the no-op row (p11 = p_noop).  Roots are batched (padding is masked)."""
    import torch
    import torch.nn.functional as F
    import xy as XY
    res, i = [None] * len(jobs), 0
    while i < len(jobs):
        j, nq = i, 0
        while j < len(jobs) and (j == i or nq + len(jobs[j][1]) <= max_q):
            nq += len(jobs[j][1]); j += 1
        vx = _views(jobs[i:j])
        b, _ = XY.collate([v for v, _ in vx], device=device, dtype=torch.float32)
        with torch.no_grad():
            C = net.coeffs(b)
        bb, a, w = C["b"].double().cpu(), C["a"].double().cpu(), C["w"].double().cpu()
        par = b["parent"].cpu()
        y0 = b["y0"].cpu()
        ls = F.logsigmoid
        lpy_s, lpy0 = ls(bb), ls(-bb)
        qo = 0
        for k, (v, xm) in enumerate(vx):
            row, seqs = jobs[i + k]
            s0 = int(y0[k])
            out, n = [], 0
            for s in seqs:
                if not s:
                    p = float(torch.sigmoid(bb[s0]))
                    out.append({"seq": [], "b": float(bb[s0]), "py": p, "p11": p, "lp11": float(lpy_s[s0])})
                    continue
                q = qo + xm[n]; n += 1
                sp = int(par[q])
                u1, u0 = a[q] + w[q], a[q]
                py, px1, px0 = float(torch.sigmoid(bb[sp])), float(torch.sigmoid(u1)), float(torch.sigmoid(u0))
                lp11 = float(lpy_s[sp] + ls(u1))
                out.append({"seq": s, "b": float(bb[sp]), "a": float(a[q]), "w": float(w[q]), "py": py, "px1": px1, "px0": px0,
                            "px": py * px1 + (1 - py) * px0, "p11": math.exp(lp11), "lp11": lp11, "logit_px1": float(u1)})
            qo += len(v["x_seqs"])
            res[i + k] = {"root_id": row["root_id"], "p_noop": float(torch.sigmoid(bb[s0])), "b0": float(bb[s0]), "rows": out}
        i = j
    return res


# ------------------------------------------------------------------------------------------------------------- frozen cVAE ranks (cached)
def cvae_table(rows, samp, name, refresh=False):
    """root_id -> {'D6': {obj: [cells]}, 'raw': {obj: {cell: p}}} for every row (frozen S1 marginal; FDS domain.cvae_raw, parity 751/751)."""
    sys.path.insert(0, str(ABF / "full_domain_sets"))
    import domain as DM
    import search as S
    f = OUT / f"cvae_{name}.pkl"
    have = pickle.loads(f.read_bytes()) if f.exists() and not refresh else {}
    todo = [r for r in rows if r["root_id"] not in have]
    for r in todo:
        raw, D6, _ = DM.cvae_raw(S.Root(r, "2d"), samp, 0, 64)
        have[r["root_id"]] = {"D6": D6, "raw": raw}
    if todo:
        OUT.mkdir(parents=True, exist_ok=True)
        f.write_bytes(pickle.dumps(have))
    return have


class Ranks:
    """Per-root action ranks under the frozen marginal: archived top-6 first, then (-p, cell); tiers T4 / T56 / TTAIL; log prior."""

    def __init__(self, ent):
        self.rank, self.lp = {}, {}
        for o, p in ent["raw"].items():
            o = int(o)
            top = [int(d) for d in ent["D6"].get(o, ent["D6"].get(str(o), []))]
            rest = sorted((int(d) for d in p if int(d) not in set(top)), key=lambda d: (-p[d], d))
            Z = sum(p.values()) or 1.0
            for r, d in enumerate(top + rest):
                self.rank[(o, d)] = r + 1
                self.lp[(o, d)] = math.log(max(p[d] / Z, 1e-12))

    def tier(self, a):
        r = self.rank.get((int(a[0]), int(a[1])))
        return "OUTSIDE" if r is None else "T4" if r <= 4 else "T56" if r <= 6 else "R7_12" if r <= 12 else "TAIL"

    def seq_info(self, seq):
        acts = [(int(o), int(d)) for o, d in seq]
        rk = [self.rank.get(a) for a in acts]
        tiers = [self.tier(a) for a in acts]
        order = ["T4", "T56", "R7_12", "TAIL", "OUTSIDE"]
        return {"ranks": rk, "max_tier": max(tiers, key=order.index) if tiers else "NOOP", "n_off4": sum(t != "T4" for t in tiers),
                "off": (sum(t != "T4" for t in tiers) / len(tiers)) if tiers else 0.0,
                "prior": (sum(self.lp.get(a, math.log(1e-12)) for a in acts) / len(acts)) if acts else 0.0}


# ------------------------------------------------------------------------------------------------------------- strict exact-contract labels
OK = lambda s: s == "VERIFIED" or str(s).startswith("CERTIFIED")  # noqa: E731


def strict_labels(caches=CACHES):
    """(root, seq json) -> {'x','y' (None unless VERIFIED / CERTIFIED_*), 'xs','ys', 'src', 'conflict'}.  Decided values from different caches
    must agree, otherwise the key is QUARANTINED (conflict=True, values dropped).  A later decided value fills an earlier missing one."""
    lab = {}
    for c in caches:
        for v in jl(c):
            for x in v["results"]:
                xr, yr = x["x"] or {}, x["y"] or {}
                xs, ys = xr.get("status"), yr.get("status")
                xv = xr.get("x") if OK(xs) else None
                yv = yr.get("y") if OK(ys) else None
                k = (v["root"], json.dumps([[int(o), int(d)] for o, d in x["seq"]]))
                e = lab.setdefault(k, {"x": None, "y": None, "xs": xs, "ys": ys, "src": [], "conflict": False})
                e["src"].append(Path(c).parent.name)
                for f_, val, st in (("x", xv, xs), ("y", yv, ys)):
                    if val is None:
                        continue
                    if e[f_] is None:
                        e[f_], e[f_ + "s"] = int(val), st
                    elif e[f_] != int(val):
                        e["conflict"] = True
    for e in lab.values():
        if e["conflict"]:
            e["x"] = e["y"] = None
    return lab


def z_logic(x, y):
    """Logical conjunction: 1 iff both verified 1; 0 if either soundly 0; else None (unresolved)."""
    if x == 1 and y == 1:
        return 1
    if x == 0 or y == 0:
        return 0
    return None


def z_hist(x, y):
    """Historical strict outcome (analyze.outcome): FAIL_Y if y = 0, SUCCESS if both 1, FAIL_X if y = 1 and x = 0, else UNKNOWN."""
    return "FAIL_Y" if y == 0 else "SUCCESS" if (x == 1 and y == 1) else "FAIL_X" if (y == 1 and x == 0) else "UNKNOWN"


def legal_k2(row, seq):
    """K<=2 canonical grammar on the ORIGINAL root: movable non-target objects, distinct objects and destinations, legal originally empty non-goal."""
    import search as S
    R = S.Root(row, "2d")
    L, mv = set(R.legal_dests(R.cells0)), set(R.movable)
    objs, ds = [int(o) for o, _ in seq], [int(d) for _, d in seq]
    return 1 <= len(seq) <= 2 and len(set(objs)) == len(objs) and len(set(ds)) == len(ds) and all(o in mv for o in objs) and all(d in L for d in ds)
