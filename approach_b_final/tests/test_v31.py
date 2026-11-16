"""V3.1 correctness tests: full-candidate retention / rule tuning (V3.1-B) and the matched goal-conditioning ablation (V3.1-A).  CPU."""
import json, os, sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import construct as CO  # noqa: E402
import evaluate as EV  # noqa: E402
import placement as PL  # noqa: E402
from test_v3 import INP, FakeSampler, FakeScorer, _row2d  # noqa: E402

V3_RULE = {"noop_gate": 0.5, "eta": 0.3, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}


def _root():
    import search as S
    row = {"root_id": "toy", "split": "val", "K_legacy": "2", "inputs": {**INP, "cell_xy": {str(c): [0.08 * (c % 3), 0.08 * (c // 3)] for c in range(9)}}}
    return S.Root(row, "2d")


# ------------------------------------------------------------------------------------------------ V3.1-B full candidate pool
def test_full_store_count_reproduction_and_parity_with_compact_store():
    full = CO.run_root(_root(), FakeSampler(), FakeScorer(), 2, 4096, V3_RULE, 0, store="all")
    comp = CO.run_root(_root(), FakeSampler(), FakeScorer(), 2, 4096, V3_RULE, 0, store_top=3)
    assert full["stored"] == "all" and full["store_mode"] == "full_precision_all"
    assert len(full["cands"]) == full["candidate_budget"]["n_scored"] + 1                    # every scored sequence + the independent no-op
    assert full["cands"][0]["seq"] == [] and all(c["seq"] for c in full["cands"][1:])
    assert EV.select(full["cands"], V3_RULE) == full["selected_ordered_seq"]                  # stored terms reproduce the decision (alpha=beta=gamma=0)
    assert full["selected_ordered_seq"] == comp["selected_ordered_seq"]                        # logging change does not alter the decision
    assert {json.dumps(c["seq"]) for c in comp["cands"]} <= {json.dumps(c["seq"]) for c in full["cands"]}   # same candidates / RNG
    assert len({c["eid"] for c in full["cands"]}) == len(full["endpoints"])
    for c in full["cands"]:
        assert full["endpoints"][c["eid"]] == sorted(map(list, c["seq"]))


def test_full_list_tuning_selects_candidate_omitted_by_top2048():
    noop = {"seq": [], "p11": 0.1, "J": 0.0, "m": 0, "D": 0.0}
    hi = [{"seq": [[0, i]], "p11": 0.5 + 0.4 * i / 2500, "J": 0.0, "m": 1, "D": 10.0} for i in range(2500)]
    lo = {"seq": [[1, 7]], "p11": 0.31, "J": 0.0, "m": 1, "D": 0.0}
    full = [noop] + hi + [lo]
    top = [noop] + sorted(full[1:], key=lambda c: -c["p11"])[:2048]
    rule = {"noop_gate": 0.5, "eta": 0.3, "alpha": 0.0, "beta": 1.0, "gamma": 0.0}
    assert EV.select(full, rule) == [[1, 7]]                                                  # cheap, admissible, outside the top 2,048
    assert EV.select(top, rule) != [[1, 7]]
    assert EV.select(full, V3_RULE) == EV.select(top, V3_RULE)                                # the probability-only rule is unaffected


def test_tuning_refuses_truncated_pools(tmp_path):
    recs = [{"root_id": "a", "stored": "all"}, {"root_id": "b", "stored": "noop+top2048_by_p11+selected"}]
    with pytest.raises(SystemExit):
        CO.require_full(recs, "x", allow_truncated=False)
    CO.require_full(recs, "x", allow_truncated=True)
    CO.require_full(recs[:1], "x", allow_truncated=False)


@pytest.mark.skipif(not (CO.ABF / "snapshot/abf_9de85710c2a7103f/data2d.jsonl").exists(), reason="needs the base snapshot")
def test_unresolved_selections_never_count_as_failures(tmp_path):
    row = next(r for r in map(json.loads, open(CO.ABF / "snapshot/abf_9de85710c2a7103f/data2d.jsonl"))
               if r["split"] == "val" and r["masks"]["eval_task"])
    A, Bq = [[0, 60]], [[1, 61]]
    rec = {"root_id": row["root_id"], "stored": "all", "cands": [{"seq": [], "p11": 0.1, "J": 0.0, "m": 0, "D": 0.0},
                                                                {"seq": A, "p11": 0.9, "J": 0.0, "m": 1, "D": 5.0},
                                                                {"seq": Bq, "p11": 0.5, "J": 0.0, "m": 1, "D": 0.0}]}
    (tmp_path / "r.jsonl").write_text(json.dumps(rec) + "\n")
    grid = [{"noop_gate": 0.5, "eta": 0.3, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}, {"noop_gate": 0.5, "eta": 0.3, "alpha": 0.0, "beta": 1.0, "gamma": 0.0}]
    (tmp_path / "g.json").write_text(json.dumps(grid))
    (tmp_path / "v.jsonl").write_text(json.dumps({"root": row["root_id"], "results": [{"seq": A, "x": {"x": 1}, "y": {"y": 1}}]}) + "\n")
    CO.tune("2D", str(tmp_path / "r.jsonl"), str(tmp_path / "g.json"), [str(tmp_path / "v.jsonl")], str(tmp_path / "t.json"))
    t = json.loads((tmp_path / "t.json").read_text())
    assert t["best_rule"] == grid[0] and t["unresolved_rules"] == 1
    assert [x["status"] for x in t["table"]] == ["resolved", "UNRESOLVED"] and t["table"][1]["objective"] is None


# ------------------------------------------------------------------------------------------------ V3.1-A matched goal ablation
def _goal_idx(dom="2d"):
    R, C = PL.GRID[dom]
    return lambda g: {g, 2 * R * C, 2 * R * C + 1, *(2 * R * C + 4 + j for j in PL.CTX_GOAL[dom])}


def test_nogoal_changes_only_goal_fields_and_is_goal_invariant():
    r = _row2d(goal=60)
    full = PL.task_features("2d", r["inputs"], r["inputs"]["cells0"], 0, True)
    nog = PL.task_features("2d", r["inputs"], r["inputs"]["cells0"], 0, "nogoal")
    diff = set(np.nonzero(full != nog)[0].tolist())
    assert diff and diff <= _goal_idx()(60)                                                   # only goal one-hot / goal offset / ctx goal xy
    r2 = _row2d(goal=5)
    r2["inputs"]["ctx"] = list(r["inputs"]["ctx"])
    r2["inputs"]["ctx"][6:8] = [0.9, 0.9]                                                     # different goal everywhere it appears
    assert np.array_equal(nog, PL.task_features("2d", r2["inputs"], r2["inputs"]["cells0"], 0, "nogoal"))
    assert nog[-1] == 1.0 and nog[64 + r["inputs"]["cells0"][3]] == 1.0                      # task_on and target one-hot kept
    assert not PL.task_features("2d", r["inputs"], r["inputs"]["cells0"], 0, False).any()     # entire task-context ablation = zeros
    with pytest.raises(ValueError):
        PL.task_features("2d", r["inputs"], r["inputs"]["cells0"], 0, "bogus")


def test_matched_variants_differ_only_in_task_input():
    base = PL.VARIANTS["q2init_all"]
    for v in ("q2init_all_nogoal", "q2init_all_notask"):
        other = {k: x for k, x in PL.VARIANTS[v].items() if k != "task"}
        assert other == {k: x for k, x in base.items() if k != "task"}                        # same init, assignments, Q2 aux
    assert (PL.VARIANTS["q2init_all"]["task"], PL.VARIANTS["q2init_all_nogoal"]["task"], PL.VARIANTS["q2init_all_notask"]["task"]) == (True, "nogoal", False)
    n = lambda: sum(p.numel() for p in PL.TaskCVAE(8, 8, PL.task_dim("2d")).parameters())  # noqa: E731  (same constructor for every variant)
    assert n() == n()


def test_repair_supervision_identical_across_task_modes(tmp_path):
    import itertools as it
    A = [[0, 40], [1, 41]]
    X = [{"seq": list(map(list, p)), "x": 1, "kind": "K"} for p in it.permutations(A)] + [{"seq": [[0, 44], [2, 45]], "x": 1, "kind": "K"}]
    Y = [{"edit": sorted(A), "y": 1}, {"edit": [[0, 44], [2, 45]], "y": 1}]
    with open(tmp_path / "data2d.jsonl", "w") as f:
        f.write(json.dumps(_row2d(labels={"X": X, "Y": Y})) + "\n")
    d = {m: PL.repair_data("2d", tmp_path, "train", "all", m, device="cpu") for m in (True, "nogoal", False)}
    N = 64
    for m in ("nogoal", False):
        for k in ("obj", "mask", "legal", "dest", "w"):
            assert (d[m][k] == d[True][k]).all(), k                                            # identical targets, weights and scene inputs
        assert d[m]["roots"] == d[True]["roots"]
        assert (d[m]["occx"][:, :N] == d[True]["occx"][:, :N]).all()                            # only the task block differs
