#!/usr/bin/env python3
"""Figures for the post-ablation validation (same visual style as ablations_k3/figs_k3.py).  Reads $K3V/runs/out/*; writes $K3V/runs/figures/."""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import vk  # noqa: E402

INK, MUTED, ACC, ACC2, GRID = "#1f2328", "#59636e", "#0969da", "#bf3989", "#d0d7de"
FIG = vk.K3V / "runs/figures"


def style(ax, title):
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8)


def dots(ax, labels, cis, hl=None, ref=0.0):
    for i, (lab, c) in enumerate(zip(labels, cis)):
        if c is None or c[0] is None:
            continue
        p, lo, hi = c
        col = ACC if (hl and hl(lab)) else INK
        ax.plot([lo, hi], [i, i], color=col if col == ACC else MUTED, lw=2, solid_capstyle="round")
        ax.plot(p, i, "o", ms=6, color=col, mec="white", mew=1.5)
    ax.axvline(ref, color=GRID, lw=1, ls="--")
    ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels, fontsize=8); ax.invert_yaxis()
    ax.grid(axis="x", color=GRID, lw=0.6)


def f_coupling():
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.2))
    for ax, dom in zip(axs, ("2d", "3d")):
        for split, col in (("val", ACC), ("test", ACC2)):
            X = [r for r in vk.jl(vk.OUT / "nodes" / f"{dom}_{split}_FULL_s0.jsonl") if r["node"] == "X"]
            s = lambda z: 1 / (1 + np.exp(-np.asarray(z)))  # noqa: E731
            dp = s([r["a"] + r["w"] for r in X]) - s([r["a"] for r in X])
            ax.hist(dp, bins=np.linspace(-0.6, 0.6, 49), histtype="step", lw=1.6, color=col, label=f"{split.upper()} (n={len(dp)})")
        style(ax, f"{dom.upper()}: P(X=1|Y=1) - P(X=1|Y=0), frozen D s0")
        ax.set_xlabel("difference in conditional X probability", fontsize=8, color=MUTED); ax.legend(fontsize=7, frameon=False)
    fig.tight_layout(); fig.savefig(FIG / "V1_coupling_delta_p.png", dpi=160); plt.close(fig)


def f_direct_scale():
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.4))
    for ax, dom in zip(axs, ("2d", "3d")):
        M = {}
        for p in sorted((vk.OUT / "multipass").glob(f"val_{dom}*.jsonl")):
            for r in vk.jl(p):
                M[r["root_id"]] = r
        priv = {e["root_id"]: e for e in vk.jl(vk.K3A / "runs/public" / f"private_val_{dom}.jsonl")}
        data, labs = [], []
        for n in ("FULL_s0", "E_s0", "DIRECT_s0"):
            for c, nm in (("NONE", "NONE (no feasible repair)"), ("K", "K1-K3")):
                v = [M[r]["variants"][f"{n}:p11"]["p"] for r in M if f"{n}:p11" in M[r]["variants"] and ((priv[r]["K"] == "NONE") == (c == "NONE")) and priv[r]["K"] != "0"]
                data.append(v); labs.append(f"{n.split('_')[0]} | {nm}")
        bp = ax.boxplot(data, orientation="horizontal", widths=0.5, patch_artist=True, showfliers=False, medianprops={"color": INK})
        for i, b in enumerate(bp["boxes"]):
            b.set_facecolor(ACC2 if "DIRECT" in labs[i] else "#9fb7d4"); b.set_edgecolor("white")
        ax.axvline(0.3, color=MUTED, lw=1, ls=":"); ax.text(0.31, 0.6, "eta = 0.3", fontsize=7, color=MUTED)
        ax.set_yticklabels(labs, fontsize=7); ax.invert_yaxis()
        style(ax, f"{dom.upper()} VAL: best-candidate score")
        ax.set_xlabel("max candidate score over the M4 pool", fontsize=8, color=MUTED)
    fig.tight_layout(); fig.savefig(FIG / "V2_direct_argmax_scale.png", dpi=160); plt.close(fig)


