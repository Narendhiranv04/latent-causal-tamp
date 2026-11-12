#!/usr/bin/env python3
"""Analyse the 3D replay audit (work/rpl3d_AB.jsonl + work/rpl3d_C.jsonl) -> manifests/3D_REPLAY_RESULTS.json,
manifests/OMISSION_13_VERDICTS.json, manifests/PROPOSED_CORRECTION_MANIFEST.json, work/3d_stats.json."""
import collections as C, hashlib, json
from pathlib import Path

H = Path(__file__).resolve().parent
GATE, G = H.parent, H.parent.parent
PKG = G / "FINAL_3D_DATASET_V4"
SRC = Path("/home/naren/Desktop/rss3d_final_src/gh-yadu-iiith/shelf_6x6_open_sides/dataset_bd_classquota_without_home_position_no_overpass")
SPLITF = Path("/home/naren/Desktop/rss-3d-relocations/gh-yadu-iiith/shelf_6x6_open_sides/dataset_placement_extension_v2/production_v3/frozen/")


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()] if Path(p).exists() else []


def okey(order):
    return "".join(o[-1] for o, _ in order)


def hh(s):
    return hashlib.sha256(s.encode()).hexdigest()


def main():
    labels = json.loads((PKG / "FINAL_3D_XY_LABEL_MANIFEST.json").read_text())["rows"]
    selm = json.loads((PKG / "FINAL_3D_SELECTION_MANIFEST.json").read_text())
    sel = {r["root_id"]: r for r in selm["rows"]}
    by_root = C.defaultdict(list)
    for l in labels:
        if l["row_kind"] == "SELECTED_ASSIGNMENT_ORDER":
            by_root[l["root_id"]].append(l)
    strength = {rid: sum(x["x"] for x in ls) for rid, ls in by_root.items()}
    seen, Q = set(), []
    for f in ("rpl3d_AB.jsonl", "rpl3d_C.jsonl", "rpl3d_D.jsonl", "rpl3d_E.jsonl", "rpl3d_GV.jsonl"):
        for r in jl(GATE / "work" / f):
            for q in r["results"]:
                k = (r["root_id"], q["qid"])
                if k in seen:
                    continue
                seen.add(k)
                Q.append({**q, "root_id": r["root_id"], "root_sha256_ok": r.get("root_sha256_ok")})
    real = [q for q in Q if q["q"] in ("X", "Y")]
    tier = lambda q: "A_MANDATORY" if any(t.startswith("M_") for t in q["tags"]) else ("B_STRATIFIED" if any(t.startswith("S_") for t in q["tags"]) else
                                                                                                           "D_RERUN_REPLAY" if any(t.startswith("D_") for t in q["tags"]) else
                                                                                                           "E_EMPTY_SAMPLE" if any(t.startswith("E_") for t in q["tags"]) else "C_ALL_WITNESSED")
    agree = lambda q: q["verdict"] in ("AGREE", "AGREE_VALUE_PHASE_DIFFERS")
    tab = C.defaultdict(C.Counter)
    for q in real:
        lab = q.get("label_x") if q["q"] == "X" else q.get("label_y")
        how = "RERUN+REPLAY" if q.get("rerun") else "STORED_WITNESS_REPLAY"
        keys = [("tier", tier(q)), ("query", q["q"], q.get("row_kind")), ("query_label", q["q"], q.get("row_kind"), lab), ("method", q["q"], how),
                ("split", q["q"], q.get("split")), ("K", q["q"], q.get("K"))]
        if q["q"] == "X" and q["row_kind"] == "SELECTED_ASSIGNMENT_ORDER":
            keys += [("x_provenance", q["x_provenance"].split("(")[0]), ("phase", "none" if lab == 1 else (q.get("label_phase") or "?").split(":")[0] + ":" + (q.get("label_phase") or "?").split(":")[-1]),
                     ("K3_strength", strength.get(q["root_id"])) if q.get("K") == "3" else ("K2_strength", strength.get(q["root_id"])),
                     ("source_family", sel[q["root_id"]]["source"]), ("xy_cell", f"X={q['label_x']},Y={q['label_y']}")]
        for k in keys:
            tab[k]["n"] += 1
            tab[k]["agree"] += int(agree(q))
            tab[k][q["verdict"]] += 1
    rerun = C.Counter()
    for q in real:
        if q.get("rerun"):
            rerun[(q["q"], "agree" if q.get("rerun_agrees_with_label") else "disagree")] += 1
    mism = [{"root_id": q["root_id"], "qid": q["qid"], "q": q["q"], "row_kind": q.get("row_kind"), "label": q.get("label_x", q.get("label_y")),
             "label_phase": q.get("label_phase"), "verdict": q["verdict"], "replay": {k: (q.get("replay") or {}).get(k) for k in ("x", "y", "phase", "how", "failure", "resolution", "error")},
             "rerun": q.get("rerun"), "error": q.get("error"), "steps": (q.get("replay") or {}).get("steps") or (q.get("replay") or {}).get("step"),
             "connector": (q.get("replay") or {}).get("connector")} for q in real if not agree(q)]
    grasp = C.Counter()
    for q in real:
        rp = q.get("replay") or {}
        for s in (rp.get("steps") or []) + ([rp["step"]] if rp.get("step") else []):
            grasp[s.get("grasp_match")] += 1
    # ---------------- ISSUE 1: the 13 omission roots
    om_rows = [l for l in labels if l["row_kind"] == "OMISSION_YNEG"]
    om13 = sorted({l["root_id"] for l in om_rows if l["y"] == 1})
    qi = {(q["root_id"], q["qid"]): q for q in Q}
    verdicts = []
    for rid in om13:
        rs = [l for l in om_rows if l["root_id"] == rid]
        yq = qi.get((rid, "Y_OM"))
        orders = []
        for l in rs:
            k = okey(l["relocations"])
            xq, lg = qi.get((rid, "X_OM_" + k)), qi.get((rid, "L_OM_" + k))
            xr = (xq or {}).get("replay") or {}
            yr = (yq or {}).get("replay") or {}
            rx, ry = xr.get("x"), yr.get("y")
            v = ("PENDING_NOT_REPLAYED" if xq is None or yq is None else "VERIFIED_SHORTER_REPAIR_X1_Y1" if rx == 1 and ry == 1 and l["x"] == 1 else
                 "RETAIN_K_X0_Y1" if rx == 0 and l["x"] == 0 and ry == 1 else "UNRESOLVED_REPLAY_DISAGREES")
            orders.append({"order": l["order"], "relocations": l["relocations"], "label_x": l["x"], "label_x_phase": l.get("x_phase"), "x_witnesses": l.get("x_witnesses"),
                           "replay_x": rx, "replay_x_phase": xr.get("phase"), "replay_x_how": xr.get("how"), "replay_verdict": (xq or {}).get("verdict"),
                           "legacy_shortened": {k2: ((lg or {}).get("legacy") or {}).get(k2) for k2 in ("y", "reason", "failed_step", "negative_kind")},
                           "verdict": v})
        sr = sel[rid]
        selq = [qi.get((rid, "X_SEL_" + okey(l["relocations"]))) for l in by_root[rid]]
        sy = qi.get((rid, "Y_SEL"))
        any_short = any(o["verdict"] == "VERIFIED_SHORTER_REPAIR_X1_Y1" for o in orders)
        full = [l for l in by_root[rid]]
        verdicts.append({"root_id": rid, "K": sr["K"], "split": sr["split"], "source": sr["source"], "layout_root_id": sr["layout_root_id"],
                         "layout_origin": sr.get("layout_origin"), "method": sr.get("method"),
                         "selected_assignment": full[0]["relocations"] if full else None, "omitted": rs[0]["omitted"],
                         "endpoint_after_omission": {o: d for o, d in rs[0]["relocations"]}, "label_y_omission": rs[0]["y"],
                         "replay_y_omission": ((yq or {}).get("replay") or {}).get("y"), "replay_y_how": ((yq or {}).get("replay") or {}).get("how"),
                         "y_witness_replayed": bool(((yq or {}).get("replay") or {}).get("step")),
                         "orders": orders,
                         "selected_rows_replay": {"n": len(selq), "agree": sum(1 for q in selq if q and agree(q)), "y_agree": bool(sy and agree(sy)),
                                                  "x_strength_label": strength.get(rid), "y_label": full[0]["y"] if full else None},
                         "verdict": "K_INCONSISTENT_UNDER_FINALIZED_PROTOCOL" if any_short else
                         ("K_RETAINED" if all(o["verdict"] == "RETAIN_K_X0_Y1" for o in orders) else "UNRESOLVED"),
                         "legacy_also_succeeds_shortened": any((o["legacy_shortened"] or {}).get("y") == 1 for o in orders)})
    pairs = {(v["root_id"], v["omitted"]) for v in verdicts}
    # ---------------- proposed corrections
    sm = json.loads((SPLITF / "split_manifest_first_cohort.json").read_text()) if (SPLITF / "split_manifest_first_cohort.json").exists() else None
    pub = json.loads((SRC / "selected.json").read_text())
    excl = set(pub.get("excluded_fixed_object", {}))
    fam_split = {}
    for rid, r in sel.items():
        try:
            p = Path(r["path"]) if Path(r["path"]).is_absolute() else Path("/home/naren/Desktop/rss3d_final_src") / r["path"]
            fam_split.setdefault(json.loads(p.read_text())["ids"]["parent_family_id"], set()).add(r["split"])
        except Exception:  # noqa: BLE001
            pass
    cands = {"3": [], "2": []}
    for x in selm["new_layout_pool"]:
        if not x["chosen"]:
            cands["3"].append({"root_id": x["root_id"], "origin": x["origin"], "legacy_min_n_success": x["min_ns"]})
    for f in sorted((SRC / "raw/roots").glob("*.json")):
        if f.stem in sel or f.stem in excl:
            continue
        r = json.loads(f.read_text())
        if str(r.get("verified_K")) == "2":
            cands["2"].append({"root_id": f.stem, "origin": "PUBLISHED_RAW_K2_NOT_SELECTED", "independent_moves": r.get("independent_moves"),
                               "parent_family_id": r["ids"]["parent_family_id"]})
    old_split = (sm or {}).get("split", {})
    for k, cs in cands.items():
        for c in cs:
            if c["root_id"] in old_split:
                c["split_if_admitted"], c["split_how"] = old_split[c["root_id"]], "FROZEN_SPLIT_MANIFEST"
            elif c.get("parent_family_id") in fam_split and len(fam_split[c["parent_family_id"]]) == 1:
                c["split_if_admitted"], c["split_how"] = next(iter(fam_split[c["parent_family_id"]])), "INHERITED_FROM_SELECTED_FAMILY"
            else:
                x = int(hh("|".join(("SHELF66V3_PLACE_ROSTER_V1", "split", c["root_id"])))[:15], 16) / 16 ** 15
                c["split_if_admitted"], c["split_how"] = ("train" if x < 0.70 else "val" if x < 0.85 else "test"), "V1_RULE_SINGLETON_ESTIMATE"
            c["finalized_xy_available"] = False
            c["omission_checked"] = False
    corr = []
    for v in verdicts:
        if v["verdict"] != "K_INCONSISTENT_UNDER_FINALIZED_PROTOCOL":
            continue
        same = [c for c in cands[v["K"]] if c["split_if_admitted"] == v["split"]]
        corr.append({"original_root_id": v["root_id"], "K": v["K"], "split": v["split"], "layout_root_id": v["layout_root_id"], "source": v["source"],
                     "evidence": {"omitted": v["omitted"], "shorter_orders_X1_Y1_replayed": [o["order"] for o in v["orders"] if o["verdict"] == "VERIFIED_SHORTER_REPAIR_X1_Y1"],
                                  "legacy_teacher_also_succeeds_on_shortened_order": v["legacy_also_succeeds_shortened"]},
                     "implied_K_upper_bound_finalized": int(v["K"]) - 1,
                     "proposal": "REMOVE_FROM_K%s_OR_RELABEL_PENDING_USER_DECISION" % v["K"],
                     "replacement_candidates_same_class_same_split": [c["root_id"] for c in same],
                     "replacement_candidates_note": "existing scenes only; none has finalized X/Y or an omission check yet (would need X/Y + omission + replay before admission)"})
    for rid, ls in sorted(by_root.items()):                          # selected assignments without any finalized X1Y1 order
        if all(l["x"] in (0, 1) and l["y"] in (0, 1) for l in ls) and not any(l["x"] == 1 and l["y"] == 1 for l in ls):
            sr = sel[rid]
            nat = sr.get("natural_assignment") or {}
            same_layout = [nat["root_id"]] if nat.get("root_id") and nat["root_id"] != rid else []
            corr.append({"original_root_id": rid, "K": sr["K"], "split": sr["split"], "layout_root_id": sr["layout_root_id"], "source": sr["source"],
                         "reason": "NO_FINALIZED_X1Y1_ORDER (the selected K-repair is not verified under the finalized protocol)",
                         "evidence": {"x_strength": sum(l["x"] for l in ls), "n_orders": len(ls), "y_endpoint": ls[0]["y"], "legacy_strength": sum(1 for l in ls if l["legacy_y"] == 1),
                                      "y_replay": (qi.get((rid, "Y_SEL")) or {}).get("verdict")},
                         "proposal": "REPLACE_ASSIGNMENT_WITHIN_LAYOUT" if same_layout else "REMOVE_FROM_K%s_OR_RELABEL_PENDING_USER_DECISION" % sr["K"],
                         "replacement_candidates_same_layout_same_split": same_layout,
                         "replacement_candidates_same_class_same_split": [c["root_id"] for c in cands[sr["K"]] if c["split_if_admitted"] == sr["split"]],
                         "replacement_candidates_note": "existing scenes only; none has finalized X/Y or an omission check yet"})
    for c in corr:
        c.setdefault("reason", "OMISSION_X1Y1 (a verified (K-1)-relocation repair exists under the finalized protocol)")
    cons = C.Counter((c["K"], c["split"]) for c in corr)
    out_v = {"version": "OMISSION_13_VERDICTS_V1", "n_rows_with_omission_y1": sum(1 for l in om_rows if l["y"] == 1), "n_unique_roots": len(om13),
             "n_unique_root_omission_pairs": len(pairs), "verdicts": verdicts,
             "summary": dict(C.Counter(v["verdict"] for v in verdicts)), "order_summary": dict(C.Counter(o["verdict"] for v in verdicts for o in v["orders"]))}
    (GATE / "manifests/OMISSION_13_VERDICTS.json").write_text(json.dumps(out_v, indent=1))
    k_counts = {k: v for k, v in selm["counts"].items()}
    after = dict(k_counts)
    for c in corr:
        after[c["K"]] -= 1
    (GATE / "manifests/PROPOSED_CORRECTION_MANIFEST.json").write_text(json.dumps({
        "version": "PROPOSED_3D_CORRECTIONS_V1", "status": "PROPOSAL_ONLY_NOT_APPLIED (no scene changed, no K changed, no replacement admitted)",
        "corrections": corr, "quota_consequence": {"current": k_counts, "if_removed_without_replacement": after, "removed_by_K_split": {f"K{k}/{s}": n for (k, s), n in cons.items()}},
        "candidate_pool": cands}, indent=1))
    stats = {"n_queries": len(real), "n_agree": sum(1 for q in real if agree(q)), "verdicts": dict(C.Counter(q["verdict"] for q in real)),
             "tables": {"|".join(map(str, k)): dict(v) for k, v in tab.items()}, "rerun_teacher_reproducibility": {"|".join(k): v for k, v in rerun.items()},
             "mismatches": mism, "grasp_recovery": dict(grasp), "root_sha_all_ok": all(q["root_sha256_ok"] for q in Q),
             "legacy_diag": [(q["root_id"], q["qid"], (q.get("legacy") or {}).get("y")) for q in Q if q["q"] == "LEGACY"]}
    (GATE / "work/3d_stats.json").write_text(json.dumps(stats, indent=1))
    (GATE / "manifests/3D_REPLAY_RESULTS.json").write_text(json.dumps({"version": "3D_REPLAY_AUDIT_V1", "queries": Q}))
    print(json.dumps({k: stats[k] for k in ("n_queries", "n_agree", "verdicts", "rerun_teacher_reproducibility", "grasp_recovery", "root_sha_all_ok")}, default=str))
    print("omission13", out_v["summary"], out_v["order_summary"], "pairs", len(pairs))
    print("mismatches", len(mism))


if __name__ == "__main__":
    main()
