"""BXY-P12 figures from measured artifacts only: run histories, the ledger, EVALUATION.json, and recorded verified witnesses of the P-min
sidecar (robot scenes). No invented number and no illustrative scene presented as an observation."""
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
import bxy_p12_run as R  # noqa: E402
import bxy_teacher as T  # noqa: E402
from bxy_p11_viz import ARM_C, _arrows  # noqa: E402
from bxy_pmin_viz import _panel  # noqa: E402

FIG = Path("visualizations/approach_b/bxy_p12_v1")
OUT = R.OUT
ARMS = tuple(P.ARMS)
SHORT = {"XY-quadratic": "XY-quad", "XY-quadratic-noJ": "XY-quad-noJ", "XY-uncoupled": "XY-unc", "XY-uncoupled-SA": "XY-unc-SA", "DIRECT": "DIRECT"}
REF_C = {"NOOP": "#8c8c8c", "SHORTEST_ADMISSIBLE": "#c9c9c4", "DISPLACEMENT_RANK": "#a8a8a2"}
INK = "#2b2a28"


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / name, dpi=135, bbox_inches="tight")
    plt.close(fig)
    return str(FIG / name)


def _clean(ax, grid="y"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if grid:
        ax.grid(axis=grid, color="#e4e4e0", lw=0.6)
    ax.set_axisbelow(True)


def runs():
    L = json.loads((OUT / "LEDGER.json").read_text())
    out = {}
    for rid, r in L["runs"].items():
        rd = OUT / "runs" / R.safe(rid)
        res = json.loads((rd / "RESULT.json").read_text()) if r["status"] == "DONE" else None
        out[rid] = {"ledger": r, "res": res, "hist": json.loads((rd / "history.json").read_text()) if res else None}
    return L, out


# ------------------------------------------------------------------ training
def fig_training(L, RUNS, lam):
    fig, ax = plt.subplots(2, 3, figsize=(18, 9.5))
    for a, arm in zip(ax.flat, ARMS):
        for rid, r in RUNS.items():
            if not r["res"] or r["res"]["spec"]["arm"] != arm:
                continue
            sp = r["res"]["spec"]
            chosen = sp["phase"] == "CROSSFIT" or float(sp["lambda_J"]) in (0.0, (lam.get(arm) or {}).get("lambda"))
            h = [(x["update"] + 1, x["es_nll"]) for x in r["hist"] if "es_nll" in x]
            if not h:
                continue
            u, e = zip(*h)
            a.plot(u, e, lw=0.9 if sp["phase"] == "SPLIT" else 0.5, alpha=0.95 if sp["phase"] == "SPLIT" and chosen else 0.25,
                   color=ARM_C[arm] if chosen else "#bdbdb8", ls="-" if sp["phase"] == "SPLIT" else ":")
            a.plot(r["res"]["info"]["best_update"], r["res"]["info"]["es_nll"], "o", ms=3.5, color=ARM_C[arm] if chosen else "#bdbdb8")
        a.set(title=f"{arm}: early-stopping NLL per evaluation", xlabel="update", ylabel="mean root NLL (early-stop roots)")
        a.set_yscale("log")
        _clean(a)
    a = ax.flat[-1]
    for i, arm in enumerate(ARMS):
        bu = [r["res"]["info"]["best_update"] for r in RUNS.values() if r["res"] and r["res"]["spec"]["arm"] == arm]
        ur = [r["res"]["info"]["updates_run"] for r in RUNS.values() if r["res"] and r["res"]["spec"]["arm"] == arm]
        a.scatter(np.full(len(bu), i) - 0.12, bu, s=10, color=ARM_C[arm], label="best (restored)" if i == 0 else None)
        a.scatter(np.full(len(ur), i) + 0.12, ur, s=10, color=ARM_C[arm], marker="x", label="updates run" if i == 0 else None)
    a.axhline(P.TRAIN["max_updates"], color="#888", ls="--", lw=0.8)
    a.set_xticks(range(len(ARMS)), [SHORT[x] for x in ARMS])
    a.set(title="restored checkpoint update and updates run (every finished run)", ylabel="update")
    a.legend(frameon=False, fontsize=8)
    _clean(a)
    fig.suptitle("Training convergence: solid = SPLIT (coloured = selected lambda / lambda 0, grey = other lambdas), dotted = CROSSFIT folds", x=0.01, ha="left")
    fig.tight_layout()
    return _save(fig, "01_training_convergence.png")


def fig_lambda(sel):
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2), sharey=False)
    for a, arm in zip(ax, ("XY-quadratic", "XY-uncoupled", "XY-uncoupled-SA")):
        es = {k: v for k, v in sel["es_nll"].items() if k.startswith(arm + "|")}
        for k, v in es.items():
            _, l, s = k.split("|")
            a.plot(float(l), v, "o", color=ARM_C[arm], alpha=0.45, ms=5)
        m = sel["selection"][arm].get("mean_es_nll") or {}
        if m:
            ls = sorted(m, key=float)
            a.plot([float(x) for x in ls], [m[x] for x in ls], "-", color=ARM_C[arm], lw=2, label="3-seed mean")
        lam = sel["selection"][arm]["lambda"]
        if lam is not None:
            a.axvline(lam, color=INK, ls="--", lw=0.9)
            a.text(lam, a.get_ylim()[1], f" lambda* = {lam}", va="top", fontsize=9)
        a.set_xscale("log")
        a.set_xticks([0.1, 0.3, 1.0], ["0.1", "0.3", "1.0"])
        a.set(title=arm, xlabel="lambda_J", ylabel="best val21 joint NLL (early stopping)")
        a.legend(frameon=False, fontsize=8)
        _clean(a)
    fig.suptitle("Lambda selection (val21 only; frozen rule: 3-seed mean, ties within 1e-3 -> smaller lambda)", x=0.01, ha="left")
    fig.tight_layout()
    return _save(fig, "02_lambda_selection.png")


