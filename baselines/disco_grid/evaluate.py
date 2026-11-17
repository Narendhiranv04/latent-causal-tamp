#!/usr/bin/env python3
"""DISCO-Grid Open-Loop and Closed-Loop Inference, Verification, and Metrics (`DISCO_plan.md` Sections 10 & 11).

Implements:
1. `select_action_model_only`:
   Model-only candidate generation (`B_test` unique legal actions from `pi_theta`) and ranking
   (by `pi_theta` alone or by `Q_phi(h_t, a)`), including learned `STOP` decision scoring.
   Guaranteed ZERO physical simulator or motion-planner calls during selection.
2. `predict_open_loop_sequence` (Primary Matched-Protocol Baseline, Section 10.2):
   Autoregressively generates at most 3 corrective actions from initial scene `S0` using deterministic
   predicted cell edits (`predict_observation_edit`), committing ONE complete sequence (or NOOP / ABSTAIN).
   Independently verified once by the physical teacher (`execute_complete_sequence`), with zero retries.
3. `run_closed_loop_episode` (Published-Style Secondary Baseline, Section 10.3):
   Executes one selected action at a time in `RepairEnv`, observes the actual resulting state, and selects
   the next action using frozen `pi_theta` / `Q_phi` without test-time MCTS or candidate screening.
4. `compute_benchmark_metrics` & `paired_bootstrap_ci`:
   Computes Task Success (`Z = 1` on K1-K3), per-stratum K1/K2/K3 success, Repair Success (certified K),
   K0 No-Op accuracy, NONE Abstention accuracy, corrective displacement `D(r)`, witnessed robot travel `J`,
   neural model calls, physical planner calls, latency, and failure taxonomy.
"""
from __future__ import annotations

import collections
import contextlib
import hashlib
import json
import math
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import data as D
import distill as DS
import env as E
import policy as P

# Wall-clock limits for physical verification. A query that exceeds its limit is recorded as
# UNRESOLVED (verified=None) and reported separately -- never silently counted as infeasible.
SEQ_TIMEOUT_S = {"2d": 300, "3d": 600}          # one complete committed sequence (X chain + connector [+ Y])
EPISODE_TIMEOUT_S = {"2d": 900, "3d": 1500}     # one closed-loop episode (all executed steps + STOP)
SEQS_PER_JOB = 4                                # verification job granularity (keeps per-root teacher caches warm)


class QueryTimeout(BaseException):
    """BaseException so teacher-internal `except Exception` blocks cannot swallow it."""


def _raise_timeout(signum, frame):
    raise QueryTimeout()


@contextlib.contextmanager
def time_limit(seconds: float):
    old = signal.signal(signal.SIGALRM, _raise_timeout)
    signal.setitimer(signal.ITIMER_REAL, float(seconds))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def initial_observation_from_row(row: dict[str, Any], dom: str) -> E.LearnerObservation:
    """Construct the initial `LearnerObservation` directly from `row['inputs']` with ZERO simulator calls."""
    dom_l = dom.lower()
    inp = row["inputs"]
    leg = D.legal_actions_at_prefix(inp, dom_l, [], include_stop=True)
    return E.LearnerObservation(
        root_id=row["root_id"],
        domain=dom_l,
        ids=list(inp["ids"]),
        cells=[int(c) for c in inp["cells0"]],
        xy=[list(x) for x in inp["xy0"]],
        attrs=[list(a) for a in inp["attrs"]],
        tid=int(inp["tid"]),
        goal_cell=int(inp["goal_cell"]),
        goal_xy=list(inp["goal"]),
        base_xy=list(inp["base"]),
        ctx=list(inp["ctx"]),
        legal_cells=[int(c) for c in inp["legal_cells"]],
        cell_xy=dict(inp["cell_xy"]),
        moved_mask=[False] * len(inp["ids"]),
        remaining_steps=3,
        eligible_objects=leg["eligible_objects"],
        legal_destinations=leg["legal_destinations"],
        can_stop=True,
        is_predicted_edit=False,
        q_t_optional=None,
    )


def analytic_displacement(inp: dict[str, Any], dom: str, seq: list[tuple[int, int]]) -> float:
    """Summed Euclidean object displacement in units of cell pitch (`search.Root.displacement`)."""
    if not seq:
        return 0.0
    pitch = 0.08 if dom.lower() == "2d" else 0.075
    cell_xy = inp["cell_xy"]
    cells0 = inp["cells0"]
    return float(sum(math.dist(cell_xy[str(cells0[int(o)])], cell_xy[str(int(d))]) for o, d in seq) / pitch)


@E.selection_only
def select_action_model_only(
    obs: E.LearnerObservation,
    proposal: P.PolicyProposalWrapper,
    B_test: int = 16,
    use_value: bool = True,
    rule: dict[str, float] | None = None,
    rng: np.random.Generator | None = None,
) -> dict[str, Any]:
    """Select one action (`(o, d)` or `'STOP'`) at `obs` using ONLY neural policy/value evaluations.
    Never invokes `RepairEnv` or any physical teacher.
    """
    rule = {
        "noop_q_gate": 0.55,
        "stop_q_margin": 0.02,
        "abstain_eta": 0.0,
        "policy_stop_thresh": 0.45,
        **(rule or {}),
    }
    rng = rng or np.random.default_rng(0)

    if obs.remaining_steps <= 0 or not obs.eligible_objects or not obs.legal_destinations:
        return {
            "selected": "STOP",
            "score": 1.0,
            "stop_score": 1.0,
            "n_candidates": 0,
            "candidates": [],
        }

    samp = proposal.sample_candidates(obs, B=B_test, rng=rng)
    cands = samp["candidates"]
    c_probs = samp["probs"]
    stop_prob = float(samp["stop_prob"])

    if not cands:
        return {
            "selected": "STOP",
            "score": stop_prob,
            "stop_score": stop_prob,
            "n_candidates": 0,
            "candidates": [],
        }

    depth = 3 - obs.remaining_steps

    if use_value and proposal.value_model is not None:
        all_acts: list[tuple[int, int] | str] = list(cands) + ["STOP"]
        q_scores = proposal.score_actions_q(obs, all_acts)
        reloc_q = q_scores[:-1]
        stop_q = float(q_scores[-1])
        # Optional named root-STOP calibration ablation, fitted on VAL only.
        # Defaults reproduce the archived raw-Q selector exactly.
        if depth == 0 and (rule.get("root_stop_temperature", 1.) != 1. or rule.get("root_stop_bias", 0.) != 0.):
            temp = float(rule.get("root_stop_temperature", 1.))
            bias = float(rule.get("root_stop_bias", 0.))
            if not math.isfinite(temp) or temp <= 0 or not math.isfinite(bias):
                raise ValueError("Invalid root STOP calibration")
            clipped = min(1.-1e-7, max(1e-7, stop_q))
            logit = (math.log(clipped / (1.-clipped)) / temp) + bias
            stop_q = float(1. / (1. + math.exp(-max(-80., min(80., logit)))))

        # Rank relocation candidates by Q (tie-break by policy probability)
        ranked_idx = sorted(range(len(cands)), key=lambda i: (round(float(reloc_q[i]), 6), float(c_probs[i])), reverse=True)
        ranked_cands = [cands[i] for i in ranked_idx]
        ranked_scores = [float(reloc_q[i]) for i in ranked_idx]
        best_act = ranked_cands[0]
        best_q = ranked_scores[0]

        if depth == 0:
            # At root: choose STOP (NOOP) if stop_q passes noop_q_gate and beats best_q - margin
            if stop_q >= rule["noop_q_gate"] and stop_q >= best_q - rule["stop_q_margin"]:
                return {
                    "selected": "STOP",
                    "score": stop_q,
                    "stop_score": stop_q,
                    "best_reloc_score": best_q,
                    "n_candidates": len(cands),
                    "candidates": cands,
                    "ranked_candidates": ranked_cands,
                    "ranked_scores": ranked_scores,
                }
            if best_q < rule["abstain_eta"]:
                return {
                    "selected": "ABSTAIN",
                    "score": best_q,
                    "stop_score": stop_q,
                    "best_reloc_score": best_q,
                    "n_candidates": len(cands),
                    "candidates": cands,
                    "ranked_candidates": ranked_cands,
                    "ranked_scores": ranked_scores,
                }
        else:
            # At intermediate prefix (depth 1 or 2): choose STOP if stop_q >= best_q - margin
            if stop_q >= best_q - rule["stop_q_margin"] and stop_q >= rule.get("stop_q_min", 0.35):
                return {
                    "selected": "STOP",
                    "score": stop_q,
                    "stop_score": stop_q,
                    "best_reloc_score": best_q,
                    "n_candidates": len(cands),
                    "candidates": cands,
                    "ranked_candidates": ranked_cands,
                    "ranked_scores": ranked_scores,
                }

        return {
            "selected": best_act,
            "score": best_q,
            "stop_score": stop_q,
            "best_reloc_score": best_q,
            "n_candidates": len(cands),
            "candidates": cands,
            "ranked_candidates": ranked_cands,
            "ranked_scores": ranked_scores,
        }

    # Policy-only selection (no Q network)
    ranked_idx = sorted(range(len(cands)), key=lambda i: float(c_probs[i]), reverse=True)
    ranked_cands = [cands[i] for i in ranked_idx]
    ranked_scores = [float(c_probs[i]) for i in ranked_idx]
    best_act = ranked_cands[0]
    best_p = ranked_scores[0]

    if depth == 0 and stop_prob >= rule.get("noop_pol_gate", 0.50):
        return {
            "selected": "STOP",
            "score": stop_prob,
            "stop_score": stop_prob,
            "best_reloc_score": best_p,
            "n_candidates": len(cands),
            "candidates": cands,
            "ranked_candidates": ranked_cands,
            "ranked_scores": ranked_scores,
        }
    if depth >= 1 and stop_prob >= rule["policy_stop_thresh"]:
        return {
            "selected": "STOP",
            "score": stop_prob,
            "stop_score": stop_prob,
            "best_reloc_score": best_p,
            "n_candidates": len(cands),
            "candidates": cands,
            "ranked_candidates": ranked_cands,
            "ranked_scores": ranked_scores,
        }
    return {
        "selected": best_act,
        "score": best_p,
        "stop_score": stop_prob,
        "best_reloc_score": best_p,
        "n_candidates": len(cands),
        "candidates": cands,
        "ranked_candidates": ranked_cands,
        "ranked_scores": ranked_scores,
    }


