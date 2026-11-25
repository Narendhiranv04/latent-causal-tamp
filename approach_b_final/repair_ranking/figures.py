#!/usr/bin/env python3
"""Compact matplotlib figures for every phase (reads committed JSON / private per-candidate tables; writes reports/figures/*.png).
    python figures.py p0|p1|p2|p4|p5|p6"""
from __future__ import annotations

import json, sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import rr

FIG = rr.REP / "figures"
TIERS = ["T4", "T56", "R7_12", "TAIL"]
INK, MUTED, BLUE, ORANGE, GREEN, RED = "#1f2328", "#6e7781", "#2f6fdf", "#e07b00", "#1a7f37", "#cf222e"


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / name, dpi=150, bbox_inches="tight", facecolor="white"); plt.close(fig)


def p0():
    T = json.loads((rr.REP / "P0_TRAIN_COVERAGE.json").read_text())
    kt = T["X_labels_by_kind_and_max_tier"]
    kinds = sorted({k.split("|")[0] for k in kt}, key=lambda k: -sum(v for kk, v in kt.items() if kk.startswith(k + "|")))
    M = np.array([[kt.get(f"{k}|{t}", 0) for t in TIERS] for k in kinds], float)
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8), gridspec_kw={"width_ratios": [1.5, 1]})
    im = ax[0].imshow(np.log10(M + 1), cmap="Blues", aspect="auto")
    for i in range(len(kinds)):
        for j in range(len(TIERS)):
            ax[0].text(j, i, f"{int(M[i, j]):,}", ha="center", va="center", fontsize=8, color="white" if M[i, j] > 1500 else INK)
    ax[0].set_xticks(range(len(TIERS)), ["ranks 1-4", "5-6", "7-12", ">12"]); ax[0].set_yticks(range(len(kinds)), [k.lower() for k in kinds], fontsize=8)
    ax[0].set_xlabel("worst frozen-cVAE destination rank in the labelled sequence"); ax[0].set_title("TRAIN X labels by intervention kind (count)", fontsize=10)
    sh = T["label_share_vs_support_by_max_tier"]
    x = np.arange(len(TIERS))
    ax[1].bar(x - 0.2, [sh[t]["share_labels"] for t in TIERS], 0.38, color=BLUE, label="share of TRAIN X labels (by worst rank)")
    ax[1].bar(x + 0.2, [sh[t]["share_legal_actions"] for t in TIERS], 0.38, color=MUTED, label="share of legal actions")
    ax[1].set_xticks(x, ["1-4", "5-6", "7-12", ">12"]); ax[1].set_ylabel("share"); ax[1].legend(fontsize=7, frameon=False)
    ax[1].set_title("label support vs legal support", fontsize=10)
    for a in ax[1:]:
        a.spines[["top", "right"]].set_visible(False)
    fig.suptitle(f"P0: original TRAIN snapshot (3,500 roots, {sum(M.ravel()):,.0f} finalized X labels); not physical truth of the full domain", fontsize=9, color=MUTED)
    _save(fig, "p0_train_rank_support.png")



def _rel(ax, y, p, label, color, bins=10):
    y, p = np.asarray(y, float), np.asarray(p, float)
    e = np.linspace(0, 1, bins + 1); k = np.clip(np.digitize(p, e) - 1, 0, bins - 1)
    xs = [p[k == b].mean() for b in range(bins) if (k == b).sum() >= 15]; ys = [y[k == b].mean() for b in range(bins) if (k == b).sum() >= 15]
    ax.plot(xs, ys, "o-", color=color, lw=2, ms=5, label=label)


