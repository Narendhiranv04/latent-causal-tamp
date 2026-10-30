"""Approach B X/Y figures (one function per phase); reference categorical palette slots 1-4 in fixed order, text in ink colours."""
from __future__ import annotations

import collections
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

FIG = Path("visualizations/approach_b/bxy")
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e0"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.axisbelow": True, "legend.frameon": False})


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / name, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return FIG / name


def _bars(ax, labels, series, names, fmt="{:d}"):
    x, w = np.arange(len(labels)), 0.8 / len(series)
    for j, (vals, nm) in enumerate(zip(series, names)):
        b = ax.bar(x + (j - (len(series) - 1) / 2) * w, vals, w * 0.92, color=C[j], label=nm)
        ax.bar_label(b, [fmt.format(v) for v in vals], fontsize=7, color=INK2, padding=1)
    ax.set_xticks(x, labels)


def fig_p0(man, R):
    """Supervision coverage per split; sequence length x recorded stage; verified K per split."""
    import bxy_data as bd
    cov = man["coverage"]["splits"]
    sp = ["train", "val", "test"]
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2), constrained_layout=True)
    _bars(ax[0], sp, [[cov[s]["y_vars"] for s in sp], [cov[s]["y_obs"] for s in sp], [cov[s]["x_vars"] for s in sp], [cov[s]["x_obs"] for s in sp],
                      [cov[s]["x_obs_positive"] for s in sp]], ["Y variables", "Y observed", "X variables", "X observed (all 0)", "X observed = 1"])
    ax[0].set_title("(a) X/Y variables vs observations per IID split\nno X = 1 exists: the terminal connector to q_ref was never tested", loc="left")
    ax[0].legend(fontsize=7, loc="upper right")
    st = collections.Counter()
    for rec in R.values():
        for b in rec["labels"]["B"]:
            st[(len(b["sequence"]), "full success" if b["y"] else "failed at relocation" if isinstance(b["failed_step"], int) else "failed at target")] += 1
    L = sorted({n for n, _ in st})
    bot = np.zeros(len(L))
    for j, k in enumerate(("full success", "failed at relocation", "failed at target")):
        v = np.array([st[(n, k)] for n in L])
        ax[1].bar(L, v, 0.7, bottom=bot, color=C[j], label=k, edgecolor="white", linewidth=1)
        bot += v
    for n, t in zip(L, bot):
        ax[1].text(n, t + 6, str(int(t)), ha="center", fontsize=7, color=INK2)
    ax[1].set(xlabel="corrective relocations in the recorded B sequence", ylabel="sequences")
    ax[1].set_title("(b) recorded B sequences by length and recorded stage\n(lengths 5-6 kept; legacy whole-sequence outcome)", loc="left")
    ax[1].legend(fontsize=7)
    ks = ["0", "1", "2", "3", "4", "None"]
    _bars(ax[2], [f"K{k}" if k != "None" else "none found" for k in ks], [[cov[s].get(f"verified_K_{k}", 0) for k in ks] for s in sp], sp)
    ax[2].set_title("(c) verified K per split (roots)", loc="left")
    ax[2].legend(fontsize=7)
    fig.suptitle(f"Phase 0: BD_GEN_V1 2D dataset ({man['roots']} roots, {man['data_hash'][:19]}...)", x=0.01, ha="left", fontsize=11, color=INK)
    return _save(fig, "P0_coverage.png")


