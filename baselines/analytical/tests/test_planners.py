"""Planner behaviour on the toy backend (real PhysBase + real planners): order sensitivity / transpositions, Y order independence,
restore after rejected branches, carried state, connector requirement, budgets / UNKNOWN, determinism, one legal committed answer."""
import copy
import json

import pytest

from baselines.analytical.contract import legality
from baselines.analytical.em4m import EM4M
from baselines.analytical.mosegman import MOSeGMan
from baselines.analytical.msmcts import MSMCTS
from toy import A, B, C, ToyPhys, toy_row

PLANNERS = [EM4M, MOSeGMan, MSMCTS]


def run(cls, seed=0, **kw):
    params = {k: kw.pop(k) for k in list(kw) if k in cls.DEFAULTS or k in ("start_check", "done_gate", "t_paths")}
    ph = ToyPhys(**kw)
    return cls(ph, seed, **params).run(), ph


@pytest.mark.parametrize("cls", PLANNERS)
def test_solves_k2_and_commits_one_legal_answer(cls):
    d, ph = run(cls)
    assert d.kind == "REPAIR" and d.termination == "SOLVED"
    assert legality(ph.inp, "2d", d.prefix) is None and {o for o, _ in d.prefix} == {A, B}
    assert ph.terminal(ph.reset()) == 0                                   # not a NOOP scene


@pytest.mark.parametrize("cls", PLANNERS)
def test_noop(cls):
    d, _ = run(cls, y_ok=lambda cells: True)
    assert d.kind == "NOOP" and d.prefix == []


@pytest.mark.parametrize("cls", PLANNERS)
def test_connector_required(cls):
    d, ph = run(cls, conn_bad={A, B, C})                                  # Y would hold, but no terminal connector ever succeeds
    assert d.kind == "ABSTAIN" and ph.n["y_calls"] == 1                   # only the start check reached Y (X = 0 skips Y)


@pytest.mark.parametrize("cls", PLANNERS)
def test_no_reference_plan_abstains(cls):
    d, ph = run(cls, sweeps=(), t_paths="planned")
    assert d.kind == "ABSTAIN" and ph.n["transition_calls"] == 0


@pytest.mark.parametrize("cls", PLANNERS)
@pytest.mark.parametrize("mode", ["planned", "linear", "both"])
def test_target_path_modes(cls, mode):
    d, ph = run(cls, t_paths=mode)
    assert d.kind == "REPAIR" and legality(ph.inp, "2d", d.prefix) is None
    assert (ph.n["ref_paths_verified"] > 0) == (mode != "linear")


def test_order_sensitivity_same_endpoint_different_x():
    ph = ToyPhys(conn_bad={B})
    s0 = ph.reset()
    ab = ph.step(ph.step(s0, A, 8), B, 9)
    ba = ph.step(ph.step(s0, B, 9), A, 8)
    assert ab.cells == ba.cells and ph.key(ab) != ph.key(ba)              # same endpoint, different carried arm state
    assert ph.terminal(ab) == 0 and ph.terminal(ba) == 1                 # different X


def test_y_order_independent():
    ph = ToyPhys()
    s0 = ph.reset()
    ab = ph.step(ph.step(s0, A, 8), B, 9)
    ba = ph.step(ph.step(s0, B, 9), A, 8)
    assert ph.terminal(ab) == ph.terminal(ba) == 1
    assert ph.n["y_calls"] == 1 and ph.n["y_cache_hits"] == 1 and ph.n["connector_calls"] == 2


def test_em4m_transposition_regression():
    """Two orders reach the same cells; only B-then-A leaves the arm where the connector works.  The legacy cells-only key keeps
    whichever order is generated first and drops the other; the physical key keeps both, so E-M4M always finds the feasible one."""
    only = {(A, d) for d in range(16) if d != 8} | {(B, d) for d in range(16) if d != 9}   # A -> 8 and B -> 9 are the only moves
    lost = 0
    for seed in range(12):
        good, _ = run(EM4M, seed, conn_bad={B}, fail=only)
        assert good.kind == "REPAIR" and good.prefix == [(B, 9), (A, 8)]
        legacy, _ = run(EM4M, seed, conn_bad={B}, fail=only, transposition="cells_legacy")
        lost += legacy.kind != "REPAIR"
    assert lost > 0


