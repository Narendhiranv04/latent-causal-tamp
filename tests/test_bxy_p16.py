"""BXY-P16: access-closure geometry, V2.1 construction / catalogue properties, label-free input adapter, readiness gate."""
import copy
import json
import math

import numpy as np
import pytest

import bxy_f1 as F1
import bxy_p16 as G
import bxy_p16_inputs as I
import bxy_teacher as T

pytestmark = pytest.mark.skipif(not G._maps_file().exists(), reason="P16 access maps not computed")


def _roots():
    R = G.roots_of("wA")
    if not R:
        pytest.skip("wave wA not generated")
    return R


def test_union_model_matches_real_pick_screen():
    """open_after(pick_map) equals the real populated-scene screen for random multi-disc layouts around valid source cells."""
    rng = np.random.default_rng(0)
    import bd_2d
    valid = bd_2d.env()["valid"]
    agree = 0
    for _ in range(12):
        src = int(rng.choice(valid))
        obs = [int(c) for c in rng.choice([c for c in range(64) if c != src], 4, replace=False)]
        pred = set(G.open_after(G.access_map("pick", src), obs))
        real = set(G.screen("pick", G._scene([src] + obs)))
        agree += pred == real
    assert agree >= 11                                                    # union model; the generator re-checks every root with real screens


def test_k_geom_counts_removals_and_order():
    """Closing all pick candidates with discs whose removal order is forced raises K_geom; removing nothing gives K0 when open."""
    src, goal = 29, 47
    assert G.k_geom({}, [], src, goal)[0] == 0
    km = G.access_map("pick", src)
    ring = sorted({c for ks in km["kill"].values() for c in ks if G.math.dist(G._xy(c), G._xy(src)) < 0.09})
    mov = {f"b{i}": c for i, c in enumerate(ring) if c != goal}
    k, opts, forced = G.k_geom(mov, [], src, goal)
    assert k is None or k >= 1
    for _, _, rem, order in opts:
        assert set(order) == set(rem)


def test_wave_records_match_frozen_construction_intent():
    for k, r in _roots().items():
        C = r["construction"]
        assert r["q_ref"] == r["q0"] == r["scene"]["robot"]["q_rad"]
        assert r["generator"] == G.GEN and r["ids"]["namespace"] == "dev"
        if r["spec"]["mechanism"] in ("pick", "nested", "mixed"):
            assert C["S0_open"]["pick"] == 0
        if r["spec"]["mechanism"] in ("open", "near_closed"):
            assert C["S0_open"]["pick"] > 0 and C["S0_open"]["place"] > 0 and C["K_geom"] == 0
        assert C["K_geom"] == r["spec"]["K_intent"]


def test_catalogue_is_outcome_blind_and_deterministic():
    """The catalogue is a function of geometry + construction intent only: adding labels / results / scrambled privileged fields to the
    record does not change it, and candidate signatures are unique, F1-screened and within six relocations."""
    R = _roots()
    k = sorted(R)[-1]
    rec = R[k]
    base = G.candidates(rec)
    noisy = copy.deepcopy(rec)
    noisy["labels"] = {"original": {"y": 1}, "B": [{"sequence": [], "y": 1}]}
    noisy["verified_K"], noisy["teacher_results"] = 0, {"anything": 1}
    assert G.candidates(noisy) == base
    sigs = [G.bd.sig(s) for s, _ in base]
    assert len(sigs) == len(set(sigs)) and all(len(s) <= 6 for s, _ in base)
    for c in rec["catalogue_v21"]:
        assert c["f1_complete_ok"] == F1.screen(rec, [tuple(a) for a in c["seq"]])["complete_ok"]


def test_design_dedupes_shared_y_and_respects_caps():
    for k, r in _roots().items():
        Q = r["design_v21"]["queries"]
        assert len(Q) <= G.MAX_QUERIES and len(r["catalogue_v21"]) <= G.MAX_CANDS
        ys = {key for key, q in Q.items() if q["side"] == "y"}
        for key, q in Q.items():
            if q["side"] == "x":
                assert q["parent_y_key"] == T.ykey(k, r, [tuple(a) for a in q["seq"]])
        ends = {}
        for c in r["catalogue_v21"]:
            seq = [tuple(a) for a in c["seq"]]
            if c["f1_y_ok"]:
                ends.setdefault(json.dumps(sorted(G.bd.endpoint(r, seq).items())), set()).add(T.ykey(k, r, seq))
        assert all(len(v) == 1 for v in ends.values())                    # one Y key per endpoint, whatever the order
        assert T.ykey(k, r, []) in ys


def test_generate_refuses_unknown_wave():
    with pytest.raises(PermissionError):
        G.generate("confirm")


def test_readiness_logic(tmp_path, monkeypatch):
    monkeypatch.setattr(G, "OUT", tmp_path)
    (tmp_path / "wX").mkdir()
    row = lambda y0, vk, disc, harm: {"results": 3, "y0": y0, "verified_K": vk, "discordant": disc, "harmful": harm}  # noqa: E731
    rows = [row(0, 2, [1], []) for _ in range(12)] + [row(0, 1, [], []) for _ in range(8)] + [row(1, 0, [], [1]) for _ in range(40)]
    (tmp_path / "wX" / "SUMMARY.json").write_text(json.dumps({"rows": rows}))
    assert G.readiness(["wX"])["decision"] == "DATA_READY"
    (tmp_path / "wX" / "SUMMARY.json").write_text(json.dumps({"rows": rows[:59]}))
    assert G.readiness(["wX"])["decision"] == "DATA_READINESS_FAILED"


# ------------------------------------------------------------------ label-free adapter
def test_adapter_view_reads_only_scene_goal_q0_qref():
    R = _roots()
    rec = R[sorted(R)[0]]
    v = I.view(rec)
    assert set(v) == set(I.READ)
    assert I.key(rec) == I.key(I.privileged_mutation(rec))
    bad = copy.deepcopy(rec)
    bad["q_ref"] = [0.0, 0.0, 0.0]
    with pytest.raises(ValueError):
        I.view(bad)


def test_adapter_inputs_invariant_to_privileged_mutation_and_match_pmin():
    R = _roots()
    k = sorted(R)[0]
    a, b = I.inputs(k, R[k]), I.inputs(k, I.privileged_mutation(R[k]))
    assert all(np.array_equal(a["inputs"][x], b["inputs"][x]) for x in a["inputs"]) and a["ids"] == b["ids"]
    eq = I.p_min_equivalence(2)
    assert all(v["ids_equal"] and v["anchor_equal"] and max(v["max_abs"].values()) == 0.0 for v in eq.values())


def test_wave_a_construction_is_deterministic_after_revision():
    """The wave-B revision leaves wave-A construction reproducible: regenerating a frozen wA root gives the identical record (CPU aside)."""
    R = _roots()
    k = "2d-bxyg21dev-wA-s005" if "2d-bxyg21dev-wA-s005" in R else sorted(R)[0]
    r = R[k]
    n = G.construct(r["spec"], G.ids("wA", int(k[-3:]), r["spec"]))
    drop = lambda d: {a: ({x: y for x, y in b.items() if "cpu" not in x} if a == "construction" else b) for a, b in d.items()  # noqa: E731
                      if a not in ("catalogue_v21", "design_v21")}
    assert drop(n) == drop(r)
