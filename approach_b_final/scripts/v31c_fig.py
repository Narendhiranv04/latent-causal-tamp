"""V3.1-C figure: verified top-1 task success vs actual scored sequences and vs latency (validation), V3 budgets vs V2 iterative budgets; K3."""
import json, os, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
V = Path(os.environ["V3OUT"])
fig, ax = plt.subplots(2, 3, figsize=(13, 7))
for i, d in enumerate(("2d", "3d")):
    S = json.loads((V / "v3_1c" / f"SUMMARY_budget_{d}.json").read_text())
    v3 = sorted([(v["n_scored_median"], v["latency_s_median"], v["task_success"], v.get("task_K3", 0), v["abstain_correct"]) for k, v in S.items() if k.startswith("v3D")])
    v2 = sorted([(v["n_scored_median"], v["latency_s_median"], v["task_success"], v.get("task_K3", 0), v["abstain_correct"]) for k, v in S.items() if k.startswith("v2_")])
    for j, (xi, yi, xl, yl) in enumerate(((0, 2, "median sequences scored per root", "verified task success"), (1, 2, "median latency per root (s)", "verified task success"), (0, 3, "median sequences scored per root", "verified K3 success"))):
        a = ax[i, j]
        a.plot([t[xi] for t in v3], [100 * t[yi] for t in v3], "-o", color="#0072B2", lw=2, label="V3 direct (B = 128 ... 4,096)")
        a.plot([t[xi] for t in v2], [100 * t[yi] for t in v2], "-s", color="#777777", lw=2, label="V2 iterative (3 ... 48 expansions)")
        a.set_xscale("log"); a.set_xlabel(xl); a.set_ylabel(yl + " (%)"); a.grid(alpha=0.3)
        a.set_title(f"{d.upper()} validation", fontsize=9)
    ax[i, 0].legend(frameon=False, fontsize=7)
fig.suptitle("V3.1-C: compute-matched comparison on validation (every selection physically verified; frozen V3 / V2 models and rules)", fontsize=9)
fig.tight_layout(); fig.savefig(V / "v3_1c" / "budget_curves.png", dpi=150)
print(V / "v3_1c" / "budget_curves.png")
