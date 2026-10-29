"""Local research track (approachD_local_parallel_research_instructions_v1_3): A/B/C/D comparison from ARCHIVED P17 records, visual
explanation figures, and (below) the bounded G2c-lite catalog pilot and the solver-free D / geometry / uniform ordering pilot.

Everything in L1 is recomputed from saved records (runs/p17/eval/P17_PROSPECTIVE.json, sealed execution files, committed P17 evidence);
no historical teacher, label, checkpoint or report is rerun or modified. Historical P17 used solver-based execution; the AD_PRECOMPILED
backend is different and is reported in separate, labelled panels."""
from __future__ import annotations

import collections
import importlib.util
import json
from itertools import product
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import config as cf  # noqa: E402

OUT, FIG = Path("runs/approach_d/local"), Path("visualizations/approach_d/local_comparison")
P17 = "runs/p17/eval/P17_PROSPECTIVE.json"
ARMS = {"A": "A", "B": "LB", "C": "P13:K-C"}                 # the exact historical arms of the P17 matched comparison
BASE = {"geometry heuristic (choose one)": "geometry", "random catalogue entry": "random", "never move": "empty_always"}
GUIDES = ["Dp17", "Dp17-norec", "geometry", "geometry-norec", "uniform"]
COL = {"A": "#b0417a", "B": "#2a78d6", "C": "#8a5a00", "D": "#1baf7a", "base": "#9a9890", "ok": "#0ca30c", "bad": "#d03b3b", "warn": "#ec835a"}


def rd(p):
    return json.loads(Path(p).read_text())


def feas(status, replay=True):
    """Historical operational convention (PoC takeaway): FEASIBLE iff VERIFIED (+ replay); CERTIFIED / UNKNOWN / budget count as not."""
    return status == "VERIFIED" and bool(replay)


# ------------------------------------------------------------------ L1: archived comparison, recomputed
def archived() -> dict:
    P = rd(P17)
    M = P["matched"]
    F = [k for k, r in M.items() if feas(r["original"])]
    I = [k for k, r in M.items() if not feas(r["original"])]

    def arm(a):
        ch = lambda k: M[k]["b"][a]["choice"]  # noqa: E731
        flag = lambda k: not ch(k).endswith(":empty")  # noqa: E731   (a repair OR an abstention flags the scene as blocked)
        act = lambda k: flag(k) and ch(k) != "ABSTAIN"  # noqa: E731
        fix = lambda k: act(k) and feas(M[k]["b"][a]["status"], M[k]["b"][a].get("replay"))  # noqa: E731
        mv = [len(ch(k).split(":")[-1].split(".")) for k in I if fix(k)]
        return {"detected": [sum(map(flag, I)), len(I)], "false_alarms": [sum(map(flag, F)), len(F)], "resolved": [sum(map(fix, I)), len(I)],
                "needless_moves_on_feasible": [sum(map(act, F)), len(F)], "mean_moves_when_resolved": float(np.mean(mv)) if mv else None,
                "abstained_on_infeasible": sum(ch(k) == "ABSTAIN" for k in I)}
    out = {"roster": {"roots": len(M), "feasible": len(F), "infeasible": len(I), "original_status": dict(collections.Counter(r["original"]
                                                                                                                      for r in M.values()))},
           "arms": {lab: arm(a) for lab, a in {**ARMS, **BASE}.items()}, "guides": {}}
    for g in GUIDES + ["D", "Dp16", "Dp16-norec"]:
        sol = {k for k in M if M[k]["d"][g]["found"] and M[k]["d"][g]["replay"]}
        res = [k for k in I if k in sol and M[k]["d"][g]["moves"] >= 1]
        out["guides"][g] = {"solved": [len(sol), len(M)], "resolved_infeasible": [len(res), len(I)],
                            "moved_on_feasible": [sum(k in sol and M[k]["d"][g]["moves"] >= 1 for k in F), len(F)],
                            "mean_moves_when_resolved": float(np.mean([M[k]["d"][g]["moves"] for k in res])) if res else None}
    S = lambda g: {k for k in M if M[k]["d"][g]["found"] and M[k]["d"][g]["replay"]}  # noqa: E731
    out["paired"] = {f"{a} vs {b}": {"both": len(S(a) & S(b)), "only_" + a: len(S(a) - S(b)), "only_" + b: len(S(b) - S(a)),
                                     "neither": len(M) - len(S(a) | S(b))} for a, b in (("Dp17-norec", "geometry-norec"), ("Dp17", "geometry"),
                                                                                         ("Dp17-norec", "uniform"))}
    rows = P["d"]["all_roots"]["disagreement"]["rows"]
    out["first_move_disagreement"] = {"roots_first_move_differs": sum(r["first_differs"] for r in rows),
                                      "of_which_outcome_differs": sum(r["first_differs"] and r["outcome"][0] != r["outcome"][1] for r in rows),
                                      "pair": "Dp17 vs geometry", "nodes_to_first_plan": {g: P["d"]["all_roots"]["effort_first_plan"][g]["nodes_to_first_mean"]
                                                                                           for g in GUIDES}}
    y = np.array([0 if feas(M[k]["original"]) else 1 for k in M])
    p = np.array([M[k]["d_pfeas"]["Dp17"] for k in M])
    auc = lambda pos, neg: float(np.mean([(a > b) + 0.5 * (a == b) for a, b in product(pos, neg)]))  # noqa: E731
    dec = np.array([M[k]["original"] != "UNKNOWN_PLANNER" for k in M])
    off = P["d"]["offline"]["Dp17"]["PARKING_LATTICE_V1"]
    out["D_classifier"] = {"detected_p<0.5": [int(np.sum(p[y == 1] < 0.5)), int(np.sum(y == 1))], "false_alarms_p<0.5": [int(np.sum(p[y == 0] < 0.5)),
                                                                                                                     int(np.sum(y == 0))],
                           "auroc_roster90_operational": auc(p[y == 0], p[y == 1]), "auroc_roster_decided_only": auc(p[dec & (y == 0)], p[dec & (y == 1)]),
                           "n_decided_roster": int(dec.sum()), "offline_auroc_140_decided_P17_test": off["auroc"], "offline_blocker_f1_31_masks": off["blocker_f1"],
                           "roc": _roc(p, y)}
    OUT.mkdir(parents=True, exist_ok=True)
    cf.write_json(OUT / "ARCHIVED_P17.json", out)
    return out


def _roc(p, y):
    th = np.unique(np.concatenate([[-1, 2], p]))
    return [[float(np.mean(p[y == 0] < t)), float(np.mean(p[y == 1] < t))] for t in th]      # (false-alarm rate, detection rate), flag = p < t


# ------------------------------------------------------------------ figures
def _style():
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


