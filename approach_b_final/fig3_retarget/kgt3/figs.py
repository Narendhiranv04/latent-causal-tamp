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
    ks = sorted({int(k) for a in arms for k in S[a]["first_failed"] if k not in (None, "None", "null")})
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


def _heat(ax, mat, hs, gs, title):
    """mat: {(h, g): (pos, neg, unresolved)} -> annotated heatmap of decided chunk labels."""
    import numpy as np
    A = np.zeros((len(hs), len(gs)))
    for i, hh in enumerate(hs):
        for j, g in enumerate(gs):
            p_, n_, u_ = mat.get((hh, g), (0, 0, 0))
            A[i, j] = p_ + n_
            ax.text(j, i, f"+{p_} / -{n_}" + (f"\n?{u_}" if u_ else ""), ha="center", va="center", fontsize=8, color=INK)
    ax.imshow(A, cmap="Blues", vmin=0, vmax=max(1, A.max()) * 1.6, aspect="auto"); ax.grid(False)
    ax.set_xticks(range(len(gs))); ax.set_xticklabels([f"chunk {g}" for g in gs]); ax.set_yticks(range(len(hs))); ax.set_yticklabels([f"{hh} preceding" for hh in hs])
    ax.set_title(title, fontsize=10)


def _scene2d(ax, cells, goal, arrows, title):
    from matplotlib.patches import Circle, FancyArrowPatch, Rectangle
    xy = lambda c: (c % 8 + 0.5, c // 8 + 0.5)  # noqa: E731
    for c in range(64):
        ax.add_patch(Rectangle((c % 8, c // 8), 1, 1, fc="#f6f8fa" if (c % 8 + c // 8) % 2 else "white", ec="#eaeef2", lw=0.4))
    for c in (50, 58):
        ax.add_patch(Rectangle((c % 8, c // 8), 1, 1, fc="#ddf4ff", ec="none"))
    ax.add_patch(Rectangle((goal % 8 + 0.1, goal // 8 + 0.1), 0.8, 0.8, fc="#dafbe1", ec=GREEN, lw=0.8))
    mv = {o for o, _ in arrows}
    for o, c in cells.items():
        ax.add_patch(Circle(xy(c), 0.32, fc=GREEN if o == "t0" else (RED if o in mv else GREY), ec=INK, lw=0.5))
        ax.text(*xy(c), o if o == "t0" else o[1:], ha="center", va="center", fontsize=6.5, color="white" if o in mv or o == "t0" else INK)
    for k, (o, d) in enumerate(arrows):
        ax.add_patch(FancyArrowPatch(xy(cells[o]), xy(d), arrowstyle="-|>", mutation_scale=9, color=ORANGE, lw=1.2))
        ax.text(*xy(d), str(k + 1), ha="center", va="center", fontsize=7, color=ORANGE, fontweight="bold")
    ax.set_xlim(0, 8); ax.set_ylim(0, 8); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([]); ax.set_title(title, fontsize=8, loc="left")


def r4b2d():
    """R4.3: 2D witness-first construction yield, decided chunk coverage, actual constructed scene with verified vs failed order."""
    D = json.loads((R4 / "b2d" / "R4_3_build2d.json").read_text())
    F = jl(R4 / "b2d" / "families.jsonl")
    fig, ax = plt.subplots(1, 4, figsize=(17, 4.2))
    lv = collections.Counter(((f.get("family") or {}).get("level") or 0) for f in F)
    ax[0].bar(["attempted", "level >= 2\nE enables B", "level 3\nF > E > B"], [len(F), lv[2] + lv[3], lv[3]], color=[GREY, BLUE, GREEN])
    for i, v in enumerate([len(F), lv[2] + lv[3], lv[3]]):
        ax[0].text(i, v + 0.5, str(v), ha="center", fontsize=8)
    ax[0].set(ylabel="families", title="(a) witness-first construction yield")
    mat = collections.defaultdict(lambda: [0, 0, 0])
    for k, v in D["chunk_matrix"].items():
        hh, g, kind = k.split("|"); hh, g = int(hh[1:]), int(g[1:])
        mat[(hh, g)][0 if kind.startswith("pos") else 1 if kind == "neg_certified" else 2] += v
    _heat(ax[1], {k: tuple(v) for k, v in mat.items()}, sorted({k[0] for k in mat}), [1, 2, 3], "(b) decided chunk labels (+ replayed / prefix, - certified)")
    ex = next((f for f in F if (f.get("family") or {}).get("level") == 3), None) or next((f for f in F if ((f.get("family") or {}).get("level") or 0) >= 2), None)
    if ex:
        fm = ex["family"]
        if fm.get("level") == 3:
            S = fm["cells2"]; ok = [("oF", fm["pF"]), ("oE", fm["pE"]), ("oB", fm["pB"])]; bad = [("oB", fm["pB"]), ("oE", fm["pE"]), ("oF", fm["pF"])]
            r3 = fm["L3"]
            _scene2d(ax[2], S, fm["goal"], ok, f"(c) {ex['key']}: F, E, B as one chunk -> {r3.get('FEB[3]')}")
            _scene2d(ax[3], S, fm["goal"], bad, f"(d) same assignment, B, E, F -> {r3.get('BEF[3]')}")
        else:
            S = fm["cells1"]
            _scene2d(ax[2], S, fm["goal"], [("oE", fm["pE"]), ("oB", fm["pB"])], f"(c) {ex['key']}: E then B -> {fm['L2'].get('EB[2]')}")
            _scene2d(ax[3], S, fm["goal"], [("oB", fm["pB"]), ("oE", fm["pE"])], f"(d) B then E -> {fm['L2'].get('BE[2]')}")
    for a in ax[:1]:
        a.spines[["top", "right"]].set_visible(False)
    fig.suptitle("R4.3 2D witness-first dependency construction (unchanged BXY teacher, full articulated planar arm; light blue = arm footprint at q_ref; numbers = execution order)", fontsize=10, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(FIG / "R4_3_build2d.png", dpi=150); print(FIG / "R4_3_build2d.png")


def r4d3d():
    """R4.4: 3D intermediate-state coverage matrix, temporary-target physical interventions, frozen-model temporary-target diagnostic."""
    D = json.loads((R4 / "d3d" / "R4_4_deep3d.json").read_text())
    T = json.loads((R4 / "d3d" / "temp_model.json").read_text())["summary"]
    fig, ax = plt.subplots(1, 3, figsize=(16, 5.0))
    mat = collections.defaultdict(lambda: [0, 0, 0])
    for hh, row in D["coverage_matrix"].items():
        for k, v in row.items():
            g = int(k.split("_")[0][1:])
            mat[(int(hh[1:]), g)][0 if "_pos" in k else 1] += v
    _heat(ax[0], {k: tuple(v) for k, v in mat.items()}, sorted({k[0] for k in mat}), [1, 2, 3], "(a) decided chunk labels by preceding relocations")
    iv = D["interventions"]
    tags = [t for t in ("TEMP_baseline", "TEMP_beneficial", "TEMP_irrelevant", "TEMP_harmful") if t in iv]
    ax[1].bar(range(len(tags)), [iv[t].get("SUCCESS", 0) for t in tags], color=GREEN, label="temporary target B -> pB VERIFIED")
    ax[1].bar(range(len(tags)), [sum(v for k, v in iv[t].items() if k != "SUCCESS") for t in tags], bottom=[iv[t].get("SUCCESS", 0) for t in tags], color=GREY, label="not verified (certified / budget / other)")
    ax[1].set_xticks(range(len(tags))); ax[1].set_xticklabels([t[5:] for t in tags]); ax[1].set(ylabel="families", title="(b) physical temporary-target interventions"); ax[1].legend(fontsize=7, frameon=False)
    n = T["n"]
    keys = [("dY_pos", "frozen Y_temp rises\nafter moving E"), ("E_proposed", "cVAE proposes E\n(temporary task)"), ("pE_in_top4", "cVAE top-4 has\nE's destination"),
            ("enabler_admitted", "recursion admits\nE -> pE"), ("best_E_proposal_admitted", "recursion admits\nsome E proposal")]
    ax[2].bar(range(len(keys)), [T[k] / n for k, _ in keys], color=BLUE)
    ir = T["irrelevant_admitted"]
    ax[2].bar([len(keys)], [ir[0] / max(1, ir[1])], color=RED)
    ax[2].bar([len(keys) + 1], [T["other_proposals_admitted_rate"]], color=RED)
    ax[2].set_xticks(range(len(keys) + 2)); ax[2].set_xticklabels([l for _, l in keys] + ["irrelevant Z\nadmitted", "other proposals\nadmitted"], fontsize=7, rotation=35, ha="right")
    ax[2].set(ylim=(0, 1.05), ylabel=f"fraction of {n} verified E-enables-B families", title="(c) frozen-model Fig. 3A assumptions (model-only)")
    for a in ax[1:]:
        a.spines[["top", "right"]].set_visible(False)
    fig.suptitle("R4.4 3D deeper intermediate-state supervision + temporary-target pilot (unchanged SHELF66V3 teacher; collection only, no training)", fontsize=10, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(FIG / "R4_4_deep3d.png", dpi=150); print(FIG / "R4_4_deep3d.png")


def r4smoke():
    """R4.5: end-to-end development smoke per domain (committed plans, no assignment / order / K given) + Fig. 3A / 3B failure funnels."""
    doms = [d for d in ("3d", "2d") if (R4 / "smoke" / f"R4_5_{d}.json").exists()]
    fig, ax = plt.subplots(1, 2 * len(doms), figsize=(8.5 * len(doms), 4.0), squeeze=False)
    ax = ax[0]
    arms = ["FLAT-INSERT", "REC-ORDERED", "GA", "B0"]
    for i, d in enumerate(doms):
        D = json.loads((R4 / "smoke" / f"R4_5_{d}.json").read_text()); S, n = D["summary"], D["n_roots"]
        w = 0.2
        for j, (k, col, lab) in enumerate((("x", GREY, "X = 1"), ("y", ORANGE, "Y = 1 (endpoint)"), ("succ", GREEN, "X, Y, replay"), ("long_succ", BLUE, "success with > 3 actions"))):
            ax[2 * i].bar([a + (j - 1.5) * w for a in range(4)], [S[a][k] for a in arms], width=w, color=col, label=lab)
        ax[2 * i].set_xticks(range(4)); ax[2 * i].set_xticklabels(["flat control", "Fig. 3A REC", "Fig. 3B GA", "B0 (K<=3)"], fontsize=8)
        ax[2 * i].set(ylabel=f"roots (of {n})", ylim=(0, n + 1), title=f"({'abcd'[2 * i]}) {d.upper()} committed repairs, physical outcome"); ax[2 * i].legend(fontsize=7, frameon=False)
        P = D["per_root"]
        for k, arm in enumerate(("REC-ORDERED", "GA")):
            rr = [P[r][arm] for r in P]
            st = [n, sum(x["length"] > 0 for x in rr), sum(x.get("x") == 1 for x in rr), sum(x.get("x") == 1 and x.get("y") == 1 for x in rr), sum(x["succ"] for x in rr), sum(x["succ"] and x["length"] > 3 for x in rr)]
            ax[2 * i + 1].plot(range(6), st, marker="o", color=[GREEN, BLUE][k], label="Fig. 3A REC-ORDERED" if k == 0 else "Fig. 3B GA")
        ax[2 * i + 1].set_xticks(range(6)); ax[2 * i + 1].set_xticklabels(["roots", "repair\ncommitted", "X = 1", "X = 1\nand Y = 1", "+ replay", "of which\n> 3 actions"], fontsize=8)
        ax[2 * i + 1].set(ylabel="roots", title=f"({'abcd'[2 * i + 1]}) {d.upper()} failure-stage funnel"); ax[2 * i + 1].legend(fontsize=7, frameon=False)
    for a in ax:
        a.spines[["top", "right"]].set_visible(False)
    fig.suptitle("R4.5 end-to-end development smoke (exposed DEV roots; one committed plan per planner; witness never given)", fontsize=10, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(FIG / "R4_5_smoke.png", dpi=150); print(FIG / "R4_5_smoke.png")


def r4compute():
    """Compute breakdown from the R4 ledger (CPU-h per physical stage vs cap; model-only GPU wall)."""
    L = json.loads((R4 / "R4_LEDGER.json").read_text())
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
    st = L["cpu"]
    names = list(st)
    ax[0].barh(names, [st[k]["cap"] for k in names], color=GREY, label="authorized cap")
    ax[0].barh(names, [st[k]["used"] for k in names], color=BLUE, label="used")
    for i, k in enumerate(names):
        ax[0].text(st[k]["used"] + 0.1, i, f"{st[k]['used']:.2f}", va="center", fontsize=8)
    ax[0].set(xlabel="aggregate CPU-hours", title="(a) physical teacher compute"); ax[0].legend(fontsize=7, frameon=False)
    g = L["gpu_wall_h"]
    ax[1].barh(list(g), list(g.values()), color=ORANGE)
    ax[1].set(xlabel="process wall-hours with the GPU model loaded (mostly CPU-bound DP)", title="(b) model-only planning / diagnostics")
    for a in ax:
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(FIG / "R4_compute.png", dpi=150); print(FIG / "R4_compute.png")


R5 = R / "r5"


def r5xl():
    """R5.2 controlled X ablations: VAL NLL matrix (seeds), matched-pair concordance, training curves (chosen recipe), reliability (selected)."""
    import numpy as np
    fig, ax = plt.subplots(2, 4, figsize=(19, 8))
    C = {json.loads(l)["name"]: json.loads(l)["curve"] for l in open(R5 / "xl" / "curves" / "curves.jsonl")}
    for i, d in enumerate(("2d", "3d")):
        Rr = jl(R5 / "xl" / f"results_{d}.jsonl")
        rc = json.loads((R5 / "xl" / f"recipe_{d}.json").read_text())
        cells = [(rep, dat) for rep in "AMG" for dat in (0, 1)]
        for j, (rep, dat) in enumerate(cells):
            v = [r["best_val"] for r in Rr if r["rep"] == rep and r["data"] == dat and r["recipe"] == rc[rep] and not r["ctrl"]]
            ax[i, 0].bar(j, np.mean(v), color=[GREY, BLUE][dat], edgecolor=INK if rep == "G" else "none")
            ax[i, 0].scatter([j] * len(v), v, color=INK, s=12, zorder=3)
        for k, c in enumerate(("ORDINV", "UNCOUPLED")):
            v = [r["best_val"] for r in Rr if r["ctrl"] == c]
            ax[i, 0].bar(len(cells) + k, np.mean(v), color=ORANGE); ax[i, 0].scatter([len(cells) + k] * len(v), v, color=INK, s=12, zorder=3)
        ax[i, 0].set_xticks(range(len(cells) + 2)); ax[i, 0].set_xticklabels([f"{r}{dd}" for r, dd in cells] + ["G1 ord-inv", "G1 uncoupled"], fontsize=7, rotation=30)
        ax[i, 0].set(ylabel="VAL family NLL (marginal pX)", title=f"({'ae'[i]}) {d.upper()} ablation matrix (0 = original, 1 = + strict local)")
        for j, (rep, dat) in enumerate(cells):
            v = [((r.get("val") or {}).get("concordance") or {}).get("concordance") for r in Rr if r["rep"] == rep and r["data"] == dat and r["recipe"] == rc[rep] and not r["ctrl"]]
            v = [x for x in v if x is not None]
            ax[i, 1].bar(j, np.mean(v), color=[GREY, BLUE][dat]); ax[i, 1].scatter([j] * len(v), v, color=INK, s=12, zorder=3)
        ax[i, 1].axhline(0.5, color=MUTED, ls="--", lw=1)
        ax[i, 1].set_xticks(range(len(cells))); ax[i, 1].set_xticklabels([f"{r}{dd}" for r, dd in cells], fontsize=8)
        ax[i, 1].set(ylim=(0, 1.05), ylabel="matched-order concordance (VAL)", title=f"({'bf'[i]}) {d.upper()} order ranking on same-endpoint pairs")
        for rep, col in (("A", GREY), ("M", ORANGE), ("G", BLUE)):
            for s_ in (0, 1):
                cv = C.get(f"{d}_{rep}1_{rc[rep]}_base_s{s_}")
                if cv:
                    ax[i, 2].plot([c["epoch"] for c in cv], [c["val"] for c in cv], color=col, lw=1.4 if s_ == 0 else 0.8, ls="-" if s_ == 0 else "--", label=f"{rep}1 s{s_}" if s_ == 0 else None)
        ax[i, 2].set(xlabel="epoch", ylabel="VAL family NLL", title=f"({'cg'[i]}) {d.upper()} learning curves (chosen recipe)"); ax[i, 2].legend(fontsize=7, frameon=False)
        cal = json.loads((R5 / "r53" / f"calib_{d}.json").read_text())
        rel = cal["reliability"]
        ax[i, 3].plot([0, 1], [0, 1], color=MUTED, ls="--", lw=1)
        ax[i, 3].plot([b["mean_p"] for b in rel], [b["freq"] for b in rel], marker="o", color=BLUE)
        for b in rel:
            ax[i, 3].text(b["mean_p"], b["freq"] + 0.03, str(b["n"]), fontsize=6, ha="center", color=MUTED)
        ax[i, 3].set(xlabel="predicted marginal pX", ylabel="observed X rate", xlim=(0, 1), ylim=(0, 1.08),
                     title=f"({'dh'[i]}) {d.upper()} reliability, {cal['name']} {'(T = %.2f)' % cal['T'] if cal['adopt'] else '(raw)'}")
    for a in ax.flat:
        a.spines[["top", "right"]].set_visible(False)
    fig.suptitle("R5.2 controlled local-X learning (fresh X heads, frozen Y / cVAE; strict local labels; selection by VAL NLL only)", fontsize=11, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(FIG / "R5_2_xlearning.png", dpi=140); print(FIG / "R5_2_xlearning.png")


def r53fig():
    """R5.3: energy by size (selected X), has_multi binding, S0 vs S2 chosen length, admission true / false rates vs m (paired), proposal coverage."""
    import numpy as np
    fig, ax = plt.subplots(2, 4, figsize=(19, 8))
    for i, d in enumerate(("2d", "3d")):
        L = jl(R5 / "r53" / f"length_{d}_sel{d}.jsonl")
        for arm, col in (("GA", BLUE), ("REC-ORDERED", GREEN)):
            sizes = sorted({int(k) for r in L for k in r["arms"][arm]["by_size"]})
            ax[i, 0].plot(sizes, [np.median([r["arms"][arm]["by_size"][str(k)]["E"] for r in L if str(k) in r["arms"][arm]["by_size"]]) for k in sizes], marker="o", color=col, label=f"{arm} best E")
            if arm == "GA":
                ax[i, 0].plot(sizes, [np.median([-np.log(max(1e-8, r["arms"][arm]["by_size"][str(k)]["y"])) for r in L if str(k) in r["arms"][arm]["by_size"]]) for k in sizes], ls="--", color=ORANGE, label="GA -log Y_global")
        ax[i, 0].set(xlabel="assignment size", ylabel="median over DEV roots", title=f"({'ae'[i]}) {d.upper()} energy by size (selected X)"); ax[i, 0].legend(fontsize=7, frameon=False)
        hm = [x for r in L for x in r["arms"]["GA"]["has_multi"]]
        cfg = json.loads((R5 / "r6" / "config.json").read_text())[d]
        for k, arm in enumerate(("GA", "REC-ORDERED")):
            for j, rn in enumerate(("S0", "S2")):
                lens = [r["arms"][arm]["picks"].get(rn, {}).get("len") for r in L if r["arms"][arm]["picks"].get(rn)]
                if lens:
                    c = collections.Counter(lens)
                    ax[i, 1].bar([x + 0.2 * (2 * k + j) - 0.3 for x in range(1, 6)], [c.get(x, 0) for x in range(1, 6)], width=0.2,
                                 color=[BLUE, GREEN][k], alpha=1.0 if j == 0 else 0.5, label=f"{arm} {rn}")
        ax[i, 1].set(xlabel="selected repair length (model-only, DEV)", ylabel="roots",
                     title=f"({'bf'[i]}) {d.upper()} chosen length; rule = {cfg['selection_rule']}; has_multi binds {sum(x['binds'] for x in hm)}/{len(hm)}")
        ax[i, 1].legend(fontsize=7, frameon=False)
        A = json.loads((R5 / "r53" / f"admission_{d}.json").read_text())
        ms = [0.0, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3]
        for sp, ls in (("VAL", "-"), ("TRAIN", "--"), ("EXPOSED", ":")):
            ta = [A[sp][f"A1_m{m}"]["true_admit"] for m in ms]; fa = [A[sp][f"A1_m{m}"]["false_admit"] for m in ms]
            ax[i, 2].plot(ms, [x if x is not None else np.nan for x in ta], ls=ls, color=GREEN, marker="o", ms=3, label=f"{sp} true admit")
            if any(x is not None for x in fa):
                ax[i, 2].plot(ms, [x if x is not None else np.nan for x in fa], ls=ls, color=RED, marker="o", ms=3, label=f"{sp} false admit")
        ax[i, 2].axvline(A["choice"]["m"], color=MUTED, lw=1)
        ax[i, 2].set(xlabel="admission margin m (A1)", ylabel="rate (paired families)", ylim=(0, 1.05), title=f"({'cg'[i]}) {d.upper()} admission; chosen {A['choice']['rule']} m={A['choice']['m']}")
        ax[i, 2].legend(fontsize=6, frameon=False)
        P = json.loads((R5 / "r53" / f"proposals_{d}.json").read_text())["summary"]
        rows = [(f"{m}", P[m]) for m in ("S1", "TOP8", "ANC64", "UNIF")]
        for tag in ("_rec_orig", "_rec_local"):
            f = R5 / "r53" / f"proposals_{d}{tag}.json"
            if f.exists():
                Q = json.loads(f.read_text())["summary"]
                rows += [(f"{m} {tag[5:].upper()}", Q[m]) for m in Q]
        ax[i, 3].bar([x - 0.2 for x in range(len(rows))], [v["ga_recall"] for _, v in rows], width=0.4, color=BLUE, label="GA initial pool")
        ax[i, 3].bar([x + 0.2 for x in range(len(rows))], [v["rec_recall"] for _, v in rows], width=0.4, color=GREEN, label="Fig. 3A recursive union")
        ax[i, 3].axhline(0.5, color=MUTED, ls="--", lw=1)
        ax[i, 3].set_xticks(range(len(rows))); ax[i, 3].set_xticklabels([n for n, _ in rows], fontsize=7, rotation=30)
        ax[i, 3].set(ylabel="witness-action recall (DEV)", ylim=(0, 1.05), title=f"({'dh'[i]}) {d.upper()} proposal coverage (UNIF = labelled control)"); ax[i, 3].legend(fontsize=7, frameon=False)
    for a in ax.flat:
        a.spines[["top", "right"]].set_visible(False)
    fig.suptitle("R5.3 energy, selection, admission and proposals for the selected X (model-only on DEV; admission paired on physical labels)", fontsize=11, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(FIG / "R5_3_scoring.png", dpi=140); print(FIG / "R5_3_scoring.png")


if __name__ == "__main__":
    {"r53fig": r53fig, "r5xl": r5xl, "p2": p2, "p4": p4, "r4cover": r4cover, "r4order": r4order, "r4b2d": r4b2d, "r4d3d": r4d3d, "r4smoke": r4smoke, "r4compute": r4compute}[sys.argv[1]]()
