#!/usr/bin/env python3
"""Figures (real public 2D VAL scenes; every probability is a FROZEN-MODEL value, never a certificate; verified = independent teacher).
  p1        P1 recall: legal grid, frozen cVAE prior heatmap of the witness object(s), top-4 / rank 5-6 / tail cells, known verified witness
  alloc     P2: tier-release / eligible-expanded-scored curves for SEEDED4 vs FULL MCTS and beam on one DEV root (model-only)
  curves    P2: model-only regret / agreement vs B_score and LIVE wall time
  physical  P4: verified success (strict and operational), paired deltas, latency
    python figs.py p1|alloc|curves|physical"""
from __future__ import annotations

import collections, json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import run as RUN  # noqa: E402

FIG = HERE / "reports" / "figures"
INK, MUTED, BLUE, RED, GREEN, ORANGE, PURPLE, GREY = "#222222", "#6b6a66", "#2a78d6", "#b4441c", "#1a9e6e", "#e07b00", "#7b5ea7", "#b9b8b3"
ARMC = {"EXACT4": INK, "EXACT6": MUTED, "EXACT_FULL": "#000000", "RAND_FULL": GREY, "BEAM_SEEDED4": ORANGE, "BEAM_FULL": "#f2b366",
        "BEAM_FULL_UNIFORM": "#f6d6a8", "PW_MCTS_SEEDED4": BLUE, "PW_MCTS_FULL": PURPLE, "PW_MCTS_UNIFORM": "#c4b5dc"}


def scene(ax, row, dom, obj=None, arrows=(), title=""):
    """All public legal cells; frozen prior of `obj` as a single-hue heatmap; rings = top-4 (solid) / rank 5-6 (dashed) of `obj`."""
    inp = row["inputs"]; xy = {int(k): v for k, v in inp["cell_xy"].items()}; c0 = [int(c) for c in inp["cells0"]]
    if obj is not None:
        p = np.array([dom.raw[(obj, d)] for d in dom.L]); v = p / p.max()
        ax.scatter([xy[d][0] for d in dom.L], [xy[d][1] for d in dom.L], s=150, c=v, cmap="Blues", vmin=0, vmax=1, marker="s", zorder=1, lw=0)
        for d in dom.D6[obj][:4]:
            ax.scatter(*xy[d], s=230, facecolors="none", edgecolors=INK, lw=1.4, marker="s", zorder=2)
        for d in dom.D6[obj][4:6]:
            ax.scatter(*xy[d], s=230, facecolors="none", edgecolors=INK, lw=1.0, ls="--", marker="s", zorder=2)
    else:
        ax.scatter([xy[d][0] for d in dom.L], [xy[d][1] for d in dom.L], s=120, color="#ececea", marker="s", zorder=1, lw=0)
    for i, c in enumerate(c0):
        t = i == inp["tid"]; mv = i in dom.objs
        ax.scatter(*xy[c], s=240, color=RED if t else (MUTED if mv else "#3d3d3a"), edgecolor="white", zorder=3)
        ax.text(*xy[c], "T" if t else str(i), ha="center", va="center", fontsize=6.5, color="white", zorder=4)
    ax.scatter(*xy[int(inp["goal_cell"])], s=300, facecolors="none", edgecolors=GREEN, lw=2.2, marker="s", zorder=3)
    for j, (o, d, col) in enumerate(arrows):
        ax.annotate("", xy[d], xy[c0[o]], arrowprops=dict(arrowstyle="-|>", color=col, lw=1.8), zorder=5)
        ax.scatter(*xy[d], s=90, marker="*", color=col, zorder=6)
        ax.text(xy[d][0], xy[d][1] + 0.025, f"{j + 1}", fontsize=7, color=col, ha="center", zorder=6)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([]); ax.set_title(title, fontsize=7.2, loc="left")
    for s in ax.spines.values():
        s.set_visible(False)


