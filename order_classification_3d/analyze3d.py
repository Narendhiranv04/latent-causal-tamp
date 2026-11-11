#!/usr/bin/env python3
"""3D order classification analysis (read-only on sources).  Inputs: Snapshot A copy (src_8fe96075), out/run/results.jsonl (K3 six orders),
the finalized X/Y sidecar V1 and the first-cohort pin / split (local copies).  Writes the 3D deliverables (new files only)."""
import gzip, hashlib, json, math, os, re
from collections import Counter, defaultdict
from pathlib import Path

H = Path(__file__).resolve().parent
COMMIT = "8fe960750b0a2701d76c91d304e0c427cc808d74"
DS = H / "src_8fe96075/gh-yadu-iiith/shelf_6x6_open_sides/dataset_bd_classquota_without_home_position_no_overpass"
PV3 = Path("/home/naren/Desktop/rss-3d-relocations/gh-yadu-iiith/shelf_6x6_open_sides/dataset_placement_extension_v2/production_v3/frozen")
SIDECAR = Path("/home/naren/Desktop/rss-3d-learning/gh-yadu-iiith/shelf_6x6_open_sides/approachb_3d_learning/physics_pilot/results_r4/BD3DS66_XY_SIDECAR_V1.json.gz")
sel_doc = json.loads((DS / "selected.json").read_text())
sel = sel_doc["selected"]
QUOTA = {"0": 511, "1": 357, "2": 612, "3": 612, "NONE": 408}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
SUB = {"NONE": "raw_none", "4": "raw_k4_ordered"}
pin = json.loads((PV3 / "source_pin_first_cohort.json").read_text())["roots"]
split = json.loads((PV3 / "split_manifest_first_cohort.json").read_text())["split"]
sc = json.load(gzip.open(SIDECAR))
Yk = {y["y_key"]: y for y in sc["y_rows"]}
Xr = defaultdict(list)
for x in sc["x_rows"]:
    Xr[x["root_id"]].append(x)
parse = lambda k: [(o, (int(a), int(b))) for o, a, b in re.findall(r"(o\d+|t0)>(\d+),(\d+)", k)]
run = {}
for l in open(H / "out/run/results.jsonl"):
    x = json.loads(l)
    assert x["root_id"] not in run
    run[x["root_id"]] = x
wit_ok = lambda ws, sub: all(any((DS / d / "witnesses" / w[:2] / f"{w}.npz").exists() for d in ("raw", "raw_k4_ordered", "raw_none")) for w in (ws or []))


def where(p):
    if p.get("y") != 0:
        return None
    return "target" if p["failed_step"] == "target" else ("first_relocation" if p["failed_step"] == 0 else "later_relocation")


def tier(fails):
    if not fails:
        return None
    rel = [p for p in fails if where(p) != "target"]
    if any(p["negative_kind"] == "CERTIFIED" for p in rel):
        return "T1_CERTIFIED_RELOCATION"
    if any(p["negative_kind"] == "OTHER_FAILURE" for p in rel):
        return "T2E_EXECUTION_FAILURE_RELOCATION"         # planned, executed in MuJoCo, end state not verified / grasp failed
    if rel:
        return "T2_BUDGET_RELOCATION"
    return "T3_TARGET_STEP_ONLY"


def sidecar_cov(rid, assign):
    """finalized connector-valid X rows for orders of exactly this assignment, plus the shared endpoint Y"""
    n = len(assign)
    rows = [x for x in Xr.get(rid, []) if x["m"] == n and len(parse(x["x_key"])) == n and dict(parse(x["x_key"])) == assign]
    orders = {tuple(o for o, _ in parse(x["x_key"])): x for x in rows}
    ys = sorted({Yk[x["y_key"]]["y"] for x in rows if x["y_key"] in Yk}, key=str)
    return {tuple(k): {"x": v["x"], "status": v["status"]} for k, v in orders.items()}, ys


