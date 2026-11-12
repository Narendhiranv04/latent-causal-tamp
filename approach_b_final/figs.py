#!/usr/bin/env python3
"""Figures from recorded results only (no new labels).   python figs.py p1 {2d,3d} SPLIT"""
from __future__ import annotations

import json, os, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ABF = Path(os.environ.get("ABF_ROOT", "/scratch/nav/approachb_final"))
COL = {"cvae": "#2a6fdb", "fm": "#e07b00", "stratified": "#3a9d5d", "uniform": "#8a8a8a"}
NAME = {"cvae": "cVAE", "fm": "Flow matching", "stratified": "Band-stratified", "uniform": "Uniform"}


def p1(dom, split):
    import torch
    import placement as PL
    out = ABF / "runs" / f"p1_{dom}" / "figs"
    out.mkdir(parents=True, exist_ok=True)
    ev = json.loads((ABF / "runs" / f"p1_{dom}" / f"eval_{split}.json").read_text())
    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    for k, v in ev["arms"].items():
        Ms = sorted(int(m) for m in v["mean"])
        ax.plot(Ms, [v["mean"][str(m)]["hit"] for m in Ms], "-o", ms=4, lw=2, color=COL[k], label=NAME[k])
    ax.set_xscale("log", base=2); ax.set_xlabel("unique proposals M"); ax.set_ylabel(f"hit@M ({split})")
    ax.set_title(f"{dom.upper()} placement proposals: hit@M"); ax.grid(alpha=0.3); ax.legend(frameon=False, fontsize=8)
    fig.tight_layout(); fig.savefig(out / f"hit_at_M_{split}.png", dpi=160); plt.close(fig)
    D = PL.Data(ABF / "data" / f"q2_{dom}", "cuda")
    si = PL.SPLITS.index(split)
    cs = torch.nonzero((D.c_split == si) & D.c_pos.any(1) & D.c_neg.any(1)).squeeze(1)[:4]
    R, C = D.R, D.C
    fig, axes = plt.subplots(len(cs), 4, figsize=(10, 2.6 * len(cs)))
    for row, c in enumerate(cs.tolist()):
        i = D.c_row[c]
        obj, mask, occ, legal = D.batch(torch.tensor([int(i)], device="cuda"))
        for col, k in enumerate(("cvae", "fm", "stratified", "uniform")):
            m = PL.load(dom, k, 0)
            g = torch.Generator(device="cuda").manual_seed(0)
            props, _, _ = PL.propose(m, obj, mask, occ, legal, D.src[i:i + 1], 4, g)
            a = axes[row, col]
            grid = np.full((R, C), 0.94)
            grid[legal[0].view(R, C).cpu().numpy()] = 1.0
            a.imshow(grid, cmap="gray", vmin=0, vmax=1)
            for cell in range(R * C):
                r, cc = divmod(cell, C)
                if occ[0, cell] > 0:
                    a.add_patch(plt.Circle((cc, r), 0.32, color="#444"))
                if D.c_pos[c, cell]:
                    a.add_patch(plt.Rectangle((cc - 0.45, r - 0.45), 0.9, 0.9, fill=False, ec="#1a9850", lw=2))
                if D.c_neg[c, cell]:
                    a.add_patch(plt.Rectangle((cc - 0.45, r - 0.45), 0.9, 0.9, fill=False, ec="#d73027", lw=2))
            sr, sc = divmod(int(D.src[i]), C)
            a.add_patch(plt.Circle((sc, sr), 0.32, color="#f1c40f"))
            for p in props[0]:
                r, cc = divmod(p, C)
                a.plot(cc, r, "x", color=COL[k], ms=10, mew=2.5)
            a.set_xticks([]); a.set_yticks([])
            if row == 0:
                a.set_title(NAME[k], fontsize=9)
    fig.suptitle(f"{dom.upper()} {split}: queried object (yellow), other objects (grey), recorded feasible (green) / failed (red) "
                 "destinations, 4 proposals (x); unmarked legal cells are untested", fontsize=8)
    fig.tight_layout(); fig.savefig(out / f"proposals_{split}.png", dpi=150); plt.close(fig)
    print(out)


if __name__ == "__main__":
    {"p1": lambda: p1(sys.argv[2], sys.argv[3])}[sys.argv[1]]()
