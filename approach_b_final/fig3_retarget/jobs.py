#!/usr/bin/env python3
"""R1 physical smoke job builders (evaluator side; deterministic selection, no model, no labels beyond the declared fixture sources).
2D: exposed TRAIN raw roots (BD class-quota mirror on gvlab2; never release_v2 / VAL / TEST) with verified_K == 2 and a verified 2-action
    minimal B sequence; the first N by sha256("FIG3_R1_2D|" + root_id).  Per root: X_PARITY, Y_TEMP_PARITY (at the endpoint),
    X_CHUNKED (1,1) + endpoint Y + drop-inner-connector fixture, Y_TEMP of the 2nd action at S0 and after the 1st, plus one REJECT root.
3D: two derived K4 cohort roots with a stored 4-action witness; per root: Y_TARGET parity (t0 at the witness endpoint, and the first
    witness move as a temporary target from q_ready = the stored first relocation), temporary target of the LAST witness action at S0 and
    at its witness pre-state, X_CHUNKED (2,2) + t0 + drop fixture, and local paired execution (3,1) (enablers -> q_ref -> parent).
    python jobs.py 2d TRAIN_IDS ROOT_DIR N OUT.json      python jobs.py 3d COHORT_DIR OUT.json"""
from __future__ import annotations

import hashlib, json, sys
from pathlib import Path


def h(s):
    return hashlib.sha256(s.encode()).hexdigest()


def build2d(ids_file, root_dir, n, out):
    ids = sorted(Path(ids_file).read_text().split(), key=lambda r: h("FIG3_R1_2D|" + r))
    jobs, picked = [], []
    for rid in ids:
        p = Path(root_dir) / f"{rid}.json"
        if not p.exists():
            continue
        rec = json.loads(p.read_text())
        if rec.get("verified_K") != 2 or rec["scene"].get("geometry_impl") not in (None, "original"):
            continue
        mini = [b for b in rec["labels"]["B"] if b.get("role") == "minimal" and b.get("y") == 1 and len(b["sequence"]) == 2]
        if not mini:
            continue
        seq = [[o, int(d)] for o, d in mini[0]["sequence"]]
        picked.append(rid)
        k = rid[-12:]
        (a1, a2) = seq
        jobs += [{"key": f"X2PAR|{k}", "path": str(p), "kind": "X_PARITY", "seq": seq},
                 {"key": f"Y2PAR|{k}", "path": str(p), "kind": "Y_TEMP_PARITY", "edit": seq},
                 {"key": f"X2CH11|{k}", "path": str(p), "kind": "X_CHUNKED", "seq": seq, "bounds": [1, 2], "y_endpoint": True, "fixture": "drop_inner_connectors"},
                 {"key": f"Y2TB|{k}", "path": str(p), "kind": "Y_TEMP", "edit": [], "target": a2[0], "goal": a2[1]},
                 {"key": f"Y2TF|{k}", "path": str(p), "kind": "Y_TEMP", "edit": [a1], "target": a2[0], "goal": a2[1]}]
        if len(picked) == int(n):
            break
    rec = json.loads((Path(root_dir) / f"{picked[0]}.json").read_text())
    occ = set(rec["scene"]["legal_cells"]) - {o["cell"] for o in rec["scene"]["objects"]} - {rec["goal_cell"]}
    free = sorted(occ)
    jobs.append({"key": f"R2REJ|{picked[0][-12:]}", "path": str(Path(root_dir) / f"{picked[0]}.json"), "kind": "REJECT", "free": free[0], "free2": free[1]})
    Path(out).write_text(json.dumps(jobs, indent=1))
    print(json.dumps({"roots": picked, "jobs": len(jobs)}))


def build3d(cohort, out, roots=("3ds66-k45-b2c2-035", "3ds66-k45-b2c2-146")):
    jobs = []
    for rid in roots:
        p = Path(cohort) / "roots" / f"{rid}.json"
        rec = json.loads(p.read_text())
        w = rec["k45"]["witness"]["order"]
        cells0 = {k: list(v) for k, v in rec["initial_cells"].items()}
        end = {**cells0, **{o: list(d) for o, d in w}}
        pre = {**cells0, **{o: list(d) for o, d in w[:-1]}}
        k = rid[-8:]
        jobs += [{"key": f"Y3PAR|{k}", "path": str(p), "kind": "Y_TARGET", "cells": end, "target": "t0", "goal": rec["goal"],
                  "ref_witness": rec["k45"]["witness"]["y_witnesses"][0]},
                 {"key": f"Y3GEN|{k}", "path": str(p), "kind": "Y_TARGET", "cells": cells0, "target": w[0][0], "goal": w[0][1],
                  "ref_witness": rec["k45"]["witness"]["x_witnesses"][0]},
                 {"key": f"Y3TB|{k}", "path": str(p), "kind": "Y_TARGET", "cells": cells0, "target": w[-1][0], "goal": w[-1][1]},
                 {"key": f"Y3TF|{k}", "path": str(p), "kind": "Y_TARGET", "cells": pre, "target": w[-1][0], "goal": w[-1][1]},
                 {"key": f"X3CH22|{k}", "path": str(p), "kind": "X_CHUNKED", "order": w, "bounds": [2, 4], "y": {"target": "t0", "goal": rec["goal"]},
                  "fixture": "drop_inner_connectors"},
                 {"key": f"X3LOC31|{k}", "path": str(p), "kind": "X_CHUNKED", "order": w, "bounds": [3, 4], "y": {"target": "t0", "goal": rec["goal"]}}]
    rec = json.loads((Path(cohort) / "roots" / f"{roots[0]}.json").read_text())
    jobs.append({"key": f"X3CONT|{roots[0][-8:]}", "path": str(Path(cohort) / "roots" / f"{roots[0]}.json"), "kind": "X_CHUNKED",
                 "order": rec["k45"]["witness"]["order"], "bounds": [4], "y": None, "ref_witnesses": rec["k45"]["witness"]["x_witnesses"]})
    Path(out).write_text(json.dumps(jobs, indent=1))
    print(json.dumps({"roots": list(roots), "jobs": len(jobs)}))


if __name__ == "__main__":
    if sys.argv[1] == "2d":
        build2d(*sys.argv[2:6])
    else:
        build3d(*sys.argv[2:4])
