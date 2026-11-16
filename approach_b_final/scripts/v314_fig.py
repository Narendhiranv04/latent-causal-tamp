"""V3.1-4 test figures from TABLE_TEST_V314.json: (1) verified task success vs scored sequences and vs latency, V3 primary B = 128 ... 4,096 vs V2
iterative 3 / 12 / 48 expansions (seed 0); (2) seed mean +- SD of verified task success: matched goal ablation and coupled D vs E / G / DIRECT.
usage: v314_fig.py TABLE_JSON OUT_DIR"""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.ticker
import matplotlib.pyplot as plt

T, OUT = json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2])
BLUE, GREY = "#0072B2", "#777777"
fig, ax = plt.subplots(2, 2, figsize=(10, 7))
for i, d in enumerate(("2d", "3d")):
    B = T[d]["budget"]
    bud = lambda k: int(k.split("=")[1]) if "=" in k else int(k.split("exp")[1])  # noqa: E731  points ordered by nominal budget (3D unique-sequence count saturates)
    v3 = [(x["n_scored_median"], x["latency_s_median"], x["task"][0]) for k, x in sorted(B.items(), key=lambda t: bud(t[0])) if k.startswith("V3")]
    v2 = [(x["n_scored_median"], x["latency_s_median"], x["task"][0]) for k, x in sorted(B.items(), key=lambda t: bud(t[0])) if k.startswith("V2")]
    for j, (xi, xl) in enumerate(((0, "median sequences scored per root"), (1, "median latency per root (s)"))):
        a = ax[i, j]
        a.plot([t[xi] for t in v3], [100 * t[2] for t in v3], "-o", color=BLUE, lw=2, ms=8, label="V3 direct (B = 128 ... 4,096)")
        a.plot([t[xi] for t in v2], [100 * t[2] for t in v2], "-s", color=GREY, lw=2, ms=8, label="V2 iterative (3 / 12 / 48 expansions)")
        a.set_xscale("log"); a.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter()); a.set_xlabel(xl); a.set_ylabel("verified task success (%)"); a.grid(alpha=0.3); a.set_title(f"{d.upper()} test, seed 0", fontsize=9)
    ax[i, 0].legend(frameon=False, fontsize=8)
fig.suptitle("V3.1-4: compute-matched comparison on TEST (every selection physically verified; frozen models / rules / budgets)", fontsize=9)
fig.tight_layout(); fig.savefig(OUT / "budget_curves_test.png", dpi=150)

fig, ax = plt.subplots(1, 2, figsize=(11, 4))
for a, (g, ttl) in zip(ax, (("goal", "matched goal / task-conditioning ablation (V3 D, B=4,096)"), ("seeds", "coupled D vs E / G / DIRECT (task cVAE, B=4,096)"))):
    names = list(T["2d"][g]); w = 0.38
    for k, (d, col) in enumerate((("2d", BLUE), ("3d", "#E69F00"))):
        m = [100 * T[d][g][n]["task"][0] for n in names]; s = [100 * T[d][g][n]["task"][1] for n in names]
        a.bar([x + (k - 0.5) * w for x in range(len(names))], m, w * 0.92, yerr=s, capsize=3, color=col, label=d.upper())
    a.set_xticks(range(len(names))); a.set_xticklabels([n.replace("q2init_all", "task cVAE").replace("_", " ") for n in names], fontsize=8, rotation=12)
    a.set_ylabel("verified task success (%)\nmean +- SD over seeds 0-2"); a.set_title(ttl, fontsize=9); a.grid(axis="y", alpha=0.3); a.legend(frameon=False, fontsize=8)
fig.tight_layout(); fig.savefig(OUT / "goal_and_seed_test.png", dpi=150)
print(OUT / "budget_curves_test.png", OUT / "goal_and_seed_test.png")
