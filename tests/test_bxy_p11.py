"""BXY-P11-TRAINING-PREREG tests: leakage-separated V2 views over the verified P-min sidecar, exact joint objective (vs bxy_core and brute
force, gradients), travel supervision, no-op handling, identity / dedup / splits, arms, selection rule, metrics, design freezing, and a
synthetic-only trainer smoke test. No real-data optimizer step, no teacher call, no test-split access."""
import copy
import itertools
import json
import random

import numpy as np
import pytest
import torch

import bxy_core as X
import bxy_data as bd

HAVE = (bd.DATA / "roots").exists() and __import__("pathlib").Path("runs/approach_b/bxy_pmin_v1/BXY_SIDECAR_V2_PMIN.json").exists()
pytestmark = pytest.mark.skipif(not HAVE, reason="local BD_GEN_V1 snapshot / P-min sidecar not present")
if HAVE:
    import bxy_p11 as P
    import bxy_p11_prereg as Q
    import bxy_v2 as V
    SC, D, R, I = P.load()
    VIEWS = P.build(sc=SC, D=D, R=R, I=I)
    BY = {v[0]["key"]: v for v in VIEWS}
    GROUP = next(v for v in VIEWS if any(len({u["x"] for u in g["members"]}) == 2 for g in v[2]["order_groups"]))


def micro(nS, nX, seed):
    g = torch.Generator().manual_seed(seed)
    b, a, w = (torch.randn(n, generator=g, dtype=torch.float64) * 2 for n in (nS, nX, nX))
    rng = random.Random(seed)
    parent = [rng.randrange(nS) for _ in range(nX)]
    ox = {q: rng.randint(0, 1) for q in range(nX) if rng.random() < 0.6}
    oy = {s: rng.randint(0, 1) for s in range(nS) if rng.random() < 0.5}
    return b, a, w, parent, ox, oy


# ------------------------------------------------------------------ exact objective
@pytest.mark.parametrize("seed", range(12))
def test_vectorized_evidence_equals_bxy_core_and_brute_force(seed):
    b, a, w, parent, ox, oy = micro(3, 4, seed)
    v = float(P.log_evidence(b, a, w, parent, ox, oy))
    assert v == pytest.approx(float(X.log_evidence(b, a, w, parent, oy, ox)), abs=1e-10)
    assert v == pytest.approx(X.brute_force(b, a, w, parent, oy, ox), abs=1e-10)


def test_evidence_gradients_exact():
    b, a, w, parent, ox, oy = micro(3, 5, 7)
    f = lambda b_, a_, w_: P.log_evidence(b_, a_, w_, parent, ox, oy)  # noqa: E731
    assert torch.autograd.gradcheck(f, tuple(t.clone().requires_grad_() for t in (b, a, w)), eps=1e-6, atol=1e-8)
    ref = [t.clone().requires_grad_() for t in (b, a, w)]
    X.log_evidence(*ref, parent, oy, ox).backward()
    mine = [t.clone().requires_grad_() for t in (b, a, w)]
    P.log_evidence(*mine, parent, ox, oy).backward()
    assert all(torch.allclose(x.grad, y.grad, atol=1e-12) for x, y in zip(ref, mine))


def test_missing_observations_marginalize_exactly():
    b, a, w, parent, ox, oy = micro(3, 4, 3)
    base = float(P.log_evidence(b, a, w, parent, ox, oy))
    b2, a2, w2 = torch.cat([b, torch.tensor([1.3], dtype=torch.float64)]), torch.cat([a, torch.tensor([-0.7, 2.0], dtype=torch.float64)]), torch.cat([w, torch.tensor([0.4, -1.1], dtype=torch.float64)])
    assert float(P.log_evidence(b2, a2, w2, parent + [3, 0], ox, oy)) == pytest.approx(base, abs=1e-12)   # unobserved X / Y sum to one
    assert float(P.log_evidence(b, a, w, parent, {}, {})) == pytest.approx(0.0, abs=1e-12)
    # an unobserved Y with observed children is summed over y, never set to 0
    lp = float(P.log_evidence(b[:1], a[:1], w[:1], [0], {0: 1}, {}))
    want = np.log(torch.sigmoid(b[0]).item() * torch.sigmoid(a[0] + w[0]).item() + torch.sigmoid(-b[0]).item() * torch.sigmoid(a[0]).item())
    assert lp == pytest.approx(want, abs=1e-12)


