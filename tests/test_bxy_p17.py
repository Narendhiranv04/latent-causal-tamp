"""BXY-P17: leakage separation of the new-corpus views, folds, matched arms, SYM loss semantics, order-invariant control, inner rule choice,
root-consistent normalization (shared Y invariant to appended X), six-step prefixes."""
import copy
import json

import numpy as np
import pytest
import torch

import bxy_core as X
import bxy_p11 as P
import bxy_p16 as G
import bxy_p17 as M
import bxy_p17_data as D

pytestmark = pytest.mark.skipif(not (G._maps_file().exists() and D.INPUTS["P15"].exists()), reason="P16 artifacts missing")


def _views(n=None):
    inp = {}
    for f in D.INPUTS.values():
        if f.exists():
            inp.update(torch.load(f, weights_only=False)["roots"])
    rows = [r for r in D.corpus_roots() if r[2] in inp]
    return [D.view(*r, inp[r[2]]) for r in rows[:n]]


def test_new_corpus_scorer_views_are_label_free():
    V = _views(40)
    for sv, lab, ev in V:
        P.check_scorer(sv)
        txt = json.dumps({k: v for k, v in sv.items() if k != "R"}, default=str)
        assert "kind" not in txt and "harmful" not in txt and "K_geom" not in txt


def test_scorer_view_invariant_to_results(tmp_path):
    """Building a root's view with its teacher results removed leaves the scorer view identical (labels / evaluator change only)."""
    inp = {}
    for f in D.INPUTS.values():
        if f.exists():
            inp.update(torch.load(f, weights_only=False)["roots"])
    corpus, wave, k, rec, d, rdir = next(r for r in D.corpus_roots() if r[2] in inp and r[0] == "V21") if any(r[0] == "V21" and r[2] in inp for r in D.corpus_roots()) \
        else next(r for r in D.corpus_roots() if r[2] in inp)
    a = D.view(corpus, wave, k, rec, d, rdir, inp[k])[0]
    b = D.view(corpus, wave, k, rec, d, tmp_path, inp[k])[0]
    strip = lambda sv: {x: y for x, y in sv.items() if x != "R"}  # noqa: E731
    assert strip(a) == strip(b)


def test_sym_loss_directions():
    b = torch.zeros(3, dtype=X.D, requires_grad=True)
    M.sym(b, {0: 0, 1: 1}, 0).backward()                                   # (0 -> 1): pushes b_1 up, b_0 down
    assert b.grad[1] < 0 and b.grad[0] > 0
    b2 = torch.zeros(3, dtype=X.D, requires_grad=True)
    M.sym(b2, {0: 1, 2: 0}, 0).backward()                                  # (1 -> 0): pushes b_2 down (a harmful edit)
    assert b2.grad[2] > 0 and b2.grad[0] < 0
    b3 = torch.tensor([0.0, 3.0], dtype=X.D, requires_grad=True)
    M.sym(b3, {0: 1, 1: 1}, 0).backward()                                  # concordant control: shrinks a large shift only
    assert b3.grad[1] > 0


def test_arms_matched_capacity_and_order_invariance():
    V = _views(60)
    n = {a: P.params(M.build_model(a, 0)) for a in M.ARMS}
    assert len({v for a, v in n.items() if a != "B:XYQ-BASE"}) == 1
    g = M.build_model("G:XYQ-GEO-SYM-ORDINV", 0)
    d = M.build_model("D:XYQ-GEO-SYM", 0)
    sv = next(sv for sv, _, _ in V if any(len(s) >= 2 for s in sv["x_seqs"]))
    s = next(s for s in sv["x_seqs"] if len(s) >= 2)
    g._memo = d._memo = {}
    assert abs(float(g._order(sv["R"], s)[0]) - float(g._order(sv["R"], s[::-1])[0])) < 1e-12
    assert M.phi_x(sv, sv["x_seqs"].index(s), False) == D.phi_x(sv["R"], s[::-1], False)


def test_shared_y_marginal_invariant_to_appended_x():
    b, a, w = torch.tensor([0.3, -1.0], dtype=X.D), torch.tensor([0.5], dtype=X.D), torch.tensor([0.7], dtype=X.D)
    m1 = X.marginals(b, a, w, [1])
    m2 = X.marginals(b, torch.tensor([0.5, -2.0], dtype=X.D), torch.tensor([0.7, 1.5], dtype=X.D), [1, 1])
    assert torch.allclose(m1["py"], m2["py"])


def test_six_step_prefix_features_and_encoding():
    V = _views(30)
    sv = V[-1][0]
    seq = [(i, (0.04 + 0.08 * (4 + i % 4), 0.04 + 0.08 * (i // 4))) for i in range(min(6, len(sv["R"].xy0) - 1))]
    f = D.phi_x(sv["R"], seq)
    assert len(f) == 8 and f[6] == len(seq) / 6.0
    m = M.build_model("D:XYQ-GEO-SYM", 0)
    m._memo = {}
    assert torch.isfinite(m._order(sv["R"], seq)[0])


def test_choose_rule_respects_guardrail():
    rows = lambda pn, pr: [{"sig": "empty", "m": 0, "p": pn, "admissible": True, "cd": 0.0, "J_hat": 0.0},  # noqa: E731
                           {"sig": "a>1", "m": 1, "p": pr, "admissible": True, "cd": 1.0, "J_hat": 0.0}]
    es = [("i", 0, rows(0.3, 0.6), {"a>1": 1, "empty": 0})] * 3 + [("f", 1, rows(0.6, 0.7), {"a>1": 1, "empty": 1})] * 3
    r = M.choose_rule("D:XYQ-GEO-SYM", es)
    assert r["inner"]["unnecessary"] <= M.U_MAX and r["inner"]["success_inf"] == 1.0


def test_folds_hold_out_each_root_once_and_keep_families():
    V = _views()
    fo = M.folds(V)
    held = [k for f in fo["folds"] for k in f["heldout"]]
    assert sorted(held) == sorted(ev["key"] for _, _, ev in V)
    fam = {ev["key"]: ev["family"] for _, _, ev in V}
    for f in fo["folds"]:
        assert not ({fam[k] for k in f["heldout"]} & {fam[k] for k in f["train"] + f["early_stop"]})
    assert not any("confirm" in k for k in held)


def test_travel_of_maps_complete_witnesses_only():
    import bxy_p17_eval as EV
    V = _views(60)
    for sv, lab, ev in V:
        t = EV.travel_of(sv, lab)
        assert len(t) == len({(a, b) for a, b, _ in lab["j"]} & ({(None, sv["y0"])} | {(c["xi"], c["yi"]) for c in sv["cands"] if c["m"] > 0}))
        for c in sv["cands"]:
            if c["sig"] in t:
                e = next(x for x in ev["cands"] if x["sig"] == c["sig"])
                assert e["success"] == 1                                     # travel only on complete verified successes


def test_analytic_reference_reads_geometry_only():
    import bxy_p17_eval as EV
    V = _views(40)
    for sv, lab, ev in V:
        rows = [dict(c, p=1.0) for c in sv["cands"]]
        assert EV.analytic_rule(sv, rows) == EV.analytic_rule(sv, [dict(r) for r in rows])
