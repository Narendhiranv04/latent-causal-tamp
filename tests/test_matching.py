"""G3 A0 tests: exact matching, Murty k-best, Hall certificates, restoration lemma."""
import itertools
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config as cf  # noqa: E402
import motion as mo  # noqa: E402
import scene as sc  # noqa: E402
import solve  # noqa: E402

V, X, U = mo.VALID, mo.INVALID, mo.UNRESOLVED


@pytest.fixture(scope="module")
def cfg():
    return cf.load_config(ROOT / "config.toml")


def random_matrix(rng, n, m, p_inf=0.3):
    C = rng.integers(0, 4, size=(n, m)).astype(float)
    C[rng.random((n, m)) < p_inf] = np.inf
    return C


def toy(cfg, obstacles, invalid=(), unresolved=(), target=0):
    """Scene with t0 at `target` and obstacles o00.. at the given cells; a synthetic
    cell status (no robot) marks the action-blocked and unresolved cells."""
    s = sc.place_scene(cfg, "toy", "v", [target], obstacles)
    status = {c: (X if c in invalid else U if c in unresolved else V) for c in s.legal_cells if c != target}
    return s, status


def test_matching_equals_exhaustive_optimum(cfg):
    rng = np.random.default_rng(0)
    for _ in range(300):
        n = int(rng.integers(1, 5))
        C = random_matrix(rng, n, int(rng.integers(n, 7)))
        ex, s = solve.exhaustive(C), solve._solve(C)
        assert (s is None) == (not ex)
        if ex:
            assert s[0] == pytest.approx(ex[0][0])


def test_kbest_matches_exhaustive_with_ties_and_no_duplicates(cfg):
    rng = np.random.default_rng(1)
    for _ in range(200):
        n = int(rng.integers(1, 5))
        C = random_matrix(rng, n, int(rng.integers(n, 6)), p_inf=0.2)
        ex = solve.exhaustive(C)
        got = solve.kbest(C, 10)
        assert len(got) == min(10, len(ex))
        assert len({a for _, a in got}) == len(got)                          # Murty: distinct
        assert [c for c, _ in got] == pytest.approx([c for c, _ in ex[:len(got)]])  # same cost sequence
        assert all(c == pytest.approx(sum(C[i, j] for i, j in enumerate(a))) for c, a in got)
    flat = np.zeros((3, 4))                                                   # all-tie case: 24 equal optima
    assert len({a for _, a in solve.kbest(flat, 30)}) == 24


def test_hall_certificate_is_checkable_proof(cfg):
    rng = np.random.default_rng(2)
    seen = 0
    for _ in range(300):
        n = int(rng.integers(2, 6))
        C = random_matrix(rng, n, int(rng.integers(n, 7)), p_inf=0.7)
        cert = solve.hall_certificate(C)
        assert (cert is None) == bool(solve.exhaustive(C))
        if cert:
            seen += 1
            assert solve.check_hall(C, *cert)
            rows, cols = cert                                                  # tampered certificates fail
            assert not solve.check_hall(C, rows, cols[:-1]) or not cols
            assert not solve.check_hall(C, rows[:1], cols) or len(cols) == 0
    assert seen > 20


def test_a0_includes_every_obstacle_with_physical_ids(cfg):
    s, st = toy(cfg, [9, 10, 20, 33], invalid={9, 17, 18}, unresolved={40})
    t = solve.a0(s, solve.domains(s, "ALL_SUPPORTED"), st, 12, cfg["suite"]["margin_m"])
    assert t["objects"] == ["o00", "o01", "o02", "o03"] and t["direct_blockers"] == ["o00"]
    assert t["lower_bound"] == 1 and len(t["assignments"]) == 12
    for a in t["assignments"]:
        cells = a["cells"]
        assert set(cells) == {"o00", "o01", "o02", "o03"} and len(set(cells.values())) == 4
        assert all(st[c] == V for c in cells.values())                      # witnesses use VALID cells only
        assert 0 not in cells.values()                                       # never the target's cell
        assert a["cost"] == len(solve.moves_of(s, cells))                    # integer part = moved IDs
    assert all(a["cost"] == 1 for a in t["assignments"])
    ties = [a["tie_break"] for a in t["assignments"]]
    assert ties == sorted(ties)                                              # nearer destinations first
    assert t["assignments"][0]["cells"]["o00"] in (1, 8)                     # an adjacent VALID cell