def test_four_state_microcase_and_psucc():
    b, a, w = (torch.tensor([v], dtype=torch.float64) for v in (0.4, -0.3, 1.2))
    tot = 0.0
    for x, y in itertools.product((0, 1), repeat=2):
        p = float(torch.exp(P.log_evidence(b, a, w, [0], {0: x}, {0: y})))
        tot += p
        if (x, y) == (1, 1):
            assert p == pytest.approx(float(torch.sigmoid(b) * torch.sigmoid(a + w)), abs=1e-12)
            assert p == pytest.approx(float(X.marginals(b, a, w, [0])["psucc"][0]), abs=1e-12)
    assert tot == pytest.approx(1.0, abs=1e-12)


def test_scene_marginal_invariant_to_appending_x_proposals():
    sv, lab, ev = VIEWS[0]
    m = P.build_model("XY-quadratic", 0)
    sv2 = dict(sv, x_seqs=sv["x_seqs"] + [[(0, (0.04, 0.04))]], parent=sv["parent"] + [sv["y0"]])
    with torch.no_grad():
        c1, c2 = m.coeffs(sv), m.coeffs(sv2)
        m1, m2 = X.marginals(c1["b"], c1["a"], c1["w"], sv["parent"]), X.marginals(c2["b"], c2["a"], c2["w"], sv2["parent"])
    assert torch.equal(m1["py"], m2["py"]) and torch.equal(m1["psucc"], m2["psucc"][:len(sv["parent"])])


# ------------------------------------------------------------------ evidence, identity, splits
def test_evidence_hashes_counts_and_audit():
    assert P.evidence()["counts"] == P.EXPECT
    a = Q.audit(VIEWS)
    assert a["splits"] == {"train": 176, "val": 21, "families_straddling_train_val": 0, "test_roots_in_design": 0, "test_roots_in_sidecar": 0,
                           "records_split_agree": True}
    assert a["dedup"]["x_rows"] == a["dedup"]["x_unique"] == 2222 and a["dedup"]["y_rows"] == a["dedup"]["y_unique"] == 1866
    assert a["travel"] == {"complete_witnesses": 1452, "noop_witnesses": 142, "on_failed_candidates": 0, "connector_in_every_complete_prefix": True}
    assert a["noop"] == {"x_variables_with_empty_prefix": 0, "y0_observed_roots": 197, "noop_travel_witnesses": 142}
    assert a["encoding"]["x_seq_length_mismatch"] == 0 and a["encoding"]["x_by_length"]["x_len6"] > 0     # six-step sequences survive
    assert a["order"] == {"order_groups": 551, "order_groups_discordant": 113, "order_failing_certified": 24, "order_failing_budget": 89}
    assert a["negatives"]["x_CERTIFIED_INFEASIBLE"] == 162 and a["negatives"]["y_UNKNOWN_PLANNER"] == 281


def test_no_test_root_and_split_guards():
    with pytest.raises(ValueError):
        P.build(("test",), sc=SC, D=D, R=R, I=I)
    I2 = copy.deepcopy(I)
    I2[D["root_order"][0]]["split"] = "test"
    with pytest.raises(RuntimeError):
        P.build(sc=SC, D=D, R=R, I=I2)
    assert {v[2]["split"] for v in VIEWS} == {"train", "val"} and len(P.build(("val",), sc=SC, D=D, R=R, I=I)) == 21


def test_folds_family_grouped_stratified_and_test_free():
    fo = P.folds(D, R)["folds"]
    allr = set(D["root_order"])
    held = [set(f["heldout"]) for f in fo]
    assert set().union(*held) == allr and sum(map(len, held)) == len(allr)
    fam = lambda ks: {R[k]["ids"]["parent_family_id"] for k in ks}  # noqa: E731
    for f in fo:
        tr, es, ho = set(f["train"]), set(f["early_stop"]), set(f["heldout"])
        assert not (tr & es or tr & ho or es & ho) and tr | es | ho == allr
        assert not (fam(tr) & fam(ho) or fam(es) & fam(ho) or fam(tr) & fam(es))
        assert 15 <= len(es) <= 30 and all(bd.split_of(R[k]) != "test" for k in tr | es | ho)
    inf = [sum(D["roots"][k]["stratum"] != "K0" for k in h) for h in held]
    assert max(inf) - min(inf) <= 2


