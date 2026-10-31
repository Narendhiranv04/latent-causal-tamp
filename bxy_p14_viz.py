"""BXY-P14 figures from runs/approach_b/bxy_p14_v1 (measured results only; scenes from recorded witnesses and saved predictions)."""
from __future__ import annotations

import collections
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.lines  # noqa: E402
import matplotlib.patches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import bxy_data as bd  # noqa: E402
import bxy_p11 as P  # noqa: E402
import bxy_p12_run as R  # noqa: E402
import bxy_p13 as Q  # noqa: E402
import bxy_p14 as H  # noqa: E402
import bxy_teacher as T  # noqa: E402
from bxy_p11_viz import _arrows  # noqa: E402
from bxy_p12_viz import _clean  # noqa: E402
from bxy_pmin_viz import _panel  # noqa: E402

FIG = Path("visualizations/approach_b/bxy_p14_v1")
INK = "#222"
COL = {"DIRECT": "#6b5ca5", "XYQ": "#2a78d6", "XYQ+CON": "#1baf7a", "XYQ+GEO": "#f2a33a", "XYQ+CON+GEO": "#b4441c"}
RULE_A = {"PRIMARY": 1.0, "PONLY": 0.45}


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    p = FIG / name
    fig.savefig(p, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return str(p)


def fig_headline(E):
    fig, ax = plt.subplots(figsize=(10, 6.2))
    base = E["arms"]["XYQ"]["PRIMARY"]
    ax.add_patch(matplotlib.patches.Rectangle((base["unnecessary"] - 1, base["succ_inf"] + 0.10), 1.05, 1, color="#1baf7a", alpha=0.07, lw=0))
    ax.plot([base["unnecessary"] + 0.05] * 2, [0, 1], color="#1baf7a", ls=":", lw=1)
    ax.axhline(base["succ_inf"] + 0.10, color="#1baf7a", ls=":", lw=1)
    ax.text(base["unnecessary"] + 0.055, 0.02, "research target: >= +0.10 corrective success,\n<= +0.05 unnecessary repairs vs XYQ / PRIMARY",
            fontsize=7.5, color="#1baf7a")
    for a, o in E["arms"].items():
        for r in H.RULES:
            x, y = o[r]["unnecessary"], o[r]["succ_inf"]
            ax.scatter(x, y, s=70, color=COL[a], alpha=RULE_A[r], marker="o" if r == "PRIMARY" else "s", edgecolor=INK, lw=0.6)
            ax.annotate(f"{y:.2f} / {x:.2f}", (x, y), (6, -3), textcoords="offset points", fontsize=6.5, color="#555")
    ax.legend(handles=[matplotlib.lines.Line2D([], [], marker="o", ls="", color=COL[a], label=a) for a in E["arms"]] +
              [matplotlib.lines.Line2D([], [], marker=m, ls="", color="#999", label=lab) for m, lab in (("o", "PRIMARY rule"), ("s", "PONLY rule"))],
              frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0.3, 0.98))
    ax.scatter(0, 0, marker="x", color=INK, s=60)
    ax.annotate("always no-op", (0, 0), (5, 4), textcoords="offset points", fontsize=7.5)
    ax.set(xlim=(-0.03, 1.0), ylim=(-0.03, 0.9), xlabel=f"unnecessary repairs on the {131} initially feasible roots",
           ylabel=f"verified success on the {E['infeasible_roots']} initially infeasible roots",
           title="P14 out-of-fold (176 TRAIN roots, 3 seeds; circles PRIMARY rule, squares PONLY)")
    _clean(ax)
    return _save(fig, "01_corrective_vs_unnecessary.png")