def test_lexicographic_tie_break_never_changes_the_moved_count(cfg):
    s, st = toy(cfg, list(range(1, 9)), invalid=set(range(1, 9)) - {4})
    dom = solve.domains(s, "ALL_SUPPORTED")
    ids, cells, C = solve.cost_matrix(s, dom, st, optimistic=False)
    assert solve.moved_count(solve._solve(C)[0]) == 7
    unit = np.where(np.isfinite(C), (C > 0).astype(float), np.inf)            # pure 0/1 objective
    assert solve._solve(unit)[0] == 7
    frac = C[np.isfinite(C)] - np.floor(C[np.isfinite(C)])
    assert frac.max() * len(ids) < 1                                         # n tie-breaks sum below 1


def test_unresolved_edges_enter_the_bound_but_never_a_witness(cfg):
    s, st = toy(cfg, [9], invalid={9}, unresolved=set(range(1, 64)) - {9})
    t = solve.a0(s, solve.domains(s, "ALL_SUPPORTED"), st, 5, cfg["suite"]["margin_m"])
    assert t["lower_bound"] == 1 and t["assignments"] == [] and t["hall"] is None


def test_restoration_lemma_optimum_equals_direct_blockers(cfg):
    """b*_terminal = |D|. (>=) every direct blocker's current cell is action-invalid,
    so 'stay' is not an edge and each must move; (<=) returning exactly the blockers
    to their reference cells is terminal-valid, because those cells were valid for
    the frozen action, are still vacant and are distinct."""
    rng = np.random.default_rng(3)
    for _ in range(40):
        cells = rng.permutation(np.arange(1, 64))[:12].tolist()
        ref, _ = toy(cfg, cells)
        free = [c for c in range(1, 64) if c not in cells]
        d = int(rng.integers(1, 5))
        hit = dict(zip((f"o{k:02d}" for k in rng.choice(12, d, replace=False)),
                       rng.choice(free, d, replace=False).tolist()))
        objs = tuple(replace(o, xy_m=ref.lattice.center(hit[o.id]), cell=hit[o.id]) if o.id in hit else o
                     for o in ref.objects)
        blocked = replace(ref, objects=objs)
        _, st = toy(cfg, cells, invalid=set(hit.values()) | {free[-1]})
        r = solve.restoration(blocked, ref, st)
        t = solve.a0(blocked, solve.domains(blocked, "ALL_SUPPORTED"), st, 3, cfg["suite"]["margin_m"])
        assert r["terminal_valid"] and r["moves"] == d == len(r["direct_blockers"])
        assert t["lower_bound"] == d == t["assignments"][0]["cost"]


def test_occupied_preferred_destination_raises_cost_not_lower_bound(cfg):
    s, st = toy(cfg, [9, 10], invalid={9})
    dom = solve.domains(s, "ALL_SUPPORTED")
    t = solve.a0(s, dom, st, 3, cfg["suite"]["margin_m"])
    f = solve.forced(s, dom, st, "o00", 10)                                  # o01 owns cell 10
    assert t["lower_bound"] == 1 and f["cost"] == 2
    assert f["cells"]["o00"] == 10 and f["cells"]["o01"] != 10
    assert solve.forced(s, dom, st, "o00", 9) is None                        # its own blocked cell: no edge


