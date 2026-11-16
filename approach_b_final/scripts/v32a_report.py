"""V3.2-A checks + validation prediction report (post-processing only: no model calls, no teacher calls).
Correctness: exact counts vs the V3.2 audit, shared-M6 vs independent M4 / M5 decisions (all 72 rules), old capped path vs exhaustive on roots
where the capped constructor was complete (candidate set, |dp11|, all 72 decisions).  Report (frozen V3 rule): decisions, changes vs the
capped M4 baseline by K, predicted p11, known-success coverage and rank, admissible pool sizes, runtime / memory, physical status of every
selection from the V1-V3 verify caches (SUCCESS / FAIL / UNRESOLVED; never inferred), and the list of new selections needing verification."""
import collections, json, os, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import evaluate as EV

ABF, V = Path(os.environ["ABF_ROOT"]), Path(os.environ["V3OUT"])
CA = V.parent / "caches"
RULES = EV.GRID


def jl(p):
    return [json.loads(l) for l in open(p)] if Path(p).exists() else []


def caches(dom):
    v = {}
    for p in sorted(CA.glob(f"*_verify_{dom}.jsonl")):
        for r in jl(p):
            for x in r["results"]:
                xr, yr = x["x"] or {}, x["y"] or {}
                ok = (lambda q: q.get("resolution", "EVALUATED") == "EVALUATED") if dom == "3d" else (lambda q: True)
                xv, yv = (xr.get("x") if ok(xr) else None), (yr.get("y") if ok(yr) else None)
                st = None if (xv is None or yv is None) else ("SUCCESS" if xv == 1 and yv == 1 else
                                                              ("FAIL:X@" + str(xr.get("phase")) if xv != 1 else "FAIL:Y"))
                v[(r["root"], json.dumps(x["seq"]))] = st
    return v


def dseq(d):
    return None if d is None else d["seq"]