def fig_contrasts(E):
    rows = [(k, v) for k, v in E["contrasts"].items() if k != "C4"] + [(f"C4 {a}", v) for a, v in E["contrasts"]["C4"].items()]
    fig, ax = plt.subplots(1, 2, figsize=(15, 0.55 * len(rows) + 1.8), sharey=True)
    lab = {"C1": "C1  CON vs XYQ (PRIMARY)", "C2": "C2  GEO vs XYQ (PRIMARY)", "C3": "C3  CON+GEO vs XYQ (PRIMARY)",
           "C5": "C5  CON+GEO / PONLY vs XYQ / PRIMARY"}
    for j, (m, title, ref) in enumerate((("succ_inf", "delta success on initially infeasible roots", 0.10), ("unnecessary", "delta unnecessary repairs", 0.05))):
        a = ax[j]
        for i, (k, v) in enumerate(rows):
            d = v[m]
            a.plot(d["ci99"], [i, i], color="#bbb", lw=5, solid_capstyle="butt")
            a.plot(d["ci95"], [i, i], color=INK, lw=2)
            a.plot(d["diff"], i, "o", color="#1baf7a" if v.get("IMPROVES") else "#b4441c", ms=6)
        a.axvline(0, color="#888", lw=0.8)
        a.axvline(ref, color="#1baf7a", ls=":", lw=1)
        a.set(title=title + (" (target +0.10)" if j == 0 else " (guardrail +0.05)"), xlabel="paired family-cluster bootstrap: dark 95 %, grey 99 %")
        _clean(a)
    ax[0].set_yticks(range(len(rows)), [lab.get(k, k + " PONLY vs PRIMARY") for k, _ in rows], fontsize=8)
    ax[0].invert_yaxis()
    fig.suptitle("Pre-registered contrasts (green point = IMPROVES under the frozen rule)", x=0.01, ha="left")
    fig.tight_layout()
    return _save(fig, "02_contrasts.png")


def fig_mechanism(E):
    arms = list(E["arms"])
    keys = [("within_auc_y", "within-root\nedited-Y AUROC"), ("edit_agree_s0_feasible", "edit contrast\n(S0 feasible, edit infeasible)"),
            ("edit_agree_s0_infeasible", "edit contrast\n(S0 infeasible, edit feasible)"), ("y0_auroc", "Y0 AUROC"),
            ("within_auc_succ", "within-root\nsuccess AUROC"), ("within_auc_x", "within-root\nX AUROC")]
    fig, ax = plt.subplots(1, 2, figsize=(18, 4.8), gridspec_kw={"width_ratios": [2.2, 1]})
    w = 0.8 / len(arms)
    for i, a in enumerate(arms):
        v = [E["arms"][a]["mechanism"].get(k) for k, _ in keys]
        ax[0].bar(np.arange(len(keys)) + (i - (len(arms) - 1) / 2) * w, [x if x is not None else 0 for x in v], w, color=COL[a], label=a)
    ax[0].axhline(0.5, color="#888", ls="--", lw=0.8)
    ax[0].set_xticks(range(len(keys)), [x for _, x in keys], fontsize=8)
    ax[0].set(ylim=(0, 1.05), title="Does the model now separate the edits within a root? (out-of-fold, seed means)")
    ax[0].legend(frameon=False, fontsize=7.5, ncol=5)
    _clean(ax[0])
    lbl = {"01": "S0 infeasible,\nedit feasible", "00": "S0 infeasible,\nedit infeasible", "11": "S0 feasible,\nedit feasible", "10": "S0 feasible,\nedit infeasible"}
    for i, a in enumerate(arms):
        sh = E["arms"][a]["mechanism"]["edit_shift_by_label"] or {}
        ax[1].bar(np.arange(4) + (i - (len(arms) - 1) / 2) * w, [sh.get(k, {}).get("mean", 0) for k in lbl], w, color=COL[a])
    ax[1].axhline(0, color="#888", lw=0.8)
    ax[1].set_xticks(range(4), list(lbl.values()), fontsize=7.5)
    ax[1].set(ylabel="mean P(Y_edit) - P(Y0)", title="Edit shift by recorded labels (P13: ~ +0.13 everywhere)")
    _clean(ax[1])
    fig.tight_layout()
    return _save(fig, "03_mechanism.png")