# ------------------------------------------------------------------ probabilities
def fig_reliability(E, tier="PRIMARY_DEV"):
    t = E["tiers"][tier]
    fig, ax = plt.subplots(1, 3, figsize=(16, 5))
    for a, (s, nm) in zip(ax, (("s", "success p_succ vs x AND y (+ Y0)"), ("x", "X: P(X=1) vs observed X"), ("y", "Y: P(Y=1) vs observed Y"))):
        a.plot([0, 1], [0, 1], color="#999", lw=0.8, ls="--")
        for arm, d in t["arms"].items():
            pr = d["prob"].get(s)
            if not pr:
                continue
            rb = pr["reliability"]
            a.plot([b["p_mean"] for b in rb], [b["y_mean"] for b in rb], "-o", ms=3 + 0 * len(rb), color=ARM_C[arm],
                   label=f"{SHORT[arm]}  LL {pr['logloss_root']:.3f}  ECE {pr['ece10']:.3f}")
        a.set(xlim=(0, 1), ylim=(0, 1), xlabel="predicted probability (bin mean)", ylabel="observed frequency", title=nm)
        a.legend(frameon=False, fontsize=7.5, loc="upper left")
        _clean(a, None)
    fig.suptitle(f"Reliability ({tier}: out-of-fold, pooled over seeds; LL = root-averaged log loss)", x=0.01, ha="left")
    fig.tight_layout()
    return _save(fig, f"03_reliability_{tier}.png")


