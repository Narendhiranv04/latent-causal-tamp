#!/usr/bin/env python3
"""R9 figures from committed raw records only (reports/final/*).  python figs_final.py -> reports/final/figures/*.png + tables (CSV/MD/TeX)."""
import csv, json, math
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

F = Path(__file__).resolve().parent / "reports" / "final"
OUT = F / "figures"; OUT.mkdir(exist_ok=True)
INK, MUTED, GRID = "#1f2328", "#6e7781", "#d0d7de"
C_FINAL, C_ABL, C_BASE, C_SIG = "#0969da", "#8c959f", "#bf8700", "#cf222e"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": GRID, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5})
LAB = {"UNCOUPLED": "no X/Y coupling", "ORDINV": "order-invariant X", "DIRECT": "direct Z", "UNIFORM4": "uniform proposals",
       "TASKFM": "task flow matching", "NOTASK": "no task conditioning", "M1": "top-1 destination", "C1": "single candidate",
       "CR": "complete-repair cVAE", "CRXY": "complete-repair cVAE + X/Y", "FC4": "factorized, count-matched", "PROD": "V3.4 production",
       "FINAL_X0": "FINAL other X seed", "FINAL_X1": "FINAL other X seed", "FINAL_X2": "FINAL other X seed"}


def wilson(k, n, z=1.96):
    if not n:
        return (0, 0)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def write_table(name, header, rows):
    with open(OUT / f"{name}.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    md = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(map(str, r)) + " |" for r in rows]
    (OUT / f"{name}.md").write_text("\n".join(md) + "\n")
    tex = ["\\begin{tabular}{" + "l" + "r" * (len(header) - 1) + "}", "\\toprule", " & ".join(header) + " \\\\", "\\midrule"]
    tex += [" & ".join(str(x).replace("%", "\\%").replace("_", "\\_") for x in r) + " \\\\" for r in rows] + ["\\bottomrule", "\\end{tabular}"]
    (OUT / f"{name}.tex").write_text("\n".join(tex) + "\n")


def panel_a():
    """(a) K <= 3 component ablations: paired difference vs FINAL with group-bootstrap 95% CI, 2D and 3D side by side."""
    P = json.loads((F / "r8a" / "R8A_PAIRED.json").read_text())
    arms = [a for a in ("UNCOUPLED", "ORDINV", "DIRECT", "UNIFORM4", "TASKFM", "NOTASK", "M1", "C1", "CR", "CRXY", "FC4", "PROD")]
    fig, axs = plt.subplots(1, 2, figsize=(9.5, 4.2), sharey=True)
    rows = []
    for ax, dom in zip(axs, ("3d", "2d")):
        for i, a in enumerate(arms):
            v = P[dom].get(a)
            if not v:
                continue
            c = v["vs_FINAL"]; lo, hi = c["ci95"]; sig = hi < 0 or lo > 0
            ax.errorbar(c["diff_pp"], i, xerr=[[c["diff_pp"] - lo], [hi - c["diff_pp"]]], fmt="o", ms=5, lw=2, capsize=0,
                        color=C_SIG if sig else C_ABL)
        ax.axvline(0, color=C_FINAL, lw=1.5)
        ax.set_title(f"{dom.upper()}: FINAL {P[dom]['FINAL']['task']:.1f}% task success (n={P[dom]['FINAL']['n_task']})", color=INK, loc="left")
        ax.set_xlabel("difference vs FINAL (percentage points)")
    axs[0].set_yticks(range(len(arms))); axs[0].set_yticklabels([LAB[a] for a in arms]); axs[0].invert_yaxis()
    fig.text(0.01, 0.01, "red = 95% group-bootstrap CI excludes 0; grey = not established", color=MUTED, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(OUT / "a_ablations.png", dpi=180); plt.close(fig)
    for a in ["FINAL"] + arms:
        r = [LAB.get(a, a)]
        for dom in ("3d", "2d"):
            v = P[dom].get(a)
            r += ([f"{v['task']:.1f}", f"{v['vs_FINAL']['diff_pp']:+.1f} [{v['vs_FINAL']['ci95'][0]:+.1f}, {v['vs_FINAL']['ci95'][1]:+.1f}]"] if v else ["-", "-"])
        rows.append(r)
    write_table("table_a_ablations", ["arm", "3D task %", "3D diff [95% CI]", "2D task %", "2D diff [95% CI]"], rows)


def panel_b():
    """(b) 3D planning on V3.4 (239 task roots): task success with Wilson CI."""
    P = json.loads((F / "r8a" / "R8A_PAIRED.json").read_text())["3d"]
    runs = [("FINAL", "Ours (FINAL)", C_FINAL), ("BL_em4m_paper_s0_b300", "E-M4M (300 CPU-s)", C_BASE), ("BL_disco_R1_ALL_succonly_s0", "DISCO-Grid s0", C_BASE),
            ("BL_disco_R1_ALL_succonly_s1", "DISCO-Grid s1", C_BASE), ("BL_disco_R1_ALL_succonly_s2", "DISCO-Grid s2", C_BASE),
            ("BL_msmcts_paper_s0_b300", "MS-MCTS (300 CPU-s)", C_BASE), ("BL_mosegman_paper_s0_b300", "MO-SeGMan (300 CPU-s)", C_BASE), ("BL_nor_full_s0", "NOR-Grid", C_BASE)]
    fig, ax = plt.subplots(figsize=(6.5, 3.6)); rows = []
    for i, (k, lab, col) in enumerate(runs):
        v = P[k]; n = v["n_task"]; s = round(v["task"] * n / 100); lo, hi = wilson(s, n)
        ax.barh(i, v["task"], color=col, height=0.6); ax.errorbar(v["task"], i, xerr=[[v["task"] - 100 * lo], [100 * hi - v["task"]]], fmt="none", ecolor=INK, lw=1)
        ax.text(v["task"] + 3, i, f"{v['task']:.1f}", va="center", color=INK, fontsize=8)
        rows.append([lab, f"{v['task']:.1f}", f"[{100 * lo:.1f}, {100 * hi:.1f}]", f"{v['noop']:.1f}", f"{v['abstain']:.1f}", f"{v['vs_FINAL']['diff_pp']:+.1f}"])
    ax.set_yticks(range(len(runs))); ax.set_yticklabels([r[1] for r in runs]); ax.invert_yaxis(); ax.set_xlim(0, 100)
    ax.set_xlabel("task success, K1-K3 (%)"); ax.set_title("3D planning, V3.4 cohort (239 task roots; one sealed plan, verified)", loc="left", color=INK)
    fig.tight_layout(); fig.savefig(OUT / "b_planning3d.png", dpi=180); plt.close(fig)
    rows.append(["REAP", "not run", "-", "-", "-", "-"])
    write_table("table_b_planning3d", ["method", "task %", "Wilson 95%", "NOOP K0 %", "ABSTAIN NONE %", "diff vs FINAL"], rows)


def panel_c():
    """(c) 3D target feasibility."""
    J = json.loads((F / "feas" / "FEAS_3D_V34.json").read_text()); ours = json.loads((F / "feas" / "FEAS_3D_V34_ours_final.json").read_text())
    rows = []
    def pull(m):
        return m["seeds"]["s0"] if "seeds" in m else m
    meth = J.get("methods", J)
    for name, key in (("PIGINet (no image)", "PIGINet"), ("SCNet", "SCNet"), ("GRN", "GRN")):
        m = next((v for k, v in meth.items() if k.lower().startswith(key.lower())), None)
        if m is None:
            continue
        m = pull(m)
        g = lambda *ks: next((m[k] for k in ks if k in m), None)  # noqa: E731
        au = g("AUROC", "auroc"); au = au[0] if isinstance(au, list) else (au.get("value") if isinstance(au, dict) else au)
        rows.append([name, g("TP"), g("FP"), g("TN"), g("FN"), au])
    rows.append(["Ours (final clean Y)", ours["TP"], ours["FP"], ours["TN"], ours["FN"], ours["AUROC"][0]])
    T = []
    for r in rows:
        tp, fp, tn, fn = r[1:5]
        T.append([r[0], tp, fp, tn, fn, f"{tp / (tp + fn):.3f}", f"{tn / (tn + fp):.3f}", f"{float(r[5]):.3f}" if r[5] is not None else "-"])
    write_table("table_c_feasibility3d", ["method", "TP", "FP", "TN", "FN", "TPR", "TNR", "AUROC"], T)
    fig, ax = plt.subplots(figsize=(5.5, 3.2))
    for i, t in enumerate(T):
        col = C_FINAL if t[0].startswith("Ours") else C_BASE
        ax.scatter(float(t[6]), float(t[5]), s=60, color=col, zorder=3); ax.annotate(f"{t[0]} (AUROC {t[7]})", (float(t[6]), float(t[5])), xytext=(6, 4), textcoords="offset points", fontsize=8, color=INK)
    ax.set_xlabel("TNR (302 infeasible)"); ax.set_ylabel("TPR (93 feasible)"); ax.set_xlim(0.94, 1.0); ax.set_ylim(0.74, 0.92)
    ax.set_title("3D initial target feasibility, V3.4 (threshold 0.5)", loc="left", color=INK)
    fig.tight_layout(); fig.savefig(OUT / "c_feasibility3d.png", dpi=180); plt.close(fig)


def panel_d():
    """(d) 3D composition on the sealed 99-root cohort: compact (Original / Recursive / Global) + full, by L_ref, with timing."""
    R = json.loads((F / "r8c" / "r8c" / "R6_r8b.json").read_text()); C = json.loads((F / "r8c" / "r8c_ctrl" / "R6_r8b.json").read_text())
    S = R["summary"]; n = R["n_roots"]
    full = [("B0", "B0 production (H<=3)", S["B0"]), ("H3", "H3 final model (H<=3)", S["H3"]), ("FLAT-INSERT", "flat insertion (H<=5)", S["FLAT-INSERT"]),
            ("REC-ORDERED", "Fig.3A recursive (H<=5)", S["REC-ORDERED"]), ("GA", "Fig.3B global (H<=5)", S["GA"]),
            ("cREC", "recursive, original-data X", C["summary"]["REC-ORDERED"]), ("cGA", "global, original-data X", C["summary"]["GA"])]
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.8), gridspec_kw={"width_ratios": [1.4, 1]})
    ax = axs[0]
    for i, (k, lab, s) in enumerate(full):
        lo, hi = s["wilson95"]; v = 100 * s["succ"] / n
        col = C_FINAL if k in ("REC-ORDERED", "GA") else (C_ABL if k.startswith("c") or k in ("B0",) else "#57606a")
        ax.barh(i, v, color=col, height=0.6); ax.errorbar(v, i, xerr=[[v - 100 * lo], [100 * hi - v]], fmt="none", ecolor=INK, lw=1)
        ax.text(100 * hi + 2, i, f"{s['succ']}/{n}", va="center", fontsize=8, color=INK)
    ax.set_yticks(range(len(full))); ax.set_yticklabels([f[1] for f in full]); ax.invert_yaxis(); ax.set_xlim(0, 100)
    ax.set_xlabel("verified success (%) [Wilson 95%]"); ax.set_title(f"sealed independent 3D cohort (n={n})", loc="left", color=INK)
    ax = axs[1]
    for j, (k, lab, s) in enumerate(full[:5]):
        b = s["by_L_ref"]
        for L, off, mk in (("4", -0.15, "o"), ("5", 0.15, "s")):
            sv, nv = b[L]; ax.scatter(j + off, 100 * sv / nv, marker=mk, s=40, color=C_FINAL if L == "4" else C_BASE, zorder=3)
    ax.set_xticks(range(5)); ax.set_xticklabels(["B0", "H3", "FLAT", "REC", "GA"]); ax.set_ylim(0, 100); ax.set_ylabel("success by L_ref (%)")
    ax.scatter([], [], marker="o", color=C_FINAL, label="L_ref 4 (n=68)"); ax.scatter([], [], marker="s", color=C_BASE, label="L_ref 5 (n=31)"); ax.legend(frameon=False, fontsize=8)
    ax.set_title("success by L_ref", loc="left", color=INK)
    fig.suptitle("3D composition (L_ref 4: 68 roots, L_ref 5: 31 roots)", x=0.01, ha="left", color=INK, fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94)); fig.savefig(OUT / "d_composition3d.png", dpi=180); plt.close(fig)
    rows = []
    for k, lab, s in full:
        pw = s["plan_wall"]
        rows.append([lab, f"{s['succ']}/{n}", f"{100 * s['wilson95'][0]:.1f}-{100 * s['wilson95'][1]:.1f}", s["succ_long"], s["succ_shorter_than_ref"],
                     f"{s['by_L_ref']['4'][0]}/{s['by_L_ref']['4'][1]}", f"{s['by_L_ref']['5'][0]}/{s['by_L_ref']['5'][1]}",
                     f"{pw['mean']:.1f}" if pw["mean"] is not None else "-", f"{pw['median']:.1f}" if pw["median"] is not None else "-", f"{pw['p90']:.1f}" if pw["p90"] is not None else "-",
                     s["budget_stops"]])
    write_table("table_d_composition3d", ["method", "success", "Wilson 95% (%)", "long (4-5) successes", "shorter than L_ref", "L_ref 4", "L_ref 5",
                                          "plan s mean", "median", "p90", "deadline stops"], rows)
    write_table("table_d_compact", ["method", "success /99", "Wilson 95% (%)"], [[r[0], r[1], r[2]] for r in rows if r[0].startswith(("H3", "Fig.3A", "Fig.3B"))])
    pr = [[k, v["gain"], v["loss"], f"{v['p_sign_two_sided']:.2g}"] for k, v in R["paired"].items()]
    write_table("table_d_paired", ["comparison", "A wins", "B wins", "sign test p"], pr)


