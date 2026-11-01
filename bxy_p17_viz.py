"""BXY-P17 figures: selection frontier vs references, paired contrasts, edit sign by transition, discrimination / calibration, order and
omission metrics, failure categories, K strata, travel on matched successes, and 2D galleries (learned probabilities vs teacher truth on
real development scenes; motion drawn only from recorded, replayed witnesses)."""
from __future__ import annotations

import collections
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import bxy_data as bd  # noqa: E402
import bxy_p11 as P  # noqa: E402
import bxy_p16 as G  # noqa: E402
import bxy_p17 as M  # noqa: E402
import bxy_p17_eval as E  # noqa: E402
import bxy_pmin_sidecar as S  # noqa: E402
import bxy_teacher as TT  # noqa: E402
from bxy_p11_viz import _arrows  # noqa: E402
from bxy_p12_viz import _clean  # noqa: E402
from bxy_p14_run import _swap  # noqa: E402
from bxy_pmin_viz import _panel  # noqa: E402

FIG = Path("visualizations/approach_b/bxy_p17_v1")
INK, MUTED = "#222", "#777"
AC = {"A:DIRECT-GEO": "#7d3c98", "B:XYQ-BASE": "#9e9e9e", "C:XYQ-GEO-CON": "#f2a33a", "D:XYQ-GEO-SYM": "#2a78d6", "E:XY-UNC-SA-GEO-SYM": "#1baf7a",
      "G:XYQ-GEO-SYM-ORDINV": "#b4441c"}
