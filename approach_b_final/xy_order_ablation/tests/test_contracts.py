"""Contract tests for the readout / order ablation (plan.md 6 P1).  CPU only.   python -m pytest tests -q"""
import ast, itertools, json, math, os, sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
os.environ["XYO_DEVICE"] = "cpu"
import readout as R  # noqa: E402
import labels as L  # noqa: E402
import ordering as O  # noqa: E402
import exhaustive as EX  # noqa: E402
import search as S  # noqa: E402
import xy as XY  # noqa: E402

PUB = Path.home() / "abf_v34/parity"
RULE = {"noop_gate": 0.5, "eta": 0.3, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}


@pytest.fixture(scope="module", params=["2d", "3d"])
def dom(request):
    return request.param


@pytest.fixture(scope="module")
def models():
    return {d: R.load(d, "cpu") for d in ("2d", "3d")}


def rows(dom, n=3, min_mov=3):
    out = []
    for l in open(PUB / f"public_val_{dom}.jsonl"):
        r = json.loads(l)
        if len(S.Root(r, dom).movable) >= min_mov:
            out.append(r)
        if len(out) >= n:
            break
    return out


# ------------------------------------------------------------------------------------------------ readout algebra / parity
def test_readout_identities_and_scorer_parity(dom, models):
    samp, scor, man = models[dom]
    for r in rows(dom):
        root = S.Root(r, dom)
        D6 = EX.proposals(root, samp, 0)
        seqs = [list(map(list, s)) for s, _ in itertools.islice(EX.stream(D6, 4), 0, 400)]
        sc, pn = R.score(scor, root, seqs)
        ref = scor.score(root, seqs)
        assert scor.score(root, [[]])[0]["p11"] == R.score(scor, root, [])[1]             # no-op = pY(empty), scored alone as in production
        assert abs(scor.score(root, [[]])[0]["p11"] - pn) < 1e-6                           # batch-context float drift only
        assert max(abs(a["p11"] - b) for a, b in zip(ref, sc["p11"])) == 0.0               # J bit-identical to production Scorer
        assert max(abs(a["py"] - b) for a, b in zip(ref, sc["py"])) == 0.0
        assert max(abs(a["px"] - b) for a, b in zip(ref, sc["px"])) == 0.0                  # marginal pX = production px
        assert np.allclose(sc["p11"], sc["py"] * sc["px1"], atol=1e-6)
        assert np.allclose(sc["px"], sc["py"] * sc["px1"] + (1 - sc["py"]) * sc["px0"], atol=1e-6)
        by = {}
        for s, p in zip(seqs, sc["py"]):                                                  # endpoint invariance across permutations
            by.setdefault(R.canon(s), set()).add(p)
        assert all(len(v) == 1 for v in by.values())


def test_batch_parity(dom, models):
    samp, scor, man = models[dom]
    r = rows(dom, 1)[0]
    root = S.Root(r, dom)
    seqs = [list(map(list, s)) for s, _ in itertools.islice(EX.stream(EX.proposals(root, samp, 0), 4), 0, 300)]
    a, _ = R.score(scor, root, seqs)
    b = {k: np.concatenate([R.score(scor, root, seqs[i:i + 77])[0][k] for i in range(0, len(seqs), 77)]) for k in a}
    for k in ("p11", "py", "px", "px1"):
        assert np.max(np.abs(a[k] - b[k])) < 1e-6


def test_run_root_J_equals_production_cpu(dom, models):
    """Same device (CPU) -> same proposals: J of the shared streamed selector == exhaustive.score_root production decision; chunking parity."""
    samp, scor, man = models[dom]
    for r in rows(dom, 2):
        root = S.Root(r, dom)
        prod = EX.score_root(root, EX.proposals(root, samp, 0), scor, [RULE], 4, set(), 8192)["per_M"]["4"]["decisions"][0]
        rec = R.run_root(r, samp, scor, man, chunk=8192)
        rec2 = R.run_root(r, samp, scor, man, chunk=97)
        want = None if prod is None else prod["seq"]
        assert rec["arms"]["J"]["seq"] == want and rec2["arms"]["J"]["seq"] == want
        assert rec["pool_hash"] == rec2["pool_hash"] and rec["n_pool"] == rec2["n_pool"]
        assert all(rec["arms"][a]["seq"] == rec2["arms"][a]["seq"] for a in R.ARMS)
        assert rec["teacher_calls"] == 0