def fig_categories(E):
    from bxy_p13_viz import CAT_FEA, CAT_INF
    arms = list(E["arms"])
    fig, ax = plt.subplots(1, 2, figsize=(17, 5.4), gridspec_kw={"width_ratios": [1.6, 1]})
    labels = [f"{a} / {r}" for a in arms for r in H.RULES]
    for a_, cats, title in ((ax[0], CAT_INF, "initially infeasible roots"), (ax[1], CAT_FEA, "initially feasible roots")):
        for i, (a, r) in enumerate((a, r) for a in arms for r in H.RULES):
            left = 0
            for c, col in cats:
                v = E["arms"][a][r]["categories"].get(c, 0.0)
                a_.barh(i, v, left=left, color=col, edgecolor="white", label=c if i == 0 else None)
                if v >= 0.07:
                    a_.text(left + v / 2, i, f"{v:.2f}", ha="center", va="center", fontsize=7, color="white" if col not in ("#d8d8d2", "#f2a33a") else INK)
                left += v
        a_.set_yticks(range(len(labels)), labels, fontsize=7.5)
        a_.invert_yaxis()
        a_.set(xlim=(0, 1), title=title, xlabel="share of (root, seed) choices, out-of-fold")
        a_.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=4 if len(cats) > 3 else 3)
        _clean(a_)
    fig.tight_layout()
    return _save(fig, "04_error_categories.png")


def fig_decomposition(E):
    arms = list(E["arms"])
    fig, ax = plt.subplots(1, 2, figsize=(15, 4.6))
    for j, (m, title) in enumerate((("succ_inf", "success on initially infeasible roots"), ("unnecessary", "unnecessary repairs on feasible roots"))):
        for i, a in enumerate(arms):
            for k, r in enumerate(H.RULES):
                v = E["arms"][a][r][m]
                ax[j].bar(i + (k - 0.5) * 0.38, v, 0.36, color=COL[a], alpha=RULE_A[r])
                ax[j].text(i + (k - 0.5) * 0.38, v + 0.01, f"{v:.2f}", ha="center", fontsize=7)
        ax[j].set_xticks(range(len(arms)), arms, fontsize=8)
        ax[j].set(ylim=(0, 1), title=title + " (solid PRIMARY, light PONLY)")
        _clean(ax[j])
    fig.suptitle("Training objective (arms) x selection mechanism (rules), same checkpoints per arm", x=0.01, ha="left")
    fig.tight_layout()
    return _save(fig, "05_training_x_selection.png")


def fig_probability(E):
    arms = list(E["arms"])
    fig, ax = plt.subplots(1, 3, figsize=(18, 4.6))
    for a in arms:
        rel = E["arms"][a]["prob"]["s"]["reliability"]
        ax[0].plot([b["p_mean"] for b in rel], [b["y_mean"] for b in rel], "-o", ms=3, color=COL[a],
                   label=f"{a}  LL {E['arms'][a]['prob']['s']['logloss_pooled']:.3f}  ECE {E['arms'][a]['prob']['s']['ece10']:.3f}")
    ax[0].plot([0, 1], [0, 1], "--", color="#999", lw=0.8)
    ax[0].set(xlabel="predicted p_succ (bin mean)", ylabel="observed frequency", title="success reliability (pooled, out-of-fold)")
    ax[0].legend(frameon=False, fontsize=7)
    oo = E["order_omission"]
    for i, a in enumerate(arms):
        ax[1].bar(i - 0.2, oo[a]["order"]["certified"]["concordance_root_mean"], 0.38, color=COL[a])
        ax[1].bar(i + 0.2, oo[a]["order"]["budget_policy"]["concordance_root_mean"], 0.38, color=COL[a], alpha=0.45)
        for k, side in enumerate(("x", "y", "success")):
            v = oo[a]["omission"][side]["sign_agreement"]
            if v is not None:
                ax[2].bar(i + (k - 1) * 0.27, v, 0.25, color=COL[a], alpha=(1, 0.65, 0.35)[k])
    for a_, t in ((ax[1], "order pairs: solid certified, light budget-policy failing order"), (ax[2], "omission sign agreement: x / y / success")):
        a_.axhline(0.5, color="#888", ls="--", lw=0.8)
        a_.set_xticks(range(len(arms)), arms, fontsize=7.5)
        a_.set(ylim=(0, 1), title=t)
        _clean(a_)
    _clean(ax[0])
    fig.tight_layout()
    return _save(fig, "06_probability_order_omission.png")