rows = []
for k, ids in sel.items():
    sub = SUB.get(k, "raw")
    for rid in ids:
        p = DS / sub / "roots" / f"{rid}.json"
        rec = json.loads(p.read_text())
        row = {"root_id": rid, "K": k, "source_commit": COMMIT, "source_path": f"{sub}/roots/{rid}.json", "source_sha256": sha(p),
               "cohort_pin_same_bytes": (pin.get(rid) == row_sha if (row_sha := sha(p)) and rid in pin else None), "split": split.get(rid)}
        if k in ("0", "1", "NONE"):
            row["order_class"] = "NOT_APPLICABLE"
            rows.append(row)
            continue
        B = rec["labels"]["B"]
        mini = next(b for b in B if b["role"] == "minimal" and b["y"] == 1)
        assign = {o: tuple(d) for o, d in mini["sequence"]}
        row["successful_original_sequence"] = mini["sequence"]
        row["assignment"] = sorted([[o, list(d)] for o, d in assign.items()])
        row["minimal_witnesses_present"] = wit_ok(mini.get("witnesses"), sub)
        if k == "3" and rid in run:
            perms = run[rid]["perms"]
        else:                                          # K2 (both orders recorded) or a K3 root not yet in the sidecar: historical only
            recd = {tuple((o, tuple(d)) for o, d in b["sequence"]): b for b in B}
            perms = []
            import itertools
            for q in itertools.permutations(list(assign.items())):
                b = recd.get(q)
                perms.append({"order": [[o, list(d)] for o, d in q], "source": "historical" if b else "not_evaluated", **({
                    "role": b["role"], "y": b["y"], "reason": b["reason"], "failed_step": b["failed_step"], "negative_kind": b["negative_kind"],
                    "witnesses": b.get("witnesses")} if b else {"y": None})})
        row["permutations"] = perms
        ev = [q for q in perms if q.get("y") in (0, 1)]
        ns, nf = sum(q["y"] == 1 for q in ev), sum(q["y"] == 0 for q in ev)
        full = len(ev) == math.factorial(len(assign))
        row["n_perms"], row["n_evaluated"], row["n_success"], row["n_fail"] = len(perms), len(ev), ns, nf
        row["order_class"] = "ORDER_DEPENDENT" if ns and nf else "ORDER_INDEPENDENT" if full else "UNRESOLVED"
        if row["order_class"] == "UNRESOLVED":
            row["unresolved_reason"] = sorted({q.get("resolution") or q["source"] for q in perms if q.get("y") is None})
        fails = [q for q in ev if q["y"] == 0]
        row["tier"] = tier(fails) if row["order_class"] == "ORDER_DEPENDENT" else None
        row["fail_where"] = dict(Counter(where(q) for q in fails))
        row["fail_kinds"] = dict(Counter(q["negative_kind"] for q in fails))
        cov, ys = sidecar_cov(rid, assign)
        row["sidecar_finalX_orders"] = [[list(o), v["x"], v["status"]] for o, v in cov.items()]
        row["sidecar_endpoint_Y"] = ys
        xv = {v["x"] for v in cov.values()}
        row["finalX_status"] = ("FINAL_X_DISCORDANT" if len(xv) == 2 else "FINAL_X_ALL_1" if xv == {1} else "FINAL_X_ALL_0" if xv == {0} else "FINAL_X_NOT_MEASURED")
        row["finalX_orders_measured"] = len(cov)
        rows.append(row)

assert len(rows) == 1999 and len({r["root_id"] for r in rows}) == 1999
with open(H / "3D_ORDER_CLASSIFICATION_PER_SCENE.jsonl", "w") as f:
    for r in rows:
        f.write(json.dumps(r, separators=(",", ":"), default=list) + "\n")

K = lambda c: [r for r in rows if r["K"] == c]
cls = lambda c, x: sum(r["order_class"] == x for r in K(c))
table1 = {c: {"total": len(K(c)), "dependent": cls(c, "ORDER_DEPENDENT"), "independent": cls(c, "ORDER_INDEPENDENT"), "unresolved": cls(c, "UNRESOLVED")}
          for c in ("0", "1", "2", "3", "NONE")}
k3 = K("3")
dist = {f"{i}/6": sum(r["n_success"] == i and r["n_evaluated"] == 6 for r in k3) for i in range(0, 7)}
dist["unresolved_or_incomplete"] = sum(r["n_evaluated"] < 6 for r in k3)
newp = [q for r in k3 for q in r["permutations"] if q["source"] == "new"]
hist_used = sum(q["source"] == "historical" for r in K("2") + k3 for q in r["permutations"] if q.get("y") in (0, 1))
(H / "3D_K3_PERMUTATION_DISTRIBUTION.json").write_text(json.dumps({
    "snapshot": "A", "source_commit": COMMIT, "k3_published": len(k3), "distribution": dist,
    "percent": {k: round(100 * v / len(k3), 2) for k, v in dist.items()}, "k2": {f"{i}/2": sum(r["n_success"] == i for r in K("2")) for i in (1, 2)},
    "new_evaluations": {"count": len(newp), "resolved": sum(q.get("y") in (0, 1) for q in newp), "errors": sum(q.get("y") is None for q in newp),
                        "cpu_h": round(sum(q.get("cpu_s") or 0 for q in newp) / 3600, 2)}, "historical_records_reused": hist_used}, indent=1))