def f_paired(fname, title, keys):
    """keys: [(label, eval key)] from rules EVAL_{split}_{dom}.json 'paired'."""
    fig, axs = plt.subplots(2, 2, figsize=(10, 1.2 + 0.32 * len(keys) * 2), sharex=True)
    for (split, dom), ax in zip([(s, d) for s in ("val", "test") for d in ("2d", "3d")], axs.flat):
        E = json.loads((vk.OUT / "rules" / f"EVAL_{split}_{dom}.json").read_text())["paired"]
        dots(ax, [k for k, _ in keys], [E.get(v, {}).get("diff") for _, v in keys])
        style(ax, f"{split.upper()} {dom.upper()}")
    for ax in axs[-1]:
        ax.set_xlabel("paired difference, pp (95% layout-cluster CI)", fontsize=8, color=MUTED)
    fig.suptitle(title, fontsize=11, color=INK, x=0.01, ha="left"); fig.tight_layout(); fig.savefig(FIG / fname, dpi=160); plt.close(fig)


def f_cvae():
    fig, axs = plt.subplots(1, 2, figsize=(9, 2.8))
    for ax, dom in zip(axs, ("2d", "3d")):
        d = json.loads((vk.OUT / "cvae" / f"C2C4_{dom}.json").read_text())["models"]
        rows = [("task cVAE, true task", d["task"]["rec_true"]["mean"]), ("task cVAE, goal swapped", d["task"]["rec_goalswap"]["mean"]),
                ("task cVAE, target swapped", d["task"]["rec_targetswap"]["mean"]), ("NoTask cVAE", d["notask"]["rec_true"]["mean"])]
        ax.barh(range(4), [100 * v for _, v in rows], color=[ACC, "#9fb7d4", "#9fb7d4", MUTED], height=0.6)
        for i, (_, v) in enumerate(rows):
            ax.text(100 * v + 1, i, f"{100 * v:.1f}", va="center", fontsize=7, color=INK)
        ax.set_yticks(range(4)); ax.set_yticklabels([r for r, _ in rows], fontsize=8); ax.invert_yaxis(); ax.set_xlim(0, 100)
        style(ax, f"{dom.upper()} VAL: recall@4 of known successful (object, cell)"); ax.set_xlabel("%", fontsize=8, color=MUTED)
    fig.tight_layout(); fig.savefig(FIG / "V5_cvae_task_sensitivity.png", dpi=160); plt.close(fig)


if __name__ == "__main__":
    FIG.mkdir(parents=True, exist_ok=True)
    f_coupling(); f_direct_scale(); f_cvae()
    f_paired("V3_knockout_and_selectors.png", "Frozen D: F5 knockout and X-only / Y-only selectors (physical task success, K1-K3)",
             [("knockout w=0, registered rule", "A5 knockout - D (registered) | task"), ("knockout w=0, fixed gating", "A5 knockout - D (fixed gating) | task"),
              ("knockout w=0, forced repair", "A5 knockout - D (forced) | task"), ("Y-only, forced", "D Y_only - p11 (forced) | task"),
              ("X marginal, forced", "D X_marg - p11 (forced) | task"), ("X|Y=1, forced", "D X|Y1 - p11 (forced) | task"),
              ("Y-only, fixed gating", "D Y_only - p11 (fixed gating) | task"), ("X marginal, fixed gating", "D X_marg - p11 (fixed gating) | task")])
    f_paired("V4_direct_fairness.png", "DIRECT and E vs D under the registered rule, VAL-tuned rules and threshold-free forced repair (task success, K1-K3)",
             [("DIRECT - D, registered", "B DIRECT - D registered | task"), ("DIRECT - D, VAL-tuned", "B DIRECT - D tuned | task"),
              ("DIRECT - D, forced repair", "B DIRECT - D forced (threshold-free) | task"), ("E - D, registered", "B E - D registered | task"),
              ("E - D, VAL-tuned", "B E - D tuned | task"), ("E - D, forced repair", "B E - D forced | task")])
    print(sorted(p.name for p in FIG.glob("*.png")))
