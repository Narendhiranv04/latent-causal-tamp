#!/usr/bin/env python3
"""Compact matplotlib figures for every phase (reads committed JSON / private per-candidate tables; writes reports/figures/*.png).
    python figures.py p0|p1|p2|p4|p5|p6"""
from __future__ import annotations

import json, sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import rr

FIG = rr.REP / "figures"
TIERS = ["T4", "T56", "R7_12", "TAIL"]
INK, MUTED, BLUE, ORANGE, GREEN, RED = "#1f2328", "#6e7781", "#2f6fdf", "#e07b00", "#1a7f37", "#cf222e"


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / name, dpi=150, bbox_inches="tight", facecolor="white"); plt.close(fig)


def p0():
    T = json.loads((rr.REP / "P0_TRAIN_COVERAGE.json").read_text())
    kt = T["X_labels_by_kind_and_max_tier"]
    kinds = sorted({k.split("|")[0] for k in kt}, key=lambda k: -sum(v for kk, v in kt.items() if kk.startswith(k + "|")))
    M = np.array([[kt.get(f"{k}|{t}", 0) for t in TIERS] for k in kinds], float)
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8), gridspec_kw={"width_ratios": [1.5, 1]})
    im = ax[0].imshow(np.log10(M + 1), cmap="Blues", aspect="auto")
    for i in range(len(kinds)):
        for j in range(len(TIERS)):
            ax[0].text(j, i, f"{int(M[i, j]):,}", ha="center", va="center", fontsize=8, color="white" if M[i, j] > 1500 else INK)
    ax[0].set_xticks(range(len(TIERS)), ["ranks 1-4", "5-6", "7-12", ">12"]); ax[0].set_yticks(range(len(kinds)), [k.lower() for k in kinds], fontsize=8)
    ax[0].set_xlabel("worst frozen-cVAE destination rank in the labelled sequence"); ax[0].set_title("TRAIN X labels by intervention kind (count)", fontsize=10)
    sh = T["label_share_vs_support_by_max_tier"]
    x = np.arange(len(TIERS))
    ax[1].bar(x - 0.2, [sh[t]["share_labels"] for t in TIERS], 0.38, color=BLUE, label="share of TRAIN X labels (by worst rank)")
    ax[1].bar(x + 0.2, [sh[t]["share_legal_actions"] for t in TIERS], 0.38, color=MUTED, label="share of legal actions")
    ax[1].set_xticks(x, ["1-4", "5-6", "7-12", ">12"]); ax[1].set_ylabel("share"); ax[1].legend(fontsize=7, frameon=False)
    ax[1].set_title("label support vs legal support", fontsize=10)
    for a in ax[1:]:
        a.spines[["top", "right"]].set_visible(False)
    fig.suptitle(f"P0: original TRAIN snapshot (3,500 roots, {sum(M.ravel()):,.0f} finalized X labels); not physical truth of the full domain", fontsize=9, color=MUTED)
    _save(fig, "p0_train_rank_support.png")


if __name__ == "__main__":
    globals()[sys.argv[1]]()
