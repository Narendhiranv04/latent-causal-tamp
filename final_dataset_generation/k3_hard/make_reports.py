#!/usr/bin/env python3
"""Builds the K3 hard-order sidecar (K3_HARD_ORDER_V1/) from ledgers, stores, consistency gates, X/Y checks and the V3 selections.
Read-only on every input; V2 selections and placement datasets are never touched.   make_reports.py"""
import glob, hashlib, json, shutil, statistics
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

H = Path(__file__).resolve().parent
G = H.parent
B = G.parent
OUT = H / "K3_HARD_ORDER_V1"
OUT.mkdir(exist_ok=True)
DS2 = Path("/home/naren/Desktop/rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_bd_classquota")
PINS3 = json.loads((G / "snapshot_a_root_sha256.json").read_text())
TARGET = {"2d": {1: 403, 2: 345, 3: 172, 4: 115, 5: 57, 6: 58}, "3d": {1: 214, 2: 184, 3: 92, 4: 61, 5: 31, 6: 30}}
S6 = range(1, 7)


def jl(p):
    p = Path(p)
    return [json.loads(l) for l in open(p)] if p.exists() else []


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rehash_witness(p):
    z = np.load(p, allow_pickle=False)
    h = hashlib.sha256()
    for k in sorted(z.files):
        v = np.ascontiguousarray(np.asarray(z[k]))
        h.update(f"{k}|{v.dtype.str}|{v.shape}".encode())
        h.update(v.tobytes())
    return h.hexdigest()[:24]


def dist(xs):
    c = Counter(xs)
    return {f"{s}/6": c.get(s, 0) for s in S6}


def utc_hours(a, b):
    import datetime as dt
    f = lambda s: dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
    return round((f(b) - f(a)).total_seconds() / 3600, 2)