@E.selection_only
def predict_open_loop_sequence(
    row: dict[str, Any],
    dom: str,
    proposal: P.PolicyProposalWrapper,
    B_test: int = 16,
    use_value: bool = True,
    rule: dict[str, float] | None = None,
    seed: int = 0,
) -> dict[str, Any]:
    """Primary Matched-Protocol Open-Loop Inference (`DISCO_plan.md` Section 10.2).
    Autoregressively generates a single committed corrective sequence (`len <= 3`), `NOOP` (`[]`),
    or `ABSTAIN` (`None`) using ONLY predicted object-position edits (`predict_observation_edit`).
    Zero physical simulator or teacher queries occur during sequence generation.
    """
    if proposal.observation_schema != P.O0:
        raise ValueError("Strict open-loop inference requires O0; O1 is closed-loop only")
    t0 = time.time()
    p_calls_0 = proposal.policy_calls
    v_calls_0 = proposal.value_calls

    obs = initial_observation_from_row(row, dom)
    committed_seq: list[tuple[int, int]] = []
    step_traces = []
    abstained = False

    for step_t in range(3):
        step_rng = np.random.default_rng(
            int(hashlib.sha256(f"eval_step|{row['root_id']}|{seed}|{step_t}".encode()).hexdigest()[:8], 16)
        )
        dec = select_action_model_only(obs, proposal, B_test=B_test, use_value=use_value, rule=rule, rng=step_rng)
        sel = dec["selected"]
        step_traces.append({
            "step": step_t,
            "selected": sel if isinstance(sel, str) else list(sel),
            "score": round(float(dec["score"]), 5),
            "stop_score": round(float(dec["stop_score"]), 5),
            "n_candidates": dec["n_candidates"],
        })
        if sel == "ABSTAIN":
            abstained = True
            break
        if sel == "STOP":
            break
        committed_seq.append((int(sel[0]), int(sel[1])))
        obs = E.predict_observation_edit(obs, (int(sel[0]), int(sel[1])))

    status = "ABSTAIN" if abstained else ("NOOP" if not committed_seq else "REPAIR")
    return {
        "root_id": row["root_id"],
        "domain": dom.lower(),
        "split": row["split"],
        "K_legacy": row["K_legacy"],
        "masks": row["masks"],
        "protocol": "open_loop",
        "observation_schema": proposal.observation_schema,
        "policy_call_unit": "scored examples (batched forwards counted separately)",
        "seed": seed,
        "status": status,
        "seq": [[int(o), int(d)] for o, d in committed_seq] if not abstained else None,
        "m": None if abstained else len(committed_seq),
        "displacement": None if abstained else round(analytic_displacement(row["inputs"], dom, committed_seq), 4),
        "policy_calls": proposal.policy_calls - p_calls_0,
        "value_calls": proposal.value_calls - v_calls_0,
        "planner_calls_during_selection": 0,
        "latency_ms": round((time.time() - t0) * 1000.0, 3),
        "step_traces": step_traces,
    }


