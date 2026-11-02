"""BXY-P26 evidence: exact universal-domain sizes on development roots, the post-hoc audit of the historical P16/P20 catalogues against
the domain (the catalogue is read HERE only, never by bxy_fullspace), enumeration throughput, and the three toy-scene figures.
    python3 bxy_p26_report.py counts | figures"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

import bxy_fullspace as S

OUT = S.OUT
FIG = Path("visualizations/approach_b/bxy_p26_fullspace_v1")
K = 4


def dev_roots() -> list:
    """(corpus, root, record) of every development root of P16 (V21 waves) and P20 (K34 waves); confirmation roots are never read."""
    out = []
    for corpus, base in (("V21", Path("runs/approach_b/bxy_p16_v1")), ("K34", Path("runs/approach_b/bxy_p20_v1"))):
        for f in sorted(base.glob("*/roots/*.json")):
            out.append((corpus, f.stem, json.loads(f.read_text())))
    return out


def audit_root(rec) -> dict:
    D = S.domain(rec)
    cat = [[(o, int(d)) for o, d in c["seq"]] for c in rec.get("catalogue_v21", [])]
    intended = [(o, int(d)) for o, d in rec.get("construction", {}).get("intended", [])]
    cls = [S.classify(D, s) for s in cat]
    n = S.count(D, K)
    return {"objects": len(D["cells0"]), "movable": len(D["movable"]), "fixed": len(D["fixed"]), "F": S.free0(D), "uniform": S.uniform(D),
            "sequences": n, "total": sum(n.values()), "endpoints": S.count_endpoints(D, K), "catalogue": len(cat),
            "catalogue_in_domain": sum(c is None for c in cls), "catalogue_m_gt_K": sum(len(s) > K for s in cat),
            "catalogue_out_of_domain": sorted({c for c in cls if c}), "catalogue_lengths": sorted({len(s) for s in cat}),
            "catalogue_max_cheb": max((max(_cheb(D["cells0"][o], d) for o, d in s) for s in cat if s), default=None),
            "intended_in_domain": (S.classify(D, intended) is None) if intended else None, "roles_keys_equal_movable": set(rec["roles"]) == set(D["movable"])}


def _cheb(a, b) -> int:
    return max(abs(a % 8 - b % 8), abs(a // 8 - b // 8))


def throughput(rec, k) -> dict:
    D = S.domain(rec)
    t0, n = time.process_time(), 0
    for _ in S.walk(D, k):
        n += 1
    dt = time.process_time() - t0
    return {"K": k, "enumerated": n, "expected": sum(S.count(D, k).values()), "cpu_s": round(dt, 2), "per_s": round(n / max(dt, 1e-9))}


def counts() -> dict:
    rows = {}
    for corpus, k, rec in dev_roots():
        rows[k] = {"corpus": corpus, **audit_root(rec)}
    tot = np.array([r["total"] for r in rows.values()], float)
    cat = np.array([r["catalogue"] for r in rows.values()], float)
    k34 = next(rec for c, k, rec in dev_roots() if c == "K34")
    tp = [throughput(k34, 2), throughput(k34, 3)]
    rate = tp[-1]["per_s"]
    summ = {"roots": len(rows), "by_corpus": {c: sum(r["corpus"] == c for r in rows.values()) for c in ("V21", "K34")},
            "total_K4": {"min": int(tot.min()), "median": float(np.median(tot)), "max": int(tot.max())},
            "catalogue": {"min": int(cat.min()), "median": float(np.median(cat)), "max": int(cat.max())},
            "catalogue_fraction_of_domain_median": float(np.median(cat / tot)),
            "catalogue_all_in_domain_or_longer_than_K": all(r["catalogue_in_domain"] + 0 == r["catalogue"] for r in rows.values()),
            "catalogue_entries_out_of_domain": sum(r["catalogue"] - r["catalogue_in_domain"] for r in rows.values()),
            "catalogue_entries_longer_than_K4": sum(r["catalogue_m_gt_K"] for r in rows.values()),
            "intended_in_domain": sum(bool(r["intended_in_domain"]) for r in rows.values()),
            "intended_present": sum(r["intended_in_domain"] is not None for r in rows.values()),
            "roles_keys_equal_movable": all(r["roles_keys_equal_movable"] for r in rows.values()),
            "all_uniform": all(r["uniform"] for r in rows.values()), "throughput": tp,
            "full_K4_enumeration_cpu_s_median_root_at_measured_rate": round(float(np.median(tot)) / rate, 0)}
    res = {"version": S.VERSION, "K": K, "summary": summ, "roots": rows, "domain_manifest_sha256": S.sha_file(OUT / "ACTION_DOMAIN_V1.json")}
    (OUT / "FULLSPACE_COUNTS_P26.json").write_text(json.dumps(res, indent=1, sort_keys=True))
    return summ


# ------------------------------------------------------------------ figures (2-3 colours: ink, blue = members, orange = negatives)
INK, BLUE, ORANGE, GREY = "#222222", "#2a6fb0", "#d9822b", "#bbbbbb"


def _board(ax, rec, title):
    import matplotlib.patches as mp
    ax.set_xlim(0, 0.64), ax.set_ylim(0, 0.64), ax.set_aspect("equal"), ax.set_xticks([]), ax.set_yticks([])
    legal = set(rec["scene"]["legal_cells"])
    for c in range(64):
        x, y = (c % 8) * 0.08, (c // 8) * 0.08
        ax.add_patch(mp.Rectangle((x, y), 0.08, 0.08, fc="white" if c in legal else "#eeeeee", ec="#dddddd", lw=0.6))
    g = rec["goal_cell"]
    ax.add_patch(mp.Rectangle(((g % 8) * 0.08 + 0.006, (g // 8) * 0.08 + 0.006), 0.068, 0.068, fc="none", ec=INK, lw=1.4, ls="--"))
    for o in rec["scene"]["objects"]:
        x, y = o["xy_m"]
        fixed = o["id"] in rec["fixed_ids"]
        ax.add_patch(mp.Circle((x, y), 0.024, fc=INK if o["kind"] == "target" else (GREY if fixed else "white"), ec=INK, lw=1.2))
        ax.text(x, y, "T" if o["kind"] == "target" else o["id"], ha="center", va="center", fontsize=7, color="white" if o["kind"] == "target" else INK)
    ax.set_title(title, fontsize=8.5)


def _xy(c):
    return ((c % 8) + 0.5) * 0.08, ((c // 8) + 0.5) * 0.08


def figures() -> list:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIG.mkdir(parents=True, exist_ok=True)
    out = []
    # 1. one-action goal blockage: every member destination of A, coloured by the sound terminal screen
    rec = S.toy({"A": 29, "B": 21}, {"W": 37}, target=27, goal=29)
    D = S.domain(rec)
    fig, axs = plt.subplots(1, 2, figsize=(8.4, 4.6))
    for ax, o in zip(axs, ("A", "B")):
        _board(ax, rec, f"all {S.free0(D)} one-action members moving {o}\n(T at 27, dashed = goal 29, grey = fixed W)")
        for s in S.walk(D, 1):
            if len(s) == 1 and s[0][0] == o:
                x, y = _xy(s[0][1])
                ax.plot(x, y, "o", ms=4, color=ORANGE if S.goal_blocked(D, s) else BLUE)
    fig.suptitle("Toy 1 - goal blockage: moving A anywhere clears the goal; moving B never does (both are enumerated)", fontsize=9.5)
    fig.text(0.5, 0.02, "blue: member, goal clear after the edit;  orange: member, goal still blocked (success 0 by the sound F1 rule, kept as a negative)",
             ha="center", fontsize=7.5)
    out.append(_save(fig, "01_toy_one_action_goal_blockage.png"))
    # 2. two-action order contrast: vacated-cell dependency and shared endpoint
    rec = S.toy({"A": 28, "B": 36}, {"W": 20}, target=27, goal=29)
    D = S.domain(rec)
    fig, axs = plt.subplots(1, 3, figsize=(11, 4.6))
    cases = [((("B", 37), ("A", 36)), "member: (1) B 36->37, then (2) A 28->36\n(A uses the cell B vacated)"),
             ((("A", 36), ("B", 37)), "OUT OF DOMAIN: (1) A 28->36 first\n(36 still occupied by B: DEST_OCCUPIED)"),
             ((("A", 5), ("B", 6)), "permutation pair: (A->5, B->6) and (B->6, A->5)\nsame Y node, two X nodes")]
    for ax, (s, t) in zip(axs, cases):
        _board(ax, rec, t)
        ok = S.classify(D, s) is None
        for j, (o, d) in enumerate(s):
            src = _xy(D["cells0"][o])
            ax.annotate("", xy=_xy(d), xytext=src, arrowprops=dict(arrowstyle="->", color=BLUE if ok else ORANGE, lw=1.8))
            ax.text(*np.add(_xy(d), (0.018, 0.018)), str(j + 1), fontsize=8, color=BLUE if ok else ORANGE)
    fig.suptitle("Toy 2 - order: the grammar decides membership per step; permutations with one endpoint share Y and keep separate X", fontsize=9.5)
    fig.text(0.5, 0.02, f"right panel - Y node: {S.ysig(D, cases[2][0])};  X nodes: {S.xsig(cases[2][0])}  and  {S.xsig(cases[2][0][::-1])}", ha="center", fontsize=7.5)
    out.append(_save(fig, "02_toy_two_action_order_contrast.png"))
    # 3. four-action closure (SCHEMATIC: no recorded witness)
    rec = S.toy({"A": 26, "B": 19, "C": 35, "E": 28}, {"W1": 18, "W2": 34, "W3": 20, "W4": 36}, target=27, goal=31)
    D = S.domain(rec)
    seq = (("E", 47), ("C", 43), ("B", 11), ("A", 25))
    fig, ax = plt.subplots(figsize=(5.2, 5.4))
    _board(ax, rec, "Toy 3 - SCHEMATIC four-action closure (no robot motion, no witness)\nT enclosed by 4 movable discs + 4 fixed walls")
    for j, (o, d) in enumerate(seq):
        ax.annotate("", xy=_xy(d), xytext=_xy(D["cells0"][o]), arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.8))
        ax.text(*np.add(_xy(d), (0.018, 0.018)), str(j + 1), fontsize=9, color=BLUE)
    n = S.count(D, 4)
    fig.text(0.5, 0.02, f"one of {sum(n.values()):,} members (K<=4; m=4: {n[4]:,}); {S.count_endpoints(D, 4)[4]:,} distinct 4-move endpoints",
             ha="center", fontsize=7.5)
    out.append(_save(fig, "03_toy_four_action_closure_SCHEMATIC.png"))
    # 4. domain size vs historical catalogue on every development root
    C = json.loads((OUT / "FULLSPACE_COUNTS_P26.json").read_text())["roots"]
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    ks = sorted(C, key=lambda k: C[k]["total"])
    x = np.arange(len(ks))
    for m, col, lab in ((1, "#9bbbe0", "m = 1"), (2, "#5a92c8", "m <= 2"), (3, BLUE, "m <= 3"), (4, INK, "m <= 4")):
        ax.plot(x, [sum(C[k]["sequences"][str(i)] for i in range(m + 1)) for k in ks], color=col, lw=1.6, label=f"universal domain, {lab}")
    ax.plot(x, [C[k]["catalogue"] for k in ks], color=ORANGE, lw=1.6, label="historical P16/P20 catalogue")
    ax.set_yscale("log"), ax.set_xlabel(f"development roots (n = {len(ks)}, sorted by domain size)"), ax.set_ylabel("ordered sequences")
    ax.legend(fontsize=7.5, frameon=False), ax.grid(alpha=0.25, lw=0.5)
    ax.set_title("Exact universal-domain size (closed form, verified by brute force on toys) vs the old catalogue", fontsize=9)
    out.append(_save(fig, "04_domain_size_vs_catalogue.png"))
    return out


def _save(fig, name) -> str:
    import matplotlib.pyplot as plt
    p = FIG / name
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return str(p)


if __name__ == "__main__":
    print(json.dumps(counts() if sys.argv[1] == "counts" else figures(), indent=1))