SHORT = {a: a.split(":")[0] + " " + a.split(":")[1] for a in AC}


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    p = FIG / name
    fig.savefig(p, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return str(p)


def fig_frontier(ev):
    fig, ax = plt.subplots(1, 3, figsize=(19, 5.4))
    for a_, pop in zip(ax, ("OB", "V21", "PMIN")):
        A_ = ev["arms"][pop]
        for arm, s in A_.items():
            for nm, mk in (("RULE", "o"), ("PRIMARY", "s"), ("TRAVEL_BLIND", "^")):
                r = s[nm]
                if r["succ_inf"] is None:
                    continue
                a_.scatter(r["unnecessary"], r["succ_inf"], marker=mk, s=70 if nm == "RULE" else 35, color=AC[arm], edgecolor=INK, lw=0.5,
                           label=SHORT[arm] if nm == "RULE" else None, zorder=3)
        for nm, r in ev["references"][pop].items():
            if r["succ_inf"] is None:
                continue
            x = r["unnecessary"] if r["unnecessary"] is not None else 0.0
            a_.scatter(x, r["succ_inf"], marker="x", color=INK, s=40, zorder=2)
            a_.annotate(nm.replace("_", " ").lower(), (x, r["succ_inf"]), fontsize=7, color=MUTED, xytext=(4, -3), textcoords="offset points")
        a_.set(xlabel="unnecessary repairs on initially feasible roots", ylabel="verified corrective success on infeasible roots",
               title=f"{pop}: {ev['infeasible'][pop]} infeasible ({ev['repairable'][pop]} with a verified repair) / {ev['roots'][pop]} roots")
        _clean(a_)
    ax[0].legend(fontsize=7.5, frameon=False, loc="upper right", title="o inner rule  s P11.1 rule  ^ travel-blind", title_fontsize=7)
    fig.tight_layout()
    return _save(fig, "01_selection_frontier.png")


def fig_contrasts(ev):
    C = ev["contrasts"]["OB"]
    mets = [("succ_inf", "Δ corrective success (infeasible)"), ("unnecessary", "Δ unnecessary repairs (feasible)"), ("joint_nll", "Δ root joint NLL (lower = better)"),
            ("order", "Δ order concordance"), ("edit_10", "Δ harmful-edit (1→0) sign accuracy")]
    fig, ax = plt.subplots(1, len(mets), figsize=(4.0 * len(mets), 3.8), sharey=True)
    names = list(C)
    for a_, (m, t) in zip(ax, mets):
        for i, c in enumerate(names):
            r = C[c][m]
            if r["diff"] is None:
                continue
            a_.plot(r["ci99"], [i, i], color="#bbb", lw=1)
            a_.plot(r["ci95"], [i, i], color="#2a78d6", lw=3)
            a_.scatter(r["diff"], i, color=INK, s=18, zorder=3)
        a_.axvline(0, color=INK, lw=0.6)
        if m == "succ_inf":
            a_.axvline(0.10, color="#1baf7a", ls="--", lw=0.8)
        if m == "unnecessary":
            a_.axvline(0.05, color="#b4441c", ls="--", lw=0.8)
        a_.set_title(t, fontsize=8)
        _clean(a_)
    ax[0].set_yticks(range(len(names)), [c.replace("_", " ") for c in names], fontsize=8)
    fig.suptitle("Pre-declared paired family-bootstrap contrasts on the outcome-blind population (95% blue, Bonferroni 99% grey)", x=0.01, ha="left", fontsize=9)
    fig.tight_layout()
    return _save(fig, "02_paired_contrasts.png")


def fig_representation(ev):
    fig, ax = plt.subplots(1, 4, figsize=(20, 4.4))
    arms = list(ev["arms"]["OB"])
    w = 0.38
    for j, pop in enumerate(("OB", "PMIN")):
        A_ = ev["arms"][pop]
        x = np.arange(len(arms)) + (j - 0.5) * w
        ax[0].bar(x, [A_[a]["RULE"]["edit_01"] or 0 for a in arms], w, color=[AC[a] for a in arms], alpha=1 - 0.45 * j, edgecolor=INK, lw=0.3)
        ax[1].bar(x, [A_[a]["RULE"]["edit_10"] or 0 for a in arms], w, color=[AC[a] for a in arms], alpha=1 - 0.45 * j, edgecolor=INK, lw=0.3)
        ax[2].bar(x, [A_[a]["RULE"]["auc_y"] or 0 for a in arms], w, color=[AC[a] for a in arms], alpha=1 - 0.45 * j, edgecolor=INK, lw=0.3)
        ax[3].bar(x, [A_[a]["y0_auroc"] or 0 for a in arms], w, color=[AC[a] for a in arms], alpha=1 - 0.45 * j, edgecolor=INK, lw=0.3)
    for a_, t in zip(ax, ("edit sign accuracy, helpful (Y0 = 0 -> Y_edit = 1)", "edit sign accuracy, harmful (Y0 = 1 -> Y_edit = 0)",
                         "within-root edited-Y AUROC", "Y0 AUROC (no-op feasibility)")):
        a_.axhline(0.5, color=INK, lw=0.6, ls=":")
        a_.set_xticks(range(len(arms)), [a.split(":")[0] for a in arms])
        a_.set(ylim=(0, 1), title=t + "\n(solid = outcome-blind, faded = P-min)")
        _clean(a_)
    fig.tight_layout()
    return _save(fig, "03_representation.png")


def fig_calibration(T, C):
    fig, ax = plt.subplots(1, 2, figsize=(12, 5))
    for arm in AC:
        for a_, side in zip(ax, ("y", "s")):
            it = [(y, p) for (a, _), t in T.items() if a == arm for k, d in t.items() if C["corpus"][k] in E.POP["OB"] for y, p in d["items"][side]]
            if not it:
                continue
            y, p = np.array([i[0] for i in it]), np.array([i[1] for i in it])
            bins = np.linspace(0, 1, 11)
            idx = np.clip(np.digitize(p, bins) - 1, 0, 9)
            xs = [p[idx == b].mean() for b in range(10) if (idx == b).sum() >= 5]
            ys = [y[idx == b].mean() for b in range(10) if (idx == b).sum() >= 5]
            a_.plot(xs, ys, "-o", ms=3.5, color=AC[arm], label=SHORT[arm], lw=1.4)
    for a_, t in zip(ax, ("P(Y_s = 1) of observed Y nodes (XY arms)", "p_succ of decided success events")):
        a_.plot([0, 1], [0, 1], color=INK, lw=0.6, ls=":")
        a_.set(xlabel="predicted", ylabel="observed frequency", title=t + " -- outcome-blind roots, out of fold")
        _clean(a_)
    ax[1].legend(fontsize=7.5, frameon=False)
    fig.tight_layout()
    return _save(fig, "04_calibration.png")


def fig_order_omission(ev):
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))
    arms = [a for a in ev["arms"]["OB"] if a != "A:DIRECT-GEO"]
    for a_, m, t in ((ax[0], "order", "order concordance on measured same-endpoint X-discordant pairs"), (ax[1], "omission", "omission sign accuracy (Y_full vs Y_omit)")):
        for j, pop in enumerate(("OB", "PMIN")):
            v = [ev["arms"][pop][a]["RULE"][m] or 0 for a in arms]
            a_.bar(np.arange(len(arms)) + (j - 0.5) * 0.38, v, 0.38, color=[AC[a] for a in arms], alpha=1 - 0.45 * j, edgecolor=INK, lw=0.3)
        a_.axhline(0.5, color=INK, ls=":", lw=0.6)
        a_.set_xticks(range(len(arms)), [a.split(":")[0] for a in arms])
        a_.set(ylim=(0, 1), title=t + "\n(solid outcome-blind, faded P-min; root means)")
        _clean(a_)
    fig.tight_layout()
    return _save(fig, "05_order_and_omission.png")