# failure mechanisms
dep = [r for r in K("2") + k3 if r["order_class"] == "ORDER_DEPENDENT"]
k3f = [r for r in k3 if r["n_evaluated"] == 6]
allf = [q for r in dep for q in r["permutations"] if q.get("y") == 0]
mech = {"dependent_scenes": len(dep), "tier": {c: dict(Counter(r["tier"] for r in K(c) if r["tier"])) for c in ("2", "3")},
        "failing_orders": len(allf), "by_kind": dict(Counter(q["negative_kind"] for q in allf)),
        "by_where": dict(Counter(where(q) for q in allf)), "by_where_kind": {f"{a}|{b}": v for (a, b), v in Counter((where(q), q["negative_kind"]) for q in allf).items()},
        "execution_failure_reasons": dict(Counter((q.get("reason") or "").split(":")[0] for q in allf if q["negative_kind"] == "OTHER_FAILURE")),
        "scenes_with_first_relocation_failure": {c: sum(r["fail_where"].get("first_relocation", 0) > 0 for r in K(c) if r["order_class"] == "ORDER_DEPENDENT") for c in ("2", "3")},
        "exactly_one_order_K3": {"scenes": sum(r["n_success"] == 1 for r in k3f), "tier": dict(Counter(r["tier"] for r in k3f if r["n_success"] == 1)),
                                 "all_failures_at_relocation": sum(r["n_success"] == 1 and "target" not in r["fail_where"] for r in k3f),
                                 "all_failures_certified": sum(r["n_success"] == 1 and set(r["fail_kinds"]) == {"CERTIFIED"} for r in k3f)},
        "tier_by_success_count_K3": {f"{i}/6": dict(Counter(r["tier"] for r in k3f if r["n_success"] == i)) for i in range(1, 6)}}
# finalized-X evidence (existing sidecar only)
fx = {}
for c in ("2", "3"):
    for oc in ("ORDER_DEPENDENT", "ORDER_INDEPENDENT"):
        fx[f"K{c}|{oc}"] = dict(Counter(r["finalX_status"] for r in K(c) if r["order_class"] == oc))
contrast = Counter()
for r in K("2") + k3:
    leg = {tuple(o for o, _ in q["order"]): q["y"] for q in r["permutations"] if q.get("y") in (0, 1)}
    for o, x, st in r["sidecar_finalX_orders"]:
        lg = leg.get(tuple(o))
        contrast[(f"K{r['K']}", "legacy_y=%s" % lg, "finalX=%s" % x)] += 1
fx["per_order_legacy_vs_finalX"] = {"|".join(k): v for k, v in sorted(contrast.items())}
fx["dependent_scenes_finalX_discordant_on_same_assignment"] = sum(r["finalX_status"] == "FINAL_X_DISCORDANT" for r in dep)
fx["independent_scenes_finalX_discordant"] = sum(r["finalX_status"] == "FINAL_X_DISCORDANT" for r in K("2") + k3 if r["order_class"] == "ORDER_INDEPENDENT")
fx["k3_orders_needing_connector_X"] = sum(6 - r["finalX_orders_measured"] for r in k3)
fx["k2_orders_needing_connector_X"] = sum(2 - r["finalX_orders_measured"] for r in K("2"))
fx["endpoints_without_Y"] = {c: sum(not r["sidecar_endpoint_Y"] or r["sidecar_endpoint_Y"] == [None] for r in K(c)) for c in ("2", "3")}
mech["finalized_X_evidence"] = fx

# K4 and excluded DEPENDENT (existing records only)
led = [json.loads(l) for l in open(DS / "raw/ledger.jsonl")]
depled = {x["root_id"]: x for x in led if x.get("observed") == "DEPENDENT"}


def rec_summary(rid, sub):
    p = DS / sub / "roots" / f"{rid}.json"
    r = json.loads(p.read_text())
    B = r["labels"]["B"]
    mini = next((b for b in B if b["role"] == "minimal" and b["y"] == 1), None)
    wo = next((b for b in B if b["role"] == "wrong_order"), None)
    rev_ok = bool(mini and wo and [tuple(x) for x in wo["sequence"]] == [tuple(x) for x in reversed(mini["sequence"])]
                  if mini and wo else False)
    return {"root_id": rid, "verified_K": r["verified_K"], "sha256": sha(p), "successful_correction": mini is not None,
            "minimal_witnesses_present": bool(mini) and wit_ok(mini.get("witnesses"), sub), "reverse_recorded": wo is not None and rev_ok,
            "reverse_y": wo["y"] if wo else None, "reverse_failed_step": wo["failed_step"] if wo else None, "reverse_kind": wo["negative_kind"] if wo else None,
            "in_cohort_pin": rid in pin, "split": split.get(rid), "in_sidecar": rid in Xr, "in_dependent_ledger": rid in depled,
            "selected_as": next((kk for kk, v in sel.items() if rid in v), None)}


