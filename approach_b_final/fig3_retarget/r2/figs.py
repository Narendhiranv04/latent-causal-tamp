#!/usr/bin/env python3
"""R2 figures (matplotlib, Agg).  Every figure states its data source; drawings vs witnesses are labelled.
    python figs.py audit INVENTORY.json OUT_DIR"""
from __future__ import annotations

import json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

INK, MUTED, A, B, C = "#1f2328", "#6e7781", "#0969da", "#bc4c00", "#1a7f37"


def _style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=7, colors=MUTED)


def audit(inv, out):
    inv = json.loads(Path(inv).read_text()); out = Path(out); out.mkdir(parents=True, exist_ok=True)
    fig, axs = plt.subplots(2, 2, figsize=(11, 6.6))
    dev = inv["development_material_N"]
    for row, dom in enumerate(("2d", "3d")):
        d = inv["domains"][dom]
        ax = axs[row, 0]
        tr, va = d["train"]["N_hist"], d["val"]["N_hist"]
        ns = sorted({int(k) for k in tr} | {int(k) for k in va})
        x = np.arange(len(ns))
        t = np.array([tr.get(str(n), 0) for n in ns], float); v = np.array([va.get(str(n), 0) for n in ns], float)
        ax.bar(x - 0.2, t / t.sum(), 0.4, color=A, label=f"TRAIN (V3.2 snapshot, {int(t.sum())} roots)")
        ax.bar(x + 0.2, v / v.sum(), 0.4, color=B, label=f"VAL (V3.4, {int(v.sum())} roots)")
        ax.set_xticks(x); ax.set_xticklabels(ns, fontsize=7)
        marks = []
        if dom == "3d" and "3d_k45_cohort" in dev:
            marks.append(("K4/K5 cohort", dev["3d_k45_cohort"]))
        if f"{dom}_c3b" in dev:
            marks.append(("C3b", dev[f"{dom}_c3b"]))
        for j, (lab, q) in enumerate(marks):
            lo, hi = ns.index(q["min"]) if q["min"] in ns else 0, ns.index(q["max"]) if q["max"] in ns else len(ns) - 1
            y = ax.get_ylim()[1] * (0.92 - 0.1 * j)
            ax.plot([lo, hi], [y, y], color=C if j == 0 else INK, lw=2)
            ax.text(hi + 0.3, y, f"{lab} N {q['min']}-{q['max']}", fontsize=7, va="center", color=INK)
        if dom == "2d":
            ax.text(len(ns) - 1, ax.get_ylim()[1] * 0.62, "release_v2 (protected, not opened):\nN 25-28 > TRAIN max 20 and > cVAE MAXOBJ 20", ha="right", fontsize=7, color=B)
        ax.set_title(f"{dom.upper()}: total object count N (incl. target)", fontsize=9, loc="left", color=INK)
        ax.set_xlabel("N", fontsize=8, color=MUTED); ax.set_ylabel("fraction of roots", fontsize=8, color=MUTED)
        ax.legend(fontsize=7, frameon=False, loc="upper left"); _style(ax)
        ax = axs[row, 1]
        bins = ["1-5", "6-10", "11-15", "16-20"] if dom == "2d" else ["1-3", "4-5", "6-7", "8-13"]
        M = np.zeros((len(bins), 4)); P = np.zeros((len(bins), 4))
        for n, v in d["train"]["byN"].items():
            n = int(n)
            bi = next(i for i, b in enumerate(bins) if int(b.split("-")[0]) <= n <= int(b.split("-")[1]))
            for m, (c, c1) in v["X_by_m"].items():
                M[bi, int(m)] += c; P[bi, int(m)] += c1
        im = ax.imshow(M[:, 1:], cmap="Blues", aspect="auto")
        for i in range(len(bins)):
            for j in range(3):
                c = M[i, j + 1]
                ax.text(j, i, f"{int(c)}\n{P[i, j + 1] / c:.0%} X=1" if c else "0", ha="center", va="center", fontsize=7, color="white" if c > M[:, 1:].max() * 0.6 else INK)
        ax.set_xticks(range(3)); ax.set_xticklabels(["m=1", "m=2", "m=3"], fontsize=7); ax.set_yticks(range(len(bins))); ax.set_yticklabels([f"N {b}" for b in bins], fontsize=7)
        ax.set_title(f"{dom.upper()} TRAIN X labels by N bin x m (no m >= 4 label exists)", fontsize=9, loc="left", color=INK)
        _style(ax)
    fig.suptitle("R2.0 audit: training support (source: snapshot labels; TEST rows skipped unread)", fontsize=9.5, x=0.01, ha="left", color=INK)
    fig.tight_layout(); fig.savefig(out / "R2_0_train_support.png", dpi=150); plt.close(fig)




