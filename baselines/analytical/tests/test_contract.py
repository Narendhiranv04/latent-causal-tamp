"""Legality: fixed / target exclusion, move-once, ORIGINALLY-empty destinations, goal cell, K <= 3; agreement with benchmark.legality."""
import importlib.util
import itertools
import json
from pathlib import Path

import numpy as np
import pytest

from baselines.analytical import contract as CT
from baselines.analytical import envs
from toy import A, B, C, F, T, ToyPhys, toy_row

BENCH = Path(__file__).resolve().parents[3] / "approach_b_final/benchmark.py"


def bench():
    sp = importlib.util.spec_from_file_location("ab_benchmark_ro", BENCH)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def test_rules():
    inp = toy_row()["inputs"]
    assert CT.movable(inp, "2d") == [A, B, C]                              # target and fixed F excluded
    assert CT.legality(inp, "2d", [(T, 5)]) == "IMMOVABLE_OBJECT"
    assert CT.legality(inp, "2d", [(F, 5)]) == "IMMOVABLE_OBJECT"
    assert CT.legality(inp, "2d", [(A, 5), (A, 6)]) == "OBJECT_MOVED_TWICE"
    assert CT.legality(inp, "2d", [(A, 5), (B, 1)]) == "ILLEGAL_DESTINATION"  # A's vacated source cell is never reused
    assert CT.legality(inp, "2d", [(A, 3)]) == "ILLEGAL_DESTINATION"          # the target's goal cell
    assert CT.legality(inp, "2d", [(A, 5), (B, 5)]) == "ILLEGAL_DESTINATION"  # occupied now
    assert CT.legality(inp, "2d", [(A, 4), (B, 5), (C, 6), (A, 7)]) == "LENGTH"
    assert CT.legality(inp, "2d", []) == "LENGTH"
    assert CT.legality(inp, "2d", [(A, 4), (B, 5), (C, 6)]) is None
    assert 1 not in CT.legal_dests(inp, CT.apply(inp, [(A, 4)])) and 3 not in CT.legal_dests(inp, inp["cells0"])
    assert CT.eligible(inp, "2d", [(A, 4), (B, 5), (C, 6)]) == []


def test_agrees_with_benchmark_legality():
    bm = bench()
    row = toy_row()
    rng = np.random.default_rng(0)
    for _ in range(3000):
        n = int(rng.integers(0, 5))
        prefix = [(int(rng.integers(0, 5)), int(rng.integers(0, 16))) for _ in range(n)]
        moves = [{"object_index": o, "object_id": row["inputs"]["ids"][o], "destination_cell": d} for o, d in prefix]
        assert CT.legality(row["inputs"], "2d", prefix) == bm.legality(row, moves), prefix


def test_real_rows_agree_with_benchmark():
    bm = bench()
    p = Path.home() / "analytical_baselines/smoke/public_train_3d.jsonl"
    if not p.exists():
        pytest.skip("smoke rows not built")
    rng = np.random.default_rng(1)
    for row in map(json.loads, open(p)):
        inp = row["inputs"]
        for _ in range(300):
            prefix = [(int(rng.integers(0, len(inp["ids"]))), int(rng.integers(0, 36))) for _ in range(int(rng.integers(1, 4)))]
            moves = [{"object_index": o, "object_id": inp["ids"][o], "destination_cell": d} for o, d in prefix]
            assert CT.legality(inp, "3d", prefix) == bm.legality(row, moves)


def test_phys_never_sends_illegal_actions():
    ph = ToyPhys()
    s0 = ph.reset()
    for o, d in [(T, 5), (F, 5), (A, 3), (A, 2)]:
        assert ph.step(s0, o, d) is None
    s1 = ph.step(s0, A, 5)
    assert ph.step(s1, B, 1) is None and ph.step(s1, A, 6) is None       # vacated cell, move-once
    s3 = ph.step(ph.step(s1, B, 6), C, 7)
    assert ph.step(s3, T, 8) is None and ph.n["transition_calls"] == 3 and ph.n["illegal_rejected"] == 7


def test_prediction_line_and_one_answer():
    row = toy_row()
    p = CT.prediction(row, "REPAIR", [(A, 4), (B, 5)])
    assert p["moves"][1] == {"object_id": "B", "object_index": B, "destination_cell": 5}
    assert CT.prediction(row, "NOOP", [(A, 4)])["moves"] == []
    with pytest.raises(AssertionError):
        CT.prediction(row, "REPAIR", [(A, 1)])
    with pytest.raises(AssertionError):
        CT.prediction(row, "MAYBE")


def test_private_keys_scrubbed():
    rec = {k: "SECRET" for k in envs.PRIVATE_RAW_KEYS} | {"scene": 1, "objects": 2, "ids": {"root_id": "x"}}
    clean = envs.scrub(rec)
    assert set(clean) == {"scene", "objects", "ids"}
    row = {"root_id": "r", "domain": "2d", "inputs": {}, "K_legacy": "3", "labels": {"X": 1}, "masks": {}}
    assert set(CT.public_row(row)) == {"root_id", "domain", "inputs"}
    for name in ("em4m", "mosegman", "msmcts", "common", "phys", "geo"):           # planners never name a private field
        src = (Path(__file__).resolve().parents[1] / f"{name}.py").read_text()
        for key in ("K_legacy", "labels", "intended_blockers", "verified_K", '"roles"', "masks"):
            assert key not in src, (name, key)
