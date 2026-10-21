"""P5.1: D3-lite frozen construction, plan and checkpoint gate (static; no teacher calls)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config as cf  # noqa: E402
import d3lite as d3  # noqa: E402
import d3lite_run as dr  # noqa: E402
import geometry as ge  # noqa: E402
import operational_teacher as ot  # noqa: E402
import sector_cert  # noqa: E402
import zlayout as zl  # noqa: E402

CFG = cf.load_config(ROOT / "config.toml")
ROBOT = ge.make_robot(CFG)
POL = ot.load_policy(ROOT / "teacher_opneg.toml")


@pytest.fixture(autouse=True)
def zero_calls(monkeypatch):
    calls, _ = sector_cert.guard_and_count(monkeypatch.setattr)
    yield
    assert not any(calls.values())


@pytest.fixture(scope="module")
def built():
    roots, ledger = d3.construct(CFG, ROBOT, ROOT)
    return roots, ledger, d3.plan(CFG, ROBOT, POL, roots)


def test_plan_is_deterministic_capped_and_split_before_outcomes(built):
    roots, ledger, plan = built
    roots2, _ = d3.construct(CFG, ROBOT, ROOT)
    assert d3.plan(CFG, ROBOT, POL, roots2)["plan_hash"] == plan["plan_hash"]
    assert len(plan["queries"]) <= 96 and len(plan["units"]) <= 288 and len(roots) == 8
    assert [r["split"] for r in roots].count("train") == 4 and [r["split"] for r in roots].count("holdout") == 2
    for b in (1, 2):
        fam = sorted(r["family"] for r in roots if r["batch"] == b)
        assert fam == ["J1", "J1", "J2", "J2"] and {r["split"] for r in roots if r["batch"] == b} == {"train", "validation", "holdout"}
    assert sum(not x["accepted"] for x in ledger) == len(ledger) - 8                 # every rejection is logged
    for q in plan["queries"]:
        assert q["query"].count(":") == 2 and len([u for u in plan["units"] if u["query"] == q["query"]]) == 3


def test_reference_scene_never_enters_a_z_vector_and_layouts_are_v2(built):
    _, _, plan = built
    refs = {q["query"] for q in plan["queries"] if q["role"] == "reference"}
    for k, r in plan["roots"].items():
        if r["queries"]:
            for p in r["queries"]["pool"]:
                zl.verify(p["z_layout"])
                assert not refs & set(p["z_layout"]["query"].values()) and p["z_layout"]["active_count"] <= 8
                assert all(v.startswith(("seq:" + k + ":", "scene:" + k + ":")) for v in p["z_layout"]["query"].values())
    planned = {q["query"] for q in plan["queries"]}
    for r in plan["roots"].values():
        for p in (r["queries"] or {"pool": []})["pool"]:
            assert set(p["z_layout"]["query"].values()) <= planned                 # every active slot is a planned query


def _rec(q, st):
    seeds = {ot.VERIFIED: [{"terminal": "WITNESS", "clean": True}], ot.BUDGET: [{"terminal": "SEARCH_LIMIT_PLAN_FAILURES", "clean": True}] * 3,
             ot.UNKNOWN: []}
    d = ot.adjudicate_query({"kind": "X", "scope": "ASSIGNMENT"} if st == ot.CERTIFIED else None, seeds.get(st, []), POL)
    return {**d, "query": q}


def test_checkpoint_gate(built):
    _, _, plan = built
    b1 = [q for q in plan["queries"] if q["batch"] == 1]
    recs = {q["query"]: _rec(q, ot.BUDGET) for q in b1}
    for q in b1:
        if q["role"] in ("reference", "single", "order_BA"):
            recs[q["query"]] = _rec(q, ot.VERIFIED)
    g = dr.gate(plan, recs, 1)
    assert g["pass"] and g["decided_order_contrasts"] >= 1 and g["roots_with_multi_repair_pool"] >= 1
    many = {q: (_rec(r["query"], ot.UNKNOWN) if i % 3 == 0 else r) for i, (q, r) in enumerate(recs.items())}
    assert not dr.gate(plan, many, 1)["pass"]                                       # > 25 % undecided halts batch 2
    same = {q: _rec(r["query"], ot.VERIFIED) for q, r in recs.items()}
    assert dr.gate(plan, same, 1)["decided_order_contrasts"] == 0 and not dr.gate(plan, same, 1)["pass"]
