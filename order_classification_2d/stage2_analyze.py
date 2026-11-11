#!/usr/bin/env python3
"""Stage-2 analysis (read-only on the dataset and on the stage-1 artifacts): merges the stage-1 per-scene file with out/run228 (the 4 remaining
permutations of the 228 already-dependent K3 scenes) and writes NEW files only:
  per_scene_six_permutation_outcomes.jsonl     all 5,000 selected scenes; K2: 2 / K3: 6 permutation records each
  k3_success_distribution.json
  order_dependence_failure_phase_summary.json
  rebalancing_availability_and_deficits.json"""
import json, math
from collections import Counter, defaultdict
from pathlib import Path

H = Path(__file__).resolve().parent
DS = Path("/home/naren/Desktop/rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_bd_classquota")
SPLIT = Path("/home/naren/Desktop/rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_relocations_v1/launch_ready_2d_v2/split_manifest.json")
rows = [json.loads(l) for l in open(H / "per_scene_order_classification.jsonl")]
r228 = {}
for l in open(H / "out/run228/results.jsonl"):
    x = json.loads(l)
    assert x["root_id"] not in r228
    r228[x["root_id"]] = x
split = {r["root_id"]: (r["split"], r["root_group_id"]) for r in json.loads(SPLIT.read_text())["roots"]}
where = lambda p: None if p["y"] != 0 else ("target" if p["failed_step"] == "target" else "relocation")

changed = 0
for r in rows:
    if r["K"] not in ("2", "3"):
        continue
    old = r["order_class"]
    if r["root_id"] in r228:
        hist = {json.dumps(p["order"]): p for p in r["permutations"] if p["source"] == "historical"}
        new = r228[r["root_id"]]["perms"]
        for p in new:                                      # historical records must be carried over unchanged
            if p["source"] == "historical":
                h = hist[json.dumps(p["order"])]
                assert (h["y"], h["failed_step"], h["negative_kind"]) == (p["y"], p["failed_step"], p["negative_kind"])
        r["permutations"] = new
    P = r["permutations"]
    ev = [p for p in P if p.get("y") in (0, 1)]
    r["n_perms"], r["n_evaluated"] = len(P), len(ev)
    r["n_success"], r["n_fail"] = sum(p["y"] == 1 for p in ev), sum(p["y"] == 0 for p in ev)
    full = len(ev) == math.factorial(int(r["K"]))
    r["order_class"] = ("ORDER_DEPENDENT" if r["n_success"] and r["n_fail"] else "ORDER_INDEPENDENT" if full and not r["n_fail"] else "UNRESOLVED")
    changed += r["order_class"] != old
    f = [p for p in ev if p["y"] == 0]
    r["fail_relocation"], r["fail_target"] = sum(where(p) == "relocation" for p in f), sum(where(p) == "target" for p in f)
    r["fail_certified"], r["fail_budget"] = sum(p["negative_kind"] == "CERTIFIED" for p in f), sum(p["negative_kind"] != "CERTIFIED" for p in f)
    r["first_step_failures"] = sum(p["failed_step"] == 0 for p in f)
    r["contrast_tier"] = (None if r["order_class"] != "ORDER_DEPENDENT" else
                          "T1_CERTIFIED_RELOCATION" if any(where(p) == "relocation" and p["negative_kind"] == "CERTIFIED" for p in f) else
                          "T2_RELOCATION_BUDGET_ONLY" if r["fail_relocation"] else "T3_TARGET_STEP_ONLY")
    r["split"], r["root_group_id"] = split.get(r["root_id"], (None, None))
    rec = json.loads((DS / "raw/roots" / f"{r['root_id']}.json").read_text())
    r["mechanism"], r["n_obstacles"], r["start_stratum"] = rec["spec"]["mechanism"], len(rec["scene"]["objects"]) - 1, rec["start_stratum"]
assert changed == 0, "a stage-1 class changed"
with open(H / "per_scene_six_permutation_outcomes.jsonl", "w") as fo:
    for r in rows:
        fo.write(json.dumps(r, separators=(",", ":")) + "\n")

K = lambda c: [r for r in rows if r["K"] == c]
dep = lambda c: [r for r in K(c) if r["order_class"] == "ORDER_DEPENDENT"]
ind = lambda c: [r for r in K(c) if r["order_class"] == "ORDER_INDEPENDENT"]
table1 = {("K" + c if c != "NONE" else c): {"total": len(K(c)), "dependent": len(dep(c)), "independent": len(ind(c)),
                                             "unresolved": sum(r["order_class"] == "UNRESOLVED" for r in K(c))} for c in ("0", "1", "2", "3", "NONE")}
