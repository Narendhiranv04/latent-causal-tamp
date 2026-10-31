"""Post-hoc, descriptive only (not a registered P11/P11.1 criterion): paired root-cluster bootstrap of OVERALL success under the PRIMARY rule,
each arm vs the no-op reference and vs DIRECT, from EVALUATION.json choices (seed mean per root; no-op success = recorded Y0)."""
import json
from pathlib import Path

import numpy as np

D = Path(__file__).parent
E = json.loads((D / "EVALUATION.json").read_text())
out = {}
for tier in ("PRIMARY_DEV", "SUPPLEMENTARY_DEV"):
    ch = E["tiers"][tier]["choices"]
    arms = sorted({k.split("|")[0] for k in ch})
    succ = {a: {} for a in arms}
    y0 = {}
    for key, rows in ch.items():
        for r, c in rows.items():
            succ[key.split("|")[0]].setdefault(r, []).append(c["success"])
            y0[r] = c["y0"]
    roots = sorted(y0)
    S = {a: np.array([np.mean(succ[a][r]) for r in roots]) for a in arms}
    S["NOOP"] = np.array([float(y0[r]) for r in roots])
    idx = np.random.default_rng(0).integers(0, len(roots), (10000, len(roots)))
    res = {}
    for a in arms:
        for b in ("NOOP", "DIRECT"):
            if a == b:
                continue
            d = S[a] - S[b]
            bs = d[idx].mean(1)
            res[f"{a} - {b}"] = {"diff": float(d.mean()), "ci95": [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))], "roots": len(roots)}
    out[tier] = res
(D / "POSTHOC_OVERALL_SUCCESS.json").write_text(json.dumps(out, indent=1))
for t, r in out.items():
    for k, v in r.items():
        print(t, f"{k:34s} {v['diff']:+.3f} [{v['ci95'][0]:+.3f}, {v['ci95'][1]:+.3f}] n={v['roots']}")
