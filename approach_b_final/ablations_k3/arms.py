#!/usr/bin/env python3
"""K<=3 ablation controls that need new code: task-conditioned Flow Matching (R5), the scratch no-task cVAE (R6), matched X/Y scorer fits
(R1-R3), and the analytical / flow proposal functions (R4, R5).  Everything else is the unchanged approach_b_final code.

    python arms.py fit xy ARM SEED DOM          xy.fit on the expanded snapshot, defaults = the frozen D fit (60 epochs, batch 64, lr 1e-3, patience 10)
    python arms.py fit notask SEED DOM          placement.fit_task(scratch_all_notask), the frozen scratch_all fixed-step budget
    python arms.py fit taskfm SEED DOM          TaskFlowMatch, same examples / weights / steps / optimizer as scratch_all
    python arms.py fit scratch_all SEED DOM     reproduction check of the frozen sampler pipeline (never used as the reference)
Outputs: $K3/runs/training/<kind>/<dom>/<name>_s<seed>/{model.pt, curve.json}."""
import hashlib, json, math, os, sys, time
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as Fn

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import placement as PL  # noqa: E402

K3 = Path(os.environ.get("K3", "."))
ABF = Path(os.environ["ABF_ROOT"])
EXP, ORIG = ABF / "snapshot/abf_v32_fb0eef4f5ff433ee", ABF / "snapshot/abf_9de85710c2a7103f"
STEPS = {"2d": (2400, 30), "3d": (1520, 19)}            # = frozen scratch_all cfg (curve.json of the bundle sampler)
PL.VARIANTS.setdefault("scratch_all_notask", dict(init="scratch", assign="all", task=False, q2aux=False))   # R6: only the task input is zeroed


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class TaskFlowMatch(torch.nn.Module):
    """R5: FlowMatch vector field (placement.FlowMatch: same time embedding, 3-layer MLP, rectified-flow target, 32 Euler steps, cell-unit
    dequantization) on the TaskCVAE encoder (TaskEncoder: Q2 scene encoder + task branch on the identical task feature vector)."""
    kind = "taskfm"

    def __init__(self, R, C, tdim, h=128, steps=32):
        super().__init__()
        self.R, self.C, self.N, self.steps, self.tdim = R, C, R * C, steps, tdim
        self.enc = PL.TaskEncoder(self.N, tdim, h)
        self.register_buffer("f", torch.exp(torch.linspace(0, math.log(100.0), 16)))
        self.register_buffer("ce", PL.centres(R, C))
        self.v = PL.mlp(2 + 32 + h, h, 2, 3)

    temb, coord = PL.FlowMatch.temb, PL.FlowMatch.coord

    def loss_w(self, obj, mask, occx, legal, dest, beta, w, gen=None):
        c = self.enc(obj, mask, occx)
        rc = torch.stack([dest // self.C, dest % self.C], -1).float() + torch.rand(dest.shape[0], 2, device=dest.device, generator=gen)
        x1 = torch.stack([2 * rc[:, 0] / self.R - 1, 2 * rc[:, 1] / self.C - 1], -1)
        x0 = torch.randn(x1.shape, device=x1.device, generator=gen)
        t = torch.rand(x1.shape[0], device=x1.device, generator=gen)
        xt = (1 - t[:, None]) * x0 + t[:, None] * x1
        l = (self.v(torch.cat([xt, self.temb(t), c], -1)) - (x1 - x0)).pow(2).sum(-1)
        ws = w.sum().clamp(min=1e-9)
        return (l * w).sum() / ws, {"fm": float(((l * w).sum() / ws).detach())}

    @torch.no_grad()
    def endpoints(self, obj, mask, occx, n, gen):
        c = self.enc(obj, mask, occx)
        B = c.shape[0]
        cc = c[:, None].expand(B, n, -1).reshape(B * n, -1)
        x = torch.randn(B * n, 2, device=c.device, generator=gen)
        for i in range(self.steps):
            x = x + self.v(torch.cat([x, self.temb(torch.full((B * n,), i / self.steps, device=c.device)), cc], -1)) / self.steps
        return x.view(B, n, 2)

    @torch.no_grad()
    def rank_dests(self, obj, mask, occx, legal, n, gen, M):
        """Predeclared empirical marginal: n endpoints -> nearest legal cell centre (FlowMatch.sample quantization) -> histogram; top-M by
        count, ties (and cells never hit) broken by the mean squared distance of the cell centre to the n endpoints, then cell index.
        -> (lists of M unique legal cells, histogram support size per context)."""
        x = self.endpoints(obj, mask, occx, n, gen)
        d2 = (x[:, :, None] - self.ce[None, None]).pow(2).sum(-1)                       # [B, n, N]
        hit = d2.masked_fill(~legal[:, None], float("inf")).argmin(-1)
        cnt = torch.zeros(legal.shape, device=x.device).scatter_add_(1, hit, torch.ones_like(hit, dtype=torch.float))
        md = d2.mean(1)
        out, sup = [], (cnt > 0).sum(1).tolist()
        for b in range(legal.shape[0]):
            cells = [int(j) for j in torch.nonzero(legal[b]).squeeze(1).tolist()]
            cells.sort(key=lambda j: (-float(cnt[b, j]), float(md[b, j]), j))
            out.append(cells[:M])
        return out, sup


def fit_taskfm(dom, seed, dev="cuda"):
    """Same examples / weights (placement.repair_data on the expanded TRAIN, VAL repair targets of the base snapshot), batch 256, AdamW lr 1e-3
    wd 1e-4, fixed steps = scratch_all; VAL criterion = weighted FM loss with a FIXED evaluation generator (seed 0), best-VAL checkpoint."""
    steps, every = STEPS[dom]
    torch.manual_seed(seed)
    tr = PL.repair_data(dom, EXP, "train", "all", True, dev)
    va = PL.repair_data(dom, ORIG, "val", "all", True, dev)
    R, C = PL.GRID[dom]
    m = TaskFlowMatch(R, C, PL.task_dim(dom)).to(dev)
    init = PL.state_sha(m)
    opt = torch.optim.AdamW(m.parameters(), lr=1e-3, weight_decay=1e-4)
    out = K3 / "runs/training/taskfm" / dom / f"taskfm_s{seed}"
    out.mkdir(parents=True, exist_ok=True)
    g = torch.Generator(device=dev).manual_seed(seed)
    n, B, curve, best, t0, step, perm, pi = len(tr["dest"]), 256, [], (math.inf, None), time.time(), 0, None, len(tr["dest"])
    pick = lambda d, ix: (d["obj"][ix], d["mask"][ix], d["occx"][ix], d["legal"][ix], d["dest"][ix])  # noqa: E731
    tl = []
    while step < steps:
        if pi >= n:
            perm, pi = torch.randperm(n, device=dev, generator=g), 0
        ix = perm[pi:pi + B]; pi += B
        m.train()
        l, _ = m.loss_w(*pick(tr, ix), None, tr["w"][ix], g)
        opt.zero_grad(); l.backward(); opt.step(); step += 1; tl.append(l.item())
        if step % every == 0 or step == steps:
            m.eval()
            with torch.no_grad():
                ge = torch.Generator(device=dev).manual_seed(0)
                vl = float(np.mean([m.loss_w(*pick(va, slice(None)), None, va["w"], ge)[0].item() for _ in range(4)]))
            curve.append({"step": step, "train": float(np.mean(tl)), "val_fm": vl}); tl = []
            if vl < best[0]:
                best = (vl, step)
                torch.save({"state": m.state_dict(), "grid": [R, C], "tdim": m.tdim, "step": step, "seed": seed, "kind": "taskfm",
                            "prov": {"train_data_sha256": sha(EXP / f"data{dom}.jsonl"), "val_data_sha256": sha(ORIG / f"data{dom}.jsonl"), "init_state_sha256": init,
                                     "torch": torch.__version__}}, out / "model.pt.tmp")
                os.replace(out / "model.pt.tmp", out / "model.pt")
    res = {"curve": curve, "best_val_fm": best[0], "best_step": best[1], "steps": steps, "eval_every": every, "batch": B, "seed": seed,
           "train_examples": n, "val_examples": len(va["dest"]), "n_params": sum(p.numel() for p in m.parameters()),
           "wall_s": round(time.time() - t0, 1), "gpu_peak_mib": round(torch.cuda.max_memory_allocated() / 2 ** 20, 1), "model_sha256": sha(out / "model.pt")}
    (out / "curve.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ("best_val_fm", "best_step", "train_examples", "n_params", "wall_s", "model_sha256")}))


def load_taskfm(path, dev="cuda"):
    ck = torch.load(path, map_location=dev, weights_only=False)
    m = TaskFlowMatch(*ck["grid"], ck["tdim"]).to(dev)
    m.load_state_dict(ck["state"])
    return m.eval()


# ----------------------------------------------------------------------------------------------- proposals (same features as search.Sampler)
def contexts(samp, root, objs):
    """search.Sampler.propose_many feature construction (S0 scene, task features on) -> tensors, legal mask, source cells."""
    cd = {root.ids[i]: c for i, c in enumerate(root.cells0)}
    legal = root.legal_dests(root.cells0)
    Fs, Ms, Os, Ls = [], [], [], []
    for o in objs:
        F, Mk, occ, _ = PL.scene_features(samp.dom, root.pattr, cd, root.ids[o], root.legal)
        lg = np.zeros(len(occ), bool)
        lg[legal] = True
        occ = np.concatenate([occ, PL.task_features(samp.dom, root.row["inputs"], root.cells0, o, True)])
        Fs.append((F - samp.mu) / samp.sd * Mk[:, None]); Ms.append(Mk); Os.append(occ); Ls.append(lg)
    T = lambda a, dt: torch.as_tensor(np.stack(a), dtype=dt, device=samp.dev)  # noqa: E731
    return T(Fs, torch.float32), T(Ms, torch.bool), T(Os, torch.float32), T(Ls, torch.bool), legal


def propose_taskfm(samp, fm, root, M=4, n=64, seed=0):
    objs = list(root.movable)
    if not objs or not root.legal_dests(root.cells0):
        return {o: [] for o in objs}, {"evals": 0, "support_lt_M": 0}
    obj, mask, occx, lg, _ = contexts(samp, root, objs)
    gen = torch.Generator(device=samp.dev).manual_seed(seed)
    out, sup = fm.rank_dests(obj, mask, occx, lg, n, gen, M)
    return dict(zip(objs, out)), {"evals": n * fm.steps * len(objs), "support_lt_M": sum(s < min(M, int(l.sum())) for s, l in zip(sup, lg))}


def propose_uniform4(root, M=4, seed=0):
    """R4 Uniform4: per (root, object) one seeded draw of M DISTINCT legal cells without replacement (never top-k on tied uniform logits)."""
    legal = root.legal_dests(root.cells0)
    out = {}
    for o in root.movable:
        rng = np.random.default_rng(int(hashlib.sha256(f"UNIFORM4|{seed}|{root.id}|{o}".encode()).hexdigest()[:16], 16))
        out[o] = [int(c) for c in rng.choice(legal, size=min(M, len(legal)), replace=False)] if legal else []
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["fit"]:
        kind, x = a[1], a[2:]
        if kind == "xy":
            import xy as XY
            os.environ["XY_RUNS"] = str(K3 / "runs/training/xy" / x[2])
            XY.fit(EXP, x[2].upper(), x[0], int(x[1]))
        elif kind in ("notask", "scratch_all"):
            os.environ.update(V3OUT=str(K3 / "runs/training"), V3_TASK_STAGE=f"{kind}_cvae")
            s, e = STEPS[x[1]]
            PL.fit_task(x[1], "scratch_all_notask" if kind == "notask" else "scratch_all", int(x[0]), {"steps": s, "eval_every": e}, EXP, ORIG, "cuda")
        elif kind == "taskfm":
            fit_taskfm(x[1], int(x[0]))
        else:
            raise SystemExit(__doc__)
    else:
        raise SystemExit(__doc__)
