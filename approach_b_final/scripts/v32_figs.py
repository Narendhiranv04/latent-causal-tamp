"""V3.2 stage-2 figures from the committed tables (VAL unless stated).  usage: v32_figs.py REPORT_DIR (= reports/v3_2_stage2)"""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

R = Path(sys.argv[1])
B = json.loads((R / "B/B_FROZEN_EXHAUSTIVE_PHYS.json").read_text())
E = json.loads((R / "E/TABLE_VAL_E3_E4.json").read_text())
F = json.loads((R / "E/TABLE_FAILURES_VAL.json").read_text())
C = json.loads((R / "E/TABLE_RESOURCE_COST_INFERENCE.json").read_text())
Ms = [4, 5, 6]
COL = {"capped": "#777777", "frozen": "#E69F00", "control": "#56B4E9", "expanded": "#0072B2"}
out = R / "figures"; out.mkdir(exist_ok=True)

# 1-2: verified task success and correct NONE abstention vs M
for metric, bkey, ekey, fname, lab in (("task", "task", "task", "verified_success_vs_M.png", "verified task success K1-K3 (%)"),
                                       ("abst", "abstain_correct", "abstain", "abstention_vs_M.png", "correct NONE abstention (%)")):
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    for a, d in zip(ax, ("2d", "3d")):
        cap = B[d]["capped_M4_B4096"][bkey]["lower"] * 100
        a.axhline(cap, color=COL["capped"], ls="--", lw=1.5, label="capped V3 (M4, B=4,096), frozen D s0")
        a.plot(Ms, [B[d][f"exhaustive_M{M}"][bkey]["lower"] * 100 for M in Ms], "-s", color=COL["frozen"], lw=2, ms=7, label="exhaustive, frozen V3 D s0")
        for arm in ("control", "expanded"):
            m = [E[d][f"{arm}_M{M}"][ekey] * 100 for M in Ms]
            sd = [E[d][f"{arm}_M{M}"]["task_seed_sd"] * 100 for M in Ms] if ekey == "task" else None
            a.errorbar(Ms, m, yerr=sd, fmt="-o", color=COL[arm], lw=2, ms=7, capsize=3, label=f"exhaustive, D-{arm} (3 seeds)")
        a.set_xticks(Ms); a.set_xlabel("M (top destinations per object)"); a.set_ylabel(lab); a.set_title(f"{d.upper()} validation (all selections physically verified)", fontsize=9)
        a.grid(alpha=0.3)
    h, l = ax[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, frameon=False, fontsize=7)
    fig.tight_layout(rect=(0, 0.08, 1, 1)); fig.savefig(out / fname, dpi=150); plt.close(fig)

# 3: calibration of the selected repair
fig, ax = plt.subplots(1, 2, figsize=(10, 4))
for a, d in zip(ax, ("2d", "3d")):
    for arm in ("control", "expanded"):
        x = [E[d][f"{arm}_M{M}"]["selected_mean_p11"] for M in Ms]; y = [E[d][f"{arm}_M{M}"]["selected_verified_rate"] for M in Ms]
        a.plot(x, y, "-o", color=COL[arm], lw=2, ms=7, label=f"D-{arm}")
        for M, xi, yi in zip(Ms, x, y):
            a.annotate(f"M{M}", (xi, yi), textcoords="offset points", xytext=(4, 4), fontsize=7)
    a.plot([0.4, 1], [0.4, 1], ":", color="#999999", lw=1); a.set_xlim(0.45, 1); a.set_ylim(0.45, 1)
    a.set_xlabel("mean p11 of the selected repair"); a.set_ylabel("physically verified success of the selected repair"); a.set_title(f"{d.upper()} calibration (VAL)", fontsize=9); a.grid(alpha=0.3)
ax[0].legend(frameon=False, fontsize=8)
fig.tight_layout(); fig.savefig(out / "calibration_selected_vs_M.png", dpi=150); plt.close(fig)