def p1(n=4):
    """First n EVAL K1/K2 roots (MCTS_ORDER) where the old EXACT4 pick was NOT a verified success and every known K<=2 witness lies
    outside the frozen top-4 pool (the P1 pool-miss candidates).  Analysis-only use of private labels; nothing here feeds the planner."""
    samp, scor, man = RUN.models()
    pr = {p["root_id"]: p for p in map(json.loads, open(Path.home() / "fds_private/P1_PER_ROOT_PRIVATE.jsonl"))}
    W = collections.defaultdict(list)
    for w in map(json.loads, open(Path.home() / "fds_private/P1_WITNESSES_PRIVATE.jsonl")):
        if w["category"] in ("TOP4", "RANK5_6", "BEYOND6"):
            W[w["root_id"]].append(w)
    pick = [r for r in RUN.root_rows(None, "EVAL") if pr[r["root_id"]]["K"] in ("1", "2") and pr[r["root_id"]]["exact4_outcome"] not in (None, "SUCCESS")
            and W[r["root_id"]] and all(w["category"] != "TOP4" for w in W[r["root_id"]])][:n]
    FIG.mkdir(parents=True, exist_ok=True); out = []
    for r in pick:
        root, dom, _ = RUN.build(r, samp, man, 0.25)
        w = sorted(W[r["root_id"]], key=lambda w: (-w["primary_source"], max(w["ranks"]), json.dumps(w["seq"])))[0]
        objs = sorted({o for o, _ in w["seq"]})
        fig, axs = plt.subplots(1, len(objs), figsize=(5.4 * len(objs), 6.4), squeeze=False)
        rk = {oo: dom.rank[(oo, d)] + 1 for oo, d in w["seq"]}
        for ax, o in zip(axs[0], objs):
            arr = [(oo, d, BLUE if oo == o else MUTED) for oo, d in w["seq"]]
            scene(ax, r, dom, o, arr, f"heatmap: frozen cVAE marginal of object {o} (rank of its witness cell: {rk[o]})")
        fig.suptitle(f"{r['root_id']}  |  VAL EVAL, K{pr[r['root_id']]['K']}  |  old EXACT4 (top-4 pool) verified outcome: {pr[r['root_id']]['exact4_outcome']}\n"
                     f"Known VERIFIED witness {[list(x) for x in w['seq']]} (source {'+'.join(w['sources'])}); stratum {w['stratum']}; numbers = witness order.\n"
                     f"Squares = all {len(dom.L)} public legal cells; solid ring = top-4, dashed ring = rank 5-6; green = goal; T = target.\n"
                     f"Frozen X/Y p11 of the witness (best order) = {w['p11_best_order']:.3f}: a model PREDICTION, not a verification.",
                     fontsize=8, x=0.01, ha="left", y=0.995)
        fig.tight_layout(rect=(0, 0, 1, 0.86))
        f = FIG / f"p1_root_{r['root_id']}.png"; fig.savefig(f, dpi=130); plt.close(fig)
        out.append({"root_id": r["root_id"], "figure": f.name, "witness_ranks": w["ranks"], "stratum": w["stratum"]})
    (HERE / "reports" / "P1_FIGURES.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))


def alloc(B=1024):
    """First DEV root (MCTS_ORDER) with >= 8 movable objects: how each frozen search arm spends B unique ordered X/Y scores (offline
    replay of the full table; model-only).  Top: distinct actions ELIGIBLE (tier level x |tier|), actions appearing in a fully SCORED set,
    and MCTS EXPANDED actions are logged separately (node count); dashed verticals = tier unlocks.  Bottom: cumulative fully scored sets by
    max-tier stratum.  Right: MCTS root widening (children vs visits)."""
    import fsearch as FS
    samp, scor, man = RUN.models(); fp = json.loads((HERE / "reports" / "P2_FROZEN_PARAMS.json").read_text())
    r = next(r for r in RUN.root_rows(None, "DEV") if len(RUN.build(r, samp, man, 0.25)[1].objs) >= 8)
    root, dom, _ = RUN.build(r, samp, man, 0.25); T = RUN.table(root, dom, scor); fn = RUN.replay(T)
    import domain as DM
    doms = {e: DM.Domain({o: {d: dom.raw[(o, d)] for (oo, d) in dom.acts if oo == o} for o in dom.objs}, dom.D6, e) for e in (0.1, 0.25, 0.5, 1.0)}
    arms = ["PW_MCTS_SEEDED4", "PW_MCTS_FULL", "BEAM_SEEDED4", "BEAM_FULL"]
    fig, axs = plt.subplots(2, 5, figsize=(22, 8.2), gridspec_kw={"width_ratios": [1, 1, 1, 1, 1.15]})
    ntier = collections.Counter(dom.tier.values()); info = []
    for j, arm in enumerate(arms):
        p = dict(fp[arm]); e = p.pop("eps", 0.25); d = doms[e]
        O = FS.Oracle(fn, B, root.displacement); st = FS.Stage(d, O, p.get("sched") if "SEEDED" in arm else None)
        rng = np.random.default_rng(FS.h64(arm.split("_")[0], r["root_id"], 0))
        if arm.startswith("PW"):
            stop, it, tree, Tn, stats = FS.mcts(d, O, st, rng, **{k: (tuple(v) if k == "pw" else v) for k, v in p.items() if k in ("c", "pw", "nb", "q_dir")})
        else:
            stop = FS.beam(d, O, st, rng, **{k: v for k, v in p.items() if k in ("w", "nb", "q_dir", "q_single")}); tree = None
        xs, acts, seen, strat = [], [], set(), collections.Counter(); cum = collections.defaultdict(list)
        for A, start, _ in O.log:
            seen |= set(A); xs.append(start); acts.append(len(seen)); s_ = "TOP4" if max(dom.tier[a] for a in A) == 1 else ("RANK5_6" if max(dom.tier[a] for a in A) == 2 else "TAIL")
            strat[s_] += 1
            for k in ("TOP4", "RANK5_6", "TAIL"):
                cum[k].append(strat[k])
        lv = [(1, 1)] + [(l, c) for l, c, w in st.events if l > 1] if st.sched else [(3, 1)]
        ex = np.arange(1, B + 1); el = np.zeros(len(ex))
        for l, c in lv:
            el[ex >= c] = sum(ntier[t] for t in range(1, l + 1))
        ax = axs[0, j]
        ax.plot(ex, el, color=MUTED, lw=2, label="actions eligible")
        ax.plot(xs, acts, color=ARMC[arm], lw=2, label="actions in a fully scored set")
        for l, c, w in st.events:
            if l > 1:
                ax.axvline(c, color=INK, ls="--", lw=1); ax.text(c, el.max() * 0.97, {2: " +T56", 3: " +TAIL"}[l] + ("\n early" if w.startswith("EARLY") else ""), fontsize=7)
        ax.set_title(f"{arm}  (stop={stop})", fontsize=8.5, loc="left"); ax.set_xlabel("unique ordered X/Y scores charged", fontsize=7.5)
        ax.legend(fontsize=7, frameon=False, loc="center right"); ax.tick_params(labelsize=7)
        ax = axs[1, j]
        for k, col in (("TOP4", INK), ("RANK5_6", ORANGE), ("TAIL", BLUE)):
            ax.plot(xs, cum[k], color=col, lw=2, label=f"sets with max tier {k}")
        ax.set_xlabel("unique ordered X/Y scores charged", fontsize=7.5); ax.set_ylabel("fully scored sets (cumulative)", fontsize=7.5)
        ax.legend(fontsize=7, frameon=False); ax.tick_params(labelsize=7)
        pick = FS.choose(O.candidates(), man["config"]["rule"])
        info.append(f"{arm}: committed {pick['seq'] if pick else None} (p11 {pick['p11'] if pick else 0:.3f}, predicted)")
        if tree is not None:
            kids = [k for k in tree.kids if not k.stop]
            axs[j % 2, 4].scatter([k.N for k in kids], [len([c for c in k.kids if not c.stop]) for k in kids], s=14, color=ARMC[arm], alpha=0.7,
                                  label=f"{arm}: {len(kids)} root children, {len(Tn)} nodes")
    for i in range(2):
        a = axs[i, 4]; a.set_xlabel("visits of a K1 node (singleton set)", fontsize=7.5); a.set_ylabel("pair children expanded under it", fontsize=7.5)
        a.legend(fontsize=7, frameon=False); a.tick_params(labelsize=7); a.set_title("progressive widening per K1 node", fontsize=8.5, loc="left")
    fig.suptitle(f"DEV root {r['root_id']}: {len(dom.objs)} movable objects x {len(dom.L)} legal cells = {len(dom.acts)} actions "
                 f"(T4 {ntier[1]}, T56 {ntier[2]}, tail {ntier[3]}); B_score = {B}; frozen P2 parameters; MODEL-ONLY (offline replay of the full table).\n"
                 "ADD order in the tree is never the execution order: every fully scored set is scored in all orders and X/Y picks the order.\n" + " | ".join(info),
                 fontsize=8, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.9)); FIG.mkdir(parents=True, exist_ok=True); fig.savefig(FIG / "p2_allocation_tiers.png", dpi=125); plt.close(fig)