def fig_p3():
    """(a) four-state joint for the methodology §7 illustrative coefficients; (b) P(Y=1) as X proposals are appended: root-consistent
    scene-first model vs a naive globally normalized product of E_q; (c) exact likelihood vs brute-force enumeration on random roots."""
    import itertools
    import torch
    import bxy_core as X
    D = torch.float64
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2), constrained_layout=True)
    states = [(0, 0), (0, 1), (1, 0), (1, 1)]
    for j, (a, b, w, nm) in enumerate([(-1.0, 2.0, 0.5, "A->B->C (a,b,w)=(-1,2,0.5)"), (0.5, 2.0, 1.0, "B->A->C (a,b,w)=(0.5,2,1)")]):
        t = lambda v: torch.tensor([v], dtype=D)  # noqa: E731
        p = [float(torch.exp(-X.energy_root(t(b), t(a), t(w), [0], (y,), (x,)))) for x, y in states]
        bars = ax[0].bar(np.arange(4) + (j - 0.5) * 0.38, p, 0.36, color=C[j], label=nm)
        ax[0].bar_label(bars, [f"{v:.2f}" for v in p], fontsize=7, color=INK2, padding=1)
    ax[0].set_xticks(range(4), [f"X={x}, Y={y}" for x, y in states])
    ax[0].set(ylabel="P(X, Y)")
    ax[0].set_title("(a) normalized four-state joint (illustrative, not measured)\np_succ = P(X=1, Y=1) = sigma(b) sigma(a+w)", loc="left")
    ax[0].legend(fontsize=7, loc="upper left")
    b0, a0, w0 = 0.3, -0.5, 1.5
    K = np.arange(0, 9)
    first = [float(torch.sigmoid(torch.tensor(b0))) for _ in K]
    naive = []
    for k in K:                                                  # exp(-sum_q E_q) normalized globally over (y, x_1..x_k)
        z = {y: np.exp(b0 * y) * (1 + np.exp(a0 + w0 * y)) ** k for y in (0, 1)}
        naive.append(z[1] / (z[0] + z[1]))
    ax[1].plot(K, first, color=C[0], lw=2, marker="o", ms=4, label="root-consistent (scene-first) model")
    ax[1].plot(K, naive, color=C[1], lw=2, marker="s", ms=4, label="naive global normalization")
    ax[1].set(xlabel="X proposals listed for the same edited scene", ylabel="P(Y_s = 1)", ylim=(0, 1))
    ax[1].set_title(f"(b) scene marginal vs number of listed candidates\n(b, a, w) = ({b0}, {a0}, {w0})", loc="left")
    ax[1].legend(fontsize=7, loc="lower right")
    errs = []
    for seed in range(40):
        g = torch.Generator().manual_seed(seed)
        nY, nX = 1 + seed % 3, 1 + seed % 4
        b, a, w = (torch.randn(n, generator=g, dtype=D) * 2 for n in (nY, nX, nX))
        par = [int(torch.randint(nY, (1,), generator=g)) for _ in range(nX)]
        rng = np.random.default_rng(seed)
        oy = {s: int(rng.integers(2)) for s in range(nY) if rng.random() < .5}
        ox = {q: int(rng.integers(2)) for q in range(nX) if rng.random() < .5}
        errs.append(abs(float(X.log_evidence(b, a, w, par, oy, ox)) - X.brute_force(b, a, w, par, oy, ox)))
    ax[2].semilogy(range(40), np.maximum(errs, 1e-17), "o", color=C[0], ms=4)
    ax[2].axhline(1e-10, color=C[1], lw=1, ls="--")
    ax[2].text(0, 2e-10, "test tolerance 1e-10", color=INK2, fontsize=7)
    ax[2].set(xlabel="random root (1-3 scenes, 1-4 prefixes, random observations)", ylabel="|exact - enumeration| of log P(D)\n(exact zeros drawn at 1e-17)")
    ax[2].set_title(f"(c) exact masked likelihood vs brute force: max error {max(errs):.1e}", loc="left")
    fig.suptitle("Phase 3: root-consistent X/Y Boltzmann model (bxy_core)", x=0.01, ha="left", fontsize=11, color=INK)
    return _save(fig, "P3_math.png")


if __name__ == "__main__":
    import sys
    import bxy_data as bd
    if sys.argv[1] == "p0":
        print(fig_p0(json.loads((bd.OUT / "P0_MANIFEST.json").read_text()), bd.roots()))
    elif sys.argv[1] == "p3":
        print(fig_p3())
