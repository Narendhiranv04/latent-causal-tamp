#!/usr/bin/env python3
"""R2.4 figures (evaluator side).  Scene panels are SCHEMATIC top-down layouts of the ACTUAL public scene (cell centres from the root's
cell_xy; not a render, not a trajectory): numbered arrows = executed order, colour = chunk, 'q' = home return to q_ref at a chunk boundary,
red cross = the first failing relocation reported by the teacher, dashed grey = recursively discovered PREREQ edge (enabler -> parent).
    python figs24.py all OUT_DIR"""
from __future__ import annotations

import json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent), str(HERE.parent / "r2")]
import analyze24 as AN  # noqa: E402
import common as C  # noqa: E402
import jobs24 as JB  # noqa: E402

O = C.FIG3 / "r24"
INK, MUTED, GRID, OK, BAD, UNK = "#1f2328", "#6e7781", "#d0d7de", "#1a7f37", "#cf222e", "#bf8700"
CHUNK = ["#0969da", "#8250df", "#bc4c00", "#1b7c83", "#a40e26"]


def _style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.yaxis.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)


def _zcol(z):
    return OK if z == 1 else (BAD if z == 0 else UNK)


# ------------------------------------------------------------------ R2.4A
def oracle(out):
    A = json.loads((O / "R2_4A_3d.json").read_text())
    arms = ["A-DP", "A-PRE", "direct", "chunkH", "random", "mode_control", "witness_split"]
    lab = ["A-DP\n(new)", "A-PRE\n(new)", "direct p11\n(K45)", "chunk-H\n(K45)", "random\n(K45)", "chunk-H order\ncontinuous", "witness order\nsplit [2,m]"]
    rids = sorted(A["roots"], key=lambda r: (A["roots"][r]["m"], r))
    fig = plt.figure(figsize=(15, 7.4))
    g = fig.add_gridspec(2, 3, width_ratios=[1.5, 1, 1], height_ratios=[1, 1], wspace=0.45, hspace=0.75)
    ax = fig.add_subplot(g[:, 0])
    for i, rid in enumerate(rids):
        for j, a in enumerate(arms):
            z = A["roots"][rid]["arms"][a]["z"]
            ax.add_patch(plt.Rectangle((j, i), 0.92, 0.88, color=_zcol(z)))
            if A["roots"][rid]["arms"][a]["exact_witness_order"]:
                ax.text(j + 0.46, i + 0.47, "w", ha="center", va="center", color="white", fontsize=7, fontweight="bold")
    ax.set_xlim(0, len(arms)); ax.set_ylim(len(rids), 0)
    ax.set_xticks(np.arange(len(arms)) + 0.46); ax.set_xticklabels(lab, fontsize=7)
    ax.set_yticks(np.arange(len(rids)) + 0.45); ax.set_yticklabels([f"K{A['roots'][r]['m']} " + r.replace("3ds66-", "")[-22:] for r in rids], fontsize=6.5)
    ax.set_title("Witness ASSIGNMENT given, order hidden: X=1,Y=1 per root\ngreen verified · red failed · amber not run · w = witness order",
                 fontsize=8.5, loc="left", color=INK)
    for s in ax.spines.values():
        s.set_visible(False)
    ax2 = fig.add_subplot(g[0, 1])
    cnt = [A["counts"][a]["verified"] for a in arms]
    dec = [A["counts"][a]["decided"] for a in arms]
    ax2.bar(range(len(arms)), cnt, color=[CHUNK[0], CHUNK[1]] + [MUTED] * 4 + [INK], width=0.6)
    for i, (c, d) in enumerate(zip(cnt, dec)):
        ax2.text(i, c + 0.3, f"{c}/{d}", ha="center", fontsize=7, color=INK)
    ax2.set_xticks(range(len(arms))); ax2.set_xticklabels([l.split("\n")[0] for l in lab], fontsize=6.5, rotation=35, ha="right")
    ax2.set_ylim(0, 21); ax2.set_ylabel("verified / decided (20 roots)", fontsize=8); _style(ax2)
    ax2.set_title("Order recovery (exposed roots; development only)", fontsize=8.5, loc="left")
    ax3 = fig.add_subplot(g[0, 2])
    rk = [A["roots"][r]["witness_rank"] / A["roots"][r]["n_orders"] for r in rids]
    for j, m in enumerate((4, 5)):
        rr = [r for r in rids if A["roots"][r]["m"] == m]
        ax3.scatter(j + np.linspace(-0.25, 0.25, len(rr)), [A["roots"][r]["witness_rank"] for r in rr], c=[_zcol(A["roots"][r]["arms"]["A-DP"]["z"]) for r in rr], s=22)
        n = 24 if m == 4 else 120
        ax3.plot([j - 0.35, j + 0.35], [n / 2, n / 2], color=MUTED, lw=1, ls="--")
    ax3.set_yscale("log"); ax3.set_xticks([0, 1]); ax3.set_xticklabels(["K4 (24 orders)", "K5 (120 orders)"], fontsize=7.5)
    ax3.set_ylabel("rank of witness order by E", fontsize=8)
    ax3.set_title(f"Witness-order rank (median {A['witness_rank']['median']:.0f})\ndashed = expected rank of a random order", fontsize=8.5, loc="left"); _style(ax3)
    ax4 = fig.add_subplot(g[1, 1:])
    f = A["A-DP_failures"]["by_chunk_h"]
    ks = sorted(f, key=lambda k: (-f[k], k))
    ax4.barh(range(len(ks)), [f[k] for k in ks], color=BAD, height=0.6)
    for i, k_ in enumerate(ks):
        ax4.text(f[k_] + 0.2, i, k_.replace("|", "  "), va="center", fontsize=7, color=INK)
    ax4.set_yticks([]); ax4.invert_yaxis(); ax4.set_xlim(0, max(f.values()) + 5)
    ax4.set_xlabel("A-DP failures", fontsize=8); _style(ax4)
    ax4.set_title("Where A-DP fails (first failing chunk, prefix length h, phase); every failing chunk had model pX >= 0.83 except one (0.26)", fontsize=8.5, loc="left")
    fig.savefig(out / "R2_4A_order_recovery.png", dpi=150, bbox_inches="tight"); plt.close(fig)


