#!/usr/bin/env python3
"""P1 placement proposals for 2D (8x8 planar lattice) and 3D (6x6 shelf): data, samplers, training, evaluation, inference API.

Samplers are the verified 3D module (rss-3d-learning approachb_3d_learning/src/models.py @ 4d2d3dbf) generalized from the fixed 6x6 grid to an
R x C grid: SceneEncoder (per-object MLP + query-keyed attention + mean + occupancy MLP), CVAE (masked categorical decoder, KL warm-up), FlowMatch
(dequantized cell coordinates, Euler ODE, projection to the nearest legal cell), Uniform and BandStratified controls, Ranker (supervised, separate).
Conditioning (plan 3.1): the hypothetical scene's objects (geometry only, no target / goal / roles / K / repairs) and the queried object; legal =
declared support cells free in that scene.  Supervision: Q2 isolated placement trials (label 1 / 0; unlabelled and static contrasts excluded).

    python placement.py build  {2d,3d} OUT_DIR            Q2 records -> features.npz + rows.json (+ train-split scalers)
    python placement.py fit    {2d,3d} DATA_DIR KIND SEED  -> runs/p1_<dom>/<kind>_s<seed>/{model.pt,curve.json}
    python placement.py eval   {2d,3d} DATA_DIR SPLIT      every arm x seeds x M -> runs/p1_<dom>/eval_<split>.json"""
from __future__ import annotations

import collections, gzip, hashlib, json, math, os, sys, time
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("ABF_ROOT", "/scratch/nav/approachb_final"))
MIR = ROOT / "mirror"
Q2_2D = Path.home() / "approachb3d_v3/2d_q2_spillover/src/gh-yadu-iiith/planar_2d/dataset_relocations_v1/q2_spillover/merged/q2_canonical_v4"
Q2_3D = Path.home() / "approachb3d_v3/repo/gh-yadu-iiith/shelf_6x6_open_sides/dataset_placement_extension_v2/production_v4"
DS2 = MIR / "rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_bd_classquota/raw/roots"
SRC3 = MIR / "rss3d_final_src/gh-yadu-iiith/shelf_6x6_open_sides/dataset_bd_classquota_without_home_position_no_overpass/raw/roots"
GRID = {"2d": (8, 8), "3d": (6, 6)}
SPLITS = ["train", "val", "test"]
MAXOBJ = {"2d": 20, "3d": 12}               # padding only (masked, permutation-invariant encoder); 3D Q2 training scenes have <= 8 objects, 3D NONE scenes more
NORM = [2, 3, 6, 7, 8]


# --------------------------------------------------------------------------------------------- domain geometry and features (label-blind)
def cell_xy(dom, c):
    R, C = GRID[dom]
    r, k = divmod(int(c), C)
    return (0.08 * (k + 0.5), 0.08 * (r + 0.5)) if dom == "2d" else (0.42 + (r - 2.5) * 0.075, (k - 2.5) * 0.075)


def scene_features(dom, objs, cells, query, legal_cells):
    """objs {id: (a0, a1, a2, a3)} geometry attributes, cells {id: cell} of the HYPOTHETICAL scene, query id ->
    F [MAXOBJ, 14] (query first, then sorted ids), mask, occ [R*C], legal [R*C].  Feature columns (3D identical to data3d.FEAT):
    a0..a3 (3D: is_box, is_cyl, size, height; 2D: radius, is_fixed, 0, 0), r/(R-1), c/(C-1), x, y, dist, angle/pi, is_query, dr_q, dc_q, cheb_q."""
    R, C = GRID[dom]
    base = (-0.14, 0.32) if dom == "2d" else (0.0, 0.0)
    ids = [query] + sorted(o for o in cells if o != query)
    F, M, occ = np.zeros((MAXOBJ[dom], 14), np.float32), np.zeros(MAXOBJ[dom], bool), np.zeros(R * C, np.float32)
    qr, qc = divmod(int(cells[query]), C)
    for i, o in enumerate(ids):
        r, c = divmod(int(cells[o]), C)
        x, y = cell_xy(dom, cells[o])
        dx, dy = x - base[0], y - base[1]
        F[i] = [*objs[o], r / (R - 1), c / (C - 1), x, y, math.hypot(dx, dy), math.atan2(dy, dx) / math.pi, o == query,
                (r - qr) / (R - 1), (c - qc) / (C - 1), max(abs(r - qr), abs(c - qc)) / (R - 1)]
        M[i] = True
        occ[int(cells[o])] = 1
    leg = np.zeros(R * C, bool)
    leg[list(legal_cells)] = True
    return F, M, occ, leg & (occ == 0)


