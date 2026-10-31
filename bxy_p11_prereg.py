"""BXY-P11-TRAINING-PREREG: frozen training / evaluation design, lock, preflight audits (evidence, data, leakage), compute benchmark and the
P11 figures. No optimizer step, no real-data training, no teacher query, no test-split access.

  design      TRAINING_DESIGN.json (every decision of the next gate: interface, objective, arms, roster, folds, selection, metrics, decision rule,
              budget, fresh-cohort protocol, limitations)
  freeze      writes TRAINING_DESIGN.json + TRAINING_LOCK.json once (refuses a different rewrite); assert_frozen() is the next gate's launch guard
  preflight   PREFLIGHT.json: evidence, data audit, leakage audit over every root, parameter counts, forward/backward cost benchmark, regression logs"""
from __future__ import annotations

import collections
import copy
import json
import random
import resource
import subprocess as sp
import sys
import time
from pathlib import Path

import numpy as np
import torch

import bxy_data as bd
import bxy_p11 as P
import bxy_pmin as PM

OUT = P.OUT
FIG = Path("visualizations/approach_b/bxy_p11_v1")
ENTRY = ("bxy_p11.py", "bxy_p11_prereg.py")
LB = Path("runs/approach_b/bd2d_lb_v1")


# ------------------------------------------------------------------ audits
def audit(views=None) -> dict:
    """Data audit of the verified P-min evidence as the learner will see it (counts only; no model, no outcome-driven choice)."""
    sc, D, R, _ = P.load()
    V = views or P.build()
    fam = collections.defaultdict(set)
    for k in D["root_order"]:
        fam[R[k]["ids"]["parent_family_id"]].add(bd.split_of(R[k]))
    test_roots = {k for k, r in R.items() if bd.split_of(r) == "test"}
    xs = [r["x_key"] for r in sc["x_queries"]]
    ys = [r["y_key"] for r in sc["y_queries"]]
    c = collections.Counter()
    shared, rev_shared, enc_bad = 0, 0, 0
    for sv, lab, ev in V:
        s = ev["split"]
        c[f"roots_{s}"] += 1
        c[f"{s}_{ev['stratum']}"] += 1
        c[f"{s}_initially_infeasible"] += ev["y0"] == 0
        kids = collections.Counter(sv["parent"])
        shared += sum(v >= 2 for v in kids.values())
        Q = D["roots"][ev["key"]]["queries"]
        for q, key in enumerate(ev["x_keys"]):
            seq = Q[key]["seq"]
            enc_bad += len(sv["x_seqs"][q]) != len(seq)
            rev_shared += "reversal" in Q[key]["classes"] and kids[sv["parent"][q]] >= 2
            c[f"x_len{len(seq)}"] += 1
        c["noop_x_variables"] += any(len(s_) == 0 for s_ in sv["x_seqs"])
        c["y0_observed"] += sv["y0"] in lab["obs_y"]
        c["j_complete"] += sum(j[0] is not None for j in lab["j"])
        c["j_noop"] += sum(j[0] is None for j in lab["j"])
        c["j_on_failed_candidate"] += sum(1 for i, yi, _ in lab["j"] if i is not None and (lab["obs_x"].get(i), lab["obs_y"].get(yi)) != (1, 1))
        c["unobserved_x_vars"] += len(sv["x_seqs"]) - len(lab["obs_x"])
        c["unobserved_y_vars"] += len(sv["y_poses"]) - len(lab["obs_y"])
        c["catalogue"] += len(sv["cands"])
        c["catalogue_f1_screened"] += sum(not x["admissible"] for x in sv["cands"])
        c["admissible_undecided"] += sum(x["success"] is None for x, y in zip(ev["cands"], sv["cands"]) if y["admissible"])
        c["infeasible_with_successful_candidate"] += ev["y0"] == 0 and any(x["success"] == 1 for x in ev["cands"])
        for m in ev["x_meta"].values():
            c[f"x_{m['status']}"] += 1
        for m in ev["y_meta"].values():
            c[f"y_{m['status']}"] += 1
        for g in ev["order_groups"]:
            c["order_groups"] += 1
            if len({u["x"] for u in g["members"]}) == 2:
                c["order_groups_discordant"] += 1
                c["order_failing_certified"] += sum(u["x"] == 0 and u["negative_kind"] == "CERTIFIED" for u in g["members"])
                c["order_failing_budget"] += sum(u["x"] == 0 and u["negative_kind"] != "CERTIFIED" for u in g["members"])
    tp = [x["travel_parts"] for x in sc["x_queries"] if x["y"] == 1]
    return {"evidence": P.evidence(), "splits": {"train": c["roots_train"], "val": c["roots_val"],
                                                 "families_straddling_train_val": sum(len(v) > 1 for v in fam.values()),
                                                 "test_roots_in_design": len(test_roots & set(D["root_order"])),
                                                 "test_roots_in_sidecar": len(test_roots & {r["root"] for r in sc["x_queries"] + sc["y_queries"]}),
                                                 "records_split_agree": all(P.inputs()[k]["split"] == bd.split_of(R[k]) for k in D["root_order"])},
            "dedup": {"x_rows": len(xs), "x_unique": len(set(xs)), "y_rows": len(ys), "y_unique": len(set(ys)),
                      "p9_reused_x": sum(r["source"] == "P9_PILOT" for r in sc["x_queries"]), "p9_reused_y": sum(r["source"] == "P9_PILOT" for r in sc["y_queries"]),
                      "unobserved_rows": sum(not r.get("observed") for r in sc["x_queries"] + sc["y_queries"])},
            "shared_y": {"y_nodes_with_2plus_x_children": shared, "reversal_x_sharing_a_y_node": rev_shared,
                         "parent_edit_equals_endpoint": "enforced by bxy_p11.build (raises otherwise)"},
            "encoding": {"x_seq_length_mismatch": enc_bad, "x_by_length": {k: v for k, v in sorted(c.items()) if k.startswith("x_len")}},
            "noop": {"x_variables_with_empty_prefix": c["noop_x_variables"], "y0_observed_roots": c["y0_observed"], "noop_travel_witnesses": c["j_noop"]},
            "travel": {"complete_witnesses": c["j_complete"], "noop_witnesses": c["j_noop"], "on_failed_candidates": c["j_on_failed_candidate"],
                       "connector_in_every_complete_prefix": all(t.get("J_connector") is not None for t in tp)},
            "missingness": {"unobserved_x_vars": c["unobserved_x_vars"], "unobserved_y_vars": c["unobserved_y_vars"]},
            "negatives": {k: v for k, v in sorted(c.items()) if k.startswith(("x_", "y_")) and not k.startswith("x_len")},
            "catalogue": {"candidates": c["catalogue"], "f1_screened": c["catalogue_f1_screened"], "admissible_undecided": c["admissible_undecided"],
                          "initially_infeasible": c["train_initially_infeasible"] + c["val_initially_infeasible"],
                          "infeasible_with_successful_candidate": c["infeasible_with_successful_candidate"]},
            "order": {k: c[k] for k in ("order_groups", "order_groups_discordant", "order_failing_certified", "order_failing_budget")},
            "strata": {k: v for k, v in sorted(c.items()) if k.startswith(("train_", "val_"))}}


