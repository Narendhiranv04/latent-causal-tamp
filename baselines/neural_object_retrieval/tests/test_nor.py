"""NOR-Grid gate tests (paper-agnostic legality / input / supervision-provenance part) (P1 legality / interface, P2 graph + supervision provenance, P3 model invariances).  CPU only."""
import json, random, sys
from pathlib import Path

import numpy as np
import pytest

H = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(H), str(H.parents[1] / "approach_b_final")]
import benchmark as BM  # noqa: E402
import graph as G  # noqa: E402
import nor_data as DA  # noqa: E402

ROWS = {d: DA.rows(d, DA.BASE, "val")[:150] for d in ("2d", "3d")}


def pub(r):
    return {"root_id": r["root_id"], "domain": r["domain"].lower(), "inputs": r["inputs"]}


@pytest.mark.parametrize("dom", ["2d", "3d"])
def test_legality_matches_benchmark(dom):
    rng = random.Random(0)
    n_legal = n_illegal = 0
    for r in ROWS[dom]:
        inp, p = r["inputs"], pub(r)
        for _ in range(12):
            k = rng.randint(1, 3)
            seq = []
            for _ in range(k):                           # random moves: legal-biased but frequently illegal
                o = rng.randrange(len(inp["ids"]))
                d = rng.choice(inp["legal_cells"] + [inp["goal_cell"], inp["cells0"][o]])
                seq.append((o, int(d)))
            mine = G.is_legal(inp, dom, seq)
            ref = BM.legality(p, [{"object_index": o, "destination_cell": d} for o, d in seq])
            assert (mine is None) == (ref is None), (seq, mine, ref)
            n_legal += mine is None
            n_illegal += mine is not None
    assert n_legal > 20 and n_illegal > 20


@pytest.mark.parametrize("dom", ["2d", "3d"])
def test_constructed_counterexamples(dom):
    r = next(x for x in ROWS[dom] if len(G.movable(x["inputs"], dom)) >= 2)
    inp = r["inputs"]
    m = G.movable(inp, dom)
    free = G.legal_dests(inp, G.apply(inp, []))
    assert G.is_legal(inp, dom, [(m[0], free[0])]) is None
    assert G.is_legal(inp, dom, []) == "LENGTH"
    assert G.is_legal(inp, dom, [(m[0], free[0]), (m[0], free[1])]) == "OBJECT_MOVED_TWICE"
    assert G.is_legal(inp, dom, [(inp["tid"], free[0])]) == "IMMOVABLE_OBJECT"
    assert G.is_legal(inp, dom, [(m[0], int(inp["cells0"][m[1]]))]) == "ILLEGAL_DESTINATION"       # occupied at S0
    assert G.is_legal(inp, dom, [(m[0], int(inp["goal_cell"]))]) == "ILLEGAL_DESTINATION"          # target goal
    assert G.is_legal(inp, dom, [(m[0], free[0]), (m[1], free[0])]) == "ILLEGAL_DESTINATION"       # same destination twice
    assert G.is_legal(inp, dom, [(m[0], free[0]), (m[1], int(inp["cells0"][m[0]]))]) == "ILLEGAL_DESTINATION"  # vacated cell
    if dom == "2d":
        fx = [i for i, a in enumerate(inp["attrs"]) if a[3]]
        if fx:
            assert G.is_legal(inp, dom, [(fx[0], free[0])]) == "IMMOVABLE_OBJECT"


@pytest.mark.parametrize("dom", ["2d", "3d"])
def test_graph_uses_public_inputs_only_and_masks(dom):
    r = ROWS[dom][0]
    p = pub(r)
    assert set(p) == {"root_id", "domain", "inputs"}
    S = G.scene(p["inputs"], dom)
    leg = set(np.nonzero(S["L"])[0])
    assert leg == set(G.legal_dests(p["inputs"], G.apply(p["inputs"], [])))
    assert not S["elig"][p["inputs"]["tid"]]
    S0 = G.scene(p["inputs"], dom, goal=False)
    assert not S0["M"][G.NMAX[dom] + 1] and float(np.abs(S0["C"][:, 9:]).sum()) == 0.0


@pytest.mark.parametrize("dom", ["2d", "3d"])
def test_supervision_never_invents_negatives(dom):
    for r in DA.rows(dom, DA.EXT, "train")[:300]:
        S = DA.supervision(r, dom)
        Y = {DA.ekey(y["edit"]): y["y"] for y in r["labels"]["Y"]}
        for p, objs in S["SEQ"]:
            assert objs                                               # positives only
        for p, o, d, lab in S["EXEC"]:
            assert lab in (0, 1)
        assert len(S["STOP"]) == len(Y)                               # one Y per endpoint, no order inflation
        for p, o, d, lab in S["EXEC"]:
            if lab == 0:                                              # a negative must come from a localised failed relocation
                assert any(json.loads(DA.okey(q["seq"]))[:len(p) + 1] == p + [[o, d]] and q.get("x_phase") == f"relocation:{len(p)}"
                           for q in r["labels"]["X"])
