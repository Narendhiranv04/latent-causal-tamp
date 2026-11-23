#!/usr/bin/env python3
"""Figures (real public 2D VAL scenes; every probability is a FROZEN-MODEL value, never a certificate; verified = independent teacher).
  p1        P1 recall: legal grid, frozen cVAE prior heatmap of the witness object(s), top-4 / rank 5-6 / tail cells, known verified witness
  alloc     P2: tier-release / eligible-expanded-scored curves for SEEDED4 vs FULL MCTS and beam on one DEV root (model-only)
  curves    P2: model-only regret / agreement vs B_score and LIVE wall time
  physical  P4: verified success (strict and operational), paired deltas, latency
    python figs.py p1|alloc|curves|physical"""
from __future__ import annotations

import collections, json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import run as RUN  # noqa: E402

FIG = HERE / "reports" / "figures"
INK, MUTED, BLUE, RED, GREEN, ORANGE, PURPLE, GREY = "#222222", "#6b6a66", "#2a78d6", "#b4441c", "#1a9e6e", "#e07b00", "#7b5ea7", "#b9b8b3"
ARMC = {"EXACT4": INK, "EXACT6": MUTED, "EXACT_FULL": "#000000", "RAND_FULL": GREY, "BEAM_SEEDED4": ORANGE, "BEAM_FULL": "#f2b366",
        "BEAM_FULL_UNIFORM": "#f6d6a8", "PW_MCTS_SEEDED4": BLUE, "PW_MCTS_FULL": PURPLE, "PW_MCTS_UNIFORM": "#c4b5dc"}


def scene(ax, row, dom, obj=None, arrows=(), title=""):
    """All public legal cells; frozen prior of `obj` as a single-hue heatmap; rings = top-4 (solid) / rank 5-6 (dashed) of `obj`."""
    inp = row["inputs"]; xy = {int(k): v for k, v in inp["cell_xy"].items()}; c0 = [int(c) for c in inp["cells0"]]
    if obj is not None:
        p = np.array([dom.raw[(obj, d)] for d in dom.L]); v = p / p.max()
        ax.scatter([xy[d][0] for d in dom.L], [xy[d][1] for d in dom.L], s=150, c=v, cmap="Blues", vmin=0, vmax=1, marker="s", zorder=1, lw=0)
        for d in dom.D6[obj][:4]:
            ax.scatter(*xy[d], s=230, facecolors="none", edgecolors=INK, lw=1.4, marker="s", zorder=2)
        for d in dom.D6[obj][4:6]:
            ax.scatter(*xy[d], s=230, facecolors="none", edgecolors=INK, lw=1.0, ls="--", marker="s", zorder=2)
    else:
        ax.scatter([xy[d][0] for d in dom.L], [xy[d][1] for d in dom.L], s=120, color="#ececea", marker="s", zorder=1, lw=0)
    for i, c in enumerate(c0):
        t = i == inp["tid"]; mv = i in dom.objs
        ax.scatter(*xy[c], s=240, color=RED if t else (MUTED if mv else "#3d3d3a"), edgecolor="white", zorder=3)
        ax.text(*xy[c], "T" if t else str(i), ha="center", va="center", fontsize=6.5, color="white", zorder=4)
    ax.scatter(*xy[int(inp["goal_cell"])], s=300, facecolors="none", edgecolors=GREEN, lw=2.2, marker="s", zorder=3)
    for j, (o, d, col) in enumerate(arrows):
        ax.annotate("", xy[d], xy[c0[o]], arrowprops=dict(arrowstyle="-|>", color=col, lw=1.8), zorder=5)
        ax.scatter(*xy[d], s=90, marker="*", color=col, zorder=6)
        ax.text(xy[d][0], xy[d][1] + 0.025, f"{j + 1}", fontsize=7, color=col, ha="center", zorder=6)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([]); ax.set_title(title, fontsize=7.2, loc="left")
    for s in ax.spines.values():
        s.set_visible(False)


def p1(n=4):
    """First n EVAL K1/K2 roots (MCTS_ORDER) where the old EXACT4 pick was NOT a verified success and every known K<=2 witness lies
    outside the frozen top-4 pool (the P1 pool-miss candidates).  Analysis-only use of private labels; nothing here feeds the planner."""
    samp, scor, man = RUN.models()
    pr = {p["root_id"]: p for p in map(json.loads, open(Path.home() / "fds_private/P1_PER_ROOT_PRIVATE.jsonl"))}
    W = collections.defaultdict(list)
    for w in map(json.loads, open(Path.home() / "fds_private/P1_WITNESSES_PRIVATE.jsonl")):
        if w["category"] in ("TOP4", "RANK5_6", "BEYOND6"):
            W[w["root_id"]].append(w)
    pick = [r for r in RUN.root_rows(None, "EVAL") if pr[r["root_id"]]["K"] in ("1", "2") and pr[r["root_id"]]["exact4_outcome"] not in (None, "SUCCESS")
            and W[r["root_id"]] and all(w["category"] != "TOP4" for w in W[r["root_id"]])][:n]
    FIG.mkdir(parents=True, exist_ok=True); out = []
    for r in pick:
        root, dom, _ = RUN.build(r, samp, man, 0.25)
        w = sorted(W[r["root_id"]], key=lambda w: (-w["primary_source"], max(w["ranks"]), json.dumps(w["seq"])))[0]
        objs = sorted({o for o, _ in w["seq"]})
        fig, axs = plt.subplots(1, len(objs), figsize=(5.4 * len(objs), 6.4), squeeze=False)
        rk = {oo: dom.rank[(oo, d)] + 1 for oo, d in w["seq"]}
        for ax, o in zip(axs[0], objs):
            arr = [(oo, d, BLUE if oo == o else MUTED) for oo, d in w["seq"]]
            scene(ax, r, dom, o, arr, f"heatmap: frozen cVAE marginal of object {o} (rank of its witness cell: {rk[o]})")
        fig.suptitle(f"{r['root_id']}  |  VAL EVAL, K{pr[r['root_id']]['K']}  |  old EXACT4 (top-4 pool) verified outcome: {pr[r['root_id']]['exact4_outcome']}\n"
                     f"Known VERIFIED witness {[list(x) for x in w['seq']]} (source {'+'.join(w['sources'])}); stratum {w['stratum']}; numbers = witness order.\n"
                     f"Squares = all {len(dom.L)} public legal cells; solid ring = top-4, dashed ring = rank 5-6; green = goal; T = target.\n"
                     f"Frozen X/Y p11 of the witness (best order) = {w['p11_best_order']:.3f}: a model PREDICTION, not a verification.",
                     fontsize=8, x=0.01, ha="left", y=0.995)
        fig.tight_layout(rect=(0, 0, 1, 0.86))
        f = FIG / f"p1_root_{r['root_id']}.png"; fig.savefig(f, dpi=130); plt.close(fig)
        out.append({"root_id": r["root_id"], "figure": f.name, "witness_ranks": w["ranks"], "stratum": w["stratum"]})
    (HERE / "reports" / "P1_FIGURES.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))


if __name__ == "__main__":
    {"p1": p1}[sys.argv[1]]()
