"""P13 analyses on frozen predictions only (no fitting, no label edits): P13-0 corrected P12 kappa estimand + zero-interaction
baseline + strict D / scene-edit correspondence; later stages add factor audits and targeted endpoints here."""
from __future__ import annotations

import collections
import math

import numpy as np

import config as cf
import p12_closure as p12
from p13_pipeline import OUT

ARMS = p12.FROZEN_ARMS
V, C = "VERIFIED_FEASIBLE", "CERTIFIED_INFEASIBLE"


def _paired(e, a, b, ks=None):
    """Root-paired Delta = e[a] - e[b] (positive = b better), exact two-sided sign test (ties removed), bootstrap CI."""
    ks = sorted(set(e[a]) & set(e[b])) if ks is None else ks
    d = [e[a][k] - e[b][k] for k in ks]
    p, pos, neg, ties = p12._sign(d)
    return {"roots": len(d), "mean_delta": float(np.mean(d)) if d else None, "ci95": p12._boot(d), "p_raw": p,
            f"{b}_better": pos, f"{a}_better": neg, "ties": ties,
            "effect_size_d": float(np.mean(d) / np.std(d, ddof=1)) if len(d) > 2 and np.std(d) > 0 else None}


def p12_four_tuples():
    snap, P, rec = p12._rd(p12.HOLD / "PREDICTIONS_FROZEN.json"), p12.plans(), {}
    for b in sorted(p12.HOLD.glob("batch*/plan.json")):
        rec |= p12.sealed_records(b.parent.name)
    four = {}
    for k, r in P.items():
        t = {it["token"]: it["query"] for it in r["items"]}
        qs = [t[""], t["edit:A"], t["edit:B"], t["edit:A+B"]]
        st = [rec.get(q, {}).get("teacher_status") for q in qs]
        if all(s in (V, C) for s in st):
            y = [int(s == V) for s in st]
            four[k] = {"q": qs, "y": y, "kappa": y[3] - y[1] - y[2] + y[0], "family": r["family"], "status": st}
    return snap, P, four


def kappa_correction() -> dict:
    """P12 primary F3 / F5s under the PREREGISTERED estimand |mean_s khat_s - kappa| (seed-averaged marginals), next to the
    published seed-wise statistic mean_s |khat_s - kappa|; constant-zero and no-coupling controls; stratified by kappa and truth pattern."""
    snap, P, four = p12_four_tuples()
    ks_ = collections.defaultdict(dict)                       # arm -> root -> [khat per seed 0..2]
    for a in snap["arms"].values():
        for k, f in four.items():
            m = a["roots"][k].get("marginals") or {}
            if all(q in m for q in f["q"]):
                q0, qa, qb, qab = f["q"]
                ks_[a["arm"]].setdefault(k, {})[a["seed"]] = m[qab] - m[qa] - m[qb] + m[q0]
    full = {arm: {k: v for k, v in d.items() if sorted(v) == [0, 1, 2]} for arm, d in ks_.items()}
    pre = {arm: {k: abs(float(np.mean(list(v.values()))) - four[k]["kappa"]) for k, v in d.items()} for arm, d in full.items()}
    sw = {arm: {k: float(np.mean([abs(x - four[k]["kappa"]) for x in v.values()])) for k, v in d.items()} for arm, d in full.items()}
    pre["ZERO"] = sw["ZERO"] = {k: float(abs(f["kappa"])) for k, f in four.items()}
    out = {"cohort": {"N": len(four), "kappa": dict(collections.Counter(f["kappa"] for f in four.values())),
                      "truth_patterns_y0_yA_yB_yAB": dict(collections.Counter("".join(map(str, f["y"])) for f in four.values()))}}
    for name, e in (("preregistered_seed_mean_marginals", pre), ("published_seedwise_errors", sw)):
        prim = {"F3": _paired(e, "B-F3", "K-B"), "F5s": _paired(e, "B-F5s", "K-B")}
        h = p12._holm({t: v["p_raw"] for t, v in prim.items()})
        for t in prim:
            prim[t]["p_holm"] = h[t]
            prim[t]["verdict"] = ("CONFIRMED" if h[t] < 0.05 and prim[t]["mean_delta"] > 0 else
                                  "SIGNIFICANT_REVERSAL" if h[t] < 0.05 else "NOT_CONFIRMED")
        out[name] = {"primary": prim, "mae": {a: float(np.mean(list(v.values()))) for a, v in e.items()},
                     "mae_by_kappa": {a: {str(c): float(np.mean([v[k] for k in v if four[k]["kappa"] == c])) for c in (-1, 0, 1)
                                          if any(four[k]["kappa"] == c for k in v)} for a, v in e.items()},
                     "B_vs_zero": _paired(e, "ZERO", "K-B"), "B_vs_SF": _paired(e, "SF", "K-B")}
    mean_khat = {arm: {k: float(np.mean(list(v.values()))) for k, v in d.items()} for arm, d in full.items()}
    out["false_interaction_on_kappa0"] = {a: {"rate_nearest_integer_nonzero": float(np.mean([abs(v[k]) >= 0.5 for k in v if four[k]["kappa"] == 0])),
                                              "mean_abs_khat": float(np.mean([abs(v[k]) for k in v if four[k]["kappa"] == 0]))}
                                          for a, v in mean_khat.items()}
    out["by_family_preregistered"] = {t: {f: float(np.mean([pre[abl][k] - pre["K-B"][k] for k in pre["K-B"] if four[k]["family"] == f]))
                                          for f in sorted({x["family"] for x in four.values()})} for t, abl in (("F3", "B-F3"), ("F5s", "B-F5s"))}
    out["per_variable_bce_not_joint"] = _bce(snap, four)
    old = p12._rd("runs/p12/p12_4/FACTOR_TESTS.json")["primary"]
    out["published_reproduced"] = {t: abs(out["published_seedwise_errors"]["primary"][t]["mean_delta"] - old[t]["mean_delta"]) < 1e-12 and
                                   abs(out["published_seedwise_errors"]["primary"][t]["p_holm"] - old[t]["p_holm"]) < 1e-12 for t in ("F3", "F5s")}
    out["mean_khat_seed_mean"] = mean_khat
    out["per_root"] = {k: {"kappa": f["kappa"], "y": f["y"], "family": f["family"]} for k, f in four.items()}
    (OUT / "p13_0").mkdir(parents=True, exist_ok=True)
    cf.write_json(OUT / "p13_0" / "KAPPA_CORRECTED.json", out)
    return out


