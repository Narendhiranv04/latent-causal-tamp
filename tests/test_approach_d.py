"""Approach D v1.0 (approachD_methodology.pdf). G1: relative-displacement retrieval over the P14/P15 witness index. Retrieval only: no
candidate is adapted or certified, cross-location witnesses are flagged requires_adaptation, the legacy exact-cell lookup is unchanged."""
import collections
import copy
import json
import math
from pathlib import Path

import numpy as np
import pytest

import p14_sweep_index as sx
import p15_lookup as pl


class _Idx:
    version, hash = "test", "sha256:test"

    def __init__(self, entries):
        self.by_key = collections.defaultdict(list)
        for e in entries:
            e["_all"] = set().union(*map(set, e["swept"].values()))
            self.by_key[(e["src"], e["dst"])].append(e)


def _e(src, dst, root, swept=None, radius=0.024, travel=1.0, i=0, q_end=(0.0, 1.0, 1.0), w=0):
    sw = {"carry": [src, dst]} if swept is None else swept
    return {"src": src, "dst": dst, "radius": radius, "support_id": root, "root": root, "file": root, "index": i, "travel_J": travel,
            "swept": sw, "q_end": list(q_end), "w3_src": [w] * 9, "w4_src": [w] * 16, "w3_dst": [w] * 9, "w4_dst": [w] * 16, "global": [0] * 64}


def _ri(entries, **over):
    return pl.RelIndex(_Idx(entries), pl.rel_cfg(**over))


@pytest.fixture(scope="module")
def real():
    idx, _ = pl.index_v2()
    return pl.RelIndex(idx, pl.rel_cfg())


def test_same_delta_elsewhere_retrieves_each_other_but_legacy_lookup_does_not():
    a, b = _e(10, 18, "rA"), _e(34, 42, "rB")                       # delta (1, 0) at two absolute positions
    ri = _ri([a, b])
    for q, other in ((a, b), (b, a)):
        r = pl.lookup_relative(ri, q, 0.024, frozenset({q["root"]}), exclude_abs=True)
        assert r["status"] == "CANDIDATES" and [c["entry"]["root"] for c in r["candidates"]] == [other["root"]]
        c = r["candidates"][0]
        assert c["requires_adaptation"] and not c["same_absolute"] and not c["adapted"] and not c["verified"]
    assert sx.rel_key(10, 18, 0.024) == sx.rel_key(34, 42, 0.024)
    assert ri.idx.by_key.get((34, 42)) == [b] and (10, 18) not in {k for k in ri.idx.by_key if k == (34, 42)}   # absolute keys stay distinct


def test_distinct_delta_and_footprint_are_not_mixed():
    ri = _ri([_e(10, 18, "rA"), _e(34, 35, "rB"), _e(26, 34, "rC", radius=0.030)])
    r = pl.lookup_relative(ri, _e(42, 50, "q"), 0.024)
    assert [c["entry"]["root"] for c in r["candidates"]] == ["rA"]
    assert pl.lookup_relative(ri, _e(42, 50, "q"), 0.030)["candidates"][0]["entry"]["root"] == "rC"


def test_no_witness_is_unknown_never_infeasible():
    r = pl.lookup_relative(_ri([_e(10, 18, "rA")]), _e(10, 12, "q"), 0.024)
    assert r["status"] == "UNKNOWN_NO_WITNESS" and r["candidates"] == [] and "INFEASIBLE" not in r["status"]
    r = pl.lookup_relative(_ri([_e(10, 18, "rA")]), _e(10, 18, "q"), 0.024, frozenset({"rA"}))
    assert r["status"] == "UNKNOWN_NO_WITNESS"                      # everything excluded -> still UNKNOWN


