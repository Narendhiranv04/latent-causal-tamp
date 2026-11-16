"""Padding parity: proposal marginals for 3D val roots are identical with MAXOBJ 12 vs 16 (masked, permutation-invariant encoder)."""
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np, torch
import placement as PL, search as S, evaluate as EV
EV.SNAP = PL.ROOT / "snapshot/abf_9de85710c2a7103f"
rows = EV.rows_of("3D", "val")[:40]
mx = 0.0
for kind in ("cvae", "task:q2init_all"):
    out = {}
    for pad in (12, 16):
        PL.MAXOBJ["3d"] = pad
        m = PL.load_task("3d", "q2init_all", 0) if kind.startswith("task") else PL.load("3d", "cvae", 0)
        samp = S.Sampler("3d", "cvae", 0, PL.ROOT / "data/q2_3d", rule={"name": "S1"}, model=m)
        res = []
        for r in rows:
            root = S.Root(r, "3d")
            if root.movable:
                res.append(samp.propose_many(root, root.cells0, root.movable, 4, torch.Generator(device="cuda").manual_seed(0)))
        out[pad] = res
    mx = max(mx, float(out[12] != out[16]))
print(json.dumps({"roots": len(rows), "proposals_differ": bool(mx)}))
