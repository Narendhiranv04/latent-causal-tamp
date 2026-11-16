#!/usr/bin/env python3
"""D2 unit tests for DISCO-Grid Policy (P0) and Value Network (Q) contracts."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import data as D
import env as E
import policy as P


def test_policy_masking_and_zero_support_safety():
    for dom in ("2d", "3d"):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        net = P.DiscoPolicyNet(dom, h=64).to(device).eval()
        q2 = D.load_q2_dataset(dom)
        scalers = q2["scalers"]
        row = D.load_snapshot_rows(dom, "train", D.BASE_SNAP)[0]
        inp = row["inputs"]
        leg_info = D.legal_actions_at_prefix(inp, dom, [])
        obs = E.LearnerObservation(
            root_id=row["root_id"],
            domain=dom,
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
            eligible_objects=leg_info["eligible_objects"],
            legal_destinations=leg_info["legal_destinations"],
            can_stop=True,
        )
        wrapper = P.PolicyProposalWrapper(dom, net, scalers, device=device, mode="p0")
        dist = wrapper.action_distribution(obs)
        assert len(dist["reloc_actions"]) == len(obs.eligible_objects) * len(obs.legal_destinations)
        assert abs(float(dist["reloc_probs"].sum()) - 1.0) < 1e-5
        assert not np.isnan(dist["reloc_probs"]).any()

        # Verify illegal cells get zero probability
        for o, p_vec in dist["dst_probs_by_obj"].items():
            for c_idx in range(len(p_vec)):
                if c_idx not in obs.legal_destinations:
                    assert p_vec[c_idx] < 1e-6

        # Verify P0 keeps uniform object prior over eligible objects
        for o, p_o in dist["obj_probs"].items():
            assert abs(p_o - 1.0 / len(obs.eligible_objects)) < 1e-6

        rng = np.random.default_rng(42)
        samp = wrapper.sample_candidates(obs, B=16, rng=rng)
        assert len(samp["candidates"]) == min(16, len(dist["reloc_actions"]))
        assert len(set(samp["candidates"])) == len(samp["candidates"])
        for o, d in samp["candidates"]:
            assert o in obs.eligible_objects
            assert d in obs.legal_destinations


def test_value_network_weighted_bce_math():
    for dom in ("2d", "3d"):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        vnet = P.DiscoValueNet(dom, h=64).to(device)
        max_o = P.MAXOBJ[dom]
        N = P.GRID[dom][0] * P.GRID[dom][1]
        tdim = P.task_dim(dom)

        B = 4
        tok = torch.randn(B, max_o, 18, device=device)
        mask = torch.ones(B, max_o, dtype=torch.bool, device=device)
        ctx = torch.randn(B, N + tdim, device=device)
        act_o = torch.tensor([0, 1, 2, max_o], dtype=torch.long, device=device)  # last is STOP
        act_d = torch.tensor([3, 5, 7, N], dtype=torch.long, device=device)      # last is STOP
        targets = torch.tensor([1.0, 0.5, 0.0, 1.0], dtype=torch.float32, device=device)
        n_leaves = torch.tensor([10, 4, 1, 8], dtype=torch.float32, device=device)

        loss, stats = vnet.weighted_bce_loss(tok, mask, ctx, act_o, act_d, targets, n_leaves)
        assert not torch.isnan(loss)
        # Verify exact log1p weighting formula
        with torch.no_grad():
            logits = vnet.forward_logits(tok, mask, ctx, act_o, act_d)
            bce = torch.nn.functional.binary_cross_entropy_with_logits(logits, targets, reduction="none")
            w = torch.log1p(n_leaves)
            expected_loss = (w * bce).sum() / w.sum()
            assert abs(float(loss.item()) - float(expected_loss.item())) < 1e-6
