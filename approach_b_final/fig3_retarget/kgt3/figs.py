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


R4 = R / "r4"
ARMS_C = ["TOP4", "TOP6", "TOP8", "TOP12", "ANC16", "ANC64", "ANC256", "ANC1024", "FULL"]


def r4cover():
    """R4.1: proposal coverage vs budget, failure taxonomy, witness-destination rank, projected exact-search cost (actual model readouts)."""
    fig, ax = plt.subplots(1, 4, figsize=(17, 4.0))
    for dom, col in (("3d", BLUE), ("2d", ORANGE)):
        S = json.loads((R4 / "cover" / f"cover_{dom}.json").read_text())
        P = jl(R4 / "cover" / f"cover_{dom}.jsonl")
        for fam, mk, ls in (("TOP", "o", "-"), ("ANC", "s", "--")):
            arms = [a for a in ARMS_C if a.startswith(fam)]
            x = [sum(r["arms"][a]["unique_dests"] / max(1, r["arms"][a]["objects_with_proposals"]) for r in P) / len(P) for a in arms]
            ax[0].plot(x, [S["arms"][a]["action_recall"] for a in arms], ls, marker=mk, color=col, label=f"{dom.upper()} {'top-k of S1 marginal' if fam == 'TOP' else 'ancestral latent draws'}")
            ax[1].plot(x, [S["arms"][a]["assignment_coverage"] / S["n"] for a in arms], ls, marker=mk, color=col)
        ax[0].scatter([sum(r["arms"]["FULL"]["unique_dests"] / max(1, r["arms"]["FULL"]["objects_with_proposals"]) for r in P) / len(P)], [1.0], marker="*", s=90, color=col)
        ax[1].scatter([sum(r["arms"]["FULL"]["unique_dests"] / max(1, r["arms"]["FULL"]["objects_with_proposals"]) for r in P) / len(P)], [1.0], marker="*", s=90, color=col)
        ranks = [v["rank"] for r in P for v in r["rank"].values()]
        ax[2].hist([min(x if x is not None else 40, 40) for x in ranks], bins=range(0, 42, 2), histtype="step", lw=1.8, color=col, density=True, label=f"{dom.upper()} (S0 scene)")
        orp = [x for r in P for x in r["oracle_prefix_rank"]]
        ax[2].hist([min(x if x is not None else 40, 40) for x in orp], bins=range(0, 42, 2), histtype="step", lw=1.0, ls=":", color=col, density=True, label=f"{dom.upper()} (after witness prefix, oracle)")
        ax[3].plot(range(len(ARMS_C)), [S["arms"][a]["distinct_x_median"] for a in ARMS_C], marker="o", color=col, label=dom.upper())
    ax[0].set_xscale("log"); ax[1].set_xscale("log")
    ax[0].set(xlabel="unique destinations per object (log)", ylabel="witness action recall", title="(a) witness-action recall vs proposal budget"); ax[0].legend(fontsize=7, frameon=False)
    ax[1].set(xlabel="unique destinations per object (log)", ylabel="fraction of roots", title="(b) complete witness-assignment coverage")
    ax[2].set(xlabel="witness-destination rank in S1 marginal (40 = zero mass)", ylabel="density", title="(c) where the cVAE puts witness destinations"); ax[2].legend(fontsize=7, frameon=False)
    ax[3].axhline(1.2e6, color=MUTED, ls="--", lw=1); ax[3].text(0.1, 1.5e6, "declared EXACT envelope (1.2M readouts)", fontsize=7, color=MUTED)
    ax[3].set_yscale("log"); ax[3].set_xticks(range(len(ARMS_C))); ax[3].set_xticklabels(ARMS_C, rotation=45, fontsize=7)
    ax[3].set(ylabel="distinct (U, ordered chunk) readouts (median root)", title="(d) projected Fig. 3B exact-search cost"); ax[3].legend(fontsize=7, frameon=False)
    for a in ax:
        a.spines[["top", "right"]].set_visible(False)
    fig.suptitle("R4.1 frozen-cVAE proposal coverage on the exposed DEV witness panels (model-only; witness = evaluator only; one valid repair, not the only one)", fontsize=10, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(FIG / "R4_1_coverage.png", dpi=150); print(FIG / "R4_1_coverage.png")


def r4order():
    """R4.2: physical known-assignment order recovery (3D, 20 exposed DEV roots)."""
    D = json.loads((R4 / "order3d" / "R4_2_order3d.json").read_text())
    S, arms = D["summary"], ["F0", "M1s", "G1s", "O2", "RANDOM", "WITNESS"]
    fig, ax = plt.subplots(1, 4, figsize=(17, 4.0))
    n = D["n_roots"]
    ax[0].bar(range(6), [S[a]["x"] for a in arms], color=GREY, label="X = 1 (all relocations + connectors)")
    ax[0].bar(range(6), [S[a]["succ"] for a in arms], color=[BLUE, BLUE, GREEN, BLUE, MUTED, INK], label="X = 1, Y = 1 and independent replay")
    for i, a in enumerate(arms):
        ax[0].text(i, S[a]["succ"] + 0.3, str(S[a]["succ"]), ha="center", fontsize=8)
    ax[0].set_xticks(range(6)); ax[0].set_xticklabels(arms); ax[0].set_ylim(0, n + 1)
    ax[0].set(ylabel=f"roots (of {n})", title="(a) one committed order + partition per arm"); ax[0].legend(fontsize=7, frameon=False, loc="upper left")
    ks = sorted({int(k) for a in arms for k in S[a]["first_failed"] if k not in (None, "None")})
    bot = [0] * 6
    for j, k in enumerate(ks):
        v = [S[a]["first_failed"].get(str(k), 0) for a in arms]
        ax[1].bar(range(6), v, bottom=bot, color=plt.cm.Oranges(0.35 + 0.15 * j), label=f"relocation {k + 1}")
        bot = [b + x for b, x in zip(bot, v)]
    cf = [S[a]["connector_fail"] for a in arms]
    ax[1].bar(range(6), cf, bottom=bot, color=RED, label="boundary connector")
    ax[1].set_xticks(range(6)); ax[1].set_xticklabels(arms); ax[1].set(ylabel="failed runs", title="(b) where the failed runs stopped"); ax[1].legend(fontsize=7, frameon=False)
    P = D["partition_study"]
    tags = ["singletons", "dp", "front", "back"]
    for i, base in enumerate(("WITNESS", "G1s")):
        ax[2].bar([x + 0.38 * i for x in range(4)], [P.get(f"{base}:{t}:succ", 0) for t in tags], width=0.38, color=[INK, GREEN][i], label=f"{base} order")
    ax[2].set_xticks([x + 0.19 for x in range(4)]); ax[2].set_xticklabels(["all singletons", "model-DP", "front 3-chunks", "back 3-chunks"], fontsize=8)
    ax[2].set(ylabel=f"successful roots (of {n})", title="(c) same fixed order, different chunk boundaries"); ax[2].legend(fontsize=7, frameon=False)
    pr = D["per_root"]
    pt = [S[a].get("plan_wall_s_median", 0) for a in arms[:4]]
    vt = []
    for a in arms[:4]:
        w = sorted(pr[r][a].get("wall_s") or 0 for r in pr if pr[r][a].get("src") == "NEW")
        vt.append(w[len(w) // 2] if w else 0)
    ax[3].bar([x - 0.2 for x in range(4)], pt, width=0.4, color=BLUE, label="model-only planning (GPU, median)")
    ax[3].bar([x + 0.2 for x in range(4)], vt, width=0.4, color=ORANGE, label="physical verification (CPU wall, median new run)")
    ax[3].set_yscale("log"); ax[3].set_xticks(range(4)); ax[3].set_xticklabels(arms[:4]); ax[3].set(ylabel="seconds (log)", title="(d) planning vs verification time"); ax[3].legend(fontsize=7, frameon=False)
    for a in ax:
        a.spines[["top", "right"]].set_visible(False)
    fig.suptitle("R4.2 3D physical order recovery GIVEN the unordered witness assignment (development diagnostic; exposed roots; not P3)", fontsize=10, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(FIG / "R4_2_order3d.png", dpi=150); print(FIG / "R4_2_order3d.png")


if __name__ == "__main__":
    {"p2": p2, "p4": p4, "r4cover": r4cover, "r4order": r4order}[sys.argv[1]]()
