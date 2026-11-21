#!/usr/bin/env python3
"""G6 figures for the released scenes (pure drawing from the private witness/label files; no physics).
  overview   one panel per accepted scene: 8x8 lattice (robot base on the left, column 0), discs, target (red), goal (dashed), the verified
             witness as numbered arrows (step j: object -> destination), K and object count in the title
  gif        per scene, a schematic step-by-step animation of the verified relocation sequence followed by the target move (frames = lattice
             states after each relocation; the physical replay itself is the teacher's independent replay recorded in G5)
    python viz_release.py LAYOUTS.jsonl G5_LABELS.jsonl OUT_DIR"""
import json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.animation import FuncAnimation, PillowWriter  # noqa: E402

T_COL, G_COL, O_COL, M_COL, GRID, INK, MUTED = "#b4441c", "#1baf7a", "#9a9a96", "#2a78d6", "#e6e6e6", "#222222", "#7a7975"


def xy(c):
    return c % 8, c // 8


def board(ax):
    ax.set_xlim(-0.6, 7.6); ax.set_ylim(-0.6, 7.6); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    for k in range(9):
        ax.plot([k - 0.5] * 2, [-0.5, 7.5], color=GRID, lw=0.6); ax.plot([-0.5, 7.5], [k - 0.5] * 2, color=GRID, lw=0.6)
    ax.add_patch(plt.Rectangle((-0.58, 2.5), 0.12, 3, color=MUTED))          # robot base side marker (left edge)
    for s in ax.spines.values():
        s.set_color(MUTED)


def draw_state(ax, cells, goal, moved=(), hl=None):
    board(ax)
    gx, gy = xy(goal)
    ax.add_patch(plt.Rectangle((gx - 0.45, gy - 0.45), 0.9, 0.9, fill=False, ec=G_COL, lw=2, ls="--"))
    for i, c in enumerate(cells):
        x, y = xy(c)
        col = T_COL if i == 0 else (M_COL if i in moved else O_COL)
        ax.add_patch(plt.Circle((x, y), 0.36, color=col, ec="white" if i != hl else INK, lw=1.5 if i == hl else 0.8))


def overview(rows, out):
    n = len(rows)
    nc = 5
    nr = (n + nc - 1) // nc
    fig, axs = plt.subplots(nr, nc, figsize=(3.0 * nc, 3.25 * nr))
    axs = [a for r in (axs if nr > 1 else [axs]) for a in r]
    for ax, (L, g5) in zip(axs, rows):
        ids = [f"t0"] + [f"o{i:02d}" for i in range(len(L["cells0"]) - 1)]
        idx = {k: i for i, k in enumerate(ids)}
        moved = [idx[o] for o, _ in g5["witness"]]
        draw_state(ax, L["cells0"], L["goal_cell"], moved)
        for j, (o, d) in enumerate(g5["witness"], 1):
            x0, y0 = xy(L["cells0"][idx[o]]); x1, y1 = xy(d)
            ax.annotate("", (x1, y1), (x0, y0), arrowprops=dict(arrowstyle="->", color=M_COL, lw=1.1, shrinkA=6, shrinkB=6))
            ax.text(x1, y1, str(j), ha="center", va="center", fontsize=6.5, color=M_COL, fontweight="bold",
                    bbox=dict(boxstyle="circle,pad=0.12", fc="white", ec=M_COL, lw=0.6))
        ax.set_title(f"K={g5['K']}  {L['root_id']}\n{len(L['cells0'])} objects  {g5['verdict']}", fontsize=7.5, color=INK)
    for ax in axs[n:]:
        ax.axis("off")
    fig.text(0.01, 0.004, "red = target, dashed green = goal, blue = relocated by the verified witness (numbers = step order and destination), "
             "grey = untouched; robot base on the left edge", fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0.012, 1, 1)); fig.savefig(out, dpi=150); plt.close(fig)


def gif(L, g5, out):
    ids = ["t0"] + [f"o{i:02d}" for i in range(len(L["cells0"]) - 1)]
    idx = {k: i for i, k in enumerate(ids)}
    states, cur, moved = [(list(L["cells0"]), (), None, "initial layout (Y = 0, certified)")], list(L["cells0"]), []
    for j, (o, d) in enumerate(g5["witness"], 1):
        cur = list(cur); cur[idx[o]] = d; moved = moved + [idx[o]]
        states.append((cur, tuple(moved), idx[o], f"relocation {j}/{g5['K']}: {o} -> cell {d}" + ("  (Y = 0)" if j < g5["K"] else "  (Y = 1)")))
    fin = list(cur); fin[0] = L["goal_cell"]
    states.append((fin, tuple(moved), 0, "target placed at goal (X = 1, Y = 1, replayed)"))
    fig, ax = plt.subplots(figsize=(3.6, 3.9))

    def frame(k):
        ax.clear(); c, m, hl, cap = states[k]
        draw_state(ax, c, L["goal_cell"], m, hl)
        ax.set_title(f"{L['root_id']}  K={g5['K']}\n{cap}", fontsize=7.5, color=INK)
    an = FuncAnimation(fig, frame, frames=len(states), interval=900)
    an.save(out, writer=PillowWriter(fps=1.1)); plt.close(fig)


def main(lay_f, g5_f, od):
    od = Path(od); (od / "gifs").mkdir(parents=True, exist_ok=True)
    Ls = {json.loads(l)["root_id"]: json.loads(l) for l in open(lay_f)}
    G = [json.loads(l) for l in open(g5_f)]
    rows = sorted([(Ls[g["root_id"]], g) for g in G], key=lambda r: (r[1]["K"], r[0].get("accepted_rank", 0), r[0]["root_id"]))
    overview(rows, od / "overview_final.png")
    for L, g in rows:
        gif(L, g, od / "gifs" / f"K{g['K']}_{L['root_id']}.gif")
    print("figures ->", od, len(rows))


if __name__ == "__main__":
    main(*sys.argv[1:4])