def root2d(rid):
    rec = json.loads((DS2 / f"{rid}.json").read_text())
    sc = rec["scene"]
    objs = {o["id"]: (o["radius_m"], float(o["id"] in rec["fixed_ids"]), 0.0, 0.0) for o in sc["objects"]}
    return objs, {o["id"]: o["cell"] for o in sc["objects"]}, sc["legal_cells"]


def root3d(rid):
    rec = json.loads((SRC3 / f"{rid}.json").read_text())
    objs = {o["id"]: (float(o["shape"] == "box"), float(o["shape"] == "cylinder"), o["size"], o["height"]) for o in rec["objects"]}
    return objs, {o: v[0] * 6 + v[1] for o, v in rec["initial_cells"].items()}, list(range(36))


def q2_rows(dom):
    """-> [(root_id, split, ctx_key, cells_of_hypothetical_scene, query object, dest cell, label 0/1, status, src cell, stratum)]"""
    out = []
    if dom == "2d":
        for f in sorted((Q2_2D / "records").iterdir()):
            d = json.loads(f.read_text())
            objs, cells0, legal = root2d(d["root_id"])
            for q in d["queries"]:
                if q["label"] not in (0, 1) or not q.get("completed"):
                    continue                                              # unlabelled / static contrasts / censored: never negatives
                cells = dict(cells0)
                for o, c in q["prefix_key"] or []:
                    cells[o] = c
                out.append((d["root_id"], d["split"], q["hypothetical_scene_hash"] + "|" + q["object_id"], cells, q["object_id"], q["destination_cell"],
                            q["label"], q.get("negative_kind") or "VERIFIED", cells[q["object_id"]], q["block"], objs, legal))
    else:
        rost = {}
        with gzip.open(Q2_3D / "frozen/q2_parity_roster_v4.jsonl.gz", "rt") as f:
            for line in f:
                r = json.loads(line)
                rost[r["qid"]] = r
        cache = {}
        for f in sorted((Q2_3D / "run_q2_parity/units").glob("*.json")):
            d = json.loads(f.read_text())
            u = f.stem
            if u not in cache:
                cache[u] = root3d(u)
            objs, _, legal = cache[u]
            for r in d["records"]:
                if r["label"] is None:
                    continue
                ro = rost[r["qid"]]
                cells = {o: c[0] * 6 + c[1] for o, c in ro["cells"].items()}
                out.append((u, ro["split"], f"{u}|{ro['scene_hash']}|{ro['object']}", cells, ro["object"], ro["dest"][0] * 6 + ro["dest"][1],
                            int(r["label"]), r["status"], ro["src"][0] * 6 + ro["src"][1], ro["block"], objs, legal))
    return out


