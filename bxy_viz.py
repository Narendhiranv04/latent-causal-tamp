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


def _reliability(ax, y, p, color, label):
    y, p = np.asarray(y, float), np.asarray(p, float)
    bins = np.minimum((p * 10).astype(int), 9)
    xs = [(p[bins == k].mean(), y[bins == k].mean(), (bins == k).sum()) for k in range(10) if (bins == k).any()]
    ax.plot([0, 1], [0, 1], color=GRID, lw=1.2)
    ax.plot([x for x, _, _ in xs], [v for _, v, _ in xs], color=color, lw=2, marker="o", ms=4, label=label)


def fig_p1():
    """LB: validation root NLL per seed; test reliability of candidate (whole-sequence) and scene-edit predictions (seed 0)."""
    L = Path("runs/approach_b/bd2d_lb_v1")
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2), constrained_layout=True)
    for s in (0, 1, 2):
        h = json.loads((L / f"TRAIN_LOG_s{s}.json").read_text())["history"]
        e = json.loads((L / f"EVAL_s{s}.json").read_text())
        v = [(x["update"] + 1, x["val"]) for x in h if x.get("val") is not None]
        ax[0].plot(*zip(*v), color=C[s], lw=2, label=f"seed {s} (best update {e['best_update']})")
        ax[0].axvline(e["best_update"], color=C[s], lw=1, ls=":")
    ax[0].set(xlabel="update", ylabel="validation root NLL")
    ax[0].set_title("(a) LB validation root NLL (early stopping, patience 15 x 20)", loc="left")
    ax[0].legend(fontsize=7)
    P = json.loads((L / "PREDICTIONS_s0.json").read_text())["test"]
    c = [x for v in P.values() for x in v["candidates"] if x["y"] is not None]
    for j, (nm, f) in enumerate((("non-empty candidates", lambda x: x["m"] > 0), ("empty (original task)", lambda x: x["m"] == 0))):
        sel = [x for x in c if f(x)]
        _reliability(ax[1], [x["y"] for x in sel], [x["p"] for x in sel], C[j], f"{nm} (n={len(sel)})")
    ax[1].set(xlabel="predicted P(whole sequence succeeds)", ylabel="observed frequency", xlim=(0, 1), ylim=(0, 1))
    ax[1].set_title("(b) test reliability, recorded whole-sequence labels (seed 0)", loc="left")
    ax[1].legend(fontsize=7, loc="upper left")
    sc = [x for v in P.values() for x in v["scene"] if x["y"] is not None]
    _reliability(ax[2], [x["y"] for x in sc], [x["p"] for x in sc], C[2], f"scene edits (n={len(sc)})")
    ax[2].set(xlabel="predicted P(target succeeds in edited scene)", ylabel="observed frequency", xlim=(0, 1), ylim=(0, 1))
    ax[2].set_title("(c) test reliability, recorded scene-edit labels (seed 0)", loc="left")
    ax[2].legend(fontsize=7, loc="upper left")
    fig.suptitle("Phase 1: production LB trained from scratch on BD_GEN_V1 2D (legacy whole-sequence baseline)", x=0.01, ha="left", fontsize=11, color=INK)
    return _save(fig, "P1_LB.png")


def fig_p5():
    """XY-quadratic lambda_J grid (seed 0): validation joint NLL; learned w over every catalogue X variable; P(X = 1) on validation."""
    import torch
    import bxy_core as X
    import bxy_run as BR
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2), constrained_layout=True)
    va = X.views("val", full=True)
    for j, lam in enumerate(BR.LAMBDA_J):
        n = f"XY-quadratic-lam{lam}-s0"
        h = json.loads((BR.OUT / "train" / f"{n}.json").read_text())
        v = [(x["update"] + 1, x["val"]) for x in h["history"] if x.get("val") is not None]
        ax[0].plot(*zip(*v), color=C[j], lw=2, label=f"lambda_J = {lam} (best {h['val_root_nll']:.3f} @ {h['best_update']})")
        P = BR.predict_xy(BR.load("XY-quadratic", n), va)
        w = np.array([x for p in P.values() for x in p["w_all"]])
        ax[1].hist(w, bins=40, color=C[j], alpha=0.55, label=f"lambda_J = {lam}: mean {w.mean():.2f}, sd {w.std():.2f}")
        px = np.array([c["px"] for p in P.values() for c in p["cands"] if c["m"]])
        ax[2].hist(px, bins=np.linspace(0, 1, 41), color=C[j], alpha=0.55, label=f"lambda_J = {lam}: median {np.median(px):.3f}")
    ax[0].set(xlabel="update", ylabel="validation joint root NLL")
    ax[0].set_title("(a) XY-quadratic, seed 0: validation joint NLL", loc="left")
    ax[0].legend(fontsize=7)
    ax[1].set(xlabel="w_q over all validation catalogue X variables", ylabel="count")
    ax[1].set_title("(b) coupling coefficients: no X = 1 was ever observed,\nso w_q is NOT an identified interaction", loc="left")
    ax[1].legend(fontsize=7)
    ax[2].set(xlabel="P(X_r = 1), full validation candidates", ylabel="count")
    ax[2].set_title("(c) predicted physical executability: trained on zeros only", loc="left")
    ax[2].legend(fontsize=7)
    fig.suptitle("Phase 5: initial X/Y learning on the existing observations", x=0.01, ha="left", fontsize=11, color=INK)
    return _save(fig, "P5_initial_learning.png")


