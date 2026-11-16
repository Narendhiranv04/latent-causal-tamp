"""V3.1-A teacher-free table: validation ELBO (3 seeds) and known-assignment ingredient recall (S1, M=4/8/12/16, 3 seeds) for the matched
goal-ablation variants (trained on gvlab, v3_1a) and the frozen V3 q2init_all (trained on gvlab2, v3_3)."""
import json, os
from pathlib import Path
import numpy as np
V = Path(os.environ["V3OUT"])
out = {}
for d in ("2d", "3d"):
    o = {"elbo": {}, "recall": {}}
    for v in ("q2init_all", "q2init_all_nogoal", "q2init_all_notask"):
        e = [json.loads((V / "v3_1a" / d / f"{v}_s{s}" / "curve.json").read_text())["best_val"] for s in (0, 1, 2)]
        o["elbo"][v] = [float(np.mean(e)), float(np.std(e))]
    r = {**json.loads((V / "v3_2" / d / "SWEEP_v31a_val.json").read_text()), **{k.replace("task:", "frozenV3:"): x for k, x in json.loads((V / "v3_2" / d / "SWEEP_v3frozen_val.json").read_text()).items()}}
    for k, x in sorted(r.items()):
        o["recall"][k] = {m: [x[m]["mean"], x[m]["sd"]] for m in ("recall", "recall_K1", "recall_K2", "recall_K3", "action_recall") if m in x}
    out[d] = o
    print("=====", d)
    for v, (m, s) in o["elbo"].items():
        print(f"  ELBO {v:22s} {m:.3f} +- {s:.3f}")
    for k, x in o["recall"].items():
        print(f"  {k:36s} recall {x['recall'][0]:.3f}+-{x['recall'][1]:.3f}  K1 {x['recall_K1'][0]:.3f} K2 {x['recall_K2'][0]:.3f} K3 {x['recall_K3'][0]:.3f}  action {x['action_recall'][0]:.3f}")
(V / "v3_1a" / "TEACHER_FREE.json").write_text(json.dumps(out, indent=1))