def dataset():
    st = json.loads((F / "r8b" / "R8B_STATS.json").read_text())
    fig, axs = plt.subplots(1, 2, figsize=(8, 3))
    N = st["roster"]["by_N"]; axs[0].bar([int(k) for k in N], list(N.values()), color=C_FINAL); axs[0].set_xlabel("objects per scene"); axs[0].set_ylabel("roots")
    axs[0].set_title("R8B sealed cohort: scene size", loc="left", color=INK)
    g = {k: v for k, v in st.items() if k.startswith("gen")}
    names = {"genP": "gvlab2", "genL": "laptop", "genW": "Blackwell", "genG": "gvlab"}
    axs[1].bar([names[k] for k in g], [v["attempts"] for v in g.values()], color=GRID, label="attempts")
    axs[1].bar([names[k] for k in g], [v["observed"].get("3", 0) for v in g.values()], color=C_FINAL, label="accepted K3 parents")
    axs[1].legend(frameon=False, fontsize=8); axs[1].set_title("parent generation per host", loc="left", color=INK)
    fig.tight_layout(); fig.savefig(OUT / "e_dataset_r8b.png", dpi=180); plt.close(fig)


if __name__ == "__main__":
    for f in (panel_a, panel_b, panel_c, panel_d, dataset):
        try:
            f(); print("ok", f.__name__)
        except Exception as e:  # noqa: BLE001
            print("FAIL", f.__name__, type(e).__name__, e)
