#!/usr/bin/env python3
"""Figures (reports/figures/).  Scene panels are real roster / VAL roots drawn from public inputs: 2D = planar 8x8 lattice, 3D = a labelled
TOP-DOWN SCHEMATIC of the 6x6 shelf cells (not a physics render).  Arrows = relocations, numbered in execution order.

    python viz.py all"""
from __future__ import annotations

import collections, json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import run as RN  # noqa: E402

FIG = RN.REP / "figures"
GRID = {"2d": (8, 8), "3d": (6, 6)}
COL = {"J": "#1f77b4", "X": "#d62728", "Y": "#2ca02c", "XC": "#9467bd"}


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / name, dpi=130, bbox_inches="tight"); plt.close(fig); print(FIG / name)


def draw(ax, dom, inp, seq, title):
    R, C = GRID[dom]
    legal = set(int(c) for c in inp["legal_cells"])
    for j in range(R * C):
        r, c = divmod(j, C)
        ax.add_patch(plt.Rectangle((c, r), 1, 1, fc="white" if j in legal else "#dddddd", ec="#bbbbbb", lw=0.5))
    g = int(inp["goal_cell"])
    ax.add_patch(plt.Rectangle((g % C, g // C), 1, 1, fc="none", ec="#2ca02c", lw=2.2))
    fixed = [bool(a[3]) for a in inp["attrs"]] if dom == "2d" else [False] * len(inp["ids"])
    for i, cell in enumerate(inp["cells0"]):
        r, c = divmod(int(cell), C)
        ax.add_patch(plt.Circle((c + .5, r + .5), .33, fc="#d62728" if i == inp["tid"] else "#7f7f7f" if fixed[i] else "#1f77b4", ec="k", lw=.5, alpha=.85))
        ax.text(c + .5, r + .5, str(i), ha="center", va="center", fontsize=6, color="white")
    for t, (o, d) in enumerate(seq or []):
        r0, c0 = divmod(int(inp["cells0"][o]), C)
        r1, c1 = divmod(int(d), C)
        ax.annotate("", xy=(c1 + .5, r1 + .5), xytext=(c0 + .5, r0 + .5), arrowprops=dict(arrowstyle="->", color="#ff7f0e", lw=1.6))
        ax.add_patch(plt.Circle((c1 + .5, r1 + .5), .33, fc="none", ec="#ff7f0e", lw=1.4, ls="--"))
        ax.text(c1 + .82, r1 + .18, str(t + 1), fontsize=8, color="#ff7f0e", weight="bold")
    ax.set_xlim(0, C); ax.set_ylim(R, 0); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([]); ax.set_title(title, fontsize=7)


def success():
    st = json.loads((RN.REP / "P4_STATS.json").read_text())
    fig, axs = plt.subplots(1, 2, figsize=(12, 4))
    for a, dom in enumerate(RN.DOMS):
        A = st["domains"][dom]["arms"]
        for j, arm in enumerate(("J", "X", "Y", "XC")):
            v = [A[f"arms:{arm}"][g]["verified_pct"] for g in ("K1", "K2", "K3", "K1-3")]
            up = [A[f"arms:{arm}"][g]["upper_pct"] - A[f"arms:{arm}"][g]["verified_pct"] for g in ("K1", "K2", "K3", "K1-3")]
            axs[a].bar(np.arange(4) + (j - 1.5) * .2, v, .2, color=COL[arm], label=arm + (" (secondary)" if arm == "XC" else ""),
                       yerr=[np.zeros(4), up], capsize=2, alpha=.5 if arm == "XC" else 1)
        axs[a].set_xticks(range(4), ["K1", "K2", "K3", "K1-3"]); axs[a].set_ylim(0, 100); axs[a].legend(fontsize=7)
        axs[a].set_title(f"{dom.upper()} locked roster, 50 / K: verified task success % (whisker = + UNKNOWN / UNQUERIED)", fontsize=8)
    save(fig, "p4_success_by_K.png")
    fig, ax = plt.subplots(figsize=(7, 3.2))
    rows = []
    for dom in RN.DOMS:
        for c, v in st["domains"][dom]["contrasts"].items():
            rows.append((f"{dom.upper()} {c}", v["strict"]))
    for i, (lab, x) in enumerate(rows):
        ax.errorbar(x["delta_pp"], i, xerr=[[x["delta_pp"] - x["ci95_pp"][0]], [x["ci95_pp"][1] - x["delta_pp"]]], fmt="o", color="k")
    ax.axvline(0, color="r", lw=.8); ax.set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=6)
    ax.set_xlabel("paired K1-K3 verified-success difference, pp (whole-family bootstrap 95 %)", fontsize=8)
    save(fig, "p4_contrasts.png")
    fig, axs = plt.subplots(1, 2, figsize=(12, 3.6))
    cats = ["X1Y1", "X0Y1", "X1Y0", "X0Y0", "X?Y1", "X1Y?", "X?Y0", "X0Y?", "X?Y?"]
    for a, dom in enumerate(RN.DOMS):
        A = st["domains"][dom]["arms"]
        bottom = np.zeros(3)
        for c in cats:
            v = np.array([A[f"arms:{arm}"]["K1-3"]["joint"].get(c, 0) for arm in ("J", "X", "Y")])
            if v.any():
                axs[a].bar(range(3), v, bottom=bottom, label=c); bottom += v
        for k in ("NOOP", "ABSTAIN", "UNQUERIED"):
            v = np.array([A[f"arms:{arm}"]["K1-3"]["classes"].get(k, 0) for arm in ("J", "X", "Y")])
            if v.any():
                axs[a].bar(range(3), v, bottom=bottom, label=k, hatch="//", alpha=.5); bottom += v
        axs[a].set_xticks(range(3), ["J", "X", "Y"]); axs[a].legend(fontsize=6, ncol=2)
        axs[a].set_title(f"{dom.upper()} K1-K3 outcome by actual factor labels (strict)", fontsize=8)
    save(fig, "p4_failure_breakdown.png")


def orders():
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
    for a, dom in enumerate(RN.DOMS):
        G = [json.loads(l) for l in open(RN.RUNS / f"dev_groups_{dom}.jsonl")]
        P, N = [], []
        for g in G:
            if g["y"] == 1 and g["px1"]["mixed"]:
                P.append(g["px1"]["concordance"])
        pts = collections.defaultdict(list)
        for g in G:
            if g["y"] == 1 and g["px1"]["complete"]:
                pts[g["px1"]["m"]].append((g["px1"]["learned_x"], g["px1"]["canonical_x"], g["px1"]["random_x"]))
        lab = []
        for m in (2, 3):
            v = np.array(pts[m], float)
            if len(v):
                axs[a].bar(np.arange(3) + (m - 2.5) * .35, v.mean(0) * 100, .35, label=f"m={m} (n={len(v)} complete Y=1 groups)")
        axs[a].set_xticks(range(3), ["learned pX1", "canonical", "uniform random"]); axs[a].set_ylim(0, 100)
        axs[a].set_title(f"{dom.upper()} VAL (exposed) O-A: executable chosen order %; mixed-group concordance {np.mean(P):.2f} (n={len(P)})", fontsize=8)
        axs[a].legend(fontsize=7)
    save(fig, "p4_order_OA.png")


def examples(n=2):
    """O-B panel: one row per assignment, all orders of the same endpoint with strict X; chosen by sha256 within outcome classes."""
    st = json.loads((RN.REP / "P4_STATS.json").read_text())
    import labels as L
    for dom in RN.DOMS:
        rows = st["domains"][dom]["panel_rows"]
        pub = {r["root_id"]: r for r in RN.jl(RN.CR_RUNS / "p3" / f"public_{dom}.jsonl")}
        sc = {x["root_id"]: x for x in RN.jl(RN.RUNS / f"panel_scores_{dom}.jsonl")}
        led = L.Ledger(dom, set(sc))
        cls = {"mixed": lambda g: g["pX1_mixed"], "all X=1": lambda g: g["pX1_complete"] and g["pX1_n_neg"] == 0,
               "all X=0": lambda g: g["pX1_complete"] and g["pX1_n_pos"] == 0}
        sel = []
        for c, f in cls.items():
            sel += [(c, g) for g in sorted((g for g in rows if f(g)), key=lambda g: RN.h("XYO_VIZ", g["root_id"]))[:n]]
        if not sel:
            continue
        cols = max(len(sc[g["root_id"]]["scores"]) for _, g in sel)
        fig, axs = plt.subplots(len(sel), cols, figsize=(2.3 * cols, 2.5 * len(sel)))
        axs = np.atleast_2d(axs)
        for i, (c, g) in enumerate(sel):
            x = sc[g["root_id"]]
            orders = sorted(x["scores"], key=lambda k: -x["scores"][k]["px1"])
            for j in range(cols):
                ax = axs[i, j]
                if j >= len(orders):
                    ax.axis("off"); continue
                k = orders[j]
                xv = led.get(g["root_id"], json.loads(k))[0] if led.queried(g["root_id"], json.loads(k)) else "unq"
                draw(ax, dom, pub[g["root_id"]]["inputs"], json.loads(k),
                     f"{c} | {g['root_id'][:16]}\nrank {j + 1}: pX1 {x['scores'][k]['px1']:.2f}  X={'?' if xv is None else xv}  Y={g['y']}")
        kind = "TOP-DOWN SCHEMATIC of shelf cells (not a render)" if dom == "3d" else "planar 8x8 lattice"
        fig.suptitle(f"O-B {dom.upper()} [{kind}]: same final arrangement, every order ranked by frozen pX1; strict teacher X", fontsize=9)
        fig.tight_layout(rect=(0, 0, 1, .97)); save(fig, f"p4_order_examples_{dom}.png")


if __name__ == "__main__":
    success(); orders(); examples()
