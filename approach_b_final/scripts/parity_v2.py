"""gvlab2 parity of the frozen V2 models (torch 2.9.1 / RTX 5090) vs the recorded gvlab V2 valsub search (torch 2.5.1 / RTX 4090)."""
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np, torch
import evaluate as EV, search as S
ABF = Path(os.environ["ABF_ROOT"]); EV.SNAP = ABF / "snapshot/abf_9de85710c2a7103f"
out = {}
for dom in ("2d", "3d"):
    rec = [json.loads(l) for l in open(ABF / f"runs/v2/p5_{dom}/search/full_s0_valsub.jsonl")][:40]
    rows = {r["root_id"]: r for r in EV.rows_of(dom.upper(), "valsub")}
    samp = S.Sampler(dom, "cvae", 0, ABF / "data" / f"q2_{dom}")
    scor = S.Scorer(ABF / f"runs/v2/p2_{dom}/D_s0/model.pt", ABF / f"runs/p3_{dom}/cost_s0/model.pt")
    dp, same_set, same_sel = [], 0, 0
    rule = json.loads((ABF / f"runs/v2/p5_{dom}/rule.json").read_text())
    for r in rec:
        root = S.Root(rows[r["root"]], dom)
        new = scor.score(root, [c["seq"] for c in r["cands"]])
        dp += [abs(n["p11"] - c["p11"]) for n, c in zip(new, r["cands"])]
        s2 = S.search(root, samp, scor, {**EV.SEARCH, "seed": 0}, mode="iterative")
        same_set += {json.dumps(c["seq"]) for c in s2["cands"]} == {json.dumps(c["seq"]) for c in r["cands"]}
        same_sel += S.select(s2["cands"], rule) == S.select(r["cands"], rule)
    out[dom] = {"roots": len(rec), "rescore_max_abs_dp11": float(np.max(dp)), "rescore_mean_abs_dp11": float(np.mean(dp)),
                "rerun_identical_candidate_set": same_set, "rerun_identical_selection": same_sel}
print(json.dumps(out, indent=1))
