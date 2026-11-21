#!/usr/bin/env python3
"""SCNet native per-root inputs for CF/NULL scoring (env3d, no torch): teacher grasp poses of t0 at its start cell (scn_geometry.grasps_of =
shelf_scene.grasp_poses) and the start->goal shift, per base record.  Parity 240/240 against the teammates' stored roots_scn.pkl.
    CF_SCN=<scn_shelf> SHELF66_V3_DIR=<shelf66_v3> python cf_scnroots.py MANIFEST.jsonl OUT.pkl"""
import json, os, pickle, sys
from pathlib import Path

import numpy as np

SCN_DIR = Path(os.environ["CF_SCN"])


def objs_of(rec):
    return [dict(id=o["id"], shape=o["shape"], size=float(o["size"]), height=float(o["height"]), color=o.get("color")) for o in rec["objects"]]


def main(man, out_pkl):
    """env3d: teacher grasp poses of t0 at its start cell + start->goal shift, per base record (SCNet's native per-root inputs)."""
    sys.path.insert(0, str(SCN_DIR))
    import scn_geometry as G
    R = {}
    for q in (json.loads(l) for l in open(man)):
        if q["path"] in R:
            continue
        rec = json.loads(Path(q["path"]).read_text())
        t = next(o for o in rec["objects"] if o["id"] == "t0")
        st, g = tuple(rec["initial_cells"]["t0"]), tuple(rec["goal"])
        pos, Rm, _ = G.grasps_of(dict(height=float(t["height"]), size=float(t["size"]), shape=t["shape"]), st)
        R[q["path"]] = dict(objects=objs_of(rec), pos=pos, R=Rm, shift=np.array([*np.subtract(G.cell_xy(g), G.cell_xy(st)), 0.0], np.float32), start=st)
    pickle.dump(R, open(out_pkl, "wb"))
    print("scn roots", len(R))



if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
