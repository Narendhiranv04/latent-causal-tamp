"""BXY-P27 evidence (no teacher, no model): bounded lazy search on development roots under NON-LEARNED priorities, exact coverage
accounting, interruption / resume equivalence, and the search diagrams.
    python3 bxy_p27_report.py run | figures"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

import bxy_full_eval as EV
import bxy_fullsearch as Q
import bxy_fullspace as S

OUT = Path("runs/approach_b/bxy_p27_fullsearch_v1")
FIG = Path("visualizations/approach_b/bxy_p27_fullsearch_v1")
BUDGET = {"expansions": 40}


def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = {}
    for corpus, k, rec in EV.dev_roots():
        D = S.domain(rec)
        r = {"corpus": corpus, "n": len(D["movable"]), "F": S.free0(D)}
        for pol in ("SHORTEST", "GEOM"):
            c0 = time.process_time()
            st, res = Q.run(D, 4, EV.Analytic(rec, pol), BUDGET, fair=EV.FAIR)
            r[pol] = {"coverage": res["coverage"], "status": res["status"], "selected": res["selected"], "cpu_s": round(time.process_time() - c0, 2),
                      "depths": {m: sum(n["m"] == m for n in st["nodes"].values()) for m in range(5)},
                      "expanded_depths": {m: sum(n["m"] == m and not n["open"] and not n["dead"] and n["m"] < 4 for n in st["nodes"].values()) for m in range(4)},
                      "goal_dead_nodes": st["goal_dead_nodes"], "root_children": sum(n["m"] == 1 for n in st["nodes"].values())}
        rows[k] = r
    # interruption / resume equivalence on one root (hash-sealed state file)
    corpus, k, rec = EV.dev_roots()[0]
    D = S.domain(rec)
    full, rf = Q.run(D, 4, EV.Analytic(rec, "GEOM"), BUDGET, fair=EV.FAIR)
    st, _ = Q.run(D, 4, EV.Analytic(rec, "GEOM"), {"expansions": 13}, fair=EV.FAIR)
    h = Q.save(st, OUT / "STATE_interrupted.json")
    st2, r2 = Q.run(D, 4, EV.Analytic(rec, "GEOM"), BUDGET, fair=EV.FAIR, st=Q.load(OUT / "STATE_interrupted.json"))
    resume = {"root": k, "state_sha256": h, "identical_nodes": set(st2["nodes"]) == set(full["nodes"]), "identical_coverage": r2["coverage"] == rf["coverage"],
              "identical_selection": r2["selected"] == rf["selected"], "identical_trace": st2["trace"] == full["trace"]}
    out = {"version": Q.VERSION, "budget": BUDGET, "fair": EV.FAIR, "K": 4, "roots": rows, "resume": resume,
           "all_balanced": all(r[p]["coverage"]["balanced"] for r in rows.values() for p in ("SHORTEST", "GEOM")),
           "min_root_children": min(r["SHORTEST"]["root_children"] for r in rows.values()), "legacy_caps": {"MAX_CANDS": 24, "MAX_QUERIES": 60}}
    (OUT / "SEARCH_P27.json").write_text(json.dumps(out, indent=1, sort_keys=True))
    return {"resume": resume, "all_balanced": out["all_balanced"], "min_root_children": out["min_root_children"]}


INK, BLUE, ORANGE, GREY = "#222222", "#2a6fb0", "#d9822b", "#bbbbbb"


def figures() -> list:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIG.mkdir(parents=True, exist_ok=True)
    out = []
    # 1. search tree of a toy domain under a bounded budget: expanded / open frontier / sound GOAL_DEAD / never generated
    rec = S.toy({"A": 28, "B": 36}, target=27, goal=29, legal=[4, 5, 27, 28, 29, 36])
    D = S.domain(rec)
    st, res = Q.run(D, 2, lambda seqs: [float(len(s)) + 0.1 * sum(d for _, d in s) / 64 for s in seqs], {"expansions": 3}, fair=2)
    allseq = list(S.walk(D, 2))
    fig, ax = plt.subplots(figsize=(11, 4.6))
    pos, levels = {}, {m: [s for s in allseq if len(s) == m] for m in range(3)}
    for m, seqs in levels.items():
        for i, s in enumerate(seqs):
            pos[S.xsig(s)] = ((i + 0.5) / len(seqs), 2 - m)
    for s in allseq:
        if s:
            a, b = pos[S.xsig(s[:-1])], pos[S.xsig(s)]
            ax.plot([a[0], b[0]], [a[1], b[1]], color="#dddddd", lw=0.6, zorder=0)
    for s in allseq:
        k = S.xsig(s)
        n = st["nodes"].get(k)
        col, mk = (GREY, "o") if n is None else (ORANGE, "x") if n["dead"] else (BLUE, "o") if (not n["open"] and n["m"] < 2) else (INK, "o")
        ax.plot(*pos[k], mk, color=col, ms=6 if n else 4, mfc=col if n else "white")
        if len(s) <= 1:
            ax.text(pos[k][0], pos[k][1] + 0.12, k, ha="center", fontsize=6.5, rotation=0 if not s else 45)
    cv = res["coverage"]
    ax.set_title(f"Toy search tree (K=2, {cv['total']} members): expanded (blue) | examined, open or terminal (black) | GOAL_DEAD, not expanded "
                 f"(orange x) | not yet generated (hollow grey)\nbudget 3 expansions: examined {cv['examined']} + pruned_sound {cv['pruned_sound']} "
                 f"+ unexplored residual {cv['unexplored_residual']} = {cv['total']}", fontsize=8.5)
    ax.set_yticks([0, 1, 2], ["m = 2", "m = 1", "m = 0"]), ax.set_xticks([]), ax.set_ylim(-0.4, 2.5)
    for sp in ("top", "right", "bottom"):
        ax.spines[sp].set_visible(False)
    out.append(_save(fig, "01_toy_search_tree_explored_vs_deferred.png"))
    # 2. coverage accounting on development roots (log scale): examined vs residual frontier, exact balance
    R = json.loads((OUT / "SEARCH_P27.json").read_text())["roots"]
    ks = list(R)
    fig, ax = plt.subplots(figsize=(10.5, 4.4))
    x = np.arange(len(ks))
    for j, (pol, col) in enumerate((("SHORTEST", BLUE), ("GEOM", ORANGE))):
        cv = [R[k][pol]["coverage"] for k in ks]
        ax.bar(x + (j - 0.5) * 0.38, [c["examined"] for c in cv], 0.36, color=col, label=f"{pol}: examined (scored) members")
    ax.plot(x, [R[k]["GEOM"]["coverage"]["total"] for k in ks], "_", color=INK, ms=14, mew=2, label="domain size N(4)")
    ax.set_yscale("log"), ax.set_xticks(x, [k.replace("2d-", "").replace("bxyg34dev-", "").replace("bxy-v21b-", "") for k in ks], rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("members"), ax.legend(fontsize=7.5, frameon=False, loc="center left", bbox_to_anchor=(1.0, 0.5)), ax.grid(alpha=0.25, axis="y", lw=0.5)
    ax.set_title("40 expansions per root (non-learned priorities): examined + pruned_sound + residual = N(4) exactly on every root\n"
                 "the unexplored residual frontier is reported as unknown, never as infeasible", fontsize=8.5)
    out.append(_save(fig, "02_dev_coverage_examined_vs_domain.png"))
    return out


def _save(fig, name) -> str:
    import matplotlib.pyplot as plt
    p = FIG / name
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return str(p)


if __name__ == "__main__":
    print(json.dumps(run() if sys.argv[1] == "run" else figures(), indent=1))