def fig_contrasts(E):
    rows = []
    for tier in ("PRIMARY_DEV", "SUPPLEMENTARY_DEV", "DESCRIPTIVE_VAL"):
        c = E["tiers"][tier]["comparisons"]
        for ctrl in ("XY-uncoupled", "XY-uncoupled-SA"):
            if "coupling" in c:
                rows += [(tier, f"quad - {SHORT[ctrl]}", m, c["coupling"][ctrl][m]) for m in ("ll_s", "succ_inf")]
        if "factorization" in c:
            rows += [(tier, "quad - DIRECT", m, c["factorization"][m]) for m in ("ll_s", "succ_inf")]
        for k in ("TRAVEL_TRAINING", "TRAVEL_RANKING", "TRAVEL_COMBINED"):
            for m in ("ll_s", "succ_inf", "J"):
                if k in c.get("travel", {}) and m in c["travel"][k]:
                    rows.append((tier, k.replace("TRAVEL_", "travel ").lower(), m, c["travel"][k][m]))
    fig, ax = plt.subplots(1, 3, figsize=(18, 7.5), sharey=True)
    labels = sorted({r[1] for r in rows}, key=lambda s: [r[1] for r in rows].index(s))
    tiers = ("PRIMARY_DEV", "SUPPLEMENTARY_DEV", "DESCRIPTIVE_VAL")
    tc = {"PRIMARY_DEV": "#2a78d6", "SUPPLEMENTARY_DEV": "#90b4d8", "DESCRIPTIVE_VAL": "#9a9a95"}
    for a, (m, nm, good) in zip(ax, (("ll_s", "Delta success log loss (A - B; < 0 = A better)", "left"),
                                     ("succ_inf", "Delta success on initially infeasible roots (> 0 = A better)", "right"),
                                     ("J", "Delta witnessed J_total of successful choices [rad] (< 0 = A shorter)", "left"))):
        for (tier, lab, mm, d) in rows:
            if mm != m or d["diff"] is None:
                continue
            y = labels.index(lab) + {"PRIMARY_DEV": -0.22, "SUPPLEMENTARY_DEV": 0.0, "DESCRIPTIVE_VAL": 0.22}[tier]
            a.plot(d["ci95"], [y, y], color=tc[tier], lw=2.2)
            a.plot(d["diff"], y, "o", color=tc[tier], ms=5)
            a.text(d["ci95"][1], y, f"  n={d['roots']}", fontsize=6.5, va="center", color="#666")
        a.axvline(0, color=INK, lw=0.8)
        a.set_title(nm, fontsize=10)
        _clean(a, "x")
    ax[0].set_yticks(range(len(labels)), labels)
    ax[0].invert_yaxis()
    for t_ in tiers:
        ax[2].plot([], [], color=tc[t_], lw=2.2, label=t_)
    ax[2].legend(frameon=False, fontsize=8, loc="lower right")
    fig.suptitle("Paired root-cluster bootstrap (B = 10000, seed-averaged per root): point = mean, bar = 95% CI. PRIMARY_DEV decides; "
                 "development evidence only", x=0.01, ha="left")
    fig.tight_layout()
    return _save(fig, "04_paired_contrasts.png")


# ------------------------------------------------------------------ selection
def fig_selection(E, tier="PRIMARY_DEV"):
    t = E["tiers"][tier]
    names = list(t["arms"]) + list(P.REFERENCES)
    get = lambda n, k: (t["arms"][n]["selection:PRIMARY"] if n in t["arms"] else t["references"][n]).get(k)  # noqa: E731
    gat = lambda n, k: t["arms"][n]["selection:GATED_NOOP"].get(k) if n in t["arms"] else None  # noqa: E731
    mets = (("success_infeasible", "success on initially infeasible roots"), ("false_repair_on_feasible", "unnecessary repair on feasible roots"),
            ("noop_correct", "no-op decision correct"), ("success", "overall success"))
    fig, ax = plt.subplots(1, 4, figsize=(20, 5))
    for a, (k, nm) in zip(ax, mets):
        v = [get(n, k) for n in names]
        a.bar(range(len(names)), [x or 0 for x in v], color=[ARM_C.get(n, REF_C.get(n, "#ccc")) for n in names], edgecolor="white")
        g = [gat(n, k) for n in names]
        a.scatter([i for i, x in enumerate(g) if x is not None], [x for x in g if x is not None], marker="_", s=260, color=INK, zorder=5,
                  label="secondary GATED_NOOP")
        for i, x in enumerate(v):
            if x is not None:
                a.text(i, x + 0.01, f"{x:.2f}", ha="center", fontsize=7.5)
        a.set_xticks(range(len(names)), [SHORT.get(n, n.replace("_", "\n").lower()) for n in names], fontsize=7.5, rotation=30)
        a.set(ylim=(0, 1.08), title=nm)
        _clean(a)
    ax[0].axhline(t["references"]["ORACLE_AVAILABILITY"]["available"], color="#1baf7a", ls="--", lw=1)
    ax[0].text(len(names) - 0.5, t["references"]["ORACLE_AVAILABILITY"]["available"], "oracle availability", ha="right", va="bottom", fontsize=8, color="#1baf7a")
    ax[0].axhline(t["references"]["VERIFY_FIRST (oracle)"]["success_infeasible"], color="#6b5ca5", ls=":", lw=1)
    ax[1].legend(frameon=False, fontsize=8)
    fig.suptitle(f"Corrective selection ({tier}, PRIMARY gate-free cost rule, mean over seeds; {t['roots']} roots, {t['infeasible_roots']} initially infeasible)",
                 x=0.01, ha="left")
    fig.tight_layout()
    return _save(fig, f"05_selection_{tier}.png")


