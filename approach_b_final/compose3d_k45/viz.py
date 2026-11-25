"""Figures from REAL scene geometry (public 3D rows: cells, box / cylinder footprints, heights).  Top-down shelf grids with numbered, group-
coloured relocation arrows and q_ref boundary marks, plus a 3D block view drawn from the same sizes / heights (a geometric drawing, not a
simulator screenshot).  Hypothetical plans are labelled as such; physical outcomes come only from the evaluator's teacher records."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

INK, MUTED, RED, GREEN, BLUE, ORANGE, PURPLE = "#1f2328", "#6e7781", "#cf222e", "#1a7f37", "#2f6fdf", "#e07b00", "#8250df"
GCOL = [BLUE, ORANGE, PURPLE, GREEN, RED]


def rc(c):
    return divmod(int(c), 6)


def top(ax, inp, seq=None, part=None, title="", cells=None):
    """Shelf seen from above: row 0 (nearest the robot) at the bottom; arrows = ordered moves, colour = group, '|q_ref' after each group."""
    cells = list(inp["cells0"]) if cells is None else cells
    for r in range(6):
        for c in range(6):
            ax.add_patch(plt.Rectangle((c - .5, r - .5), 1, 1, fc="#f6f8fa", ec="#d0d7de", lw=.6))
    g = rc(inp["goal_cell"]); ax.add_patch(plt.Rectangle((g[1] - .45, g[0] - .45), .9, .9, fc="none", ec=GREEN, lw=2.2))
    for i, a in enumerate(inp["attrs"]):
        r, c = rc(cells[i]); s = a[2] / 0.075 * 1.6
        col = RED if i == inp["tid"] else MUTED
        if a[0] > .5:
            ax.add_patch(plt.Rectangle((c - s, r - s), 2 * s, 2 * s, fc=col, ec="white", lw=.8, zorder=3))
        else:
            ax.add_patch(plt.Circle((c, r), s, fc=col, ec="white", lw=.8, zorder=3))
        ax.text(c, r, "T" if i == inp["tid"] else str(i), ha="center", va="center", color="white", fontsize=6.5, zorder=4)
    if seq:
        part = part or [len(seq)]
        gi, k, cur = 0, 0, list(cells)
        bounds = np.cumsum(part)
        for j, (o, d) in enumerate(seq):
            while j >= bounds[gi]:
                gi += 1
            a, b = rc(cur[int(o)]), rc(d)
            ax.annotate("", (b[1], b[0]), (a[1], a[0]), arrowprops=dict(arrowstyle="-|>", color=GCOL[gi % 5], lw=1.8), zorder=5)
            ax.text(b[1] + .28, b[0] + .28, f"{j + 1}" + ("|q" if (j + 1) in bounds[:-1] else ""), color=GCOL[gi % 5], fontsize=7, zorder=6, weight="bold")
            cur[int(o)] = int(d)
    ax.set_xlim(-.6, 5.6); ax.set_ylim(-.6, 5.6); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(title, fontsize=7.5, loc="left")
    ax.text(2.5, -.95, "robot side (row 0)", ha="center", fontsize=6, color=MUTED)


def blocks3d(ax, inp, cells=None, title=""):
    cells = list(inp["cells0"]) if cells is None else cells
    for i, a in enumerate(inp["attrs"]):
        r, c = rc(cells[i]); s = a[2] / 0.075; h = a[3] / 0.075
        ax.bar3d(c - s, r - s, 0, 2 * s, 2 * s, h, color=(RED if i == inp["tid"] else "#8c959f"), alpha=.9, shade=True)
    g = rc(inp["goal_cell"]); ax.bar3d(g[1] - .4, g[0] - .4, 0, .8, .8, .02, color=GREEN, alpha=.5)
    ax.set_xlim(-.5, 5.5); ax.set_ylim(-.5, 5.5); ax.set_zlim(0, 3); ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([])
    ax.set_title(title, fontsize=7.5); ax.view_init(28, -110)


def roster(rows, labels, out):
    n = len(rows); cols = 5; rws = (n + cols - 1) // cols
    fig = plt.figure(figsize=(3.1 * cols, 3.0 * rws * 2))
    for k, r in enumerate(rows):
        ax = fig.add_subplot(rws * 2, cols, (k // cols) * 2 * cols + k % cols + 1)
        top(ax, r["inputs"], title=f"{r['root_id'].split('-k45-')[-1]}  {labels.get(r['root_id'], '')}  n_obj={len(r['inputs']['ids'])}")
        ax3 = fig.add_subplot(rws * 2, cols, (k // cols) * 2 * cols + cols + k % cols + 1, projection="3d")
        blocks3d(ax3, r["inputs"])
    fig.suptitle("P1 sealed K4/K5 cohort: public initial scenes (red = target T, green square = goal; grey = other objects; drawn from real cells / sizes / heights)", fontsize=9, color=MUTED)
    fig.savefig(out, dpi=110, bbox_inches="tight", facecolor="white"); plt.close(fig)
