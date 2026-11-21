#!/usr/bin/env python3
"""CF/NULL figures from sealed files only.
    python cf_figures.py 3d RESULTS_DIR OUT_DIR       (RESULTS_DIR has metrics3d.json, tripman3d.json, scores3d.jsonl, jobs3d.jsonl)
    python cf_figures.py 2d RESULTS_DIR OUT_DIR"""
import json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

COL = {"ours": "#2a78d6", "piginet": "#b4441c", "scnet": "#1baf7a", "grn": "#e07b00"}
NAME = {"ours": "Ours", "piginet": "PIGINet (no img)", "scnet": "SceneCollisionNet", "grn": "GRN"}
INK, MUTED, GRID = "#222222", "#7a7975", "#e6e6e6"


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(MUTED); ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(colors=INK, labelsize=9)
    ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)


def metrics_fig(dom, m, fams, out):
    coh = m["cohorts"]["STRONG"]
    fig, axs = plt.subplots(1, 2, figsize=(9, 0.55 * len(fams) + 1.4), sharey=True)
    for ax, key, title, ref in ((axs[0], "cf_pair_auroc", "CF-pair AUROC (BASE vs CF)", 0.5), (axs[1], "null_retention", "NULL retention (p ≥ 0.5)", None)):
        for i, f in enumerate(fams):
            v = coh["models"][f + "_seedmean"]
            p, (lo, hi) = v["point"][key], v["ci95"][key]
            ax.plot([lo, hi], [i, i], color=COL[f], lw=2, solid_capstyle="round")
            ax.plot(p, i, "o", color=COL[f], ms=8, mec="white", mew=2)
            ax.text(hi + 0.012, i, f"{p:.3f}" if key == "cf_pair_auroc" else f"{100 * p:.1f}%", va="center", fontsize=9, color=INK)
            for s in range(3):
                ax.plot(coh["models"][f"{f}_s{s}"]["point"][key], i - 0.22, "|", color=COL[f], ms=6, alpha=0.7)
        if ref is not None:
            ax.axvline(ref, color=MUTED, ls=":", lw=1); ax.text(ref, len(fams) - 0.45, "constant 0.5", fontsize=8, color=MUTED, ha="left")
        ax.set_title(title, fontsize=10, color=INK, loc="left"); style(ax)
        ax.set_xlim(0.45 if ref else 0.4, 1.06)
    axs[0].set_yticks(range(len(fams))); axs[0].set_yticklabels([NAME[f] for f in fams]); axs[0].invert_yaxis()
    fig.suptitle(f"{dom.upper()} STRONG triplets (n = {coh['n_triplets']}); seed mean with 95% lineage-bootstrap CI, ticks = seeds s0–s2",
                 fontsize=9.5, color=INK, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(out, dpi=170); plt.close(fig)


def scores_fig(dom, man, S, fams, out):
    T = [t for t in man["triplets"] if t["cohort"] == "STRONG"]
    fig, axs = plt.subplots(1, len(fams), figsize=(2.6 * len(fams), 3.2), sharey=True)
    axs = np.atleast_1d(axs)
    rng = np.random.default_rng(0)
    for ax, f in zip(axs, fams):
        g = lambda q: np.mean([S[q][k] for k in S[q] if k.startswith(f + "_s")])  # noqa: E731
        for j, (k, lab) in enumerate((("base", "BASE"), ("cf", "CF"), ("null", "NULL"))):
            v = np.array([g(t[k]) for t in T])
            ax.scatter(j + rng.uniform(-0.18, 0.18, len(v)), v, s=6, color=COL[f], alpha=0.35, lw=0)
            ax.plot([j - 0.25, j + 0.25], [np.median(v)] * 2, color=INK, lw=2)
        ax.axhline(0.5, color=MUTED, ls=":", lw=1)
        ax.set_xticks([0, 1, 2]); ax.set_xticklabels(["BASE\n(y=1)", "CF\n(y=0 cert.)", "NULL\n(y=1)"], fontsize=8)
        ax.set_title(NAME[f], fontsize=10, color=INK, loc="left")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.set_ylim(-0.03, 1.03)
    axs[0].set_ylabel("predicted target feasibility (seed mean)", fontsize=9)
    fig.tight_layout(); fig.savefig(out, dpi=170); plt.close(fig)


def examples_fig(man, J, S, out, n=4):
    T = sorted([t for t in man["triplets"] if t["cohort"] == "STRONG"], key=lambda t: t["root_id"])[:: max(1, len(man["triplets"]) // (3 * n))][:n]
    fig, axs = plt.subplots(n, 3, figsize=(7.2, 2.5 * n))
    for r, t in enumerate(T):
        for c, k in enumerate(("base", "cf", "null")):
            ax = axs[r, c]; j = J[t[k]]
            cells = {o: tuple(v) for o, v in j["cells"].items()}
            goal = tuple(json.loads(Path(j["path"]).read_text())["goal"])
            ax.set_xlim(-0.5, 5.5); ax.set_ylim(-0.5, 5.5); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
            for x in range(7):
                ax.plot([x - 0.5] * 2, [-0.5, 5.5], color=GRID, lw=0.6); ax.plot([-0.5, 5.5], [x - 0.5] * 2, color=GRID, lw=0.6)
            ax.add_patch(plt.Rectangle((goal[1] - 0.45, goal[0] - 0.45), 0.9, 0.9, fill=False, ec=COL["scnet"], lw=2, ls="--"))
            for o, (rr, cc) in cells.items():
                fc = COL["piginet"] if o == "t0" else ("#f2a33a" if o == t["obj"] else "#9a9a96")
                ax.add_patch(plt.Circle((cc, rr), 0.36, color=fc))
            if k != "base":
                fr = tuple(J[t["base"]]["cells"][t["obj"]])
                ax.add_patch(plt.Circle((fr[1], fr[0]), 0.36, fill=False, ec="#f2a33a", ls=":", lw=1.5))
            sc = " ".join(f"{NAME[f].split()[0][:4]} {np.mean([S[t[k]][f'{f}_s{s}'] for s in range(3)]):.2f}" for f in ("ours", "piginet", "scnet", "grn"))
            ax.set_title(f"{k.upper()}  y={1 if k != 'cf' else 0}\n{sc}", fontsize=6.5, color=INK)
            if c == 0:
                ax.set_ylabel(t["root_id"][:22], fontsize=6.5)
    fig.text(0.01, 0.003, "rows = shelf rows (robot side at row 0); red = target t0, dashed green = goal, orange = moved obstacle (dotted = its BASE cell)",
             fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.015, 1, 1)); fig.savefig(out, dpi=170); plt.close(fig)


def main(dom, rd, od):
    rd, od = Path(rd), Path(od); od.mkdir(parents=True, exist_ok=True)
    m = json.load(open(rd / f"metrics{dom}.json")); man = json.load(open(rd / f"tripman{dom}.json"))
    S = {json.loads(l)["qid"]: json.loads(l) for l in open(rd / f"scores{dom}.jsonl")}
    fams = [f for f in ("ours", "piginet", "scnet", "grn") if f + "_seedmean" in m["cohorts"]["STRONG"]["models"]]
    metrics_fig(dom, m, fams, od / f"fig_{dom}_cf_null_metrics.png")
    scores_fig(dom, man, S, fams, od / f"fig_{dom}_score_strips.png")
    if dom == "3d":
        J = {json.loads(l)["qid"]: json.loads(l) for l in open(rd / "jobs3d.jsonl")}
        examples_fig(man, J, S, od / "fig_3d_example_triplets.png")
    print("figures ->", od)


if __name__ == "__main__":
    main(*sys.argv[1:4])
