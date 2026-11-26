#!/usr/bin/env python3
"""R3 figures (local; reads the committed report JSONs).  python figs3.py r30 [R24_LABELS_3D.jsonl]"""
from __future__ import annotations

import json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

R = Path(__file__).resolve().parent / "reports"
FIG = R / "figures"
INK, MUTED, GRID = "#1f2328", "#6e7781", "#d0d7de"
BLUE, ORANGE, GREEN, RED = "#2f6fb0", "#d9822b", "#3a8f5c", "#c4453c"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5})


def _auc(d, k):
    v = d.get(k) or {}
    return v.get("auroc"), v.get("auroc_ci")


def r30(lab_path):
    rd = {d: json.loads((R / "r30" / f"readouts_{d}.json").read_text()) for d in ("3d", "2d")}
    sl = json.loads((R / "r30" / "shortlist_3d.json").read_text())
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8), gridspec_kw={"width_ratios": [1.5, 1, 1]})
    # (a) AUROC of marginal pX / conditional pX1 / pX0 / p11 on the natural VAL panel and the R2.4 hard panel (3D)
    nat, hard = rd["3d"]["natural_val"], rd["3d"]["hard_r24"]
    groups = [("natural VAL\nall m<=3", {k: nat[f"{k}_vs_x_all"]["all"] if k != "px" else nat["marginal_px_vs_x"]["all"] for k in ("px", "px1", "px0")}),
              ("natural VAL m=1\n(133/134 pos.)", {"px": nat["marginal_px_vs_x"]["m1"]}),
              ("R2.4 hard\nh=0", {k: hard[k]["h0"] for k in ("px", "px1", "px0")}),
              ("R2.4 hard\nh>=1", {k: hard[k]["h>=1"] for k in ("px", "px1", "px0")}),
              ("R2.4 hard\nh>=1, m=2-3", {k: hard[k]["h>=1_m23"] for k in ("px", "px1", "px0")})]
    cols = {"px": BLUE, "px1": ORANGE, "px0": GREEN}
    for gi, (g, d) in enumerate(groups):
        for ki, k in enumerate(("px", "px1", "px0")):
            v = d.get(k)
            if not v or v.get("auroc") is None:
                continue
            x = gi + (ki - 1) * 0.26
            ci = v.get("auroc_ci")
            ax[0].bar(x, v["auroc"], 0.24, color=cols[k], label={"px": "marginal pX", "px1": "pX | Y=1", "px0": "pX | Y=0"}[k] if gi == 0 else None)
            if ci:
                ax[0].plot([x, x], ci, color=INK, lw=1)
    ax[0].axhline(0.5, color=MUTED, ls=":", lw=1); ax[0].axhline(0.75, color=RED, ls="--", lw=0.8)
    ax[0].text(2.45, 0.765, "R3.2 gate 0.75", color=RED, fontsize=7, ha="right")
    ax[0].set_xticks(range(len(groups))); ax[0].set_xticklabels([g for g, _ in groups], fontsize=7.5)
    ax[0].set_ylim(0, 1.02); ax[0].set_ylabel("AUROC vs exact X label (family-cluster 95% CI)")
    ax[0].set_title("(a) 3D frozen X readouts: natural panel vs hard local panel", loc="left", fontsize=9)
    ax[0].legend(frameon=False, fontsize=7.5, loc="upper right", bbox_to_anchor=(1.0, 0.97))
        # (b) confident negatives: pX1 vs pX0
    L = [json.loads(l) for l in open(lab_path)]
    L = [e for e in L if e["t"] == "chunk" and e["label"] in (0, 1) and e.get("px1") is not None]
    for lab, c, nm in ((1, BLUE, "executable"), (0, RED, "not executable")):
        s = [e for e in L if e["label"] == lab]
        ax[1].scatter([e["px0"] for e in s], [e["px1"] for e in s], s=9, color=c, alpha=0.55, edgecolors="white", linewidths=0.3, label=f"{nm} (n={len(s)})")
    ax[1].set_xlabel("pX | Y=0  = sig(a)"); ax[1].set_ylabel("pX | Y=1  = sig(a+w)")
    ax[1].set_title("(b) 3D hard panel: both conditional logits high\non 144/157 confident negatives", loc="left", fontsize=9)
    ax[1].legend(frameon=False, fontsize=7.5, loc="lower right"); ax[1].set_xlim(-0.02, 1.02); ax[1].set_ylim(-0.02, 1.02)
    # (c) GA shortlist truncation
    ip = sorted([v for v in sl.values() if v["in_union_pool"]], key=lambda v: v["rank_by_y"])
    ax[2].scatter([v["n_same_size"] for v in ip], [v["rank_by_y"] for v in ip], s=22, color=ORANGE, edgecolors="white", linewidths=0.4, zorder=3)
    ax[2].axhline(4, color=RED, ls="--", lw=0.8); ax[2].text(5e3, 5.2, "top-4 shortlist", color=RED, fontsize=7)
    ax[2].set_xscale("log"); ax[2].set_yscale("log"); ax[2].xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter()); ax[2].set_xlabel("same-size sets enumerated (union pool)"); ax[2].set_ylabel("rank of verified witness set by Y_global")
    ax[2].set_title(f"(c) GA Y-only shortlist: witness set in pool\non {len(ip)}/20 roots, ranked 349-11,897", loc="left", fontsize=9)
    fig.tight_layout()
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "R3_0_audit.png", dpi=160); print(FIG / "R3_0_audit.png")