def test_restore_after_rejected_branch_and_carried_state():
    ph = ToyPhys(fail={(A, 5)}, unknown={(A, 6)})
    s0 = ph.reset()
    snap = copy.deepcopy(s0)
    assert ph.step(s0, A, 5) is None and ph.step(s0, A, 6) is None         # failed and UNKNOWN branches
    assert s0 == snap                                                      # the parent state is untouched
    s1 = ph.step(s0, A, 8)
    fresh = ToyPhys()
    t1 = fresh.step(fresh.reset(), A, 8)
    assert fresh.key(t1) == ph.key(s1)                                     # identical to a branch never preceded by rejections
    s2 = ph.step(s1, B, 9)
    assert ph.step_starts[-1] == s1.q_t != s0.q_t                           # 2nd move starts from the carried q, not q_ref
    assert s2.q_t != ph.inp["q_ref"] and ph.n["transition_unknown"] == 1 and ph.n["transition_failed"] == 1


def test_cache_and_accounting():
    ph = ToyPhys()
    s0 = ph.reset()
    for _ in range(3):
        ph.step(s0, A, 8)
    ph.terminal(s0), ph.terminal(s0)
    assert ph.n["transition_calls"] == 1 and ph.n["transition_cache_hits"] == 2
    assert ph.n["terminal_queries"] == 1 and ph.n["terminal_cache_hits"] == 1
    st = ph.stats()
    assert st["physical_calls"] == (ph.n["transition_calls"] + ph.n["connector_calls"] + ph.n["y_calls"] + ph.n["ref_plan_calls"]
                                    + ph.n["terminal_capped"])


@pytest.mark.parametrize("cls", PLANNERS)
def test_timeout_is_abstain_never_label(cls):
    d, ph = run(cls, burn_s=0.05, budget_s=0.12)
    assert d.kind == "ABSTAIN" and d.termination == "TIMEOUT"
    assert d.stats["phys"]["cpu_s"] < 0.12 + 0.1                          # the run stops at its budget (call interrupted)


def test_call_cap_unknown():
    ph = ToyPhys(burn_s=0.3, call_cap_s=0.05)
    s0 = ph.reset()
    assert ph.step(s0, A, 8) is None and ph.n["capped_calls"] == 1 and ph.n["transition_unknown"] == 1
    assert ph.terminal(s0) is None and ph.n["terminal_unknown"] == 1      # UNKNOWN, not 0
    assert ph.physical_calls() == 2                                       # interrupted calls are still counted


def test_wall_and_call_budgets():
    ph = ToyPhys(max_calls=1)
    d = EM4M(ph, 0).run()
    assert d.termination == "TIMEOUT" and "calls" in d.reason


@pytest.mark.parametrize("cls", PLANNERS)
def test_deterministic_replay(cls):
    runs = [run(cls, 7, fail={(A, 4), (B, 6)}) for _ in range(2)]
    a, b = (json.dumps([d.kind, d.prefix, d.stats["search"], {k: v for k, v in d.stats["phys"].items() if not k.endswith("_s")}])
            for d, _ in runs)
    assert a == b


@pytest.mark.parametrize("cls", PLANNERS)
def test_private_fields_do_not_change_output(cls):
    row = toy_row()
    dirty = {**row, "K_legacy": "2", "labels": {"X": [{"seq": [[1, 15]], "x": 1}]}, "masks": {"eval_task": True}}
    from baselines.analytical.contract import public_row
    outs = []
    for r in (row, public_row(dirty)):
        d = cls(ToyPhys(row=r), 3).run()
        outs.append((d.kind, d.prefix, d.stats["search"]))
    assert outs[0] == outs[1]


def test_msmcts_keeps_clearing_when_goal_refuted():
    """T's paths look clear after moving A and B, but the real task also needs C moved: the refuted goal child must not kill the node."""
    y = lambda cells: cells[A] not in (1, 2) and cells[B] not in (1, 2) and cells[C] != 10  # noqa: E731
    d, ph = run(MSMCTS, y_ok=y)
    assert d.kind == "REPAIR" and {o for o, _ in d.prefix} == {A, B, C} and d.stats["search"]["goal_refuted"] >= 1
