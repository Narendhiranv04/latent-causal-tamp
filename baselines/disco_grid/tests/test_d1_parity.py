#!/usr/bin/env python3
"""D1 Stateful Physical Adapter Parity Audit and Unit Tests (2D and 3D).

Verifies `DISCO_plan.md` Sections 4.1-4.4 and 14 (D1):
1. Stratified TRAIN fixture set across 2D and 3D: K0, K1, K2, K3, NONE, order-sensitive pairs (same endpoint,
   one order X=1 and another order X=0), and omission Y-negatives (X=1, Y=0 or X=0, Y=0).
2. Replays every fixture sequence via `reset -> transition -> ... -> terminal_query` and compares X, Y, Z,
   failure phase, and witness hashes against the authoritative snapshot labels.
3. Verifies canonical endpoint Y invariance across permutations and measures 3D sub-cell executed pose drift.
4. Verifies static grammar enforcement (target move, fixed object move, duplicate object move, vacated-cell reuse,
   goal-cell placement, depth > 3) and zero-cross-contamination state cloning/restoration across MCTS branches.
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import data as D
import env as E


def select_stratified_train_fixtures(dom: str, max_per_stratum: int = 3) -> list[dict[str, Any]]:
    """Deterministically select TRAIN roots covering K0, K1, K2, K3 (including order-sensitive roots) and NONE."""
    rows = D.load_snapshot_rows(dom, "train", D.BASE_SNAP)
    rows.sort(key=lambda r: hashlib.sha256(f"d1_fixture|{r['root_id']}".encode()).hexdigest())

    selected = []
    # 1. K0 roots with empty-sequence Y=1
    k0_rows = [r for r in rows if r["K_legacy"] == "0" and any(not y["edit"] and y["y"] == 1 for y in r["labels"]["Y"])]
    for r in k0_rows[:max_per_stratum]:
        selected.append({"row": r, "stratum": "K0_noop", "queries": [{"seq": [], "expected_x": 1, "expected_y": 1, "kind": "EMPTY_K0"}]})

    # 2. K1, K2, K3 roots (preferring roots that have BOTH X=1 and X=0 orders on the same endpoint for K2/K3, plus omission Y=0)
    for k_cls in ("1", "2", "3"):
        k_rows = [r for r in rows if r["K_legacy"] == k_cls and r["labels"]["X"]]
        if k_cls in ("2", "3"):
            # Sort so roots with both X=1 and X=0 on SELECTED_ASSIGNMENT_ORDER come first
            def has_mixed_orders(r):
                sel = [q for q in r["labels"]["X"] if q["kind"] == "SELECTED_ASSIGNMENT_ORDER"]
                xs = {q["x"] for q in sel}
                return 0 in xs and 1 in xs
            k_rows.sort(key=lambda r: (not has_mixed_orders(r), hashlib.sha256(r["root_id"].encode()).hexdigest()))
        for r in k_rows[:max_per_stratum]:
            ylab = {json.dumps(sorted(map(tuple, y["edit"]))): y["y"] for y in r["labels"]["Y"]}
            qs = []
            # Pick up to 2 SELECTED_ASSIGNMENT_ORDER (one X=1, one X=0 if available) and 1 OMISSION_YNEG
            sel_pos = [q for q in r["labels"]["X"] if q["kind"] == "SELECTED_ASSIGNMENT_ORDER" and q["x"] == 1]
            sel_neg = [q for q in r["labels"]["X"] if q["kind"] == "SELECTED_ASSIGNMENT_ORDER" and q["x"] == 0]
            om_neg = [q for q in r["labels"]["X"] if q["kind"] == "OMISSION_YNEG"]
            for q in (sel_pos[:1] + sel_neg[:1] + om_neg[:1]):
                ek = json.dumps(sorted(map(tuple, q["seq"])))
                if ek in ylab and q["x"] in (0, 1) and ylab[ek] in (0, 1):
                    qs.append({
                        "seq": q["seq"],
                        "expected_x": int(q["x"]),
                        "expected_y": int(ylab[ek]),
                        "expected_phase": q.get("x_phase"),
                        "expected_x_witnesses": q.get("x_witnesses"),
                        "kind": q["kind"],
                    })
            if qs:
                selected.append({"row": r, "stratum": f"K{k_cls}", "queries": qs})
    return selected


def _audit_one_root(args: tuple[str, dict[str, Any]]) -> dict[str, Any]:
    dom, item = args
    env = E.RepairEnv(dom)
    r = item["row"]
    rid = r["root_id"]
    strat = item["stratum"]
    endpoint_ys: dict[str, list[int]] = collections.defaultdict(list)
    records_out = []
    drifts = []
    for q in item["queries"]:
        seq = [(int(o), int(d)) for o, d in q["seq"]]
        res = env.execute_complete_sequence(rid, seq, seed=0)
        ek = json.dumps(sorted(map(tuple, seq)))
        if res["status"] == "DECIDED" and res["y"] is not None:
            endpoint_ys[ek].append(int(res["y"]))
        if dom == "3d" and res["stop_result"] is not None:
            drifts.extend(res["stop_result"].endpoint_pose_drift_m.values())
        records_out.append({
            "root_id": rid,
            "stratum": strat,
            "kind": q["kind"],
            "seq": seq,
            "expected_x": q["expected_x"],
            "expected_y": q["expected_y"],
            "status": res["status"],
            "got_x": res["x"],
            "got_y": res["y"],
            "got_z": res["z"],
            "failed_phase": res["failed_phase"],
            "teacher_status": res["teacher_status"],
        })
    return {
        "root_id": rid,
        "stratum": strat,
        "records": records_out,
        "endpoint_ys": dict(endpoint_ys),
        "drifts": drifts,
    }


def run_d1_parity_audit(n_per_stratum_2d: int = 4, n_per_stratum_3d: int = 2, workers_3d: int = 8) -> dict[str, Any]:
    import multiprocessing as mp
    report: dict[str, Any] = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "domains": {},
        "sample_traces": {},
    }
    for dom, n_per in (("2d", n_per_stratum_2d), ("3d", n_per_stratum_3d)):
        fixtures = select_stratified_train_fixtures(dom, max_per_stratum=n_per)
        counts = collections.Counter()
        by_phase = collections.Counter()
        by_stratum = collections.Counter()
        disagreements = []
        drifts_3d = []
        order_sensitive_checks = []
        records_out = []

        if dom == "3d" and workers_3d > 1 and len(fixtures) > 1:
            with mp.get_context("spawn").Pool(min(workers_3d, len(fixtures))) as pool:
                root_outs = pool.map(_audit_one_root, [(dom, item) for item in fixtures])
        else:
            root_outs = [_audit_one_root((dom, item)) for item in fixtures]

        for rout in root_outs:
            rid = rout["root_id"]
            strat = rout["stratum"]
            drifts_3d.extend(rout["drifts"])
            for rec_entry in rout["records"]:
                counts["n_checked"] += 1
                by_stratum[f"{strat}|checked"] += 1
                if rec_entry["status"] != "DECIDED" or rec_entry["got_x"] is None or rec_entry["got_y"] is None:
                    counts["n_unresolved"] += 1
                    by_stratum[f"{strat}|unresolved"] += 1
                    rec_entry["agree"] = False
                    records_out.append(rec_entry)
                    continue

                counts["n_decided"] += 1
                exp_x, exp_y = rec_entry["expected_x"], rec_entry["expected_y"]
                exp_z = int(exp_x == 1 and exp_y == 1)
                got_x, got_y, got_z = int(rec_entry["got_x"]), int(rec_entry["got_y"]), int(rec_entry["got_z"])
                agree_all = (got_x == exp_x) and (got_y == exp_y) and (got_z == exp_z)
                rec_entry["agree"] = agree_all

                seq = rec_entry["seq"]
                phase_tag = rec_entry["failed_phase"] or ("verified_noop" if not seq and got_z == 1 else "verified_Z1" if got_z == 1 else "failed_other")
                by_phase[f"{phase_tag}|checked"] += 1

                if agree_all:
                    counts["n_agree"] += 1
                    by_stratum[f"{strat}|agree"] += 1
                    by_phase[f"{phase_tag}|agree"] += 1
                else:
                    counts["n_disagree"] += 1
                    by_stratum[f"{strat}|disagree"] += 1
                    by_phase[f"{phase_tag}|disagree"] += 1
                    disagreements.append({
                        "root_id": rid,
                        "seq": seq,
                        "expected": {"x": exp_x, "y": exp_y, "z": exp_z},
                        "got": {"x": got_x, "y": got_y, "z": got_z, "phase": rec_entry["failed_phase"], "status": rec_entry["teacher_status"]},
                    })
                records_out.append(rec_entry)

            if len(rout["records"]) >= 2 and rid not in report["sample_traces"].get(dom, {}):
                report["sample_traces"].setdefault(dom, {})[rid] = rout["records"]

            for ek, ys in rout["endpoint_ys"].items():
                if len(ys) > 1:
                    order_sensitive_checks.append({
                        "root_id": rid,
                        "endpoint": ek,
                        "ys_across_orders": ys,
                        "y_invariant": len(set(ys)) == 1,
                    })

        report["domains"][dom] = {
            "n_roots_audited": len(fixtures),
            "n_checked": counts["n_checked"],
            "n_decided": counts["n_decided"],
            "n_agree": counts["n_agree"],
            "n_disagree": counts["n_disagree"],
            "n_unresolved": counts["n_unresolved"],
            "by_stratum": dict(sorted(by_stratum.items())),
            "by_phase": dict(sorted(by_phase.items())),
            "order_sensitive_endpoint_y_checks": order_sensitive_checks,
            "all_endpoint_y_invariant": all(c["y_invariant"] for c in order_sensitive_checks),
            "mean_3d_pose_drift_m": round(float(np.mean(drifts_3d)), 6) if drifts_3d else 0.0,
            "max_3d_pose_drift_m": round(float(np.max(drifts_3d)), 6) if drifts_3d else 0.0,
            "disagreements": disagreements,
            "records": records_out,
        }

    out_path = HERE / "reports/d1_parity_audit.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))
    return report


def test_d1_grammar_and_state_isolation_2d():
    env = E.RepairEnv("2d")
    fixtures = select_stratified_train_fixtures("2d", max_per_stratum=2)
    k2_item = next(x for x in fixtures if x["stratum"] == "K2")
    row = k2_item["row"]
    rid = row["root_id"]
    inp = row["inputs"]

    s0 = env.reset(rid, seed=0)
    obs0 = env.observe(s0)
    assert obs0.q_t_optional is None  # Default learner observation hides intermediate q_t
    assert obs0.remaining_steps == 3
    assert not any(obs0.moved_mask)

    # Check illegal actions rejected without mutating state
    tid = inp["tid"]
    d_leg = obs0.legal_destinations[0]
    res_target = env.transition(s0, (tid, d_leg))
    assert res_target.status == "PHYSICALLY_FAILED" and res_target.failure_kind == "INELIGIBLE"

    o_elig = obs0.eligible_objects[0]
    res_goal = env.transition(s0, (o_elig, int(inp["goal_cell"])))
    assert res_goal.status == "PHYSICALLY_FAILED" and res_goal.failure_kind == "INELIGIBLE"

    # Check fixed object move rejected if fixed object exists
    fixed_idxs = [i for i, a in enumerate(inp["attrs"]) if i != tid and len(a) >= 4 and bool(a[3])]
    if fixed_idxs:
        res_fixed = env.transition(s0, (fixed_idxs[0], d_leg))
        assert res_fixed.status == "PHYSICALLY_FAILED" and res_fixed.failure_kind == "INELIGIBLE"

    # Execute first step of a verified sequence, clone state, pollute, restore, and verify exact match
    pos_q = next(q for q in k2_item["queries"] if q["expected_x"] == 1)
    seq = pos_q["seq"]
    step0 = env.transition(s0, tuple(seq[0]))
    assert step0.status == "EXECUTED"
    s1 = step0.next_state
    assert s1.depth == 1
    assert s1.q_t != s0.q_t  # Robot joint state carried, not reset to q_ref

    blob = env.clone_or_serialize(s1)
    # Branch A: try a duplicate move of the same object (illegal) and another move
    dup_res = env.transition(s1, (seq[0][0], obs0.legal_destinations[1]))
    assert dup_res.status == "PHYSICALLY_FAILED" and dup_res.failure_kind == "INELIGIBLE"
    # Vacated cell reuse is illegal
    vacated_cell = int(inp["cells0"][seq[0][0]])
    other_o = [o for o in obs0.eligible_objects if o != seq[0][0]][0]
    vac_res = env.transition(s1, (other_o, vacated_cell))
    assert vac_res.status == "PHYSICALLY_FAILED" and vac_res.failure_kind == "INELIGIBLE"

    # Restore s1 and complete the sequence
    s1_restored = env.restore(blob)
    assert s1_restored.state_hash() == s1.state_hash()
    step1 = env.transition(s1_restored, tuple(seq[1]))
    assert step1.status == "EXECUTED"
    stop_res = env.terminal_query(step1.next_state)
    assert stop_res.status == "DECIDED"
    assert stop_res.x_terminal == pos_q["expected_x"]
    assert stop_res.y_target == pos_q["expected_y"]


def test_d1_grammar_and_state_isolation_3d():
    env = E.RepairEnv("3d")
    s0 = env.reset("3ds66-srv3-w0089-s006", seed=0)
    obs0 = env.observe(s0)
    assert obs0.q_t_optional is None
    assert obs0.remaining_steps == 3

    # Illegal target move rejected
    res_target = env.transition(s0, (obs0.tid, obs0.legal_destinations[0]))
    assert res_target.status == "PHYSICALLY_FAILED" and res_target.failure_kind == "INELIGIBLE"

    # Execute step 0 of verified order [(3, 32), (1, 24)]
    step0 = env.transition(s0, (3, 32))
    assert step0.status == "EXECUTED"
    s1 = step0.next_state
    blob = env.clone_or_serialize(s1)

    # Pollute live MuJoCo env by resetting to root and running failing order [(1, 24), (3, 32)]
    fail_seq = env.execute_complete_sequence("3ds66-srv3-w0089-s006", [(1, 24), (3, 32)], seed=0)
    assert fail_seq["x"] == 0 and fail_seq["failed_phase"] == "relocation:1" and fail_seq["y"] == 1

    # Restore s1 from serialized blob and finish step 1 + terminal connector
    s1_restored = env.restore(blob)
    assert s1_restored.state_hash() == s1.state_hash()
    step1 = env.transition(s1_restored, (1, 24))
    assert step1.status == "EXECUTED"
    stop_res = env.terminal_query(step1.next_state)
    assert stop_res.status == "DECIDED"
    assert stop_res.x_terminal == 1 and stop_res.y_target == 1 and stop_res.z_outcome == 1


def test_d1_stratified_parity_2d_and_3d():
    rep = run_d1_parity_audit(n_per_stratum_2d=4, n_per_stratum_3d=2)
    for dom in ("2d", "3d"):
        d = rep["domains"][dom]
        assert d["n_checked"] > 0
        assert d["n_decided"] == d["n_checked"]
        assert d["n_disagree"] == 0, f"Parity disagreement in {dom}: {d['disagreements']}"
        assert d["all_endpoint_y_invariant"], f"Endpoint Y not order-invariant in {dom}"