# 4: failure decomposition (task roots) + known-success coverage
cats = [("SUCCESS", "#009E73"), ("RANK_FAIL_Y", "#D55E00"), ("RANK_FAIL_X", "#E69F00"), ("COVER_UNKNOWN_Y", "#CC79A7"), ("COVER_UNKNOWN_X", "#F0E442")]
fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
for a, d in zip(ax, ("2d", "3d")):
    arms = ["capped_M4_B4096"] + [f"{arm}_M{M}" for arm in ("frozen_V3D_s0", "control", "expanded") for M in (4, 6)]
    bottom = np.zeros(len(arms))
    for c, col in cats:
        v = []
        for k in arms:
            al = F[d][k]["all"]; tot = sum(x for kk, x in al.items() if kk != "known_in_pool")
            v.append(100 * al.get(c, 0) / tot)
        a.bar(range(len(arms)), v, bottom=bottom, color=col, label=c, width=0.75); bottom += np.array(v)
    rest = 100 - bottom
    a.bar(range(len(arms)), rest, bottom=bottom, color="#BBBBBB", label="other (no-op / abstain)", width=0.75)
    a.set_xticks(range(len(arms))); a.set_xticklabels([k.replace("_B4096", "").replace("frozen_V3D_s0", "frozen").replace("_", " ") for k in arms], rotation=35, fontsize=7)
    a.set_ylabel("% of task roots"); a.set_title(f"{d.upper()} validation: success vs ranking vs coverage failures", fontsize=9)
    kin = {M: 100 * F[d][f"expanded_M{M}"]["all"]["known_in_pool"] / sum(x for kk, x in F[d][f"expanded_M{M}"]["all"].items() if kk != "known_in_pool") for M in Ms}
    a.text(0.02, 0.02, "known success in pool: " + ", ".join(f"M{M} {kin[M]:.0f}%" for M in Ms), transform=a.transAxes, fontsize=7)
h, l = ax[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=6, frameon=False, fontsize=7)
fig.tight_layout(rect=(0, 0.07, 1, 1)); fig.savefig(out / "failure_decomposition.png", dpi=150); plt.close(fig)

# 5: compute vs M
fig, ax = plt.subplots(1, 2, figsize=(10, 4))
for d, col in (("2d", "#0072B2"), ("3d", "#E69F00")):
    k = next(k for k in C if k.startswith(d + " trained"))
    ax[0].plot(Ms, [C[k][f"n_scored_M{M}_median"] for M in Ms], "-o", color=col, lw=2, label=f"{d.upper()} median")
    ax[0].plot(Ms, [C[k][f"n_scored_M{M}_max"] for M in Ms], "--o", color=col, lw=1.5, label=f"{d.upper()} max")
    ax[1].bar([0 if d == "2d" else 1], [C[k]["wall_s_median"]], color=col, width=0.6)
    ax[1].errorbar([0 if d == "2d" else 1], [C[k]["wall_s_median"]], yerr=[[0], [C[k]["p90"] - C[k]["wall_s_median"]]], color="k", capsize=4)
ax[0].axhline(4096, color="#777777", ls=":", lw=1.5, label="old cap B = 4,096")
ax[0].set_yscale("log"); ax[0].set_xticks(Ms); ax[0].set_xlabel("M"); ax[0].set_ylabel("ordered sequences scored per root"); ax[0].legend(frameon=False, fontsize=7); ax[0].grid(alpha=0.3)
ax[1].set_xticks([0, 1]); ax[1].set_xticklabels(["2D", "3D"]); ax[1].set_ylabel("wall s / root (M6 pass, median; bar = p90)"); ax[1].set_title("exhaustive scoring cost per root (1 CPU + GPU)", fontsize=9)
fig.tight_layout(); fig.savefig(out / "compute_vs_M.png", dpi=150); plt.close(fig)
print(sorted(p.name for p in out.iterdir()))