def perturb(sc, R, seed=0) -> tuple:
    """A self-consistent alternative outcome world: every X / Y label flipped (new positives carry replay flags and random travel, pairs
    recomputed), failure metadata and legacy roles / labels / travel rewritten, legacy catalogue order shuffled; geometry and actions untouched."""
    sc2, R2, rng = copy.deepcopy(sc), copy.deepcopy(R), random.Random(seed)
    for r in sc2["x_queries"] + sc2["y_queries"]:
        r["y"] = 1 - r["y"]
        r["negative_kind"], r["failed_phase"], r["detail"], r["teacher_status"] = "PERTURBED", "perturbed:0", "perturbed", "PERTURBED"
        r["independent_replay"] = True if r["y"] else None
        r["verification"] = dict(r["verification"], witness=bool(r["y"]))
        if r["side"] == "y":
            r["J_target"] = rng.uniform(0.2, 3.0) if r["y"] else None
        else:
            r["travel_parts"] = {"J_prefix_stitched": rng.uniform(1.0, 9.0), "J_connector": rng.uniform(0.1, 1.0)} if r["y"] else None
    xr, yr = {r["x_key"]: r for r in sc2["x_queries"]}, {r["y_key"]: r for r in sc2["y_queries"]}
    for p in sc2["paired"]:
        x, y = xr[p["x_key"]], yr[p["y_key"]]
        p.update(x=x["y"], y=y["y"], full_joint_success=x["y"] * y["y"],
                 J_total=x["travel_parts"]["J_prefix_stitched"] + y["J_target"] if x["y"] * y["y"] else None)
    for rec in R2.values():
        rng.shuffle(rec["labels"]["B"])
        for b in rec["labels"]["B"]:
            b.update(role="perturbed", y=1 - b["y"], travel=None if b["travel"] else 9.9, failed_step=7)
        rec["labels"]["original"]["y"] = 1 - rec["labels"]["original"]["y"]
        rec["roles"] = {o: "perturbed" for o in rec["roles"]}
    return sc2, R2


