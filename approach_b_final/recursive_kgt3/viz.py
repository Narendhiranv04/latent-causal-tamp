#!/usr/bin/env python3
"""Visual artifacts for recursive_kgt3.
  mock   P2: hidden dependency DAG of the synthetic chain, the recursive insertions REC made, and the composed order vs FLAT's plan
  dev    P3 (post-seal only): per DEV scene, the committed plans of REC/REC2/FLAT on the 8x8 grid with relaxation labels (U movers)
    python viz.py mock P2_TRACES.json OUT.png
    python viz.py dev EVAL_DIR OUT_DIR"""
import json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

INK, MUTED, BLUE, RED, GREEN, ORANGE, GREY = "#222222", "#7a7975", "#2a78d6", "#b4441c", "#1baf7a", "#e07b00", "#9a9a96"


def mock(trace_f, out):
    sys.path.insert(0, str(Path(__file__).resolve().parent / "tests"))
    from test_p1_p2 import CHAINS
    T = json.loads(Path(trace_f).read_text())
    fig, axs = plt.subplots(2, 2, figsize=(14, 8.5))
    for row, name in enumerate(("K6", "K12")):
        BLK, GB = CHAINS[name]
        rec, flat = T[f"{name}_REC"], T[f"{name}_FLAT"]
        ax = axs[row, 0]
        level = {0: 0}
        frontier = [0]
        while frontier:
            nxt = []
            for x in frontier:
                for b in BLK.get(x, []) + (GB if x == 0 else []):
                    if b not in level:
                        level[b] = level[x] + 1; nxt.append(b)
            frontier = nxt
        bylev = {}
        for o, l in level.items():
            bylev.setdefault(l, []).append(o)
        pos = {o: (l, i - (len(bylev[l]) - 1) / 2) for l, os in bylev.items() for i, o in enumerate(sorted(os))}
        for x, bs in list(BLK.items()) + [(0, GB)]:
            for b in bs:
                ax.annotate("", pos[x], pos[b], arrowprops=dict(arrowstyle="->", color=GREY, lw=1.2, shrinkA=12, shrinkB=12))
        for o, (x, y) in pos.items():
            ax.add_patch(plt.Circle((x, y), 0.22, color=RED if o == 0 else (ORANGE if o in GB else BLUE)))
            ax.text(x, y, "T" if o == 0 else f"o{o}", ha="center", va="center", color="white", fontsize=8, fontweight="bold")
        ax.set_xlim(-0.5, max(level.values()) + 0.5); ax.set_ylim(-3, 3); ax.axis("off")
        ax.set_title(f"{name} hidden dependency structure (arrow: must move before)\nred = target, orange = goal blocker, blue = pick blocker", fontsize=9, loc="left")
        ax = axs[row, 1]
        seq = [o for o, _ in rec["res"]["seq"]]
        fseq = [o for o, _ in flat["res"]["seq"]]
        ins = rec["log"]["insert"]
        enab = {}
        for e in ins:
            for o, _ in e["enabling"]:
                enab.setdefault(o, e["before"][0])
        for i, o in enumerate(seq):
            ax.add_patch(plt.Rectangle((i, 1.1), 0.9, 0.8, color=BLUE if o in enab else GREEN))
            ax.text(i + 0.45, 1.5, f"o{o}", ha="center", va="center", color="white", fontsize=8, fontweight="bold")
            if o in enab and enab[o] in seq:
                j = seq.index(enab[o])
                ax.annotate("", (j + 0.45, 1.95), (i + 0.45, 1.95), arrowprops=dict(arrowstyle="->", color=MUTED, lw=0.8, connectionstyle="arc3,rad=-0.35"))
        for i, o in enumerate(fseq):
            ax.add_patch(plt.Rectangle((i, -0.4), 0.9, 0.8, color=GREY))
            ax.text(i + 0.45, 0.0, f"o{o}", ha="center", va="center", color="white", fontsize=8, fontweight="bold")
        r, f = rec["res"], flat["res"]
        ax.text(0, 2.75, f"REC: {len(seq)} moves, valid dependency order, local calls {r['budget']['local']}, temporary-target probes {r['budget']['ytask']}, "
                f"{len(ins)} insertions", fontsize=8.5, color=INK)
        ax.text(0, 0.65, f"FLAT (same loop, no temporary targets): {len(fseq)} moves, misses every nested enabler -> invalid", fontsize=8.5, color=INK)
        ax.set_xlim(-0.2, 12.5); ax.set_ylim(-0.8, 3.1); ax.axis("off")
        ax.set_title(f"{name}: composed plan (green = direct target action, blue = recursively inserted enabler; arc = enables)", fontsize=9, loc="left")
    fig.suptitle("P2 mock-only search traces (symbolic world, perfect mock signals; NOT model or physics evidence)", fontsize=11, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(out, dpi=140); plt.close(fig)
    print("wrote", out)


def dev(eval_dir, out_dir):
    E = Path(eval_dir); O = Path(out_dir); O.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(l) for l in open(E / "per_scene.jsonl")]
    arms = [a for a in ("REC", "REC2", "FLAT", "RAND") if any(a in r["arms"] for r in rows)]
    for r in rows:
        fig, axs = plt.subplots(1, len(arms), figsize=(4.2 * len(arms), 5.0))
        for ax, a in zip(axs, arms):
            x = r["arms"].get(a)
            cells, T0, G0 = r["cells0"], r["T0"], r["G0"]
            ax.set_xlim(-0.6, 7.6); ax.set_ylim(-0.6, 7.6); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
            for k in range(9):
                ax.plot([k - 0.5] * 2, [-0.5, 7.5], color="#e6e6e6", lw=0.6); ax.plot([-0.5, 7.5], [k - 0.5] * 2, color="#e6e6e6", lw=0.6)
            ax.add_patch(plt.Rectangle((G0 % 8 - 0.45, G0 // 8 - 0.45), 0.9, 0.9, fill=False, ec=GREEN, lw=2, ls="--"))
            moved = {o: i for i, (o, _) in enumerate(x["seq"])} if x else {}
            for i, c in enumerate(cells):
                col = RED if i == T0 else (ORANGE if i in r["U"] else GREY)
                ax.add_patch(plt.Circle((c % 8, c // 8), 0.36, color=col, ec=BLUE if i in moved else "white", lw=2.2 if i in moved else 0.5))
            if x:
                for i, (o, d) in enumerate(x["seq"]):
                    c = cells[o]
                    ax.annotate("", (d % 8, d // 8), (c % 8, c // 8), arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.0, shrinkA=6, shrinkB=4))
                    ax.text(d % 8, d // 8, str(i + 1), ha="center", va="center", fontsize=6.5, color=BLUE, bbox=dict(boxstyle="circle,pad=0.1", fc="white", ec=BLUE, lw=0.5))
                ax.set_title(f"{a}: {x['outcome']}  |r|={len(x['seq'])}  K={r['K']}\n{x['failure']}  hY={x['hY']:.3f}", fontsize=8)
            else:
                ax.set_title(f"{a}: no prediction", fontsize=8)
        fig.text(0.01, 0.01, "red = target, dashed green = goal, orange = mover in some minimal goal set (relaxation label, post-seal), blue ring/arrows = committed plan",
                 fontsize=7, color=MUTED)
        fig.suptitle(f"{r['root_id']}  (certified K={r['K']}, {r['n_objects']} objects)", fontsize=9, x=0.01, ha="left")
        fig.tight_layout(rect=(0, 0.03, 1, 0.93)); fig.savefig(O / f"{r['root_id']}.png", dpi=120); plt.close(fig)
    print("wrote", len(rows), "scene figures to", O)


def summary(eval_dir, out):
    import numpy as np
    S = json.loads((Path(eval_dir) / "DEV_SUMMARY.json").read_text())
    P = [json.loads(l) for l in open(Path(eval_dir) / "per_scene.jsonl")]
    arms = ["B0", "FLAT", "RAND", "REC", "REC2"]
    COL = {"B0": GREY, "FLAT": ORANGE, "RAND": MUTED, "REC": BLUE, "REC2": GREEN}
    fig, axs = plt.subplots(1, 3, figsize=(17, 5))
    ax = axs[0]
    cats = ["SUCCESS", "INGREDIENT", "COMPOSITION", "EXECUTION", "FINAL_Y", "ABSTAIN", "NOOP"]
    ccol = {"SUCCESS": GREEN, "INGREDIENT": RED, "COMPOSITION": ORANGE, "EXECUTION": BLUE, "FINAL_Y": "#7b5ea7", "ABSTAIN": GREY, "NOOP": "#cccccc"}
    for i, a in enumerate(arms):
        left = 0
        for c in cats:
            n = sum(1 for r in P if r["arms"][a]["failure"].startswith(c))
            if n:
                ax.barh(i, n, left=left, color=ccol[c], edgecolor="white", height=0.6)
                ax.text(left + n / 2, i, str(n), ha="center", va="center", color="white", fontsize=8)
                left += n
    ax.set_yticks(range(len(arms))); ax.set_yticklabels([f"{a}  ({S['arms'][a]['success']}/25)" for a in arms])
    ax.set_xlabel("DEV scenes (25)"); ax.set_title("Physical outcome of the committed plan (teacher_long)\nfailure class: first applicable in the pre-registered order", fontsize=9, loc="left")
    for c in cats:
        ax.bar(0, 0, color=ccol[c], label=c)
    ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=4, frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax = axs[1]
    rng = np.random.default_rng(0)
    for i, a in enumerate(arms):
        xs = [r["K"] + (i - 2) * 0.13 for r in P]; ys = [r["arms"][a]["len"] + rng.uniform(-0.12, 0.12) for r in P]
        ax.scatter(xs, ys, s=16, color=COL[a], alpha=0.8, label=a, lw=0)
    ax.plot([3, 13], [3, 13], color=INK, lw=0.8, ls="--"); ax.text(10.2, 11.2, "|r| = certified K", fontsize=8)
    ax.set_xlabel("certified minimum K"); ax.set_ylabel("committed plan length |r|"); ax.set_xticks([4, 5, 6, 9, 12]); ax.set_ylim(-0.5, 13)
    ax.set_title("Committed plans are shorter than the minimum K\n(below the dashed line = guaranteed failure)", fontsize=9, loc="left")
    ax.legend(fontsize=7, frameon=False, loc="upper left")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax = axs[2]
    items = [("D1 original task: useful-mover rank (U)", S["D1_auroc_U"]), ("D1 original task: witness-mover rank (W)", S["D1_auroc_W"]),
             ("D2 final h_Y: witness vs random sets", S["D2_hY_witness_vs_random_auroc"]), ("D3 temp-target ŷ at S0 vs static feasibility", S["D3i_ytask_S0_auroc"]),
             ("D3 temp-target ŷ, REC-logged probes", {"mean": S["D3ii_ytask_logged_auroc"]["REC"]["auroc"], "ci95": None}),
             ("D4 temp-task enabling-mover rank (S0)", S["D4_tt_blocker_ranking_auroc_S0"])]
    for i, (lab, v) in enumerate(items):
        m, ci = v["mean"], v.get("ci95")
        col = GREEN if ci and ci[0] > 0.5 else (RED if ci else BLUE)
        if ci:
            ax.plot(ci, [i, i], color=col, lw=2)
        ax.plot(m, i, "o", color=col, ms=7)
        ax.text(1.0, i, f"{m:.2f}" + (f" [{ci[0]:.2f}, {ci[1]:.2f}]" if ci else ""), va="center", fontsize=8)
    ax.axvline(0.5, color=MUTED, ls=":"); ax.set_xlim(0.3, 1.25); ax.set_yticks(range(len(items))); ax.set_yticklabels([l for l, _ in items], fontsize=8)
    ax.invert_yaxis(); ax.set_xlabel("AUROC (0.5 = no information); bootstrap 95% CI over scenes")
    ax.set_title(f"Where the frozen models carry information\nD5: inserted enablers that are true blockers {S['D5_insertion_precision_S0']['true']}/{S['D5_insertion_precision_S0']['all']}", fontsize=9, loc="left")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.suptitle("P3 DEV (25 engineering scenes, K4-K12): recursive vs flat vs random vs frozen K<=3; predictions sealed before labels", fontsize=10.5, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(out, dpi=140); plt.close(fig)
    print("wrote", out)


if __name__ == "__main__":
    {"mock": lambda: mock(sys.argv[2], sys.argv[3]), "dev": lambda: dev(sys.argv[2], sys.argv[3]),
     "summary": lambda: summary(sys.argv[2], sys.argv[3])}[sys.argv[1]]()