def test_shared_y_across_orders_and_distinct_x():
    sv, lab, ev = GROUP
    g = next(g for g in ev["order_groups"] if len({u["x"] for u in g["members"]}) == 2)
    xs = [u["xi"] for u in g["members"]]
    assert len({sv["parent"][q] for q in xs}) == 1 and len({ev["x_keys"][q] for q in xs}) == len(xs)
    seqs = [D["roots"][sv["key"]]["queries"][ev["x_keys"][q]]["seq"] for q in xs]
    assert len({bd.sig(map(tuple, s)) for s in seqs}) == len(xs) and len({json.dumps(bd.endpoint(R[sv["key"]], [tuple(a) for a in s])) for s in seqs}) == 1
    assert sorted(sv["x_seqs"][xs[0]]) == sorted(sv["x_seqs"][xs[1]]) and sv["x_seqs"][xs[0]] != sv["x_seqs"][xs[1]]


def test_duplicate_rows_collapse_and_conflicts_raise():
    sc2 = copy.deepcopy(SC)
    r = next(x for x in sc2["x_queries"] if x["source"] == "P9_PILOT")
    sc2["x_queries"].append(copy.deepcopy(r))
    assert V.observations(sc2)[r["root"]]["x"] == V.observations(SC)[r["root"]]["x"]
    bad = copy.deepcopy(r)
    bad["y"] = 1 - bad["y"]
    sc2["x_queries"].append(bad)
    with pytest.raises(V.ConflictError):
        V.observations(sc2)


# ------------------------------------------------------------------ leakage
def test_scorer_view_whitelist():
    for sv, _, _ in VIEWS:
        P.check_scorer(sv)
        assert all(set(c) == set(P.CAND_KEYS) for c in sv["cands"])
    sv = dict(VIEWS[0][0])
    with pytest.raises(KeyError):
        P.check_scorer(sv | {"y_obs": {}})
    bad = dict(sv, cands=[dict(c, role="minimal") for c in sv["cands"]])
    with pytest.raises(KeyError):
        P.check_scorer(bad)
    with pytest.raises(KeyError):
        P.build_model("XY-quadratic", 0).coeffs(sv | {"travel": 1.0})


def test_hidden_outcomes_cannot_change_inputs_coefficients_probabilities_or_choices():
    sc2, R2 = Q.perturb(SC, R)
    B = P.build(sc=sc2, D=D, R=R2, I=I)
    assert all(Q.same_scorer(a[0], b[0]) for a, b in zip(VIEWS, B))
    assert all(a[1]["obs_y"] != b[1]["obs_y"] for a, b in zip(VIEWS, B)) and any(a[1]["j"] != b[1]["j"] for a, b in zip(VIEWS, B))
    for arm in P.ARMS:
        m = P.build_model(arm, 1)
        for a, b in zip(VIEWS[:3], B[:3]):
            with torch.no_grad():
                ca, cb = m.coeffs(a[0]), m.coeffs(b[0])
            assert all(torch.equal(ca[k], cb[k]) for k in ca)
            pa, pb = P.predict(m, a[0]), P.predict(m, b[0])
            assert pa == pb and P.choose(pa) == P.choose(pb)


def test_candidate_order_is_canonical_not_historical():
    k = GROUP[0]["key"]
    R2 = copy.deepcopy(R)
    R2[k]["labels"]["B"].reverse()
    a = P.build(sc=SC, D=D, R=R, I=I)
    b = P.build(sc=SC, D=D, R=R2, I=I)
    sa, sb = next(v[0] for v in a if v[0]["key"] == k), next(v[0] for v in b if v[0]["key"] == k)
    assert sa["cands"] == sb["cands"] and [c["sig"] for c in sa["cands"]] == [c["sig"] for c in sorted(sa["cands"], key=lambda c: (c["m"], c["sig"]))]


