#!/usr/bin/env python3
"""D6 and D7 unit tests for Open-Loop and Closed-Loop Inference & Metric Accounting."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import torch

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import data as D
import evaluate as EV
import policy as P


def test_open_loop_zero_physical_calls_and_grammar_validity():
    for dom in ("2d", "3d"):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        q2 = D.load_q2_dataset(dom)
        scalers = q2["scalers"]
        pnet = P.DiscoPolicyNet(dom, h=64).to(device).eval()
        vnet = P.DiscoValueNet(dom, h=64).to(device).eval()
        wrap = P.PolicyProposalWrapper(dom, pnet, scalers, device=device, mode="distilled", value_model=vnet)

        rows = D.load_snapshot_rows(dom, "valsub", D.BASE_SNAP)[:6]
        for r in rows:
            res = EV.predict_open_loop_sequence(r, dom, wrap, B_test=8, use_value=True, seed=0)
            assert res["planner_calls_during_selection"] == 0
            assert res["protocol"] == "open_loop"
            if res["seq"] is not None:
                assert len(res["seq"]) <= 3
                assert D.validate_repair_sequence(r["inputs"], dom, [tuple(a) for a in res["seq"]]) == []