def fig_resources(L, E):
    fig, ax = plt.subplots(1, 3, figsize=(18, 4.4))
    rid = list(L["runs"])
    arm = [r.split("/")[2] for r in rid]
    ax[0].bar(range(len(rid)), [L["runs"][r]["cpu"] for r in rid], color=[COL.get(a, "#999") for a in arm], width=1.0)
    ax[0].axhline(H.LIMITS["per_run_cpu_s"], color="#b4441c", ls="--", lw=1)
    ax[0].legend(handles=[matplotlib.patches.Patch(color=COL[a], label=a) for a in H.ARMS], frameon=False, fontsize=7)
    ax[0].set(xlabel="run (fair launch order)", ylabel="CPU-s", title="CPU per run (dashed = 1,500 cap)")
    ev = sorted((e for e in L["events"] if e["kind"] in ("launch", "reap")), key=lambda e: e["t"])
    t0, run, tt, nn, agg, aa = ev[0]["t"], 0, [], [], 0.0, []
    for e in ev:
        run += 1 if e["kind"] == "launch" else -1
        agg += e.get("cpu", 0.0) if e["kind"] == "reap" else 0.0
        tt.append((e["t"] - t0) / 3600)
        nn.append(run)
        aa.append(agg)
    ax[1].step(tt, nn, where="post", color=INK)
    ax[1].set(xlabel="hours", ylabel="running workers", title="memory-gated workers (cap 4)")
    ax[2].plot(tt, aa, color="#2a78d6")
    ax[2].axhline(H.LIMITS["aggregate_cpu_s"], color="#b4441c", ls="--", lw=1, label="aggregate ceiling 45,000")
    ax[2].axhline(H.LIMITS["aggregate_cpu_s"] - H.RESERVE["evaluation_cpu_s"], color="#f2a33a", ls=":", lw=1, label="training cap")
    ax[2].legend(frameon=False, fontsize=7.5)
    ax[2].set(xlabel="hours", ylabel="aggregate worker CPU-s", title="aggregate CPU")
    for a in ax:
        _clean(a)
    fig.tight_layout()
    return _save(fig, "07_resources.png")


