#!/usr/bin/env python3
"""Final order classification of the selected 5,000 2D target-task scenes from (a) historical labels.B records and (b) the additive sidecar
out/run/results.jsonl (missing K3 permutations evaluated with the pinned teacher).  Writes per_scene_order_classification.jsonl and
order_classification_summary.json.  Read-only on the dataset."""
import hashlib, itertools, json, math
from collections import Counter
from pathlib import Path

H = Path(__file__).resolve().parent
DS = Path("/home/naren/Desktop/rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_bd_classquota")
sel = json.loads((DS / "selected.json").read_text())["selected"]
run = {}
for l in (H / "out/run/results.jsonl").read_text().splitlines():
    x = json.loads(l)
    run[x["root_id"]] = x                                   # resumable appends: one line per finished root (verified unique below)
run_lines = len((H / "out/run/results.jsonl").read_text().splitlines())
repro = [json.loads(l) for l in (H / "out/repro/results.jsonl").read_text().splitlines()]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def hist_perm(b, role=None):
    return {"order": b["sequence"], "source": "historical", "role": role or b["role"], "y": b["y"], "reason": b["reason"],
            "failed_step": b["failed_step"], "negative_kind": b["negative_kind"], "witnesses": b["witnesses"]}


def where(p):
    return None if p["y"] != 0 else ("target" if p["failed_step"] == "target" else "relocation")


rows, implied = [], {"scenes": 0, "implied_perms": 0, "new_confirms_failure": 0, "new_success_contradicts": 0, "unresolved": 0}
for cls in ("0", "1", "2", "3", "NONE"):
    for rid in sel[cls]:
        p = DS / "raw/roots" / f"{rid}.json"
        rec = json.loads(p.read_text())
        row = {"root_id": rid, "K": cls, "source_sha256": sha(p), "geometry_impl": rec.get("geometry_impl") or "original",
               "construction_method": (rec.get("construction") or {}).get("method")}
        if cls in ("0", "1", "NONE"):
            row["order_class"] = "NOT_APPLICABLE"
            if cls == "NONE":
                row["none_kind"] = "CERTIFIED_CONSTRUCTION" if row["construction_method"] == "none_cover2d" else "NO_REPAIR_FOUND"
            rows.append(row)
            continue
        B = rec["labels"]["B"]
        mini = next(b for b in B if b["role"] == "minimal" and b["y"] == 1)
        assign = [tuple(s) for s in mini["sequence"]]
        row["successful_original_sequence"] = mini["sequence"]
        row["assignment"] = sorted([list(s) for s in assign])
        recd = {tuple(tuple(s) for s in b["sequence"]): b for b in B}
        perms = []
        if rid in run:
            perms = run[rid]["perms"]
        else:
            for q in itertools.permutations(assign):
                if q in recd:
                    perms.append(hist_perm(recd[q]))
                else:
                    perms.append({"order": [list(s) for s in q], "source": "not_evaluated", "y": None})
        row["permutations"] = perms
        ev = [q for q in perms if q.get("y") in (0, 1)]
        unres = [q for q in perms if q.get("y") is None]
        ns, nf = sum(q["y"] == 1 for q in ev), sum(q["y"] == 0 for q in ev)
        if ns >= 1 and nf >= 1:
            row["order_class"] = "ORDER_DEPENDENT"
        elif ns == len(perms) == math.factorial(len(assign)):
            row["order_class"] = "ORDER_INDEPENDENT"
        else:
            row["order_class"] = "UNRESOLVED"
            row["unresolved_reason"] = sorted({q.get("resolution") or q["source"] for q in unres})
        row["n_perms"], row["n_evaluated"], row["n_success"], row["n_fail"] = len(perms), len(ev), ns, nf
        row["contrast_location"] = (None if row["order_class"] != "ORDER_DEPENDENT" else
                                    "relocation" if any(where(q) == "relocation" for q in ev) else "target_only")
        # consistency: permutations bd_2d.teach tried (and failed) before finding the stored minimal must evaluate y=0 (K3 sidecar scenes)
        if rid in run:
            obj = {o["id"]: o for o in rec["scene"]["objects"]}
            T = obj["t0"]["xy_m"]
            base = sorted([o for o, _ in assign], key=lambda o: (math.dist(obj[o]["xy_m"], T), o))
            order = list(dict.fromkeys(itertools.permutations(base)))[:6]
            mo = tuple(o for o, _ in assign)
            if mo in order and order.index(mo) > 0:
                implied["scenes"] += 1
                for objs in order[:order.index(mo)]:
                    q = next(q for q in perms if tuple(s[0] for s in q["order"]) == objs)
                    implied["implied_perms"] += 1
                    k = ("new_confirms_failure" if q["y"] == 0 else "new_success_contradicts" if q["y"] == 1 else "unresolved")
                    implied[k] += 1
        rows.append(row)

assert len(rows) == 5000 and len({r["root_id"] for r in rows}) == 5000
by = lambda c: [r for r in rows if r["K"] == c]
table = {}
for c in ("0", "1", "2", "3", "NONE"):
    rr = by(c)
    oc = Counter(r["order_class"] for r in rr)
    table[f"K{c}" if c != "NONE" else "NONE"] = {"total": len(rr), "order_dependent": oc.get("ORDER_DEPENDENT", 0), "order_independent": oc.get("ORDER_INDEPENDENT", 0),
                                                 "unresolved": oc.get("UNRESOLVED", 0), "not_applicable": oc.get("NOT_APPLICABLE", 0)}