def p1():
    import pickle
    import search as S
    sys.path.insert(0, str(rr.ABF / "full_domain_sets"))
    import domain as DM
    from figs import scene
    roots = pickle.loads((rr.PRIV / "p1_val_table.pkl").read_bytes()); tr = pickle.loads((rr.PRIV / "p1_train_table.pkl").read_bytes())
    K12 = [r for r in roots if r["K"] in ("1", "2")]
    # (a) reliability by factor and tier
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.9))
    ys, ps, xs, p1s, y11, p11, tt = [], [], [], [], [], [], []
    for r in K12:
        sc = r["sc"]["s0"]
        for i, v in r["known"].items():
            if v["y"] is not None:
                ys.append(v["y"]); ps.append(sc["py"][i])
            if v["y"] == 1 and v["x"] is not None:
                xs.append(v["x"]); p1s.append(sc["px1"][i])
            if v["z"] is not None:
                y11.append(v["z"]); p11.append(sc["p11"][i]); tt.append(r["info"][i]["max_tier"])
    trL = [c for c in tr if len(c["seq"]) <= 2 and c["z"] is not None]
    _rel(ax[0], ys, ps, "pY vs Y (VAL)", BLUE); _rel(ax[0], xs, p1s, "pX1 vs X | Y=1 (VAL)", ORANGE)
    _rel(ax[0], [c["z"] for c in trL], [c["p11"] for c in trL], "p11 vs Z (TRAIN, in-sample)", MUTED)
    ax[0].set_title("factor reliability, K1/K2 labelled candidates", fontsize=9)
    y11, p11, tt = np.array(y11), np.array(p11), np.array(tt)
    for t, c in zip(TIERS, [BLUE, GREEN, ORANGE, RED]):
        m = tt == t
        _rel(ax[1], y11[m], p11[m], f"{t} (n={m.sum()})", c, bins=6)
    ax[1].set_title("p11 vs verified Z by worst destination rank (VAL)", fontsize=9)
    for a in ax[:2]:
        a.plot([0, 1], [0, 1], ":", color=MUTED, lw=1); a.set_xlabel("predicted"); a.set_ylabel("observed rate"); a.legend(fontsize=7, frameon=False)
        a.spines[["top", "right"]].set_visible(False)
    R = json.loads((rr.REP / "P1_RANKING.json").read_text())["VAL"]
    names = [("frozen_p11_s0", "p11 (frozen)"), ("pY_only", "pY only"), ("pX1_only", "pX1 only"), ("cvae_prior_only_control", "cVAE prior only"), ("random_control", "random")]
    v = [R[k]["concordance"] for k, _ in names]
    ax[2].barh(range(len(v)), [x[0] for x in v], xerr=[[x[0] - x[1] for x in v], [x[2] - x[0] for x in v]], color=[BLUE, BLUE, ORANGE, MUTED, MUTED], height=0.6)
    ax[2].axvline(0.5, ls=":", color=MUTED); ax[2].set_yticks(range(len(v)), [n for _, n in names], fontsize=8); ax[2].invert_yaxis()
    ax[2].set_xlabel("within-root concordance Z+ vs Z- (root-macro, 95% family CI)"); ax[2].set_title(f"ranking known candidates ({R['frozen_p11_s0']['roots']} K1/K2 roots)", fontsize=9)
    ax[2].spines[["top", "right"]].set_visible(False)
    fig.suptitle("P1: exact-contract labels on exposed VAL (development evidence); labelled candidates are selection-biased (picked by earlier methods)", fontsize=8.5, color=MUTED)
    _save(fig, "p1_calibration_ranking.png")
    # (b) tier-pair concordance heatmap
    tp = R["frozen_p11_s0"]["by_tier_pair"]
    M = np.full((4, 4), np.nan); N = np.zeros((4, 4), int)
    for k, d in tp.items():
        a, b = k.split("|"); i, j = TIERS.index(a[4:]), TIERS.index(b[4:]); M[i, j] = d["root_macro_conc"]; N[i, j] = d["pairs"]
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    ax.imshow(M, cmap="RdBu", vmin=0, vmax=1)
    for i in range(4):
        for j in range(4):
            if not np.isnan(M[i, j]):
                ax.text(j, i, f"{M[i, j]:.2f}\n({N[i, j]})", ha="center", va="center", fontsize=8, color=INK)
    ax.set_xticks(range(4), ["1-4", "5-6", "7-12", ">12"]); ax.set_yticks(range(4), ["1-4", "5-6", "7-12", ">12"])
    ax.set_xlabel("worst rank of the verified FAILURE"); ax.set_ylabel("worst rank of the verified SUCCESS")
    ax.set_title("P(p11 success > p11 failure), same root\n(blue = correct order; cells with >= 20 pairs)", fontsize=9)
    _save(fig, "p1_tier_pair_concordance.png")
    # (c) four real scenes
    per = {r["root_id"]: r for r in rr.jl(rr.FDS_REP / "P3_PHYSICAL_PER_ROOT.jsonl")}
    pub = {r["root_id"]: r for r in rr.public_val()}
    T = {r["root_id"]: r for r in roots}
    order = sorted(per, key=lambda r: rr.hx("XYRR_FIG|", r))
    pick = {}
    for rid in order:
        e4, ef, ms = per[rid]["EXACT4@None"], per[rid]["EXACT_FULL@None"], per[rid]["PW_MCTS_SEEDED4@1024"]
        if per[rid]["K"] not in ("1", "2"):
            continue
        if e4["strict"] == "FAIL_X":
            pick.setdefault("EXACT4 FAIL_X (Y verified, execution failed)", (rid, e4))
        if e4["strict"] == "FAIL_Y":
            pick.setdefault("EXACT4 FAIL_Y (endpoint does not restore task)", (rid, e4))
        if ms["strict"] == "SUCCESS" and "OFF4" in (ms.get("pick_stratum") or "") and e4["strict"] != "SUCCESS":
            pick.setdefault("off-top-4 rescue (seeded MCTS) where EXACT4 failed", (rid, ms))
        if ef["strict"] in ("FAIL_X", "FAIL_Y") and "OFF4" in (ef.get("pick_stratum") or "") and e4["strict"] == "SUCCESS":
            pick.setdefault("off-top-4 harmful replacement (EXACT_FULL) where EXACT4 succeeded", (rid, ef))
    fig, axs = plt.subplots(1, 4, figsize=(20, 5.6))
    samp, _, _ = rr.bundle()
    cv = rr.cvae_table(list(pub.values()), samp, "val")
    for ax, (title, (rid, e)) in zip(axs, pick.items()):
        row = pub[rid]; dom = DM.Domain(cv[rid]["raw"], cv[rid]["D6"], 0.25)
        seq = e["seq"] or []
        x = rr.readout(rr.load_net(rr.scorer_path(0)), [(row, [seq])])[0]["rows"][0] if seq else {}
        rk = [dom.rank.get((o, d), -1) + 1 for o, d in seq]
        scene(ax, row, dom, obj=seq[0][0] if seq else None, arrows=[(o, d, BLUE if i == 0 else ORANGE) for i, (o, d) in enumerate(seq)],
              title=f"{title}\nK{per[rid]['K']}  verified: {e['strict']}  ranks {rk}\np11 {x.get('p11', 0):.2f}  pY {x.get('py', 0):.2f}  pX1 {x.get('px1', 0):.2f}")
    fig.suptitle("P1 real VAL scenes (public inputs; outcome = exact-contract teacher). Rings: top-4 (solid) / ranks 5-6 (dashed) of the first moved object; heat = frozen cVAE prior; green square = goal; red = target",
                 fontsize=8.5, color=MUTED)
    _save(fig, "p1_real_scenes.png")
    return {k: v[0] for k, v in pick.items()}



