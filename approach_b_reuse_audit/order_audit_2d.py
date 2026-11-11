#!/usr/bin/env python3
"""READ-ONLY order-dependence audit of the 2D class-quota target-task dataset (Narendhiranv04/rss-ebm-infeasibility, yadu/dataset-3d,
gh-yadu-iiith/planar_2d/dataset_bd_classquota).  Reads selected.json, raw/ledger.jsonl, raw/roots/*.json and checks that raw/witnesses files
exist.  No physics, no planner, no writes to the dataset.  Output: order_audit_2d.json next to this script.

Outcome semantics (dataset-bd/bd_2d.py seq() -> p16_common.verify_sequence): steps executed on the carried state (cells AND robot q), T planned
from the robot state reached after the last relocation (legacy combined target-from-achieved-state; NOT a q_ref connector-valid Approach B X).
failed_step = relocation index (int) or "target"; y=0 negatives keep no witnesses; NO_PLAN_FOUND / TIMEOUT are budgeted, CERTIFIED is proven."""
import itertools, json, math, os, sys
from collections import Counter, defaultdict
from pathlib import Path

D = Path(sys.argv[1] if len(sys.argv) > 1 else
         "/home/naren/Desktop/rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_bd_classquota")
sel = json.loads((D / "selected.json").read_text())["selected"]
cls = {r: k for k, v in sel.items() for r in v}
ledger = [json.loads(l) for l in open(D / "raw/ledger.jsonl")]
dep_lines = [x for x in ledger if x.get("observed") == "DEPENDENT"]
dep_ids = [x["root_id"] for x in dep_lines]


def wit_ok(b):
    """success entry: one witness per executed action (relocations + T), every file present"""
    w = b.get("witnesses") or []
    return len(w) == b["n_actions"] and all((D / "raw/witnesses" / x[:2] / f"{x}.npz").exists() for x in w)


def scene(rid):
    d = json.loads((D / "raw/roots" / f"{rid}.json").read_text())
    B = d["labels"].get("B") or []
    mini = next((b for b in B if b["role"] == "minimal"), None)
    k = d.get("verified_K")
    out = {"root_id": rid, "verified_K": k, "observed": d.get("observed"), "independent_moves": d.get("independent_moves"),
           "method": (d.get("construction") or {}).get("method"), "generator": d.get("generator_version_plus"),
           "original_y": d["labels"]["original"]["y"], "original_kind": d["labels"]["original"].get("negative_kind")}
    # group recorded B entries by assignment (object->dest map, each object once); a permutation contrast = same map, different order
    groups = defaultdict(dict)
    for b in B:
        seq = [tuple(s) for s in b["sequence"]]
        if len({o for o, _ in seq}) != len(seq):
            continue
        groups[frozenset(seq)][tuple(seq)] = b
    out["min_recorded"] = bool(mini and mini["y"] == 1)
    out["min_witness_ok"] = bool(mini and mini["y"] == 1 and wit_ok(mini))
    if mini:
        A = frozenset(tuple(s) for s in mini["sequence"])
        orders = groups[A]
        n = len(mini["sequence"])
        out["min_seq"] = mini["sequence"]
        out["n_orders_recorded"] = len(orders)
        out["n_orders_possible"] = math.factorial(n)
        succ = [o for o, b in orders.items() if b["y"] == 1]
        fail = [o for o, b in orders.items() if b["y"] == 0]
        out["orders_success"] = len(succ)
        out["orders_fail"] = len(fail)
        out["orders_fail_detail"] = [{"order": [list(x) for x in o], "failed_step": orders[o]["failed_step"], "negative_kind": orders[o]["negative_kind"],
                                      "role": orders[o]["role"]} for o in fail]
        out["success_witness_ok"] = all(wit_ok(orders[o]) for o in succ)
        rev = tuple(reversed([tuple(s) for s in mini["sequence"]]))
        rb = orders.get(rev) if n >= 2 else None
        out["reverse"] = None if rb is None else {"y": rb["y"], "failed_step": rb["failed_step"], "negative_kind": rb["negative_kind"],
                                                  "witness_ok": wit_ok(rb) if rb["y"] == 1 else None, "role": rb["role"]}
        out["other_perms_recorded"] = len([o for o in orders if o not in (tuple(tuple(s) for s in mini["sequence"]), rev)])
        # implied-but-unrecorded attempts: bd_2d.teach tries permutations of the clearing set sorted by distance to T (ties by id), stopping at the
        # first success (<= MAX_ORDERS=6); permutations enumerated before the stored minimal were attempted and returned y=0, outcome not stored
        obj = {o["id"]: o for o in d["scene"]["objects"]}
        T = obj["t0"]["xy_m"]
        base = sorted([o for o, _ in mini["sequence"]], key=lambda o: (math.dist(obj[o]["xy_m"], T), o))
        perms = list(dict.fromkeys(itertools.permutations(base)))[:6]
        mo = tuple(o for o, _ in mini["sequence"])
        out["min_perm_index"] = perms.index(mo) if mo in perms else None
    # any other assignment group with >= 2 recorded orders (e.g. alternative clearing sets)
    out["other_groups_contrast"] = sum(1 for g, o in groups.items() if (not mini or g != frozenset(tuple(s) for s in mini["sequence"]))
                                       and len(o) >= 2 and len({b["y"] for b in o.values()}) == 2)
    out["other_groups_multiorder"] = sum(1 for g, o in groups.items() if (not mini or g != frozenset(tuple(s) for s in mini["sequence"])) and len(o) >= 2)
    return out