def same_scorer(a, b) -> bool:
    ra, rb = a["R"], b["R"]
    tens = all(torch.equal(getattr(ra, f), getattr(rb, f)) for f in ("xy0", "vis", "flags", "base", "goal", "ctx")) and ra.tid == rb.tid
    return tens and all(a[k] == b[k] for k in P.SCORER_KEYS if k != "R")


def leakage_audit(arms=tuple(P.ARMS), n_model_roots=12) -> dict:
    """Scorer views identical for every root under perturb(); coefficients, probabilities and selections identical for every arm on a root
    sample; labels / evaluator views do change (the perturbation is real); candidate-list permutation never changes a selection."""
    sc, D, R, I = P.load()
    A = P.build(sc=sc, D=D, R=R, I=I)
    sc2, R2 = perturb(sc, R)
    B = P.build(sc=sc2, D=D, R=R2, I=I)
    same = [same_scorer(a[0], b[0]) for a, b in zip(A, B)]
    lab_changed = sum(a[1]["obs_x"] != b[1]["obs_x"] or a[1]["obs_y"] != b[1]["obs_y"] for a, b in zip(A, B))
    ev_changed = sum(a[2]["cands"] != b[2]["cands"] for a, b in zip(A, B))
    pick = [i for i in sorted(range(len(A)), key=lambda i: PM.bc.sha([A[i][0]["key"], "P11_LEAK"]))[:n_model_roots]]
    res, rng = {}, random.Random(0)
    for arm in arms:
        m = P.build_model(arm, 0)
        d = {"coeff_max_abs_diff": 0.0, "pred_max_abs_diff": 0.0, "choice_diff": 0, "perm_choice_diff": 0}
        for i in pick:
            with torch.no_grad():
                ca, cb = m.coeffs(A[i][0]), m.coeffs(B[i][0])
            d["coeff_max_abs_diff"] = max(d["coeff_max_abs_diff"], *(float((ca[k] - cb[k]).abs().max()) if ca[k].numel() else 0.0 for k in ca))
            pa, pb = P.predict(m, A[i][0]), P.predict(m, B[i][0])
            d["pred_max_abs_diff"] = max(d["pred_max_abs_diff"], max(abs(x.get("p", 0) - y.get("p", 0)) for x, y in zip(pa, pb)))
            ia, ib = P.choose(pa), P.choose(pb)
            d["choice_diff"] += (pa[ia]["sig"] if ia is not None else None) != (pb[ib]["sig"] if ib is not None else None)
            perm = pa[:]
            rng.shuffle(perm)
            ip = P.choose(perm)
            d["perm_choice_diff"] += (perm[ip]["sig"] if ip is not None else None) != (pa[ia]["sig"] if ia is not None else None)
        res[arm] = d
    return {"roots": len(A), "scorer_views_identical": int(sum(same)), "labels_changed_roots": lab_changed, "evaluator_changed_roots": ev_changed,
            "model_roots": len(pick), "arms": res,
            "passed": all(same) and lab_changed == len(A) and all(v["coeff_max_abs_diff"] == 0 and v["pred_max_abs_diff"] == 0 and not v["choice_diff"]
                                                                   and not v["perm_choice_diff"] for v in res.values())}


def param_table() -> dict:
    """Total and active (receiving gradient in one real forward/backward) parameter counts per arm, plus the frozen LB reference."""
    import abc7_models as a7
    V = P.build(("val",))
    out = {}
    for arm in P.ARMS:
        m = P.build_model(arm, 0)
        tot, _ = P.batch_loss(m, [v[0] for v in V[:4]], [v[1] for v in V[:4]], 0.3 if P.ARMS[arm]["travel"] else 0.0)
        tot.backward()
        out[arm] = {"total": P.params(m), "active": sum(p.numel() for p in m.parameters() if p.grad is not None and p.grad.abs().sum() > 0),
                    "extra_heads": [h for h in ("xy", "xs") if hasattr(m, h)]}
    lb = a7.ModelBC7("B", "none", order="pred").double()
    out["LB (frozen reference)"] = {"total": P.params(lb), "active": None, "extra_heads": []}
    return out