def domain(dom):
    D = dom.upper()
    v2 = json.loads((G / "FINAL_DATASET_SELECTION_MANIFESTS" / f"{D}_SELECTION_V2.json").read_text())
    v3 = json.loads((H / f"{D}_K3_STRENGTH_SELECTION_V3.json").read_text())
    r2, r3 = v2["rows"], v3["rows"]
    k3v2 = [r for r in r2 if r["K"] == "3"]
    k3v3 = [r for r in r3 if r["K"] == "3"]
    res = {"domain": D}
    # ---------------- original distributions
    src = B / ("order_classification_2d/per_scene_six_permutation_outcomes.jsonl" if dom == "2d" else "order_classification_3d/3D_ORDER_CLASSIFICATION_PER_SCENE.jsonl")
    nat = {r["root_id"]: sum(p["y"] for p in r["permutations"]) for r in jl(src) if r.get("permutations") and len(r["permutations"]) == 6
           and all(p["y"] in (0, 1) for p in r["permutations"])}
    lay_split = {r["layout_root_id"]: r["split"] for r in k3v3}
    res["v2_k3_distribution"] = dist(r["n_success"] for r in k3v2)
    res["natural_source_distribution_of_layouts"] = dist(nat[L] for L in lay_split if L in nat)
    res["natural_holdout_view"] = {"definition": "test-split K3 layouts, each with its ORIGINAL source assignment and its natural source strength "
                                   "(the 6-order outcome of the published original root); same layouts as the hard-order test view, different assignment",
                                   "n": sum(1 for L, s in lay_split.items() if s == "test" and L in nat),
                                   "distribution": dist(nat[L] for L, s in lay_split.items() if s == "test" and L in nat),
                                   "rows": [{"layout_root_id": L, "root_id": L, "n_success": nat[L]}
                                            for L, s in sorted(lay_split.items()) if s == "test" and L in nat]}
    # ---------------- jobs and ledgers
    pilot = json.loads((H / f"pilot{dom}.json").read_text())
    bulk = json.loads((H / f"bulk{dom}.json").read_text())
    jobs = {j["job_id"]: dict(j, phase="pilot") for j in pilot}
    jobs.update({j["job_id"]: dict(j, phase="bulk") for j in bulk})
    leds = ([("LAPTOP", H / "d2/ledger.jsonl"), ("GVLAB", H / "d2_gvlab/ledger.jsonl")] if dom == "2d" else [("GVLAB", H / "d3/ledger.jsonl")])
    ent = {}
    for host, p in leds:
        for r in jl(p):
            if "skipped" in r or r.get("job_id") not in jobs:
                continue
            ent[r["job_id"]] = dict(r, host=host)
    claimed = set(json.loads((H / "d2/claims_other_host.json").read_text())) if dom == "2d" else set()
    outc = Counter()
    for jid, j in jobs.items():
        e = ent.get(jid)
        if e is None:
            outc["NOT_STARTED_OR_IN_FLIGHT_AT_CAP (MISSING)"] += 1
        elif str(e.get("reason", "")).startswith("ADMIN_STOP"):
            outc["ADMIN_STOP (MISSING)"] += 1
        elif e.get("accepted"):
            outc["ACCEPTED"] += 1
        else:
            outc[str(e.get("reason"))[:40]] += 1
    done = [e for e in ent.values() if not str(e.get("reason", "")).startswith("ADMIN_STOP")]
    res["jobs"] = {"total": len(jobs), "pilot": len(pilot), "bulk": len(bulk), "by_split": dict(Counter(j["split"] for j in jobs.values())),
                   "handed_to_gvlab": len(claimed), "outcomes": dict(outc),
                   "start_strength_of_all_jobs": dist(j["start_ns"] for j in jobs.values()),
                   "final_strength_of_accepted_jobs": dist(e["n_success"] for e in done if e.get("accepted"))}
    trans = defaultdict(Counter)
    for e in done:
        trans[e["start_ns"]][e["n_success"] if e.get("accepted") else "none"] += 1
    res["start_to_final_transition"] = {f"start {s}/6": dict(trans[s]) for s in sorted(trans)}
    # ---------------- CPU / throughput
    cpu = {}
    for host in sorted({e["host"] for e in ent.values()}):
        es = [e for e in ent.values() if e["host"] == host]
        u = sorted(e["utc"] for e in es)
        cpu[host] = {"jobs_finished": sum(1 for e in es if not str(e.get("reason", "")).startswith("ADMIN_STOP")),
                     "cpu_h": round(sum(e.get("cpu_s", 0) for e in es) / 3600, 1), "first_utc": u[0], "last_utc": u[-1],
                     "mean_cpu_s_per_job": round(statistics.mean(e.get("cpu_s", 0) for e in es)),
                     "median_cpu_s_per_job": round(statistics.median(e.get("cpu_s", 0) for e in es))}
    res["cpu_by_host"] = cpu
    tot_cpu = sum(e.get("cpu_s", 0) for e in done)
    by_final = defaultdict(list)
    for e in done:
        by_final[e["n_success"] if e.get("accepted") else "no_accept"].append(e.get("cpu_s", 0))
    res["cpu_by_final_strength"] = {(f"{k}/6" if k != "no_accept" else k): {"jobs": len(v), "mean_cpu_s": round(statistics.mean(v)), "cpu_h": round(sum(v) / 3600, 2)}
                                    for k, v in sorted(by_final.items(), key=lambda x: str(x[0]))}
    by_start = defaultdict(list)
    for e in done:
        by_start[e["start_ns"]].append(e)
    res["yield_by_start_strength"] = {f"start {s}/6": {"jobs": len(v), "cpu_h": round(sum(e.get("cpu_s", 0) for e in v) / 3600, 1),
                                                         "to_1_6": sum(1 for e in v if e.get("accepted") and e["n_success"] == 1),
                                                         "to_le_2_6": sum(1 for e in v if e.get("accepted") and e["n_success"] <= 2)}
                                      for s, v in sorted(by_start.items())}
    res["generation_cpu_h_total"] = round(tot_cpu / 3600, 1)
    # ---------------- new roots + gates
    stores = [H / "d2/store", H / "d2_gvlab/store"] if dom == "2d" else [H / "d3/store"]
    cons = ({r["root_id"]: r for r in jl(H / "consistency2d.jsonl")} if dom == "2d" else {})
    roots = {}
    for st in stores:
        for f in sorted((st / "roots").glob("D*H_*.json")):
            roots[f.stem] = (f, json.loads(f.read_text()))
    gate = {}
    for rid, (f, r) in roots.items():
        if dom == "2d":
            c = cons.get(rid)
            gate[rid] = "PASS" if c and c["consistent"] else ("FAIL" if c else "UNCHECKED")
        else:
            gate[rid] = "PASS" if r.get("teacher_vs_fresh_env") == "ALL_TEACHER_ORDERS_REPRODUCED" else "MISSING"
    res["new_roots"] = {"saved": len(roots), "gate": dict(Counter(gate.values())),
                        "gate_rule": ("consistency2d: every teacher-labelled order re-executed on a fresh cache, all y equal" if dom == "2d" else
                                      "hard3d.finish_checked: every teacher-labelled order re-executed by perm3d.seq on a fresh MuJoCo env before saving"),
                        "by_strength_all": dist(r["n_success"] for _, r in roots.values()),
                        "by_strength_gate_pass": dist(r["n_success"] for rid, (_, r) in roots.items() if gate[rid] == "PASS"),
                        "layouts_improved": len({r["construction"]["layout_root_id"] for rid, (_, r) in roots.items() if gate[rid] == "PASS"})}
    if dom == "2d":
        res["new_roots"]["consistency_failures"] = [{"root_id": k, "disagree": [c for c in v["checked"] if c["teacher_y"] != c["fresh_y"]]}
                                                    for k, v in cons.items() if not v["consistent"]]
    else:
        c3 = {r["root_id"]: r for r in jl(H / "consistency3d.jsonl")}
        res["v1_children_fresh_env_gate"] = {"checked": len(c3), "pass": sum(1 for r in c3.values() if r.get("consistent") is True),
                                             "fail": sorted(k for k, r in c3.items() if r.get("consistent") is False),
                                             "error": sorted(k for k, r in c3.items() if r.get("consistent") is None)}
    # ---------------- selection
    res["selection"] = {k: v3[k] for k in ("version", "targets", "selected_distribution", "deficit_vs_target", "layouts_with_option",
                                            "n_layouts", "excluded_by_gates", "xy_checked_selected", "xy_verified_selected") if k in v3}
    res["selection"]["source_mix"] = dict(Counter(r["source"] for r in k3v3))
    res["selection"]["by_split"] = {s: dist(r["n_success"] for r in k3v3 if r["split"] == s) for s in ("train", "val", "test")}
    if dom == "3d":
        full = TARGET["3d"]
        sel = Counter(r["n_success"] for r in k3v3)
        res["selection"]["vs_full_612_target"] = {"target": {f"{s}/6": full[s] for s in S6}, "selected_published_357": {f"{s}/6": sel[s] for s in S6},
                                                  "remaining_for_unpublished_255": {f"{s}/6": max(0, full[s] - sel[s]) for s in S6}}
    chosen = {r["root_id"] for r in k3v3}
    resv = Counter()
    for rid, (_, r) in roots.items():
        if gate[rid] == "PASS" and rid not in chosen:
            resv[r["n_success"]] += 1
    res["reserves_unselected_gate_pass_hard_roots"] = dist([s for s, n in resv.items() for _ in range(n)])
    alt = Counter()
    for r in k3v3:
        for s in set(r["alternatives_available"]) - {r["n_success"]}:
            alt[s] += 1
    res["reserves_layouts_with_unused_option"] = {f"{s}/6": alt[s] for s in S6}
    # ---------------- uniqueness / lineage
    v2_layout_split = {}
    for r in k3v2:
        L = r["root_id"] if r["source"] == "ORIGINAL_SELECTED" else (r["parent_root_id"] if r.get("method") in ("repark2d", "depseek3d_repark") else r["root_id"])
        v2_layout_split[L] = r["split"]
    non3_same = [json.dumps(a, sort_keys=True) for a in r2 if a["K"] != "3"] == [json.dumps(a, sort_keys=True) for a in r3 if a["K"] != "3"]
    lin_fail = Counter()
    rows_out = []
    for r in k3v3:
        rid, L = r["root_id"], r["layout_root_id"]
        row = dict(r)
        if r["source"] == "NEW_HARD_ORDER":
            f, rec = roots[rid]
            c = rec["construction"]
            row["root_sha256"] = sha_file(f)
            row["parent_root_id"] = c["parent_root_id"]
            row["changed_destinations"] = c.get("changed_destinations")
            if c.get("layout_root_id", c.get("parent_root_id")) != L or not c.get("same_layout_as_parent", True):
                lin_fail["layout_mismatch"] += 1
            want = sha_file(DS2 / "raw/roots" / f"{L}.json") if dom == "2d" else PINS3.get(L)
            if c.get("parent_sha256") != want:
                lin_fail["parent_sha256_mismatch"] += 1
            if c.get("destinations_free_distinct_in_original") is not True:
                lin_fail["destinations_not_certified_free_distinct"] += 1
            if rec.get("verified_K") != 3 or rec.get("n_success") != r["n_success"]:
                lin_fail["verified_K_or_strength_mismatch"] += 1
            if gate[rid] != "PASS":
                lin_fail["selected_without_gate_pass"] += 1
        if v2_layout_split.get(L) != r["split"]:
            lin_fail["split_changed"] += 1
        rows_out.append(row)
    res["uniqueness_lineage"] = {
        "rows_total": len(r3), "rows_total_v2": len(r2), "k_counts_v3": dict(Counter(r["K"] for r in r3)), "k_counts_v2": dict(Counter(r["K"] for r in r2)),
        "unique_root_ids": len({r["root_id"] for r in r3}) == len(r3), "unique_k3_layouts": len({r["layout_root_id"] for r in k3v3}) == len(k3v3),
        "k3_layout_set_equals_v2": set(r["layout_root_id"] for r in k3v3) == set(v2_layout_split), "non_k3_rows_identical_to_v2": non3_same,
        "lineage_failures": dict(lin_fail)}
    # ---------------- witness / hash integrity (selected NEW_HARD_ORDER roots)
    wc = Counter()
    for r in k3v3:
        if r["source"] != "NEW_HARD_ORDER":
            continue
        f, rec = roots[r["root_id"]]
        st = f.parent.parent
        wids = set()
        for b in rec["labels"]["B"]:
            wids.update(b.get("witnesses") or [])
        for p in rec["permutations"]:
            wids.update(p.get("witnesses") or [])
        for w in wids:
            p = st / "witnesses" / w[:2] / f"{w}.npz"
            if not p.exists():
                wc["missing"] += 1
            elif rehash_witness(p) != w:
                wc["content_hash_mismatch"] += 1
            else:
                wc["ok"] += 1
    res["witness_integrity_selected_new_roots"] = dict(wc)
    return res, rows_out, v3