def p2():
    R = json.loads((rr.REP / "P2_RESULTS.json").read_text()); ch = R["selection"]["family_choices"]
    rules = [f"{f}@{ch[f]}" for f in ("F2", "F3a", "F3b", "F5")]
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
    for k, (part, col) in enumerate((("DEV_CAL", BLUE), ("DEV_AUDIT", ORANGE))):
        v = [R[part][r]["paired_conc_delta_vs_F0"] for r in rules]
        y = np.arange(len(rules)) + (k - 0.5) * 0.35
        ax[0].errorbar([x[0] for x in v], y, xerr=[[x[0] - x[1] for x in v], [x[2] - x[0] for x in v]], fmt="o", color=col, label=f"{part} (n={R[part]['F0']['roots']} roots)", capsize=3)
    ax[0].axvline(0, ls=":", color=MUTED); ax[0].set_yticks(range(len(rules)), rules); ax[0].invert_yaxis(); ax[0].legend(fontsize=7, frameon=False)
    ax[0].set_xlabel("paired within-root concordance change vs F0 (95% family CI)"); ax[0].set_title("rules tuned on DEV_CAL; DEV_AUDIT evaluated once", fontsize=9)
    e = R["DEV_CAL_end_to_end"]; a = R["DEV_AUDIT_end_to_end"]
    names = ["F0"] + [r for r in rules if r in e]
    for k, (src, col, part) in enumerate(((e, BLUE, "DEV_CAL"), (a, ORANGE, "DEV_AUDIT"))):
        vals = [src[n]["d12"]["decided_success_rate"] for n in names]; un = [src[n]["d12"]["unresolved"] for n in names]
        x = np.arange(len(names)) + (k - 0.5) * 0.38
        ax[1].bar(x, vals, 0.36, color=col, label=part)
        for xi, v_, u in zip(x, vals, un):
            ax[1].text(xi, v_ + 0.01, f"{u} unres.", ha="center", fontsize=6.5, color=MUTED, rotation=90)
    ax[1].set_xticks(range(len(names)), names, fontsize=8); ax[1].set_ylim(0.5, 1.0); ax[1].set_ylabel("decided success rate (cached labels)")
    ax[1].set_title("EXACT12 pool end-to-end (unresolved picks excluded; not paired)", fontsize=9); ax[1].legend(fontsize=7, frameon=False)
    for a_ in ax:
        a_.spines[["top", "right"]].set_visible(False)
    fig.suptitle("P2: frozen-scorer inference rules (exact-contract labels, exposed VAL; development evidence)", fontsize=8.5, color=MUTED)
    _save(fig, "p2_rules_cal_vs_audit.png")


if __name__ == "__main__":
    globals()[sys.argv[1]]()
