#!/usr/bin/env python3
"""CF/NULL metrics from SEALED files only (jobs, teacher labels, frozen-model scores); no model is loaded here.
  triplets   cf_report.triplets: PROTOCOL_LOCK acceptance (first object in sha order with both; first CF y=0 certified / budget; first NULL y=1)
  metrics    pooled CF-pair AUROC (BASE vs CF, midrank ties), within-pair flip-rank (ties 0.5), CF blocked acc (p<0.5), NULL retention (p>=0.5),
             conditional NULL retention (p_B>=0.5), mean p_B-p_CF and |p_B-p_NULL|, BASE feasible acc; oracle rates over ALL attempted proposals;
             2,000-replicate bootstrap (seed 0) over base lineage; constant-score control (expected flip-rank 0.5).
    python cf_report.py triplets DOM JOBS LABELS OUT_MANIFEST       (seal the accepted triplet manifest)
    python cf_report.py metrics DOM MANIFEST LABELS SCORES OUT.json"""
import collections, json, sys

import numpy as np
from scipy.stats import rankdata

NEG_CERT = {"3d": {"CERTIFIED"}, "2d": {"CERTIFIED"}}


def jl(p):
    return [json.loads(l) for l in open(p)]


def triplets(dom, jobs_f, lab_f, out_f):
    J = {j["qid"]: j for j in jl(jobs_f)}
    L = {r["qid"]: r for r in jl(lab_f)}
    by = collections.defaultdict(list)
    for j in J.values():
        by[j["root_id"]].append(j)
    acc, fun = [], collections.Counter()
    for rid, js in sorted(by.items()):
        b = L.get(f"{rid}|BASE")
        if b is None or b.get("y") != 1:
            fun["base_not_verified_feasible" if b else "base_missing"] += 1
            continue
        objs = []
        for j in sorted(js, key=lambda j: j["qid"]):
            if j["kind"] != "BASE" and j["obj"] not in objs:
                objs.append(j["obj"])
        objs = [o for o in [j["obj"] for j in js if j["kind"] == "CF" and j["rank"] == 0]]        # generator order (sha) via rank-0 CF rows
        got = None
        for o in objs:
            cf = sorted((j for j in js if j["kind"] == "CF" and j["obj"] == o), key=lambda j: j["rank"])
            nl = sorted((j for j in js if j["kind"] == "NULL" and j["obj"] == o), key=lambda j: j["rank"])
            n = next((j for j in nl if L.get(j["qid"], {}).get("y") == 1), None)
            c_s = next((j for j in cf if L.get(j["qid"], {}).get("y") == 0 and L[j["qid"]].get("negative_kind") in NEG_CERT[dom]), None)
            c_b = next((j for j in cf if L.get(j["qid"], {}).get("y") == 0), None)
            if n and c_s:
                got = ("STRONG", o, c_s, n); break
            if n and c_b and got is None:
                got = ("BUDGET", o, c_b, n)
        if got is None:
            fun["no_matched_cf_null"] += 1
            continue
        coh, o, c, n = got
        fun[coh] += 1
        acc.append({"root_id": rid, "cohort": coh, "obj": o, "base": f"{rid}|BASE", "cf": c["qid"], "null": n["qid"], "base_kind": J[f"{rid}|BASE"].get("base_kind"),
                    "lineage": J[f"{rid}|BASE"].get("lineage", rid), "cf_kind": L[c["qid"]].get("negative_kind"), "cf_status": L[c["qid"]].get("status")})
    allp = [L[q] for q, j in J.items() if j["kind"] in ("CF", "NULL") and q in L]
    orc = {}
    for kind in ("CF", "NULL"):
        R = [L[q] for q, j in J.items() if j["kind"] == kind and q in L]
        orc[kind] = {"attempted": len(R), "y1": sum(r.get("y") == 1 for r in R), "y0_certified": sum(r.get("y") == 0 and r.get("negative_kind") in NEG_CERT[dom] for r in R),
                     "y0_budget": sum(r.get("y") == 0 and r.get("negative_kind") not in NEG_CERT[dom] for r in R), "error_or_unknown": sum(r.get("y") not in (0, 1) for r in R)}
    orc["NULL"]["oracle_false_flip_rate"] = (orc["NULL"]["y0_certified"] + orc["NULL"]["y0_budget"]) / max(1, orc["NULL"]["attempted"] - orc["NULL"]["error_or_unknown"])
    orc["CF"]["oracle_certified_flip_rate"] = orc["CF"]["y0_certified"] / max(1, orc["CF"]["attempted"] - orc["CF"]["error_or_unknown"])
    man = {"dom": dom, "n_bases": len(by), "funnel": dict(fun), "oracle": orc, "triplets": acc}
    json.dump(man, open(out_f, "w"), indent=1)
    print(json.dumps({k: man[k] for k in ("n_bases", "funnel", "oracle")}, indent=1))