def xy_summary(dom):
    X = [r for r in jl(H / f"xy{dom}_all.jsonl")]
    ok = [r for r in X if "error" not in r]
    by = defaultdict(Counter)
    for r in ok:
        same = all(r["x"][k]["x"] == v for k, v in r["legacy"].items())
        by[r["legacy_n_success"]]["checked"] += 1
        by[r["legacy_n_success"]]["Y_success"] += (r["y"] or {}).get("y") == 1
        by[r["legacy_n_success"]]["X_same_strength"] += r["x_n_success"] == r["legacy_n_success"]
        by[r["legacy_n_success"]]["X_same_per_order_pattern"] += same
        by[r["legacy_n_success"]]["X_and_Y_verified"] += (r["x_n_success"] == r["legacy_n_success"] and (r["y"] or {}).get("y") == 1)
        by[r["legacy_n_success"]][f"X={r['x_n_success']}/6"] += 1
        by[r["legacy_n_success"]]["X_unresolved_orders"] += r.get("x_unresolved", 0) or 0
    return {"checked": len(X), "errors": len(X) - len(ok), "error_examples": [r["error"] for r in X if "error" in r][:5],
            "by_legacy_strength": {f"{s}/6": dict(by[s]) for s in sorted(by)},
            "totals": {k: sum(by[s][k] for s in by) for k in ("checked", "Y_success", "X_same_strength", "X_same_per_order_pattern", "X_and_Y_verified")}}


