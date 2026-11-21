#!/usr/bin/env python3
"""P4 visual traces (post-evaluation only; ground truth is drawn only here, never used by a planner).
  scenes   per DEV scene: (a) committed R2 vs F plans on the grid with the certified witness (dashed green); (b) candidate-pool energy vs length,
           statically complete candidates marked, committed plan starred; (c) R2 recursive-insertion dependency graph (enabler -> dependent,
           by depth); (d) budget: local calls per round and split original-task vs temporary-target calls
  summary  across arms: success, pool-complete scenes, object-set / order correctness, len >= K, effort
    python p4_viz.py scenes P4_DIR EVAL_DIR DEV_PUBLIC DEV_PRIVATE TABLES OUT_DIR
    python p4_viz.py summary EVAL_DIR OUT.png"""
import json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
INK, MUTED, BLUE, RED, GREEN, ORANGE, GREY, PURPLE = "#222222", "#7a7975", "#2a78d6", "#b4441c", "#1baf7a", "#e07b00", "#9a9a96", "#7b5ea7"


def grid(ax, cells, T0, G0, plans, witness):
    ax.set_xlim(-0.6, 7.6); ax.set_ylim(-0.6, 7.6); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    for k in range(9):
        ax.plot([k - 0.5] * 2, [-0.5, 7.5], color="#eeeeee", lw=0.5); ax.plot([-0.5, 7.5], [k - 0.5] * 2, color="#eeeeee", lw=0.5)
    ax.add_patch(plt.Rectangle((G0 % 8 - 0.45, G0 // 8 - 0.45), 0.9, 0.9, fill=False, ec=GREEN, lw=2))
    wobj = {o for o, _ in witness}
    for i, c in enumerate(cells):
        ax.add_patch(plt.Circle((c % 8, c // 8), 0.34, color=RED if i == T0 else (ORANGE if i in wobj else GREY)))
    for o, d in witness:
        c = cells[o]
        ax.annotate("", (d % 8, d // 8), (c % 8, c // 8), arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.0, ls="--", shrinkA=5, shrinkB=4))
    for (seq, col, off) in plans:
        for j, (o, d) in enumerate(seq):
            c = cells[o]
            ax.annotate("", (d % 8 + off, d // 8 + off), (c % 8 + off, c // 8 + off), arrowprops=dict(arrowstyle="->", color=col, lw=1.1, shrinkA=5, shrinkB=4))
            ax.text(d % 8 + off, d // 8 + off, str(j + 1), fontsize=5.5, color=col, ha="center", va="center", bbox=dict(boxstyle="circle,pad=0.08", fc="white", ec=col, lw=0.4))


def scenes(p4, ev, dev_public, priv, tables, out):
    from dev_eval import Static, jl
    ST = Static(tables)
    pub = {r["root_id"]: r for r in jl(dev_public)}
    pv = {r["root_id"]: r for r in jl(Path(priv) / "dev_private.jsonl")}
    per = {r["root_id"]: r for r in jl(Path(ev) / "p4_per_scene.jsonl")}
    O = Path(out); O.mkdir(parents=True, exist_ok=True)
    for rid, r in per.items():
        inp = pub[rid]["inputs"]; c0 = [int(c) for c in inp["cells0"]]; T0, G0 = int(inp["tid"]), int(inp["goal_cell"])
        W = [(inp["ids"].index(o), int(d)) for o, d in pv[rid]["witness"]]
        fig, axs = plt.subplots(1, 4, figsize=(20, 4.8))
        a2, af = r["arms"].get("R2"), r["arms"].get("F")
        grid(axs[0], c0, T0, G0, [(a2["seq"] if a2 else [], BLUE, -0.12), (af["seq"] if af else [], PURPLE, 0.12)], W)
        axs[0].set_title(f"{rid}  K={r['K']}  objects={r['n_objects']}\nR2 (blue) {'SUCCESS' if a2 and a2['success'] else 'FAIL'} |r|={a2['len'] if a2 else '-'}   "
                         f"F (purple) {'SUCCESS' if af and af['success'] else 'FAIL'} |r|={af['len'] if af else '-'}   witness (green dashed)", fontsize=8, loc="left")
        ax = axs[1]
        for arm, col, mk in (("F", PURPLE, "s"), ("R2", BLUE, "o")):
            f = Path(p4) / arm / "traces" / f"{rid}.json"
            if not f.exists():
                continue
            t = json.loads(f.read_text())
            for c in t["cands"]:
                s = [tuple(x) for x in c["seq"]]
                comp = ST.endpoint_y(c0, T0, G0, s) and ST.order_valid(c0, T0, G0, s)
                ax.scatter(len(s) + (0.15 if arm == "R2" else -0.15), c["C"], s=22 if comp else 8, marker=mk, color=GREEN if comp else col, alpha=0.9 if comp else 0.35, lw=0)
            ch = t["res"]["seq"]
            if ch and t["res"].get("energy"):
                ax.scatter(len(ch) + (0.15 if arm == "R2" else -0.15), t["res"]["energy"]["C"], s=120, marker="*", color=col, edgecolor=INK, lw=0.6)
        ax.axvline(r["K"], color=MUTED, ls=":"); ax.set_xlabel("candidate length (dotted = certified K, post hoc)"); ax.set_ylabel("energy C (lower = preferred)")
        ax.set_title("candidate pools: R2 (o) vs F (s); green = statically complete; star = committed", fontsize=8, loc="left")
        ax = axs[2]
        f2 = Path(p4) / "R2" / "traces" / f"{rid}.json"
        if f2.exists():
            t = json.loads(f2.read_text())
            edges, nodes = {}, {}
            for e in t["log"]["insert"]:
                dep = e["before"][0]
                for o, _ in e["enabling"]:
                    edges[(o, dep)] = min(edges.get((o, dep), 9), e.get("depth", 0))
                    nodes[o] = min(nodes.get(o, 9), e.get("depth", 0) + 1); nodes.setdefault(dep, e.get("depth", 0))
            levels = {}
            for n, l in nodes.items():
                levels.setdefault(l, []).append(n)
            pos = {n: (l, i - (len(v) - 1) / 2) for l, v in levels.items() for i, n in enumerate(sorted(v))}
            wobj = {o for o, _ in W}
            for (u, v), l in edges.items():
                ax.annotate("", pos[v], pos[u], arrowprops=dict(arrowstyle="->", color=GREY, lw=0.8, shrinkA=8, shrinkB=8))
            for n, (x, y) in pos.items():
                ax.scatter(x, y, s=170, color=ORANGE if n in wobj else GREY, edgecolor=BLUE if any(n == o for o, _ in (a2["seq"] if a2 else [])) else "white", lw=1.6, zorder=3)
                ax.text(x, y, str(n), ha="center", va="center", fontsize=6, color="white", zorder=4)
            ax.set_title(f"R2 recursive insertions: enabler -> dependent ({len(t['log']['insert'])} events)\norange = witness object, blue ring = in committed plan", fontsize=8, loc="left")
        ax.axis("off")
        ax = axs[3]
        for arm, col in (("R2", BLUE), ("F", PURPLE), ("N", GREY), ("R3", GREEN)):
            f = Path(p4) / arm / "traces" / f"{rid}.json"
            if f.exists():
                t = json.loads(f.read_text())
                ax.plot([0] + [x["round"] for x in t["log"]["rounds"]], [0] + [x.get("local_used", 0) for x in t["log"]["rounds"]], "-o", ms=3, color=col, label=arm)
        if f2.exists():
            t = json.loads(f2.read_text())
            n0 = sum(1 for L in t["log"]["local"] if L["task"] == "T0"); n1 = sum(1 for L in t["log"]["local"] if L["task"] != "T0")
            ax.text(0.02, 0.93, f"R2 local calls: original task {n0}, temporary targets {n1}", transform=ax.transAxes, fontsize=7.5)
        ax.set_xlabel("round"); ax.set_ylabel("cumulative local-generator calls"); ax.set_ylim(0, 155); ax.axhline(150, color=MUTED, ls=":")
        ax.legend(fontsize=7, frameon=False, loc="lower right"); ax.set_title("budget allocation over rounds (cap 150)", fontsize=8, loc="left")
        for s_ in ("top", "right"):
            axs[1].spines[s_].set_visible(False); axs[3].spines[s_].set_visible(False)
        fig.tight_layout(); fig.savefig(O / f"{rid}.png", dpi=110); plt.close(fig)
    print("wrote", len(per), "scene traces to", O)


def summary(ev, out):
    S = json.loads((Path(ev) / "P4_SUMMARY.json").read_text())
    arms = [a for a in ("R0_REC", "R0_REC2", "R0_FLAT", "R1", "R2", "R3", "F", "N") if a in S["arms"]]
    keys = [("success", "physical success"), ("scenes_pool_success", "pool holds a verified success"), ("scenes_pool_complete", "pool holds static-complete plan"),
            ("object_set_correct", "committed object set correct"), ("order_valid", "committed order valid"), ("len_ge_K", "committed |r| >= K")]
    fig, axs = plt.subplots(1, 2, figsize=(16, 5))
    ax = axs[0]
    w = 0.13
    cols = [GREEN, "#0f7a55", BLUE, ORANGE, PURPLE, GREY]
    for j, (k, lab) in enumerate(keys):
        ax.bar([i + (j - 2.5) * w for i in range(len(arms))], [S["arms"][a][k] for a in arms], width=w, color=cols[j], label=lab)
    ax.set_xticks(range(len(arms))); ax.set_xticklabels(arms); ax.set_ylabel("DEV scenes (of 25)"); ax.set_ylim(0, 26)
    ax.legend(fontsize=7.5, frameon=False, ncol=2, loc="upper left"); ax.set_title("P4 DEV (exploratory, 25 exposed engineering scenes)", fontsize=9, loc="left")
    ax = axs[1]
    for a in arms:
        v = S["arms"][a]
        ax.scatter(v["mean_local"], v["success"], s=60, label=a)
        ax.annotate(a, (v["mean_local"], v["success"]), fontsize=8, xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("mean local-generator calls per scene (cap 150)"); ax.set_ylabel("physical successes"); ax.set_title("success vs search expenditure", fontsize=9, loc="left")
    for s_ in ("top", "right"):
        axs[0].spines[s_].set_visible(False); axs[1].spines[s_].set_visible(False)
    fig.tight_layout(); fig.savefig(out, dpi=140); plt.close(fig)
    print("wrote", out)


if __name__ == "__main__":
    {"scenes": lambda: scenes(*sys.argv[2:8]), "summary": lambda: summary(sys.argv[2], sys.argv[3])}[sys.argv[1]]()
