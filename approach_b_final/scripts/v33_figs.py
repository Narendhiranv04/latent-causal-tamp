"""V3.3 figures (VALIDATION only).  usage: v33_figs.py REPORT_DIR PHYS_TABLE_JSON
 training_curves.png (VAL weighted -ELBO vs optimizer step), proposal_coverage_vs_M.png (teacher-free known-success coverage),
 physical_val.png (verified task success / NONE abstention per sampler seed + seed mean), failure_decomposition.png (coverage vs ranking)."""
import glob, json, os, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

C = {"control": "#0072B2", "expanded": "#D55E00", "q2init": "#7F7F7F"}
LBL = {"control": "S-control (scratch, V3 data)", "expanded": "S-expanded (scratch, V3.2 data)", "q2init": "q2init_all reference (different init + data)"}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25})


def legend_below(fig, axs, n=3):
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=n, frameon=False)


def curves(R):
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.6))
    for ax, d in zip(axs, ("2d", "3d")):
        for a in ("control", "expanded"):
            for s in (0, 1, 2):
                c = json.load(open(R / "train_curves" / f"{d}_{a}_scratch_all_s{s}.json"))
                x = [p["step"] for p in c["curve"]]; y = [p["val"] for p in c["curve"]]
                ax.plot(x, y, color=C[a], lw=1.2, alpha=0.85, label=LBL[a] if s == 0 else None)
                ax.plot(c["best_step"], c["best_val"], "o", color=C[a], ms=4)
        ax.set_title(f"{d.upper()}: VAL weighted −ELBO (dots = selected checkpoints)"); ax.set_xlabel("optimizer step (matched budget)")
        ax.set_ylim(top=min(ax.get_ylim()[1], 4.5 if d == "2d" else 3.5))
    axs[0].set_ylabel("VAL −ELBO (nats)")
    legend_below(fig, axs, 2); fig.tight_layout(rect=(0, 0.1, 1, 1)); fig.savefig(R / "figures/training_curves.png", dpi=160); plt.close(fig)


def coverage(R):
    cv = json.load(open(R / "COVERAGE_VAL.json"))
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.6))
    for ax, d in zip(axs, ("2d", "3d")):
        arms = cv[d]["arms"]
        for a in ("control", "expanded"):
            Y = np.array([[arms[f"{a}_s{s}"][str(M)]["task"] for M in (4, 5, 6)] for s in (0, 1, 2)]) * 100
            for y in Y:
                ax.plot((4, 5, 6), y, color=C[a], lw=0.8, alpha=0.35)
            ax.plot((4, 5, 6), Y.mean(0), color=C[a], lw=2, marker="o", label=LBL[a])
        ax.plot((4, 5, 6), [100 * arms["q2init_s0"][str(M)]["task"] for M in (4, 5, 6)], color=C["q2init"], lw=2, ls="--", marker="s", label=LBL["q2init"])
        ax.set_xticks((4, 5, 6)); ax.set_xlabel("M (top destination proposals per object)")
        ax.set_title(f"{d.upper()}: VAL task roots with a known success in the top-M pool")
    axs[0].set_ylabel("% of VAL task roots (lower bound)")
    legend_below(fig, axs); fig.tight_layout(rect=(0, 0.1, 1, 1)); fig.savefig(R / "figures/proposal_coverage_vs_M.png", dpi=160); plt.close(fig)


def physical(R, T):
    fig, axs = plt.subplots(1, 4, figsize=(13, 3.6))
    for j, d in enumerate(("2d", "3d")):
        for k, (key, ttl) in enumerate((("task", "verified task success"), ("abstain", "correct NONE abstention"))):
            ax = axs[2 * j + k]
            for i, a in enumerate(("control", "expanded", "q2init")):
                x = T[d].get(a)
                if not x:
                    continue
                ps = np.array(x[f"{key}_per_seed"]) * 100
                ax.scatter(np.full(len(ps), i) + np.linspace(-0.08, 0.08, len(ps)), ps, color=C[a], s=18, zorder=3)
                ax.bar(i, x[key] * 100, color=C[a], alpha=0.35, width=0.6, label=LBL[a])
            ax.set_xticks([]); ax.set_title(f"{d.upper()}: {ttl}"); ax.set_ylabel("%")
            lo = min(min(np.array(T[d][a][f"{key}_per_seed"]) * 100) for a in ("control", "expanded", "q2init") if T[d].get(a))
            ax.set_ylim(max(0, lo - 15), 100)
    legend_below(fig, axs); fig.tight_layout(rect=(0, 0.1, 1, 1)); fig.savefig(R / "figures/physical_val.png", dpi=160); plt.close(fig)


def failures(R, T):
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.6))
    cats = [("RANK_FAIL_Y", "ranking: Y-infeasible pick"), ("RANK_FAIL_X", "ranking: X-infeasible pick"), ("RANK_ABSTAIN", "ranking: abstained"),
            ("RANK_NOOP", "ranking: no-op"), ("COVER_FAIL_Y", "no known success in pool: Y fail"), ("COVER_FAIL_X", "no known success: X fail"),
            ("COVER_ABSTAIN", "no known success: abstained"), ("COVER_NOOP", "no known success: no-op")]
    col = ["#CC79A7", "#E69F00", "#56B4E9", "#009E73", "#882255", "#AA4499", "#332288", "#117733"]
    for ax, d in zip(axs, ("2d", "3d")):
        arms = [a for a in ("control", "expanded", "q2init") if T[d].get(a)]
        bot = np.zeros(len(arms))
        n = T[d][arms[0]]["n"]["task"]
        for (k, lab), c in zip(cats, col):
            v = np.array([T[d][a]["task_failures"].get(k, 0) / n * 100 for a in arms])
            ax.bar(range(len(arms)), v, bottom=bot, color=c, label=lab, width=0.6, edgecolor="white", linewidth=1)
            bot += v
        ax.set_xticks(range(len(arms))); ax.set_xticklabels(["S-control", "S-expanded", "q2init ref"][:len(arms)])
        ax.set_title(f"{d.upper()}: failed VAL task roots (seed mean, % of task roots)"); ax.set_ylabel("%")
    legend_below(fig, axs, 4); fig.tight_layout(rect=(0, 0.16, 1, 1)); fig.savefig(R / "figures/failure_decomposition.png", dpi=160); plt.close(fig)


if __name__ == "__main__":
    R = Path(sys.argv[1]); (R / "figures").mkdir(exist_ok=True)
    curves(R); coverage(R)
    if len(sys.argv) > 2:
        T = json.load(open(sys.argv[2])); physical(R, T); failures(R, T)