def fig_p7():
    """Test (frozen): selection success per arm and seed with baselines; Y log loss; selection success by verified K (seed mean)."""
    import bxy_run as BR
    E = json.loads((BR.OUT / "EVAL_P7.json").read_text())
    arms = ["LB", "XY-uncoupled", "XY-quadratic", "XY-quadratic-noJ"]
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.4), constrained_layout=True)
    for j, a in enumerate(arms):
        v = [E["arms"][f"{a}-s{s}"]["selection"]["success"] for s in BR.SEEDS]
        ax[0].scatter([j] * 3, v, color=C[j], s=28, zorder=3)
        ax[0].hlines(np.mean(v), j - 0.25, j + 0.25, color=C[j], lw=2)
        ax[0].text(j + 0.28, np.mean(v), f"{np.mean(v):.2f}", fontsize=7, color=INK2, va="center")
    for k, (nm, v) in enumerate(E["baselines"].items()):
        ax[0].axhline(v["success"], color=[INK2, "#8c8c8c", "#b0aea6"][k], lw=1, ls=["--", ":", "-."][k])
        ax[0].text(-0.45, v["success"] + 0.005, nm, fontsize=7, color=INK2, va="bottom", ha="left")
    ax[0].set_xticks(range(4), arms, rotation=12)
    ax[0].set(ylabel="test selection success (recorded full-execution check)", ylim=(0, 1.05))
    ax[0].set_title(f"(a) repair selection on {E['arms']['LB-s0']['selection']['roots']} test roots (dots = seeds)", loc="left")
    for j, a in enumerate(arms):
        v = [E["arms"][f"{a}-s{s}"]["metrics"]["Y_observed"]["log_loss"] for s in BR.SEEDS]
        ax[1].scatter([j] * 3, v, color=C[j], s=28, zorder=3)
        ax[1].hlines(np.mean(v), j - 0.25, j + 0.25, color=C[j], lw=2)
        ax[1].text(j + 0.28, np.mean(v), f"{np.mean(v):.3f}", fontsize=7, color=INK2, va="center")
    ax[1].set_xticks(range(4), arms, rotation=12)
    ax[1].set(ylabel="log loss")
    ax[1].set_title("(b) test log loss on observed target-from-q0 labels\n(original task + scene edits; Y for XY arms)", loc="left")
    ks = sorted({k for a in arms for k in E["arms"][f"{a}-s0"]["by_K"]}, key=lambda x: (x == "None", x))
    w = 0.8 / len(arms)
    for j, a in enumerate(arms):
        v = [np.mean([E["arms"][f"{a}-s{s}"]["by_K"].get(k, np.nan) for s in BR.SEEDS]) for k in ks]
        ax[2].bar(np.arange(len(ks)) + (j - 1.5) * w, v, w * 0.92, color=C[j], label=a)
    nK = {k: sum(str(r["K"]) == k for r in E["arms"]["LB-s0"]["rows"]) for k in ks}
    ax[2].set_xticks(range(len(ks)), [f"K{k}\n(n={nK[k]})" if k != "None" else f"none\n(n={nK[k]})" for k in ks])
    ax[2].set(ylabel="selection success (seed mean)", ylim=(0, 1.05))
    ax[2].set_title("(c) by verified K (test roots)", loc="left")
    ax[2].legend(fontsize=7)
    fig.suptitle("Phase 7: frozen test comparison (validation-only model and rule selection)", x=0.01, ha="left", fontsize=11, color=INK)
    return _save(fig, "P7_comparison.png")


if __name__ == "__main__":
    import sys
    import bxy_data as bd
    if sys.argv[1] in ("p1", "p5", "p7"):
        print({"p1": fig_p1, "p5": fig_p5, "p7": fig_p7}[sys.argv[1]]())
    if sys.argv[1] == "p0":
        print(fig_p0(json.loads((bd.OUT / "P0_MANIFEST.json").read_text()), bd.roots()))
    elif sys.argv[1] == "p3":
        print(fig_p3())
