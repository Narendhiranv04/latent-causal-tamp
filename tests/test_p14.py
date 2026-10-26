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


# ------------------------------------------------------------------ D1 retrieval / D2 search
import p14_sweep_index as sx  # noqa: E402


class _Idx:
    version, hash = "test", "test"

    def __init__(self, entries):
        import collections
        self.by_key = collections.defaultdict(list)
        for e in entries:
            e["_all"] = set().union(*map(set, e["swept"].values()))
            self.by_key[(e["src"], e["dst"])].append(e)


def _e(src, dst, root, cells, radius=0.024, travel=1.0, i=0):
    occ = [0] * 64
    return {"src": src, "dst": dst, "radius": radius, "support_id": root, "file": root, "index": i, "travel_J": travel,
            "swept": {"carry": cells}, "w3_src": [0] * 9, "w4_src": [0] * 16, "w3_dst": [0] * 9, "w4_dst": [0] * 16, "global": occ}


@pytest.fixture(scope="module")
def scene():
    from scene import scene_from_dict
    r = next(iter(json.loads(Path("runs/p13/data/train_b1/plan.json").read_text())["roots"].values()))
    return scene_from_dict(r["scene"]), r["goal_cell"]


def test_fixed_base_same_delta_elsewhere_and_footprint_are_not_reusable(scene):
    s, g = scene
    idx = _Idx([_e(20, 36, "r1", [1, 2])])
    assert sx.lookup_candidates(idx, "o00", 21, 37, s, g, 0.024)["status"] == "UNKNOWN_NO_COMPATIBLE_WITNESS"   # same delta, other cells
    r = sx.lookup_candidates(idx, "o00", 20, 36, s, g, 0.030)
    assert r["status"] == "UNKNOWN_NO_COMPATIBLE_WITNESS" and r["rejected"]["footprint"] == 1


def test_modes_ranked_by_independent_support_not_duplicates_and_modal_only_drops_rare(scene):
    s, g = scene
    freq = [_e(20, 36, f"r{i}", [1, 2, 3], i=i) for i in range(3)]                # one mode, three independent roots
    dup = [_e(20, 36, "rdup", [40, 41, 42], i=10 + i) for i in range(5)]           # one mode, five records from ONE root
    rare = [_e(20, 36, "rare", [50, 51], i=20)]
    r = sx.lookup_candidates(_Idx(freq + dup + rare), "o00", 20, 36, s, g, 0.024)
    assert r["modes"] == 3 and r["candidates"][0]["support"] == 3 and r["candidates"][0]["entry"]["swept"]["carry"] == [1, 2, 3]
    assert {c["entry"]["support_id"] for c in r["candidates"]} >= {"rare", "rdup"}
    m = sx.lookup_candidates(_Idx(freq + dup + rare), "o00", 20, 36, s, g, 0.024, modal_only=True)
    assert len(m["candidates"]) == 1 and all(c["entry"]["support_id"] != "rare" for c in m["candidates"])


def test_real_witness_certifier_catches_link_sweep_collision_away_from_end_effector():
    import geometry as ge
    import motion as mo
    import skill as sk
    import config as cf
    from dataclasses import replace
    cfg = cf.load_config("config.toml")
    robot, p = ge.make_robot(cfg), sk.params(cfg)
    idx = sx.Index()
    for key, es in sorted(idx.by_key.items()):
        e = es[0]
        r = sx._plans()[e["root"]]
        prov = next(pr for pr, a, rr in sx.records() if pr["file"] == e["file"] and pr["index"] == e["index"])
        s = sx.scene_at(r, prov["prefix"])
        a = idx.arrays(e)
        occupied = {o.cell for o in s.objects} | {s.get(prov["moved"]).cell, e["dst"], r["goal_cell"]}
        far = [c for c in e["swept"]["pregrasp"] if c not in occupied and min(abs(c // 8 - x // 8) + abs(c % 8 - x % 8) for x in (key[0], key[1])) >= 3]
        if not far:
            continue
        assert all(v.status == ge.CLEAR for v in mo.certify_trajectory(robot, s, prov["moved"], a, p["delta"], p["eps"], p["evals"]))
        o = s.objects[0]
        s2 = replace(s, objects=s.objects + (replace(o, id="probe", cell=far[0], xy_m=s.lattice.center(far[0])),))
        v = mo.certify_trajectory(robot, s2, prov["moved"], a, p["delta"], p["eps"], p["evals"])
        if any(x.status == ge.COLLISION for x in v):
            return
    pytest.fail("no witness found whose pregrasp link sweep collides with an obstacle far from source / destination")
