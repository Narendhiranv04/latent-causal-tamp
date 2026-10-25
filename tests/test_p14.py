"""P14: errata guards (J-contrast sign orientation, execution ledger recomputation, bounded compute status), keyed catalogue invariance,
and the D-sidecar unit tests (sweep provenance, similarity retrieval, joint search) added by later P14 stages."""
import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("P10C_OUT", "runs/p10c")

import p14_audit as pa  # noqa: E402


def test_paired_orientation_positive_means_first_argument_larger():
    r = pa.paired({"a": 0.9, "b": 0.8, "c": 0.7}, {"a": 0.8, "b": 0.8, "c": 0.6})
    assert r["mean_a_minus_b"] > 0 and r["a_larger"] == 2 and r["b_larger"] == 0 and r["ties"] == 1


def test_j_contrast_sign_corrected():
    e = json.loads(Path("runs/p14/audit/P13_ERRATA.json").read_text())["J_sign"]
    assert abs(e["corrected_J_minus_noJ"] - (e["rates"]["J"] - e["rates"]["noJ"])) < 1e-9
    assert e["corrected_J_minus_noJ"] > 0 and e["stored_mean_delta"] < 0


def test_execution_recompute_matches_final_ledgers():
    e = json.loads(Path("runs/p14/audit/P13_ERRATA.json").read_text())["execution"]
    assert e["episodes"] == 428 and sum(e["histogram_final_ledgers"].values()) == 428 and e["histogram_final_ledgers"]["SUCCESS"] == 301
    assert e["max_abs_difference_vs_reported"] < 1e-9


def test_training_compute_reported_as_bound_not_exact():
    c = json.loads(Path("runs/p14/audit/P13_ERRATA.json").read_text())["compute_P13_training"]
    assert c["best_estimate"] <= c["upper_bound_min_guard_wall"] <= c["raw_guard_sum"] and "BOUNDED" in c["status"]


def test_keyed_invariant_to_listing_an_omission_query_unkeyed_not():
    k = json.loads(Path("runs/p14/audit/KEYING_INVARIANCE.json").read_text())
    assert k["K-B"]["omission_slot_vs_listed_candidate"]["max"] < 1e-9
    assert k["B-U"]["omission_slot_vs_listed_candidate"]["max"] > 1e-3