def test_restricted_domain_hall_infeasible_while_all_supported_feasible(cfg):
    s, st = toy(cfg, [9, 10, 30], invalid={9, 10})
    dom = solve.restricted_domain(s, st, ["o00", "o01"], 1, exclude=())
    assert dom["o00"] == dom["o01"] and len(dom["o00"]) == 1
    delta = cfg["suite"]["margin_m"]
    allsup = solve.a0(s, solve.domains(s, "ALL_SUPPORTED"), st, 3, delta)
    restr = solve.a0(s, solve.domains(s, "RESTRICTED", dom), st, 3, delta)
    assert allsup["lower_bound"] == 2 and restr["lower_bound"] is None and restr["assignments"] == []
    assert restr["hall"] == {"objects": ["o00", "o01"], "neighbourhood_cells": dom["o00"]}
    ids, cells, C = solve.cost_matrix(s, solve.domains(s, "RESTRICTED", dom), st, optimistic=True)
    assert solve.check_hall(C, [ids.index(o) for o in restr["hall"]["objects"]],
                            [cells.index(c) for c in restr["hall"]["neighbourhood_cells"]])
    wide = solve.restricted_domain(s, st, ["o00", "o01"], 2, exclude=())
    assert solve.a0(s, solve.domains(s, "RESTRICTED", wide), st, 3, delta)["lower_bound"] == 2
    excl = solve.restricted_domain(s, st, ["o00", "o01"], 5, exclude=(1, 2))
    assert not {1, 2} & set(excl["o00"]) and not {9, 10, 30} & set(excl["o00"])


def test_reduction_guard_rejects_non_identical_discs(cfg):
    s, _ = toy(cfg, [9, 10])
    big = replace(s, objects=tuple(replace(o, radius_m=0.03) if o.id == "o00" else o for o in s.objects))
    with pytest.raises(solve.ReductionInvalid):
        solve.check_reduction(big, cfg["suite"]["margin_m"])
    solve.check_reduction(s, cfg["suite"]["margin_m"])
    assert cfg["suite"]["pitch_m"] > 2 * cfg["suite"]["obstacle_radius_m"] + cfg["suite"]["margin_m"]


def test_exhaustive_small_case_audit_of_a0_on_a_real_status_map(cfg):
    """A0 vs brute force over all injective maps on a 3-obstacle, 7-cell domain."""
    s, st = toy(cfg, [9, 10, 11], invalid={9, 11}, unresolved={13})
    allowed = [9, 10, 11, 12, 13, 14, 15]
    dom = {o: tuple(allowed) for o in ("o00", "o01", "o02")}
    t = solve.a0(s, dom, st, 50, cfg["suite"]["margin_m"])
    brute = []
    for p in itertools.permutations(allowed, 3):
        if all(st[c] == V for c in p):
            brute.append(sum(c != s.get(o).cell for o, c in zip(("o00", "o01", "o02"), p)))
    assert sorted(a["cost"] for a in t["assignments"]) == sorted(brute)[:len(t["assignments"])]
    assert len(t["assignments"]) == len(brute) and t["lower_bound"] == min(brute) == 2


def test_restoration_rejected_when_its_premises_fail(cfg):
    """A reference cell taken by another object (or itself action-blocked) breaks the
    lemma's witness: restoration must not be reported terminal-valid."""
    ref, _ = toy(cfg, [9, 30])
    o00 = replace(ref.get("o00"), xy_m=ref.lattice.center(10), cell=10)        # blocker: 9 -> 10
    o01 = replace(ref.get("o01"), xy_m=ref.lattice.center(9), cell=9)          # o01 now holds o00's reference cell
    taken = replace(ref, objects=tuple({"o00": o00, "o01": o01}.get(o.id, o) for o in ref.objects))
    _, st = toy(cfg, [9, 30], invalid={10})
    r = solve.restoration(taken, ref, st)
    assert r["direct_blockers"] == ["o00"] and not r["terminal_valid"]
    moved = replace(ref, objects=tuple(o00 if o.id == "o00" else o for o in ref.objects))
    assert solve.restoration(moved, ref, st)["terminal_valid"]                 # premises hold: valid
    _, st2 = toy(cfg, [9, 30], invalid={10, 9})
    assert not solve.restoration(moved, ref, st2)["terminal_valid"]            # reference cell action-blocked