def category(s):
    k = s["verified_K"]
    if k is None:
        return "G_NONE"
    if k in (0, 1):
        return "F_K0_K1"
    if not s["min_recorded"]:
        return "E_inconclusive"
    if s["orders_success"] >= 1 and s["orders_fail"] >= 1:
        return "A_order_dependent"
    if s["orders_success"] == s["n_orders_possible"]:
        return "B_order_independent_K2" if k == 2 else "D_fully_order_independent_K3plus"
    if s["orders_success"] >= 2:
        return "C_partially_order_compatible"
    return "E_inconclusive"


S = {r: scene(r) for r in cls}
for r in S:
    S[r]["class"] = cls[r]
    S[r]["category"] = category(S[r])
DEP = {}
for r in dep_ids:
    if (D / "raw/roots" / f"{r}.json").exists():
        DEP[r] = scene(r)
        DEP[r]["category"] = category(DEP[r])
    else:
        DEP[r] = {"root_id": r, "missing_file": True, "category": "MISSING_FILE"}

res = {"source": str(D), "selected_by_class": {k: len(v) for k, v in sel.items()}, "selected_total": len(cls),
       "selected_files_present": sum((D / "raw/roots" / f"{r}.json").exists() for r in cls),
       "verified_K_matches_class": sum(str(S[r]["verified_K"] if S[r]["verified_K"] is not None else "NONE") == S[r]["class"] for r in S),
       "independent_moves_true_selected": sum(bool(S[r]["independent_moves"]) for r in S),
       "dependent_ledger_lines": len(dep_lines), "dependent_unique_roots": len(set(dep_ids)),
       "dependent_overlap_selected": len(set(dep_ids) & set(cls)), "dependent_files_present": sum(not DEP[r].get("missing_file") for r in DEP),
       "dependent_independent_moves_flag": dict(Counter(str(DEP[r].get("independent_moves")) for r in DEP)),
       "dependent_ledger_verified_K": dict(Counter(str(x.get("verified_K")) for x in dep_lines)),
       "table1": {}, "table2": {}, "table4": {}, "none": {}, "scenes_selected": S, "scenes_dependent": DEP}
for c in ("0", "1", "2", "3", "NONE"):
    rows = [S[r] for r in sel[c]]
    res["table1"][c] = dict(Counter(x["category"] for x in rows), total=len(rows))
for k in (2, 3, 4):
    rows = [x for x in DEP.values() if x.get("verified_K") == k]
    res["table2"][str(k)] = {"count": len(rows), "category": dict(Counter(x["category"] for x in rows)),
                             "min_success_witness_ok": sum(x["min_witness_ok"] for x in rows),
                             "contrast_fail_recorded": sum(x["orders_fail"] >= 1 for x in rows if x["min_recorded"]),
                             "reverse_fail_kind": dict(Counter(f'{x["reverse"]["failed_step"] if isinstance(x["reverse"]["failed_step"], str) else "relocation"}:{x["reverse"]["negative_kind"]}'
                                                               for x in rows if x.get("reverse") and x["reverse"]["y"] == 0)),
                             "fully_usable": sum(x["category"] == "A_order_dependent" and x["min_witness_ok"] for x in rows),
                             "original_y": dict(Counter(x["original_y"] for x in rows))}


def t4(rows):
    rv = [x for x in rows if x.get("reverse")]
    return {"denominator": len(rows), "min_success_recorded": sum(x["min_recorded"] for x in rows),
            "min_success_witness_ok": sum(x["min_witness_ok"] for x in rows), "reverse_attempted": len(rv),
            "reverse_success": sum(x["reverse"]["y"] == 1 for x in rv),
            "reverse_fail_relocation": sum(x["reverse"]["y"] == 0 and not isinstance(x["reverse"]["failed_step"], str) for x in rv),
            "reverse_fail_target": sum(x["reverse"]["y"] == 0 and x["reverse"]["failed_step"] == "target" for x in rv),
            "reverse_fail_kinds": dict(Counter(f'{"target" if x["reverse"]["failed_step"] == "target" else "relocation"}:{x["reverse"]["negative_kind"]}' for x in rv if x["reverse"]["y"] == 0)),
            "other_perms_recorded": sum(x.get("other_perms_recorded", 0) > 0 for x in rows),
            "all_perms_evaluated": sum(x.get("n_orders_recorded") == x.get("n_orders_possible") for x in rows if x["min_recorded"]),
            "implied_unrecorded_earlier_perm_attempts": sum((x.get("min_perm_index") or 0) > 0 for x in rows),
            "min_perm_index_hist": dict(Counter(str(x.get("min_perm_index")) for x in rows)),
            "success_witness_missing_or_incomplete": sum(not x.get("success_witness_ok", False) for x in rows if x["min_recorded"]),
            "other_assignment_groups_multiorder": sum(x["other_groups_multiorder"] > 0 for x in rows),
            "other_assignment_groups_contrast": sum(x["other_groups_contrast"] > 0 for x in rows)}


res["table4"] = {"selected_K2": t4([S[r] for r in sel["2"]]), "selected_K3": t4([S[r] for r in sel["3"]]),
                 "dependent_K2": t4([x for x in DEP.values() if x.get("verified_K") == 2]),
                 "dependent_K3": t4([x for x in DEP.values() if x.get("verified_K") == 3]),
                 "dependent_K4": t4([x for x in DEP.values() if x.get("verified_K") == 4])}
none = [S[r] for r in sel["NONE"]]
res["none"] = {"total": len(none), "method": dict(Counter(str(x["method"]) for x in none)),
               "certified_construction_none_cover2d": sum(x["method"] == "none_cover2d" for x in none),
               "original_kind": dict(Counter(str(x["original_kind"]) for x in none))}
out = Path(__file__).with_name("order_audit_2d.json")
out.write_text(json.dumps(res, indent=1, default=list))
print(json.dumps({k: res[k] for k in res if not k.startswith("scenes_")}, indent=1, default=list))
