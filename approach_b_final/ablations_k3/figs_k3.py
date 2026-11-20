#!/usr/bin/env python3
"""Figures rebuilt only from $K3/runs/tables/*.json and sealed predictions / results (python figs_k3.py SPLIT).
1 placement recall + known-assignment-in-pool per sampler; 2 paired physical success (95 % CI) by K, K0 NOOP, NONE ABSTAIN; 3 same-endpoint order
ranking (D vs E/G/DIRECT); 4 common-Z reliability per scorer; 5 cost vs success; 6 error breakdown; 7 illustrative 2D scenes (VAL, fixed roots)."""
import collections, json, os, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

K3 = Path(os.environ["K3"])
TAB, FIG = K3 / "runs/tables", K3 / "runs/figures"
PRIMARY = ["FULL_s0", "E_s0", "G_s0", "DIRECT_s0", "UNIFORM4_r0", "TASKFM_s0", "NOTASK_s0", "M1", "C1_r0"]
LABEL = {"FULL_s0": "FULL", "E_s0": "E (no coupling)", "G_s0": "G (order-inv.)", "DIRECT_s0": "DIRECT", "UNIFORM4_r0": "Uniform4",
         "TASKFM_s0": "TaskFM", "NOTASK_s0": "No task ctx", "M1": "M1", "C1_r0": "C1", "DREFIT_s0": "D refit (env.)"}
INK, MUTED, ACC = "#1f2328", "#6e7781", "#2f6fb0"


def style(ax, title):
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="x", color="#d0d7de", lw=0.6)
    ax.tick_params(colors=MUTED, labelsize=8)


def forest(split):
    for dom in ("2d", "3d"):
        T = json.loads((TAB / f"physical_{split}_{dom}.json").read_text())["arms"]
        keys = [("task_Kall", "Task K1-K3"), ("task_K1", "K1"), ("task_K2", "K2"), ("task_K3", "K3"), ("noop_K0", "K0 NOOP"), ("abstain_KNONE", "NONE ABSTAIN")]
        fig, axs = plt.subplots(1, len(keys), figsize=(3.0 * len(keys), 3.6), sharey=True)
        arms = [a for a in PRIMARY if a in T]
        for ax, (k, t) in zip(axs, keys):
            for i, a in enumerate(arms):
                p, lo, hi = T[a][k]["rate_ci"]
                if p is None:
                    continue
                ax.plot([lo, hi], [i, i], color=ACC if a == "FULL_s0" else MUTED, lw=2, solid_capstyle="round")
                ax.plot(p, i, "o", ms=6, color=ACC if a == "FULL_s0" else INK, mec="white", mew=1.5)
            style(ax, t)
            ax.set_xlabel("% (95% CI)", fontsize=8, color=MUTED)
        axs[0].set_yticks(range(len(arms)), [LABEL[a] for a in arms]); axs[0].invert_yaxis()
        fig.suptitle(f"Physically verified outcomes, {split.upper()} {dom.upper()} (lineage-cluster bootstrap)", fontsize=11, color=INK, x=0.01, ha="left")
        fig.tight_layout(); fig.savefig(FIG / f"F2_physical_{split}_{dom}.png", dpi=170); plt.close(fig)


def placement(split):
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.4))
    for ax, dom in zip(axs, ("2d", "3d")):
        T = json.loads((TAB / f"placement_{split}_{dom}.json").read_text())
        arms = [a for a in ("FULL_s0", "TASKFM_s0", "NOTASK_s0", "UNIFORM4_r0", "M1") if a in T]
        y = np.arange(len(arms))
        ax.barh(y - 0.18, [100 * T[a]["ingredient_recall"] for a in arms], 0.34, color=ACC, label="ingredient recall")
        ax.barh(y + 0.18, [100 * T[a]["known_assignment_in_pool"] for a in arms], 0.34, color="#9fb7d4", label="known assignment in pool")
        ax.set_yticks(y, [LABEL[a] for a in arms]); ax.invert_yaxis()
        style(ax, f"{dom.upper()} placement diagnostics (K1-K3, {split.upper()})"); ax.set_xlabel("%", fontsize=8, color=MUTED)
    axs[0].legend(fontsize=7, frameon=False, loc="lower right")
    fig.tight_layout(); fig.savefig(FIG / f"F1_placement_{split}.png", dpi=170); plt.close(fig)


def order_rank(split):
    fig, axs = plt.subplots(1, 2, figsize=(9, 2.8))
    for ax, dom in zip(axs, ("2d", "3d")):
        T = json.loads((TAB / f"scorer_{split}_{dom}.json").read_text())
        tags = [t for t in ("D_s0", "E_s0", "G_s0", "DIRECT_s0") if t in T and T[t].get("order_rank_ci")]
        for i, t in enumerate(tags):
            p, lo, hi = T[t]["order_rank_ci"]
            ax.plot([lo, hi], [i, i], color=MUTED, lw=2); ax.plot(p, i, "o", color=ACC if t == "D_s0" else INK, ms=6, mec="white", mew=1.5)
        ax.axvline(50, color="#d0d7de", lw=1, ls="--")
        ax.set_yticks(range(len(tags)), [f"{t} ({T[t]['order_pairs']} pairs / {T[t]['order_rank_roots']} roots)" for t in tags]); ax.invert_yaxis()
        style(ax, f"{dom.upper()} same-endpoint finalized-X ranking (not handoff-only)"); ax.set_xlabel("pairwise accuracy %", fontsize=8, color=MUTED)
    fig.tight_layout(); fig.savefig(FIG / f"F3_order_rank_{split}.png", dpi=170); plt.close(fig)


