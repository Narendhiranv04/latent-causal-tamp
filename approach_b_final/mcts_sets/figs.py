#!/usr/bin/env python3
"""Figures for the K<=2 set-search study.  All probabilities shown are FROZEN-MODEL PREDICTIONS, never certificates.
  roots   real public VAL roots (first 4 EVAL roots in MCTS_ORDER where sealed UCT_SET@256 chose a REPAIR; no label used): 2D scene, cVAE
          top-4 destinations per object, MCTS explored sets (visits, mean predicted reward), both execution orders of the selected set with
          pX / pY / p11; re-runs UCT and asserts the decision equals the sealed prediction
  curves  model-only agreement with EXACT_K2 vs budget (EVAL, all strata) and LIVE wall time vs budget (timing subset)
    python figs.py roots|curves"""
from __future__ import annotations

import collections, hashlib, itertools, json, statistics as st, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import run as RUN  # noqa: E402
import search_sets as SS  # noqa: E402

FIG = HERE / "reports" / "figures"
INK, MUTED, BLUE, RED, GREEN, ORANGE, GREY, PURPLE = "#222222", "#7a7975", "#2a78d6", "#b4441c", "#1baf7a", "#e07b00", "#9a9a96", "#7b5ea7"
ARMC = {"EXACT_K2": INK, "UCT_SET": BLUE, "PW_UCT_SET": PURPLE, "BEAM_SET": ORANGE, "RAND_SET": GREY}


def scene(ax, row, D, order=None):
    inp = row["inputs"]; xy = {int(k): v for k, v in inp["cell_xy"].items()}; c0 = [int(c) for c in inp["cells0"]]
    for c in inp["legal_cells"]:
        ax.scatter(*xy[int(c)], s=18, color="#eeeeee", marker="s", zorder=1)
    cols = plt.cm.tab10.colors
    for i, (o, ds) in enumerate(sorted(D.items())):
        for r, d in enumerate(ds):
            ax.scatter(*xy[d], s=34 - 6 * r, color=cols[i % 10], alpha=0.55, zorder=2, lw=0)
    for i, c in enumerate(c0):
        t = i == inp["tid"]
        ax.scatter(*xy[c], s=260, color=RED if t else GREY, edgecolor="white", zorder=3)
        ax.text(*xy[c], "T" if t else str(i), ha="center", va="center", fontsize=6.5, color="white", zorder=4)
    g = xy[int(inp["goal_cell"])]; ax.scatter(*g, s=330, facecolors="none", edgecolors=GREEN, lw=2, marker="s", zorder=3)
    for j, (o, d) in enumerate(order or []):
        ax.annotate("", xy[d], xy[c0[o]], arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.6), zorder=5)
        ax.text(*xy[d], str(j + 1), fontsize=7, color=BLUE, ha="center", va="bottom", zorder=6)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])