# ------------------------------------------------------------------ travel and no-op
def test_travel_labels_are_complete_replayed_witnesses_only():
    for sv, lab, ev in VIEWS:
        for xi, yi, j in lab["j"]:
            assert j > 0
            if xi is None:
                assert yi == sv["y0"] and lab["obs_y"][yi] == 1
            else:
                assert sv["parent"][xi] == yi and lab["obs_x"][xi] == 1 and lab["obs_y"][yi] == 1
    sc2 = copy.deepcopy(SC)
    p = next(p for p in sc2["paired"] if p["full_joint_success"] == 1)
    p["J_total"] += 0.5                                                              # stitched parts no longer add up
    with pytest.raises(RuntimeError):
        P.build(sc=sc2, D=D, R=R, I=I)
    sc3 = copy.deepcopy(SC)
    q = next(p for p in sc3["paired"] if p["full_joint_success"] == 0 and p["root"] == VIEWS[0][0]["key"])
    q["J_total"] = 123.0                                                             # a failed candidate's travel is never a label
    assert next(v for v in P.build(sc=sc3, D=D, R=R, I=I) if v[0]["key"] == q["root"])[1]["j"] == BY[q["root"]][1]["j"]


def test_travel_loss_is_pooled_huber_on_log1p_and_off_at_lambda_zero():
    m = P.build_model("XY-quadratic", 0)
    vs = VIEWS[:3]
    tot, rec = P.batch_loss(m, [v[0] for v in vs], [v[1] for v in vs], 0.3)
    jp, jo, nll = [], [], []
    for sv, lab, _ in vs:
        n, a, b = P.root_terms(m, sv, lab)
        nll.append(n)
        jp.append(a)
        jo.append(b)
    jp, jo = torch.cat(jp), torch.cat(jo)
    hub = torch.nn.functional.huber_loss(torch.log1p(jp), torch.log1p(jo), reduction="sum") / len(jp)
    assert float(tot.detach()) == pytest.approx(float((torch.stack(nll).mean() + 0.3 * hub).detach()), rel=1e-12)
    t0, _ = P.batch_loss(m, [v[0] for v in vs], [v[1] for v in vs], 0.0)
    assert float(t0.detach()) == pytest.approx(float(torch.stack(nll).mean().detach()), rel=1e-12)


def test_noop_x_is_one_by_definition_and_y0_is_learned():
    m = P.build_model("XY-quadratic", 0)
    for sv, lab, ev in VIEWS[:5]:
        assert sv["y_poses"][sv["y0"]] == {} and all(len(s) for s in sv["x_seqs"])
        rows = P.predict(m, sv)
        e = next(r for r in rows if r["m"] == 0)
        with torch.no_grad():
            c = m.coeffs(sv)
        assert e["admissible"] and e["px"] == 1.0 and e["p"] == pytest.approx(float(torch.sigmoid(c["b"][sv["y0"]])), abs=1e-12)
        assert e["J_hat"] > 0 and e["J_hat"] == pytest.approx(float(c["J0"]), abs=1e-12)          # nonzero target travel for the no-op
        assert ev["y0"] == lab["obs_y"][sv["y0"]] and lab["succ"][None] == ev["y0"]


def test_direct_success_events_and_loss():
    assert P.success_events({0: 1, 1: 0, 2: 1}, {0: 1, 1: 1, 2: 0}, [0, 1, 2], 0) == {0: 1, 1: 0, 2: 0, None: 1}
    assert P.success_events({0: 1}, {}, [1], 0) == {}                                     # undecided success is absent, never 0
    m = P.build_model("DIRECT", 0)
    sv, lab, _ = VIEWS[0]
    nll, _, _ = P.root_terms(m, sv, lab)
    with torch.no_grad():
        c = m.coeffs(sv)
    lg = torch.stack([c["b"][sv["y0"]] if q is None else c["a"][q] for q in lab["succ"]])
    y = torch.tensor([float(v) for v in lab["succ"].values()], dtype=torch.float64)
    assert float(nll.detach()) == pytest.approx(float(torch.nn.functional.binary_cross_entropy_with_logits(lg, y, reduction="sum")), rel=1e-12)


# ------------------------------------------------------------------ arms
def test_arm_structure_and_capacity_matching():
    n = {a: P.params(P.build_model(a, 0)) for a in P.ARMS}
    assert n["XY-quadratic"] == n["XY-uncoupled-SA"] == n["DIRECT"] == n["XY-quadratic-noJ"] > n["XY-uncoupled"]
    sv = VIEWS[1][0]
    with torch.no_grad():
        cq, cu, cs = (P.build_model(a, 0).coeffs(sv) for a in ("XY-quadratic", "XY-uncoupled", "XY-uncoupled-SA"))
    assert torch.count_nonzero(cu["w"]) == 0 and torch.count_nonzero(cs["w"]) == 0 and torch.count_nonzero(cq["w"]) == len(cq["w"])
    assert torch.equal(cq["b"], cu["b"]) and torch.equal(cq["a"], cu["a"]) and not torch.equal(cs["a"], cu["a"])   # SA: a += xs(g, v, c)


