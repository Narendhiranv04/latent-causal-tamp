"""V3-4 label analysis: frozen V2 scorer calibration on the task-cVAE candidate distribution (TRAIN roots, physical Z), by p11 band and
legacy class; NONE roots with a newly verified repair (protocol-relative; plan V3 6.4)."""
import collections, json, os, sys
from pathlib import Path
import numpy as np
V = Path(os.environ["V3OUT"]) / "v3_4"
T = "task:q2init_all-S1_M4_B4096_s0"
out = {}
for d in ("2d", "3d"):
    items = {i["root"]: i for i in json.loads((V / d / f"items_{T}.json").read_text())}
    rows = []
    for fp in sorted((V / d).glob(f"labels_{T}_*.jsonl")):
        for r in map(json.loads, open(fp)):
            it = items[r["root"]]
            p = {json.dumps(q): (pp, w) for q, pp, w in zip(it["cands"], it["p11"], it["why"])}
            for x in r["results"]:
                xr, yr = x["x"] or {}, x["y"] or {}
                ok = (lambda q: q.get("resolution", "EVALUATED") == "EVALUATED") if d == "3d" else (lambda q: True)
                y = yr.get("y") if ok(yr) else None
                xv = xr.get("x") if (x["x"] and ok(xr)) else None
                z = 0 if y == 0 else (int(xv == 1) if y == 1 and xv in (0, 1) else None)
                pp, w = p[json.dumps(x["seq"])]
                rows.append({"root": r["root"], "K": it["K"], "p11": pp, "why": w, "z": z, "y": y, "x": xv, "m": len(x["seq"])})
    z = [r for r in rows if r["z"] is not None]
    yv, pv = np.array([r["z"] for r in z]), np.array([r["p11"] for r in z])
    bands = [(0.0, 0.1), (0.1, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.01)]
    rel = {f"{lo:.1f}-{min(hi, 1):.1f}": {"n": int(((pv >= lo) & (pv < hi)).sum()), "mean_p11": float(pv[(pv >= lo) & (pv < hi)].mean()) if ((pv >= lo) & (pv < hi)).any() else None,
                                          "z_rate": float(yv[(pv >= lo) & (pv < hi)].mean()) if ((pv >= lo) & (pv < hi)).any() else None} for lo, hi in bands}
    ece = sum(abs(v["mean_p11"] - v["z_rate"]) * v["n"] for v in rel.values() if v["n"]) / len(z)
    byK = {K: {"n": sum(r["K"] == K for r in z), "z_rate": float(np.mean([r["z"] for r in z if r["K"] == K])),
               "mean_p11": float(np.mean([r["p11"] for r in z if r["K"] == K])),
               "roots_with_Z1": len({r["root"] for r in z if r["K"] == K and r["z"] == 1}), "roots": len({r["root"] for r in z if r["K"] == K})} for K in ("0", "1", "2", "3", "NONE")}
    top = [r for r in z if r["why"] == "top"]
    out[d] = {"labelled_sequences": len(rows), "z_known": len(z), "z_rate": float(yv.mean()), "mean_p11": float(pv.mean()), "ece_v2_scorer": float(ece),
              "reliability": rel, "by_K": byK, "top2_by_p11_z_rate": float(np.mean([r["z"] for r in top])), "top2_mean_p11": float(np.mean([r["p11"] for r in top])),
              "none_roots_new_verified_repair": sorted({r["root"] for r in z if r["K"] == "NONE" and r["z"] == 1})[:50]}
    print(d, json.dumps({k: v for k, v in out[d].items() if k not in ("reliability", "none_roots_new_verified_repair")}))
    print("   reliability", json.dumps(rel))
(V / "V3_4_LABEL_ANALYSIS.json").write_text(json.dumps(out, indent=1))
