#!/usr/bin/env python3
"""KGT3 figures (local; committed report JSONs only).
    python figs.py p2      -> reports/figures/KGT3_P2.png        (teacher outcomes, gate support, 3D model metrics, actual matched-order scenes)
    python figs.py p4      -> reports/figures/KGT3_P4_planners.png (model-only planner accounting on the DEV panels)"""
from __future__ import annotations

import collections, json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "r3"))
import figs3 as F3  # noqa: E402
R = HERE / "reports"; P2 = R / "p2"; FIG = R / "figures"
INK, MUTED, GRID, BLUE, ORANGE, GREEN, RED = F3.INK, F3.MUTED, F3.GRID, F3.BLUE, F3.ORANGE, F3.GREEN, F3.RED
GREY = "#c9cdd2"


def jl(p):
    return [json.loads(l) for l in open(p)]


def p2():
    import numpy as np
    S = json.loads((P2 / "p2_stats.json").read_text())
    D = json.loads((P2 / "gate_3d_descriptive_all_arms.json").read_text())
    fig = plt.figure(figsize=(14, 8.8))
    gs = fig.add_gridspec(2, 4, height_ratios=[1, 1.1], hspace=0.45, wspace=0.3, left=0.05, right=0.99, top=0.93, bottom=0.07)
    ax = fig.add_subplot(gs[0, 0])
    cats = [(d, sp, st) for d in ("2d", "3d") for st in ("CHAIN", "ORD") for sp in ("TRAIN", "SELECT", "GATE")]
    for i, (d, sp, st) in enumerate(cats):
        v = S[d]["status"]; b = 0
        for cls, c in (("X1", GREEN), ("X0", RED), ("UNKNOWN", GREY)):
            n = v.get(f"{sp}|{st}|{cls}", 0); ax.bar(i, n, bottom=b, color=c, label=cls if i == 0 else None); b += n
    ax.set_xticks(range(len(cats))); ax.set_xticklabels([f"{d} {st[:2]} {sp[:3]}" for d, sp, st in cats], rotation=70, fontsize=6.5)
    ax.set_ylabel("teacher runs"); ax.legend(frameon=False, fontsize=7, title="outcome", title_fontsize=7)
    ax.set_title("(a) P2 teacher outcomes (X only)\n2D 1,032 runs: 644 UNKNOWN; 3D 525 runs: 0", loc="left", fontsize=9)
    ax = fig.add_subplot(gs[0, 1])
    sup = {"2d": {"mixed_h1_g23": 14, "discordant_perm_families": 6, "mixed_h0": 34}, "3d": json.loads((P2 / "gate_3d_metrics.json").read_text())["decision"]["support"]}
    keys = [("mixed_h1_g23", "mixed h>=1\ng=2-3"), ("discordant_perm_families", "discordant\npermutation"), ("mixed_h0", "mixed h0")]
    for j, d in enumerate(("2d", "3d")):
        ax.bar(np.arange(3) + (j - 0.5) * 0.38, [sup[d][k] for k, _ in keys], 0.36, color=(ORANGE, BLUE)[j], label=f"{d.upper()} GATE")
    ax.axhline(10, color=RED, ls="--", lw=0.9); ax.text(2.45, 10.6, "floor 10", color=RED, fontsize=7, ha="right")
    ax.set_xticks(range(3)); ax.set_xticklabels([k for _, k in keys], fontsize=7.5); ax.set_ylabel("independent families")
    ax.legend(frameon=False, fontsize=7); ax.set_title("(b) fresh VAL_GATE support after the\npreregistered expansion: both DATA_LIMITED", loc="left", fontsize=9)
    ax = fig.add_subplot(gs[0, 2:])
    arms = ["F0", "M1s_s0", "G1s_s0", "M1ft_O1_s0", "M1ft_O1_s1", "M1ft_O2_s0", "M1ft_O2_s1"]
    for i, a in enumerate(arms):
        st = D[a]["strata"]["h>=1_g23"]; cc = D[a]["concordance"]
        x = i * 1.0
        ax.bar(x - 0.18, st["auroc"], 0.34, color=BLUE, label="h>=1, g=2-3 AUROC" if i == 0 else None)
        if st.get("auroc_ci"):
            ax.plot([x - 0.18] * 2, st["auroc_ci"], color=INK, lw=0.9)
        ax.bar(x + 0.18, cc["concordance"], 0.34, color=ORANGE, label="permutation concordance" if i == 0 else None)
        ax.plot([x + 0.18] * 2, cc["ci95"], color=INK, lw=0.9)
    ax.axhline(0.75, color=BLUE, ls="--", lw=0.8); ax.axhline(0.70, color=ORANGE, ls=":", lw=0.9); ax.axhline(0.5, color=MUTED, lw=0.6)
    ax.set_xticks(range(len(arms))); ax.set_xticklabels([a.replace("_s0", " s0").replace("_s1", " s1").replace("M1ft_", "M1ft ") + (" *" if a == "M1ft_O2_s0" else "") for a in arms], fontsize=7.5)
    ax.set_ylim(0, 1.02); ax.legend(frameon=False, fontsize=7, loc="lower right")
    ax.set_title("(c) 3D VAL_GATE, 22 families (descriptive; decision DATA_LIMITED; * = selected on SELECT)\nmulti-action intermediate AUROC < 0.75 for every arm; training lowers NLL, not this AUROC", loc="left", fontsize=9)
    rows3 = {r["root_id"]: r for r in jl(P2 / "rows3d_con.jsonl")}
    L3 = [e for e in jl(P2 / "labels_p2_3d.jsonl") if e["template"] in ("h0_PAIR_EB", "h1_PAIR_EB") and e["m"] == 2 and e["split"] == "GATE"]
    g = collections.defaultdict(dict)
    for e in L3:
        g[(e["root_id"], e["template"])][json.dumps(e["chunk"])] = e
    ex = []
    for t in ("h0_PAIR_EB", "h1_PAIR_EB"):
        for (rid, tt), v in sorted(g.items()):
            if tt == t and sorted(x["label"] for x in v.values()) == [0, 1]:
                ex.append(sorted(v.values(), key=lambda e: -e["label"])); break
    for k, pair in enumerate(ex[:2]):
        for j, e in enumerate(pair):
            a = fig.add_subplot(gs[1, 2 * k + j])
            F3.draw_scene(a, rows3[e["root_id"]], e["prefix"], e["chunk"], f"{'enabler first' if e['label'] else 'blocked body first'}: h={e['h']}", e["label"])
    fig.text(0.01, 0.005, "(d-g) Actual 3D VAL_GATE constructed scenes (top-down footprints at true scale from public inputs; red = target, green = already moved, blue = queried movers, dashed = goal).\n"
             "The enabler E (one new largest-size obstacle) was placed by the offline probe construction; X labels are actual teacher outcomes of the continuous 2-action chunk + connector.", fontsize=6.8, color=MUTED)
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "KGT3_P2.png", dpi=160); print(FIG / "KGT3_P2.png")