def fig_categories(ev):
    arms = list(ev["arms"]["OB"])
    cats = sorted({c for a in arms for c in ev["arms"]["OB"][a]["RULE"]["categories"]})
    col = dict(zip(cats, plt.cm.tab20(np.linspace(0, 1, len(cats)))))
    fig, ax = plt.subplots(figsize=(12, 4.8))
    for i, a in enumerate(arms):
        c = ev["arms"]["OB"][a]["RULE"]["categories"]
        n, left = sum(c.values()), 0
        for k in cats:
            v = c.get(k, 0) / n if n else 0
            ax.barh(i, v, left=left, color=col[k], edgecolor="white", label=k if i == 0 else None)
            left += v
    ax.set_yticks(range(len(arms)), [SHORT[a] for a in arms])
    ax.legend(fontsize=7, frameon=False, ncol=3, bbox_to_anchor=(0, -0.12), loc="upper left")
    ax.set(xlabel="fraction of (root, seed) decisions, outcome-blind roots", title="decision categories under each arm's inner rule")
    _clean(ax)
    return _save(fig, "06_decision_categories.png")


def fig_strata(T, C):
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ks = ["1", "2", "3"]
    for j, arm in enumerate(AC):
        v, n = [], []
        for K in ks:
            sm = E.seed_mean(T, arm, lambda d: d["RULE"]["success"] if d["y0"] == 0 else None, lambda k: C["corpus"][k] in E.POP["OB"] and str(C["by"][k][2]["verified_K"]) == K)
            v.append(np.mean(list(sm.values())) if sm else 0)
            n.append(len(sm))
        ax.bar(np.arange(3) + (j - 2.5) * 0.13, v, 0.13, color=AC[arm], label=SHORT[arm])
    ax.set_xticks(range(3), [f"verified K{K} (n = {nn})" for K, nn in zip(ks, n)])
    ax.set(ylabel="corrective success", title="corrective success by verified K (outcome-blind infeasible roots with a verified repair)")
    ax.legend(fontsize=7, frameon=False)
    _clean(ax)
    return _save(fig, "07_success_by_K.png")


def fig_travel(T, C):
    """Witnessed J of successful choices on roots where BOTH compared arms succeeded (matched successes)."""
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    for a_, (x, y) in zip(ax, (("D:XYQ-GEO-SYM", "A:DIRECT-GEO"), ("D:XYQ-GEO-SYM", "B:XYQ-BASE"))):
        jx = E.seed_mean(T, x, lambda d: d["RULE"]["J"] if d["RULE"]["success"] and d["RULE"]["J"] is not None else None, lambda k: True)
        jy = E.seed_mean(T, y, lambda d: d["RULE"]["J"] if d["RULE"]["success"] and d["RULE"]["J"] is not None else None, lambda k: True)
        ks = sorted(set(jx) & set(jy))
        a_.scatter([jy[k] for k in ks], [jx[k] for k in ks], s=18, color=AC[x], edgecolor=INK, lw=0.3)
        lim = max([jx[k] for k in ks] + [jy[k] for k in ks] + [1.0])
        a_.plot([0, lim], [0, lim], color=INK, ls=":", lw=0.6)
        a_.set(xlabel=f"{SHORT[y]}: witnessed J", ylabel=f"{SHORT[x]}: witnessed J", title=f"matched successes (n = {len(ks)} roots, all corpora)")
        _clean(a_)
    fig.tight_layout()
    return _save(fig, "08_travel_matched.png")


def _pred(C, arm, k):
    return C["oof"][(arm, 0)].get(k)