# ------------------------------------------------------------------ selection and metrics
def rows_(*spec):
    return [{"sig": s, "m": m, "cd": cd, "admissible": ad, "p": p, "J_hat": j, "xi": None, "yi": None} for s, m, cd, ad, p, j in spec]


def test_selection_rule():
    r = rows_(("empty", 0, 0, True, 0.2, 1.0), ("a>1", 1, 2, False, 0.99, 1.0), ("b>2", 1, 1, True, 0.6, 2.0), ("c>3", 2, 1, True, 0.62, 1.0))
    assert P.choose(r) == 2                   # C: b>2 .511+.1+.1 = .711 < c>3 .478+.2+.05 = .728                                                               # inadmissible p = .99 is never chosen
    assert P.choose(rows_(("empty", 0, 0, True, 0.55, 1.0), ("b>2", 1, 1, True, 0.99, 1.0))) == 0   # no-op gate
    assert P.choose(r, P.RULE | {"noop_gate": None, "eta": 0.95}) is None                         # abstain
    tie = rows_(("empty", 0, 0, True, 0.1, 1.0), ("z>2", 1, 1, True, 0.6, 1.0), ("a>2", 1, 1, True, 0.6, 1.0))
    for perm in itertools.permutations(tie):
        assert list(perm)[P.choose(list(perm))]["sig"] == "a>2"
    assert P.REFERENCES["SHORTEST_ADMISSIBLE"](r) == 2 and P.REFERENCES["NOOP"](r) == 0 and P.REFERENCES["DISPLACEMENT_RANK"](r) == 2


def test_metrics_root_averaging_bootstrap_and_verdict():
    items = [("a", 1, 0.9), ("a", 1, 0.9), ("a", 1, 0.9), ("b", 0, 0.5)]
    pm = P.prob_metrics(items)
    assert pm["logloss_root"] == pytest.approx((-np.log(0.9) + -np.log(0.5)) / 2) and pm["roots"] == 2 and pm["n"] == 4
    a, b = {k: 1.0 for k in "abcdef"}, {k: 0.5 for k in "abcdef"}
    bs = P.cluster_boot(a, b, B=200)
    assert bs["diff"] == 0.5 and bs["ci95"] == [0.5, 0.5] and P.cluster_boot(a, b, B=200) == bs
    good, flat = {"diff": -0.1, "ci95": [-0.2, -0.02]}, {"diff": 0.0, "ci95": [-0.03, 0.03]}
    assert P.verdict(good, good, flat, flat, True) == "BENEFICIAL"
    assert P.verdict(good, {"diff": 0.01, "ci95": [-0.05, 0.07]}, flat, flat, True) == "UNSUPPORTED"
    assert P.verdict(good, {"diff": -0.01, "ci95": [-0.05, 0.03]}, flat, flat, True) == "INCONCLUSIVE"
    assert P.verdict(good, good, {"diff": -0.1, "ci95": [-0.2, -0.01]}, flat, True) == "UNSUPPORTED"
    assert P.verdict(good, good, flat, flat, False) == "INCONCLUSIVE"


def test_order_metric_and_selection_rows_use_evaluator_only():
    sv, lab, ev = GROUP
    m = P.build_model("XY-quadratic", 0)
    pa = P.predict_all(m, sv)
    pr = pa["cands"]
    om = P.order_metric([pa], [ev])
    n = sum(1 for g in ev["order_groups"] for i, u in enumerate(g["members"]) for v in g["members"][i + 1:] if u["x"] != v["x"])
    assert om["certified"]["pairs"] + om["budget_policy"]["pairs"] == n
    i = P.choose(pr)
    row = P.selection_row(pr, ev, i, {})
    assert row["success"] == int(ev["cands"][i]["success"] == 1) and row["initially_feasible"] == ev["y0"]
    om2 = P.omission_metric([pa], [ev])
    nx = sum(1 for o in ev["omissions"] for t in o["omit"] if t["xi"] is not None and ev["obs_x"][o["xi"]] != ev["obs_x"][t["xi"]])
    assert om2["x"]["pairs"] == nx and set(om2) == {"x", "y", "success"}
    vf = P.verify_first(ev, sv)
    assert vf["success"] == int(any(c["success"] == 1 for c in ev["cands"]))


