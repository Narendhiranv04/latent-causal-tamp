#!/usr/bin/env python3
"""D0 preflight and source/dataset/grammar audit tests for DISCO-Grid."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import data as D


def test_snapshots_and_locks():
    for snap in (D.BASE_SNAP, D.V2_SNAP):
        res = D.verify_snapshot_lock(snap)
        assert res["all_ok"], f"Snapshot lock verification failed for {snap}: {res}"


def test_split_hygiene_and_root_counts():
    for dom, expected_n in (("2d", 5000), ("3d", 2500)):
        rows = D.load_snapshot_rows(dom, None, D.BASE_SNAP)
        assert len(rows) == expected_n
        hyg = D.check_split_hygiene(rows)
        assert hyg["root_split_conflicts"] == 0
        assert hyg["family_split_conflicts"] == 0
        assert hyg["layout_split_conflicts"] == 0

        # Check valsub and valrest partition val cleanly
        val = D.load_snapshot_rows(dom, "val", D.BASE_SNAP)
        valsub = D.load_snapshot_rows(dom, "valsub", D.BASE_SNAP)
        valrest = D.load_snapshot_rows(dom, "valrest", D.BASE_SNAP)
        assert len(valsub) + len(valrest) == len(val)
        assert not ({r["root_id"] for r in valsub} & {r["root_id"] for r in valrest})


def test_raw_root_files_exist_and_match_sha():
    for dom in ("2d", "3d"):
        rows = D.load_snapshot_rows(dom, "train", D.BASE_SNAP)[:15]
        for r in rows:
            p = D.raw_root_path(dom, r["root_id"])
            assert p.exists(), f"Missing raw root file {p}"
            assert D.sha256_file(p) == r["root_sha256"]


def test_static_action_grammar():
    for dom in ("2d", "3d"):
        row = D.load_snapshot_rows(dom, "train", D.BASE_SNAP)[0]
        inp = row["inputs"]
        tid = int(inp["tid"])
        goal = int(inp["goal_cell"])
        occ0 = [int(c) for c in inp["cells0"]]

        # Empty repair (K0 STOP) is valid
        assert D.validate_repair_sequence(inp, dom, []) == []

        info = D.legal_actions_at_prefix(inp, dom, [])
        assert tid not in info["eligible_objects"]
        assert goal not in info["legal_destinations"]
        for c in occ0:
            assert c not in info["legal_destinations"]

        if info["eligible_objects"] and len(info["legal_destinations"]) >= 2:
            o0 = info["eligible_objects"][0]
            d0, d1 = info["legal_destinations"][0], info["legal_destinations"][1]
            assert D.validate_repair_sequence(inp, dom, [(o0, d0)]) == []
            # Moving target is illegal
            assert "target_moved" in D.validate_repair_sequence(inp, dom, [(tid, d0)])
            # Moving same object twice is illegal
            assert "object_moved_twice" in D.validate_repair_sequence(inp, dom, [(o0, d0), (o0, d1)])
            # Placing into target goal cell is illegal
            assert "target_goal_cell_used" in D.validate_repair_sequence(inp, dom, [(o0, goal)])
            # Placing into an originally occupied cell (even if vacated) is illegal
            if len(info["eligible_objects"]) >= 2:
                o1 = info["eligible_objects"][1]
                vacated_cell = occ0[o0]
                assert "initially_occupied_cell_reused" in D.validate_repair_sequence(
                    inp, dom, [(o0, d0), (o1, vacated_cell)]
                )
                # Shared destination is illegal
                assert "shared_destination" in D.validate_repair_sequence(
                    inp, dom, [(o0, d0), (o1, d0)]
                )


def test_q2_datasets_and_zero_split_leakage():
    for dom in ("2d", "3d"):
        q2 = D.load_q2_dataset(dom)
        assert q2["scalers"]["fit_on"] == "TRAIN split only"
        assert q2["scalers"]["roots_in_two_splits"] == 0
        xy_rows = {r["root_id"]: r["split"] for r in D.load_snapshot_rows(dom, None, D.BASE_SNAP)}
        for r_id, sp_idx in zip(q2["roots"], q2["split"].tolist()):
            sp_name = D.SPLITS[int(sp_idx)]
            if r_id in xy_rows:
                assert xy_rows[r_id] == sp_name, f"Split mismatch on {r_id}: Q2={sp_name} vs XY={xy_rows[r_id]}"