def draw_scene(ax, row, pre, chunk, title, lab=None, px=None):
    """Top-down scene from PUBLIC inputs (schematic footprints at the canonical prefix; arrows = the queried chunk, numbered by order)."""
    from matplotlib.patches import Circle, Rectangle
    inp = row["inputs"]; xy = [list(p) for p in inp["xy0"]]; cell = inp["cell_xy"]
    for o, d in pre:
        xy[int(o)] = cell[str(int(d))]
    xs = [cell[c][0] for c in cell]; ys = [cell[c][1] for c in cell]
    for c in inp["legal_cells"]:
        x, y = cell[str(c)]
        ax.add_patch(Rectangle((x - 0.035, y - 0.035), 0.07, 0.07, fc="none", ec=GRID, lw=0.4))
    gx, gy = inp["goal"]
    ax.add_patch(Rectangle((gx - 0.035, gy - 0.035), 0.07, 0.07, fc="#f3e8c8", ec=ORANGE, lw=0.8, ls="--"))
    moved = {int(o) for o, _ in pre}; mv = {int(o) for o, _ in chunk}
    for i, (x, y) in enumerate(xy):
        a = inp["attrs"][i]
        r = a[2] if len(a) == 5 else a[0]
        is_t = (a[4] if len(a) == 5 else a[1]) > 0.5
        fc = RED if is_t else (GREEN if i in moved else ("#9fb7d6" if i not in mv else BLUE))
        if len(a) == 5 and a[0] > 0.5:
            ax.add_patch(Rectangle((x - r, y - r), 2 * r, 2 * r, fc=fc, ec="white", lw=0.6, zorder=3))
        else:
            ax.add_patch(Circle((x, y), r, fc=fc, ec="white", lw=0.6, zorder=3))
    for k, (o, d) in enumerate(chunk):
        x0, y0 = xy[int(o)]; x1, y1 = cell[str(int(d))]
        ax.annotate("", (x1, y1), (x0, y0), arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.0), zorder=4)
        ax.text(x1, y1, str(k + 1), fontsize=7, ha="center", va="center", color="white", zorder=5,
                bbox=dict(boxstyle="circle,pad=0.15", fc=INK, ec="none"))
    bx, by = inp["base"]
    x0, x1, y0, y1 = min(xs) - 0.05, max(xs) + 0.05, min(ys) - 0.05, max(ys) + 0.05
    ax.annotate("base", (min(max(bx, x0), x1), min(max(by, y0), y1)), fontsize=6, color=MUTED, ha="left", va="center")
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    tag = "" if lab is None else (" | X=1" if lab == 1 else " | X=0")
    ax.set_title(title.replace(": ", "\n", 1) + ", " + tag.strip(" |") + ("" if px is None else f", F0 pX = {px:.2f}"), fontsize=7.5, loc="left", color=GREEN if lab == 1 else RED if lab == 0 else INK)


