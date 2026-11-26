"""R2 shared helpers: paths (gvlab2), PUBLIC rows, private label pool, metrics with family-cluster bootstrap CIs."""
from __future__ import annotations

import collections, hashlib, json, math, os
from pathlib import Path

import numpy as np

NW = Path(os.environ.get("R2_NW", "/home/projects/long-horizon/naren_workspace"))
FIG3 = NW / "fig3"
R2 = FIG3 / "r2"
SNAP_TRAIN = NW / "k3abl/abf/snapshot/abf_v32_fb0eef4f5ff433ee"
SNAP_V34 = NW / "k3abl/abf/snapshot/abf_9de85710c2a7103f"
PRIV = NW / "k3abl/runs/public"
NBINS = {"2d": [(1, 5), (6, 10), (11, 15), (16, 20)], "3d": [(1, 3), (4, 5), (6, 7), (8, 13)]}     # TRAIN-quantile-based, predeclared


def h(s):
    return hashlib.sha256(str(s).encode()).hexdigest()


def nbin(dom, n):
    for lo, hi in NBINS[dom]:
        if lo <= n <= hi:
            return f"{lo}-{hi}"
    return f">{NBINS[dom][-1][1]}"


def snapshot_rows(dom, splits=("train", "val"), snap=None):
    """Non-TEST rows (TEST lines skipped by split before parsing)."""
    out = {}
    for s in ([snap] if snap else [SNAP_TRAIN, SNAP_V34]):
        for line in open(s / f"data{dom}.jsonl"):
            i = line.find('"split": "'); sp = line[i + 10:i + 10 + line[i + 10:].find('"')]
            if sp in splits:
                r = json.loads(line)
                out.setdefault(r["root_id"], r)
    return out


def pool(dom):
    return [json.loads(l) for l in open(R2 / "audit" / f"pool_{dom}.jsonl")]


def raw_path(dom, rid):
    for sp in ("val", "train"):
        p = PRIV / f"private_{sp}_{dom}.jsonl"
        for l in open(p):
            if f'"{rid}"' in l:
                e = json.loads(l)
                if e.get("root_id", e.get("evaluation_group_id")) == rid:
                    return e["path"], e.get("geom", "original")
    return None, None


# ------------------------------------------------------------------ metrics
def auroc(y, p):
    y, p = np.asarray(y), np.asarray(p, float)
    pos, neg = p[y == 1], p[y == 0]
    if not len(pos) or not len(neg):
        return None
    r = np.argsort(np.argsort(np.concatenate([pos, neg]), kind="stable"), kind="stable").astype(float)
    allv = np.concatenate([pos, neg])                                   # average ranks for ties
    for v in np.unique(allv):
        m = allv == v
        if m.sum() > 1:
            r[m] = r[m].mean()
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) - 1) / 2) / (len(pos) * len(neg)))


def auprc(y, p):
    y, p = np.asarray(y), np.asarray(p, float)
    if y.sum() == 0:
        return None
    o = np.argsort(-p, kind="stable"); y = y[o]
    tp = np.cumsum(y); prec = tp / np.arange(1, len(y) + 1)
    return float((prec * y).sum() / y.sum())


def brier(y, p):
    return float(np.mean((np.asarray(p, float) - np.asarray(y)) ** 2))


def nll(y, p):
    p = np.clip(np.asarray(p, float), 1e-7, 1 - 1e-7); y = np.asarray(y)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def ece(y, p, n=10):
    y, p = np.asarray(y), np.asarray(p, float)
    b = np.minimum((p * n).astype(int), n - 1)
    return float(sum(abs(y[b == k].mean() - p[b == k].mean()) * (b == k).mean() for k in range(n) if (b == k).any()))


def concordance(groups):
    """groups: list of [(label, score)] within one context; pairs with different labels; ties count 1/2."""
    num = den = 0.0
    for g in groups:
        for (ya, pa) in g:
            for (yb, pb) in g:
                if ya == 1 and yb == 0:
                    den += 1; num += 1.0 if pa > pb else (0.5 if pa == pb else 0.0)
    return (num / den if den else None), int(den)


def cluster_boot(items, fam, stat, B=1000, seed=0):
    """Percentile CI of stat(list) over family-cluster resamples."""
    by = collections.defaultdict(list)
    for it, f in zip(items, fam):
        by[f].append(it)
    keys = sorted(by)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(B):
        s = [it for k in rng.choice(keys, len(keys)) for it in by[k]]
        v = stat(s)
        if v is not None:
            vals.append(v)
    if len(vals) < B * 0.5:
        return None
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def summary(rows, ykey, pkey, famkey="fam", B=1000):
    """rows: dicts with label, score, family.  AUROC/AUPRC/Brier/NLL/ECE + family-cluster CI on AUROC."""
    rows = [r for r in rows if r.get(ykey) in (0, 1) and r.get(pkey) is not None]
    if not rows:
        return {"n": 0}
    y = [r[ykey] for r in rows]; p = [r[pkey] for r in rows]
    out = {"n": len(rows), "pos": int(sum(y)), "families": len({r[famkey] for r in rows}), "prevalence": float(np.mean(y)), "mean_p": float(np.mean(p)),
           "auroc": auroc(y, p), "auprc": auprc(y, p), "brier": brier(y, p), "nll": nll(y, p), "ece": ece(y, p)}
    mixed = collections.defaultdict(set)
    for r in rows:
        mixed[r[famkey]].add(r[ykey])
    out["mixed_families"] = sum(1 for v in mixed.values() if len(v) == 2)
    if out["auroc"] is not None and out["mixed_families"] >= 2:
        out["auroc_ci"] = cluster_boot(rows, [r[famkey] for r in rows], lambda s: auroc([r[ykey] for r in s], [r[pkey] for r in s]), B)
    return out
