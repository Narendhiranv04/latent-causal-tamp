#!/usr/bin/env python3
"""R2 figures (matplotlib, Agg).  Every figure states its data source; drawings vs witnesses are labelled.
    python figs.py audit INVENTORY.json OUT_DIR"""
from __future__ import annotations

import json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

INK, MUTED, A, B, C = "#1f2328", "#6e7781", "#0969da", "#bc4c00", "#1a7f37"


def _style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=7, colors=MUTED)


def audit(inv, out):
    inv = json.loads(Path(inv).read_text()); out = Path(out); out.mkdir(parents=True, exist_ok=True)
    fig, axs = plt.subplots(2, 2, figsize=(11, 6.6))
    dev = inv["development_material_N"]
    for row, dom in enumerate(("2d", "3d")):
        d = inv["domains"][dom]
        ax = axs[row, 0]
        tr, va = d["train"]["N_hist"], d["val"]["N_hist"]
        ns = sorted({int(k) for k in tr} | {int(k) for k in va})
        x = np.arange(len(ns))
        t = np.array([tr.get(str(n), 0) for n in ns], float); v = np.array([va.get(str(n), 0) for n in ns], float)
        ax.bar(x - 0.2, t / t.sum(), 0.4, color=A, label=f"TRAIN (V3.2 snapshot, {int(t.sum())} roots)")
        ax.bar(x + 0.2, v / v.sum(), 0.4, color=B, label=f"VAL (V3.4, {int(v.sum())} roots)")
        ax.set_xticks(x); ax.set_xticklabels(ns, fontsize=7)
        marks = []
        if dom == "3d" and "3d_k45_cohort" in dev:
            marks.append(("K4/K5 cohort", dev["3d_k45_cohort"]))
        if f"{dom}_c3b" in dev:
            marks.append(("C3b", dev[f"{dom}_c3b"]))
        for j, (lab, q) in enumerate(marks):
            lo, hi = ns.index(q["min"]) if q["min"] in ns else 0, ns.index(q["max"]) if q["max"] in ns else len(ns) - 1
            y = ax.get_ylim()[1] * (0.92 - 0.1 * j)
            ax.plot([lo, hi], [y, y], color=C if j == 0 else INK, lw=2)
            ax.text(hi + 0.3, y, f"{lab} N {q['min']}-{q['max']}", fontsize=7, va="center", color=INK)
        if dom == "2d":
            ax.text(len(ns) - 1, ax.get_ylim()[1] * 0.62, "release_v2 (protected, not opened):\nN 25-28 > TRAIN max 20 and > cVAE MAXOBJ 20", ha="right", fontsize=7, color=B)
        ax.set_title(f"{dom.upper()}: total object count N (incl. target)", fontsize=9, loc="left", color=INK)
        ax.set_xlabel("N", fontsize=8, color=MUTED); ax.set_ylabel("fraction of roots", fontsize=8, color=MUTED)
        ax.legend(fontsize=7, frameon=False, loc="upper left"); _style(ax)
        ax = axs[row, 1]
        bins = ["1-5", "6-10", "11-15", "16-20"] if dom == "2d" else ["1-3", "4-5", "6-7", "8-13"]
        M = np.zeros((len(bins), 4)); P = np.zeros((len(bins), 4))
        for n, v in d["train"]["byN"].items():
            n = int(n)
            bi = next(i for i, b in enumerate(bins) if int(b.split("-")[0]) <= n <= int(b.split("-")[1]))
            for m, (c, c1) in v["X_by_m"].items():
                M[bi, int(m)] += c; P[bi, int(m)] += c1
        im = ax.imshow(M[:, 1:], cmap="Blues", aspect="auto")
        for i in range(len(bins)):
            for j in range(3):
                c = M[i, j + 1]
                ax.text(j, i, f"{int(c)}\n{P[i, j + 1] / c:.0%} X=1" if c else "0", ha="center", va="center", fontsize=7, color="white" if c > M[:, 1:].max() * 0.6 else INK)
        ax.set_xticks(range(3)); ax.set_xticklabels(["m=1", "m=2", "m=3"], fontsize=7); ax.set_yticks(range(len(bins))); ax.set_yticklabels([f"N {b}" for b in bins], fontsize=7)
        ax.set_title(f"{dom.upper()} TRAIN X labels by N bin x m (no m >= 4 label exists)", fontsize=9, loc="left", color=INK)
        _style(ax)
    fig.suptitle("R2.0 audit: training support (source: snapshot labels; TEST rows skipped unread)", fontsize=9.5, x=0.01, ha="left", color=INK)
    fig.tight_layout(); fig.savefig(out / "R2_0_train_support.png", dpi=150); plt.close(fig)


if __name__ == "__main__":
    if sys.argv[1] == "audit":
        audit(sys.argv[2], sys.argv[3])
