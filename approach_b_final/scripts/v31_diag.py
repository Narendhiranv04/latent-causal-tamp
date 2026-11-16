"""V3.1-3 diagnostics on VALIDATION (frozen V3 primary, full candidate pool; no tuning).  Teacher-free parts use only the base-snapshot labels;
physical parts use the verify caches (unresolved stays unresolved).
  K3 (and K1/K2) failure decomposition per root: D1 ingredients in the one-pass proposal set, D2 known assignment constructed, D3 a known
  X=1 order of it scored, D4 the selection is / is not a known or verified success, D5 known success present but rejected (p11 < eta or no-op
  gate), D6 physical outcome / failure phase of the selection.
  NONE false positives: P(Y), P(X|Y) of the selected repair, pool size with p11 >= eta, p_noop, physical outcome.
  Known-success coverage vs budget B (v3_1c runs + full-pool B=4096)."""
import collections, json, os, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import contracts as CT
ABF, V = Path(os.environ["ABF_ROOT"]), Path(os.environ["V3OUT"])
P = "task:q2init_all-S1_M4"
RULE = {d: json.loads((V.parent / "v3_artifacts/v3_5" / f"rule_{d}.json").read_text()) for d in ("2d", "3d")}


def caches(dom):
    v = {}
    ps = [ABF / f"runs/v2/p5_{dom}/verify.jsonl", ABF / f"runs/p5_{dom}/verify.jsonl", Path("/scratch/nav/abf_v3/runs") / f"verify_{dom}.jsonl", V / f"verify_{dom}.jsonl"]
    ps += sorted(Path("/scratch/nav/abf_v3/caches").glob(f"final_*_verify_{dom}.jsonl"))
    for p in ps:
        if p.exists():
            for r in map(json.loads, open(p)):
                for x in r["results"]:
                    v[(r["root"], json.dumps(x["seq"]))] = x
    return v


def phys(x, dom):
    if x is None:
        return "UNRESOLVED"
    xr, yr = x["x"] or {}, x["y"] or {}
    ok = (lambda q: q.get("resolution", "EVALUATED") == "EVALUATED") if dom == "3d" else (lambda q: True)
    xv, yv = (xr.get("x") if ok(xr) else None), (yr.get("y") if ok(yr) else None)
    if xv is None or yv is None:
        return "UNRESOLVED"
    if xv == 1 and yv == 1:
        return "SUCCESS"
    return ("X_ok" if xv == 1 else f"X_fail@{xr.get('phase')}") + "|" + ("Y_ok" if yv == 1 else "Y_fail")


