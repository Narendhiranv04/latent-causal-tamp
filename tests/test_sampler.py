"""G4B exact sampler checks (G4B contract §6): independent enumeration, exact transition
matrices (normalization, detailed balance, stationarity), reference Hastings ratios,
Gibbs conditionals, self-transitions, B/C bounded-z gold standard and invariances,
mutation guards, seeded reproducibility and planner isolation. Synthetic fixtures only."""
import itertools
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config as cf  # noqa: E402
import g4b  # noqa: E402
import g4b_figures  # noqa: E402
import sampler as sp  # noqa: E402
import sequences as sq  # noqa: E402

TOL = g4b.TOL


def test_state_counts_are_exact_and_canonical():
    expect = lambda d, b: sum(sum(math.prod(len(d[o]) for o in c) for c in itertools.permutations(  # noqa: E731
        [o for o in d if d[o]], m)) for m in range(b + 1))
    for name, (d, cap, _, n) in g4b.SPACES.items():
        st = g4b.reference_states(d, cap)
        assert len(st) == n == expect(d, cap) and len(set(st)) == n, name
        assert all(sp.canonical_state(sp.Domain.make(d, cap), s) == s for s in st)
    a1 = g4b.reference_states(*g4b.SPACES["A1"][:2])
    assert [sum(len(s) == m for s in a1) for m in range(3)] == [1, 4, 8]
    a2 = g4b.reference_states(*g4b.SPACES["A2"][:2])
    assert [sum(len(s) == m for s in a2) for m in range(3)] == [1, 6, 22] and not any(o == "d" for s in a2 for o, _ in s)
    dom = sp.Domain.make(g4b.SPACES["A2"][0], 2)
    for bad in ([("a", 7), ("a", 7)], [("d", 1)], [("b", 9)], [("a", 7), ("b", 3), ("c", 5)], [("b", True)], [("b", 3.0)]):
        with pytest.raises((ValueError, TypeError)):
            sp.canonical_state(dom, bad)


@pytest.mark.parametrize("name", list(g4b.SPACES))
@pytest.mark.parametrize("probs", [sp.DEFAULT_PROBS, (0.4, 0.3, 0.2, 0.1)])
def test_exact_transition_matrix_is_reversible_and_stationary(name, probs):
    dom, E, d, cap, _ = g4b.space(name)
    st = g4b.reference_states(d, cap)
    c, pi, P = g4b.certify(dom, E, g4b.T0, st, probs)
    assert c["pass"] and c["max_error"] <= TOL, c
    assert c["row_sum_error"] <= TOL and c["kernel_row_sum_error"] <= TOL and c["stationarity_error"] <= TOL
    if name in ("A1", "A2"):
        assert all(v > 0 for v in c["offdiagonal_transitions"].values())       # every kernel actually moves


def test_hastings_ratios_match_independent_proposal_probabilities():
    dom, E, d, cap, _ = g4b.space("A2")                    # K = [1, 2, 3] and a K = 0 context object
    p = (0.4, 0.3, 0.2, 0.1)
    N = 3
    assert dom.eligible == ("a", "b", "c")
    for r in g4b.reference_states(d, cap):
        m = len(r)
        for q, r2 in sp.birth_moves(dom, r):
            new = next(o for o, _ in r2 if o not in dict(r))
            fwd = p[2] / ((N - m) * len(d[new]) * (m + 1))
            rev = p[3] / (m + 1)
            assert abs(p[2] * q - fwd) < 1e-15
            assert abs(math.exp(sp.log_hastings(dom, r, r2, "BIRTH", p)) - rev / fwd) < 1e-12
        for q, r2 in sp.death_moves(r):
            gone = next(o for o, _ in r if o not in dict(r2))
            fwd, rev = p[3] / m, p[2] / ((N - m + 1) * len(d[gone]) * m)
            assert abs(math.exp(sp.log_hastings(dom, r, r2, "DEATH", p)) - rev / fwd) < 1e-12


def test_gibbs_conditional_self_transitions_and_no_renormalization():
    dom, E, d, cap, _ = g4b.space("A2")
    r = (("c", 5), ("b", 3))
    row = sp.transition_row(dom, r, E, g4b.T0)
    for t in range(2):
        cands = [r[:t] + ((r[t][0], x),) + r[t + 1:] for x in d[r[t][0]]]
        w = np.exp([-E(c) for c in cands])
        assert all(abs(row["DESTINATION"].get(c, 0) - 0.25 / 2 * wi / w.sum()) < 1e-15 for c, wi in zip(cands, w)
                   if c != r) and r in cands                                  # current destination included
    assert all(abs(sum(row[k].values()) - 0.25) < 1e-15 for k in sp.KERNELS)
    empty = sp.transition_row(dom, (), E, g4b.T0)
    assert empty["DESTINATION"] == {(): 0.25} and empty["SWAP"] == {(): 0.25} and empty["DEATH"] == {(): 0.25}
    full = sp.transition_row(dom, (("a", 7), ("b", 3)), E, g4b.T0)
    assert full["BIRTH"] == {(("a", 7), ("b", 3)): 0.25}                        # m = b: birth is a self-transition
    dom1, E1 = g4b.space("A3_single_K1")[:2]
    k1 = sp.transition_row(dom1, (("a", 1),), E1, g4b.T0)
    assert k1["DESTINATION"] == {(("a", 1),): 0.25}
    with pytest.raises(ValueError):
        sp.check_probs((0.5, 0.5, 0.0, 0.1))
    with pytest.raises(ValueError):
        sp.check_probs((0.5, 0.3, 0.2, 0.0))                                   # birth without death is irreversible


