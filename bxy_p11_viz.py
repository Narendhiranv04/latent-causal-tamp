"""BXY-P11 figures (data and protocol only; no model output is plotted): training-data audit, cross-fit design, a scene-backed example of
the scorer / evaluator separation, and the preregistered roster / budget / capacity."""
from __future__ import annotations

import collections
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import bxy_data as bd  # noqa: E402
import bxy_f1 as F1  # noqa: E402
import bxy_p11 as P  # noqa: E402
import bxy_teacher as T  # noqa: E402
from bxy_p11_prereg import FIG, OUT  # noqa: E402
from bxy_pmin_viz import CAT, INK2, _panel  # noqa: E402

STRATA = ("K0", "K1", "K>=2", "None")
ARM_C = {"XY-quadratic": "#2a78d6", "XY-quadratic-noJ": "#8fb8ea", "XY-uncoupled": "#e87b2e", "XY-uncoupled-SA": "#b4441c", "DIRECT": "#6b5ca5"}


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / name, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return str(FIG / name)


def _clean(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#e4e4e0", lw=0.6)
    ax.set_axisbelow(True)


def fig_audit(V):
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.6), constrained_layout=True)
    for j, sp in enumerate(("train", "val")):
        vs = [v for v in V if v[2]["split"] == sp]
        fe = [sum(v[2]["stratum"] == s and v[2]["y0"] == 1 for v in vs) for s in STRATA]
        inf = [sum(v[2]["stratum"] == s and v[2]["y0"] == 0 for v in vs) for s in STRATA]
        x = np.arange(4) + (j - 0.5) * 0.38
        ax[0].bar(x, fe, 0.36, color="#9fd3bf" if sp == "train" else "#1baf7a", label=f"{sp}: Y0 = 1 (initially feasible)")
        ax[0].bar(x, inf, 0.36, bottom=fe, color="#f6c48a" if sp == "train" else "#b4441c", label=f"{sp}: Y0 = 0 (needs repair)")
        for xx, a, b in zip(x, fe, inf):
            ax[0].text(xx, a + b + 1.5, str(a + b), ha="center", fontsize=8, color=INK2)
    ax[0].set(xticks=range(4), xticklabels=["K0", "K1", "K>=2", "unknown K"], ylabel="independent roots", ylim=(0, 150),
              title="Roots by split and verified K (176 train / 21 val)")
    ax[0].legend(fontsize=7, frameon=False)
    for i, side in enumerate(("x", "y")):
        for j, sp in enumerate(("train", "val")):
            c = collections.Counter(m["status"] for v in V if v[2]["split"] == sp for m in v[2][f"{side}_meta"].values())
            n = sum(c.values())
            parts = [("VERIFIED (1)", c["VERIFIED"]), ("certified 0", c["CERTIFIED_INFEASIBLE"]), ("budget / planner 0", c["UNKNOWN_PLANNER"] + c["UNKNOWN_TRANSIT"])]
            left = 0
            for name, k in parts:
                ax[1].barh(i * 2.4 + j, k / n, left=left, color=CAT[name], label=name if (i, j) == (0, 0) else None, height=0.8)
                if k / n > 0.06:
                    ax[1].text(left + k / n / 2, i * 2.4 + j, str(k), ha="center", va="center", fontsize=7, color="white")
                left += k / n
    ax[1].set(yticks=[0, 1, 2.4, 3.4], yticklabels=["X train", "X val", "Y train", "Y val"], xlabel="fraction of observed queries", xlim=(0, 1),
              title="Labels the joint NLL sees (failure kind = evaluator metadata only)")
    ax[1].legend(fontsize=7, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3)
    jc = [j for v in V for i, _, j in v[1]["j"] if i is not None]
    j0 = [j for v in V for i, _, j in v[1]["j"] if i is None]
    bins = np.linspace(0, np.log1p(max(jc + j0)), 30)
    ax[2].hist(np.log1p(jc), bins, color="#2a78d6", alpha=0.85, label=f"complete X+connector+Y witness (n={len(jc)})")
    ax[2].hist(np.log1p(j0), bins, color="#1baf7a", alpha=0.85, label=f"no-op: Y0 target witness (n={len(j0)})")
    ax[2].set(xlabel="log1p(J)  [L1 joint travel, rad]", ylabel="witnesses", title="Travel supervision: replayed complete successes only")
    ax[2].legend(fontsize=7, frameon=False)
    for a in ax:
        _clean(a)
    return _save(fig, "01_training_data_audit.png")