def roots(n=4):
    import search as S
    samp, scor, man = RUN.models()
    E = {json.loads(l)["root_id"]: json.loads(l) for l in open(RUN.OUT / "eval_val.jsonl")}
    rows = [r for r in RUN.root_rows(None, "EVAL") if any(x["arm"] == "UCT_SET" and x["budget"] == 256 and x["seed"] == 0 and x["decision"] == "REPAIR"
                                                         for x in E[r["root_id"]]["results"])][:n]
    FIG.mkdir(parents=True, exist_ok=True); checks = []
    for r in rows:
        root = S.Root(r, "2d"); D, _ = RUN.proposals(root, samp, man); T = RUN.table(root, scor, D)
        fp = json.loads((HERE / "reports" / "P2_FROZEN_PARAMS.json").read_text())["UCT_SET"]
        O = SS.Oracle(RUN.replay_fn(T), 256, root.displacement); stop, it, tree = SS.uct(SS.Pool(D), O, seed=0, key=r["root_id"], **fp)
        pick = SS.choose(O.candidates(), man["config"]["rule"])
        sealed = next(x for x in E[r["root_id"]]["results"] if x["arm"] == "UCT_SET" and x["budget"] == 256 and x["seed"] == 0)
        checks.append({"root_id": r["root_id"], "matches_sealed": (pick or {}).get("seq") == sealed["seq"]})
        nodes, st_ = [], [tree]
        while st_:
            n_ = st_.pop(); st_ += n_.kids
            if n_.A and n_.N and not n_.stop:
                nodes.append(n_)
        top = sorted(nodes, key=lambda n_: (-n_.N, n_.A))[:14]
        A = SS.Pool.canon([tuple(m) for m in pick["seq"]])
        perms = [(p, T[p]) for p in itertools.permutations(A)]
        fig, axs = plt.subplots(1, 3, figsize=(19, 5.6), gridspec_kw={"width_ratios": [1.1, 1.2, 0.9]})
        scene(axs[0], r, D, [tuple(m) for m in pick["seq"]])
        axs[0].set_title(f"{r['root_id']}\nobjects (T = target, green square = goal); dots = frozen cVAE top-4 destinations per object\n"
                         f"arrows = selected REPAIR in X/Y-chosen execution order", fontsize=7.5, loc="left")
        lab = [" + ".join(f"o{o}->{d}" for o, d in n_.A) for n_ in top]
        axs[1].barh(range(len(top)), [n_.N for n_ in top], color=BLUE, height=0.6)
        for i, n_ in enumerate(top):
            axs[1].text(n_.N + 0.3, i, f"mean predicted reward {n_.W / n_.N:.2f}" + (f" | set max p11 {O.sets[n_.A]:.2f}" if n_.A in O.sets else ""), va="center", fontsize=6.5, color=INK)
        axs[1].set_yticks(range(len(top))); axs[1].set_yticklabels(lab, fontsize=6.5); axs[1].invert_yaxis()
        axs[1].set_xlabel("MCTS visits (unordered sets; tree insertion order is NOT execution order)", fontsize=7.5)
        axs[1].set_title(f"UCT_SET B=256: {O.n['scored']} unique ordered X/Y calls (incl. no-op), {O.n['sets_scored']} sets, {it} iterations, stop={stop}",
                         fontsize=7.5, loc="left")
        txt = [f"selected set {list(A)}", ""] + [f"order {[list(x) for x in p]}:  pX={v['px']:.3f}  pY={v['py']:.3f}  p11={v['p11']:.3f}" for p, v in perms]
        txt += ["", f"no-op p11 = {T[()]['p11']:.3f} (gate 0.5);  eta = 0.3", f"chosen order (energy argmin): {pick['seq']}", "",
                "pY is shared by both orders (same endpoint); only pX is order-dependent.", "All values are frozen-model predictions."]
        axs[2].text(0.0, 0.98, "\n".join(txt), va="top", fontsize=7.5, family="monospace", transform=axs[2].transAxes); axs[2].axis("off")
        fig.tight_layout(); fig.savefig(FIG / f"root_{r['root_id']}.png", dpi=115); plt.close(fig)
    (HERE / "reports" / "FIG_ROOT_CHECKS.json").write_text(json.dumps(checks, indent=1)); print(json.dumps(checks))


