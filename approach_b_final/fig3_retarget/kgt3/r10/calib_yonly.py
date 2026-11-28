#!/usr/bin/env python3
"""R10.3 YONLY_CAL: VAL-only operating point for the Y-only score (no outcome of any evaluation track is read; VAL predictions only).
On the canonical VAL roster: r_noop = FINAL's NOOP rate, r_abst = FINAL's ABSTAIN rate.  Y-only rule with thresholds (g, e):
NOOP if pY(initial) >= g; else REPAIR(top nonempty endpoint by pY, = YONLY_RANK) if its pY >= e; else ABSTAIN.  g = the (1 - r_noop) quantile
of pY(initial) on VAL; e = the r_abst-quantile, among VAL roots not NOOP, chosen so the ABSTAIN fraction of ALL VAL roots equals r_abst.
    python3 calib_yonly.py PRED_DIR DOM      -> PRED_DIR/YONLY_CAL/r10u_DOM.jsonl + files_DOM.json (thresholds)"""
import json, sys
from pathlib import Path

import numpy as np


def jl(p):
    return {json.loads(l)["root_id"]: json.loads(l) for l in open(p)}


def main(pred, dom):
    pred = Path(pred)
    Fv, Yv, YRv = jl(pred / "FINAL" / f"val10_{dom}.jsonl"), jl(pred / "YONLY" / f"val10_{dom}.jsonl"), jl(pred / "YONLY_RANK" / f"val10_{dom}.jsonl")
    n = len(Fv)
    r_noop = sum(r["decision"] == "NOOP" for r in Fv.values()) / n
    r_abst = sum(r["decision"] == "ABSTAIN" for r in Fv.values()) / n
    pn = np.array([Yv[k]["p_noop"] for k in Fv]); top = np.array([YRv[k]["score"] if YRv[k]["score"] is not None else -1.0 for k in Fv])
    g = float(np.quantile(pn, 1 - r_noop)) if r_noop > 0 else float("inf")
    rest = top[pn < g]
    k_abst = int(round(r_abst * n))
    e = float(np.sort(rest)[k_abst]) if 0 < k_abst < len(rest) else (float("-inf") if k_abst == 0 else float("inf"))
    chk = {"noop": float(np.mean(pn >= g)), "abstain": float(np.mean((pn < g) & (top < e)))}
    Y, YR = jl(pred / "YONLY" / f"r10u_{dom}.jsonl"), jl(pred / "YONLY_RANK" / f"r10u_{dom}.jsonl")
    out = pred / "YONLY_CAL"; out.mkdir(exist_ok=True)
    with open(out / f"r10u_{dom}.jsonl", "w") as f:
        for k, y in Y.items():
            yr = YR[k]
            if y["p_noop"] >= g:
                d, mv = "NOOP", []
            elif yr["score"] is not None and yr["score"] >= e and yr["moves"]:
                d, mv = "REPAIR", yr["moves"]
            else:
                d, mv = "ABSTAIN", []
            f.write(json.dumps({"root_id": k, "domain": dom, "arm": "YONLY_CAL", "decision": d, "moves": mv, "p_noop": y["p_noop"], "score": yr["score"],
                                "wall_s": y.get("wall_s")}) + "\n")
    meta = {"rule": __doc__.split("\n")[1:5], "val_roots": n, "final_val_rates": {"noop": r_noop, "abstain": r_abst}, "g": g, "e": e, "yonly_cal_val_rates": chk,
            "source_files": [str(pred / a / f"val10_{dom}.jsonl") for a in ("FINAL", "YONLY", "YONLY_RANK")]}
    (out / f"files_{dom}.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps({k: meta[k] for k in ("final_val_rates", "g", "e", "yonly_cal_val_rates")}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