def benchmark(n=5, seed=0) -> dict:
    """Forward + backward CPU per 12-root batch and early-stopping evaluation CPU per arm on real views. NO optimizer step, nothing saved."""
    torch.set_num_threads(1)
    V = P.build()
    tr = [v for v in V if v[2]["split"] == "train"]
    va = [v for v in V if v[2]["split"] == "val"]
    rng, out = np.random.default_rng(seed), {}
    for arm in P.ARMS:
        m = P.build_model(arm, seed)
        ts = []
        for _ in range(n + 1):
            idx = rng.choice(len(tr), 12, replace=False)
            t = time.process_time()
            tot, _ = P.batch_loss(m, [tr[i][0] for i in idx], [tr[i][1] for i in idx], 0.3 if P.ARMS[arm]["travel"] else 0.0)
            tot.backward()
            m.zero_grad()
            ts.append(time.process_time() - t)
        t = time.process_time()
        with torch.no_grad():
            [P.root_terms(m, s, l) for s, l, _ in va]
        out[arm] = {"update_cpu_s": float(np.mean(ts[1:])), "update_cpu_s_max": float(np.max(ts[1:])), "es_eval_cpu_s": time.process_time() - t}
    out["max_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    return out


def budget(bench, runs, expected_updates=1500) -> dict:
    """Per-run worst case = max_updates x the slowest measured batch + every early-stopping evaluation; the aggregate request covers every
    roster run at 1.25 x its expected cost (1500 updates: historical V1 runs stopped at 640-1000) plus evaluation, capped below the sum of
    worst cases; a projection checkpoint after 12 finished runs stops new launches if the projection exceeds the cap."""
    c = P.TRAIN
    worst = {a: c["max_updates"] * bench[a]["update_cpu_s_max"] + c["max_updates"] / c["eval_every"] * bench[a]["es_eval_cpu_s"] for a in P.ARMS}
    exp = {a: expected_updates * bench[a]["update_cpu_s"] + expected_updates / c["eval_every"] * bench[a]["es_eval_cpu_s"] for a in P.ARMS}
    n = collections.Counter(r["arm"] for r in runs)
    tot_worst = sum(worst[a] * n[a] for a in n)
    tot_exp = sum(exp[a] * n[a] for a in n)
    eval_cpu = 10000
    per_run = int(np.ceil(1.6 * max(worst.values()) / 100) * 100)                # 1.6 x: contention headroom over a single-process benchmark
    agg = int(np.ceil(min(tot_worst, 1.25 * tot_exp) / 1000) * 1000) + eval_cpu
    eff = 4                                                                        # memory-limited planning assumption (see memory_gate)
    return {"runs": len(runs), "runs_by_arm": dict(n), "per_run_worst_cpu_s": worst, "per_run_expected_cpu_s": exp,
            "sum_worst_cpu_s": tot_worst, "sum_expected_cpu_s": tot_exp, "evaluation_cpu_s": eval_cpu, "benchmark_max_rss_mb": bench["max_rss_mb"],
            "requested": {"aggregate_cpu_s": agg, "per_run_cpu_s": per_run, "workers": 8, "torch_threads_per_worker": 1,
                          "wall_s": int(np.ceil((agg / eff + per_run) / 600) * 600), "memory_floor_gb": 2.0},
            "memory_gate": "launch a worker only if available memory >= 2.0 GB + 0.8 GB per running worker (ramp 2 -> 4 -> 8); the host showed ~4 GB "
                           "available at P11, so the wall request assumes 4 effective workers",
            "expected_wall_s_8_workers": tot_exp / 8, "expected_wall_s_4_workers": tot_exp / 4, "checkpoint": "after 12 finished runs: projected = spent / expected(finished) x expected(all); "
                                                                   "stop launching (never kill a running run) if projected > aggregate cap"}


# ------------------------------------------------------------------ design
def design(bench=None) -> dict:
    sc, D, R, _ = P.load()
    fo = P.folds(D, R)
    runs = P.roster(D, R)
    split = {s: sorted(k for k in D["root_order"] if bd.split_of(R[k]) == s) for s in ("train", "val")}
    lb = {f"BXY-LB-s{s}": P.sha(LB / "ckpt" / f"BXY-LB-s{s}.pt") for s in P.SEEDS} | {f"PREDICTIONS_s{s}.json": P.sha(LB / f"PREDICTIONS_s{s}.json") for s in P.SEEDS}
    return {
        "version": "BXY_P11_TRAINING_DESIGN_V1", "gate": "BXY-P11-TRAINING-PREREG", "date": "2026-10-31",
        "evidence": {"sha256": P.EVIDENCE, "counts": P.EXPECT, "sidecar_version": sc["version"], "teacher_hash": sc["manifest"]["teacher_hash"][0],
                     "data_sha256": D["data_sha256"], "pmin_phase": P.PHASE},
        "custody": {"train": split["train"], "val": split["val"], "excluded": "34 historical test roots (exposed in P7): historical diagnostics only, never trained, "
                    "tuned, early-stopped or evaluated in P12", "rule": "bxy_data.split_of (family-grouped IID); build() raises on any test root"},
        "interface": {"scorer_keys": list(P.SCORER_KEYS), "candidate_keys": list(P.CAND_KEYS), "forbidden_substrings": list(P.FORBIDDEN),
                      "scene_inputs": "abc_models.Root of RECORDS.pt `inputs` only: object_xy, object_radius, is_active_target, is_obstacle (= object kind), "
                                      "robot_q, goal_xy, robot_fk_joints, DINOv2 visual features of the rendered scene",
                      "variables": "every F1-admissible PMIN_DEV_MATCHED design query of the root (outcome-free design) + parent Y of every X + Y0",
                      "candidate_order": "sorted by (m, action signature); the historical catalogue order (minimal success first) is never used",
                      "admissibility": "bxy_f1.screen complete_ok (x_ok, y_ok, no GOAL_BLOCKED); the zero-move candidate is always admissible",
                      "labels": "Labels object: observed X / Y (absent = marginalized), DIRECT success events, complete-witness travel",
                      "evaluator": "EvalView: candidate outcomes, teacher status / negative kind / failed phase / certificate, legacy roles, order groups, omissions"},
        "objective": {"model": "P(Y_s=1)=sigmoid(b_s/tau); P(X_q=1|Y=y)=sigmoid((a_q+w_q y)/tau); tau=1 (frozen)",
                      "p_success": "sigmoid(b_s) sigmoid(a_q+w_q); no-op: P(Y0=1) (X_empty = 1 by definition, no X variable)",
                      "L_joint": "mean over batch roots of -log P(D_c), exact per-unique-scene marginalization (bxy_p11.log_evidence == bxy_core.log_evidence == brute force)",
                      "L_travel": "sum over the batch's complete witnesses of Huber_delta=1(log1p J_hat, log1p J) / N_J (methodology §6.2 pooled form)",
                      "J_hat": "complete travel: jt(v_s, c) + softplus(cost(g_q)) for a nonempty prefix (relocations + connector + target), jt(v_0, c) for the no-op",
                      "L_total": "L_joint + lambda_J L_travel", "no_static_bce": True, "no_extra_pair_or_higher_order_terms": True},
        "arms": {
            "XY-quadratic": "primary: F2 a_q, F3 b_s, F5 w_q = xy(g_q, v_s, c); lambda_J = its own validation-selected lambda* in LAMBDAS",
            "XY-quadratic-noJ": "same model, lambda_J = 0; selection gamma = 0 (its travel head is untrained)",
            "XY-uncoupled": "same shared representation, w = 0; lambda* selected by the same rule",
            "XY-uncoupled-SA": "capacity / feature control: w = 0 and a_q += xs(g_q, v_s, c), a head with the SAME inputs and parameter count as the "
                               "coupling head; isolates the x*y interaction from extra scene features and capacity",
            "DIRECT": "protocol-aligned direct success: logit a_q (+ xs(g_q, v_s, c)) trained by root-summed BCE on x AND y of every decided X query, "
                      "no-op logit b_0 trained on Y0; same modules and parameter count as XY-quadratic; lambda_J = 0, gamma = 0",
            "LB (historical reference)": {"checkpoints_sha256": lb, "protocol": "trained on BD_GEN_V1 whole-sequence outcomes from the ACHIEVED robot state "
                                          "(different execution-outcome protocol); evaluated on val21 from its frozen predictions and later on the fresh cohort; "
                                          "not cross-fittable; gamma = 0"},
            "references": {"NOOP": "always the zero-move candidate", "SHORTEST_ADMISSIBLE": "shortest F1-admissible nonempty candidate (C_d, signature ties)",
                           "DISPLACEMENT_RANK": "smallest C_d F1-admissible nonempty candidate (m, signature ties)",
                           "VERIFY_FIRST (oracle)": "evaluator verifies admissible candidates in (m, C_d, signature) order; reports success and verifications",
                           "ORACLE_AVAILABILITY": "any admissible successful candidate in the root's catalogue"}},
        "feature_access": {"all learned arms": "scene inputs + ordered actions + edited endpoint scenes (identical); no label, role, travel or failure field",
                           "selection": "p, m, C_d (exact), J_hat (J-trained arms only), F1 admissibility", "LB": "same scene inputs, LB candidate encoding"},
        "training": P.TRAIN | {"seeds": list(P.SEEDS), "lambdas": list(P.LAMBDAS), "sampling": "uniform root sampling without replacement per update (root-balanced)",
                               "early_stopping_metric": "mean root NLL of the arm's own likelihood (joint NLL for XY, success BCE for DIRECT) on the early-stopping roots; "
                                                        "restore the best checkpoint",
                               "lambda_selection": "per J-trained arm: lambda* = argmin over LAMBDAS of the mean over 3 seeds of the best val21 joint NLL; a relative "
                                                   "difference <= 1e-3 is a tie -> smaller lambda",
                               "changes_from_historical": ["data: verified P-min V2 sidecar via leakage-separated views (was V1 / LB records)",
                                                           "travel loss pooled over witnesses per methodology §6.2 (was per-root mean)",
                                                           "J_hat includes target travel and the no-op target travel (was 0 for the no-op)",
                                                           "torch threads = 1 per worker (deterministic, 8 workers)", "early stopping on NLL only, never on selection"]},
        "roster": runs, "folds": fo,
        "selection": {"rule": P.RULE, "cost": "C(r) = -log p_succ(r) + alpha m(r) + beta C_d(r) + gamma J_hat(r), C_d in lattice cells (L = 0.08 m)",
                      "steps": ["F1 screen (zero-move kept)", "no-op gate: P(Y0=1) >= 0.5 -> zero-move", "admit p >= eta (eta = 0: never abstain)",
                                "argmin C, ties (m, C_d, signature)"],
                      "gamma_by_arm": {"XY-quadratic": 0.05, "XY-uncoupled": 0.05, "XY-uncoupled-SA": 0.05, "XY-quadratic-noJ": 0.0, "DIRECT": 0.0, "LB": 0.0},
                      "not_tuned": "fixed a priori: val21 has 10 initially infeasible roots, too few to tune 4 decision hyperparameters",
                      "secondary_abstaining": P.RULE | {"eta": 0.5}, "sensitivity_grid_report_only": P.SENSITIVITY,
                      "lexicographic_length_first": "preregistered ablation (alpha = 100), report only",
                      "selection_vs_training_weights": "alpha, beta, gamma, eta are decision hyperparameters; lambda_J is the training auxiliary weight"},
        "evaluation": {
            "development_primary": "CROSSFIT out-of-fold predictions of all 197 train+val roots (each root scored by models that never trained on it); "
                                   "per-root metrics averaged over the 3 seeds, then paired root-cluster bootstrap (B = 10000) between arms",
            "development_split": "SPLIT models on val21 (descriptive only; LB comparable only here)",
            "confirmatory": "SPLIT checkpoints (3 seeds per arm, frozen before the cohort exists) on the fresh independent cohort, evaluated once",
            "probability": {"sets": ["X: P(X=1) marginal vs every observed X", "Y: P(Y=1) vs every observed Y",
                                     "success: p_succ vs x AND y of every decided X query + P(Y0) vs Y0", "joint observed-data NLL per root (XY arms)"],
                            "metrics": "root-averaged log loss and Brier (each root weight 1), pooled log loss / Brier, ECE10, reliability diagrams"},
            "selection": ["success on initially infeasible roots (Y0 = 0) [PRIMARY decision metric]", "overall success", "false repair on Y0 = 1 roots",
                          "abstention", "oracle availability", "optimal (fewest moves among successes)", "chosen m, C_d", "witnessed J_total of successful choices",
                          "travel regret vs the root's minimum successful J"],
            "ordering": "concordance of p_succ (and P(X)) on discordant same-endpoint order pairs, separately for the certified (sound relocation certificate) "
                        "and budget/planner-policy failing orders; never pooled into a single causal claim",
            "omission": "sign agreement of predicted changes (P(X), P(Y), p_succ) with decided full -> omitted transitions; two-move interaction table "
                        "descriptive; no geometrically-necessary-cause claim from planner-budget zeros (only the certified subset may support one)",
            "strata": "K0 / K1 / K>=2 / unknown-K reported separately with the actual number of independent roots; no claim when a stratum has < 10 roots",
            "uncertainty": "root-cluster bootstrap; per-seed results also reported; queries are never treated as independent samples",
            "coupling_decision": {"primary_metric": "root-averaged success log loss (lower better)", "key_secondary": "success on initially infeasible roots",
                                  "controls": ["XY-uncoupled", "XY-uncoupled-SA"],
                                  "BENEFICIAL": "Delta logloss (quadratic - control) CI upper < 0 vs BOTH controls, selection non-inferior (CI lower > -0.05) vs both, "
                                                ">= 2 of 3 seeds individually improve vs both",
                                  "UNSUPPORTED": "point estimate Delta logloss >= 0 vs either control, or selection point estimate < 0 with CI lower <= -0.05",
                                  "INCONCLUSIVE": "otherwise", "w_nonzero_is_not_evidence": True,
                                  "deployment": "if not BENEFICIAL on the fresh cohort, the learned coupling is removed from the deployed model (methodology §8.2)",
                                  "development_label": "a CROSSFIT verdict is development evidence only; the confirmatory verdict is the fresh-cohort one"},
            "travel_decision": "lambda* retained over 0 only if XY-quadratic vs XY-quadratic-noJ: Delta success logloss CI upper < 0.02 (calibration not "
                               "sacrificed) and paired witnessed J of successful choices lower with CI upper < 0",
            "direct_decision": "the factorized model is preferred over DIRECT only if it is not worse on success logloss (CI upper < 0.02) and selection "
                               "(CI lower > -0.05); otherwise DIRECT / LB is reported as the simpler alternative",
            "visualizations": ["reliability diagrams of P(X), P(Y), p_succ per arm", "per-root paired difference plots with bootstrap CIs",
                               "loss curves (train total / NLL / travel, early-stopping NLL) per run", "order-contrast panels (certified vs budget) with scenes",
                               "no-op decisions (P(Y0) vs Y0 per root)", "selection error gallery: false repairs and missed repairs with scenes",
                               "failure categories of chosen candidates (relocation / connector / target, certified vs budget)",
                               "successful selected corrections with replayed witnesses", "w distribution by four-cell outcome (descriptive only)"]},
        "budget": budget(bench, runs) if bench else None,
        "fresh_cohort_protocol": fresh_cohort(),
        "limitations": LIMITATIONS,
        "stop": "P11 performs no training, tuning, teacher query, scene generation, test evaluation, PREFIX_COMPLETE, P-full or 3D work"}


def fresh_cohort() -> dict:
    return {"status": "PLAN ONLY (not generated)", "purpose": "the confirmatory, never-seen evaluation of the frozen SPLIT checkpoints",
            "generator": "a new versioned BD_GEN generator seed space disjoint from BD_GEN_V1 families (new family ids, new seeds, hash-checked disjointness)",
            "target_mix": {"K0": "<= 30%", "K1": ">= 20%", "K2": ">= 20%", "K3": ">= 15%", "K4": ">= 10%", "order_sensitive_roots": ">= 25% (by construction, verified)",
                           "connector_stress": ">= 10% roots with cluttered goal-side workspace", "multi_obstacle": "4-8 movable objects, 1-2 fixed"},
            "size": "planning target >= 300 independent roots with >= 200 initially infeasible (about 4x the 55 available now); the exact size is set by a "
                    "paired-root power calculation that uses the CROSSFIT discordance rate, inside the cohort's own budget request",
            "catalogue": "outcome-blind proposer: candidates enumerated from geometry only (all sufficient blocker subsets of the analytic swept-volume "
                         "obstruction set up to 4 moves, both orders for 2-move sets, one alternative destination, one redundant and one wrong-destination "
                         "control, a fixed number per root by a seeded rule); no teacher outcome of a candidate decides whether it enters the catalogue; "
                         "the catalogue is frozen and hashed before any teacher query",
            "labels": "the frozen BXY teacher (same teacher hash, budgets, q_ref, F1) queries X, Y, Y0 for every admissible catalogue candidate plus "
                      "reversals and omissions; independent replay of every positive",
            "custody": "generated, labelled and hashed by a runner that cannot import model code; frozen before any model is evaluated; evaluated once",
            "historical_test": "the 34 exposed BD_GEN_V1 test roots remain historical diagnostics only"}


LIMITATIONS = ["val21 is small (10 initially infeasible roots): SPLIT validation results are descriptive; development comparisons use 197-root cross-fitting "
               "and confirmation needs the fresh cohort",
               "K0 dominates (142 / 197 roots); K>=2 has 9 roots and unknown-K 9; K3 / K4 are essentially absent -> no stratum claim with < 10 roots",
               "most negatives are budget-limited (X 328 of 490, Y 281 of 345): zeros are budget-policy-relative, not impossibility; certified subsets are small "
               "(X 162, Y 64; 24 certified order failures)",
               "the historical catalogue is outcome-guided (BD_GEN_V1 'minimal' = first teacher-verified success, other roles derived from it): scorers never see "
               "roles or catalogue order, but catalogue composition inflates oracle availability (48 / 55 infeasible roots) for every method alike",
               "every P-min variable is observed: exact marginalization is tested but inactive on this data (it matters for PREFIX_COMPLETE and future cohorts)",
               "conditional independence of X queries given their shared Y is a modelling approximation",
               "lambda* selection uses val21; val roots later appear as cross-fit held-out roots (low-dimensional choice; disclosed)",
               "LB is trained on a different execution-outcome protocol and cannot be cross-fitted; its comparison is val21 + fresh cohort only",
               "travel labels are first-witness teacher-policy travel, not minimum travel"]


# ------------------------------------------------------------------ freezing
def freeze(D=None) -> dict:
    D = D or design()
    text = json.dumps(D, indent=1, sort_keys=True, default=str)
    f = OUT / "TRAINING_DESIGN.json"
    if f.exists() and f.read_text() != text:
        raise FileExistsError(f"{f} is frozen and differs from the recomputed design")
    OUT.mkdir(parents=True, exist_ok=True)
    f.write_text(text)
    lock = {"design_sha256": P.sha(f), "evidence_sha256": P.EVIDENCE, "sources": PM.sources(ENTRY), "git_head_at_freeze": PM.git("rev-parse", "HEAD"),
            "frozen_at": time.time(), "authorized": False, "requested_budget": (D.get("budget") or {}).get("requested"),
            "note": "authorized stays false; a training gate needs a separate, versioned authorization manifest (never a rewrite of this lock)"}
    lf = OUT / "TRAINING_LOCK.json"
    if lf.exists():
        old = json.loads(lf.read_text())
        if {k: v for k, v in old.items() if k not in ("frozen_at", "git_head_at_freeze")} != {k: v for k, v in lock.items() if k not in ("frozen_at", "git_head_at_freeze")}:
            raise FileExistsError(f"{lf} is frozen and differs")
        return old
    lf.write_text(json.dumps(lock, indent=1, sort_keys=True))
    return lock


def assert_frozen(check_git=True) -> dict:
    """Launch guard of the next gate: design == lock, evidence hashes, no semantic source drift, both files committed and clean."""
    lock, bad = json.loads((OUT / "TRAINING_LOCK.json").read_text()), []
    if P.sha(OUT / "TRAINING_DESIGN.json") != lock["design_sha256"]:
        bad.append("design differs from the lock")
    bad += [f"evidence {f}" for f, h in lock["evidence_sha256"].items() if P.sha(PM.OUT / f) != h]
    now = PM.sources(ENTRY)
    bad += [f"source drift: {f}" for f in sorted(set(now) | set(lock["sources"])) if now.get(f) != lock["sources"].get(f)]
    if check_git:
        for f in ("TRAINING_DESIGN.json", "TRAINING_LOCK.json"):
            p = str(OUT / f)
            if sp.run(["git", "ls-files", "--error-unmatch", p], capture_output=True).returncode or sp.run(["git", "diff", "--quiet", "HEAD", "--", p]).returncode:
                bad.append(f"{f} not committed / not clean")
    if bad:
        raise RuntimeError("; ".join(bad))
    return lock


def preflight() -> dict:
    lock = assert_frozen(check_git=False)
    D = json.loads((OUT / "TRAINING_DESIGN.json").read_text())
    reg = OUT / "regression"
    logs = {p.name: (p.read_text().strip().splitlines() or [""])[-1] for p in sorted(reg.glob("*.log"))} if reg.exists() else {}
    rep = (reg / "replay_exit.txt").read_text().split() if (reg / "replay_exit.txt").exists() else []
    out = {"lock_design_sha256": lock["design_sha256"], "evidence": P.evidence(), "audit": audit(), "leakage": leakage_audit(), "params": param_table(),
           "benchmark_in_design": (D.get("budget") or {}), "regression": {"pytest_tail": logs, "replays": dict(zip(rep[0::2], rep[1::2]))},
           "no_training_performed": True, "optimizer_steps": 0, "teacher_queries": 0, "test_roots_touched": 0}
    out["passed"] = bool(out["leakage"]["passed"] and out["audit"]["splits"]["families_straddling_train_val"] == 0 and
                         out["audit"]["splits"]["test_roots_in_design"] == 0 and out["audit"]["dedup"]["x_rows"] == out["audit"]["dedup"]["x_unique"] and
                         out["audit"]["dedup"]["y_rows"] == out["audit"]["dedup"]["y_unique"] and out["audit"]["travel"]["on_failed_candidates"] == 0 and
                         out["audit"]["noop"]["x_variables_with_empty_prefix"] == 0 and out["audit"]["encoding"]["x_seq_length_mismatch"] == 0)
    (OUT / "PREFLIGHT.json").write_text(json.dumps(out, indent=1, sort_keys=True, default=str))
    return out


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "freeze":
        b = benchmark()
        print(json.dumps({"benchmark": b, "lock": {k: v for k, v in freeze(design(b)).items() if k != "sources"}}, indent=1, default=str))
    elif cmd == "preflight":
        r = preflight()
        print(json.dumps({k: r[k] for k in ("passed", "leakage", "params")}, indent=1, default=str))
    elif cmd == "figures":
        import bxy_p11_viz
        print(bxy_p11_viz.all_figures())