def fig_methods(dst=FIG):
    """01: what each approach learns, how it chooses a correction, how the choice is checked (P17 implementation map / 0094 / 0098)."""
    _style()
    cols = [("A", "A (retrained P13 architecture)", ["Learns: local endpoint penalties U, V + a GRU over the", "ordered sequence -> task logit u_A(r) per repair r",
                                                       "E_A(r) = sum U + sum V + lambda softplus(-u_A(r))"],
             ["Scores every catalogue repair; EMPTY if p(empty) >= t0,", "else fewest-move admitted repair, else ABSTAIN"],
             ["one score per whole sequence;", "explanations only by re-scoring"]),
            ("B", "B (lean B, 'LB', production)", ["Learns: Bernoulli outcome variables z0 (no move),", "zS[I] (scene edits), zR (ordered repair), zO[t]",
                                                    "(omissions); P(z) = P_S(z_s) P_Q(z_q)  (no coupling)"],
             ["Same calibrated rule over the same finite catalogue"], ["production drops couplings; the coupled", "LB+G did not replicate (resolved 23/63)"]),
            ("C", "C (historical P13:K-C checkpoint)", ["Learns: B's outcome variables + couplings, with", "A's GRU as the order factor (frozen in P13)"],
             ["Same calibrated rule"], ["frozen P13 checkpoint,", "not retrained on P16/P17 data"]),
            ("D", "D (Dp17, pairless)", ["Learns: p_T = sigma(u(S, T, g_T, q)) for the ORIGINAL target", "and P(b | y0 = 0) = prod Bernoulli(sigma(a_i)) blockers",
                                         "loss: BCE(p_T, y) + 2 * masked blocker NLL"],
             ["Chooses NO sequence: reorders movers in a search by", "(1 - p_T) * marg_i, re-querying D for T after each move"],
             ["no search-success gain over geometry", "(norec: 71 = 71 of 90 roots)"])]
    fig = plt.figure(figsize=(17, 6.6))
    fig.text(0.015, 0.965, "Four approaches, one shared physics backend (historical P17)", fontsize=15, weight="bold", va="top")
    fig.text(0.015, 0.915, "Every chosen correction is executed by the same certified solver-based provider and independently replayed; "
                           "a plan counts only if its replay is CLEAR.", fontsize=10, color="#52514e", va="top")
    for i, (k, name, learns, choose, lim) in enumerate(cols):
        x = 0.015 + i * 0.247
        ax = fig.add_axes([x, 0.13, 0.235, 0.74])
        ax.axis("off")
        ax.add_patch(plt.Rectangle((0, 0), 1, 1, fc="#fcfcfb", ec=COL[k], lw=2.2, transform=ax.transAxes))
        ax.text(0.04, 0.95, name, fontsize=11.5, weight="bold", color=COL[k], va="top", transform=ax.transAxes)
        y = 0.84
        for head, lines in (("What is learned", learns), ("How a correction is chosen", choose)):
            ax.text(0.04, y, head, fontsize=9.5, weight="bold", va="top", transform=ax.transAxes)
            y -= 0.075
            for ln in lines:
                ax.text(0.05, y, ln, fontsize=8.6, va="top", transform=ax.transAxes)
                y -= 0.062
            y -= 0.03
        ax.text(0.04, 0.33, "Detection used below", fontsize=9.5, weight="bold", va="top", transform=ax.transAxes)
        ax.text(0.05, 0.26, "p_T < 0.5 (classifier)" if k == "D" else "chosen query is not EMPTY", fontsize=8.6, va="top", transform=ax.transAxes)
        ax.text(0.04, 0.17, "Limitation", fontsize=9.5, weight="bold", color="#7a3030", va="top", transform=ax.transAxes)
        for j, ln in enumerate(lim):
            ax.text(0.05, 0.105 - 0.062 * j, ln, fontsize=8.6, color="#7a3030", va="top", transform=ax.transAxes)
    fig.text(0.015, 0.06, "Not learned by any approach: object destinations (scene-only slot rule), IK, trajectories, swept volumes. "
                          "D additionally does not learn obstacle ORDER or WHICH sequence to execute: search does.", fontsize=9.5, va="top")
    p = dst / "01_methods.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    return p


def fig_outcomes(a, dst=FIG):
    """02: matched archived outcomes with denominators (old operational convention)."""
    _style()
    rows = [("A", a["arms"]["A"], COL["A"]), ("B  (LB)", a["arms"]["B"], COL["B"]), ("C  (P13:K-C)", a["arms"]["C"], COL["C"]),
            ("D  (Dp17 classifier + D-guided search)", None, COL["D"]), ("geometry heuristic (choose one)", a["arms"]["geometry heuristic (choose one)"], COL["base"]),
            ("geometry-guided search", "geometry", COL["base"]), ("uniform-order search", "uniform", COL["base"]),
            ("random catalogue entry", a["arms"]["random catalogue entry"], COL["base"]), ("never move", a["arms"]["never move"], COL["base"])]
    dc, g = a["D_classifier"], a["guides"]

    def vals(lab, r):
        if lab.startswith("D"):
            return [dc["detected_p<0.5"], dc["false_alarms_p<0.5"], g["Dp17"]["resolved_infeasible"], g["Dp17"]["moved_on_feasible"]]
        if isinstance(r, str):
            return [None, None, g[r]["resolved_infeasible"], g[r]["moved_on_feasible"]]
        return [r["detected"], r["false_alarms"], r["resolved"], r["needless_moves_on_feasible"]]
    heads = ["Blockage detected  (higher is better)", "False alarm on feasible  (lower is better)", "Blocked task resolved  (higher)",
             "Needless relocation on feasible  (lower)"]
    fig, axs = plt.subplots(1, 4, figsize=(17, 5.4), sharey=True, constrained_layout=True)
    y = np.arange(len(rows))
    for j, ax in enumerate(axs):
        for i, (lab, r, c) in enumerate(rows):
            v = vals(lab, r)[j]
            if v is None:
                ax.text(0.01, i, "n/a (search always verifies first)" if j < 2 else "", va="center", fontsize=8, color="#7a7975")
                continue
            ax.barh(i, v[0] / v[1], color=c, height=0.62)
            ax.text(v[0] / v[1] + 0.015, i, f"{v[0]}/{v[1]}", va="center", fontsize=8.5)
        ax.set_xlim(0, 1.18)
        ax.set_title(heads[j], fontsize=9.5, loc="left")
        ax.set_xticks([0, 0.5, 1], ["0", "50%", "100%"])
    axs[0].set_yticks(y, [r[0] for r in rows], fontsize=9)
    axs[0].invert_yaxis()
    fig.suptitle(f"Historical P17 — archived shared evaluation: {a['roster']['roots']} roots, {a['roster']['feasible']} operationally feasible / "
                 f"{a['roster']['infeasible']} infeasible (UNKNOWN counted as infeasible, old convention)", fontsize=12, x=0.01, ha="left")
    p = dst / "02_archived_outcomes.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    return p