def test_windows_are_translation_consistent_with_consistent_border_padding():
    occ = np.zeros(64, int)
    for c, v in ((19, 1), (20, 4), (28, 2), (29, 3)):              # pattern around cell 20 = (2, 4)
        occ[c] = v
    moved = np.zeros(64, int)
    for c, v in ((19, 1), (20, 4), (28, 2), (29, 3)):
        moved[c + 8 * 2 - 2] = v                                   # translate by (+2 rows, -2 cols)
    assert sx.windows(occ, 20) == sx.windows(moved, 20 + 16 - 2)
    w3, w4 = sx.windows(np.zeros(64, int), 0)                       # corner: off-board cells are -1 at fixed window positions
    assert w3 == [-1, -1, -1, -1, 0, 0, -1, 0, 0] and w4[:4] == [-1] * 4 and w4[4::4] == [-1] * 3
    w3b, _ = sx.windows(np.zeros(64, int), 63)
    assert w3b == [0, 0, -1, 0, 0, -1, -1, -1, -1]


def test_descriptor_is_invariant_to_object_ids_and_matches_stored_entries():
    from scene import scene_from_dict
    r = next(iter(json.loads(Path("runs/p13/data/train_b1/plan.json").read_text())["roots"].values()))
    s = scene_from_dict(r["scene"])
    o = next(x for x in s.objects if x.kind != "target")
    d0 = sx.descriptor(s, r["goal_cell"], o.id, o.cell, 0)
    ren = copy.deepcopy(r["scene"])
    names = {x["id"]: (x["id"] if x["id"] == "t0" else f"zz{i}") for i, x in enumerate(ren["objects"])}
    for x in ren["objects"]:
        x["id"] = names[x["id"]]
    d1 = sx.descriptor(scene_from_dict(ren), r["goal_cell"], names[o.id], o.cell, 0)
    assert d0 == d1
    occ = sx._occ(s, r["goal_cell"], o.id)
    assert (d0["w3_src"], d0["w4_src"]) == tuple(sx.windows(occ, o.cell)) and d0["global"] == occ.tolist()


def test_modes_are_deterministic_and_split_by_branch_and_local_sweep():
    es = [_e(10, 18, "r1", travel=1.0, i=0), _e(34, 42, "r2", {"carry": [34, 42]}, travel=2.0, i=1),
          _e(26, 34, "r3", q_end=(0, -1, 1), travel=0.5), _e(2, 10, "r4", {"carry": [2, 10, 11, 12]}, travel=0.7)]
    for e in es:
        e["_loc"], e["_branch"] = sx.local_sweep(e["swept"], e["src"], e["dst"]), sx.branch(e["q_end"])
    m1, m2 = pl.rel_modes(es, 0.6), pl.rel_modes(list(reversed(es)), 0.6)
    assert [[x["root"] for x in m] for m in m1] == [[x["root"] for x in m] for m in m2]
    assert sorted(len(m) for m in m1) == [1, 1, 2]                 # r1+r2 same pattern; r3 other branch; r4 other local sweep
    assert sx.local_sweep({"carry": [10, 18]}, 10, 18) == sx.local_sweep({"carry": [34, 42]}, 34, 42)


def test_shortlist_is_bounded_diverse_and_flags_same_location_witnesses():
    es = [_e(10, 18, f"r{i}", {"carry": [10, 18] + ([11] * (i % 3 == 1)) + ([12, 13, 9] * (i % 3 == 2))}, i=i, q_end=(0, 1, 1)) for i in range(9)]
    es += [_e(20, 28, "same", i=99, travel=0.1)]                   # cheapest, so it leads its (tied-score) mode
    ri = _ri(es)
    r = pl.lookup_relative(ri, _e(20, 28, "q"), 0.024)
    c = r["candidates"]
    assert len(c) <= ri.cfg["mode_limit"] * ri.cfg["witnesses_per_mode"]
    assert all(sum(x["mode"] == m for x in c) <= ri.cfg["witnesses_per_mode"] for m in {x["mode"] for x in c})
    assert {x["entry"]["root"]: x["requires_adaptation"] for x in c}.get("same") is False
    assert all(x["requires_adaptation"] == ((x["entry"]["src"], x["entry"]["dst"]) != (20, 28)) for x in c)


