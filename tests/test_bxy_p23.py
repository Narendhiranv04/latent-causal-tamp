"""BXY-P23: P24 refuses without the user's approval; the successor locks reference the untouched P22 originals; the frozen-model append keeps
D / E / A and adds G with the declared pooled rules; scorer views and sealed predictions cannot see labels; the locked analysis runs on a
development dry run (structure only, not evidence) and its statistics behave."""
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

OUT = Path("runs/approach_b/bxy_p23_v1")
pytestmark = pytest.mark.skipif(not (OUT / "CONFIRM_ANALYSIS_P23_LOCK.json").exists(), reason="P23 artifacts missing")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def test_p24_refuses_without_explicit_approval(tmp_path, monkeypatch):
    import bxy_p24_confirm as C24
    if not (C24.OUT / "AUTHORIZATION_P24.json").exists():                 # before the user's P24 approval: nothing exists, every step refuses
        assert not C24.OUT.exists() and not any(Path("runs").glob("**/*bxyg34confirm*"))
        for fn in (C24.generate, C24.collect, C24.evaluate, C24.require_authorization):
            with pytest.raises(PermissionError):
                fn()
        with pytest.raises(PermissionError):
            C24.freeze()
    else:                                                                   # after approval the real steps are never called from a test
        assert json.loads((C24.OUT / "AUTHORIZATION_P24.json").read_text())["approved"] is True
    prop = json.loads((OUT / "AUTHORIZATION_P24_PROPOSED.json").read_text())
    assert prop["approved"] is False and prop["approved_by"] is None
    monkeypatch.setattr(C24, "OUT", tmp_path)
    (tmp_path / "AUTHORIZATION_P24.json").write_text(json.dumps(prop))
    with pytest.raises(PermissionError, match="explicit approval"):
        C24.require_authorization()
    stale = dict(prop, approved=True, approved_by="test", approval_text="x", locks_sha256={k: "0" * 64 for k in prop["locks_sha256"]})
    (tmp_path / "AUTHORIZATION_P24.json").write_text(json.dumps(stale))
    with pytest.raises(PermissionError, match="drift"):
        C24.require_authorization()


def test_locks_are_successors_of_untouched_p22_files():
    pl, an = (json.loads((OUT / f).read_text()) for f in ("CONFIRM_PLAN_P23_LOCK.json", "CONFIRM_ANALYSIS_P23_LOCK.json"))
    for x in (pl, an):
        assert sha(x["parent"]["file"]) == x["parent"]["sha256"]
    p22 = json.loads(Path(pl["parent"]["file"]).read_text())
    assert pl["slot_count"] == 440 == len({s["slot"] for s in pl["slots"]})
    assert pl["mix_counts"] == {k.replace("|K", "|K"): round(440 * f) for k, f in p22["mix"].items()}
    assert pl["namespace"] == "bxyg34confirm" and pl["construction_revision"] == __import__("bxy_p20_k34").REV34["k3"]
    assert sha(pl["p18_plan"]["path"]) == pl["p18_plan"]["sha256"]
    assert an["implementation"]["analysis_sha256"] == sha("bxy_p24_analysis.py") and an["implementation"]["engine_sha256"] == sha("bxy_p23_engine.py")
    assert an["frozen_models_sha256"] == pl["frozen_models_sha256"] == sha(OUT / "FROZEN_MODELS_P23_APPEND.json")
    assert an["hierarchy"]["authoritative_primary"].startswith("U_unconditional")


def test_frozen_append_keeps_p22_arms_and_adds_g_with_pooled_rules():
    import bxy_p18 as Z18
    import bxy_p21_eval as E2
    fz = json.loads((OUT / "FROZEN_MODELS_P23_APPEND.json").read_text())
    p22 = json.loads(Path(fz["parent"]["file"]).read_text())
    assert sha(fz["parent"]["file"]) == fz["parent"]["sha256"]
    for arm in p22["arms"]:
        assert sorted(m["rid"] for m in fz["arms"][arm]["members"]) == sorted(p22["arms"][arm]["runs"])
        assert {m["rid"]: m["checkpoint_sha256"] for m in fz["arms"][arm]["members"]} == {r: c["sha256"] for r, c in p22["arms"][arm]["checkpoints"].items()}
    g = fz["arms"]["G:XYQ-GEO-SYM-ORDINV"]
    assert len(g["members"]) == 15 and len({(m["rid"]) for m in g["members"]}) == 15
    C = E2.context()
    for arm, v in fz["arms"].items():
        assert Z18.pooled_rule(arm, C)["rule"] == v["rule"]


def _dev_root(w="k3", n=0):
    import torch
    import bxy_p17_data as DATA
    import bxy_p20_k34 as Z
    D = json.loads((Z.wdir(w) / "DESIGN.json").read_text())
    R = Z.roots_of(w)
    k = [k for k in D["root_order"] if R[k]["construction"].get("K_cert") == 4][n]
    inp = torch.load("runs/approach_b/bxy_p21_v1/INPUTS_K34.pt", weights_only=False)["roots"][k]
    return k, R[k], D, inp, DATA._results(Z.wdir(w) / "results" / k)