def test_empty_pool_root(models):
    samp, scor, man = models["2d"]
    r = json.loads(json.dumps(rows("2d", 1)[0]))
    for i, a in enumerate(r["inputs"]["attrs"]):                                           # synthetic: every non-target object fixed
        if i != r["inputs"]["tid"]:
            a[3] = 1.0
    assert not S.Root(r, "2d").movable
    rec = R.run_root(r, samp, scor, man)
    assert rec["n_pool"] == 0 and all(rec["arms"][a]["decision"] in ("NOOP", "ABSTAIN") for a in R.ARMS) and all(v is None for v in rec["rank_only"].values())


# ------------------------------------------------------------------------------------------------ selectors
def choose(seqs, p, pn, rule):
    rows_ = [{"admissible": True, "m": 0, "p": pn, "cd": 0.0, "J_hat": 0.0, "sig": "[]"}] + [
        {"admissible": True, "m": len(s), "p": float(p[i]), "cd": 0.0, "J_hat": 0.0, "sig": json.dumps([list(a) for a in s])} for i, s in enumerate(seqs)]
    k = XY.choose(rows_, rule)
    return None if k is None else json.loads(rows_[k]["sig"])


def test_selectors_match_choose_incl_noop_below_gate():
    g = np.random.default_rng(1)
    seqs = [((1, 2),), ((1, 3),), ((2, 4), (1, 2)), ((1, 2), (2, 4)), ((3, 9),)]
    hits = 0
    for t in range(300):
        p = g.uniform(0, 1, len(seqs)); pn = float(g.uniform(0.25, 0.6)) if t % 2 else float(g.uniform(0, 1))
        hits += 0.3 <= pn < 0.5
        sel = EX.Selectors([RULE])
        sel.update(seqs, p, np.array([len(s) for s in seqs]), np.zeros(5), np.zeros(5), np.zeros(5, int), {})
        d = sel.finish(pn)[4][0]
        assert (None if d is None else d["seq"]) == choose(seqs, p, pn, RULE)
    assert hits > 20                                                                       # the competing no-op below the gate was exercised


def test_y_arm_is_order_blind_and_rank_only_excludes_noop():
    perms = [tuple(p) for p in itertools.permutations(((1, 2), (2, 5), (3, 7)))]
    py = np.full(6, 0.8)
    picks = set()
    for t in range(20):
        px = np.random.default_rng(t).uniform(0, 1, 6)                                    # X readouts change; Y arm must not
        sel = EX.Selectors([RULE])
        sel.update(perms, py, np.full(6, 3), np.zeros(6), np.zeros(6), np.zeros(6, int), {"px": px})
        picks.add(json.dumps(sel.finish(0.1)[4][0]["seq"]))
    assert len(picks) == 1
    rk = EX.Selectors([R.RANK_RULE])
    rk.update(perms, np.full(6, 0.01), np.full(6, 3), np.zeros(6), np.zeros(6), np.zeros(6, int), {})
    assert rk.best[(4, 0.0, (0.0, 0.0, 0.0))][1]["seq"]                                  # nonempty even with tiny scores; no no-op entry exists


