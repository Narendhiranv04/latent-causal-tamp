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
        fig, axs = plt.subplots(1, len(arms), figsize=(4.2 * len(arms), 4.6))
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
        fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(O / f"{r['root_id']}.png", dpi=120); plt.close(fig)
    print("wrote", len(rows), "scene figures to", O)


if __name__ == "__main__":
    {"mock": lambda: mock(sys.argv[2], sys.argv[3]), "dev": lambda: dev(sys.argv[2], sys.argv[3])}[sys.argv[1]]()