def md_table(d, cols=None):
    rows = list(d.items())
    cols = cols or sorted({k for _, v in rows for k in (v if isinstance(v, dict) else {})}, key=str)
    s = "| | " + " | ".join(map(str, cols)) + " |\n|---|" + "---:|" * len(cols) + "\n"
    for k, v in rows:
        s += f"| {k} | " + " | ".join(str(v.get(c, 0)) for c in cols) + " |\n"
    return s


def main():
    R, ROWS, V3 = {}, {}, {}
    for dom in ("2d", "3d"):
        R[dom], ROWS[dom], V3[dom] = domain(dom)
        R[dom]["xy"] = xy_summary(dom)
    S = [f"{s}/6" for s in S6]
    # ---------- selection manifest
    man = {"version": "K3_STRENGTH_SELECTION_V3 (hard-order challenge view)", "baselines_kept_unchanged": ["2D_SELECTION_V2.json", "3D_SELECTION_V2.json"],
           "selection_rule": V3["2d"]["rule"], "full_row_files": ["2D_K3_STRENGTH_SELECTION_V3.json", "3D_K3_STRENGTH_SELECTION_V3.json"],
           "views": {"hard_order_challenge": "the V3 K3 rows (one assignment per layout, strength-targeted)",
                     "natural_distribution_holdout": "test-split layouts with their ORIGINAL source assignment (natural_holdout_view)"}}
    for dom in ("2d", "3d"):
        r = R[dom]
        man[dom.upper()] = {"targets": r["selection"]["targets"], "selected_distribution": r["selection"]["selected_distribution"],
                            "deficit_vs_target": r["selection"]["deficit_vs_target"], "source_mix": r["selection"]["source_mix"],
                            "by_split": r["selection"]["by_split"], "k3_rows": ROWS[dom], "natural_holdout_view": r["natural_holdout_view"]}
        if dom == "3d":
            man["3D"]["vs_full_612_target"] = r["selection"]["vs_full_612_target"]
    (OUT / "K3_STRENGTH_SELECTION_MANIFEST.json").write_text(json.dumps(man, indent=1))
    for dom in ("2d", "3d"):
        shutil.copy(H / f"{dom.upper()}_K3_STRENGTH_SELECTION_V3.json", OUT / f"{dom.upper()}_K3_STRENGTH_SELECTION_V3.json")
    (OUT / "k3_hard_order_raw_stats.json").write_text(json.dumps(R, indent=1, default=str))
    # ---------- readiness
    rd = {"stage": "K3 hard-order generation complete (bounded 12 h per host); STOPPED BEFORE TRAINING", "training_started": False,
          "placement_datasets_modified": False, "v2_selections_overwritten": False}
    for dom in ("2d", "3d"):
        r = R[dom]
        defi = {k: v for k, v in r["selection"]["deficit_vs_target"].items() if v > 0}
        ul = r["uniqueness_lineage"]
        integ_ok = (ul["unique_root_ids"] and ul["unique_k3_layouts"] and ul["k3_layout_set_equals_v2"] and ul["non_k3_rows_identical_to_v2"]
                    and not ul["lineage_failures"] and not r["witness_integrity_selected_new_roots"].get("missing")
                    and not r["witness_integrity_selected_new_roots"].get("content_hash_mismatch"))
        rd[dom.upper()] = {"status": ("READY" if not defi else "READY_WITH_STRENGTH_DEFICITS") if integ_ok else "BLOCKED_INTEGRITY",
                           "rows": ul["rows_total"], "k_counts": ul["k_counts_v3"], "k3_selected": r["selection"]["selected_distribution"],
                           "k3_deficits": defi, "integrity_checks_pass": integ_ok, "new_root_gate": r["new_roots"]["gate"],
                           "xy_selected_checked": r["selection"].get("xy_checked_selected"), "xy_selected_verified": r["selection"].get("xy_verified_selected"),
                           "selection_file": f"{dom.upper()}_K3_STRENGTH_SELECTION_V3.json",
                           "sha256": sha_file(OUT / f"{dom.upper()}_K3_STRENGTH_SELECTION_V3.json")}
    rd["3D"]["unpublished"] = "teammate's 255 K3 roots (of 510) not published/verified -> not counted; 3D K3 is 357/612 layouts"
    rd["3D"]["vs_full_612_target"] = R["3d"]["selection"]["vs_full_612_target"]
    (OUT / "K3_DATASET_READINESS.json").write_text(json.dumps(rd, indent=1))
    # ---------- markdown reports
    gen = ["# K3 Hard-Order Generation Report (Approach B, 2D + 3D)\n",
           "Sidecar `final_dataset_generation/k3_hard/K3_HARD_ORDER_V1/`. V2 selections are unchanged baselines; nothing was trained.\n",
           "Method: re-parking with a hard-order-focused precedence search (park V next to U's initial cell so U must precede V; pairs ranked by how "
           "many currently successful orders they remove), greedy first-improvement toward 1/6, minimal K re-verified by a fresh teach "
           "(verified_K = 3, same assignment), all 6 orders evaluated with sequential physical execution (carried robot state, no resets, no swaps, "
           "fixed IK/geometry/grasps/budgets, destinations distinct and free in the original scene, identical across the 6 orders). Planner-budget "
           "failure = 0; administrative stops = MISSING. 2D also keeps intermediate verified levels (<= 4/6) as lineage siblings.\n"]
    for dom in ("2d", "3d"):
        r = R[dom]
        D = dom.upper()
        gen += [f"\n## {D}\n", "### Distributions\n",
                md_table({"V2 baseline K3 (old, not new)": r["v2_k3_distribution"], "natural source strength of the same layouts": r["natural_source_distribution_of_layouts"],
                          "target": {f"{s}/6": r["selection"]["targets"][str(s)] if str(s) in r["selection"]["targets"] else r["selection"]["targets"].get(s) for s in S6},
                          "V3 selected": r["selection"]["selected_distribution"], "deficit (+ = short)": r["selection"]["deficit_vs_target"]}, S),
                "\n### Jobs\n", "```\n" + json.dumps(r["jobs"], indent=1) + "\n```\n",
                "Start -> final (accepted strength, or `none`):\n", md_table(r["start_to_final_transition"]),
                "\n### New verified roots\n", "```\n" + json.dumps({k: v for k, v in r["new_roots"].items() if k != "consistency_failures"}, indent=1) + "\n```\n"]
        if dom == "2d":
            gen.append(f"Consistency failures (excluded): {len(r['new_roots']['consistency_failures'])}\n")
        else:
            gen.append("Earlier (V1 DEPSEEK) 3D children re-checked on a fresh env: ```" + json.dumps(r["v1_children_fresh_env_gate"]) + "```\n")
        gen += ["\n### Selection\n", "```\n" + json.dumps(r["selection"], indent=1) + "\n```\n",
                "\n### Reserves\n", md_table({"unselected gate-pass hard roots": r["reserves_unselected_gate_pass_hard_roots"],
                                               "layouts with an unused option at s": r["reserves_layouts_with_unused_option"]}, S),
                "\n### Uniqueness and lineage\n", "```\n" + json.dumps(r["uniqueness_lineage"], indent=1) + "\n```\n",
                "\n### Witness and hash integrity (selected new roots; witnesses re-hashed from content)\n", "```\n" + json.dumps(r["witness_integrity_selected_new_roots"]) + "\n```\n",
                "\n### Natural-distribution holdout view\n", f"{r['natural_holdout_view']['definition']}: n = {r['natural_holdout_view']['n']}\n\n",
                md_table({"natural holdout": r["natural_holdout_view"]["distribution"], "hard-order test view": r["selection"]["by_split"]["test"]}, S)]
    gen += ["\n## 3D completed vs unpublished\n", "```\n" + json.dumps(rd["3D"]["vs_full_612_target"], indent=1) + "\n```\n", rd["3D"]["unpublished"] + "\n"]
    (OUT / "K3_HARD_ORDER_GENERATION_REPORT.md").write_text("".join(gen))
    xy = ["# K3 X/Y Contrast Validation\n",
          "Finalized Approach-B check: X = the ordered relocations with carried robot state + connector back to q_ref; Y = target from q_ref in the "
          "endpoint scene (all 6 orders of one assignment reach the same endpoint and share one Y). Legacy strength (target planned from the achieved "
          "pose) is NOT assumed to equal X strength; selection prefers roots whose X strength equals the legacy strength with Y = 1.\n"]
    for dom in ("2d", "3d"):
        x = R[dom]["xy"]
        xy += [f"\n## {dom.upper()}\n", f"checked {x['checked']}, errors {x['errors']} {x['error_examples']}\n\n",
               md_table(x["by_legacy_strength"]), "\nTotals: ```" + json.dumps(x["totals"]) + "```\n",
               f"\nSelected V3 K3 rows with an X/Y record: {R[dom]['selection'].get('xy_checked_selected')}; X/Y-verified at the selected strength: "
               f"{R[dom]['selection'].get('xy_verified_selected')}\n"]
    xy.append("\n3D X/Y is a teacher pass (no independent replay); 2D X/Y includes independent replay.\n")
    (OUT / "K3_XY_CONTRAST_VALIDATION.md").write_text("".join(xy))
    mh = ["# K3 Multi-Host Resource Report\n", "Hosts: laptop (<= 27 logical CPUs, 5 left free) and gvlab (<= 20 CPUs, >= 4 left free). Enigma and Blackwell were not used; "
          "no GPU (would change the teacher). 2D ran on gvlab only after cross-host parity: 36/36 perm2d re-evaluations byte-identical to the laptop "
          "(incl. witness ids) and 4/4 hard2d jobs identical (root id, strength, path, evals). Two earlier gvlab parity attempts were invalid "
          "(missing scipy, then PIL in the 3D venv); fixed with a separate 2D venv pinned to the laptop freeze (Python 3.13.11, numpy 2.4.6, scipy 1.18.1).\n"]
    for dom in ("2d", "3d"):
        r = R[dom]
        mh += [f"\n## {dom.upper()}\n", "CPU by host:\n", md_table(r["cpu_by_host"]),
               "\nCPU by final strength of the job:\n", md_table(r["cpu_by_final_strength"]),
               "\nYield by start strength:\n", md_table(r["yield_by_start_strength"]),
               f"\nGeneration CPU-h total: {r['generation_cpu_h_total']}; new gate-pass roots per strength: ```{json.dumps(r['new_roots']['by_strength_gate_pass'])}```\n"]
    mh.append("\nWindow: both hosts stopped by STOP file at 2026-11-11T10:28Z (12 h cap incl. pilot); in-flight jobs are MISSING, not failures. "
              "Validation (consistency, X/Y) ran after the cap on the freed CPUs within the same caps.\n")
    (OUT / "K3_MULTIHOST_RESOURCE_REPORT.md").write_text("".join(mh))
    with open(OUT / "SHA256SUMS", "w") as f:
        for p in sorted(OUT.glob("*")):
            if p.name != "SHA256SUMS":
                f.write(f"{sha_file(p)}  {p.name}\n")
    for dom in ("2d", "3d"):
        print(dom, R[dom]["selection"]["selected_distribution"], R[dom]["uniqueness_lineage"]["lineage_failures"], R[dom]["witness_integrity_selected_new_roots"])


if __name__ == "__main__":
    main()
