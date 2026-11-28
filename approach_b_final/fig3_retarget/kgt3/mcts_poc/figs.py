#!/usr/bin/env python3
"""GA-MCTS figures (matplotlib, static PNG).  Colors: fixed categorical order (GA blue, GA-MCTS orange, REC aqua, H3 yellow); one y-axis each.
  eval EVAL_DIR OUT_DIR : 1 verified success vs budget (log x; Wilson bands; REC / H3 reference lines; MCTS seeds 1/2 thin)
                          2 selected-plan learned-energy regret vs budget (median + IQR)
                          3 paired wins / losses of GA-MCTS s0 vs GA per budget (Holm p annotated)
                          4 CDF of time to final incumbent (GA vs GA-MCTS s0)
                          5 per-root learned energy GA vs GA-MCTS s0 at 30 s and 180 s (marker = verified success agreement)
  dev GA.jsonl MCTS.jsonl OUT_DIR : energy-only DEV versions of 2, 4, 5 (no physical outcome exists on DEV)"""
from __future__ import annotations

import json, math, statistics, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

C = {"GA": "#257de0", "GA-MCTS": "#f47230", "REC": "#00b894", "H3": "#f2a600", "ink": "#191919", "ink2": "#666666", "grid": "#e6e6e6"}
B = (5, 10, 20, 30, 60, 180)


def style(ax, title, xl, yl):
    ax.set_title(title, loc="left", fontsize=11, color=C["ink"]); ax.set_xlabel(xl, color=C["ink2"]); ax.set_ylabel(yl, color=C["ink2"])
    ax.grid(True, color=C["grid"], lw=0.8); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(C["ink2"])


def jl(p):
    return [json.loads(l) for l in open(p)]


def esel(v):
    return v["E"] if v["decision"] == "REPAIR" and v["E"] is not None else None


def t_final(r):
    tr = [(t, e) for t, e in r["trace"] if e is not None]
    return next(t for t, e in tr if e <= tr[-1][1] + 1e-12) if tr else None


def regret_plot(ax, E, labs, roots):
    best = {}
    for r in roots:
        v = [E[l][r][b] for l in labs if r in E[l] for b in B if E[l][r].get(b) is not None]
        best[r] = min(v) if v else math.nan
    for i, l in enumerate(labs):
        med, lo, hi, xs = [], [], [], []
        for b in B:
            v = [E[l][r][b] - best[r] for r in roots if r in E[l] and E[l][r].get(b) is not None and not math.isnan(best[r])]
            if v:
                xs.append(b); med.append(np.median(v)); lo.append(np.percentile(v, 25)); hi.append(np.percentile(v, 75))
        col = C["GA"] if l == "GA" else C["GA-MCTS"]
        ax.fill_between(xs, lo, hi, color=col, alpha=0.15, lw=0); ax.plot(xs, med, "-o", color=col, lw=2, ms=8, label=l)
    ax.set_xscale("log"); ax.set_xticks(B); ax.set_xticklabels([str(b) for b in B])
    style(ax, "Learned-energy regret of the selected plan", "budget (s, log)", "E - per-root best E (median, IQR)"); ax.legend(frameon=False)


def cdf_plot(ax, T, labs):
    for l in labs:
        t = sorted(x for x in (t_final(r) for r in T[l].values()) if x is not None)
        if t:
            ax.step(t, np.arange(1, len(t) + 1) / len(t), where="post", lw=2, color=C["GA"] if l == "GA" else C["GA-MCTS"], label=l)
    ax.set_xscale("log"); style(ax, "Time to final incumbent", "elapsed (s, log)", "fraction of roots"); ax.legend(frameon=False)


def scatter_plot(ax, E, a, b, roots, budget, mark=None):
    xs = [(E[a][r].get(budget), E[b][r].get(budget), r) for r in roots if r in E[a] and r in E[b]]
    xs = [t for t in xs if t[0] is not None and t[1] is not None]
    if not xs:
        return
    mk = mark or (lambda r: ("o", C["ink2"]))
    for x, y, r in xs:
        m, c = mk(r); ax.scatter(x, y, s=64, marker=m, color=c, edgecolor="white", lw=1.5, zorder=3)
    lo = min(min(x, y) for x, y, _ in xs); hi = max(max(x, y) for x, y, _ in xs)
    ax.plot([lo, hi], [lo, hi], color=C["ink2"], lw=1, ls="--")
    style(ax, f"Selected-plan energy at {budget} s (below diagonal = GA-MCTS lower)", f"{a} E", f"{b} E")


