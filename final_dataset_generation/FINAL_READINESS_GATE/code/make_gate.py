#!/usr/bin/env python3
"""FINAL_READINESS_GATE package: integrity gates for 2D (5,000) and 3D (2,500), label distributions, readiness decision, reports, SHA256SUMS.
Inputs: manifests/2D_FINAL_XY_LABEL_MANIFEST.json + work/2d_stats.json (assemble2d.py), manifests/OMISSION_13_VERDICTS.json,
PROPOSED_CORRECTION_MANIFEST.json, 3D_REPLAY_RESULTS.json + work/3d_stats.json (analyze3d.py), FINAL_3D_DATASET_V4 (read-only)."""
import collections as C, hashlib, json, subprocess, time
from pathlib import Path

import numpy as np

H = Path(__file__).resolve().parent
GATE, G = H.parent, H.parent.parent
MAN, WK = GATE / "manifests", GATE / "work"
PKG = G / "FINAL_3D_DATASET_V4"
SEL2 = G / "k3_hard/2D_K3_STRENGTH_SELECTION_V3.json"
V3PKG = G / "k3_hard/K3_HARD_ORDER_V1"
Q2 = {"0": 1250, "1": 800, "2": 800, "3": 1150, "NONE": 1000}
Q3 = {"NONE": 408, "0": 511, "1": 357, "2": 612, "3": 612}
SPL = ("train", "val", "test")
CELLS = ("X=1,Y=1", "X=0,Y=1", "X=1,Y=0", "X=0,Y=0")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rehash(p):
    z = np.load(p, allow_pickle=False)
    h = hashlib.sha256()
    for k in sorted(z.files):
        v = np.ascontiguousarray(np.asarray(z[k]))
        h.update(f"{k}|{v.dtype.str}|{v.shape}".encode()); h.update(v.tobytes())
    return h.hexdigest()[:24]


def cell(x, y):
    return f"X={x},Y={y}" if x in (0, 1) and y in (0, 1) else "missing"


def md_table(head, rows):
    return "\n".join(["| " + " | ".join(map(str, head)) + " |", "|" + "|".join("---" if i == 0 else "---:" for i in range(len(head))) + "|"] +
                     ["| " + " | ".join(map(str, r)) + " |" for r in rows])