def fig_gallery(T, C):
    """Outcome-blind infeasible roots with a verified repair: the D choice vs the DIRECT choice vs a verified alternative (teacher truth)."""
    E_ = TT.env()
    ks = [k for k, (sv, lab, ev) in C["by"].items() if ev["corpus"] == "V21" and ev["y0"] == 0 and any(c["success"] == 1 for c in ev["cands"])
          and isinstance(ev["verified_K"], int) and ev["verified_K"] >= 2][:4]
    if not ks:
        return None
    fig, ax = plt.subplots(len(ks), 3, figsize=(16, 5.2 * len(ks)), constrained_layout=True, squeeze=False)
    R = {}
    for w in G.WAVES:
        R.update(G.roots_of(w))
    for row, k in zip(ax, ks):
        sv, lab, ev = C["by"][k]
        rec = R[k]
        c0 = bd.cells0(rec)
        sig_seq = lambda s: [] if s == "empty" else [(a.split(">")[0], int(a.split(">")[1])) for a in s.split(".")]  # noqa: E731
        for a_, arm in zip(row[:2], ("D:XYQ-GEO-SYM", "A:DIRECT-GEO")):
            pr = _pred(C, arm, k)
            d = T[(arm, 0)].get(k)
            if pr is None or d is None:
                a_.axis("off")
                continue
            i = d["RULE"]["chosen"]
            sig = pr["cands"][i]["sig"] if i is not None else None
            seq = sig_seq(sig) if sig else []
            with _swap(S, "OUT", G.wdir(ev["wave"])):
                _panel(a_, E_, k, rec, c0, f"{SHORT[arm]} (seed 0) chooses {sig or 'ABSTAIN'}  p = {pr['cands'][i]['p']:.2f}" if i is not None else f"{SHORT[arm]}: abstain",
                       q=TT.qref(rec), note=f"teacher truth for this choice: success = {ev['cands'][i]['success'] if i is not None else '-'} "
                       f"(X {ev['cands'][i]['x'] if i is not None else '-'}, Y {ev['cands'][i]['y'] if i is not None else '-'})")
            if seq:
                _arrows(a_, rec, seq)
        okj = [j for j, c in enumerate(ev["cands"]) if c["success"] == 1]
        j = min(okj, key=lambda j: (sv["cands"][j]["m"], sv["cands"][j]["sig"]))
        seq = sig_seq(sv["cands"][j]["sig"])
        res = G.results(ev["wave"], k)
        xr, yr = res.get(TT.xkey(k, rec, seq), {}), res.get(TT.ykey(k, rec, seq), {})
        pD = _pred(C, "D:XYQ-GEO-SYM", k)
        with _swap(S, "OUT", G.wdir(ev["wave"])):
            _panel(row[2], E_, k, rec, {**c0, **dict(seq)}, f"shortest verified repair {sv['cands'][j]['sig']} (teacher: X = 1, Y = 1)",
                   x=xr if xr.get("y") == 1 else None, ywit=yr.get("target_witness"),
                   note=f"D's p_succ for it = {pD['cands'][j]['p']:.2f}; verified K = {ev['verified_K']}; replayed witnesses" if pD else "")
    fig.suptitle("Development failure / success gallery (out-of-fold predictions; probabilities are learned, success labels are teacher truth)", x=0.01, ha="left")
    return _save(fig, "09_gallery_choices.png")


def fig_order_gallery(C):
    """One measured X-discordant order twin with P(X) from D (order-aware) and G (order-invariant)."""
    E_ = TT.env()
    R = {}
    for w in G.WAVES:
        R.update(G.roots_of(w))
    for k, (sv, lab, ev) in C["by"].items():
        if ev["corpus"] != "V21":
            continue
        for g in ev["order_groups"]:
            if len({u["x"] for u in g["members"]}) == 2 and any(u["negative_kind"] == "CERTIFIED" for u in g["members"]):
                break
        else:
            continue
        break
    else:
        return None
    rec = R[k]
    keys = ev["x_keys"]
    fig, ax = plt.subplots(1, 2, figsize=(12, 5.4), constrained_layout=True)
    pD, pG = _pred(C, "D:XYQ-GEO-SYM", k), _pred(C, "G:XYQ-GEO-SYM-ORDINV", k)
    c0 = bd.cells0(rec)
    for a_, u in zip(ax, g["members"][:2]):
        seq = [(s.split(">")[0], int(s.split(">")[1])) for s in keys[u["xi"]].split(":", 3)[3].split(".")]
        with _swap(S, "OUT", G.wdir(ev["wave"])):
            _panel(a_, E_, k, rec, c0, "order " + " -> ".join(f"{o}@{d}" for o, d in seq), q=TT.qref(rec),
                   note=f"teacher X = {u['x']} ({u['status']}, {u['negative_kind']})\nP(X=1): D order-aware {pD['vars']['px'][u['xi']]:.2f} | G order-invariant {pG['vars']['px'][u['xi']]:.2f}"
                   if pD and pG else f"teacher X = {u['x']}")
        _arrows(a_, rec, seq)
    fig.suptitle(f"{k}: same endpoint (one Y), different measured X -- learned P(X) of the order-aware vs order-invariant F2", x=0.01, ha="left")
    return _save(fig, "10_order_twin_probabilities.png")


def all_figures() -> list:
    ev = json.loads((M.OUT / "EVALUATION_P17.json").read_text())
    C = E.context()
    R_ = E.rules(C)
    T = E.tables(C, R_)
    out = [fig_frontier(ev), fig_contrasts(ev), fig_representation(ev), fig_calibration(T, C), fig_order_omission(ev), fig_categories(ev),
           fig_strata(T, C), fig_travel(T, C), fig_gallery(T, C), fig_order_gallery(C)]
    return [o for o in out if o]


if __name__ == "__main__":
    print("\n".join(all_figures()))
