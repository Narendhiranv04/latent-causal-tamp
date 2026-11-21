#!/usr/bin/env python3
"""G6 release assembly (bookkeeping + raw-record serialisation via the frozen scene template; no physics, no model).
  public/roots/<root_id>.json   raw root record in the frozen 2D format (scene, goal, q0, roles) -- NO labels, no K, no witness
  public/PUBLIC_MANIFEST.jsonl  root_id, path, sha256, in sha256('RELEASE|root_id') order (K not inferable from order or id)
  private/LABELS.jsonl          K (certified minimum), witness, MINK_STATIC V1/V2 certificates, Y0, X/Y statuses + replay hashes, G5 audit
  private/COVERAGE.jsonl        every final-stratum candidate: verdict, n_queries, selection status (SELECTED / CERTIFIED_PAIR_CAP /
                                CERTIFIED_AFTER_QUOTA / NO_WITNESS_FOUND / NOT_RUN_*)
  SUMMARY.json                  per-K quota, candidates, run, certified, selected, object counts, query totals
    python release.py SPEC.json OUT_DIR     (SPEC: strata -> {candidates, witness[], selected_layouts, g5}; see G6/RELEASE_SPEC.json)"""
import hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import witness as W  # noqa: E402

QUOTA = {4: 5, 5: 5, 6: 5, 9: 5, 12: 5}


def jl(p):
    return [json.loads(l) for l in open(p)] if Path(p).exists() else []


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(spec_f, od):
    spec = json.loads(Path(spec_f).read_text())
    base = Path(spec_f).resolve().parent                      # mink.boot chdirs: resolve every path first
    ab = lambda p: str(p if Path(p).is_absolute() else base / p)  # noqa: E731
    for s in spec["strata"].values():
        for key in ("candidates", "selected_layouts", "g5"):
            s[key] = ab(s[key])
        s["witness"] = [ab(f) for f in s["witness"]]
    od = Path(od).resolve(); (od / "public/roots").mkdir(parents=True, exist_ok=True); (od / "private").mkdir(parents=True, exist_ok=True)
    labels, cov, summ, pub = [], [], {}, []
    for ks, s in spec["strata"].items():
        k = int(ks)
        C = jl(s["candidates"]); Wt = {}
        for f in s["witness"]:
            for r in jl(f):
                Wt[r["root_id"]] = r
        sel = {L["root_id"]: L for L in jl(s["selected_layouts"]) if L["K_lb"] == k}
        G5 = {g["root_id"]: g for g in jl(s["g5"]) if g["K"] == k}
        for c in sorted((c for c in C if c["K_lb"] == k), key=lambda c: c["final_order"]):
            w = Wt.get(c["root_id"])
            st = ("SELECTED" if c["root_id"] in sel else
                  s.get("not_run_reason", "NOT_RUN") if w is None else
                  w["verdict"] if w["verdict"] != "CERTIFIED_MIN_K" else
                  ("CERTIFIED_PAIR_CAP" if s.get("pair_cap_hit", {}).get(f"{c['cells0'][0]},{c['goal_cell']}") else "CERTIFIED_AFTER_QUOTA"))
            cov.append({"root_id": c["root_id"], "K_lb": k, "final_order": c["final_order"], "target": c["cells0"][0], "goal": c["goal_cell"],
                        "n_objects": len(c["cells0"]), "verdict": w["verdict"] if w else None, "n_queries": w.get("n_queries") if w else None,
                        "cpu_s": w.get("cpu_s") if w else None, "status": st})
        for rid, L in sel.items():
            g, w = G5[rid], Wt[rid]
            assert g["verdict"] == "LABEL_OK", rid
            rec, _ = W.rec_of(L, L["geom"])
            p = od / "public/roots" / f"{rid}.json"
            p.write_text(json.dumps(rec, indent=1))
            pub.append({"root_id": rid, "path": f"public/roots/{rid}.json", "sha256": sha(p), "geometry": L["geom"]})
            fin = next(t for t in w["tries"] if t.get("final"))
            labels.append({"root_id": rid, "K_certified": k, "n_objects": len(L["cells0"]), "target_cell": L["cells0"][0], "goal_cell": L["goal_cell"],
                           "witness": g["witness"], "certificate": w["certificate"], "Y0": w["Y0"],
                           "X": {k2: fin.get(k2) for k2 in ("x", "x_status", "x_replay", "x_teacher", "x_steps_witness", "x_connector_witness")},
                           "Y": {k2: fin.get(k2) for k2 in ("y", "y_status", "y_replay", "y_teacher", "y_witness")},
                           "g5_checks": g["checks"], "g5_queries": g["queries"], "provenance": {"gen": L.get("gen"), "seed": L.get("seed"),
                           "final_order": L["final_order"], "accepted_rank": L.get("accepted_rank"), "g5": g.get("provenance")}})
        cs = [x for x in cov if x["K_lb"] == k]
        summ[k] = {"quota": QUOTA[k], "candidates": len(cs), "run": sum(x["verdict"] is not None for x in cs),
                   "certified": sum(x["verdict"] == "CERTIFIED_MIN_K" for x in cs), "selected": len(sel),
                   "no_witness": sum(x["verdict"] == "NO_WITNESS_FOUND" for x in cs), "not_run": sum(x["verdict"] is None for x in cs),
                   "selected_n_objects": sorted(len(L["cells0"]) for L in sel.values()),
                   "selected_target_goal_pairs": sorted({(L["cells0"][0], L["goal_cell"]) for L in sel.values()}),
                   "witness_queries_total": sum(x["n_queries"] or 0 for x in cs), "witness_cpu_h": round(sum(x["cpu_s"] or 0 for x in cs) / 3600, 2)}
    for k in QUOTA:
        summ.setdefault(k, {"quota": QUOTA[k], "selected": 0, "status": "BLOCKED (see G3/K12_BLOCKED.md)"})
    pub.sort(key=lambda r: hashlib.sha256(("RELEASE|" + r["root_id"]).encode()).hexdigest())
    (od / "public/PUBLIC_MANIFEST.jsonl").write_text("".join(json.dumps(r) + "\n" for r in pub))
    (od / "private/LABELS.jsonl").write_text("".join(json.dumps(r) + "\n" for r in sorted(labels, key=lambda r: (r["K_certified"], r["root_id"]))))
    (od / "private/COVERAGE.jsonl").write_text("".join(json.dumps(r) + "\n" for r in cov))
    summ = {"dataset": "SCALING2D_K4_12_TEST_V1", "selected_total": len(labels), "per_K": {str(k): v for k, v in sorted(summ.items())}}
    (od / "SUMMARY.json").write_text(json.dumps(summ, indent=1, default=list))
    print(json.dumps({k: (v.get("selected"), v.get("certified"), v.get("candidates")) for k, v in summ["per_K"].items()}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
