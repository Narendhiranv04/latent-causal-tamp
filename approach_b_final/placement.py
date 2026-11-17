#!/usr/bin/env python3
"""P1 placement proposals for 2D (8x8 planar lattice) and 3D (6x6 shelf): data, samplers, training, evaluation, inference API.

Samplers are the verified 3D module (rss-3d-learning approachb_3d_learning/src/models.py @ 4d2d3dbf) generalized from the fixed 6x6 grid to an
R x C grid: SceneEncoder (per-object MLP + query-keyed attention + mean + occupancy MLP), CVAE (masked categorical decoder, KL warm-up), FlowMatch
(dequantized cell coordinates, Euler ODE, projection to the nearest legal cell), Uniform and BandStratified controls, Ranker (supervised, separate).
Conditioning (plan 3.1): the hypothetical scene's objects (geometry only, no target / goal / roles / K / repairs) and the queried object; legal =
declared support cells free in that scene.  Supervision: Q2 isolated placement trials (label 1 / 0; unlabelled and static contrasts excluded).

    python placement.py build  {2d,3d} OUT_DIR            Q2 records -> features.npz + rows.json (+ train-split scalers)
    python placement.py fit    {2d,3d} DATA_DIR KIND SEED  -> runs/p1_<dom>/<kind>_s<seed>/{model.pt,curve.json}
    python placement.py eval   {2d,3d} DATA_DIR SPLIT      every arm x seeds x M -> runs/p1_<dom>/eval_<split>.json
    python placement.py fit_task {2d,3d} VARIANT SEED     V3-3 task-conditioned cVAE -> $V3OUT/v3_3/<dom>/<variant>_s<seed>/"""
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
MAXOBJ = {"2d": 20, "3d": 16}               # padding only (masked, permutation-invariant encoder); 3D TRAIN NONE scenes have up to 13 objects
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