def test_legacy_switch_and_legacy_weights_reproduce_the_absolute_lookup(real):
    import p6_scenes as p6
    from scene import scene_from_dict
    key = max(real.idx.by_key, key=lambda k: (len(real.idx.by_key[k]), k))
    e = sorted(real.idx.by_key[key], key=lambda e: (e["file"], e["index"]))[0]
    P = sx._plans()
    s = scene_from_dict(P[e["root"]]["scene"])
    oid = next(o.id for o in s.objects if o.kind != "target")
    if s.get(oid).cell != key[0] and key[0] not in {o.cell for o in s.objects}:
        s = p6.moved(s, {oid: key[0]})                              # query object placed at the key's source cell
    assert s.get(oid).cell == key[0]
    goal = P[e["root"]]["goal_cell"]
    leg = sx.lookup_candidates(real.idx, oid, key[0], key[1], s, goal, 0.024)
    ra = copy.copy(real)
    ra.cfg = {**real.cfg, "key": "absolute_src_dst"}
    assert pl.retrieve(ra, oid, key[0], key[1], s, goal, 0.024) == leg
    q = sx.descriptor(s, goal, oid, *key)
    rel = {(x["file"], x["index"]): pl.rel_score(q, x, real.cfg, real.base)["total"] for x in real.idx.by_key[key]}
    assert all(abs(rel[(c["entry"]["file"], c["entry"]["index"])] - c["similarity"]) < 1e-12 for c in leg["candidates"])


def test_indexed_retrieval_equals_brute_force_scan_and_honours_exclusions(real):
    keys = sorted(real.idx.by_key)[::25]
    for key in keys:
        q = sorted(real.idx.by_key[key], key=lambda e: (e["file"], e["index"]))[0]
        excl = frozenset({q["support_id"]})
        for loko in (False, True):
            a = pl.lookup_relative(real, q, q["radius"], excl, loko)
            b = pl.lookup_relative_scan(real, q, q["radius"], exclude_roots=excl, exclude_abs=loko)
            assert [(c["entry"]["file"], c["entry"]["index"], c["mode"]) for c in a["candidates"]] == \
                   [(c["entry"]["file"], c["entry"]["index"], c["mode"]) for c in b["candidates"]]
            assert all(c["entry"]["support_id"] not in excl for c in a["candidates"])
            assert not loko or all(tuple(c["abs_key"]) != key for c in a["candidates"])


def test_base_residual_is_zero_only_for_an_exact_base_rotation():
    base = sx.center(27)                                           # a base on a cell centre makes 90 deg rotations land on cells
    res, psi = sx.base_residual(base, 28, 29, 35, 43)               # offsets (0,1),(0,2) -> (1,0),(2,0)
    assert res < 1e-12 and abs(abs(psi) - math.pi / 2) < 1e-12
    assert sx.base_residual(base, 28, 29, 28, 29)[0] < 1e-12
    real_base = (-0.14, 0.32)
    assert sx.base_residual(real_base, 10, 18, 34, 42)[0] > 0.01   # same delta, different robot-relative geometry


def test_config_overlay_is_validated_and_config_toml_is_untouched(tmp_path):
    src = Path("approach_d.toml").read_text()
    (tmp_path / "bad.toml").write_text(src.replace("mode_limit = 3", "mode_limt = 3"))
    with pytest.raises(ValueError):
        pl.rel_cfg(tmp_path / "bad.toml")
    (tmp_path / "bad2.toml").write_text(src.replace('"UNKNOWN_NO_WITNESS"', '"INFEASIBLE"'))
    with pytest.raises(ValueError):
        pl.rel_cfg(tmp_path / "bad2.toml")
    import config as cf
    assert "relative_lookup" not in cf.load_config("config.toml")