def curves():
    S = json.loads((HERE / "reports" / "MODEL_SUMMARY_EVAL.json").read_text())
    L = [json.loads(l) for l in open(HERE / "reports" / "P2_LIVE_TIMING.jsonl")]
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.8)); Bs = list(RUN.BUDGETS)
    for arm in ("UCT_SET", "PW_UCT_SET", "BEAM_SET", "RAND_SET"):
        axs[0].plot(Bs, [S["arms"][f"{arm}@{b}"]["agree_with_exact"] for b in Bs], "-o", color=ARMC[arm], label=arm, lw=2, ms=6)
    axs[0].axhline(1.0, color=INK, ls=":", lw=1); axs[0].text(Bs[0], 1.005, f"EXACT_K2 (median {S['EXACT_K2']['median_scored']:.0f} scored)", fontsize=7.5)
    axs[0].set_xscale("log", base=2); axs[0].set_xlabel("budget: unique ordered X/Y evaluations (incl. no-op)"); axs[0].set_ylabel("agreement with EXACT_K2 decision")
    axs[0].set_title(f"MODEL-ONLY: agreement with exhaustive K<=2 (EVAL, {S['roots']} roots, seeds 0-2)", fontsize=8.5, loc="left"); axs[0].legend(frameon=False, fontsize=8)
    w = collections.defaultdict(list)
    for r in L:
        for x in r["results"]:
            w[(x["arm"], x["budget"])].append(x["wall_s"])
    for arm in ("UCT_SET", "PW_UCT_SET", "BEAM_SET", "RAND_SET"):
        axs[1].plot(Bs, [st.median(w[(arm, b)]) for b in Bs], "-o", color=ARMC[arm], label=arm, lw=2, ms=6)
    ex = st.median(w[("EXACT_K2", None)]); axs[1].axhline(ex, color=INK, ls=":", lw=1.2); axs[1].text(Bs[0], ex * 1.15, f"EXACT_K2 live median {ex:.3f} s", fontsize=7.5)
    axs[1].set_xscale("log", base=2); axs[1].set_yscale("log"); axs[1].set_xlabel("budget"); axs[1].set_ylabel("median live planning wall time (s)")
    axs[1].set_title(f"LIVE wall time ({len(L)} EVAL roots, RTX 5060): many small batches vs one batched exhaustive pass", fontsize=8.5, loc="left")
    for a in axs:
        for s_ in ("top", "right"):
            a.spines[s_].set_visible(False)
    FIG.mkdir(parents=True, exist_ok=True); fig.tight_layout(); fig.savefig(FIG / "budget_curves_model_only.png", dpi=130); plt.close(fig)


def physical():
    """PHYSICALLY VERIFIED (unchanged teacher, frozen v32b_phys outcome): pooled K1+K2 success per arm at B=64 / 256 and EXACT_K2, K1 vs K2,
    and paired differences vs EXACT_K2 with 95 % root bootstrap intervals."""
    S = json.loads((HERE / "reports" / "P3_PHYSICAL_VAL.json").read_text())
    fig, axs = plt.subplots(1, 2, figsize=(15, 4.8))
    arms = ["EXACT_K2@None"] + [f"{a}@{b}" for b in (64, 256) for a in ("UCT_SET", "PW_UCT_SET", "BEAM_SET", "RAND_SET")]
    x = range(len(arms))
    for j, (k, off) in enumerate((("K1", -0.2), ("K2", 0.0), ("K1K2", 0.2))):
        v = [S["arms"][a][k]["rate"] for a in arms]
        axs[0].bar([i + off for i in x], v, width=0.2, color=[GREY, MUTED, BLUE][j], label=k)
    axs[0].set_xticks(list(x)); axs[0].set_xticklabels([a.replace("@None", "").replace("_SET", "") for a in arms], rotation=30, fontsize=7.5)
    axs[0].set_ylabel("verified task success"); axs[0].set_ylim(0, 0.8); axs[0].legend(frameon=False, fontsize=8)
    axs[0].set_title(f"PHYSICALLY VERIFIED, EVAL K1 ({S['roots']['1']}) / K2 ({S['roots']['2']}) roots, seed 0", fontsize=8.5, loc="left")
    pk = [k for k in S["paired"] if k.endswith("EXACT_K2@None")] + [k for k in S["paired"] if "BEAM" in k or "RAND" in k]
    for i, k in enumerate(pk):
        v = S["paired"][k]; axs[1].plot(v["ci95"], [i, i], color=BLUE, lw=2); axs[1].scatter(v["diff"], i, color=INK, zorder=3)
    axs[1].axvline(0, color=MUTED, lw=1); axs[1].axvline(-0.05, color=RED, ls=":", lw=1); axs[1].text(-0.05, len(pk) - 0.4, "-5 pp margin", color=RED, fontsize=7)
    axs[1].set_yticks(range(len(pk))); axs[1].set_yticklabels([k.replace("_SET", "").replace("@None", "") for k in pk], fontsize=7)
    axs[1].set_xlabel("paired difference in pooled K1+K2 success (95 % root bootstrap)"); axs[1].set_title("paired comparisons (same roots)", fontsize=8.5, loc="left")
    for a in axs:
        for s_ in ("top", "right"):
            a.spines[s_].set_visible(False)
    fig.tight_layout(); fig.savefig(FIG / "physical_success.png", dpi=130); plt.close(fig)


if __name__ == "__main__":
    {"roots": roots, "curves": curves, "physical": physical}[sys.argv[1]]()