# ------------------------------------------------------------------ R2.4B / C
def arms(out):
    fig, axs = plt.subplots(2, 2, figsize=(13, 7.2), gridspec_kw={"hspace": 0.6, "wspace": 0.3})
    for k, dom in enumerate(("3d", "2d")):
        B = json.loads((O / f"R2_4B_{dom}.json").read_text())
        names = ["B0 (R2.3)", "R-FIG3 (R2.3)", "F-FLAT (R2.3)", "R-FIG3-X", "R-FIG3-XP", "R-FIG3-XC", "GA-INIT", "GA-UNION"]
        v = [B["arms"][n]["verified"] for n in names]; d = [B["arms"][n]["decided"] for n in names]
        ax = axs[0, k]
        ax.bar(range(len(names)), v, color=[MUTED] * 3 + [CHUNK[0], CHUNK[1], CHUNK[3], CHUNK[2], CHUNK[4]], width=0.6)
        for i, (a, b) in enumerate(zip(v, d)):
            ax.text(i, a + 0.3, f"{a}/{b}", ha="center", fontsize=7)
        ax.set_xticks(range(len(names))); ax.set_xticklabels(names, rotation=35, ha="right", fontsize=7); ax.set_ylim(0, 21); _style(ax)
        ax.set_title(f"{dom.upper()}: verified X=1,Y=1 / decided (20 exposed development roots)", fontsize=8.5, loc="left")
        ax = axs[1, k]
        arms_ = ["R-FIG3-X", "R-FIG3-XP", "R-FIG3-XC", "GA-INIT", "GA-UNION"]
        F = B["funnel"]
        rows = [("known set in action pool", "known_set_in_pool"), ("known set ranked (top 40)", "known_set_ranked_top40"), ("known set selected", "known_set_selected"),
                ("verified (any plan)", "verified")]
        for j, (lbl, key) in enumerate(rows):
            ax.bar(np.arange(len(arms_)) + (j - 1.5) * 0.2, [F[a].get(key, 0) for a in arms_], width=0.19, color=[CHUNK[0], CHUNK[1], CHUNK[2], OK][j], label=lbl)
        ax.set_xticks(range(len(arms_))); ax.set_xticklabels(arms_, fontsize=7); ax.set_ylim(0, 21); _style(ax)
        known = "generator witness assignment" if dom == "3d" else "any verified K<=3 repair (pool)"
        ax.set_title(f"{dom.upper()}: coverage vs discovery (known = {known})", fontsize=8.5, loc="left")
        ax.legend(fontsize=6.5, frameon=False, ncol=2, loc="upper right")
    fig.savefig(out / "R2_4B_arms.png", dpi=150, bbox_inches="tight"); plt.close(fig)


