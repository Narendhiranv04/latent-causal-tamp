"""BXY-P25 final evidence from the stored P24 cohort only (no teacher call, no optimizer step, no second cohort, no change to EVALUATION_P24.json).

- member_predictions: forward passes of the 60 frozen checkpoints on the sealed label-free views; the 15-member means must reproduce the sealed
  PREDICTIONS_P24.json exactly (else STOP) before anything is derived from them.
- ablations: single members, ensemble size, and decision-rule variants, scored with the locked selection code (bxy_p24_analysis.root_rows) on the
  already-collected teacher outcomes. EXPLORATORY and descriptive: none of them is a test, none replaces the one-shot evaluation.
- storyboards: certified K3/K4 repairs chosen (sealed) by D, and one certified order twin, drawn only from recorded teacher witnesses.
"""
from __future__ import annotations

import gzip
import json
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import bxy_p11 as P  # noqa: E402
import bxy_p24_analysis as AN  # noqa: E402
import bxy_p24_confirm as C  # noqa: E402
import bxy_p24_report as R24  # noqa: E402
import bxy_teacher as TT  # noqa: E402
import bxy_data as bd  # noqa: E402
import bxy_pmin_sidecar as S  # noqa: E402
from bxy_p12_viz import _clean  # noqa: E402
from bxy_p14_run import _swap  # noqa: E402
from bxy_p17_viz import AC  # noqa: E402
from bxy_pmin_viz import _panel, done_steps  # noqa: E402

OUT = Path("runs/approach_b/bxy_p25_v1")
FIG = Path("visualizations/approach_b/bxy_p25_v1")
ARMS, SHORT = C.ARMS, R24.SHORT
TOL = 1e-9


def member_predictions(Cx) -> dict:
    """{root: {arm: [P.predict_all(member, label-free view) for 15 members]}}; label-free views exactly as at freeze time (results=None)."""
    import torch
    torch.set_num_threads(1)
    D = C.EN.design(C.OUT)
    inp = torch.load(C.OUT / "INPUTS_P24.pt", weights_only=False)["roots"]
    nets = C.load_all(C.frozen_models())
    pr = {}
    for k, v in Cx["by"].items():
        sv0 = C.view(C.OUT, k, v["rec"], D, inp[k])[0]
        pr[k] = {a: [P.predict_all(n, sv0) for n in nets[a]] for a in ARMS}
    return pr


def ens(prs, cands, idx) -> dict:
    """bxy_p24_confirm.ensemble over the member subset idx (same fields, same rule: mean where every member has a value)."""
    rows = []
    for j, c in enumerate(cands):
        r = {f: c[f] for f in ("sig", "m", "cd", "xi", "yi", "admissible")}
        if c["admissible"]:
            for f in ("p", "J_hat", "px", "py"):
                v = [prs[i]["cands"][j].get(f) for i in idx]
                if all(x is not None for x in v):
                    r[f] = float(np.mean(v))
        rows.append(r)
    var = {f: (np.mean([prs[i]["vars"][f] for i in idx], 0).tolist() if prs[idx[0]]["vars"].get(f) is not None else None) for f in ("px", "py")}
    return {"cands": rows, "vars": var}


def reproduce(Cx, MP) -> dict:
    worst = 0.0
    for k, v in Cx["by"].items():
        for a in ARMS:
            e = ens(MP[k][a], v["preds"][a]["cands"], list(range(15)))
            for x, y in zip(e["cands"], v["preds"][a]["cands"]):
                for f in ("p", "J_hat"):
                    if (x.get(f) is None) != (y.get(f) is None):
                        raise RuntimeError(f"{k} {a}: field presence differs")
                    if x.get(f) is not None:
                        worst = max(worst, abs(x[f] - y[f]))
    if worst > TOL:
        raise RuntimeError(f"member re-prediction does not reproduce the sealed ensemble (max diff {worst})")
    return {"roots": len(Cx["by"]), "members": 60, "max_abs_diff_vs_sealed": worst, "tolerance": TOL}