def dev(ga, mc, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    T = {"GA": {r["root_id"]: r for r in jl(ga) if r["arm"] == "GA"}, "GA-MCTS": {r["root_id"]: r for r in jl(mc) if r["arm"] == "GA-MCTS"}}
    E = {l: {rid: {int(b): esel(v) for b, v in r["budgets"].items()} for rid, r in T[l].items()} for l in T}
    roots = sorted(set(T["GA"]) & set(T["GA-MCTS"]))
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.6))
    regret_plot(ax[0], E, ["GA", "GA-MCTS"], roots); cdf_plot(ax[1], T, ["GA", "GA-MCTS"]); scatter_plot(ax[2], E, "GA", "GA-MCTS", roots, 30)
    fig.suptitle("DEV (20 exposed roots): learned energy only, no physical verification", x=0.01, ha="left", color=C["ink"])
    fig.tight_layout(); fig.savefig(out / "dev_anytime.png", dpi=130); print(out / "dev_anytime.png")


def evalfigs(ev, out):
    ev, out = Path(ev), Path(out); out.mkdir(parents=True, exist_ok=True)
    R = json.loads((ev / "EVAL_RESULTS.json").read_text()); S = R["summary"]; n = R["n_roots"]
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    for lab, col, lw in (("GA", C["GA"], 2), ("GA-MCTS-s0", C["GA-MCTS"], 2), ("GA-MCTS-s1", C["GA-MCTS"], 0.8), ("GA-MCTS-s2", C["GA-MCTS"], 0.8)):
        y = [100 * S[f"{lab}@{b}"]["rate"] for b in B]
        if lw == 2:
            w = [S[f"{lab}@{b}"]["wilson95"] for b in B]
            ax.fill_between(B, [100 * a for a, _ in w], [100 * c for _, c in w], color=col, alpha=0.12, lw=0)
        ax.plot(B, y, "-o" if lw == 2 else "-", color=col, lw=lw, ms=8, label=lab if lab != "GA-MCTS-s2" else None)
    for lab, col in (("REC", C["REC"]), ("H3", C["H3"])):
        ax.axhline(100 * S[lab]["rate"], color=col, lw=2, ls="--", label=f"{lab} (one plan)")
    ax.set_xscale("log"); ax.set_xticks(B); ax.set_xticklabels([str(b) for b in B])
    style(ax, f"Verified success vs planning budget ({n} BENCH_COMP roots)", "budget (s, log)", "verified success (%)"); ax.legend(frameon=False, fontsize=9)
    fig.tight_layout(); fig.savefig(out / "1_success_vs_budget.png", dpi=130); plt.close(fig)
    T = {"GA": {}, "GA-MCTS": {}}
    for f in sorted(ev.glob("any_s*.part*.jsonl")):
        for r in jl(f):
            if r["arm"] == "GA":
                T["GA"][r["root_id"]] = r
            elif r["seed"] == 0:
                T["GA-MCTS"][r["root_id"]] = r
    E = {l: {rid: {int(b): esel(v) for b, v in r["budgets"].items()} for rid, r in T[l].items()} for l in T}
    roots = sorted(set(T["GA"]) & set(T["GA-MCTS"]))
    fig, ax = plt.subplots(figsize=(7.5, 4.8)); regret_plot(ax, E, ["GA", "GA-MCTS"], roots); fig.tight_layout(); fig.savefig(out / "2_energy_regret.png", dpi=130); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    P = R["primary_paired"]; x = np.arange(len(B))
    ax.bar(x - 0.18, [p["b_wins"] for p in P], 0.34, color=C["GA-MCTS"], label="GA-MCTS s0 wins")
    ax.bar(x + 0.18, [p["b_losses"] for p in P], 0.34, color=C["GA"], label="GA wins")
    for i, p in enumerate(P):
        ax.text(i, max(p["b_wins"], p["b_losses"]) + 0.4, f"p_Holm={p['p_holm']:.2g}", ha="center", fontsize=8, color=C["ink2"])
    ax.set_xticks(x); ax.set_xticklabels([f"{b} s" for b in B]); style(ax, "Paired discordant roots per budget", "budget", "roots"); ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(out / "3_paired_wins.png", dpi=130); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7.5, 4.8)); cdf_plot(ax, T, ["GA", "GA-MCTS"]); fig.tight_layout(); fig.savefig(out / "4_time_to_incumbent.png", dpi=130); plt.close(fig)
    per = R["per_root"]
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    for a_, bud in zip(ax, (30, 180)):
        def mk(r, bud=bud):
            g, m = per[r][f"GA@{bud}"]["succ"], per[r][f"GA-MCTS-s0@{bud}"]["succ"]
            return ("^", C["GA-MCTS"]) if m and not g else ("v", C["GA"]) if g and not m else ("o", C["ink2"])
        scatter_plot(a_, E, "GA", "GA-MCTS", roots, bud, mk)
    fig.text(0.01, 0.01, "orange ^ = only GA-MCTS verified; blue v = only GA verified; gray o = same outcome", color=C["ink2"], fontsize=9)
    fig.tight_layout(); fig.savefig(out / "5_energy_scatter.png", dpi=130); plt.close(fig)
    print("figures ->", out)


if __name__ == "__main__":
    {"dev": lambda: dev(*sys.argv[2:5]), "eval": lambda: evalfigs(*sys.argv[2:4])}[sys.argv[1]]()