def p4():
    import numpy as np
    fig, ax = plt.subplots(1, 3, figsize=(14, 4))
    arms = ["REC-ORDERED", "REC-REORDER", "FLAT-INSERT", "GA", "GA-YONLY"]
    for j, d in enumerate(("2d", "3d")):
        f = R / "p4" / f"p4_model_only_{d}.jsonl"
        if not f.exists():
            continue
        Rr = jl(f)
        wall = [[r["arms"][a]["wall_s"] for r in Rr if a in r["arms"]] for a in arms]
        ax[0].boxplot(wall, positions=np.arange(5) + (j - 0.5) * 0.35, widths=0.3, patch_artist=True, boxprops=dict(facecolor=(ORANGE, BLUE)[j], alpha=0.6), medianprops=dict(color=INK))
        lng = [sum(r["arms"][a]["long"] for r in Rr if a in r["arms"]) / len(Rr) for a in arms]
        ax[1].bar(np.arange(5) + (j - 0.5) * 0.38, lng, 0.36, color=(ORANGE, BLUE)[j], label=f"{d.upper()} (n={len(Rr)})")
        cov = [np.mean([r["arms"]["GA"]["coverage"].get("witness_in_D4", False) for r in Rr]), np.mean([bool(r["arms"]["GA"]["coverage"].get("witness_optimized")) for r in Rr]),
               np.mean([r["arms"]["GA"]["coverage"]["selected_is_witness_set"] for r in Rr])]
        ax[2].bar(np.arange(3) + (j - 0.5) * 0.38, cov, 0.36, color=(ORANGE, BLUE)[j], label=d.upper())
    ax[0].set_xticks(range(5)); ax[0].set_xticklabels(arms, fontsize=7, rotation=15); ax[0].axhline(180, color=RED, ls="--", lw=0.8); ax[0].set_ylabel("planning wall s (CUDA-synced)")
    ax[0].set_title("(a) planner wall time per root (cap 180 s)\norange = 2D (30 roots), blue = 3D (20 roots)", loc="left", fontsize=9)
    ax[1].set_xticks(range(5)); ax[1].set_xticklabels(arms, fontsize=7, rotation=15); ax[1].set_ylabel("fraction of roots"); ax[1].legend(frameon=False, fontsize=7)
    ax[1].set_title("(b) selected plan longer than 3 actions\n(model-only; NOT physically verified)", loc="left", fontsize=9)
    ax[2].set_xticks(range(3)); ax[2].set_xticklabels(["witness set in\ninitial D4 pool", "witness set\nDP-optimized", "selected =\nwitness set"], fontsize=7.5)
    ax[2].set_ylim(0, 1); ax[2].legend(frameon=False, fontsize=7); ax[2].set_title("(c) Fig. 3B assignment funnel (evaluator-only)", loc="left", fontsize=9)
    fig.tight_layout(); fig.savefig(FIG / "KGT3_P4_planners.png", dpi=160); print(FIG / "KGT3_P4_planners.png")


if __name__ == "__main__":
    {"p2": p2, "p4": p4}[sys.argv[1]]()
