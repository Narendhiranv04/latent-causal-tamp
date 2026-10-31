"""BXY-P11.1 figure: analytic decision regions of the superseded gated rule vs the primary cost rule, evaluation tiers, travel contrasts.
No data outcome and no model is used (pure rule geometry and the frozen root counts)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import bxy_p11 as P  # noqa: E402
import bxy_p11_1 as A  # noqa: E402

FIG = Path("visualizations/approach_b/bxy_p11_1_v1")


def figure() -> str:
    FIG.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(1, 3, figsize=(17, 5.4), gridspec_kw={"width_ratios": [1.15, 1, 1.1]})
    g = np.linspace(0.005, 0.995, 400)
    p0, p1 = np.meshgrid(g, g)                                                # x: P(Y0=1) (no-op), y: p_succ of a 1-move correction
    new = (-np.log(p1) + 0.1) < -np.log(p0)                                   # equal J_hat: primary picks the correction
    old = new & (p0 < 0.5)
    reg = np.where(new & ~old, 2, np.where(new, 1, 0))
    ax[0].contourf(p0, p1, reg, levels=[-0.5, 0.5, 1.5, 2.5], colors=["#dfe7f2", "#9ec5e8", "#e8a33d"])
    ax[0].axvline(0.5, color="#555", ls="--", lw=1)
    ax[0].plot(0.55, 0.95, "o", ms=9, mfc="white", mec="black")
    ax[0].annotate("contract example\nP(Y0)=0.55, p=0.95:\nold -> no-op, new -> repair", (0.55, 0.95), (0.6, 0.62), fontsize=8.5,
                   arrowprops={"arrowstyle": "->", "lw": 0.8})
    ax[0].text(0.05, 0.04, "no-op chosen by both", fontsize=9)
    ax[0].text(0.06, 0.88, "repair chosen\nby both", fontsize=9)
    ax[0].text(0.52, 0.40, "gate overrode\na lower-cost\nrepair", fontsize=9, color="#7a4b00")
    ax[0].set(xlabel="P(Y0 = 1)  (zero-move candidate)", ylabel="p_succ of a 1-move correction (same J_hat)",
              title="A. Primary rule: no-op is an ordinary candidate\n(orange = region removed from the gate's override)")
    t = {"PRIMARY_DEV": 176, "SUPPLEMENTARY_DEV": 197, "DESCRIPTIVE_VAL": 21}
    lab = ["PRIMARY dev\nOOF on train176", "SUPPLEMENTARY\nOOF on all 197", "DESCRIPTIVE\nSPLIT on val21", "CONFIRMATORY\nfuture cohort"]
    ax[1].barh(range(4), [t["PRIMARY_DEV"], t["SUPPLEMENTARY_DEV"], t["DESCRIPTIVE_VAL"], 0], color=["#2b6cb0", "#90b4d8", "#b8b8b8", "white"],
               edgecolor="#333", height=0.6)
    for i, v in enumerate([176, 197, 21]):
        ax[1].text(v + 3, i, f"{v} roots", va="center", fontsize=9)
    ax[1].text(3, 3, "not generated; not part of P12", va="center", fontsize=9, style="italic")
    ax[1].set_yticks(range(4), lab, fontsize=9)
    ax[1].invert_yaxis()
    ax[1].set(xlim=(0, 260), xlabel="independent roots", title="B. Evaluation tiers (folds and 108 runs unchanged)\nval21 chose lambda* -> excluded from PRIMARY")
    ax[2].axis("off")
    ax[2].set_title("C. Travel: training vs ranking vs combined", fontsize=11)
    box = lambda x, y, s, c: ax[2].text(x, y, s, ha="center", va="center", fontsize=9, bbox={"boxstyle": "round", "fc": c, "ec": "#333"})  # noqa: E731
    box(0.2, 0.8, "XY-quadratic\nlambda* trained\ngamma = 0.05", "#f6d8a8")
    box(0.8, 0.8, "XY-quadratic\nlambda* trained\ngamma = 0", "#fbe9cc")
    box(0.5, 0.18, "XY-quadratic-noJ\nlambda = 0\ngamma = 0", "#dfe7f2")
    arrow = lambda a, b, s, xy: (ax[2].annotate("", b, a, arrowprops={"arrowstyle": "<->", "lw": 1.2}), ax[2].text(*xy, s, ha="center", fontsize=8.5))  # noqa: E731
    arrow((0.34, 0.8), (0.66, 0.8), "RANKING\n(same checkpoint)", (0.5, 0.86))
    arrow((0.78, 0.68), (0.58, 0.3), "TRAINING\n(both gamma = 0)", (0.82, 0.45))
    arrow((0.22, 0.68), (0.42, 0.3), "COMBINED\n(labelled)", (0.17, 0.45))
    ax[2].set(xlim=(0, 1), ylim=(0, 1))
    fig.suptitle("BXY-P11.1 amendment (frozen before any real-data training; analytic, no outcomes)", fontsize=12)
    fig.tight_layout()
    f = FIG / "01_p11_1_amendment.png"
    fig.savefig(f, dpi=130)
    plt.close(fig)
    return str(f)


if __name__ == "__main__":
    print(figure(), A.PRIMARY, P.RULE)