# ------------------------------------------------------------------ R2.1 / R2.2 figures
def _ci(ax, x, s, color, label=None, marker="o"):
    if not s or s.get("auroc") is None:
        return
    lo, hi = s.get("auroc_ci") or [s["auroc"], s["auroc"]]
    ax.errorbar([x], [s["auroc"]], yerr=[[s["auroc"] - lo], [hi - s["auroc"]]], fmt=marker, color=color, ms=6, capsize=3, label=label)


def scorer(dom, an, out):
    d = json.loads(Path(an, f"R2_1_model_only_{dom}.json").read_text()); P = d["P1_P2_P4"]
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.8))
    bins = [b for b in P["heldout"]["p11~Z_by_N"]]
    order = ["1-5", "6-10", "11-15", "16-20"] if dom == "2d" else ["1-3", "4-5", "6-7", "8-13"]
    bins = [b for b in order if b in P["heldout"]["p11~Z_by_N"]]
    ax = axs[0]
    for i, b in enumerate(bins):
        _ci(ax, i - 0.12, P["heldout"]["p11~Z_by_N"][b], A, "held-out (VAL + TRAIN-cache)" if i == 0 else None)
        _ci(ax, i + 0.12, P["fit_reference"]["p11~Z_by_N"].get(b), MUTED, "TRAIN fit reference" if i == 0 else None, "s")
        s = P["heldout"]["p11~Z_by_N"][b]
        ax.text(i, 0.42, f"n={s.get('n')}\npos={s.get('pos')}\nmf={s.get('mixed_families')}", ha="center", fontsize=6.5, color=MUTED)
    ax.set_xticks(range(len(bins))); ax.set_xticklabels([f"N {b}" for b in bins], fontsize=7); ax.set_ylim(0.4, 1.0)
    ax.axhline(0.6, color=B, lw=0.8, ls=":"); ax.set_ylabel("AUROC  p11 vs X*Y (supplied local m<=3)", fontsize=8, color=MUTED)
    ax.set_title(f"{dom.upper()}: by object count N", fontsize=9, loc="left", color=INK); ax.legend(fontsize=7, frameon=False, loc="lower left"); _style(ax)
    ax = axs[1]
    for i, m in enumerate(["1", "2", "3"]):
        _ci(ax, i - 0.12, P["heldout"]["p11~Z_by_m"].get(m), A); _ci(ax, i + 0.12, P["fit_reference"]["p11~Z_by_m"].get(m), MUTED, marker="s")
    xt = ["m=1", "m=2", "m=3"]
    if dom == "3d" and "OOD_m45" in d:
        for j, m in enumerate(["4", "5"]):
            _ci(ax, 3 + j, d["OOD_m45"]["by_m"].get(m), B, "K4/K5 cohort direct (OOD)" if j == 0 else None, "D")
        xt += ["m=4 (OOD)", "m=5 (OOD)"]
        ax.legend(fontsize=7, frameon=False, loc="lower left")
    ax.set_xticks(range(len(xt))); ax.set_xticklabels(xt, fontsize=7); ax.set_ylim(0.2, 1.0); ax.axhline(0.6, color=B, lw=0.8, ls=":"); ax.axhline(0.5, color=MUTED, lw=0.6)
    ax.set_title("by local sequence length m", fontsize=9, loc="left", color=INK); _style(ax)
    ax = axs[2]
    wr = P["heldout"]["within_root_p11~Z_by_N"]
    for i, b in enumerate(bins):
        v = wr.get(b, {})
        if v.get("top1_rate") is None:
            continue
        ax.bar(i - 0.18, v["top1_rate"], 0.36, color=A, label="top-1 by p11" if i == 0 else None)
        ax.bar(i + 0.18, v["random_rate"], 0.36, color=MUTED, label="random candidate" if i == 0 else None)
        ax.text(i, 0.02, f"{v['mixed_roots']} roots", ha="center", fontsize=6.5, color="white")
    ax.set_xticks(range(len(bins))); ax.set_xticklabels([f"N {b}" for b in bins], fontsize=7); ax.set_ylim(0, 1)
    ax.set_ylabel("verified (X=1, Y=1) rate", fontsize=8, color=MUTED); ax.set_title("within-root selection (mixed roots)", fontsize=9, loc="left", color=INK)
    ax.legend(fontsize=7, frameon=False); _style(ax)
    fig.suptitle(f"R2.1 frozen X/Y on supplied labelled assignments ({dom.upper()}; exact teacher labels; no cVAE, no search)", fontsize=9.5, x=0.01, ha="left", color=INK)
    fig.tight_layout(); fig.savefig(Path(out) / f"R2_1_scorer_{dom}.png", dpi=150); plt.close(fig)