def fig_folds(D, R):
    fo = P.folds(D, R)["folds"]
    M = np.array([[sum(D["roots"][k]["stratum"] == s for k in f["heldout"]) for s in STRATA] for f in fo])
    fig, ax = plt.subplots(1, 2, figsize=(13, 3.8), constrained_layout=True, gridspec_kw={"width_ratios": [1.2, 1]})
    im = ax[0].imshow(M, cmap="Blues", vmin=0, vmax=M.max())
    for (i, j), v in np.ndenumerate(M):
        ax[0].text(j, i, str(v), ha="center", va="center", color="white" if v > M.max() / 2 else INK2, fontsize=9)
    ax[0].set(xticks=range(4), xticklabels=["K0", "K1", "K>=2", "K?"], yticks=range(5), yticklabels=[f"fold {i}" for i in range(5)],
              title="Held-out roots per fold (family-grouped, stratified)")
    fig.colorbar(im, ax=ax[0], shrink=0.8)
    n = np.array([[len(f["train"]), len(f["early_stop"]), len(f["heldout"])] for f in fo])
    for j, (lab, col) in enumerate(zip(("train", "early stop", "held out (scored)"), ("#2a78d6", "#f2a33a", "#52514e"))):
        ax[1].barh(range(5), n[:, j], left=n[:, :j].sum(1), color=col, label=lab, height=0.7)
    ax[1].set(yticks=range(5), yticklabels=[f"fold {i}" for i in range(5)], xlabel="roots (197 train+val; 34 test never used)", title="Per-fold custody")
    ax[1].invert_yaxis()
    ax[1].legend(fontsize=7, frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.38))
    _clean(ax[1])
    return _save(fig, "02_crossfit_design.png")


def _arrows(ax, rec, seq):
    c0 = bd.cells0(rec)
    for t, (o, d) in enumerate(seq):
        (x0, y0), (x1, y1) = F1.center(rec, c0[o]), F1.center(rec, int(d))
        ax.annotate("", (x1, y1), (x0, y0), arrowprops={"arrowstyle": "-|>", "color": "#2a78d6", "lw": 2.0}, zorder=9)
        ax.text(x0 + 0.3 * (x1 - x0), y0 + 0.3 * (y1 - y0) + 0.028, str(t + 1), fontsize=9, color="white", ha="center", va="center", zorder=10,
                bbox={"boxstyle": "circle,pad=0.2", "fc": "#2a78d6", "ec": "none"})


def fig_separation(V, sc, R):
    """A root with a discordant same-endpoint order pair: scorer input (two orders, shared endpoint scene) vs evaluator-only outcomes."""
    sv, lab, ev = next((v for v in V if any(len({u["x"] for u in g["members"]}) == 2 and any(u["negative_kind"] == "CERTIFIED" for u in g["members"])
                                            for g in v[2]["order_groups"])), None)
    g = next(g for g in ev["order_groups"] if len({u["x"] for u in g["members"]}) == 2)
    k, rec, E = sv["key"], R[sv["key"]], T.env()
    Dq = json.loads((P.PM.OUT / "PMIN_DESIGN.json").read_text())["roots"][k]["queries"]
    mem = g["members"][:2]
    seqs = [[tuple(a) for a in Dq[ev["x_keys"][u["xi"]]]["seq"]] for u in mem]
    fig, ax = plt.subplots(1, 4, figsize=(21, 5.2), constrained_layout=True, gridspec_kw={"width_ratios": [1, 1, 1, 0.95]})
    c0 = bd.cells0(rec)
    for a, s, nm in zip(ax[:2], seqs, ("A", "B")):
        _panel(a, E, k, rec, c0, f"SCORER INPUT  X_{nm}: ordered prefix {bd.sig(s)}", q=T.qref(rec),
               note="S0, q0, object ids, destinations, order (numbered); F1 admissible")
        _arrows(a, rec, s)
    end = {**c0, **bd.endpoint(rec, seqs[0])}
    _panel(ax[2], E, k, rec, end, "SCORER INPUT  shared Y node: hypothetical edited scene", q=T.qref(rec),
           note=f"one Y variable for both orders (identical final poses), robot at q_ref")
    ax[3].axis("off")
    ax[3].add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax[3].transAxes, fc="#fbf3e6", ec="#b4441c", lw=1.5))
    yi = sv["parent"][mem[0]["xi"]]
    jt = {(i, y): j for i, y, j in lab["j"]}
    lines = ["EVALUATOR / LOSS ONLY  (never a scorer input)", ""]
    for u, nm in zip(mem, ("A", "B")):
        det = "ORDER_FIRST_ACTION certificate" if "ORDER_FIRST_ACTION" in (u["detail"] or "") else (u["detail"] or "")
        lines += [f"X_{nm} = {u['x']}   {u['status']}", f"   {u['negative_kind'] or ''} at {u['phase']}" if u["phase"] else "   relocations + connector replayed",
                  f"   {det}" if det else "",
                  f"   J_total = {jt[(u['xi'], yi)]:.2f} rad" if (u["xi"], yi) in jt else "   no travel label (not a complete success)", ""]
    ym = ev["y_meta"][yi]
    leg = sorted({r["role"] for c in ev["cands"] for r in c["legacy"] if c["sig"] in {bd.sig(s) for s in seqs}})
    lines += [f"Y (shared) = {lab['obs_y'][yi]}   {ym['status']}", f"Y0 = {ev['y0']}  (root {'feasible' if ev['y0'] else 'needs repair'} at q_ref)", "",
              f"legacy catalogue roles: {', '.join(leg) or '(not in catalogue: reversal query)'}",
              "roles / order / y_full / travel / failed_step", "are stripped: perturbing them leaves every", "coefficient, probability and choice", "bit-identical (PREFLIGHT leakage audit)"]
    ax[3].text(0.05, 0.95, "\n".join(lines), transform=ax[3].transAxes, va="top", family="monospace", fontsize=8.5, color="#2b2a28")
    fig.suptitle(f"{k}: same endpoint, two orders -> one Y node, two X nodes (methodology §3.2)", x=0.01, ha="left", fontsize=11)
    return _save(fig, f"03_scorer_vs_evaluator_{k.split('-')[-1]}.png")