def errors(split):
    cats = ["SUCCESS", "FAIL_X", "FAIL_Y", "UNKNOWN", "NOOP", "ABSTAIN"]
    col = {"SUCCESS": ACC, "FAIL_X": "#c9662b", "FAIL_Y": "#a1324a", "UNKNOWN": "#8c959f", "NOOP": "#b6c7d9", "ABSTAIN": "#e1e4e8"}
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.6))
    for ax, dom in zip(axs, ("2d", "3d")):
        T = json.loads((TAB / f"physical_{split}_{dom}.json").read_text())["arms"]
        arms = [a for a in PRIMARY if a in T]
        left = np.zeros(len(arms))
        for c in cats:
            v = np.array([T[a]["outcomes"].get(c, 0) for a in arms], float)
            ax.barh(range(len(arms)), v, left=left, color=col[c], label=c, edgecolor="white", lw=1)
            left += v
        ax.set_yticks(range(len(arms)), [LABEL[a] for a in arms]); ax.invert_yaxis()
        style(ax, f"{dom.upper()} outcome breakdown, all roots ({split.upper()})")
    axs[1].legend(fontsize=7, frameon=False, ncol=3, loc="lower right")
    fig.tight_layout(); fig.savefig(FIG / f"F6_errors_{split}.png", dpi=170); plt.close(fig)


def cost(split):
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.4))
    for ax, dom in zip(axs, ("2d", "3d")):
        T = json.loads((TAB / f"physical_{split}_{dom}.json").read_text())["arms"]
        P = json.loads((TAB / f"placement_{split}_{dom}.json").read_text())
        for a in [a for a in PRIMARY if a in T and a in P]:
            x, y = max(P[a]["n_scored"]["mean"], 1), T[a]["task_Kall"]["rate_ci"][0]
            ax.plot(x, y, "o", color=ACC if a == "FULL_s0" else INK, ms=6, mec="white", mew=1.5)
            ax.annotate(LABEL[a], (x, y), fontsize=7, color=MUTED, xytext=(4, 2), textcoords="offset points")
        ax.set_xscale("log"); style(ax, f"{dom.upper()} task success vs scored candidates / root"); ax.set_xlabel("mean scored candidates (log)", fontsize=8, color=MUTED)
        ax.set_ylabel("task success %", fontsize=8, color=MUTED)
    fig.tight_layout(); fig.savefig(FIG / f"F5_cost_{split}.png", dpi=170); plt.close(fig)


def scenes(split, n=4):
    """Illustrative 2D VAL scenes (first n K3 roots in root-id order where FULL and Uniform4 decide differently); declared illustrative."""
    pub = {r["root_id"]: r for r in map(json.loads, open(K3 / "runs/public" / f"public_{split}_2d.jsonl"))}
    A = {a: {r["root_id"]: r for r in map(json.loads, open(K3 / "runs/predictions" / a / f"{split}_2d.jsonl"))} for a in ("FULL_s0", "UNIFORM4_r0")}
    R = {a: {r["root_id"]: r for r in map(json.loads, open(K3 / "runs/verification" / split / f"results_{a}_2d.jsonl"))} for a in A}
    ks = [k for k in sorted(pub) if R["FULL_s0"][k]["K"] == "3" and A["FULL_s0"][k]["moves"] != A["UNIFORM4_r0"][k]["moves"]][:n]
    fig, axs = plt.subplots(len(ks), 2, figsize=(7, 3.3 * len(ks)))
    for row, k in zip(np.atleast_2d(axs), ks):
        inp = pub[k]["inputs"]
        for ax, a in zip(row, A):
            for c, (x, y) in inp["cell_xy"].items():
                ax.add_patch(plt.Rectangle((x - 0.04, y - 0.04), 0.08, 0.08, fill=False, ec="#eaeef2", lw=0.5))
            for i, (x, y) in enumerate(inp["xy0"]):
                t = i == inp["tid"]
                ax.add_patch(plt.Circle((x, y), inp["attrs"][i][0], color="#a1324a" if t else "#8c959f", alpha=0.9))
            ax.plot(*inp["goal"], marker="*", color="#a1324a", ms=12)
            for m in A[a][k]["moves"]:
                x0, y0 = inp["xy0"][m["object_index"]]; x1, y1 = inp["cell_xy"][str(m["destination_cell"])]
                ax.annotate("", (x1, y1), (x0, y0), arrowprops=dict(arrowstyle="->", color=ACC, lw=1.6))
            ax.set_aspect("equal"); ax.set_xlim(0, 0.64); ax.set_ylim(0, 0.64); ax.axis("off")
            ax.set_title(f"{LABEL[a]}: {A[a][k]['decision']} -> {R[a][k]['outcome']}", fontsize=8, color=INK, loc="left")
        row[0].text(0, -0.04, k, fontsize=7, color=MUTED)
    fig.suptitle(f"Illustrative 2D {split.upper()} K3 scenes (target red, goal star, arrows = selected relocations)", fontsize=9, color=INK)
    fig.tight_layout(); fig.savefig(FIG / f"F7_scenes_{split}_2d.png", dpi=170); plt.close(fig)


if __name__ == "__main__":
    split = sys.argv[1]
    FIG.mkdir(parents=True, exist_ok=True)
    for f in (forest, placement, order_rank, errors, cost, scenes):
        try:
            f(split); print("ok", f.__name__)
        except Exception as e:                                      # a missing table must not hide the others; reported, never silent
            print("SKIPPED", f.__name__, repr(e))
