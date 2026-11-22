"""P6A public order composition: exactness of the (set, last w-1) merge vs exhaustive permutations, budget monotonicity, window
semantics, legality / determinism, public-only imports.  Mock scorer (no GPU).   python -m pytest tests/test_p6_order.py -q"""
import itertools, json, random, sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import p6_order as P  # noqa: E402


class MockM:
    """px depends on the hypothetical scene (SET of done moves) and the ordered window, like the frozen head; records every request."""
    def __init__(s, seed=0):
        s.seed, s.log = seed, []

    def score(s, hr, seqs):
        s.log += [(hr, q) for q in seqs]
        return [{"px": 0.02 + 0.96 * P._u("M", s.seed, tuple(sorted(hr)), q)} for q in seqs]


def mk(w_mode="W3", seed=0):
    M = MockM(seed)
    return M, P.Scorer(M, {"root_id": f"r{seed}"}, w_mode, mk_hr=lambda base: base)


def acts(m, seed=0):
    rng = random.Random(seed)
    return [(o, 40 + o) for o in rng.sample(range(20), m)]


@pytest.mark.parametrize("mode", ["W1", "W2", "W3"])
@pytest.mark.parametrize("m", [2, 3, 4, 5, 6, 7])
def test_wide_beam_is_exact(mode, m):
    for seed in range(4):
        _, sc = mk(mode, seed); A = acts(m, seed)
        top, _ = P.beam(sc, A, B=10 ** 6)
        c, perm = P.exhaustive(sc, A)
        assert abs(top[0]["C"] - c) < 1e-9 and [tuple(a) for a in top[0]["order"]] == list(perm)


def test_budget_monotone_and_greedy():
    for seed in range(10):
        _, sc = mk("W3", seed); A = acts(7, seed)
        best = [P.beam(sc, A, B)[0][0]["C"] for B in (1, 4, 16, 64)]
        assert all(best[i + 1] <= best[i] + 1e-12 for i in range(3))


def test_window_semantics():
    M, sc = mk("W3", 1); o = [(1, 41), (2, 42), (3, 43), (4, 44)]
    sc.steps(o)
    assert M.log == [((), ((1, 41),)), ((), ((1, 41), (2, 42))), ((), ((1, 41), (2, 42), (3, 43))), (((1, 41),), ((2, 42), (3, 43), (4, 44)))]
    M, sc = mk("W1", 1); sc.steps(o)
    assert M.log[-1] == (((1, 41), (2, 42), (3, 43)), ((4, 44),))      # W1: single move in the scene after ALL previous moves


def test_history_kept_when_last_moves_differ():
    """Two prefixes with the same done SET but different last-2 order are distinct states (future windows differ); identical keys merge."""
    _, sc = mk("W3", 2); A = acts(5, 2)
    top, st = P.beam(sc, A, B=10 ** 6)
    assert st["merged"] > 0
    full = 0
    for k in range(1, 6):                                       # #keys at depth k = C(5,k) * (#ordered last-min(2,k) tuples)
        full += len(list(itertools.combinations(range(5), k))) * (k if k == 1 else k * (k - 1))
    assert st["expanded"] <= sum(len(list(itertools.permutations(range(5), k))) for k in range(1, 6)) and full > 0


def test_outputs_legal_permutations_and_deterministic():
    _, sc = mk("W3", 3); A = acts(8, 3)
    a = P.beam(sc, A, 16); b = P.beam(mk("W3", 3)[1], A, 16)
    assert a == b
    for t in a[0]:
        assert sorted(map(tuple, t["order"])) == sorted(A) and len({o for o, _ in t["order"]}) == 8