def triplets_ins(jobs_f, lab_f, out_f):
    """PROP_INS_3D (amendment 4).  BASE: re-verified task y = 1 via g* (its y_grasp = 1 by construction, re-checked).  Per base, CF = first insertion
    (rank order: edge desc, standoff asc) whose fixed grasp g* FLIPS (y_grasp = 0, paper unit); NULL = first matched off-corridor box of the SAME
    size with y_grasp = 1 AND task y = 1.  Cohorts: GRASP_FLIP (paper: same grasp, identical pose; task may stay feasible through other grasps) and
    TASK_FLIP (the CF also makes the whole target task infeasible, task y = 0) -- TASK_FLIP is the subset on which a task-level score SHOULD drop.
    Oracle (all attempted): paper 'Flip' = P(y_grasp = 0 | CF), paper 'Null' = P(y_grasp = 0 | NULL); task-level analogues too."""
    J = {j["qid"]: j for j in jl(jobs_f)}
    L = {r["qid"]: r for r in jl(lab_f)}
    by = collections.defaultdict(list)
    for j in J.values():
        by[j["root_id"]].append(j)
    acc, fun = [], collections.Counter()
    for rid, js in sorted(by.items()):
        b = L.get(f"{rid}|BASE")
        if not b or b.get("y") != 1 or b.get("y_grasp") != 1:
            fun["base_not_verified"] += 1
            continue
        cfs = sorted((j for j in js if j["kind"] == "CF"), key=lambda j: j["rank"])
        c = next((j for j in cfs if L.get(j["qid"], {}).get("y_grasp") == 0), None)
        if c is None:
            fun["no_grasp_flip" if cfs else "no_corridor_cell"] += 1
            continue
        si = c["qid"].rsplit("|", 1)[1]
        n = next((j for j in sorted((j for j in js if j["kind"] == "NULL" and j["qid"].endswith("|" + si)), key=lambda j: j["rank"])
                  if L.get(j["qid"], {}).get("y_grasp") == 1 and L[j["qid"]].get("y") == 1), None)
        if n is None:
            fun["no_null"] += 1
            continue
        lc = L[c["qid"]]
        coh = ["GRASP_FLIP"] + (["TASK_FLIP"] if lc.get("y") == 0 else [])
        fun["GRASP_FLIP"] += 1; fun["TASK_FLIP"] += "TASK_FLIP" in coh
        acc.append({"root_id": rid, "cohort": coh, "base": f"{rid}|BASE", "cf": c["qid"], "null": n["qid"], "base_kind": J[f"{rid}|BASE"].get("base_kind"),
                    "lineage": rid, "grasp_kind": lc.get("grasp_negative_kind"), "task_y": lc.get("y"), "task_kind": lc.get("negative_kind"),
                    "standoff_m": c.get("standoff_m"), "box_edge_m": c.get("box_edge_m"), "null_dist_m": n.get("dist_from_cf_m")})
    orc = {}
    for kind in ("CF", "NULL"):
        R = [L[q] for q, j in J.items() if j["kind"] == kind and q in L and L[q].get("y_grasp") is not None]
        orc[kind] = {"attempted": len(R), "grasp_flip_rate": sum(r["y_grasp"] == 0 for r in R) / max(1, len(R)),
                     "grasp_flip_certified": sum(r["y_grasp"] == 0 and r.get("grasp_negative_kind") == "CERTIFIED" for r in R) / max(1, len(R)),
                     "task_flip_rate": sum(r.get("y") == 0 for r in R) / max(1, len(R)),
                     "errors": sum(1 for q, j in J.items() if j["kind"] == kind and L.get(q, {}).get("y_grasp") is None)}
    man = {"dom": "3d_ins", "n_bases": len(by), "funnel": dict(fun), "oracle": orc, "cohort_names": ["GRASP_FLIP", "TASK_FLIP"], "triplets": acc}
    json.dump(man, open(out_f, "w"), indent=1)
    print(json.dumps({k: man[k] for k in ("n_bases", "funnel", "oracle")}, indent=1))


