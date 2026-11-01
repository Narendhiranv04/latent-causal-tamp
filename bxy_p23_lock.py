"""BXY-P23 prospective protocol lock: successor files to the untouched P22 plan / analysis (referenced by sha256), written and committed before
any P24 scene exists, plus the PROPOSED (not approved) P24 authorization manifest.
  CONFIRM_PLAN_P23_LOCK.json      the fixed 440-slot population (P22 mix, BXY_GEN_K34C = P20 REV34['k3'] / P16 V21B), every slot's spec, the
                                  labelling order rule, no replacement / adaptive sampling, development-based yield projection WITH uncertainty
  CONFIRM_ANALYSIS_P23_LOCK.json  endpoints and denominators, the authoritative inferential hierarchy, Holm families, gates, bootstrap, K labels,
                                  missingness, references, the power diagnostic, and an explicit reconciliation with the P22 wording
  AUTHORIZATION_P24_PROPOSED.json the proposed ceilings and the hashes the user is asked to approve (approved = false)"""
from __future__ import annotations

import collections
import json
import math
from pathlib import Path

import numpy as np

import bxy_p24_analysis as AN
import bxy_p24_confirm as C24
from bxy_p24_confirm import sha_file

OUT = Path("runs/approach_b/bxy_p23_v1")
P22 = Path("runs/approach_b/bxy_p22_v1")
CAT = ("REJECTED", "0", "1", "2", "3", "4", "None")
LIMITS = {"aggregate_cpu_s": 90000, "wall_s": 40000, "workers": 4, "per_root_cpu_s": 1400, "evaluation_reserve_cpu_s": 3000, "slots": 440, "torch_threads": 1}


