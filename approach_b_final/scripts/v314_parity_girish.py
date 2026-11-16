"""girish-laptop vs gvlab V3.1-B/C selections (validation, V3 primary s0, B=128 and B=4096): identical selected sequence + decision per root."""
import json, sys
from pathlib import Path
H = Path.home() / "abf_v31"
res = {}
for d in ("2d", "3d"):
    for B in (128, 4096):
        name = f"v3D_task:q2init_all-S1_M4_B{B}_s0_val.jsonl"
        ref = {r["root_id"]: r for r in map(json.loads, open(H / "parity_ref" / d / name))}
        mine = H / "runs" / "v3_1_4_parity" / d / name
        got = {r["root_id"]: r for r in map(json.loads, open(mine))} if mine.exists() else {}
        same = sum(1 for k, r in got.items() if k in ref and (r["selected_ordered_seq"], r["decision"]) == (ref[k]["selected_ordered_seq"], ref[k]["decision"]))
        res[f"{d}_B{B}"] = {"roots_ref": len(ref), "roots_girish": len(got), "identical": same,
                            "diff": [k for k, r in got.items() if k in ref and (r["selected_ordered_seq"], r["decision"]) != (ref[k]["selected_ordered_seq"], ref[k]["decision"])][:10]}
out = json.dumps(res, indent=1)
print(out)
(H / "runs" / "v3_1_4_parity" / "PARITY_GIRISH_VS_GVLAB.json").write_text(out)
