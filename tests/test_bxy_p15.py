"""BXY-P15: deterministic, outcome-blind catalogue and query design, reserved confirmatory namespace, disjoint ids, footprint geometry.
No planner or teacher call happens here (catalogue tests reuse a BD_GEN_V1 root's stored target-only sweep as the reference sweep)."""
import copy
from pathlib import Path

import pytest

import bxy_data as bd

HAVE = (bd.DATA / "roots").exists()
pytestmark = pytest.mark.skipif(not HAVE, reason="local BD_GEN_V1 snapshot not present")
if HAVE:
    import bd_2d
    import bxy_f1 as F1
    import bxy_p15 as G


def pseudo(rec):
    """A BD_GEN_V1 root in the V2 record shape (stored target-only sweep as reference); labels kept only to prove they are never read."""
    r = copy.deepcopy(rec)
    r["construction"] = {"reference_sweep": rec["empty_scene_T_swept"], "q_ref_footprint": sorted(G.footprint(rec["q0"]))}
    return r


@pytest.fixture(scope="module")
def roots():
    R = bd.roots()
    return [pseudo(R[k]) for k in sorted(R)[:25]]


def test_catalogue_is_deterministic_and_outcome_blind(roots):
    for r in roots:
        a = G.candidates(r)
        r2 = copy.deepcopy(r)
        r2["labels"] = {"original": {"y": 1 - r["labels"]["original"]["y"]}, "B": [], "D": []}   # flipped / removed outcomes
        r2["verified_K"], r2["intended_blockers"] = 99, []
        assert G.candidates(r2) == a and G.root_design("k", r2) == G.root_design("k", r)


def test_design_respects_caps_f1_and_classes(roots):
    for r in roots:
        d = G.root_design("k", r)
        assert len(d["catalogue"]) <= G.MAX_CANDS and len(d["queries"]) <= G.MAX_QUERIES
        assert sum(q["classes"] == ["y0"] for q in d["queries"].values()) == 1
        for q in d["queries"].values():
            f = F1.screen(r, [tuple(a) for a in q["seq"]])
            assert (f["x_ok"] if q["side"] == "x" else f["y_ok"])
        for c in d["catalogue"]:
            assert len({o for o, _ in c["seq"]}) == len(c["seq"]) and all(o in r["roles"] for o, _ in c["seq"])


def test_catalogue_covers_the_required_phenomena(roots):
    kinds = {c["kind"] for r in roots for c in G.root_design("k", r)["catalogue"]}
    assert {"single_park", "pair_park", "pair_park_reversed", "single_incorrect_placement"} <= kinds
    assert kinds & {"single_qref_destination", "occupied_destination_pair", "unnecessary_displacement"}


def test_confirmatory_namespace_is_reserved_and_ids_are_disjoint(tmp_path):
    with pytest.raises(PermissionError):
        G.generate("confirm", out=tmp_path)
    R = bd.roots()
    old_ids, old_fam = set(R), {r["ids"]["parent_family_id"] for r in R.values()}
    for ns in ("pilot", "confirm"):
        for slot, s in enumerate(G.specs(G.PILOT_K)):
            i = G.ids(ns, 0, slot, s)
            assert i["root_id"] not in old_ids and i["parent_family_id"] not in old_fam and i["root_id"].startswith(f"2d-{G.NS[ns]}-")
    p = {G.ids("pilot", 0, s, x)["construction_seed"] for s, x in enumerate(G.specs(G.PILOT_K))}
    c = {G.ids("confirm", 0, s, x)["construction_seed"] for s, x in enumerate(G.specs(G.PILOT_K))}
    assert not p & c


def test_specs_and_footprint():
    s = G.specs(G.PILOT_K)
    assert len(s) == 30 and sum(x["K_intent"] >= 2 for x in s) == 22 and s == G.specs(G.PILOT_K)
    assert all(x["K_intent"] + bd_2d.bc.N_DISTRACT[x["distractors"]][0] <= bd_2d.bc.MAX_MOVABLE for x in s)
    assert G.footprint((1.5708, 1.5708, 1.5708)) == set()                 # home pose S0 rests outside the 8 x 8 board
    f = G.footprint((0.7854, 1.5708, 1.5708))                              # S2 rests over the board's upper-left cells
    assert f and all(0 <= c < 64 for c in f)
    plan = G.confirm_plan()
    assert plan["roots"] >= 300 and sum(plan["K_intent"].values()) == plan["roots"] and plan["K_intent"][2] + plan["K_intent"][3] + plan["K_intent"][4] >= 200


def test_construct_is_deterministic_outcome_blind_and_teacher_compatible(tmp_path, monkeypatch):
    """construct() with the reference planner replaced by a stored target-only witness (no planner call): deterministic, exactly one
    reference call, BD_GEN_V1 record schema accepted by F1 / the teacher's key functions, roles / fixed ids consistent."""
    import bxy_teacher as T
    R = bd.roots()
    w = T.load_w(bd.DATA, R[sorted(R)[0]]["empty_scene_T_witness"])
    calls = []
    monkeypatch.setattr(bd_2d, "t_goal", lambda task, cache, cells, q: (calls.append(task["key"]) or ("VERIFIED", w, 0.0)))
    out = []
    for slot, s in enumerate(G.specs(G.PILOT_K)[:12]):
        i = G.ids("pilot", 0, slot, s)
        try:
            a, b = G.construct(s, i, tmp_path), G.construct(s, i, tmp_path)
        except bd_2d.Reject:
            continue
        strip = lambda r: {**r, "construction": {k: v for k, v in r["construction"].items() if not k.endswith("cpu_s")}}  # noqa: E731
        assert strip(a) == strip(b) and calls[-1].endswith(":ref") and calls[-2] == calls[-1]
        assert set(a["roles"]).isdisjoint(a["fixed_ids"]) and "t0" not in a["roles"] and len(a["intended_blockers"]) == s["K_intent"]
        assert T.ykey(i["root_id"], a, []).startswith("Y2:") and F1.screen(a, [])["y_ok"]
        d = G.root_design(i["root_id"], a)
        assert len(d["queries"]) <= G.MAX_QUERIES
        out.append(a)
    assert len(out) >= 6 and len(calls) == 2 * len(calls) // 2