def test_controls_are_permutations_and_seeded():
    row = {"root_id": "x", "inputs": {"cell_xy": {str(c): [0.04 + 0.08 * (c % 8), 0.04 + 0.08 * (c // 8)] for c in range(64)},
                                      "cells0": list(range(10)), "base": [-0.14, 0.32]}}
    A = [(i, 50 + i) for i in range(1, 7)]
    c1, c2 = P.controls(row, A, A[::-1]), P.controls(row, A, A[::-1])
    assert c1 == c2 and c1["ORIG"] == A[::-1]
    for o in c1.values():
        assert sorted(o) == sorted(A)


def test_randscore_is_seeded_and_model_free():
    M, sc = mk("RANDSCORE", 4); A = acts(5, 4)
    a = P.beam(sc, A, 4)[0]; assert M.log == [] and a == P.beam(mk("RANDSCORE", 4)[1], A, 4)[0]


def code_tokens(path):
    """Imports, names, attributes and string constants of a module, EXCLUDING docstrings (which describe what is never read)."""
    import ast
    t = ast.parse(Path(path).read_text()); docs = set()
    for n in ast.walk(t):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body and isinstance(n.body[0], ast.Expr) \
                and isinstance(getattr(n.body[0], "value", None), ast.Constant):
            docs.add(id(n.body[0].value))
    out = []
    for n in ast.walk(t):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs:
            out.append(n.value)
        elif isinstance(n, ast.Name):
            out.append(n.id)
        elif isinstance(n, ast.Attribute):
            out.append(n.attr)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            out += [a.name for a in n.names] + ([n.module] if getattr(n, "module", None) else [])
    return " ".join(out)


def test_public_module_has_no_privileged_inputs():
    src = code_tokens(HERE / "p6_order.py")
    for bad in ("p5_order_audit", "p5b_physical", "dev_eval", "MINK", "QCLEAR", "Static", "dev_private", "dev_records", "witness", "verify",
                "teacher", "K_certified", "P5B", "q23", "e3c632"):
        assert bad not in src, bad


def test_stratified_auroc_and_depth_labels(tmp_path):
    import p6_eval as E
    assert E.strat_auroc([(0, 1, 0.9), (0, 0, 0.1), (1, 1, 0.2), (1, 0, 0.8)]) == (0.5, 2)   # pairs only within the same step index
    assert E.strat_auroc([(0, 1, 0.9), (0, 0, 0.1), (1, 0, 0.95)]) == (1.0, 1)
    v = tmp_path / "v.jsonl"; b = tmp_path / "b.jsonl"
    v.write_text(json.dumps({"root_id": "r", "seq": [[1, 2], [3, 4], [5, 6]], "x_phase": "relocation:1", "x_status": "UNKNOWN_PLANNER"}) + "\n" +
                 json.dumps({"root_id": "r", "seq": [[3, 4], [1, 2], [5, 6]], "x_phase": None, "x_status": "VERIFIED"}) + "\n")
    b.write_text(json.dumps({"root_id": "r", "seq": [[5, 6], [3, 4], [1, 2]], "m": 3, "failed_step": 0,
                             "X": {"evidence": "P5B_NEW_TEACHER_CALL", "teacher_status": "UNKNOWN_PLANNER"}}) + "\n")
    L = E.physical_labels(v, b)
    assert L[("r", "[[1, 2], [3, 4], [5, 6]]")] == (1, "UNKNOWN_PLANNER", 3) and L[("r", "[[3, 4], [1, 2], [5, 6]]")][0] == 3
    assert L[("r", "[[5, 6], [3, 4], [1, 2]]")] == (0, "UNKNOWN_PLANNER", 3)            # status kept verbatim: UNKNOWN is never a negative


def test_p6b_proposal_never_spends_on_untested_orig(tmp_path):
    import p6_eval as E
    o = tmp_path / "o"; o.mkdir(); rep = tmp_path / "rep"; rep.mkdir()
    arm = lambda seq: {"top": [{"order": seq}]}  # noqa: E731
    (o / "p6_method.jsonl").write_text(json.dumps({"root_id": "r", "rank_public": 0, "m": 2, "endpoint_signature": "[[1, 2], [3, 4]]",
        "arms": {"W3_B16": arm([[3, 4], [1, 2]]), "CLUTTER_LOW_FIRST": arm([[3, 4], [1, 2]]), "ORIG": arm([[1, 2], [3, 4]])}}) + "\n")
    v = tmp_path / "v.jsonl"; v.write_text(json.dumps({"root_id": "r", "seq": [[9, 9]], "y": 0, "y_status": "UNKNOWN_PLANNER"}) + "\n")
    E.schedule(o, v, rep)
    S = json.loads((rep / "P6B_PROPOSED_SCHEDULE.json").read_text())
    assert [q["arm"] for q in S["queue"]] == ["W3_B16", "Y_ENDPOINT"] and S["new_calls"] == 2 and S["caps"]["teacher_calls"] == 6


def test_public_module_never_imports_evaluator():
    src = code_tokens(HERE / "p6_order.py")
    assert "p6_eval" not in src and "physical_labels" not in src
    for f in ("data.py", "models.py", "planner.py", "planner_r.py", "run_p4.py"):
        assert "p6_eval" not in code_tokens(HERE / f) and "p6_order" not in code_tokens(HERE / f)
