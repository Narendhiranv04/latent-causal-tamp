"""R2 harness tests (synthetic records; no teacher, no model)."""
from __future__ import annotations

import json, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent.parent), str(HERE.parent.parent.parent)]
import common as C  # noqa: E402
import perturb as PT  # noqa: E402


def raw2d():
    objs = [{"cell": c, "id": f"o{j:02d}", "kind": "obstacle", "radius_m": 0.024, "support": "table", "xy_m": [0.08 * (c % 8 + 0.5), 0.08 * (c // 8 + 0.5)]}
            for j, c in enumerate([9, 10, 20])] + [{"cell": 12, "id": "t0", "kind": "target", "radius_m": 0.024, "support": "table", "xy_m": [0.36, 0.12]}]
    return {"ids": {"root_id": "syn2d"}, "goal_cell": 45, "fixed_ids": [], "roles": {"o00": "b", "o01": "b", "o02": "d"}, "q0": [0.0, 0.0, 0.0],
            "scene": {"objects": objs, "legal_cells": list(range(64)), "lattice": {"rows": 8, "cols": 8, "pitch_m": 0.08}, "robot": {"gripper_gap_m": 0.07}, "root_id": "syn2d"}}


def raw3d():
    objs = [{"id": "t0", "shape": "box", "size": 0.02, "height": 0.15}, {"id": "o00", "shape": "cylinder", "size": 0.015, "height": 0.16},
            {"id": "o01", "shape": "box", "size": 0.012, "height": 0.14}]
    return {"ids": {"root_id": "syn3d"}, "objects": objs, "initial_cells": {"t0": [1, 1], "o00": [1, 2], "o01": [2, 1]}, "goal": [4, 4], "roles": {"o00": "b", "o01": "d"}}


def test_2d_add_is_legal_nested_and_protected():
    r = raw2d()
    protect = [12, 9, 30]
    a, ids_a = PT.add("2d", r, 4, protect)
    b, ids_b = PT.add("2d", r, 8, protect)
    assert ids_b[:4] == ids_a and len(ids_b) == 8                                          # nested variants share distractors
    ca = [o["cell"] for o in a["scene"]["objects"]]
    assert len(set(ca)) == len(ca) and 45 not in ca[4:]
    for o in b["scene"]["objects"][4:]:
        assert all(PT.cheb("2d", o["cell"], p, 8) >= 2 for p in protect + [45]) and o["kind"] == "obstacle" and o["radius_m"] == 0.024
        assert abs(o["xy_m"][0] - 0.08 * (o["cell"] % 8 + 0.5)) < 1e-9 and b["roles"][o["id"]] == "distractor:added_r2"
    assert [o["id"] for o in b["scene"]["objects"][:4]] == [o["id"] for o in r["scene"]["objects"]]      # indices of existing bodies unchanged
    assert b["ids"]["root_id"] == "syn2d~N+8" and r["ids"]["root_id"] == "syn2d" and len(r["scene"]["objects"]) == 4


def test_3d_add_copies_template_and_refuses_when_unsupported():
    r = raw3d()
    a, ids = PT.add("3d", r, 3, [7, 8, 13, 28])
    assert len(ids) == 3 and all(a["initial_cells"][i] for i in ids)
    cells = [rc[0] * 6 + rc[1] for rc in a["initial_cells"].values()]
    assert len(set(cells)) == len(cells)
    t = [o for o in a["objects"] if o["id"] in ids]
    assert len({(o["shape"], o["size"], o["height"]) for o in t}) == 1 and t[0]["shape"] in ("box", "cylinder")
    bad, why = PT.add("3d", r, 40, [7])
    assert bad is None and "qualifying" in why


def test_views_compile_with_added_bodies():
    import contracts as CT
    r = raw2d()
    b, _ = PT.add("2d", r, 4, [12])
    v0, v = CT.view2d(r), CT.view2d(b)
    assert len(v["ids"]) == len(v0["ids"]) + 4 and v["tid"] == v0["tid"] and v["goal_cell"] == v0["goal_cell"]
    assert v["attrs"][:4] == v0["attrs"] and all(a[1] == 0.0 and a[2] == 1.0 for a in v["attrs"][4:])


def test_metrics():
    assert C.auroc([1, 1, 0, 0], [0.9, 0.8, 0.2, 0.1]) == 1.0 and C.auroc([1, 0], [0.5, 0.5]) == 0.5
    assert abs(C.auprc([1, 0, 1], [0.9, 0.8, 0.1]) - (1 + 2 / 3) / 2) < 1e-12
    c, n = C.concordance([[(1, 0.9), (0, 0.1), (0, 0.95)]])
    assert n == 2 and c == 0.5
    rows = [{"y": int(i % 2), "p": float(i % 2) * 0.8 + 0.1, "fam": i // 4} for i in range(40)]
    s = C.summary(rows, "y", "p")
    assert s["auroc"] == 1.0 and s["auroc_ci"] == [1.0, 1.0] and s["mixed_families"] == 10
    assert C.nbin("2d", 17) == "16-20" and C.nbin("3d", 13) == "8-13" and C.nbin("2d", 25) == ">20"