def score(Cx, preds_of, rules) -> dict:
    """Locked selection (AN.root_rows) on stored teacher outcomes; per-arm U / C / REP34 / unnecessary, plus per-root success columns."""
    per = Cx["eval"]["per_root"]
    T = {}
    for k, v in Cx["by"].items():
        r = {"key": k, "sv": v["sv"], "ev": v["ev"], "lab": v["lab"], "preds": preds_of(k)}
        T[k] = AN.root_rows(r, rules)
    pops = {"INF": [k for k in per if per[k]["info"]["y0"] == 0], "FEA": [k for k in per if per[k]["info"]["y0"] == 1]}
    pops["AVAIL"] = [k for k in pops["INF"] if per[k]["info"]["available"]]
    pops["REP34"] = [k for k in pops["AVAIL"] if per[k]["info"]["K"] in (3, 4)]
    out = {}
    for a in ARMS:
        out[a] = {"U": np.mean([T[k][a]["success"] for k in pops["INF"]]), "C": np.mean([T[k][a]["success"] for k in pops["AVAIL"]]),
                  "REP34": np.mean([T[k][a]["success"] for k in pops["REP34"]]), "unnecessary": np.mean([T[k][a]["false_repair"] for k in pops["FEA"]])}
        out[a] = {m: round(float(x), 4) for m, x in out[a].items()}
    return {"summary": out, "T": T, "pops": pops}