def local(out):
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.0), gridspec_kw={"wspace": 0.3})
    st = ["h0", "h>=1", "h1-2", "h>=3", "h>=1,g1", "h>=1,g2-3"]
    for k, dom in enumerate(("3d", "2d")):
        L = json.loads((O / f"R2_4_local_{dom}.json").read_text())
        ax = axs[k]
        for i, s in enumerate(st):
            S = L["by_h"][s]["px"]
            if S.get("auroc") is None:
                ax.text(i, 0.12, "n/a", ha="center", fontsize=7, color=MUTED); continue
            ci = S.get("auroc_ci") or [S["auroc"], S["auroc"]]
            ax.errorbar(i, S["auroc"], yerr=[[S["auroc"] - ci[0]], [ci[1] - S["auroc"]]], fmt="o", color=CHUNK[0] if s == "h0" else CHUNK[2], ms=5, capsize=3)
            ax.text(i, 0.04, f"n={S['n']}\n+{S['pos']}\nr={S['mixed_families']}", ha="center", fontsize=6, color=MUTED)
        ax.axhline(0.5, color=GRID, lw=1); ax.axhline(0.75, color=GRID, lw=1, ls="--")
        ax.set_xticks(range(len(st))); ax.set_xticklabels(st, fontsize=7, rotation=20); ax.set_ylim(0.0, 1.02); _style(ax)
        ax.set_title(f"{dom.upper()}: chunk pX AUROC by prefix length h\n(teacher chunk labels; root-cluster CI; r = mixed roots)", fontsize=8, loc="left")
    ax = axs[2]
    for k, dom in enumerate(("3d", "2d")):
        L = json.loads((O / f"R2_4_local_{dom}.json").read_text())
        for j, s in enumerate(("m<=3", "m>=4")):
            for q, (rep, mk) in enumerate((("y_global", "o"), ("y_rebased", "s"))):
                S = L["Y"][s][rep]
                if S.get("auroc") is None:
                    continue
                x = k * 2.5 + j + (q - 0.5) * 0.3
                ci = S.get("auroc_ci") or [S["auroc"]] * 2
                ax.errorbar(x, S["auroc"], yerr=[[S["auroc"] - ci[0]], [ci[1] - S["auroc"]]], fmt=mk, color=[CHUNK[0], CHUNK[2]][q], capsize=2, ms=5,
                            label=("Y_global (original-root edit)" if q == 0 else "Y_rebased (fresh-root no-op)") if k == 0 and j == 0 else None)
                ax.text(x, 0.33, f"{S['n']}", ha="center", fontsize=6, color=MUTED)
    ax.set_xticks([0, 1, 2.5, 3.5]); ax.set_xticklabels(["3D m<=3", "3D m>=4", "2D m<=3", "2D m>=4"], fontsize=7)
    ax.axhline(0.5, color=GRID, lw=1); ax.set_ylim(0.3, 1.02); _style(ax); ax.legend(fontsize=6.5, frameon=False, loc="lower left")
    ax.set_title("Endpoint Y AUROC, identical endpoints\n(numbers = labelled endpoints)", fontsize=8, loc="left")
    fig.savefig(out / "R2_4_local_x_and_y.png", dpi=150, bbox_inches="tight"); plt.close(fig)