def _bce(snap, four):
    """Mean per-variable binary NLL over the four fixed-q0 bits (seed-mean marginals). NOT a joint likelihood."""
    v = collections.defaultdict(list)
    for arm in ARMS:
        for k, f in four.items():
            ps = [a["roots"][k]["marginals"] for a in snap["arms"].values() if a["arm"] == arm and a["roots"][k].get("marginals")]
            if len(ps) == 3:
                for q, y in zip(f["q"], f["y"]):
                    p = min(max(float(np.mean([m[q] for m in ps])), 1e-9), 1 - 1e-9)
                    v[arm].append(-math.log(p if y else 1 - p))
    return {a: float(np.mean(x)) for a, x in v.items()}


def _strict(r, k):
    """Exact D <-> scene-edit correspondence for one root: every parking subset of the pool is a planned item whose edit equals the
    parking map restricted to that subset, keyed by the same object ids, evaluated at the root's q0 (empty subset = the executed empty
    repair, i.e. the original task). Returns (subset -> query) or the failure reason."""
    import p10b_scenes as pb
    import itertools
    inv, pool = {v: kk for kk, v in r["ids"].items()}, list(r["parking"])
    byq = {it["query"]: it for it in r["items"]}
    lat = {}
    for n in range(len(pool) + 1):
        for sub in itertools.combinations(pool, n):
            roles = sorted(inv[o] for o in sub)
            ed = {o: r["parking"][o] for o in sub}
            q = pb._query_id(k, "ORDERED_TEACHER", []) if not sub else pb._query_id(k, "SCENE_TARGET_ONLY", ed)
            it = byq.get(q)
            if it is None:
                return None, "parking subset not in the frozen catalogue"
            if it.get("d_subset") is None or sorted(it["d_subset"]) != roles:
                return None, "subset label differs from the parking subset"
            if sub and (it["kind"] != "SCENE_TARGET_ONLY" or it["edit"] != ed):
                return None, "edit dict differs from the parking map"
            if not sub and (it["kind"] != "ORDERED_TEACHER" or it["sequence"]):
                return None, "original is not the empty fixed-q0 repair"
            lat[frozenset(pool.index(o) for o in sub)] = q
    return lat, None