def fig_roster(Dn):
    b, runs, pt = Dn["budget"], Dn["roster"], json.loads((OUT / "PREFLIGHT.json").read_text())["params"] if (OUT / "PREFLIGHT.json").exists() else None
    fig, ax = plt.subplots(1, 2, figsize=(14, 4.2), constrained_layout=True)
    arms = list(P.ARMS)
    for j, ph in enumerate(("SPLIT", "CROSSFIT")):
        n = [sum(r["arm"] == a and r["phase"] == ph for r in runs) for a in arms]
        cpu = [n_ * b["per_run_expected_cpu_s"][a] / 1000 for n_, a in zip(n, arms)]
        x = np.arange(len(arms)) + (j - 0.5) * 0.38
        ax[0].bar(x, cpu, 0.36, color=[ARM_C[a] for a in arms], alpha=1.0 if ph == "SPLIT" else 0.55, edgecolor="white")
        for xx, c, n_ in zip(x, cpu, n):
            ax[0].text(xx, c + 0.3, f"{n_}", ha="center", fontsize=7, color=INK2)
    ax[0].set(xticks=range(len(arms)), xticklabels=[a.replace("XY-", "") for a in arms], ylabel="expected CPU (1000 s)",
              title=f"{b['runs']} preregistered runs (left SPLIT, right CROSSFIT; label = runs); request {b['requested']['aggregate_cpu_s']:,} CPU-s")
    _clean(ax[0])
    if pt:
        tot = [pt[a]["total"] / 1000 for a in arms]
        act = [pt[a]["active"] / 1000 for a in arms]
        ax[1].bar(np.arange(len(arms)) - 0.19, tot, 0.36, color=[ARM_C[a] for a in arms], label="total parameters")
        ax[1].bar(np.arange(len(arms)) + 0.19, act, 0.36, color=[ARM_C[a] for a in arms], alpha=0.45, label="active (receive gradient)")
        ax[1].axhline(pt["LB (frozen reference)"]["total"] / 1000, color=INK2, lw=1, ls="--")
        ax[1].text(len(arms) - 0.5, pt["LB (frozen reference)"]["total"] / 1000 + 6, "LB reference", ha="right", fontsize=7, color=INK2)
        ax[1].set(xticks=range(len(arms)), xticklabels=[a.replace("XY-", "") for a in arms], ylabel="parameters (thousands)", ylim=(0, max(tot) * 1.15),
                  title="Capacity: quadratic = uncoupled-SA = DIRECT (same heads, same inputs)")
        ax[1].legend(fontsize=7, frameon=False, loc="lower right")
        _clean(ax[1])
    return _save(fig, "04_roster_budget_capacity.png")


def all_figures() -> list:
    sc, D, R, I = P.load()
    V = P.build(sc=sc, D=D, R=R, I=I)
    out = [fig_audit(V), fig_folds(D, R), fig_separation(V, sc, R)]
    if (OUT / "TRAINING_DESIGN.json").exists():
        out.append(fig_roster(json.loads((OUT / "TRAINING_DESIGN.json").read_text())))
    return out