k3 = K("3")
dist = {f"{i}/6": sum(r["n_success"] == i for r in k3) for i in range(0, 7)}
newp = [p for r in k3 if r["root_id"] in r228 for p in r["permutations"] if p["source"] == "new"]
(H / "k3_success_distribution.json").write_text(json.dumps({
    "k3_scenes": len(k3), "fully_enumerated": sum(r["n_evaluated"] == 6 for r in k3), "distribution": dist,
    "percent": {k: round(100 * v / len(k3), 2) for k, v in dist.items()},
    "by_source_group": {"stage1_922": {f"{i}/6": sum(r["n_success"] == i for r in k3 if r["root_id"] not in r228) for i in range(1, 7)},
                        "stage2_228": {f"{i}/6": sum(r["n_success"] == i for r in k3 if r["root_id"] in r228) for i in range(1, 7)}},
    "k2_distribution": {f"{i}/2": sum(r["n_success"] == i for r in K("2")) for i in (1, 2)},
    "stage2_new_evaluations": {"count": len(newp), "resolved": sum(p.get("y") in (0, 1) for p in newp), "y1": sum(p.get("y") == 1 for p in newp),
                               "y0": sum(p.get("y") == 0 for p in newp), "errors": [p for p in newp if p.get("y") is None],
                               "cpu_h": round(sum(p["cpu_s"] for p in newp) / 3600, 2)}}, indent=1))


