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


OKABE = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9"]


def draw_root(a, inp, arrows=(), title="", heat=None):
    """Grid view of a root from learner inputs (2D 8x8 lattice / 3D 6x6 shelf, top view): objects, target (T), goal (G), optional proposal heat,
    arrows [(obj idx, dest cell, colour, label)].  Recorded labels only; no robot motion is drawn."""
    R, C = inp["grid"]
    rc = lambda c: divmod(int(c), C)  # noqa: E731
    g = np.full((R, C), 0.92)
    for c in inp["legal_cells"]:
        g[rc(c)] = 1.0
    a.imshow(g, cmap="gray", vmin=0, vmax=1)
    if heat is not None:
        a.imshow(np.ma.masked_less_equal(np.asarray(heat, float).reshape(R, C), 0), cmap="Blues", alpha=0.75, vmin=0)
    gr, gc = rc(inp["goal_cell"])
    a.add_patch(plt.Rectangle((gc - 0.45, gr - 0.45), 0.9, 0.9, fill=False, ec="#d62728", lw=2, ls="--"))
    a.text(gc, gr + 0.38, "G", ha="center", va="center", fontsize=7, color="#d62728")
    for i, c in enumerate(inp["cells0"]):
        r, k = rc(c)
        fixed = len(inp["attrs"][i]) == 4 and inp["attrs"][i][3] and i != inp["tid"]
        a.add_patch(plt.Circle((k, r), 0.3, color="#d62728" if i == inp["tid"] else ("#222" if fixed else "#777")))
        a.text(k, r, "T" if i == inp["tid"] else str(inp["ids"][i])[-2:], ha="center", va="center", fontsize=6, color="white")
    for j, (o, d, col, lab) in enumerate(arrows):
        (r0, k0), (r1, k1) = rc(inp["cells0"][o]), rc(d)
        a.annotate("", (k1, r1), (k0, r0), arrowprops=dict(arrowstyle="-|>", color=col, lw=1.8, shrinkA=6, shrinkB=4))
        a.add_patch(plt.Rectangle((k1 - 0.4, r1 - 0.4), 0.8, 0.8, fill=False, ec=col, lw=1.8))
    a.set_xticks([]); a.set_yticks([]); a.set_title(title, fontsize=8)


def v3_0(audit_dir, snap, examples):
    """V3-0: distinct verified Z = 1 assignments per TRAIN root (base vs V2) + one 2D / one 3D root with its assignments and orders."""
    audit_dir = Path(audit_dir)
    A = json.loads((audit_dir / "V3_0_AUDIT.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.2))
    for a, dom in zip(axes, ("2d", "3d")):
        w, x = 0.38, np.arange(3)
        for j, name in enumerate(("base", "v2")):
            n = A["domains"][dom][name]["n_v3_legal_assignments_per_root"]
            bottom = np.zeros(3)
            for b, shade in zip(range(5), ("#bbbbbb", "#0072B2", "#56B4E9", "#E69F00", "#CC79A7")):
                tot = np.array([sum(v for k, v in n.items() if k.startswith(f"train|{K}|")) for K in "123"], float)
                h = np.array([n.get(f"train|{K}|{b}", 0) for K in "123"]) / np.maximum(tot, 1)
                a.bar(x + (j - 0.5) * w, h, w * 0.92, bottom=bottom, color=shade, edgecolor="white", lw=0.8,
                      label=(["0", "1", "2", "3", ">=4"][b] if j == 0 else None))
                bottom += h
            for xi in x:
                a.text(xi + (j - 0.5) * w, 1.02, name, ha="center", fontsize=7)
        a.set_xticks(x, [f"K{K}" for K in "123"]); a.set_ylim(0, 1.1); a.set_ylabel("fraction of TRAIN roots")
        a.set_title(f"{dom.upper()}: distinct verified Z=1 assignments per root", fontsize=9)
    axes[1].legend(title="# assignments", frameon=False, fontsize=7, title_fontsize=7, loc="center left", bbox_to_anchor=(1.0, 0.5))
    fig.tight_layout(); fig.savefig(audit_dir / "assignments_per_root.png", dpi=160); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.4))
    for a, (dom, rid) in zip(axes, examples):
        row = next(r for r in map(json.loads, open(Path(snap) / f"data{dom}.jsonl")) if r["root_id"] == rid)
        led = next(r for r in map(json.loads, open(audit_dir / f"assignments_{dom}.jsonl")) if r["root_id"] == rid)
        arrows, lines = [], []
        for j, asg in enumerate(led["assignments"][:4]):
            col = OKABE[j]
            arrows += [(o, d, col, "") for o, d in asg["assignment"]]
            ids = row["inputs"]["ids"]
            okey = lambda s: " > ".join(f"{str(ids[o])[-2:]}->{d}" for o, d in s)  # noqa: E731
            lines.append((col, f"A{j + 1} [{asg['source']}]: {asg['n_success_orders']} X=1 order(s), {asg['n_failed_orders']} X=0"))
            lines += [(col, "   ok  " + okey(s)) for s in asg["orders"][:3]]
        draw_root(a, row["inputs"], arrows, f"{dom.upper()} TRAIN {rid} (legacy K{row['K_legacy']})")
        for i, (col, t) in enumerate(lines[:12]):
            a.text(0.0, -0.08 - 0.055 * i, t, transform=a.transAxes, fontsize=6, color=col, va="top", family="monospace")
    fig.suptitle("Each colour = one verified unordered assignment (ONE cVAE target set); its X=1 orders are separate Boltzmann observations "
                 "(recorded labels only)", fontsize=8)
    fig.subplots_adjust(bottom=0.36, top=0.9, wspace=0.15); fig.savefig(audit_dir / "assignment_vs_order_examples.png", dpi=160); plt.close(fig)
    print(audit_dir)


if __name__ == "__main__":
    {"p1": lambda: p1(sys.argv[2], sys.argv[3]),
     "v3_0": lambda: v3_0(sys.argv[2], sys.argv[3], [("2d", sys.argv[4]), ("3d", sys.argv[5])])}[sys.argv[1]]()
