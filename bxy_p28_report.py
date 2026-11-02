"""BXY-P28 evidence tables, figures and the PROPOSED (not authorized) P29 development design, from GUIDED_SEARCH_P28.json only.
    python3 bxy_p28_report.py tables | figures | proposal | consistency"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import numpy as np

import bxy_full_eval as EV
import bxy_fullspace as S

OUT, FIG = EV.OUT, EV.FIG
POL = ("E", "D", "DIRECT", "G", "GEOM", "SHORTEST", "UNIFORM")
INK, BLUE, ORANGE, GREY = "#222222", "#2a6fb0", "#d9822b", "#9a9a9a"
STYLE = {"E": (BLUE, "-"), "D": (BLUE, "--"), "DIRECT": (ORANGE, "-"), "G": (GREY, "-")}
TRAIN_CHEB_GE3 = 572 / 4137                                       # P16 + P20 development catalogues: actions with Chebyshev >= 3


def load() -> dict:
    return json.loads((OUT / "GUIDED_SEARCH_P28.json").read_text())


def tables() -> dict:
    R = load()
    roots, recs = R["roots"], {k: rec for _, k, rec in EV.dev_roots()}
    t = {"roots": len(roots), "budget": R["budget"], "policies": {}}
    for p in POL:
        rows = [r["policies"][p] for r in roots.values()]
        sel = [x["selected"] for x in rows]
        t["policies"][p] = {"selected_m": dict(collections.Counter(x["m"] for x in rows)), "noop_selected": sum(s == "empty" for s in sel),
                            "outside_catalogue": sum(not x["in_catalogue"] for x in rows), "scored_median": float(np.median([x["scored_calls"] for x in rows])),
                            "examined_median": float(np.median([x["coverage"]["examined"] for x in rows])),
                            "fraction_examined_median": float(np.median([x["coverage"]["fraction_examined"] for x in rows])),
                            "model_cpu_s_total": round(sum(x["model_cpu_s"] for x in rows), 1), "search_cpu_s_total": round(sum(x["search_cpu_s"] for x in rows), 1),
                            "rss_mb_max": max(x["rss_mb"] for x in rows), "all_balanced": all(x["coverage"]["balanced"] for x in rows),
                            "statuses": dict(collections.Counter(x["status"] for x in rows)),
                            "selected_actions_cheb_ge3": _frac([c for x in rows for c in (x["selected_cheb"] or [])])}
        if p in EV.LEARNED:
            a = p
            gain, spread_sel, spread_cat, own_same = [], [], [], 0
            for k, r in roots.items():
                s = r["policies"][p]["selected"]
                cat = [c for c in r["catalogue_in_K"]]
                ps = r["cross"][a][s]["p"]
                best_cat = max((r["cross"][a][c]["p"] for c in cat), default=None)
                if best_cat is not None and s != "empty":
                    gain.append(ps - best_cat)
                spread_sel.append(r["spread"][a][s])
                spread_cat += [r["spread"][a][c] for c in cat]
                own_same += r["policies"][p]["own_rule_selected"] == s
            dg = [r["policies"][p]["diagnostics"] for r in roots.values()]
            t["policies"][p] |= {"pred_p_selected_minus_best_catalogue_median": float(np.median(gain)) if gain else None, "n_gain": len(gain),
                                 "ensemble_sd_selected_median": float(np.median(spread_sel)), "ensemble_sd_catalogue_median": float(np.median(spread_cat)),
                                 "own_rule_same_selection": own_same,
                                 "py_goal_blocked_median": _med([d["py_goal_blocked_median"] for d in dg]), "py_goal_blocked_max": _max([d["py_goal_blocked_max"] for d in dg]),
                                 "py_other_median": _med([d["py_other_median"] for d in dg]), "perm_dpx_median": _med([d["perm_dpx_median"] for d in dg]),
                                 "perm_dpx_max": _max([d["perm_dpx_max"] for d in dg]), "perm_groups": sum(d["perm_groups"] for d in dg),
                                 "scored_actions_cheb_ge3_median": _med([d["frac_actions_cheb_ge3"] for d in dg])}
    agree = {}
    for a in POL[:5]:
        for b in POL[:5]:
            if a < b:
                agree[f"{a}|{b}"] = {"same_sequence": sum(r["policies"][a]["selected"] == r["policies"][b]["selected"] for r in roots.values()),
                                     "same_endpoint": sum(_y(recs[k], r, a) == _y(recs[k], r, b) for k, r in roots.items())}
    t["agreement"] = agree
    kc = {k: recs[k]["construction"].get("K_cert") for k in roots}               # POST HOC, evaluation only: sound necessity certificate
    t["certified_short"] = {"roots_with_K_cert": sum(bool(v) for v in kc.values()), "K_cert": kc,
                            "note": "K_cert: removing ANY K_cert - 1 movables leaves the target pick or place certified closed; relocating them only adds "
                                    "bodies, so every selection with m < K_cert is a certain Y = 0 failure (no teacher needed)",
                            "per_policy": {p: sum(1 for k in roots if kc[k] and (roots[k]["policies"][p]["m"] or 0) < kc[k]) for p in POL}}
    t["train_catalogue_actions_cheb_ge3"] = TRAIN_CHEB_GE3
    (OUT / "TABLES_P28.json").write_text(json.dumps(t, indent=1, sort_keys=True))
    return t


def _y(rec, r, p) -> str:
    return S.ysig(S.domain(rec), EV._seq(r["policies"][p]["selected"]))


def _frac(v):
    return float(np.mean([c >= 3 for c in v])) if v else None


def _med(v):
    v = [x for x in v if x is not None]
    return float(np.median(v)) if v else None


def _max(v):
    v = [x for x in v if x is not None]
    return float(max(v)) if v else None


# ------------------------------------------------------------------ figures
def figures() -> list:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import bxy_p26_report as R26
    FIG.mkdir(parents=True, exist_ok=True)
    roots, out = load()["roots"], []
    recs = {k: rec for _, k, rec in EV.dev_roots()}
    # 1. anytime: best predicted success among examined members vs scored members, per root
    ks = list(roots)
    fig, axs = plt.subplots(3, 4, figsize=(12, 7.6), sharex=True)
    for ax, k in zip(axs.flat, ks):
        for a, (col, ls) in STYLE.items():
            tr = [x for x in roots[k]["policies"][a]["anytime"] if x[1] is not None]
            ax.plot([x[0] for x in tr], [x[1] for x in tr], color=col, ls=ls, lw=1.5, label=a)
        ax.set_title(k.replace("2d-", ""), fontsize=7.5), ax.grid(alpha=0.25, lw=0.5), ax.tick_params(labelsize=7)
    for ax in axs[-1]:
        ax.set_xlabel("members scored", fontsize=8)
    for ax in axs[:, 0]:
        ax.set_ylabel("best predicted p_succ", fontsize=8)
    axs[0, 0].legend(fontsize=7, frameon=False)
    fig.suptitle("Anytime learned search (no teacher): best PREDICTED success among examined members, each arm under the common rule. "
                 "A prediction, not a verified repair.", fontsize=9)
    out.append(_save(fig, "01_anytime_best_predicted_success.png"))
    # 2. selected sequences on four scenes, one policy per panel (rows E / DIRECT / GEOM), numbers = action order
    pick = [k for k in ks if roots[k]["corpus"] == "K34" and recs[k]["construction"].get("K_cert", 0) >= 3][:4]
    fig, axs = plt.subplots(3, len(pick), figsize=(3.3 * len(pick), 10.4))
    for c, k in enumerate(pick):
        rec = recs[k]
        D = S.domain(rec)
        for r_, (p, col, ls) in enumerate((("E", BLUE, "-"), ("DIRECT", ORANGE, "-"), ("GEOM", INK, "--"))):
            ax, x = axs[r_, c], roots[k]["policies"][p]
            R26._board(ax, rec, "")
            for j, (o, d) in enumerate(EV._seq(x["selected"])):
                a0, b0 = R26._xy(D["cells0"][o]), R26._xy(d)
                ax.annotate("", xy=b0, xytext=a0, arrowprops=dict(arrowstyle="->", color=col, lw=1.6, ls=ls))
                ax.text(b0[0] + 0.012, b0[1] + 0.012, str(j + 1), fontsize=8, color=col, weight="bold")
            q = f"p^ {roots[k]['cross'][p][x['selected']]['p']:.2f}" if p in EV.LEARNED else f"h {x['selected_row']['h']:.0f}"
            ax.set_title(f"{p}: m={x['m']}, {q}{'' if x['in_catalogue'] else ', not in catalogue'}", fontsize=8)
            if r_ == 0:
                ax.text(0.32, 0.70, f"{k.replace('2d-bxyg34dev-', '')} (K_cert {rec['construction'].get('K_cert')}, post hoc)", ha="center", fontsize=8.5)
    fig.suptitle("Selected corrections, PREDICTED only (no teacher): rows = E (blue), DIRECT (orange), GEOM (black dashed); numbers = order", fontsize=9.5)
    out.append(_save(fig, "02_selected_sequences_boards.png"))
    # 3. reliability diagnostics (label-free)
    T = json.loads((OUT / "TABLES_P28.json").read_text())["policies"]
    fig, axs = plt.subplots(1, 3, figsize=(12.5, 3.9))
    for j, a in enumerate(EV.LEARNED):
        sel = [roots[k]["spread"][a][roots[k]["policies"][a]["selected"]] for k in ks]
        cat = [roots[k]["spread"][a][c] for k in ks for c in roots[k]["catalogue_in_K"]]
        axs[0].scatter(np.full(len(cat), j - 0.15) + np.random.default_rng(j).uniform(-0.06, 0.06, len(cat)), cat, s=6, color=GREY, alpha=0.6)
        axs[0].scatter(np.full(len(sel), j + 0.15), sel, s=14, color=BLUE)
    axs[0].set_xticks(range(4), list(EV.LEARNED)), axs[0].set_ylabel("across-member SD of p", fontsize=8)
    axs[0].set_title("ensemble disagreement: catalogue members (grey)\nvs the search's selection (blue)", fontsize=8)
    xy = [a for a in ("E", "D", "G")]
    axs[1].bar(np.arange(3) - 0.18, [T[a]["py_other_median"] for a in xy], 0.34, color=BLUE, label="other endpoints")
    axs[1].bar(np.arange(3) + 0.18, [T[a]["py_goal_blocked_median"] for a in xy], 0.34, color=ORANGE, label="GOAL_BLOCKED endpoints (Y = 0 for sure)")
    axs[1].set_xticks(range(3), xy), axs[1].set_ylabel("median predicted P(Y)", fontsize=8), axs[1].legend(fontsize=7, frameon=False, loc="upper right")
    axs[1].set_ylim(0, 0.25)
    axs[1].set_title("sound-F1 sanity: P(Y) where the goal is occupied", fontsize=8)
    labs = ["training catalogues"] + [f"{a} scored" for a in EV.LEARNED] + [f"{a} selected" for a in ("E", "DIRECT", "GEOM")]
    vals = [TRAIN_CHEB_GE3] + [T[a]["scored_actions_cheb_ge3_median"] for a in EV.LEARNED] + [T[a]["selected_actions_cheb_ge3"] or 0 for a in ("E", "DIRECT", "GEOM")]
    axs[2].bar(range(len(vals)), vals, color=[INK] + [GREY] * 4 + [BLUE, ORANGE, INK])
    axs[2].set_xticks(range(len(vals)), labs, fontsize=7, rotation=40, ha="right"), axs[2].set_ylabel("fraction of actions with Chebyshev >= 3", fontsize=8)
    axs[2].set_title("out-of-distribution parking distance", fontsize=8)
    out.append(_save(fig, "03_label_free_reliability_diagnostics.png"))
    # 4. compute fairness
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    ax.bar(range(len(POL)), [T[p]["model_cpu_s_total"] for p in POL], color=[BLUE, BLUE, ORANGE, GREY, INK, INK, INK])
    for i, p in enumerate(POL):
        ax.text(i, T[p]["model_cpu_s_total"] + 5, f"{T[p]['scored_median']:.0f} scored\n(median/root)", ha="center", fontsize=6.5)
    ax.set_xticks(range(len(POL)), POL), ax.set_ylabel("priority CPU-s, 12 roots", fontsize=8), ax.set_ylim(0, 680)
    ax.set_title("Equal scored-member budget is not equal compute: learned priorities cost ~18 ms/member/arm, analytic ones ~0", fontsize=8.5)
    out.append(_save(fig, "04_compute_per_policy.png"))
    return out


def _save(fig, name) -> str:
    import matplotlib.pyplot as plt
    p = FIG / name
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return str(p)


# ------------------------------------------------------------------ dynamic vs legacy design views on every P28 root
def consistency() -> dict:
    """max |dynamic - legacy| of p / px / py / J_hat over every F1-admissible catalogue member of the 12 roots, all four ensembles."""
    import torch
    import bxy_fullscore as SC
    import bxy_p24_confirm as C
    torch.set_num_threads(1)
    inp, fz = SC.inputs(), C.frozen_models()
    nets, out = C.load_all(fz), {}
    for corpus, k, rec in EV.dev_roots():
        base = Path("runs/approach_b/bxy_p20_v1" if corpus == "K34" else "runs/approach_b/bxy_p16_v1") / k.rsplit("-", 2)[-2]
        D = json.loads((base / "DESIGN.json").read_text())
        sv_old, _, _ = C.view(base, k, rec, D, inp[k], {})
        seqs = [()] + [tuple((o, int(d)) for o, d in c["seq"]) for c in D["roots"][k]["catalogue"] if c["f1_complete_ok"]]
        sv_new = SC.view(k, rec, inp[k], seqs)
        diff = 0.0
        for arm in C.ARMS:
            old = {r["sig"]: r for r in C.ensemble(arm, nets[arm], sv_old)["cands"] if r["admissible"]}
            new = {r["sig"]: r for r in C.ensemble(arm, nets[arm], sv_new)["cands"]}
            assert set(old) == set(new)
            diff = max([diff] + [abs(old[x][f] - new[x][f]) for x in old for f in ("p", "px", "py", "J_hat") if old[x].get(f) is not None])
        out[k] = {"members": len(seqs), "max_abs_diff": diff}
    res = {"roots": out, "max_abs_diff": max(v["max_abs_diff"] for v in out.values()), "members": sum(v["members"] for v in out.values())}
    (OUT / "CONSISTENCY_P28.json").write_text(json.dumps(res, indent=1, sort_keys=True))
    return res


# ------------------------------------------------------------------ P29 proposal (PROPOSED, not authorized)
def proposal() -> dict:
    P = {"status": "PROPOSED_NOT_AUTHORIZED", "gate": "P29", "namespace": "bxyfull_dev", "purpose": "small NEW development-only physical "
         "validation of universal guided search; never a confirmation", "roots": 12,
         "slots": [{"family": "local_mixed", "K_intent": 4, "n": 4}, {"family": "local_mixed", "K_intent": 3, "n": 3},
                   {"family": "local_pick", "K_intent": 3, "n": 1}, {"family": "local_mixed", "K_intent": 2, "n": 1},
                   {"family": "v21b_nested", "K_intent": 3, "n": 1}, {"family": "v21b_near_closed", "K_intent": 0, "n": 2}],
         "generators": "existing BXY_GEN_K34C doorway (local_mixed / local_pick) and P16 V21B (nested, near_closed) with new bxyfull_dev seeds; "
                       "every attempt recorded, no replacement; K_intent / construction are never search inputs",
         "policies": {"primary": "E (common rule)", "matched": ["DIRECT", "G", "GEOM", "UNIFORM"], "optional_if_budget": ["D"]},
         "per_policy_per_root": {"search_scored_members": 3000, "expansions": 16, "teacher_calls": 8, "K": 4, "fair": 4},
         "order": ["generate", "freeze search inputs + run all searches + SEAL ranked lists and selections (sha256) before any teacher call",
                   "verify each policy's ranked list (Y of the endpoint first, then X) until FOUND_VERIFIED or 8 calls; a candidate already "
                   "verified for another policy is reused (labels are policy-independent) but charged to each policy's budget",
                   "write-once rows, witnesses kept, one evaluation"],
         "teacher": "unchanged bxy_teacher x_query / y_query, per-query budget bd_2d.QB, no reset between relocations, one connector to q_ref",
         "primary_dev_question": "does universal guided search find teacher-verified repairs ABSENT from the historical P20-style catalogue "
                                 "(catalogue rebuilt post hoc for comparison only)?",
         "outcomes_reported": ["FOUND_VERIFIED rate per policy at 8 calls", "verified repairs absent from the catalogue", "calls to first success",
                               "negative kinds (CERTIFIED vs NO_PLAN / TIMEOUT)", "unnecessary repairs on K0 roots", "model vs teacher CPU",
                               "statuses incl. VERIFY_BUDGET_EXHAUSTED_UNKNOWN (never 'no repair')"],
         "limits": {"aggregate_cpu_s": 12000, "wall_s": 9000, "workers": 2, "single_thread": True, "teacher_cpu_s_per_root": 1400,
                    "per_query_budget": "unchanged bd_2d.QB"},
         "estimate": {"model_scoring_cpu_s_per_root": "about 4 learned arms x 3000 x 18 ms = 220 s (+ D optional 55 s)",
                      "teacher_cpu_s_per_root": "<= 40 calls (5 policies x 8, fewer with reuse) x 5-30 s each, capped at 1400",
                      "generation_cpu_s": "about 60-120 per accepted root (P24 rate)"},
         "forbidden": ["P24 confirmation scenes, labels, results or witnesses", "retraining", "new teacher or skills", "a second cohort"],
         "open_decisions": {
             "D1_certified_closed_Y_screen": "OPTIONAL, needs approval: a sound label-free terminal screen computed from the scene at search time "
                                             "(bxy_p19_audit-style real-screen certificate: target pick or place certified closed in the edited scene -> "
                                             "the candidate is never selected; subtrees are NOT pruned). P28 shows the frozen learned guides select "
                                             "certified-impossible short sequences on 3-5 of 8 roots; without the screen P29 will spend teacher calls on them. "
                                             "It extends F1 (an addition, not a change to F1's existing rules) and would apply to every policy equally.",
             "D2_common_rule": "COMMON = dev-selected DIRECT rule (gate 0.5, alpha 0.3, gamma 0) as primary; each arm's own P23 rule as secondary",
             "D3_budget": "12 roots and 12,000 CPU-s as proposed, or smaller"},
         "requires": "the user's explicit approval text; a smaller budget is acceptable"}
    (OUT / "P29_PROPOSAL.json").write_text(json.dumps(P, indent=1, sort_keys=True))
    return P


if __name__ == "__main__":
    print(json.dumps({"tables": tables, "figures": figures, "proposal": proposal, "consistency": consistency}[sys.argv[1]](), indent=1, default=str))
