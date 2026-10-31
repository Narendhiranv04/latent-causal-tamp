"""BXY-P13 figures from runs/approach_b/bxy_p13_v1 (measured diagnostics only; scenes drawn from recorded witnesses and saved predictions)."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import bxy_data as bd  # noqa: E402
import bxy_p11 as P  # noqa: E402
import bxy_p13 as Q  # noqa: E402
import bxy_teacher as T  # noqa: E402
from bxy_p11_viz import ARM_C, _arrows  # noqa: E402
from bxy_p12_viz import SHORT, _clean  # noqa: E402
from bxy_pmin_viz import _panel  # noqa: E402

FIG = Path("visualizations/approach_b/bxy_p13_v1")
INK = "#222"
ARMS = ("DIRECT", "XY-quadratic", "XY-quadratic-noJ", "XY-uncoupled", "XY-uncoupled-SA")
XY = ARMS[1:]
CAT_INF = [("SUCCESS", "#1baf7a"), ("MISSED_RANKED_BELOW_NOOP", "#b4441c"), ("MISSED_PENALTY_REJECTED", "#f2a33a"), ("WRONG_REPAIR_Y0", "#7d3c98"),
           ("WRONG_REPAIR_X0", "#2a78d6"), ("WRONG_REPAIR_UNDECIDED", "#9e9e9e"), ("NO_REPAIR_AVAILABLE", "#d8d8d2")]
CAT_FEA = [("CORRECT_NOOP", "#1baf7a"), ("UNNECESSARY_REPAIR_OK", "#f2a33a"), ("UNNECESSARY_REPAIR_FAIL", "#b4441c")]


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    p = FIG / name
    fig.savefig(p, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return str(p)


def fig_categories(D):
    fig, ax = plt.subplots(1, 2, figsize=(16, 4.6), gridspec_kw={"width_ratios": [1.6, 1]})
    for a, cats, title in ((ax[0], CAT_INF, f"initially infeasible roots ({D['infeasible_roots']} roots x 3 seeds)"),
                           (ax[1], CAT_FEA, f"initially feasible roots ({D['roots'] - D['infeasible_roots']} roots x 3 seeds)")):
        for i, arm in enumerate(ARMS):
            left = 0.0
            for c, col in cats:
                v = D["oof"][arm]["categories"].get(c, {}).get("share", 0.0)
                a.barh(i, v, left=left, color=col, edgecolor="white", label=c if i == 0 else None)
                if v >= 0.06:
                    a.text(left + v / 2, i, f"{v:.2f}", ha="center", va="center", fontsize=7.5, color="white" if col not in ("#d8d8d2", "#f2a33a") else INK)
                left += v
        a.set_yticks(range(len(ARMS)), [SHORT[x] for x in ARMS])
        a.invert_yaxis()
        a.set(xlim=(0, 1), title=title, xlabel="share of (root, seed) choices, PRIMARY rule, out-of-fold")
        a.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=4 if len(cats) > 3 else 3)
        _clean(a)
    fig.suptitle("Where corrective selection fails (P12 out-of-fold predictions, 176 TRAIN roots)", x=0.01, ha="left")
    fig.tight_layout()
    return _save(fig, "01_failure_categories.png")


def fig_oracles(D):
    order = ["model", "X", "Y0", "Y", "Y0+X", "Y+X", "Y0+Y", "Y0+Y+X"]
    fig, ax = plt.subplots(1, 2, figsize=(16, 4.8), gridspec_kw={"width_ratios": [1.7, 1]})
    for arm in XY:
        o = D["oof"][arm]["oracle_succ_inf"]
        ax[0].plot(range(len(order)), [o[s] for s in order], "-o", ms=4, color=ARM_C[arm], label=SHORT[arm])
    od = D["oof"]["DIRECT"]["oracle_succ_inf"]
    ax[0].scatter([0, 2], [od["model"], od["Y0"]], marker="s", color=ARM_C["DIRECT"], zorder=5, label="DIRECT (model, oracle Y0)")
    av = D["oof"]["XY-quadratic"]["oracle_succ_inf"]["Y0+Y+X"]
    ax[0].axhline(av, color="#1baf7a", ls=":", lw=1)
    ax[0].text(0, av + 0.01, "all three substituted (≈ verified-repair availability)", fontsize=7.5, color="#1baf7a")
    ax[0].set_xticks(range(len(order)), ["model"] + [f"oracle {s}" for s in order[1:]], rotation=20, fontsize=8)
    ax[0].set(ylim=(0, 1), ylabel="success on initially infeasible roots", title="Evaluator-only oracle substitution (diagnostic upper bounds, NOT deployable)")
    ax[0].legend(frameon=False, fontsize=7.5)
    _clean(ax[0])
    w = 0.18
    for j, arm in enumerate(XY):
        s = D["shapley"][arm]
        ax[1].bar(np.arange(3) + (j - 1.5) * w, [s[k] for k in Q.SUBS], w, color=ARM_C[arm], label=SHORT[arm])
    ax[1].set_xticks(range(3), ["Y0 (unedited scene)", "Y edited scene", "X motion prefix"])
    ax[1].set(ylabel="Shapley share of the corrective-success gap", title="Attribution of the gap (mean over orderings)")
    ax[1].legend(frameon=False, fontsize=7.5)
    _clean(ax[1])
    fig.tight_layout()
    return _save(fig, "02_oracle_attribution.png")


def fig_ranking(D):
    fig, ax = plt.subplots(1, 3, figsize=(18, 4.6))
    for arm in ARMS:
        r = D["oof"][arm]["ranking"]
        ax[0].plot(Q.KS, [r[f"top{k}_p"] for k in Q.KS], "-o", color=ARM_C[arm], label=SHORT[arm], ms=4)
        ax[1].plot(Q.KS, [r[f"top{k}_cost"] for k in Q.KS], "-o", color=ARM_C[arm], ms=4)
    r = D["oof"]["XY-quadratic"]["ranking"]
    for a in ax[:2]:
        a.plot(Q.KS, [r[f"rand_top{k}"] for k in Q.KS], "--", color="#777", label="random order (same roots)")
        a.set(ylim=(0, 1.02), xlabel="k", xticks=Q.KS)
        _clean(a)
    ax[0].set(ylabel="best verified repair in top k", title=f"Repairs only, ranked by predicted p ({r['roots']} repairable infeasible roots)")
    ax[1].set(title="All admissible candidates incl. no-op, ranked by PRIMARY cost")
    ax[0].legend(frameon=False, fontsize=7.5)
    for i, arm in enumerate(ARMS):
        rr = D["oof"][arm]["ranking"]
        ax[2].bar(i - 0.2, rr["p_best_ok"], 0.38, color=ARM_C[arm])
        ax[2].bar(i + 0.2, rr["p_noop"], 0.38, color=ARM_C[arm], alpha=0.45)
        ax[2].plot([i - 0.38, i + 0.38], [rr["p_best_fail"]] * 2, color=INK, lw=1.5)
    ax[2].set_xticks(range(len(ARMS)), [SHORT[a] for a in ARMS], fontsize=8)
    ax[2].set(ylim=(0, 1), ylabel="mean predicted p", title="solid: best verified repair, light: no-op P(Y0), line: best failing repair")
    _clean(ax[2])
    fig.suptitle("Ranking of the verified repair on repairable, initially infeasible roots (out-of-fold)", x=0.01, ha="left")
    fig.tight_layout()
    return _save(fig, "03_repair_ranking.png")


def fig_y(D):
    fig, ax = plt.subplots(1, 3, figsize=(18, 4.6))
    for i, arm in enumerate(XY):
        o = D["oof"][arm]
        ax[0].bar(i - 0.2, o["edit_agree_y0_0"][0], 0.38, color=ARM_C[arm])
        ax[0].bar(i + 0.2, o["edit_agree_y0_1"][0], 0.38, color=ARM_C[arm], alpha=0.45)
    ax[0].axhline(0.5, color="#888", ls="--", lw=0.8)
    ax[0].set_xticks(range(len(XY)), [SHORT[a] for a in XY], fontsize=8)
    ax[0].set(ylim=(0, 1.05), ylabel="sign agreement of P(Y_edit) - P(Y0)",
              title="Matched edit contrasts: solid = S0 infeasible, edit feasible;\nlight = S0 feasible, edit infeasible")
    _clean(ax[0])
    keys = [("within_auc_succ", "success (repairs)"), ("within_auc_x", "X"), ("within_auc_y", "edited Y")]
    for j, (k, lab) in enumerate(keys):
        for i, arm in enumerate(ARMS):
            v = D["oof"][arm].get(k)
            if v and v[0] is not None:
                ax[1].bar(j + (i - 2) * 0.16, v[0], 0.15, color=ARM_C[arm], label=SHORT[arm] if j == 0 else None)
    ax[1].axhline(0.5, color="#888", ls="--", lw=0.8)
    ax[1].set_xticks(range(3), [x for _, x in keys])
    ax[1].set(ylim=(0.3, 0.9), ylabel="within-root AUROC (root mean)", title="Discrimination between candidates of the SAME root")
    ax[1].legend(frameon=False, fontsize=7)
    _clean(ax[1])
    for i, arm in enumerate(ARMS):
        o = D["oof"][arm]
        ax[2].bar(i - 0.2, o["p_noop_mean"]["0"], 0.38, color=ARM_C[arm])
        ax[2].bar(i + 0.2, o["p_noop_mean"]["1"], 0.38, color=ARM_C[arm], alpha=0.45)
        ax[2].text(i, max(o["p_noop_mean"].values()) + 0.03, f"AUROC {o['y0_auroc']:.2f}", ha="center", fontsize=7.5)
    ax[2].set_xticks(range(len(ARMS)), [SHORT[a] for a in ARMS], fontsize=8)
    ax[2].set(ylim=(0, 1.05), ylabel="mean predicted P(Y0 = 1)", title="No-op probability: solid = S0 infeasible, light = S0 feasible")
    _clean(ax[2])
    fig.suptitle("Edited-scene Y: the model separates roots, not the edits inside a root (out-of-fold)", x=0.01, ha="left")
    fig.tight_layout()
    return _save(fig, "04_y_diagnostics.png")


def fig_generalization(D):
    mets = [("y0_auroc", "Y0 AUROC", lambda o: o["y0_auroc"]), ("auc_succ", "within-root\nsuccess AUROC", lambda o: o["within_auc_succ"][0]),
            ("auc_y", "within-root\nedited-Y AUROC", lambda o: o["within_auc_y"][0]), ("edit1", "edit contrast\n(S0 feasible)", lambda o: o["edit_agree_y0_1"][0]),
            ("succ_inf", "corrective success\n(PRIMARY)", lambda o: o["oracle_succ_inf"]["model"])]
    fig, ax = plt.subplots(1, len(mets) + 1, figsize=(20, 4.4))
    for a, (_, title, f) in zip(ax, mets):
        for i, arm in enumerate(ARMS):
            try:
                vo, vi = f(D["oof"][arm]), f(D["insample"][arm])
            except (TypeError, KeyError):
                continue
            if vo is None or vi is None:
                continue
            a.bar(i - 0.2, vi, 0.38, color=ARM_C[arm], alpha=0.45)
            a.bar(i + 0.2, vo, 0.38, color=ARM_C[arm])
        a.set_xticks(range(len(ARMS)), [SHORT[x] for x in ARMS], rotation=35, fontsize=7)
        a.set(ylim=(0, 1), title=title)
        _clean(a)
    oo = D["order_omission"]
    a = ax[-1]
    for i, arm in enumerate(ARMS):
        a.bar(i - 0.2, oo[arm]["insample"]["order"]["certified"]["concordance_root_mean"], 0.38, color=ARM_C[arm], alpha=0.45)
        a.bar(i + 0.2, oo[arm]["oof"]["order"]["certified"]["concordance_root_mean"], 0.38, color=ARM_C[arm])
    a.axhline(0.5, color="#888", ls="--", lw=0.8)
    a.set_xticks(range(len(ARMS)), [SHORT[x] for x in ARMS], rotation=35, fontsize=7)
    a.set(ylim=(0, 1), title="certified order pairs\nconcordance")
    _clean(a)
    fig.suptitle("Training-root fit (light: each CROSSFIT checkpoint on its own training roots) vs out-of-fold (solid)", x=0.01, ha="left")
    fig.tight_layout()
    return _save(fig, "05_insample_vs_oof.png")


def fig_loss(D):
    fig, ax = plt.subplots(1, 3, figsize=(18, 4.6))
    comp = ["y0", "y_edit", "x_obs_y", "x_mix"]
    lc = D["loss_census"]
    cols = {"y0": "#b4441c", "y_edit": "#7d3c98", "x_obs_y": "#2a78d6", "x_mix": "#8fb8e8", "travel": "#1baf7a", "succ_repair": "#6b5ca5"}
    for i, arm in enumerate(XY):
        left = 0
        for c in comp:
            v = lc[arm]["share_of_nll"][c]
            ax[0].barh(i, v, left=left, color=cols[c], edgecolor="white", label=c if i == 0 else None)
            left += v
    ax[0].set_yticks(range(len(XY)), [SHORT[a] for a in XY])
    ax[0].invert_yaxis()
    ax[0].set(xlim=(0, 1), xlabel="share of out-of-fold joint NLL", title="Which terms the root-summed NLL consists of")
    ax[0].legend(frameon=False, fontsize=7.5, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.15))
    _clean(ax[0])
    ga = D["grad_audit"]
    arms = list(ga)
    for j, st in enumerate(("init", "best")):
        a = ax[1 + j]
        names = sorted({n for arm in arms for n in ga[arm]["summary"][st]["norm_median"]})
        w = 0.8 / max(1, len(names))
        for i, arm in enumerate(arms):
            s = ga[arm]["summary"][st]
            for k, n in enumerate(names):
                if n in s["norm_median"]:
                    a.bar(i + (k - (len(names) - 1) / 2) * w, s["norm_median"][n], w, color=cols.get(n, "#999"), label=n if i == 0 else None)
            a.plot([i - 0.4, i + 0.4], [s["total_norm_median"]] * 2, color=INK, lw=2)
            a.text(i, s["total_norm_median"] * 1.12, f"{100 * s['frac_over_clip']:.0f}% > clip", ha="center", fontsize=7.5)
        a.axhline(P.TRAIN["clip_norm"], color="#b4441c", ls="--", lw=1)
        a.set_yscale("log")
        a.set_xticks(range(len(arms)), [SHORT[x] for x in arms])
        a.set(ylabel="gradient norm (median over batches)", title=f"{'at initialization' if st == 'init' else 'at the restored checkpoint'}: component norms, black = total")
        a.legend(handles=[matplotlib.patches.Patch(color=cols.get(n, "#999"), label=n) for n in names], frameon=False, fontsize=7, loc="lower left")
        _clean(a)
    fig.suptitle("Loss composition and read-only gradient audit (12-root training batches; dashed = clip norm 10)", x=0.01, ha="left")
    fig.tight_layout()
    return _save(fig, "06_loss_gradient_audit.png")


def fig_probe(D):
    g = D["geometry_probe"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    keys = [("y0_auroc", "Y0 AUROC"), ("y_edit_auroc_pooled", "edited-Y AUROC\n(pooled)"), ("edit_contrast_agree_root_mean", "edit-contrast\nagreement")]
    for i, (k, _) in enumerate(keys):
        ax.bar(i - 0.2, g["xy_quadratic_oof"][k], 0.38, color=ARM_C["XY-quadratic"], label="XY-quadratic (out-of-fold, seed mean)" if i == 0 else None)
        ax.bar(i + 0.2, g["probe_logreg"][k], 0.38, color="#9e9e9e", label="8 hand-made clearances + logistic regression" if i == 0 else None)
    ax.axhline(0.5, color="#888", ls="--", lw=0.8)
    ax.set_xticks(range(3), [x for _, x in keys])
    ax.set(ylim=(0, 1), title=f"Geometry probe on scorer-available inputs ({g['roots']} held-out TRAIN roots, same folds)")
    ax.legend(frameon=False, fontsize=8)
    _clean(ax)
    fig.tight_layout()
    return _save(fig, "07_geometry_probe.png")


def fig_scene(pick, tag, title):
    """S0 with the chosen / verified candidates, the verified repair's endpoint with its replayed witnesses, and every candidate's
    out-of-fold p (XY-quadratic, seed mean) coloured by the recorded outcome."""
    k, d = pick
    sc = json.loads(P.SIDECAR.read_text())
    xr, yr = {r["x_key"]: r for r in sc["x_queries"]}, {r["y_key"]: r for r in sc["y_queries"]}
    sc_, Dd, Rr, I = P.load()
    by = {v[0]["key"]: v for v in P.build(sc=sc_, D=Dd, R=Rr, I=I)}
    sv, lab, ev = by[k]
    rec, E_ = Rr[k], T.env()
    c0 = bd.cells0(rec)
    seqof = lambda s: [] if s in ("", "empty") else [(a.split(">")[0], int(a.split(">")[1])) for a in s.split(".")]  # noqa: E731
    fig, ax = plt.subplots(1, 3, figsize=(19, 5.8), constrained_layout=True, gridspec_kw={"width_ratios": [1, 1, 1.05]})
    _panel(ax[0], E_, k, rec, c0, f"{k}  S0 (recorded Y0 = {ev['y0']}, {ev['stratum']}); arrows = model choice {d['chosen']}", q=T.qref(rec))
    if seqof(d["chosen"]):
        _arrows(ax[0], rec, seqof(d["chosen"]))
    ok = d["show"]
    ci = next(i for i, c in enumerate(sv["cands"]) if c["sig"] == ok)
    cand = sv["cands"][ci]
    xrow = xr.get(ev["x_keys"][cand["xi"]]) if cand["xi"] is not None else None
    yrow = yr.get(ev["y_keys"][cand["yi"]]) if cand["yi"] is not None else None
    _panel(ax[1], E_, k, rec, {**c0, **dict(seqof(ok))}, f"{d['show_label']}: {ok}  (X = {ev['cands'][ci]['x']}, Y = {ev['cands'][ci]['y']}, recorded)",
           x=xrow if xrow and xrow["y"] == 1 else None, ywit=yrow.get("target_witness") if yrow and yrow["y"] == 1 else None,
           note="replayed witnesses: relocations blue, connector pink, target green" if ev["cands"][ci]["success"] == 1 else
           f"recorded failure: {(yrow or xrow or {}).get('teacher_status')} / {(yrow or xrow or {}).get('negative_kind')}")
    rows = sorted(d["rows"], key=lambda r: -r["p"])[:14]
    col = {1: "#1baf7a", 0: "#b4441c", None: "#9e9e9e"}
    ax[2].barh(range(len(rows)), [r["p"] for r in rows], color=[col[r["success"]] for r in rows])
    for i, r in enumerate(rows):
        ax[2].text(r["p"] + 0.01, i, f"P(Y)={r['py']:.2f}  P(X|Y=1)={r['px1']:.2f}" if r["m"] else f"P(Y0)={r['p']:.2f}", va="center", fontsize=7)
    ax[2].set_yticks(range(len(rows)), [("no-op" if r["m"] == 0 else r["sig"]) + ("  <- chosen" if r["sig"] == d["chosen"] else "") for r in rows], fontsize=7.5)
    ax[2].invert_yaxis()
    ax[2].set(xlim=(0, 1.25), xlabel="out-of-fold p_succ, XY-quadratic seed mean (green verified success, red verified failure, grey undecided)")
    _clean(ax[2])
    fig.suptitle(title, x=0.01, ha="left")
    return _save(fig, tag)


def pick_scenes(D, per_root):
    """Roots chosen by measured category (majority over XY-quadratic seeds): a missed repair and a wrong edited-scene repair."""
    import collections
    rows = collections.defaultdict(list)
    for key, t in per_root.items():
        if key.startswith("XY-quadratic|"):
            for k, d in t.items():
                rows[k].append(d)
    C = Q.context()
    pr = C["tiers"][Q.TIER]
    out = {}
    for want in ("MISSED_RANKED_BELOW_NOOP", "WRONG_REPAIR_Y0", "MISSED_PENALTY_REJECTED"):
        for k in sorted(rows):
            cats = collections.Counter(d["cat"] for d in rows[k])
            if cats.most_common(1)[0][0] != want or cats[want] < 2:
                continue
            sv, lab, ev = C["by"][k]
            ps = [pr[("XY-quadratic", s)][k] for s in P.SEEDS]
            b = np.mean([np.array(p["coeffs"]["b"]) for p in ps], 0)
            a1 = np.mean([np.array(p["coeffs"]["a"]) + np.array(p["coeffs"]["w"]) for p in ps], 0)
            cr = []
            for c, e in zip(sv["cands"], ev["cands"]):
                if c["admissible"]:
                    py = float(Q.sig(b[c["yi"]]))
                    cr.append({"sig": c["sig"], "m": c["m"], "success": e["success"], "py": py, "px1": float(Q.sig(a1[c["xi"]])) if c["m"] else 1.0,
                               "p": py * (float(Q.sig(a1[c["xi"]])) if c["m"] else 1.0)})
            chosen = collections.Counter(P.choose(p["cands"], Q.rule("XY-quadratic")) for p in ps).most_common(1)[0][0]
            okc = [r for r in cr if r["success"] == 1 and r["m"] > 0]
            if not okc:
                continue
            show = sv["cands"][chosen]["sig"] if want == "WRONG_REPAIR_Y0" else max(okc, key=lambda r: r["p"])["sig"]
            out[want] = (k, {"chosen": sv["cands"][chosen]["sig"], "show": show, "rows": cr,
                             "show_label": "chosen repair (recorded failure)" if want == "WRONG_REPAIR_Y0" else "verified repair the model ranked lower"})
            break
    return out


def all_figures() -> list:
    D = json.loads((Q.OUT / "DIAGNOSTICS.json").read_text())
    out = [fig_categories(D), fig_oracles(D), fig_ranking(D), fig_y(D), fig_generalization(D), fig_loss(D), fig_probe(D)]
    picks = pick_scenes(D, json.loads((Q.OUT / "PER_ROOT_OOF.json").read_text()))
    titles = {"MISSED_RANKED_BELOW_NOOP": "Missed repair: a verified repair existed, but P(Y0) of the infeasible S0 was ranked above it",
              "WRONG_REPAIR_Y0": "Wrong edited scene: the chosen repair moves objects but leaves the target infeasible (Y = 0)",
              "MISSED_PENALTY_REJECTED": "Penalty rejection: the verified repair had higher p than the no-op but lost on the action / travel cost"}
    for i, (want, pick) in enumerate(picks.items()):
        out.append(fig_scene(pick, f"{8 + i:02d}_scene_{want.lower()}.png", titles[want]))
    return out


if __name__ == "__main__":
    print("\n".join(all_figures()))