def fig_d_vs_geometry(a, dst=FIG):
    """03: where learning helps (diagnosis) and where it does not (search success)."""
    _style()
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(17, 5.2), constrained_layout=True, gridspec_kw={"width_ratios": [1, 1.1, 1]})
    roc = np.array(a["D_classifier"]["roc"])
    a1.plot(roc[:, 0], roc[:, 1], color=COL["D"], lw=2, label=f"D (Dp17) p_T threshold sweep, AUROC {a['D_classifier']['auroc_roster90_operational']:.2f}")
    for lab, k in (("A", "A"), ("B", "B"), ("C", "C"), ("geo", "geometry heuristic (choose one)")):
        r = a["arms"][k]
        x, yv = r["false_alarms"][0] / r["false_alarms"][1], r["detected"][0] / r["detected"][1]
        a1.scatter([x], [yv], s=60, color=COL.get(lab, COL["base"]), zorder=5)
        a1.annotate(lab, (x, yv), textcoords="offset points", xytext=(6, -12), fontsize=9)
    d = a["D_classifier"]
    a1.scatter([d["false_alarms_p<0.5"][0] / d["false_alarms_p<0.5"][1]], [d["detected_p<0.5"][0] / d["detected_p<0.5"][1]], s=70, marker="D", color=COL["D"],
               zorder=6, label="D at p_T < 0.5")
    a1.plot([0, 1], [0, 1], color="#cccccc", lw=1, ls="--")
    a1.set(xlabel="false-alarm rate on the 27 feasible roots", ylabel="detection rate on the 63 blocked roots", xlim=(-0.02, 1.02), ylim=(-0.02, 1.02))
    a1.legend(fontsize=8, loc="lower right", frameon=False)
    a1.set_title("(a) Learning helps DIAGNOSIS: D's original-target classifier\n"
                 f"(offline, 140 decided P17-test originals: AUROC {d['offline_auroc_140_decided_P17_test']:.3f})", fontsize=9.5, loc="left")
    g = a["guides"]
    names = ["Dp17", "Dp17-norec", "geometry", "geometry-norec", "uniform"]
    cols = [COL["D"], COL["D"], COL["base"], COL["base"], "#c3c2b7"]
    v = [g[n]["solved"][0] for n in names]
    a2.bar(range(5), v, color=cols, width=0.62)
    for i, x in enumerate(v):
        a2.text(i, x + 0.6, f"{x}/90", ha="center", fontsize=9)
    a2.set_xticks(range(5), ["D-guided\n(Dp17)", "D-guided\nno recursion", "geometry", "geometry\nno recursion", "uniform"], fontsize=8.5)
    a2.set_ylim(60, 75)
    a2.set_ylabel("roots solved (verified plan, replay CLEAR)")
    a2.set_title("(b) ...but not SEARCH SUCCESS: identical domain, budget,\nsearch and replay; only the obstacle ORDER differs", fontsize=9.5, loc="left")
    pr = a["paired"]["Dp17-norec vs geometry-norec"]
    fm = a["first_move_disagreement"]
    a3.axis("off")
    txt = [("Dp17-norec vs geometry-norec (same 90 roots)", True), (f"solved by both: {pr['both']}", False),
           (f"only D-guided: {pr['only_Dp17-norec']}      only geometry: {pr['only_geometry-norec']}", False), (f"solved by neither: {pr['neither']}", False),
           ("", False), ("Dp17 vs geometry, first relocation tried", True), (f"differs on {fm['roots_first_move_differs']} of 90 roots", False),
           (f"changes the outcome on {fm['of_which_outcome_differs']} of those", False),
           (f"mean nodes to first plan: D {fm['nodes_to_first_plan']['Dp17-norec']:.1f} vs geometry {fm['nodes_to_first_plan']['geometry-norec']:.1f} (norec)", False),
           ("", False), ("Why: the search verifies T first, enumerates every", True), ("mover x slot at each depth within a budget that is rarely", False),
           ("exhausted, so ordering changes WHICH plan is found first,", False), ("not WHETHER one is found. Nearest-to-target geometry", False),
           ("already puts the true blockers early.", False)]
    yy = 0.97
    for t, b in txt:
        a3.text(0.0, yy, t, fontsize=9.5 if b else 9, weight="bold" if b else "normal", va="top", transform=a3.transAxes)
        yy -= 0.062
    a3.set_title("(c) The null result, unpacked", fontsize=9.5, loc="left")
    fig.suptitle("Historical P17 — archived shared evaluation: D versus non-learned guidance", fontsize=12, x=0.01, ha="left")
    p = dst / "03_d_vs_geometry.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    return p