def d_strict(cohort="p10b") -> dict:
    """D / D-pairless / geometry vs A / B / C / SF blocker attribution on roots whose whole parking lattice is exactly the scored
    scene-edit queries (_strict). Per-arm coverage and NO_PREDICTED_CLEARING_SET are reported; scores are on the same common roots,
    with a no-clearing-set choice scored as a miss (F1 0, exact 0), never as an empty blocker set; seed-level masks, metrics averaged."""
    import p11_closure as q
    snap, P, rec, dl, roots, get, heur = p12._cohort(cohort)
    inf = {k: dl[k] for k in roots if dl[k]["mask"] is not None and dl[k]["y0"] == 0 and dl[k]["n"] > 0}
    lat, why = {}, collections.Counter()
    for k in inf:
        L, w = _strict(P[k], k)
        (lat.__setitem__(k, L) if L else why.update([w]))
    preds, nopred, cover = collections.defaultdict(dict), collections.Counter(), collections.defaultdict(set)
    for n, a in snap["arms"].items():
        if a["arm"] not in ("A", "SF", "K-B", "K-C") or a.get("regime", "full") != "full":
            continue
        for k, L in lat.items():
            m = (get("arms", n, k) or {}).get("marginals") or {}
            if not all(x in m for x in L.values()):
                continue
            st = {s: m[x] for s, x in L.items()}
            pm = None if not any(p >= 0.5 for p in st.values()) else q._derived_mask(st, inf[k]["n"])
            nopred[a["arm"]] += pm is None
            preds[a["arm"]].setdefault(k, []).append(pm)
    for arm, d in preds.items():
        cover[arm] = {k for k, v in d.items() if len(v) == 3}
    for n, x in snap["d"].items():
        if x["lambda_B"] == snap["baselines"][f"{x['arm']}_lambda_B"]:
            thr = snap["baselines"][f"{x['arm']}_threshold"]
            for k in inf:
                v = get("d", n, k)
                preds[x["arm"]].setdefault(k, []).append([int(v["p_feasible"] < 0.5 and mm >= thr) for mm in v["marg"]])
    preds["geometry_heuristic"] = {k: [heur[k]] for k in inf}
    arms = ("D", "D-pairless", "geometry_heuristic", "K-B", "K-C", "A", "SF")
    common = sorted(set(lat).intersection(*[cover[a] for a in ("K-B", "K-C", "A", "SF")])) if lat else []
    allpred = [k for k in common if all(pm is not None for a in ("K-B", "K-C", "A", "SF") for pm in preds[a][k])]
    miss = {"precision": 0.0, "recall": 0.0, "f1": 0.0, "exact": 0.0, "jaccard": 0.0}
    def score(arm, ks):
        return {k: {m: float(np.mean([(q._set_metrics(inf[k]["mask"], pm) if pm is not None else miss)[m] for pm in preds[arm][k]]))
                    for m in miss} for k in ks}
    agg = lambda per: {"roots": len(per)} | {m: float(np.mean([v[m] for v in per.values()])) if per else None for m in miss}  # noqa: E731
    out = {"cohort": cohort, "infeasible_complete_masks": len(inf), "strict_lattice_roots": len(lat), "strict_failures": dict(why),
           "coverage_full_lattice_3_seeds": {a: len(cover[a]) for a in ("K-B", "K-C", "A", "SF")},
           "NO_PREDICTED_CLEARING_SET_choices": dict(nopred), "common_N": len(common), "all_arms_predict_N": len(allpred),
           "common_proof_grounded_N": sum(inf[k]["provenance"] == "proof_grounded" for k in common)}
    for name, ks in (("common_conservative", common), ("common_all_arms_predict", allpred),
                     ("common_proof_grounded", [k for k in common if inf[k]["provenance"] == "proof_grounded"]),
                     ("common_operational", [k for k in common if inf[k]["provenance"] != "proof_grounded"])):
        per = {a: score(a, ks) for a in arms}
        out[name] = {"arms": {a: agg(per[a]) for a in arms},
                     "paired_f1_vs_D": {a: _paired({x: {k: v["f1"] for k, v in per[x].items()} for x in ("D", a)}, a, "D") for a in arms if a != "D"} if len(ks) > 1 else None}
    p12old = p12._rd(f"runs/p12/p12_6/D_SEMANTICS_{cohort}.json")["matched"]
    out["p12_published_matched_N"] = p12old["matched_infeasible_N"]
    cf.write_json(OUT / "p13_0" / f"D_STRICT_{cohort}.json", out)
    return out