# ------------------------------------------------------------------ scene panels
def prereq_edges(tree):
    E = set()

    def walk(n):
        for ch in n.get("children", []):
            if "action" in ch and ch["action"] != "ROOT":
                for rr in ch.get("repairs", []):
                    for g in rr["group"]:
                        E.add((tuple(g), tuple(ch["action"])))
                    walk(rr)
            walk(ch)
    walk(tree)
    return E


def panel(ax, row, seq, part, fail, title, edges=()):
    inp = row["inputs"]; xy = inp["cell_xy"]; ids = inp["ids"]
    P = lambda c: np.array(xy[str(int(c))])  # noqa: E731
    cs = np.array([xy[k] for k in xy])
    ax.scatter(cs[:, 0], cs[:, 1], s=6, color=GRID, zorder=0)
    moved = {int(o) for o, _ in seq}
    for i, c in enumerate(inp["cells0"]):
        p = P(c)
        col = INK if i == inp["tid"] else (CHUNK[0] if i in moved else MUTED)
        ax.scatter(*p, s=90 if i == inp["tid"] else 55, color="white", edgecolor=col, lw=1.6 if i == inp["tid"] else 1.1, zorder=2,
                   marker="s" if row["domain"] == "3d" and inp["attrs"][i][0] > 0.5 else "o")
        ax.text(*(p + [0, 0.0]), "T" if i == inp["tid"] else ids[i][-2:], ha="center", va="center", fontsize=5.5, color=col, zorder=3)
    ax.scatter(*P(inp["goal_cell"]), marker="*", s=140, color=INK, zorder=1); ax.text(*(P(inp["goal_cell"]) + [0, -0.03]), "goal", ha="center", fontsize=6, color=INK)
    b = np.cumsum([0] + list(part))
    chunk_of = {i: j for j in range(len(part)) for i in range(b[j], b[j + 1])}
    fi = fail.get("idx") if fail else None
    for i, (o, d) in enumerate(seq):
        p0, p1 = P(inp["cells0"][int(o)]), P(d)
        col = CHUNK[chunk_of[i] % len(CHUNK)]
        ax.annotate("", xy=p1, xytext=p0, arrowprops=dict(arrowstyle="-|>", color=col, lw=1.4, alpha=0.35 if fi is not None and i > fi else 1.0), zorder=4)
        m = (p0 + p1) / 2
        ax.text(*m, str(i + 1), fontsize=7, color="white", ha="center", va="center", zorder=5, bbox=dict(boxstyle="circle,pad=0.15", fc=col, ec="none"))
        if fi == i:
            ax.scatter(*m, marker="x", s=120, color=BAD, lw=2.2, zorder=6)
    for e, f in edges:
        ka = [i for i, (o, d) in enumerate(seq) if (ids[int(o)], int(d)) == (e[0], int(e[1]))]
        kb = [i for i, (o, d) in enumerate(seq) if (ids[int(o)], int(d)) == (f[0], int(f[1]))]
        if ka and kb:
            pa, pb = P(seq[ka[0]][1]), P(seq[kb[0]][1])
            ax.annotate("", xy=pb, xytext=pa, arrowprops=dict(arrowstyle="->", color=MUTED, lw=1, ls="--", connectionstyle="arc3,rad=0.3"), zorder=3)
    chunks = " | q | ".join(" ".join(str(i + 1) for i in range(b[j], b[j + 1])) for j in range(len(part)))
    ax.set_title(title + f"\nchunks: {chunks}", fontsize=7.5, loc="left", color=INK)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color(GRID)


def _fail_idx(o, part):
    if not o or o.get("x") != 0:
        return None
    k, _, j = (o.get("phase") or "").partition(":")
    if not j.isdigit():
        return None
    return {"idx": int(j) if k == "relocation" else int(j) - 1}