def ablations(Cx, MP) -> dict:
    fz = C.frozen_models()
    rules = {a: fz["arms"][a]["rule"] for a in ARMS}
    by = Cx["by"]
    sealed = lambda k: by[k]["preds"]  # noqa: E731
    base = score(Cx, sealed, rules)
    fam = {k: Cx["eval"]["per_root"][k]["info"]["family"] for k in by}
    res = {"sealed_15": base["summary"]}
    single = {a: [] for a in ARMS}
    for i in range(15):
        s = score(Cx, lambda k: {a: ens(MP[k][a], by[k]["preds"][a]["cands"], [i]) for a in ARMS}, rules)["summary"]
        for a in ARMS:
            single[a].append(s[a])
    res["single_member"] = single
    rng = np.random.default_rng(0)
    size = {}
    for n in (1, 3, 5, 10, 15):
        subs = [list(range(15))] if n == 15 else [sorted(rng.choice(15, n, replace=False).tolist()) for _ in range(10)]
        vals = [score(Cx, lambda k: {a: ens(MP[k][a], by[k]["preds"][a]["cands"], s_) for a in ARMS}, rules)["summary"] for s_ in subs]
        size[n] = {a: {m: [float(np.min([v[a][m] for v in vals])), float(np.mean([v[a][m] for v in vals])), float(np.max([v[a][m] for v in vals]))]
                       for m in ("U", "C", "unnecessary")} for a in ARMS}
        size[n]["subsets"] = len(subs)
    res["ensemble_size_min_mean_max"] = size
    variants = {"D/E/G no-op gate 0.5 (DIRECT's)": {a: (dict(rules[a], noop_gate=0.5) if a != "A:DIRECT-GEO" else rules[a]) for a in ARMS},
                "DIRECT no-op gate 0.7 (D/E's)": {a: (dict(rules[a], noop_gate=0.7) if a == "A:DIRECT-GEO" else rules[a]) for a in ARMS},
                "DIRECT alpha 0 (no length penalty)": {a: (dict(rules[a], alpha=0.0) if a == "A:DIRECT-GEO" else rules[a]) for a in ARMS},
                "D/E alpha 0.3 (DIRECT's length penalty)": {a: (dict(rules[a], alpha=0.3) if a[0] in "DE" else rules[a]) for a in ARMS}}
    rv = {}
    for nm, rl in variants.items():
        s = score(Cx, sealed, rl)
        col = lambda arm, ks, f="success", T=s["T"]: {k: float(T[k][arm][f]) for k in ks}  # noqa: E731
        con = {}
        for x, y in (("D:XYQ-GEO-SYM", "A:DIRECT-GEO"), ("E:XY-UNC-SA-GEO-SYM", "A:DIRECT-GEO")):
            u = AN.boot(col(x, s["pops"]["INF"]), col(y, s["pops"]["INF"]), fam)
            f = AN.boot(col(x, s["pops"]["FEA"], "false_repair"), col(y, s["pops"]["FEA"], "false_repair"), fam)
            con[f"{x[0]}-DIRECT"] = {"U_diff": u["diff"], "U_ci95": u["ci95"], "unnecessary_diff": f["diff"], "unnecessary_ci95": f["ci95"]}
        rv[nm] = {"rules": rl, "summary": s["summary"], "paired_vs_DIRECT_exploratory": con}
    res["rule_variants"] = rv
    res["note"] = "EXPLORATORY: recomputed selections on the already-labelled P24 cohort; not tests; the confirmatory result is EVALUATION_P24.json only"
    return res


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    p = FIG / name
    fig.savefig(p, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return str(p)


def fig_ablation(A):
    fig, ax = plt.subplots(1, 3, figsize=(18, 4.8), constrained_layout=True)
    for j, a in enumerate(ARMS):
        u = [s["U"] for s in A["single_member"][a]]
        ax[0].scatter(np.full(15, j) + np.linspace(-0.18, 0.18, 15), u, s=16, color=AC[a], alpha=0.75)
        ax[0].plot([j - 0.3, j + 0.3], [A["sealed_15"][a]["U"]] * 2, color="#222", lw=2)
    ax[0].set_xticks(range(len(ARMS)), [SHORT[a] for a in ARMS], fontsize=8)
    ax[0].set(ylabel="U (193 infeasible roots)", title="single frozen members (dots) vs 15-member ensemble (bar)")
    ns = [1, 3, 5, 10, 15]
    for a in ARMS:
        m = [A["ensemble_size_min_mean_max"][n][a]["U"] for n in ns]
        ax[1].plot(ns, [x[1] for x in m], "o-", color=AC[a], lw=2, label=SHORT[a])
        ax[1].fill_between(ns, [x[0] for x in m], [x[2] for x in m], color=AC[a], alpha=0.12)
    ax[1].set(xlabel="ensemble size (10 random subsets, min-mean-max)", ylabel="U", title="ensemble size")
    ax[1].legend(frameon=False, fontsize=8)
    rv = A["rule_variants"]
    names = ["sealed rules"] + list(rv)
    for j, nm in enumerate(names):
        s = A["sealed_15"] if j == 0 else rv[nm]["summary"]
        for i, a in enumerate(ARMS):
            ax[2].scatter(s[a]["unnecessary"], s[a]["U"], color=AC[a], marker="osD^v"[j], s=60, edgecolor="#222", lw=0.5,
                          label=(nm if i == 0 else None))
    ax[2].set(xlabel="unnecessary repairs on 44 FEA roots", ylabel="U", title="decision-rule variants (marker) per arm (colour)")
    ax[2].legend(frameon=False, fontsize=7, loc="lower right")
    for a_ in ax:
        _clean(a_)
    fig.suptitle("P25 exploratory ablations on the labelled P24 cohort (frozen weights, locked selection code, stored teacher outcomes; not tests)",
                 x=0.01, ha="left")
    return _save(fig, "01_ablations.png")


def fig_order_twin(Cx):
    """A certified order twin: same moves, same endpoint (one Y), one order certified infeasible during X, another executes."""
    E_ = TT.env()
    per = Cx["eval"]["per_root"]
    for k in sorted(Cx["by"], key=lambda k: (not (per[k]["D:XYQ-GEO-SYM"]["success"] and not per[k]["G:XYQ-GEO-SYM-ORDINV"]["success"]), k)):
        v = Cx["by"][k]
        e = v["ev"]
        for g in e["order_groups"]:
            bad = [u for u in g["members"] if u["x"] == 0 and u["negative_kind"] == "CERTIFIED"]
            good = [u for u in g["members"] if u["x"] == 1]
            if bad and good and e["obs_y"].get(g["y"]) == 1:
                rec, c0 = v["rec"], bd.cells0(v["rec"])
                rb, rg = v["res"][e["x_keys"][bad[0]["xi"]]], v["res"][e["x_keys"][good[0]["xi"]]]
                yr = v["res"][e["y_keys"][g["y"]]]
                fig, ax = plt.subplots(1, 3, figsize=(16, 5.2), constrained_layout=True)
                with _swap(S, "OUT", C.OUT):
                    sb = [tuple(s) for s in rb["ordered_actions"]]
                    ws = done_steps(rb)
                    _panel(ax[0], E_, k, rec, {**c0, **dict(sb[:len(rb.get("steps") or [])])}, f"order {'.'.join(f'{o}>{d}' for o, d in sb)}",
                           q=TT.qref(rec) if not ws else None, partial=ws or None,
                           note=f"X = 0 at {rb['failed_phase']}: {rb['teacher_status']} (certified); {len(rb.get('steps') or [])} relocation(s) done")
                    sg = [tuple(s) for s in rg["ordered_actions"]]
                    _panel(ax[1], E_, k, rec, {**c0, **dict(sg)}, f"order {'.'.join(f'{o}>{d}' for o, d in sg)}", x=rg, note="X = 1: relocations blue, connector pink")
                    _panel(ax[2], E_, k, rec, {**c0, **dict(sg)}, "shared Y: same edited scene, target from q_ref", q=TT.qref(rec),
                           ywit=yr.get("target_witness"), note=f"Y = {yr['y']} ({yr['teacher_status']})")
                pr = Cx["eval"]["per_root"][k]
                fig.suptitle(f"Certified order twin at {k}: same moves and endpoint, different order -> different X "
                             f"(sealed successes D {pr['D:XYQ-GEO-SYM']['success']}, G {pr['G:XYQ-GEO-SYM-ORDINV']['success']})", x=0.01, ha="left")
                return _save(fig, "02_certified_order_twin.png")
    return None


def storyboards(Cx, n=2) -> list:
    """Certified K4 and K3 roots where D's sealed choice succeeded: its own chosen repair, step by step."""
    per, out = Cx["eval"]["per_root"], []
    R24.FIG = FIG
    for K in (4, 3):
        ks = sorted(k for k in per if per[k]["info"]["certified"] and per[k]["info"]["K"] == K and per[k]["D:XYQ-GEO-SYM"]["success"])[:n]
        for k in ks:
            out.append(R24.storyboard(Cx, k, f"03_storyboard_K{K}_{k[-4:]}_D_choice.png", j=per[k]["D:XYQ-GEO-SYM"]["chosen"]))
    return out


def failures(Cx) -> dict:
    """Per arm, where its sealed choice on each initially infeasible root ends: success, no-op, X fails (relocation / connector), Y fails, unverified."""
    per, out = Cx["eval"]["per_root"], {}
    for a in ARMS:
        z = dict.fromkeys(("success", "noop", "X_fail_relocation", "X_fail_connector", "Y_fail", "unverified"), 0)
        for k, v in Cx["by"].items():
            if per[k]["info"]["y0"] != 0:
                continue
            c = v["sv"]["cands"][per[k][a]["chosen"]]
            e = v["ev"]
            x, y = e["obs_x"].get(c["xi"]) if c["xi"] is not None else 1, e["obs_y"].get(c["yi"])
            if per[k][a]["success"]:
                z["success"] += 1
            elif c["m"] == 0:
                z["noop"] += 1
            elif x is None or (x == 1 and y is None):
                z["unverified"] += 1
            elif x == 0:
                z["X_fail_connector" if str(e["x_meta"][c["xi"]]["phase"]).startswith("connector") else "X_fail_relocation"] += 1
            else:
                z["Y_fail"] += 1
        out[a] = z
    return out


def fig_failures(F):
    keys = [("success", "#1baf7a"), ("noop", "#999999"), ("X_fail_relocation", "#b4441c"), ("X_fail_connector", "#e87ba4"), ("Y_fail", "#7d3c98"),
            ("unverified", "#dddddd")]
    fig, ax = plt.subplots(figsize=(12, 3.6), constrained_layout=True)
    for i, a in enumerate(ARMS):
        left = 0
        for kk, col in keys:
            v = F[a][kk]
            ax.barh(i, v, left=left, color=col, height=0.6, label=kk.replace("_", " ") if i == 0 else None)
            if v >= 6:
                ax.text(left + v / 2, i, str(v), ha="center", va="center", fontsize=8, color="white" if kk not in ("unverified",) else "#333")
            left += v
    ax.set_yticks(range(len(ARMS)), [SHORT[a] for a in ARMS])
    ax.invert_yaxis()
    ax.set(xlabel="initially infeasible P24 roots (n = 193)", title="Where each arm's sealed choice ends (teacher outcome of the chosen candidate)")
    ax.legend(frameon=False, fontsize=8, ncol=6, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    _clean(ax)
    return _save(fig, "04_failure_breakdown.png")


def fig_frontier(Cx):
    ev = Cx["eval"]
    fig, ax = plt.subplots(figsize=(7.5, 5.2), constrained_layout=True)
    for a in list(ARMS) + ["ANALYTIC_ACCESS", "NOOP", "SHORTEST_ADMISSIBLE"]:
        s = ev["arms"][a]
        col = AC.get(a, "#888")
        ax.errorbar(s["unnecessary"], s["U"], yerr=[[s["U"] - s["U_wilson"][0]], [s["U_wilson"][1] - s["U"]]], fmt="o" if a in ARMS else "s",
                    color=col, ms=8, mec="white", capsize=3)
        off = {"ANALYTIC_ACCESS": (6, -12), "D:XYQ-GEO-SYM": (6, -6), "E:XY-UNC-SA-GEO-SYM": (6, 6)}.get(a, (6, 4))
        ax.annotate(SHORT.get(a, a.replace("_", " ").lower()), (s["unnecessary"], s["U"]), xytext=off, textcoords="offset points", fontsize=8)
    ax.plot(0, ev["oracle_verify_first"]["U"], "*", color="#222", ms=12)
    ax.annotate(f"verify-first oracle (evaluator-only, {ev['oracle_verify_first']['mean_verifications_INF']:.1f} teacher calls/root)",
                (0, ev["oracle_verify_first"]["U"]), xytext=(8, -3), textcoords="offset points", fontsize=8)
    ax.set(xlabel="unnecessary repairs on 44 initially feasible roots", ylabel="U on 193 initially infeasible roots (Wilson 95%)", xlim=(-0.03, 1.08),
           title="P24 success / false-repair frontier (one-shot, frozen ensembles)")
    _clean(ax)
    return _save(fig, "05_frontier.png")


def fig_schematic():
    """Protocol and architecture schematic (schematic, not data)."""
    fig, ax = plt.subplots(figsize=(15, 5.4))
    ax.set(xlim=(0, 15), ylim=(0, 5.4))
    ax.axis("off")

    def box(x, y, w, h, t, fc):
        ax.add_patch(plt.Rectangle((x, y), w, h, fc=fc, ec="#333", lw=0.8))
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=8.5, wrap=True)

    def arrow(x0, y0, x1, y1):
        ax.annotate("", (x1, y1), (x0, y0), arrowprops={"arrowstyle": "-|>", "color": "#333", "lw": 1.1})
    ax.text(0.1, 5.15, "Teacher protocol (labels)", fontsize=10, weight="bold")
    steps = [("q0, original scene\nY0: target from q_ref?", "#eeeeee"), ("relocation a1\n(online, no reset)", "#d6e6fa"), ("...", "#d6e6fa"),
             ("relocation am\n(no reset)", "#d6e6fa"), ("connector\nto q_ref, gripper free", "#fadbe8"), ("Y: target from q_ref\nin the edited scene", "#d3f2e6")]
    for i, (t, c) in enumerate(steps):
        box(0.1 + i * 2.45, 3.6, 2.1, 1.1, t, c)
        if i:
            arrow(0.1 + i * 2.45 - 0.33, 4.15, 0.1 + i * 2.45, 4.15)
    ax.text(0.1, 3.25, "X_q = 1 iff every relocation and the connector execute (prefix order matters); Y_s = 1 iff the target succeeds from q_ref "
            "in the edited scene; success = X * Y; negatives keep CERTIFIED vs NO_PLAN_FOUND/TIMEOUT evaluator-side", fontsize=8, color="#333")
    ax.text(0.1, 2.75, "Scorer (frozen; ranks an already-generated catalogue; never generates trajectories)", fontsize=10, weight="bold")
    mods = [("F1 analytic screen\n(admissible?)", "#eeeeee"), ("GEO2 access features\n(analytic, label-free)", "#eeeeee"),
            ("F2: X unary a_q\n(order-aware prefix)", "#d6e6fa"), ("F3: Y unary b_s\n(edited scene)", "#d3f2e6"), ("F5: coupling w_q\n(E: w = 0)", "#fde9c8"),
            ("p = σ(b) σ(a + w)\n→ choose: no-op gate,\n−log p + α m + γ Ĵ", "#f3e1f7")]
    for i, (t, c) in enumerate(mods):
        box(0.1 + i * 2.45, 1.0, 2.1, 1.3, t, c)
        if i:
            arrow(0.1 + i * 2.45 - 0.33, 1.65, 0.1 + i * 2.45, 1.65)
    ax.text(0.1, 0.45, "DIRECT-GEO: one success head on the same inputs (no X/Y split). G: F2 sees no order (order-invariant control). "
            "Training: joint X/Y likelihood + travel (Huber) + SYM edit contrast; 15 frozen members per arm (P21).", fontsize=8, color="#333")
    return _save(fig, "00_protocol_and_architecture_schematic.png")


def decision(Cx, A, F) -> dict:
    ev = Cx["eval"]
    pr, od = ev["primary"], ev["order"]
    lab = lambda d: d["label"]  # noqa: E731
    return {"version": "BXY_P25_DECISION_V1", "source_evaluation_sha256": Cx["eval_sha256"],
            "confirmatory": {"D_vs_DIRECT_U": lab(pr["D_vs_DIRECT"]), "E_vs_DIRECT_U": lab(pr["E_vs_DIRECT"]), "D_vs_E_U": lab(pr["D_vs_E_coupling"]),
                             "secondary_K34": {k: lab(v) for k, v in ev["secondary_K34"].items()}, "order": {k: lab(v) for k, v in od.items()}},
            "answers": {
                "whole_system_advantage_over_DIRECT": "NOT_ESTABLISHED (U +0.041 / +0.052, Holm-adjusted CIs include 0; below the +0.10 gain gate; "
                                                      "unnecessary-repair guardrail would fail: +0.182)",
                "ordering": "SUPPORTED (O2 D - G success on repairable K3/K4 +0.173, Holm CI [0.058, 0.308]); O1/O3 strict-order wins are structural",
                "coupling_F5": "UNSUPPORTED (D - E U -0.010 [-0.031, 0.010])",
                "K3_K4": "PHYSICALLY VERIFIED and certified necessary in 52 roots (31 K3, 21 K4); learned selection descriptive only",
                "two_d_readiness": "the 2D pipeline is complete and reproducible; the X/Y advantage over a matched direct predictor is not established"},
            "deployment_preference": "E (uncoupled X/Y) over D, as preregistered if coupling stays unhelpful; not over DIRECT on this evidence",
            "failure_breakdown_INF": F, "exploratory_ablations": "runs/approach_b/bxy_p25_v1/ABLATIONS_P25.json (not tests)",
            "scope": "new seeds of the same 2D K34 doorway generator family; no cross-generator or 3D claim"}


def _md_tables(md: str) -> list:
    """[(section heading, [rows])] of every markdown table in a report, cells stripped of markup (for the printable PDF)."""
    import re
    out, head, rows = [], "", []
    for ln in md.splitlines() + [""]:
        if ln.startswith("#"):
            head = ln.lstrip("# ").strip()
        if ln.startswith("|"):
            if not re.fullmatch(r"\|[\s:|-]+\|", ln.strip()):
                rows.append([re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", c).replace("**", "").replace("`", "").strip() for c in ln.strip().strip("|").split("|")])
        elif rows:
            out.append((head, rows))
            rows = []
    return out


def pdf(path=Path("responses-phases/APPROACH_B_P25_FINAL_FINDINGS.pdf")) -> str:
    """Printable findings: verdict page, every table of 0132 and the methodology, then the P24 / P25 figures (all from committed artifacts)."""
    import textwrap
    from matplotlib.backends.backend_pdf import PdfPages
    rep = Path("responses-phases/0132_BXY_P25_FINAL_METHOD_AND_FINDINGS.md").read_text()
    meth = Path("responses-phases/METHODOLOGY_FINAL_IMPLEMENTED.md").read_text()
    dec = json.loads((OUT / "DECISION_P25.json").read_text())
    figs = sorted(Path("visualizations/approach_b/bxy_p24_v1").glob("*.png")) + sorted(FIG.glob("*.png"))
    W, H = 11.69, 8.27
    with PdfPages(path, metadata={"Title": "Approach B (2D) final findings: P24 confirmation and P25", "Author": "BXY P25", "CreationDate": None}) as pp:
        fig = plt.figure(figsize=(W, H))
        fig.text(0.05, 0.93, "Approach B (X/Y), 2D: final implemented method and one-shot confirmation", fontsize=16, weight="bold")
        fig.text(0.05, 0.89, f"Verdict: {rep.split('**`')[1].split('`**')[0] if '**`' in rep else ''}    |    EVALUATION_P24.json sha256 {dec['source_evaluation_sha256'][:16]}", fontsize=9)
        y = 0.83
        for k, v in dec["answers"].items():
            for i, line in enumerate(textwrap.wrap(f"{k.replace('_', ' ')}: {v}", 150)):
                fig.text(0.05 + (0.02 if i else 0), y, line, fontsize=9.5)
                y -= 0.03
            y -= 0.012
        y -= 0.02
        for line in textwrap.wrap("Scope: new seeds of the same 2D K34 doorway generator family; one locked look at 237 independent roots with frozen 15-member "
                                  "ensembles; no cross-generator or 3D claim. Exploratory P25 ablations are recomputations on the labelled cohort, not tests.", 150):
            fig.text(0.05, y, line, fontsize=9, color="#444")
            y -= 0.028
        pp.savefig(fig)
        plt.close(fig)
        for src, md in (("0132 final findings", rep), ("final implemented methodology", meth)):
            for head, rows in _md_tables(md):
                ncol = max(len(r) for r in rows)
                width = [max(len(r[j]) if j < len(r) else 0 for r in rows) for j in range(ncol)]
                wrapw = [max(8, min(int(150 * w / max(sum(width), 1)), 70)) for w in width]
                cells = [["\n".join(textwrap.wrap(r[j] if j < len(r) else "", wrapw[j])) for j in range(ncol)] for r in rows]
                nl = sum(max(c.count("\n") + 1 for c in r) for r in cells)
                fig, ax = plt.subplots(figsize=(W, max(2.0, min(H, 0.9 + 0.2 * nl))))
                ax.axis("off")
                t = ax.table(cellText=cells[1:], colLabels=cells[0], loc="upper center", cellLoc="left", colWidths=[w / sum(wrapw) for w in wrapw])
                t.auto_set_font_size(False)
                t.set_fontsize(7.5)
                for (r_, _), c in t.get_celld().items():
                    c.set_height(0.035 * (max(cc.count("\n") + 1 for cc in (cells[r_] if r_ < len(cells) else [""]))) * 8.27 / fig.get_figheight())
                    c.set_edgecolor("#bbb")
                    if r_ == 0:
                        c.set_facecolor("#eef3fa")
                ax.set_title(f"{src} -- {head}", loc="left", fontsize=10)
                pp.savefig(fig, bbox_inches="tight")
                plt.close(fig)
        for f in figs:
            im = plt.imread(f)
            h, w = im.shape[:2]
            fig = plt.figure(figsize=(W, H))
            ax = fig.add_axes([0.03, 0.05, 0.94, 0.88])
            ax.imshow(im)
            ax.axis("off")
            ax.set_aspect("equal")
            fig.text(0.03, 0.96, str(f), fontsize=8, color="#555")
            pp.savefig(fig)
            plt.close(fig)
    return str(path)


def write_all() -> dict:
    t0, w0 = time.process_time(), time.time()
    Cx = R24.context()
    MP = member_predictions(Cx)
    rep = reproduce(Cx, MP)
    OUT.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT / "MEMBER_PREDICTIONS_P25.json.gz", "wt") as f:
        json.dump({k: {a: [{"p": [c.get("p") for c in m["cands"]], "J_hat": [c.get("J_hat") for c in m["cands"]]} for m in v[a]] for a in ARMS}
                   for k, v in MP.items()}, f)
    A = ablations(Cx, MP)
    A["reproduction"] = rep
    A["source_evaluation_sha256"] = Cx["eval_sha256"]
    (OUT / "ABLATIONS_P25.json").write_text(json.dumps(A, indent=1, sort_keys=True, default=float))
    F = failures(Cx)
    (OUT / "DECISION_P25.json").write_text(json.dumps(decision(Cx, A, F), indent=1, sort_keys=True))
    figs = [fig_schematic(), fig_ablation(A), fig_order_twin(Cx)] + storyboards(Cx) + [fig_failures(F), fig_frontier(Cx)]
    return {"reproduction": rep, "figures": [f for f in figs if f], "cpu_s": round(time.process_time() - t0, 1), "wall_s": round(time.time() - w0, 1)}


if __name__ == "__main__":
    import os
    import sys
    for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[v] = "1"
    print(pdf() if sys.argv[1:] == ["pdf"] else json.dumps(write_all(), indent=1))