def fig_noop(E, tier="PRIMARY_DEV"):
    t = E["tiers"][tier]
    fig, ax = plt.subplots(1, len(t["arms"]), figsize=(4 * len(t["arms"]), 4.6), sharey=True)
    for a, arm in zip(ax, t["arms"]):
        acc = collections.defaultdict(list)
        for key, ch in t["choices"].items():
            if key.split("|")[0] != arm:
                continue
            for k, c in ch.items():
                acc[k].append(c)
        rng = np.random.default_rng(0)
        for k, cs in acc.items():
            y0, p = cs[0]["y0"], float(np.mean([c["p_noop"] for c in cs]))
            rep = np.mean([c["sig"] not in ("", None) and c["sig"] != "empty" and c.get("sig") for c in cs]) if cs else 0
            x = (0 if y0 == 1 else 1) + rng.uniform(-0.18, 0.18)
            a.scatter(x, p, s=14, color="#1baf7a" if np.mean([c["success"] for c in cs]) >= 0.5 else "#b4441c", alpha=0.8,
                      marker="o" if rep < 0.5 else "^")
        a.set_xticks([0, 1], ["Y0 = 1\n(feasible)", "Y0 = 0\n(needs repair)"])
        a.set(title=SHORT[arm], ylim=(0, 1))
        _clean(a)
    ax[0].set_ylabel("predicted P(Y0 = 1) (seed mean)")
    ax[0].scatter([], [], color="#1baf7a", label="choice succeeded (seed majority)")
    ax[0].scatter([], [], color="#b4441c", label="choice failed")
    ax[0].scatter([], [], color="#777", marker="^", label="repair chosen (majority)")
    ax[0].legend(frameon=False, fontsize=7.5, loc="lower left")
    fig.suptitle(f"No-op decisions per root ({tier}): circle = zero-move chosen, triangle = a correction chosen", x=0.01, ha="left")
    fig.tight_layout()
    return _save(fig, f"06_noop_decisions_{tier}.png")


def fig_order_omission(E, tier="PRIMARY_DEV"):
    t = E["tiers"][tier]
    fig, ax = plt.subplots(1, 2, figsize=(15, 4.8))
    arms = list(t["arms"])
    for j, kind in enumerate(("certified", "budget_policy")):
        v = [t["order"][a]["psucc"][kind] for a in arms]
        x = np.arange(len(arms)) + (j - 0.5) * 0.36
        ax[0].bar(x, [d["concordance_root_mean"] or 0 for d in v], 0.34, color=[ARM_C[a] for a in arms], alpha=1.0 if j == 0 else 0.45,
                  edgecolor="white", label=f"{kind} failing order ({v[0]['pairs']} pairs / {v[0]['roots']} roots per seed set)")
        for xi, d in zip(x, v):
            if d["ci95"]:
                ax[0].plot([xi, xi], d["ci95"], color=INK, lw=1)
    ax[0].axhline(0.5, color="#888", ls="--", lw=0.8)
    ax[0].set_xticks(range(len(arms)), [SHORT[a] for a in arms])
    ax[0].set(ylim=(0, 1.05), ylabel="concordance (root mean, 95% CI)", title="Same-endpoint order pairs: is the executable order ranked higher? (p_succ)")
    ax[0].legend(frameon=False, fontsize=7.5)
    _clean(ax[0])
    for j, side in enumerate(("x", "y", "success")):
        v = [t["omissions"][a]["sign_agreement"][side] for a in arms]
        ax[1].bar(np.arange(len(arms)) + (j - 1) * 0.27, [d["sign_agreement"] or 0 for d in v], 0.25, color=[ARM_C[a] for a in arms],
                  alpha=(1.0, 0.65, 0.35)[j], edgecolor="white", label=f"{side} ({v[0]['pairs']} decided pairs)")
    ax[1].axhline(0.5, color="#888", ls="--", lw=0.8)
    ax[1].set_xticks(range(len(arms)), [SHORT[a] for a in arms])
    ax[1].set(ylim=(0, 1.05), ylabel="sign agreement", title="Omissions: predicted change matches the decided full -> omitted change")
    ax[1].legend(frameon=False, fontsize=7.5)
    _clean(ax[1])
    fig.suptitle(f"Order and omission ({tier}); budget-limited zeros are teacher-policy outcomes, not geometric impossibility", x=0.01, ha="left")
    fig.tight_layout()
    return _save(fig, f"07_order_omission_{tier}.png")


