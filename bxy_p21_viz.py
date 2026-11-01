"""BXY-P21 figures: success / unnecessary-repair frontier (OB, K34, P-min), pre-declared contrasts, K1..K4 strata with n, K3/K4 hypotheses,
strict order on K34, and a 2D gallery of held-out K4 roots (each arm's out-of-fold choice vs the verified repair; teacher truth labelled)."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import bxy_data as bd  # noqa: E402
import bxy_p17_eval as E  # noqa: E402
import bxy_p17_viz as V17  # noqa: E402
import bxy_p20_k34 as Z  # noqa: E402
import bxy_p21_eval as E2  # noqa: E402
import bxy_p21_k34 as H  # noqa: E402
import bxy_pmin_sidecar as S  # noqa: E402
import bxy_teacher as TT  # noqa: E402
from bxy_p11_viz import _arrows  # noqa: E402
from bxy_p12_viz import _clean  # noqa: E402
from bxy_p14_run import _swap  # noqa: E402
from bxy_pmin_viz import _panel  # noqa: E402

FIG = Path("visualizations/approach_b/bxy_p21_v1")
AC, SHORT = V17.AC, V17.SHORT


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    p = FIG / name
    fig.savefig(p, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return str(p)


def fig_frontier(ev):
    fig, ax = plt.subplots(1, 3, figsize=(19, 5.4))
    for a_, pop in zip(ax, ("OB", "K34", "PMIN")):
        for arm, s in ev["arms"][pop].items():
            r = s["RULE"]
            if r["succ_inf"] is not None:
                a_.scatter(r["unnecessary"], r["succ_inf"], s=70, color=AC[arm], edgecolor="#222", lw=0.5, label=SHORT[arm])
                if s.get("succ_avail") is not None:
                    a_.scatter(r["unnecessary"], s["succ_avail"], s=40, marker="^", color=AC[arm], edgecolor="#222", lw=0.4)
        for nm, r in ev["references"][pop].items():
            if r["succ_inf"] is not None:
                x = r["unnecessary"] if r["unnecessary"] is not None else 0.0
                a_.scatter(x, r["succ_inf"], marker="x", color="#222", s=40)
                a_.annotate(nm.replace("_", " ").lower(), (x, r["succ_inf"]), fontsize=7, color="#777", xytext=(4, -3), textcoords="offset points")
        a_.set(xlabel="unnecessary repairs (initially feasible roots)", ylabel="repair success (o unconditional, ^ availability-conditioned)",
               title=f"{pop}: {ev['infeasible'][pop]} infeasible, {ev['available'][pop]} with a verified repair")
        _clean(a_)
    ax[0].legend(fontsize=7, frameon=False)
    fig.tight_layout()
    return _save(fig, "01_frontier.png")


def fig_strata(ev):
    fig, ax = plt.subplots(1, 2, figsize=(15, 4.6))
    for a_, pop in zip(ax, ("OB", "K34")):
        st = ev["strata"][pop]
        arms = list(st)
        for j, arm in enumerate(arms):
            v = [st[arm][f"K{K}"]["success"] or 0 for K in (1, 2, 3, 4)]
            a_.bar(np.arange(4) + (j - 2.5) * 0.13, v, 0.13, color=AC[arm], label=SHORT[arm])
        n = [st[arms[0]][f"K{K}"]["n"] for K in (1, 2, 3, 4)]
        a_.set_xticks(range(4), [f"K{K} (n = {nn}){' descriptive' if K == 4 else ' exploratory' if K == 3 else ''}" for K, nn in zip((1, 2, 3, 4), n)], fontsize=8)
        a_.set(ylim=(0, 1), ylabel="repair success (verified-K stratum, OOF seed mean)", title=f"{pop}: success by verified K")
        _clean(a_)
    ax[0].legend(fontsize=7, frameon=False, ncol=2)
    fig.tight_layout()
    return _save(fig, "02_success_by_K.png")


def fig_hypotheses(ev):
    hs = ev["hypotheses_K34"]
    fig, ax = plt.subplots(1, 2, figsize=(13, 3.6), sharey=True)
    for a_, key, t, lim in ((ax[0], "success_repairable_K34", "Δ success, repairable K3/K4 roots", 0.10), (ax[1], "unnecessary_OB", "Δ unnecessary repairs, OB feasible", 0.05)):
        for i, (h, v) in enumerate(hs.items()):
            r = v[key]
            if r["diff"] is None:
                continue
            a_.plot(r["ci99"], [i, i], color="#bbb", lw=1)
            a_.plot(r["ci95"], [i, i], color="#2a78d6", lw=3)
            a_.scatter(r["diff"], i, color="#222", s=18, zorder=3)
            a_.text(r["ci95"][1] + 0.01, i, f"n = {r['n']}", fontsize=7, va="center")
        a_.axvline(0, color="#222", lw=0.6)
        a_.axvline(lim, color="#1baf7a" if lim == 0.10 else "#b4441c", ls="--", lw=0.8)
        a_.set_title(t + " (EXPLORATORY)", fontsize=9)
        _clean(a_)
    ax[0].set_yticks(range(len(hs)), list(hs), fontsize=8)
    fig.tight_layout()
    return _save(fig, "03_k34_hypotheses.png")


def fig_order(ev):
    so = ev["strict_order_K34"]
    arms = list(so)
    fig, ax = plt.subplots(figsize=(9, 4))
    for j, sub in enumerate(("all", "certified")):
        ax.bar(np.arange(len(arms)) + (j - 0.5) * 0.38, [so[a][sub]["concordance"] or 0 for a in arms], 0.38, color=[AC[a] for a in arms], alpha=1 - 0.45 * j,
               edgecolor="#222", lw=0.3)
    ax.axhline(0.5, color="#222", ls=":", lw=0.6)
    ax.set_xticks(range(len(arms)), [a.split(":")[0] for a in arms])
    n = so[arms[0]]
    ax.set(ylim=(0, 1), title=f"strict same-endpoint permutation order on K34 roots (solid all, faded certified); "
           f"{n['all']['pairs_x_seeds']} / {n['certified']['pairs_x_seeds']} pair x seeds, {n['roots']} roots")
    _clean(ax)
    return _save(fig, "04_strict_order_K34.png")


def fig_k4_gallery(C, T):
    """Held-out verified K4 roots: D's and DIRECT's out-of-fold choices (seed 0) and the shortest verified repair (teacher truth)."""
    E_ = TT.env()
    ks = sorted(k for k, (sv, lab, ev) in C["by"].items() if ev["corpus"] == "K34" and ev["verified_K"] == 4)[:4]
    if not ks:
        return None
    R = {}
    for w in Z.WAVES:
        R.update(Z.roots_of(w))
    fig, ax = plt.subplots(len(ks), 3, figsize=(17, 5.4 * len(ks)), constrained_layout=True, squeeze=False)
    sig_seq = lambda s: [] if s == "empty" else [(a.split(">")[0], int(a.split(">")[1])) for a in s.split(".")]  # noqa: E731
    for row, k in zip(ax, ks):
        sv, lab, ev = C["by"][k]
        rec = R[k]
        c0 = bd.cells0(rec)
        for a_, arm in zip(row[:2], ("D:XYQ-GEO-SYM", "A:DIRECT-GEO")):
            pr, d = C["oof"][(arm, 0)].get(k), T[(arm, 0)].get(k)
            if pr is None or d is None:
                a_.axis("off")
                continue
            i = d["RULE"]["chosen"]
            sig = pr["cands"][i]["sig"] if i is not None else None
            seq = sig_seq(sig) if sig else []
            with _swap(S, "OUT", Z.wdir(ev["wave"])):
                _panel(a_, E_, k, rec, c0, f"{SHORT[arm]} chooses {sig or 'ABSTAIN'} (m = {len(seq)}), p = {pr['cands'][i]['p']:.2f}" if i is not None else f"{SHORT[arm]}: abstain",
                       q=TT.qref(rec), note=f"teacher truth: success = {ev['cands'][i]['success'] if i is not None else '-'} (X {ev['cands'][i]['x'] if i is not None else '-'}, "
                       f"Y {ev['cands'][i]['y'] if i is not None else '-'}); held-out fold model")
            if seq:
                _arrows(a_, rec, seq)
        okj = [j for j, c in enumerate(ev["cands"]) if c["success"] == 1]
        j = min(okj, key=lambda j: (sv["cands"][j]["m"], sv["cands"][j]["sig"]))
        seq = sig_seq(sv["cands"][j]["sig"])
        with Z.p16_paths():
            import bxy_p16 as G
            res = G.results(ev["wave"], k)
        xr, yr = res.get(TT.xkey(k, rec, seq), {}), res.get(TT.ykey(k, rec, seq), {})
        with _swap(S, "OUT", Z.wdir(ev["wave"])):
            _panel(row[2], E_, k, rec, {**c0, **dict(seq)}, f"verified K4 repair {sv['cands'][j]['sig']} (certified necessary)", x=xr if xr.get("y") == 1 else None,
                   ywit=yr.get("target_witness"), note="replayed witnesses: relocations blue, connector pink, target green")
    fig.suptitle("Held-out K4 roots (descriptive, n = 7 in total): out-of-fold choices of D and DIRECT-GEO vs the verified, certified-necessary repair", x=0.01, ha="left")
    return _save(fig, "05_k4_heldout_gallery.png")


def all_figures():
    ev = json.loads((H.OUT / "EVALUATION_P21.json").read_text())
    C = E2.context()
    T = E.tables(C, E.rules(C))
    out = [fig_frontier(ev), fig_strata(ev), fig_hypotheses(ev), fig_order(ev), fig_k4_gallery(C, T)]
    V17.FIG = FIG
    out += [V17.fig_contrasts(ev), V17.fig_representation(dict(ev, arms={"OB": ev["arms"]["OB"], "PMIN": ev["arms"]["PMIN"]})), V17.fig_calibration(T, C),
            V17.fig_categories(ev), V17.fig_travel(T, C)]
    return [o for o in out if o]


if __name__ == "__main__":
    print("\n".join(all_figures()))