def curves(model_json, lat_json, tag):
    """Model-only regret / agreement / off-top-4 picks vs B_score (seeds pooled) and LIVE end-to-end latency vs B."""
    M = json.loads(Path(model_json).read_text()); L = json.loads(Path(lat_json).read_text()) if lat_json and Path(lat_json).exists() else None
    arms = ["RAND_FULL", "BEAM_SEEDED4", "BEAM_FULL", "BEAM_FULL_UNIFORM", "PW_MCTS_SEEDED4", "PW_MCTS_FULL", "PW_MCTS_UNIFORM"]
    Bs = [64, 256, 1024, 4096]
    fig, axs = plt.subplots(1, 4, figsize=(21, 4.8))
    for k, ax, lab in (("mean_regret", axs[0], "mean model regret vs EXACT_FULL (p11)"), ("agree_EXACT_FULL", axs[1], "committed decision == EXACT_FULL"),
                       ("pick_off_top4", axs[2], "share of roots whose committed set is off top-4")):
        for a in arms:
            y = [M["arms"].get(f"{a}@{b}", {}).get(k) for b in Bs]
            ax.plot(Bs, y, marker="o", ms=4, lw=1.8, color=ARMC[a], label=a)
        for a, ls in (("EXACT4", "-"), ("EXACT6", "--")):
            ax.axhline(M["arms"][f"{a}@None"][k], color=ARMC[a], ls=ls, lw=1.2, label=f"{a} (natural cost {M['arms'][f'{a}@None']['median_scored']:.0f})")
        ax.set_xscale("log", base=4); ax.set_xticks(Bs); ax.set_xticklabels(Bs); ax.set_xlabel("B_score (unique ordered X/Y scores)", fontsize=8)
        ax.set_title(lab, fontsize=9, loc="left"); ax.tick_params(labelsize=7.5)
    axs[0].legend(fontsize=6.5, frameon=False)
    if L:
        for a in arms:
            y = [L["arms"].get(f"{a}@{b}", {}).get("end_to_end_s_median") for b in Bs]
            axs[3].plot(Bs, y, marker="o", ms=4, lw=1.8, color=ARMC[a], label=a)
        for a, ls in (("EXACT4", "-"), ("EXACT6", "--"), ("EXACT_FULL", ":")):
            axs[3].axhline(L["arms"][f"{a}@None"]["end_to_end_s_median"], color=ARMC[a], ls=ls, lw=1.2, label=a)
        axs[3].set_xscale("log", base=4); axs[3].set_yscale("log"); axs[3].set_xticks(Bs); axs[3].set_xticklabels(Bs)
        axs[3].set_title(f"LIVE end-to-end latency, median over {L['roots']} roots (s, log)", fontsize=9, loc="left"); axs[3].legend(fontsize=6.5, frameon=False)
        axs[3].set_xlabel("B_score", fontsize=8); axs[3].tick_params(labelsize=7.5)
    fig.suptitle(f"{tag}: {M['roots']} roots, seeds pooled; values are frozen-model PREDICTIONS (not physical verification); latency = live RTX 5060 runs", fontsize=9, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.93)); fig.savefig(FIG / f"p2_budget_curves_{tag.lower()}.png", dpi=125); plt.close(fig)