# ------------------------------------------------------------------ freezing and the synthetic trainer
def test_freeze_refuses_rewrite_and_guard_detects_drift(tmp_path, monkeypatch):
    monkeypatch.setattr(Q, "OUT", tmp_path)
    lock = Q.freeze({"x": 1, "budget": {"requested": {"aggregate_cpu_s": 1}}})
    assert not lock["authorized"] and Q.freeze({"x": 1, "budget": {"requested": {"aggregate_cpu_s": 1}}})["design_sha256"] == lock["design_sha256"]
    with pytest.raises(FileExistsError):
        Q.freeze({"x": 2})
    assert Q.assert_frozen(check_git=False)["design_sha256"] == lock["design_sha256"]
    real = Q.PM.sources
    monkeypatch.setattr(Q.PM, "sources", lambda entry: {**real(entry), "bxy_p11.py": "drift"})
    with pytest.raises(RuntimeError, match="source drift"):
        Q.assert_frozen(check_git=False)
    monkeypatch.setattr(Q.PM, "sources", real)
    (tmp_path / "TRAINING_DESIGN.json").write_text("{}")
    with pytest.raises(RuntimeError, match="design differs"):
        Q.assert_frozen(check_git=False)


def synthetic(seed):
    """A random synthetic root (NOT real data) with 2 Y nodes, 3 X queries and labels."""
    import abc_models as am
    rng = np.random.default_rng(seed)
    n = 4
    inp = {"object_xy": rng.uniform(0, 0.64, (n, 2)), "object_radius": np.full(n, 0.024), "is_active_target": np.eye(n)[n - 1],
           "is_obstacle": 1 - np.eye(n)[n - 1], "robot_q": rng.uniform(-2, 2, 3), "goal_xy": rng.uniform(0, 0.64, 2),
           "robot_fk_joints": rng.uniform(0, 0.6, (4, 2)), "visual": rng.normal(size=(n, 384))}
    d = [tuple(rng.uniform(0, 0.64, 2)) for _ in range(2)]
    sv = {"key": f"syn{seed}", "R": am.Root({"inputs": inp}), "y_poses": [{}, {0: d[0], 1: d[1]}], "y0": 0,
          "x_seqs": [[(0, d[0]), (1, d[1])], [(1, d[1]), (0, d[0])], [(0, d[0])]], "parent": [1, 1, 1],
          "cands": [{"sig": "empty", "m": 0, "cd": 0.0, "xi": None, "yi": 0, "admissible": True}]}
    lab = {"obs_x": {0: 1, 1: 0}, "obs_y": {0: int(seed % 2), 1: 1}, "succ": {0: 1, 1: 0, None: int(seed % 2)}, "j": [(0, 1, 3.0)] + ([(None, 0, 0.8)] if seed % 2 else [])}
    return sv, lab


@pytest.mark.parametrize("arm", ["XY-quadratic", "DIRECT"])
def test_trainer_smoke_on_synthetic_roots_is_deterministic(arm):
    tr, es = [synthetic(s) for s in range(4)], [synthetic(s) for s in (10, 11)]
    cfg = P.TRAIN | {"max_updates": 6, "eval_every": 2, "batch_roots": 3, "patience_evals": 5}
    m1, r1 = P.fit(arm, 0, tr, es, 0.3, cfg)
    m2, r2 = P.fit(arm, 0, tr, es, 0.3, cfg)
    assert r1["updates_run"] == 6 and r1["best_update"] in (2, 4, 6) and np.isfinite(r1["es_nll"])
    assert all(torch.equal(a, b) for a, b in zip(m1.state_dict().values(), m2.state_dict().values()))
    assert [h["total"] for h in r1["history"]] == [h["total"] for h in r2["history"]]
    assert not all(torch.equal(a, b) for a, b in zip(m1.state_dict().values(), P.build_model(arm, 0).state_dict().values()))