def _poc():
    spec = importlib.util.spec_from_file_location("poc_build", "PoC-takeaway/build.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)                     # read-only use of its drawing helpers; nothing is written into PoC-takeaway/
    return m


def fig_scenes(dst=FIG):
    """04: authentic scenes. Top: committed P17 mechanism evidence (verified witnesses + recorded counterfactuals). Bottom: recorded P17
    test decisions of the matched comparison (choices as recorded, statuses as recorded)."""
    import p17_data as pdat
    from scene import scene_from_dict
    B = _poc()
    _style()
    cfg, robot = B.sim()
    blue, red, grey = "#2a78d6", COL["bad"], "#7a7975"
    fig, axs = plt.subplots(2, 4, figsize=(18, 9.6), constrained_layout=True)
    ev_panels = [("M0", "Feasible clutter: moving the decoy is unneeded", "decoy"), ("M1", "One genuine blocker", None),
                 ("M2", "Two blockers: neither move alone clears T", None), ("M4", "Order matters: reversed order is certified infeasible", "reverse")]
    for ax, (tag, cap, show) in zip(axs[0], ev_panels):
        ev = rd(f"runs/p17/mechanisms/evidence/{tag}.json")
        ex = rd("runs/p17/mechanisms/EXEMPLARS.json")[tag]
        root = pdat._plan(ex["split"])["roots"][ev["root"]]
        s = scene_from_dict(root["scene"])
        B.draw_scene(ax, s, root["goal_cell"], robot, set(root.get("fixed", [])), robot_alpha=0.45, view=B.VIEW_SCENE)
        cen, cells = s.lattice.center, {o.id: o.cell for o in s.objects}
        seq = ev["positive"]["sequence"]
        for j, (o, d) in enumerate(seq):
            B.arrow(ax, cen(cells[o]), cen(d), blue, j + 1 if len(seq) > 1 else None)
            B.ghost(ax, cen(d), blue)
            cells[o] = d
        cfx = ev.get("counterfactuals") or []
        if show == "decoy" and cfx:
            o, d = cfx[0]["sequence"][0]
            B.arrow(ax, s.get(o).xy_m, cen(d), grey, dashed=True, lw=2)
            ax.text(*cen(d), "unneeded", fontsize=9, color=grey, ha="center", va="top", zorder=12)
        if show == "reverse" and len(seq) == 2:
            ax.text(0.02, 0.02, f"verified: {seq[0][0]} then {seq[1][0]}\nreverse order: certified infeasible", transform=ax.transAxes, fontsize=8.5, va="bottom")
        ax.set_title(f"{cap}\n[{tag}: {ev['root']}]", fontsize=9.5, loc="left")
    M = rd(P17)["matched"]
    dec = rd("runs/p17/data/p17test/sealed_exec_d_d0.json")
    roots = pdat._plan("p17test")["roots"]
    cases = [("p13_2026290000", "LB", "Feasible as is: B relocates o03 needlessly\n(move verified, but the task never needed it)"),
             ("p13_2026290020", "LB", "Blocked: A and B choose o00>28, o02>59 -> not verified"),
             ("p13_2026290020", "Dp17", "Same root, D-guided search: o02>59, o03>52 verified\n(geometry search finds this same plan)"),
             ("p13_2026290020", "geometry-norec", "Same root, geometry search (no recursion):\no03>36, o02>59 verified, LESS travel than D's")]
    for ax, (k, who, cap) in zip(axs[1], cases):
        root = roots[k]
        s = scene_from_dict(root["scene"])
        B.draw_scene(ax, s, root["goal_cell"], robot, set(root.get("fixed", [])), robot_alpha=0.45, view=B.VIEW_SCENE)
        cen, cells = s.lattice.center, {o.id: o.cell for o in s.objects}
        if who in ("LB", "A"):
            ch = M[k]["b"][who]["choice"].split(":")[-1]
            seq = [(x.split(">")[0], int(x.split(">")[1])) for x in ch.split(".")] if ch not in ("empty", "ABSTAIN") else []
            ok = feas(M[k]["b"][who]["status"], M[k]["b"][who].get("replay"))
            color = (COL["warn"] if feas(M[k]["original"]) else blue) if ok else red
            status = M[k]["b"][who]["status"]
        else:
            st = dec[k]["d"][who]
            seq, ok, color, status = [(o, d) for o, d, *_ in st["steps"]], st["replay"], blue, "VERIFIED + replay CLEAR"
        for j, (o, d) in enumerate(seq):
            B.arrow(ax, cen(cells[o]), cen(d), color, j + 1 if len(seq) > 1 else None, cross=not ok and j == len(seq) - 1)
            B.ghost(ax, cen(d), color)
            cells[o] = d
        ax.text(0.02, 0.02, f"original: {M[k]['original']}\nrecorded: {status}", transform=ax.transAxes, fontsize=8.5, va="bottom")
        ax.set_title(f"{cap}\n[P17 test {k}]", fontsize=9.5, loc="left")
    fig.suptitle("Historical P17 — authentic scenes. Top: committed mechanism evidence (verified witnesses). Bottom: recorded decisions of the "
                 "matched P17 test comparison. Orange target, dashed ring = its goal; numbers = move order.", fontsize=11, x=0.01, ha="left")
    p = dst / "04_scenes.png"
    fig.savefig(p, dpi=130)
    plt.close(fig)
    return p


def l1() -> dict:
    FIG.mkdir(parents=True, exist_ok=True)
    a = archived()
    return {"archived": str(OUT / "ARCHIVED_P17.json"), "figures": [str(f) for f in (fig_methods(), fig_outcomes(a), fig_d_vs_geometry(a), fig_scenes())]}


if __name__ == "__main__":
    print(json.dumps(l1(), indent=1))


# ------------------------------------------------------------------ L2: G2c-lite catalog additions (offline only, bounded, predeclared)
import multiprocessing as mp  # noqa: E402
import time  # noqa: E402

DEV_PLAN = "runs/p16/data/dev/plan.json"
LKEYS = {"top_movers", "slots", "max_depth", "node_cap", "compile_attempts", "compile_cpu_s"}


def lcfg(path="approach_d.toml") -> dict:
    import tomllib
    with open(path, "rb") as f:
        c = tomllib.load(f)["local_pilot"]
    if set(c) != LKEYS:
        raise ValueError(f"invalid [local_pilot]: {sorted(set(c) ^ LKEYS)}")
    return c


_LC = lcfg()
LOCAL_BUDGET = {"compile_attempts": _LC["compile_attempts"], "cpu_s": _LC["compile_cpu_s"]}
TOP_MOVERS, SLOTS, MAX_DEPTH, NODE_CAP = _LC["top_movers"], _LC["slots"], _LC["max_depth"], _LC["node_cap"]


def dev_roots():
    """The fixed DEV set: every P16-labelled development root (runs/p16/data/dev/pilot_keys.json), no selection."""
    return sorted(rd("runs/p16/data/dev/pilot_keys.json"))


class Stub:
    """Scene-only container for p17_domain.slot_fn and p17_d.Guide (no planner, provider or IK is reachable through it)."""

    def __init__(self, root):
        import ad_compile as ac
        import p6_scenes as p6
        from scene import scene_from_dict
        P = rd(DEV_PLAN)["roots"][root]
        self.cfg, self.robot, _ = ac.setup()
        self.s0, self.goal_cell, self.scr = scene_from_dict(P["scene"]), P["goal_cell"], p6.Screens(self.cfg, self.robot)
        self.task = {"scene": P["scene"], "goal_cell": P["goal_cell"], "fixed_ids": [o.id for o in self.s0.objects if o.cell in set(P.get("fixed", []))],
                     "target": "t0", "key": root}

    def scene(self, cells, q):
        from dataclasses import replace
        return replace(self.s0, objects=tuple(replace(o, cell=cells[o.id], xy_m=self.s0.lattice.center(cells[o.id])) for o in self.s0.objects),
                       robot=replace(self.s0.robot, q_rad=tuple(map(float, q))))


def domain(root):
    """Finite search domain (same for every guide): the TOP_MOVERS P17 movers nearest T, each to its first SLOTS scene-only slots
    (p17_domain.slot_fn without library destinations), recomputed on every hypothetical occupancy; <= MAX_DEPTH relocations, no repeats."""
    import p17_domain as dm
    st = Stub(root)
    cells0 = {o.id: o.cell for o in st.s0.objects}
    mv, _ = dm.movers(st.task, cells0)
    f = dm.slot_fn(st, None, width=SLOTS, origin=cells0)
    return st, cells0, mv[:TOP_MOVERS], (lambda cells, o: f(cells, o)[:SLOTS])


def _ledger_spend(kind, attempts, cpu, note):
    f = OUT / "COMPILE_LEDGER.json"
    led = rd(f) if f.exists() else {"budget": LOCAL_BUDGET, "entries": []}
    used = (sum(e["attempts"] for e in led["entries"]), sum(e["cpu_s"] for e in led["entries"]))
    if used[0] + attempts > LOCAL_BUDGET["compile_attempts"] or used[1] + cpu > LOCAL_BUDGET["cpu_s"]:
        raise RuntimeError(f"local compile budget exceeded: {used} + ({attempts}, {cpu:.0f})")
    led["entries"].append({"kind": kind, "attempts": attempts, "cpu_s": cpu, "note": note})
    cf.write_json(f, led)


def _catalog_all():
    import ad_compile as ac
    T = ac.load_catalog()
    for d in (Path("runs/approach_d/g2b/catalog"), OUT / "catalog"):
        for f in sorted(d.glob("CATALOG_*.json")) if d.exists() else []:
            T.update(ac.load_catalog(f.stem, d))
    return T


def _run_jobs(jobs, name, kind, workers=8):
    import ad_compile as ac
    with mp.get_context("spawn").Pool(workers) as pool:
        outs = pool.map(ac.compile_job, jobs, chunksize=1)
    atts = [{**a, "qid": j["qid"]} for j, o in zip(jobs, outs) for a in o["attempts"]]
    real = [a for a in atts if not a["termination_reason"].startswith("DUPLICATE")]
    cpu = sum(a["cpu_s"] for a in real) + sum(o["screen"]["cpu_s"] for o in outs) + sum(r.get("sweep_cpu_s", 0) for o in outs for r, _ in o["templates"])
    _ledger_spend(kind, len(real), cpu, f"{len(jobs)} jobs")
    cat = ac.save_catalog([x for o in outs for x in o["templates"]], atts, name, OUT / "catalog")
    return {"jobs": len(jobs), "attempts": len(real), "compiled": sum(a["compiled"] for a in real), "cpu_s": cpu, "templates": len(cat["templates"])}


def compile_search_pairs(workers=8) -> dict:
    """Relocation templates for the search domain at the ORIGINAL state of every DEV root (pairs already covered by >= 3 catalogued
    templates are skipped): <= 1 exact-cell witness, 1 relative-family mode, 2 branch-spread templates."""
    import ad_g2b as g2
    T = _catalog_all()
    have = collections.Counter((t["src"], t["dst"]) for t in T.values() if t["kind"] != "ENTRY")
    pairs = collections.OrderedDict()
    for k in dev_roots():
        st, cells0, mv, sl = domain(k)
        for o in mv:
            for d in sl(cells0, o):
                if have[(cells0[o], d)] < 3:
                    pairs.setdefault((k, o), (cells0[o], d)) if (k, o) not in pairs else pairs.setdefault((k, f"{o}#{d}"), (cells0[o], d))
    jobs = [{**j, "direct_k": 2, "seeds": [s for s in j["seeds"] if s["mode"] == j["seeds"][0]["mode"]][:2] if j["seeds"] else []}
            for j in g2.chain_jobs(pairs)]
    return _run_jobs(jobs, "CATALOG_LOCAL_SEARCH", "search_pair_templates", workers)


def compile_target_diversity(workers=8) -> dict:
    """Original-target T only: per DEV root, one template per (pick branch, place branch, 60-degree pick sector) not yet catalogued, <= 6."""
    T = _catalog_all()
    jobs = []
    for k in dev_roots():
        st = Stub(k)
        src, dst = st.s0.get("t0").cell, st.goal_cell
        skip = [tuple(round(x, 6) for x in (t["grasp"][0][0], t["grasp"][0][1], t["grasp"][1][0], t["grasp"][1][1])) for t in T.values()
                if t["kind"] != "ENTRY" and (t["src"], t["dst"]) == (src, dst) and t.get("grasp")]
        jobs.append({"qid": f"T:{k}", "src": src, "dst": dst, "kind": "TARGET", "direct_k": 6, "direct": ("access",), "seeds": [], "exact": [],
                     "skip": skip})
    return _run_jobs(jobs, "CATALOG_LOCAL_TARGET", "target_diversity_templates", workers)


def _conn_job(job):
    import ad_compile as ac
    cfg, robot, p = ac.setup()
    c0 = time.process_time()
    a, term, neg = ac.compile_connector(cfg, robot, p, job["qa"], job["qb"], job["key"])
    return {**job, "arrays": a, "term": term, "neg": neg, "cpu_s": time.process_time() - c0}


def compile_connectors(workers=8, per_pair=2) -> dict:
    """Bypass-home connectors, chosen without looking at any scene outcome: for every DEV root and every search-domain relocation pair,
    from the retreat-end node of its first catalogued template to the per_pair nearest (joint L-inf) approach-start nodes of that root's
    target templates."""
    import ad_compile as ac
    T = _catalog_all()
    jobs, seen = [], set()
    for k in dev_roots():
        st, cells0, mv, sl = domain(k)
        tgt = [t for t in T.values() if t["kind"] != "ENTRY" and (t["src"], t["dst"]) == (st.s0.get("t0").cell, st.goal_cell)]
        starts = {ac.qid(s["core"]["q"][0]): s["core"]["q"][0] for s in (ac.segment(t["arrays"]) for t in tgt)}
        for o in mv:
            for d in sl(cells0, o):
                rel = sorted((t for t in T.values() if t["kind"] != "ENTRY" and (t["src"], t["dst"]) == (cells0[o], d)), key=lambda t: t["id"])
                if not rel or not starts:
                    continue
                qa = ac.segment(rel[0]["arrays"])["core"]["q"][-1]
                for n, qb in sorted(starts.items(), key=lambda x: (float(np.max(np.abs(x[1] - qa))), x[0]))[:per_pair]:
                    if (ac.qid(qa), n) not in seen:
                        seen.add((ac.qid(qa), n))
                        jobs.append({"root": k, "from_template": rel[0]["id"], "qa": qa, "qb": qb, "key": f"local/conn/{ac.qid(qa)}>{n}"})
    with mp.get_context("spawn").Pool(workers) as pool:
        outs = pool.map(_conn_job, jobs, chunksize=1)
    cpu = sum(o["cpu_s"] for o in outs)
    _ledger_spend("bypass_home_connectors", len(outs), cpu, f"{len(outs)} retreat-end -> target approach-start")
    ok = [o for o in outs if o["arrays"] is not None]
    np.savez_compressed(OUT / "catalog" / "CONNECTORS_LOCAL.npz", **{f"c{i}__{f}": np.asarray(v) for i, o in enumerate(ok) for f, v in
                                                                      {**o["arrays"], "qa": o["qa"], "qb": o["qb"]}.items()})
    cf.write_json(OUT / "catalog" / "CONNECTORS_LOCAL.json", [{"root": o["root"], "from_template": o["from_template"], "compiled": o["arrays"] is not None,
                                                                "termination": o["term"], "negative_kind": o["neg"], "cpu_s": o["cpu_s"]} for o in outs])
    return {"attempts": len(outs), "compiled": len(ok), "cpu_s": cpu}


def _connectors():
    f = OUT / "catalog" / "CONNECTORS_LOCAL.npz"
    if not f.exists():
        return []
    z, meta = np.load(f), [m for m in rd(OUT / "catalog" / "CONNECTORS_LOCAL.json") if m["compiled"]]
    out = []
    for i, m in enumerate(meta):
        a = {k.split("__")[1]: z[k] for k in z.files if k.startswith(f"c{i}__")}
        out.append((a.pop("qa"), a.pop("qb"), a, {"origin_rule": "LOCAL_BYPASS_HOME_V1", "root": m["root"], "from_template": m["from_template"]}))
    return out


def build_catalogs() -> dict:
    """C1 = G2a + G2b + search-domain templates; C2 = C1 + target diversity; C3 = C2 + bypass-home connectors. Nested, so catalog gains are
    separable from guide gains."""
    import ad_compile as ac
    base = ac.load_catalog()
    for f in sorted(Path("runs/approach_d/g2b/catalog").glob("CATALOG_G2B*.json")):
        base.update(ac.load_catalog(f.stem, "runs/approach_d/g2b/catalog"))
    ent = [t for t in base.values() if t["kind"] == "ENTRY"]
    tpl = {i: t for i, t in base.items() if t["kind"] != "ENTRY"}
    s1 = ac.load_catalog("CATALOG_LOCAL_SEARCH", OUT / "catalog")
    s2 = ac.load_catalog("CATALOG_LOCAL_TARGET", OUT / "catalog")
    out = {}
    for name, T, extra in (("C1", {**tpl, **s1}, ()), ("C2", {**tpl, **s1, **s2}, ()), ("C3", {**tpl, **s1, **s2}, _connectors())):
        m = ac.build_graph(T, ent, OUT / "catalog", f"GRAPH_{name}", extra)
        out[name] = {"actions": len(m["actions"]), "connectors": len(m["connectors"]), "nodes": len(m["nodes"]), "rejected": len(m["rejected"]),
                     "hash": m["hash"], "validation_cpu_s": m["validation_cpu_s"]}
    cf.write_json(OUT / "CATALOGS.json", out)
    return out


# ------------------------------------------------------------------ L3: historical guides on the solver-free backend (matched pilot)
GUIDES_L3 = ["Dp17-norec", "geometry-norec", "uniform"]       # recursion variants excluded: they query D for temporary targets


def search(prov, guide, cells0, q0, movers, slots, max_depth=MAX_DEPTH, node_cap=NODE_CAP):
    """Verify-first iterative deepening over the finite domain, ordered ONLY by guide.order (the unchanged P17 Guide). Every relocation and
    the final target action come from the AD_PRECOMPILED provider (stored records, current-scene certification); first verified chain wins."""
    st = {"edges": 0, "goals": 0, "first_move": None}

    def dfs(cells, q, moved, chain, left):
        if left == 0:
            st["goals"] += 1
            r = prov.goal(cells, q)
            return chain + [r] if r["status"] == "SUCCESS" else None
        cands = [(o, d) for o in movers if o not in moved for d in slots(cells, o)]
        for o, d in guide.order(cells, q, frozenset(moved), cands):
            if st["edges"] >= node_cap:
                return None
            st["edges"] += 1
            if st["first_move"] is None:
                st["first_move"] = [o, d]
            e = prov.edges(cells, q, o, d)
            if e["status"] == "SUCCESS":
                r = dfs(e["cells"], prov.g.q[e["q_end"]], moved + [o], chain + [e], left - 1)
                if r:
                    return r
        return None
    for depth in range(max_depth + 1):
        chain = dfs(dict(cells0), np.asarray(q0, float), [], [], depth)
        if chain:
            steps = [(k, i, c["object"] if k == "action" else None) for c in chain for k, i in c["steps"]]
            rep = prov.verify_plan(cells0, q0, steps)
            return {"found": rep["status"] == "SUCCESS", "depth": depth, "moves": [[c["object"], c["dest"]] for c in chain[:-1]],
                    "replay": rep["status"], "trajectory_hash": rep.get("trajectory_hash"), **st}
    return {"found": False, "depth": None, "moves": None, "replay": None, **st}


def _pilot_job(item):
    import ad_g2b as g2
    import ad_provider as pv
    import ad_runtime as ar
    import p17_d as pd
    root, cat = item
    st, cells0, mv, sl = domain(root)
    g = pv.Graph(OUT / "catalog", f"GRAPH_{cat}")
    ri, member = g2._ri()
    excl = g2._excl(root)
    out = {}
    with ar.forbid("raise") as calls:
        for kind in GUIDES_L3:
            gd = pd.Guide(kind, st.task, st, mv)
            prov = pv.Precompiled(st.cfg, st.robot, st.s0, st.goal_cell, g, g2.Ranker(ri, member, excl, **g2.POLICIES["EXACT+REL_6x1+CATALOG"]),
                                  6, 2, "OFF", f"L3/{kind}")
            c0 = time.process_time()
            r = search(prov, gd, cells0, st.s0.robot.q_rad, mv, sl)
            out[kind] = {**r, "cpu_s": time.process_time() - c0, "d_calls": gd.d_calls, "provider": prov.stats()["counts"],
                         "trace": gd.trace[:3]}
    return root, cat, out, sum(calls.values())


def pilot(workers=12, cats=("C1", "C2", "C3"), name="PILOT_L3") -> dict:
    items = [(k, c) for k in dev_roots() for c in cats]
    with mp.get_context("spawn").Pool(workers) as pool:
        res = pool.map(_pilot_job, items, chunksize=1)
    labels = {}
    for f in sorted(Path("runs/p16/data/dev").glob("labels_v2w*.json")):
        labels.update(rd(f))
    rows = {f"{k}|{c}": {"root": k, "catalog": c, "p16_original": labels.get(k, {}).get("original", {}).get("status"), "guides": o}
            for k, c, o, _ in res}
    summ = {c: {g: {"found": sum(rows[f"{k}|{c}"]["guides"][g]["found"] for k in dev_roots()), "n": len(dev_roots()),
                    "edges": sum(rows[f"{k}|{c}"]["guides"][g]["edges"] for k in dev_roots()),
                    "certify_action": sum(rows[f"{k}|{c}"]["guides"][g]["provider"].get("certify_action", 0) for k in dev_roots()),
                    "d_calls": sum(rows[f"{k}|{c}"]["guides"][g]["d_calls"] for k in dev_roots()),
                    "cpu_s": round(sum(rows[f"{k}|{c}"]["guides"][g]["cpu_s"] for k in dev_roots()), 1)} for g in GUIDES_L3} for c in cats}
    out = {"domain": {"top_movers": TOP_MOVERS, "slots": SLOTS, "max_depth": MAX_DEPTH, "node_cap": NODE_CAP, "action_budget": 6, "max_hops": 2,
                      "policy": "EXACT+REL_6x1+CATALOG", "prefilter": "OFF"}, "forbidden_calls": sum(x[3] for x in res), "summary": summ, "rows": rows}
    cf.write_json(OUT / f"{name}.json", out)
    return {k: v for k, v in out.items() if k != "rows"}


def _attr_job(item):
    """Failure-source attribution (ordering-free): every state reachable in the finite domain with stored relocations (<= MAX_DEPTH), the
    target check at each state, and every relocation attempt, with the provider's per-attempt reasons."""
    import ad_g2b as g2
    import ad_provider as pv
    import ad_runtime as ar
    root, cat = item
    st, cells0, mv, sl = domain(root)
    g = pv.Graph(OUT / "catalog", f"GRAPH_{cat}")
    ri, member = g2._ri()
    prov = pv.Precompiled(st.cfg, st.robot, st.s0, st.goal_cell, g, g2.Ranker(ri, member, g2._excl(root), **g2.POLICIES["EXACT+REL_6x1+CATALOG"]),
                          6, 2, "OFF", "attribution")
    tgt, rel = collections.Counter(), collections.Counter()
    states, frontier = 0, [(dict(cells0), np.asarray(st.s0.robot.q_rad, float), [])]
    with ar.forbid("raise"):
        for depth in range(MAX_DEPTH + 1):
            nxt = []
            for cells, q, moved in frontier:
                states += 1
                r = prov.goal(cells, q)
                tgt["SUCCESS" if r["status"] == "SUCCESS" else "state_failed"] += 1
                for a in r["attempts"]:
                    tgt[a["reason"]] += 1
                if r["status"] == "FAILURE" and not r["attempts"]:
                    tgt[r["reason"]] += 1
                if depth == MAX_DEPTH:
                    continue
                for o in mv:
                    if o in moved:
                        continue
                    for d in sl(cells, o):
                        e = prov.edges(cells, q, o, d)
                        rel["SUCCESS" if e["status"] == "SUCCESS" else e["reason"]] += 1
                        if e["status"] == "SUCCESS":
                            nxt.append((e["cells"], prov.g.q[e["q_end"]], moved + [o]))
            frontier = nxt
    return root, cat, {"states": states, "target": dict(tgt), "relocation": dict(rel)}


def attribute(workers=12) -> dict:
    items = [(k, c) for k in dev_roots() for c in ("C1", "C2", "C3")]
    with mp.get_context("spawn").Pool(workers) as pool:
        res = pool.map(_attr_job, items, chunksize=1)
    rows = {f"{k}|{c}": v for k, c, v in res}
    summ = {}
    for c in ("C1", "C2", "C3"):
        t, r = collections.Counter(), collections.Counter()
        for k in dev_roots():
            t.update(rows[f"{k}|{c}"]["target"])
            r.update(rows[f"{k}|{c}"]["relocation"])
        summ[c] = {"states": sum(rows[f"{k}|{c}"]["states"] for k in dev_roots()), "target": dict(t), "relocation": dict(r),
                   "roots_with_target_success_somewhere": sum(rows[f"{k}|{c}"]["target"].get("SUCCESS", 0) > 0 for k in dev_roots())}
    out = {"summary": summ, "rows": rows}
    cf.write_json(OUT / "ATTRIBUTION_L3.json", out)
    return summ


def _avail_job(item):
    """Budget-free catalog availability at every state reachable in the domain (a diagnostic, not a runtime policy): how many stored target
    actions certify, and how many of those have a stored connector path that certifies from the robot's actual state."""
    import ad_g2b as g2
    import ad_provider as pv
    import ad_runtime as ar
    root, cat = item
    st, cells0, mv, sl = domain(root)
    g = pv.Graph(OUT / "catalog", f"GRAPH_{cat}")
    ri, member = g2._ri()
    prov = pv.Precompiled(st.cfg, st.robot, st.s0, st.goal_cell, g, g2.Ranker(ri, member, g2._excl(root), **g2.POLICIES["EXACT+REL_6x1+CATALOG"]),
                          6, 2, "OFF", "availability")
    rows, frontier = [], [(dict(cells0), np.asarray(st.s0.robot.q_rad, float), [])]
    with ar.forbid("raise"):
        for depth in range(MAX_DEPTH + 1):
            nxt = []
            for cells, q, moved in frontier:
                cand = g.by_pair.get((cells["t0"], st.goal_cell), [])
                core = [i for i in cand if prov._cert(i, cells, "t0")["ok"]]
                node = g.node_of(q)
                conn = [i for i in core if node and prov._connect(cells, node, g.actions[i]["from"])[0] is not None]
                rows.append({"depth": depth, "moved": moved, "target_actions": len(cand), "core_ok": len(core), "connected": len(conn),
                             "origins_core_ok": sorted({o for i in core for o in g.actions[i]["origins"]}), "node": node,
                             "core_ok_from": sorted({g.actions[i]["from"] for i in core})})
                if depth < MAX_DEPTH:
                    for o in mv:
                        if o not in moved:
                            for d in sl(cells, o):
                                e = prov.edges(cells, q, o, d)
                                if e["status"] == "SUCCESS":
                                    nxt.append((e["cells"], prov.g.q[e["q_end"]], moved + [o]))
            frontier = nxt
    return root, cat, rows


def availability(workers=12, cats=("C1", "C2", "C3"), name="AVAILABILITY_L2") -> dict:
    items = [(k, c) for k in dev_roots() for c in cats]
    with mp.get_context("spawn").Pool(workers) as pool:
        res = pool.map(_avail_job, items, chunksize=1)
    out = {"rows": {f"{k}|{c}": r for k, c, r in res}, "summary": {}}
    for c in cats:
        R = [x for k in dev_roots() for x in out["rows"][f"{k}|{c}"]]
        out["summary"][c] = {"states": len(R), "states_core_ok": sum(x["core_ok"] > 0 for x in R), "states_connected": sum(x["connected"] > 0 for x in R),
                             "roots_core_ok_somewhere": sum(any(x["core_ok"] for x in out["rows"][f"{k}|{c}"]) for k in dev_roots()),
                             "roots_connected_somewhere": sum(any(x["connected"] for x in out["rows"][f"{k}|{c}"]) for k in dev_roots()),
                             "target_actions_per_state": float(np.mean([x["target_actions"] for x in R]))}
    cf.write_json(OUT / f"{name}.json", out)
    return out["summary"]


def compile_state_connectors(workers=8) -> dict:
    """C4 (DEV-INFORMED, reported separately): for EVERY state of the C3 availability scan where a stored target action certifies but no
    stored connector path does, one offline connector from the robot's actual node (retreat end or root stratum) to each such action's
    approach-start node. No state is selected or skipped."""
    import ad_provider as pv
    A = rd(OUT / "AVAILABILITY_L2.json")["rows"]
    g = pv.Graph(OUT / "catalog", "GRAPH_C3")
    pairs = sorted({(x["node"], f) for k in dev_roots() for x in A[f"{k}|C3"] if x["core_ok"] and not x["connected"] and x["node"] for f in x["core_ok_from"]})
    jobs = [{"root": "dev", "from_template": None, "qa": g.q[a], "qb": g.q[b], "key": f"local/state_conn/{a}>{b}"} for a, b in pairs]
    with mp.get_context("spawn").Pool(workers) as pool:
        outs = pool.map(_conn_job, jobs, chunksize=1)
    cpu = sum(o["cpu_s"] for o in outs)
    _ledger_spend("state_connectors_dev_informed", len(outs), cpu, f"{len(outs)} actual-state -> clearing target approach-start")
    ok = [o for o in outs if o["arrays"] is not None]
    np.savez_compressed(OUT / "catalog" / "CONNECTORS_STATE.npz", **{f"c{i}__{f}": np.asarray(v) for i, o in enumerate(ok) for f, v in
                                                                      {**o["arrays"], "qa": o["qa"], "qb": o["qb"]}.items()})
    cf.write_json(OUT / "catalog" / "CONNECTORS_STATE.json", [{"compiled": o["arrays"] is not None, "termination": o["term"], "negative_kind": o["neg"],
                                                                "cpu_s": o["cpu_s"]} for o in outs])
    return {"pairs": len(pairs), "compiled": len(ok), "cpu_s": cpu}


def build_c4() -> dict:
    import ad_compile as ac
    base = ac.load_catalog()
    for f in sorted(Path("runs/approach_d/g2b/catalog").glob("CATALOG_G2B*.json")):
        base.update(ac.load_catalog(f.stem, "runs/approach_d/g2b/catalog"))
    ent = [t for t in base.values() if t["kind"] == "ENTRY"]
    T = {i: t for i, t in base.items() if t["kind"] != "ENTRY"}
    T.update(ac.load_catalog("CATALOG_LOCAL_SEARCH", OUT / "catalog"))
    T.update(ac.load_catalog("CATALOG_LOCAL_TARGET", OUT / "catalog"))
    z, meta = np.load(OUT / "catalog" / "CONNECTORS_STATE.npz"), [m for m in rd(OUT / "catalog" / "CONNECTORS_STATE.json") if m["compiled"]]
    extra = list(_connectors())
    for i in range(len(meta)):
        a = {k.split("__")[1]: z[k] for k in z.files if k.startswith(f"c{i}__")}
        extra.append((a.pop("qa"), a.pop("qb"), a, {"origin_rule": "LOCAL_STATE_CONNECTOR_DEV_INFORMED"}))
    m = ac.build_graph(T, ent, OUT / "catalog", "GRAPH_C4", extra)
    c = rd(OUT / "CATALOGS.json")
    c["C4"] = {"actions": len(m["actions"]), "connectors": len(m["connectors"]), "nodes": len(m["nodes"]), "rejected": len(m["rejected"]), "hash": m["hash"],
               "validation_cpu_s": m["validation_cpu_s"], "dev_informed": True}
    cf.write_json(OUT / "CATALOGS.json", c)
    return c["C4"]


# ------------------------------------------------------------------ figures 05 / 06 (new precompiled backend; DEV only)
def first_move_hits() -> dict:
    """On infeasible DEV roots with a historically VERIFIED repair (P16 labels): does each guide's first tried relocation (C3 pilot) move
    an object of a verified minimal repair, and is it exactly that repair's first step?"""
    import glob
    lab = {}
    for f in sorted(glob.glob("runs/p16/data/dev/labels_v2w*.json")):
        lab.update(rd(f))
    R = rd(OUT / "PILOT_L3.json")["rows"]
    out = {g: {"object_hit": 0, "exact_first_step": 0, "n": 0} for g in GUIDES_L3}
    rows = []
    for k in dev_roots():
        v = lab.get(k)
        if not v or v["original"]["status"] == "VERIFIED":
            continue
        ver = [s for s, x in v["sequences"].items() if x["status"] == "VERIFIED"]
        if not ver:
            continue
        m = min(len(s.split(".")) for s in ver)
        mins = [s for s in ver if len(s.split(".")) == m]
        objs, firsts = {x.split(">")[0] for s in mins for x in s.split(".")}, {s.split(".")[0] for s in mins}
        row = {"root": k, "verified_minimal": mins}
        for g in GUIDES_L3:
            fm = R[f"{k}|C3"]["guides"][g]["first_move"]
            out[g]["n"] += 1
            out[g]["object_hit"] += fm[0] in objs
            out[g]["exact_first_step"] += f"{fm[0]}>{fm[1]}" in firsts
            row[g] = fm
        rows.append(row)
    res = {"summary": out, "rows": rows}
    cf.write_json(OUT / "FIRST_MOVE_HITS.json", res)
    return res


def fig_chain(dst=FIG):
    """05: the G2b A->B->T chain on stored records, next to what the HISTORICAL teacher and D say about the same root."""
    import glob
    import ad_compile as ac
    import ad_g2b as g2
    import ad_provider as pv
    import ad_viz as av
    from scene import scene_from_dict
    _style()
    B = _poc()
    cfg, robot, _ = ac.setup()
    g = pv.Graph(g2.OUT / "catalog")
    P = rd(DEV_PLAN)["roots"]
    row = rd(g2.OUT / "CHAINS.json")["rows"]["F12|EXACT+REL_6x1+CATALOG"]
    k = row["root"]
    s = scene_from_dict(P[k]["scene"])
    lab = {}
    for f in sorted(glob.glob("runs/p16/data/dev/labels_v2w*.json")):
        lab.update(rd(f))
    L = lab[k]
    d = rd(OUT / "D_F12.json") if (OUT / "D_F12.json").exists() else None
    fig, axs = plt.subplots(1, 5, figsize=(23, 6.4), constrained_layout=True)
    B.draw_scene(axs[0], s, P[k]["goal_cell"], robot, robot_alpha=0.6, view=B.VIEW_SCENE)
    txt = "D (Dp17) on the original scene, target t0 only:\n" + (f"p_T = {d['p_feasible']:.3f}\n" + "\n".join(f"blocker marginal {o}: {m:.2f}" for o, m in
                                                                                                         zip(d["pool"], d["marg"])) if d else "")
    axs[0].text(0.02, 0.02, txt, transform=axs[0].transAxes, fontsize=9, va="bottom")
    axs[0].set_title(f"(a) {k}, start {P[k]['stratum']}: original target BLOCKED\n(P16 label: {L['original']['status']})", fontsize=9.5, loc="left")
    cen = s.lattice.center
    B.draw_scene(axs[1], s, P[k]["goal_cell"], robot, robot_alpha=0.25, view=B.VIEW_SCENE)
    B.arrow(axs[1], cen(56), cen(59), COL["ok"])
    B.ghost(axs[1], cen(59), COL["ok"])
    axs[1].text(0.02, 0.02, "historical P16 teacher (online planner):\n" + "\n".join(f"{q}: {x['status']}" for q, x in L["sequences"].items()),
                transform=axs[1].transAxes, fontsize=8.5, va="bottom")
    axs[1].set_title("(b) Historical teacher: ONE relocation (o00>59) then T\nis VERIFIED -> this root is NOT a proven two-blocker task",
                     fontsize=9.5, loc="left")
    prov = pv.Precompiled(cfg, robot, s, P[k]["goal_cell"], g, lambda *a: [], 6)
    av._chain_panels(axs[2:], robot, prov, row, "stored-record chain")
    for a in axs[2:]:
        a.set_title(a.get_title(loc="left").replace("stored-record chain", "(c) G2b stored records:"), fontsize=9.5, loc="left")
    fig.suptitle("New precompiled backend — limited DEV demonstration. The G2b chain uses two relocations because the FINITE LIBRARY could not "
                 "realise the one-move repair (G2b F10: o00>59 then T fails on connectors), not because the task needs two.", fontsize=11, x=0.01, ha="left")
    p = dst / "05_precompiled_chain.png"
    fig.savefig(p, dpi=130)
    plt.close(fig)
    return p


def fig_g2c(dst=FIG):
    """06: catalog availability before/after (C1..C4), failure sources, and the matched guide pilot on the same catalogs."""
    _style()
    A = {**rd(OUT / "AVAILABILITY_L2.json")["summary"], **rd(OUT / "AVAILABILITY_C4.json")["summary"]}
    T = rd(OUT / "ATTRIBUTION_L3.json")["summary"]
    S = {**rd(OUT / "PILOT_L3.json")["summary"], **rd(OUT / "PILOT_L3_C4.json")["summary"]}
    H = rd(OUT / "FIRST_MOVE_HITS.json")["summary"]
    cats = ["C1", "C2", "C3", "C4"]
    names = {"C1": "C1 base\n(+search templates)", "C2": "C2 = C1 +\ntarget diversity", "C3": "C3 = C2 +\nrule connectors", "C4": "C4 = C3 + state\nconnectors (dev-informed)"}
    fig, axs = plt.subplots(1, 4, figsize=(21, 5.4), constrained_layout=True)
    x = np.arange(4)
    a1 = axs[0]
    a1.bar(x - 0.18, [A[c]["states_core_ok"] for c in cats], 0.34, color="#9fd09f", label="a stored target action certifies")
    a1.bar(x + 0.18, [A[c]["states_connected"] for c in cats], 0.34, color=COL["ok"], label="...and a stored connector path reaches it")
    for i, c in enumerate(cats):
        a1.text(i - 0.18, A[c]["states_core_ok"] + 0.4, str(A[c]["states_core_ok"]), ha="center", fontsize=8.5)
        a1.text(i + 0.18, A[c]["states_connected"] + 0.4, str(A[c]["states_connected"]), ha="center", fontsize=8.5)
    a1.set_xticks(x, [names[c] for c in cats], fontsize=7.8)
    a1.set_ylabel(f"reachable states (of {A['C1']['states']}, 12 DEV roots)")
    a1.set_ylim(0, 21)
    a1.legend(fontsize=8, frameon=False, loc="upper right")
    a1.set_title("(a) Budget-free availability of the original-target action", fontsize=9.5, loc="left")
    t = T["C3"]["target"]
    r = T["C3"]["relocation"]
    keys = [("target action collides", t.get("TARGET_ACTION_COLLISION", 0)), ("target ok, connector collides", t.get("CONNECTOR_COLLISION", 0)),
            ("relocation collides", r.get("COLLISION_CURRENT_SCENE", 0)), ("relocation connector collides", r.get("CONNECTOR_COLLISION", 0)),
            ("relocation: no template", r.get("NO_TEMPLATE", 0)), ("relocation: check budget", r.get("CHECK_BUDGET_EXHAUSTED", 0)),
            ("relocation accepted", r.get("SUCCESS", 0))]
    axs[1].barh(range(len(keys)), [v for _, v in keys], color=[COL["bad"], COL["warn"], COL["bad"], COL["warn"], "#9a9890", "#9a9890", COL["ok"]])
    for i, (_, v) in enumerate(keys):
        axs[1].text(v + 2, i, str(v), va="center", fontsize=8.5)
    axs[1].set_yticks(range(len(keys)), [k for k, _ in keys], fontsize=8.5)
    axs[1].invert_yaxis()
    axs[1].set_xlabel("provider attempts (C3, all reachable states)")
    axs[1].set_title("(b) Where the finite library fails (source attribution)", fontsize=9.5, loc="left")
    G = ["Dp17-norec", "geometry-norec", "uniform"]
    for j, gname in enumerate(G):
        axs[2].bar(x + (j - 1) * 0.26, [S[c][gname]["found"] for c in cats], 0.24, color=[COL["D"], COL["base"], "#c3c2b7"][j], label=gname)
    axs[2].set_xticks(x, [c for c in cats])
    axs[2].set_ylim(0, 12)
    axs[2].set_ylabel("DEV roots repaired end to end (of 12)")
    axs[2].legend(fontsize=8, frameon=False)
    axs[2].set_title("(c) Matched pilot: same domain, catalog, budgets\n(only the K0 root succeeds, for every guide)", fontsize=9.5, loc="left")
    for j, gname in enumerate(G):
        h = H[gname]
        axs[3].bar(j - 0.18, h["object_hit"], 0.34, color=[COL["D"], COL["base"], "#c3c2b7"][j])
        axs[3].bar(j + 0.18, h["exact_first_step"], 0.34, color=[COL["D"], COL["base"], "#c3c2b7"][j], alpha=0.5, hatch="//")
        axs[3].text(j - 0.18, h["object_hit"] + 0.1, f"{h['object_hit']}/{h['n']}", ha="center", fontsize=8.5)
        axs[3].text(j + 0.18, h["exact_first_step"] + 0.1, f"{h['exact_first_step']}/{h['n']}", ha="center", fontsize=8.5)
    axs[3].set_xticks(range(3), ["D (Dp17-norec)", "geometry-norec", "uniform"], fontsize=8.5)
    axs[3].set_ylim(0, 8)
    axs[3].set_ylabel("infeasible DEV roots with a verified historical repair")
    axs[3].set_title("(d) First relocation tried: object in a verified minimal repair\n(solid) / exactly its first step (hatched); n = 7, suggestive only",
                     fontsize=9.5, loc="left")
    fig.suptitle("New precompiled backend — limited DEV pilot (12 P16-labelled DEV roots; zero runtime IK / planner calls). "
                 "Catalog availability, not guidance, is the binding constraint.", fontsize=11, x=0.01, ha="left")
    p = dst / "06_g2c_lite_and_pilot.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    return p