def run_closed_loop_episode(
    env: E.RepairEnv,
    row: dict[str, Any],
    proposal: P.PolicyProposalWrapper,
    B_test: int = 16,
    use_value: bool = True,
    rule: dict[str, float] | None = None,
    seed: int = 0,
    max_action_retries: int = 0,
) -> dict[str, Any]:
    """Secondary Published-Style Closed-Loop Deployment (`DISCO_plan.md` Section 10.3).
    Executes one chosen action at a time in `RepairEnv`, observes the actual resulting state, and chooses
    the next action without test-time MCTS or candidate motion-planner pre-screening.
    Default `max_action_retries=0` counts any physically failed selected correction immediately as failure.
    When `max_action_retries=1` (disclosed separately per Section 10.3 item 3), allows at most 1 retry
    from the next-highest ranked candidate in `C_theta(h_t)` if an executed step fails.
    """
    if max_action_retries != 0:
        raise ValueError("Retries require certified post-failure state; Stage 2 supports no-retry only")
    t0 = time.time()
    p_calls_0 = proposal.policy_calls
    v_calls_0 = proposal.value_calls

    st = env.reset(row["root_id"], seed=seed)
    executed_seq: list[tuple[int, int]] = []
    planner_calls = 0
    retries_used = 0
    abstained = False
    failed_mid_episode = False
    failed_phase = None
    failure_kind = None
    unresolved_mid_episode = False

    for step_t in range(3):
        obs = env.observe(st, include_qt=proposal.observation_schema == P.O1)
        step_rng = np.random.default_rng(
            int(hashlib.sha256(f"eval_step|{row['root_id']}|{seed}|{step_t}".encode()).hexdigest()[:8], 16)
        )
        dec = select_action_model_only(obs, proposal, B_test=B_test, use_value=use_value, rule=rule, rng=step_rng)
        sel = dec["selected"]
        if sel == "ABSTAIN":
            abstained = True
            break
        if sel == "STOP":
            break

        ranked_cands = dec.get("ranked_candidates") or [sel]
        step_succeeded = False
        last_attempt = None
        for attempt_idx in range(min(1 + max_action_retries, len(ranked_cands))):
            cand = ranked_cands[attempt_idx]
            act = (int(cand[0]), int(cand[1]))
            last_attempt = act
            if attempt_idx > 0:
                retries_used += 1
            sr = env.transition(st, act)
            planner_calls += sr.planner_calls
            if sr.status == "EXECUTED" and sr.next_state is not None:
                executed_seq.append(act)
                st = sr.next_state
                step_succeeded = True
                break
            failed_phase = f"relocation:{step_t}"
            failure_kind = sr.failure_kind
            if sr.status == "UNRESOLVED":
                unresolved_mid_episode = True
                break

        if not step_succeeded:
            # Record the action that was actually attempted last (the failed physical edit)
            executed_seq.append(last_attempt)
            failed_mid_episode = True
            break

    if abstained:
        return {
            "root_id": row["root_id"],
            "domain": env.domain,
            "split": row["split"],
            "K_legacy": row["K_legacy"],
            "masks": row["masks"],
            "protocol": "closed_loop",
            "max_action_retries": max_action_retries,
            "action_retries_used": retries_used,
            "seed": seed,
            "status": "ABSTAIN",
            "seq": None,
            "m": None,
            "displacement": None,
            "verified": 0,
            "x": None,
            "y": None,
            "failed_phase": "abstain",
            "failure_kind": "ABSTAIN",
            "policy_calls": proposal.policy_calls - p_calls_0,
            "value_calls": proposal.value_calls - v_calls_0,
            "execution_planner_calls": planner_calls,
            "wall_s": round(time.time() - t0, 3),
        }

    if failed_mid_episode:
        # X = 0 is physically decided (a selected relocation failed), so Z = 0 regardless of Y;
        # Y is not queried (saves teacher time; disclosed in the report).
        return {
            "root_id": row["root_id"],
            "domain": env.domain,
            "split": row["split"],
            "K_legacy": row["K_legacy"],
            "masks": row["masks"],
            "protocol": "closed_loop",
            "max_action_retries": max_action_retries,
            "action_retries_used": retries_used,
            "seed": seed,
            "status": "REPAIR",
            "seq": [[int(o), int(d)] for o, d in executed_seq],
            "m": len(executed_seq),
            "displacement": round(analytic_displacement(row["inputs"], env.domain, executed_seq), 4),
            "verified": None if unresolved_mid_episode else 0,
            "x": None if unresolved_mid_episode else 0,
            "y": None,
            "failed_phase": failed_phase,
            "failure_kind": failure_kind,
            "policy_calls": proposal.policy_calls - p_calls_0,
            "value_calls": proposal.value_calls - v_calls_0,
            "execution_planner_calls": planner_calls,
            "wall_s": round(time.time() - t0, 3),
        }

    stop_res = env.terminal_query(st, evaluate_y_on_x_fail=False)
    planner_calls += stop_res.planner_calls
    status = "NOOP" if not executed_seq else "REPAIR"
    return {
        "root_id": row["root_id"],
        "domain": env.domain,
        "split": row["split"],
        "K_legacy": row["K_legacy"],
        "masks": row["masks"],
        "protocol": "closed_loop",
        "max_action_retries": max_action_retries,
        "action_retries_used": retries_used,
        "seed": seed,
        "status": status,
        "seq": [[int(o), int(d)] for o, d in executed_seq],
        "m": len(executed_seq),
        "displacement": round(analytic_displacement(row["inputs"], env.domain, executed_seq), 4),
        "verified": stop_res.z_outcome,
        "x": stop_res.x_terminal,
        "y": stop_res.y_target,
        "failed_phase": stop_res.failed_phase,
        "failure_kind": stop_res.failure_kind,
        "policy_calls": proposal.policy_calls - p_calls_0,
        "value_calls": proposal.value_calls - v_calls_0,
        "execution_planner_calls": planner_calls,
        "wall_s": round(time.time() - t0, 3),
    }


def lookup_existing_snapshot_label(row: dict[str, Any], seq: list[list[int]] | None) -> dict[str, Any] | None:
    """Check if `(row['root_id'], seq)` is already decided in `row['labels']` of the verified snapshot."""
    if seq is None:
        return None
    ek = json.dumps(sorted(map(tuple, seq)))
    ylab = {json.dumps(sorted(map(tuple, y["edit"]))): y["y"] for y in row["labels"]["Y"]}
    if not seq:
        if "[]" in ylab and ylab["[]"] in (0, 1):
            yv = int(ylab["[]"])
            return {"x": 1, "y": yv, "z": int(yv == 1), "failed_phase": None if yv == 1 else "target", "failure_kind": None if yv == 1 else "TARGET_FAILED", "source": "snapshot"}
        return None
    xk = json.dumps([[int(o), int(d)] for o, d in seq])
    xlab = {json.dumps(q["seq"]): q for q in row["labels"]["X"] if q.get("x") in (0, 1)}
    if xk in xlab and ek in ylab and ylab[ek] in (0, 1):
        q = xlab[xk]
        xv, yv = int(q["x"]), int(ylab[ek])
        zv = int(xv == 1 and yv == 1)
        ph = q.get("x_phase") if xv == 0 else (None if yv == 1 else "target")
        return {"x": xv, "y": yv, "z": zv, "failed_phase": ph, "failure_kind": ph, "source": "snapshot"}
    return None