def auroc(pos, neg):
    s = np.concatenate([pos, neg]); r = rankdata(s)
    n1 = len(pos)
    return float((r[:n1].sum() - n1 * (n1 + 1) / 2) / (n1 * len(neg)))


def stats(pB, pC, pN):
    return {"cf_pair_auroc": auroc(pB, pC), "flip_rank": float(np.mean((pB > pC) + 0.5 * (pB == pC))), "cf_blocked_acc": float(np.mean(pC < 0.5)),
            "null_retention": float(np.mean(pN >= 0.5)), "null_retention_given_base_pos": float(np.mean(pN[pB >= 0.5] >= 0.5)) if (pB >= 0.5).any() else None,
            "base_feasible_acc": float(np.mean(pB >= 0.5)), "mean_drop_base_minus_cf": float(np.mean(pB - pC)), "median_drop": float(np.median(pB - pC)),
            "mean_abs_base_null": float(np.mean(np.abs(pB - pN)))}


def boot(pB, pC, pN, lin, B=2000, seed=0):
    ul, inv = np.unique(lin, return_inverse=True)
    idx = [np.nonzero(inv == g)[0] for g in range(len(ul))]
    rng = np.random.default_rng(seed)
    acc = collections.defaultdict(list)
    for _ in range(B):
        k = np.concatenate([idx[g] for g in rng.integers(0, len(ul), len(ul))])
        for m, v in stats(pB[k], pC[k], pN[k]).items():
            if v is not None:
                acc[m].append(v)
    return {m: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for m, v in acc.items()}


def metrics(dom, man_f, lab_f, sc_f, out_f):
    man = json.load(open(man_f))
    S = {r["qid"]: r for r in jl(sc_f)}
    models = sorted(k for k in next(iter(S.values())) if k.startswith(("ours_s", "grn_s", "piginet_s", "scnet_s", "scnetgrasp_s")))
    res = {"dom": dom, "oracle": man["oracle"], "funnel": man["funnel"], "cohorts": {}}
    for coh in man.get("cohort_names", ("STRONG", "BUDGET", "STRONG+BUDGET")):
        T = [t for t in man["triplets"] if (coh in t["cohort"] if isinstance(t["cohort"], list) else t["cohort"] in coh.split("+"))]
        if not T:
            continue
        lin = np.array([t["lineage"] for t in T])
        out = {"n_triplets": len(T), "by_base_kind": dict(collections.Counter(t["base_kind"] for t in T)), "models": {}}
        fams = sorted({m.rsplit("_s", 1)[0] for m in models})
        for m in models + [f + "_seedmean" for f in fams] + ["constant_0.5"]:
            if m == "constant_0.5":
                pB = pC = pN = np.full(len(T), 0.5)
            elif m.endswith("_seedmean"):
                f = m[:-9]
                g = lambda q: np.mean([S[q][x] for x in models if x.startswith(f + "_s")])  # noqa: E731
                pB, pC, pN = (np.array([g(t[k]) for t in T]) for k in ("base", "cf", "null"))
            else:
                pB, pC, pN = (np.array([S[t[k]][m] for t in T]) for k in ("base", "cf", "null"))
            assert np.isfinite(pB).all() and np.isfinite(pC).all() and np.isfinite(pN).all(), m
            out["models"][m] = {"point": stats(pB, pC, pN), "ci95": boot(pB, pC, pN, lin)}
        res["cohorts"][coh] = out
    json.dump(res, open(out_f, "w"), indent=1)
    for coh, o in res["cohorts"].items():
        print(coh, o["n_triplets"])
        for m, v in o["models"].items():
            p = v["point"]
            print(f"  {m:16s} AUROC {p['cf_pair_auroc']:.3f} {v['ci95'].get('cf_pair_auroc')} flip {p['flip_rank']:.3f} CFacc {p['cf_blocked_acc']:.3f} NULLret {p['null_retention']:.3f} {v['ci95'].get('null_retention')}")


if __name__ == "__main__":
    a = sys.argv[1:]
    {"triplets": lambda: triplets(*a[1:5]), "triplets_ins": lambda: triplets_ins(*a[1:4]), "metrics": lambda: metrics(*a[1:6])}[a[0]]()