# --------------------------------------------------------------------------------------------- V3 sampling rules (plan V3 4.3, S0-S4)
def band_dist(legal, src, C):
    """Exact distribution of the band-stratified control: equal mass per non-empty Chebyshev band (1 / 2-3 / >=4 from src), uniform inside."""
    N = legal.shape[1]
    r, c = torch.arange(N, device=legal.device) // C, torch.arange(N, device=legal.device) % C
    ch = torch.maximum((r[None] - (src // C)[:, None]).abs(), (c[None] - (src % C)[:, None]).abs())
    p = torch.zeros(legal.shape, device=legal.device)
    nb = torch.zeros(legal.shape[0], 1, device=legal.device)
    for m in ((ch == 1), (ch >= 2) & (ch <= 3), (ch >= 4)):
        m = (m & legal).float()
        k = m.sum(1, keepdim=True)
        p += torch.where(k > 0, m / k.clamp(min=1), m)
        nb += (k > 0).float()
    return p / nb.clamp(min=1)


@torch.no_grad()
def marginal(m, obj, mask, occ, legal, src, n_z, gen):
    """Proposal marginal over destinations.  cVAE: Monte-Carlo estimate E_z softmax(masked decoder(c, z)) with n_z prior draws (z ~ N(0, I));
    uniform / band controls: their exact sampling distributions.  -> [B, N] (0 on illegal cells), decoder evaluations per context."""
    if isinstance(m, CVAE):
        c = m.enc(obj, mask, occ)
        B = c.shape[0]
        z = torch.randn(B, n_z, m.zdim, device=c.device, generator=gen)
        p = masked(m.dec(torch.cat([c[:, None].expand(B, n_z, -1), z], -1)), legal[:, None]).softmax(-1).mean(1)
        return p * legal, n_z
    if isinstance(m, BandStratified):
        return band_dist(legal, src, m.C), 0
    return legal.float() / legal.float().sum(1, keepdim=True).clamp(min=1), 0


@torch.no_grad()
def propose_rule(m, obj, mask, occ, legal, src, M, gen, rule, raw_mult=8, broad=None):
    """V3 sampling rules -> (unique legal destinations per context, model draws / decoder evaluations per context).
    S0 = propose() (repeat-and-dedup, raw_mult * M draws; NOT top-k); S1 = top-M of the MC marginal; S2 = Gumbel-top-M without replacement from
    the MC marginal; S3 = S2 on p^(1/tau); S4 = S2 on (1 - eps) p + eps q_broad (q_broad: 'uniform' legal or 'band' = exact band distribution)."""
    name = rule["name"]
    if name == "S0":
        out, raw, _ = propose(m, obj, mask, occ, legal, src, M, gen, raw_mult)
        return out, raw
    p, ev = marginal(m, obj, mask, occ, legal, src, rule.get("n_z", 64), gen)
    if name == "S4":
        R, C = GRID_RC(legal.shape[1], m)
        q = band_dist(legal, src, C) if rule["broad"] == "band" else legal.float() / legal.float().sum(1, keepdim=True).clamp(min=1)
        p = (1 - rule["eps"]) * p + rule["eps"] * q
    lg = torch.where(legal & (p > 0), p.clamp(min=1e-30).log() / rule.get("tau", 1.0), torch.full_like(p, -float("inf")))
    if name in ("S2", "S3", "S4"):
        u = torch.rand(lg.shape, device=lg.device, generator=gen).clamp(1e-9, 1 - 1e-9)
        lg = lg - (-u.log()).log()
    k = min(M, lg.shape[1])
    val, idx = lg.topk(k, -1)
    return [[int(d) for d, v in zip(ix, vv) if v > -float("inf")] for ix, vv in zip(idx.tolist(), val.tolist())], ev


# --------------------------------------------------------------------------------------------- V3-3 task-conditioned cVAE (same family)
def task_dim(dom):
    N = GRID[dom][0] * GRID[dom][1]
    return 2 * N + 4 + {"2d": 9, "3d": 19}[dom] + 1


CTX_GOAL = {"2d": (6, 7), "3d": (14, 15)}      # goal (x, y) inside the contracts view ctx (2D: sin q x3, cos q x3, goal xy, gap; 3D: x7, x7, goal xy, size, height, box)


def task_features(dom, inp, cells, q, on=True):
    """Inference-time task context for query object index q in scene `cells` (learner-visible only): goal one-hot, target-cell one-hot,
    query-relative goal / target offsets, the root's robot / target context vector (contracts view ctx) and task_on.  No labels, no K, no
    blocker identities.  on=True -> full; on=False -> zeros (entire task-context ablation, also the goal-masked Q2 branch);
    on="nogoal" -> goal-only ablation (V3.1-A): goal one-hot, query-to-goal offset and the goal (x, y) in ctx are zeroed, everything else kept."""
    R, C = GRID[dom]
    t = np.zeros(task_dim(dom), np.float32)
    if on is False or on is None:
        return t
    if on not in (True, "nogoal"):
        raise ValueError(f"task mode {on!r}")
    g, tc, qc = int(inp["goal_cell"]), int(cells[inp["tid"]]), int(cells[q])
    t[g], t[R * C + tc] = 1.0, 1.0
    qr, qk = divmod(qc, C)
    t[2 * R * C:2 * R * C + 4] = [(g // C - qr) / (R - 1), (g % C - qk) / (C - 1), (tc // C - qr) / (R - 1), (tc % C - qk) / (C - 1)]
    t[2 * R * C + 4:-1] = inp["ctx"]
    t[-1] = 1.0
    if on == "nogoal":
        t[g] = 0.0
        t[2 * R * C:2 * R * C + 2] = 0.0
        for j in CTX_GOAL[dom]:
            t[2 * R * C + 4 + j] = 0.0
    return t


class TaskEncoder(nn.Module):
    """Q2 SceneEncoder (unchanged) + additive task branch; input occx = [occ (N) | task features].  The task branch's last layer starts at
    zero, so a Q2-initialized TaskCVAE equals the Q2 cVAE before fine-tuning."""

    def __init__(self, N, tdim, h=128):
        super().__init__()
        self.N, self.base, self.task = N, SceneEncoder(N, 14, h), mlp(tdim, h, h, 2)
        nn.init.zeros_(self.task[-1].weight); nn.init.zeros_(self.task[-1].bias)

    def forward(self, obj, mask, occx):
        return self.base(obj, mask, occx[:, :self.N]) + self.task(occx[:, self.N:])


class TaskCVAE(CVAE):
    kind = "taskcvae"

    def __init__(self, R, C, tdim, h=128, z=8):
        super().__init__(R, C, h, z)
        self.enc, self.tdim = TaskEncoder(R * C, tdim, h), tdim

    def loss_w(self, obj, mask, occx, legal, dest, beta, w):
        """Weighted negative conditional ELBO: sum_i w_i [ -log p(d_i | z_i, c_i) + beta KL(q(z | c_i, d_i) || N(0, I)) ] / sum_i w_i."""
        c = self.enc(obj, mask, occx)
        mu, lv = self.post(torch.cat([c, Fn.one_hot(dest, self.N).float()], -1)).chunk(2, -1)
        z = mu + torch.randn_like(mu) * (0.5 * lv).exp()
        rec = Fn.cross_entropy(masked(self.dec(torch.cat([c, z], -1)), legal), dest, reduction="none")
        kl = 0.5 * (mu.pow(2) + lv.exp() - 1 - lv).sum(-1)
        ws = w.sum().clamp(min=1e-9)
        return ((rec + beta * kl) * w).sum() / ws, {"rec": float((rec * w).sum() / ws), "kl": float((kl * w).sum() / ws)}


def init_from_q2(tm, q2):
    """Copy the Q2 cVAE into a TaskCVAE (encoder -> enc.base, posterior, decoder); the zero-initialized task branch is left as is."""
    sd = q2.state_dict()
    tm.enc.base.load_state_dict({k[4:]: v for k, v in sd.items() if k.startswith("enc.")})
    tm.post.load_state_dict({k[5:]: v for k, v in sd.items() if k.startswith("post.")})
    tm.dec.load_state_dict({k[4:]: v for k, v in sd.items() if k.startswith("dec.")})
    return tm


VARIANTS = {"scratch_one": dict(init="scratch", assign="one", task=True, q2aux=False),
            "scratch_all": dict(init="scratch", assign="all", task=True, q2aux=False),
            "q2init_one": dict(init="q2", assign="one", task=True, q2aux=False),
            "q2init_all": dict(init="q2", assign="all", task=True, q2aux=False),
            "combined_one": dict(init="scratch", assign="one", task=True, q2aux=True),
            "goalablated_one": dict(init="scratch", assign="one", task=False, q2aux=False),   # historical, CONFOUNDED (init + assign + task)
            "q2init_all_nogoal": dict(init="q2", assign="all", task="nogoal", q2aux=False),    # V3.1-A matched goal-only ablation of q2init_all
            "q2init_all_notask": dict(init="q2", assign="all", task=False, q2aux=False)}       # V3.1-A matched entire-task-context ablation


def repair_data(dom, snap, split, assign, task_on, device="cuda"):
    """Repair-destination supervision (plan V3 3.2-3.3): per root the V3-legal verified Z=1 assignments (contracts.positive_assignments,
    v3_grammar) -> 'one' = the frozen primary assignment (argmin sha256('v3primary|root|key')), 'all' = every distinct assignment; one example per
    (object, destination) action with context = ORIGINAL scene S0 + task features; weight = 1 / |A_i| * 1 / |A| (six orders of one assignment
    are one target; roots without a positive give no examples, never negatives).  Static legal mask = declared support, not initially
    occupied, not the goal cell."""
    import hashlib
    import contracts as CT
    import search as S
    sc = json.loads((ROOT / "data" / f"q2_{dom}" / "scalers.json").read_text())
    mu, sd = np.array(sc["mean"], np.float32), np.array(sc["std"], np.float32)
    F, Mk, O, L, Dd, W, rid = [], [], [], [], [], [], []
    for r in map(json.loads, open(Path(snap) / f"data{dom}.jsonl")):
        if r["split"] != split:
            continue
        pa = {k: a for k, a in CT.positive_assignments(r).items() if not CT.v3_grammar(r["inputs"], a["assignment"])}
        if not pa:
            continue
        keys = sorted(pa) if assign == "all" else [min(pa, key=lambda k: hashlib.sha256(f"v3primary|{r['root_id']}|{k}".encode()).hexdigest())]
        root = S.Root(r, dom)
        cd = {root.ids[i]: c for i, c in enumerate(root.cells0)}
        lg = np.zeros(GRID[dom][0] * GRID[dom][1], bool)
        lg[root.legal_dests(root.cells0)] = True
        for k in keys:
            A = pa[k]["assignment"]
            for o, d in A:
                f, m, occ, _ = scene_features(dom, root.pattr, cd, root.ids[o], root.legal)
                assert lg[d], (r["root_id"], o, d)
                F.append((f - mu) / sd * m[:, None]); Mk.append(m); L.append(lg)
                O.append(np.concatenate([occ, task_features(dom, r["inputs"], root.cells0, o, task_on)])); Dd.append(d)
                W.append(1.0 / len(keys) / len(A)); rid.append(r["root_id"])
    T = lambda a, dt: torch.as_tensor(np.stack(a), dtype=dt, device=device)  # noqa: E731
    w = np.array(W, np.float32)
    return {"obj": T(F, torch.float32), "mask": T(Mk, torch.bool), "occx": T(O, torch.float32), "legal": T(L, torch.bool),
            "dest": torch.as_tensor(Dd, dtype=torch.long, device=device), "w": torch.as_tensor(w / w.mean(), device=device), "roots": rid}


def state_sha(m):
    """sha256 over a module's state_dict (sorted keys, CPU float bytes): checkpoint / initialization identity."""
    h = hashlib.sha256()
    for k, t in sorted(m.state_dict().items()):
        h.update(k.encode()); h.update(t.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def fit_task(dom, variant, seed, cfg=None, train_snap=None, val_snap=None, device=None):
    """Train one task-conditioned cVAE variant (TRAIN = V2 snapshot train roots; model selection = weighted negative ELBO on VALIDATION repair
    targets of the base snapshot).  Identical architecture / optimizer / epochs for every variant; only init, supervision and task input differ.
    V3.3 switches (absent = the exact historical behaviour): train_snap / val_snap or env V33_TRAIN_SNAP / V33_VAL_SNAP = explicit immutable
    snapshot dirs; device or env ABF_DEVICE (default cuda); cfg["steps"] (env V33_STEPS) = fixed optimizer-step budget with VAL evaluated every
    cfg["eval_every"] steps (env V33_EVAL_EVERY), beta warm-up counted in evaluations, best-VAL checkpoint, no early stopping."""
    v = VARIANTS[variant]
    env = {k: int(os.environ[e]) for k, e in (("steps", "V33_STEPS"), ("eval_every", "V33_EVAL_EVERY")) if os.environ.get(e)}
    cfg = {"epochs": 80, "batch": 256, "lr": 1e-3, "beta_max": 1.0, "warm": 10, "hidden": 128, "zdim": 8, "patience": 15, **env, **(cfg or {})}
    dev = device or os.environ.get("ABF_DEVICE", "cuda")
    train_snap = Path(train_snap or os.environ.get("V33_TRAIN_SNAP") or ROOT / "snapshot/abf_v2_7d146b53e4b92fe4")
    val_snap = Path(val_snap or os.environ.get("V33_VAL_SNAP") or ROOT / "snapshot/abf_9de85710c2a7103f")
    torch.manual_seed(seed)
    V3 = Path(os.environ.get("V3OUT", str(ROOT.parent / "runs")))
    tr = repair_data(dom, train_snap, "train", v["assign"], v["task"], dev)
    va = repair_data(dom, val_snap, "val", "all", v["task"], dev)
    R, C = GRID[dom]
    m = TaskCVAE(R, C, task_dim(dom), cfg["hidden"], cfg["zdim"]).to(dev)
    if v["init"] == "q2":
        init_from_q2(m, load(dom, "cvae", seed, dev))
    if "steps" in cfg:
        return _fit_task_steps(dom, variant, v, seed, cfg, m, tr, va, train_snap, val_snap, dev, V3)
    q2 = None
    if v["q2aux"]:
        D = Data(ROOT / "data" / f"q2_{dom}", dev)
        q2 = (D, torch.nonzero((D.split == 0) & (D.label == 1)).squeeze(1))
    opt = torch.optim.AdamW(m.parameters(), lr=cfg["lr"], weight_decay=1e-4)
    out = V3 / os.environ.get("V3_TASK_STAGE", "v3_3") / dom / f"{variant}_s{seed}"
    out.mkdir(parents=True, exist_ok=True)
    g = torch.Generator(device=dev).manual_seed(seed)
    n, curve, best, t0, bad = len(tr["dest"]), [], (math.inf, None), time.time(), 0
    pick = lambda d, ix: (d["obj"][ix], d["mask"][ix], d["occx"][ix], d["legal"][ix], d["dest"][ix])  # noqa: E731
    for ep in range(cfg["epochs"]):
        m.train()
        beta = cfg["beta_max"] * min(1.0, (ep + 1) / cfg["warm"])
        perm, tl = torch.randperm(n, device=dev, generator=g), []
        for i in range(0, n, cfg["batch"]):
            ix = perm[i:i + cfg["batch"]]
            l, _ = m.loss_w(*pick(tr, ix), beta, tr["w"][ix])
            if q2 is not None:                                      # goal-masked Q2 branch: task features = 0 (task_on = 0), equal-size batch
                D, pos = q2
                jx = pos[torch.randint(len(pos), (len(ix),), device=dev, generator=g)]
                occx = torch.cat([D.occ[jx], torch.zeros(len(jx), m.tdim, device=dev)], 1)
                lq, _ = m.loss_w(D.obj[jx], D.mask[jx], occx, D.legal[jx], D.dest[jx], beta, torch.ones(len(jx), device=dev))
                l = l + lq
            opt.zero_grad(); l.backward(); opt.step()
            tl.append(l.item())
        m.eval()
        with torch.no_grad():
            vl, parts = m.loss_w(*pick(va, slice(None)), cfg["beta_max"], va["w"])
        curve.append({"epoch": ep, "train": float(np.mean(tl)), "val": float(vl), **{f"val_{k}": x for k, x in parts.items()}, "beta": beta})
        if float(vl) < best[0]:
            best, bad = (float(vl), ep), 0
            torch.save({"state": m.state_dict(), "cfg": cfg, "variant": variant, "v": v, "grid": [R, C], "tdim": m.tdim, "epoch": ep}, out / "model.pt.tmp")
            os.replace(out / "model.pt.tmp", out / "model.pt")
        else:
            bad += 1
            if bad >= cfg["patience"]:
                break
    (out / "curve.json").write_text(json.dumps({"curve": curve, "best_val": best[0], "best_epoch": best[1], "cfg": cfg, "variant": v, "seed": seed,
                                                "train_examples": n, "train_roots": len(set(tr["roots"])), "val_examples": len(va["dest"]),
                                                "wall_s": round(time.time() - t0, 1), "gpu_peak_mib": round(torch.cuda.max_memory_allocated() / 2 ** 20, 1)}, indent=1))
    print(json.dumps({"dom": dom, "variant": variant, "seed": seed, "best_val": best[0], "best_epoch": best[1], "n": n, "wall_s": round(time.time() - t0, 1)}))


def _fit_task_steps(dom, variant, v, seed, cfg, m, tr, va, train_snap, val_snap, dev, V3):
    """V3.3 fixed-step training (matched optimizer steps across data arms): batches = consecutive slices of seeded permutations of this arm's
    examples (re-drawn when exhausted), VAL weighted negative ELBO (beta_max) every eval_every steps, best-VAL checkpoint, no early stopping."""
    assert not v["q2aux"], "fixed-step mode supports repair supervision only"
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731
    init_sha = state_sha(m)
    opt = torch.optim.AdamW(m.parameters(), lr=cfg["lr"], weight_decay=1e-4)
    out = V3 / os.environ.get("V3_TASK_STAGE", "v3_3") / dom / f"{variant}_s{seed}"
    out.mkdir(parents=True, exist_ok=True)
    g = torch.Generator(device=dev).manual_seed(seed)
    n, S, E, B = len(tr["dest"]), int(cfg["steps"]), int(cfg["eval_every"]), int(cfg["batch"])
    pick = lambda d, ix: (d["obj"][ix], d["mask"][ix], d["occx"][ix], d["legal"][ix], d["dest"][ix])  # noqa: E731
    prov = {"train_snapshot": str(train_snap), "train_data_sha256": sha(Path(train_snap) / f"data{dom}.jsonl"), "val_snapshot": str(val_snap),
            "val_data_sha256": sha(Path(val_snap) / f"data{dom}.jsonl"), "q2_scaler_sha256": sha(ROOT / "data" / f"q2_{dom}" / "scalers.json"),
            "init": v["init"], "init_state_sha256": init_sha, "device": dev, "torch": torch.__version__}
    curve, best, t0, step, ev, perm, pi, tl, parts_tr = [], (math.inf, None), time.time(), 0, 0, None, n, [], []
    while step < S:
        if pi >= n:
            perm, pi = torch.randperm(n, device=dev, generator=g), 0
        ix = perm[pi:pi + B]
        pi += B
        m.train()
        beta = cfg["beta_max"] * min(1.0, (ev + 1) / cfg["warm"])
        l, pt = m.loss_w(*pick(tr, ix), beta, tr["w"][ix])
        opt.zero_grad(); l.backward(); opt.step()
        step += 1
        tl.append(l.item()); parts_tr.append(pt)
        if step % E == 0 or step == S:
            m.eval()
            with torch.no_grad():
                vl, parts = m.loss_w(*pick(va, slice(None)), cfg["beta_max"], va["w"])
            curve.append({"eval": ev, "step": step, "data_epochs": round(step * B / n, 3), "train": float(np.mean(tl)),
                          "train_rec": float(np.mean([p["rec"] for p in parts_tr])), "train_kl": float(np.mean([p["kl"] for p in parts_tr])),
                          "val": float(vl), **{f"val_{k}": x for k, x in parts.items()}, "beta": beta})
            tl, parts_tr = [], []
            if float(vl) < best[0]:
                best = (float(vl), step)
                torch.save({"state": m.state_dict(), "cfg": cfg, "variant": variant, "v": v, "grid": list(GRID[dom]), "tdim": m.tdim, "epoch": ev,
                            "step": step, "prov": prov}, out / "model.pt.tmp")
                os.replace(out / "model.pt.tmp", out / "model.pt")
            ev += 1
    peak = round(torch.cuda.max_memory_allocated() / 2 ** 20, 1) if str(dev).startswith("cuda") else None
    res = {"curve": curve, "best_val": best[0], "best_step": best[1], "cfg": cfg, "variant": v, "seed": seed, "prov": prov,
           "train_examples": n, "train_roots": len(set(tr["roots"])), "val_examples": len(va["dest"]), "val_roots": len(set(va["roots"])),
           "wall_s": round(time.time() - t0, 1), "gpu_peak_mib": peak, "model_sha256": sha(out / "model.pt")}
    (out / "curve.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({"dom": dom, "variant": variant, "seed": seed, "best_val": best[0], "best_step": best[1], "n": n, "init_sha": init_sha[:12],
                      "wall_s": res["wall_s"]}))


def load_task(dom, variant, seed, device=None):
    device = device or os.environ.get("ABF_DEVICE", "cuda")
    V3 = Path(os.environ.get("V3OUT", str(ROOT.parent / "runs")))
    ck = torch.load(V3 / os.environ.get("V3_TASK_STAGE", "v3_3") / dom / f"{variant}_s{seed}" / "model.pt", map_location=device, weights_only=False)
    m = TaskCVAE(*ck["grid"], ck["tdim"], ck["cfg"]["hidden"], ck["cfg"]["zdim"]).to(device)
    m.load_state_dict(ck["state"])
    m.task_on = ck["v"]["task"]
    return m.eval()


def GRID_RC(N, m):
    return (m.R, m.C) if hasattr(m, "C") else {64: (8, 8), 36: (6, 6)}[N]


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
    elif cmd == "fit_task":
        fit_task(dom, sys.argv[3], int(sys.argv[4]))
    else:
        raise SystemExit(__doc__)