def fig_strata(E, tier="SUPPLEMENTARY_DEV"):
    t = E["tiers"][tier]
    st = ("K0", "K1", "K>=2", "None")
    arms = list(t["arms"])
    fig, ax = plt.subplots(1, 2, figsize=(15, 4.6))
    for i, arm in enumerate(arms):
        d = t["arms"][arm]["strata"]
        x = np.arange(4) + (i - 2) * 0.16
        ax[0].bar(x, [d[s]["ll_s"] or 0 for s in st], 0.15, color=ARM_C[arm], label=SHORT[arm])
        ax[1].bar(x, [d[s]["succ_inf"] or 0 for s in st], 0.15, color=ARM_C[arm])
    d = t["arms"][arms[0]]["strata"]
    ax[0].set_xticks(range(4), [f"{s}\n{d[s]['roots']} roots" for s in st])
    ax[1].set_xticks(range(4), [f"{s}\n{d[s]['infeasible_roots']} infeasible" for s in st])
    ax[0].set(ylabel="success log loss (root mean, seeds pooled)", title="probability quality by difficulty")
    ax[1].set(ylabel="success on initially infeasible roots", ylim=(0, 1.05), title="corrective selection by difficulty")
    ax[0].legend(frameon=False, fontsize=8)
    for a in ax:
        _clean(a)
    fig.suptitle(f"Difficulty strata ({tier}); strata with < 10 roots are descriptive only", x=0.01, ha="left")
    fig.tight_layout()
    return _save(fig, f"08_strata_{tier}.png")


def fig_travel(E, tier="PRIMARY_DEV"):
    t = E["tiers"][tier]
    arms = list(t["arms"])
    fig, ax = plt.subplots(1, 2, figsize=(15, 4.8))
    for a, key, nm in ((ax[0], "travel_parts_of_successful_choices", "all successful choices (no-op: target only)"),
                       (ax[1], "travel_parts_successful_corrections", "successful corrections only (m >= 1)")):
        bot = np.zeros(len(arms))
        for part, c in (("relocation", "#2a78d6"), ("connector", "#e87ba4"), ("target", "#1baf7a")):
            v = np.array([(t["arms"][x][key] or {}).get(part, 0.0) for x in arms])
            a.bar(range(len(arms)), v, bottom=bot, color=c, label=part, edgecolor="white")
            bot += v
        for i, x in enumerate(arms):
            d = t["arms"][x][key]
            if d:
                a.text(i, bot[i] + 0.03, f"{d['J']:.2f}", ha="center", fontsize=8)
        a.set_xticks(range(len(arms)), [SHORT[x] for x in arms])
        a.set(ylabel="mean witnessed robot travel [rad]", title=nm)
        a.legend(frameon=False, fontsize=8)
        _clean(a)
    fig.suptitle(f"Complete robot travel of chosen, verified-successful candidates ({tier}): relocations (incl. approaches) + connector + "
                 "target, from replayed witnesses", x=0.01, ha="left")
    fig.tight_layout()
    return _save(fig, f"09_travel_decomposition_{tier}.png")


