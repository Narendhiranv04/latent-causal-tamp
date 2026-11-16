"""V3-6 witnessed travel (evaluate.outcomes definition, never imputed): per arm, mean J_complete = sum |dq| / joint range over the witnessed
relocation + connector + target trajectories of VERIFIED SUCCESSFUL selections on test task roots; coverage = share with every witness found."""
import json, math, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import cost as CO
ABF, V3 = Path(os.environ["ABF_ROOT"]), Path(os.environ["V3OUT"])
ST, CA = V3.parent / "stores", V3.parent / "caches"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v3_6_table import ARMS  # noqa: E402  (same arm definitions)
out = {}
for dom in ("2d", "3d"):
    rows = {r["root_id"]: r for r in map(json.loads, open(ABF / "snapshot/abf_9de85710c2a7103f" / f"data{dom}.jsonl")) if r["split"] == "test"}
    if dom == "2d":
        rng = np.full(3, 2 * math.pi)
        stores = CO.STORES2 + [ABF / "runs/v2/2d/witnesses", V3 / "teacher2d_witnesses"] + [ST / n for n in ("g2v3_2d", "g2v2_t2d", "g2v2_2dw", "lap_2d")]
    else:
        rng = np.array(json.loads((ABF / "runs/p3/ranges3d.json").read_text())["arm_joint_ranges"])
        stores = CO.STORES3 + [ABF / "runs/p5_3d/verify_store", ABF / "runs/v2/3d/store", V3 / "verify_store_3d"] + [ST / n for n in ("g2v3_3d", "g2v2_3d", "g2v2_p53d", "lap_3d")]
    stores = [s for s in stores if s.exists()]
    ver = {}
    for p in [ABF / f"runs/v2/p5_{dom}/verify.jsonl", V3 / f"verify_{dom}.jsonl"] + sorted(CA.glob(f"final_*_verify_{dom}.jsonl")):
        if p.exists():
            for v in map(json.loads, open(p)):
                for x in v["results"]:
                    ver[(v["root"], json.dumps(x["seq"]))] = x
    res = {}
    for name, files in ARMS:
        J, miss, n = [], 0, 0
        for f in files:
            fp = V3 / "slim_test" / dom / f"{f}.jsonl"
            if not fp.exists():
                continue
            for r in map(json.loads, open(fp)):
                sel = r["selected_ordered_seq"]
                if not sel or not rows[r["root_id"]]["masks"]["eval_task"]:
                    continue
                v = ver.get((r["root_id"], json.dumps(sel)))
                if not v or (v["x"] or {}).get("x") != 1 or (v["y"] or {}).get("y") != 1:
                    continue
                n += 1
                xw = v["x"].get("witnesses") or []
                yw = [v["y"].get("witness")] if dom == "2d" else (v["y"].get("witnesses") or [])
                ws = [CO.wload(w, stores) for w in xw + [w for w in yw if w]]
                if any(w is None for w in ws):
                    miss += 1
                    continue
                J.append(sum(CO.jrec(w["connector_q"] if "connector_q" in w else w["q"], rng) for w in ws))
        res[name] = {"successes": n, "witnessed": len(J), "coverage": len(J) / max(1, n), "travel_mean": float(np.mean(J)) if J else None,
                     "travel_median": float(np.median(J)) if J else None}
        print(dom, f"{name:45s}", json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in res[name].items()}))
    out[dom] = res
(V3 / "v3_6" / "TRAVEL_TEST.json").parent.mkdir(parents=True, exist_ok=True)
(V3 / "v3_6" / "TRAVEL_TEST.json").write_text(json.dumps(out, indent=1))