# ------------------------------------------------------------------------------------------------ labels
def test_factor_mapping():
    assert L.factor("2d", {"x": 0, "status": "UNKNOWN_PLANNER"}, "X")[:2] == (None, 0)
    assert L.factor("2d", {"x": 0, "status": "CERTIFIED_INFEASIBLE"}, "X")[:2] == (0, 0)
    assert L.factor("2d", {"x": 0, "status": "Q_REF_NOT_CLEAR_IN_EDITED_SCENE"}, "X")[:2] == (0, 0)
    assert L.factor("2d", {"y": 0, "status": "REPLAY_FAILED"}, "Y")[:2] == (None, 0)
    assert L.factor("3d", {"x": 0, "resolution": "EVALUATED", "status": "no feasible side grasp"}, "X")[:2] == (0, 0)
    assert L.factor("3d", {"resolution": "UNRESOLVED_ADMIN"}, "X")[:2] == (None, None)
    assert L.factor("2d", None, "X")[2] == "MISSING"


def test_ledger_conflicts_upgrades_and_z():
    led = L.Ledger.__new__(L.Ledger)
    led.dom, led.X, led.Y, led.conflicts, led.files = "2d", {}, {}, __import__("collections").Counter(), {}
    s = [[1, 5], [2, 6]]
    led.add("r", s, {"x": 0, "status": "UNKNOWN_PLANNER"}, {"y": 1, "status": "VERIFIED"}, "a")
    assert led.get("r", s) [:3] == (None, 1, None) and led.get("r", s, "oper")[:3] == (0, 1, 0)
    led.add("r", s, {"x": 1, "status": "VERIFIED"}, {"y": 1, "status": "VERIFIED"}, "b")       # decided upgrade of an UNKNOWN
    assert led.get("r", s)[:3] == (1, 1, 1)
    led.add("r", s, {"x": 0, "status": "CERTIFIED_INFEASIBLE"}, {"y": 1, "status": "VERIFIED"}, "c")   # decided contradiction -> quarantine
    assert led.get("r", s)[0] is None and led.conflicts[("X", "decided")] == 1
    led.add("r", [[2, 6], [1, 5]], {"x": 0, "status": "CERTIFIED_INFEASIBLE"}, None, "d")     # Y joins by canonical endpoint, X by exact order
    assert led.get("r", [[2, 6], [1, 5]])[:3] == (0, 1, 0)
    assert led.get("r", [])[0] == 1


# ------------------------------------------------------------------------------------------------ ordering
def test_order_group_metrics():
    A = [[1, 5], [2, 6], [3, 7]]
    orders = O.all_orders(A)
    assert len(orders) == 6 and O.canonical(orders) == [[1, 5], [2, 6], [3, 7]]
    s = {O.sig(q): i / 10 for i, q in enumerate(orders)}
    x = {O.sig(q): int(i >= 3) for i, q in enumerate(orders)}
    g = O.group(A, s, x)
    assert g["concordance"] == 1.0 and g["learned_x"] == 1 and g["canonical_x"] == 0 and abs(g["random_x"] - 0.5) < 1e-12 and g["mixed"]
    x2 = {O.sig(orders[0]): 1, O.sig(orders[1]): 0}
    g2 = O.group(A, s, x2)
    assert g2["random_x"] is None and g2["random_bounds"] == [1 / 6, 5 / 6] and g2["oracle_any"] == 1
    flat = {k: 0.5 for k in s}
    assert O.group(A, flat, x)["concordance"] == 0.5 and O.sig(O.learned_top(orders, flat)) == O.sig(O.canonical(orders))


def test_panel_constraints():
    p = json.loads((HERE / "reports/P0_PANEL.json").read_text())
    for dom, d in p["domains"].items():
        roots = [x["root_id"] for x in d["items"]]
        assert len(roots) == len(set(roots)) and d["ordered_requests_max"] <= 80
        for x in d["items"]:
            assert len(x["permutations"]) == math.factorial(x["m"]) and sorted(map(tuple, x["assignment"])) == [tuple(a) for a in x["assignment"]]


def test_planner_never_imports_labels():
    src = (HERE / "readout.py").read_text()
    mods = {n.names[0].name for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Import)} | \
           {n.module for n in ast.walk(ast.parse(src)) if isinstance(n, ast.ImportFrom)}
    assert "labels" not in mods and "run" not in mods
    for bad in ("cr_cvae_private", "xyo_private", "verify_", "PRIVATE_INDEX", "labels.B"):
        assert bad not in src