def phase(c):
    D = dep(c)
    F = [p for r in D for p in r["permutations"] if p.get("y") == 0]
    one = [r for r in D if r["n_success"] == 1]
    return {"dependent_scenes": len(D), "tier": dict(Counter(r["contrast_tier"] for r in D)),
            "scenes_with_any_certified_failure": sum(r["fail_certified"] > 0 for r in D), "scenes_budget_limited_failures_only": sum(r["fail_certified"] == 0 for r in D),
            "scenes_with_relocation_and_target_failures": sum(r["fail_relocation"] > 0 and r["fail_target"] > 0 for r in D),
            "failing_orders": len(F), "failing_orders_by_step_and_kind": {f"{k[0]}|{k[1]}": v for k, v in sorted(Counter((str(p["failed_step"]), p["negative_kind"]) for p in F).items())},
            "failing_orders_first_relocation": sum(p["failed_step"] == 0 for p in F),
            "scenes_with_a_first_relocation_failure": sum(r["first_step_failures"] > 0 for r in D),
            "exactly_one_order": {"scenes": len(one), "tier": dict(Counter(r["contrast_tier"] for r in one)),
                                  "all_failures_at_relocation": sum(r["fail_target"] == 0 for r in one),
                                  "all_failures_certified": sum(r["fail_budget"] == 0 for r in one)} if c == "3" else None,
            "tier_by_success_count": {f"{i}/{math.factorial(int(c))}": dict(Counter(r["contrast_tier"] for r in D if r["n_success"] == i)) for i in range(1, math.factorial(int(c)))},
            "by_split": {s: {"dependent": sum(r["split"] == s for r in D), "independent": sum(r["split"] == s for r in ind(c))} for s in ("train", "val", "test")},
            "split_by_tier_and_count": {s: dict(Counter(f'{r["n_success"]}/{math.factorial(int(c))}' for r in D if r["split"] == s)) for s in ("train", "val", "test")},
            "lineage_groups": {"dependent": len({r["root_group_id"] for r in D}), "independent": len({r["root_group_id"] for r in ind(c)}),
                               "groups_with_both": len({r["root_group_id"] for r in D} & {r["root_group_id"] for r in ind(c)})},
            "mechanism": {m: {"dependent": sum(r["mechanism"] == m for r in D), "independent": sum(r["mechanism"] == m for r in ind(c))} for m in sorted({r["mechanism"] for r in K(c)})},
            "home_start": {"dependent": f'{sum(r["start_stratum"] == "S0" for r in D)}/{len(D)}', "independent": f'{sum(r["start_stratum"] == "S0" for r in ind(c))}/{len(ind(c))}'},
            "n_obstacles_median": {"dependent": sorted(r["n_obstacles"] for r in D)[len(D) // 2], "independent": sorted(r["n_obstacles"] for r in ind(c))[len(ind(c)) // 2]}}


ph = {"K2": phase("2"), "K3": phase("3")}
tiers = Counter(r["contrast_tier"] for c in ("2", "3") for r in dep(c))
ph["all"] = {"dependent": sum(tiers.values()), "tier": dict(tiers),
             "possibly_confounded_by_achieved_robot_configuration": tiers["T2_RELOCATION_BUDGET_ONLY"] + tiers["T3_TARGET_STEP_ONLY"],
             "need_qref_connector_and_independent_Y_before_final_XY": {"dependent_scenes": sum(tiers.values()), "independent_scenes": len(ind("2")) + len(ind("3")),
                                                                       "all_K2plus": len(K("2")) + len(K("3"))}}
(H / "order_dependence_failure_phase_summary.json").write_text(json.dumps(ph, indent=1))

# excluded scenes (existing records only)
A = json.load(open(H.parent / "approach_b_reuse_audit/order_audit_2d.json"))["scenes_dependent"]
lin = {x["root_id"]: x for x in json.load(open(H / "excluded131_lineage.json"))}
exc = {}
for k in (2, 3, 4):
    xs = [x for x in A.values() if x["verified_K"] == k]
    a = [x for x in xs if x["category"] == "A_order_dependent"]
    mov = [x for x in a if lin[x["root_id"]]["fixed_ids"] == 0]
    exc[f"K{k}"] = {"scenes": len(xs), "order_dependent_recorded": len(a), "no_contrast_recorded": len(xs) - len(a),
                    "orders_recorded_per_scene": dict(Counter(x["n_orders_recorded"] for x in xs)), "additional_permutations_recorded": sum(x["other_perms_recorded"] for x in xs),
                    "exactly_one_OBSERVED_successful_order": sum(x["orders_success"] == 1 for x in a),
                    "exactly_one_VERIFIED_across_all_orders": sum(x["orders_success"] == 1 and x["n_orders_recorded"] == x["n_orders_possible"] for x in a),
                    "certified_failing_order": sum(any(d["negative_kind"] == "CERTIFIED" for d in x["orders_fail_detail"]) for x in a),
                    "fails_on_first_relocation": sum(any(d["failed_step"] == 0 for d in x["orders_fail_detail"]) for x in a),
                    "movable_only_dependent": len(mov), "with_immovable_structures_dependent": len(a) - len(mov),
                    "identical_scene_in_selected": sum(bool(lin[x["root_id"]]["dup_scene_in_selected"]) for x in xs),
                    "same_parent_family_as_a_selected_scene": sum(bool(lin[x["root_id"]]["family_in_selected"]) for x in a),
                    "movable_only_and_family_disjoint": sum(not lin[x["root_id"]]["family_in_selected"] for x in mov),
                    "is_conversion_of_another_root": sum(bool(lin[x["root_id"]]["is_conversion_of"]) for x in xs)}

# rebalancing arithmetic (availability only; no selection is made)
quota = {"K2": 800, "K3": 1150}
have = {"K2": (len(dep("2")), len(ind("2"))), "K3": (len(dep("3")), len(ind("3")))}
pools = {"evidence_eligible_all_excluded": {k: exc[k]["order_dependent_recorded"] for k in quota},
         "dataset_rule_compatible_movable_only": {k: exc[k]["movable_only_dependent"] for k in quota}}
reb = {"quota": quota, "selected": {k: {"dependent": v[0], "independent": v[1]} for k, v in have.items()}, "excluded_pools": pools, "scenarios": {}}
for name, pool in pools.items():
    S = {}
    for ratio in (0.60, 0.70, 0.75):
        per, tot_need = {}, 0
        for k, q in quota.items():
            need = math.ceil(ratio * q)
            d0, i0 = have[k]
            add = min(pool[k], max(0, need - d0))
            per[k] = {"required_dependent": need, "required_independent": q - need, "selected_dependent_retained": d0, "excluded_dependent_added": add,
                      "independent_removed": i0 - (q - need), "independent_retained": q - need, "dependent_deficit": max(0, need - d0 - add),
                      "max_dependent_share_existing_only_pct": round(100 * (d0 + pool[k]) / q, 2), "feasible_existing_only": need <= d0 + pool[k]}
        allq = sum(quota.values())
        need_all = math.ceil(ratio * allq)
        avail = sum(have[k][0] + pool[k] for k in quota)
        S[f"{int(ratio * 100)}:{100 - int(ratio * 100)}"] = {"per_class": per, "overall": {"required_dependent": need_all, "required_independent": allq - need_all, "available_dependent": avail,
                                                                                         "dependent_deficit": max(0, need_all - avail), "feasible_existing_only": need_all <= avail,
                                                                                         "sum_of_per_class_deficits": sum(v["dependent_deficit"] for v in per.values())}}
    reb["scenarios"][name] = S
reb["upper_bound_dependent_K2plus"] = {n: sum(have[k][0] + p[k] for k in quota) for n, p in pools.items()}
reb["excluded"] = exc
reb["note"] = ("LEGACY dependence only. Connector-valid (q_ref) X and independent Y are not established for any scene here; "
               "T3 target-step-only scenes are the most likely to stop being order-dependent under final X/Y.")
(H / "rebalancing_availability_and_deficits.json").write_text(json.dumps(reb, indent=1))
print(json.dumps({"table1": table1, "k3_dist": dist, "phase": ph, "excluded": exc, "rebalancing": {n: {r: {"per_class": {k: (v["required_dependent"], v["excluded_dependent_added"], v["independent_removed"], v["dependent_deficit"]) for k, v in s["per_class"].items()}, "overall": s["overall"]} for r, s in S.items()} for n, S in reb["scenarios"].items()}, "upper": reb["upper_bound_dependent_K2plus"]}, indent=1))