k4 = [rec_summary(r, "raw_k4_ordered") for r in sel["4"]]
excl = [rec_summary(r, "raw") for r in depled if r not in sel["4"]]
exc_tab = {}
for kk in (2, 3):
    xs = [x for x in excl if x["verified_K"] == kk]
    exc_tab[f"K{kk}"] = {"scenes": len(xs), "unique": len({x["root_id"] for x in xs}), "successful_correction": sum(x["successful_correction"] for x in xs),
                         "witness_files_present": sum(x["minimal_witnesses_present"] for x in xs), "reverse_recorded": sum(x["reverse_recorded"] for x in xs),
                         "reverse_failed": sum(x["reverse_y"] == 0 for x in xs), "reverse_succeeded": sum(x["reverse_y"] == 1 for x in xs),
                         "reverse_fail_kind": dict(Counter(x["reverse_kind"] for x in xs if x["reverse_y"] == 0)),
                         "reverse_fail_first_relocation": sum(x["reverse_y"] == 0 and x["reverse_failed_step"] == 0 for x in xs),
                         "in_cohort_pin": sum(x["in_cohort_pin"] for x in xs), "in_split": dict(Counter(str(x["split"]) for x in xs)),
                         "in_sidecar": sum(x["in_sidecar"] for x in xs)}
exc_tab["K4_selected_9"] = {"scenes": len(k4), "unique": len({x["root_id"] for x in k4}), "also_in_raw_DEPENDENT_ledger": sum(x["in_dependent_ledger"] for x in k4),
                            "successful_correction": sum(x["successful_correction"] for x in k4), "witness_files_present": sum(x["minimal_witnesses_present"] for x in k4),
                            "reverse_recorded": sum(x["reverse_recorded"] for x in k4), "reverse_failed": sum(x["reverse_y"] == 0 for x in k4),
                            "reverse_fail_kind": dict(Counter(x["reverse_kind"] for x in k4 if x["reverse_y"] == 0)),
                            "in_cohort_pin": sum(x["in_cohort_pin"] for x in k4), "in_sidecar": sum(x["in_sidecar"] for x in k4)}
mech["excluded_and_k4"] = exc_tab
mech["excluded_detail"] = excl
mech["k4_detail"] = k4

# snapshot manifest
(H / "3D_SOURCE_SNAPSHOT_MANIFEST.json").write_text(json.dumps({
    "snapshot_A": {"repo": "Narendhiranv04/rss-ebm-infeasibility", "branch": "yadu/dataset-3d", "commit": COMMIT,
                   "path": "gh-yadu-iiith/shelf_6x6_open_sides/dataset_bd_classquota_without_home_position_no_overpass",
                   "selected_sha256": sha(DS / "selected.json"), "selected_status": sel_doc["status"], "counts": {k: len(v) for k, v in sel.items()},
                   "roots": {r["root_id"]: {"K": r["K"], "sha256": r["source_sha256"]} for r in rows}},
    "learning_branch": {"branch": "naren/approachb-3d-learning", "commit": "4d2d3dbf89788a452c713a4cb8443be3fd0568eb",
                        "sidecar": str(SIDECAR), "sidecar_sha256": sha(SIDECAR)},
    "cohort_pin": {"path": str(PV3 / "source_pin_first_cohort.json"), "sha256": sha(PV3 / "source_pin_first_cohort.json"),
                   "selected_K0_K3_in_pin_same_bytes": sum(bool(r["cohort_pin_same_bytes"]) for r in rows),
                   "selected_K0_K3_total": sum(r["K"] in ("0", "1", "2", "3") for r in rows)}}, indent=1))

summary = {"snapshot": "A", "source_commit": COMMIT, "table1": table1, "k4_published": len(sel["4"]),
           "k2plus": {"published": len(K("2")) + len(k3), "dependent": len(dep), "independent": sum(r["order_class"] == "ORDER_INDEPENDENT" for r in K("2") + k3),
                      "unresolved": sum(r["order_class"] == "UNRESOLVED" for r in K("2") + k3)},
           "k3_distribution": dist, "mechanisms": {k: v for k, v in mech.items() if not k.endswith("_detail")},
           "new_evaluations": len(newp), "new_errors": sum(q.get("y") is None for q in newp), "historical_reused": hist_used,
           "new_cpu_h": round(sum(q.get("cpu_s") or 0 for q in newp) / 3600, 2),
           "source_integrity": {"selected_unique": len({r['root_id'] for r in rows}), "minimal_witness_missing": sum(r.get("minimal_witnesses_present") is False for r in rows)}}
s2 = summary["k2plus"]
summary["k2plus"]["dependent_pct"] = round(100 * s2["dependent"] / s2["published"], 2)
(H / "3D_ORDER_AUDIT_SUMMARY.json").write_text(json.dumps({**summary, "detail": {"excluded": excl, "k4": k4}}, indent=1, default=list))
print(json.dumps(summary, indent=1, default=list))