def fig_resources(L):
    fig, ax = plt.subplots(1, 3, figsize=(18, 4.6))
    cpu = [(rid, r["cpu"]) for rid, r in L["runs"].items()]                  # ledger order = fair launch order
    arms = [rid.split("/")[1] if rid.startswith("split") else rid.split("/")[2] for rid, _ in cpu]
    ax[0].bar(range(len(cpu)), [c for _, c in cpu], color=[ARM_C.get(a, "#999") for a in arms], width=1.0)
    ax[0].axhline(L["limits"]["per_run_cpu_s"], color="#b4441c", ls="--", lw=1)
    ax[0].text(0, L["limits"]["per_run_cpu_s"], " per-run ceiling", va="bottom", fontsize=8, color="#b4441c")
    ax[0].set(xlabel="run (ledger order)", ylabel="CPU-s incl. resumes", title="CPU per run")
    ev = sorted((e for e in L["events"] if e["kind"] in ("launch", "reap")), key=lambda e: e["t"])
    t0 = ev[0]["t"] if ev else 0
    run, tt, nn, agg, aa = 0, [], [], 0.0, []
    for e in ev:
        run += 1 if e["kind"] == "launch" else -1
        agg += e.get("cpu", 0.0) if e["kind"] == "reap" else 0.0
        tt.append((e["t"] - t0) / 3600)
        nn.append(run)
        aa.append(agg)
    ax[1].step(tt, nn, where="post", color=INK)
    ax[1].set(xlabel="hours since first launch", ylabel="running workers", title="memory-gated worker ramp")
    ax[2].plot(tt, aa, color="#2a78d6")
    ax[2].axhline(L["limits"]["aggregate_cpu_s"], color="#b4441c", ls="--", lw=1)
    ax[2].axhline(L["limits"]["aggregate_cpu_s"] - L["reserve"]["evaluation_cpu_s"], color="#f2a33a", ls=":", lw=1)
    ax[2].set(xlabel="hours since first launch", ylabel="aggregate worker CPU-s (finished attempts)", title="aggregate CPU vs ceiling / training cap")
    for a in ax:
        _clean(a)
    fig.suptitle("Measured resource use (ledger)", x=0.01, ha="left")
    fig.tight_layout()
    return _save(fig, "13_resources.png")


# ------------------------------------------------------------------ robot scenes (recorded witnesses only)
def _choice_majority(t, arm, k):
    cs = [ch[k] for key, ch in t["choices"].items() if key.split("|")[0] == arm and k in ch]
    sig = collections.Counter(c["sig"] for c in cs).most_common(1)[0][0] if cs else None
    return sig, cs