def sequences(out):
    A = json.loads((O / "R2_4A_3d.json").read_text())
    R3 = AN.roster("3d")
    OI3 = AN.outcome_index("3d")
    arch = JB.archive("3d", R3)
    succ = [r for r in sorted(A["roots"]) if A["roots"][r]["arms"]["A-DP"]["z"] == 1][:1]
    fail = [r for r in sorted(A["roots"]) if A["roots"][r]["arms"]["A-DP"]["z"] == 0][:1]
    D3 = {json.loads(l)["root_id"]: json.loads(l) for l in open(O / "deploy_3d.jsonl")}
    B3 = json.loads((O / "R2_4B_3d.json").read_text())["per_root"]
    rx = [r for r in sorted(D3) if B3["R-FIG3-X"][r]["z"] == 1][:1] + [r for r in sorted(D3) if B3["R-FIG3-X"][r]["z"] == 0 and len(D3[r]["R-FIG3-X"]["seq"] or []) >= 4][:1]
    D2 = {json.loads(l)["root_id"]: json.loads(l) for l in open(O / "deploy_2d.jsonl")}
    B2 = json.loads((O / "R2_4B_2d.json").read_text())["per_root"]
    R2 = AN.roster("2d")
    OI2 = AN.outcome_index("2d")
    r2s = [r for r in sorted(D2) if B2["R-FIG3-X"][r]["z"] == 1 and len(D2[r]["R-FIG3-X"]["partition"] or []) >= 2][:1] or [r for r in sorted(D2) if B2["R-FIG3-X"][r]["z"] == 1][:1]
    r2f = [r for r in sorted(D2) if B2["GA-UNION"][r]["z"] == 0][:1]
    fig, axs = plt.subplots(2, 4, figsize=(17, 9.2), gridspec_kw={"wspace": 0.12, "hspace": 0.28})
    k = 0
    for rid in succ + fail:
        a = A["roots"][rid]["arms"]
        for name in ("witness_split", "A-DP"):
            s = a[name]
            o = OI3.get((rid, json.dumps(s["order"]), json.dumps(JB.bounds(s["partition"])))) or JB.lookup("3d", arch, rid, R3[rid]["inputs"]["ids"], s["order"], JB.bounds(s["partition"]))
            lab = {1: "VERIFIED", 0: "FAILED", None: "not run"}[s["z"]]
            panel(axs.flat[k], R3[rid], s["order"], s["partition"], _fail_idx(o, s["partition"]),
                  f"3D R2.4A {name} ({'privileged order' if name == 'witness_split' else 'order hidden, DP'}): {lab}\n{rid[-30:]}")
            k += 1
    for rid in rx:
        p = D3[rid]["R-FIG3-X"]
        o = OI3.get((rid, json.dumps(p["seq"]), json.dumps(JB.bounds(p["partition"]))))
        panel(axs.flat[k], R3[rid], p["seq"], p["partition"], _fail_idx(o, p["partition"]),
              f"3D R2.4B R-FIG3-X: {'VERIFIED' if B3['R-FIG3-X'][rid]['z'] == 1 else 'FAILED'}\n(dashed = PREREQ) {rid[-24:]}", prereq_edges(D3[rid]["_tree"]))
        k += 1
    for rid, arm in [(r, "R-FIG3-X") for r in r2s] + [(r, "GA-UNION") for r in r2f]:
        p = D2[rid][arm]
        o = OI2.get((rid, json.dumps(p["seq"]), json.dumps(JB.bounds(p["partition"]))))
        z = B2[arm][rid]["z"]
        panel(axs.flat[k], R2[rid], p["seq"], p["partition"], _fail_idx(o, p["partition"]),
              f"2D R2.4C {arm}: {'VERIFIED' if z == 1 else ('FAILED' if z == 0 else 'not run')}\n{rid[-30:]}", prereq_edges(D2[rid]["_tree"]) if arm.startswith("R-") else ())
        k += 1
    for ax in axs.flat[k:]:
        ax.axis("off")
    fig.suptitle("SCHEMATIC top-down layouts of the actual scenes (cell centres; not renders). Numbers = executed order; colour = chunk; 'q' = home return; "
                 "red x = first failing relocation (teacher); faded = not reached", fontsize=8.5, color=MUTED, y=0.995)
    fig.savefig(out / "R2_4_sequences.png", dpi=150, bbox_inches="tight"); plt.close(fig)


if __name__ == "__main__":
    out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    for f in (oracle, arms, local, sequences):
        try:
            f(out); print("ok", f.__name__)
        except Exception as e:  # noqa: BLE001
            import traceback; traceback.print_exc(); print("FAIL", f.__name__, e)