out = {}
for dom in ("2d", "3d"):
    rows = {r["root_id"]: r for r in map(json.loads, open(ABF / "snapshot/abf_9de85710c2a7103f" / f"data{dom}.jsonl")) if r["split"] == "val"}
    ver, rule = caches(dom), RULE[dom]
    recs = [json.loads(l) for l in open(V / "v3_1b" / dom / f"v3D_{P}_B4096_s0_val.jsonl")]
    dec, none, ksum = collections.defaultdict(collections.Counter), [], {}
    for r in recs:
        row = rows[r["root_id"]]; K = row["K_legacy"]; mk = row["masks"]
        sel = r["selected_ordered_seq"]
        if mk["eval_task"]:
            pa = CT.positive_assignments(row)
            Y = {CT.ekey(y["edit"]): y["y"] for y in row["labels"]["Y"]}
            known_ok = {json.dumps(q["seq"]) for q in row["labels"]["X"] if q["x"] == 1 and Y.get(CT.ekey(q["seq"])) == 1}
            acts = {tuple(a) for a in r["proposal_actions"]}
            ends = {json.dumps(e) for e in r["endpoints"]}
            cand = {json.dumps(c["seq"]): c for c in r["cands"]}
            verified_ok = {s for s in cand if json.loads(s) and phys(ver.get((r["root_id"], s)), dom) == "SUCCESS"}
            succ_present = (set(cand) & known_ok) | verified_ok
            sel_out = phys(ver.get((r["root_id"], json.dumps(sel))), dom) if sel else r["decision"]
            if not pa:
                stage = "no_known_assignment"
            elif not any(all(tuple(a) in acts for a in A["assignment"]) for A in pa.values()):
                stage = "D1_ingredients_missing"
            elif not any(json.dumps(A["assignment"]) in ends for A in pa.values()):
                stage = "D2_assignment_not_constructed"
            elif not (set(cand) & known_ok):
                stage = "D3_no_known_successful_order_scored"
            else:
                stage = "known_success_in_pool"
            if sel_out == "SUCCESS":
                fin = "SUCCESS"
            elif succ_present:
                best = max(succ_present, key=lambda s: cand[s]["p11"])
                rejected = (not sel and sel is not None and cand[json.dumps([])]["p11"] >= rule["noop_gate"]) or (sel is None and cand[best]["p11"] < rule["eta"])
                fin = "D5_rejected(gate/eta)" if (sel is None or sel == []) and rejected else ("D4_ranking(selected other)" if sel else "D5_rejected(gate/eta)")
            else:
                fin = "no_success_known_in_pool:" + (sel_out if isinstance(sel_out, str) else "")
            dec[K][(stage, fin if not fin.startswith("no_success") else "no_success_known_in_pool")] += 1
            dec[K][("selected_outcome", sel_out if isinstance(sel_out, str) else str(sel_out))] += 1
        if mk["eval_abstain"] and sel:
            c = next(c for c in r["cands"] if c["seq"] == sel)
            none.append({"root": r["root_id"], "m": len(sel), "p11": c["p11"], "py": c["py"], "px": c["px"], "p_noop": r["p_noop"],
                         "n_admissible": sum(1 for x in r["cands"] if x["seq"] and x["p11"] >= rule["eta"]), "n_scored": len(r["cands"]) - 1,
                         "outcome": phys(ver.get((r["root_id"], json.dumps(sel))), dom)})
    abst = [r for r in recs if rows[r["root_id"]]["masks"]["eval_abstain"]]
    nfp = {"n_none_roots": len(abst), "n_repair_selected": len(none), "outcomes": dict(collections.Counter(x["outcome"] for x in none)),
           "median_py": float(np.median([x["py"] for x in none])) if none else None, "median_px": float(np.median([x["px"] for x in none])) if none else None,
           "median_p11": float(np.median([x["p11"] for x in none])) if none else None,
           "median_admissible_pool": float(np.median([x["n_admissible"] for x in none])) if none else None,
           "abstained_median_admissible_pool": float(np.median([sum(1 for x in r["cands"] if x["seq"] and x["p11"] >= rule["eta"]) for r in abst if r["selected_ordered_seq"] is None])) if abst else None,
           "cases": none}
    # known-success coverage vs budget
    cov = {}
    for B in (128, 256, 512, 1024, 2048, 4096):
        f = V / ("v3_1b" if B == 4096 else "v3_1c") / dom / f"v3D_{P}_B{B}_s0_val.jsonl"
        hit, n, ns = [], 0, []
        for r in map(json.loads, open(f)):
            row = rows[r["root_id"]]
            if not row["masks"]["eval_task"]:
                continue
            Y = {CT.ekey(y["edit"]): y["y"] for y in row["labels"]["Y"]}
            known_ok = {json.dumps(q["seq"]) for q in row["labels"]["X"] if q["x"] == 1 and Y.get(CT.ekey(q["seq"])) == 1}
            if not known_ok:
                continue
            hit.append(bool({json.dumps(c["seq"]) for c in r["cands"]} & known_ok)); ns.append(r["candidate_budget"]["n_scored"])
        cov[B] = {"known_success_order_in_pool": float(np.mean(hit)), "roots": len(hit), "n_scored_median": float(np.median(ns))}
    out[dom] = {"decomposition_by_K": {K: {"|".join(k): v for k, v in sorted(c.items())} for K, c in sorted(dec.items())}, "none_false_positives": nfp,
                "known_success_coverage_vs_B": cov}
    print("=====", dom)
    for K, c in sorted(dec.items()):
        print("  K" + K, json.dumps({"|".join(k): v for k, v in sorted(c.items()) if k[0] != "selected_outcome"}))
    print("  NONE FP", json.dumps({k: v for k, v in nfp.items() if k != "cases"}))
    print("  coverage vs B", json.dumps(cov))
(V / "v31_diag").mkdir(exist_ok=True)
(V / "v31_diag" / "DIAG_VAL.json").write_text(json.dumps(out, indent=1))