def fig_scenes(E, tier="PRIMARY_DEV"):
    """Representative roots: (1) a needs-repair root where XY-quadratic's choice succeeded, drawn with its replayed relocation + connector +
    target witnesses; (2) a selection error (missed repair / failed correction / unnecessary repair). Shown with the arms' choices."""
    sc = json.loads(P.SIDECAR.read_text())
    xr = {r["x_key"]: r for r in sc["x_queries"]}
    yr = {r["y_key"]: r for r in sc["y_queries"]}
    t = E["tiers"][tier]
    sc_, D, Rr, I = P.load()
    by = {v[0]["key"]: v for v in P.build(sc=sc_, D=D, R=Rr, I=I)}
    E_ = T.env()
    good, bad = None, None
    for k in sorted(by):
        sig, cs = _choice_majority(t, "XY-quadratic", k)
        if not cs:
            continue
        sv, lab, ev = by[k]
        ok = np.mean([c["success"] for c in cs])
        if good is None and ev["y0"] == 0 and ok == 1 and sig not in (None, "empty", "") and by[k][2]["stratum"] in ("K1", "K>=2"):
            good = (k, sig)
        if bad is None and ok == 0 and ev["y0"] == 0 and any(c["success"] == 1 for c in ev["cands"]):
            bad = (k, sig)
    out = []
    for tag, pick in (("10_scene_successful_correction", good), ("11_scene_selection_error", bad)):
        if pick is None:
            continue
        k, sig = pick
        sv, lab, ev = by[k]
        rec = Rr[k]
        c0 = bd.cells0(rec)
        ci = next(i for i, c in enumerate(sv["cands"]) if c["sig"] == sig)
        cand = sv["cands"][ci]
        seq = [(a.split(">")[0], int(a.split(">")[1])) for a in sig.split(".")] if cand["m"] else []
        fig, ax = plt.subplots(1, 3, figsize=(18, 5.8), constrained_layout=True, gridspec_kw={"width_ratios": [1, 1, 0.9]})
        _panel(ax[0], E_, k, rec, c0, f"{k}: initial scene S0 (Y0 = {ev['y0']}: target infeasible at q_ref)", q=T.qref(rec))
        if seq:
            _arrows(ax[0], rec, seq)
        xk = ev["x_keys"][cand["xi"]] if cand["xi"] is not None else None
        yk = ev["y_keys"][cand["yi"]] if cand["yi"] is not None else None
        xrow, yrow = (xr.get(xk) if xk else None), (yr.get(yk) if yk else None)
        end = {**c0, **dict(seq)}
        note = (f"X = {ev['cands'][ci]['x']}, Y = {ev['cands'][ci]['y']} (recorded teacher outcomes); "
                + ("relocations blue, connector pink, target green (replayed witnesses)" if ev["cands"][ci]["success"] == 1 else
                   f"failure: {(xrow or {}).get('teacher_status') if ev['cands'][ci]['x'] == 0 else (yrow or {}).get('teacher_status')}"))
        _panel(ax[1], E_, k, rec, end, f"XY-quadratic choice (seed majority): {sig}", x=xrow if xrow and xrow["y"] == 1 else None,
               ywit=yrow.get("target_witness") if yrow and yrow["y"] == 1 else None, note=note)
        ax[2].axis("off")
        lines = [f"choices on this root ({tier}, PRIMARY rule)", ""]
        for arm in t["arms"]:
            s2, cs = _choice_majority(t, arm, k)
            lines.append(f"{SHORT[arm]:<12} {str(s2 or 'empty'):<18} success {np.mean([c['success'] for c in cs]):.2f}  P(Y0) {np.mean([c['p_noop'] for c in cs]):.2f}")
        lines += ["", "verified-successful candidates of this root:"]
        lines += [f"  {c['sig'] or 'empty'}" for c in ev["cands"] if c["success"] == 1][:8]
        ax[2].text(0.0, 0.98, "\n".join(lines), transform=ax[2].transAxes, va="top", family="monospace", fontsize=8.5, color=INK)
        fig.suptitle({"10_scene_successful_correction": "Successful corrective selection (recorded witnesses)",
                      "11_scene_selection_error": "Selection error on a repairable root (a verified success existed)"}[tag], x=0.01, ha="left")
        out.append(_save(fig, f"{tag}.png"))
    return out


def fig_order_scene(E, tier="PRIMARY_DEV"):
    """A discordant same-endpoint order pair with a CERTIFIED failing order, the arms' predicted p_succ for both orders (seed mean)."""
    import bxy_p11_viz as V11
    t = E["tiers"][tier]
    sc_, D, Rr, I = P.load()
    V = P.build(sc=sc_, D=D, R=Rr, I=I)
    keys = set(next(iter(t["choices"].values())).keys())
    cand = [v for v in V if v[0]["key"] in keys and any(len({u["x"] for u in g["members"]}) == 2 and any(u["negative_kind"] == "CERTIFIED" for u in g["members"])
                                                        for g in v[2]["order_groups"])]
    if not cand:
        return None
    f = V11.fig_separation(cand, json.loads(P.SIDECAR.read_text()), Rr)                 # scene of the order pair (P11 layout)
    src = Path(f)
    dst = FIG / ("12_order_pair_scene_" + src.name.split("_")[-1])
    FIG.mkdir(parents=True, exist_ok=True)
    src.replace(dst)
    return str(dst)


def all_figures() -> list:
    E = json.loads((OUT / "EVALUATION.json").read_text())
    L, RUNS = runs()
    sel = json.loads((OUT / "LAMBDA_SELECTION.json").read_text())
    out = [fig_training(L, RUNS, sel["selection"]), fig_lambda(sel), fig_reliability(E), fig_contrasts(E), fig_selection(E), fig_noop(E),
           fig_order_omission(E), fig_strata(E), fig_travel(E), fig_resources(L)]
    out += fig_scenes(E)
    out.append(fig_order_scene(E))
    if E["tiers"]["DESCRIPTIVE_VAL"]["arms"]:
        out += [fig_selection(E, "DESCRIPTIVE_VAL"), fig_reliability(E, "SUPPLEMENTARY_DEV")]
    return out


if __name__ == "__main__":
    print("\n".join(str(x) for x in all_figures()))
