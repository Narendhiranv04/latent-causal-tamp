"""BXY-P28 dynamic scoring of universal-domain members by the frozen ensembles: exact equality with the legacy P20 design views,
chunk invariance, shared-Y identity across permutations (G exactly order-invariant), label-free inputs, domain-only candidates."""
import copy
import json
from pathlib import Path

import pytest

import bxy_fullscore as SC
import bxy_fullspace as S
import bxy_p24_confirm as C

W = Path("runs/approach_b/bxy_p20_v1/k3")
pytestmark = pytest.mark.skipif(not (W / "DESIGN.json").exists() or not SC.INPUTS[0].exists(), reason="development artifacts missing")
FIELDS = ("p", "px", "py", "J_hat")


@pytest.fixture(scope="module")
def env():
    import torch
    torch.set_num_threads(1)
    fz = C.frozen_models()
    return {"inp": SC.inputs(), "fz": fz, "nets": C.load_all(fz), "D": json.loads((W / "DESIGN.json").read_text())}


def _rec(k):
    return json.loads((W / "roots" / f"{k}.json").read_text())


@pytest.mark.parametrize("i", [0, 7])
def test_dynamic_view_equals_legacy_design_view(env, i):
    k = env["D"]["root_order"][i]
    rec, inp = _rec(k), env["inp"][k]
    assert inp["q_ref"] == rec["q0"] == rec["q_ref"]                                    # q_ref contract of the frozen tensors
    sv_old, _, _ = C.view(W, k, rec, env["D"], inp, {})
    seqs = [()] + [tuple((o, int(d)) for o, d in c["seq"]) for c in env["D"]["roots"][k]["catalogue"] if c["f1_complete_ok"]]
    sv_new = SC.view(k, rec, inp, seqs)
    for arm in C.ARMS:
        old = {r["sig"]: r for r in C.ensemble(arm, env["nets"][arm], sv_old)["cands"] if r["admissible"]}
        new = {r["sig"]: r for r in C.ensemble(arm, env["nets"][arm], sv_new)["cands"]}
        assert set(old) == set(new)
        for s in old:
            for f in FIELDS:
                assert (old[s].get(f) is None and new[s].get(f) is None) or abs(old[s][f] - new[s][f]) <= 1e-9, (arm, s, f)


def test_chunk_invariance_shared_y_and_order_sensitivity(env):
    k = env["D"]["root_order"][3]
    rec, inp = _rec(k), env["inp"][k]
    D = S.domain(rec)
    acts = list(S.actions(D, dict(D["cells0"]), set()))
    one = [(a,) for o in D["movable"][:3] for a in [x for x in acts if x[0] == o][::17][:2]]
    pairs = [(x[0], y[0]) for x in one for y in one if x[0][0] < y[0][0] and x[0][1] != y[0][1]][:6]
    assert len(pairs) >= 4
    seqs = [()] + one + pairs + [p[::-1] for p in pairs]
    for arm in C.ARMS:
        a = SC.Scorer(k, rec, inp, arm, env["nets"][arm], env["fz"]["arms"][arm]["rule"], chunk=400).score(seqs)
        b = SC.Scorer(k, rec, inp, arm, env["nets"][arm], env["fz"]["arms"][arm]["rule"], chunk=5).score(seqs)
        assert all(abs(a[s][f] - b[s][f]) <= 1e-12 for s in a for f in FIELDS if a[s].get(f) is not None)
        for p in pairs:
            u, v = a[S.xsig(p)], a[S.xsig(p[::-1])]
            if arm.startswith("A:"):
                continue                                                                 # DIRECT has no X / Y split
            assert u["py"] == v["py"]                                                    # one Y node per endpoint
            if arm.startswith("G:"):
                assert abs(u["px"] - v["px"]) <= 1e-12 and abs(u["p"] - v["p"]) <= 1e-12  # order-invariant control: equal to rounding
    e = SC.Scorer(k, rec, inp, C.ARMS[0], env["nets"][C.ARMS[0]], env["fz"]["arms"][C.ARMS[0]]["rule"]).score(seqs)
    assert max(abs(e[S.xsig(p)]["px"] - e[S.xsig(p[::-1])]["px"]) for p in pairs) > 0                 # D is order-aware


def test_scores_ignore_privileged_fields_and_refuse_non_members(env):
    k = env["D"]["root_order"][5]
    rec, inp = _rec(k), env["inp"][k]
    D = S.domain(rec)
    seqs = [()] + [(a,) for a in S.actions(D, dict(D["cells0"]), set())][:5]
    m = copy.deepcopy(rec)
    m["construction"], m["roles"] = {"options": [], "intended": []}, {o: "distractor" for o in rec["roles"]}
    m["catalogue_v21"], m["design_v21"], m["spec"] = [], {}, {}
    arm = C.ARMS[1]
    a = SC.Scorer(k, rec, inp, arm, env["nets"][arm], env["fz"]["arms"][arm]["rule"]).score(seqs)
    b = SC.Scorer(k, m, inp, arm, env["nets"][arm], env["fz"]["arms"][arm]["rule"]).score(seqs)
    assert a == b
    with pytest.raises(ValueError):
        SC.view(k, rec, inp, [(("t0", 5),)])
    sv = SC.view(k, rec, inp, seqs)
    assert "R" in sv and all(set(c) == {"admissible", "cd", "m", "sig", "xi", "yi"} for c in sv["cands"])


def test_cost_gate_and_length_penalty():
    rule = {"noop_gate": 0.5, "alpha": 0.3, "beta": 0.0, "gamma": 0.0}
    assert SC.cost({"m": 0, "p": 0.6, "cd": 0.0}, rule) == SC.GATE_COST
    assert SC.cost({"m": 0, "p": 0.4, "cd": 0.0}, rule) == pytest.approx(-__import__("math").log(0.4))
    assert SC.cost({"m": 2, "p": 0.5, "cd": 3.0, "J_hat": 9.0}, rule) == pytest.approx(-__import__("math").log(0.5) + 0.6)