def test_scorer_view_and_sealed_predictions_are_label_blind():
    import bxy_p11 as P
    import bxy_p16_inputs as I
    import bxy_p20_k34 as Z
    import bxy_p24_confirm as C24
    k, rec, D, inp, res = _dev_root()
    assert res                                                              # this root has teacher labels on disk
    sv0, lab0, _ = C24.view("unused", k, rec, D, inp)                       # prediction-time view: no result is read
    sv1, lab1, _ = C24.view("unused", k, rec, D, inp, res)
    assert not lab0["obs_x"] and not lab0["obs_y"] and (lab1["obs_x"] or lab1["obs_y"])
    for f in ("cands", "x_seqs", "y_poses", "parent", "y0", "key"):
        assert sv0[f] == sv1[f]
    fz = C24.frozen_models()
    for arm in C24.ARMS:
        net = C24.load_member(arm, fz["arms"][arm]["members"][0])
        a, b = P.predict_all(net, sv0), P.predict_all(net, sv1)
        assert a == b
    mut = I.privileged_mutation(rec)
    assert I.key(mut) == I.key(rec)
    noisy = copy.deepcopy(rec)
    noisy["labels"], noisy["verified_K"], noisy["witness"] = {"original": {"y": 1}}, 0, {"fake": True}
    assert Z.root_design(k, noisy) == Z.root_design(k, rec)
    for c in sv0["cands"]:
        assert set(c) == set(P.CAND_KEYS)                                   # no kind / role / K / certificate reaches the scorer


def test_statistics_units():
    import bxy_p24_analysis as AN
    ks = [f"r{i}" for i in range(80)]
    fam = {k: k for k in ks}
    one, zero = {k: 1.0 for k in ks}, {k: 0.0 for k in ks}
    t = AN.boot(one, zero, fam)
    assert t["diff"] == 1.0 and t["p_two_sided"] == 0.0
    same = AN.boot(one, one, fam)
    assert same["diff"] == 0.0 and same["p_two_sided"] == 1.0
    rng = np.random.default_rng(1)
    noisy = {k: float(rng.random() < 0.55) for k in ks}
    T = AN.holm({"a": AN.boot(one, zero, fam), "b": AN.boot(noisy, zero, fam), "c": AN.boot(one, one, fam)})
    assert T["a"]["holm_reject"] and not T["c"]["holm_reject"] and T["a"]["holm_level"] == 0.05 / 3
    assert AN.label(T["a"], T["a"], {"diff": 0.0}) == "IMPROVES" and AN.label(T["c"], None, {"diff": 0.0}) == "NOT_ESTABLISHED"
    assert AN.label(T["a"], T["a"], {"diff": 0.2}) == "GUARDRAIL_FAILED"
    small = {k: float(i < 4) for i, k in enumerate(ks)}
    Ts = AN.holm({"s": AN.boot(small, zero, fam)})
    assert AN.label(Ts["s"], Ts["s"], {"diff": 0.0}) in ("POSITIVE_BELOW_THRESHOLD", "NOT_ESTABLISHED")
    w = AN.wilson(7, 7)
    assert 0.59 < w[0] < 0.65 and w[1] == 1.0


def test_locked_analysis_development_dry_run_structure():
    """Structure check on the K34 DEVELOPMENT roots with P21 out-of-fold seed-0 predictions standing in for the sealed ensembles (not evidence)."""
    import bxy_p20_k34 as Z
    import bxy_p21_eval as E2
    import bxy_p24_analysis as AN
    C = E2.context()
    fz = json.loads((OUT / "FROZEN_MODELS_P23_APPEND.json").read_text())
    R = {}
    for w in Z.WAVES:
        R.update(Z.roots_of(w))
    Rs = [{"key": k, "family": ev["family"], "sv": sv, "lab": lab, "ev": ev, "rec": R[k], "preds": {a: C["oof"][(a, 0)][k] for a in AN.ARMS}}
          for k, (sv, lab, ev) in C["by"].items() if ev["corpus"] == "K34" and all(k in C["oof"][(a, 0)] for a in AN.ARMS)]
    out = AN.evaluate(Rs, {a: fz["arms"][a]["rule"] for a in AN.ARMS})
    pops = out["populations"]
    assert pops["roots"] == len(Rs) == 86 and pops["INF"] + pops["FEA"] + pops["y0_unobserved"] == 86
    assert pops["REP34"] == 21
    assert out["order_concordance_level"]["G:XYQ-GEO-SYM-ORDINV"]["all_mean"] == 0.5          # order-invariant: exact ties
    labels = {"IMPROVES", "POSITIVE_BELOW_THRESHOLD", "GUARDRAIL_FAILED", "REVERSED", "NOT_ESTABLISHED"}
    assert all(v["label"] in labels for fam in ("primary", "secondary_K34", "order") for v in out[fam].values())
    assert out["strata_availability_conditioned"]["K4_certified"]["n"] == 7 and not out["strata_availability_conditioned"]["K4"]["inferential"]
    assert out["arms"]["NOOP"]["U"] == 0.0
    json.dumps(out)