def main(dom, tags):
    fr = json.loads((V / "v3_5" / f"rule_{dom}.json").read_text())
    ri = RULES.index(fr)
    rows = {r["root_id"]: r for r in map(json.loads, open(ABF / "snapshot/abf_9de85710c2a7103f" / f"data{dom}.jsonl")) if r["split"] == "val"}
    audit = {r["root_id"]: r for r in jl(V / "v32" / f"counts_{dom}_s0.jsonl") if r["split"] == "val"}
    ex = {r["root_id"]: r for r in jl(V / "v32a" / dom / f"{tags['shared']}.jsonl")}
    ind = {M: {r["root_id"]: r for r in jl(V / "v32a" / dom / f"{t}.jsonl")} for M, t in tags["indep"].items()}
    old = {r["root_id"]: r for r in jl(V / "v32a" / dom / f"{tags['old']}.jsonl")}
    ver = caches(dom)
    import exhaustive as EXH
    KN = {rid: EXH.known_success(r) for rid, r in rows.items()}
    mmax = max(int(m) for r in ex.values() for m in r["per_M"])
    Ms = [M for M in (4, 5, 6) if M <= mmax]
    C = {"roots_shared": len(ex), "roots_old": len(old)}
    # 1. exact counts vs audit
    bad = [(rid, M) for rid, r in ex.items() for M in Ms
           if r["per_M"][str(M)]["counts_by_K"] != [audit[rid][f"M{M}"][k] for k in ("K1", "K2", "K3")]]
    C["count_mismatch_vs_audit"] = len(bad)
    C["total_scored_shared"] = int(sum(r["per_M"][str(mmax)]["n_scored"] for r in ex.values()))
    C["total_expected_audit"] = int(sum(audit[rid][f"M{mmax}"]["total"] for rid in ex))
    # 2. shared vs independent passes
    for M, d in ind.items():
        diff = [rid for rid, r in d.items() if [dseq(x) for x in r["per_M"][str(M)]["decisions"]] != [dseq(x) for x in ex[rid]["per_M"][str(M)]["decisions"]]]
        cnt = [rid for rid, r in d.items() if r["per_M"][str(M)]["counts_by_K"] != ex[rid]["per_M"][str(M)]["counts_by_K"]]
        dp = [abs((a or {}).get("p11", 0) - (b or {}).get("p11", 0)) for rid, r in d.items()
              for a, b in zip(r["per_M"][str(M)]["decisions"], ex[rid]["per_M"][str(M)]["decisions"]) if a and b and a["seq"] == b["seq"]]
        C[f"independent_M{M}"] = {"roots": len(d), "roots_with_any_rule_decision_diff": len(diff), "count_diff": len(cnt),
                                  "max_abs_dp11_same_selection": float(max(dp)) if dp else 0.0, "diff_roots": diff[:10]}
    # 3. old capped path on roots where it was complete
    comp = [rid for rid, o in old.items() if o["mode"] == "complete" and rid in ex]
    setdiff = sum(1 for rid in comp if ex[rid]["p11_M4_small"] is None or set(ex[rid]["p11_M4_small"]) != set(k for k in old[rid]["p11"] if k != "[]"))
    dps = [abs(old[rid]["p11"][k] - v) for rid in comp if ex[rid]["p11_M4_small"] for k, v in ex[rid]["p11_M4_small"].items() if k in old[rid]["p11"]]
    decdiff = [rid for rid in comp if [o for o in old[rid]["decisions"]] != [dseq(x) for x in ex[rid]["per_M"]["4"]["decisions"]]]
    C["old_path_complete_roots"] = {"roots": len(comp), "candidate_set_diff": setdiff, "max_abs_dp11": float(max(dps)) if dps else None,
                                    "mean_abs_dp11": float(np.mean(dps)) if dps else None, "roots_with_any_rule_decision_diff": len(decdiff), "diff_roots": decdiff[:10]}
    # 4. report under the frozen V3 rule
    R, newsel = {}, []
    for M in Ms:
        S = collections.defaultdict(collections.Counter); ranks, sel_p, best_p = collections.defaultdict(list), [], []
        for rid, r in ex.items():
            row = rows[rid]; K = row["K_legacy"]; mk = row["masks"]
            pm = r["per_M"][str(M)]; d = pm["decisions"][ri]; s = dseq(d)
            o = old[rid]["decisions"][ri] if rid in old else "NA"
            dec = "ABSTAIN" if s is None else ("NOOP" if s == [] else "REPAIR")
            st = None if not s else ver.get((rid, json.dumps(s)))
            S[K]["decision:" + dec] += 1
            S[K]["changed_vs_capped"] += int(s != o)
            if s:
                S[K]["status:" + (st or "UNRESOLVED")] += 1
                sel_p.append(d["p11"])
            if s and s != o and st is None:
                newsel.append({"domain": dom, "M": M, "root_id": rid, "K_legacy": K, "seq": s, "p11": d["p11"], "py": d.get("py"), "px": d.get("px"),
                               "capped_baseline_seq": o, "masks": {k: mk[k] for k in ("eval_task", "eval_noop", "eval_abstain")}})
            if mk["eval_task"]:
                S[K]["known_success_in_pool"] += int(pm["known_success_in_pool"] > 0)
                if pm["best_known"]:
                    ranks[K].append(pm["best_known"]["rank_by_p11"]); best_p.append(pm["best_known"]["p11"])
                    S[K]["selected_is_known_success"] += int(bool(s) and tuple(tuple(a) for a in s) in KN[rid])
            S[K]["roots"] += 1
            S[K]["admissible_eta0.3_sum"] += pm["n_admissible"]["0.3"]
        wall = [r["wall_s"] for r in ex.values()]
        R[f"M{M}"] = {"by_K": {K: dict(c) for K, c in sorted(S.items())},
                      "best_known_rank_median": {K: float(np.median(v)) for K, v in sorted(ranks.items())},
                      "selected_p11_median": float(np.median(sel_p)) if sel_p else None,
                      "best_known_p11_median": float(np.median(best_p)) if best_p else None}
    # capped baseline under the frozen rule (same bookkeeping)
    B = collections.defaultdict(collections.Counter)
    for rid, o in old.items():
        row = rows[rid]; K = row["K_legacy"]; s = o["decisions"][ri]
        B[K]["decision:" + ("ABSTAIN" if s is None else "NOOP" if s == [] else "REPAIR")] += 1
        if s:
            B[K]["status:" + (ver.get((rid, json.dumps(s))) or "UNRESOLVED")] += 1
        if row["masks"]["eval_task"]:
            B[K]["known_success_in_pool"] += int((o.get("known_success_in_pool") or 0) > 0)
        B[K]["roots"] += 1
    R["capped_M4_B4096"] = {"by_K": {K: dict(c) for K, c in sorted(B.items())}}
    wall = np.array([r["wall_s"] for r in ex.values()])
    R["runtime_shared_pass"] = {"median_s": float(np.median(wall)), "p99_s": float(np.percentile(wall, 99)), "max_s": float(wall.max()), "total_h": float(wall.sum() / 3600),
                                "gpu_peak_mib": max(r.get("gpu_peak_mib", 0) for r in ex.values()),
                                "seq_per_s": C["total_scored_shared"] / max(wall.sum(), 1e-9)}
    if old:
        ow = np.array([o["wall_s"] for o in old.values()])
        R["runtime_capped"] = {"median_s": float(np.median(ow)), "max_s": float(ow.max()), "total_h": float(ow.sum() / 3600)}
    out = {"domain": dom, "frozen_rule": fr, "checks": C, "report": R, "new_selections_unresolved": len(newsel)}
    (V / "v32a" / dom / "V32A_REPORT.json").write_text(json.dumps(out, indent=1))
    with open(V / "v32a" / dom / "NEW_SELECTIONS_TO_VERIFY.jsonl", "w") as f:
        for x in newsel:
            f.write(json.dumps(x) + "\n")
    print(json.dumps({"domain": dom, "checks": C}, indent=1))
    for k, v in R.items():
        print(k, json.dumps(v))
    print("new unresolved selections:", collections.Counter(x["M"] for x in newsel))


if __name__ == "__main__":
    dom = sys.argv[1]
    main(dom, json.loads(sys.argv[2]))