def physical(phys_json):
    """Verified K1+K2 success per arm: strict (decided-only rate, ITT bounds) and operational; paired contrasts with cluster 95% CIs."""
    S = json.loads(Path(phys_json).read_text())
    arms = [a for a in S["by_mode"]["strict"]["arms"]]
    fig, axs = plt.subplots(1, 2, figsize=(17, 6.2), gridspec_kw={"width_ratios": [1, 1.25]})
    ax = axs[0]
    for i, a in enumerate(arms):
        st_ = S["by_mode"]["strict"]["arms"][a]["K1+K2"]; op = S["by_mode"]["operational"]["arms"][a]["K1+K2"]
        ax.plot(st_["itt_bounds"], [i, i], color=GREY, lw=5, solid_capstyle="butt")
        ax.scatter(st_["rate_decided"], i, color=ARMC.get(a.split("@")[0], INK), s=40, zorder=3)
        ax.scatter(op["rate_decided"], i, facecolors="none", edgecolors=INK, s=40, zorder=3)
        ax.text(1.005, i, f"{st_['success']}/{st_['decided']} decided, {st_['unknown']} UNKNOWN", va="center", fontsize=7)
    ax.set_yticks(range(len(arms))); ax.set_yticklabels(arms, fontsize=7.5); ax.invert_yaxis(); ax.set_xlim(0.3, 1.0)
    ax.set_xlabel("K1+K2 verified task success", fontsize=8)
    ax.set_title("filled = strict (UNKNOWN excluded), grey bar = bounds if UNKNOWN all fail / all succeed,\nopen = operational (frozen v32b_phys: UNKNOWN value 0 = failure)", fontsize=8, loc="left")
    ax = axs[1]; C = S["by_mode"]["strict"]["contrasts"]; ks = [k for k in C if k.endswith("| K1+K2") and C[k]["pairs"]]
    for i, k in enumerate(ks):
        m, lo, hi = C[k]["diff"]
        ax.plot([lo, hi], [i, i], color=INK, lw=1.6); ax.scatter(m, i, color=BLUE if lo > 0 else (RED if hi < 0 else INK), s=30, zorder=3)
        ax.text(0.33, i, f"n={C[k]['pairs']}  W/L {C[k]['wins']}/{C[k]['losses']}", va="center", fontsize=6.8)
    ax.axvline(0, color=MUTED, lw=1); ax.set_yticks(range(len(ks))); ax.set_yticklabels([k.replace(" | K1+K2", "") for k in ks], fontsize=7)
    ax.invert_yaxis(); ax.set_xlim(-0.35, 0.45); ax.set_xlabel("paired difference in verified success (strict, both decided), 95% lineage-cluster bootstrap", fontsize=8)
    fig.suptitle(f"{S['cohort']}: physical verification by the unchanged independent teacher; seed-0 sealed picks", fontsize=9, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95)); fig.savefig(FIG / "p4_physical_success.png", dpi=125); plt.close(fig)


if __name__ == "__main__":
    a = sys.argv[1:]
    {"p1": p1, "alloc": alloc, "curves": lambda: curves(a[1], a[2] if len(a) > 2 else None, a[3] if len(a) > 3 else "DEV"),
     "physical": lambda: physical(a[1])}[a[0]]()
