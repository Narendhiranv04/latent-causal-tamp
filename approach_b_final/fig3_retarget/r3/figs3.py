#!/usr/bin/env python3
"""R3 figures (local; reads the committed report JSONs).  python figs3.py r30 [R24_LABELS_3D.jsonl]"""
from __future__ import annotations

import json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

R = Path(__file__).resolve().parent / "reports"
FIG = R / "figures"
INK, MUTED, GRID = "#1f2328", "#6e7781", "#d0d7de"
BLUE, ORANGE, GREEN, RED = "#2f6fb0", "#d9822b", "#3a8f5c", "#c4453c"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5})


def _auc(d, k):
    v = d.get(k) or {}
    return v.get("auroc"), v.get("auroc_ci")


def r30(lab_path):
    rd = {d: json.loads((R / "r30" / f"readouts_{d}.json").read_text()) for d in ("3d", "2d")}
    sl = json.loads((R / "r30" / "shortlist_3d.json").read_text())
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8), gridspec_kw={"width_ratios": [1.5, 1, 1]})
    # (a) AUROC of marginal pX / conditional pX1 / pX0 / p11 on the natural VAL panel and the R2.4 hard panel (3D)
    nat, hard = rd["3d"]["natural_val"], rd["3d"]["hard_r24"]
    groups = [("natural VAL\nall m<=3", {k: nat[f"{k}_vs_x_all"]["all"] if k != "px" else nat["marginal_px_vs_x"]["all"] for k in ("px", "px1", "px0")}),
              ("natural VAL m=1\n(133/134 pos.)", {"px": nat["marginal_px_vs_x"]["m1"]}),
              ("R2.4 hard\nh=0", {k: hard[k]["h0"] for k in ("px", "px1", "px0")}),
              ("R2.4 hard\nh>=1", {k: hard[k]["h>=1"] for k in ("px", "px1", "px0")}),
              ("R2.4 hard\nh>=1, m=2-3", {k: hard[k]["h>=1_m23"] for k in ("px", "px1", "px0")})]
    cols = {"px": BLUE, "px1": ORANGE, "px0": GREEN}
    for gi, (g, d) in enumerate(groups):
        for ki, k in enumerate(("px", "px1", "px0")):
            v = d.get(k)
            if not v or v.get("auroc") is None:
                continue
            x = gi + (ki - 1) * 0.26
            ci = v.get("auroc_ci")
            ax[0].bar(x, v["auroc"], 0.24, color=cols[k], label={"px": "marginal pX", "px1": "pX | Y=1", "px0": "pX | Y=0"}[k] if gi == 0 else None)
            if ci:
                ax[0].plot([x, x], ci, color=INK, lw=1)
    ax[0].axhline(0.5, color=MUTED, ls=":", lw=1); ax[0].axhline(0.75, color=RED, ls="--", lw=0.8)
    ax[0].text(2.45, 0.765, "R3.2 gate 0.75", color=RED, fontsize=7, ha="right")
    ax[0].set_xticks(range(len(groups))); ax[0].set_xticklabels([g for g, _ in groups], fontsize=7.5)
    ax[0].set_ylim(0, 1.02); ax[0].set_ylabel("AUROC vs exact X label (family-cluster 95% CI)")
    ax[0].set_title("(a) 3D frozen X readouts: natural panel vs hard local panel", loc="left", fontsize=9)
    ax[0].legend(frameon=False, fontsize=7.5, loc="upper right", bbox_to_anchor=(1.0, 0.97))
        # (b) confident negatives: pX1 vs pX0
    L = [json.loads(l) for l in open(lab_path)]
    L = [e for e in L if e["t"] == "chunk" and e["label"] in (0, 1) and e.get("px1") is not None]
    for lab, c, nm in ((1, BLUE, "executable"), (0, RED, "not executable")):
        s = [e for e in L if e["label"] == lab]
        ax[1].scatter([e["px0"] for e in s], [e["px1"] for e in s], s=9, color=c, alpha=0.55, edgecolors="white", linewidths=0.3, label=f"{nm} (n={len(s)})")
    ax[1].set_xlabel("pX | Y=0  = sig(a)"); ax[1].set_ylabel("pX | Y=1  = sig(a+w)")
    ax[1].set_title("(b) 3D hard panel: both conditional logits high\non 144/157 confident negatives", loc="left", fontsize=9)
    ax[1].legend(frameon=False, fontsize=7.5, loc="lower right"); ax[1].set_xlim(-0.02, 1.02); ax[1].set_ylim(-0.02, 1.02)
    # (c) GA shortlist truncation
    ip = sorted([v for v in sl.values() if v["in_union_pool"]], key=lambda v: v["rank_by_y"])
    ax[2].scatter([v["n_same_size"] for v in ip], [v["rank_by_y"] for v in ip], s=22, color=ORANGE, edgecolors="white", linewidths=0.4, zorder=3)
    ax[2].axhline(4, color=RED, ls="--", lw=0.8); ax[2].text(5e3, 5.2, "top-4 shortlist", color=RED, fontsize=7)
    ax[2].set_xscale("log"); ax[2].set_yscale("log"); ax[2].xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter()); ax[2].set_xlabel("same-size sets enumerated (union pool)"); ax[2].set_ylabel("rank of verified witness set by Y_global")
    ax[2].set_title(f"(c) GA Y-only shortlist: witness set in pool\non {len(ip)}/20 roots, ranked 349-11,897", loc="left", fontsize=9)
    fig.tight_layout()
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "R3_0_audit.png", dpi=160); print(FIG / "R3_0_audit.png")


if __name__ == "__main__":
    {"r30": lambda: r30(sys.argv[2])}[sys.argv[1]]()
