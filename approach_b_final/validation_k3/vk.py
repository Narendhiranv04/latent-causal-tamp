"""Post-ablation validation (k3val): shared paths, loaders and statistics.  Reads the completed K<=3 ablation artifacts READ-ONLY ($K3A);
writes only under $K3V.  No frozen checkpoint, prediction, seal, manifest or dataset is modified."""
import collections, hashlib, json, os, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
K3A, K3V = Path(os.environ["K3A"]), Path(os.environ["K3V"])
ABF = Path(os.environ["ABF_ROOT"])
SNAP, EXPS = ABF / "snapshot/abf_9de85710c2a7103f", ABF / "snapshot/abf_v32_fb0eef4f5ff433ee"
BUNDLE = K3A / "stage/bundle"
OUT = K3V / "runs/out"
B, SEED = 2000, 0


def jl(p):
    return [json.loads(l) for l in open(p)] if Path(p).exists() else []


def wjson(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, indent=1, default=float))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ckpt(model, dom):
    """FULL_s* = frozen bundle D (never modified); E/G/DIRECT/DREFIT(=training D) = the ablation fits."""
    arm, s = model.rsplit("_s", 1)
    if arm == "FULL":
        return BUNDLE / dom / f"scorer_s{s}.pt"
    return K3A / "runs/training/xy" / dom / f"p2_{dom}" / f"{'D' if arm == 'DREFIT' else arm}_s{s}" / "model.pt"


def rows(dom, split, snap=None):
    snap = snap or (EXPS if split == "train" else SNAP)
    return [r for r in map(json.loads, open(Path(snap) / f"data{dom}.jsonl")) if r["split"] == split]


def cluster_boot(vals, groups, n=B, seed=SEED, scale=100.0):
    """mean with a cluster bootstrap over groups -> [point, lo, hi] (x scale)."""
    vals, groups = np.asarray(vals, float), np.asarray(groups)
    if not len(vals):
        return [None, None, None]
    ug, inv = np.unique(groups, return_inverse=True)
    sums, cnts = np.bincount(inv, vals, len(ug)), np.bincount(inv, None, len(ug))
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(n):
        k = rng.integers(0, len(ug), len(ug))
        bs.append(sums[k].sum() / cnts[k].sum())
    return [round(scale * float(vals.mean()), 4), round(scale * float(np.percentile(bs, 2.5)), 4), round(scale * float(np.percentile(bs, 97.5)), 4)]


def bce(y, p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    y = np.asarray(y, float)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def ece(y, p, n=10):
    y, p = np.asarray(y, float), np.asarray(p, float)
    if not len(y):
        return None
    bins = np.minimum((p * n).astype(int), n - 1)
    return float(sum(abs(y[bins == k].mean() - p[bins == k].mean()) * (bins == k).mean() for k in range(n) if (bins == k).any()))


def reliability(y, p, n=10):
    y, p = np.asarray(y, float), np.asarray(p, float)
    bins = np.minimum((p * n).astype(int), n - 1)
    return [{"bin": k, "n": int((bins == k).sum()), "mean_p": float(p[bins == k].mean()), "freq": float(y[bins == k].mean())} for k in range(n) if (bins == k).any()]


def auroc(y, p):
    y, p = np.asarray(y), np.asarray(p, float)
    if len(y) == 0 or y.min() == y.max():
        return None
    from scipy.stats import rankdata
    r = rankdata(p)
    n1 = y.sum()
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1)))


def auprc(y, p):
    y, p = np.asarray(y), np.asarray(p, float)
    if y.sum() == 0:
        return None
    o = np.argsort(-p, kind="mergesort")
    tp = np.cumsum(y[o])
    return float(((tp / np.arange(1, len(y) + 1)) * y[o]).sum() / y.sum())


def lineage(dom, split):
    return {r["root_id"]: r["layout_root_id"] for r in rows(dom, split)}
