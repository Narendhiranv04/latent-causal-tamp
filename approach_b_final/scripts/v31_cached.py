"""V3.1 cached-label analyses (no new teacher queries, no tuning; historical V3-6 TEST selections, descriptive):
physical failure phases of the selected repair (D6) by legacy class, minimality vs the certified K, NONE / K0 decisions and their physical
outcomes, witnessed travel on the intersection of roots solved by both V3 primary and V2 iterative (per seed pair, paired root bootstrap)."""
import collections, json, math, os, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cost as CO
ABF = Path(os.environ["ABF_ROOT"]); V3 = Path("/scratch/nav/abf_v3"); OUT = Path(os.environ["V3OUT"]) / "v31_cached"
OUT.mkdir(parents=True, exist_ok=True)
P = "task:q2init_all-S1_M4_B4096"
ARMS = {"V3 primary": [f"v3D_{P}_s{s}_test" for s in (0, 1, 2)], "V2 iterative": [f"v2_iterative_s{s}_test" for s in (0, 1, 2)]}


def caches(dom):
    v = {}
    for p in [ABF / f"runs/v2/p5_{dom}/verify.jsonl", ABF / f"runs/p5_{dom}/verify.jsonl", V3 / f"runs/verify_{dom}.jsonl"] + sorted((V3 / "caches").glob(f"final_*_verify_{dom}.jsonl")):
        if p.exists():
            for r in map(json.loads, open(p)):
                for x in r["results"]:
                    v[(r["root"], json.dumps(x["seq"]))] = x
    return v


def outcome(x, dom):
    xr, yr = x["x"] or {}, x["y"] or {}
    ok = (lambda q: q.get("resolution", "EVALUATED") == "EVALUATED") if dom == "3d" else (lambda q: True)
    xv, yv = (xr.get("x") if ok(xr) else None), (yr.get("y") if ok(yr) else None)
    if xv == 1 and yv == 1:
        return "SUCCESS"
    if xv is None or yv is None:
        return "UNRESOLVED"
    xs = "X_ok" if xv == 1 else f"X_fail@{xr.get('phase')}[{xr.get('status')}]"
    ys = "Y_ok" if yv == 1 else f"Y_fail[{yr.get('status')}]"
    return f"{xs}|{ys}"


res = {}
for dom in ("2d", "3d"):
    rows = {r["root_id"]: r for r in map(json.loads, open(ABF / "snapshot/abf_9de85710c2a7103f" / f"data{dom}.jsonl")) if r["split"] == "test"}
    ver = caches(dom)
    sel = {a: [{r["root_id"]: r for r in map(json.loads, open(V3 / "runs/slim_test" / dom / f"{f}.jsonl"))} for f in fs] for a, fs in ARMS.items()}
    R = {}
    for a, seeds in sel.items():
        ph, mini, none, k0 = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
        for s in seeds:
            for rt, r in s.items():
                row, q = rows[rt], r["selected_ordered_seq"]
                K, mk = row["K_legacy"], row["masks"]
                x = ver.get((rt, json.dumps(q))) if q else None
                o = None if not q else (outcome(x, dom) if x else "UNVERIFIED")
                if mk["eval_task"]:
                    ph[(K, r["decision"] if not q else ("SUCCESS" if o == "SUCCESS" else "FAIL:" + o))] += 1
                    if o == "SUCCESS" and mk["eval_repair"]:
                        mini[("lt" if len(q) < int(K) else "eq" if len(q) == int(K) else "gt", K)] += 1
                if mk["eval_abstain"]:
                    none[r["decision"] if not q else ("REPAIR:" + o)] += 1
                if mk["eval_noop"]:
                    k0[r["decision"] if not q else ("REPAIR:" + o)] += 1
        n_task = sum(v for (K, _), v in ph.items())
        R[a] = {"task_outcomes_by_K": {f"{K}|{k}": v for (K, k), v in sorted(ph.items())},
                "fail_phase_summary": dict(collections.Counter(k.split("|")[0].split("[")[0] for (K, k), v in ph.items() for _ in range(v) if k.startswith("FAIL"))),
                "minimality_on_repair_roots": {f"{c}|K{K}": v for (c, K), v in sorted(mini.items())},
                "none_roots": dict(none), "k0_roots": dict(k0), "n_task_selections": n_task}
    # witnessed travel on the intersection of roots solved by both methods (seed i vs seed i)
    if dom == "2d":
        rng = np.full(3, 2 * math.pi); stores = CO.STORES2 + [ABF / "runs/v2/2d/witnesses", V3 / "runs/teacher2d_witnesses"] + [V3 / "stores" / n for n in ("g2v3_2d", "g2v2_t2d", "g2v2_2dw", "lap_2d")]
    else:
        rng = np.array(json.loads((ABF / "runs/p3/ranges3d.json").read_text())["arm_joint_ranges"])
        stores = CO.STORES3 + [ABF / "runs/p5_3d/verify_store", ABF / "runs/v2/3d/store", V3 / "runs/verify_store_3d"] + [V3 / "stores" / n for n in ("g2v3_3d", "g2v2_3d", "g2v2_p53d", "lap_3d")]
    stores = [s for s in stores if s.exists()]

    def travel(rt, q):
        x = ver.get((rt, json.dumps(q)))
        if not x or outcome(x, dom) != "SUCCESS":
            return None
        xw = x["x"].get("witnesses") or []
        yw = [x["y"].get("witness")] if dom == "2d" else (x["y"].get("witnesses") or [])
        ws = [CO.wload(w, stores) for w in xw + [w for w in yw if w]]
        return None if any(w is None for w in ws) else sum(CO.jrec(w["connector_q"] if "connector_q" in w else w["q"], rng) for w in ws)
    diffs, a3, a2, both_m = [], [], [], collections.Counter()
    for s3, s2 in zip(sel["V3 primary"], sel["V2 iterative"]):
        for rt in set(s3) & set(s2):
            if not rows[rt]["masks"]["eval_task"]:
                continue
            q3, q2 = s3[rt]["selected_ordered_seq"], s2[rt]["selected_ordered_seq"]
            if not q3 or not q2:
                continue
            t3, t2 = travel(rt, q3), travel(rt, q2)
            if t3 is None or t2 is None:
                continue
            diffs.append(t3 - t2); a3.append(t3); a2.append(t2); both_m[(len(q3), len(q2))] += 1
    d = np.array(diffs); g = np.random.default_rng(0)
    bs = [d[g.integers(0, len(d), len(d))].mean() for _ in range(2000)] if len(d) else [0]
    R["travel_intersection"] = {"pairs": len(d), "v3_mean": float(np.mean(a3)) if a3 else None, "v2_mean": float(np.mean(a2)) if a2 else None,
                                "delta_mean": float(d.mean()) if len(d) else None, "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                                "same_move_count_pairs": sum(v for (a, b), v in both_m.items() if a == b), "move_count_pairs": {f"{a}v{b}": v for (a, b), v in sorted(both_m.items())}}
    res[dom] = R
    print("=====", dom)
    for a in ARMS:
        print(a, "fail phases", R[a]["fail_phase_summary"], "| minimality", R[a]["minimality_on_repair_roots"])
        print("   NONE", R[a]["none_roots"], "| K0", R[a]["k0_roots"])
    print("travel intersection", json.dumps(R["travel_intersection"]))
(OUT / "CACHED_ANALYSIS_TEST.json").write_text(json.dumps(res, indent=1))