tot = {k: sum(v[k] for v in table.values()) for k in ("total", "order_dependent", "order_independent", "unresolved", "not_applicable")}
k2p = [r for r in rows if r["K"] in ("2", "3")]
dep, ind, unr = (sum(r["order_class"] == x for r in k2p) for x in ("ORDER_DEPENDENT", "ORDER_INDEPENDENT", "UNRESOLVED"))
allp = [q for r in k2p for q in r["permutations"]]
used = [q for q in allp if q.get("y") in (0, 1)]
k3full = [r for r in by("3") if r["n_evaluated"] == 6]
summary = {
    "dataset": "rss-ebm-infeasibility @ yadu/dataset-3d 8fe960750b0a2701d76c91d304e0c427cc808d74 : gh-yadu-iiith/planar_2d/dataset_bd_classquota",
    "teacher": "BD2D_TEACHER_V1:DetPhysics(P16_FAST,no-library) via bd_2d.teach.seq semantics (carried robot state; T from achieved state; QB per sequence)",
    "outcome_convention": "LEGACY combined target-task outcome; NOT connector-valid Approach B X / independent Y",
    "table": table, "total": tot,
    "k2plus": {"total": len(k2p), "order_dependent": dep, "order_dependent_pct": round(100 * dep / len(k2p), 2), "order_independent": ind,
               "order_independent_pct": round(100 * ind / len(k2p), 2), "unresolved": unr, "dependent_strict_majority": dep > len(k2p) / 2},
    "k3_success_count_distribution_fully_enumerated": {f"{i}/6": sum(r["n_success"] == i for r in k3full) for i in range(0, 7)},
    "k3_fully_enumerated_scenes": len(k3full),
    "k3_not_fully_enumerated": {"scenes": len(by("3")) - len(k3full), "why": "ORDER_DEPENDENT from historical minimal vs reverse contrast; remaining orders not needed and not evaluated"},
    "permutation_records": {"historical_reused": sum(q["source"] == "historical" for q in used), "new_evaluated": sum(q["source"] == "new" for q in allp),
                            "new_resolved": sum(q["source"] == "new" and q.get("y") in (0, 1) for q in allp),
                            "not_evaluated_not_needed": sum(q["source"] == "not_evaluated" for q in allp)},
    "failures": {"total": sum(q["y"] == 0 for q in used), "certified": sum(q["y"] == 0 and q["negative_kind"] == "CERTIFIED" for q in used),
                 "budget_limited": sum(q["y"] == 0 and q["negative_kind"] != "CERTIFIED" for q in used),
                 "kinds": dict(Counter(q["negative_kind"] for q in used if q["y"] == 0)),
                 "relocation_step": sum(where(q) == "relocation" for q in used), "target_step": sum(where(q) == "target" for q in used),
                 "new_only": {"certified": sum(q["source"] == "new" and q["y"] == 0 and q["negative_kind"] == "CERTIFIED" for q in used),
                              "budget_limited": sum(q["source"] == "new" and q["y"] == 0 and q["negative_kind"] != "CERTIFIED" for q in used),
                              "relocation_step": sum(q["source"] == "new" and where(q) == "relocation" for q in used),
                              "target_step": sum(q["source"] == "new" and where(q) == "target" for q in used)}},
    "dependent_contrast_location": {f"K{c}": dict(Counter(r["contrast_location"] for r in by(c) if r["order_class"] == "ORDER_DEPENDENT")) for c in ("2", "3")},
    "unresolved_scenes": [{"root_id": r["root_id"], "K": r["K"], "reason": r.get("unresolved_reason")} for r in k2p if r["order_class"] == "UNRESOLVED"],
    "new_eval_errors": [{"root_id": r["root_id"], "order": q["order"], "resolution": q.get("resolution"), "error": q.get("error")}
                        for r in k2p for q in r["permutations"] if q["source"] == "new" and q.get("y") is None],
    "none": dict(Counter(r["none_kind"] for r in by("NONE"))),
    "not_applicable_total": tot["not_applicable"],
    "implied_attempt_consistency": implied,
    "reproduction_audit": {"sequences": len(repro), "label_status_failedstep_kind_match": sum(all(r["match"][k] for k in ("y", "reason", "failed_step", "negative_kind")) for r in repro),
                           "witness_bitwise_match_successes": f'{sum(r["match"]["witnesses"] for r in repro if r["stored"]["y"] == 1)}/{sum(r["stored"]["y"] == 1 for r in repro)}',
                           "standard": "LABEL_EQUIVALENT_NOT_BITWISE (trajectory float diffs <= 2.2e-15; one segment differs by one waypoint)"},
    "new_cpu_s": round(sum(q.get("cpu_s") or 0 for q in allp if q["source"] == "new"), 1),
    "sidecar_lines": run_lines, "sidecar_unique_roots": len(run),
    "x_y_status": "every permutation outcome here (historical and new) is legacy; each needs a q_ref connector check after its relocations and an independent Y replay from q_ref before use as finalized Approach B X/Y",
}
with open(H / "per_scene_order_classification.jsonl", "w") as f:
    for r in rows:
        f.write(json.dumps(r, separators=(",", ":")) + "\n")
(H / "order_classification_summary.json").write_text(json.dumps(summary, indent=1))
print(json.dumps({k: summary[k] for k in summary if k not in ("unresolved_scenes", "new_eval_errors")}, indent=1))