def test_static_invalid_endpoint_stays_searchable():
    dom, E, d, cap, _ = g4b.space("A3_static_invalid")
    st = g4b.reference_states(d, cap)
    c, pi, P = g4b.certify(dom, E, g4b.T0, st)
    for bad in ((("a", 9), ("b", 9)), (("b", 9), ("a", 9))):
        i = st.index(bad)
        assert pi[i] > 0 and P[:, i].sum() - P[i, i] > 0 and P[i].sum() - P[i, i] > 0
    assert c["pass"]


def test_mutations_and_invariances_are_caught():
    g = g4b_figures.guards()
    for k in ("mutation_wrong_hastings_caught", "mutation_flipped_acceptance_caught",
              "mutation_missing_order_recompute_caught", "mutation_inactive_z_multiplicity_caught"):
        assert g[k] is True, k
    assert g["inactive_slot_insertion_max_dp"] <= TOL and g["inactive_metadata_permutation_max_dp"] <= TOL
    assert g["catalogue_change_recorded"] and g["catalogue_change_max_dp"] > 1e-3
    assert g["more_than_8_active_status"].startswith("NOT_RUN")
    assert g["cost_inside_vs_outside_max_diff"] <= TOL and g["cost_added_twice_detected"]
    assert g["temperature_mismatch_refused"] and g["inner_T_0.5_vs_gold_max_dp"] > 1e-3
    assert g["relabel_matrix_max_diff"] <= TOL and g["order_changes_energy"] and g["order_swap_same_assignment"]
    assert g["seed_reproducible"] and g["different_seed_differs"]


@pytest.mark.parametrize("kind", ["B", "C"])
def test_bounded_z_marginal_matches_the_joint_gold_standard(kind):
    c, pi, P, marg, st = g4b.certify_bc(kind)
    assert c["pass"] and c["max_error"] <= TOL and c["conditional_error"] <= TOL
    assert c["coupling_not_constant_offset"] > 0.05 and c["p_z0_range"] > 0.05      # z genuinely coupled to r
    assert c["max_active_z"] <= sp.MAX_ACTIVE_Z
    assert g4b.gradient_check(kind, (("a", 2), ("b", 3))) <= g4b_figures.GRAD_TOL
    assert g4b.gradient_check(kind, ()) <= g4b_figures.GRAD_TOL
    L0, L2 = g4b.layout_fn(()), g4b.layout_fn((("a", 1), ("b", 3)))
    act = lambda L: [s for s, a in zip(L.slots, L.active) if a]  # noqa: E731
    assert act(L0) == ["z0", "zS1"] and act(L2) == ["z0", "zS1", "zR", "zO0", "zO1"]
    assert all(set(z) == set(act(L0)) for z, _ in marg.conditional(()))               # inactive never reaches E
    assert sq.omit((("a", 1), ("b", 3)), [0]) == (("b", 3),)                           # omission keeps order


def test_seeded_step_implements_the_same_rules_as_the_matrix():
    dom, E, d, cap, _ = g4b.space("A2")
    r = (("c", 6), ("b", 4))
    row = {}
    for k, v in sp.transition_row(dom, r, E, g4b.T0).items():
        for s, x in v.items():
            row[s] = row.get(s, 0) + x
    rng, n, hits = np.random.default_rng(7), 40_000, {}
    for _ in range(n):
        s, _ = sp.step(dom, r, E, g4b.T0, rng)
        hits[s] = hits.get(s, 0) + 1
    assert set(hits) <= set(row)
    assert max(abs(hits.get(s, 0) / n - v) for s, v in row.items()) < 0.01           # supplementary Monte Carlo
    st = g4b.reference_states(d, cap)
    emp = g4b_figures._empirical(dom, E, st, 60_000, 3)
    assert 0.5 * np.abs(emp - g4b.reference_pi(st, E, g4b.T0)).sum() < 0.03          # supplementary only


def test_sampler_cannot_reach_planner_target_or_teacher_code():
    code = ("import sys; sys.path.insert(0, %r); import sampler, g4b; "
            "print(sorted(m for m in ('planner', 'skill', 'verify', 'evaluate', 'ordered', 'certificates', 'teacher', "
            "'g4d_run') if m in sys.modules))")
    out = subprocess.run([sys.executable, "-c", code % str(ROOT)], capture_output=True, text=True, check=True).stdout
    assert out.strip() == "[]"


def test_historical_config_hashes_unchanged():
    assert cf.config_hash(cf.load_config(ROOT / "config.toml")) == json.loads(
        (ROOT / "runs/g4a_evidence_audit/config.json").read_text())["config_hash"]
    assert cf.stable_hash(cf.load_config_v2(ROOT / "config_v2.toml")) == json.loads(
        (ROOT / "runs/g4d_evidence/final_plan.json").read_text())["config_v2_hash"]
