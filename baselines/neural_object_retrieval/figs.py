#!/usr/bin/env python3
"""NOR-Grid scene-backed figures from PUBLIC root geometry (+ TRAIN-only labels / sealed predictions where stated).
Top-down cell grid (2D 8x8 lattice / 3D 6x6 shelf), objects drawn at their real poses and sizes; target red outline, goal star,
fixed objects grey, movable objects white; hypothetical placements dashed (never shown as executed motion).

    figs.py labels DOM LABELS.jsonl ROOT_ID OUT.png          P2: reference-path sweep union, per-object blocking counts, RPNet cost map
    figs.py policy DOM PUBLIC.jsonl PRED.jsonl ROOT_ID OUT.png   P5: OSNet / RPNet rollout of a sealed prediction"""
import json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import graph as G  # noqa: E402

INK, MUTED, GRID = "#1f2328", "#6e7781", "#d0d7de"
SEQ = plt.get_cmap("Blues")


def base(ax, inp, dom, cells=None, title=""):
    cells = cells or [int(c) for c in inp["cells0"]]
    xy = {int(k): np.array(v) for k, v in inp["cell_xy"].items()}
    pitch = 0.08 if dom == "2d" else 0.075
    for c, p in xy.items():
        ax.add_patch(plt.Rectangle(p - pitch / 2, pitch, pitch, fill=False, ec=GRID, lw=0.6))
    fixed = [bool(a[3]) for a in inp["attrs"]] if dom == "2d" else [False] * len(inp["ids"])
    for i, oid in enumerate(inp["ids"]):
        p = xy[cells[i]] if cells[i] != int(inp["cells0"][i]) else np.array(inp["xy0"][i])
        r = inp["attrs"][i][0] if dom == "2d" else max(inp["attrs"][i][2], 0.015)
        fc = "#8c959f" if fixed[i] else "white"
        if dom == "3d" and inp["attrs"][i][0] > 0.5:
            ax.add_patch(plt.Rectangle(p - r, 2 * r, 2 * r, fc=fc, ec=INK, lw=1.0, zorder=3))
        else:
            ax.add_patch(plt.Circle(p, r, fc=fc, ec=INK, lw=1.0, zorder=3))
        if i == inp["tid"]:
            ax.add_patch(plt.Circle(p, r * 1.25, fill=False, ec="#cf222e", lw=2.0, zorder=4))
        ax.text(*p, oid[-2:] if i != inp["tid"] else "T", ha="center", va="center", fontsize=6, color=INK, zorder=5)
    g = xy[int(inp["goal_cell"])]
    ax.plot(*g, marker="*", ms=12, color="#cf222e", mec="white", zorder=6)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(title, fontsize=9, color=INK)
    return xy, pitch


def labels(dom, lab, rid, out):
    import nor_data as DA
    import samples as SM
    r = next(x for x in DA.rows(dom, DA.BASE, "train") if x["root_id"] == rid)
    e = next(json.loads(l) for l in open(lab) if json.loads(l)["root_id"] == rid)
    inp = r["inputs"]
    P = SM.paths_of(e, dom, inp)
    cells = G.apply(inp, [])
    cnt = SM.counts(inp, dom, cells, P)
    top = max(sorted(cnt), key=lambda o: cnt[o])
    cost = SM.cost_map(inp, cells, P, top, G.NCELL[dom])
    fig, axs = plt.subplots(1, 2, figsize=(11, 5.6))
    xy, pitch = base(axs[0], inp, dom, title=f"{rid} (K={r['K_legacy']})\nOSNet label: blocking counts over {len(P)} reference paths")
    for c in xy:
        f = sum(c in p["sweep"] for p in P) / max(1, len(P))
        if f:
            axs[0].add_patch(plt.Rectangle(xy[c] - pitch / 2, pitch, pitch, fc=plt.get_cmap("Oranges")(0.1 + 0.6 * f), ec="none", zorder=1))
    for o, c in cnt.items():
        if c:
            axs[0].text(*(np.array(inp["xy0"][o]) + [0, pitch * 0.42]), f"{c}/{len(P)}", ha="center", fontsize=7, color="#9a6700", zorder=6)
    base(axs[1], inp, dom, title=f"RPNet label: region cost for top blocker {inp['ids'][top]}\n(darker = lower cost = preferred)")
    for c, p in xy.items():
        axs[1].add_patch(plt.Rectangle(p - pitch / 2, pitch, pitch, fc=SEQ(0.95 - 0.75 * cost[c] / 0.9) if cost[c] < 1 else "#eaeef2", ec="none", zorder=1))
    fig.text(0.5, 0.01, "TRAIN-only labels. Orange shade = fraction of collision-ignorant reference paths whose arm / gripper / carried-target sweep "
             "reaches the cell.\nGrey = cost 1 (statically illegal, or swept by >= half of the paths).  Red ring = target, star = its goal, grey disc = fixed.",
             ha="center", fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.07, 1, 0.95)); fig.savefig(out, dpi=150); plt.close(fig)


def policy(dom, pub, pred, rid, out):
    r = next(json.loads(l) for l in open(pub) if json.loads(l)["root_id"] == rid)
    p = next(json.loads(l) for l in open(pred) if json.loads(l)["root_id"] == rid)
    inp = r["inputs"]
    fig, ax = plt.subplots(figsize=(5.6, 6.0))
    xy, pitch = base(ax, inp, dom, title=f"{rid}: {p['decision']}\nSTOP p per prefix k=0..3: {[round(x, 3) for x in p['stop_probs']]}")
    cells = [int(c) for c in inp["cells0"]]
    for k, (o, d) in enumerate(p["rollout"]):
        a, b = xy[cells[o]], xy[d]
        used = k < len(p["moves"])
        ax.annotate("", b, a, arrowprops=dict(arrowstyle="->", color=INK if used else MUTED, ls="-" if used else ":", lw=1.4), zorder=7)
        ax.add_patch(plt.Circle(b, pitch * 0.3, fill=False, ec=INK if used else MUTED, ls="--", zorder=7))
        ax.text(*(b + [0, -pitch * 0.45]), str(k + 1), ha="center", fontsize=7, color=INK)
        cells[o] = d
    fig.text(0.5, 0.01, "hypothetical placements (dashed), not executed motion\nsolid = selected prefix, dotted = rollout beyond STOP",
             ha="center", fontsize=6.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.05, 1, 0.97)); fig.savefig(out, dpi=150); plt.close(fig)


if __name__ == "__main__":
    a = sys.argv
    if a[1] == "labels":
        labels(a[2], a[3], a[4], a[5])
    else:
        policy(a[2], a[3], a[4], a[5], a[6])