def fig_scenes(E):
    """Roots where the pre-specified combination changes the outcome (seed majority), drawn from recorded witnesses with both arms' p."""
    sc = json.loads(P.SIDECAR.read_text())
    xr, yr = {r["x_key"]: r for r in sc["x_queries"]}, {r["y_key"]: r for r in sc["y_queries"]}
    sc_, Dd, Rr, I = P.load()
    by = {v[0]["key"]: v for v in P.build(splits=("train",), sc=sc_, D=Dd, R=Rr, I=I)}
    ch = E["choices"]
    maj = lambda a, r, k: collections.Counter(ch[f"{a}|{s}"][k][r]["sig"] for s in P.SEEDS if k in ch.get(f"{a}|{s}", {})).most_common(1)[0][0]  # noqa: E731
    succ = lambda a, r, k: np.mean([ch[f"{a}|{s}"][k][r]["success"] for s in P.SEEDS if k in ch.get(f"{a}|{s}", {})])  # noqa: E731
    new, base = ("XYQ+CON+GEO", "PRIMARY"), ("XYQ", "PRIMARY")
    picks = {"gain": None, "loss": None}
    for k in sorted(by):
        ev = by[k][2]
        if ev["y0"] != 0:
            continue
        g, b = succ(*new, k), succ(*base, k)
        if picks["gain"] is None and g >= 2 / 3 and b <= 1 / 3:
            picks["gain"] = k
        if picks["loss"] is None and g <= 1 / 3 and b >= 2 / 3:
            picks["loss"] = k
    preds = {}
    for rid, spec in ((r, json.loads((H.OUT / "runs" / R.safe(r) / "RESULT.json").read_text())["spec"]) for r in E["runs"]):
        p = json.loads((H.OUT / "runs" / R.safe(rid) / "predictions.json").read_text())
        for k in p:
            preds.setdefault((spec["arm"], k), []).append(p[k])
    out = []
    for tag, k in picks.items():
        if k is None:
            continue
        sv, lab, ev = by[k]
        rec, E_ = Rr[k], T.env()
        c0 = bd.cells0(rec)
        sig_new, sig_base = maj(*new, k), maj(*base, k)
        seqof = lambda s: [] if s in ("", "empty", None) else [(a.split(">")[0], int(a.split(">")[1])) for a in s.split(".")]  # noqa: E731
        fig, ax = plt.subplots(1, 3, figsize=(19, 5.8), constrained_layout=True, gridspec_kw={"width_ratios": [1, 1, 1.1]})
        _panel(ax[0], E_, k, rec, c0, f"{k}  S0 (Y0 = {ev['y0']}); arrows = XYQ / PRIMARY choice {sig_base}", q=T.qref(rec))
        if seqof(sig_base):
            _arrows(ax[0], rec, seqof(sig_base))
        ci = next(i for i, c in enumerate(sv["cands"]) if c["sig"] == sig_new)
        cand = sv["cands"][ci]
        xrow = xr.get(ev["x_keys"][cand["xi"]]) if cand["xi"] is not None else None
        yrow = yr.get(ev["y_keys"][cand["yi"]]) if cand["yi"] is not None else None
        _panel(ax[1], E_, k, rec, {**c0, **dict(seqof(sig_new))}, f"XYQ+CON+GEO / PRIMARY choice: {sig_new} (X = {ev['cands'][ci]['x']}, Y = {ev['cands'][ci]['y']})",
               x=xrow if xrow and xrow["y"] == 1 else None, ywit=yrow.get("target_witness") if yrow and yrow["y"] == 1 else None,
               note="replayed witnesses: relocations blue, connector pink, target green" if ev["cands"][ci]["success"] == 1 else
               f"recorded failure: X {(xrow or {}).get('teacher_status')} at {(xrow or {}).get('failed_phase')} ({(xrow or {}).get('negative_kind')}); "
               "the green target path belongs to the endpoint scene's Y = 1")
        rows = []
        for j, c in enumerate(sv["cands"]):
            if c["admissible"]:
                pa = np.mean([p["cands"][j]["p"] for p in preds[("XYQ", k)]])
                pb = np.mean([p["cands"][j]["p"] for p in preds[("XYQ+CON+GEO", k)]])
                rows.append((c["sig"] if c["m"] else "no-op", pa, pb, ev["cands"][j]["success"]))
        rows = sorted(rows, key=lambda r: -max(r[1], r[2]))[:12]
        y = np.arange(len(rows))
        col = {1: "#1baf7a", 0: "#b4441c", None: "#9e9e9e"}
        ax[2].barh(y - 0.2, [r[1] for r in rows], 0.38, color=[col[r[3]] for r in rows], alpha=0.45, label="XYQ (light)")
        ax[2].barh(y + 0.2, [r[2] for r in rows], 0.38, color=[col[r[3]] for r in rows], label="XYQ+CON+GEO (solid)")
        ax[2].set_yticks(y, [r[0] for r in rows], fontsize=7.5)
        ax[2].invert_yaxis()
        ax[2].set(xlim=(0, 1), xlabel="out-of-fold p_succ, seed mean (green verified success, red verified failure)")
        ax[2].legend(frameon=False, fontsize=7.5)
        _clean(ax[2])
        fig.suptitle({"gain": "Corrective gain: the combination selects a verified repair where XYQ did not",
                      "loss": "Regression: XYQ selected a verified repair, the combination did not"}[tag], x=0.01, ha="left")
        out.append(_save(fig, f"{8 + len(out):02d}_scene_{tag}.png"))
    return out


def all_figures() -> list:
    E = json.loads((H.OUT / "EVALUATION_P14.json").read_text())
    L = json.loads((H.OUT / "LEDGER.json").read_text())
    return [fig_headline(E), fig_contrasts(E), fig_mechanism(E), fig_categories(E), fig_decomposition(E), fig_probability(E), fig_resources(L, E)] + fig_scenes(E)


if __name__ == "__main__":
    print("\n".join(all_figures()))
