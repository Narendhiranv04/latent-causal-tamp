#!/usr/bin/env python3
"""Dependent-share requirements for 2D (existing 5,000) and 3D (planned 2,500) target-task datasets, from the finished audits only.
Writes 3D_2D_REBALANCING_REQUIREMENTS.json (the .md report quotes it)."""
import json, math
from pathlib import Path

H = Path(__file__).resolve().parent
d3 = json.loads((H / "3D_ORDER_AUDIT_SUMMARY.json").read_text())
p3 = [json.loads(l) for l in open(H / "3D_ORDER_CLASSIFICATION_PER_SCENE.jsonl")]
r2 = json.loads((H.parent / "order_classification_2d/rebalancing_availability_and_deficits.json").read_text())
k2d = json.loads((H.parent / "order_classification_2d/k3_success_distribution.json").read_text())
RATIOS = (0.60, 0.70, 0.75)


def domain(name, quota, dep, ind, excl, excl_movable, hard16, published, unpublished):
    out = {"quota": quota, "published": published, "not_yet_uploaded": unpublished, "existing": {}, "ratios": {}}
    for k in quota:
        out["existing"][k] = {"dependent": dep[k], "independent": ind[k], "excluded_dependent_eligible": excl[k],
                              "excluded_dependent_rule_compatible": excl_movable[k]}
    out["existing"]["hard_K3_1of6"] = hard16
    tot = sum(quota.values())
    out["strict_majority_needs"] = tot // 2 + 1
    for r in RATIOS:
        per = {}
        for k, q in quota.items():
            need = math.ceil(r * q)
            have = dep[k] + excl[k]
            keep_ind = q - need
            per[k] = {"required_dependent": need, "required_independent": keep_ind, "existing_dependent": dep[k], "excluded_added": min(excl[k], max(0, need - dep[k])),
                      "existing_independent_to_drop": max(0, ind[k] - keep_ind), "deficit_after_existing": max(0, need - have),
                      "unpublished_slots": unpublished.get(k, 0),
                      "deficit_after_existing_if_all_unpublished_dependent": max(0, need - have - unpublished.get(k, 0)),
                      "feasible_existing_only": need <= have}
        need_all = math.ceil(r * tot)
        have_all = sum(dep.values()) + sum(excl.values())
        out["ratios"][f"{round(r * 100)}:{round(100 - r * 100)}"] = {"per_class": per, "total_required_dependent": need_all, "total_existing_plus_excluded": have_all,
                                                                     "total_deficit": max(0, need_all - have_all), "sum_per_class_deficit": sum(v["deficit_after_existing"] for v in per.values()),
                                                                     "targeted_generation_necessary": need_all > have_all + sum(unpublished.values())
                                                                     or any(v["deficit_after_existing_if_all_unpublished_dependent"] > 0 for v in per.values())}
    obs_dep, obs_tot = sum(dep.values()), sum(published.values())
    out["observed_dependent_share_published_pct"] = round(100 * obs_dep / obs_tot, 2)
    out["final_dependent_range_if_unpublished_arrive"] = {"min_all_unpublished_independent": obs_dep, "max_all_unpublished_dependent": obs_dep + sum(unpublished.values()),
                                                          "min_pct": round(100 * obs_dep / tot, 2), "max_pct": round(100 * (obs_dep + sum(unpublished.values())) / tot, 2),
                                                          "note": "a range, not evidence: the unpublished scenes are not observed"}
    return out


t1 = d3["table1"]
ex = d3["mechanisms"]["excluded_and_k4"]
e3 = {"2": ex["K2"]["reverse_failed"], "3": ex["K3"]["reverse_failed"]}         # excluded DEPENDENT with a recorded failing reverse
hard3 = d3["k3_distribution"]["1/6"]
res = {"2D": domain("2D", {"2": 800, "3": 1150}, {"2": 105, "3": 498}, {"2": 695, "3": 652},
                    {"2": 107, "3": 21}, {"2": 19, "3": 2}, k2d["distribution"]["1/6"], {"2": 800, "3": 1150}, {}),
       "3D": domain("3D", {"2": 612, "3": 612}, {"2": t1["2"]["dependent"], "3": t1["3"]["dependent"]}, {"2": t1["2"]["independent"], "3": t1["3"]["independent"]},
                    e3, e3, hard3, {"2": t1["2"]["total"], "3": t1["3"]["total"]}, {"2": 612 - t1["2"]["total"], "3": 612 - t1["3"]["total"]})}
res["3D"]["unresolved_published"] = {"2": t1["2"]["unresolved"], "3": t1["3"]["unresolved"]}
res["notes"] = ["Ratios enforced within K2 and within K3; K4 never fills a K2/K3 quota.",
                "2D excluded 'rule_compatible' = movable-only (all selected 2D scenes are movable-only); 3D excluded fixed-object check status is not recorded.",
                "All dependence here is LEGACY (carried arm state, target from the achieved pose); connector-valid X can differ (see the 3D finalized-X table).",
                "The teammate's pending 3D generation keeps the independence rule (DEPENDENT scenes are not counted), so its scenes are not designed to be order-dependent."]
(H / "3D_2D_REBALANCING_REQUIREMENTS.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