def r31(lab_path, rows_path):
    import collections
    L = [json.loads(l) for l in open(lab_path)]
    rows = json.loads(Path(rows_path).read_text())
    fig = plt.figure(figsize=(13, 7.4))
    gs = fig.add_gridspec(2, 5, height_ratios=[0.8, 1.35], hspace=0.32, wspace=0.12, left=0.05, right=0.99, top=0.95, bottom=0.05)
    ax = fig.add_subplot(gs[0, :2])
    cats = [("h0", "m1"), ("h0", "m2-3"), ("h>=1", "m1"), ("h>=1", "m2-3")]
    for si, sp in enumerate(("TRAIN_SCALE", "VAL_SCALE")):
        for ci, (h, m) in enumerate(cats):
            S = [e for e in L if e["split"] == sp and (e["h"] == 0) == (h == "h0") and (e["m"] == 1) == (m == "m1") and e["label"] in (0, 1)]
            pos, neg = sum(e["label"] for e in S), sum(1 - e["label"] for e in S)
            x = ci + (si - 0.5) * 0.38
            ax.bar(x, pos, 0.34, color=BLUE if si == 0 else "#8fb3dc"); ax.bar(x, neg, 0.34, bottom=pos, color=RED if si == 0 else "#e6a09a")
            ax.text(x, pos + neg + 2, f"{pos}/{neg}", ha="center", fontsize=6.5, color=MUTED)
    ax.set_xticks(range(4)); ax.set_xticklabels([f"{h}, {m}" for h, m in cats])
    ax.set_ylabel("exact local labels (executable / not)")
    ax.set_title("(a) R3.1 3D yield: dark = TRAIN_SCALE, light = VAL_SCALE; blue executable, red not", loc="left", fontsize=9)
    ax2 = fig.add_subplot(gs[0, 3:])
    st = collections.Counter((e["h"] > 0, e["status"].split(":")[0][:28]) for e in L if e["label"] == 0)
    items = sorted(st.items(), key=lambda t: -t[1])[:8]
    ax2.barh(range(len(items)), [v for _, v in items], color=[RED if not k[0] else ORANGE for k, _ in items])
    ax2.set_yticks(range(len(items))); ax2.set_yticklabels([("h>=1: " if k[0] else "h0: ") + k[1] for k, _ in items], fontsize=7)
    ax2.invert_yaxis(); ax2.set_xlabel("non-executable chunks"); ax2.set_title("(b) teacher failure cause of negative labels", loc="left", fontsize=9)
    by = collections.defaultdict(dict)
    for e in L:
        by[(e["root_id"], e["template"])][(json.dumps(e["prefix"]), json.dumps(e["chunk"]))] = e
    ex = []
    neg = sorted([e for e in L if e["h"] == 0 and e["m"] == 1 and e["label"] == 0], key=lambda e: -e["f0_px"])
    if neg:
        ex.append((neg[0], "blocked first grasp"))
    for e in L:                                                     # same action before (T1) / after (T2) a relocation, discordant
        if e["template"] == "T2" and e["h"] == 1:
            t1 = [x for x in L if x["root_id"] == e["root_id"] and x["template"] == "T1" and x["chunk"] == e["chunk"]]
            if t1 and t1[0]["label"] != e["label"]:
                ex += [(t1[0], "same action at S0"), (e, "after one relocation")]; break
    for e in L:                                                     # matched permutation pair, discordant
        if e["template"] == "T5":
            t4 = [x for x in L if x["root_id"] == e["root_id"] and x["template"] == "T4"]
            if t4 and t4[0]["label"] != e["label"]:
                ex += [(t4[0], "set, order A"), (e, "same set, order B")]; break
    for k, (e, t) in enumerate(ex[:5]):
        a = fig.add_subplot(gs[1, k])
        draw_scene(a, rows[e["root_id"]], e["base"] + e["prefix"], e["chunk"], f"{t}: h={e['h']}, N={e['N']}", e["label"], e["f0_px"])
    fig.text(0.01, 0.01, "Scenes: top-down footprints at true scale from public inputs (red = target, green = already moved, blue = queried mover, dashed = goal cell; 'base' marks the robot-base side); X labels are exact teacher outcomes (chunk + connector to q_ref).", fontsize=7, color=MUTED)
    fig.savefig(FIG / "R3_1_data_3d.png", dpi=160); print(FIG / "R3_1_data_3d.png")


if __name__ == "__main__":
    {"r30": lambda: r30(sys.argv[2]), "r31": lambda: r31(sys.argv[2], sys.argv[3])}[sys.argv[1]]()
