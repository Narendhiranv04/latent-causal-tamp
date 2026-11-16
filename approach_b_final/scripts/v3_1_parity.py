"""V3.1-1 parity: frozen V3 primary (task cVAE q2init_all s0 + V3 D s0 + frozen V3 rule) re-run on gvlab vs the original gvlab2 valsub records
(same roots, seed, M, B): identical proposal sets, candidate sets, selections; max |dp11| over shared stored candidates."""
import json, os, sys
from pathlib import Path
import numpy as np
V3, ART = Path(os.environ["V3OUT"]), Path(os.environ["V3ART"])
out = {}
for d in ("2d", "3d"):
    T = "v3D_task:q2init_all-S1_M4_B4096_s0_valsub.jsonl"
    ref = {r["root_id"]: r for r in map(json.loads, open(ART / "v3_5" / d / T))}
    new = {r["root_id"]: r for r in map(json.loads, open(V3 / "v3_1_parity" / d / T))}
    same_prop = same_sel = same_cand = n = 0
    dp = []
    for k, r in new.items():
        q = ref[k]; n += 1
        same_prop += r["proposal_actions"] == q["proposal_actions"]
        same_sel += r["selected_ordered_seq"] == q["selected_ordered_seq"]
        a = {json.dumps(c["seq"]): c["p11"] for c in r["cands"]}; b = {json.dumps(c["seq"]): c["p11"] for c in q["cands"]}
        same_cand += set(a) == set(b)
        dp += [abs(a[s] - b[s]) for s in set(a) & set(b)]
    out[d] = {"roots": n, "identical_proposals": same_prop, "identical_selection": same_sel, "identical_stored_candidates": same_cand,
              "max_abs_dp11": float(np.max(dp)), "mean_abs_dp11": float(np.mean(dp))}
print(json.dumps(out, indent=1))
(V3 / "v3_1_parity" / "PARITY.json").write_text(json.dumps(out, indent=1))