def build(dom, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows = q2_rows(dom)
    F, M, OCC, LEG, meta = [], [], [], [], []
    for (rid, sp, ck, cells, o, dest, lab, st, src, blk, objs, legal) in rows:
        f, m, occ, leg = scene_features(dom, objs, cells, o, legal)
        if not leg[dest]:
            raise SystemExit(f"{rid} {ck}: destination {dest} not legal/free in its hypothetical scene")
        F.append(f); M.append(m); OCC.append(occ); LEG.append(leg)
        meta.append({"root": rid, "split": sp, "ctx": ck, "dest": int(dest), "label": int(lab), "status": st, "src": int(src), "block": blk})
    F, M, OCC, LEG = map(np.stack, (F, M, OCC, LEG))
    split = np.array([SPLITS.index(m["split"]) for m in meta], np.int8)
    mu, sd = np.zeros(14, np.float32), np.ones(14, np.float32)
    for j in NORM:
        v = F[split == 0][:, :, j][M[split == 0]]
        mu[j], sd[j] = v.mean(), v.std() + 1e-6
    ctx = {c: i for i, c in enumerate(dict.fromkeys(m["ctx"] for m in meta))}
    np.savez_compressed(out / "features.npz", obj=F, mask=M, occ=OCC, legal=LEG, split=split,
                        dest=np.array([m["dest"] for m in meta], np.int16), label=np.array([m["label"] for m in meta], np.int8),
                        ctx=np.array([ctx[m["ctx"]] for m in meta], np.int32), src=np.array([m["src"] for m in meta], np.int16))
    (out / "rows.json").write_text(json.dumps({"roots": [m["root"] for m in meta], "status": [m["status"] for m in meta], "block": [m["block"] for m in meta]}))
    sc = {"domain": dom, "grid": GRID[dom], "maxobj": MAXOBJ[dom], "mean": mu.tolist(), "std": sd.tolist(), "fit_on": "TRAIN split only",
          "n": len(meta), "contexts": len(ctx), "features_sha256": hashlib.sha256((out / "features.npz").read_bytes()).hexdigest(),
          "by_split": {s: {"queries": int((split == i).sum()), "roots": len({m["root"] for m in meta if m["split"] == s}),
                           "label_1": int(((split == i) & (np.array([m["label"] for m in meta]) == 1)).sum())} for i, s in enumerate(SPLITS)},
          "roots_in_two_splits": sum(len(v) > 1 for v in _split_sets(meta).values())}
    (out / "scalers.json").write_text(json.dumps(sc, indent=1))
    print(json.dumps({k: sc[k] for k in ("n", "contexts", "by_split", "roots_in_two_splits", "features_sha256")}))


def _split_sets(meta):
    d = collections.defaultdict(set)
    for m in meta:
        d[m["root"]].add(m["split"])
    return d


# --------------------------------------------------------------------------------------------- models (generalized from the verified 3D module)
import torch  # noqa: E402
from torch import nn  # noqa: E402
from torch.nn import functional as Fn  # noqa: E402


def mlp(i, h, o, n=2):
    layers, d = [], i
    for _ in range(n):
        layers += [nn.Linear(d, h), nn.SiLU()]
        d = h
    return nn.Sequential(*layers, nn.Linear(d, o))


def centres(R, C):
    return torch.tensor([[2 * (r + 0.5) / R - 1, 2 * (c + 0.5) / C - 1] for r in range(R) for c in range(C)])


class SceneEncoder(nn.Module):
    def __init__(self, ncell, nfeat=14, h=128):
        super().__init__()
        self.phi = mlp(nfeat, h, h)
        self.q, self.k, self.v = nn.Linear(h, h), nn.Linear(h, h), nn.Linear(h, h)
        self.grid, self.out, self.h = mlp(ncell, h, h, 1), mlp(4 * h, h, h, 1), h

    def forward(self, obj, mask, occ):
        e = self.phi(obj) * mask[..., None]
        qtok = e[:, 0]
        att = ((self.q(qtok)[:, None] * self.k(e)).sum(-1) / math.sqrt(self.h)).masked_fill(~mask, -1e9).softmax(-1)
        ctx = (att[..., None] * self.v(e)).sum(1)
        mean = e.sum(1) / mask.sum(1, keepdim=True).clamp(min=1)
        return self.out(torch.cat([qtok, ctx, mean, self.grid(occ)], -1))


def masked(lg, legal):
    return lg.masked_fill(~legal, -1e9)


def gumbel_argmax(lg, gen):
    u = torch.rand(lg.shape, device=lg.device, generator=gen).clamp(1e-9, 1 - 1e-9)
    return (lg - (-u.log()).log()).argmax(-1)


class CVAE(nn.Module):
    kind = "cvae"

    def __init__(self, R, C, h=128, z=8):
        super().__init__()
        self.R, self.C, self.N = R, C, R * C
        self.enc, self.zdim = SceneEncoder(self.N, 14, h), z
        self.post, self.dec = mlp(h + self.N, h, 2 * z), mlp(h + z, h, self.N)

    def loss(self, obj, mask, occ, legal, dest, beta):
        c = self.enc(obj, mask, occ)
        mu, lv = self.post(torch.cat([c, Fn.one_hot(dest, self.N).float()], -1)).chunk(2, -1)
        z = mu + torch.randn_like(mu) * (0.5 * lv).exp()
        rec = Fn.cross_entropy(masked(self.dec(torch.cat([c, z], -1)), legal), dest)
        kl = 0.5 * (mu.pow(2) + lv.exp() - 1 - lv).sum(-1).mean()
        return rec + beta * kl, {"rec": rec.item(), "kl": kl.item()}

    @torch.no_grad()
    def sample(self, obj, mask, occ, legal, n, gen=None, src=None):
        c = self.enc(obj, mask, occ)
        B = c.shape[0]
        z = torch.randn(B, n, self.zdim, device=c.device, generator=gen)
        lg = masked(self.dec(torch.cat([c[:, None].expand(B, n, -1), z], -1)), legal[:, None])
        return gumbel_argmax(lg, gen), torch.zeros(B, n, dtype=torch.bool, device=c.device)


class FlowMatch(nn.Module):
    kind = "fm"

    def __init__(self, R, C, h=128, steps=32):
        super().__init__()
        self.R, self.C, self.N, self.steps = R, C, R * C, steps
        self.enc = SceneEncoder(self.N, 14, h)
        self.register_buffer("f", torch.exp(torch.linspace(0, math.log(100.0), 16)))
        self.register_buffer("ce", centres(R, C))
        self.v = mlp(2 + 32 + h, h, 2, 3)

    def temb(self, t):
        a = t[:, None] * self.f[None] * 2 * math.pi
        return torch.cat([a.sin(), a.cos()], -1)

    def coord(self, dest):
        rc = torch.stack([dest // self.C, dest % self.C], -1).float() + torch.rand(dest.shape[0], 2, device=dest.device)
        return torch.stack([2 * rc[:, 0] / self.R - 1, 2 * rc[:, 1] / self.C - 1], -1)

    def loss(self, obj, mask, occ, legal, dest, beta=None):
        c = self.enc(obj, mask, occ)
        x1 = self.coord(dest)
        x0 = torch.randn_like(x1)
        t = torch.rand(x1.shape[0], device=x1.device)
        xt = (1 - t[:, None]) * x0 + t[:, None] * x1
        l = (self.v(torch.cat([xt, self.temb(t), c], -1)) - (x1 - x0)).pow(2).sum(-1).mean()
        return l, {"fm": l.item()}

    @torch.no_grad()
    def sample(self, obj, mask, occ, legal, n, gen=None, src=None):
        c = self.enc(obj, mask, occ)
        B = c.shape[0]
        cc = c[:, None].expand(B, n, -1).reshape(B * n, -1)
        x = torch.randn(B * n, 2, device=c.device, generator=gen)
        for i in range(self.steps):
            x = x + self.v(torch.cat([x, self.temb(torch.full((B * n,), i / self.steps, device=c.device)), cc], -1)) / self.steps
        x = x.view(B, n, 2)
        ood = (x.abs() > 1).any(-1)
        rr = ((x[..., 0] + 1) * self.R / 2).floor().clamp(0, self.R - 1).long()
        cl = ((x[..., 1] + 1) * self.C / 2).floor().clamp(0, self.C - 1).long()
        raw_illegal = ood | ~legal.gather(1, rr * self.C + cl)
        d2 = (x[:, :, None] - self.ce[None, None]).pow(2).sum(-1).masked_fill(~legal[:, None], float("inf"))
        return d2.argmin(-1), raw_illegal


class Uniform(nn.Module):
    kind = "uniform"

    def __init__(self, R, C):
        super().__init__()

    def sample(self, obj, mask, occ, legal, n, gen=None, src=None):
        d = torch.multinomial(legal.float() / legal.float().sum(1, keepdim=True), n, replacement=True, generator=gen)
        return d, torch.zeros_like(d, dtype=torch.bool)


class BandStratified(nn.Module):
    """Analytical control: round robin over Chebyshev distance bands from the source cell (near 1 / mid 2-3 / far >= 4), uniform inside a band."""
    kind = "stratified"

    def __init__(self, R, C):
        super().__init__()
        self.R, self.C = R, C

    def sample(self, obj, mask, occ, legal, n, gen=None, src=None):
        B, N = legal.shape
        r, c = torch.arange(N, device=legal.device) // self.C, torch.arange(N, device=legal.device) % self.C
        ch = torch.maximum((r[None] - (src // self.C)[:, None]).abs(), (c[None] - (src % self.C)[:, None]).abs())
        bands = [(ch == 1), (ch >= 2) & (ch <= 3), (ch >= 4)]
        out = torch.empty(B, n, dtype=torch.long, device=legal.device)
        for j in range(n):
            sel = legal
            for k in (2, 1, 0):
                m = bands[(j + k) % 3] & legal
                sel = torch.where(m.any(1, keepdim=True), m, sel)
            out[:, j] = torch.multinomial(sel.float() / sel.float().sum(1, keepdim=True), 1, generator=gen).squeeze(1)
        return out, torch.zeros_like(out, dtype=torch.bool)


ARMS = {"cvae": CVAE, "fm": FlowMatch, "uniform": Uniform, "stratified": BandStratified}
LEARNED = ("cvae", "fm")


# --------------------------------------------------------------------------------------------- data, training, evaluation
class Data:
    def __init__(self, d, device):
        z = np.load(Path(d) / "features.npz")
        sc = json.loads((Path(d) / "scalers.json").read_text())
        obj = (z["obj"] - np.array(sc["mean"], np.float32)) / np.array(sc["std"], np.float32) * z["mask"][..., None]
        T = lambda a, dt=None: torch.as_tensor(a, dtype=dt, device=device)  # noqa: E731
        self.obj, self.mask, self.occ, self.legal = T(obj, torch.float32), T(z["mask"]), T(z["occ"], torch.float32), T(z["legal"])
        self.dest, self.label, self.split, self.ctx, self.src = (T(z[k], torch.long) for k in ("dest", "label", "split", "ctx", "src"))
        self.R, self.C = sc["grid"]
        ctx = z["ctx"]
        nC = int(ctx.max()) + 1
        first = np.full(nC, -1)
        for i, c in enumerate(ctx):
            if first[c] < 0:
                first[c] = i
        pos, neg = np.zeros((nC, self.R * self.C), bool), np.zeros((nC, self.R * self.C), bool)
        lab, dst = z["label"], z["dest"]
        pos[ctx[lab == 1], dst[lab == 1]] = True
        neg[ctx[lab == 0], dst[lab == 0]] = True
        self.c_row, self.c_pos, self.c_neg = T(first, torch.long), T(pos), T(neg)
        self.c_split = self.split[self.c_row]
        self.roots = json.loads((Path(d) / "rows.json").read_text())["roots"]

    def batch(self, idx):
        return self.obj[idx], self.mask[idx], self.occ[idx], self.legal[idx]


def fit(dom, data_dir, kind, seed, cfg=None):
    cfg = {"epochs": 40, "batch": 512, "lr": 1e-3, "beta_max": 1.0, "warm": 10, "hidden": 128, "zdim": 8, **(cfg or {})}
    dev = "cuda"
    torch.manual_seed(seed)
    D = Data(data_dir, dev)
    m = ARMS[kind](D.R, D.C, cfg["hidden"], **({"z": cfg["zdim"]} if kind == "cvae" else {})).to(dev)
    tr = torch.nonzero((D.split == 0) & (D.label == 1)).squeeze(1)
    va = torch.nonzero((D.split == 1) & (D.label == 1)).squeeze(1)
    opt = torch.optim.AdamW(m.parameters(), lr=cfg["lr"], weight_decay=1e-4)
    out = ROOT / "runs" / f"p1_{dom}" / f"{kind}_s{seed}"
    out.mkdir(parents=True, exist_ok=True)
    g = torch.Generator(device=dev).manual_seed(seed)
    curve, best, t0 = [], (math.inf, None), time.time()
    for ep in range(cfg["epochs"]):
        m.train()
        beta = cfg["beta_max"] * min(1.0, (ep + 1) / cfg["warm"])
        perm = tr[torch.randperm(len(tr), device=dev, generator=g)]
        tl = []
        for i in range(0, len(perm), cfg["batch"]):
            ix = perm[i:i + cfg["batch"]]
            l, _ = m.loss(*D.batch(ix), D.dest[ix], beta)
            opt.zero_grad(); l.backward(); opt.step()
            tl.append(l.item())
        m.eval()
        with torch.no_grad():
            vl = float(np.mean([m.loss(*D.batch(va[i:i + 4096]), D.dest[va[i:i + 4096]], cfg["beta_max"])[0].item() for i in range(0, len(va), 4096)]))
        curve.append({"epoch": ep, "train": float(np.mean(tl)), "val": vl, "beta": beta})
        if vl < best[0]:
            best = (vl, ep)
            torch.save({"state": m.state_dict(), "cfg": cfg, "kind": kind, "grid": [D.R, D.C], "epoch": ep}, out / "model.pt.tmp")
            os.replace(out / "model.pt.tmp", out / "model.pt")
    (out / "curve.json").write_text(json.dumps({"curve": curve, "best_val": best[0], "best_epoch": best[1], "cfg": cfg, "seed": seed,
                                                "train_positives": len(tr), "wall_s": round(time.time() - t0, 1),
                                                "gpu_peak_mib": round(torch.cuda.max_memory_allocated() / 2 ** 20, 1)}, indent=1))
    print(json.dumps({"kind": kind, "seed": seed, "best_val": best[0], "best_epoch": best[1], "wall_s": round(time.time() - t0, 1)}))


def load(dom, kind, seed, device="cuda"):
    R, C = GRID[dom]
    if kind not in LEARNED:
        return ARMS[kind](R, C).to(device)
    ck = torch.load(ROOT / "runs" / f"p1_{dom}" / f"{kind}_s{seed}" / "model.pt", map_location=device, weights_only=False)
    m = ARMS[kind](R, C, ck["cfg"]["hidden"], **({"z": ck["cfg"]["zdim"]} if kind == "cvae" else {})).to(device)
    m.load_state_dict(ck["state"])
    return m.eval()


@torch.no_grad()
def propose(m, obj, mask, occ, legal, src, M, gen, raw_mult=8):
    """First M UNIQUE legal destinations out of raw_mult * M draws with replacement (the shared budget rule) -> (list of lists, raw draws, raw illegal)."""
    d, ill = m.sample(obj, mask, occ, legal, raw_mult * M, gen=gen, src=src)
    out = []
    for row in d.tolist():
        seen = []
        for c in row:
            if c not in seen:
                seen.append(c)
                if len(seen) == M:
                    break
        out.append(seen)
    return out, d.shape[1], ill.float().mean().item()


def evaluate(dom, data_dir, split, seeds=(0, 1, 2), eval_seeds=(0, 1, 2), Ms=(1, 2, 4, 8, 16)):
    dev = "cuda"
    D = Data(data_dir, dev)
    si = SPLITS.index(split)
    cs = torch.nonzero((D.c_split == si) & (D.c_pos.any(1) | D.c_neg.any(1))).squeeze(1)
    rows = D.c_row[cs]
    obj, mask, occ, legal = D.batch(rows)
    src = D.src[rows]
    roots = np.array(D.roots)[rows.cpu().numpy()]
    res = {"split": split, "contexts": len(cs), "contexts_with_positive": int(D.c_pos[cs].any(1).sum()), "roots": len(set(roots)), "arms": {}}
    pos, neg = D.c_pos[cs].cpu().numpy(), D.c_neg[cs].cpu().numpy()
    for kind in ("cvae", "fm", "uniform", "stratified"):
        runs = []
        for s in (seeds if kind in LEARNED else (0,)):
            m = load(dom, kind, s, dev)
            for es in eval_seeds:
                g = torch.Generator(device=dev).manual_seed(1000 * es + s)
                t0 = time.time()
                props, raw, ill = propose(m, obj, mask, occ, legal, src, max(Ms), g)
                torch.cuda.synchronize()
                lat = (time.time() - t0) / len(cs) * 1000
                per, hit4 = {}, []
                for i, p in enumerate(props):
                    hit4.append(float(any(pos[i, c] for c in p[:4])) if pos[i].any() else np.nan)
                for M in Ms:
                    hit, known, kpos, uniq, regions = [], [], [], [], []
                    for i, p in enumerate(props):
                        p = p[:M]
                        hit.append(float(any(pos[i, c] for c in p))) if pos[i].any() else None
                        kn = [c for c in p if pos[i, c] or neg[i, c]]
                        known.append(len(kn) / max(1, len(p)))
                        if kn:
                            kpos.append(sum(pos[i, c] for c in kn) / len(kn))
                        uniq.append(len(p))
                    per[M] = {"hit": float(np.mean(hit)), "known_label_precision": float(np.mean(kpos)) if kpos else None,
                              "known_fraction": float(np.mean(known)), "unique_mean": float(np.mean(uniq))}
                runs.append({"seed": s, "eval_seed": es, "per_M": per, "raw_illegal_rate": ill, "latency_ms_per_context": lat, "_hit4": hit4})
        agg = {M: {k: float(np.mean([r["per_M"][M][k] for r in runs if r["per_M"][M][k] is not None])) for k in runs[0]["per_M"][M]} for M in Ms}
        res["arms"][kind] = {"runs": runs, "mean": agg, "latency_ms": float(np.mean([r["latency_ms_per_context"] for r in runs])),
                             "raw_illegal_rate": float(np.mean([r["raw_illegal_rate"] for r in runs]))}
    # root-cluster bootstrap 95% CI of hit@4 differences vs cvae (per-context mean over runs, then per-root mean; 2,000 resamples of roots)
    per_ctx = {k: np.nanmean(np.array([r.pop("_hit4") for r in v["runs"]]), 0) for k, v in res["arms"].items()}
    ok = ~np.isnan(per_ctx["cvae"])
    uroots = sorted(set(roots[ok]))
    ridx = {r: i for i, r in enumerate(uroots)}
    def by_root(x):
        s_, n_ = np.zeros(len(uroots)), np.zeros(len(uroots))
        for r, v in zip(roots[ok], x[ok]):
            s_[ridx[r]] += v; n_[ridx[r]] += 1
        return s_ / np.maximum(n_, 1)
    base = by_root(per_ctx["cvae"])
    g = np.random.default_rng(0)
    res["paired_hit4_vs_cvae"] = {}
    for k, x in per_ctx.items():
        if k == "cvae":
            continue
        d = by_root(x) - base
        bs = [d[g.integers(0, len(d), len(d))].mean() for _ in range(2000)]
        res["paired_hit4_vs_cvae"][k] = {"delta": float(d.mean()), "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))], "roots": len(d)}
    if split == "val":
        best = max(("uniform", "stratified"), key=lambda k: res["arms"][k]["mean"][4]["hit"])
        (ROOT / "runs" / f"p1_{dom}" / "analytic_choice.json").write_text(json.dumps({"kind": best, "rule": "higher VAL hit@4 of uniform vs stratified",
                                                                                      "val_hit4": {k: res["arms"][k]["mean"][4]["hit"] for k in ("uniform", "stratified")}}))
    out = ROOT / "runs" / f"p1_{dom}" / f"eval_{split}.json"
    out.write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: {M: round(v["mean"][M]["hit"], 3) for M in Ms} for k, v in res["arms"].items()}))


if __name__ == "__main__":
    cmd, dom = sys.argv[1], sys.argv[2]
    if cmd == "build":
        build(dom, sys.argv[3])
    elif cmd == "fit":
        fit(dom, sys.argv[3], sys.argv[4], int(sys.argv[5]))
    elif cmd == "eval":
        evaluate(dom, sys.argv[3], sys.argv[4])
    else:
        raise SystemExit(__doc__)
