#!/usr/bin/env python3
"""Figures (reports/figures/).  Every scene panel is a REAL snapshot / cohort root drawn from its public inputs: 2D = the 8x8 planar lattice,
3D = a labelled TOP-DOWN schematic of the 6x6 shelf cells (not a physics render).  Arrows = relocations, numbered in execution order.

    python viz.py p0                      corpus counts (reports/P0_DATA.json)
    python viz.py p1 [CKPT_2D CKPT_3D]    verified TRAIN repairs vs posterior reconstruction / prior samples of a checkpoint
    python viz.py p2                      learning curves of every fit in $CR_RUNS/models"""
from __future__ import annotations

import json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import data as D  # noqa: E402

FIG = D.HERE / "reports" / "figures"
COL = {"target": "#d62728", "fixed": "#7f7f7f", "movable": "#1f77b4", "goal": "#2ca02c", "move": "#ff7f0e"}


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / name, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(FIG / name)


def draw_scene(ax, dom, row, seq=None, title=""):
    """Grid, objects at S0 cells (index labels), goal cell, and the ordered relocations of `seq` ([[obj, cell], ...])."""
    R, C = D.GRID[dom]
    inp = row["inputs"]
    legal = set(int(c) for c in inp["legal_cells"])
    for j in range(R * C):
        r, c = divmod(j, C)
        ax.add_patch(plt.Rectangle((c, r), 1, 1, fc="white" if j in legal else "#dddddd", ec="#bbbbbb", lw=0.5))
    g = int(inp["goal_cell"])
    ax.add_patch(plt.Rectangle((g % C, g // C), 1, 1, fc="none", ec=COL["goal"], lw=2.2))
    ax.text(g % C + 0.5, g // C + 0.85, "goal", ha="center", va="center", fontsize=6, color=COL["goal"])
    fixed = [bool(a[3]) for a in inp["attrs"]] if dom == "2d" else [False] * len(inp["ids"])
    for i, cell in enumerate(inp["cells0"]):
        r, c = divmod(int(cell), C)
        k = "target" if i == inp["tid"] else "fixed" if fixed[i] else "movable"
        ax.add_patch(plt.Circle((c + 0.5, r + 0.5), 0.33, fc=COL[k], ec="k", lw=0.5, alpha=0.85))
        ax.text(c + 0.5, r + 0.5, str(i), ha="center", va="center", fontsize=6, color="white")
    for t, (o, d) in enumerate(seq or []):
        r0, c0 = divmod(int(inp["cells0"][o]), C)
        r1, c1 = divmod(int(d), C)
        ax.annotate("", xy=(c1 + 0.5, r1 + 0.5), xytext=(c0 + 0.5, r0 + 0.5), arrowprops=dict(arrowstyle="->", color=COL["move"], lw=1.6))
        ax.add_patch(plt.Circle((c1 + 0.5, r1 + 0.5), 0.33, fc="none", ec=COL["move"], lw=1.4, ls="--"))
        ax.text(c1 + 0.82, r1 + 0.18, str(t + 1), fontsize=7, color=COL["move"], weight="bold")
    ax.set_xlim(0, C); ax.set_ylim(R, 0); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(title, fontsize=7)


def p0():
    rep = json.loads((D.HERE / "reports/P0_DATA.json").read_text())
    fig, axs = plt.subplots(2, 3, figsize=(13, 6.5))
    for a, dom in enumerate(("2d", "3d")):
        tr = rep[dom]["train"]["by_K"]
        Ks = [k for k in ("0", "1", "2", "3", "NONE") if k in tr]
        x = np.arange(len(Ks))
        for j, sz in enumerate((1, 2, 3)):
            axs[a, 0].bar(x + (j - 1) * 0.27, [tr[k].get(f"assign_size{sz}", 0) for k in Ks], 0.27, label=f"{sz} relocation(s)")
        axs[a, 0].set_xticks(x, [f"K{k}" if k != "NONE" else k for k in Ks]); axs[a, 0].set_title(f"{dom.upper()} TRAIN verified assignments by legacy K")
        axs[a, 0].legend(fontsize=7)
        hist = {}
        for k in Ks:
            for key, v in tr[k].items():
                if key.startswith("assign_size3_orders"):
                    hist[int(key.rsplit("orders", 1)[1])] = hist.get(int(key.rsplit("orders", 1)[1]), 0) + v
        axs[a, 1].bar(sorted(hist), [hist[k] for k in sorted(hist)], color="#9467bd")
        axs[a, 1].set_title(f"{dom.upper()} TRAIN 3-object assignments: verified orders (of 6)"); axs[a, 1].set_xlabel("verified X=1 orders")
        labs = {s: rep[dom][s]["labels"] for s in ("train", "val")}
        cls = ["NOOP", "REPAIR", "ABSTAIN", "MASKED"]
        for j, s in enumerate(("train", "val")):
            axs[a, 2].bar(np.arange(4) + (j - 0.5) * 0.4, [labs[s].get(c, 0) for c in cls], 0.4, label=s)
        axs[a, 2].set_xticks(range(4), cls); axs[a, 2].set_title(f"{dom.upper()} root decision labels"); axs[a, 2].legend(fontsize=7)
    for ax in axs.flat:
        ax.title.set_fontsize(8)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.suptitle("P0: complete-repair supervision (verified X=1, Y=1 orders only; ABSTAIN = benchmark-relative legacy NONE)", fontsize=10)
    save(fig, "p0_corpus.png")


def p1(ckpts=None, n_roots=3, n_samples=3):
    import torch
    import train as TR
    for dom in ("2d", "3d"):
        rr, triples, _ = D.supervision(dom, D.TRAIN_SNAP, "train")
        ck = (ckpts or {}).get(dom) or D.RUNS / "overfit" / dom / "model.pt"
        idx = sorted({i for i, _, _ in triples})
        if ckpts:                                                     # trained model: hash-chosen TRAIN roots; overfit: its own 16-root fixture
            idx = sorted(idx, key=lambda i: D.stratum_hash("CRVIZ", rr[i]["root_id"]))
        else:
            idx = idx[:16]
        pick = [i for i in idx if len(json.loads(D.verified_orders(rr[i])[next(iter(D.verified_orders(rr[i])))][0])) >= 2][:n_roots]
        m, meta = TR.load(ck, "cpu")
        fig, axs = plt.subplots(n_roots, 1 + n_samples, figsize=(3.0 * (1 + n_samples), 3.1 * n_roots))
        for a, i in enumerate(pick):
            r = rr[i]
            vo = D.verified_orders(r)
            s0 = json.loads(vo[sorted(vo)[0]][0])
            draw_scene(axs[a, 0], dom, r, s0, f"{r['root_id'][:22]}\nverified X=1,Y=1 order ({len(vo)} assignments)")
            b1 = {k: torch.as_tensor(v[None]) for k, v in D.encode(dom, r).items()}
            o, d, n = m.sample(b1, 64, torch.Generator().manual_seed(0))
            known = {x for v in vo.values() for x in v}
            nhit = sum(json.dumps([[int(o[j, t]), int(d[j, t])] for t in range(int(n[j]))]) in known for j in range(64))
            axs[a, 0].set_title(axs[a, 0].get_title() + f"\n{nhit}/64 prior samples = a verified order", fontsize=7)
            for j in range(n_samples):
                s = [[int(o[j, t]), int(d[j, t])] for t in range(int(n[j]))]
                hit = json.dumps(s) in {x for v in vo.values() for x in v}
                draw_scene(axs[a, 1 + j], dom, r, s, f"prior sample {j + 1} (len {len(s)})\n{'= a verified order' if hit else 'not a known witness'}")
        kind = "TOP-DOWN SCHEMATIC of shelf cells (not a render)" if dom == "3d" else "planar 8x8 lattice"
        fig.suptitle(f"P1 {dom.upper()} [{kind}]: checkpoint {Path(ck).parent.parent.name}/{Path(ck).parent.name} (step {meta.get('step')}) - static-legal samples; "
                     "red target, blue movable, grey fixed, green goal", fontsize=9)
        save(fig, f"p1_{dom}_samples_{Path(ck).parent.parent.name}_{Path(ck).parent.name}.png")


def p2():
    runs = sorted((D.RUNS / "models").glob("*/*/curve.json"))
    if not runs:
        print("no fits"); return
    fig, axs = plt.subplots(2, 3, figsize=(14, 7))
    for f in runs:
        c = json.loads(f.read_text())
        a = 0 if c["dom"] == "2d" else 1
        st = [x["step"] for x in c["curve"]]
        lab, col = f"{c['tag']} s{c['seed']}", f"C{c['seed']}"
        axs[a, 0].plot(st, [x["val_neg_elbo"] for x in c["curve"]], label=lab, color=col)
        axs[a, 0].plot(st, [x["train_nll"] + x["train_kl"] for x in c["curve"]], ls=":", alpha=0.6, color=col)
        axs[a, 1].plot(st, [x["val_kl"] for x in c["curve"]], label=lab, color=col)
        axs[a, 2].plot(st, [x["val_dec_ce"] for x in c["curve"]], label=lab, color=col)
        axs[a, 0].axvline(c["best_step"], color=col, lw=0.6)
    for a, dom in enumerate(("2D", "3D")):
        axs[a, 0].set_title(f"{dom} -ELBO (VAL solid, TRAIN dotted)"); axs[a, 1].set_title(f"{dom} VAL KL"); axs[a, 2].set_title(f"{dom} VAL decision CE")
        for ax in axs[a]:
            ax.set_xlabel("optimizer step"); ax.legend(fontsize=6)
    fig.tight_layout()
    save(fig, "p2_curves.png")



def p2dev():
    fig, axs = plt.subplots(2, 3, figsize=(14, 7))
    for a, dom in enumerate(("2d", "3d")):
        f = D.HERE / "reports" / f"P2_DEV_{dom}.json"
        if not f.exists():
            continue
        r = json.loads(f.read_text())
        ag, bs = r["agg"], r["budgets"]
        for name, ls in (("order", "-"), ("assignment", "--"), ("objset", ":")):
            axs[a, 0].plot(bs, [ag[f"recall_{name}@{b}"]["rate"] for b in bs], ls, marker="o", label=f"CR {name}")
        axs[a, 0].axhline(ag["C0_recall_assignment"]["rate"], color="k", lw=1, label="C0 top-4 exhaustive (order = assignment)")
        axs[a, 0].set_xscale("log", base=2); axs[a, 0].set_xticks(bs, [str(b) for b in bs]); axs[a, 0].set_ylim(0, 1.02)
        axs[a, 0].set_title(f"{dom.upper()} VAL known-witness recall vs raw draws (lower bound)", fontsize=8); axs[a, 0].legend(fontsize=6)
        axs[a, 1].plot(bs, [ag[f"unique@{b}"]["mean"] for b in bs], marker="o", label="unique legal sequences")
        axs[a, 1].plot(bs, [ag[f"dup_rate@{b}"]["mean"] * b for b in bs], marker="s", label="duplicate draws")
        axs[a, 1].axhline(ag["C0_n_scored"]["mean"], color="k", lw=1, label=f"C0 scored (mean {ag['C0_n_scored']['mean']:.0f})")
        axs[a, 1].set_xscale("log", base=2); axs[a, 1].set_yscale("log"); axs[a, 1].set_title(f"{dom.upper()} pool size per root", fontsize=8); axs[a, 1].legend(fontsize=6)
        L = r["pool_length_dist"]
        axs[a, 2].bar([1, 2, 3], [L.get(str(k), 0) / sum(L.values()) for k in (1, 2, 3)])
        axs[a, 2].set_title(f"{dom.upper()} main-pool repair length (off-top-4 action rate {r['off_top4_action_rate']:.2f})", fontsize=8)
    save(fig, "p2_dev_pools.png")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "p0":
        p0()
    elif cmd == "p1":
        p1({"2d": Path(sys.argv[2]), "3d": Path(sys.argv[3])} if len(sys.argv) > 3 else None)
    elif cmd == "p2":
        p2()
    elif cmd == "p2dev":
        p2dev()