def slots(plan22) -> list:
    """The 440 slots in P22 mix order; spec fields cycle exactly as bxy_p20_k34.specs."""
    out, i = [], 0
    for key, f in plan22["mix"].items():
        fam, K = key.split("|")
        for _ in range(round(plan22["slots"] * f)):
            out.append({"slot": i, "spec": {"family": fam, "K_intent": int(K[1:]), "mechanism": fam, "start_pose": ("home", "nonhome")[(i // 2) % 2],
                                            "displacement": ("short", "medium", "long")[(2 * i) % 3], "source": ("near", "mid", "far")[(i + 1) % 3], "distractors": True}})
            i += 1
    if len(out) != plan22["slots"]:
        raise RuntimeError("mix does not round to the planned slot count")
    return out


def projection(plan22, rates, sims=10000) -> dict:
    """Dirichlet(counts + 1/2) posterior per family x K_intent from the P20 k3 realization, multinomial confirmation draws; quantiles."""
    rng = np.random.default_rng(0)
    tot = collections.defaultdict(list)
    for _ in range(sims):
        acc = collections.Counter()
        for key, f in plan22["mix"].items():
            r = rates[key]
            n_dev = r["slots"]
            c = np.array([round(n_dev * (1 - r["accept_rate"]))] + [round(n_dev * r["verified_K_per_slot"].get(k, 0.0)) for k in CAT[1:]], float)
            Ki = int(key.split("|K")[1])                                    # K_cert = K_intent is sound: a verified K below it cannot occur
            ok = np.array([k in ("REJECTED", "None") or key.startswith("v21b") or int(k) >= Ki for k in CAT])
            pr = np.zeros(len(CAT))
            pr[ok] = rng.dirichlet(c[ok] + 0.5)
            draw = rng.multinomial(round(plan22["slots"] * f), pr)
            for k, v in zip(CAT, draw):
                acc[k] += v
            acc["cpu"] += round(plan22["slots"] * f) * r["cpu_per_slot"]
        inf = sum(acc[k] for k in ("1", "2", "3", "4", "None"))
        for nm, v in (("accepted", sum(acc[k] for k in CAT[1:])), ("INF", inf), ("AVAIL", sum(acc[k] for k in "1234")), ("REP34", acc["3"] + acc["4"]),
                      ("K3", acc["3"]), ("K4", acc["4"]), ("K0", acc["0"]), ("FEA", acc["0"])):
            tot[nm].append(v)
        tot["cpu_point"].append(acc["cpu"])
    return {k: {"median": float(np.median(v)), "q10": float(np.quantile(v, 0.1)), "q90": float(np.quantile(v, 0.9))} for k, v in tot.items()}


def p21_paired_sd() -> dict:
    import bxy_p17_eval as E
    import bxy_p21_eval as E2
    Cx = E2.context()
    T = E.tables(Cx, E.rules(Cx))
    ob = lambda k: Cx["corpus"][k] in ("P15", "V21", "K34")  # noqa: E731
    av = lambda k: ob(k) and Cx["by"][k][2]["y0"] == 0 and any(c["success"] == 1 for c in Cx["by"][k][2]["cands"])  # noqa: E731
    r34 = lambda k: Cx["corpus"][k] == "K34" and Cx["by"][k][2]["verified_K"] in (3, 4)  # noqa: E731
    out = {}
    for nm, keep in (("U", ob), ("C", av), ("REP34", r34)):
        for a2 in ("A:DIRECT-GEO", "G:XYQ-GEO-SYM-ORDINV"):
            a = E.seed_mean(T, "D:XYQ-GEO-SYM", E.METRICS["succ_inf"]("RULE"), keep)
            b = E.seed_mean(T, a2, E.METRICS["succ_inf"]("RULE"), keep)
            d = np.array([a[k] - b[k] for k in sorted(set(a) & set(b))])
            out[f"{nm}|D-{a2.split(':')[0]}"] = {"n": len(d), "mean": float(d.mean()), "sd": float(d.std(ddof=1)), "disagree_rate": float(np.mean(d != 0))}
    return out


def power(proj, sd) -> dict:
    rows = {}
    for pop in ("INF", "AVAIL", "REP34"):
        for q in ("median", "q10"):
            n = max(proj[pop][q], 1.0)
            key = {"INF": "U", "AVAIL": "C", "REP34": "REP34"}[pop]
            for s in (sd[f"{key}|D-A"]["sd"], math.sqrt(sd[f"{key}|D-A"]["disagree_rate"]), 0.3, 0.5, 1.0):
                rows[f"{pop}|n_{q}={n:.0f}|sd={s:.3f}"] = {"half_width_95": 1.96 * s / math.sqrt(n), "mde_80pct_power": 2.80 * s / math.sqrt(n)}
    return rows


def plan_lock(fz_sha) -> dict:
    import bd_2d
    import bxy_p20_k34 as Z
    p22 = json.loads((P22 / "CONFIRM_PLAN_K04.json").read_text())
    rates = json.loads((P22 / "K34_RATES.json").read_text())
    sl = slots(p22)
    return {"version": "BXY_P23_CONFIRM_PLAN_LOCK_V1", "parent": {"file": str(P22 / "CONFIRM_PLAN_K04.json"), "sha256": sha_file(P22 / "CONFIRM_PLAN_K04.json")},
            "namespace": C24.NS, "wave_label": C24.WAVE, "generator": C24.GEN, "construction_revision": Z.REV34["k3"], "max_cands": Z.MAX_CANDS, "max_queries": Z.MAX_QUERIES,
            "per_query_teacher_budget": bd_2d.QB, "slots": sl, "slot_count": len(sl), "mix_counts": dict(collections.Counter(f"{s['spec']['family']}|K{s['spec']['K_intent']}" for s in sl)),
            "seeds": "construction_seed = int(sha256-json([BXY_GEN_K34C, 'bxyg34confirm', 'c34', slot])[:8], 16); family id per slot (each root its own family)",
            "labelling_order": "roots sorted by sha256('bxyg34confirm|label-order|<root_id>'): a budget stop leaves an outcome-independent remainder",
            "rules": {"replacement": "none: a rejected slot stays rejected and is reported; slot composition never changes",
                      "adaptive_sampling": "none: no look at labels or model outputs before the single evaluation",
                      "collections": "exactly one generation, one design freeze (catalogue + queries + sealed predictions before any teacher call), one labelling run, one evaluation",
                      "shortfall": "realized n below the analysis lock's minimums -> the locked analysis still runs once and is labelled UNDERPOWERED; no extra wave",
                      "exclusion": "no root is dropped for difficulty or failure; only registered missingness (Y0 unobserved) leaves a denominator",
                      "disjoint_from": ["BD_GEN_V1 and the 34 exposed test roots", "bxyg2pilot", "bxyg2confirm", "bxyg21dev", "bxyg21confirm (P18 plan, never generated)", "bxyg34dev"]},
            "projection": projection(p22, rates), "projection_basis": "P20 wave k3 realization (5-25 dev slots per family): Dirichlet(counts + 1/2) uncertainty; "
            "the P22 point projection (K3 49.5, K4 41.4, repairable 90.9, 70,322 CPU-s) is reproduced as a median-type figure, not a guarantee",
            "p22_point_expected": p22["expected"], "p18_plan": p22["p18_plan"], "frozen_models_sha256": fz_sha}


def analysis_lock(fz_sha, sd) -> dict:
    p22a = json.loads((P22 / "CONFIRM_ANALYSIS_P22.json").read_text())
    return {"version": "BXY_P23_CONFIRM_ANALYSIS_LOCK_V1", "parent": {"file": str(P22 / "CONFIRM_ANALYSIS_P22.json"), "sha256": sha_file(P22 / "CONFIRM_ANALYSIS_P22.json"),
                                                                       "primary_wording": p22a["primary"]},
            "implementation": {"analysis": "bxy_p24_analysis.py", "analysis_sha256": sha_file("bxy_p24_analysis.py"), "runner_sha256": sha_file("bxy_p24_confirm.py"),
                               "engine_sha256": sha_file("bxy_p23_engine.py")},
            "frozen_models_sha256": fz_sha, "models": {"arms": list(AN.ARMS), "ensemble": "15-member mean, F1 first, frozen pooled rule per arm; one deterministic predictor per arm",
                                                       "no_calibration_or_rule_tuning_on_test": True},
            "success": "a chosen candidate is a success iff the teacher verified it: X = 1 (every relocation in order from q0 with the achieved state carried, then the "
                       "single connector to q_ref) and Y = 1 (target task from q_ref in the edited scene), with independent replay; for the no-op, Y0 = 1; "
                       "predicted success never counts",
            "populations": {"INF": "initially infeasible: Y0 = 0 observed", "AVAIL": "INF with >= 1 teacher-verified candidate in the frozen catalogue",
                            "FEA": "initially feasible: Y0 = 1", "REP34": "AVAIL with verified K in {3, 4} (K = shortest verified candidate with every shorter "
                            "admissible candidate decided)"},
            "endpoints": {"U_unconditional": "repair success over ALL INF roots (roots with no verified candidate count as failures for every arm)",
                          "C_availability_conditioned": "repair success over AVAIL roots", "unnecessary": "false repair (chosen m > 0) over FEA roots; harmful = chosen edit fails"},
            "hierarchy": {"authoritative_primary": "U_unconditional (P17 / P21 / P22 lineage: 'succ_inf'; the P22 'first' endpoint); the headline verdict of each comparison",
                          "consistency_requirement": "C_availability_conditioned 95% CI lower > 0 is REQUIRED for a positive primary label (no endpoint switching: "
                                                     "C cannot rescue a failed U, U is never replaced by C)",
                          "families": {"PRIMARY (Holm over 3)": AN.PRIMARY, "SECONDARY_K34 (Holm over 3, REP34, conditional)": AN.PRIMARY,
                                       "ORDER (Holm over 3)": {k: v[:2] for k, v in AN.ORDER.items()}},
                          "descriptive_only": ["K1-K4 strata with and without certification (Wilson 95%)", "K0 no-op correctness", "harmful unnecessary repairs",
                                               "Y0 AUROC / Brier", "omission sign", "prefix Y pattern of repairs", "witnessed travel on matched successes",
                                               "certified vs fixed-budget negatives", "catalogue availability by generator family", "references incl. the oracle"]},
            "gates": {"IMPROVES": "Holm-rejected two-sided bootstrap test on U with Holm-level interval lower > 0, U point >= 0.10, C 95% CI lower > 0, and "
                                  "unnecessary-repair point increase <= +0.05 (historical P17 / P21 / P22 thresholds, unchanged)",
                      "POSITIVE_BELOW_THRESHOLD": "as IMPROVES but U point < 0.10 (statistically positive, below the meaningful-effect criterion; not a supported advantage)",
                      "GUARDRAIL_FAILED": "positive but unnecessary increase > 0.05", "REVERSED": "Holm-level interval upper < 0", "NOT_ESTABLISHED": "otherwise (incl. ties)",
                      "SECONDARY_K34": "same labels on REP34 conditional success (threshold 0.10, guardrail on FEA)",
                      "ORDER": "O1 / O3 strict-order concordance difference: Holm-rejected with interval lower > 0 (historical 'ORDER_FAVOURS_FIRST', no magnitude "
                               "threshold); O2 REP34 success: threshold 0.10 + guardrail (P21 H4 replication)",
                      "minimum_n_flag_UNDERPOWERED": AN.MIN_N},
            "statistics": {"bootstrap": f"paired, unit = root family (one per confirmation root), B = {AN.B}, seed {AN.SEED}, percentile intervals",
                           "p_value": "two-sided bootstrap p = min(1, 2 min(P*(d <= 0), P*(d >= 0)))", "multiplicity": "Holm step-down at alpha 0.05 within each family; "
                           "families are separate (primary / K34 secondary / order); 95% intervals also reported",
                           "strict_order": f"per root: same action multiset, same endpoint, both F1-admissible and observed, X discordant; |dpx| <= {AN.TIE} scores 0.5; "
                                           "root mean first, roots are the samples (pair x seed counts are never treated as independent)",
                           "ties_in_selection": "bxy_p11.choose: lowest cost, then (m, C_d, signature); deterministic"},
            "K_labels": {"K_catalogue": "shortest verified candidate, every shorter admissible candidate decided", "K_cert": "construction certificate (every (K-1)-subset "
                         "of movable discs removed leaves the target pick or place certified closed; declared grasp family, monotone collisions)",
                         "certified_necessary": "K_cert == K_catalogue (reported with and without)", "never": "K_intent is never evidence; no global-minimality claim"},
            "missingness": {"y0_unobserved": "excluded from success denominators, counted", "censored_query": "absent (never 0)", "unattempted_query": "absent, reason kept",
                            "corrupt_row": "absent + custody event in the report", "undecided_choice": "a chosen candidate with X or Y undecided is NOT a verified success "
                            "(counted per arm); sensitivity: same tests excluding roots where any arm chose an undecided candidate",
                            "negatives": "attempted fixed-budget failures are operational 0 with negative kind CERTIFIED vs NO_PLAN_FOUND / TIMEOUT kept evaluator-side; "
                                         "no impossibility claim from budget failures"},
            "references": {"NOOP": "always no-op", "SHORTEST_ADMISSIBLE": "", "DISPLACEMENT_RANK": "", "ANALYTIC_ACCESS": "geometry-only rule (bxy_p17_eval.analytic_rule)",
                           "VERIFY_FIRST_ORACLE": "evaluator-only upper bound, cost = teacher verifications; never deployed or described as learned"},
            "q_ref": "q_ref = q0 = scene robot state for every root (adapter refuses otherwise)",
            "attribution": "a positive whole-system X/Y vs DIRECT difference would not isolate the factorization: X/Y arms also use component labels and SYM supervision",
            "generator_shift": "new seeds of the SAME K34 doorway family + V21B controls: no cross-generator or 3D claim",
            "power": {"p21_paired": sd, "note": "P21 per-root values are 3-seed means (sd deflated); a single ensemble gives per-root differences in {-1, 0, 1}, whose sd is "
                      "about sqrt(disagreement rate) (P21: U 0.42, C 0.64, REP34 0.62 for D vs DIRECT), reported with the 0.3 / 0.5 / 1.0 sensitivity; the P22 0.062 half-width is a projection, not a guarantee"},
            "reconciliation_with_P22": [
                "P22 listed two primary endpoints 'by K stratum' with Holm 'per endpoint': clarified to ONE authoritative endpoint (U, pooled over strata) with C as a "
                "required consistency condition; K strata are descriptive (K3 / K4 inferential only via the REP34 secondary family)",
                "P22 did not define the population of the K3/K4 test: fixed as REP34 (P21 H1-H3 definition)",
                "P22 froze D / E / A only: G is added (FROZEN_MODELS_P23_APPEND) with a separate ORDER family",
                "P22 did not record the arms' pooled rules: recorded in FROZEN_MODELS_P23_APPEND, computed by the declared procedure",
                "thresholds (0.10 gain, +0.05 unnecessary, CI lower > 0) are unchanged; Holm is now applied with explicit Holm-level intervals",
                "prediction timing: predictions are computed and sealed (sha256 in the ledger) after the design freeze and BEFORE any teacher label (new, stricter)"]}


def authorization_proposal() -> dict:
    import bd_2d
    import bxy_teacher as T
    return {"version": "BXY_P24_AUTHORIZATION_PROPOSED_V1", "approved": False, "approved_by": None, "approval_text": None,
            "scope": "one-shot generation, design freeze, labelling and evaluation of the 440-slot bxyg34confirm cohort; nothing else",
            "limits": LIMITS, "per_query_teacher_budget": bd_2d.QB, "teacher_hash": T.teacher_hash(), "locks_sha256": C24.locks_now(), "code_tree": C24.code_tree(),
            "cost_basis": {"construction_cpu_per_slot_k3": 75.3, "construction_max_slot_k3": 218.8, "teacher_cpu_per_accepted_root_k3": 154.0,
                           "freeze_inputs_predictions": "~2 CPU-s per root (DINOv2) + 60 member forward passes per root (~0.1-0.25 CPU-s each)",
                           "note": "construction has no per-slot RLIMIT (bounded by the fixed layout tries); labelling starts only if aggregate - reserve - spent > 0"},
            "projection_cpu_s": json.loads((OUT / "CONFIRM_PLAN_P23_LOCK.json").read_text())["projection"]["cpu_point"],
            "how_to_approve": "the user replies with explicit approval of these ceilings; the approved copy is written to runs/approach_b/bxy_p24_v1/AUTHORIZATION_P24.json "
                              "with approved = true, approved_by and the verbatim approval text, committed before `python3 bxy_p24_confirm.py generate`",
            "proposed_approval_text": "I authorize BXY-P24: one-shot generation and labelling of the 440-slot bxyg34confirm cohort and one evaluation of the frozen "
                                      "D / E / DIRECT-GEO / G ensembles, with at most 90,000 aggregate CPU-s (including a 3,000 CPU-s evaluation reserve), 40,000 s "
                                      "wall, 4 single-thread workers and 1,400 CPU-s per root; the per-query teacher budget unchanged."}


def write_all(save) -> dict:
    fz = sha_file(OUT / "FROZEN_MODELS_P23_APPEND.json")
    sd = p21_paired_sd()
    pl = plan_lock(fz)
    out = {"plan": save("CONFIRM_PLAN_P23_LOCK.json", pl, once=True)}
    al = analysis_lock(fz, sd)
    al["power"]["projection_half_widths"] = power(pl["projection"], sd)
    out["analysis"] = save("CONFIRM_ANALYSIS_P23_LOCK.json", al, once=True)
    out["authorization_proposed"] = save("AUTHORIZATION_P24_PROPOSED.json", authorization_proposal())
    return out


def figure() -> str:
    """(a) projected confirmation yields with development uncertainty vs the P22 point projection and the locked minimum n; (b) paired 95%
    half-width vs n under the single-ensemble sd of each endpoint; (c) the frozen pooled rules' early-stop (development) operating points."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from bxy_p17_viz import AC
    pl, an = (json.loads((OUT / f).read_text()) for f in ("CONFIRM_PLAN_P23_LOCK.json", "CONFIRM_ANALYSIS_P23_LOCK.json"))
    fz = json.loads((OUT / "FROZEN_MODELS_P23_APPEND.json").read_text())
    pr, p22 = pl["projection"], pl["p22_point_expected"]
    fig, ax = plt.subplots(1, 3, figsize=(19, 4.8))
    keys = ["accepted", "INF", "AVAIL", "REP34", "K3", "K4", "FEA"]
    for i, k in enumerate(keys):
        ax[0].plot([i, i], [pr[k]["q10"], pr[k]["q90"]], color="#2a78d6", lw=6, solid_capstyle="butt")
        ax[0].scatter(i, pr[k]["median"], color="#0b3d78", zorder=3, s=25)
        if k in AN.MIN_N:
            ax[0].plot([i - 0.3, i + 0.3], [AN.MIN_N[k]] * 2, color="#b4441c", lw=1.5)
    for k, x in (("K3", 4), ("K4", 5), ("FEA", 6)):
        ax[0].scatter(x, p22[{"FEA": "K0"}.get(k, k)], marker="x", color="#222", s=40, zorder=4)
    ax[0].set_xticks(range(len(keys)), keys)
    ax[0].set(ylabel="roots in the 440-slot cohort", title="(a) projected yield: median, 10-90% (bars)\nP22 point (x), locked minimum n (red)")
    sd = an["power"]["p21_paired"]
    n = np.arange(20, 300)
    for key, lab, c in (("U|D-A", "U (all infeasible)", "#2a78d6"), ("C|D-A", "C (availability-conditioned)", "#1baf7a"), ("REP34|D-A", "REP34 (K3/K4)", "#b4441c")):
        s = math.sqrt(sd[key]["disagree_rate"])
        ax[1].plot(n, 1.96 * s / np.sqrt(n), color=c, label=f"{lab}: sd {s:.2f}")
        m = pr[{"U|D-A": "INF", "C|D-A": "AVAIL", "REP34|D-A": "REP34"}[key]]["median"]
        ax[1].scatter(m, 1.96 * s / math.sqrt(m), color=c, zorder=3)
    ax[1].axhline(0.10, color="#222", ls="--", lw=0.8)
    ax[1].legend(frameon=False, fontsize=8)
    ax[1].set(xlabel="paired roots", ylabel="95% half-width of D - DIRECT", ylim=(0, 0.4), title="(b) power under single-ensemble sd\ndots: projected median n; dashed: 0.10 gate")
    for arm, v in fz["arms"].items():
        r = v["rule_inner_pooled_early_stop"]
        ax[2].scatter(r["unnecessary"], r["success_inf"], s=80, color=AC[arm], edgecolor="#222", lw=0.5)
        ax[2].annotate(f"{arm.split(':')[0]}  gate {v['rule']['noop_gate']}, alpha {v['rule']['alpha']}, gamma {v['rule']['gamma']}", (r["unnecessary"], r["success_inf"]),
                       fontsize=8, xytext=(6, 8 if arm.startswith("G") else -3), textcoords="offset points")
    ax[2].axvline(0.10, color="#b4441c", ls="--", lw=0.8)
    ax[2].set(xlabel="unnecessary repairs (pooled early-stop, development)", ylabel="repair success (pooled early-stop)", xlim=(0.05, 0.13),
              title="(c) frozen pooled rules on P21 early-stop roots\n(development only; dashed: U_MAX)")
    for a in ax:
        for sp_ in ("top", "right"):
            a.spines[sp_].set_visible(False)
    fig.tight_layout()
    d = Path("visualizations/approach_b/bxy_p23_v1")
    d.mkdir(parents=True, exist_ok=True)
    fig.savefig(d / "01_protocol_power_rules.png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return str(d / "01_protocol_power_rules.png")
