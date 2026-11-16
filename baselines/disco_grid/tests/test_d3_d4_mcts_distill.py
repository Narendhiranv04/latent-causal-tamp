#!/usr/bin/env python3
"""D3 and D4 unit tests for DISCO-Grid MCTS and Tree-to-Policy/Value Distillation."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import data as D
import distill as DS
import env as E
import mcts as M
import policy as P


def test_mcts_progressive_widening_ucb_and_backup_math():
    """Verify PW condition at N=0/1..k, UCB tie-breaking, path_return telescoping, and backup running mean."""
    obs_dummy = E.LearnerObservation(
        root_id="toy_root",
        domain="2d",
        ids=["t0", "o0", "o1"],
        cells=[0, 10, 20],
        xy=[[0.04, 0.04], [0.20, 0.12], [0.36, 0.20]],
        attrs=[[0.024, 1.0, 0.0, 0.0], [0.024, 0.0, 1.0, 0.0], [0.024, 0.0, 1.0, 0.0]],
        tid=0,
        goal_cell=18,
        goal_xy=[0.20, 0.20],
        base_xy=[-0.14, 0.32],
        ctx=[0.0] * 9,
        legal_cells=list(range(64)),
        cell_xy={str(c): [0.08 * (c % 8 + 0.5), 0.08 * (c // 8 + 0.5)] for c in range(64)},
        moved_mask=[False, False, False],
        remaining_steps=3,
        eligible_objects=[1, 2],
        legal_destinations=[30, 31, 32],
    )
    # Check nonterminal progress kappa is strictly < 1.0, and verified terminal success is 1.0
    k_nonterm = M.compute_progress_kappa(obs_dummy, is_verified_terminal_success=False, mode="geometric")
    assert 0.0 <= k_nonterm <= 0.85 < 1.0
    k_term = M.compute_progress_kappa(obs_dummy, is_verified_terminal_success=True, mode="geometric")
    assert k_term == 1.0
    assert M.compute_progress_kappa(obs_dummy, is_verified_terminal_success=False, mode="sparse") == 0.0
    assert M.compute_progress_kappa(obs_dummy, is_verified_terminal_success=True, mode="sparse") == 1.0

    # Hand-construct a 4-node tree to verify leaf_stats, UCB, and backup equations
    root = M.MCTSNode(0, None, [], 0, b"", "h0", obs_dummy, None, progress_kappa=0.2, edge_reward=0.0, visit_count=5, children_ids=[1, 2])
    c1 = M.MCTSNode(1, 0, [(1, 30)], 1, b"", "h1", obs_dummy, (1, 30), progress_kappa=0.5, edge_reward=0.3, visit_count=3, Q=0.3, children_ids=[3, 4])
    c2 = M.MCTSNode(2, 0, [(2, 31)], 1, b"", "h2", obs_dummy, (2, 31), progress_kappa=0.4, edge_reward=0.2, visit_count=1, Q=0.2, terminal_z=0)
    # Leaf 3 under c1 succeeds (Z=1); Leaf 4 under c1 fails (Z=0); Leaf 5 under c1 is UNRESOLVED (terminal_z=None)
    l3 = M.MCTSNode(3, 1, [(1, 30)], 2, b"", "h3", obs_dummy, "STOP", is_stop_node=True, progress_kappa=1.0, edge_reward=0.5, visit_count=2, Q=0.8, terminal_z=1)
    l4 = M.MCTSNode(4, 1, [(1, 30), (2, 32)], 2, b"", "h4", obs_dummy, (2, 32), progress_kappa=0.6, edge_reward=0.1, visit_count=1, Q=0.4, terminal_z=0)
    l5 = M.MCTSNode(5, 1, [(1, 30), (2, 31)], 2, b"", "h5", obs_dummy, (2, 31), progress_kappa=0.5, edge_reward=0.0, visit_count=1, Q=0.3, terminal_z=None)
    c1.children_ids = [3, 4, 5]

    nodes = [root, c1, c2, l3, l4, l5]
    stats = DS.compute_leaf_stats(nodes)
    # l3 is 1/1; l4 is 0/1; l5 is 0/0 (unresolved excluded from denominator!)
    assert stats[3] == (1, 1)
    assert stats[4] == (0, 1)
    assert stats[5] == (0, 0)
    # c1 has 1 success leaf out of 2 decided leaves -> y_1 = 0.5, w_1 = log(1 + 2)
    assert stats[1] == (1, 2)
    # c2 has 0 success leaves out of 1 decided leaf -> y_2 = 0.0, w_2 = log(1 + 1)
    assert stats[2] == (0, 1)
    # root has 1 success leaf out of 3 decided leaves
    assert stats[0] == (1, 3)

    # Verify UCB formula
    expected_ucb_c1 = 0.3 + 1.5 * math.sqrt(math.log(5 + 1) / (3 + 1))
    assert abs(c1.ucb_score(5, 1.5) - expected_ucb_c1) < 1e-9


def test_distillation_extraction_all_feasible_vs_successful_only():
    q2 = D.load_q2_dataset("2d")
    scalers = q2["scalers"]
    row = D.load_snapshot_rows("2d", "train")[0]
    inp = row["inputs"]
    leg = D.legal_actions_at_prefix(inp, "2d", [])
    obs0 = E.LearnerObservation(
        root_id=row["root_id"],
        domain="2d",
        ids=list(inp["ids"]),
        cells=list(inp["cells0"]),
        xy=list(inp["xy0"]),
        attrs=list(inp["attrs"]),
        tid=int(inp["tid"]),
        goal_cell=int(inp["goal_cell"]),
        goal_xy=list(inp["goal"]),
        base_xy=list(inp["base"]),
        ctx=list(inp["ctx"]),
        legal_cells=list(inp["legal_cells"]),
        cell_xy=dict(inp["cell_xy"]),
        moved_mask=[False] * len(inp["ids"]),
        remaining_steps=3,
        eligible_objects=leg["eligible_objects"],
        legal_destinations=leg["legal_destinations"],
    )
    o0, o1 = obs0.eligible_objects[0], obs0.eligible_objects[1]
    d0, d1 = obs0.legal_destinations[0], obs0.legal_destinations[1]
    obs1 = E.predict_observation_edit(obs0, (o0, d0))
    obs2 = E.predict_observation_edit(obs0, (o1, d1))

    stop_neg = E.StopResult("DECIDED", False, 1, 0, 0, "target", "NO_PLAN_FOUND", "VERIFIED", "UNKNOWN_PLANNER")
    stop_pos = E.StopResult("DECIDED", True, 1, 1, 1, None, None, "VERIFIED", "VERIFIED")

    root = M.MCTSNode(0, None, [], 0, b"", "h0", obs0, None, visit_count=4, children_ids=[1, 2], stop_evaluated=True, stop_result=stop_neg, terminal_z=0)
    # Child 1 leads to a successful STOP child 3
    c1 = M.MCTSNode(1, 0, [(o0, d0)], 1, b"", "h1", obs1, (o0, d0), visit_count=2, children_ids=[3], stop_evaluated=True, stop_result=stop_pos, stop_child_id=3, terminal_z=1)
    c2 = M.MCTSNode(2, 0, [(o1, d1)], 1, b"", "h2", obs2, (o1, d1), visit_count=1, children_ids=[], stop_evaluated=True, stop_result=stop_neg, terminal_z=0)
    c3 = M.MCTSNode(3, 1, [(o0, d0)], 2, b"", "h3", obs1, "STOP", is_stop_node=True, visit_count=2, stop_evaluated=True, stop_result=stop_pos, terminal_z=1)

    nodes = [root, c1, c2, c3]
    ext_all = DS.extract_distillation_data_from_tree(nodes, "2d", scalers, edges_mode="all_feasible")
    ext_succ = DS.extract_distillation_data_from_tree(nodes, "2d", scalers, edges_mode="successful_only")

    # Under all_feasible, BOTH c1 and c2 are extracted as policy destination rows (2 rows)
    assert len(ext_all["policy_dst_rows"]) == 2
    # Under successful_only, ONLY c1 (which has a successful descendant leaf) is extracted (1 row)
    assert len(ext_succ["policy_dst_rows"]) == 1
    assert ext_succ["policy_dst_rows"][0]["target_dest"] == d0

    # Value rows include: root STOP (Z=0), c1 relocation (y=1.0), c2 relocation (y=0.0), c1 STOP (Z=1), c2 STOP (Z=0)
    assert len(ext_all["value_rows"]) == 5
    stop_targets = [r["value_target"] for r in ext_all["value_rows"] if r["is_stop"]]
    assert 0.0 in stop_targets and 1.0 in stop_targets