def main():
    t0 = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    sel2 = json.loads(SEL2.read_text())["rows"]
    lab2 = json.loads((MAN / "2D_FINAL_XY_LABEL_MANIFEST.json").read_text())["rows"]
    st2 = json.loads((WK / "2d_stats.json").read_text())
    sel3m = json.loads((PKG / "FINAL_3D_SELECTION_MANIFEST.json").read_text())
    sel3 = sel3m["rows"]
    lab3 = json.loads((PKG / "FINAL_3D_XY_LABEL_MANIFEST.json").read_text())["rows"]
    st3 = json.loads((WK / "3d_stats.json").read_text())
    om13 = json.loads((MAN / "OMISSION_13_VERDICTS.json").read_text())
    corr = json.loads((MAN / "PROPOSED_CORRECTION_MANIFEST.json").read_text())
    gates = {}

    def gate(name, ok, detail):
        gates[name] = {"pass": bool(ok), "detail": detail}
    # ---------------------------------------------------------------- 1-3 counts / quotas
    c2, c3 = C.Counter(r["K"] for r in sel2), C.Counter(r["K"] for r in sel3)
    gate("G1_2D_exactly_5000", len(sel2) == 5000 and len({r["root_id"] for r in sel2}) == 5000, {"rows": len(sel2), "unique": len({r["root_id"] for r in sel2})})
    gate("G2_3D_exactly_2500_main", len(sel3) == 2500 and len({r["root_id"] for r in sel3}) == 2500, {"rows": len(sel3), "k4_archived_outside": len(sel3m["k4_archived"]["ids"])})
    gate("G3_quotas", dict(c2) == Q2 and dict(c3) == Q3, {"2D": dict(c2), "3D": dict(c3)})
    # ---------------------------------------------------------------- 4 roots / labels / witnesses resolve
    miss, wc = [], C.Counter()
    src3 = Path("/home/naren/Desktop/rss3d_final_src")
    recs3 = {}
    for r in sel3:
        p = Path(r["path"]) if Path(r["path"]).is_absolute() else src3 / r["path"]
        if not p.exists():
            miss.append(r["root_id"]); continue
        if r.get("root_sha256") and sha(p) != r["root_sha256"]:
            wc["3d_root_sha_mismatch"] += 1
        recs3[r["root_id"]] = json.loads(p.read_text())
    stores3 = [G / "final3d_v4/work/store", G / "final3d_v4/work/store_gvlab", G / "k3_hard/d3/store", WK / "rpl_store"]

    def fw(w, stores):
        for s in stores:
            f = s / "witnesses" / w[:2] / f"{w}.npz"
            if f.exists():
                return f
    seen = set()
    ywit = set()
    for q in json.loads((MAN / "3D_REPLAY_RESULTS.json").read_text())["queries"]:
        if q["q"] == "Y" and q.get("witnesses"):
            ywit.update(q["witnesses"])
    for f in ("k2_xy_yneg.jsonl", "xy_final_laptop.jsonl", "xy_final_gvlab.jsonl", "xy_assist_laptop.jsonl", "es_verify.jsonl"):
        for line in open(G / "final3d_v4/work" / f):
            r = json.loads(line)
            if r.get("y"):
                ywit.update(r["y"].get("witnesses") or [])
    for w in [w for l in lab3 for w in (l.get("x_witnesses") or [])] + sorted(ywit):
        if w in seen:
            continue
        seen.add(w)
        f = fw(w, stores3)
        wc["3d:" + ("missing" if f is None else "ok" if rehash(f) == w else "hash_mismatch")] += 1
    w2 = WK / "xy2d_witnesses"
    for l in lab2:
        for w in (l.get("x_witnesses") or []) + ([l["y_witness"]] if l.get("y_witness") else []):
            if w in seen:
                continue
            seen.add(w)
            f = w2 / "witnesses" / w[:2] / f"{w}.npz"
            wc["2d:" + ("missing" if not f.exists() else "ok" if rehash(f) == w else "hash_mismatch")] += 1
    lab_missing2 = sum(1 for l in lab2 if l["x"] not in (0, 1) or l["y"] not in (0, 1))
    lab_missing3 = sum(1 for l in lab3 if l["x"] not in (0, 1) or l["y"] not in (0, 1))
    gate("G4_roots_labels_witnesses_resolve", not miss and not wc["3d:missing"] and not wc["3d:hash_mismatch"] and not wc["2d:missing"] and not wc["2d:hash_mismatch"]
         and not lab_missing2 and not lab_missing3 and not wc["3d_root_sha_mismatch"],
         {"3d_roots_missing": miss, "witness_check": dict(wc), "2d_label_rows_missing_x_or_y": lab_missing2, "3d_label_rows_missing_x_or_y": lab_missing3,
          "note": "2D rows reused from k3_hard/xy2d_all.jsonl carry teacher replay flags but no witness ids (parity re-run regenerates them)"})
    # ---------------------------------------------------------------- 5 hashes / unique endpoints / lineage-disjoint splits
    sh2 = st2["coverage"].get("source_sha_mismatch", 0)
    fam3 = C.defaultdict(set)
    lay3 = C.defaultdict(set)
    for r in sel3:
        rec = recs3[r["root_id"]]
        fam3[rec["ids"]["parent_family_id"]].add(r["split"])
        lay = json.dumps([sorted((o["id"], o["shape"], round(o["size"], 6), round(o["height"], 6)) for o in rec["objects"]),
                          sorted((k, list(v)) for k, v in rec["initial_cells"].items())])
        lay3[lay].add((r["split"], r["K"]))
    fam_conf3 = {f: sorted(s) for f, s in fam3.items() if len(s) > 1}
    lay_dup3 = sum(1 for v in lay3.values() if len(v) > 1)
    fam2 = C.defaultdict(set)
    for l in lab2:
        fam2[l["parent_family_id"]].add(l["split"])
    fam_conf2 = {f: sorted(s) for f, s in fam2.items() if len(s) > 1}
    gate("G5_hashes_endpoints_lineage", sh2 == 0 and not wc["3d_root_sha_mismatch"] and not fam_conf3 and not fam_conf2,
         {"2d_source_sha_mismatch": sh2, "3d_root_sha_mismatch": wc["3d_root_sha_mismatch"], "3d_family_split_conflicts": len(fam_conf3),
          "2d_family_split_conflicts": len(fam_conf2), "3d_layouts_shared_by_two_selected_rows": lay_dup3})
    # ---------------------------------------------------------------- 6 / 9 identical endpoints share one Y; no contradicting duplicates
    lay_of = {r["layout_root_id"]: r["root_id"] for r in sel3}

    def ykey3(rid, relocs):
        rec = recs3[rid] if rid in recs3 else recs3[lay_of[rid]]          # EMPTY_SEQUENCE rows of re-parked K3 rows are keyed by their layout root
        cells = {**{k: list(v) for k, v in rec["initial_cells"].items()}, **{o: list(d) for o, d in relocs}}
        return hashlib.sha256(json.dumps([sorted((o["id"], o["shape"], round(o["size"], 6), round(o["height"], 6)) for o in rec["objects"]),
                                          sorted((k, list(v)) for k, v in cells.items()), list(rec["goal"])]).encode()).hexdigest()
    yv3, xv3 = C.defaultdict(set), C.defaultdict(set)
    for l in lab3:
        yv3[ykey3(l["root_id"], l["relocations"])].add(l["y"])
        if l["relocations"]:
            xv3[(l["root_id"], json.dumps(l["relocations"]))].add(l["x"])
    yc3 = sum(1 for v in yv3.values() if len(v) > 1)
    xc3 = sum(1 for v in xv3.values() if len(v) > 1)
    yv2, xv2 = C.defaultdict(set), C.defaultdict(set)
    for l in lab2:
        yv2[(l["root_id"], json.dumps(sorted(map(tuple, l["relocations"]))))].add(l["y"])
        if l["relocations"]:
            xv2[(l["root_id"], json.dumps(l["relocations"]))].add(l["x"])
    yc2 = sum(1 for v in yv2.values() if len(v) > 1) + len(st2.get("y_key_contradictions", {}))
    xc2 = sum(1 for v in xv2.values() if len(v) > 1)
    gate("G6_identical_endpoints_share_one_Y", yc3 == 0 and yc2 == 0, {"3d_endpoints": len(yv3), "3d_conflicts": yc3, "2d_endpoints": len(yv2), "2d_conflicts": yc2})
    # ---------------------------------------------------------------- 7 finalized teachers (no legacy substitution)
    p3 = C.Counter((l["row_kind"], l["x_provenance"].split("(")[0], l["y_provenance"].split("(")[0]) for l in lab3)
    p2 = C.Counter((l["row_kind"], l["x_provenance"].split("(")[0], l["y_provenance"].split("(")[0]) for l in lab2)
    tab = st3["tables"]
    r2 = tab.get("x_provenance|R2_FRESH_LEGACY_RELOCATION_FAILURE", {})
    n_r2 = sum(1 for l in lab3 if l["x_provenance"].startswith("R2"))
    rr = st3["rerun_teacher_reproducibility"]
    r2_ok = r2.get("n", 0) == n_r2 and r2.get("agree", 0) == n_r2
    leg_used = sum(1 for l in lab2 if "LEGACY" in l["x_provenance"].upper())
    emp = st2["parity"]
    gate("G7_finalized_teachers_only", r2_ok and leg_used == 0,
         {"3d_provenance": {"|".join(k): v for k, v in p3.items()}, "2d_provenance": {"|".join(k): v for k, v in p2.items()},
          "3d_R2_rows": n_r2, "3d_R2_rows_rerun_by_finalized_teacher_and_replayed": r2.get("n", 0), "3d_R2_agree": r2.get("agree", 0),
          "2d_empty_endpoint_labels_original_parity": f"{emp.get('empty_agree', 0)}/{emp.get('empty_checked', 0)}",
          "note": "2D: every empty endpoint (K0-K3, NONE) has a BXY_Y_TEACHER_V1 query run in this gate (labels.original kept as legacy, parity reported). "
                  "3D EMPTY_SEQUENCE_YNEG uses the teacher's original direct check (bd_3dt.query of t0 from q_ready in the unedited scene = the Y "
                  "teacher's query on the empty endpoint; es_verify fresh re-run 60/60)"})
    # ---------------------------------------------------------------- 8 supervision per split
    def dist(lab, kinds):
        d = C.defaultdict(C.Counter)
        for l in lab:
            if l["row_kind"] in kinds:
                d[l["split"]][cell(l["x"], l["y"])] += 1
        return d
    learn2 = dist(lab2, ("SELECTED_ASSIGNMENT_ORDER", "OMISSION_YNEG", "EMPTY_SEQUENCE_YNEG", "EMPTY_SEQUENCE_K0"))
    learn3 = dist(lab3, ("SELECTED_ASSIGNMENT_ORDER", "OMISSION_YNEG", "EMPTY_SEQUENCE_YNEG"))
    absent = {f"{dom}/{s}/{c_}": 0 for dom, d in (("2D", learn2), ("3D", learn3)) for s in SPL for c_ in CELLS if d[s][c_] == 0}
    gate("G8_meaningful_pos_neg_per_split", all(d[s]["X=1,Y=1"] > 0 and d[s]["X=1,Y=0"] + d[s]["X=0,Y=0"] > 0 and d[s]["X=0,Y=1"] + d[s]["X=0,Y=0"] > 0
                                                for d in (learn2, learn3) for s in SPL),
         {"2D": {s: dict(learn2[s]) for s in SPL}, "3D": {s: dict(learn3[s]) for s in SPL}, "absent_cells": sorted(absent)})
    gate("G9_no_contradicting_duplicates", xc3 == 0 and xc2 == 0 and yc3 == 0 and yc2 == 0, {"3d_x_conflicts": xc3, "2d_x_conflicts": xc2, "3d_y_conflicts": yc3, "2d_y_conflicts": yc2})
    ps = subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True).stdout
    tr = [l for l in ps.splitlines() if any(s in l for s in ("abc_train", "train.py", "abc7_train", "torchrun")) and "grep" not in l]
    gate("G10_no_training_launched", not tr, {"training_processes": tr})
    # ---------------------------------------------------------------- 3D replay / K-consistency
    rep_ok = st3["n_queries"] > 0 and st3["n_agree"] == st3["n_queries"]
    gate("G11_3D_replay_agreement", rep_ok, {"agree": st3["n_agree"], "queries": st3["n_queries"], "mismatches": len(st3["mismatches"])})
    par = st2["parity"]
    gate("G12_2D_reuse_parity", par.get("sel_x_checked", 0) > 0 and par.get("sel_x_agree") == par.get("sel_x_checked") and par.get("sel_y_agree") == par.get("sel_y_checked")
         and emp.get("empty_agree") == emp.get("empty_checked"), dict(par))
    # 2D K-consistency (same rule as the 3D omission check) + selected roots without any finalized X1Y1 order
    k2d_om = sorted({(l["root_id"], l["K"], l["split"], l["omitted"]) for l in lab2 if l["row_kind"] == "OMISSION_YNEG" and l["x"] == 1 and l["y"] == 1})
    by2 = C.defaultdict(list)
    for l in lab2:
        if l["row_kind"] == "SELECTED_ASSIGNMENT_ORDER":
            by2[l["root_id"]].append(l)
    nov2 = sorted((rid, ls[0]["K"], ls[0]["split"], sum(1 for l in ls if l["x"] == 1), ls[0]["y"]) for rid, ls in by2.items()
                  if all(l["x"] in (0, 1) and l["y"] in (0, 1) for l in ls) and not any(l["x"] == 1 and l["y"] == 1 for l in ls))
    by3 = C.defaultdict(list)
    for l in lab3:
        if l["row_kind"] == "SELECTED_ASSIGNMENT_ORDER":
            by3[l["root_id"]].append(l)
    nov3 = sorted((rid, ls[0]["K"], ls[0]["split"], sum(1 for l in ls if l["x"] == 1), ls[0]["y"]) for rid, ls in by3.items()
                  if not any(l["x"] == 1 and l["y"] == 1 for l in ls))
    k3d = [c_["original_root_id"] for c_ in corr["corrections"] if c_["reason"].startswith("OMISSION")]
    om2y1 = sorted({(l["root_id"], l["K"]) for l in lab2 if l["row_kind"] == "OMISSION_YNEG" and l["y"] == 1})
    kinc = {"3D_omission_X1Y1_shorter_repair": k3d, "3D_selected_without_X1Y1_order": [x[0] for x in nov3], "2D_omission_X1Y1_shorter_repair": [x[0] for x in k2d_om],
            "2D_selected_without_X1Y1_order": [x[0] for x in nov2]}
    n_k23_2 = sum(1 for r in sel2 if r["K"] in ("2", "3")) + sum(1 for r in sel2 if r["K"] == "1")
    n_k23_3 = sum(1 for r in sel3 if r["K"] in ("2", "3"))
    rate2 = len(set(kinc["2D_omission_X1Y1_shorter_repair"]) | set(kinc["2D_selected_without_X1Y1_order"])) / n_k23_2
    rate3 = len(set(k3d) | set(kinc["3D_selected_without_X1Y1_order"])) / n_k23_3
    gate("G13_K_consistency_under_finalized_protocol", not any(kinc.values()),
         {**{k: len(v) for k, v in kinc.items()}, "2D_rate_over_K1_K3": round(rate2, 4), "3D_rate_over_K2_K3": round(rate3, 4)})
    # ---------------------------------------------------------------- distributions
    def full(lab, kinds):
        d = C.defaultdict(C.Counter)
        for l in lab:
            if l["row_kind"] in kinds:
                d[(l["row_kind"], l["K"], l["split"])][cell(l["x"], l["y"])] += 1
        return d
    D2 = full(lab2, ("SELECTED_ASSIGNMENT_ORDER", "OMISSION_YNEG", "EMPTY_SEQUENCE_YNEG", "EMPTY_SEQUENCE_K0"))
    D3 = full(lab3, ("SELECTED_ASSIGNMENT_ORDER", "OMISSION_YNEG", "EMPTY_SEQUENCE_YNEG"))
    yneg = {}
    for dom, lab in (("2D", lab2), ("3D", lab3)):
        y = C.Counter()
        for l in lab:
            if l["y"] == 0:
                y[(l["row_kind"], l["split"])] += 1
        yneg[dom] = {f"{k[0]}|{k[1]}": v for k, v in sorted(y.items())}
    s2 = C.Counter((x["K"], x["split"], x["x_strength"]) for x in st2["strength"] if x["K"] == "3")
    sl2 = C.Counter((x["K"], x["split"], x["legacy_strength"]) for x in st2["strength"] if x["K"] == "3")
    s3 = C.Counter()
    for rid, ls in by3.items():
        if ls[0]["K"] == "3":
            s3[(ls[0]["split"], sum(l["x"] for l in ls), sum(1 for l in ls if l["legacy_y"] == 1))] += 1
    dists = {"2D": {"|".join(k): dict(v) for k, v in sorted(D2.items())}, "3D": {"|".join(k): dict(v) for k, v in sorted(D3.items())},
             "y_negatives": yneg,
             "2D_K3_strength": {"finalized_x": {f"{sp}|{n}/6": sum(v for (K, s_, n_), v in s2.items() if s_ == sp and n_ == n) for sp in SPL for n in range(7)},
                                "legacy": {f"{sp}|{n}/6": sum(v for (K, s_, n_), v in sl2.items() if s_ == sp and n_ == n) for sp in SPL for n in range(7)}},
             "3D_K3_strength": {"finalized_x": {f"{sp}|{n}/6": sum(v for (s_, x_, l_), v in s3.items() if s_ == sp and x_ == n) for sp in SPL for n in range(7)},
                                "legacy": {f"{sp}|{n}/6": sum(v for (s_, x_, l_), v in s3.items() if s_ == sp and l_ == n) for sp in SPL for n in range(7)}}}
    lab_by2 = {r["root_id"]: r for r in sel2}
    (MAN / "2D_PROPOSED_CORRECTIONS.json").write_text(json.dumps({
        "version": "PROPOSED_2D_CORRECTIONS_V1", "status": "PROPOSAL_ONLY_NOT_APPLIED",
        "K_REPAIR_UNVERIFIED_UNDER_FINALIZED_PROTOCOL": [
            {"root_id": rid, "K": K, "split": sp, "source": lab_by2[rid]["source"], "x_strength": xs, "n_orders": len(by2[rid]), "y_endpoint": y,
             "legacy_successes": sum(1 for l in by2[rid] if l["legacy_y"] == 1),
             "x_failures": sorted({f"{l.get('x_status')}@{(l.get('x_phase') or '').split(':')[0]}" for l in by2[rid] if l["x"] == 0}),
             "options": ["keep with K as the legacy-verified class tag (finalized X/Y rows stay as measured X=0,Y=1 supervision)",
                         "reclassify out of K (finalized minimal K unknown, >= K or no repair within budget)", "replace with a same-class same-split scene (needs X/Y first)"]}
            for rid, K, sp, xs, y in nov2],
        "K_CONTRADICTION_SHORTER_REPAIR": [list(x) for x in k2d_om]}, indent=1))
    (MAN / "FINAL_LABEL_DISTRIBUTIONS.json").write_text(json.dumps(dists, indent=1))
    # ---------------------------------------------------------------- decision
    hard = [g for g in ("G1_2D_exactly_5000", "G2_3D_exactly_2500_main", "G3_quotas", "G4_roots_labels_witnesses_resolve", "G5_hashes_endpoints_lineage",
                        "G6_identical_endpoints_share_one_Y", "G7_finalized_teachers_only", "G8_meaningful_pos_neg_per_split", "G9_no_contradicting_duplicates",
                        "G10_no_training_launched", "G11_3D_replay_agreement", "G12_2D_reuse_parity") if not gates[g]["pass"]]
    KTHR = 0.01
    k_block = rate2 > KTHR or rate3 > KTHR
    status = "BLOCKED" if hard or k_block else ("READY_WITH_DOCUMENTED_NONBLOCKING_CAVEATS" if not gates["G13_K_consistency_under_finalized_protocol"]["pass"] or absent else "READY_FOR_TRAINING")
    ready = {"gate": "FINAL_READINESS_GATE_V1", "generated_utc": t0, "status": status,
             "decision_rule": {"BLOCKED": "any of G1-G12 fails, or K-inconsistent scenes exceed 1 % of the K>=1 (2D) / K>=2 (3D) rows",
                               "READY_WITH_DOCUMENTED_NONBLOCKING_CAVEATS": "G1-G12 pass; K-inconsistent scenes <= 1 % (their finalized X/Y labels are measured and "
                                                                            "replay-consistent; only their K class tag is overstated) and/or some X/Y cell is absent in a split",
                               "READY_FOR_TRAINING": "all gates pass, no K inconsistency, every X/Y cell present in every split"},
             "hard_gate_failures": hard, "gates": {k: v["pass"] for k, v in gates.items()},
             "k_inconsistent": kinc, "k_inconsistency_rates": {"2D": round(rate2, 4), "3D": round(rate3, 4), "threshold": KTHR},
             "absent_xy_cells_by_split": sorted(absent),
             "remaining_blockers": ([] if not k_block else [{
                 "blocker": "K_REPAIR_OR_MINIMALITY_NOT_CONFIRMED_UNDER_FINALIZED_PROTOCOL",
                 "ids_2D_no_X1Y1_order": kinc["2D_selected_without_X1Y1_order"], "ids_3D_no_X1Y1_order": kinc["3D_selected_without_X1Y1_order"],
                 "ids_3D_shorter_repair_proven": kinc["3D_omission_X1Y1_shorter_repair"],
                 "required_fix": "a user decision per flagged scene (manifests/2D_PROPOSED_CORRECTIONS.json, PROPOSED_CORRECTION_MANIFEST.json): "
                                 "(a) declare K a legacy-verified class tag and keep the measured finalized X/Y rows -> status becomes "
                                 "READY_WITH_DOCUMENTED_NONBLOCKING_CAVEATS with no recomputation; or (b) reclassify / remove the scenes "
                                 "(quota change) or (c) replace them with same-class same-split scenes after the same X/Y + omission + replay pass"}]),
             "counts": {"2D": dict(c2), "3D": dict(c3)}, "training_started": False,
             "proposed_corrections_applied": False}
    # ---------------------------------------------------------------- 3D learning-view manifest annotated with replay evidence
    rq = {(q["root_id"], q["qid"]): q for q in json.loads((MAN / "3D_REPLAY_RESULTS.json").read_text())["queries"]}
    okey = lambda rel: "".join(o[-1] for o, _ in rel)
    ann = []
    for l in lab3:
        if l["row_kind"] == "EMPTY_SEQUENCE_YNEG":
            eq = rq.get((l["root_id"], "Y_EMPTY"))
            ann.append({**l, "x_replay": "N/A(empty sequence)",
                        "y_replay": {"verdict": eq["verdict"], "method": "RERUN+REPLAY", "tier": sorted(eq["tags"])} if eq else
                        ("FRESH_RERUN(es_verify)" if l.get("fresh_verified_y") is not None else "NOT_REPLAYED")})
            continue
        tag = "SEL" if l["row_kind"] == "SELECTED_ASSIGNMENT_ORDER" else "OM"
        xq_, yq_ = rq.get((l["root_id"], f"X_{tag}_" + okey(l["relocations"]))), rq.get((l["root_id"], f"Y_{tag}"))
        f = lambda q: None if q is None else {"verdict": q["verdict"], "method": "RERUN+REPLAY" if q.get("rerun") else "STORED_WITNESS_REPLAY",
                                             "tier": sorted(q["tags"])}
        ann.append({**l, "x_replay": f(xq_) or "NOT_REPLAYED", "y_replay": f(yq_) or "NOT_REPLAYED"})
    (MAN / "3D_FINAL_XY_LABEL_MANIFEST_WITH_REPLAY.json").write_text(json.dumps({"version": "3D_XY_LABELS_V4_WITH_REPLAY_GATE_V1",
                                                                                "labels_unchanged_from": "FINAL_3D_DATASET_V4/FINAL_3D_XY_LABEL_MANIFEST.json", "rows": ann}))
    cov = C.Counter((a["row_kind"], "x:" + (a["x_replay"]["method"] if isinstance(a["x_replay"], dict) else a["x_replay"])) for a in ann)
    cov.update((a["row_kind"], "y:" + (a["y_replay"]["method"] if isinstance(a["y_replay"], dict) else a["y_replay"])) for a in ann)
    ready_cov = {"|".join(k): v for k, v in sorted(cov.items())}
    (WK / "3d_row_replay_coverage.json").write_text(json.dumps(ready_cov, indent=1))
    (GATE / "FINAL_TRAINING_READINESS.json").write_text(json.dumps(ready, indent=1))
    (MAN / "FINAL_INTEGRITY_GATES.json").write_text(json.dumps(gates, indent=1, default=str))
    print(json.dumps({"status": status, "hard": hard, "gates": {k: v["pass"] for k, v in gates.items()}, "kinc": {k: len(v) for k, v in kinc.items()},
                      "rates": ready["k_inconsistency_rates"], "absent": sorted(absent)}, indent=1))


if __name__ == "__main__":
    main()