def matched(dom, an, out, jobs):
    d = json.loads(Path(an, f"R2_phys_{dom}.json").read_text())["matchedN"]
    F = json.loads(Path(jobs, f"families_{dom}.json").read_text())
    rows = [r for r in d["rows"] if r.get("py_rep") is not None]
    fams = sorted({r["fam"] for r in rows})
    fig = plt.figure(figsize=(12, 7.2))
    gs = fig.add_gridspec(2, 3)
    for j, (yk, pk, title) in enumerate((("y_rep", "py_rep", "repair endpoint"), ("y_neg", "py_neg", "non-enabling endpoint"), ("y_noop", "py_noop", "no-op (blocked)"))):
        ax = fig.add_subplot(gs[0, j])
        for f in fams:
            rr = sorted([r for r in rows if r["fam"] == f and r["k"] != 0], key=lambda r: r["N"])
            ax.plot([r["N"] for r in rr], [r[pk] for r in rr], color=MUTED, lw=0.8)
            for r in rr:
                ax.plot(r["N"], r[pk], "o", ms=6, mfc=A if r.get(yk) == 1 else "white", mec=A if r.get(yk) == 1 else B)
        ax.plot([], [], "o", mfc=A, mec=A, label="teacher Y = 1"); ax.plot([], [], "o", mfc="white", mec=B, label="teacher Y = 0")
        lim = 15.5 if dom == "2d" else 8.5
        ax.axvspan(lim, ax.get_xlim()[1] if ax.get_xlim()[1] > lim else lim + 5, color="#f6e7d8", lw=0)
        ax.text(lim + 0.2, 0.95, "TRAIN: every root\nhere is NONE (Y=0)", fontsize=6.5, color=B, va="top")
        ax.set_ylim(-0.03, 1.03); ax.set_xlabel("N (total objects)", fontsize=8, color=MUTED); ax.set_ylabel("frozen pY (Y_global)", fontsize=8, color=MUTED)
        ax.set_title(f"{title}", fontsize=9, loc="left", color=INK); _style(ax)
        if j == 0:
            ax.legend(fontsize=7, frameon=False, loc="lower left")
    # scene drawings of one family: orig, +k1, +k2 (geometric drawing of the raw records)
    f = F["families"][0]
    vs = [{"k": "orig", "path": f["path"]}] + [v for v in F["variants"] if v["root_id"] == f["root_id"] and v["built"] and v["k"] != 0]
    for j, v in enumerate(vs[:3]):
        ax = fig.add_subplot(gs[1, j])
        raw = json.loads(Path(v["path"]).read_text())
        if dom == "2d":
            sc = raw["scene"]; cols = sc["lattice"]["cols"]; rws = sc["lattice"]["rows"]
            objs = [(o["id"], o["cell"], o["kind"]) for o in sc["objects"]]; goal = raw["goal_cell"]
        else:
            cols = rws = 6
            objs = [(o["id"], rc[0] * 6 + rc[1], "target" if o["id"] == "t0" else "obstacle") for o in raw["objects"] for rc in [raw["initial_cells"][o["id"]]]]
            goal = raw["goal"][0] * 6 + raw["goal"][1]
        added = set((raw.get("r2_perturbation") or {}).get("added", []))
        ax.set_xlim(-0.5, cols - 0.5); ax.set_ylim(-0.5, rws - 0.5); ax.set_aspect("equal")
        for c in range(cols * rws):
            ax.add_patch(plt.Rectangle((c % cols - 0.5, c // cols - 0.5), 1, 1, fill=False, ec="#d0d7de", lw=0.4))
        ax.add_patch(plt.Rectangle((goal % cols - 0.5, goal // cols - 0.5), 1, 1, fc="#dafbe1", ec=C, lw=1.2))
        rep = {o for o, _ in f["rep"]}
        for oid, c, kind in objs:
            col = C if kind == "target" else (B if oid in added else (A if raw["objects" if dom == "3d" else "scene"] and False else MUTED))
            ax.add_patch(plt.Circle((c % cols, c // cols), 0.35, fc=col, ec="white", lw=0.8))
        for o, dst in f["rep"]:
            oid = (raw["scene"]["objects"][o]["id"] if dom == "2d" else raw["objects"][o]["id"])
            c = next(cc for i_, cc, _ in objs if i_ == oid)
            ax.annotate("", xy=(dst % cols, dst // cols), xytext=(c % cols, c // cols), arrowprops=dict(arrowstyle="->", color=A, lw=1.4))
        lab = next((r for r in d["rows"] if r["fam"] == f["fam"] and str(r["k"]) == str(v["k"])), {})
        ax.set_title(f"{'original' if v['k'] == 'orig' else '+' + str(v['k'])}: N={len(objs)}  teacher X={lab.get('x')} Y={lab.get('y_rep')}  pY={lab.get('py_rep', 0) or 0:.2f}",
                     fontsize=8, loc="left", color=INK)
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle(f"R2.1-A matched object count ({dom.upper()}): add-only distractors (orange) far from task cells; green = target/goal, blue arrows = fixed repair. "
                 "Bottom: geometric drawing of the raw records (not a render).", fontsize=8.5, x=0.01, ha="left", color=INK)
    fig.tight_layout(); fig.savefig(Path(out) / f"R2_1_matchedN_{dom}.png", dpi=150); plt.close(fig)


def retarget(an, out):
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.8))
    for j, dom in enumerate(("2d", "3d")):
        d = json.loads(Path(an, f"R2_1_model_only_{dom}.json").read_text())["P3_C3b"]
        _ci(axs[0], j - 0.12, d["Ytau_retargeted"], A, "retargeted context" if j == 0 else None)
        _ci(axs[0], j + 0.12, d["Ytau_original_context"], MUTED, "original-task context" if j == 0 else None, "s")
        a = d["admission_beats_empty"]
        axs[1].bar(j - 0.2, a["fn_rate_enabling"], 0.4, color=B, label="enabling group discarded (FN)" if j == 0 else None)
        axs[1].bar(j + 0.2, a["fp_rate_nonenabling"], 0.4, color=MUTED, label="non-enabling admitted (FP)" if j == 0 else None)
        axs[1].text(j - 0.2, a["fn_rate_enabling"] + 0.01, f"{a['fn']}/{a['tp'] + a['fn']}", ha="center", fontsize=7)
        axs[1].text(j + 0.2, a["fp_rate_nonenabling"] + 0.01, f"{a['fp']}/{a['fp'] + a['tn']}", ha="center", fontsize=7)
        c = d["RETARGET_dpy_concordance_enabling_vs_not"]
        lo, hi = c["ci"] or [c["concordance"]] * 2
        axs[2].errorbar([j], [c["concordance"]], yerr=[[c["concordance"] - lo], [hi - c["concordance"]]], fmt="o", color=A, capsize=3)
        t = d["top1_p11_is_verified_enabler"]
        axs[2].plot(j + 0.25, t["rate"], "D", color=C); axs[2].plot(j + 0.25, t["random"], "x", color=MUTED)
    for ax, t, yl in ((axs[0], "temporary-target Y_tau AUROC (C3b, exact labels)", (0.2, 1)), (axs[1], "relative-pY admission errors", (0, 0.6)),
                      (axs[2], "dpY concordance (o), top-1 p11 verified (D) vs random (x)", (0, 1))):
        ax.set_xticks([0, 1]); ax.set_xticklabels(["2D", "3D"], fontsize=8); ax.set_ylim(*yl); ax.set_title(t, fontsize=8.5, loc="left", color=INK); _style(ax)
    axs[0].axhline(0.5, color=MUTED, lw=0.6); axs[2].axhline(0.5, color=MUTED, lw=0.6)
    axs[0].legend(fontsize=7, frameon=False); axs[1].legend(fontsize=7, frameon=False)
    fig.suptitle("R2.1-C retargeting interventions (C3b blocked temporary tasks, TT_ADAPTER_V1 labels; restricted candidate sets = diagnostic only)", fontsize=9.5, x=0.01, ha="left", color=INK)
    fig.tight_layout(); fig.savefig(Path(out) / "R2_1_retarget.png", dpi=150); plt.close(fig)


def rebase(an, out):
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.4))
    for ax, dom in zip(axs, ("2d", "3d")):
        p = json.loads(Path(an, f"R2_1_model_only_{dom}.json").read_text())["P1_P2_P4"]["P2_rebase"]
        for i, h in enumerate(("1", "2", "3")):
            v = p["by_h"].get(h) or p["by_h"].get(int(h)) or {}
            _ci(ax, i - 0.12, v.get("global"), A, "Y_global (original root + edits)" if i == 0 else None)
            _ci(ax, i + 0.12, v.get("rebased"), B, "Y_rebased (fresh-root no-op)" if i == 0 else None, "s")
        dd = p["rebased_minus_global"]
        ax.set_title(f"{dom.upper()}: rebased - global AUROC {dd['diff']:+.3f} CI {[round(x, 3) for x in dd['ci']] if dd['ci'] else None}", fontsize=8.5, loc="left", color=INK)
        ax.set_xticks(range(3)); ax.set_xticklabels(["h=1", "h=2", "h=3"], fontsize=8); ax.set_ylim(0.7, 1.0); ax.legend(fontsize=7, frameon=False, loc="lower left"); _style(ax)
    fig.suptitle("R2.1-B identical endpoints, two representations (held-out exact Y labels)", fontsize=9.5, x=0.01, ha="left", color=INK)
    fig.tight_layout(); fig.savefig(Path(out) / "R2_1_rebase.png", dpi=150); plt.close(fig)


def connectors(an, out):
    fig, axs = plt.subplots(1, 2, figsize=(12, 3.8))
    for ax, dom in zip(axs, ("2d", "3d")):
        c = json.loads(Path(an, f"R2_phys_{dom}.json").read_text())["connectors"]
        xs, labs = 0, []
        for grp, s in c["summary"].items():
            for b, v in s.items():
                if not isinstance(v, dict):
                    continue
                lo, hi = v["wilson"] or [v["rate"], v["rate"]]
                col = MUTED if b.strip("[]").split(",")[-1].strip() == b.strip("[]").split(",")[0].strip() and "," not in b else A
                ax.bar(xs, v["rate"], 0.7, color=B if grp == "m2_conn_fail" else (MUTED if b in ("[2]", "[3]") else A))
                ax.errorbar([xs], [v["rate"]], yerr=[[v["rate"] - lo], [hi - v["rate"]]], fmt="none", color=INK, capsize=2)
                ax.text(xs, 0.03, f"{v['x1']}/{v['decided']}", ha="center", fontsize=6.5, color="white")
                labs.append(f"{grp}\n{b}"); xs += 1
        g = c["gate"]
        ax.axhline(0.9, color=B, ls=":", lw=0.8)
        ax.set_xticks(range(len(labs))); ax.set_xticklabels(labs, fontsize=6, rotation=60, ha="right"); ax.set_ylim(0, 1.05)
        ax.set_title(f"{dom.upper()}: split verified {g['split_x1']}/{g['split_runs']} = {g['split_rate']} {g['wilson']} -> {g['decision']}", fontsize=8.5, loc="left", color=INK)
        ax.set_ylabel("X verified rate (same sequence)", fontsize=8, color=MUTED); _style(ax)
    fig.suptitle("R2.2 continuous vs chunked execution with verified q_ref returns (grey = continuous re-verification, orange = continuous failed at connector)", fontsize=9.5, x=0.01, ha="left", color=INK)
    fig.tight_layout(); fig.savefig(Path(out) / "R2_2_connectors.png", dpi=150); plt.close(fig)


def conn_traj(out):
    """ACTUAL teacher witnesses (joint space): one 3D all-singleton run that failed at a q_ref connector, one that succeeded, one 2D split failure."""
    import sys as _s
    _s.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import viz as VZ
    R = Path("/home/projects/long-horizon/naren_workspace/fig3")
    rows3 = [json.loads(l) for l in open(R / "r2/phys_3d.jsonl")]
    rows2 = [json.loads(l) for l in open(R / "r2/phys_2d.jsonl")]
    fail3 = next(r for r in rows3 if "singletons" in r["key"] and (r.get("X") or {}).get("x") == 0 and "boundary" in str(r["X"].get("phase")))
    ok3 = next(r for r in rows3 if "singletons" in r["key"] and (r.get("X") or {}).get("x") == 1)
    fail2 = next(r for r in rows2 if r["key"].startswith("C|m2_pos") and (r.get("X") or {}).get("x") == 0 and "boundary" in str(r["X"].get("failed_phase")))
    fig, axs = plt.subplots(3, 1, figsize=(11, 8))
    for ax, r, dom in ((axs[0], ok3, "3d"), (axs[1], fail3, "3d"), (axs[2], fail2, "2d")):
        items = []
        for st in r["X"]["trace"]:
            if dom == "3d":
                z = np.load(R / "store/witnesses" / st["witness"][:2] / f"{st['witness']}.npz") if st.get("witness") else None
                if z is None:
                    continue
                items.append({"kind": st["kind"], "q": z["q"] if st["kind"] == "move" else z["connector_q"], "label": "q_ready" if st["kind"] != "move" else ""})
            else:
                z = np.load(R / "w2d/witnesses" / st["witness"][:2] / f"{st['witness']}.npz")
                items.append({"kind": st["kind"], "q": z["q"], "label": f"q_ref ({st.get('how')})" if st["kind"] != "move" else ""})
        VZ._joint_panel(ax, items, f"{r['key'][:70]}  X={r['X']['x']} " + (f"FAILED at {r['X'].get('phase') or r['X'].get('failed_phase')} ({r['X'].get('status') or r['X'].get('teacher_status')})" if r["X"]["x"] == 0 else "VERIFIED"),
                        7 if dom == "3d" else 3)
        if r["X"]["x"] == 0:
            ax.text(0.99, 0.9, "next connector to q_ref: no collision-free plan within budget -> X = 0 (never relabelled)", transform=ax.transAxes, ha="right", fontsize=8, color=B)
    fig.suptitle("R2.2 ACTUAL teacher witnesses in joint space (3D: MuJoCo-executed SHELF66V3 plans; 2D: geometry-certified records). Grey = executed connector to q_ref. Not a render.",
                 fontsize=9, x=0.01, ha="left", color=INK)
    fig.tight_layout(); fig.savefig(Path(out) / "R2_2_connector_trajectories.png", dpi=150); plt.close(fig)


if __name__ == "__main__":
    if sys.argv[1] == "audit":
        audit(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "r21":
        an, out, jobs = sys.argv[2], sys.argv[3], sys.argv[4]
        for dom in ("2d", "3d"):
            scorer(dom, an, out); matched(dom, an, out, jobs)
        retarget(an, out); rebase(an, out); connectors(an, out); conn_traj(out)