def compute_benchmark_metrics(outcomes: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute primary and secondary metrics (`DISCO_plan.md` Section 11.2) from verified outcomes."""
    task_rows = [o for o in outcomes if o["masks"]["eval_task"]]
    rep_rows = [o for o in outcomes if o["masks"]["eval_repair"]]
    k0_rows = [o for o in outcomes if o["masks"]["eval_noop"]]
    none_rows = [o for o in outcomes if o["masks"]["eval_abstain"]]

    is_task_succ = lambda o: o.get("verified") == 1 and o["status"] == "REPAIR"  # noqa: E731
    is_unres = lambda o: o["status"] != "ABSTAIN" and o.get("verified") is None  # noqa: E731

    by_k = {}
    for k_cls in ("1", "2", "3"):
        sub = [o for o in task_rows if str(o["K_legacy"]) == k_cls]
        by_k[f"K{k_cls}_success"] = round(float(np.mean([is_task_succ(o) for o in sub])), 4) if sub else None
        by_k[f"n_K{k_cls}"] = len(sub)
        by_k[f"n_K{k_cls}_unresolved"] = sum(1 for o in sub if is_unres(o))

    # Check if any legacy NONE root received a newly verified physical repair (DISCO_plan.md Section 10.4)
    novel_none_repairs = [o["root_id"] for o in none_rows if is_task_succ(o)]

    fail_counts = collections.Counter()
    for o in task_rows:
        if not is_task_succ(o):
            if o["status"] == "NOOP":
                fail_counts["early_STOP_noop_on_task_root"] += 1
            elif o["status"] == "ABSTAIN":
                fail_counts["abstained_on_task_root"] += 1
            elif is_unres(o):
                fail_counts["UNRESOLVED_" + str(o.get("failed_phase") or "timeout")] += 1
            else:
                ph = o.get("failed_phase") or "unknown_failure"
                if str(o.get("failure_kind")) == "TIMEOUT":
                    ph = f"{ph}|teacher_budget_TIMEOUT"
                fail_counts[str(ph)] += 1

    succ_task = [o for o in task_rows if is_task_succ(o)]
    n_unres_task = sum(1 for o in task_rows if is_unres(o))
    decided_task = [o for o in task_rows if not is_unres(o)]
    return {
        "n_total": len(outcomes),
        "n_distinct_roots": len({o["root_id"] for o in outcomes}),
        "n_distinct_task_roots": len({o["root_id"] for o in task_rows}),
        "task_macro_K1_K2_K3": float(np.mean([by_k[f"K{k}_success"] for k in (1, 2, 3) if by_k[f"K{k}_success"] is not None])) if task_rows else None,
        "none_explicit_abstain_rate": float(np.mean([o["status"] == "ABSTAIN" for o in none_rows])) if none_rows else None,
        "none_noop_rate": float(np.mean([o["status"] == "NOOP" for o in none_rows])) if none_rows else None,
        "task_success": round(float(np.mean([is_task_succ(o) for o in task_rows])), 4) if task_rows else None,
        "task_success_lower_bound_note": "task_success counts UNRESOLVED as not-success; see task_success_upper and n_task_unresolved",
        "task_success_upper": round(float(np.mean([is_task_succ(o) or is_unres(o) for o in task_rows])), 4) if task_rows else None,
        "task_success_on_decided": round(float(np.mean([is_task_succ(o) for o in decided_task])), 4) if decided_task else None,
        "n_task_unresolved": n_unres_task,
        "n_task": len(task_rows),
        **by_k,
        "repair_success": round(float(np.mean([is_task_succ(o) and o.get("m") == int(o["K_legacy"]) for o in rep_rows])), 4) if rep_rows else None,
        "n_repair": len(rep_rows),
        "noop_accuracy_K0": round(float(np.mean([o["status"] == "NOOP" and o.get("verified") == 1 for o in k0_rows])), 4) if k0_rows else None,
        "noop_selected_rate_K0": round(float(np.mean([o["status"] == "NOOP" for o in k0_rows])), 4) if k0_rows else None,
        "n_k0": len(k0_rows),
        "abstain_rate_NONE": round(float(np.mean([o["status"] in ("ABSTAIN", "NOOP") for o in none_rows])), 4) if none_rows else None,
        "novel_verified_repairs_on_NONE": len(novel_none_repairs),
        "novel_NONE_root_ids": novel_none_repairs,
        "n_none": len(none_rows),
        "unverified_count": sum(1 for o in outcomes if o["status"] != "ABSTAIN" and o.get("verified") is None),
        "mean_relocations_success": round(float(np.mean([o["m"] for o in succ_task if o.get("m") is not None])), 3) if succ_task else None,
        "mean_displacement_success": round(float(np.mean([o["displacement"] for o in succ_task if o.get("displacement") is not None])), 3) if succ_task else None,
        "mean_policy_calls": round(float(np.mean([o.get("policy_calls", 0) for o in outcomes])), 2) if outcomes else 0.0,
        "mean_value_calls": round(float(np.mean([o.get("value_calls", 0) for o in outcomes])), 2) if outcomes else 0.0,
        "mean_latency_ms": round(float(np.mean([o.get("latency_ms", 0.0) for o in outcomes])), 2) if outcomes else 0.0,
        "failure_taxonomy_task_roots": dict(sorted(fail_counts.items())),
    }


def paired_root_bootstrap_ci(
    outcomes_a: list[dict[str, Any]],
    outcomes_b: list[dict[str, Any]],
    B_boot: int = 2000,
    seed: int = 0,
    require_same_seeds: bool = False,
) -> dict[str, Any]:
    """Paired root-cluster bootstrap 95% CI of (Arm A - Arm B) task success on `eval_task` roots."""
    def root_means(outs):
        by_r = collections.defaultdict(list)
        for o in outs:
            if o["masks"]["eval_task"]:
                ok = float(o.get("verified") == 1 and o["status"] == "REPAIR")
                by_r[o["root_id"]].append(ok)
        return {r: float(np.mean(v)) for r, v in by_r.items()}

    def coverage(outs):
        cov = collections.defaultdict(set)
        for o in outs:
            if o["masks"]["eval_task"]:
                key = (o["domain"], o["root_id"]) if "domain" in o else ("UNKNOWN", o["root_id"])
                if o.get("seed", 0) in cov[key]:
                    raise ValueError("Duplicate root/seed in paired comparison")
                cov[key].add(o.get("seed", 0))
        return dict(cov)
    ca, cb = coverage(outcomes_a), coverage(outcomes_b)
    if ca.keys() != cb.keys():
        raise ValueError("Paired comparison requires exactly identical domain/root cohorts")
    if require_same_seeds and ca != cb:
        raise ValueError("Matched comparison requires identical seed coverage per root")
    ma, mb = root_means(outcomes_a), root_means(outcomes_b)
    shared = sorted(set(ma) & set(mb))
    if not shared:
        return {"delta": None, "ci95": [None, None], "n_roots": 0}
    diffs = np.array([ma[r] - mb[r] for r in shared], dtype=np.float64)
    rng = np.random.default_rng(seed)
    boots = [float(diffs[rng.integers(0, len(diffs), len(diffs))].mean()) for _ in range(B_boot)]
    return {
        "delta": round(float(diffs.mean()), 4),
        "ci95": [round(float(np.percentile(boots, 2.5)), 4), round(float(np.percentile(boots, 97.5)), 4)],
        "n_roots": len(shared),
        "same_seed_coverage": ca == cb,
        "resampling_unit": "root; average model/trial seeds within root",
        "unresolved_policy": "verified success lower bound; unknown outcomes remain censored in raw rows",
    }


def _unresolved_result(source: str, detail: str) -> dict[str, Any]:
    return {"x": None, "y": None, "z": None, "failed_phase": "unresolved_timeout", "failure_kind": detail, "source": source}


def _verify_sequences_worker(job: dict[str, Any]) -> dict[str, Any]:
    os.environ["OMP_NUM_THREADS"] = "1"
    dom = job["domain"]
    root_id = job["root_id"]
    seqs = job["seqs"]
    lim = float(job.get("seq_timeout_s", SEQ_TIMEOUT_S[dom]))
    env = E.RepairEnv(dom)
    out = {}
    t_job = time.time()
    for s in seqs:
        seq_t = [(int(o), int(d)) for o, d in s]
        t0 = time.time()
        try:
            with time_limit(lim):
                # X = 0 already decides Z = 0, so Y is only queried when X = 1 (or X undecided).
                res = env.execute_complete_sequence(root_id, seq_t, seed=0, evaluate_y_on_x_fail=False)
            out[json.dumps(s)] = {
                "x": res["x"],
                "y": res["y"],
                "z": res["z"],
                "failed_phase": res["failed_phase"],
                "failure_kind": res["failure_kind"],
                "source": "physical_verifier",
                "wall_s": round(time.time() - t0, 2),
            }
        except QueryTimeout:
            out[json.dumps(s)] = {**_unresolved_result("physical_verifier_timeout", f"WALL_TIMEOUT_{int(lim)}s"),
                                  "wall_s": round(time.time() - t0, 2)}
            env = E.RepairEnv(dom)  # discard any partially-updated per-root planner state
    return {"root_id": root_id, "results": out, "job_wall_s": round(time.time() - t_job, 2)}


def verify_predictions_batch(
    dom: str,
    rows_by_id: dict[str, dict[str, Any]],
    predictions: list[dict[str, Any]],
    cache_path: Path,
    workers: int = 12,
    label: str = "",
) -> dict[tuple[str, str], dict[str, Any]]:
    """Verify every unique `(root_id, seq)` committed across `predictions` using:
    1. Existing decided labels in the verified snapshot (`lookup_existing_snapshot_label`),
    2. Persistent verification cache at `cache_path` (appended after EVERY finished job, so restarts resume),
    3. Parallel physical verification via `RepairEnv.execute_complete_sequence` for all remaining sequences,
       with a per-sequence wall-clock limit (worker-side) and a parent-side watchdog. Anything that exceeds
       either limit is stored as UNRESOLVED (z=None), never as infeasible.
    """
    import multiprocessing as mp
    dom_l = dom.lower()
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    verified_map: dict[tuple[str, str], dict[str, Any]] = {}
    if cache_path.exists():
        for line in open(cache_path):
            if line.strip():
                r = json.loads(line)
                for sk, v in r["results"].items():
                    verified_map[(r["root_id"], sk)] = v

    todo_by_root: dict[str, list[list[list[int]]]] = collections.defaultdict(list)
    seen_todo: set[tuple[str, str]] = set()
    n_snap = 0

    for p in predictions:
        if p["status"] == "ABSTAIN" or p["seq"] is None:
            continue
        rid = p["root_id"]
        sk = json.dumps(p["seq"])
        if (rid, sk) in verified_map:
            continue
        snap_hit = lookup_existing_snapshot_label(rows_by_id[rid], p["seq"])
        if snap_hit is not None:
            verified_map[(rid, sk)] = snap_hit
            n_snap += 1
            continue
        if (rid, sk) not in seen_todo:
            seen_todo.add((rid, sk))
            todo_by_root[rid].append(p["seq"])

    jobs = []
    for rid, seqs in sorted(todo_by_root.items()):
        for i in range(0, len(seqs), SEQS_PER_JOB):
            jobs.append({"domain": dom_l, "root_id": rid, "seqs": seqs[i:i + SEQS_PER_JOB], "seq_timeout_s": SEQ_TIMEOUT_S[dom_l]})
    n_seq = sum(len(j["seqs"]) for j in jobs)
    _log(f"verify[{label}] {dom_l}: {len(predictions)} predictions, {n_snap} snapshot hits, "
         f"{len(verified_map) - n_snap} cached, {n_seq} sequences to run in {len(jobs)} jobs on {workers} workers")

    if jobs:
        # Parent watchdog: if no job completes within this window, remaining jobs are marked UNRESOLVED.
        watchdog_s = SEQ_TIMEOUT_S[dom_l] * SEQS_PER_JOB + 300
        pending = {id(j): j for j in jobs}
        key_of = {}
        for j in jobs:
            key_of.setdefault((j["root_id"], json.dumps(j["seqs"])), id(j))
        done_seq = 0
        t_start = time.time()
        ctx = mp.get_context("spawn")
        pool = ctx.Pool(min(workers, len(jobs)), maxtasksperchild=25)
        with open(cache_path, "a") as f:
            it = pool.imap_unordered(_verify_sequences_worker, jobs, chunksize=1)
            while pending:
                try:
                    o = it.next(timeout=watchdog_s)
                except mp.TimeoutError:
                    _log(f"verify[{label}] watchdog: no completion in {watchdog_s}s; marking {len(pending)} jobs UNRESOLVED")
                    break
                except StopIteration:
                    break
                f.write(json.dumps(o) + "\n")
                f.flush()
                for sk, v in o["results"].items():
                    verified_map[(o["root_id"], sk)] = v
                k = key_of.get((o["root_id"], json.dumps([json.loads(s) for s in o["results"].keys()])))
                if k in pending:
                    pending.pop(k)
                else:  # fall back: remove the first pending job for this root with identical seq set
                    for pk, pj in list(pending.items()):
                        if pj["root_id"] == o["root_id"] and {json.dumps(s) for s in pj["seqs"]} == set(o["results"].keys()):
                            pending.pop(pk)
                            break
                done_seq += len(o["results"])
                el = time.time() - t_start
                eta = el / max(done_seq, 1) * (n_seq - done_seq)
                if (len(jobs) - len(pending)) % 5 == 0 or not pending:
                    _log(f"verify[{label}] {dom_l}: {len(jobs) - len(pending)}/{len(jobs)} jobs, {done_seq}/{n_seq} seqs, "
                         f"elapsed {el / 60:.1f} min, ETA {eta / 60:.1f} min")
            if pending:
                for pj in pending.values():
                    res = {json.dumps(s): _unresolved_result("parent_watchdog_timeout", f"WATCHDOG_{watchdog_s}s") for s in pj["seqs"]}
                    o = {"root_id": pj["root_id"], "results": res}
                    f.write(json.dumps(o) + "\n")
                    for sk, v in res.items():
                        verified_map[(pj["root_id"], sk)] = v
                pool.terminate()
            else:
                pool.close()
            pool.join()

    # Attach verification outcomes to predictions in-place
    for p in predictions:
        if p["status"] == "ABSTAIN" or p["seq"] is None:
            p["verified"] = 0
            p["x"] = None
            p["y"] = None
            p["failed_phase"] = "abstain"
            continue
        v = verified_map.get((p["root_id"], json.dumps(p["seq"])))
        if v is not None:
            p["verified"] = v["z"]
            p["x"] = v["x"]
            p["y"] = v["y"]
            p["failed_phase"] = v["failed_phase"]
            p["failure_kind"] = v.get("failure_kind")
            p["verification_source"] = v.get("source")
        else:
            p["verified"] = None
    return verified_map


def _closed_loop_worker(job: dict[str, Any]) -> dict[str, Any]:
    os.environ["OMP_NUM_THREADS"] = "1"
    dom = job["domain"]
    row = job["row"]
    scalers = job["scalers"]
    arms_cfg = job["arms_cfg"]
    rule = job["rule"]
    B_test = job["B_test"]
    seed = job["seed"]

    env = E.RepairEnv(dom)
    loaded_pol = {}
    loaded_val = {}
    out = {}
    for arm_name, ccfg in arms_cfg.items():
        pol_ckpt = ccfg.get("pol")
        val_ckpt = ccfg.get("val")
        prop_mode = ccfg["mode"]
        use_value = ccfg["use_v"]
        max_ret = int(ccfg.get("max_retries", 0))

        pol_model = None
        if pol_ckpt is not None and prop_mode != "uniform":
            if pol_ckpt not in loaded_pol:
                loaded_pol[pol_ckpt], _ = P.load_policy_checkpoint(pol_ckpt, device="cpu")
            pol_model = loaded_pol[pol_ckpt]
        val_model = None
        if val_ckpt is not None and use_value:
            if val_ckpt not in loaded_val:
                loaded_val[val_ckpt], _ = DS.load_value_checkpoint(val_ckpt, device="cpu")
            val_model = loaded_val[val_ckpt]

        wrap = P.PolicyProposalWrapper(dom, pol_model, scalers, device="cpu", mode=prop_mode, value_model=val_model)
        lim = EPISODE_TIMEOUT_S[dom]
        t0 = time.time()
        try:
            with time_limit(lim):
                out[arm_name] = run_closed_loop_episode(
                    env, row, wrap, B_test=B_test, use_value=use_value, rule=rule, seed=seed, max_action_retries=max_ret
                )
        except QueryTimeout:
            out[arm_name] = {
                "root_id": row["root_id"], "domain": dom, "split": row["split"], "K_legacy": row["K_legacy"],
                "masks": row["masks"], "protocol": "closed_loop", "max_action_retries": max_ret, "action_retries_used": None,
                "seed": seed, "status": "UNRESOLVED", "seq": None, "m": None, "displacement": None,
                "verified": None, "x": None, "y": None, "failed_phase": "unresolved_timeout",
                "failure_kind": f"WALL_TIMEOUT_{lim}s", "policy_calls": None, "value_calls": None,
                "execution_planner_calls": None, "wall_s": round(time.time() - t0, 3),
            }
            env = E.RepairEnv(dom)
    return out


def select_eval_cohort(dom: str, split: str = "test", counts_by_k: dict[str, int] | None = None) -> list[dict[str, Any]]:
    """Select deterministic stratified evaluation cohort from `split` (`valsub` or `test`).
    For `2d`, uses up to 75 roots (`15` per class across `K0, K1, K2, K3, NONE`) or full split if smaller;
    for `3d`, uses up to 30 roots (`6` per class across `K0, K1, K2, K3, NONE`) so all open-loop and
    closed-loop arms can be 100% physically verified with zero unverified predictions.
    """
    dom_l = dom.lower()
    if counts_by_k is None:
        counts_by_k = (
            {"0": 15, "1": 15, "2": 15, "3": 15, "NONE": 15}
            if dom_l == "2d"
            else {"0": 6, "1": 6, "2": 6, "3": 6, "NONE": 6}
        )
    rows = D.load_snapshot_rows(dom_l, split, D.BASE_SNAP)
    out = []
    for k_cls, cnt in counts_by_k.items():
        sub = [r for r in rows if r["K_legacy"] == k_cls]
        sub.sort(key=lambda r: hashlib.sha256(f"eval_cohort|{dom_l}|{split}|{r['root_id']}".encode()).hexdigest())
        out.extend(sub[:cnt])
    return out


def tune_stopping_rule_on_val(
    dom: str,
    val_rows: list[dict[str, Any]],
    scalers: dict[str, Any],
    pol_ckpt: Path | str,
    val_ckpt: Path | str,
    B_test: int = 16,
    device: str = "cuda",
    cache_path: Path | None = None,
    workers: int = 12,
) -> dict[str, Any]:
    """Tune `noop_q_gate`, `stop_q_margin`, `abstain_eta` on VALIDATION (`val_rows`) ONLY (`DISCO_plan.md` Section 11.1)."""
    if any(r["split"]!="val" for r in val_rows):raise ValueError("Stopping-rule selection requires benchmark VAL only")
    dom_l = dom.lower()
    pol_model, _ = P.load_policy_checkpoint(pol_ckpt, device=device)
    val_model, _ = DS.load_value_checkpoint(val_ckpt, device=device)
    wrap = P.PolicyProposalWrapper(dom_l, pol_model, scalers, device=device, mode="distilled", value_model=val_model)

    grid = [
        {"noop_q_gate": ng, "stop_q_margin": sm, "abstain_eta": ae, "stop_q_min": 0.35, "policy_stop_thresh": 0.45, "noop_pol_gate": 0.50}
        for ng in (0.45, 0.55, 0.65)
        for sm in (0.0, 0.03)
        for ae in (0.0, 0.08, 0.15)
    ]

    rows_by_id = {r["root_id"]: r for r in val_rows}
    all_preds = []
    preds_by_rule = []
    for rule in grid:
        r_preds = [predict_open_loop_sequence(r, dom_l, wrap, B_test=B_test, use_value=True, rule=rule, seed=0) for r in val_rows]
        preds_by_rule.append((rule, r_preds))
        all_preds.extend(r_preds)

    c_path = cache_path or (D.DISCO_ROOT / "caches" / f"verify_{dom_l}_val.jsonl")
    verify_predictions_batch(dom_l, rows_by_id, all_preds, c_path, workers=workers, label="val")

    scored = []
    for rule, r_preds in preds_by_rule:
        m = compute_benchmark_metrics(r_preds)
        parts = [v for v in (m["task_success"], m["noop_accuracy_K0"], m["none_explicit_abstain_rate"]) if v is not None]
        obj = float(np.mean(parts)) if parts else 0.0
        scored.append((obj, m["task_success"] or 0.0, rule, m))
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    best = scored[0]
    return {"best_rule": best[2], "best_val_objective": round(best[0], 4), "best_val_metrics": best[3]}


def run_d6_d7_d8_evaluation(
    seeds: tuple[int, ...] = (0, 1, 2),
    device: str = "cuda",
    domains: tuple[str, ...] = ("2d", "3d"),
) -> dict[str, Any]:
    """Run complete D6 (Open-Loop evaluation across all arms and ablations),
    D7 (Closed-Loop evaluation), and D8 (Final comparison & statistical bootstrap report).
    The summary JSON is rewritten after EACH domain, so a finished domain is never lost.
    """
    import multiprocessing as mp
    out_path = HERE / "reports/d6_d7_d8_evaluation_summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    final_rep: dict[str, Any] = json.loads(out_path.read_text()) if out_path.exists() else {"domains": {}}
    final_rep.update({
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "baseline_designation": "DISCO-Grid (adapted)",
        "verification_limits": {
            "seq_timeout_s": SEQ_TIMEOUT_S, "episode_timeout_s": EPISODE_TIMEOUT_S, "seqs_per_job": SEQS_PER_JOB,
            "unresolved_policy": "timed-out queries are stored as UNRESOLVED (verified=None) and reported separately",
            "y_on_x_fail": "Y is not queried once X=0 is physically decided (Z=0 regardless)",
        },
    })
    final_rep.setdefault("domains", {})

    for dom in domains:
        _log(f"===== domain {dom}: start =====")
        q2 = D.load_q2_dataset(dom)
        scalers = q2["scalers"]
        workers = 12 if dom == "2d" else 10
        B_test = 16 if dom == "2d" else 12

        val_cohort = select_eval_cohort(
            dom,
            split="valsub",
            counts_by_k={"0": 8, "1": 8, "2": 8, "3": 8, "NONE": 8} if dom == "2d" else {"0": 4, "1": 4, "2": 4, "3": 4, "NONE": 4},
        )
        test_cohort = select_eval_cohort(
            dom,
            split="test",
            counts_by_k={"0": 15, "1": 15, "2": 15, "3": 15, "NONE": 15} if dom == "2d" else {"0": 6, "1": 6, "2": 6, "3": 6, "NONE": 6},
        )
        test_rows_by_id = {r["root_id"]: r for r in test_cohort}

        p2_s0 = D.DISCO_ROOT / "runs/distill" / dom / "r2_s0/policy.pt"
        q2_s0 = D.DISCO_ROOT / "runs/distill" / dom / "r2_s0/value.pt"

        # 1. Tune stopping/admission rule on VALIDATION cohort only
        tune_res = tune_stopping_rule_on_val(
            dom, val_cohort, scalers, p2_s0, q2_s0, B_test=B_test, device=device, workers=workers
        )
        frozen_rule = tune_res["best_rule"]
        _log(f"validation rule frozen for {dom}: {frozen_rule} (val objective {tune_res['best_val_objective']})")

        # 2. D6 Open-Loop Arms on Held-Out TEST Cohort
        open_arms_cfg = {
            "uniform_no_q": {"pol": None, "val": None, "mode": "uniform", "use_v": False, "seeds": (0,)},
            "p0_only": {"pol": "runs/p0/{dom}/s{s}/model.pt", "val": None, "mode": "p0", "use_v": False, "seeds": seeds},
            "p1_only": {"pol": "runs/distill/{dom}/r1_s{s}/policy.pt", "val": None, "mode": "distilled", "use_v": False, "seeds": seeds},
            "p1_q1": {"pol": "runs/distill/{dom}/r1_s{s}/policy.pt", "val": "runs/distill/{dom}/r1_s{s}/value.pt", "mode": "distilled", "use_v": True, "seeds": seeds},
            "p2_only": {"pol": "runs/distill/{dom}/r2_s{s}/policy.pt", "val": None, "mode": "distilled", "use_v": False, "seeds": seeds},
            "p2_q2_primary": {"pol": "runs/distill/{dom}/r2_s{s}/policy.pt", "val": "runs/distill/{dom}/r2_s{s}/value.pt", "mode": "distilled", "use_v": True, "seeds": seeds},
            "p1_succ_only_q1": {"pol": "runs/distill/{dom}/r1_succ_only_s0/policy.pt", "val": "runs/distill/{dom}/r1_succ_only_s0/value.pt", "mode": "distilled", "use_v": True, "seeds": (0,)},
        }

        open_preds_by_arm: dict[str, list[dict[str, Any]]] = {}
        all_open_preds: list[dict[str, Any]] = []

        for arm_name, cfg in open_arms_arm_iter(open_arms_cfg, dom):
            arm_preds = []
            for s in cfg["seeds"]:
                p_ck = (D.DISCO_ROOT / cfg["pol"].format(dom=dom, s=s)) if cfg["pol"] else None
                v_ck = (D.DISCO_ROOT / cfg["val"].format(dom=dom, s=s)) if cfg["val"] else None
                p_mod = P.load_policy_checkpoint(p_ck, device=device)[0] if p_ck else None
                v_mod = DS.load_value_checkpoint(v_ck, device=device)[0] if v_ck else None
                wrap = P.PolicyProposalWrapper(dom, p_mod, scalers, device=device, mode=cfg["mode"], value_model=v_mod)
                for r in test_cohort:
                    pr = predict_open_loop_sequence(r, dom, wrap, B_test=B_test, use_value=cfg["use_v"], rule=frozen_rule, seed=s)
                    pr["arm"] = arm_name
                    arm_preds.append(pr)
            open_preds_by_arm[arm_name] = arm_preds
            all_open_preds.extend(arm_preds)

        test_cache = D.DISCO_ROOT / "caches" / f"verify_{dom}_test.jsonl"
        _log(f"D6 open-loop {dom}: {len(all_open_preds)} committed predictions generated with zero physical calls")
        verify_predictions_batch(dom, test_rows_by_id, all_open_preds, test_cache, workers=workers, label="test")

        open_metrics = {arm: compute_benchmark_metrics(preds) for arm, preds in open_preds_by_arm.items()}
        open_boot_vs_primary = {
            arm: paired_root_bootstrap_ci(preds, open_preds_by_arm["p2_q2_primary"])
            for arm, preds in open_preds_by_arm.items()
            if arm != "p2_q2_primary"
        }

        # 3. D7 Closed-Loop Evaluation on Held-Out TEST Subset (seed 0)
        cl_cohort = select_eval_cohort(
            dom,
            split="test",
            counts_by_k={"0": 6, "1": 6, "2": 6, "3": 6, "NONE": 6} if dom == "2d" else {"0": 3, "1": 4, "2": 4, "3": 3, "NONE": 2},
        )
        cl_root_ids = {r["root_id"] for r in cl_cohort}
        cl_arms_cfg = {
            "closed_loop_p0_only": {"pol": str(D.DISCO_ROOT / f"runs/p0/{dom}/s0/model.pt"), "val": None, "mode": "p0", "use_v": False, "max_retries": 0},
            "closed_loop_p2_only": {"pol": str(p2_s0), "val": None, "mode": "distilled", "use_v": False, "max_retries": 0},
            "closed_loop_p2_q2": {"pol": str(p2_s0), "val": str(q2_s0), "mode": "distilled", "use_v": True, "max_retries": 0},
            "closed_loop_p2_q2_retry1": {"pol": str(p2_s0), "val": str(q2_s0), "mode": "distilled", "use_v": True, "max_retries": 1},
        }
        jobs = [
            {
                "domain": dom,
                "row": r,
                "scalers": scalers,
                "arms_cfg": cl_arms_cfg,
                "rule": frozen_rule,
                "B_test": B_test,
                "seed": 0,
            }
            for r in cl_cohort
        ]
        _log(f"D7 closed-loop {dom}: {len(jobs)} roots x {len(cl_arms_cfg)} arms on {min(workers, len(jobs))} workers")
        per_root_cl = []
        cl_watchdog = EPISODE_TIMEOUT_S[dom] * len(cl_arms_cfg) + 300
        pool = mp.get_context("spawn").Pool(min(workers, len(jobs)), maxtasksperchild=10)
        it = pool.imap_unordered(_closed_loop_worker, jobs, chunksize=1)
        t_cl = time.time()
        done_ids = set()
        while len(per_root_cl) < len(jobs):
            try:
                pr = it.next(timeout=cl_watchdog)
            except mp.TimeoutError:
                _log(f"D7 closed-loop {dom}: watchdog fired; {len(jobs) - len(per_root_cl)} roots UNRESOLVED")
                break
            per_root_cl.append(pr)
            done_ids.add(next(iter(pr.values()))["root_id"])
            _log(f"D7 closed-loop {dom}: {len(per_root_cl)}/{len(jobs)} roots, elapsed {(time.time() - t_cl) / 60:.1f} min")
        if len(per_root_cl) < len(jobs):
            pool.terminate()
            for r in cl_cohort:
                if r["root_id"] not in done_ids:
                    per_root_cl.append({
                        cl_name: {"root_id": r["root_id"], "domain": dom, "split": r["split"], "K_legacy": r["K_legacy"],
                                  "masks": r["masks"], "protocol": "closed_loop", "seed": 0, "status": "UNRESOLVED",
                                  "seq": None, "m": None, "displacement": None, "verified": None, "x": None, "y": None,
                                  "failed_phase": "unresolved_timeout", "failure_kind": "PARENT_WATCHDOG"}
                        for cl_name in cl_arms_cfg
                    })
        else:
            pool.close()
        pool.join()

        closed_metrics = {}
        closed_outs_by_arm = {cl_name: [pr[cl_name] for pr in per_root_cl] for cl_name in cl_arms_cfg}
        for cl_name, cl_outs in closed_outs_by_arm.items():
            cm = compute_benchmark_metrics(cl_outs)
            cm["mean_execution_planner_calls"] = round(float(np.mean([o.get("execution_planner_calls", 0) for o in cl_outs])), 2)
            cm["mean_action_retries_used"] = round(float(np.mean([o.get("action_retries_used", 0) for o in cl_outs])), 3)
            closed_metrics[cl_name] = cm

        # Matched open-loop metrics on the exact same `cl_cohort` roots (seed 0) for direct open-vs-closed comparison
        matched_open_on_cl = {}
        for ol_name in ("p0_only", "p2_only", "p2_q2_primary"):
            sub_preds = [p for p in open_preds_by_arm[ol_name] if p["root_id"] in cl_root_ids and p["seed"] == 0]
            matched_open_on_cl[ol_name] = compute_benchmark_metrics(sub_preds)

        final_rep["domains"][dom] = {
            "val_rule_tuning": tune_res,
            "n_test_roots": len(test_cohort),
            "open_loop_test_metrics": open_metrics,
            "open_loop_paired_bootstrap_vs_p2_q2": open_boot_vs_primary,
            "n_closed_loop_test_roots": len(cl_cohort),
            "closed_loop_test_metrics": closed_metrics,
            "matched_open_loop_on_closed_loop_cohort": matched_open_on_cl,
            "closed_vs_open_p2_q2_bootstrap": paired_root_bootstrap_ci(
                closed_outs_by_arm["closed_loop_p2_q2"],
                [p for p in open_preds_by_arm["p2_q2_primary"] if p["root_id"] in cl_root_ids and p["seed"] == 0],
            ),
            "sample_predictions": [
                {k: v for k, v in p.items() if k != "masks"}
                for p in open_preds_by_arm["p2_q2_primary"][:15]
            ],
            "closed_loop_per_root": {
                cl_name: [{k: v for k, v in o.items() if k != "masks"} for o in outs]
                for cl_name, outs in closed_outs_by_arm.items()
            },
            "open_loop_primary_per_prediction": [
                {k: v for k, v in p.items() if k not in ("masks", "step_traces")}
                for p in open_preds_by_arm["p2_q2_primary"]
            ],
        }
        out_path.write_text(json.dumps(final_rep, indent=2))
        _log(f"===== domain {dom}: done, summary written to {out_path} =====")

    return final_rep


def open_arms_arm_iter(cfg_dict: dict[str, dict[str, Any]], dom: str):
    for k, v in cfg_dict.items():
        yield k, v


if __name__ == "__main__":
    if sys.argv[1:2] == ["run_eval"]:
        doms = tuple(sys.argv[2:]) or ("2d", "3d")
        r = run_d6_d7_d8_evaluation(domains=doms)
        print(json.dumps({"eval_done": list(r["domains"].keys())}), flush=True)


def fit_root_stop_calibration(examples: list[dict[str, Any]]) -> dict[str, Any]:
    """Named root-only scalar calibration, split by VAL family; no TEST selection.

    Fits a regularized affine logit on one VAL half; reports the other half.
    This is a task adaptation, not a new DISCO value-supervision definition.
    """
    import torch
    if any(r["split"] != "val" for r in examples):
        raise ValueError("STOP calibration accepts benchmark VALIDATION only")
    if any(r["z_stop"] not in (0, 1) for r in examples):
        raise ValueError("STOP calibration requires decided physical labels")
    keys = [(r["root_id"],r.get("seed",0)) for r in examples]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate calibration root/seed")
    fit, audit = [], []
    for row in examples:
        family = str(row.get("family_id") or row["root_id"])
        (fit if int(hashlib.sha256(family.encode()).hexdigest()[:8],16)%2 == 0 else audit).append(row)
    if not fit or not audit or len({r["z_stop"] for r in fit}) < 2:
        raise ValueError("Insufficient independent decided VAL families for calibration")
    def arrays(rows):
        q = torch.tensor([min(1.-1e-6,max(1e-6,r["q_stop"])) for r in rows], dtype=torch.float64)
        return torch.logit(q),torch.tensor([r["z_stop"] for r in rows],dtype=torch.float64)
    x,y = arrays(fit)
    params = torch.tensor([0.,0.],dtype=torch.float64,requires_grad=True)
    opt = torch.optim.LBFGS([params],max_iter=80,line_search_fn="strong_wolfe")
    def closure():
        opt.zero_grad()
        scale = params[0].clamp(-4.,4.).exp()
        loss = torch.nn.functional.binary_cross_entropy_with_logits(scale*x+params[1],y) + .01*params.square().sum()
        loss.backward()
        return loss
    opt.step(closure)
    scale = float(params[0].detach().clamp(-4.,4.).exp())
    bias = float(params[1].detach())
    hx,hy=arrays(audit)
    def metrics(logits):
        return {"nll":float(torch.nn.functional.binary_cross_entropy_with_logits(logits,hy)),
                "brier":float((torch.sigmoid(logits)-hy).square().mean())}
    return {"adaptation":"VAL-only affine-logit root-STOP calibration; intermediate STOP unchanged",
            "rule":{"root_stop_temperature":1./scale,"root_stop_bias":bias},
            "n_fit_roots":len({r["root_id"] for r in fit}), "n_audit_roots":len({r["root_id"] for r in audit}),
            "fit_family_ids":sorted({r.get("family_id",r["root_id"]) for r in fit}),
            "audit_family_ids":sorted({r.get("family_id",r["root_id"]) for r in audit}),
            "audit_raw":metrics(hx),"audit_calibrated":metrics(scale*hx+bias),
            "task_success_claim":"NOT_EVALUATED; no TEST selection or performance inferred"}


def root_level_metrics(outcomes, root_manifest, seeds=(0,1,2), bootstrap=10000, seed=20261117):
    """Frozen-root intention-to-evaluate metrics; missing seeds stay in denominator.

    One domain/protocol/arm at a time. Resample source families as clusters and
    retain all fixed model seeds per root. No observed rows means NOT_RUN, not 0%.
    """
    roots={r['root_id']:r for r in root_manifest}
    if len(roots)!=len(root_manifest) or not seeds or len(set(seeds))!=len(seeds):raise ValueError('Duplicate/empty roots or seeds')
    lookup={}
    for row in outcomes:
        key=(row['root_id'],row['seed'])
        if key in lookup or key[0] not in roots or key[1] not in seeds:raise ValueError('Unexpected or duplicate root/seed')
        lookup[key]=row
    if len({r.get('domain') for r in outcomes})>1:raise ValueError('Report domains separately')
    def metrics(ids):
        if not ids:return {'status':'NOT_RUN','n_roots':0,'success_rate':None,'ci95':None}
        means=[];upper=[];decided=[];families=[];trials=succ=unknown=abstain=notrun=0;perseed={s:0 for s in seeds}
        for rid in ids:
            vals=[];ups=[]
            for s in seeds:
                row=lookup.get((rid,s));trials+=1
                if row is None:unknown+=1;notrun+=1;vals.append(0);ups.append(1);continue
                ok=int(row.get('verified')==1);succ+=ok;perseed[s]+=ok
                is_abstain=row.get('status')=='ABSTAIN';abstain+=is_abstain
                unres=row.get('verified') is None and not is_abstain
                unknown+=unres;vals.append(ok);ups.append(int(ok or unres))
                if row.get('verified') in (0,1) and not is_abstain:decided.append(ok)
            means.append(np.mean(vals));upper.append(np.mean(ups));families.append(roots[rid].get('family_id',rid))
        distinct=sorted(set(families));rng=np.random.default_rng(seed)
        values=np.asarray(means);groups=[np.flatnonzero(np.array(families)==f) for f in distinct]
        boots=[]
        for _ in range(bootstrap):
            ix=np.concatenate([groups[i] for i in rng.integers(len(groups),size=len(groups))]);boots.append(float(values[ix].mean()))
        observed=trials-notrun
        return dict(status='NOT_RUN' if not observed else 'PARTIAL' if unknown else 'MEASURED',n_roots=len(ids),n_families=len(groups),
            n_expected_predictions=trials,n_observed_predictions=observed,n_verified_success=succ,n_physically_decided=len(decided),
            n_unresolved_or_unexecuted=unknown,n_not_run=notrun,n_abstentions=abstain,
            success_rate=float(values.mean()) if observed else None,ci95=list(np.percentile(boots,[2.5,97.5])) if observed else None,
            pessimistic=float(values.mean()) if observed else None,optimistic=float(np.mean(upper)) if observed else None,
            decided_only=float(np.mean(decided)) if decided else None,per_seed_success=perseed,
            resampling_unit='source-family cluster, fixed model seeds within root',bootstrap_replicates=bootstrap,bootstrap_seed=seed)
    return {'overall':metrics(list(roots)), 'tasks_K1_K2_K3':metrics([r for r,x in roots.items() if str(x['K_legacy']) in ('1','2','3')]),
            'by_K':{k:metrics([r for r,x in roots.items() if str(x['K_legacy'])==k]) for k in ('0','1','2','3','NONE')}}


def paired_frozen_root_metrics(a,b,root_manifest,seeds=(0,1,2),bootstrap=10000,seed=20261117):
    """Within-DISCO paired root-family bootstrap with fixed missing-trial denominators."""
    # Reuse input validation, including duplicates and unexpected roots/seeds.
    root_level_metrics(a,root_manifest,seeds,bootstrap=1,seed=seed)
    root_level_metrics(b,root_manifest,seeds,bootstrap=1,seed=seed)
    if not root_manifest:raise ValueError('Empty paired cohort')
    aa={(r['root_id'],r['seed']):r for r in a};bb={(r['root_id'],r['seed']):r for r in b}
    values=[];lower=[];upper=[];families=[];unknown=0
    def bounds(row):
        if row is None:return 0,1
        ok=int(row.get('verified')==1)
        unresolved=row.get('verified') is None and row.get('status')!='ABSTAIN'
        return ok,int(ok or unresolved)
    for root in root_manifest:
        av=[];bv=[];al=[];bl=[]
        for s in seeds:
            x,xu=bounds(aa.get((root['root_id'],s)));y,yu=bounds(bb.get((root['root_id'],s)))
            av.append(x);bv.append(y);al.append(x-yu);bl.append(xu-y);unknown+=int(x!=xu or y!=yu)
        values.append(np.mean(av)-np.mean(bv));lower.append(np.mean(al));upper.append(np.mean(bl));families.append(root.get('family_id',root['root_id']))
    distinct=sorted(set(families));groups=[np.flatnonzero(np.asarray(families)==f) for f in distinct]
    rng=np.random.default_rng(seed);values=np.asarray(values);boots=[]
    for _ in range(bootstrap):
        ix=np.concatenate([groups[i] for i in rng.integers(len(groups),size=len(groups))]);boots.append(float(values[ix].mean()))
    return dict(n_roots=len(root_manifest),n_families=len(groups),fixed_seeds=list(seeds),delta=float(values.mean()),
        ci95=list(np.percentile(boots,[2.5,97.5])),unknown_pair_trials=unknown,
        unresolved_sensitivity=[float(np.mean(lower)),float(np.mean(upper))],bootstrap_replicates=bootstrap,bootstrap_seed=seed,
        interpretation='Paired verified-success indicator difference; unknowns retained, not certified physical negatives')
